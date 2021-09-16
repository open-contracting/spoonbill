import codecs
import copy
import functools
import gzip
import json
import logging
import re
from collections import OrderedDict
from itertools import chain
from numbers import Number
from pathlib import Path

import ijson
import jsonref
import requests
from scalpl import Cut

from spoonbill.common import COMBINED_TABLES, SEPARATOR

PYTHON_TO_JSON_TYPE = {
    "list": "array",
    "dict": "object",
    "string": "string",
    "int": "integer",
    "float": "number",
}
LOGGER = logging.getLogger("spoonbill")

ABBREVIATION_KEY = {
    "additionalIdentifiers": "ids",
    "additionalClassifications": "class",
    "documents": "docs",
}

ABBREVIATION_TABLE_NAME = {
    "contracts_implementation": "implementation",
    "contracts_implementation_transactions": "transactions",
}

GZIP_MAGIC_NUMBER = (b"\x1f", b"\x8b")


@functools.lru_cache(maxsize=None)
def common_prefix(path, subpath, separator="/"):
    """Given two paths, returns the longest common sub-path.

    >>> common_prefix('/contracts', '/contracts/items')
    '/contracts'
    >>> common_prefix('/tender/submissionMethod', '/tender/submissionMethodDetails')
    '/tender'
    >>> common_prefix('/tender/items/id', '/tender/items/description')
    '/tender/items'
    >>> common_prefix('/tender/items/0/additionalClassifications/0/id', '/tender/items/0')
    '/tender/items/0'
    """
    paths = [path.split(separator), subpath.split(separator)]
    if len(paths[0]) <= len(paths[1]):
        s1, s2 = paths
    else:
        s2, s1 = paths
    for i, path in enumerate(s1):
        if path != s2[i]:
            common = s1[:i]
            break
    else:
        common = s1
    return separator.join(common)


def iter_file(fd, root, multiple_values=False):
    """Iterate over `root` array in file provided by `filename` using ijson

    :param fd: File descriptor
    :param str root: Array field name inside file
    :param bool multiple_values: Determine line-delimited JSON
    :return: Iterator of bytes read and item as a tuple

    >>> [r for r in iter_file(open('tests/data/ocds-sample-data.json', 'rb'), 'records')]
    []
    >>> len([r for r in iter_file(open('tests/data/ocds-sample-data.json', 'rb'), 'releases')])
    6
    """
    reader = ijson.items(
        fd, prefix=("" if multiple_values else f"{root}.item"), multiple_values=multiple_values, map_type=OrderedDict
    )
    for item in reader:
        yield item


def extract_type(item):
    """Extract item possible types from jsonschema definition.
    >>> extract_type({'type': 'string'})
    ['string']
    >>> extract_type(None)
    []
    >>> extract_type({})
    []
    >>> extract_type({'type': ['string', 'null']})
    ['string', 'null']
    """
    if not item or "type" not in item:
        return []
    type_ = item["type"]
    if not isinstance(type_, list):
        type_ = [type_]
    return type_


def validate_type(type_, item):
    """Validate if python object corresponds to provided type
    >>> validate_type(['string'], 'test_string')
    True
    >>> validate_type(['number'], 11.1)
    True
    >>> validate_type(['number'], 11)
    True
    >>> validate_type(['array'], [])
    True
    >>> validate_type(['array'], {})
    False
    >>> validate_type(['object'], [])
    False
    >>> validate_type(['object'], {})
    True
    """
    if isinstance(item, Number):
        name = "number"
    else:
        name = type(item).__name__
    expected = PYTHON_TO_JSON_TYPE.get(name)
    if expected:
        return expected in type_
    return True


def get_root(table):
    """Extract top level toot table of `table`"""
    while table.parent:
        table = table.parent
    return table


def combine_path(root, path, index="0", separator="/"):
    """Generates index based header for combined column"""
    combined_path = path
    for array in sorted(root.arrays, reverse=True):
        if common_prefix(path, array) == array:
            chunk = separator.join((array, index))
            combined_path = combined_path.replace(array, chunk)
    return combined_path


def get_matching_tables(tables, path):
    """Get list of matching tables for provided path

    Return list is sorted by longest matching path part

    :param tables: List of `Table' objects
    :param path: Path like string
    :return: List of matched by path tables
    """
    candidates = []
    for table in tables.values():
        for candidate in table.path:
            if common_prefix(candidate, path) == candidate:
                candidates.append(table)

    return sorted(candidates, key=lambda c: max((len(p) for p in c.path)), reverse=True)


def generate_table_name(parent_table, parent_key, key):
    """Generates name for non root table, to be used as sheet name

    :param str parent_table: Parent table name
    :param str parent_key: Parent object field name
    :param str key: Current object field name
    :return: Generated table name
    :rtype: str

    >>> generate_table_name('tenders', 'tender', 'items')
    'tenders_items'
    >>> generate_table_name('tenders', 'items', 'additionalClassifications')
    'tenders_items_class'
    >>> generate_table_name('parties', 'parties', 'roles')
    'parties_roles'
    """

    if key in ABBREVIATION_KEY:
        key = ABBREVIATION_KEY[key]

    if parent_key in parent_table:
        table_name = f"{parent_table}_{key}"
    else:
        table_name = f"{parent_table}_{parent_key}_{key}"

    if table_name in ABBREVIATION_TABLE_NAME:
        table_name = ABBREVIATION_TABLE_NAME[table_name]

    if len(table_name) >= 31:
        if parent_key in parent_table:
            table_name = f"{parent_table}_{key[:5]}"
        else:
            table_name = f"{parent_table}_{parent_key[:5]}_{key[:5]}"

    return table_name


def insert_after_key(columns, insert, last_key):
    data = OrderedDict()
    for key, val in columns.items():
        data[key] = val
        if key == last_key:
            for k, v in insert.items():
                data[k] = v
    return data


def resolve_file_uri(file_path):
    """Read json file from provided uri
    :param file_path: URI to file, could be url or path
    :return: Read file as dictionary
    """
    if str(file_path).startswith("http://") or str(file_path).startswith("https://"):
        return requests.get(file_path).json()
    if isinstance(file_path, (str, Path)):
        with codecs.open(file_path, encoding="utf-8") as fd:
            return json.load(fd, object_pairs_hook=OrderedDict)


def read_lines(path):
    """Read file as lines"""
    with open(path) as fd:
        return [line.strip() for line in fd.readlines()]


def get_pointer(table, abs_path, path, split, *, index=None):
    """Combine path and abs_path in order to fit table columns

    For example /tender/items/0/id should be /tender/items/0/id for tenders table
    but /tender/items/id for tenders_items table
    """
    array = table.is_array(path)
    if index and (array or table.is_combined):
        return SEPARATOR.join((abs_path, index))
    if table.is_root:
        return abs_path

    if array:
        paths = abs_path.split(SEPARATOR)
        prefix = ""

        for index, pth in enumerate(paths, 1):
            if pth.isdigit():
                continue
            if not pth:
                continue
            prefix = SEPARATOR.join((prefix, pth))
            if prefix == array:
                break
        pointer = SEPARATOR.join(paths[index:])
        if pointer:
            return SEPARATOR.join((prefix, pointer))
        return prefix
    return path


class RepeatFilter(logging.Filter):
    """
    Logger filter to avoid repeating of same messages during file processing
    """

    def filter(self, record):
        current_log = (record.module, record.levelno, record.msg)
        if current_log != getattr(self, "last_log", None):
            self.last_log = current_log
            return True
        return False


def make_count_column(array):
    """Make column name for arrays elements count

    >>> make_count_column('/tender/items')
    '/tender/itemsCount'
    >>> make_count_column('/tender/items/additionalClassifications')
    '/tender/items/additionalClassificationsCount'
    >>> make_count_column('/tender/items/')
    '/tender/itemsCount'
    """

    return array.rstrip("/") + "Count"


def get_reader(path):
    """
    Get reader function for a respective file format
    :param path: path to a file
    :return: reader function
    """
    first_bytes = open(path, "rb").read(2)
    if (first_bytes[0:1], first_bytes[1:2]) == GZIP_MAGIC_NUMBER:
        return gzip.open
    else:
        return open


def get_order(properties):
    order = [name for name in chain(properties, COMBINED_TABLES)]
    if "tender" in order:
        order[order.index("tender")] = "tenders"
    return order


def nonschema_title_formatter(title):
    """
    Formatting a path, that is absent in schema, to human-readable form
    :param title: str
    :return: formatted title

    >>> nonschema_title_formatter('legalEntityTypeDetail')
    'Legal Entity Type Detail'
    >>> nonschema_title_formatter('fuenteFinanciamiento')
    'Fuente Financiamiento'
    >>> nonschema_title_formatter('Óóó-Ñññ_Úúú')
    'Óóó Ñññ Úúú'
    """
    title = title.replace("_", " ").replace("-", " ")
    title = re.sub(r"(?<![A-Z])(?<!^)([A-Z])", r" \1", title)
    title = title.replace("  ", " ").replace("/", ": ")
    if title.startswith(": "):
        title = title[2:]
    title = title.title()
    return title


class SchemaHeaderExtractor:
    """
    Human-readable headers extracted from schema

    :param schema: The dataset's schema
    """

    def __init__(self, schema):
        self.schema = schema
        if not isinstance(self.schema, jsonref.JsonRef) and not isinstance(self.schema, OrderedDict):
            self.schema = jsonref.JsonRef.replace_refs(self.schema)

    def _get_header(self, id, paths):
        final_title = []
        for path in paths:
            _object = Cut(self.schema)["properties." + ".".join(path[:-1])]
            if hasattr(_object, "__reference__") and "title" in _object.__reference__:
                title = _object.__reference__["title"]
            else:
                title = Cut(self.schema)["properties." + ".".join(path)]
            if isinstance(title, dict):
                continue
            final_title.append(title)
        if id.startswith("/documents"):
            final_title = final_title[3:]
        if "Organization reference" in final_title:
            final_title.remove("Organization reference")
        return ": ".join(final_title)

    def get_header(self, id, paths):
        if paths and isinstance(paths, list):
            return self._get_header(id, paths)
        elif paths == []:
            return nonschema_title_formatter(id)
        else:
            return nonschema_title_formatter(paths)


def generate_paths(source):
    """
    Generate full paths for nested dictionary or alike object
    :param source: Input object
    :return: List of paths
    """
    paths = []
    if isinstance(source, dict):
        for k, v in source.items():
            paths.append([k])
            paths += [[k] + x for x in generate_paths(v)]
    return paths


def add_paths_to_schema(schema):
    """
    Extracts full path for each title in schema; creates paths list of full title for each
    :param unres_schema: Unresolved schema
    :param schema: Schema object that will be updated
    :return: Schema with full title paths
    """
    proxy = Cut(copy.deepcopy(schema))
    updated_items = {}
    for table in proxy["properties"].keys():
        path_item = Cut({table: copy.deepcopy(proxy["properties"][table])})
        # Generating path to each title in schema
        for path in generate_paths({table: proxy["properties"][table]}):
            if path[-1] == "title":
                object_path = ".".join(path[:-1])
                path_item[object_path]["$path"] = path
        updated_items[table] = path_item[table]
    proxy["properties"] = updated_items
    # Generating array with title paths for each title in schema
    title_paths = [path for path in title_path(proxy["properties"])]

    for path_list in title_paths:
        location = "properties." + ".".join(path_list[-1][:-1])
        proxy[location]["$title"] = path_list

    return proxy


def title_path(schema, path=[]):
    """
    Get path for each previous title and form full list of titles for each object
    :param schema: Object
    :param path: List of paths for full title
    :return:
    """
    for k, v in schema.items():
        newpath = path
        if "$path" in schema:
            newpath = path + [schema.get("$path", [])]
        if isinstance(v, dict):
            for result in title_path(v, newpath):
                if result:
                    yield result
        else:
            if newpath:
                yield newpath


def get_nestiness(abs_path):
    arrays = [c for c in abs_path if c.isdigit()]
    return len(arrays) - 1


def get_path_for_array_col(abs_path, array):
    nestiness = get_nestiness(abs_path)
    chunks = abs_path.split("/")[len(array.split("/")) + nestiness :]
    return "/".join(chain([array], chunks))

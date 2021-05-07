import codecs
import json
import logging
from collections import OrderedDict
from dataclasses import replace
from itertools import chain
from numbers import Number

import ijson

from spoonbill.common import DEFAULT_FIELDS_COMBINED

PYTHON_TO_JSON_TYPE = {
    "list": "array",
    "dict": "object",
    "string": "string",
    "int": "integer",
    "float": "number",
}
LOGGER = logging.getLogger("spoonbill")


def common_prefix(path, subpath, separator="/"):
    """Given two paths, returns the longest common sub-path.

    >>> common_prefix('/contracts', '/contracts/items')
    '/contracts'
    >>> common_prefix('/tender/submissionMethod', '/tender/submissionMethodDetails')
    '/tender'
    >>> common_prefix('/tender/items/id', '/tender/items/description')
    '/tender/items'
    """
    paths = path.split(separator)
    subpaths = subpath.split(separator)
    common = [chunk for chunk in paths if chunk in subpaths]
    return separator.join(common)


def iter_file(filename, root):
    """Iterate over `root` array in file provided by `filename` using ijson

    :param str filename: Path to file
    :param str root: Array field name inside file
    :return: Array items iterator

    >>> [r for r in iter_file('tests/data/ocds-sample-data.json', 'records')]
    []
    >>> len([r for r in iter_file('tests/data/ocds-sample-data.json', 'releases')])
    6
    """
    with open(filename, "rb") as fd:
        reader = ijson.items(fd, f"{root}.item")
        for item in reader:
            yield item


def extract_type(item):
    """Exrtact item possible types from jsonschema definition.
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


def prepare_title(item, parent):
    """Attempts to extract human friendly table header from schema

    :param item: Schema description of item for which title should be generated
    :param parent: Schema description of item parent object
    :return: Generated title
    """
    title = []
    if hasattr(parent, "__reference__") and parent.__reference__.get("title"):
        parent_title = parent.__reference__.get("title", "")
    else:
        parent_title = parent.get("title", "")
    for chunk in chain(parent_title.split(), item["title"].split()):
        chunk = chunk.capitalize()
        if chunk not in title:
            title.append(chunk)
    return " ".join(title)


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
    'tenders_items_addit'
    >>> generate_table_name('parties', 'parties', 'roles')
    'parties_roles'
    """
    if parent_key in parent_table:
        return f"{parent_table}_{key[:5]}"
    else:
        return f"{parent_table}_{parent_key[:5]}_{key[:5]}"


def generate_row_id(ocid, item_id, parent_key=None, top_level_id=None):
    """Generates uniq rowID for table row

    :param str ocid: OCID of release
    :param str item_id: Corresponding object id for current row, e.g. tender/id
    :param str parent_key: Corresponding field name for current object frow which row is constructed, e.g. documents
    :param top_level_id: The ID of whole release
    :return: Generated rowID
    :rtype: str

    >>> generate_row_id('ocid', 'item', 'documens', 'top')
    'ocid/top/documens:item'
    >>> generate_row_id('ocid', 'item', '', '1')
    'ocid/1/item'
    >>> generate_row_id('ocid', 'item', 'documens', '')
    'ocid/documens:item'
    >>> generate_row_id('ocid', 'item', '', '')
    'ocid/item'
    """
    tail = f"{parent_key}:{item_id}" if parent_key else item_id
    if top_level_id:
        return f"{ocid}/{top_level_id}/{tail}"
    return f"{ocid}/{tail}"


def recalculate_headers(root, abs_path, key, item, max_items, separator="/"):
    """Rebuild table headers when array is expanded with attempt to preserve order

    Also deletes combined columns from tables columns if array becomes bigger than threshold

    :param root: Table for which headers should be rebuild
    :param abs_path: Full jsonpath to array
    :param key: Array field name
    :param item: Array items
    :param max_items: Maximum elements in array before it should be split into table
    :param separator: header path separator
    """
    head = OrderedDict()
    tail = OrderedDict()
    cols = head
    base_prefix = separator.join((abs_path, key))
    zero_prefix = separator.join((base_prefix, "0"))
    should_split = len(item) > max_items

    zero_cols = {
        col_p: col
        for col_p, col in root.combined_columns.items()
        if col_p not in DEFAULT_FIELDS_COMBINED and common_prefix(col_p, zero_prefix) == zero_prefix
    }
    new_cols = {}
    for col_i, _ in enumerate(item, 1):
        col_prefix = separator.join((base_prefix, str(col_i)))
        for col_p, col in zero_cols.items():
            col_id = col.id.replace(zero_prefix, col_prefix)
            new_cols[col_id] = replace(col, id=col_id)

    head_updated = False
    for col_p, col in root.combined_columns.items():
        if col_p in zero_cols and not head_updated:
            head.update(zero_cols)
            tail.update(new_cols)
            head_updated = True
            cols = tail
        else:
            if col_p not in cols:
                cols[col_p] = col
    if should_split:
        for col_path in chain(zero_cols, new_cols):
            root.columns.pop(col_path, "")

    for col_path, col in chain(head.items(), tail.items()):
        root.combined_columns[col_path] = col


def resolve_file_uri(file_path):
    """Read json file from provided uri

    :param file_path: URI to file, could be url or path
    :return: Read file as dictionary
    """
    if file_path.startswith("http"):
        import requests

        return requests.get(file_path).json()
    else:
        with codecs.open(file_path, encoding="utf-8") as fd:
            return json.load(fd)


def get_headers(table, options):
    """Generate table headers respecting human and override options

    :param table: Target table
    :param options: Flattening options
    :return: Mapping between column and its header
    """
    split = options.split
    headers = {c: c for c in table.available_rows(split=split)}
    if options.pretty_headers:
        for c in headers:
            headers[c] = table.titles.get(c, c)
    if options.headers:
        for c, h in options.headers.items():
            headers[c] = h
    return headers


def get_pointer(pointer, abs_path, key, split, separator="/", is_root=True):
    if split or is_root:
        return pointer
    return separator.join((abs_path, key))

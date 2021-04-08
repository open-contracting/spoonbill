from itertools import chain
from dataclasses import replace
from collections import OrderedDict
from os.path import commonpath

import ijson

from spoonbill.common import DEFAULT_FIELDS_COMBINED

# for now we care only about types which can break flattening
_PYTHON_TO_JSON_TYPE = {'list': 'array', 'dict': 'object'}


def iter_file(filename, root):
    with open(filename) as fd:
        reader = ijson.items(fd, f'{root}.item')
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
    if not item or 'type' not in item:
        return []
    type_ = item['type']
    if not isinstance(type_, list):
        type_ = [type_]
    return type_


def validate_type(type_, item):
    """ Validate if python object corresponds to provided type
    >>> validate_type(['string'], 'test_string')
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
    name = type(item).__name__
    if expected := _PYTHON_TO_JSON_TYPE.get(name):
        return expected in type_
    return True


def get_root(table):
    """ Extract top level toot table of `table` """
    while table.parent:
        table = table.parent
    return table


def combine_path(root, path, index="0", separator="/"):
    combined_path = path
    for array in sorted(root.arrays, reverse=True):
        if commonpath((path, array)) == array:
            chunk = separator.join((array, index))
            combined_path = combined_path.replace(array, chunk)
    return combined_path


def prepare_title(item, parent):
    title = []
    if hasattr(parent, '__reference__') and parent.__reference__.get('title'):
        parent_title = parent.__reference__.get('title', '')
    else:
        parent_title = parent.get('title', '')
    for chunk in chain(parent_title.split(), item['title'].split()):
        chunk = chunk.capitalize()
        if chunk not in title:
            title.append(chunk)
    return ' '.join(title)


def get_maching_tables(tables, path):
    candidates = []
    for table in tables.values():
        for candidate in table.path:
            if commonpath((candidate, path)) == candidate:
                candidates.append(table)
    return sorted(
        candidates,
        key=lambda c: max((len(p) for p in c.path)),
        reverse=True
    )


def generate_table_name(parent_table, parent_key, key):
    """ Generates name for non root table, to be used as sheet name

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
        return f'{parent_table}_{key[:5]}'
    else:
        return f'{parent_table}_{parent_key[:5]}_{key[:5]}'


def generate_row_id(ocid, item_id, parent_key=None, top_level_id=None):
    """ Generates uniq rowID for table row

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
    tail = f'{parent_key}:{item_id}' if parent_key else \
        item_id
    if top_level_id:
        return f'{ocid}/{top_level_id}/{tail}'
    return f'{ocid}/{tail}'


def recalculate_headers(root, abs_path, key, item, separator='/'):
    """Recalculate table combined headers when array is expanded with attempt to preserve order"""
    head = OrderedDict()
    tail = OrderedDict()
    cols = head
    base_prefix= separator.join((abs_path, key))
    for col_path, col in root.combined_columns.items():
        cols[col_path] = col
        if col_path in DEFAULT_FIELDS_COMBINED or base_prefix not in col_path:
            continue

        for col_i, _ in enumerate(item, 1):
            prev_col_prefix = separator.join((base_prefix, str(col_i - 1)))
            new_col_prefix = separator.join((base_prefix, str(col_i)))
            if commonpath((col_path, prev_col_prefix)) == prev_col_prefix:
                new_id = col.id.replace(prev_col_prefix, new_col_prefix)
                new_col = replace(col, id=new_id)
                cols = tail
                cols[new_id] = new_col
    for col_path, col in chain(head.items(), tail.items()):
        root.combined_columns[col_path] = col

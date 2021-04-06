from itertools import chain
from os.path import commonpath

import ijson


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
    while table.parent:
        table = table.parent
    return table


def combine_path(root, path, index="0", separator="/"):
    combined_path = path
    for array in sorted(root.arrays, reverse=True):
        if path.startswith(array):
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


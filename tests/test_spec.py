from collections import OrderedDict
from spoonbill.spec import Table, Column
from spoonbill.utils import combine_path


def test_combine_path():
    root = Table(
        name='tenders',
        path=['/tender'],
        columns=OrderedDict([
            ('ocid', Column(title='ocid', type='string', id='ocid', hits=0)),
            ('id', Column(title='id', type='string', id='id', hits=0)),
            ('rowID', Column(title='rowID', type='string', id='rowID', hits=0)),
            ('parentID', Column(title='parentID', type='string', id='parentID', hits=0))]),
        combined_columns=OrderedDict([
            ('ocid', Column(title='ocid', type='string', id='ocid', hits=0)),
            ('id', Column(title='id', type='string', id='id', hits=0)),
            ('rowID', Column(title='rowID', type='string', id='rowID', hits=0)),
            ('parentID', Column(title='parentID', type='string', id='parentID', hits=0))]),
        arrays={'/tender/submissionMethod': 0, '/tender/items': 0, '/tender/items/additionalClassifications': 0})
    path = combine_path(root, '/tender/id')
    assert path == '/tender/id'
    path = combine_path(root, '/tender/submissionMethodDetails')
    assert path == '/tender/submissionMethodDetails'
    path = combine_path(root, '/tender/submissionMethod')
    assert path == '/tender/submissionMethod/0'
    path = combine_path(root, '/tender/items/id')
    assert path == '/tender/items/0/id'
    path = combine_path(root, '/tender/items/additionalClassifications/id')
    assert path == '/tender/items/0/additionalClassifications/0/id'

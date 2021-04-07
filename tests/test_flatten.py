from spoonbill.flatten import Flattener
from spoonbill.stats import DataPreprocessor
from .data import TEST_ROOT_TABLES, TEST_COMBINED_TABLES


def test_flatten(schema, releases):
    ''''''
    spec = DataPreprocessor(
        schema,
        TEST_ROOT_TABLES,
        combined_tables=TEST_COMBINED_TABLES
    )
    options = {
        'selection': {'tenders': {'split': True}, 'parties': {'split': False}},
        'pretty_headers': False
    }
    flattener = Flattener(options, spec.tables)
    for flat in flattener.flatten(releases):
            for name, rows in flat.items():
                for row in rows:
                    assert 'id' in row
                    assert 'ocid' in row
                    assert 'rowID' in row
from spoonbill.flatten import Flattener
from spoonbill.stats import DataPreprocessor
from .data import TEST_ROOT_TABLES, TEST_COMBINED_TABLES


def test_flatten(schema, releases):
    ''''''
    spec = DataPreprocessor(
        schema,
        TEST_ROOT_TABLES,
        combined_tables=TEST_COMBINED_TABLES,
        propagate_cols=['/ocid'])
    options = {
        'selection': {'tenders': {'split': True}, 'parties': {'split': False}},
        'pretty_headers': False
    }
    flattener = Flattener(options, spec.dump()['tables'])
    for flat in flattener.flatten(releases):
            for name, rows in flat.items():
                for row in rows:
                    assert row
                    

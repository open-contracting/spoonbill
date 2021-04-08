from spoonbill.spec import Table, Column
from spoonbill.stats import DataPreprocessor
from jsonpointer import resolve_pointer

from .data import *

COLUMNS = {
    'tenders': tenders_columns,
    'parties': parties_columns,
    'awards': awards_columns,
    'contracts': contracts_columns,
    'planning': planning_columns
}
COMBINED_COLUMNS = {
    'tenders': tenders_combined_columns,
    'parties': parties_combined_columns,
    'awards': awards_combined_columns,
    'contracts': contracts_combined_columns,
    'planning': planning_combined_columns
}
ARRAYS_COLUMNS = {
    'tenders': tenders_arrays,
    'parties': parties_arrays,
    'awards': awards_arrays,
    'contracts': contracts_arrays,
    'planning': planning_arrays
}


def test_parse_schema(schema):
    spec = DataPreprocessor(
        schema,
        TEST_ROOT_TABLES,
        combined_tables=TEST_COMBINED_TABLES
    )
    for name in TEST_ROOT_TABLES:
        table = spec[name]
        assert isinstance(table, Table)
        assert table.total_rows == 0
        assert not table.parent
        assert table.is_root
        assert not table.is_combined
        for col_id in COLUMNS[name]:
            col = table[col_id]
            assert isinstance(col, Column)
            assert col.hits == 0
            assert col.id == col_id
            assert col.title == OCDS_TITLES_COMBINED[col_id]

        for col_id in COMBINED_COLUMNS[name]:
            col = table.combined_columns[col_id]
            assert col.hits == 0
            assert col.id == col_id
            assert col.title == OCDS_TITLES_COMBINED[col_id]

        for col_id in ARRAYS_COLUMNS[name]:
            col = table.arrays[col_id]
            assert col == 0


def test_get_table(schema, releases):
    spec = DataPreprocessor(
        schema,
        TEST_ROOT_TABLES,
        combined_tables=TEST_COMBINED_TABLES)
    table = spec.get_table('/tender')
    assert table.name == 'tenders'
    table = spec.get_table('/tender/submissionMethodDetails')
    assert table.name == 'tenders'
    table = spec.get_table('/tender/submissionMethod')
    assert table.name == 'tenders_submi'

    table = spec.get_table('/tender/items/id')
    assert table.name == 'tenders_items'

    table = spec.get_table('/tender/items/additionalClassifications/id')
    assert table.name == 'tenders_items_addit'

    table = spec.get_table('/planning')
    assert table.name == 'planning'
    table = spec.get_table('/parties')
    assert table.name == 'parties'

    table = spec.get_table('/parties/roles')
    assert table.name == 'parties_roles'


def test_generate_titles(schema, releases):
    spec = DataPreprocessor(
        schema,
        TEST_ROOT_TABLES,
        combined_tables=TEST_COMBINED_TABLES)
    for table in spec.tables.values():
        for path, title in table.titles.items():
            assert OCDS_TITLES_COMBINED[path] == title


def test_parse_with_combined_tables(schema):
    pass


def test_analyze(schema, releases):
    spec = DataPreprocessor(
        schema,
        TEST_ROOT_TABLES,
        combined_tables=TEST_COMBINED_TABLES)

    spec.process_items(releases)


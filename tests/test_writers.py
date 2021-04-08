from spoonbill.writer import CSVWriter, XlsxWriter
from spoonbill.stats import DataPreprocessor
from pathlib import Path
from csv import DictReader

from .data import *

ID_FIELDS = {
    'tenders': '/tender/id',
    'parties': '/parties/id'
}


def test_writer_init(schema, tmpdir, flatten_options):
    spec = DataPreprocessor(
        schema,
        TEST_ROOT_TABLES,
        combined_tables=TEST_COMBINED_TABLES)

    tables = {
        name: table for name, table
        in spec.tables.items() if name in flatten_options.selection
    }
    for name, table in tables.items():
        table.inc_column(ID_FIELDS[name])
    workdir = Path(tmpdir)
    writers = [CSVWriter(workdir, tables, flatten_options),
               XlsxWriter(workdir, tables, flatten_options)]
    for writer in writers:
        writer.close()
    path = workdir / 'result.xlsx'
    assert path.is_file()
    for name in flatten_options.selection:
        path = workdir / f'{name}.csv'
        assert path.is_file()


def test_headers_filtering(schema, tmpdir, flatten_options):
    spec = DataPreprocessor(
        schema,
        TEST_ROOT_TABLES,
        combined_tables=TEST_COMBINED_TABLES)

    tables = {
        name: table for name, table
        in spec.tables.items() if name in flatten_options.selection
    }
    for name, table in tables.items():
        table.inc_column(ID_FIELDS[name])
    workdir = Path(tmpdir)
    writer = CSVWriter(workdir, tables, flatten_options)
    writer.writeheaders()
    writer.close()
    for name in flatten_options.selection:
        path = workdir / f'{name}.csv'
        with open(path) as fd:
            reader = DictReader(fd)
            headers = reader.fieldnames
            assert len(headers) == 1
            assert headers[0] == ID_FIELDS[name]

import csv

import openpyxl

from spoonbill.writers import CSVWriter, XlsxWriter


def read_csv_headers(path):
    with open(path) as fd:
        return [c for c in csv.DictReader(fd).fieldnames]


def read_xlsx_headers(path, sheet):
    wb = openpyxl.load_workbook(filename=path)
    sheet = wb[sheet]
    columns = sheet.columns
    return [c.value for cell in columns for c in cell]


def get_writers(workdir, tables, options, schema=None):

    with CSVWriter(workdir, tables, options, schema=schema) as csv, XlsxWriter(
        workdir, tables, options, schema=schema
    ) as xlsx:
        return [csv, xlsx]


def prepare_tables(spec, options, inc_columns=None):
    tables = {name: table for name, table in spec.tables.items() if name in options.selection}
    if inc_columns:
        for name, table in tables.items():
            table.inc_column(inc_columns[name], inc_columns[name])
    return tables

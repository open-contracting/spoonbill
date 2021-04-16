import csv
import openpyxl

from spoonbill.writers import CSVWriter, XlsxWriter


def read_csv_headers(path):
    with open(path) as fd:
        reader = csv.DictReader(fd)
        return [c for c in reader.fieldnames]


def read_xlsx_headers(path, sheet):
    wb = openpyxl.load_workbook(filename=path)
    sheet = wb[sheet]
    columns = sheet.columns
    return [c.value for cell in columns for c in cell]


def read_headers(path, sheet, type):
    if type == "csv":
        return read_csv_headers(path)
    return read_xlsx_headers(path, sheet)


def get_writers(workdir, tables, options):
    writers = [
        CSVWriter(workdir, tables, options),
        XlsxWriter(workdir, tables, options),
    ]
    for writer in writers:
        writer.writeheaders()
        writer.close()
    return writers


def prepare_tables(spec, options, inc_columns=None):
    tables = {
        name: table for name, table in spec.tables.items() if name in options.selection
    }
    if inc_columns:
        for name, table in tables.items():
            table.inc_column(inc_columns[name])
    return tables

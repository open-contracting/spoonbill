import collections
import logging

import xlsxwriter
from xlsxwriter.exceptions import XlsxWriterException

from spoonbill.common import ROOT_TABLES
from spoonbill.i18n import _
from spoonbill.utils import get_headers

LOGGER = logging.getLogger("spoonbill")


class XlsxWriter:
    """Writer class with output to xlsx files

    For each table will be created corresponding sheet inside workbook

    :param workdir: Working directory
    :param tables: Tables data
    :options: Flattening options
    """

    name = "xlsx"

    def __init__(self, workdir, tables, options):
        self.workdir = workdir
        self.workbook = xlsxwriter.Workbook(workdir / "result.xlsx", {"constant_memory": True})
        self.row_counters = {}
        self.tables = tables
        self.options = options
        self.col_index = collections.defaultdict(dict)
        self.names = {}

    def writeheaders(self):
        """Write headers to output file"""
        for name, table in self.tables.items():
            opt = self.options.selection[name]
            table_name = opt.name or name
            self.names[name] = table_name
            sheet = self.workbook.add_worksheet(table_name)
            headers = get_headers(table, opt)
            for col_index, col_name in enumerate(headers):
                self.col_index[name][col_name] = col_index
                try:
                    sheet.write(0, col_index, headers[col_name])
                except XlsxWriterException as err:
                    LOGGER.error(
                        _("Failed to write header {} to xlsx sheet {} with error {}").format(col_name, name, err)
                    )
            self.row_counters[name] = 1

    def writerow(self, table, row):
        """Write row to output file"""
        table_name = self.names.get(table, table)
        sheet = self.workbook.get_worksheet_by_name(table_name)

        for column, value in row.items():
            if any(field in column for field in ROOT_TABLES["buyer"]):
                col_index = len(self.col_index[table])
            else:
                col_index = self.col_index[table][column]
            try:
                sheet.write(self.row_counters[table], col_index, value)
            except XlsxWriterException as err:
                LOGGER.error(_("Failed to write column {} to xlsx sheet {} with error {}").format(column, table, err))

        self.row_counters[table] += 1

    def close(self):
        """Finish work"""
        self.workbook.close()

from xlsxwriter.exceptions import XlsxWriterException

import xlsxwriter
import collections
import logging

from spoonbill.i18n import _
from spoonbill.utils import get_headers


LOGGER = logging.getLogger('spoonbill')


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
        self.workbook = xlsxwriter.Workbook(
            workdir / "result.xlsx", {"constant_memory": True}
        )
        self.row_counters = {}
        self.tables = tables
        self.options = options
        self.col_index = collections.defaultdict(dict)

    def writeheaders(self):
        """Write headers to output file"""
        for table_key, opt in self.self.options.selection.items():
            split = opt.split
            sheet = self.workbook.add_worksheet(table_key)
            headers = get_headers(self.tables[table_key], opt)
            for col_index, col_name in enumerate(headers):
                self.col_index[table_key][col_name] = col_index
                try:
                    sheet.write(0, col_index, headers[col_name])
                except XlsxWriterException as err:
                    LOGGER.error(_("Failed to write header {} to xlsx sheet {} with error {}").format(
                        col_name, table_key, err
                    ))
            self.row_counters[table_key] = 1

    def writerow(self, table, row):
        """Write row to output file"""
        sheet = self.workbook.get_worksheet_by_name(table)

        for column, value in row.items():
            col_index = self.col_index[table][column]
            try:
                sheet.write(self.row_counters[table], col_index, value)
            except XlsxWriterException as err:
                LOGGER.error(_("Failed to write column {} to xlsx sheet {} with error {}").format(
                    column, table, err
                ))

        self.row_counters[table] += 1

    def close(self):
        """Finish work"""
        self.workbook.close()
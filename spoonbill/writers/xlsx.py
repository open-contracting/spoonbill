import collections
import logging

import xlsxwriter
from xlsxwriter.exceptions import XlsxWriterException

from spoonbill.i18n import _
from spoonbill.writers.base_writer import BaseWriter

LOGGER = logging.getLogger("spoonbill")


class XlsxWriter(BaseWriter):
    """
    Writer class with output to XLSX files.

    For each table, a corresponding sheet in an Excel workbook will be created.
    """

    name = "xlsx"

    def __init__(self, workdir, tables, options, schema, filename="result.xlsx"):
        """
        :param workdir: Working directory
        :param tables: The table objects
        :param options: Flattening options
        """

        super().__init__(workdir, tables, options, schema=schema)
        self.col_index = collections.defaultdict(dict)
        self.path = workdir / filename
        self.workbook = xlsxwriter.Workbook(self.path, {"constant_memory": True})
        self.row_counters = {}

    def __enter__(self):
        """
        Write the headers to the output file.
        """

        for name, table in self.tables.items():
            table_name, headers = self.init_sheet(name, table)
            sheet = self.workbook.add_worksheet(table_name)

            for col_index, col_name in enumerate(headers):
                self.col_index[name][col_name] = col_index
                try:
                    sheet.write(0, col_index, headers[col_name])
                except XlsxWriterException as err:
                    LOGGER.error(
                        _("Failed to write header {} to xlsx sheet {} with error {}").format(col_name, name, err)
                    )
            self.row_counters[name] = 1
        return self

    def __exit__(self, *args):
        """
        Close the workbook.
        """
        LOGGER.info(_("Dumped all sheets to file to file '{}'").format(self.path))
        self.workbook.close()

    def writerow(self, table, row):
        """
        Write a row to the output file.
        """

        table_name = self.names.get(table, table)
        sheet = self.workbook.get_worksheet_by_name(table_name)
        columns = self.col_index[table]
        if not columns:
            LOGGER.error(_("Invalid table {}").format(table))
            return

        for column, value in row.items():
            if isinstance(value, bool):
                value = str(value)
            try:
                col_index = columns[column]
            except KeyError:
                LOGGER.error(
                    _("Operation produced invalid path. This a software bug, please send issue to developers")
                )
                LOGGER.error(_("Failed to write column {} to xlsx sheet {}").format(column, table))
                return
            try:
                sheet.write(self.row_counters[table], col_index, value)
            except XlsxWriterException as err:
                LOGGER.error(_("Failed to write column {} to xlsx sheet {} with error {}").format(column, table, err))

        self.row_counters[table] += 1

import csv
import logging
from collections import defaultdict

from spoonbill.i18n import _
from spoonbill.writers.base_writer import BaseWriter

LOGGER = logging.getLogger("spoonbill")


class CSVWriter(BaseWriter):
    """Writer class with output to csv files
    For each table will be created corresponding csv file
    :param workdir: Working directory
    :param tables: Tables data
    :options: Flattening options
    """

    name = "csv"

    def __init__(self, workdir, tables, options):
        super().__init__(workdir, tables, options)
        self.writers = {}
        self.fds = []

    def __enter__(self):
        """Write headers to output file"""
        for name, table in self.tables.items():
            table_name, headers = self.init_sheet(name, table)

            try:
                path = self.workdir / f"{table_name}.csv"
                LOGGER.info(_("Dumping table '{}' to file '{}'").format(table_name, path))
                fd = open(path, "w")
            except (IOError, OSError) as e:
                LOGGER.error(_("Failed to open file {} with error {}").format(path, e))
                return
            writer = csv.DictWriter(fd, headers)
            self.fds.append(fd)
            self.writers[name] = writer

        for name, writer in self.writers.items():
            headers = self.headers[name]
            try:
                writer.writerow(headers)
            except ValueError as err:
                LOGGER.error(_("Failed to headers with error {}").format(err))
        return self

    def __exit__(self, *args):
        for fd in self.fds:
            fd.close()

    def writerow(self, table, row):
        """Write row to output file"""
        try:
            self.writers[table].writerow(row)
        except ValueError as err:
            LOGGER.error(_("Operation produced invalid path. This a software bug, please send issue to developers"))
            LOGGER.error(_("Failed to write row {} with error {}").format(row.get("rowID"), err))
        except KeyError:
            LOGGER.error(_("Invalid table {}").format(table))

import csv
import logging

from spoonbill.i18n import _
from spoonbill.utils import get_headers

LOGGER = logging.getLogger("spoonbill")


class CSVWriter:
    """Writer class with output to csv files

    For each table will be created corresponding csv file

    :param workdir: Working directory
    :param tables: Tables data
    :options: Flattening options
    """

    name = "csv"

    def __init__(self, workdir, tables, options):
        self.workdir = workdir
        self.writers = {}
        self.fds = []
        self.tables = tables
        self.options = options
        self.headers = {}
        self.names_counter = {}
        for name, table in self.tables.items():
            opt = self.options.selection[name]
            headers = get_headers(table, opt)
            self.headers[name] = headers
            table_name = opt.name or name

            if table_name not in self.names_counter:
                self.names_counter[table_name] = 0
            else:
                self.names_counter[table_name] += 1
                table_name += str(self.names_counter[table_name])

            try:
                path = workdir / f"{table_name}.csv"
                fd = open(path, "w")
            except (IOError, OSError) as e:
                LOGGER.error(_("Failed to open file {} with error {}").format(path, e))
                return
            writer = csv.DictWriter(fd, headers)
            self.fds.append(fd)
            self.writers[name] = writer

    def writeheaders(self):
        """Write headers to output file"""
        for name, writer in self.writers.items():
            headers = self.headers[name]
            try:
                writer.writerow(headers)
            except ValueError as err:
                LOGGER.error(_("Failed to headers with error {}").format(err))

    def writerow(self, table, row):
        """Write row to output file"""
        try:
            self.writers[table].writerow(row)
        except ValueError as err:
            LOGGER.error(_("Failed to write row {} with error {}").format(row["rowID"], err))

    def close(self):
        """Finish work"""
        for fd in self.fds:
            fd.close()

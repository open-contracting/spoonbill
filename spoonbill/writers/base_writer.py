from collections import defaultdict

from spoonbill.utils import SchemaHeaderExtractor


class BaseWriter:
    """
    Base writer class
    """

    def __init__(self, workdir, tables, options, schema=None, unres_schema_path=None):
        """
        :param workdir: Working directory
        :param tables: The table objects
        :param options: Flattening options
        """
        self.workdir = workdir
        self.tables = tables
        self.options = options
        self.names = {}
        self.headers = {}
        self.names_counter = defaultdict(int)
        self.schema = schema
        self.unres_schema_path = unres_schema_path
        self.schema_headers = SchemaHeaderExtractor(self.schema, self.unres_schema_path) if schema else None

    def get_headers(self, table, options):
        """
        Return a table's headers, respecting the human and override options.

        :param table: A table object
        :param options: Flattening options
        :return: Mapping between the machine-readable headers and the output headers
        """
        # split = options.split and (table.roll_up or table.should_split)
        split = options.split and table.should_split
        headers = {c: c for c in table.available_rows(split=split)}
        if options.pretty_headers:
            for c in headers:
                headers[c] = self.schema_headers.get_header(c) if self.schema_headers else c
        if options.headers:
            for c, h in options.headers.items():
                headers[c] = h
        return headers

    def _name_check(self, table_name):
        self.names_counter[table_name] += 1
        if self.names_counter[table_name] > 1:
            table_name += str(self.names_counter[table_name] - 1)
        return table_name

    def init_sheet(self, name, table):
        """
        Initialize a sheet, setting its headers and unique name.

        In this context, the sheet might be either a CSV file or a sheet in an Excel workbook.

        :param name: Table name
        :param table: Table object
        """
        options = self.options.selection[name]
        self.headers[name] = self.get_headers(table, options)
        self.names[name] = self._name_check(options.name or name)
        return self.names[name], self.headers[name]

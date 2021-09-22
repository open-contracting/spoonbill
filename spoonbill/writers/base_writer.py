from collections import defaultdict

from spoonbill.utils import SchemaHeaderExtractor


class BaseWriter:
    """
    Base writer class
    """

    def __init__(self, workdir, tables, options, schema):
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
        self.schema_headers = SchemaHeaderExtractor(self.schema)

    def get_headers(self, table, options):
        """
        Return a table's headers, respecting the human and override options.

        :param table: A table object
        :param options: Flattening options
        :return: Mapping between the machine-readable headers and the output headers
        """
        split = options.split and (table.rolled_up or table.splitted)
        # split = options.split and table.splitted
        if table.parent != "" and table.child_tables:
            split = True
        headers = {c: c for c in table.available_rows(split=split)}
        if (
            table.parent != ""
            and table.parent.name in self.options.selection  # noqa: W503
            and self.options.selection[table.parent.name].pretty_headers  # noqa:W503
        ):
            self.options.selection[table.name].pretty_headers = True
        if options.pretty_headers:
            for c in headers:
                headers[c] = table.titles.get(c, c)
                for k, v in headers.items():
                    headers[k] = self.schema_headers.get_header(k, v)
            for col in headers.keys():
                for char in col:
                    if char.isnumeric() and char != "0":
                        title_col = col.replace(char, "0")
                        headers[col] = headers[title_col]

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

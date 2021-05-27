from collections import defaultdict


class BaseWriter:
    def __init__(self, workdir, tables, options):
        """Base writer class
        :param workdir: Working directory
        :param tables: Tables data
        :options: Flattening options
        """
        self.workdir = workdir
        self.tables = tables
        self.options = options
        self.names = {}
        self.headers = {}
        self.names_counter = defaultdict(int)

    def get_headers(self, table, options):
        """Generate table headers respecting human and override options

        :param table: Target table
        :param options: Flattening options
        :return: Mapping between column and its header
        """
        # split = options.split and (table.roll_up or table.should_split)
        split = options.split and table.should_split
        headers = {c: c for c in table.available_rows(split=split)}
        if options.pretty_headers:
            for c in headers:
                headers[c] = table.titles.get(c, c)
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
        """Initialize sheet in writer

        Sheet in this context might be either csv file or sheet inside xlsx workbook

        :param name: Table name
        :param table: Table object
        """
        options = self.options.selection[name]
        self.headers[name] = self.get_headers(table, options)
        self.names[name] = self._name_check(options.name or name)
        return self.names[name], self.headers[name]

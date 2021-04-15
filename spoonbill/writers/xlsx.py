import collections

import xlsxwriter


class XlsxWriter:
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
        for name, table in self.tables.items():
            # if spec[name]['total_rows'] == 0:
            # continue
            split = self.options.selection[name].split
            sheet = self.workbook.add_worksheet(name)
            headers = table.available_rows(split=split)
            for col_index, col_name in enumerate(headers):
                self.col_index[name][col_name] = col_index
                sheet.write(0, col_index, col_name)
            self.row_counters[name] = 1

    def writerow(self, table, row):
        """Write row to output file"""
        sheet = self.workbook.get_worksheet_by_name(table)

        for column, value in row.items():
            col_index = self.col_index[table][column]
            sheet.write(self.row_counters[table], col_index, value)
        self.row_counters[table] += 1

    def close(self):
        """Finish work"""
        self.workbook.close()
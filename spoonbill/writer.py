import xlsxwriter
import csv
import pathlib
import collections


class CSVWriter:
    def __init__(self, spec, workdir):
        self.spec = spec
        self.sheets = {}
        self.fds = []
        for name in spec.tables:
            if spec[name]['total_rows'] == 0:
                continue
            headers = [k for k, c in spec[name]['data'].items() if c > 0]
                
            sheet_path = pathlib.Path(workdir) / f'{name}.csv'
            fd = open(sheet_path, 'w')
            writer = csv.DictWriter(fd, headers)
            self.fds.append(fd)
            writer.writeheader()
            self.sheets[name] = writer

    def writerow(self, table, row):
        self.sheets[table].writerow(row)

    def close(self):
        for fd in self.fds:
            fd.close()


class XlsxWriter:
    def __init__(self, spec, workdir):
        path = workdir / 'result.xlsx'
        self.workbook = xlsxwriter.Workbook(path, {'constant_memory': True})
        self.counters = {}
        self.headers = collections.defaultdict(dict)
        for name in spec.tables:
            if spec[name]['total_rows'] == 0:
                continue
            sheet = self.workbook.add_worksheet(name)
            headers = [k for k, c in spec[name]['data'].items() if c > 0]
            for col_index, col_name in enumerate(headers):
                self.headers[name][col_name] = col_index
                sheet.write(0, col_index, col_name)
            self.counters[name] = 1

    def writerow(self, table, row):
        sheet = self.workbook.get_worksheet_by_name(table)
        headers = self.headers[table]
        curr_row = self.counters[table]
        for column, value in row.items():
            col_index = headers[column]
            sheet.write(curr_row, col_index, value)
        self.counters[table] += 1

    def close(self):
        self.workbook.close()

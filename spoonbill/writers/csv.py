import csv


class CSVWriter:

    def __init__(self, workdir, tables, options):
        self.workdir = workdir
        self.writers = {}
        self.fds = []
        self.tables = tables
        self.options = options
        for name, table in tables.items():
            # if table.total_rows == 0:
            # LOGGER.info("Skipping table %s as empty")
            # continue
            split = options.selection[name].split
            fd = open(workdir / f"{name}.csv", "w")
            writer = csv.DictWriter(fd, table.available_rows(split=split))
            self.fds.append(fd)
            self.writers[name] = writer

    def writeheaders(self):
        """Write headers to output file"""
        for w in self.writers.values():
            w.writeheader()

    def writerow(self, table, row):
        """Write row to output file"""
        self.writers[table].writerow(row)

    def close(self):
        """Finish work"""
        for fd in self.fds:
            fd.close()
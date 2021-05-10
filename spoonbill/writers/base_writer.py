from collections import defaultdict


class BaseWriter:
    def name_check(self, table_name):
        self.names_counter[table_name] += 1
        if self.names_counter[table_name] > 1:
            table_name += str(self.names_counter[table_name] - 1)
        return table_name

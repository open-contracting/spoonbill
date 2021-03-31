import pathlib
import json
from collections import deque, defaultdict
from dataclasses import asdict
from spoonbill.spec import TablesDefinition
from spoonbill.utils import iter_file


_TABLE_THRESHOLD = 5
_PREVIEW_ROWS = 20


class DataPreprocessor:
    ''''''
    def __init__(self, schema, root):
        ''''''
        self.schema = schema
        self.spec = TablesDefinition.from_schema(self.schema, root)
        self.root = root

    def process_file(self, filename, with_preview=True):
        ''''''
        root = self.spec.root_table
        preview_counts = defaultdict(int)

        for item in iter_file(filename, root):
            rows = deque([('', root, item)])
            preview_rows = defaultdict(dict)
            scopes = deque()
            while rows:
                path, table_name, record = rows.pop()
                table = self.spec.factory(table_name)
                if not path or path == table_name:
                    table.inc()
        
                for key, item in record.items():
                    if isinstance(item, dict):
                        rows.append((f'{path}/{key}', table_name, item))
                    elif isinstance(item, list):
                        for index, value in enumerate(item):
                            if isinstance(value, (dict, list)):
                                rows.append((key, key, value))
                            else:
                                header = f'{path}/{key}/{index}'
                                if with_preview and preview_counts[table_name] < _PREVIEW_ROWS:
                                    preview_rows[table_name][header] = value
                                table.add_column(header)
                    else:
                        header = f'{path}/{key}'
                        if with_preview and preview_counts[table_name] < _PREVIEW_ROWS:
                            preview_rows[table_name][header] = item
                        table.add_column(header)
            for name, row in preview_rows.items():
                self.spec[name].preview_rows.append(row)
                preview_counts[table_name] += 1
        return self.spec

    def save_to_file(self, filename):
        with open(filename, 'w') as fd:
            json.dump(asdict(self.spec), fd)



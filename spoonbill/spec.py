from collections import deque, defaultdict
from dataclasses import dataclass, field

import codecs
import json
import jsonref


@dataclass
class Table:
    name: str
    data: dict[str, int] = field(default_factory=dict)
    total_rows: int = 0
    arrays: dict[str, int]  = field(default_factory=dict)
    titles: dict[str, str]  = field(default_factory=dict)
    preview_rows: list[dict] = field(default_factory=list)

    def add_array(self, path):
        self.arrays[path] = 0

    def add_column(self, header, title=''):
        self.data[header] = 0
        self.titles[header] = title

    def inc_column(self, header):
        self.data[header] += 1

    def inc_array(self, header):
        self.array[header] += 1

    def inc(self):
        self.total_rows += 1



@dataclass    
class TablesDefinition:
    root_table: str
    tables: dict[Table] = field(default_factory=dict)
    # schema_dict: dict = field(default_factory=dict)

    def __getitem__(self, table):
        ''''''
        return self.tables[table]

    def factory(self, name):
        if name not in self.tables:
            self.tables[name] = Table(name)
        return self[name]

    @classmethod
    def from_schema(cls, schema, root):
        ''''''
        schema_dict = jsonref.JsonRef.replace_refs(schema)
        tables = cls(root_table=root)
        properties = deque([('', tables.root_table, schema_dict)])
        while properties:
            path, table_name, prop = properties.pop()
            table = tables.factory(table_name)
            for key, item in prop['properties'].items():
                type_ = 'type' in item and item['type']
                d_key = f'{path}/{key}'
                if type_ == 'array':
                    d_type_  = item['items']['type']
                    if d_type_ in ('array', 'object'):
                        table.add_array(d_key)
                        items = item['items']
                        properties.append((key, key, items))
                    else:
                        table.add_column(d_key, item.get('title'))
                elif type_ == 'object':
                    properties.append((d_key, table_name, item))
                else:
                    table.add_column(d_key, item.get('title'))
        return tables

    @classmethod
    def from_file(cls, filename):
        with codecs.open(filename) as fd:
            data = json.load(fd)
        return cls(**data)

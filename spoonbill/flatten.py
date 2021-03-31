from dataclasses import dataclass
from collections import defaultdict, deque
from collections.abc import Iterable

from spoonbill.spec import TablesDefinition
from spoonbill.stats import DataPreprocessor
from spoonbill.utils import iter_file
from spoonbill.writer import XlsxWriter, CSVWriter

import codecs
import json
import pathlib


@dataclass
class FlattenOptions:
    selection: list[str]
    workdir: str
    root: str


@dataclass
class Flattener:
    ''''''
    tables: TablesDefinition
    records: Iterable[dict]

    def __iter__(self):
        root = self.tables.root_table

        for item in self.records:
            scopes = deque()
            contiainers = []
            rows = {root: [defaultdict(str)]}

            to_parse = deque([('', root, item)])

            while to_parse:
                path, table_name, record = to_parse.pop()
                table = self.tables.factory(table_name)
        
                for key, item in record.items():
                    if isinstance(item, dict):
                        rows[table_name] = [defaultdict(str)]
                        to_parse.append((f'{path}/{key}', table_name, item))
                    elif isinstance(item, list):
                        for index, value in enumerate(item):
                            if isinstance(value, (dict, list)):
                                if key not in rows:
                                    rows[key] = []
                                rows[key].append(defaultdict(str))
                                to_parse.append((key, key, value))
                            else:
                                header = f'{path}/{key}/{index}'
                                rows[table_name][-1][header] = value
                    else:
                        header = f'{path}/{key}'
                        rows[table_name][-1][header] = item
            yield rows



class SpoonbillTool:

    def __init__(self, options, schema=None, datafile=None,):
        ''''''
        self.options = options
        self.workdir = pathlib.Path(options.workdir)
        self.root = options.root
        if datafile:
            path = self.workdir / datafile
            self.spec = TablesDefinition.from_file(path)
        elif schema:
            path = self.workdir / schema
            with codecs.open(path) as fd:
                schema = json.load(fd)
                self.dp = DataPreprocessor(schema, options.root)
                self.spec = self.dp.spec
        else:
            raise Exception("No source for tables provided")

    def analyze_file(self, filename, with_preview=True):
        full_path = self.workdir / filename
        out_path = f'{full_path}.analyzed.json'
        self.dp.process_file(full_path, with_preview)
        self.dp.save_to_file(out_path)

    def writerow(self, table, row):
        ''''''
        for wr in self.writers:
            wr.writerow(table, row)

    def close(self):
        for wr in self.writers:
            wr.close() 

    def flatten_file(self, filename):
        self.writers = (
            CSVWriter(self.spec, self.workdir),
            XlsxWriter(self.spec, self.workdir),            
        )
        full_path = self.workdir / filename
        flattener = Flattener(self.spec, iter_file(full_path, self.root))
        for data in flattener:
            for table, rows in data.items():
                for row in rows:
                    self.writerow(table, row)
        self.close()
            # for table, row in :
                
        

if __name__ == '__main__':
    from pprint import pprint
    options = FlattenOptions(['releases', 'parties'], '.', 'releases')
    dt = SpoonbillTool(options, 'schema.json')
    dt.analyze_file('ocds-213czf-000-00001.json')
    dt = SpoonbillTool(options, datafile='ocds-213czf-000-00001.json.analyzed.json')
    dt.flatten_file('ocds-213czf-000-00001.json')

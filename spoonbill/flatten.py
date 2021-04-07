from dataclasses import dataclass, is_dataclass, field
from collections.abc import Mapping, Sequence
from collections import defaultdict, deque
from spoonbill.spec import Table
from spoonbill.stats import DataPreprocessor
from spoonbill.utils import iter_file
from spoonbill.writer import XlsxWriter, CSVWriter
from pathlib import Path
from typing import Set

import json
import logging

LOGGER = logging.getLogger('spoonbill')

# we can try to infer tables from  schema
# but it may require some heuristics or handling exceptional cases
# like "tenders" which is not array and called "tender"
# so this way seems like middle ground between flexibility and simlpicity
ROOT_TABLES = {
    'tenders': ['/tender'],
    'awards': ['/awards'],
    'contracts': ['/contracts'],
    'planning': ['/planning'],
    'parties': ['/parties']
}
COMBINED_TABLES = {
    'documents': [
        '/planning/documents',
        '/tender/documents',
        '/awards/documents',
        '/contracts/documents',
    ],
    'milestones': [
        '/planning/milestones',
        '/tender/milestones',
        '/contracts/milestones',
        '/contracts/implementation/milestones'
    ],
    'amendments': [
        "/planning/milestones",
        "/tender/milestones",
        "/contracts/milestones",
        "/contracts/implementation/milestones"
    ]
}


@dataclass
class TableFlattenConfig:
    split: bool


@dataclass
class FlattenOptions:
    selection: Mapping[str, TableFlattenConfig]
    pretty_headers: bool = False
    separator: bool = '/'

    # combine: bool = True

    def __post_init__(self):
        for name, table in self.selection.items():
            if not is_dataclass(table):
                self.selection[name] = TableFlattenConfig(**table)


@dataclass
class Flattener:
    ''''''
    options: FlattenOptions
    tables: Mapping[str, Table]

    _lookup_cache: Mapping[str, Table] = field(default_factory=dict, init=False)
    _types_cache: Mapping[str, Sequence[str]] = field(default_factory=dict, init=False)
    _path_cache: Mapping[str, Table] = field(default_factлory=dict, init=False)
    _propagate_cols: Set[str] = field(default_factory=set, init=False)

    def __post_init__(self):
        self.options = FlattenOptions(**self.options)
        tables = {}
        for name, table in self.tables.items():
            if name not in self.options.selection:
                continue

            split = self.options.selection[name].split
            for p in table.path:
                self._path_cache[p] = table
            for path in table.types:
                self._types_cache[path] = table
            cols = table if split else table.combined_columns
            for path in cols:
                if path not in table.propagated_columns:
                    self._lookup_cache[path] = table
            for col in table.propagated_columns:
                self._propagate_cols.add(col)

            if split:
                for c_name in table.child_tables:
                    data = self.tables[c_name]
                    data.pop('preview_rows', '')
                    data.pop('preview_rows_combined', '')
                    c_table = Table(**data)
                    tables[c_name] = c_table
                    self.options.selection[c_name] = TableFlattenConfig(split=True)
                    for p in c_table.path:
                        self._path_cache[p] = c_table
                    for path in c_table.types:
                        self._types_cache[path] = c_table
                    for col in c_table.propagated_columns:
                        self._propagate_cols.add(col)
        if tables:
            self.tables = tables

    def flatten(self, records):

        for item in records:
            rows = defaultdict(list)
            to_flatten = deque([('', '', {}, item, {})])
            separator = self.options.separator

            while to_flatten:
                abs_path, path, parent, record, propagate = to_flatten.pop()
                # Strict match /tender /parties etc., so this is a new row
                if table := self._path_cache.get(path):
                    rows[table.name].append({})

                for key, item in record.items():
                    pointer = separator.join((path, key))
                    if pointer in self._propagate_cols:
                        propagate[pointer] = item
                    table = self._lookup_cache.get(pointer)
                    if not table:
                        table = self._types_cache.get(pointer)
                    if not table:
                        continue

                    if isinstance(item, dict):
                        a_p = separator.join((abs_path, key))
                        to_flatten.append((a_p, pointer, record, item, propagate))
                    elif isinstance(item, list):
                        for index, value in enumerate(item):
                            if isinstance(value, dict):
                                if table.is_root:
                                    a_p = separator.join((abs_path, key))
                                else:
                                    a_p = separator.join((abs_path, key, str(index)))
                                to_flatten.append((a_p, pointer, record, value, propagate))
                            else:
                                if self.options.selection[table.name].split:
                                    a_p = separator.join((abs_path, key))
                                else:
                                    a_p = separator.join((abs_path, key, str(index)))
                                if not table.is_root:
                                    rows[table.name].append({})
                                rows[table.name][-1][a_p] = value
                    else:
                        a_pointer = separator.join((abs_path, key))
                        if a_pointer in self._lookup_cache:
                            rows[table.name][-1][a_pointer] = item
                        else:
                            rows[table.name][-1][pointer] = item
            if propagate:
                for data in rows.values():
                    for row in data:
                        row.update(propagate)
            yield rows


class FileAnalyzer:

    def __init__(self,
                 workdir,
                 schema,
                 root_tables=ROOT_TABLES,
                 combined_tables=COMBINED_TABLES,
                 propagate_cols=['/ocid'],
                 root_key='releases',
                 preview=True
                 ):
        self.workdir = Path(workdir)
        self.spec = DataPreprocessor(
            json.load(schema),
            root_tables,
            combined_tables=combined_tables,
            propagate_cols=propagate_cols,
            preview=preview
        )
        self.root_key = root_key

        def analyze_file(self, filename):
            path = self.workdir / filename
            self.spec.process_items(
                iter_file(path, self.root_key)
            )

        def dump_to_file(self, filename):
            path = self.workdir / filename
            with open(path, 'w') as fd:
                json.dump(self.spec.dump(), fd, default=str)


class FileFlattener:

    def __init__(self,
                 workdir,
                 options,
                 tables,
                 root_key='releases',
                 csv=True,
                 xlsx=True):
        self.flattener = Flattener(options, tables)
        self.workdir = Path(workdir)
        self.root_key = root_key
        self.writers = []

        if csv:
            self.writers.append(CSVWriter(self.workdir, self.flattener.tables, self.flattener.options))
        if xlsx:
            self.writers.append(XlsxWriter(self.workdir, self.flattener.tables, self.flattener.options))

    def writerow(self, table, row):
        ''''''
        for wr in self.writers:
            wr.writerow(table, row)

    def close(self):
        for wr in self.writers:
            wr.close()

    def flatten_file(self, filename):
        path = self.workdir / filename
        for w in self.writers:
            w.writeheaders()

        for data in self.flattener.flatten(iter_file(path, self.root_key)):
            try:
                for table, rows in data.items():
                    for row in rows:
                        self.writerow(table, row)
            except Exception as err:
                LOGGER.warning(f"Failed to write row {row}")
        self.close()
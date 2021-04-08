from dataclasses import dataclass, is_dataclass, field
from collections.abc import Mapping, Sequence
from collections import defaultdict, deque
from pathlib import Path

import json
import logging

from spoonbill.spec import Table
from spoonbill.stats import DataPreprocessor
from spoonbill.utils import iter_file, generate_row_id
from spoonbill.writer import XlsxWriter, CSVWriter
from spoonbill.common import ROOT_TABLES, COMBINED_TABLES

LOGGER = logging.getLogger('spoonbill')


@dataclass
class TableFlattenConfig:
    split: bool


@dataclass
class FlattenOptions:
    selection: Mapping[str, TableFlattenConfig]
    pretty_headers: bool = False
    separator: str = '/'

    # combine: bool = True

    def __post_init__(self):
        for name, table in self.selection.items():
            if not is_dataclass(table):
                self.selection[name] = TableFlattenConfig(**table)


@dataclass
class Flattener:
    options: FlattenOptions
    tables: Mapping[str, Table]

    _lookup_cache: Mapping[str, Table] = field(default_factory=dict, init=False)
    _types_cache: Mapping[str, Sequence[str]] = field(default_factory=dict, init=False)
    _path_cache: Mapping[str, Table] = field(default_factory=dict, init=False)

    def __post_init__(self):
        if not is_dataclass(self.options):
            self.options = FlattenOptions(**self.options)
        tables = {}
        for name, table in self.tables.items():
            if name not in self.options.selection:
                continue
            for p in table.path:
                self._path_cache[p] = table
            for path in table.types:
                self._types_cache[path] = table

            split = self.options.selection[name].split
            cols = table if split else table.combined_columns
            for path in cols:
                self._lookup_cache[path] = table

            if split:
                for c_name in table.child_tables:
                    c_table = self.tables[c_name]
                    tables[c_name] = c_table
                    self.options.selection[c_name] = TableFlattenConfig(split=True)
                    for p in c_table.path:
                        self._path_cache[p] = c_table
                    for path in c_table.types:
                        self._types_cache[path] = c_table
        if tables:
            self.tables = tables

    def flatten(self, releases):

        for release in releases:
            rows = defaultdict(list)
            to_flatten = deque([('', '', '', {}, release)])
            separator = self.options.separator
            ocid = release['ocid']
            top_level_id = release['id']

            while to_flatten:
                abs_path, path, parent_key, parent, record = to_flatten.pop()
                # Strict match /tender /parties etc., so this is a new row
                if table := self._path_cache.get(path):
                    row_id = generate_row_id(ocid,
                                             record.get('id', ''),
                                             parent_key,
                                             top_level_id)
                    rows[table.name].append({
                        'rowID': row_id,
                        'id': top_level_id,
                        'parentID': parent.get('id'),
                        'ocid': ocid
                    })

                for key, item in record.items():
                    pointer = separator.join((path, key))
                    table = self._lookup_cache.get(pointer)
                    if not table:
                        table = self._types_cache.get(pointer)
                    if not table:
                        continue

                    if isinstance(item, dict):
                        a_p = separator.join((abs_path, key))
                        to_flatten.append((a_p, pointer, key, record, item))
                    elif isinstance(item, list):
                        for index, value in enumerate(item):
                            if isinstance(value, dict):
                                if table.is_root:
                                    a_p = separator.join((abs_path, key))
                                else:
                                    a_p = separator.join((abs_path, key, str(index)))
                                to_flatten.append((a_p, pointer, key, record, value))
                            else:
                                if self.options.selection[table.name].split:
                                    a_p = separator.join((abs_path, key))
                                else:
                                    a_p = separator.join((abs_path, key, str(index)))
                                if not table.is_root:
                                    rows[table.name].append({
                                        'rowID': row_id,
                                        'id': top_level_id,
                                        'parentID': parent.get('id'),
                                        'ocid': ocid
                                    })
                                rows[table.name][-1][a_p] = value
                    else:
                        a_pointer = separator.join((abs_path, key))
                        if a_pointer in self._lookup_cache:
                            rows[table.name][-1][a_pointer] = item
                        else:
                            rows[table.name][-1][pointer] = item
            yield rows


class FileAnalyzer:

    def __init__(self,
                 workdir,
                 schema,
                 root_tables=ROOT_TABLES,
                 combined_tables=COMBINED_TABLES,
                 root_key='releases',
                 preview=True
                 ):
        self.workdir = Path(workdir)
        self.spec = DataPreprocessor(
            json.load(schema),
            root_tables,
            combined_tables=combined_tables,
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

import pathlib
import json
from collections import deque, defaultdict
from dataclasses import asdict
from spoonbill.spec import Table, Column
from spoonbill.utils import iter_file


from collections import deque, defaultdict, OrderedDict
from itertools import chain
from os.path import commonpath
from dataclasses import dataclass, field, asdict, replace
from spoonbill.utils import extract_type,\
    iter_file, validate_type, get_root, combine_path, prepare_title,\
    get_maching_tables

import codecs
import json
import jsonref
import logging


PREVIEW_ROWS = 20
LOGGER = logging.getLogger('spoonbill')


@dataclass    
class DataPreprocessor:
    schema_dict: dict
    root_tables: dict[str, list]
    combined_tables: dict[str, list] = field(default_factory=dict)
    populate_cols: list[str] = field(default_factory=list)

    # better to keep '/' to be more like jsonpointers
    header_separator: str = '/'
    preview: bool = True

    tables: dict[str, Table] = field(default_factory=dict, init=False)
    _lookup_cache: dict[str, Table] = field(default_factory=dict, init=False)
    _table_by_path: dict[str, Table] = field(default_factory=dict, init=False)
    types: dict[str, str] = field(default_factory=dict, init=False)

    def __getitem__(self, table):
        return self.tables[table]

    def _init_tables(self, tables, is_root=False, is_combined=False, parent=''):
        for name, path in tables.items():
            table = Table(name,
                          path,
                          is_root=is_root,
                          is_combined=is_combined,
                          parent=parent)
            self.tables[name] = table
            for p in path:
                self._table_by_path[p] = table

    def __post_init__(self):
        if isinstance(self.schema_dict, str):
            if self.schema_dict.startswith('http'):
                import requests
                self.schema_dict = requests.get(self.schema_dict).json()
            else:
                with open(self.schema_dict) as fd:
                    self.schema_dict = json.load(fd)
            
        self.schema_dict = jsonref.JsonRef.replace_refs(self.schema_dict)
        self._init_tables(self.root_tables, is_root=True)
        if self.combined_tables:
            self._init_tables(self.combined_tables, is_combined=True, is_root=True)            

        separator = self.header_separator
        todo = deque([('', ('', {}), self.schema_dict, [])])
        while todo:
            path, (parent_key, parent), prop, populate_cols = todo.pop()
            if prop.get('deprecated'):
                continue
            # TODO: handle oneOf anyOf allOf
            if properties := prop.get('properties', {}):
                for key, item in properties.items():
                    if item.get('deprecated'):
                        continue
                    if hasattr(item, '__reference__') and item.__reference__.get('deprecated'):
                        continue

                    type_ = extract_type(item)
                    curr_path = separator.join([path, key])
                    self.curr_table = self.get_table(curr_path)
                    
                    if curr_path in self.populate_cols:
                        populate_cols.append((curr_path, item))
                        for table in self.tables.values():
                            table.add_column(
                                curr_path,
                                item,
                                type_,
                                parent=prop
                            )
                            table.path.append(curr_path)
                    if not self.curr_table:
                        continue

                    self.types[curr_path] = type_
                    if 'object' in type_:
                        todo.append((curr_path, (key, properties), item, populate_cols))
                    elif 'array' in type_:
                        if curr_path not in self.curr_table.path:
                            if self.curr_table.name.endswith(parent_key):
                                table_name = f'{self.curr_table.name}_{key}'
                            else:
                                table_name = f'{self.curr_table.name}_{parent_key}_{key}'
                            child_table = Table(table_name, [curr_path], parent=self.curr_table)
                            if populate_cols:
                                for c_path, c_item in populate_cols:
                                    child_table.add_column(
                                        c_path,
                                        c_item,
                                        extract_type(c_item),
                                        parent={'title': ''}
                                    )
                            self.curr_table.child_tables.append(table_name)
                            self.tables[table_name] = child_table
                            self._lookup_cache = dict()
                            get_root(self.curr_table).arrays[curr_path] = 0
                            self.curr_table = child_table
                        items = item['items']
                        item_type = extract_type(items)
                        if set(item_type) & set(('array', 'object')):
                            todo.append((curr_path, (key, properties), items, populate_cols))
                        else:
                            self.curr_table.add_column(
                                curr_path,
                                item,
                                type_,
                                parent=prop
                            )
                    else:
                        self.curr_table.add_column(
                            curr_path,
                            item,
                            type_,
                            parent=prop
                        )
            else:
                # TODO: not sure what to do here
                continue

    def get_table(self, path):
        if path in self._lookup_cache:
            return self._lookup_cache[path]
        candidates = get_maching_tables(self.tables, path)
        if not candidates:
            return
        table = candidates[0] 
        self._lookup_cache[path] = table
        return table

    def add_preview_row(self, default=None):
        self.curr_table.preview_rows.append({})
        if self.curr_table.is_root:
            default = default or {}
            self.curr_table.preview_rows_combined.append({**default})

    def process_items(self, items, with_preview=True):
        separator = self.header_separator

        for count, item in enumerate(items):

            todo = deque([('', '', {}, item)])
            populate_cols = defaultdict(dict)
            scopes = deque()
            while todo:
                abs_path, path, parent, record = todo.pop()
                if table := self._table_by_path.get(path):
                    table.inc()
                    for col_name, col_val in populate_cols.items():
                        table.inc_column(col_name)
                for key, item in record.items():
                    curr_path = separator.join([path, key])
                    self.curr_table = self.get_table(curr_path)
                    if not self.curr_table:
                        continue
                    type_ = self.types.get(curr_path)

                    if curr_path not in self.populate_cols\
                       and curr_path in self.curr_table.path:
                        if count < PREVIEW_ROWS:
                            self.add_preview_row(populate_cols)
                    if type_ and not validate_type(type_, item):
                        LOGGER.debug(
                            f'Mismatched type on {curr_path} expected {type_}'
                        )
                        continue
                    if isinstance(item, dict):
                        todo.append((separator.join([abs_path, key]),
                                     curr_path,
                                     record,
                                     item))
                    elif isinstance(item, list):
                        if self.curr_table.is_root:
                            a_path = separator.join([abs_path, key])
                            for value in item:
                                todo.append((
                                    a_path,
                                    curr_path,
                                    record,
                                    value,
                                ))
                        else:
                            root = get_root(self.curr_table)
                            prev_len = root.arrays[curr_path]
                            if root.set_array(curr_path, item):
                                new_cols = []
                                for col_i, _ in enumerate(item, prev_len):
                                    prev_col_p = separator.join((abs_path, key, str(col_i)))
                                    new_col_p = separator.join((abs_path, key, str(col_i + 1)))
                                    for col_p, col in root.combined_columns.items():
                                        if commonpath((col_p, prev_col_p)) == prev_col_p:
                                            new_id = col.id.replace(prev_col_p, new_col_p)
                                            new_col = replace(col, id=new_id)
                                            new_cols.append(new_col)
                                for col in new_cols:
                                    root.combined_columns[col.id] = col
                            for i, value in enumerate(item):
                                if isinstance(value, (list, dict)):
                                    p = separator.join([abs_path, key, str(i)])
                                    todo.append((
                                        p,
                                        curr_path,
                                        record,
                                        value,
                                    ))

                                else:
                                    p = separator.join((curr_path, str(i)))
                                    if self.preview and count < PREVIEW_ROWS:
                                        self.curr_table.preview_rows[-1][curr_path] = value
                                        p = separator.join((curr_path, str(i)))
                                        root.preview_rows_combined[-1][p] = value
                    else:
                        if curr_path in self.populate_cols:
                            populate_cols[curr_path] = item
                            continue
                        root = get_root(self.curr_table)
                        if curr_path not in self.curr_table.columns:
                            self.curr_table.add_column(
                                curr_path,
                                {'title': key},
                                'na',
                                parent=record,
                                additional=True
                            )

                        self.curr_table.inc_column(curr_path)
                        if self.preview and count < PREVIEW_ROWS:
                            table = self.curr_table
                            if not self.curr_table.is_root:
                                table = get_root(self.curr_table)
                            p = separator.join((abs_path, key))
                            table.preview_rows_combined[-1][p] = item
                            self.curr_table.preview_rows[-1][curr_path] = item

    def dump(self):
        return {
            'tables': {name: asdict(table) for name, table in self.tables.items()}
        }



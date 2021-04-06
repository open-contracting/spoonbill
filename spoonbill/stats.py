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
    propagate_cols: list[str] = field(default_factory=list)

    # better to keep '/' to be more like jsonpointers
    header_separator: str = '/'
    preview: bool = True

    tables: dict[str, Table] = field(default_factory=dict, init=False)
    _lookup_cache: dict[str, Table] = field(default_factory=dict, init=False)
    _table_by_path: dict[str, Table] = field(default_factory=dict, init=False)

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
        to_analyze = deque([('', ('', {}), self.schema_dict, [])])
        while to_analyze:
            path, (parent_key, parent), prop, propagate_cols = to_analyze.pop()
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
                    pointer = separator.join([path, key])
                    self.curr_table = self.get_table(pointer)
                    
                    if pointer in self.propagate_cols:
                        propagate_cols.append((pointer, item))
                        for table in self.tables.values():
                            table.add_column(
                                pointer,
                                item,
                                type_,
                                parent={},
                                propagated=True
                            )
                            # table.path.append(pointer)
                    if not self.curr_table:
                        continue

                    self.curr_table.types[pointer] = type_
                    if 'object' in type_:
                        to_analyze.append((pointer, (key, properties), item, propagate_cols))
                    elif 'array' in type_:
                        if pointer not in self.curr_table.path:
                            if self.curr_table.name.endswith(parent_key):
                                table_name = f'{self.curr_table.name}_{key[:5]}'
                            else:
                                table_name = f'{self.curr_table.name}_{parent_key[:5]}_{key[:5]}'

                            child_table = Table(table_name, [pointer], parent=self.curr_table)
                            if propagate_cols:
                                for c_path, c_item in propagate_cols:
                                    child_table.add_column(
                                        c_path,
                                        c_item,
                                        extract_type(c_item),
                                        parent={'title': ''},
                                        propagated=True
                                    )
                            self.curr_table.child_tables.append(table_name)
                            self.tables[table_name] = child_table
                            self._lookup_cache = dict()
                            get_root(self.curr_table).arrays[pointer] = 0
                            self.curr_table = child_table
                        items = item['items']
                        item_type = extract_type(items)
                        if set(item_type) & set(('array', 'object')):
                            to_analyze.append((pointer, (key, properties), items, propagate_cols))
                        else:
                            self.curr_table.add_column(
                                pointer,
                                item,
                                type_,
                                parent=prop
                            )
                    else:
                        self.curr_table.add_column(
                            pointer,
                            item,
                            type_,
                            parent=prop
                        )
            else:
                # TO_ANALYZE: not sure what to do here
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

            to_analyze = deque([('', '', {}, item)])
            propagate_cols = defaultdict(dict)
            scopes = deque()
            while to_analyze:
                abs_path, path, parent, record = to_analyze.pop()
                if table := self._table_by_path.get(path):
                    table.inc()
                    for col_name, col_val in propagate_cols.items():
                        table.inc_column(col_name)
                for key, item in record.items():
                    pointer = separator.join([path, key])
                    self.curr_table = self.get_table(pointer)
                    if not self.curr_table:
                        continue
                    type_ = self.curr_table.types.get(pointer)

                    if pointer not in self.propagate_cols\
                       and pointer in self.curr_table.path:
                        if count < PREVIEW_ROWS:
                            self.add_preview_row(propagate_cols)
                    if type_ and not validate_type(type_, item):
                        LOGGER.debug(
                            f'Mismatched type on {pointer} expected {type_}'
                        )
                        continue
                    if isinstance(item, dict):
                        to_analyze.append((separator.join([abs_path, key]),
                                     pointer,
                                     record,
                                     item))
                    elif isinstance(item, list):
                        if self.curr_table.is_root:
                            a_path = separator.join([abs_path, key])
                            for value in item:
                                to_analyze.append((
                                    a_path,
                                    pointer,
                                    record,
                                    value,
                                ))
                        else:
                            root = get_root(self.curr_table)
                            prev_len = root.arrays[pointer]
                            if root.set_array(pointer, item):
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
                                    to_analyze.append((
                                        p,
                                        pointer,
                                        record,
                                        value,
                                    ))

                                else:
                                    p = separator.join((pointer, str(i)))
                                    if self.preview and count < PREVIEW_ROWS:
                                        self.curr_table.preview_rows[-1][pointer] = value
                                        p = separator.join((pointer, str(i)))
                                        root.preview_rows_combined[-1][p] = value
                    else:
                        if pointer in self.propagate_cols:
                            propagate_cols[pointer] = item
                            continue
                        root = get_root(self.curr_table)
                        if pointer not in self.curr_table.columns:
                            self.curr_table.add_column(
                                pointer,
                                {'title': key},
                                'na',
                                parent=record,
                                additional=True
                            )

                        self.curr_table.inc_column(pointer)
                        if self.preview and count < PREVIEW_ROWS:
                            table = self.curr_table
                            if not self.curr_table.is_root:
                                table = get_root(self.curr_table)
                            p = separator.join((abs_path, key))
                            table.preview_rows_combined[-1][p] = item
                            self.curr_table.preview_rows[-1][pointer] = item

    def dump(self):
        return {
            'tables': {name: asdict(table) for name, table in self.tables.items()}
        }



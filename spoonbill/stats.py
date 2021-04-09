import json
import logging
from typing import List, Mapping
from collections import deque
from dataclasses import dataclass, field, asdict

import jsonref

from spoonbill.spec import Table, Column, add_child_table
from spoonbill.common import DEFAULT_FIELDS, ARRAY, JOINABLE, JOINABLE_SEPARATOR
from spoonbill.utils import extract_type, \
    validate_type, get_root, get_matching_tables, generate_row_id, recalculate_headers

PREVIEW_ROWS = 20
LOGGER = logging.getLogger('spoonbill')


@dataclass
class DataPreprocessor:
    schema_dict: Mapping
    root_tables: Mapping[str, List]
    combined_tables: Mapping[str, List] = field(default_factory=dict)

    # better to keep '/' to be more like jsonpointers
    # TODO: do we need this to be configurable at all???
    header_separator: str = '/'
    tables: Mapping[str, Table] = field(default_factory=dict, init=False)
    current_table: Table = field(init=False)
    _lookup_cache: Mapping[str, Table] = field(default_factory=dict, init=False)
    _table_by_path: Mapping[str, Table] = field(default_factory=dict, init=False)

    def __getitem__(self, table):
        return self.tables[table]

    def init_tables(self, tables, is_combined=False):
        for name, path in tables.items():
            table = Table(name,
                          path,
                          is_root=True,
                          is_combined=is_combined,
                          parent='')
            for col in DEFAULT_FIELDS:
                column = Column(col, 'string', col)
                table.columns[col] = column
                table.combined_columns[col] = column
                table.titles[col] = col
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
        self.init_tables(self.root_tables)
        if self.combined_tables:
            self.init_tables(self.combined_tables, is_combined=True)
        separator = self.header_separator
        to_analyze = deque([('', '', {}, self.schema_dict)])

        while to_analyze:
            path, parent_key, parent, prop = to_analyze.pop()
            if prop.get('deprecated'):
                continue
            # TODO: handle oneOf anyOf allOf
            properties = prop.get('properties', {})
            if properties:
                for key, item in properties.items():
                    if item.get('deprecated'):
                        continue
                    if hasattr(item, '__reference__') and item.__reference__.get('deprecated'):
                        continue

                    type_ = extract_type(item)
                    pointer = separator.join([path, key])
                    self.current_table = self.get_table(pointer)
                    if not self.current_table:
                        continue

                    self.current_table.types[pointer] = type_
                    if 'object' in type_:
                        to_analyze.append((pointer, key, properties, item))
                    elif 'array' in type_:
                        items = item['items']
                        items_type = extract_type(items)
                        if set(items_type) & {'array', 'object'}:
                            if pointer not in self.current_table.path:
                                # found child array, need to create child table
                                child_table = add_child_table(self.current_table, pointer, parent_key, key)
                                self.tables[child_table.name] = child_table
                                self._lookup_cache = dict()
                                self.current_table = child_table
                            to_analyze.append((pointer, key, properties, items))
                        else:
                            # This means we in array of strings, so this becomes a single joinable column
                            type_ = ARRAY.format(items_type)
                            self.current_table.types[pointer] = JOINABLE
                            self.current_table.add_column(
                                pointer,
                                item,
                                type_,
                                parent=prop,
                                joinable=True
                            )
                    else:
                        if self.current_table.is_combined:
                            pointer = separator + separator.join((parent_key, key))
                        self.current_table.add_column(
                            pointer,
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
        candidates = get_matching_tables(self.tables, path)
        if not candidates:
            return
        table = candidates[0]
        self._lookup_cache[path] = table
        return table

    def add_preview_row(self, ocid, item_id, row_id, parent_id, parent_table=''):
        """Append empty row to previews

        Important to do because all preview items is set using -1 index to access current row
        :param ocid: Row ocid
        :param item_id: Current object id
        :param row_id: Unique row id
        :param parent_id: Parent object id
        :param parent_table: Parent table name
        """
        defaults = {'ocid': ocid, "rowID": row_id, 'parentID': parent_id, "id": item_id}
        if parent_table:
            defaults['parentTable'] = parent_table
        self.current_table.preview_rows.append(defaults)
        if self.current_table.is_root:
            self.current_table.preview_rows_combined.append(defaults)

    def process_items(self, releases, with_preview=True):
        """Analyze releases

        Iterate over every item in provided list to
        calculate metrics and optionally generate combined and split of flattened preview

        :param releases: Iterator of items to analyze
        :param with_preview: Generate previews if set to True
        """
        separator = self.header_separator
        for count, release in enumerate(releases):

            to_analyze = deque([('', '', '', {}, release)])
            ocid = release['ocid']
            top_level_id = release['id']

            while to_analyze:
                abs_path, path, parent_key, parent, record = to_analyze.pop()
                table = self._table_by_path.get(path)
                if table:
                    table.inc()
                    for col_name in DEFAULT_FIELDS:
                        table.inc_column(col_name)

                    # TODO: fields without ids??
                    row_id = generate_row_id(ocid,
                                             record.get('id', ''),
                                             parent_key,
                                             top_level_id)
                    self.current_table = table
                    if count < PREVIEW_ROWS:
                        self.add_preview_row(
                            ocid,
                            record.get('id'),
                            row_id,
                            parent.get('id'),
                            parent_key)
                for key, item in record.items():
                    pointer = separator.join([path, key])
                    self.current_table = self.get_table(pointer)
                    if not self.current_table:
                        continue
                    type_ = self.current_table.types.get(pointer)
                    # TODO: this validation should probably be smarter with arrays
                    if type_ and type_ != JOINABLE and not validate_type(type_, item):
                        LOGGER.debug(
                            f'Mismatched type on {pointer} expected {type_}'
                        )
                        continue

                    if isinstance(item, dict):
                        to_analyze.append((separator.join([abs_path, key]),
                                           pointer,
                                           key,
                                           record,
                                           item))
                    elif isinstance(item, list):
                        if type_ == JOINABLE:
                            if with_preview and count < PREVIEW_ROWS:
                                value = JOINABLE_SEPARATOR.join(item)
                                self.current_table.preview_rows[-1][pointer] = value
                        elif self.current_table.is_root:
                            a_path = separator.join([abs_path, key])
                            for value in item:
                                to_analyze.append((
                                    a_path,
                                    pointer,
                                    key,
                                    record,
                                    value,
                                ))
                        else:
                            root = get_root(self.current_table)
                            if root.set_array(pointer, item):
                                recalculate_headers(root, abs_path, key, item, separator)

                            for i, value in enumerate(item):
                                if isinstance(value,  dict):
                                    if count < PREVIEW_ROWS:
                                        if pointer in self.current_table.path:
                                            self.add_preview_row(
                                                ocid,
                                                value.get('id'),
                                                row_id,
                                                parent.get('id'),
                                                parent_key)
                                    p = separator.join([abs_path, key, str(i)])
                                    to_analyze.append((
                                        p,
                                        pointer,
                                        key,
                                        record,
                                        value,
                                    ))
                    else:
                        root = get_root(self.current_table)
                        abs_pointer = separator.join((abs_path, key))
                        if self.current_table.is_combined:
                            pointer = separator + separator.join((parent_key, key))
                            abs_pointer = pointer

                        if pointer not in self.current_table.columns:
                            self.current_table.add_column(
                                pointer,
                                {'title': key},
                                'na',
                                parent=record,
                                additional=True
                            )
                        self.current_table.inc_column(pointer)
                        root.inc_column(abs_pointer, combined=True)
                        if with_preview and count < PREVIEW_ROWS:
                            self.current_table.preview_rows[-1][pointer] = item
                            root.preview_rows_combined[-1][abs_pointer] = item

    def dump(self):
        """Dump table objects to python dictionary"""
        return {
            'tables': {name: asdict(table) for name, table in self.tables.items()}
        }

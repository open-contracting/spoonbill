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


LOGGER = logging.getLogger('spoonbill')


@dataclass
class Column:
    title: str
    type: str
    id: str
    hits: int = 0


@dataclass
class Table:
    name: str
    path: [str]
    total_rows: int = 0
    # parent is Table object but dataclasses don`t play well with recursion
    parent: object = field(default_factory=dict)
    is_root: bool = False
    is_combined: bool = False
    columns: OrderedDict[str, Column] = field(default_factory=OrderedDict)
    combined_columns: OrderedDict[str, Column] = field(default_factory=OrderedDict)
    additional_columns: OrderedDict[str, Column] = field(default_factory=OrderedDict)
    # max length not count
    arrays: dict[str, int]  = field(default_factory=dict)
    # for headers
    titles: dict[str, str]  = field(default_factory=dict)
    preview_rows: list[dict] = field(default_factory=list)
    preview_rows_combined: list[dict] = field(default_factory=list)

    child_tables: list[str] = field(default_factory=list, init=False)

    @property
    def missing_rows(self):
        return [
            header for header, count in self.columns.items()
            if count == 0
        ]

    def __iter__(self):
        for col in self.columns:
            yield col

    def __getitem__(self, path):
        ''''''
        return self.columns.get(path)

    def add_column(self,
                   path,
                   item,
                   type_,
                   parent,
                   combined_only=False,
                   additional=False):
        title = prepare_title(item, parent)
        column = Column(title, type_, path)
        root = get_root(self)
        combined_path = combine_path(root, path)
        self.combined_columns[combined_path] = Column(title, type_, combined_path)
        if not combined_only:
            self.columns[path] = column
        if not self.is_root:
            root_table = get_root(self)
            root_table.add_column(
                path,
                item,
                type_,
                parent=parent,
                combined_only=True
            )
        if additional:
            self.additional_columns[path] = column            

    def inc_column(self, header):
        self.columns[header].hits += 1
        if header in self.additional_columns:
            self.additional_columns[header].hits += 1

    def set_array(self, header, item):
        count = self.arrays[header] or 0
        length = len(item)
        if length > count:
            self.arrays[header] = length
            return True
        return False

    def inc(self):
        self.total_rows += 1


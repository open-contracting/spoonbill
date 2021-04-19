import logging
from collections import OrderedDict
from typing import Mapping, Sequence, List
from dataclasses import dataclass, field, is_dataclass, asdict

from spoonbill.utils import get_root, combine_path, prepare_title, generate_table_name
from spoonbill.common import DEFAULT_FIELDS

LOGGER = logging.getLogger("spoonbill")


@dataclass
class Column:
    """Column class is a data container to store column information
    :param title: Column human friendly title
    :param type: Column expected type
    :param id: Column path
    :param hits: Count number of times column is set during analysis
    """

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
    columns: Mapping[str, Column] = field(default_factory=OrderedDict)
    combined_columns: Mapping[str, Column] = field(default_factory=OrderedDict)
    propagated_columns: Mapping[str, Column] = field(default_factory=OrderedDict)
    additional_columns: Mapping[str, Column] = field(default_factory=OrderedDict)
    # max length not count
    arrays: Mapping[str, int] = field(default_factory=dict)
    # for headers
    titles: Mapping[str, str] = field(default_factory=dict)
    child_tables: List[str] = field(default_factory=list)
    types: Mapping[str, List[str]] = field(default_factory=dict)

    preview_rows: Sequence[dict] = field(default_factory=list)
    preview_rows_combined: Sequence[dict] = field(default_factory=list)

    def __post_init__(self):
        for attr in (
            "columns",
            "propagated_columns",
            "combined_columns",
            "additional_columns",
        ):
            obj = getattr(self, attr, {})
            if obj:
                init = OrderedDict()
                for name, col in obj.items():
                    if not is_dataclass(col):
                        col = Column(**col)
                    init[name] = col
                setattr(self, attr, init)

    def _counter(self, split, cond):
        cols = self.columns if split else self.combined_columns
        return [header for header, col in cols.items() if cond(col)]

    def missing_rows(self, split=True):
        """Return columns available in schema but not in analyzed data"""
        return self._counter(split, lambda c: c.hits == 0)

    def available_rows(self, split=True):
        """Return available in analyzed data columns"""
        return self._counter(split, lambda c: c.hits > 0)

    def __iter__(self):
        for col in self.columns:
            yield col

    def __getitem__(self, path):
        return self.columns.get(path)

    def add_column(
        self,
        path,
        item,
        item_type,
        parent,
        combined_only=False,
        additional=False,
        joinable=False,
    ):
        """Add new column to the table

        :param path: Column path
        :param item: Object schema description
        :param item_type: Column expected type
        :param parent: Parent object schema description
        :param combined_only: Make this column available only in combined version of table
        :param additional: Mark this column as missing in schema
        :param joinable: Mark this column as array of strings
        """
        title = prepare_title(item, parent)
        column = Column(title, item_type, path)
        root = get_root(self)
        # combined_path = combine_path(root, path) if not joinable else path
        combined_path = combine_path(root, path)
        self.combined_columns[combined_path] = Column(title, item_type, combined_path)

        for p in (path, combined_path):
            self.titles[p] = title

        if not combined_only:
            self.columns[path] = column
        if not self.is_root:
            root_table = get_root(self)
            root_table.add_column(
                path,
                item,
                item_type,
                parent=parent,
                combined_only=True,
                joinable=joinable,
            )
        if additional:
            self.additional_columns[path] = column

    def inc_column(self, header, combined=False):
        """Increment data counter in column

        :param header: Column path
        :param combined: Increment header only in combined version of table
        """
        if combined:
            self.combined_columns[header].hits += 1
            return
        self.columns[header].hits += 1
        if header in self.combined_columns:
            self.combined_columns[header].hits += 1
        if header in self.additional_columns:
            self.additional_columns[header].hits += 1

    def set_array(self, header, item):
        """Try to set maximum length of array

        :param header: Path to array object
        :param item: Array from data
        :return: True if array is bigger than previously found and length was updated
        """
        count = self.arrays[header] or 0
        length = len(item)
        if length > count:
            self.arrays[header] = length
            return True
        return False

    def inc(self):
        """Increment number of rows in table"""
        self.total_rows += 1

    def dump(self):
        data = asdict(self)
        if data['parent']:
            data['parent'] = data['parent']['name']
        return data



def add_child_table(current_table, pointer, parent_key, key):
    """Create and append new child table to `current_table`

    :param current_table: Parent table to newly created table
    :param pointer: Path to which table should match
    :param parent_key: New table parent object filed name, used to generate table name
    :param key: New table field name object filed name, used to generate table name
    :return: Child table
    """
    table_name = generate_table_name(current_table.name, parent_key, key)
    child_table = Table(table_name, [pointer], parent=current_table)
    for col in DEFAULT_FIELDS:
        column = Column(col, "string", col)
        child_table.columns[col] = column
        child_table.combined_columns[col] = column
        child_table.titles[col] = col
    current_table.child_tables.append(table_name)
    get_root(current_table).arrays[pointer] = 0
    return child_table

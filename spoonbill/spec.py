import logging
from collections import OrderedDict
from dataclasses import dataclass, field, is_dataclass, replace
from typing import List, Mapping, Sequence

from spoonbill.common import DEFAULT_FIELDS, DEFAULT_FIELDS_COMBINED
from spoonbill.i18n import _
from spoonbill.utils import (
    combine_path,
    common_prefix,
    generate_table_name,
    get_path_for_array_col,
    get_pointer,
    insert_after_key,
)

LOGGER = logging.getLogger("spoonbill")


@dataclass
class Column:
    """
    A container for column information.

    :param id: The JSON path without indexes
    :param path: The JSON path with indexes
    :param title: The human-friendly title
    :param type: The expected type
    :param hits: The number of times the column contains data during analysis
    """

    id: str
    path: str
    title: str
    type: str
    hits: int = 0
    header: list = field(default_factory=list)


@dataclass
class Table:
    """
    A container for table information.

    :param name: Table name
    :param path: List of paths to gather data to this table
    :param total_rows: Total available rows in this table
    :param parent: Parent table, None if this table is root table
    :param is_root: This table is root table
    :param is_combined: This table contains data collected from different paths
    :param splitted: This table should be splitted
    :param rolled_up: This table should be ated from its parent
    :param columns: Columns extracted from schema for split version of this table
    :param combined_columns: Columns extracted from schema for unsplit version of this table
    :param additional_columns: Columns identified in dataset but not in schema
    :param arrays: Table array columns and maximum items (not the total count) in each array
    :param titles: All human-friendly column titles, extracted from the schema
    :param child_tables: List of possible child tables
    :param types: All paths matched to this table with corresponding object type on each path
    :param preview_rows: Generated preview for split version of this table
    :param preview_rows_combined: Generated preview for unsplit version of this table
    """

    name: str
    path: List[str]
    total_rows: int = 0
    # `parent` is a Table object, but dataclasses don't play well with recursion.
    parent: object = field(default_factory=dict)
    is_root: bool = False
    is_combined: bool = False
    splitted: bool = False
    rolled_up: bool = False
    columns: Mapping[str, Column] = field(default_factory=OrderedDict)
    combined_columns: Mapping[str, Column] = field(default_factory=OrderedDict)
    additional_columns: Mapping[str, Column] = field(default_factory=OrderedDict)
    arrays: Mapping[str, int] = field(default_factory=dict)
    titles: Mapping[str, str] = field(default_factory=dict)
    child_tables: List[str] = field(default_factory=list)
    types: Mapping[str, List[str]] = field(default_factory=dict)
    array_columns: Mapping[str, Column] = field(default_factory=OrderedDict)
    array_positions: Mapping[str, str] = field(default_factory=dict)

    preview_rows: Sequence[dict] = field(default_factory=list)
    preview_rows_combined: Sequence[dict] = field(default_factory=list)

    def __post_init__(self):
        for attr in (
            "columns",
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
            cols = DEFAULT_FIELDS_COMBINED
            if self.is_root and not self.is_combined:
                cols = DEFAULT_FIELDS
            for col in cols:
                column = Column(col, col, "string", col)
                if col not in self.columns:
                    self.columns[col] = column
                if col not in self.combined_columns:
                    self.combined_columns[col] = column
                self.titles[col] = _(col)

    def _counter(self, split, cond):
        cols = self.columns if split else self.combined_columns
        return [header for header, col in cols.items() if cond(col)]

    def missing_rows(self, split=True):
        """
        Return the columns that are available in the schema, but not present in the analyzed data.
        """

        return self._counter(split, lambda c: c.hits == 0)

    def available_rows(self, split=True):
        """
        Return the columns that are available in the analyzed data.
        """

        return self._counter(split, lambda c: c.hits > 0)

    def filter_columns(self, filter):
        self.columns = {col_id: col for col_id, col in self.columns.items() if not filter(col)}
        self.combined_columns = {col_id: col for col_id, col in self.combined_columns.items() if not filter(col)}

    def __iter__(self):
        for col in self.columns:
            yield col

    def __getitem__(self, path):
        return self.columns.get(path)

    def add_array_column(self, col, path, abs_path, max):
        array = self.is_array(path)
        col_path = get_path_for_array_col(abs_path, array)
        if self.arrays[array] > max:
            return

        if col_path not in self.combined_columns:
            col = replace(col, path=col_path)
            last_key = self.array_positions[array]
            self.array_positions[array] = col_path
            self.combined_columns = insert_after_key(self.combined_columns, {col_path: col}, last_key)
        if not self.is_root:
            self.parent.add_array_column(col, path, abs_path, max=max)

    def add_column(self, path, item_type, title, *, propagated=False, additional=False, abs_path=None, header=[]):
        """
        Add a new column to the table.

        :param path: The column's path
        :param item_type: The column's expected type
        :param title: Column title
        :param combined_only: Make this column available only in combined version of table
        :param propagated: Add column to parent table
        :param additional: Mark this column as missing in schema
        :param abs_path: The column's full JSON path
        """
        combined_path = combine_path(self, path)
        col = Column(path, combined_path, title, item_type, header=header)
        array = self.is_array(path)
        if additional:
            if array:
                # when we analyzing file we need to keep index from data not to use 0
                # e.g. /tender/items/166/relatedLot
                combined_path = abs_path
                col = replace(col, path=combined_path)
            LOGGER.debug(_("Detected additional column: %s in %s table") % (path, self.name))
            self.additional_columns[combined_path] = col

        if not propagated:
            self.columns[combined_path] = col
        self.combined_columns[combined_path] = col

        if propagated:
            self.array_columns[combined_path] = col
            self.array_positions[array] = combined_path
        if not self.is_root:
            self.parent.add_column(path, item_type, title, propagated=True, header=header)
        for p in (path, combined_path):
            if path not in self.titles:
                self.titles[p] = header
        if path not in self.types:
            self.types[path] = item_type

    def is_array(self, path):
        """
        Check whether the given path is in any table's arrays.
        """

        for array in sorted(self.arrays, reverse=True):
            if common_prefix(array, path) == array:
                return array
        return False

    def inc_column(self, abs_path, path):
        """
        Increment the number of non-empty cells in the column.

        :param abs_path: The column's full JSON path
        :param path: The column's JSON path without array indexes
        """
        header = get_pointer(self, abs_path, path, True)
        if header in self.combined_columns:
            self.combined_columns[header].hits += 1
        if not self.is_root:
            self.parent.inc_column(abs_path, path)

    def add_array(self, header):
        self.arrays[header] = 0
        if not self.is_root:
            self.parent.add_array(header)

    def set_array(self, header, item):
        """
        Try to set the maximum length of an array.

        :param header: The path to the array
        :param item: Array from data
        :return: Whether the array is bigger than previously found and the length was updated
        """
        count = self.arrays.get(header, 0)
        length = len(item)
        if length > count:
            self.arrays[header] = length
            if not self.is_root:
                return self.parent.set_array(header, item)
            return True
        return False

    def inc(self):
        """
        Increment the number of rows in the table.
        """

        self.total_rows += 1
        for col_name in DEFAULT_FIELDS_COMBINED:
            self.inc_column(col_name, col_name)

    def set_preview_path(self, abs_path, path, value, max_items):
        header = get_pointer(self, abs_path, path, True)
        array = self.is_array(path)
        self.preview_rows_combined[-1][header] = value
        if header in self.combined_columns:
            if not array or (array and self.arrays[array] < max_items):
                self.preview_rows[-1][header] = value
        if not self.is_root:
            self.parent.set_preview_path(abs_path, path, value, max_items)

    def split(self, pointer):
        def drop(col):
            return parent.is_array(col.id) == pointer

        self.rolled_up = True
        parent = self.parent
        if parent:
            parent.splitted = True
            parent.filter_columns(drop)
            parent.split(pointer)


def add_child_table(table, pointer, parent_key, key):
    """
    Create and append a new child table to the given table.

    :param table: The parent table to the newly created table
    :param pointer: Path to which table should match
    :param parent_key: New table parent object filed name, used to generate table name
    :param key: New table field name object filed name, used to generate table name
    :return: Child table
    """
    table_name = generate_table_name(table.name, parent_key, key)
    child_table = Table(table_name, [pointer], parent=table)
    table.child_tables.append(table_name)
    table.add_array(pointer)
    return child_table

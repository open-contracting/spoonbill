import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field, is_dataclass
from typing import List, Mapping

from spoonbill.common import DEFAULT_FIELDS, JOINABLE, JOINABLE_SEPARATOR
from spoonbill.i18n import LOCALE, _
from spoonbill.spec import Table
from spoonbill.utils import generate_row, get_pointer, get_root, make_count_column

LOGGER = logging.getLogger("spoonbill")


@dataclass
class TableFlattenConfig:
    """Table specific flattening configuration

    :param split: Split child arrays to separate tables
    :param pretty_headers: Use human friendly headers extracted from schema
    :param headers: User edited headers to override automatically extracted
    :param unnest: List of columns to output from child to parent table
    :param repeat: List of columns to clone in child tables
    :param only: List of columns to output
    """

    split: bool
    pretty_headers: bool = False
    headers: Mapping[str, str] = field(default_factory=dict)
    repeat: List[str] = field(default_factory=list)
    unnest: List[str] = field(default_factory=list)
    only: List[str] = field(default_factory=list)
    name: str = ""


@dataclass
class FlattenOptions:
    """Flattening configuration

    :param selection: List of selected tables to extract from data
    :param count: Include number of rows in child table in each parent table
    :param exclude: List of tables to exclude from export
    """

    selection: Mapping[str, TableFlattenConfig]
    exclude: List[str] = field(default_factory=list)
    count: bool = False

    def __post_init__(self):
        for name, table in self.selection.items():
            if not is_dataclass(table):
                self.selection[name] = TableFlattenConfig(**table)


class Flattener:
    """Data flattener

    In order to export data correctly Flattener requires previously analyzed tables data.
    During the process flattener could add columns not based on schema analysis, such as
    `itemsCount`.
    In every generated row, depending on table type, flattener will always few add autogenerated columns.
    For root table:
    * rowID
    * id
    * ocid
    For child tables this list well be extended with `parentID` column.

    :param options: Flattening options
    :param tables: Analyzed tables data
    """

    def __init__(self, options: FlattenOptions, tables: Mapping[str, Table], language=LOCALE):
        if not is_dataclass(options):
            options = FlattenOptions(**options)
        self.options = options
        self.tables = tables
        self.language = language

        self._lookup_cache = {}
        self._types_cache = {}
        self._path_cache = {}

        # init cache and filter only selected tables
        self.tables = {}
        for name, table in tables.items():
            if name not in self.options.selection:
                continue
            options = self.options.selection[name]
            split = options.split
            only = options.only
            if only:
                self._only(table, only, split)
            self._init_table_lookup(self.tables, table)
            for c_name in table.child_tables:
                if c_name in self.options.exclude:
                    continue

                c_table = tables[c_name]
                self._init_child_tables(tables, table, c_table, options)
        self._init_options(self.tables)

    def _init_child_tables(self, tables, table, c_table, options):
        split = options.split
        only = options.only

        if split and c_table.roll_up:
            if c_table.name not in self.options.selection:
                options = TableFlattenConfig(split=True)
                self.options.selection[c_table.name] = options
            self._init_table_lookup(self.tables, c_table)
        else:
            # use parent table
            self._init_cache(self._types_cache, c_table.types, table, only=only)
            self._init_cache(self._lookup_cache, c_table.combined_columns, table, only=only)
        if c_table.child_tables:
            for c_name in c_table.child_tables:
                if c_name in self.options.exclude:
                    continue
                cc_table = tables[c_name]
                self._init_child_tables(tables, table, cc_table, options)

    def _init_cache(self, cache, paths, table, only=None):
        for path in paths:
            if path not in DEFAULT_FIELDS:
                if not only or (only and path in only):
                    cache[path] = table

    def _cache_path(self, table):
        self._init_cache(self._path_cache, table.path, table)

    def _cache_types(self, table):
        self._init_cache(self._types_cache, table.types, table)

    def _cache_cols(self, table, split):
        cols = table if split else table.combined_columns
        self._init_cache(self._lookup_cache, cols, table)

    def _init_table_lookup(self, tables, table):
        if table.total_rows == 0:
            return

        name = table.name
        options = self.options.selection[name]
        split = options.split
        tables[name] = table

        self._cache_path(table)
        self._cache_types(table)
        self._cache_cols(table, split)

    def _init_options(self, tables):
        for table in tables.values():

            name = table.name
            count = self.options.count
            options = self.options.selection[name]
            unnest = options.unnest
            split = options.split
            repeat = options.repeat

            if count:
                for array in table.arrays:
                    path = make_count_column(array)
                    target = self._types_cache.get(array) or table
                    combined = split and table.should_split
                    if combined:
                        # add count columns only if table is rolled up
                        # in other way it could be frustrating
                        # e.g. it may generate columns for whole array like:
                        # /tender/items/200/additionalClassificationsCount
                        target.add_column(
                            path,
                            "integer",
                            _(path, self.language),
                            additional=True,
                            combined_only=not combined,
                            propagate=False,
                        )
                        target.inc_column(path, path)
            if unnest:
                for col_id in unnest:
                    col = table.combined_columns[col_id]
                    table.columns[col_id] = col
            if repeat:
                for col_id in repeat:
                    columns = table.columns if split else table.combined_columns
                    title = _(col_id)
                    col = columns.get(col_id)
                    if not col:
                        LOGGER.warning(
                            _("Ignoring repeat column {} because it is not in table {}").format(col_id, name)
                        )
                        continue
                    for c_name in table.child_tables:
                        child_table = self.tables.get(c_name)
                        if child_table:
                            child_table.columns[col_id] = col
                            child_table.combined_columns[col_id] = col
                            child_table.titles[col_id] = title

    def _only(self, table, only, split):
        columns = table.columns
        if split:
            columns = table.combined_columns
        paths = {c_id: c for c_id, c in table.types.items() if c_id not in columns}
        columns = {c_id: c for c_id, c in columns.items() if c_id in only}
        paths.update(columns)
        table.columns = columns
        table.combined_columns = columns
        table.types = paths

    def flatten(self, releases):
        """Flatten releases

        :param releases: releases as iterable object
        :return: Iterator over mapping between table name and list of rows for each release
        """

        for counter, release in enumerate(releases):
            rows = defaultdict(list)
            to_flatten = deque([("", "", "", {}, release, {})])
            separator = "/"
            ocid = release["ocid"]
            buyer = release.get("buyer", {})

            while to_flatten:
                abs_path, path, parent_key, parent, record, repeat = to_flatten.pop()

                table = self._path_cache.get(path)
                if path == "/buyer":
                    # only useful in analysis
                    continue
                if table:
                    # Strict match /tender /parties etc., so this is a new row
                    row = generate_row(
                        table, ocid, record.get("id", ""), parent.get("id", ""), parent_table=parent_key, buyer=buyer
                    )
                    only = self.options.selection[table.name].only
                    if only:
                        row = {col: col_v for col, col_v in row.items() if col in only}
                    if table.is_root:
                        repeat = {}
                    if repeat:
                        row.update(repeat)
                    rows[table.name].append(row)
                for key, item in record.items():
                    pointer = separator.join((path, key))
                    abs_pointer = separator.join((abs_path, key))

                    table = self._lookup_cache.get(pointer) or self._types_cache.get(pointer)
                    if not table:
                        continue

                    item_type = table.types.get(pointer)
                    options = self.options.selection[table.name]
                    split = options.split
                    if pointer in options.repeat:
                        repeat[pointer] = item

                    if isinstance(item, dict):
                        to_flatten.append((abs_pointer, pointer, key, record, item, repeat))
                    elif isinstance(item, list):
                        if item_type == JOINABLE:
                            value = JOINABLE_SEPARATOR.join(item)
                            rows[table.name][-1][pointer] = value
                        else:
                            if self.options.count and pointer not in table.path and split and table.should_split:
                                abs_pointer = get_pointer(
                                    table,
                                    abs_pointer,
                                    pointer,
                                    split,
                                    separator=separator,
                                )
                                abs_pointer += "Count"
                                if abs_pointer in table:
                                    rows[table.name][-1][abs_pointer] = len(item)
                            for index, value in enumerate(item):
                                if isinstance(value, dict):
                                    abs_pointer = get_pointer(
                                        table,
                                        separator.join((abs_path, key)),
                                        pointer,
                                        split,
                                        separator=separator,
                                        index=str(index),
                                    )
                                    to_flatten.append(
                                        (
                                            abs_pointer,
                                            pointer,
                                            key,
                                            record,
                                            value,
                                            repeat,
                                        )
                                    )
                    else:
                        if not table.is_root:
                            root = get_root(table)
                            unnest = self.options.selection[root.name].unnest
                            if unnest and abs_pointer in unnest:
                                rows[root.name][-1][abs_pointer] = item
                                continue
                        pointer = get_pointer(table, abs_pointer, pointer, split, separator=separator)
                        rows[table.name][-1][pointer] = item
            yield counter, rows

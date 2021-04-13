from dataclasses import dataclass, is_dataclass, field
from typing import Mapping, Sequence
from collections import defaultdict, deque
from pathlib import Path

import json
import logging

from spoonbill.spec import Table
from spoonbill.stats import DataPreprocessor
from spoonbill.utils import iter_file, generate_row_id
from spoonbill.writer import XlsxWriter, CSVWriter
from spoonbill.common import ROOT_TABLES, COMBINED_TABLES, JOINABLE

LOGGER = logging.getLogger("spoonbill")


@dataclass
class TableFlattenConfig:
    """Table specific flattening configuration

    :param split: Split child arrays to separate tables
    :param pretty_headers: Use human friendly headers extracted from schema
    :param headers: User edited headers to override automatically extracted
    """

    split: bool
    pretty_headers: bool = False
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass
class FlattenOptions:
    """Whole flattening process configuration

    :param selection: List of of tables to extract from data and flatten
    """

    selection: Mapping[str, TableFlattenConfig]
    # combine: bool = True

    def __post_init__(self):
        for name, table in self.selection.items():
            if not is_dataclass(table):
                self.selection[name] = TableFlattenConfig(**table)


@dataclass
class Flattener:
    """Configurable data flattener

    :param options: Flattening options
    :param tables: Analyzed tables data
    """

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
        """Flatten releases

        :param releases: releases as iterable object
        :return: Iterator over mapping between table name and list of rows for each release
        """

        for release in releases:
            rows = defaultdict(list)
            to_flatten = deque([("", "", "", {}, release)])
            separator = "/"
            ocid = release["ocid"]
            top_level_id = release["id"]

            while to_flatten:
                abs_path, path, parent_key, parent, record = to_flatten.pop()
                # Strict match /tender /parties etc., so this is a new row
                table = self._path_cache.get(path)
                if table:
                    row_id = generate_row_id(
                        ocid, record.get("id", ""), parent_key, top_level_id
                    )
                    rows[table.name].append(
                        {
                            "rowID": row_id,
                            "id": top_level_id,
                            "parentID": parent.get("id"),
                            "ocid": ocid,
                        }
                    )

                for key, item in record.items():
                    pointer = separator.join((path, key))
                    table = self._lookup_cache.get(pointer) or self._types_cache.get(
                        pointer
                    )
                    if not table:
                        continue
                    type_ = table.types.get(pointer)

                    if isinstance(item, dict):
                        a_p = separator.join((abs_path, key))
                        to_flatten.append((a_p, pointer, key, record, item))
                    elif isinstance(item, list):
                        if type_ == JOINABLE:
                            value = JOINABLE.join(item)
                            rows[table.name][-1][pointer] = value
                        else:
                            for index, value in enumerate(item):
                                if isinstance(value, dict):
                                    if table.is_root:
                                        a_p = separator.join((abs_path, key))
                                    else:
                                        a_p = separator.join(
                                            (abs_path, key, str(index))
                                        )
                                    to_flatten.append(
                                        (a_p, pointer, key, record, value)
                                    )
                    else:
                        a_pointer = separator.join((abs_path, key))
                        if a_pointer in self._lookup_cache:
                            rows[table.name][-1][a_pointer] = item
                        else:
                            rows[table.name][-1][pointer] = item
            yield rows


class FileAnalyzer:
    """Main utility for analyzing files

    :param workdir: Working directory
    :param schema: Json schema file to use with data
    :param root_tables: Path configuration which should become root tables
    :param combined_tables: Path configuration for tables with multiple sources
    :param root_key: Field name to access records
    """

    def __init__(
        self,
        workdir,
        schema,
        root_tables=ROOT_TABLES,
        combined_tables=COMBINED_TABLES,
        root_key="releases",
    ):
        self.workdir = Path(workdir)
        self.spec = DataPreprocessor(
            json.load(schema), root_tables, combined_tables=combined_tables
        )
        # TODO: decect package
        self.root_key = root_key

    def analyze_file(self, filename):
        """Analyze provided file
        :param filename: Input filename
        """
        path = self.workdir / filename
        self.spec.process_items(iter_file(path, self.root_key))

    def dump_to_file(self, filename):
        """Save analyzed information to file

        :param filename: Output filename in working directory
        """
        path = self.workdir / filename
        with open(path, "w") as fd:
            json.dump(self.spec.dump(), fd, default=str)


class FileFlattener:
    """Main utility for flattening files

    :param workdir: Working directory
    :param options: Flattening configuration
    :param tables: Analyzed tables data
    :param root_key: Field name to access records
    :param csv: If True generate cvs files
    :param xlsx: Generate combined xlsx table
    """

    def __init__(
        self, workdir, options, tables, root_key="releases", csv=True, xlsx=True
    ):
        self.flattener = Flattener(options, tables)
        self.workdir = Path(workdir)
        # TODO: detect package, where?
        self.root_key = root_key
        self.writers = []

        if csv:
            self.writers.append(
                CSVWriter(self.workdir, self.flattener.tables, self.flattener.options)
            )
        if xlsx:
            self.writers.append(
                XlsxWriter(self.workdir, self.flattener.tables, self.flattener.options)
            )

    def writerow(self, table, row):
        """Write row to output file"""
        for wr in self.writers:
            wr.writerow(table, row)

    def _close(self):
        for wr in self.writers:
            wr.close()

    def flatten_file(self, filename):
        """Flatten file

        :param filename: Input filename in working directory
        """
        path = self.workdir / filename
        for w in self.writers:
            w.writeheaders()

        for data in self.flattener.flatten(iter_file(path, self.root_key)):
            try:
                for table, rows in data.items():
                    for row in rows:
                        self.writerow(table, row)
            except Exception as err:
                LOGGER.warning(f"Failed to write row {row} with {err}")
        self._close()

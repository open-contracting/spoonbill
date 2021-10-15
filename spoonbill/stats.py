import logging
import pickle
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import List, Mapping

import jsonref
from flatten_dict import flatten

from spoonbill.common import ARRAY, JOINABLE, JOINABLE_SEPARATOR, PREVIEW_ROWS, SEPARATOR, TABLE_THRESHOLD
from spoonbill.i18n import LOCALE, _
from spoonbill.rowdata import Rows
from spoonbill.spec import Table, add_child_table
from spoonbill.utils import (
    PYTHON_TO_JSON_TYPE,
    RepeatFilter,
    add_paths_to_schema,
    common_prefix,
    extract_type,
    generate_table_name,
    get_matching_tables,
    resolve_file_uri,
    validate_type,
)

LOGGER = logging.getLogger("spoonbill")
LOGGER.addFilter(RepeatFilter())


class DataPreprocessor:
    """
    Data analyzer

    Processes the given schema and, based on this, extracts information from the iterable dataset.

    :param schema: The dataset's schema
    :param root_tables: The paths which should become root tables
    :param combined_tables: The paths which should become tables that combine data from different locations
    :param tables: Use these tables objects instead of parsing the schema
    :param table_threshold: The maximum array length, before it is recommended to split out a child table
    :param total_items: The total objects processed
    :param language: Language to use for the human-readable headings
    """

    def __init__(
        self,
        schema: Mapping,
        root_tables: Mapping[str, List],
        combined_tables: Mapping[str, List] = None,
        tables: Mapping[str, Table] = None,
        table_threshold=TABLE_THRESHOLD,
        total_items=0,
        language=LOCALE,
        multiple_values=False,
        pkg_type=None,
        with_preview=True,
    ):
        self.schema = schema
        self.root_tables = root_tables
        self.combined_tables = combined_tables or {}
        self.tables = tables or {}
        self.table_threshold = table_threshold
        self.multiple_values = multiple_values

        self.total_items = total_items
        self.current_table = None

        self.language = language
        self.names_counter = defaultdict(int)
        self.with_preview = with_preview
        if not self.tables:
            self.parse_schema()
        self.pkg_type = pkg_type

    def __getitem__(self, table):
        return self.tables[table]

    def name_check(self, parent_key, key):
        table_name = generate_table_name(self.current_table.name, parent_key, key)
        self.names_counter[table_name] += 1
        if self.names_counter[table_name] > 1:
            key = key[:4] + str(self.names_counter[table_name] - 1)
        return key

    def guess_type(self, item):
        return [PYTHON_TO_JSON_TYPE.get(type(item).__name__)]

    def init_tables(self, tables, is_combined=False):
        """
        Initialize the root tables with default fields.
        """
        for name, path in tables.items():
            table = Table(name, path, is_root=True, is_combined=is_combined, parent="")
            self.tables[name] = table

    def is_base_table(self):
        return self.current_table.is_root or self.current_table.is_combined

    def load_schema(
        self,
    ):
        """"""
        # if isinstance(self.schema, (str, Path)):
        #     self.schema = resolve_file_uri(self.schema)
        # if not isinstance(self.schema, jsonref.JsonRef):
        #     self.schema = jsonref.JsonRef.replace_refs(self.schema)

        if isinstance(self.schema, (str, Path)):
            self.schema = resolve_file_uri(self.schema)
        self.init_tables(self.root_tables)
        if not isinstance(self.schema, jsonref.JsonRef):
            self.schema = jsonref.JsonRef.replace_refs(self.schema)
        if self.combined_tables:
            self.init_tables(self.combined_tables, is_combined=True)

    def prepare_tables(self):
        self.init_tables(self.root_tables)
        if self.combined_tables:
            self.init_tables(self.combined_tables, is_combined=True)

    def parse_schema(self):
        """
        Extract information from the schema.
        """
        self.load_schema()
        # self.prepare_tables()
        proxy = add_paths_to_schema(self.schema)
        to_analyze = deque([("", "", {}, proxy)])

        # TODO: check if recursion is better for field ordering
        while to_analyze:
            path, parent_key, parent, prop = to_analyze.pop()
            if prop.get("deprecated"):
                continue
            # TODO: handle oneOf anyOf allOf
            properties = prop.get("properties", {})
            if properties:
                for key, item in properties.items():
                    if key in ("$title", "$path"):
                        continue
                    if item.get("deprecated"):
                        continue
                    if hasattr(item, "__reference__") and item.__reference__.get("deprecated"):
                        continue

                    typeset = extract_type(item)
                    pointer = self.join_path(path, key)
                    self.current_table = self.get_table(pointer)

                    if not self.current_table:
                        continue

                    self.current_table.types[pointer] = typeset

                    if "object" in typeset:
                        to_analyze.append((pointer, key, properties, item))
                    elif "array" in typeset:
                        items = item["items"]
                        items_type = extract_type(items)
                        if set(items_type) & {"array", "object"}:
                            if pointer not in self.current_table.path:
                                # found child array, need to create child table
                                key = self.name_check(parent_key, key)
                                self._add_table(add_child_table(self.current_table, pointer, parent_key, key), pointer)
                            to_analyze.append((pointer, key, properties, items))
                        else:
                            # This means we in array of strings, so this becomes a single joinable column
                            typeset = ARRAY.format(items_type)
                            self.current_table.types[pointer] = JOINABLE
                            self.current_table.add_column(
                                pointer, typeset, _(pointer, self.language), header=item["$title"]
                            )
                    else:
                        if self.current_table.is_combined:
                            pointer = SEPARATOR + self.join_path(parent_key, key)
                        self.current_table.add_column(
                            pointer, typeset, _(pointer, self.language), header=item["$title"]
                        )

            else:
                # TODO: not sure what to do here
                continue

    def add_column(self, pointer, typeset):
        self.current_table.add_column(pointer, typeset, _(pointer, self.language))

    def _add_table(self, table, pointer):
        self.tables[table.name] = table
        self.current_table = table
        self.get_table.cache_clear()

    def add_additional_table(self, pointer, abs_pointer, parent_key, key, item):
        LOGGER.debug(_("Detected additional table: %s") % pointer)
        self.current_table.types[pointer] = ["array"]
        self._add_table(add_child_table(self.current_table, pointer, parent_key, key), pointer)
        # add columns beforehand because it might be required
        # to recalculate  and reorder headers when enlarging array
        # there must be a better way but it should work for now
        for extended_item in item:
            for path_, it in flatten(extended_item, reducer="path").items():
                ppointer = self.join_path(pointer, path_)
                if ppointer not in self.current_table:
                    self.current_table.add_column(
                        ppointer,
                        self.guess_type(it),
                        _(ppointer, self.language),
                        abs_path=self.join_path(abs_pointer, path_),
                        header=ppointer,
                    )

    @lru_cache(maxsize=None)
    def get_table(self, path):
        """
        Get the table that best matches the given path.

        :param path: A path
        :return: A table
        """
        candidates = get_matching_tables(self.tables, path)
        if not candidates:
            return
        return candidates[0]

    def add_preview_row(self, rows, item_id, parent_key):
        """
        Append a mostly-empty row to the previews.

        This is important to do, because other code uses an index of -1 to access and update the current row.

        :param rows: The Rows object
        :param item_id: Object id
        """
        table = self.current_table
        if self.with_preview and table.total_rows < PREVIEW_ROWS:
            for p_rows in table.preview_rows, table.preview_rows_combined:
                row = rows.new_row(table, item_id).as_dict()
                p_rows.append(row)

    def inc_table_rows(self, item, rows, parent_key, record):
        c = item if isinstance(item, list) else [item]
        for _nop in c:
            self.current_table.inc()
            self.add_preview_row(rows, record.get("id", ""), parent_key)

    def is_new_row(self, pointer):
        # strict match like /parties, /tender
        return pointer in self.current_table.path and pointer != "/buyer"

    def join_path(self, *args):
        return SEPARATOR.join(args)

    def get_paths_for_combined_table(self, parent_key, key):
        pointer = SEPARATOR + self.join_path(parent_key, key)
        return (pointer, pointer)

    def is_type_matched(self, pointer, item, item_type):
        # TODO: this validation should probably be smarter with arrays
        if item_type and item_type != JOINABLE and not validate_type(item_type, item):
            LOGGER.error("Mismatched type on %s expected %s" % (pointer, item_type))
            return False
        return True

    def add_joinable_column(self, abs_pointer, pointer):
        LOGGER.debug(_("Detected additional column: %s in %s table") % (abs_pointer, self.current_table.name))
        self.current_table.types[pointer] = JOINABLE
        self.current_table.add_column(
            pointer, JOINABLE, _(pointer, self.language), additional=True, abs_path=abs_pointer, header=pointer
        )

    def handle_array_expanded(self, pointer, item, abs_path, key):
        splitted = len(item) >= self.table_threshold
        if splitted:
            self.current_table.split(pointer)

    def is_array_col(self, abs_path):
        chunks = abs_path.split(SEPARATOR)
        path = self.join_path(*[p for p in chunks if not p.isdigit()])
        return path in self.current_table

    def clean_up_missing_arrays(self):
        def drop(col):
            is_array = table.is_array(col.id)
            return is_array and col.hits == 0

        for table in self.tables.values():
            table.filter_columns(drop)

    def process_items(self, releases, with_preview=True):
        """
        Analyze releases.

        Iterates over every release to calculate metrics and optionally generates previews for combined and split
        versions of each table.

        :param releases: The releases to analyze
        :param with_preview: Whether to generate previews for each table
        """
        for count, release in enumerate(releases):

            to_analyze = deque([("", "", "", {}, release)])
            rows = Rows(ocid=release["ocid"], buyer=release.get("buyer", {}), data=defaultdict(list))
            while to_analyze:
                abs_path, path, parent_key, parent, record = to_analyze.popleft()
                if hasattr(record, "items"):
                    for key, item in record.items():
                        pointer = self.join_path(path, key)

                        self.current_table = self.get_table(pointer)
                        if not self.current_table:
                            continue

                        if self.is_new_row(pointer):
                            self.inc_table_rows(item, rows, parent_key, record)

                        self.extend_table_types(pointer, item)
                        item_type = self.current_table.types.get(pointer)

                        if not self.is_type_matched(pointer, item, item_type):
                            continue

                        if isinstance(item, dict):
                            to_analyze.append(
                                (
                                    self.join_path(abs_path, key),
                                    pointer,
                                    key,
                                    record,
                                    item,
                                )
                            )
                        elif item and isinstance(item, list):
                            abs_pointer = self.join_path(abs_path, key)

                            if not isinstance(item[0], dict) and not item_type:
                                item_type = JOINABLE
                                self.add_joinable_column(abs_pointer, pointer)

                            if item_type == JOINABLE:
                                self.current_table.inc_column(abs_pointer, pointer)
                                if self.with_preview and count < PREVIEW_ROWS:
                                    value = JOINABLE_SEPARATOR.join(item)
                                    self.current_table.set_preview_path(
                                        abs_pointer, pointer, value, self.table_threshold
                                    )
                            elif self.is_base_table():
                                for value in item:
                                    to_analyze.append(
                                        (
                                            abs_pointer,
                                            pointer,
                                            key,
                                            record,
                                            value,
                                        )
                                    )
                            else:
                                parent_table = self.current_table.parent
                                if pointer not in parent_table.arrays:
                                    LOGGER.debug(_("Detected additional table: %s") % pointer)
                                    self.current_table.types[pointer] = ["array"]
                                    parent_table = self.current_table
                                    self.add_additional_table(pointer, abs_pointer, parent_key, key, item)
                                    self.add_preview_row(rows, record.get("id", ""), parent_key)

                                if parent_table.set_array(pointer, item):
                                    self.handle_array_expanded(pointer, item, abs_path, key)

                                for i, value in enumerate(item):
                                    if isinstance(value, dict):
                                        abs_pointer = self.join_path(abs_path, key, str(i))
                                        to_analyze.append(
                                            (
                                                abs_pointer,
                                                pointer,
                                                parent_key,
                                                record,
                                                value,
                                            )
                                        )
                        else:
                            abs_pointer = self.join_path(abs_path, key)
                            if self.current_table.is_combined:
                                pointer, abs_pointer = self.get_paths_for_combined_table(parent_key, key)
                            col = self.current_table.columns.get(pointer)
                            if col:
                                if abs_pointer not in self.current_table:
                                    parent = self.current_table.parent
                                    parent.add_array_column(col, pointer, abs_pointer, max=self.table_threshold)
                            else:
                                self.current_table.add_column(
                                    pointer,
                                    self.guess_type(item),
                                    _(pointer, self.language),
                                    additional=True,
                                    abs_path=abs_pointer,
                                )
                            self.current_table.inc_column(abs_pointer, pointer)
                            if item and self.with_preview and count < PREVIEW_ROWS:
                                if not pointer.startswith("/buyer"):
                                    self.current_table.set_preview_path(
                                        abs_pointer, pointer, item, self.table_threshold
                                    )
            yield count
        self.clean_up_missing_arrays()
        self.total_items = count

    def dump(self, path):
        """
        Dump the data processor's state to a file.

        :param path: Full path to file
        """
        try:
            with open(path, "wb") as fd:
                pickle.dump(self, fd)
        except (OSError, IOError) as e:
            LOGGER.error(_("Failed to dump DataPreprocessor to file. Error: {}").format(e))

    @classmethod
    def restore(_cls, path):
        """
        Restore a data preprocessor's state from a file.

        :param path: Full path to file
        """
        try:
            with open(path, "rb") as fd:
                return pickle.load(fd)
        except (TypeError, pickle.UnpicklingError):
            LOGGER.error(_("Invalid pickle file. Can't restore."))

    def extend_table_types(self, pointer, item):
        """
        Check if path belong to table and expand its types
        :param pointer: Path to an item
        :param item: Item being analyzed
        """
        table = self.current_table
        if pointer not in table.types and pointer not in table.path:
            if any((common_prefix(pointer, path) for path in table.path)):
                self.current_table.types[pointer] = self.guess_type(item)

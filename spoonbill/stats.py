import logging
import pickle
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import List, Mapping

import jsonref
from flatten_dict import flatten

from spoonbill.common import ARRAY, COMBINED_TABLES, JOINABLE, JOINABLE_SEPARATOR, PREVIEW_ROWS, TABLE_THRESHOLD
from spoonbill.i18n import LOCALE, _
from spoonbill.rowdata import Rows
from spoonbill.spec import Table, add_child_table
from spoonbill.utils import (
    PYTHON_TO_JSON_TYPE,
    RepeatFilter,
    add_paths_to_schema,
    extract_type,
    generate_table_name,
    get_matching_tables,
    get_root,
    recalculate_headers,
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
        header_separator="/",
        language=LOCALE,
        multiple_values=False,
        pkg_type=None,
    ):
        self.schema = schema
        self.root_tables = root_tables
        self.combined_tables = combined_tables or {}
        self.tables = tables or {}
        self.table_threshold = table_threshold
        self.multiple_values = multiple_values

        self.header_separator = header_separator
        self.total_items = total_items
        self.current_table = None

        self.language = language
        self.names_counter = defaultdict(int)
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

    def init_tables(self, tables, is_combined=False):
        """
        Initialize the root tables with default fields.
        """
        for name, path in tables.items():
            table = Table(name, path, is_root=True, is_combined=is_combined, parent="")
            self.tables[name] = table

    def parse_schema(self):
        """
        Extract information from the schema.
        """
        if isinstance(self.schema, (str, Path)):
            self.schema = resolve_file_uri(self.schema)
        self.init_tables(self.root_tables)
        if not isinstance(self.schema, jsonref.JsonRef):
            self.schema = jsonref.JsonRef.replace_refs(self.schema)
        if self.combined_tables:
            self.init_tables(self.combined_tables, is_combined=True)
        separator = self.header_separator
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
                    pointer = separator.join([path, key])
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
                            pointer = separator + separator.join((parent_key, key))

                        self.current_table.add_column(
                            pointer, typeset, _(pointer, self.language), header=item["$title"]
                        )

            else:
                # TODO: not sure what to do here
                continue

    def _add_table(self, table, pointer):
        self.tables[table.name] = table
        self.current_table = table
        self.get_table.cache_clear()

    def _add_additional_table(self, pointer, abs_pointer, parent_key, key, item, separator="/"):
        LOGGER.debug(_("Detected additional table: %s") % pointer)
        self.current_table.types[pointer] = ["array"]
        self._add_table(add_child_table(self.current_table, pointer, parent_key, key), pointer)
        # add columns beforehand because it might be required
        # to recalculate  and reorder headers when enlarging array
        # there must be a better way but it should work for now
        for extended_item in item:
            for path_, it in flatten(extended_item, reducer="path").items():
                p = separator.join((pointer, path_))
                a_p = separator.join((abs_pointer, path_))
                if p not in self.current_table:
                    self.current_table.add_column(
                        p,
                        PYTHON_TO_JSON_TYPE.get(type(it).__name__, "N/A"),
                        _(p, self.language),
                        abs_path=a_p,
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
        for p_rows in table.preview_rows, table.preview_rows_combined:
            p_rows.append(rows.new_row(table, item_id).as_dict())

    def process_items(self, releases, with_preview=True):
        """
        Analyze releases.

        Iterates over every release to calculate metrics and optionally generates previews for combined and split
        versions of each table.

        :param releases: The releases to analyze
        :param with_preview: Whether to generate previews for each table
        """
        separator = self.header_separator
        for count, release in enumerate(releases):
            to_analyze = deque([("", "", "", {}, release)])
            rows = Rows(ocid=release["ocid"], buyer=release.get("buyer", {}), data=defaultdict(list))

            while to_analyze:
                abs_path, path, parent_key, parent, record = to_analyze.pop()
                for key, item in record.items():
                    pointer = separator.join([path, key])
                    self.current_table = self.get_table(pointer)
                    if not self.current_table:
                        continue
                    item_type = self.current_table.types.get(pointer)
                    if pointer in self.current_table.path and pointer != "/buyer":
                        # strict match like /parties, /tender
                        c = item if isinstance(item, list) else [item]
                        for _nop in c:
                            self.current_table.inc()
                            if with_preview and count < PREVIEW_ROWS:
                                self.add_preview_row(rows, record.get("id", ""), parent_key)

                    # TODO: this validation should probably be smarter with arrays
                    if item_type and item_type != JOINABLE and not validate_type(item_type, item):
                        LOGGER.error("Mismatched type on %s expected %s" % (pointer, item_type))
                        continue

                    if self.current_table.name in COMBINED_TABLES:
                        self.extend_table_types(pointer, item)

                    if isinstance(item, dict):
                        self.current_table.types[pointer] = [PYTHON_TO_JSON_TYPE.get(type(item).__name__)]
                        to_analyze.append(
                            (
                                separator.join([abs_path, key]),
                                pointer,
                                key,
                                record,
                                item,
                            )
                        )
                    elif item and isinstance(item, list):
                        abs_pointer = separator.join([abs_path, key])
                        if not isinstance(item[0], dict) and not item_type:
                            LOGGER.debug(
                                _("Detected additional column: %s in %s table")
                                % (abs_pointer, self.current_table.name)
                            )
                            item_type = JOINABLE
                            self.current_table.add_column(
                                pointer,
                                JOINABLE,
                                _(pointer, self.language),
                                additional=True,
                                abs_path=abs_pointer,
                            )
                        if item_type == JOINABLE:
                            self.current_table.inc_column(abs_pointer, pointer)
                            if with_preview and count < PREVIEW_ROWS:
                                value = JOINABLE_SEPARATOR.join(item)
                                self.current_table.set_preview_path(abs_pointer, pointer, value, self.table_threshold)
                        elif self.current_table.is_root or self.current_table.is_combined:
                            self.current_table.types[pointer] = [PYTHON_TO_JSON_TYPE.get(type(item).__name__)]
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
                                # TODO: do we need to mark this table as additional
                                self._add_additional_table(pointer, abs_pointer, parent_key, key, item)
                                self.add_preview_row(rows, record.get("id", ""), parent_key)
                            if parent_table.set_array(pointer, item):
                                should_split = len(item) >= self.table_threshold
                                if should_split:
                                    parent_table.should_split = True
                                    self.current_table.roll_up = True
                                recalculate_headers(
                                    parent_table, pointer, abs_path, key, item, should_split, separator
                                )

                            for i, value in enumerate(item):
                                if isinstance(value, dict):
                                    abs_pointer = separator.join([abs_path, key, str(i)])
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
                        root = get_root(self.current_table)
                        abs_pointer = separator.join((abs_path, key))
                        if self.current_table.is_combined:
                            pointer = separator + separator.join((parent_key, key))
                            abs_pointer = pointer
                        if abs_pointer not in root.combined_columns:
                            self.current_table.add_column(
                                pointer,
                                PYTHON_TO_JSON_TYPE.get(type(item).__name__, "N/A"),
                                _(pointer, self.language),
                                additional=True,
                                abs_path=abs_pointer,
                            )
                        self.current_table.inc_column(abs_pointer, pointer)
                        if item and with_preview and count < PREVIEW_ROWS:
                            if not pointer.startswith("/buyer"):
                                self.current_table.set_preview_path(abs_pointer, pointer, item, self.table_threshold)
            yield count
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
        for path in self.current_table.path:
            if pointer.startswith(path) and pointer not in self.current_table.types:
                self.current_table.types[pointer] = [PYTHON_TO_JSON_TYPE.get(type(item).__name__)]

import locale
import logging
import pickle
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import List, Mapping

import jsonref

from spoonbill.common import ARRAY, DEFAULT_FIELDS, JOINABLE, JOINABLE_SEPARATOR, TABLE_THRESHOLD
from spoonbill.i18n import DOMAIN, LOCALE, LOCALEDIR, _
from spoonbill.spec import Column, Table, add_child_table
from spoonbill.utils import (
    PYTHON_TO_JSON_TYPE,
    RepeatFilter,
    extract_type,
    generate_row_id,
    generate_table_name,
    get_matching_tables,
    get_pointer,
    get_root,
    recalculate_headers,
    resolve_file_uri,
    validate_type,
)

PREVIEW_ROWS = 20
LOGGER = logging.getLogger("spoonbill")
LOGGER.addFilter(RepeatFilter())


class DataPreprocessor:
    """Data analyzer

    Process provided schema and based on this data extracts information fromm iterable dataset

    :param schema: Dataset schema
    :param root_tables: Paths which should become root tables
    :param combined_tables: List of tables with data from different locations
    :param tables: Do not parse schema and use this tables data
    :param table_threshold: Maximum array length before system recommends it to separated to child table
    :param total_items: Total objects processed
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
    ):
        self.schema = schema
        self.root_tables = root_tables
        self.combined_tables = combined_tables or {}
        self.tables = tables or {}
        self.table_threshold = table_threshold

        self.header_separator = header_separator
        self.total_items = total_items
        self.current_table = None

        self.language = language
        self.names_counter = defaultdict(int)
        if not self.tables:
            self.parse_schema()

    def __getitem__(self, table):
        return self.tables[table]

    def name_check(self, parent_key, key):
        table_name = generate_table_name(self.current_table.name, parent_key, key)
        self.names_counter[table_name] += 1
        if self.names_counter[table_name] > 1:
            key = key[:4] + str(self.names_counter[table_name] - 1)
        return key

    def init_tables(self, tables, is_combined=False):
        """Initialize root tables with default fields"""
        for name, path in tables.items():
            table = Table(name, path, is_root=True, is_combined=is_combined, parent="")
            self.tables[name] = table

    def parse_schema(self):
        """Extract all available information from schema"""
        if isinstance(self.schema, (str, Path)):
            self.schema = resolve_file_uri(self.schema)
        self.schema = jsonref.JsonRef.replace_refs(self.schema)
        self.init_tables(self.root_tables)
        if self.combined_tables:
            self.init_tables(self.combined_tables, is_combined=True)
        separator = self.header_separator
        to_analyze = deque([("", "", {}, self.schema)])

        # TODO: check if recursion is better for field ordering
        while to_analyze:
            path, parent_key, parent, prop = to_analyze.pop()
            if prop.get("deprecated"):
                continue
            # TODO: handle oneOf anyOf allOf
            properties = prop.get("properties", {})
            if properties:
                for key, item in properties.items():
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
                            self.current_table.add_column(pointer, typeset, _(pointer, self.language))
                    else:
                        if self.current_table.is_combined:
                            pointer = separator + separator.join((parent_key, key))
                        self.current_table.add_column(pointer, typeset, _(pointer, self.language))
            else:
                # TODO: not sure what to do here
                continue

    def _add_table(self, table, pointer):
        self.tables[table.name] = table
        self.current_table = table
        self.get_table.cache_clear()

    @lru_cache(maxsize=None)
    def get_table(self, path):
        """Get best matching table for `path`

        :param path: Path to find corresponding table
        :return: Best matching table
        """
        candidates = get_matching_tables(self.tables, path)
        if not candidates:
            return
        return candidates[0]

    def add_preview_row(self, ocid, item_id, row_id, parent_id, parent_table=""):
        """Append empty row to previews

        Important to do because all preview items is set using -1 index to access current row

        :param ocid: Row ocid
        :param item_id: Current object id
        :param row_id: Unique row id
        :param parent_id: Parent object id
        :param parent_table: Parent table name
        """
        defaults = {"ocid": ocid, "rowID": row_id, "parentID": parent_id, "id": item_id}
        if parent_table:
            defaults["parentTable"] = parent_table
        self.current_table.preview_rows.append(defaults)
        self.current_table.preview_rows_combined.append(defaults)

    def process_items(self, releases, with_preview=True):
        """Analyze releases

        Iterate over every item in provided list to
        calculate metrics and optionally generate preview for combined and split version of the table

        :param releases: Iterator of items to analyze
        :param with_preview: If set to True generates previews for each table
        """
        separator = self.header_separator
        for count, release in enumerate(releases):
            to_analyze = deque([("", "", "", {}, release)])
            ocid = release["ocid"]
            top_level_id = release["id"]

            while to_analyze:
                abs_path, path, parent_key, parent, record = to_analyze.pop()
                for key, item in record.items():
                    pointer = separator.join([path, key])
                    self.current_table = self.get_table(pointer)
                    if not self.current_table:
                        continue
                    item_type = self.current_table.types.get(pointer)
                    if pointer in self.current_table.path:
                        # strict match like /parties, /tender
                        row_id = generate_row_id(ocid, record.get("id", ""), parent_key, top_level_id)
                        c = item if isinstance(item, list) else [item]
                        for _nop in c:
                            self.current_table.inc()
                            if with_preview and count < PREVIEW_ROWS:
                                parent_table = not self.current_table.is_root and parent_key
                                self.add_preview_row(ocid, record.get("id"), row_id, parent.get("id"), parent_table)

                    # TODO: this validation should probably be smarter with arrays
                    if item_type and item_type != JOINABLE and not validate_type(item_type, item):
                        LOGGER.error("Mismatched type on %s expected %s" % (pointer, item_type))
                        continue

                    if isinstance(item, dict):
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
                            LOGGER.debug(_("Detected additional column: %s in %s table") % (abs_pointer, root.name))
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
                                self._add_table(add_child_table(self.current_table, pointer, parent_key, key), pointer)
                                self.add_preview_row(ocid, record.get("id"), row_id, parent.get("id"), parent_table)

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
                            LOGGER.debug(
                                _("Path %s is targeted to combined table %s") % (pointer, self.current_table.name)
                            )
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
                            self.current_table.set_preview_path(abs_pointer, pointer, item, self.table_threshold)
            yield count
        self.total_items = count

    def dump(self, path):
        """Dump table objects to file system"""
        try:
            with open(path, "wb") as fd:
                pickle.dump(self, fd)
        except (OSError, IOError) as e:
            LOGGER.error(_("Failed to dump DataPreprocessor to file. Error: {}").format(e))

    @classmethod
    def restore(_cls, path):
        """Restore DataPreprocessor from file

        :param path: Full path to file
        """
        try:
            with open(path, "rb") as fd:
                return pickle.load(fd)
        except (TypeError, pickle.UnpicklingError):
            LOGGER.error(_("Invalid pickle file. Can't restore."))

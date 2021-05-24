import locale
import logging
from collections import deque
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

        self._lookup_cache = {}
        self._table_by_path = {}
        self.language = language
        if not self.tables:
            self.parse_schema()

    def __getitem__(self, table):
        return self.tables[table]

    def init_tables(self, tables, is_combined=False):
        """Initialize root tables with default fields"""
        for name, path in tables.items():
            table = Table(name, path, is_root=True, is_combined=is_combined, parent="")
            self.tables[name] = table
            for p in path:
                self._table_by_path[p] = table

    def parse_schema(self):
        """Extract all available information from schema"""
        if isinstance(self.schema, str):
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
        for cache in self._lookup_cache, self._table_by_path:
            cache[pointer] = table

    def get_table(self, path):
        """Get best matching table for `path`

        :param path: Path to find corresponding table
        :return: Best matching table
        """
        if path in self._lookup_cache:
            return self._lookup_cache[path]
        candidates = get_matching_tables(self.tables, path)
        if not candidates:
            return
        table = candidates[0]
        self._lookup_cache[path] = table
        return table

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
        self.current_table.preview_rows_combined.append(
            {"ocid": ocid, "rowID": row_id, "parentID": parent_id, "id": item_id}
        )

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
                table = self._table_by_path.get(path)
                if table:
                    # TODO: fields without ids??
                    row_id = generate_row_id(ocid, record.get("id", ""), parent_key, top_level_id)
                    table.inc()

                    for col_name in DEFAULT_FIELDS:
                        table.inc_column(col_name, col_name)

                    self.current_table = table
                    if with_preview and count < PREVIEW_ROWS:
                        self.add_preview_row(ocid, record.get("id"), row_id, parent.get("id"), parent_key)
                for key, item in record.items():
                    pointer = separator.join([path, key])
                    self.current_table = self.get_table(pointer)
                    if not self.current_table:
                        continue
                    item_type = self.current_table.types.get(pointer)

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
                    elif isinstance(item, list):
                        abs_pointer = separator.join([abs_path, key])
                        if not isinstance(item[0], dict) and not item_type:
                            LOGGER.debug(
                                _("Detected additional column: {} in {} table").format(abs_pointer, root.name)
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
                                LOGGER.debug(_("Detected additional table: {}").format(pointer))
                                self.current_table.types[pointer] = ["array"]
                                # TODO: do we need to mark this table as additional
                                self._add_table(add_child_table(self.current_table, pointer, parent_key, key), pointer)

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
                                    if with_preview and count < PREVIEW_ROWS:
                                        if pointer in self.current_table.path:
                                            self.add_preview_row(
                                                ocid,
                                                value.get("id"),
                                                row_id,
                                                parent.get("id"),
                                                parent_key,
                                            )
                                    abs_pointer = separator.join([abs_path, key, str(i)])
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
                        root = get_root(self.current_table)
                        abs_pointer = separator.join((abs_path, key))
                        if self.current_table.is_combined:
                            LOGGER.debug(
                                _("Path %s is targeted to combined table %s") % (pointer, self.current_table.name)
                            )
                            pointer = separator + separator.join((parent_key, key))
                            abs_pointer = pointer
                        if abs_pointer not in root.combined_columns:
                            LOGGER.debug(
                                _("Detected additional column: {} in {} table").format(abs_pointer, root.name)
                            )
                            self.current_table.add_column(
                                pointer,
                                PYTHON_TO_JSON_TYPE.get(type(item).__name__, "N/A"),
                                _(pointer, self.language),
                                additional=True,
                                abs_path=abs_pointer,
                            )
                        self.current_table.inc_column(abs_pointer, pointer)
                        if with_preview and count < PREVIEW_ROWS:
                            self.current_table.set_preview_path(abs_pointer, pointer, item, self.table_threshold)
            yield count
        self.total_items = count

    def dump(self):
        """Dump table objects to python dictionary"""
        return {
            "schema": self.schema,
            "root_tables": self.root_tables,
            "combined_tables": self.combined_tables,
            "header_separator": self.header_separator,
            "tables": {name: table.dump() for name, table in self.tables.items()},
            "table_threshold": self.table_threshold,
            "total_items": self.total_items,
        }

    @classmethod
    def restore(cls, data):
        """Restore DataPreprocessor from existing data

        :param data: Data to restore from
        """
        try:
            spec = {
                "schema": data["schema"],
                "root_tables": data["root_tables"],
                "combined_tables": data["combined_tables"],
                "header_separator": data["header_separator"],
                "table_threshold": data["table_threshold"],
                "total_items": data["total_items"],
            }
        except KeyError as e:
            LOGGER.error(_("Failed to restore from malformed data. Missing {} attribute").format(e))
            raise ValueError(_("Unable to restore, invalid input data"))
        tables = {name: Table(**table) for name, table in data["tables"].items() if table["is_root"]}

        for name, table in data["tables"].items():
            if not table["is_root"]:
                parent = tables[table["parent"]]
                table["parent"] = parent
                tables[name] = Table(**table)
        spec["tables"] = tables
        return cls(**spec)

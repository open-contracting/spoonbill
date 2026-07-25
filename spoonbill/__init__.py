import logging
from operator import attrgetter
from pathlib import Path

import jsonref
from ocdskit.util import detect_format

from spoonbill.common import (
    COMBINED_TABLES,
    CURRENT_SCHEMA_TAG,
    DEFAULT_SCHEMA_URL,
    ROOT_TABLES,
    TABLE_THRESHOLD,
)
from spoonbill.i18n import LOCALE, _
from spoonbill.utils import get_reader

LOGGER = logging.getLogger("spoonbill")


class FileAnalyzer:
    """Main utility for analyzing files
    :param workdir: Working directory
    :param root_tables: Path configuration which should become root tables
    :param combined_tables: Path configuration for tables with multiple sources
    """

    def __init__(
        self,
        workdir,
        root_tables=ROOT_TABLES,
        combined_tables=COMBINED_TABLES,
        pkg_type="releases",
        language=LOCALE,
        table_threshold=TABLE_THRESHOLD,
    ):
        self.workdir = Path(workdir)
        self.root_tables = root_tables
        self.combined_tables = combined_tables
        self.pkg_type = pkg_type
        self.language = language
        self.table_threshold = table_threshold

        self.multiple_values = False
        self.spec = None
        self.order = None

    def analyze_file(self, filenames, with_preview=True):
        """Analyze provided file
        :param filename: Input filename
        :param with_preview: Generate preview during analysis
        """
        if not isinstance(filenames, list):
            filenames = [filenames]

        path = self.workdir / filenames[0]
        (
            input_format,
            _is_concatenated,
            _is_array,
        ) = detect_format(path=path, reader=get_reader(path))

        LOGGER.info(_("Input file is {}").format(input_format))
        self.multiple_values = _is_concatenated
        self.parse_schema(input_format, self.schema)

        if self.spec is None:
            self.spec = DataPreprocessor(
                self.schema,
                self.root_tables,
                combined_tables=self.combined_tables,
                language=self.language,
                table_threshold=self.table_threshold,
                multiple_values=self.multiple_values,
                pkg_type=self.pkg_type,
            )

        for filename in filenames:
            path = self.workdir / filename
            reader = get_reader(path)
            with reader(path, "rb") as fd:
                items = iter_file(fd, self.pkg_type, multiple_values=self.multiple_values)
                for count in self.spec.process_items(items):
                    yield fd.tell(), count
        self.sort_tables()

    def dump_to_file(self, filename):
        """Save analyzed information to file
        :param filename: Output filename in working directory
        """
        path = self.workdir / filename
        self.spec.dump(path)

    def parse_schema(self, input_format, schema=None):
        if schema:
            schema = resolve_file_uri(schema)

        if "release" in input_format:
            pkg_type = "releases"
            getter = attrgetter("release_package_schema")
        else:
            pkg_type = "records"
            getter = attrgetter("record_package_schema")

        url = DEFAULT_SCHEMA_URL[pkg_type][self.language]

        if not schema:
            LOGGER.info(_("No schema provided, using version {}").format(CURRENT_SCHEMA_TAG))
            profile = ProfileBuilder(CURRENT_SCHEMA_TAG, {}, schema_base_url=url)
            schema = getter(profile)()

        title = schema.get("title", "").lower()
        if not title:
            raise ValueError(_("Incomplete schema, please make sure your data is correct"))

        if "package" in title:
            # TODO: is is a good way to get release/record schema
            schema = jsonref.JsonRef.replace_refs(schema)
            schema = schema["properties"][pkg_type]["items"]

        self.schema = schema
        self.pkg_type = pkg_type

    def sort_tables(self):
        """
        Sort tables according to order of arrays in schema
        :return:
        """
        self.order = get_order(self.spec.schema["properties"].keys())

        out_schema_tables = {
            name: table for name, table in self.spec.tables.items() if name.split("_")[0] not in self.order
        }
        within_schema_tables = {
            name: table for name, table in self.spec.tables.items() if name.split("_")[0] in self.order
        }

        sorted_tables = dict(
            sorted(
                within_schema_tables.items(),
                key=lambda sheet: self.order.index(sheet[0].split("_")[0])
                if sheet[0].split("_")[0] in self.order
                else -1,
            )
        )

        self.spec.tables = {**sorted_tables, **out_schema_tables}

import logging
import pickle
from pathlib import Path

from spoonbill.common import COMBINED_TABLES, ROOT_TABLES, TABLE_THRESHOLD
from spoonbill.flatten import Flattener
from spoonbill.i18n import LOCALE, _
from spoonbill.stats import DataPreprocessor
from spoonbill.utils import iter_file
from spoonbill.writers import CSVWriter, XlsxWriter

LOGGER = logging.getLogger("spoonbill")


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
        schema=None,
        state_file=None,
        root_tables=ROOT_TABLES,
        combined_tables=COMBINED_TABLES,
        root_key="releases",
        language=LOCALE,
        table_threshold=TABLE_THRESHOLD,
    ):
        self.workdir = Path(workdir)
        if state_file:
            self.spec = DataPreprocessor.restore(state_file)
        else:
            self.spec = DataPreprocessor(
                schema,
                root_tables,
                combined_tables=combined_tables,
                language=language,
                table_threshold=table_threshold,
            )
        self.root_key = root_key

    def analyze_file(self, filename, with_preview=True):
        """Analyze provided file
        :param filename: Input filename
        :param with_preview: Generate preview during analysis
        """
        path = self.workdir / filename
        with open(path, "rb") as fd:
            items = iter_file(fd, self.root_key)
            for count in self.spec.process_items(items, with_preview=with_preview):
                yield fd.tell(), count

    def dump_to_file(self, filename):
        """Save analyzed information to file

        :param filename: Output filename in working directory
        """
        path = self.workdir / filename
        self.spec.dump(path)


class FileFlattener:
    """Main utility for flattening files

    :param workdir: Working directory
    :param options: Flattening configuration
    :param tables: Analyzed tables data
    :param root_key: Field name to access records
    :param csv: If True generate cvs files
    :param xlsx: Generate combined xlsx table
    """

    def __init__(self, workdir, options, tables, root_key="releases", csv=None, xlsx="result.xlsx", language=LOCALE):
        self.flattener = Flattener(options, tables, language=language)
        self.workdir = Path(workdir)
        # TODO: detect package, where?
        self.root_key = root_key
        self.writers = []
        self.csv = csv
        self.xlsx = xlsx

    def _flatten(self, filename, writers):
        path = self.workdir / filename
        with open(path, "rb") as fd:
            items = iter_file(fd, self.root_key)
            for count, data in self.flattener.flatten(items):
                for table, rows in data.items():
                    for row in rows:
                        for wr in writers:
                            wr.writerow(table, row)
                yield count

    def flatten_file(self, filename):
        """Flatten file

        :param filename: Input filename in working directory
        """
        workdir = self.workdir
        if isinstance(self.csv, Path):
            workdir = self.csv
        if not self.xlsx and self.csv:
            with CSVWriter(workdir, self.flattener.tables, self.flattener.options) as writer:
                for count in self._flatten(filename, [writer]):
                    yield count
        if self.xlsx and not self.csv:
            with XlsxWriter(self.workdir, self.flattener.tables, self.flattener.options, filename=self.xlsx) as writer:
                for count in self._flatten(filename, [writer]):
                    yield count

        if self.xlsx and self.csv:
            with XlsxWriter(
                self.workdir, self.flattener.tables, self.flattener.options, filename=self.xlsx
            ) as xlsx, CSVWriter(workdir, self.flattener.tables, self.flattener.options) as csv:
                for count in self._flatten(filename, [xlsx, csv]):
                    yield count


__all__ = ["FileFlattener", "FileAnalyzer"]

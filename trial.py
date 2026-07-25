import csv
import dataclasses
import os.path
import queue
import shutil
import tempfile
import threading
from collections import OrderedDict
from typing import List, Mapping, Sequence

import flatterer
import ijson
import simplejson


@dataclasses.dataclass
class Column:
    id: str
    hits: int = 0


@dataclasses.dataclass
class Table:
    name: str
    parent: object = dataclasses.field(default_factory=dict)
    # `parent` is a Table object, but dataclasses don't play well with recursion.
    additional_columns: Mapping[str, Column] = dataclasses.field(default_factory=OrderedDict)
    arrays: Mapping[str, int] = dataclasses.field(default_factory=dict)
    child_tables: list[str] = dataclasses.field(default_factory=list)
    columns: Mapping[str, Column] = dataclasses.field(default_factory=OrderedDict)
    combined_columns: Mapping[str, Column] = dataclasses.field(default_factory=OrderedDict)
    preview_rows: Sequence[dict] = dataclasses.field(default_factory=list)
    preview_rows_combined: Sequence[dict] = dataclasses.field(default_factory=list)
    splitted: bool = False
    titles: Mapping[str, str] = dataclasses.field(default_factory=dict)
    total_rows: int = 0


def read(*components: list[str]) -> list[Dict[str, Any]]:
    """
    Returns the rows from the CSV file at the given path.

    :param components: the path components
    """
    with open(os.path.join(*components)) as f:
        return list(csv.DictReader(f))


class DataPreprocessor:
    def __init__(self, filename, report=print):
        self.filename = filename
        self.report = report

        self.total_items = 0
        self.fields = []
        self.tables = []
        self.data = {}

    # https://stackoverflow.com/questions/28057445/python-threading-multiline-progress-report
    def analyze(self):
        """
        Runs the analysis of the file, using a thread for each of the "analyzer" and "reporter".
        """
        q = queue.Queue()

        analyzer = threading.Thread(target=self.analyzer, args=(q,))
        reporter = threading.Thread(target=self.reporter, args=(q,))

        threads = [analyzer, reporter]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # TODO move main() logic here

    # Using flatterer.flatten() incurs overhead (like pandas).
    def analyzer(self, q):
        """
        Calls and reads the output of the flatterer library.

        See the :meth:`~spoonbill.FileAnalyzer.generator` method for the input provided to the flatterer library.

        :param q: the queue for exchanging information between threads
        """
        output_dir = tempfile.mkdtemp(prefix="spoonbill-")

        try:
            flatterer.iterator_flatten_rs(
                self.generator(q),
                output_dir,
                csv=True,
                xlsx=False,
                sqlite=False,
                main_table_name="tender",  # default 'main'
                emit_path=[],
                force=True,  # default if output_dir is a temporary directory
                fields="",
                only_fields=False,
                tables="",
                only_tables=False,
                inline_one_to_one=True,  # default False
                schema="",
                table_prefix="",
                path_separator="_",
                schema_titles="",
                sqlite_path="",
                preview=5,  # default 0
                log_error=False,
            )

            self.fields = read(output_dir, "fields.csv")  # table_name, field_name, field_type, field_title, count
            self.tables = read(output_dir, "tables.csv")  # table_name, table_title
            self.data = {row["table_name"]: read(output_dir, "csv", f"{row['table_name']}.csv") for row in self.tables}
            # TODO test with empty input
            self.total_items = self.data["tender"][0]["count"]
        finally:
            shutil.rmtree(output_dir)

    def generator(self, q):
        """
        Yields each JSON text from the file as bytes.

        Enqueues the current position in the file and the index of the JSON text.

        See the :meth:`~spoonbill.FileAnalyzer.get_prefix` method for more about the JSON texts.

        :param q: the queue for exchanging information between threads
        """
        with open(self.filename, "rb") as f:
            for count, item in enumerate(ijson.items(f, self.get_prefix(), multiple_values=True)):
                q.put((f.tell(), count))
                yield simplejson.dumps(item, use_decimal=True).encode()
            q.put(())

    def get_prefix(self):
        """
        Returns the ijson prefix for the JSON texts, preferring compiled releases to individual releases.

        If the topmost texts are concatenated or in an array, then all texts are assumed to follow the same format.

        If no releases are found, the topmost texts are assumed to be releases.
        """
        # Based on https://ocdskit.readthedocs.io/en/latest/api/util.html#ocdskit.util.detect_format
        with open(self.filename, "rb") as f:
            events = ijson.parse(f, multiple_values=True)
            prefix, event, value = next(events)

            if event == "start_array":
                # Consume "start_map" if object array.
                next(events)
                prepend = "item."
                item_prefix = "item"
            else:
                prepend = ""
                item_prefix = ""

            # Prefer compiled releases to individual releases.
            prefixes = {
                f"{prepend}records.item.compiledRelease": True,  # record package
                f"{prepend}records.item.releases.item": False,  # record package
                f"{prepend}compiledRelease": True,  # record
                f"{prepend}releases.item": False,  # release package, record
            }

            return_value = item_prefix

            for prefix, event, value in events:
                if prefix in prefixes:
                    if prefixes[prefix]:
                        return prefix
                    return_value = prefix
                if prefix == item_prefix and event not in (
                    "end_array",
                    "end_map",
                    "map_key",
                ):  # release
                    return return_value

    def reporter(self, q):
        """
        Dequeues messages, and calls the ``report`` function with each message.

        :param q: the queue for exchanging information between threads
        """
        while message := q.get():
            self.report(message)


def main():
    analyzer = Analyzer("CY.jsonl")
    analyzer.analyze()

    tables = {}
    table_names = set()
    current_table = None
    for field in analyzer.fields:
        if not current_table or field["table_name"] != current_table.name:
            name = field["table_name"]

            print(current_table)

            rows = analyzer.data[name]
            current_table = Table(
                name=name,
                parent="",
                preview_rows=rows,
                preview_rows_combined=rows,  # TODO determine the difference
                splitted=True,
            )

            # Find the longest common table name.
            for i in range(len(name) - 1, -1, -1):
                if name[i] == "_" and name[:i] in table_names:
                    current_table.parent = tables[name[:i]]
                    current_table.parent.child_tables.append(name)
                    break

            tables[name] = current_table
            table_names.add(name)

        if field["field_name"] == "_link":
            current_table.total_rows = field["count"]
        else:
            pass


main()

"""
TODO

make Analyzer conform to DataPreprocessor's API

compare running time with threading (no-op reporter) and without threading, to see if GIL gets in the way

finish filling in Table attributes:
- columns: create Column objects using fields table
- combined_columns: set same as columns
- additional_columns: leave empty?
- arrays: set value to 99 when setting child_tables
- titles: need to investigate logic more (how arrays are used)
"""


"""
spec dataclass
✓ .name
✓ .parent
✓ .child_tables
- .arrays maximum items in each array is not tracked by flatterer, set to 99?
  {'/parties/additionalIdentifiers': 4}
- .additional_columns can be calculated by comparing field names to schema, ordered dict like:
  {'/tender/lots/id': Column(id='/tender/lots/id', path='/tender/lots/id', title='/tender/lots/id', type=[None], hits=16881, header=[])}
- .columns like:
  {'ocid': Column(id='ocid', path='ocid', title='string', type='ocid', hits=38863, header=[]}
- .combined_columns adds columns like:
    '/parties/additionalIdentifiers/0/id',
    '/parties/additionalIdentifiers/0/scheme',
    '/parties/additionalIdentifiers/1/id',
    '/parties/additionalIdentifiers/1/scheme',
    '/parties/additionalIdentifiers/2/id'
    '/parties/additionalIdentifiers/2/scheme',
    '/parties/additionalIdentifiers/3/id',
    '/parties/additionalIdentifiers/3/scheme',
✓ .preview_rows
~ .preview_rows_combined adds parentID for CY.jsonl
✓ .splitted
- .titles combine with existing logic, looks like:
  {
    '/buyer/contactPoint/email': [
      ['buyer', 'title'],
      ['buyer', 'properties', 'contactPoint', 'title'],
      ['buyer', 'properties', 'contactPoint', 'properties', 'email', 'title']
    ]
  }
✓ .total_rows

    :param name: Table name
           str
    :param parent: Parent table, None if this table is root table
           object = dataclasses.field(default_factory=dict)

    :param additional_columns: Columns identified in dataset but not in schema
           Mapping[str, Column] = dataclasses.field(default_factory=OrderedDict)
    :param columns: Columns extracted from schema for split version of this table
           Mapping[str, Column] = dataclasses.field(default_factory=OrderedDict)
    :param combined_columns: Columns extracted from schema for unsplit version of this table
           Mapping[str, Column] = dataclasses.field(default_factory=OrderedDict)

    :param arrays: Table array columns and maximum items (not the total count) in each array
           Mapping[str, int] = dataclasses.field(default_factory=dict)
    :param child_tables: List of possible child tables
           List[str] = dataclasses.field(default_factory=list)
    :param titles: All human-friendly column titles, extracted from the schema
           Mapping[str, str] = dataclasses.field(default_factory=dict)

    :param splitted: This table should be splitted
           bool = False
    :param total_rows: Total available rows in this table
           int = 0

    :param preview_rows: Generated preview for split version of this table
           Sequence[dict] = dataclasses.field(default_factory=list)
    :param preview_rows_combined: Generated preview for unsplit version of this table
           Sequence[dict] = dataclasses.field(default_factory=list)

Column:
- .id str The JSON path without indexes
- .hits int The number of times the column contains data during analysis
"""

"""
from spoonbill import FileAnalyzer
analyzer = FileAnalyzer('../spoonbill-ng', language='en')
for bytes_read, count in analyzer.analyze_file('CY.jsonl'):
    pass

analyzer.spec.tables['parties']
"""

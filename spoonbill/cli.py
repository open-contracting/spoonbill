"""cli.py - Command line interface related routines"""
import logging
import pathlib

import click
from ocdsextensionregistry import ProfileBuilder
from ocdskit.util import detect_format

from spoonbill.common import COMBINED_TABLES, ROOT_TABLES
from spoonbill.flatten import FileAnalyzer, FileFlattener, FlattenOptions
from spoonbill.i18n import _
from spoonbill.stats import DataPreprocessor
from spoonbill.utils import resolve_file_uri

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("spoonbill")
CURRENT_SCHEMA_TAG = "1__1__5"


class CommaSeparated(click.ParamType):
    """Click option type to convert comma separated string into list"""

    name = "comma"

    def convert(self, value, param, ctx):  # noqa
        if not value:
            return []
        return [v.lower() for v in value.split(",")]


def get_selected_tables(base, selection):
    for name in selection:
        if name not in base:
            msg = _("Wrong selection, table '{}' does not exist").format(name)
            raise click.BadParameter(msg)
    return {name: tab for name, tab in base.items() if name in selection}


def should_split(spec, table_name, split, threshold=5):
    table = spec.tables[table_name]
    if table_name in split:
        return True
    return any((i > threshold for i in table.arrays.values()))


# TODO: we could provide two commands: flatten and analyze
# TODO: generated state-file + overridden options could lead to unexpected bugs, raise error?


@click.command(help=_("CLI tool to flatten OCDS datasets"))
@click.option("--schema", help=_("Schema file uri"), type=str)
@click.option("--selection", help=_("List of tables to extract"), type=CommaSeparated())
@click.option(
    "--split",
    help=_("List of tables to split into multiple sheets"),
    type=CommaSeparated(),
    default="",
)
@click.option(
    "--state-file",
    help=_("Uri to previously generated state file"),
    type=click.Path(exists=True),
)
@click.option("--xlsx", help=_("Path to result xlsx file"), default=True, is_flag=True)
@click.option(
    "--csv",
    help=_("Path to directory for output csv files"),
    default=True,
    is_flag=True,
)
@click.option(
    "--unnest",
    help=_("Output column to parent table"),
    type=CommaSeparated(),
    default="",
)
@click.option("--combine", help=_("Combine same objects to single table"), type=CommaSeparated())
@click.option("--only", help=_("Specify which fields to output"), type=CommaSeparated())
@click.option(
    "--reify",
    help=_("For array, use one field value as the column name and another field value as the cell value"),
)
@click.option(
    "--repeat",
    help=_("Repeat a column from a parent sheet onto child tables"),
    type=CommaSeparated(),
)
@click.option(
    "--count",
    help=_("For each array field, add a count column to the parent table"),
    is_flag=True,
)
@click.option(
    "--human",
    help=_("Use the schema's title properties for column headings"),
    is_flag=True,
)
@click.argument("filename", type=click.Path(exists=True))
def cli(
    filename,
    schema,
    selection,
    split,
    state_file,
    xlsx,
    csv,
    unnest,
    combine,
    only,
    reify,
    repeat,
    count,
    human,
):
    """Spoonbill cli entry point"""
    # TODO: decect_format is reading file from disk, may by slow
    (
        input_format,
        _is_concatenated,
        _is_array,
    ) = detect_format(filename)
    is_package = "package" in input_format
    if not is_package:
        # TODO: fix this
        click.echo("Single releases are not supported by now")
        import sys

        sys.exit(1)
    if schema:
        schema = resolve_file_uri(schema)
    if "release" in input_format:
        root_key = "releases"
        if not schema:
            profile = ProfileBuilder(CURRENT_SCHEMA_TAG, {})
            schema = profile.release_package_schema()
    else:
        root_key = "records"
        if not schema:
            profile = ProfileBuilder(CURRENT_SCHEMA_TAG, {})
            schema = profile.record_package_schema()
    if reify:
        raise NotImplementedError(_("We are sorry but reify option is currently disabled"))
    title = schema.get("title", "").lower()
    if not title:
        raise Exception(_("Incomplete schema, please make sure your data is correct"))
    if "package" in title:
        # TODO: is is a good way to get release/record schema
        schema = schema["properties"][root_key]["items"]

    path = pathlib.Path(filename)
    workdir = path.parent
    filename = path.name
    selection = selection or ROOT_TABLES.keys()
    combine = combine or COMBINED_TABLES.keys()
    root_tables = get_selected_tables(ROOT_TABLES, selection)
    combined_tables = get_selected_tables(COMBINED_TABLES, combine)

    if state_file:
        analyzer = FileAnalyzer(workdir, state_file=state_file)
    else:
        analyzer = FileAnalyzer(
            workdir,
            schema=schema,
            root_key=root_key,
            root_tables=root_tables,
            combined_tables=combined_tables,
        )
        analyzer.analyze_file(filename, with_preview=False)
        analyzer.dump_to_file(f"{filename}.analyzed.json")

    options = {"selection": {}, "count": count}
    for name in selection:
        table = analyzer.spec[name]
        if table.total_rows == 0:
            LOGGER.warning(_("Ignoring empty table {}").format(name))
            continue
        unnest = [col for col in unnest if col in table]
        options["selection"][name] = {
            "split": should_split(analyzer.spec, name, split),
            "pretty_headers": human,
            "unnest": unnest,
        }

    options = FlattenOptions(**options)
    flattener = FileFlattener(workdir, options, analyzer.spec.tables, root_key=root_key, csv=csv, xlsx=xlsx)
    flattener.flatten_file(filename)

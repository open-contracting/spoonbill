"""cli.py - Command line interface related routines"""
import logging
import os
import pathlib
from itertools import chain

import click
import click_logging
from ocdsextensionregistry import ProfileBuilder
from ocdskit.util import detect_format

from spoonbill import FileAnalyzer, FileFlattener
from spoonbill.common import COMBINED_TABLES, ROOT_TABLES, TABLE_THRESHOLD
from spoonbill.flatten import FlattenOptions
from spoonbill.i18n import LOCALE, _
from spoonbill.utils import read_lines, resolve_file_uri

LOGGER = logging.getLogger("spoonbill")
click_logging.basic_config(LOGGER)


CURRENT_SCHEMA_TAG = "1__1__5"
ANALYZED_LABEL = _("  Processed {} objects")
FLATTENED_LABEL = _("  Flattened {} objects")
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class CommaSeparated(click.ParamType):
    """Click option type to convert comma separated string into list"""

    name = "comma"

    def convert(self, value, param, ctx):  # noqa
        if not value:
            return []
        return [v for v in value.split(",")]


def read_option_file(option, option_file):
    if option_file:
        option = read_lines(option_file)
    return option


def get_selected_tables(base, selection):
    for name in selection:
        if name not in base:
            msg = _("Wrong selection, table '{}' does not exist").format(name)
            raise click.BadParameter(msg)
    return {name: tab for name, tab in base.items() if name in selection}


# TODO: we could provide two commands: flatten and analyze
# TODO: generated state-file + schema how to validate


@click.command(context_settings=CONTEXT_SETTINGS, help=_("CLI tool to flatten OCDS datasets"))
@click.option(
    "--schema",
    help=_(
        "Schema file uri. This option is used to provide OCDS schema which spoonbill requires to analyze dataset. URI might be file path or HTTP link. Spoonbill will use default schema tag if not provided (requires internet connection)"
    ),
    type=str,
)
@click.option("--selection", type=CommaSeparated())
@click.option(
    "--threshold",
    help=_("Maximum number of elements in array before its spitted into table"),
    type=int,
    default=TABLE_THRESHOLD,
)
@click.option(
    "--state-file",
    help=_("Uri to previously generated state file"),
    type=click.Path(exists=True),
)
@click.option("--xlsx", help=_("Path to result xlsx file"), type=click.Path(), default="result.xlsx")
@click.option("--csv", help=_("Path to directory for output csv files"), type=click.Path(), required=False)
@click.option("--combine", help=_("Combine same objects to single table"), type=CommaSeparated())
@click.option("--exclude", help=_("Exclude tables from export"), type=CommaSeparated(), default="")
@click.option(
    "--unnest",
    help=_("Extract columns form child tables to parent table"),
    type=CommaSeparated(),
    default="",
)
@click.option(
    "--unnest-file",
    help=_("Same as --unnest, but read columns from a file"),
    type=click.Path(exists=True),
    required=False,
)
@click.option("--only", help=_("Specify which fields to output"), type=CommaSeparated(), default="")
@click.option(
    "--only-file",
    help=_("Same as --only, but read columns from a file"),
    type=click.Path(exists=True),
    required=False,
)
@click.option(
    "--repeat",
    help=_("Repeat a column from a parent sheet onto child tables"),
    type=CommaSeparated(),
    default="",
)
@click.option(
    "--repeat-file",
    help=_("Same as --repeat, but read columns from a file"),
    type=click.Path(exists=True),
    required=False,
)
@click.option(
    "--count", help=_("For each array field, add a count column to the parent table"), is_flag=True, default=False
)
@click.option(
    "--human",
    help=_("Use the schema's title properties for column headings"),
    is_flag=True,
)
@click.option(
    "--language",
    help=_("Language for headings"),
    default=LOCALE.split("_")[0],
    type=click.Choice(["en", "es"]),
)
@click_logging.simple_verbosity_option(LOGGER)
@click.argument("filename", type=click.Path(exists=True))
def cli(
    filename,
    schema,
    selection,
    threshold,
    state_file,
    xlsx,
    csv,
    combine,
    exclude,
    unnest,
    unnest_file,
    only,
    only_file,
    repeat,
    repeat_file,
    count,
    human,
    language,
):
    """Spoonbill cli entry point"""
    click.echo(_("Detecting input file format"))
    # TODO: handle line separated json
    # TODO: handle single release/record
    (
        input_format,
        _is_concatenated,
        _is_array,
    ) = detect_format(filename)
    if csv:
        csv = pathlib.Path(csv).resolve()
        if not csv.exists():
            raise click.BadParameter(_("Desired location {} does not exists").format(csv))
    if xlsx:
        xlsx = pathlib.Path(xlsx).resolve()
        if not xlsx.parent.exists():
            raise click.BadParameter(_("Desired location {} does not exists").format(xlsx.parent))
    click.echo(_("Input file is {}").format(click.style(input_format, fg="green")))
    is_package = "package" in input_format
    combine_choice = combine if combine else ""
    if not is_package:
        # TODO: fix this
        click.echo("Single releases are not supported by now")
        return
    if schema:
        schema = resolve_file_uri(schema)
    if "release" in input_format:
        root_key = "releases"
        if not schema:
            click.echo(_("No schema provided, using version {}").format(click.style(CURRENT_SCHEMA_TAG, fg="cyan")))
            profile = ProfileBuilder(CURRENT_SCHEMA_TAG, {})
            schema = profile.release_package_schema()
    else:
        root_key = "records"
        if not schema:
            click.echo(_("No schema provided, using version {}").format(click.style(CURRENT_SCHEMA_TAG, fg="cyan")))
            profile = ProfileBuilder(CURRENT_SCHEMA_TAG, {})
            schema = profile.record_package_schema()
    title = schema.get("title", "").lower()
    if not title:
        raise ValueError(_("Incomplete schema, please make sure your data is correct"))
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
        click.secho(_("Restoring from provided state file"), bold=True)
        analyzer = FileAnalyzer(workdir, state_file=state_file)
    else:
        click.secho(_("State file not supplied, going to analyze input file first"), bold=True)
        analyzer = FileAnalyzer(
            workdir,
            schema=schema,
            root_key=root_key,
            root_tables=root_tables,
            combined_tables=combined_tables,
            language=language,
            table_threshold=threshold,
        )
        click.echo(_("Analyze options:"))
        click.echo(_(" - table threshold => {}").format(click.style(str(threshold), fg="cyan")))
        click.echo(_(" - language        => {}").format(click.style(language, fg="cyan")))
        click.echo(_("Processing file: {}").format(click.style(str(path), fg="cyan")))
        total = path.stat().st_size
        progress = 0
        # Progress bar not showing with small files
        # https://github.com/pallets/click/pull/1296/files
        with click.progressbar(width=0, show_percent=True, show_pos=True, length=total) as bar:
            for read, number in analyzer.analyze_file(filename, with_preview=True):
                bar.label = ANALYZED_LABEL.format(click.style(str(number), fg="cyan"))
                bar.update(read - progress)
                progress = read
        click.secho(
            _("Done processing. Analyzed objects: {}").format(click.style(str(number + 1), fg="red")), fg="green"
        )
        state_file = pathlib.Path(f"{filename}.state")
        state_file_path = workdir / state_file
        click.echo(_("Dumping analyzed data to '{}'").format(click.style(str(state_file_path.absolute()), fg="cyan")))
        analyzer.dump_to_file(state_file)

    click.echo(_("Flattening file: {}").format(click.style(str(path), fg="cyan")))

    if unnest and unnest_file:
        raise click.UsageError(_("Conflicting options: unnest and unnest-file"))
    if repeat and repeat_file:
        raise click.UsageError(_("Conflicting options: repeat and repeat-file"))
    if only and only_file:
        raise click.UsageError(_("Conflicting options: only and only-file"))
    if exclude:
        click.echo(_("Ignoring tables (excluded by user): {}").format(click.style(",".join(exclude), fg="red")))

    options = {"selection": {}, "count": count, "exclude": exclude}
    unnest = read_option_file(unnest, unnest_file)
    repeat = read_option_file(repeat, repeat_file)
    only = read_option_file(only, only_file)

    for name in selection:
        table = analyzer.spec[name]
        if table.total_rows == 0:
            click.echo(_("Ignoring empty table {}").format(click.style(name, fg="red")))
            continue

        unnest = [col for col in unnest if col in table.combined_columns]
        if unnest:
            click.echo(
                _("Unnesting columns {} for table {}").format(
                    click.style(",".join(unnest), fg="cyan"), click.style(name, fg="cyan")
                )
            )

        only = [col for col in only if col in table]
        if only:
            click.echo(
                _("Using only columns {} for table {}").format(
                    click.style(",".join(only), fg="cyan"), click.style(name, fg="cyan")
                )
            )

        repeat = [col for col in repeat if col in table]
        if repeat:
            click.echo(
                _("Repeating columns {} in all child table of {}").format(
                    click.style(",".join(repeat), fg="cyan"), click.style(name, fg="cyan")
                )
            )

        options["selection"][name] = {
            "split": analyzer.spec[name].should_split,
            "pretty_headers": human,
            "unnest": unnest,
            "only": only,
            "repeat": repeat,
        }
    options = FlattenOptions(**options)
    flattener = FileFlattener(
        workdir,
        options,
        analyzer.spec.tables,
        root_key=root_key,
        csv=csv,
        xlsx=xlsx,
        language=language,
    )

    all_tables = chain([table for table in flattener.flattener.tables.keys()], combine_choice)

    click.echo(_("Going to export tables: {}").format(click.style(",".join(all_tables), fg="magenta")))

    click.echo(_("Processed tables:"))
    for table in flattener.flattener.tables.keys():
        message = _("{}: {} rows").format(table, flattener.flattener.tables[table].total_rows)
        if not flattener.flattener.tables[table].is_root:
            message = "└-----" + message
            click.echo(message)
        else:
            click.echo(message)
    click.echo(_("Flattening input file"))
    with click.progressbar(
        flattener.flatten_file(filename),
        length=analyzer.spec.total_items + 1,
        width=0,
        show_percent=True,
        show_pos=True,
    ) as bar:
        for count in bar:
            bar.label = FLATTENED_LABEL.format(click.style(str(count + 1), fg="cyan"))

    click.secho(_("Done flattening. Flattened objects: {}").format(click.style(str(count + 1), fg="red")), fg="green")

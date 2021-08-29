"""cli.py - Command line interface related routines"""
import logging
import pathlib

import click
import click_logging

from spoonbill import FileAnalyzer, FileFlattener
from spoonbill.common import COMBINED_TABLES, ROOT_TABLES, TABLE_THRESHOLD
from spoonbill.flatten import FlattenOptions
from spoonbill.i18n import LOCALE, _
from spoonbill.utils import read_lines

LOGGER = logging.getLogger("spoonbill")
click_logging.basic_config(LOGGER)


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


@click.command(context_settings=CONTEXT_SETTINGS, help=_("CLI tool to flatten OCDS files"))
@click.option(
    "--schema",
    help=_(
        "A JSON schema file URI. The URI can be a file path or an HTTP link. Spoonbill uses the schema to analyze the "
        "provided JSON file. Defaults to the OCDS 1.1.5 release schema (requires internet connection)"
    ),
    type=str,
)
@click.option(
    "--selection",
    type=CommaSeparated(),
    help=_(
        "A comma-separated list of initial tables to write. The available tables to select are: "
        "parties, planning, tenders, awards, contracts"
    ),
)
@click.option(
    "--threshold",
    help=_("The maximum number of elements in an array before it is split into a table"),
    type=int,
    default=TABLE_THRESHOLD,
    show_default=True,
)
@click.option(
    "--state-file",
    help=_("A file path URI to a previously generated state file. If not provided, a new state file is generated"),
    type=click.Path(exists=True),
)
@click.option(
    "--xlsx",
    help=_(
        "A file path to store the resulting xlsx file. Default to result.xlsx. "
        "Set to '' to disable the xlsx file generation"
    ),
    type=click.Path(),
    default="result.xlsx",
)
@click.option(
    "--csv",
    help=_("An existing directory path. If set also generates CSV files in the given directory. Disabled by default"),
    type=click.Path(),
    required=False,
)
@click.option(
    "--combine",
    help=_(
        "A comma-separated list of tables. Combines same OCDS object types from different locations "
        "(tender, awards, etc) into a single table. The available tables are: documents, milestones, and amendments"
    ),
    type=CommaSeparated(),
)
@click.option(
    "--exclude",
    help=_("A comma-separated list of tables to exclude from export. Disabled by default"),
    type=CommaSeparated(),
    default="",
)
@click.option(
    "--unnest",
    help=_(
        "A comma-separated list of column names to copy from child tables into their parent table. Disabled by default"
    ),
    type=CommaSeparated(),
    default="",
)
@click.option(
    "--unnest-file",
    help=_("A file path directory. Same as --unnest, but read column names from a file with one column per line"),
    type=click.Path(exists=True),
    required=False,
)
@click.option(
    "--only",
    help=_(
        "A comma-separated list of a subset of columns to output instead of all, in JSON path format, "
        "e.g. /parties/name. Defaults to all the available columns"
    ),
    type=CommaSeparated(),
    default="",
)
@click.option(
    "--only-file",
    help=_("A file path directory. Same as --only, but read the columns names from a file with one column per line"),
    type=click.Path(exists=True),
    required=False,
)
@click.option(
    "--repeat",
    help=_(
        "A comma-separated list of columns to repeat from a parent table into its child tables, in JSON path format,"
        "e.g. /parties/name. Disabled by default"
    ),
    type=CommaSeparated(),
    default="",
)
@click.option(
    "--repeat-file",
    help=_("A file path directory. Same as --repeat, but read the columns names from a file with one column per line"),
    type=click.Path(exists=True),
    required=False,
)
@click.option(
    "--count",
    help=_("For each array field, add a count column to its parent table. Disabled by default"),
    is_flag=True,
    default=False,
)
@click.option(
    "--human",
    help=_("Change the tables headings to human-readable format, using the schema's title properties"),
    is_flag=True,
)
@click.option(
    "--language",
    help=_("Use with --human, the language to use for the human-readable headings"),
    default=LOCALE.split("_")[0],
    show_default=True,
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
    if csv:
        csv = pathlib.Path(csv).resolve()
        if not csv.exists():
            raise click.BadParameter(_("Desired location {} does not exists").format(csv))
    if xlsx:
        xlsx = pathlib.Path(xlsx).resolve()
        if not xlsx.parent.exists():
            raise click.BadParameter(_("Desired location {} does not exists").format(xlsx.parent))

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
            root_tables=root_tables,
            combined_tables=combined_tables,
            language=language,
            table_threshold=threshold,
        )
        click.echo(_("Analyze options:"))
        for name, option in ("threshold", str(threshold)), ("language", language):
            click.echo(_(" - {:30} => {}").format(name, click.style(option, fg="cyan")))
        click.echo(_("Processing file: {}").format(click.style(str(path), fg="cyan")))
        total = path.stat().st_size
        progress = 0
        # Progress bar not showing with small files
        # https://github.com/pallets/click/pull/1296/files
        with click.progressbar(width=0, show_percent=True, show_pos=True, length=total) as bar:
            for read, number in analyzer.analyze_file(filename, with_preview=False):
                bar.label = ANALYZED_LABEL.format(click.style(str(number), fg="cyan"))
                bar.update(read - progress)
                progress = read
        click.secho(
            _("Done processing. Analyzed objects: {}").format(click.style(str(number + 1), fg="red")), fg="green"
        )
        if isinstance(filename, list):
            state_file = pathlib.Path(f"{filename[0]}.state")
        else:
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

    for name in list(selection) + list(combine):
        table = analyzer.spec[name]
        if table.total_rows == 0:
            click.echo(_("Ignoring empty table {}").format(click.style(name, fg="red")))
            continue
        options["selection"][name] = {
            "split": analyzer.spec[name].splitted,
            "pretty_headers": human,
        }
        if not analyzer.spec[name].is_combined:
            unnest_in_table = [col for col in unnest if col in table.combined_columns]
            if unnest_in_table:
                click.echo(
                    _("Unnesting columns {} for table {}").format(
                        click.style(",".join(unnest_in_table), fg="cyan"), click.style(name, fg="cyan")
                    )
                )

            only_in_table = [col for col in only if col in table]
            if only_in_table:
                click.echo(
                    _("Using only columns {} for table {}").format(
                        click.style(",".join(only_in_table), fg="cyan"), click.style(name, fg="cyan")
                    )
                )

            repeat_in_table = [col for col in repeat if col in table]
            if repeat_in_table:
                click.echo(
                    _("Repeating columns {} in all child table of {}").format(
                        click.style(",".join(repeat_in_table), fg="cyan"), click.style(name, fg="cyan")
                    )
                )
            options["selection"][name]["only"] = only_in_table
            options["selection"][name]["repeat"] = repeat_in_table
            options["selection"][name]["unnest"] = unnest_in_table

    options = FlattenOptions(**options)
    flattener = FileFlattener(
        workdir,
        options,
        analyzer,
        csv=csv,
        xlsx=xlsx,
        language=language,
    )

    click.echo(
        _("Going to export tables: {}").format(click.style(",".join(flattener.flattener.tables.keys()), fg="magenta"))
    )
    click.echo(_("Processed tables:"))
    for table_name, table in flattener.flattener.tables.items():
        msg = _(" - {:30} => {} rows") if table.is_root else _(" ---- {:27} => {} rows")
        message = msg.format(table_name, click.style(str(table.total_rows), fg="cyan"))
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

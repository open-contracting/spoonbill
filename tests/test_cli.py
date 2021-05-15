import pathlib
import shutil

from click.testing import CliRunner

from spoonbill.cli import cli

FILENAME = pathlib.Path("tests/data/ocds-sample-data.json").absolute()
SCHEMA = pathlib.Path("tests/data/ocds-simplified-schema.json").absolute()
ANALYZED = pathlib.Path("tests/data/analyzed.json").absolute()
ONLY = pathlib.Path("tests/data/only").absolute()
UNNEST = pathlib.Path("tests/data/unnest").absolute()


def test_no_filename():
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 2
    assert result.output.startswith("Usage")
    assert "Missing argument 'FILENAME'" in result.output


def test_default():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        result = runner.invoke(cli, ["data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Dumping analyzed data" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output


def test_with_selections():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        result = runner.invoke(cli, ["--selection", "tenders", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Dumping analyzed data" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output


def test_with_combine():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        result = runner.invoke(cli, ["--combine", "documents", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Dumping analyzed data" in result.output
        assert "Going to export tables: tenders,awards,contracts,planning,parties,documents" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output


def test_table_typo():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        for option in ("--selection", "--combine"):
            result = runner.invoke(cli, [option, "missing", "data.json"])
            assert result.exit_code == 2
            assert "Invalid value" in result.output
            assert "Wrong selection, table 'missing' does not exist"


def test_with_schema():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        shutil.copyfile(SCHEMA, "schema.json")
        result = runner.invoke(cli, ["--selection", "tenders", "--schema", "schema.json", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Dumping analyzed data" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output
        assert "Going to export tables: tenders" in result.output


def test_state_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        shutil.copyfile(ANALYZED, "analyzed.json")
        result = runner.invoke(cli, ["--state-file", "analyzed.json", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Restoring from provided state file" in result.output
        assert "Going to export tables: tenders,awards,contracts,planning,parties" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output


def test_only():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        shutil.copyfile(ANALYZED, "analyzed.json")
        result = runner.invoke(cli, ["--only", "/tender/title", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Using only columns" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output


def test_only_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        shutil.copyfile(ANALYZED, "analyzed.json")
        shutil.copyfile(ONLY, "only")
        result = runner.invoke(cli, ["--only-file", "only", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Using only columns" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output


def test_repleat():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        shutil.copyfile(ANALYZED, "analyzed.json")
        result = runner.invoke(cli, ["--repeat", "/tender/id", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Repeating columns /tender/id in all child table of tenders" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output


def test_repeat_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        shutil.copyfile(ANALYZED, "analyzed.json")
        shutil.copyfile(ONLY, "only")
        result = runner.invoke(cli, ["--repeat-file", "only", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Repeating columns /tender/id,/tender/title in all child table of tenders" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output


def test_unnest():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        shutil.copyfile(ANALYZED, "analyzed.json")
        result = runner.invoke(cli, ["--unnest", "/tender/items/0/id", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Unnesting columns /tender/items/0/id for table tenders" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output


def test_unnest_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        shutil.copyfile(FILENAME, "data.json")
        shutil.copyfile(ANALYZED, "analyzed.json")
        shutil.copyfile(UNNEST, "unnest")
        result = runner.invoke(cli, ["--unnest-file", "unnest", "data.json"])
        assert result.exit_code == 0
        assert "Input file is release package" in result.output
        assert "Unnesting columns /tender/items/0/id for table tenders" in result.output
        assert "Done flattening. Flattened objects: 6" in result.output

from operator import attrgetter
from unittest.mock import call, mock_open, patch

from jmespath import search
from jsonpointer import resolve_pointer
from pytest import fail

from spoonbill.common import JOINABLE_SEPARATOR
from spoonbill.spec import Column, Table
from spoonbill.stats import DataPreprocessor
from spoonbill.utils import insert_after_key
from tests.conftest import TEST_COMBINED_TABLES, TEST_ROOT_TABLES, schema_path
from tests.data import (
    awards_arrays,
    awards_columns,
    awards_combined_columns,
    contracts_arrays,
    contracts_columns,
    contracts_combined_columns,
    parties_arrays,
    parties_columns,
    parties_combined_columns,
    planning_arrays,
    planning_columns,
    planning_combined_columns,
    tenders_arrays,
    tenders_columns,
    tenders_combined_columns,
)

COLUMNS = {
    "tenders": tenders_columns,
    "parties": parties_columns,
    "awards": awards_columns,
    "contracts": contracts_columns,
    "planning": planning_columns,
}
COMBINED_COLUMNS = {
    "tenders": tenders_combined_columns,
    "parties": parties_combined_columns,
    "awards": awards_combined_columns,
    "contracts": contracts_combined_columns,
    "planning": planning_combined_columns,
}
ARRAYS_COLUMNS = {
    "tenders": tenders_arrays,
    "parties": parties_arrays,
    "awards": awards_arrays,
    "contracts": contracts_arrays,
    "planning": planning_arrays,
}
ADDITIONAL_COLUMNS = ["/parties/test"]


def test_parse_schema(schema, spec):
    for name in TEST_ROOT_TABLES:
        table = spec[name]
        assert isinstance(table, Table)
        assert table.total_rows == 0
        assert not table.parent
        assert table.is_root
        assert not table.is_combined
        for col_path in COLUMNS[name]:
            col = table[col_path]
            assert isinstance(col, Column)
            assert col.hits == 0
            assert col.path == col_path

        for col_path in COMBINED_COLUMNS[name]:
            col = table.combined_columns[col_path]
            assert col.hits == 0
            assert col.path == col_path

        for col_path in ARRAYS_COLUMNS[name]:
            col = table.arrays[col_path]
            assert col == 0


def test_resolve_schema_uri():
    dp = DataPreprocessor(schema_path, TEST_ROOT_TABLES, combined_tables=TEST_COMBINED_TABLES)
    assert isinstance(dp.schema, dict)


def test_get_table(spec, releases):
    table = spec.get_table("/tender")
    assert table.name == "tenders"
    table = spec.get_table("/tender/submissionMethodDetails")
    assert table.name == "tenders"
    table = spec.get_table("/tender/submissionMethod")
    assert table.name == "tenders"

    table = spec.get_table("/tender/items/id")
    assert table.name == "tenders_items"

    table = spec.get_table("/tender/items/additionalClassifications/id")
    assert table.name == "tenders_items_class"

    table = spec.get_table("/planning")
    assert table.name == "planning"
    table = spec.get_table("/parties")
    assert table.name == "parties"


# TODO: analyze combined tables
def test_analyze(spec, releases):
    [count for count in spec.process_items(releases)]
    tenders = spec.tables["tenders"]
    parties = spec.tables["parties"]
    awards = spec.tables["awards"]
    contracts = spec.tables["contracts"]

    tender_ids = search("[].tender.id", releases)
    assert tenders.total_rows == len(tender_ids)
    assert tenders["/tender/id"].hits == len(tender_ids)
    preview_ids = [i["/tender/id"] for i in tenders.preview_rows]
    assert not set(tender_ids).difference(preview_ids)

    tender_items = sorted(search("[].tender.items", releases), reverse=True, key=len)
    max_len = len(tender_items[0])
    assert tenders.arrays["/tender/items"] == max_len
    for index, item in enumerate(tender_items[0]):
        path = f"/tender/items/{index}/id"
        items = search(f"[].tender.items[{index}].id", releases)
        assert len(items) == tenders.combined_columns[path].hits
        # assert len(items) == tenders.columns[path].hits
    items_ids = [i["id"] for item in tender_items for i in item]
    assert len(items_ids) == spec.tables["tenders_items"].total_rows

    for array in ("awards", "parties", "contracts"):
        ids = search(f"[].{array}[]", releases)
        table = locals().get(array)
        assert table.total_rows == len(ids)
        assert table[f"/{array}/id"].hits == len(ids)
    # check joinable calculation
    assert parties["/parties/roles"].hits == len(search("[].parties[].roles", releases))


@patch("spoonbill.LOGGER.error")
def test_mismatched_types(log, spec, releases):
    releases[0]["tender"]["id"] = ["/test/id"]
    for _ in spec.process_items(releases):
        pass
    log.assert_has_calls([call("Mismatched type on /tender/id expected ['string', 'integer']")])


@patch("spoonbill.LOGGER.error")
def test_dump_restore(log, spec, releases, tmpdir):
    for _ in spec.process_items(releases):
        pass
    spec.dump(tmpdir / "result.json")
    spec2 = DataPreprocessor.restore(tmpdir / "result.json")

    for name, table in spec.tables.items():
        assert table == spec2.tables[name]
    for key in (
        "schema",
        "root_tables",
        "combined_tables",
        # "header_separator",
        "tables",
        "table_threshold",
        "total_items",
        "multiple_values",
        "language",
        "names_counter",
        "with_preview",
    ):

        assert key in spec2.__dict__
    with patch("builtins.open", mock_open(read_data="invalid")):
        spec2 = DataPreprocessor.restore(tmpdir / "result.json")
        log.assert_has_calls([call("Invalid pickle file. Can't restore.")])

    with patch("builtins.open", mock_open(read_data=b"invalid")):
        spec2 = DataPreprocessor.restore(tmpdir / "result.json")
        log.assert_has_calls([call("Invalid pickle file. Can't restore.")])


def test_recalculate_headers(root_table, releases):
    items = releases[0]["tender"]["items"]
    # insert_after_key(root_table, "/tender/items", "/tender", "items", items, False)
    insert_after_key(root_table.combined_columns, "/tender", "items")
    for key in (
        "/tender/items/0/id",
        "/tender/items/0/additionalClassifications/0/id",
    ):
        assert key in root_table.combined_columns
        assert key in root_table.columns
    for key in ("/tender/items/1/id", "/tender/items/1/additionalClassifications/0/id"):
        assert key not in root_table.combined_columns
        assert key not in root_table.columns
    items = items * 2
    # insert_after_key(root_table, "/tender/items", "/tender", "items", items, False)
    insert_after_key(root_table.combined_columns, "/tender", "items")

    for key in (
        "/tender/items/0/id",
        "/tender/items/0/additionalClassifications/0/id",
    ):
        assert key in root_table.combined_columns
        assert key in root_table.columns
    for key in ("/tender/items/2/id", "/tender/items/2/additionalClassifications/0/id"):
        assert key not in root_table.combined_columns
        assert key not in root_table.columns

    items = [
        {
            "description": "Cycle path construction work",
            "id": "45233162-2",
            "scheme": "CPV",
            "uri": "http://cpv.data.ac.uk/code-45233162.html",
        }
    ] * 2
    insert_after_key(root_table.combined_columns, "/tender/items/0", "additionalClassifications")
    for key in ("/tender/items/0/id", "/tender/items/0/additionalClassifications/0/id"):
        assert key in root_table.combined_columns
        assert key in root_table.columns
    for key in (
        "/tender/items/0/additionalClassifications/2/id",
        "/tender/items/1/additionalClassifications/1/id",
        "/tender/items/2/additionalClassifications/1/id",
    ):
        assert key not in root_table.combined_columns
        assert key not in root_table.columns

    items = releases[0]["tender"]["items"] * 5
    # insert_after_key(root_table, "/tender/items", "/tender", "items", items, True)
    insert_after_key(root_table.combined_columns, "/tender", "items")
    for key in ("/tender/items/0/id", "/tender/items/0/additionalClassifications/0/id"):
        assert key in root_table.combined_columns
        assert key in root_table.columns


def test_analyze_preview_rows(spec_analyzed, releases):
    tenders = spec_analyzed.tables["tenders"]
    tenders_items = spec_analyzed.tables["tenders_items"]
    tenders_tende = spec_analyzed.tables["tenders_tenderers"]
    tenders_items_class = spec_analyzed.tables["tenders_items_class"]

    for getter in (attrgetter("preview_rows"), attrgetter("preview_rows_combined")):
        for count, row in enumerate(getter(tenders)):
            tenderers = [r for r in getter(tenders_tende) if r["parentID"] == row["rowID"]]
            items = [r for r in getter(tenders_items) if r["parentID"] == row["rowID"]]
            items_class = []
            for it in items:
                for r in getter(tenders_items_class):
                    if r["parentID"] == it["rowID"]:
                        items_class.append(r)
            for key, item in row.items():
                if "/" in key:
                    # Check headers are present in tables
                    assert key in tenders.combined_columns
                    expected = resolve_pointer(releases[count], key)
                    if isinstance(expected, list):
                        # joinable
                        expected = JOINABLE_SEPARATOR.join(expected)
                    assert item == expected
                    if "tenderers" in key:
                        for index, tenderer in enumerate(reversed(tenderers)):
                            assert tenderer["parentTable"] == "tenders"
                            for k, v in tenderer.items():
                                if "/" in k:
                                    path = k.replace("/tender/tenderers", f"/tender/tenderers/{index}")
                                    value = resolve_pointer(releases[count], path)
                                    assert value == v

                    if "/tender/items/" in key:
                        for index, it in enumerate(reversed(items)):
                            assert it["parentTable"] == "tenders"
                            for k, v in it.items():
                                if "/" in k:
                                    path = k.replace("/tender/items", f"/tender/items/{index}")
                                    value = resolve_pointer(releases[count], path)
                                    assert value == v
                                    if "additionalClassifications" in k:
                                        for i, cls in enumerate(reversed(items_class)):
                                            assert cls["parentTable"] == "tenders_items"
                                            for k, v in cls.items():
                                                if "/" in k:
                                                    path = k.replace("/tender/items", f"/tender/items/{index}")
                                                    path = path.replace(
                                                        "/additionalClassifications/",
                                                        f"/additionalClassifications/{i}/",
                                                    )
                                                    value = resolve_pointer(releases[count], path)
                                                    assert v == value


def test_analyze_array_extentions_no_split(spec, releases):
    attr = {"name": "Presentacion", "id": "1"}
    items = releases[0]["tender"]["items"]
    items[0]["attributes"] = [attr]
    [_ for _ in spec.process_items(releases)]

    cols = spec.tables["tenders"].combined_columns
    assert "/tender/items/0/attributes/0/id" in cols
    assert "/tender/items/0/attributes/0/name" in cols
    assert "/tender/items/1/attributes/0/name" not in cols
    assert "/tender/items/0/attributes/1/name" not in cols
    assert "/tender/items/1/attributes/1/name" not in cols
    cols = spec.tables["tenders_items"].combined_columns
    assert "/tender/items/attributes/0/name" in cols
    assert "/tender/items/attributes/0/name" in cols
    assert "/tender/items/attributes/1/name" not in cols
    assert "/tender/items/attributes/1/name" not in cols

    for cols in spec.tables["tenders_items_attributes"], spec.tables["tenders_items_attributes"].combined_columns:
        assert "/tender/items/attributes/name" in cols


def test_analyze_array_extentions_split(spec, releases):
    attr = {"name": "Presentacion", "id": "1"}
    items = releases[0]["tender"]["items"]
    items[0]["attributes"] = [attr] * 10
    releases[0]["tender"]["items"] = items
    [_ for _ in spec.process_items(releases)]

    cols = spec.tables["tenders"]

    for key in (
        "/tender/items/0/attributes/0/id",
        "/tender/items/0/attributes/1/id",
        "/tender/items/1/attributes/0/id",
        "/tender/items/1/attributes/1/id",
        "/tender/items/0/attributes/0/name",
        "/tender/items/0/attributes/1/name",
        "/tender/items/1/attributes/0/name",
        "/tender/items/1/attributes/1/name",
    ):
        assert key not in cols

    cols = spec.tables["tenders"].combined_columns

    for key in (
        "/tender/items/0/attributes/0/id",
        "/tender/items/0/attributes/0/name",
    ):
        assert key not in cols
    for key in (
        "/tender/items/1/attributes/0/name",
        "/tender/items/1/attributes/0/id",
        "/tender/items/1/attributes/1/name",
        "/tender/items/1/attributes/1/id",
        "/tender/items/0/attributes/1/name",
        "/tender/items/0/attributes/1/id",
    ):
        assert key not in cols

    cols = spec.tables["tenders_items"]
    assert "/tender/items/attributes/0/id" not in cols
    assert "/tender/items/attributes/0/name" not in cols
    assert "/tender/items/attributes/1/id" not in cols
    assert "/tender/items/attributes/1/name" not in cols

    cols = spec.tables["tenders_items"].combined_columns
    assert "/tender/items/attributes/0/id" not in cols
    assert "/tender/items/attributes/0/name" not in cols
    assert "/tender/items/attributes/1/id" not in cols
    assert "/tender/items/attributes/1/name" not in cols
    cols = spec.tables["tenders_items_attributes"].combined_columns
    assert "/tender/items/attributes/id" in cols
    assert "/tender/items/attributes/name" in cols


def test_analyze_test_dataset(spec, test_dataset_releases):
    try:
        [_ for _ in spec.process_items(test_dataset_releases)]
    except AttributeError as e:
        fail(f"{e.__class__.__name__}: {str(e)}")


def test_analyze_with_combined_tables(spec, releases_with_combined_tables):
    [_ for _ in spec.process_items(releases_with_combined_tables)]

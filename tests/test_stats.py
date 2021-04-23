from json import dump, load

from jmespath import search

from spoonbill.spec import Column, Table
from spoonbill.stats import DataPreprocessor
from tests.data import (
    OCDS_TITLES_COMBINED,
    TEST_ROOT_TABLES,
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
        for col_id in COLUMNS[name]:
            col = table[col_id]
            assert isinstance(col, Column)
            assert col.hits == 0
            assert col.id == col_id
            assert col.title == OCDS_TITLES_COMBINED[col_id]

        for col_id in COMBINED_COLUMNS[name]:
            col = table.combined_columns[col_id]
            assert col.hits == 0
            assert col.id == col_id
            assert col.title == OCDS_TITLES_COMBINED[col_id]

        for col_id in ARRAYS_COLUMNS[name]:
            col = table.arrays[col_id]
            assert col == 0


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
    assert table.name == "tenders_items_addit"

    table = spec.get_table("/planning")
    assert table.name == "planning"
    table = spec.get_table("/parties")
    assert table.name == "parties"


def test_generate_titles(spec):
    for table in spec.tables.values():
        for path, title in table.titles.items():
            assert OCDS_TITLES_COMBINED[path] == title


# TODO: analyze combined tables
def test_analyze(spec, releases):
    spec.process_items(releases)
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
    items_ids = [i["id"] for item in tender_items for i in item]
    assert len(items_ids) == spec.tables["tenders_items"].total_rows

    for array in ("awards", "parties", "contracts"):
        ids = search(f"[].{array}[]", releases)
        table = locals().get(array)
        assert table.total_rows == len(ids)
        assert table[f"/{array}/id"].hits == len(ids)
    # check joinable calculation
    assert parties["/parties/roles"].hits == len(search("[].parties[].roles", releases))


def test_dump_restore(spec, releases, tmpdir):
    spec.process_items(releases)
    with open(tmpdir / "result.json", "w") as fd:
        dump(spec.dump(), fd)

    with open(tmpdir / "result.json") as fd:
        data = load(fd)

    spec2 = DataPreprocessor.restore(data)
    for name, table in spec.tables.items():
        assert table == spec2.tables[name]


def test_analyze_preview_rows(spec, releases):
    spec.process_items(releases)
    commodities_path = ["tenders", "parties", "awards", "contracts", "planning"]
    commodities = [spec.tables.get(i) for i in commodities_path]
    counters = {}
    # Compare values of input file and preview_rows
    for commodity in commodities:
        for row in commodity.preview_rows:
            for key, value in row.items():
                if "/" in key:
                    if key not in counters:
                        counters[key] = 0
                    # Check headers are present in tables
                    header = key
                    for char in header:
                        if char.isdigit():
                            header = header.replace(char, "0")
                    assert header in COMBINED_COLUMNS[commodity.name] or header in ADDITIONAL_COLUMNS
                    # Query formatting
                    query = "".join(["" if char.isdigit() or char == "." else char for char in key]).replace("//", "/")
                    query = query.replace("//", "/").replace("/", "[].") + "[]"
                    search_result = search(query, releases)

                    if len(search_result) == 8:
                        search_result.reverse()
                        assert value == search_result[counters[key] - 1]
                    elif len(search_result) == 2 and value is not search_result[counters[key]]:
                        search_result.reverse()
                        assert value == search_result[counters[key]]
                    else:
                        assert value == search_result[counters[key]]

                    counters[key] += 1


def test_analyze_preview_rows_combined(spec, releases):
    spec.process_items(releases)
    commodities_path = ["tenders", "parties", "awards", "contracts", "planning"]
    commodities = [spec.tables.get(i) for i in commodities_path]
    counters = {}
    # Compare values of input file and preview_rows
    for commodity in commodities:
        for row in commodity.preview_rows_combined:
            for key, value in row.items():
                if "/" in key:
                    if key not in counters:
                        counters[key] = 0
                    # Check headers are present in tables
                    header = key
                    for char in header:
                        if char.isdigit():
                            header = header.replace(char, "0")
                    assert header in COMBINED_COLUMNS[commodity.name] or header in ADDITIONAL_COLUMNS
                    # Query formatting
                    query = "".join(["" if char.isdigit() or char == "." else char for char in key]).replace("//", "/")
                    query = query.replace("//", "/").replace("/", "[].") + "[]"
                    search_result = search(query, releases)

                    if len(search_result) == 8:
                        search_result.reverse()
                        assert value == search_result[counters[key] - 1]
                    elif len(search_result) == 2 and value is not search_result[counters[key]]:
                        search_result.reverse()
                        assert value == search_result[counters[key]]
                    else:
                        assert value == search_result[counters[key]]

                    counters[key] += 1

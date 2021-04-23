from jmespath import search

from spoonbill.flatten import Flattener, FlattenOptions

ID_ITEMS = {
    "tenders": [
        {"/tender/id": "ocds-213czf-000-00001-01-planning"},
        {"/tender/id": "ocds-213czf-000-00001-01-tender"},
        {"/tender/id": "ocds-213czf-000-00001-01-tender"},
        {"/tender/id": "ocds-213czf-000-00001-01-tender"},
    ],
    "parties": [
        {"/parties/id": "GB-LAC-E09000003"},
        {"/parties/id": "GB-LAC-E09000003"},
        {"/parties/id": "GB-LAC-E09000003"},
        {"/parties/id": "GB-COH-22222222"},
        {"/parties/id": "GB-COH-11111111"},
        {"/parties/id": "GB-LAC-E09000003"},
        {"/parties/id": "GB-LAC-E09000003"},
        {"/parties/id": "GB-LAC-E09000003"},
    ],
}


def test_flatten(spec_analyzed, releases):
    options = FlattenOptions(
        **{
            "selection": {"tenders": {"split": True}, "parties": {"split": False}},
        }
    )
    flattener = Flattener(options, spec_analyzed.tables)
    count = {"tenders": 0, "parties": 0}
    for flat in flattener.flatten(releases):
        for name, rows in flat.items():
            for row in rows:
                assert "id" in row
                assert "ocid" in row
                assert "rowID" in row
                if name in ID_ITEMS:
                    key = "tender" if name == "tenders" else "parties"
                    path = f"/{key}/id"
                    assert ID_ITEMS[name][count[name]][path] == row.get(path)
                    count[name] += 1


def test_flatten_with_count(spec_analyzed, releases):

    options = FlattenOptions(**{"selection": {"tenders": {"split": True}}, "count": True})
    flattener = Flattener(options, spec_analyzed.tables)
    for count, flat in enumerate(flattener.flatten(releases)):
        for name, rows in flat.items():
            if name == "tenders":
                for row in rows:
                    items = search(f"[{count}].tender.items", releases)
                    if items:
                        assert "/tender/itemsCount" in row
                        assert len(items) == row["/tender/itemsCount"]
            elif name == "tenders_items":
                for index, row in enumerate(rows):
                    additional = search(
                        f"[{count}].tender.items[{index}].additionalClassifications",
                        releases,
                    )
                    if additional:
                        assert "/tender/items/additionalClassificationsCount" in row
                        assert len(additional) == row["/tender/items/additionalClassificationsCount"]


def test_flatten_with_repeat(spec_analyzed, releases):
    options = FlattenOptions(
        **{
            "selection": {"tenders": {"split": True, "repeat": ["/tender/id"]}},
        }
    )
    flattener = Flattener(options, spec_analyzed.tables)
    for count, flat in enumerate(flattener.flatten(releases)):
        for name, rows in flat.items():
            if name == "tenders":
                continue
            for row in rows:
                assert "id" in row
                assert "ocid" in row
                assert "rowID" in row
                assert "/tender/id" in row
                assert row["/tender/id"] == search(f"[{count}].tender.id", releases)


def test_flatten_with_unnest(spec_analyzed, releases):
    field = "/tender/items/0/id"
    options = FlattenOptions(
        **{
            "selection": {"tenders": {"split": True, "unnest": [field]}},
        }
    )
    flattener = Flattener(options, spec_analyzed.tables)
    for count, flat in enumerate(flattener.flatten(releases)):
        for name, rows in flat.items():
            for row in rows:
                if name != "tenders":
                    assert field not in row
                    continue
                item_id = search(f"[{count}].tender.items[0].id", releases)
                if item_id:
                    assert field in row
                    assert search(f"[{count}].tender.items[0].id", releases) == row[field]


def test_flatten_fields_compare(spec_analyzed, releases):
    options = FlattenOptions(
        **{
            "selection": {"tenders": {"split": True}, "parties": {"split": False}},
        }
    )
    flattener = Flattener(options, spec_analyzed.tables)
    counters = {}
    for flat in flattener.flatten(releases):
        for name, rows in flat.items():
            for row in rows:
                for key, value in row.items():
                    if "/" in key:
                        if key not in counters:
                            counters[key] = 0
                        query = key.replace("/", "[].") + "[]"
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


def test_flatten_joinable_arrays(spec_analyzed, releases):
    options = FlattenOptions(
        **{
            "selection": {"tenders": {"split": True}, "parties": {"split": False}},
        }
    )
    flattener = Flattener(options, spec_analyzed.tables)
    fields = ["submissionMethod", "roles"]
    counters = {}
    for flat in flattener.flatten(releases):
        for name, rows in flat.items():
            for row in rows:
                for key, value in row.items():
                    if any(field in key for field in fields):
                        if key not in counters:
                            counters[key] = 0
                        query = key.replace("/", "[].") + "[]"
                        search_result = search(query, releases)

                        if len(search_result) == 8:
                            search_result.reverse()
                            assert value == search_result[counters[key] - 1]
                        else:
                            assert value == search_result[counters[key]]
                        counters[key] += 1

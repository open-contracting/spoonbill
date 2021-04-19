from jmespath import search
from spoonbill.flatten import Flattener, FlattenOptions


def test_flatten(spec, releases):
    spec.process_items(releases)

    options = FlattenOptions(
        **{
            "selection": {"tenders": {"split": True}, "parties": {"split": False}},
        }
    )
    flattener = Flattener(options, spec.tables)
    for flat in flattener.flatten(releases):
        for name, rows in flat.items():
            for row in rows:
                assert "id" in row
                assert "ocid" in row
                assert "rowID" in row


def test_flatten_with_count(spec, releases):
    spec.process_items(releases)

    options = FlattenOptions(
        **{"selection": {"tenders": {"split": True}}, "count": True}
    )
    flattener = Flattener(options, spec.tables)
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
                        assert (
                            len(additional)
                            == row["/tender/items/additionalClassificationsCount"]
                        )


def test_flatten_with_repeat(spec, releases):
    spec.process_items(releases)
    options = FlattenOptions(
        **{
            "selection": {"tenders": {"split": True, "repeat": ["/tender/id"]}},
        }
    )
    flattener = Flattener(options, spec.tables)
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


def test_flatten_with_unnest(spec, releases):
    spec.process_items(releases)
    field = "/tender/items/0/id"
    options = FlattenOptions(
        **{
            "selection": {"tenders": {"split": True, "unnest": [field]}},
        }
    )
    flattener = Flattener(options, spec.tables)
    for count, flat in enumerate(flattener.flatten(releases)):
        for name, rows in flat.items():
            for row in rows:
                if name != "tenders":
                    assert field not in row
                    continue
                item_id = search(f"[{count}].tender.items[0].id", releases)
                if item_id:
                    assert field in row
                    assert (
                        search(f"[{count}].tender.items[0].id", releases) == row[field]
                    )

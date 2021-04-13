from spoonbill.flatten import Flattener
from spoonbill.stats import DataPreprocessor
from .data import TEST_ROOT_TABLES, TEST_COMBINED_TABLES

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


def test_flatten(schema, releases):
    spec = DataPreprocessor(
        schema, TEST_ROOT_TABLES, combined_tables=TEST_COMBINED_TABLES
    )
    options = {
        "selection": {"tenders": {"split": True}, "parties": {"split": False}},
    }
    flattener = Flattener(options, spec.tables)
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

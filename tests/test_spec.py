from spoonbill.spec import add_child_table
from spoonbill.utils import combine_path, get_pointer


def test_combine_path(root_table):
    path = combine_path(root_table, "/tender/id")
    assert path == "/tender/id"
    path = combine_path(root_table, "/tender/submissionMethodDetails")
    assert path == "/tender/submissionMethodDetails"
    path = combine_path(root_table, "/tender/submissionMethod")
    assert path == "/tender/submissionMethod"
    path = combine_path(root_table, "/tender/items/id")
    assert path == "/tender/items/0/id"
    path = combine_path(root_table, "/tender/items/additionalClassifications/id")
    assert path == "/tender/items/0/additionalClassifications/0/id"
    root_table.arrays = {"/tender/items/additionalClassifications": 0}
    path = combine_path(root_table, "/tender/items/additionalClassifications/id")
    assert path == "/tender/items/additionalClassifications/0/id"


def test_inc_column(root_table):
    child = add_child_table(root_table, "/tender/items", "tender", "items")
    child.add_column("/tender/items/id", ["string"], "Tender Id", additional=True, abs_path="/tender/items/0/test")
    child.arrays["/tender/items/additionalClassifications"] = 0
    root_table.inc_column("ocid", "ocid")
    assert root_table.combined_columns["ocid"].hits == 1

    root_table.inc_column("/tender/awardCriteriaDetails", "/tender/awardCriteriaDetails")
    assert root_table.combined_columns["/tender/awardCriteriaDetails"].hits == 1

    child.inc_column("/tender/items/0/id", "/tender/items/id")
    assert root_table.combined_columns["/tender/items/0/id"].hits == 1
    assert child["/tender/items/id"].hits == 1
    assert child.combined_columns["/tender/items/id"].hits == 1

    child_child = add_child_table(
        child, "/tender/items/additionalClassifications", "items", "additionalClassifications"
    )
    child_child.add_column(
        "/tender/items/additionalClassifications/id",
        ["string"],
        "Classification Id",
        additional=True,
    )
    child_child.inc_column(
        "/tender/items/0/additionalClassifications/0/id", "/tender/items/additionalClassifications/id"
    )
    assert child.combined_columns["/tender/items/additionalClassifications/0/id"].hits == 1
    assert root_table.combined_columns["/tender/items/0/additionalClassifications/0/id"].hits == 1


def test_add_column(root_table):
    root_table.add_column("/tender/id", ["string", "integer"], "Tender Id")
    assert "/tender/id" in root_table
    assert "/tender/id" in root_table.combined_columns

    root_table.add_column("/tender/itemsCount", ["string", "integer"], "Items Count")
    assert "/tender/itemsCount" in root_table
    assert "/tender/itemsCount" in root_table.combined_columns

    root_table.add_column(
        "/tender/items/additionalClassificationsCount", ["string", "integer"], "Classifications Count"
    )
    assert "/tender/items/0/additionalClassificationsCount" in root_table
    assert "/tender/items/0/additionalClassificationsCount" in root_table.combined_columns

    child = add_child_table(root_table, "/tender/items", "tender", "items")
    child.add_column(
        "/tender/items/test",
        ["string", "integer"],
        "/tender/items/test",
        additional=True,
        abs_path="/tender/items/0/test",
    )
    assert "/tender/items/test" in child
    assert "/tender/items/test" in child.combined_columns
    assert "/tender/items/0/test" in root_table.combined_columns
    child.add_column("/tender/items/id", ["string", "integer"], "Items Id")

    child.arrays["/tender/items/additionalClassifications"] = 0
    child.add_column("/tender/items/additionalClassifications/id", ["string", "integer"], "Classification ID")
    assert "/tender/items/additionalClassifications/0/id" in child
    assert "/tender/items/id" in child
    assert "/tender/items/0/id" in root_table
    assert "/tender/items/0/additionalClassifications/0/id" in root_table

    child.add_column(
        "/tender/items/additionalClassificationsCount",
        ["string", "integer"],
        "Classification Count",
        propagated=False,
    )
    assert "/tender/items/additionalClassificationsCount" in child
    assert "/tender/items/additionalClassificationsCount" in child.combined_columns

    assert "/tender/items/additionalClassificationsCount" not in root_table
    assert "/tender/items/additionalClassificationsCount" not in root_table.combined_columns


def test_row_counters(root_table):
    available = ["ocid", "id", "rowID"]
    for col in available:
        root_table.inc_column(col, col)
    cols = root_table.available_rows()
    assert not set(cols).difference(available)

    cols = root_table.missing_rows()
    assert set(cols).difference(
        [
            "parentID",
            "/tender/awardCriteriaDetails",
            "/tender/items/0/id",
            "/tender/items/0/additionalClassifications/0/id",
        ]
    )


def test_set_array(root_table):
    items = root_table.arrays["/tender/items"]
    assert items == 0

    root_table.set_array("/tender/items", [i for i in range(10)])
    items = root_table.arrays["/tender/items"]
    assert items == 10

    root_table.set_array("/tender/items", [i for i in range(5)])
    items = root_table.arrays["/tender/items"]
    assert items == 10


def test_is_array(root_table):
    assert root_table.is_array("/tender/items")
    assert root_table.is_array("/tender/items/id")
    assert root_table.is_array("/tender/items/0/id")
    assert root_table.is_array("/tender/items/additionalClassifications")
    assert not root_table.is_array("/tender/id")
    assert not root_table.is_array("/tender/title")
    assert not root_table.is_array("/tender/submissionMethod")


def test_add_child_table(root_table):
    child = add_child_table(root_table, "/tender/tenderers", "", "tenderers")
    assert child.name == "tenders_tenderers"
    assert child.name in root_table.child_tables
    assert child.total_rows == 0
    child.parent == root_table.name


def test_get_pointer(root_table):
    child = add_child_table(root_table, "/tender/items", "tender", "items")
    child_child = add_child_table(
        child, "/tender/items/additionalClassifications", "items", "additionalClassifications"
    )
    pointer = get_pointer(
        child_child,
        "/tender/items/0/additionalClassifications/0/id",
        "/tender/items/additionalClassifications/id",
        True,
    )
    assert pointer == "/tender/items/additionalClassifications/id"

    pointer = get_pointer(
        child, "/tender/items/0/additionalClassifications/0/id", "/tender/items/additionalClassifications/id", True
    )
    assert pointer == "/tender/items/additionalClassifications/0/id"

    pointer = get_pointer(
        child, "/tender/items/0/additionalClassifications/0", "/tender/items/additionalClassifications", True
    )
    assert pointer == "/tender/items/additionalClassifications/0"

    pointer = get_pointer(
        child, "/tender/items/0/additionalClassifications", "/tender/items/additionalClassifications", True
    )
    assert pointer == "/tender/items/additionalClassifications"

    pointer = get_pointer(
        root_table,
        "/tender/items/0/additionalClassifications/0/id",
        "/tender/items/additionalClassifications/id",
        True,
    )
    assert pointer == "/tender/items/0/additionalClassifications/0/id"

    pointer = get_pointer(root_table, "/tender/items/0/id", "/tender/items/id", True)
    assert pointer == "/tender/items/0/id"

    pointer = get_pointer(child, "/tender/items/0/id", "/tender/items/id", True)
    assert pointer == "/tender/items/id"
    pointer = get_pointer(root_table, "/tender/id", "/tender/id", True)
    assert pointer == "/tender/id"

    pointer = get_pointer(root_table, "/tender/items", "/tender/items", True, index="0")
    assert pointer == "/tender/items/0"

    pointer = get_pointer(root_table, "/tender", "/tender", True, index="0")
    assert pointer == "/tender"

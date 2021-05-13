from collections import OrderedDict

from spoonbill.spec import Column, Table, add_child_table
from spoonbill.utils import combine_path


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


def test_inc_column(root_table):
    root_table.inc_column("ocid")
    assert root_table["ocid"].hits == 1
    assert root_table.combined_columns["ocid"].hits == 1

    root_table.inc_column("/tender/items/0/id", combined=True)
    assert root_table["/tender/items/0/id"].hits == 0
    assert root_table.combined_columns["/tender/items/0/id"].hits == 1


def test_add_column(root_table):
    root_table.add_column("/tender/id", {"title": "Tender ID"}, ["string", "integer"], {})
    assert "/tender/id" in root_table


def test_row_counters(root_table):
    available = ["ocid", "id", "rowID"]
    for col in available:
        root_table.inc_column(col)
    cols = root_table.available_rows()
    assert not set(cols).difference(available)

    cols = root_table.missing_rows()
    assert not set(cols).difference(["parentID", "/tender/awardCriteriaDetails", "/tender/items/0/id"])


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
    data = root_table.dump()
    assert not data["parent"]
    child = add_child_table(root_table, "/tender/tenderers", "", "tenderers")
    assert child.name == "tenders_tenderers"
    assert child.name in root_table.child_tables
    assert child.total_rows == 0
    data = child.dump()
    data["parent"] == root_table.name

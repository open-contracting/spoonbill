from collections import OrderedDict

from spoonbill.spec import Column, Table
from spoonbill.utils import combine_path


def test_combine_path():
    root = Table(
        name="tenders",
        path=["/tender"],
        columns=OrderedDict(
            [
                ("ocid", Column(title="ocid", type="string", id="ocid", hits=0)),
                ("id", Column(title="id", type="string", id="id", hits=0)),
                ("rowID", Column(title="rowID", type="string", id="rowID", hits=0)),
                (
                    "parentID",
                    Column(title="parentID", type="string", id="parentID", hits=0),
                ),
                (
                    "/tender/awardCriteriaDetails",
                    Column(
                        title="Tender Award Criteria Details",
                        type="string",
                        id="/tender/awardCriteriaDetails",
                        hits=0,
                    ),
                ),
                (
                    "/tender/submissionMethodDetails",
                    Column(
                        title="Tender Submission Method Details",
                        type="string",
                        id="/tender/submissionMethodDetails",
                        hits=0,
                    ),
                ),
            ]
        ),
        combined_columns=OrderedDict(
            [
                ("ocid", Column(title="ocid", type="string", id="ocid", hits=0)),
                ("id", Column(title="id", type="string", id="id", hits=0)),
                ("rowID", Column(title="rowID", type="string", id="rowID", hits=0)),
                (
                    "parentID",
                    Column(title="parentID", type="string", id="parentID", hits=0),
                ),
                (
                    "/tender/submissionMethod",
                    Column(
                        title="Tender Submission Method",
                        type="array",
                        id="/tender/submissionMethod/0",
                    ),
                ),
                (
                    "/tender/submissionMethodDetails",
                    Column(
                        title="Tender Submission Method Details",
                        type="string",
                        id="/tender/submissionMethodDetails",
                        hits=0,
                    ),
                ),
            ]
        ),
        arrays={"/tender/items": 0, "/tender/items/additionalClassifications": 0},
    )
    path = combine_path(root, "/tender/id")
    assert path == "/tender/id"
    path = combine_path(root, "/tender/submissionMethodDetails")
    assert path == "/tender/submissionMethodDetails"
    path = combine_path(root, "/tender/submissionMethod")
    assert path == "/tender/submissionMethod"
    path = combine_path(root, "/tender/items/id")
    assert path == "/tender/items/0/id"
    path = combine_path(root, "/tender/items/additionalClassifications/id")
    assert path == "/tender/items/0/additionalClassifications/0/id"


def test_inc_column():
    root = Table(
        name="tenders",
        path=["/tender"],
        columns=OrderedDict(
            [
                ("ocid", Column(title="ocid", type="string", id="ocid", hits=0)),
                ("id", Column(title="id", type="string", id="id", hits=0)),
                ("rowID", Column(title="rowID", type="string", id="rowID", hits=0)),
                (
                    "parentID",
                    Column(title="parentID", type="string", id="parentID", hits=0),
                ),
                (
                    "/tender/awardCriteriaDetails",
                    Column(
                        title="Tender Award Criteria Details",
                        type="string",
                        id="/tender/awardCriteriaDetails",
                        hits=0,
                    ),
                ),
                (
                    "/tender/items/0/id",
                    Column(
                        title="Tender Item id",
                        type="string",
                        hits=0,
                        id="/tender/items/0/id",
                    ),
                ),
            ]
        ),
        combined_columns=OrderedDict(
            [
                ("ocid", Column(title="ocid", type="string", id="ocid", hits=0)),
                ("id", Column(title="id", type="string", id="id", hits=0)),
                ("rowID", Column(title="rowID", type="string", id="rowID", hits=0)),
                (
                    "parentID",
                    Column(title="parentID", type="string", id="parentID", hits=0),
                ),
                (
                    "/tender/submissionMethod",
                    Column(
                        title="Tender Submission Method",
                        type="array",
                        id="/tender/submissionMethod/0",
                    ),
                ),
                (
                    "/tender/items/0/id",
                    Column(title="Tender Item id", type="string", id="/tender/items/0/id"),
                ),
            ]
        ),
        arrays={
            "/tender/submissionMethod": 0,
            "/tender/items": 0,
            "/tender/items/additionalClassifications": 0,
        },
    )
    root.inc_column("ocid")
    assert root["ocid"].hits == 1
    assert root.combined_columns["ocid"].hits == 1

    root.inc_column("/tender/items/0/id", combined=True)
    assert root["/tender/items/0/id"].hits == 0
    assert root.combined_columns["/tender/items/0/id"].hits == 1

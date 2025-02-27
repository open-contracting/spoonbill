import json

import pytest

from spoonbill.flatten import FlattenOptions
from spoonbill.spec import Column, Table
from spoonbill.stats import DataPreprocessor
from tests.data import (
    BASE_DIR,
    RELEASES_EXTENSION_PATH,
    RELEASES_PATH,
    SCHEMA_PATH,
    TEST_COMBINED_TABLES,
    TEST_ROOT_TABLES,
)


@pytest.fixture
def schema():
    with SCHEMA_PATH.open("rb") as fd:
        return json.load(fd)


@pytest.fixture
def releases():
    with RELEASES_PATH.open("rb") as fd:
        return json.load(fd)["releases"]


@pytest.fixture
def releases_extension():
    with RELEASES_EXTENSION_PATH.open("rb") as fd:
        return json.load(fd)["releases"]


@pytest.fixture
def flatten_options():
    return FlattenOptions(selection={"tenders": {"split": True}, "parties": {"split": False}})


@pytest.fixture
def spec(schema):
    return DataPreprocessor(schema, TEST_ROOT_TABLES, combined_tables=TEST_COMBINED_TABLES, with_preview=True)


@pytest.fixture
def spec_analyzed(schema, releases):
    dp = DataPreprocessor(schema, TEST_ROOT_TABLES, combined_tables=TEST_COMBINED_TABLES, with_preview=True)
    list(dp.process_items(releases))
    return dp


@pytest.fixture
def root_table():
    return Table(
        name="tenders",
        path=["/tender"],
        is_root=True,
        columns={
            "ocid": Column(id="ocid", path="ocid", title="ocid", type="string", hits=0),
            "id": Column(id="id", path="id", title="id", type="string", hits=0),
            "rowID": Column(path="rowID", title="rowID", type="string", id="rowID", hits=0),
            "parentID": Column(path="parentID", title="parentID", type="string", id="parentID", hits=0),
            "/tender/awardCriteriaDetails": Column(
                title="Tender Award Criteria Details",
                type="string",
                id="/tender/awardCriteriaDetails",
                path="/tender/awardCriteriaDetails",
                hits=0,
            ),
            "/tender/items/0/id": Column(
                title="Tender Item id",
                type="string",
                hits=0,
                id="/tender/items/0/id",
                path="/tender/items/0/id",
            ),
            "/tender/items/0/additionalClassifications/0/id": Column(
                title="Tender Item Classification id",
                type="string",
                id="/tender/items/0/additionalClassifications/0/id",
                path="/tender/items/0/additionalClassifications/0/id",
            ),
        },
        combined_columns={
            "ocid": Column(title="ocid", type="string", id="ocid", path="ocid", hits=0),
            "id": Column(title="id", path="id", type="string", id="id", hits=0),
            "rowID": Column(title="rowID", type="string", id="rowID", path="rowID", hits=0),
            "parentID": Column(title="parentID", type="string", id="parentID", path="parentID", hits=0),
            "/tender/awardCriteriaDetails": Column(
                title="Tender Award Criteria Details",
                type="string",
                id="/tender/awardCriteriaDetails",
                path="/tender/awardCriteriaDetails",
                hits=0,
            ),
            "/tender/submissionMethod": Column(
                title="Tender Submission Method",
                type="array",
                id="/tender/submissionMethod",
                path="/tender/submissionMethod",
            ),
            "/tender/items/0/id": Column(title="Tender Item id", type="string", id="/tender/items/0/id", path="id"),
            "/tender/items/0/additionalClassifications/0/id": Column(
                title="Tender Item Classification id",
                type="string",
                id="/tender/items/0/additionalClassifications/0/id",
                path="id",
            ),
        },
        arrays={"/tender/items": 0, "/tender/items/additionalClassifications": 0},
    )


@pytest.fixture
def test_dataset_releases():
    with (BASE_DIR / "data" / "test_data.json").open("rb") as fd:
        return json.load(fd)["releases"]


@pytest.fixture
def releases_with_combined_tables():
    with (BASE_DIR / "data" / "releases_with_combined_tables.json").open("rb") as fd:
        return json.load(fd)

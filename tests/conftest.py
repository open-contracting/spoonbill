import json
import pytest
import pathlib
from spoonbill.flatten import FlattenOptions
from spoonbill.stats import DataPreprocessor
from .data import TEST_ROOT_TABLES, TEST_COMBINED_TABLES

here = pathlib.Path(__file__).parent
schema_path = here / "data" / "ocds-simplified-schema.json"
releases_path = here / "data" / "ocds-sample-data.json"
analyzed_path = here / "data" / "analyzed.json"

@pytest.fixture
def schema():
    with open(schema_path) as fd:
        return json.load(fd)


@pytest.fixture
def releases():
    with open(releases_path) as fd:
        return json.load(fd)["releases"]


@pytest.fixture
def flatten_options():
    return FlattenOptions(
        **{
            "selection": {"tenders": {"split": True}, "parties": {"split": False}},
        }
    )


@pytest.fixture
def spec(schema):
    return DataPreprocessor(
        schema, TEST_ROOT_TABLES, combined_tables=TEST_COMBINED_TABLES
    )


@pytest.fixture
def spec_analyzed():
    with open(analyzed_path) as fd:
        data =  json.load(fd)
    dp = DataPreprocessor.restore(data)
    return dp



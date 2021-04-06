import json
import pytest
import pathlib
from spoonbill.flatten import FlattenOptions


here = pathlib.Path(__file__).parent
schema_path = here / 'data' / 'ocds-simplified-schema.json'
releases_path = here / 'data' / 'ocds-sample-data.json'


@pytest.fixture
def schema():
    with open(schema_path) as fd:
        return json.load(fd)


@pytest.fixture
def releases():
    with open(releases_path) as fd:
        return json.load(fd)['releases']


@pytest.fixture
def flatten_options():
    return FlattenOptions(**{
        'selection': {'tenders': {'split': True}, 'parties': {'split': False}},
        'pretty_headers': False
    })



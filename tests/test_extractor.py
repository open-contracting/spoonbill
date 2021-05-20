import pathlib

from spoonbill.i18n import extract_schema_po
from tests.data import awards_columns, contracts_columns, parties_columns, planning_columns, tenders_columns

here = pathlib.Path(__file__).parent


def test_babel_extractor():
    with open(here / "data" / "ocds-simplified-schema.json", "rb") as schema:
        result = [msg for msg in extract_schema_po(schema, "", "", {"combine": "documents,amendments,milestones"})]
    msg_ids = [c[2] for c in result]
    for columns in (tenders_columns, parties_columns, contracts_columns, awards_columns, planning_columns):
        for col in columns:
            assert col in msg_ids

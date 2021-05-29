# we can try to infer tables from  schema
# but it may require some heuristics or handling exceptional cases
# like "tenders" which is not array and called "tender"
# so this way seems like middle ground between flexibility and simplicity
ROOT_TABLES = {
    "tenders": ["/tender"],
    "awards": ["/awards"],
    "contracts": ["/contracts"],
    "planning": ["/planning"],
    "parties": ["/parties", "/buyer"],
}
# TODO: extract types from schema? items and additionalClassifications as table?
COMBINED_TABLES = {
    "documents": [
        "/planning/documents",
        "/tender/documents",
        "/awards/documents",
        "/contracts/documents",
        "/contracts/implementation/documents",
    ],
    "milestones": [
        "/planning/milestones",
        "/tender/milestones",
        "/contracts/milestones",
        "/contracts/implementation/milestones",
    ],
    "amendments": [
        "/planning/amendments",
        "/tender/amendments",
        "/awards/amendments",
        "/contracts/amendments",
        "/contracts/implementation/amendments",
    ],
}

DEFAULT_FIELDS = ["ocid", "id", "rowID", "parentID"]
DEFAULT_FIELDS_COMBINED = ["ocid", "id", "rowID", "parentID", "parentTable"]

ARRAY = "array of {}"
# TODO: is joinable good name?
JOINABLE = "joinable"
JOINABLE_SEPARATOR = ";"
TABLE_THRESHOLD = 5

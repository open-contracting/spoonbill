from dataclasses import dataclass, field, is_dataclass
from typing import List, Mapping


@dataclass
class TableFlattenConfig:
    """Table specific flattening configuration

    :param split: Split child arrays to separate tables
    :param pretty_headers: Use human friendly headers extracted from schema
    :param headers: User edited headers to override automatically extracted
    :param unnest: List of columns to output from child to parent table
    :param repeat: List of columns to clone in child tables
    :param only: List of columns to output
    :param name: Overwrite table name
    """

    split: bool
    pretty_headers: bool = False
    headers: Mapping[str, str] = field(default_factory=dict)
    repeat: list[str] = field(default_factory=list)
    unnest: list[str] = field(default_factory=list)
    only: list[str] = field(default_factory=list)
    name: str = ""


@dataclass
class FlattenOptions:
    """Flattening configuration

    :param selection: List of selected tables to extract from data
    :param count: Include number of rows in child table in each parent table
    :param exclude: List of tables to exclude from export
    """

    selection: Mapping[str, TableFlattenConfig]
    exclude: list[str] = field(default_factory=list)
    count: bool = False

    def __post_init__(self):
        for name, table in self.selection.items():
            if not is_dataclass(table):
                self.selection[name] = TableFlattenConfig(**table)

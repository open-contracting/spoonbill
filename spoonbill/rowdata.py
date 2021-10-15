from collections import OrderedDict
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any, List, Mapping


class MappingBase(MutableMapping):
    data: List[Mapping[str, Any]]

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key, value):
        del self.data[key]

    def __iter__(self):
        for k in self.data:
            yield k

    def __len__(self):
        return len(self.data)

    def as_dict(self):
        return self.data


@dataclass
class Row(MappingBase):
    """
    Row data container
    """

    row_id: str
    table_name: str
    data: List[Mapping[str, Any]]
    parent: object


@dataclass
class Rows(MappingBase):
    """
    Flattened rows for each object
    """

    ocid: str
    buyer: Mapping[str, str]
    data: Mapping[str, List[Row]] = field(default_factory=list)
    row: Row = ""

    def new_row(self, table, item_id):
        name = table.name
        head = self.ocid
        row = OrderedDict(
            {
                "id": item_id,
                "ocid": self.ocid,
            }
        )
        parent_row = self.row

        if table.is_combined:
            while parent_row and parent_row.parent:
                parent_row = parent_row.parent
            if parent_row:
                row["parentTable"] = parent_row.table_name

        if not table.is_root:
            parent_table = table.parent
            while parent_row and parent_row.parent:
                if parent_row.table_name == parent_table.name:
                    break
                if parent_row:
                    parent_row = parent_row.parent
            row["parentTable"] = parent_table.name
            if parent_row:
                parent_id = parent_row.row_id
                row["parentID"] = parent_id
                head = parent_id
        row_id = f"{head}/{name}:{item_id}"
        row["rowID"] = row_id
        if table.name == "parties" and self.buyer:
            # it works and we bind to OCDS anyway
            # but this is a hack
            # and its a good idea to find better way of doing it in future
            row["/buyer/id"] = self.buyer.get("id")
            row["/buyer/name"] = self.buyer.get("name")
        row = Row(row_id=row_id, data=row, table_name=table.name, parent=parent_row)
        self.row = row
        return row

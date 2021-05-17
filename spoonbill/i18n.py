import gettext
import json
from collections import deque
from pathlib import Path

import jsonref

from spoonbill.common import COMBINED_TABLES
from spoonbill.utils import common_prefix, extract_type

domain = "spoonbill"
locale_dir = str(Path(__file__).parent / "locales")

try:
    t = gettext.translation(domain, locale_dir)
    _ = t.gettext
except FileNotFoundError:
    _ = lambda m: m  # noqa: E731


# slightly modified version of ocds-babel`s extract_schema
# TODO: discuss upstreaming this extractor
def extract_schema_po(fileobj, keywords, comment_tags, options):
    """
    Yields the "title" and "description" values of a JSON Schema file.
    """
    combine = options.get("combine")
    combined_paths = []
    if combine:
        for table in combine.split(","):
            table = table.strip()
            if table in COMBINED_TABLES:
                combined_paths.extend(COMBINED_TABLES[table])
            else:
                print(f"sp_schema: {table} is not combined table!")

    def walk(prop, path="", parent_key=""):
        """Walk through schema"""
        todo = deque([(prop, "", "")])
        while todo:
            prop, path, parent_key = todo.pop()
            if prop.get("deprecated"):
                return
            properties = prop.get("properties", {})
            if properties:
                for key, item in properties.items():
                    if item.get("deprecated"):
                        continue
                    if hasattr(item, "__reference__") and item.__reference__.get("deprecated"):
                        continue
                    pointer = "/".join([path, key])
                    typeset = extract_type(item)
                    if "object" in typeset:
                        todo.append((item, pointer, key))
                    elif "array" in typeset:
                        items = item["items"]
                        items_type = extract_type(items)
                        if set(items_type) & {"array", "object"}:
                            todo.append((items, pointer, key))
                            yield pointer + "Count"
                        else:
                            yield pointer
                    else:
                        if combined_paths:
                            for p in combined_paths:
                                if common_prefix(p, pointer) == p:
                                    yield "/" + "/".join((parent_key, key))
                                    # break
                        yield pointer

    data = json.loads(fileobj.read().decode())
    schema = jsonref.JsonRef.replace_refs(data)
    for pointer in walk(schema):
        yield 1, "", pointer, ""

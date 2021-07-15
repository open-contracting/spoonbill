import gettext
import json
import locale
from collections import deque
from functools import lru_cache

import jsonref
import pkg_resources

from spoonbill.common import COMBINED_TABLES
from spoonbill.utils import common_prefix, extract_type

DOMAIN = "spoonbill"
LOCALEDIR = pkg_resources.resource_filename(DOMAIN, "locales/")
LOCALE = "en_US"

system_locale = locale.getdefaultlocale()
if system_locale and system_locale[0]:
    LOCALE = system_locale[0]


def translate(msg_id, lang=LOCALE):
    """Simple wrapper of python's gettext with ability to override desired language"""
    try:
        translator = _translation(lang)
    except FileNotFoundError:
        LOCALE = "en_US"
        lang = LOCALE
        translator = _translation(lang)

    if translator:
        return translator.gettext(msg_id)
    return msg_id


@lru_cache(maxsize=None)
def _translation(lang):
    return gettext.translation(DOMAIN, LOCALEDIR, languages=[lang], fallback=None)


_ = translate


# slightly modified version of ocds-babel's extract_schema
# TODO: discuss upstreaming this extractor
def extract_schema_po(fileobj, keywords, comment_tags, options):
    """
    Yields json path values of a JSON Schema file.
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

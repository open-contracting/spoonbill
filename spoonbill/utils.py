import gzip
import re
from collections import OrderedDict

import jsonref
from scalpl import Cut

GZIP_MAGIC_NUMBER = (b"\x1f", b"\x8b")


def get_reader(path):
    """
    Get reader function for a respective file format
    :param path: path to a file
    :return: reader function
    """
    with open(path, "rb") as f:
        first_bytes = f.read(2)
    if (first_bytes[0:1], first_bytes[1:2]) == GZIP_MAGIC_NUMBER:
        return gzip.open
    else:
        return open


def nonschema_title_formatter(title):
    """
    Formatting a path, that is absent in schema, to human-readable form
    :param title: str
    :return: formatted title

    >>> nonschema_title_formatter('legalEntityTypeDetail')
    'Legal Entity Type Detail'
    >>> nonschema_title_formatter('fuenteFinanciamiento')
    'Fuente Financiamiento'
    >>> nonschema_title_formatter('Óóó-Ñññ_Úúú')
    'Óóó Ñññ Úúú'
    """
    title = title.replace("_", " ").replace("-", " ")
    title = re.sub(r"(?<![A-Z])(?<!^)([A-Z])", r" \1", title)
    title = title.replace("  ", " ").replace("/", ": ")
    if title.startswith(": "):
        title = title[2:]
    title = title.title()
    return title


class SchemaHeaderExtractor:
    """
    Human-readable headers extracted from schema

    :param schema: The dataset's schema
    """

    def __init__(self, schema):
        self.schema = schema
        if not isinstance(self.schema, jsonref.JsonRef) and not isinstance(self.schema, OrderedDict):
            self.schema = jsonref.JsonRef.replace_refs(self.schema)

    def _get_header(self, id, paths):
        final_title = []
        for path in paths:
            _object = Cut(self.schema)["properties." + ".".join(path[:-1])]
            if hasattr(_object, "__reference__") and "title" in _object.__reference__:
                title = _object.__reference__["title"]
            else:
                title = Cut(self.schema)["properties." + ".".join(path)]
            if isinstance(title, dict):
                continue
            final_title.append(title)
        if id.startswith("/documents"):
            final_title = final_title[3:]
        if "Organization reference" in final_title:
            final_title.remove("Organization reference")
        return ": ".join(final_title)

    def get_header(self, id, paths):
        if paths and isinstance(paths, list):
            return self._get_header(id, paths)
        elif paths == []:
            return nonschema_title_formatter(id)
        else:
            return nonschema_title_formatter(paths)

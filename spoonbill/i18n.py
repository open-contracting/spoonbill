import atexit
import contextlib
import functools
import gettext
import locale
import warnings

try:
    import importlib_resources
except ImportError:
    import importlib.resources as importlib_resources

# https://importlib-resources.readthedocs.io/en/latest/migration.html#pkg-resources-resource-filename
file_manager = contextlib.ExitStack()
atexit.register(file_manager.close)
ref = importlib_resources.files("spoonbill") / "locale"
path = file_manager.enter_context(importlib_resources.as_file(ref))

LOCALE = "en"
language_code = locale.getlocale()[0]
if language_code and language_code != "C":  # None if LC_CTYPE=C or LC_CTYPE=UTF-8
    # Windows can set the locale to "English_United States", which fails normalization. "English" succeeds, but is
    # normalized as en_EN.ISO8859-1. So, we split again.
    LOCALE = locale.normalize(language_code.split("_")[0]).split("_")[0]


def translate(msg_id, lang=LOCALE):
    """Wrap Python's gettext with ability to override desired language."""
    return translator(lang).gettext(msg_id)


@functools.cache
def translator(lang):
    try:
        return gettext.translation("spoonbill", path, languages=[lang], fallback=None)
    except FileNotFoundError as e:
        warnings.warn(f"{e.strerror} {e.filename} in language {lang}", stacklevel=2)
        return gettext.NullTranslations()


_ = translate

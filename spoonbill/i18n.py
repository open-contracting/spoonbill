import gettext
import locale
import warnings
from functools import lru_cache

import pkg_resources

DOMAIN = "spoonbill"
LOCALEDIR = pkg_resources.resource_filename(DOMAIN, "locale/")
LOCALE = "en"

language_code, encoding = locale.getlocale()
if language_code:
    # Windows can set the locale to "English_United States", which fails normalization. "English" succeeds, but is
    # normalized as en_EN.ISO8859-1. So, we split again.
    LOCALE = locale.normalize(language_code.split("_")[0]).split("_")[0]


def translate(msg_id, lang=LOCALE):
    """Simple wrapper of python's gettext with ability to override desired language"""
    return translator(lang).gettext(msg_id)


@lru_cache(maxsize=None)
def translator(lang):
    try:
        return gettext.translation(DOMAIN, LOCALEDIR, languages=[lang], fallback=None)
    except FileNotFoundError as e:
        warnings.warn(f"{e.strerror} {e.filename} in language {lang}")
        return gettext.NullTranslations()


_ = translate

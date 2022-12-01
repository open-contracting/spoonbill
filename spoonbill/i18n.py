import gettext
import locale
import warnings
from functools import lru_cache

import pkg_resources

DOMAIN = "spoonbill"
LOCALEDIR = pkg_resources.resource_filename(DOMAIN, "locale/")
LOCALE = "en"

system_locale = locale.getlocale()
if system_locale and system_locale[0]:
    LOCALE = system_locale[0]


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

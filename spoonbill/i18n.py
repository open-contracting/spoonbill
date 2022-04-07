import gettext
import locale
from functools import lru_cache

import pkg_resources

DOMAIN = "spoonbill"
LOCALEDIR = pkg_resources.resource_filename(DOMAIN, "locales/")
LOCALE = "en"

system_locale = locale.getdefaultlocale()
if system_locale and system_locale[0]:
    LOCALE = system_locale[0]


def translate(msg_id, lang=LOCALE):
    """Simple wrapper of python's gettext with ability to override desired language"""
    try:
        translator = _translation(lang)
    except FileNotFoundError:
        LOCALE = "en"
        lang = LOCALE
        translator = _translation(lang)

    if translator:
        return translator.gettext(msg_id)
    return msg_id


@lru_cache(maxsize=None)
def _translation(lang):
    return gettext.translation(DOMAIN, LOCALEDIR, languages=[lang], fallback=None)


_ = translate

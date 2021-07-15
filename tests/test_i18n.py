from spoonbill.cli import ANALYZED_LABEL
from spoonbill.i18n import translate


def test_translate_absent_locale():
    translation = translate(ANALYZED_LABEL, "uk_UA")
    assert translation == ANALYZED_LABEL

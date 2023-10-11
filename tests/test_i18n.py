import pytest

from spoonbill.cli import ANALYZED_LABEL
from spoonbill.i18n import translate


def test_translate_absent_locale():
    with pytest.warns(UserWarning) as records:
        translation = translate(ANALYZED_LABEL, "uk_UA")
        assert translation == ANALYZED_LABEL

    assert str(records[0].message) == "No translation file found for domain spoonbill in language uk_UA"
    assert len(records) == 1


def test_translate():
    translation = translate(ANALYZED_LABEL, "es")
    assert translation == "  {} objetos procesados"

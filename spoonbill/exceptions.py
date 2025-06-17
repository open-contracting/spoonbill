class SpoonbillWarning(UserWarning):
    """Base class for warnings from within this package."""


class UnsupportedLanguageWarning(SpoonbillWarning):
    """Used when a translation file can't be found."""

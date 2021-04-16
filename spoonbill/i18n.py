import gettext
from pathlib import Path

domain = "spoonbill"
locale_dir = str(Path(__file__).parent / "locales")

try:
    t = gettext.translation(domain, locale_dir)
    _ = t.gettext
except FileNotFoundError:
    _ = lambda m: m  # noqa: E731

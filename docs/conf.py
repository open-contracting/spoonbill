import os
import sys
import sphinx_rtd_theme

sys.path.insert(0, os.path.abspath('..'))


# -- Project information -----------------------------------------------------
project = 'spoonbill'
copyright = '2021, Open Contracting Partnership'
author = 'Open Contracting Partnership'
release = '0.0.1'


# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    "sphinx_rtd_theme",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']

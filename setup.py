from setuptools import find_packages, setup

with open("README.rst") as f:
    long_description = f.read()


requires = [
    "ijson>=2.5",
    "jsonref",
    "jsonpointer",
    "xlsxwriter",
    "requests",
    "click",
    "click_logging",
    "ocdskit",
    "ocdsextensionregistry",
    'dataclasses;python_version<"3.7"',
]
test_requires = ["pytest", "jmespath", "pytest-cov", "coveralls", "openpyxl", "jsonpointer"] + requires
docs_requires = [
    "Sphinx",
    "sphinx-autobuild",
    "sphinx-rtd-theme",
    "sphinx_click",
    "sphinx_changelog",
]

setup(
    name="spoonbill",
    version="1.0.1b1",
    author="Open Contracting Partnership",
    author_email="data@open-contracting.org",
    url="https://github.com/open-contracting/spoonbill",
    description="An instrument to flatten OCDS data",
    license="BSD",
    packages=find_packages(exclude=["tests", "tests.*"]),
    long_description=long_description,
    install_requires=requires,
    extras_require={
        "test": test_requires,
        "docs": docs_requires,
    },
    package_data={"spoonbill": ["locales/*/*/*.mo", "locales/*/*/*.po"]},
    include_package_data=True,
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={
        "console_scripts": ["spoonbill = spoonbill.cli:cli"],
        "babel.extractors": [
            "sp_schema = spoonbill.i18n:extract_schema_po",
        ],
    },
)

from setuptools import find_packages, setup

with open("README.rst") as f:
    long_description = f.read()

__pkg__ = "spoonbill"
__version__ = "1.0.9b10"


setup(
    name=__pkg__,
    version=__version__,
    author="Open Contracting Partnership",
    author_email="data@open-contracting.org",
    url="https://github.com/open-contracting/spoonbill",
    description="Converts data that conforms to the Open Contracting Data Standard from JSON to Excel / CSV",
    license="BSD",
    packages=find_packages(exclude=["tests", "tests.*"]),
    long_description=long_description,
    include_package_data=True,
    install_requires=[
        "click",
        "click_logging",
        "flatten-dict",
        "ijson>=2.5",
        "jsonref",
        "ocdsextensionregistry",
        "ocdskit>=1.0.1",
        "requests",
        "scalpl",
        "setuptools",
        "xlsxwriter",
        'dataclasses;python_version<"3.7"',
    ],
    extras_require={
        "test": [
            "coveralls",
            "jsonpointer",
            "jmespath",
            "openpyxl",
            "pytest",
            "pytest-cov",
        ],
        "docs": [
            "furo",
            "sphinx",
            "sphinx-autobuild",
            "sphinx_click",
        ],
    },
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    entry_points={
        "console_scripts": [
            "spoonbill = spoonbill.cli:cli",
        ],
        "babel.extractors": [
            "sp_schema = spoonbill.i18n:extract_schema_po",
        ],
    },
)

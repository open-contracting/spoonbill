from setuptools import find_packages, setup

with open("README.rst") as f:
    long_description = f.read()

__pkg__ = "spoonbill"
__version__ = "1.0.9b9"


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
        "ijson>=2.5",
        "jsonpointer",
        "jsonref",
        "ocdsextensionregistry",
        "ocdskit>=1.0.1",
        "requests",
        "xlsxwriter",
        'dataclasses;python_version<"3.7"',
        "flatten-dict",
        "scalpl",
    ],
    extras_require={
        "test": [
            "coveralls",
            "jmespath",
            "openpyxl",
            "pytest",
            "pytest-cov",
        ],
        "docs": [
            "sphinx<4",
            "sphinx-autobuild",
            "sphinx-rtd-theme",
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

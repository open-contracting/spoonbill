Library Usage
=============

File Analyzer
-------------

Analyze file
~~~~~~~~~~~~

To create analyzer object, use:

.. code-block:: python

    from spoonbill import  FileAnalyzer
    from spoonbill.common import ROOT_TABLES, COMBINED_TABLES

    analyzer = FileAnalyzer(
        '.',
        schema=path_to_schema,
        root_tables=ROOT_TABLES,
        combined_tables=COMBINED_TABLES,
        language='en',
        table_threshold=5,
    )

To analyze file and track progress, use:

.. code-block:: python

    for bytes_read, count in analyzer.analyze_file(path_to_file):
        print(f'analyzed {count} ({bytes_read})')

Storing state
~~~~~~~~~~~~~

To dump state file after analysis, use:

.. code-block:: python

    analyzer.dump_to_file('analyzed.state')

.. Note::

    This sile may be re-used for new instance of analyzer. Can be used to omit anlysis step in case of multiple flatteting of the same file.

To restore from state, use:

.. code-block:: python

    analyzer = FileAnalyzer('.', state_file='analyzed.state')

Flattener
---------

Flattening options
~~~~~~~~~~~~~~~~~~

To create flattening options and extract only table and split if its possible,(*for example, tenders*) use:

.. code-block:: python

    from spoonbill.flatten import FlattenOptions

    options = FlattenOptions({"selection": {"tenders": {"split": True}}})

To select multiple tables (*for example, tender and parties*), use:

.. code-block:: python

    from spoonbill.flatten import FlattenOptions

    options = FlattenOptions(**{
        "selection": {
            "tenders": {"split": True},
            "parties": {"split": True}
        }
    })

Flatten file
~~~~~~~~~~~~

To flatten file, use:

.. code-block:: python

    from spoonbill import FileFlattener

    flattener = FileFlattener(
        '.',
        options,
        analyzer,
        csv=True, # Generate csv files
        xlsx=True, # Generate xlsx files
        language='en',
    )

    for count in flattener.flatten_file(filename):
        print(f'Flattened {count} items')

.. note::

    Please note that flattening routine requires data to be analyzed beforehand.

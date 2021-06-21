Command-Line Interface
======================

To see all options available, run:

.. code-block:: bash

   spoonbill --help

To flatten a file, run:

.. code-block:: bash

   spoonbill filename.json

The inputs can be `concatenated JSON <https://en.wikipedia.org/wiki/JSON_streaming#Concatenated_JSON>`_ or an OCDS `release <https://standard.open-contracting.org/latest/en/schema/release_package/>`_ or `record package <https://standard.open-contracting.org/latest/en/schema/record_package/>`_.

Choose output formats
---------------------

Spoonbill creates a ``result.xlsx`` file in the current path by default.

To change the name or location of the Excel file, use the `\--xlsx <#cmdoption-spoonbill-xlsx>`_ option. For example:

.. code-block:: bash

   spoonbill --xlsx path/to/file.xlsx filename.json

To *also* write CSV files to an existing directory, use the `\--csv <#cmdoption-spoonbill-csv>`_ option. For example:

.. code-block:: bash

   spoonbill --csv directory/ filename.json

To *only* write CSV files, set ``--xlsx ""``, for example:

.. code-block:: bash

   spoonbill --csv directory/ --xlsx "" filename.json

Change column headings
----------------------

The default headings are JSON paths, like ``/tender/procurementMethod``.

To change the headings to human-readable English text, run:

.. code-block:: bash

   spoonbill --human filename.json

To change the headings to human-readable Spanish text, run:

.. code-block:: bash

   spoonbill --human --language es filename.json

.. warning::

    Please note, ``-- language`` would not do any changes unless used in combination with ``-- human``.

.. _combine-tables:

Combine related tables
----------------------

During :ref:`analysis<how-it-works>`, each array within the JSON file is assigned to a separate table. However, if an array always contains a small number of entries, it is often preferable to combine its corresponding table with its parent table.

For example, let's say there are at most two identifiers per organization. Separated tables might look like this (omitting the ``ocid``, ``id`` and ``parentTable`` columns for simplicity):

.. list-table:: parties
   :widths: auto
   :header-rows: 1

   * - rowID
     - parentID
     - /parties/name
     - /parties/id
   * - ocds-213czf-1/tender/parties:1
     - ocds-213czf-1/tender
     - Acme Inc.
     - 1

.. list-table:: parties_ids
   :widths: auto
   :header-rows: 1

   * - rowID
     - parentID
     - /parties/additionalIdentifiers/scheme
     - /parties/additionalIdentifiers/id
   * - ocds-213czf-1/tender/additionalIdentifiers:254900UIZS15MTA7H075
     - ocds-213czf-1/tender/parties:1
     - XI-LEI
     - 254900UIZS15MTA7H075
   * - ocds-213czf-1/tender/additionalIdentifiers:example
     - ocds-213czf-1/tender/parties:1
     - XE-EXAMPLE
     - example

Instead of creating separate tables, the two tables can be combined. That way, you can read an organization's identifiers without performing a lookup across the two tables.

.. list-table::
   :widths: auto
   :header-rows: 1

   * - rowID
     - parentID
     - /parties/name
     - /parties/id
     - /parties/additionalIdentifiers/0/scheme
     - /parties/additionalIdentifiers/0/id
     - /parties/additionalIdentifiers/1/scheme
     - /parties/additionalIdentifiers/1/id
   * - ocds-213czf-1/tender/parties:1
     - ocds-213czf-1/tender
     - Acme Inc.
     - 1
     - XI-LEI
     - 254900UIZS15MTA7H075
     - XE-EXAMPLE
     - example

You will notice that the ``additionalIdentifiers`` columns now contain indexes – ``0`` and ``1`` – to group the columns for each identifier.

By default, tables are combined if the child table has less than 5 entries for any given row in the parent table. This threshold can be changed with the `\--threshold <#cmdoption-spoonbill-threshold>`_ option. For example:

.. code-block:: bash

   spoonbill --threshold 3 filename.json

To disable this feature, set the threshold to 1. For example:

.. code-block:: bash

   spoonbill --threshold 1 filename.json

Storing objects that follow the same schema in the same table
-------------------------------------------------------------

OCDS JSON format is described using JSON Schema, and reuses the same schema in multiple locations. For example, an array of ``document`` objects is allowed under five different objects (Award, Contract, etc.).

``spoobill`` would combine those five ``document`` locations into a single table, in cases where the user research indicates this preference.

Currently, ``spoonbill`` supports combining following object types:

.. hlist::
   :columns: 1

   -  documents
   -  ammendments
   -  milestones

This behavior can be overitten, by invoking ``combine`` command. To combine only ``document`` arrays, and ommit ``milestones, ammendments``, use:

.. code-block:: bash

   spoonbill --combine documents filename.json

Select which data to output
---------------------------

Choose initial tables
~~~~~~~~~~~~~~~~~~~~~

By default, these initial tables are written:

.. hlist::
   :columns: 3

   -  parties
   -  planning
   -  tenders
   -  awards
   -  contracts

To change which initial tables are written, use the `\--selection <#cmdoption-spoonbill-selection>`_ option. For example:

.. code-block:: bash

   spoonbill --selection parties,tenders filename.json

Exclude child tables
~~~~~~~~~~~~~~~~~~~~

Child tables might be written for the initial tables (see :ref:`combine-tables`).

To exclude child tables from being written, use the `\--exclude <#cmdoption-spoonbill-exclude>`_ option. For example:

.. code-block:: bash

   spoonbill --exclude parties_ids,tenders_items_class filename.json

Choose columns
~~~~~~~~~~~~~~

OCDS data can contain hundreds of columns. If you only need a small number of columns, use the `\--only <#cmdoption-spoonbill-only>`_ option. For example:

.. code-block:: bash

   spoonbill --only /parties/name,/parties/id filename.json

Instead of writing a long list of columns on the command line, you can provide a file with one column per line, using the `\--only-file <#cmdoption-spoonbill-only-file>`_ option. For example:

.. code-block:: bash

   spoonbill --only-file columns.txt filename.json

Copy data between tables
------------------------

Unnest columns from child tables into parent tables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To copy a few columns from a child table to a parent table, use the `\--unnest <#cmdoption-spoonbill-unnest>`_ option. For example:

.. code-block:: bash

   spoonbill --unnest /tender/items/0/id,/tender/items/0/description filename.json

Instead of writing a long list of columns on the command line, you can provide a file with one column per line, using the `\--unnest-file <#cmdoption-spoonbill-unnest-file>`_ option. For example:

.. code-block:: bash

   spoonbill --unnest-file columns.txt filename.json

Repeat columns from parent tables into child tables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To repeat a column from a parent table into a child table, use the `\--repeat <#cmdoption-spoonbill-repeat>`_ option. For example:

.. code-block:: bash

   spoonbill --repeat /parties/name,/parties/id filename.json

Instead of writing a long list of columns on the command line, you can provide a file with one column per line, using the `\--repeat-file <#cmdoption-spoonbill-repeat-file>`_ option. For example:

.. code-block:: bash

   spoonbill --repeat-file columns.txt filename.json

Add calculated values
---------------------

Count the number of child rows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It can be helpful to know the number of related entries in a child table while viewing a parent row. To add columns with these numbers, use the `\--count <#cmdoption-spoonbill-count>`_ option.

This will add, for example, a ``/tender/itemsCount`` column to the ``tenders`` table, with the number of entries in the ``/tender/items`` array that are related to each row.

.. code-block:: bash

   spoobill --count filename.json

Advanced features
-----------------

To flatten a file with a local schema instead of the default schema, run:

.. code-block:: bash

   spoonbill --schema schema.json filename.json

To reuse a :ref:`state file<how-it-works>` to flatten another file with the same characteristics, run:

.. code-block:: bash

   spoonbill --state-file filename.json.state filename.json

Reference
---------

.. click:: spoonbill.cli:cli
   :prog: spoonbill
   :nested: full

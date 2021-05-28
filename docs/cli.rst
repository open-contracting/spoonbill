Command-Line Interface
======================

To see all options available, run:

.. code-block:: bash

   spoonbill --help

To flatten a file, run:

.. code-block:: bash

   spoonbill filename.json

Change the headings
-------------------

The default headings are JSON paths, like ``/tender/procurementMethod``.

To change the headings to human-readable English text, run:

.. code-block:: bash

   spoonbill --human filename.json

To change the headings to human-readable Spanish text, run:

.. code-block:: bash

   spoonbill --human --language es filename.json

.. _combine-tables:

Combine child tables with parent tables
---------------------------------------

During :ref:`analysis<how-it-works>`, each array within the JSON file is assigned to a separate table. However, if an array always contains a small number of entries, it is often preferable to combine its corresponding table with its parent table.

For example, let's say there are at most two identifiers per organization. Separated tables might look like this:

.. list-table:: parties
   :widths: auto
   :header-rows: 1

   * - ocid
     - id
     - rowID
     - parentID
     - /parties/name
     - /parties/id
   * - ocds-213czf-1
     - tender
     - ocds-213czf-1/tender/parties:1
     - Acme Inc.
     - 1

.. list-table:: parties_ids
   :widths: auto
   :header-rows: 1

   * - ocid
     - id
     - rowID
     - parentID
     - parentTable
     - /parties/additionalIdentifiers/scheme
     - /parties/additionalIdentifiers/id
   * - ocds-213czf-1
     - tender
     - ocds-213czf-1/tender/parties:1/additionalIdentifiers:1
     - ocds-213czf-1/tender/parties:1
     - XI-LEI
     - 254900UIZS15MTA7H075
   * - ocds-213czf-1
     - tender
     - ocds-213czf-1/tender/parties:1/additionalIdentifiers:2
     - ocds-213czf-1/tender/parties:1
     - XE-EXAMPLE
     - example

Instead of creating separate tables, the ``parties_ids`` table can be combined into the ``parties`` table. That way, you can read an organization's identifiers without performing a lookup across the two tables.

.. list-table:: parties
   :widths: auto
   :header-rows: 1

   * - ocid
     - id
     - rowID
     - parentID
     - /parties/name
     - /parties/id
     - /parties/additionalIdentifiers/0/scheme
     - /parties/additionalIdentifiers/0/id
     - /parties/additionalIdentifiers/1/scheme
     - /parties/additionalIdentifiers/1/id
   * - ocds-213czf-1
     - tender
     - ocds-213czf-1/tender/parties:1
     - Acme Inc.
     - 1
     - XI-LEI
     - 254900UIZS15MTA7H075
     - XE-EXAMPLE
     - example

Note that the ``additionalIdentifiers`` columns contain indexes – ``0`` and ``1`` – to group the columns for each identifier.

By default, a child table is combined with its parent table if the child table never has more than 5 entries for a given row in the parent table. This threshold can be changed with the :option:`threshold` option. For example:

.. code-block:: bash

   spoonbill --threshold 3 filename.json

To disable this feature, set the threshold to 1. For example:

.. code-block:: bash

   spoonbill --threshold 1 filename.json

Select which data to output
---------------------------

Choose initial tables
~~~~~~~~~~~~~~~~~~~~~

By default, these initial tables are written:

-  parties
-  planning
-  tenders
-  awards
-  contracts

To change which initial tables are written, use the :option:`selection` option. For example:

.. code-block:: bash

   spoonbill --selection parties,tenders filename.json

Exclude child tables
~~~~~~~~~~~~~~~~~~~~

Child tables might be written for the initial tables (see :ref:`combine-tables`).

To exclude child tables from being written, use the :option:`exclude` option. For example:

.. code-block:: bash

   spoonbill --exclude parties_ids,tenders_items_class filename.json

Choose columns
~~~~~~~~~~~~~~

OCDS data can contain hundreds of columns. If you only need a small number of columns, use the :option:`only` option. For example:

.. code-block:: bash

   spoonbill --only /parties/name,/parties/id filename.json

Instead of writing a long list of columns on the command line, you can provide a file with one column per line, using the :option:`only-file` option. For example:

.. code-block:: bash

   spoonbill --only-file columns.txt filename.json

Copy data between tables
------------------------

Unnest columns from child tables into parent tables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To copy a few columns from a child table to a parent table, use the :option:`unnest` option. For example:

.. code-block:: bash

   spoonbill --unnest /tender/items/0/id,/tender/items/0/description filename.json

Instead of writing a long list of columns on the command line, you can provide a file with one column per line, using the :option:`unnest-file` option. For example:

.. code-block:: bash

   spoonbill --unnest-file columns.txt filename.json

Repeat columns from parent tables into child tables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To repeat a column from a parent table into a child table, use the :option:`repeat` option. For example:

.. code-block:: bash

   spoonbill --repeat /parties/name,/parties/id filename.json

Instead of writing a long list of columns on the command line, you can provide a file with one column per line, using the :option:`repeat-file` option. For example:

.. code-block:: bash

   spoonbill --repeat-file columns.txt filename.json

Add calculated values
---------------------

Count the number of child rows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It can be helpful to know the number of related entries in a child table while viewing a parent row. To add columns with these numbers, use the :option:`count` option.

This will add, for example, a ``/tender/itemsCount`` column to the ``tenders`` table, with the number of entries in the ``/tender/items`` array that are related to each row.

.. code-block:: bash

   --count

Advanced features
-----------------

To flatten a file with a local schema instead of the default schema, run:

.. code-block:: bash

   spoonbill --schema schema.json filename.json

Spoonbill analyzes the input data to determine which columns and tables to write. It stores the results of its analysis in a state file. To reuse a state file to flatten a file with the same characteristics, run:

.. code-block:: bash

   spoonbill --state-file filename.json.state filename.json

Reference
---------

.. click:: spoonbill.cli:cli
   :prog: spoonbill
   :nested: full

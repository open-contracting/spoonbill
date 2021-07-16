OCDS Spoonbill |release|
========================

.. include:: ../README.rst

This documentation describes the :doc:`command-line tool <cli>` and :doc:`Python library <api>`. Spoonbill is also accessible as a web application (URL pending).

Installation
------------

From the command line:

.. code-block:: bash

   pip install spoonbill

Spoonbill requires Python 3.6 or greater.

.. _how-it-works:

How it works
------------

Spoonbill reads the JSON file once to **analyze** its structure. It stores the results of its analysis in a "state file". It then reads the JSON file a second time to **write** the tables.

Spoonbill aims to improve the user experience when working with tables by:

-  Reducing the number of Excel sheets and/or CSV files you need to work with.

   -  OCDS allows arrays of ``Document`` objects in five locations (under ``planning``, ``tender``, etc.). Instead of creating one table per location, Spoonbill combines documents into one table. It does the same for milestones and amendments.
   -  Some arrays always have few entries within a given dataset: for example, an organization's identifiers. Instead of creating a new table, Spoonbill merges short arrays into their parent table.

-  Providing :doc:`options <cli>` to customize the layout of the tables to fit your needs.

Row relations through parentID and rowID
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If ``id`` column is equal to the ``id`` column of table object (For example ``items/id``) than the ``rowID`` is a concatenation of ``{ocid}/{field_name}:{id}`` for root tables and ``{parentID}/{field_name}:{id}`` for child tables.

The ``field_name`` is the field name of the array, and the ``id`` is the value of the ``id`` field of the item in the array.

For example, the contracts table for a compiled release might have a rowID of ``ocds-lcuori-1/contracts:1`` then, the contracts items table might have a rowID of ``ocds-lcuori-1/contracts:1/items:1`` and so on.

Similar to ``rowID``, each child table contains ``parentID`` column, which is corresponding ``rowID`` of parent table.

Each non-root table contains ``parentTable`` column, which corresponse to the name of the sheet.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   cli
   library
   api
   tables
   contributing
   changelog

Copyright (c) 2021 Open Contracting Partnership, released under the BSD license

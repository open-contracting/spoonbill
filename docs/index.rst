OCDS Spoonbill |release|
========================

.. include:: ../README.rst

This documentation describes the :doc:`command-line tool <cli>` and :doc:`Python library <api>`. Spoonbill is also accessible as a web application (URL pending).

Installation
------------

From the command line:

.. code-block:: bash

   pip install spoonbill

To improve performance, install the `YAJL <http://lloyd.github.io/yajl/>`__ system library (on macOS, run ``brew install yajl``).

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

.. toctree::
   :maxdepth: 2
   :caption: Contents

   cli
   api
   contributing
   changelog

Copyright (c) 2021 Open Contracting Partnership, released under the BSD license

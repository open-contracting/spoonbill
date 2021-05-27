Spoonbill |release|
===================

.. include:: ../../README.rst

To install:

.. code-block:: bash

    pip install spoonbill

To improve performance, install the `YAJL <http://lloyd.github.io/yajl/>`__ system library (for example, on macOS, run ``brew install yajl``).

Spoonbill requires Python 3.6 or greater.

Goals
-----

Spoonbill aims to improve the user's experience by:

#. Reducing the number of tables:

   -  OCDS allows arrays of ``Document`` objects in five locations (under ``planning``, ``tender``, etc.). Instead of creating one table per location, Spoonbill combines documents into one table. It does the same for milestones and amendments.
   -  Some arrays always have few entries within a given dataset: for example, an organization's identifiers. Instead of creating a new table, Spoonbill merges short arrays into their parent table.

#. Exploring the dataset to see what fields are available and customization to fit your requirements.


.. toctree::
   :maxdepth: 2
   :caption: Contents

   cli-usage
   flattenning-conf
   cli
   api
   contributing
   changelog

Copyright (c) 2021 Open Contracting Partnership, released under the BSD license

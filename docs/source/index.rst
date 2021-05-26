.. spoonbill documentation master file, created by
   sphinx-quickstart on Mon Apr 19 15:11:07 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

+++++++++++++++++++++++++++++++++++++
Welcome to spoonbill's documentation!
+++++++++++++++++++++++++++++++++++++

The primary use case for OCDS Flatten Tool is to convert data that conforms to the Open Contracting Data Standard from JSON to Excel / CSV (*hereinafter tables*).

It aims to improve the user's experience with performing a simple transformation of JSON to tables by:

1. Mitigating a high number of tables through rollup of top-level arrays into the initial table.
2. Exploring the dataset to see what fields are available and customization to fit your requirements.
3. Storing objects that follow the same schema in the same table. For example, an array of Document objects is allowed under 5 different objects (Award, Contract, Planning, Tenders,Implementation) woud be created as a single table.
4. test.


.. toctree::
   :maxdepth: 2

   getting-started
   cli_usage
   cli
   api
   developer-guide
   change-log

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. spoonbill documentation master file, created by
   sphinx-quickstart on Mon Apr 19 15:11:07 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#####################################
Welcome to spoonbill's documentation!
#####################################

The primary use case for OCDS Flatten Tool is to convert data that conforms to the Open Contracting Data Standard from JSON to Excel / CSV (*hereinafter tables*).

It aims to improve the user's experience with performing a simple transformation of JSON to tables by:

1. Mitigating a high number of tables through rollup of top-level arrays into the root table.
For example, an array of ``Document`` objects is allowed under 5 different objects (``Award, Contract, Planning, Tenders,Implementation``) woud be created as a single root table.
2. Exploring the dataset to see what fields are available and customization to fit your requirements.
3. Rolling up short arrays into parent tables. If an array consistently has a small number of entries, it can be moved into its root table, with additional columns for each entry.

For users which are not familiar with the command line, this tool is available as web interface to perform and configure the conversion.

.. toctree::
   :maxdepth: 2

   getting-started
   cli-usage
   flattenning-conf
   cli
   api
   developer-guide
   change-log

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

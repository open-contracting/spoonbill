*********
Spoonbill
*********

Spoonbill is a library and command-line tool to convert OCDS data from JSON to Excel/CSV

Installation
############

Use the package manager `pip <https://pip.pypa.io/en/stable/>`_ to install spoonbill.

.. code-block:: bash

   pip install spoonbill

Features
############

The primary use case for OCDS Flatten Tool is to convert data that conforms to the Open Contracting Data Standard from JSON to Excel / CSV (*hereinafter tables*).

It aims to improve the user's experience with performing a simple transformation of JSON to tables by:

1. Mitigating a high number of tables through rollup of top-level arrays into the initial table.
2. Exploring the dataset to see what fields are available and customization to fit your requirements.
3. Storing objects that follow the same schema in the same table. For example, an array of Document objects is allowed under 5 different objects (Award, Contract, Planning, Tenders,Implementation) woud be created as a single table.

For more examples see `documentation <https://open-contracting.github.io/spoonbill/index.html>`_

*********
Spoonbill
*********

Spoonbill is a library and command-line tool to convert OCDS data from JSON to Excel/CSV 

Installation
############

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install spoonbill.

.. code-block:: bash

   pip install spoonbill

Features
############

* Convert data from json to csv and xlsx sheets
* Generate state file with analyzed data from intput file
* Use a JSON schema to guide the approach to flattening
* Use a JSON schema to provide column titles rather than field names
* Output tables selection
* Same datatypes from different locations could be combined into one table

  
Usage
############


.. code-block:: bash

   spoonbill --selection tenders,parties tests/data/ocds-sample-data.json

Contributing
############
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

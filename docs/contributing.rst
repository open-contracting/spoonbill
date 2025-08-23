Contributing
============

Setup
-----

Clone the repository:

.. code-block:: bash

   git clone git@github.com:open-contracting/spoonbill.git
   cd spoonbill

Create a virtual environment. For example:

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate

Install the development requirements:

.. code-block:: bash

   pip install -e .[test] babel

Install the pre-commit script:

.. code-block:: bash

   pip install pre-commit
   pre-commit install

Testing
-------

Compile the message catalogs:

.. code-block:: bash

   pybabel compile -f -d spoonbill/locale -D spoonbill

Run the tests:

.. code-block:: bash

   pytest

If you want to lint the working copy, use following command:

.. code-block:: bash

   pre-commit run -a

Translation
-----------

Extract messages:

.. code-block:: bash

   pybabel extract -o spoonbill/locale/messages.pot .
   pybabel update -N -i spoonbill/locale/messages.pot -d spoonbill/locale -D spoonbill

Edit PO files to translate strings.

Finally, compile catalogs:

.. code-block:: bash

   pybabel compile -f -d spoonbill/locale -D spoonbill

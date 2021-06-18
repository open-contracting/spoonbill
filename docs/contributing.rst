Contributing
============

Installation
------------

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

   pip install -e .[test]

Install the pre-commit script:

.. code-block:: bash

   pip install pre-commit
   pre-commit install

Tests
-----

Run the tests:

.. code-block:: bash

   pytest

If you want to lint the working copy, use following command:

.. code-block:: bash

   pre-commit run -a

Commit messages
---------------

Follow the `Conventional Commits <https://www.conventionalcommits.org/en/v1.0.0/>`_ specification.

Package releases
----------------

This package is versioned. A changelog is maintained.

To prepare a changelog for a new release from the commit history, you can use `semantic-release <https://github.com/relekang/python-semantic-release>`_. For example:

.. code-block:: bash

   semantic-release changelog

To create new release use:

.. code-block:: bash

   semantic-release version

.. note::
      Please keep in mind than semantic-release does not recognize `pre-release <https://github.com/relekang/python-semantic-release/issues/267>`_ versions.

You can then convert the file to reStructuredText with `pandoc <https://pandoc.org>`_:

.. code-block:: bash

   pandoc --from=rst --to=markdown --wrap=none --output=CHANGELOG.rst CHANGELOG.md

And copy the new content into ``docs/changelog.rst``.

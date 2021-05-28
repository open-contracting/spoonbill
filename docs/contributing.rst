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

Run the linters:

.. code-block:: bash

   pre-commit run -a

Commit messages
---------------

Follow the `Conventional Commits <https://www.conventionalcommits.org/en/v1.0.0/>`_ specification.

Package releases
----------------

This package is versioned. A changelog is maintained.

To prepare a changelog for a new release from the commit history, you can use `conventional-changelog-cli <https://github.com/conventional-changelog/conventional-changelog/tree/master/packages/conventional-changelog-cli>`_. For example:

.. code-block:: bash

   conventional-changelog -i CHANGELOG.md -s -p angular

You can then convert the file to reStructuredText with `pandoc <https://pandoc.org>`_:

.. code-block:: bash

   pandoc --from=rst --to=markdown --wrap=none --output=CHANGELOG.md CHANGELOG.rst

And copy the new content into ``docs/changelog.rst``.

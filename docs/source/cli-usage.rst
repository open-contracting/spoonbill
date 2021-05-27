.. _usage_examples:

*****
Usage
*****

To see all options available, run:

.. code-block:: bash

    spoonbill --help

To flatten file, run:

.. code-block:: bash

    spoonbill filename.json

To flatten file with human-friendly headings, run:

.. code-block:: bash

    spoonbill --human filename.json

To flatten file with human-friendly headings, translated to a different language(in example, spanish), run:

.. code-block:: bash

    spoonbill --human --language es filename.json

To flatten file with the local shema instead of default shema, run:

.. code-block:: bash

    spoonbill --schema schema.json filename.json

To flatten file using state file with analyzed data(As a default this file is generated as artifact of flattening process), run:

.. code-block:: bash

    spoonbill --state-file statefilename filename.json

To flatten file with selecting specific root tables(in ex. parties and tenders), run:

.. code-block:: bash

    spoonbill --selection parties,tenders filename.json

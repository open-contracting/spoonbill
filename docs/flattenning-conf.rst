*************************
Flattenning configuration
*************************

Threshold
=========

To ease user experience of analyzing data Spoonbill tool provides configuration of ``threshold``. It allows to indicate on which amount of arrays system should split array table from root table.

As a default it is configured to split root table when array has ``>=5`` items.

To change treshhold (`in ex. for 3`), run:

.. code-block:: bash

    --treshhold 3

Selection
=========


For cases when user is not planning to work with all root tables, tool provides ``selection`` configuration.

To select which root tables should be used for flattening (`in ex. tenders,parties`), run:

.. code-block:: bash

    --selection tenders,parties

In cases when root tables would have an arrays bigger than ``threshold``, tool would create an additional array tables.

For example, if ``parties`` table whould contain array of ``parties/additionalIdentifiers`` which have arrays items equal to or exceeding ``threshold``, flattening would create two tables `Parties` and `Parties.additionalIdentifiers`.

Exclude array table
-------------------

For cases when an additional array table would not be needed, tool allows to exclude it from use.

To exclude table from use (`i.. code-block:: bashn ex. Parties.additionalIdentifiers`), run:

.. code-block:: bash

    --exclude parties_ids

Repeating columns from root table
---------------------------------

To improve usability of array table, tool supports extending of array table structure with additional columns repeated from root table.

To repeat a column from a root table into array table (`in ex. parties name and id`), run:

.. code-block:: bash

    --repeat /parties/name,/parties/id

To simplify ``repeat`` command tool provides an option to use plaintext file as indication of columns to be repeated. Such file should contain newline separated column ids.

.. code-block:: bash

    --repeat-file filename

Unnesting columns from array table
----------------------------------

For cases when array table is not needed as a whole, but part of information is usefull to be included in root table, tool allows to transfer columns from array table to root table.

To include columns from array table to root table (`in ex. /tender/items/id and /tender/items/description`), run:

.. code-block:: bash

    --unnest /tender/items/0/id,/tender/items/0/description

Similar to ``repeat-file`` tool provides ``unnest-file`` command which allows to use plaintext file as indication of columns to be unnested. Such file should contain newline separated column ids.

.. code-block:: bash

    --unnest-file filename

Coulmns specification
---------------------

In case when user requires only specific set of data  in a table, tool provides ability to indicate list of columns to be used.

To specify which column table should keep, (`in ex. keep only /parties/name and /parties/id`) run:

.. code-block:: bash

    --only /parties/name,/parties/id

Similar to others, tool offers ``only-file`` command which allows to use use plaintext file as indication of columns to be included in a table. Such file should contain newline separated column ids.

.. code-block:: bash

    --only-file filename

Count
=====

To display a number of array items in a root table as a separate value, tool foresees ``count`` command.

.. code-block:: bash

    --count

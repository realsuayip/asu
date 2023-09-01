Handling Python Requirements
============================

This project uses :code:`pip-tools` to **lock** Python requirements. Each
requirement must be specified in :code:`pyproject.toml` and then locked via
:code:`pip-compile`. Development and production requirements are seperated. The
relevant commands for generating lock files are:

For development:

.. code-block:: shell

    pip-compile --extra=dev --output-file=deps/dev.txt pyproject.toml


For production:

.. code-block:: shell

    pip-compile --allow-unsafe --extra=prod --generate-hashes --output-file=deps/prod.txt pyproject.toml


If you're upgrading packages, make sure to add :code:`--upgrade` flag.

Once you update the dependencies, rebuild the project and make sure the tests
are passing.

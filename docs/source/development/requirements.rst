.. _handling-requirements:

##############################
 Handling Python Requirements
##############################

This project uses ``uv`` to **lock** Python requirements. Each
requirement must be specified in ``pyproject.toml`` and then locked via
``uv lock``. Development and production requirements are separated via
dependency groups.

If you're upgrading packages, make sure to add ``--upgrade`` flag.

Once you update the dependencies, rebuild the project and make sure the
tests are passing.

Code Style
==========

The project uses variety of tools (including formatters and linters) to ensure
the code is written in a consistent manner.

* For formatting Python files, use the latest :code:`black`.
* For linting, use the latest :code:`ruff`. Ruff is also used to sort imports.

Make sure you have :code:`pre-commit` in your environment and project hooks are
installed to your Git directory. Pre-commit configuration includes other useful
checks as well as the tools listed above.

Here is a checklist you can use just before committing:

*   Check :code:`pre-commit` hooks are passing:

    .. code-block:: shell

        make format

*   Check typing errors:

    .. code-block:: shell

        make type

*   Run tests:

    .. code-block:: shell

            make test

    Additionally, you may check coverage stats to see if you have
    missed any important lines:

    .. code-block:: shell

            make coverage

    .. warning::

            If you have changed any of the project dependencies (e.g. Python
            requirements or Docker image tags), you need to rebuild Docker
            image(s) before running tests.

*   If new documentation is added, make sure it builds and content is rendered
    properly:

    .. code-block:: shell

            make docs

*   Finally, if developing an API, check the OpenAPI documentation. It should
    render properly and present appropriate information.

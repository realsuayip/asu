Type hints
==========

This project is typed, and types are checked using :code:`mypy`, in strict mode.
To check types use:

.. code-block:: shell

    make type

If you're adding a new (untyped) Python package, search for external type stubs
and (if found) consider adding them to development requirements.

Do not use :code:`type: ignore` excessively. Only ignore typing errors that
cannot be resolved within the project (i.e., 3rd party package issues). When
ignoring a typing error, be specific; avoid catch-all ignore statements and
file-wide ignores.

Typing is not necessary for tests.

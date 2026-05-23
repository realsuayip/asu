############
 Code Style
############

Make sure you have ``pre-commit`` in your environment and project hooks
are installed to your Git directory.

Here is a checklist you can use just before committing:

-  Check ``pre-commit`` hooks are passing:

   .. code:: shell

      just format

-  Check typing errors:

   .. code:: shell

      just type

-  Run tests:

   .. code:: shell

      just test

   Additionally, you may check coverage stats to see if you have missed
   any important lines:

   .. code:: shell

      just coverage

   .. warning::

      If you have changed any of the project dependencies (e.g. Python
      requirements or Docker image tags), you need to rebuild Docker
      image(s) before running tests.

-  If new documentation is added, make sure it builds and content is
   rendered properly:

   .. code:: shell

      just docs

-  Finally, if developing an API, check the OpenAPI documentation. It
   should render properly and present appropriate information.

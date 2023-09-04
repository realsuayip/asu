.. _configuration-management:

Configuration
=============

Once in a while, you will require adding new configuration options to the
project. There are two ways to do it:

1. Add the variable as environment variable. If the variable changes,
project will need re-deployment. This is useful if the variable does not
change too frequently and accessed frequently. To add the variable you'll
need to edit related environment file in :code:`conf` folder and add the
definition to Django settings file.

.. warning::

    Avoid loading configuration from files or any other medium that is not
    **environment variables**. Do not override environment variables dynamically.
    The configuration should only be fetched from statically loaded
    environment variables (i.e., Docker compose :code:`env` or :code:`env_file`
    directives or Kubernetes :code:`envFrom` directive).

2. Add the variable dynamically, using :code:`ProjectVariable` table. In
this case, the variable will be fetched from the database (and will be
cached in Redis for subsequent access). This is useful if the variable
changes frequently and re-deployment is too disruptive.

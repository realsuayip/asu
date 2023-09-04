Layout
======

Here are the root directories with their purposes:

* :code:`asu`

This is the root code directory. All Python code resides here.

* :code:`conf`

This directory contains project configuration files. See
:ref:`configuration-management` to learn about configuring using
environment variables.

* :code:`deps`

This directory contains lock files for Python dependencies. See
:ref:`handling-requirements` to learn about requirement pinning.

* :code:`tests`

This directory contains all the tests. See :ref:`writing-tests`.

* :code:`docs`

This directory contains documentation files, like this one you are reading
right now.

* :code:`docker`

This directory contains all Docker-related configuration files.


* :code:`k8s`

This directory contains all Kubernetes-related configuration files.

Understanding the Code Directory
--------------------------------

If you visit :code:`asu` directory, you'll see that it contains :code:`apps.py`
file. In installed apps, this app is also mentioned. This means that **the root
code directory also acts a Django app**.

This **root app** is useful to put project-wide code that is not assignable to
specific apps. For example, if you have an utility that is used by multiple
apps, you can define the utility there (hence the :code:`asu.utils` module).

Many projects usually use a :code:`core` app (or module) that contains
project-wide logic. However, this is not the case here; if you have such code,
put them in root. For example, the model :code:`ProjectVariable` is a
project-wide one since all apps may require dynamic configuration. As a result,
model definitions are made in module :code:`asu.models`.

It is also common to put :code:`settings.py` and root URL configuration—:code:`urls.py`
(along with :code:`wsgi.py` and :code:`asgi.py` files) in a separate folder
(in fact, the default Django boilerplate is created that way). However, in this
project, those files are treated as a part of root app, hence the current
arrangement.

App templates, template tags, static files, tests and fixtures should also
reside in root with each app having their own sub-directory. For example,
instead of :code:`app/templates/index.html` use :code:`templates/app/index.html`.

Other than these, the project follows the standard: Django apps placed in the
code directory.

.. important::

    Apps should be used to divide code into relevant parts. Do not work too hard
    on creating self-contained apps. Most of the time, apps are highly coupled
    and cannot work on their own.

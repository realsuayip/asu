Getting Started
===============

To serve the project, you'll at least need Docker with compose plugin
installed. First off, clone the project:

.. code-block:: shell

    git clone https://github.com/realsuayip/asu


Navigate to the root directory, and run:

.. code-block:: shell

    make

Makefile also includes helper targets that can execute related Docker
commands, if you don't have GNU make at your disposal, you may also use the
docker commands directly:

.. code-block:: shell

    docker-compose -p asu -f docker/docker-compose.yml up


If you are using it for the first time, it might take a while to set up the
containers. Once the containers are up and running, you may navigate to
`127.0.0.1:8000/api/ <http://127.0.0.1:8000/api/>`_ to browse the API.

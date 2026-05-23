#################
 Getting Started
#################

To serve the project, you'll at least need Docker with compose plugin
installed. First off, clone the project:

.. code:: shell

   git clone https://github.com/realsuayip/asu

Navigate to the root directory, and run:

.. code:: shell

   just

This project uses `just <hhttps://github.com/casey/just/>`__ command
runner, to see available commands, run:

.. code:: shell

   just --list

If you are using it for the first time, it might take a while to set up
the containers. Once the containers are up and running, you may navigate
to `127.0.0.1:8000/api/ <http://127.0.0.1:8000/api/>`_ to browse the
API.

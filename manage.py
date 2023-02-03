#!/usr/bin/env python
import os
import sys


def main():
    context = os.environ.get("CONTEXT")
    # Default to docker helper module to work with Docker containers,
    # then exit. For example:
    #   $ CONTEXT=setup python manage.py up
    # The command above will build and run all containers.
    if context == "setup":
        from docker.cli import entrypoint

        entrypoint()

    # The command is running inside the docker container, so run usual
    # Django management stuff.
    from django.core.management import execute_from_command_line

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zaida.settings")
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

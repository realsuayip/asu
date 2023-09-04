Home
====

.. toctree::
    :hidden:
    :maxdepth: 3
    :caption: Contents:

    self
    features
    getting-started
    development/index
    license

This is a comprehensive Django project for reference. The project roughly
constitutes a real-time chat application with **complete** user management.

You may use this as a base project (for your projects themed as social media
websites, community forums etc.) or you can scrap the parts you don't need and
bootstrap a highly optimized Django project.


The project is an example of a standard Django stack, the components being:

* Postgres (database)
* Redis (cache & channel layer)
* RabbitMQ (message broker)
* Celery (task queue)
* Nginx (reverse proxy)

All of these components are available through Docker setup (for both
production and development environments).

There is also single-node-ready Kubernetes configuration that can be adjusted
to support multiple nodes.

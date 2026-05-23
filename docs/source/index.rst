######
 Home
######

.. toctree::
   :hidden:
   :maxdepth: 3
   :caption: Contents:

   self
   features
   getting-started
   development/index

This is a comprehensive Django project for reference.

You may use this as a base project or you can scrap the parts you don't
need and bootstrap a highly optimized Django project.

The project is an example of a standard Django stack, the components
being:

-  Postgres (database)
-  Redis (cache & channel layer)
-  RabbitMQ (message broker)
-  Celery (task queue)
-  Nginx (reverse proxy)

All of these components are available through Docker setup (for both
production and development environments).

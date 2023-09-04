# asu

[![codecov](https://codecov.io/github/realsuayip/asu/branch/main/graph/badge.svg?token=A0BJ9TINW1)](https://codecov.io/github/realsuayip/asu)

Documentation available at: [https://asu.readthedocs.io](https://asu.readthedocs.io)

This is a comprehensive Django project for reference. The project roughly
constitutes a real-time chat application with **complete** user management (see
feature rundown for details).

You may use this as a base project (for your projects themed as social media
websites, community forums etc.) or you can scrap the parts you don't need and
bootstrap a highly optimized Django project.

## Major features

* Authentication & Account Management
    * OAuth 2.0 (Authorization Code with PKCE & Client Credentials)
    * Two-factor authentication
    * CRU operations
    * Blocking operations
    * Following operations
      * Follow requests
      * Ability to mark profile as 'private'
    * Profile pictures
      * Thumbnail generation
      * Image validation
          * Image scaling & compression on upload
          * Mime type validation
* Verifications (all flows employ email confirmation)
    * Registration flow
      * No account generation before email validation.
    * Password reset flow
    * Email change flow
* Messaging
    * CRUD operations
    * One-to-one conversations & messaging
    * Message requests
    * Read receipts
    * Ability to disable messages from strangers
    * Instant messaging with WebSocket
      *  Ticket-based authentication

Notice that interactions of these features are well-handled. For instance,
users with blocking relations may not message each other. You may message
your followers without having them accept your message request (and so on).

## Technical details

The project is an example of a standard Django stack, the components being:

* Postgres (database)
* Redis (cache & channel layer)
* RabbitMQ (message broker)
* Celery (task queue)
* Nginx (reverse proxy)

All of these components are available through Docker setup (for both
production and development environments).

There is also single-node-ready Kubernetes configuration that can easily be
adjusted to support multiple nodes.

The project has a high test coverage and all the major features are
well-tested.

## Installation

To serve the project, you'll at least need Docker with compose plugin
installed. First off, clone the project:

```shell
git clone https://github.com/realsuayip/asu
```

Navigate to the root directory, and run:

````shell
make
````

Makefile also includes helper targets that can execute related Docker
commands, if you don't have GNU make at your disposal, you may also use the
docker commands directly:

````shell
docker-compose -p asu -f docker/docker-compose.yml up
````

If you are using it for the first time, it might take a while to set up the
containers. Once the containers are up and running, you may navigate to
[`127.0.0.1:8000/api/`](http://127.0.0.1:8000/api/) to browse the API.

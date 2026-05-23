# asu

[![codecov](https://codecov.io/github/realsuayip/asu/branch/main/graph/badge.svg?token=A0BJ9TINW1)](https://codecov.io/github/realsuayip/asu)

Documentation available at: [https://asu.readthedocs.io](https://asu.readthedocs.io)

This is a comprehensive Django project for reference.

You may use this as a base project, or you can scrap the parts you don't need and
bootstrap a highly optimized Django project.

## Features

* Authentication & Account Management
    * OAuth 2.0 (Authorization Code with PKCE & Client Credentials)
    * Two-factor authentication
    * CRUD operations
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
    * Password reset flow
    * Email change flow

## Technical details

The project is an example of a standard Django stack, the components being:

* Postgres (database)
* Redis (cache)
* RabbitMQ (message broker)
* Celery (task queue)
* Nginx (reverse proxy)

All of these components are available through Docker setup (for both
production and development environments).

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
just
````

This project uses [just](<hhttps://github.com/casey/just/>) command
runner, to see available commands, run:

````shell
just --list
````

If you are using it for the first time, it might take a while to set up the
containers. Once the containers are up and running, you may navigate to
[`127.0.0.1:8000/api/`](http://127.0.0.1:8000/api/) to browse the API.

[WikiClip](README.md) > Getting Started

# Getting Started

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
    - [Get the repository](#get-the-repository)
    - [Using `venv` to manage your Python environment \[TBD\]](#using-venv-to-manage-your-python-environment-tbd)
    - [Install dependencies](#install-dependencies)
  - [Configuration](#configuration)
  - [Set environment variables](#set-environment-variables)
    - [Invoke command usage](#invoke-command-usage)
  - [Building and running the service](#building-and-running-the-service)
    - [The API key](#the-api-key)
    - [Local development](#local-development)
  - [Dependencies](#dependencies)
  - [Migrations](#migrations)
  - [Testing the Service \[TBD\]](#testing-the-service-tbd)
  - [Swagger](#swagger)
  - [Deployment](#deployment)
  - [API](#api)

This service is available in the following environments:
1 - Production at https://prod.XXX [TBD]
2 - Staging at https://staging.XXX [TBD]
3 - Development at: https://dev.XXX [TBD]
4 - Local at: [http://localhost:17000](localhost:17000).

## Prerequisites

Docker and Git are essential tools in the realm of development.
It's important to have them installed and properly configured on your computer,
as they are fundamental for nearly all types of development projects.
Their utility spans a wide range of applications,
making them indispensable for modern development workflows.:

- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Git](https://git-scm.com/downloads)

## Installation

### Get the repository

```
git clone https://github.com/Echo-Harbor-Press/ehp-core.git
cd ehp-core
```

### Using `venv` to manage your Python environment [TBD]

Although not strictly necessary, we recommend you use a `virtual environment` to isolate
the Python environments for your various projects. For a thorough intro to doing that,
see [this tutorial](https://realpython.com/intro-to-pyenv/).
For WikiClip app on a Mac or Linux based SO, it works like this:

```
python -m venv ./venv/
source ./venv/bin/activate
```

### Install dependencies

To install Python dependencies needed to build ehp-core, do the following:

```
pip-compile requirements/requirements.in
pip install -r requirements/requirements.txt
```

At this point, you should be able to run `invoke -l` or `ìnv -l` and see a list of
commands.

## Configuration

## Set environment variables

Building, running, and syncing ehp-core requires certain environment variables to
be set. In general, any command that depends on a service connection will require
environment variables.

The environment variables are defined in a configuration file, `.env`, that
should be placed in the root folder of the repository (that is, the `ehp-core` folder):

```
ehp-core/
├── docs/
├── ehp/
├── migrations/
├── requirements/
├── tasks/
├── application.py
├── .env -- This should not be uploaded to the repository.
├── .env.example
├── .flake8
├── .mypy.ini
├── ...
└── docker files...
```

Due to the sensitive nature of certain values, such as secret keys, we cannot store the
`.env` file on GitHub. However, for your convenience, we provide a `.env.example` file.
This file outlines the usual structure and the set of environment variables commonly used
by our developers. It's advisable to use this example as a template: simply copy it and
rename it to `.env`. For any additional details or to obtain missing secret values,
please reach out to a fellow engineer who can assist you.

### Invoke command usage

Python Invoke is a task execution library, much like Make or Rake, but with Python's
capabilities and flexibility. It allows you to write tasks as Python functions and
execute them via command-line calls. The Invoke library is particularly useful for
automating tasks in software development workflows, such as building, testing, deploying,
or managing various project-related activities.

Weé set up a few tasks that the developer can use to speed up the implementation.
For example:

```
invoke build -- builds the docker image.
```

```
invoke run -- runs the docker image.
```

`inv` can be used as a shorthand for `invoke` in any of the above commands, so

```
invoke build -- builds the docker image.
```

```
invoke run -- runs the docker image.
```

also works.

Please, use this tasks for your convenience. If you want to add more tasks, you can.

Migrate Database

```bash
inv migrate
```

To initialize the database run

```bash
inv init-db
```

And execute the output SQL code in the SQL client

Run the test suit

```bash
inv pytest
```

Run code formatters and linters

```bash
inv lint
```

Stop the Application

```bash
inv kill
```

Open Shell in the Main Container

```bash
inv connect
```

Open Python shell with all core development modules already imported

```bash
inv shell
```

Start Containers (Non-detached mode)

```bash
inv run
```

Restart the services

```bash
inv restart
```

Create New migrations

```bash
inv db-make-migrations
```

Compile requirements

```bash
inv pip-compile
```

## Building and running the service

First, run `inv build` in the repository's root directory. This command will
[build a Docker container](https://docs.docker.com/compose/overview/) that can
run the service locally.

Finally, run `inv run` to start the container for the service.

Successful completion looks like:

```
 ➜ invoke run
Running the raw command 'docker-compose up -d'.

Starting etai-core-app ... done
Running the raw command 'python3 application.py'.

 * Serving Flask app "application" (lazy loading)
 * Environment: dev
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
 * Running on http://0.0.0.0:17000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 516-474-444
```

You can access the service at:

```
Meta endpoint: http://localhost:17000/_meta (Requires API key)
Swagger endpoint: http://localhost:17000/docs
Authentication Page: http://localhost:17000/
```

### The API key

If you need to access external services, you will receive the message
`ERROR: Unauthorized`. This is because the service endpoints are protected by a
secret token/key that needs to be passed with each request.

When accessing the service API, you will need to provide the same API key you have set
in the `X-Api-Key` environment variable in your `.env`.

And also a `X-User-Key` header in the request. This key is created through the system
in the User Key form, and should be done locally and in every environment.

For example, if you want to access the endpoints, you need to add a variable named
`X-Api-Key=X_API_KEY_VALUE`
and
`X-Token-Auth=X_USER_KEY_VALUE`, in every request, regardless of methods.

### Local development

At this point, you're all set up and ready to develop locally. Changes you make while
coding will force FastAPI to restart, meaning you shouldn't have to `inv run` more
than once. (Syntax errors can cause FastAPI to crash, however, so there may be times
when you need to restart while editing code.)

There are unit tests and style checks that can be run with `inv pytest`,
`inv flake8`, `inv black`, and `inv mypy`. If you want to run the all together you should
run `inv lint`.

## Dependencies

If you need to update Python dependencies, you should update `requirements/requirements.in`,
run `inv pip-compile` to rebuild `requirements/requirements.txt`. These changes should be committed
to Git. If other engineers update Python dependencies, you will need to do `inv build` to
update your Docker container.

## Migrations

In order to setup the local database proceed with:

```
inv migrate -- It will (try to) initialize the database, create the migration's files and upgrade the database.
```

Otherwise you should run:

```
inv db-upgrade -- This will upgrade the current database to the latest version and preload the initial data.
```

## Testing the Service [TBD]

You can test that the service is running and functioning by hitting the following endpoint:
LOCAL http://localhost:17000/_meta
This is the meta endpoints, so it is not necessary to send the API key. Other endpoints
need the `X-Api-Key` in the request header.

## Swagger

API documentation is automatically created by Swagger.
To access the documentation refer to https://localhost:9020/docs

## Deployment

[TBD]

## API

The API entry points are developed in FastAPI which is responsible for processing
incoming requests, validating ownership and security tokens and exposes Swagger
documentation. All incoming requests will undergo the following steps:

1.  **Identity Validation:** The identity validation process aims at recognizing if all
    incoming requests are from a reliable source. It must contain a header variable named
    `X-Api-Key`, and `X-Token-Auth` with App’s APP Key.

        *Implementation: annotate fastapi route to validate the header.*

        - *The `needs_api_key` and `authorized_session` annotations are available in the Repository.*
        - *The key is stored in a variable called `X_API_KEY_VALUE` in the `config/ehp_core.py` file.*
        - *The user key is stored in the database and should be created locally*
        - *Make sure you have all service keys set in the `settings` object.*

2. **Special Identity Validation Cases:** For routes that require direct user interaction, like forgot password flow or change email flow,
  where the user needs to click a generated link and will not have access to any Header, we use a separate router to avoid the
  `needs_api_key` validation, as can be seen in the `application.py` file. This will allow the application to receive a valid JWT in the 
  `x-token-auth` query param. Example:
```python
from ehp.base.middleware import authorized_session
from ehp.utils.authentication import needs_api_key

# Application is instantiated with the authorized_session to close all routes to at least
# one form of authentication
app = Fastapi(..., dependencies=[Depends(authorized_session)])

# main_router where most routes will be assigned to uses needs_api_key to enforce X-Api-Key
# requirements.
main_router = APIRouter(dependencies=[Depends(needs_api_key)])

# if there is a special route that needs to not use api key
# we can register directly to the app instead

app.include_router(my_unkeyed_router)

# or 

@app.get("/specific-unclosed-resource")
async def do_something(): ...
```


- Health endpoints:
  - Meta: general service information.
    1. https://[HOST:PORT]/
    2. https://[HOST:PORT]/_meta

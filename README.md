# Online Cinema API

REST API for an online cinema service built with FastAPI.

The project provides user registration and account activation, JWT
authentication, password reset, movie catalog browsing, favorites, shopping
cart management, asynchronous email delivery, scheduled cleanup tasks,
Docker infrastructure, automated tests, and CI.

## Technologies

- Python 3.12
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2
- Alembic
- Pydantic
- JWT
- Argon2 password hashing
- Celery
- Redis
- Mailpit
- MinIO
- Docker
- Docker Compose
- Poetry
- Pytest
- pytest-cov
- flake8
- GitHub Actions

## Implemented Features

The project implements the following main business features.

### 1. Registration and Account Activation

Users can create an account using an email address and password.

New accounts are inactive by default.

After registration:

- an activation token is generated;
- the token is valid for 24 hours;
- an activation email is queued through Celery;
- the account can be activated using the received token.

Main endpoints:

```text
POST /accounts/register
POST /accounts/activate
```

### 2. Resend Activation Token

An inactive user can request a new activation token.

When a new token is generated:

- the previous activation token is replaced;
- the new token is valid for 24 hours;
- a new activation email is queued asynchronously.

Endpoint:

```text
POST /accounts/activation/resend
```

### 3. JWT Authentication

The application uses access and refresh JWT tokens.

After successful login:

- an access token is generated;
- a refresh token is generated;
- the refresh token is stored in the database.

The access token is used to access protected API endpoints.

The refresh token can be used to obtain a new access token.

Logout invalidates the supplied refresh token by removing it from the
database.

Endpoints:

```text
POST /accounts/login
POST /accounts/refresh
POST /accounts/logout
```

### 4. Password Reset

Users can request a password reset.

A password reset token is generated and an email is queued through Celery.

The token can then be used to set a new password.

Endpoints:

```text
POST /accounts/password-reset/request
POST /accounts/password-reset/confirm
```

### 5. Movie Catalog

The movie catalog supports:

- movie list;
- movie details;
- pagination;
- title search;
- genre filtering;
- certification filtering;
- release year filtering;
- sorting;
- ascending and descending ordering.

Endpoints:

```text
GET /movies
GET /movies/{movie_id}
```

Example:

```text
GET /movies?page=1&page_size=10&search=Matrix&sort_by=title&order=asc
```

### 6. Favorites

Authenticated users can manage their favorite movies.

Supported operations:

- add a movie to favorites;
- list favorite movies;
- remove a movie from favorites.

Endpoints:

```text
POST   /favorites/{movie_id}
GET    /favorites
DELETE /favorites/{movie_id}
```

JWT authentication is required.

### 7. Shopping Cart

Authenticated users can manage movies in their shopping cart.

Supported operations:

- add a movie to the cart;
- list cart contents;
- remove a movie from the cart;
- clear the entire cart.

Adding the same movie to the cart more than once is prevented.

Endpoints:

```text
POST   /cart/{movie_id}
GET    /cart
DELETE /cart/{movie_id}
DELETE /cart
```

JWT authentication is required.

## Background Tasks

Celery is used for asynchronous and scheduled tasks.

Implemented tasks include:

- activation email delivery;
- password reset email delivery;
- expired activation token cleanup.

Redis is used as the Celery broker and result backend.

Celery Worker executes background tasks.

Celery Beat runs scheduled tasks.

## Email Development Environment

Mailpit is used as the local SMTP server.

When the project is running with Docker Compose, the Mailpit web interface is
available at:

```text
http://localhost:8025
```

Application emails can be inspected there during development.

## MinIO

MinIO is included in the Docker infrastructure and provides an
S3-compatible object storage service for future media/file storage
functionality.

MinIO API:

```text
http://localhost:9000
```

MinIO Console:

```text
http://localhost:9001
```

MinIO is currently part of the project infrastructure; movie media upload
functionality is not implemented as one of the selected business features.

## Project Structure

```text
online-cinema/
├── .github/
│   └── workflows/
│       └── ci.yml
├── migrations/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── src/
│   ├── accounts/
│   │   ├── dependencies.py
│   │   ├── email.py
│   │   ├── models.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── services.py
│   │   └── tasks.py
│   ├── carts/
│   │   ├── models.py
│   │   └── router.py
│   ├── config/
│   │   └── settings.py
│   ├── database/
│   │   ├── base.py
│   │   └── session.py
│   ├── favorites/
│   │   ├── models.py
│   │   └── router.py
│   ├── movies/
│   │   ├── models.py
│   │   ├── router.py
│   │   └── schemas.py
│   ├── celery_app.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_accounts.py
│   ├── test_auth_tokens.py
│   ├── test_cart.py
│   ├── test_dependencies.py
│   ├── test_docs.py
│   ├── test_email.py
│   ├── test_favorites.py
│   ├── test_health.py
│   ├── test_movies.py
│   ├── test_password_reset.py
│   └── test_tasks.py
├── .dockerignore
├── .env.sample
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── poetry.lock
├── pyproject.toml
└── README.md
```

## Environment Configuration

Create the local environment configuration from the example:

```bash
cp .env.sample .env.docker
```

Example configuration:

```env
POSTGRES_USER=cinema
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=online_cinema

JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

SMTP_HOST=mailpit
SMTP_PORT=1025
EMAIL_FROM=noreply@online-cinema.local

DOCS_USERNAME=admin
DOCS_PASSWORD=change-me-docs-password

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=change-me-minio-password
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=online-cinema
```

Do not commit real credentials or secrets.

The `.env` and `.env.docker` files are excluded from Git.

## Running with Docker

Docker and Docker Compose are required.

Build and start the application:

```bash
docker compose --env-file .env.docker up -d --build
```

Check running services:

```bash
docker compose --env-file .env.docker ps
```

The following services are started:

```text
db
redis
mailpit
minio
web
celery_worker
celery_beat
```

The FastAPI application is available at:

```text
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

MinIO health check:

```bash
curl -I http://localhost:9000/minio/health/live
```

Stop the containers:

```bash
docker compose --env-file .env.docker down
```

To also delete persistent Docker volumes:

```bash
docker compose --env-file .env.docker down -v
```

Use `down -v` carefully because PostgreSQL and MinIO persistent data will be
removed.

## Database Migrations

Alembic is used for database migrations.

Apply all migrations:

```bash
poetry run alembic upgrade head
```

Check the current migration:

```bash
poetry run alembic current
```

View migration history:

```bash
poetry run alembic history
```

Create a new migration:

```bash
poetry run alembic revision --autogenerate -m "Migration description"
```

## API Documentation

The project provides OpenAPI documentation using Swagger UI and ReDoc.

Documentation access is protected with HTTP Basic authentication.

Swagger UI:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

OpenAPI schema:

```text
http://localhost:8000/openapi.json
```

The credentials are configured through:

```env
DOCS_USERNAME=admin
DOCS_PASSWORD=your-password
```

Requests without valid documentation credentials receive:

```text
401 Unauthorized
```

Example:

```bash
curl -u admin:your-password http://localhost:8000/openapi.json
```

HTTP Basic authentication protects access to the documentation itself.

JWT Bearer authentication is used separately for protected application
endpoints such as Favorites and Cart.

## Using JWT Authentication in Swagger

First log in using:

```text
POST /accounts/login
```

The response contains:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

In Swagger UI, click **Authorize** and provide the access token.

After authorization, protected endpoints can be executed directly from
Swagger UI.

## Local Development with Poetry

Install Poetry if it is not already installed.

Install project dependencies:

```bash
poetry install --no-root
```

The project requires Python 3.12 or newer.

Run FastAPI locally:

```bash
poetry run uvicorn src.main:app --reload
```

For local execution outside Docker, environment variables such as the
PostgreSQL host, Redis host, and SMTP host must point to services accessible
from the host machine.

## Tests

The project uses Pytest.

Run all tests:

```bash
pytest -q
```

The test suite covers:

- registration;
- account activation;
- activation token resend;
- JWT login;
- access and refresh tokens;
- logout;
- authentication dependencies;
- password reset;
- movie catalog;
- movie filtering and sorting;
- favorites;
- shopping cart;
- email delivery;
- Celery tasks;
- protected API documentation;
- application health check.

Run a specific test file:

```bash
pytest tests/test_movies.py -v
```

Run tests matching a name:

```bash
pytest -k activation -v
```

## Test Coverage

Coverage is measured using `pytest-cov`.

Run:

```bash
pytest --cov=src --cov-report=term-missing
```

An XML coverage report can be generated with:

```bash
pytest \
  --cov=src \
  --cov-report=term-missing \
  --cov-report=xml
```

At the current project state, the complete test suite contains 74 passing
tests and provides approximately 77% total source coverage.

## Code Quality

flake8 is used for static style checking.

Run:

```bash
flake8 src tests migrations
```

Before submitting changes, run:

```bash
flake8 src tests migrations
pytest -q
```

## CI

GitHub Actions is configured in:

```text
.github/workflows/ci.yml
```

The CI pipeline runs for pushes and pull requests targeting `main` or
`develop`.

The pipeline:

1. starts PostgreSQL;
2. starts Redis;
3. installs Python 3.12;
4. installs Poetry;
5. installs project dependencies;
6. creates the test database;
7. runs flake8;
8. runs the complete test suite;
9. generates test coverage information.

## Git Workflow

Development uses feature branches.

The main branches are:

```text
main
develop
```

Features are implemented in dedicated branches and then integrated through
the development workflow.

Examples used during development include:

```text
feature/project-setup
feature/accounts-registration
feature/email-celery
feature/api-documentation
feature/docker-infrastructure
feature/ci-pipeline
feature/final-polish
```

Commit messages describe the implemented change, for example:

```text
Implement user registration endpoint
Implement JWT login refresh and logout
Implement password reset functionality
Implement movie catalog
Implement favorites functionality
Implement shopping cart functionality
Add asynchronous email delivery and token cleanup
Improve OpenAPI documentation
Add Docker infrastructure
Add CI pipeline
Protect API documentation
```

## API Overview

| Method | Endpoint | Description | Authentication |
|---|---|---|---|
| POST | `/accounts/register` | Register user | No |
| POST | `/accounts/activate` | Activate account | No |
| POST | `/accounts/activation/resend` | Resend activation token | No |
| POST | `/accounts/login` | Login | No |
| POST | `/accounts/refresh` | Refresh access token | Refresh token |
| POST | `/accounts/logout` | Logout | Refresh token |
| POST | `/accounts/password-reset/request` | Request password reset | No |
| POST | `/accounts/password-reset/confirm` | Set new password | Reset token |
| GET | `/movies` | Movie catalog | No |
| GET | `/movies/{movie_id}` | Movie details | No |
| GET | `/favorites` | Favorite movies | JWT |
| POST | `/favorites/{movie_id}` | Add favorite | JWT |
| DELETE | `/favorites/{movie_id}` | Remove favorite | JWT |
| GET | `/cart` | Shopping cart | JWT |
| POST | `/cart/{movie_id}` | Add movie to cart | JWT |
| DELETE | `/cart/{movie_id}` | Remove movie from cart | JWT |
| DELETE | `/cart` | Clear cart | JWT |
| GET | `/health` | Application health | No |

## Security

The project includes:

- Argon2 password hashing;
- JWT access tokens;
- JWT refresh tokens;
- refresh token persistence;
- refresh token invalidation during logout;
- password validation;
- account activation;
- expiring activation tokens;
- expiring password reset tokens;
- protected application endpoints;
- protected Swagger/ReDoc/OpenAPI documentation;
- environment-based secrets.

Production deployments must use strong unique values for:

```text
POSTGRES_PASSWORD
JWT_SECRET_KEY
DOCS_PASSWORD
MINIO_ROOT_PASSWORD
```

Development credentials from example configuration must not be reused in
production.

## Current Scope

This implementation focuses on seven selected business features:

1. registration and account activation;
2. activation token resend;
3. JWT login, refresh and logout;
4. password reset;
5. movie catalog;
6. favorites;
7. shopping cart.

Orders and payment processing are outside the selected implementation scope.

MinIO is available as infrastructure, but media upload/storage endpoints are
not part of the currently implemented feature set.

## Author

Maksym Kaplunovskyi

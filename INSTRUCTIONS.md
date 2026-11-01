# INSTRUCTIONS.md: Complete Production Flask API with Pydantic & JWT Authentication

This document is an all-in-one implementation guide and reference for building an idiomatic, test-driven REST API in Flask using **Pydantic (v2)** for data parsing and validation, **SQLAlchemy** for persistence, **PyJWT** for stateless authentication, **Pytest** for test automation, and **uv** for package and project management.

---

## Table of Contents

1. [Architecture & File Map](#1-architecture--file-map)
2. [Prerequisites & Dependencies (`pyproject.toml`)](#2-prerequisites--dependencies-pyprojecttoml)
3. [Configuration (`src/flask_api/config.py`)](#3-configuration-srcflask_apiconfigpy)
4. [Database Models (`src/flask_api/models.py`)](#4-database-models-srcflask_apimodelspy)
5. [Pydantic Schemas (`src/flask_api/schemas.py`)](#5-pydantic-schemas-srcflask_apischemaspy)
6. [JWT & Validation Utilities (`src/flask_api/auth/utils.py`)](#6-jwt--validation-utilities-srcflask_apiauthutilspy)
7. [Authentication Endpoints (`src/flask_api/auth/routes.py`)](#7-authentication-endpoints-srcflask_apiauthroutespy)
8. [Global Error Handlers (`src/flask_api/errors/handlers.py`)](#8-global-error-handlers-srcflask_apierrorshandlerspy)
9. [Application Factory & Entrypoint (`src/flask_api/__init__.py`)](#9-application-factory--entrypoint-srcflask_api__init__py)
10. [Running the Application](#10-running-the-application)
11. [Automated Test Suite (`tests/conftest.py` & `tests/test_auth.py`)](#11-automated-test-suite)
12. [Verification via cURL](#12-verification-via-curl)

---

## 1. Architecture & File Map

The system uses the Application Factory pattern with modular Blueprints inside a `src/` package layout compatible with `uv_build` to avoid circular dependencies and make tests isolated and fast.

```text
flask-api/
├── src/
│   └── flask_api/
│       ├── __init__.py          # App factory, extension binding, and CLI entrypoint
│       ├── config.py            # Environment configurations
│       ├── models.py            # SQLAlchemy models (User)
│       ├── schemas.py           # Pydantic schemas (Request/Response models)
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── routes.py        # /register, /login, /me endpoints
│       │   └── utils.py         # JWT tokens & @validate_body decorator
│       └── errors/
│           ├── __init__.py
│           └── handlers.py      # Standardized JSON error responses
├── tests/
│   ├── conftest.py              # Pytest fixtures and in-memory test client
│   └── test_auth.py             # Complete integration tests
├── pyproject.toml               # Project metadata and dependencies managed by uv
└── uv.lock                      # Locked dependency versions
```

---

## 2. Prerequisites & Dependencies (`pyproject.toml`)

### Project & Virtual Environment Setup with `uv`

```bash
# Sync dependencies and create/update the virtual environment (.venv)
uv sync

# Or add dependencies directly via uv
uv add "flask>=3.0.0" "flask-sqlalchemy>=3.1.0" "pydantic[email]>=2.6.0" "pyjwt>=2.8.0" "pytest>=8.0.0" "python-dotenv>=1.0.0" "werkzeug>=3.0.0"
```

### `pyproject.toml`

```toml
[project]
name = "flask-api"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
authors = [
    { name = "Tomislav Dukez", email = "tomdu3@ymail.com" }
]
requires-python = ">=3.12"
dependencies = [
    "flask>=3.0.0",
    "flask-sqlalchemy>=3.1.0",
    "pydantic[email]>=2.6.0",
    "pyjwt>=2.8.0",
    "pytest>=8.0.0",
    "python-dotenv>=1.0.0",
    "werkzeug>=3.0.0",
]

[project.scripts]
flask-api = "flask_api:main"

[build-system]
requires = ["uv_build>=0.13.4,<0.14.0"]
build-backend = "uv_build"
```

---

## 3. Configuration (`src/flask_api/config.py`)

Centralized configuration that reads from environment variables with sensible defaults.

```python
import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_EXPIRATION_DELTA = timedelta(hours=2)


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dev.db")


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
```

---

## 4. Database Models (`src/flask_api/models.py`)

Defines the `User` entity with indexing, timestamps, and secure password hashing via Werkzeug.

```python
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_api import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
```

---

## 5. Pydantic Schemas (`src/flask_api/schemas.py`)

Handles JSON payload validation, regex matching, type coercion, and safe serialization.

```python
from datetime import datetime
import re
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain alphanumeric characters, underscores, and hyphens."
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        return v


class UserLoginSchema(BaseModel):
    identifier: str = Field(..., min_length=3, description="Username or email")
    password: str = Field(..., min_length=1)


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponseSchema(BaseModel):
    token: str
    token_type: str = "Bearer"
    user: UserResponseSchema
```

---

## 6. JWT & Validation Utilities (`src/flask_api/auth/utils.py`)

Contains:

- `generate_token(user_id)`: Generates a signed JWT with expiration claims.
- `@token_required`: Protects routes and passes `current_user` to the handler.
- `@validate_body(Schema)`: Decorator that runs request payloads through Pydantic and returns structured 422 errors on validation failure.

```python
from datetime import datetime, timezone
from functools import wraps
import jwt
from flask import current_app, request, jsonify
from pydantic import ValidationError
from flask_api import db
from flask_api.models import User


def generate_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + current_app.config["JWT_EXPIRATION_DELTA"],
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Authorization header is missing"}), 401

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return (
                jsonify(
                    {"error": "Authorization header must be formatted as: Bearer <token>"}
                ),
                401,
            )

        token = parts[1]
        try:
            payload = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            current_user = db.session.get(User, int(payload["sub"]))
            if not current_user or not current_user.is_active:
                return jsonify({"error": "User account inactive or not found"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Authentication token has expired"}), 401
        except (jwt.InvalidTokenError, ValueError, KeyError):
            return jsonify({"error": "Invalid authentication token"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def validate_body(schema_class):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            payload = request.get_json(silent=True)
            if payload is None:
                return jsonify({"error": "Request body must be valid JSON"}), 400

            try:
                validated_data = schema_class(**payload)
            except ValidationError as err:
                formatted_errors = [
                    {
                        "field": ".".join(str(loc) for loc in e["loc"]),
                        "message": e["msg"],
                    }
                    for e in err.errors()
                ]
                return jsonify({"errors": formatted_errors}), 422

            return f(validated_data, *args, **kwargs)

        return wrapper

    return decorator
```

---

## 7. Authentication Endpoints (`src/flask_api/auth/routes.py`)

Implements `/register`, `/login`, and the protected `/me` endpoint.

```python
from flask import Blueprint, jsonify
from flask_api import db
from flask_api.models import User
from flask_api.schemas import (
    UserRegisterSchema,
    UserLoginSchema,
    UserResponseSchema,
    TokenResponseSchema,
)
from flask_api.auth.utils import generate_token, token_required, validate_body

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
@validate_body(UserRegisterSchema)
def register(data: UserRegisterSchema):
    if User.query.filter_by(username=data.username).first():
        return jsonify({"error": "Username already exists"}), 409
    if User.query.filter_by(email=data.email).first():
        return jsonify({"error": "Email already exists"}), 409

    user = User(username=data.username, email=data.email)
    user.set_password(data.password)

    db.session.add(user)
    db.session.commit()

    user_response = UserResponseSchema.model_validate(user).model_dump(mode="json")
    return (
        jsonify({"message": "User registered successfully", "user": user_response}),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
@validate_body(UserLoginSchema)
def login(data: UserLoginSchema):
    cleaned_id = data.identifier.strip()
    user = User.query.filter(
        (User.username == cleaned_id) | (User.email == cleaned_id.lower())
    ).first()

    if not user or not user.check_password(data.password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is disabled"}), 403

    token = generate_token(user.id)
    response_data = TokenResponseSchema(
        token=token, user=UserResponseSchema.model_validate(user)
    ).model_dump(mode="json")

    return jsonify(response_data), 200


@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user(current_user: User):
    user_response = UserResponseSchema.model_validate(current_user).model_dump(
        mode="json"
    )
    return jsonify({"user": user_response}), 200
```

---

## 8. Global Error Handlers (`src/flask_api/errors/handlers.py`)

Ensures standard HTTP errors always return JSON payloads instead of default HTML.

```python
from flask import Blueprint, jsonify

errors_bp = Blueprint("errors", __name__)


@errors_bp.app_errorhandler(400)
def handle_bad_request(e):
    return jsonify({"error": "Bad request"}), 400


@errors_bp.app_errorhandler(404)
def handle_not_found(e):
    return jsonify({"error": "Resource not found"}), 404


@errors_bp.app_errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify({"error": "HTTP method not allowed"}), 405


@errors_bp.app_errorhandler(500)
def handle_internal_server_error(e):
    return jsonify({"error": "Internal server error occurred"}), 500
```

---

## 9. Application Factory & Entrypoint (`src/flask_api/__init__.py`)

Creates and wires the Flask instance with SQLAlchemy and Blueprints, and exposes `main()` for the `flask-api` script defined in `pyproject.toml`.

```python
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name: str = "default") -> Flask:
    from flask_api.config import config_by_name

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)

    # Register Blueprints
    from flask_api.auth.routes import auth_bp
    from flask_api.errors.handlers import errors_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(errors_bp)

    return app


def main() -> None:
    env = os.getenv("FLASK_ENV", "development")
    app = create_app(env)
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
```

---

## 10. Running the Application

Run the development server via `uv`:

```bash
uv run flask-api
```

---

## 11. Automated Test Suite

### `tests/conftest.py`

Sets up an isolated, in-memory SQLite database for every test session.

```python
import pytest
from flask_api import create_app, db


@pytest.fixture
def app_instance():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()
```

### `tests/test_auth.py`

Validates full registration, Pydantic failure cases, login flows, and token authorization.

```python
def test_user_registration_success(client):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "tester",
            "email": "tester@example.com",
            "password": "SecurePassword1",
        },
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["user"]["username"] == "tester"
    assert "password_hash" not in body["user"]


def test_user_registration_pydantic_validation_error(client):
    # Invalid email syntax and short/simple password
    res = client.post(
        "/api/v1/auth/register",
        json={"username": "t", "email": "not-an-email", "password": "short"},
    )
    assert res.status_code == 422
    body = res.get_json()
    assert "errors" in body
    assert len(body["errors"]) >= 1


def test_registration_duplicate_username(client):
    payload = {
        "username": "duplicate_user",
        "email": "first@example.com",
        "password": "ValidPassword123",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    payload["email"] = "second@example.com"
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.get_json()["error"] == "Username already exists"


def test_login_and_protected_route_flow(client):
    # 1. Register
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "curaleaf_dev",
            "email": "dev@curaleaf.com",
            "password": "StrongPassword99",
        },
    )

    # 2. Login via email
    login_res = client.post(
        "/api/v1/auth/login",
        json={"identifier": "dev@curaleaf.com", "password": "StrongPassword99"},
    )
    assert login_res.status_code == 200
    token = login_res.get_json()["token"]

    # 3. Query protected /me endpoint with Bearer token
    me_res = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.get_json()["user"]["username"] == "curaleaf_dev"


def test_protected_route_missing_token(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "Authorization header is missing" in res.get_json()["error"]


def test_protected_route_invalid_token(client):
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert res.status_code == 401
    assert "Invalid authentication token" in res.get_json()["error"]
```

### Running the Test Suite

```bash
uv run pytest -v
```

---

## 12. Verification via cURL

### 1. Register a New User

```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePassword1"
  }'
```

### 2. Login and Obtain JWT

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "john@example.com",
    "password": "SecurePassword1"
  }'
```

### 3. Access Protected Route

```bash
curl -X GET http://localhost:5000/api/v1/auth/me \
  -H "Authorization: Bearer <PASTE_YOUR_JWT_TOKEN_HERE>"
```

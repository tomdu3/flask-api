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


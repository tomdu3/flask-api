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


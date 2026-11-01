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

from flask_api.db import db
from flask_api import app

with app.app_context():
    db.create_all()
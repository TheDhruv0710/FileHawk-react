from flask import Flask
from flask_app.models import db
from flask.sessions import NullSession

def setup_app():
    app = Flask(__name__)
    app.config['SESSION_TYPE'] = 'null'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scheduler.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app
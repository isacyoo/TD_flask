import json
from datetime import timedelta
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import select
from flask_jwt_extended import JWTManager
from server.routes import *

from databases import db, User
from utils.misc import configure_logging

def create_app():
    app = Flask(__name__)
    migrate = Migrate(app, db, render_as_batch=True)
    CORS(app)
    jwt = JWTManager()
    
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        user = db.session.execute(
            select(User).where(User.id == identity)
        ).scalars().one_or_none()
        return user
    
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
    app.config.from_prefixed_env()
    db.init_app(app)
    jwt.init_app(app)
    configure_logging()
    
    return app

def register_blueprint(app):
    
    with app.app_context():
        app.register_blueprint(users)
        app.register_blueprint(upload)
        app.register_blueprint(auth)
        app.register_blueprint(video)
        app.register_blueprint(action)
        app.register_blueprint(location)
        app.register_blueprint(schedule)
        db.create_all()
        

    return app
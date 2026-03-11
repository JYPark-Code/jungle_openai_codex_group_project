import os

from dotenv import load_dotenv
from flask import Flask

from config import Config
from app.routes.commits import commits_bp
from app.models.db import init_app as init_db_app
from app.routes.auth import auth_bp
from app.routes.api import api_bp
from app.routes.dashboard import dashboard_bp
from app.routes.issues import issues_bp
from app.routes.recommendations import recommendations_bp
from app.routes.repositories import repositories_bp
from app.utils.errors import register_error_handlers


def create_app(config_object=None, config_overrides=None):
    load_dotenv(dotenv_path=".env", override=True)

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or Config)

    default_database = os.path.join(app.instance_path, "study_dashboard.sqlite3")
    app.config["DATABASE"] = app.config.get("DATABASE") or default_database

    if config_overrides:
        app.config.update(config_overrides)

    os.makedirs(app.instance_path, exist_ok=True)

    init_db_app(app)
    register_error_handlers(app)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(commits_bp)
    app.register_blueprint(repositories_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(recommendations_bp)

    return app

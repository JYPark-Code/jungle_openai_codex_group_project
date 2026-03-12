import os
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv
from flask import Flask, redirect, request
from flask_cors import CORS

from config import Config, apply_runtime_env
from app.routes.commits import commits_bp
from app.models.db import init_app as init_db_app
from app.routes.auth import auth_bp
from app.routes.api import api_bp
from app.routes.dashboard import dashboard_bp
from app.routes.design_system import design_system_bp
from app.routes.issues import issues_bp
from app.routes.projects import projects_bp
from app.routes.recommendations import recommendations_bp
from app.routes.repositories import repositories_bp
from app.routes.web import web_bp
from app.utils.errors import register_error_handlers


def create_app(config_object=None, config_overrides=None):
    load_dotenv(dotenv_path=".env", override=True)

    app = Flask(__name__, instance_relative_config=True, template_folder="../templates")
    app.config.from_object(config_object or Config)
    apply_runtime_env(app)

    default_database = os.path.join(app.instance_path, "study_dashboard.sqlite3")
    app.config["DATABASE"] = app.config.get("DATABASE") or default_database

    if config_overrides:
        app.config.update(config_overrides)

    os.makedirs(app.instance_path, exist_ok=True)

    allowed_origins = [
        origin.strip()
        for origin in str(app.config.get("CORS_ALLOWED_ORIGINS", "")).split(",")
        if origin.strip()
    ]
    if allowed_origins:
        CORS(
            app,
            supports_credentials=True,
            resources={r"/api/*": {"origins": allowed_origins}},
        )

    @app.before_request
    def redirect_localhost_to_loopback():
        if app.testing:
            return None
        parsed_url = urlsplit(request.url)
        if parsed_url.hostname != "localhost":
            return None
        port_suffix = f":{parsed_url.port}" if parsed_url.port else ""
        normalized_netloc = f"127.0.0.1{port_suffix}"
        return redirect(
            urlunsplit(
                (
                    parsed_url.scheme,
                    normalized_netloc,
                    parsed_url.path,
                    parsed_url.query,
                    parsed_url.fragment,
                )
            ),
            code=307,
        )

    init_db_app(app)
    register_error_handlers(app)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(design_system_bp)
    app.register_blueprint(commits_bp)
    app.register_blueprint(repositories_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(web_bp)

    return app

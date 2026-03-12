import os


class Config:
    ENV_NAME = "development"
    TESTING = False
    JSON_AS_ASCII = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://127.0.0.1:5000/auth/github/callback")
    GITHUB_OAUTH_SCOPE = os.getenv("GITHUB_OAUTH_SCOPE", "read:user")
    FRONTEND_OAUTH_SUCCESS_URL = os.getenv("FRONTEND_OAUTH_SUCCESS_URL", "http://127.0.0.1:3000/auth/callback")
    FRONTEND_OAUTH_FAILURE_URL = os.getenv("FRONTEND_OAUTH_FAILURE_URL", "http://127.0.0.1:3000/login")
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:3000")
    REPO_OWNER = os.getenv("REPO_OWNER", "")
    REPO_NAME = os.getenv("REPO_NAME", "")
    ACTIVE_WEEK = os.getenv("ACTIVE_WEEK", "")
    DATABASE = os.getenv("DATABASE") or None


class TestingConfig(Config):
    ENV_NAME = "testing"
    TESTING = True
    SECRET_KEY = "test-secret-key"
    GITHUB_TOKEN = "test-token"
    GITHUB_CLIENT_ID = "test-client-id"
    GITHUB_CLIENT_SECRET = "test-client-secret"
    GITHUB_REDIRECT_URI = "http://127.0.0.1/test/callback"
    FRONTEND_OAUTH_SUCCESS_URL = "http://127.0.0.1:3000/auth/callback"
    FRONTEND_OAUTH_FAILURE_URL = "http://127.0.0.1:3000/login"
    CORS_ALLOWED_ORIGINS = "http://127.0.0.1:3000"
    REPO_OWNER = "test-owner"
    REPO_NAME = "test-repo"
    ACTIVE_WEEK = ""


def apply_runtime_env(app) -> None:
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", app.config.get("SECRET_KEY", "dev-secret-key")),
        SESSION_COOKIE_SAMESITE=os.getenv(
            "SESSION_COOKIE_SAMESITE",
            app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
        ),
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        GITHUB_TOKEN=os.getenv("GITHUB_TOKEN", app.config.get("GITHUB_TOKEN", "")),
        GITHUB_CLIENT_ID=os.getenv("GITHUB_CLIENT_ID", app.config.get("GITHUB_CLIENT_ID", "")),
        GITHUB_CLIENT_SECRET=os.getenv(
            "GITHUB_CLIENT_SECRET",
            app.config.get("GITHUB_CLIENT_SECRET", ""),
        ),
        GITHUB_REDIRECT_URI=os.getenv(
            "GITHUB_REDIRECT_URI",
            app.config.get("GITHUB_REDIRECT_URI", "http://127.0.0.1:5000/auth/github/callback"),
        ),
        GITHUB_OAUTH_SCOPE=os.getenv(
            "GITHUB_OAUTH_SCOPE",
            app.config.get("GITHUB_OAUTH_SCOPE", "read:user"),
        ),
        FRONTEND_OAUTH_SUCCESS_URL=os.getenv(
            "FRONTEND_OAUTH_SUCCESS_URL",
            app.config.get("FRONTEND_OAUTH_SUCCESS_URL", "http://127.0.0.1:3000/auth/callback"),
        ),
        FRONTEND_OAUTH_FAILURE_URL=os.getenv(
            "FRONTEND_OAUTH_FAILURE_URL",
            app.config.get("FRONTEND_OAUTH_FAILURE_URL", "http://127.0.0.1:3000/login"),
        ),
        CORS_ALLOWED_ORIGINS=os.getenv(
            "CORS_ALLOWED_ORIGINS",
            app.config.get("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:3000"),
        ),
        REPO_OWNER=os.getenv("REPO_OWNER", app.config.get("REPO_OWNER", "")),
        REPO_NAME=os.getenv("REPO_NAME", app.config.get("REPO_NAME", "")),
        ACTIVE_WEEK=os.getenv("ACTIVE_WEEK", app.config.get("ACTIVE_WEEK", "")),
    )

import os


class Config:
    ENV_NAME = "development"
    TESTING = False
    JSON_AS_ASCII = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://127.0.0.1:5000/api/auth/github/callback")
    GITHUB_OAUTH_SCOPE = os.getenv("GITHUB_OAUTH_SCOPE", "read:user")
    REPO_OWNER = os.getenv("REPO_OWNER", "")
    REPO_NAME = os.getenv("REPO_NAME", "")
    ACTIVE_WEEK = os.getenv("ACTIVE_WEEK", "")
    DATABASE = None


class TestingConfig(Config):
    ENV_NAME = "testing"
    TESTING = True
    SECRET_KEY = "test-secret-key"
    GITHUB_TOKEN = "test-token"
    GITHUB_CLIENT_ID = "test-client-id"
    GITHUB_CLIENT_SECRET = "test-client-secret"
    GITHUB_REDIRECT_URI = "http://localhost/test/callback"
    REPO_OWNER = "test-owner"
    REPO_NAME = "test-repo"
    ACTIVE_WEEK = "week2"

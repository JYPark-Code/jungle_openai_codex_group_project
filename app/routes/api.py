from flask import Blueprint, current_app, redirect, url_for

from app.models.db import database_health, get_table_names
from app.utils.responses import success_response


api_bp = Blueprint("api", __name__)


@api_bp.get("/")
def root():
    return redirect("/login")


@api_bp.get("/api/health")
def health():
    return success_response(
        data={
            "status": "ok",
            "environment": current_app.config["ENV_NAME"],
            "database": {
                "path": current_app.config["DATABASE"],
                "connected": database_health(),
                "tables": get_table_names(),
            },
            "github": {
                "repo_owner": current_app.config.get("REPO_OWNER", ""),
                "repo_name": current_app.config.get("REPO_NAME", ""),
                "token_configured": bool(current_app.config.get("GITHUB_TOKEN")),
            },
        },
        message="헬스 체크가 완료되었습니다.",
    )

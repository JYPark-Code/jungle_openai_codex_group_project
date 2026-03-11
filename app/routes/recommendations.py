from flask import Blueprint

from app.routes.repositories import _require_current_repository
from app.services.recommendation_service import generate_recommendations, get_recommendations
from app.utils.auth import require_authenticated_user
from app.utils.responses import success_response


recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.post("/api/repositories/current/recommendations/generate")
def generate_repository_recommendations():
    require_authenticated_user()
    repository = _require_current_repository()
    result = generate_recommendations(repository["id"])
    return success_response(
        data=result,
        message="약점 기반 추천 문제를 생성했습니다.",
    )


@recommendations_bp.get("/api/repositories/current/recommendations")
def list_repository_recommendations():
    require_authenticated_user()
    repository = _require_current_repository()
    result = get_recommendations(repository["id"])
    return success_response(
        data=result,
        message="저장된 추천 문제를 조회했습니다.",
    )

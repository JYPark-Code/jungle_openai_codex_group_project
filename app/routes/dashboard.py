from flask import Blueprint

from app.routes.repositories import _require_current_repository
from app.services.report_service import build_dashboard_summary, build_user_report
from app.utils.auth import require_authenticated_user
from app.utils.responses import success_response


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/api/dashboard/summary")
def dashboard_summary():
    require_authenticated_user()
    repository = _require_current_repository()
    result = build_dashboard_summary(repository["id"])
    return success_response(
        data=result,
        message="대시보드 요약 정보를 조회했습니다.",
    )


@dashboard_bp.get("/api/mypage/report")
def mypage_report():
    require_authenticated_user()
    repository = _require_current_repository()
    result = build_user_report(repository["id"], report_scope="mypage_report")
    return success_response(
        data=result,
        message="마이페이지 분석 리포트를 조회했습니다.",
    )

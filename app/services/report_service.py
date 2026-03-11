from app.models.db import (
    get_latest_analysis_report,
    get_problem_summary_by_repository_id,
    get_repository_by_id,
    get_sync_status,
    save_analysis_report,
)
from app.services.issue_template_service import build_template_status
from app.services.recommendation_service import get_recommendations, rank_weak_topics
from app.services.skill_map_service import build_skill_map


def build_dashboard_summary(repository_id: int) -> dict:
    report = build_user_report(repository_id, report_scope="dashboard_summary")
    return {
        "status": report["status"],
        "solved_count": report["solved_count"],
        "attempted_count": report["attempted_count"],
        "week_progress": report["week_progress"],
        "last_synced_at": report["last_synced_at"],
        "skill_map": report["skill_map"],
        "weak_topics": report["weak_topics"],
        "recommendations": report["recommendations"],
    }


def build_user_report(repository_id: int, report_scope: str = "mypage_report") -> dict:
    repository = get_repository_by_id(repository_id)
    summary = get_problem_summary_by_repository_id(repository_id)
    template_status = build_template_status(repository_id)
    sync_status = get_sync_status(repository_id)
    skill_map = build_skill_map(repository_id)
    recommendation_data = get_recommendations(repository_id)
    weak_topic_ranking = rank_weak_topics(repository_id, limit=5)

    solved_count = summary["solved_count"]
    attempted_count = summary["attempted_count"] + summary["possibly_solved_count"]
    total_templates = template_status["template_count"]
    week_progress = (template_status["matched_count"] / total_templates) if total_templates else 0.0
    solved_ratio = solved_count / max(solved_count + attempted_count, 1)

    status = evaluate_learning_status(
        week_progress=week_progress,
        solved_ratio=solved_ratio,
        weak_topic_count=len(recommendation_data["weak_topics"]),
    )
    ai_summary = build_ai_summary(status, week_progress, solved_ratio, recommendation_data["weak_topics"])
    area_analysis = build_area_analysis(skill_map)

    report = {
        "repository": repository,
        "status": status,
        "solved_count": solved_count,
        "attempted_count": attempted_count,
        "possibly_solved_count": summary["possibly_solved_count"],
        "week_progress": round(week_progress, 2),
        "last_synced_at": sync_status["last_synced_at"],
        "skill_map": skill_map,
        "ai_summary": ai_summary,
        "domain_analysis": area_analysis,
        "weak_topics": recommendation_data["weak_topics"],
        "weak_topic_ranking": weak_topic_ranking,
        "recommendations": recommendation_data["recommendations"],
    }

    save_analysis_report(
        repository_id=repository_id,
        report_scope=report_scope,
        solved_count=solved_count,
        attempted_count=attempted_count,
        status_label=status,
        summary_text=ai_summary,
        topic_breakdown=skill_map,
        weak_topics=report["weak_topics"],
    )
    return report


def get_cached_report(repository_id: int, report_scope: str) -> dict | None:
    return get_latest_analysis_report(repository_id, report_scope)


def evaluate_learning_status(week_progress: float, solved_ratio: float, weak_topic_count: int) -> str:
    if week_progress >= 0.7 and solved_ratio >= 0.6 and weak_topic_count <= 2:
        return "Good"
    if week_progress < 0.4 or (solved_ratio < 0.35 and weak_topic_count >= 3):
        return "Risk"
    return "Watch"


def build_ai_summary(status: str, week_progress: float, solved_ratio: float, weak_topics: list[str]) -> str:
    weak_text = ", ".join(weak_topics[:3]) if weak_topics else "특별히 두드러진 약점이 아직 없습니다"
    return (
        f"현재 상태는 {status}입니다. "
        f"주차 진행률은 {week_progress:.0%}, solved 비율은 {solved_ratio:.0%}이며, "
        f"우선 보강이 필요한 영역은 {weak_text}입니다."
    )


def build_area_analysis(skill_map: dict) -> list[dict]:
    analysis = []
    for domain in skill_map.get("domains", []):
        total = domain["total"]
        solved = domain["solved"]
        solved_ratio = solved / total if total else 0.0
        analysis.append(
            {
                "name": domain["name"],
                "total": total,
                "solved": solved,
                "status": "강점" if solved_ratio >= 0.6 else "보강 필요",
                "solved_ratio": round(solved_ratio, 2),
            }
        )
    return analysis

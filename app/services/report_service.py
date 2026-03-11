from __future__ import annotations

from app.models.db import (
    get_active_github_project,
    get_latest_analysis_report,
    get_issues_by_repository_id,
    get_repository_by_id,
    get_sync_status,
    list_problem_judgements_by_repository_id,
    save_analysis_report,
)
from app.services.issue_template_service import build_template_status, is_challenge_issue, is_common_issue
from app.services.recommendation_service import get_recommendations, rank_weak_topics
from app.services.skill_map_service import build_skill_map


def build_dashboard_summary(repository_id: int) -> dict:
    report = build_user_report(repository_id, report_scope="dashboard_summary")
    return {
        "status": report["status"],
        "active_week": report["active_week"],
        "solved_count": report["solved_count"],
        "attempted_count": report["attempted_count"],
        "extra_practice_count": report["extra_practice_count"],
        "week_progress": report["week_progress"],
        "last_synced_at": report["last_synced_at"],
        "skill_map": report["skill_map"],
        "weak_topics": report["weak_topics"],
        "recommendations": report["recommendations"],
        "current_project": report["current_project"],
    }


def build_user_report(repository_id: int, report_scope: str = "mypage_report") -> dict:
    repository = get_repository_by_id(repository_id)
    template_status = build_template_status(repository_id)
    sync_status = get_sync_status(repository_id)
    skill_map = build_skill_map(repository_id)
    recommendation_data = get_recommendations(repository_id)
    weak_topic_ranking = rank_weak_topics(repository_id, limit=5)
    current_project = get_active_github_project(repository_id)

    tracked_summary = build_tracked_problem_summary(repository_id)
    solved_count = tracked_summary["solved_count"]
    attempted_count = tracked_summary["attempted_count"]
    possibly_solved_count = tracked_summary["possibly_solved_count"]
    extra_practice_count = tracked_summary["extra_practice_count"]
    challenge_count = tracked_summary["challenge_count"]

    week_progress = template_status.get("required_progress")
    if week_progress is None:
        template_count = template_status.get("required_template_count", 0)
        matched_count = template_status.get("required_matched_count", 0)
        if not template_count:
            template_count = template_status.get("template_count", 0)
            matched_count = template_status.get("matched_count", 0)
        week_progress = (matched_count / template_count) if template_count else 0.0

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
        "active_week": template_status.get("active_week"),
        "status": status,
        "solved_count": solved_count,
        "attempted_count": attempted_count,
        "possibly_solved_count": possibly_solved_count,
        "extra_practice_count": extra_practice_count,
        "challenge_count": challenge_count,
        "total_issue_count": tracked_summary["total_issue_count"],
        "remaining_issue_count": tracked_summary["remaining_issue_count"],
        "week_progress": round(week_progress, 2),
        "required_template_count": template_status.get("required_template_count", 0),
        "required_matched_count": template_status.get("required_matched_count", 0),
        "last_synced_at": sync_status["last_synced_at"],
        "current_project": current_project,
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


def build_tracked_problem_summary(repository_id: int) -> dict:
    issues = get_issues_by_repository_id(repository_id)
    judgements = list_problem_judgements_by_repository_id(repository_id)
    template_status = build_template_status(repository_id)
    issue_meta_map = _build_issue_meta_map(template_status)
    challenge_issue_numbers = _build_challenge_issue_numbers(judgements)

    tracked = [item for item in judgements if item.get("issue_number") is not None]
    extra = [item for item in judgements if item.get("issue_number") is None]

    best_status_by_issue = {}
    priority = {"not_started": 0, "attempted": 1, "possibly_solved": 2, "solved": 3}
    for item in tracked:
        issue_number = item.get("issue_number")
        if issue_number is None:
            continue
        status = item["judgement_status"]
        current = best_status_by_issue.get(issue_number)
        if current is None or priority.get(status, -1) > priority.get(current, -1):
            best_status_by_issue[issue_number] = status

    summary = {
        "solved_count": 0,
        "attempted_count": 0,
        "possibly_solved_count": 0,
        "extra_practice_count": len(extra),
        "challenge_count": 0,
        "total_issue_count": 0,
        "remaining_issue_count": 0,
    }

    for issue in issues:
        if _is_common_or_challenge_issue(issue, issue_meta_map, challenge_issue_numbers):
            if issue["issue_number"] in challenge_issue_numbers or is_challenge_issue(issue_meta_map.get(issue["issue_number"], {})):
                summary["challenge_count"] += 1
            continue

        summary["total_issue_count"] += 1
        status = best_status_by_issue.get(issue["issue_number"])
        if issue["state"] == "closed":
            status = "solved"

        if status == "solved":
            summary["solved_count"] += 1
        elif status == "possibly_solved":
            summary["possibly_solved_count"] += 1
            summary["attempted_count"] += 1
        elif status == "attempted":
            summary["attempted_count"] += 1
        else:
            summary["remaining_issue_count"] += 1

    if not issues:
        summary["total_issue_count"] = len(best_status_by_issue)
        for issue_number, status in best_status_by_issue.items():
            if issue_number in challenge_issue_numbers:
                summary["challenge_count"] += 1
                summary["total_issue_count"] -= 1
                continue
            if status == "solved":
                summary["solved_count"] += 1
            elif status == "possibly_solved":
                summary["possibly_solved_count"] += 1
                summary["attempted_count"] += 1
            elif status == "attempted":
                summary["attempted_count"] += 1
            else:
                summary["remaining_issue_count"] += 1

    return summary


def evaluate_learning_status(week_progress: float, solved_ratio: float, weak_topic_count: int) -> str:
    if week_progress >= 0.95 and solved_ratio >= 0.8:
        return "Good"
    if week_progress >= 0.7 and solved_ratio >= 0.6 and weak_topic_count <= 2:
        return "Good"
    if week_progress < 0.4 or (solved_ratio < 0.35 and weak_topic_count >= 3):
        return "Risk"
    return "Watch"


def build_ai_summary(status: str, week_progress: float, solved_ratio: float, weak_topics: list[str]) -> str:
    weak_text = ", ".join(weak_topics[:3]) if weak_topics else "뚜렷한 약점 영역이 아직 없습니다"
    return (
        f"현재 상태는 {status}입니다. "
        f"필수 과제 진행률은 {week_progress:.0%}, solved 비율은 {solved_ratio:.0%}이며, "
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


def _build_issue_meta_map(template_status: dict) -> dict[int, dict]:
    meta_map = {}
    for item in template_status.get("all_matched_issues", []):
        issue_number = item.get("issue_number")
        if issue_number is not None:
            meta_map[issue_number] = item
    return meta_map


def _build_challenge_issue_numbers(judgements: list[dict]) -> set[int]:
    challenge_issue_numbers = set()
    for item in judgements:
        issue_number = item.get("issue_number")
        file_path = item.get("file_path", "") or ""
        if issue_number is None:
            continue
        if _is_high_difficulty_file(file_path):
            challenge_issue_numbers.add(issue_number)
    return challenge_issue_numbers


def _is_common_or_challenge_issue(issue: dict, issue_meta_map: dict[int, dict], challenge_issue_numbers: set[int]) -> bool:
    issue_number = issue.get("issue_number")
    meta = issue_meta_map.get(issue_number, {})
    if is_common_issue(meta):
        return True
    if is_challenge_issue(meta):
        return True
    if issue_number in challenge_issue_numbers:
        return True
    return False


def _is_high_difficulty_file(file_path: str) -> bool:
    file_name = file_path.split("/")[-1]
    return file_name.startswith("난이도상_")

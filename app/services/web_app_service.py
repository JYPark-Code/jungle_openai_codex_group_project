from __future__ import annotations

import math
import re
from datetime import datetime

from app.models.db import (
    get_issues_by_repository_id,
    get_sync_status,
    list_problem_judgements_by_repository_id,
)
from app.services.code_review import get_commit_review
from app.services.commit_judge_service import (
    get_commit_detail,
    get_commit_judge_result,
    list_repository_commits,
)
from app.services.github_service import fetch_commit_changed_files, fetch_file_content_at_ref
from app.services.issue_template_service import build_template_status, is_challenge_issue, is_common_issue, normalize_title
from app.services.recommendation_service import generate_recommendations
from app.services.report_service import build_user_report
from app.utils.errors import ApiError


STATUS_PRIORITY = {
    "not_started": 0,
    "attempted": 1,
    "possibly_solved": 2,
    "solved": 3,
    "challenge": 4,
}

STATUS_COPY = {
    "not_started": "풀어야 하는 문제",
    "attempted": "풀고 있는 문제",
    "possibly_solved": "풀고 있는 문제",
    "solved": "푼 문제",
    "challenge": "도전 문제",
}

RADAR_DOMAIN_ORDER = ["자료구조", "탐색", "수학", "구현", "정렬"]
ACTIVITY_SORT_OPTIONS = {
    "issue_asc": "이슈 번호 오름차순",
    "issue_desc": "이슈 번호 내림차순",
    "status": "상태순",
}


def build_dashboard_page_data(repository: dict, activity_sort: str = "issue_asc") -> dict:
    report = build_user_report(repository["id"], report_scope="dashboard_page")
    recommendations = report["recommendations"]
    if not recommendations and report["weak_topics"]:
        generated = generate_recommendations(repository["id"])
        recommendations = generated["recommendations"]
        report["weak_topics"] = generated["weak_topics"]

    issue_board = build_issue_board(repository, activity_sort=activity_sort)
    template_status = build_template_status(repository["id"])
    sync_status = get_sync_status(repository["id"])

    return {
        "repository": repository,
        "report": report,
        "progress_cards": [
            {"label": "전체 필수 문제", "value": report["total_issue_count"]},
            {"label": "푼 문제", "value": report["solved_count"]},
            {"label": "남은 문제", "value": report["remaining_issue_count"]},
        ],
        "issue_board": issue_board,
        "recommendations": recommendations,
        "sync_status": sync_status,
        "formatted_last_synced_at": _format_display_date(sync_status.get("last_synced_at")),
        "template_status": {
            **template_status,
            "status_note": _build_template_status_note(template_status),
        },
        "activity_sort": activity_sort if activity_sort in ACTIVITY_SORT_OPTIONS else "issue_asc",
        "activity_sort_options": ACTIVITY_SORT_OPTIONS,
    }


def build_issue_board(repository: dict, activity_sort: str = "issue_asc") -> dict:
    issues = get_issues_by_repository_id(repository["id"])
    judgements = list_problem_judgements_by_repository_id(repository["id"])
    template_status = build_template_status(repository["id"])
    issue_meta_map = _build_issue_meta_map(template_status)
    challenge_issue_numbers = _build_challenge_issue_numbers(judgements)
    best_status_by_issue = _build_issue_status_map(judgements)

    current_week_key = _pick_current_week_key(issues)
    current_week_issues = []

    for issue in issues:
        if current_week_key and _extract_week_key(issue["title"]) != current_week_key:
            continue

        issue_meta = issue_meta_map.get(issue["issue_number"], {})
        if is_common_issue(issue_meta):
            continue

        if issue["issue_number"] in challenge_issue_numbers or is_challenge_issue(issue_meta):
            status_key = "challenge"
        else:
            status_key = best_status_by_issue.get(issue["issue_number"])
            if not status_key and issue["state"] == "closed":
                status_key = "solved"
            if not status_key:
                status_key = "not_started"

        item = {
            "issue_number": issue["issue_number"],
            "title": issue["title"],
            "state": issue["state"],
            "status_key": status_key,
            "status_label": STATUS_COPY[status_key],
            "issue_url": _build_issue_url(repository["full_name"], issue["issue_number"]),
        }
        current_week_issues.append(item)

    _sort_issue_activity(current_week_issues, activity_sort)

    columns = {
        "todo": [item for item in current_week_issues if item["status_key"] == "not_started"],
        "in_progress": [
            item
            for item in current_week_issues
            if item["status_key"] in {"attempted", "possibly_solved"}
        ],
        "done": [item for item in current_week_issues if item["status_key"] == "solved"],
        "challenge": [item for item in current_week_issues if item["status_key"] == "challenge"],
    }

    return {
        "week_label": current_week_key or "전체 문제",
        "activity": current_week_issues,
        "columns": columns,
        "summary": {
            "total": len(current_week_issues),
            "todo": len(columns["todo"]),
            "in_progress": len(columns["in_progress"]),
            "done": len(columns["done"]),
            "challenge": len(columns["challenge"]),
        },
    }


def build_profile_page_data(repository: dict) -> dict:
    report = build_user_report(repository["id"], report_scope="profile_page")
    radar = build_radar_chart(report["skill_map"])

    return {
        "repository": repository,
        "report": report,
        "radar": radar,
        "status_rules": [
            "Good: 주차 진행률이 높고 약점이 적음",
            "Watch: 진행은 되지만 유형 편중이 있음",
            "Risk: 진행률이 낮거나 약점 영역이 많음",
        ],
    }


def build_reviews_page_data(repository: dict, access_token: str, selected_sha: str = "") -> dict:
    commits = list_repository_commits(repository["id"])
    selected = None

    if selected_sha:
        selected = _build_commit_review_detail(repository, selected_sha, access_token)
    elif commits:
        selected = _build_commit_review_detail(repository, commits[0]["sha"], access_token, strict=False)

    selected_commit_sha = selected["commit"]["sha"] if selected else selected_sha

    return {
        "repository": repository,
        "commits": [
            {
                **item,
                "formatted_committed_at": _format_display_datetime(item.get("committed_at")),
                "is_selected": item["sha"] == selected_commit_sha,
            }
            for item in commits
        ],
        "selected": selected,
    }


def build_radar_chart(skill_map: dict) -> dict:
    domain_lookup = {domain["name"]: domain for domain in skill_map.get("domains", [])}
    metrics = []

    for label in RADAR_DOMAIN_ORDER:
        domain = domain_lookup.get(label, {})
        total = domain.get("total", 0)
        weighted_score = (
            domain.get("solved", 0)
            + domain.get("possibly_solved", 0) * 0.6
            + domain.get("attempted", 0) * 0.25
        )
        score = round((weighted_score / total) * 100) if total else 0
        metrics.append({"label": label, "value": int(score)})

    center = 150
    radius = 108
    points = []
    label_points = []
    grid_polygons = []

    for index, metric in enumerate(metrics):
        angle = math.radians(-90 + (360 / len(metrics)) * index)
        points.append(
            f"{center + math.cos(angle) * radius * (metric['value'] / 100):.1f},"
            f"{center + math.sin(angle) * radius * (metric['value'] / 100):.1f}"
        )
        label_points.append(
            {
                "label": metric["label"],
                "x": round(center + math.cos(angle) * (radius + 26), 1),
                "y": round(center + math.sin(angle) * (radius + 26), 1),
            }
        )

    for level in [20, 40, 60, 80, 100]:
        level_points = []
        scale = level / 100
        for index in range(len(metrics)):
            angle = math.radians(-90 + (360 / len(metrics)) * index)
            level_points.append(
                f"{center + math.cos(angle) * radius * scale:.1f},{center + math.sin(angle) * radius * scale:.1f}"
            )
        grid_polygons.append({"level": level, "points": " ".join(level_points)})

    return {
        "metrics": metrics,
        "points": " ".join(points),
        "grid_polygons": grid_polygons,
        "labels": label_points,
        "center": center,
        "radius": radius,
    }


def _build_commit_review_detail(
    repository: dict,
    sha: str,
    access_token: str,
    strict: bool = True,
) -> dict | None:
    try:
        commit = get_commit_detail(repository["id"], sha)
    except ApiError:
        if strict:
            raise
        return None

    try:
        review = get_commit_review(repository["id"], sha)
    except ApiError:
        review = None

    try:
        judge_result = get_commit_judge_result(repository["id"], sha)
    except ApiError:
        judge_result = None

    file_previews = []
    if access_token and access_token != "demo-token":
        try:
            payload = fetch_commit_changed_files(repository["owner"], repository["name"], sha, access_token)
            for item in payload["files"]:
                if not item["filename"].endswith(".py"):
                    continue
                source = fetch_file_content_at_ref(
                    repository["owner"],
                    repository["name"],
                    item["filename"],
                    sha,
                    access_token,
                )
                preview_lines = source.splitlines()
                file_previews.append(
                    {
                        "file_path": item["filename"],
                        "preview": "\n".join(preview_lines[:80]),
                        "line_count": len(preview_lines),
                    }
                )
                if len(file_previews) >= 3:
                    break
        except Exception:
            file_previews = []

    if not file_previews and review:
        for item in review.get("files", []):
            line_comments = item.get("line_comments", [])
            snippet = line_comments[0]["snippet"] if line_comments else ""
            if not snippet:
                continue
            file_previews.append(
                {
                    "file_path": item["file_path"],
                    "preview": snippet,
                    "line_count": len(snippet.splitlines()),
                }
            )

    return {
        "commit": {
            **commit,
            "formatted_committed_at": _format_display_datetime(commit.get("committed_at")),
        },
        "review": review,
        "judge_result": judge_result,
        "file_previews": file_previews,
    }


def _build_issue_status_map(judgements: list[dict]) -> dict[int, str]:
    best_status_by_issue = {}
    for judgement in judgements:
        issue_number = judgement.get("issue_number")
        if not issue_number:
            continue

        next_status = judgement["judgement_status"]
        current_status = best_status_by_issue.get(issue_number)
        if not current_status or STATUS_PRIORITY[next_status] > STATUS_PRIORITY[current_status]:
            best_status_by_issue[issue_number] = next_status
    return best_status_by_issue


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
        if file_path.split("/")[-1].startswith("난이도상_"):
            challenge_issue_numbers.add(issue_number)
    return challenge_issue_numbers


def _build_issue_url(full_name: str, issue_number: int | None) -> str:
    return f"https://github.com/{full_name}/issues/{issue_number}" if issue_number else "#"


def _extract_week_key(title: str) -> str:
    normalized = (title or "").strip()
    week_match = re.search(r"(week\s*\d+|w\s*\d+|\d+\s*주차)", normalized, re.IGNORECASE)
    if not week_match:
        return ""

    token = week_match.group(1).casefold()
    number_match = re.search(r"\d+", token)
    if not number_match:
        return token

    return f"week{int(number_match.group())}"


def _pick_current_week_key(issues: list[dict]) -> str:
    detected = []
    for issue in issues:
        week_key = _extract_week_key(issue["title"])
        if week_key:
            detected.append(week_key)

    if not detected:
        return ""

    return sorted(detected, key=_week_sort_key)[-1]


def _week_sort_key(token: str) -> tuple[int, str]:
    number_match = re.search(r"\d+", token)
    return (int(number_match.group()) if number_match else -1, token)


def _format_display_date(value: str | None) -> str:
    if not value:
        return "없음"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return f"{parsed.year}.{parsed.month:02d}.{parsed.day:02d}"


def _format_display_datetime(value: str | None) -> str:
    if not value:
        return "시각 정보 없음"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return f"{parsed.year}.{parsed.month:02d}.{parsed.day:02d} {parsed.hour:02d}:{parsed.minute:02d}"


def _build_template_status_note(template_status: dict) -> str:
    active_total = template_status.get("active_week_template_count", 0)
    active_connected = len(template_status.get("matched_issues", []))
    overall_connected = template_status.get("matched_count", 0)
    challenge_count = template_status.get("challenge_issue_count", 0)

    if not active_total:
        return "현재 주차에 해당하는 템플릿이 없습니다."
    if not active_connected and overall_connected:
        return "전체 연결 이슈는 있지만 현재 주차에 매칭된 이슈가 없습니다."
    return (
        f"현재 주차 연결 {active_connected}건, 전체 연결 {overall_connected}건이며, "
        f"도전 문제는 {challenge_count}건입니다."
    )


def _sort_issue_activity(items: list[dict], activity_sort: str) -> None:
    if activity_sort == "issue_desc":
        items.sort(key=lambda item: (item["issue_number"] or 0, item["title"]), reverse=True)
        return
    if activity_sort == "status":
        items.sort(
            key=lambda item: (
                STATUS_PRIORITY.get(item["status_key"], -1),
                item["issue_number"] or 0,
                item["title"],
            )
        )
        return
    items.sort(key=lambda item: (item["issue_number"] or 0, item["title"]))

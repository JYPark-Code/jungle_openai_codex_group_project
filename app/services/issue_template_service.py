from __future__ import annotations

import csv
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app

from app.models.db import get_issues_by_repository_id, record_issue_sync_result, save_issue
from app.services.github_service import create_issue_with_access_token


DEFAULT_TEMPLATE_DIRECTORY = Path("resources/csv")
WEEK3_START_DATE = date(2026, 3, 13)
KNOWN_CHALLENGE_TITLES = {
    "문자열 - 광고",
    "정수론 - 제곱 ㄴㄴ 수",
}


def load_issue_templates(template_directory: str | Path = DEFAULT_TEMPLATE_DIRECTORY) -> list[dict]:
    directory = Path(template_directory)
    templates = []

    for csv_path in sorted(directory.glob("*.csv")):
        week_label = extract_week_label(csv_path.name)
        rows = _read_csv_rows(csv_path)
        for row in rows:
            title = str(row.get("title", "")).strip()
            content = str(row.get("content", "")).strip()
            if not title:
                continue

            category = classify_issue_title(title)
            track_type = infer_track_type(title, content, category)
            difficulty_level = infer_difficulty_level(title, content)
            requirement_level = infer_requirement_level(title, content, category, track_type, difficulty_level)

            templates.append(
                {
                    "title": title,
                    "content": content,
                    "normalized_title": normalize_title(title),
                    "category": category,
                    "track_type": track_type,
                    "difficulty_level": difficulty_level,
                    "requirement_level": requirement_level,
                    "week_label": week_label,
                    "source_file": csv_path.name,
                }
            )

    return templates


def build_template_status(
    repository_id: int,
    template_directory: str | Path = DEFAULT_TEMPLATE_DIRECTORY,
    active_week: str | None = None,
) -> dict:
    templates = load_issue_templates(template_directory)
    saved_issues = get_issues_by_repository_id(repository_id)
    issue_map = {normalize_title(issue["title"]): issue for issue in saved_issues}

    matched = []
    missing = []

    for template in templates:
        issue = issue_map.get(template["normalized_title"])
        base_payload = {
            "title": template["title"],
            "category": template["category"],
            "track_type": template["track_type"],
            "difficulty_level": template["difficulty_level"],
            "requirement_level": template["requirement_level"],
            "week_label": template["week_label"],
            "source_file": template["source_file"],
        }
        if issue:
            matched.append(
                {
                    **base_payload,
                    "github_issue_id": issue["github_issue_id"],
                    "issue_number": issue["issue_number"],
                    "state": issue["state"],
                }
            )
        else:
            missing.append(
                {
                    **base_payload,
                    "content": template["content"],
                }
            )

    selected_week = active_week or determine_active_week(templates, matched)
    active_templates = [item for item in templates if item["week_label"] == selected_week] if selected_week else []
    active_matched = [item for item in matched if item["week_label"] == selected_week] if selected_week else []
    active_missing = [item for item in missing if item["week_label"] == selected_week] if selected_week else []

    required_active_templates = [item for item in active_templates if is_required_coding_issue(item)]
    matched_required_titles = {
        item["title"]
        for item in active_matched
        if is_required_coding_issue(item)
    }
    challenge_active_issues = [
        item for item in (active_matched + active_missing)
        if is_challenge_issue(item)
    ]

    required_progress = (
        len(matched_required_titles) / len(required_active_templates)
        if required_active_templates
        else 0.0
    )

    return {
        "template_count": len(templates),
        "matched_count": len(matched),
        "missing_count": len(missing),
        "active_week": selected_week,
        "active_week_template_count": len(active_templates),
        "required_template_count": len(required_active_templates),
        "required_matched_count": len(matched_required_titles),
        "required_progress": round(required_progress, 2),
        "challenge_issue_count": len(challenge_active_issues),
        "matched_issues": active_matched if selected_week else matched,
        "missing_issues": active_missing if selected_week else missing,
        "all_matched_issues": matched,
        "all_missing_issues": missing,
    }


def create_missing_issues(
    repository: dict,
    access_token: str,
    template_directory: str | Path = DEFAULT_TEMPLATE_DIRECTORY,
    active_week: str | None = None,
) -> dict:
    status = build_template_status(repository["id"], template_directory, active_week=active_week)
    created_results = []

    for missing_issue in status["missing_issues"]:
        created_issue = create_issue_with_access_token(
            access_token=access_token,
            repo_owner=repository["owner"],
            repo_name=repository["name"],
            title=missing_issue["title"],
            body=missing_issue["content"],
        )
        save_issue(
            repository_id=repository["id"],
            github_issue_id=str(created_issue.get("id", "")),
            issue_number=created_issue.get("number"),
            title=created_issue.get("title", missing_issue["title"]),
            body=created_issue.get("body") or missing_issue["content"],
            state=created_issue.get("state", "open"),
            github_created_at=created_issue.get("created_at", ""),
        )
        created_results.append(
            {
                "title": missing_issue["title"],
                "category": missing_issue["category"],
                "track_type": missing_issue["track_type"],
                "difficulty_level": missing_issue["difficulty_level"],
                "requirement_level": missing_issue["requirement_level"],
                "week_label": missing_issue["week_label"],
                "issue_number": created_issue.get("number"),
                "issue_url": created_issue.get("html_url"),
                "state": created_issue.get("state", "open"),
            }
        )

    record_issue_sync_result(
        repository_id=repository["id"],
        week_label=status["active_week"] or "all-weeks",
        source_csv_path=str(template_directory),
        requested_count=status["missing_count"],
        created_count=len(created_results),
        missing_count=max(status["missing_count"] - len(created_results), 0),
        status="completed",
        summary={
            "template_count": status["template_count"],
            "matched_count": status["matched_count"],
            "created_count": len(created_results),
            "required_progress": status["required_progress"],
        },
    )

    updated_status = build_template_status(repository["id"], template_directory, active_week=active_week)
    return {
        "template_count": updated_status["template_count"],
        "matched_count": updated_status["matched_count"],
        "missing_count": updated_status["missing_count"],
        "active_week": updated_status["active_week"],
        "required_template_count": updated_status["required_template_count"],
        "required_matched_count": updated_status["required_matched_count"],
        "required_progress": updated_status["required_progress"],
        "missing_issues": updated_status["missing_issues"],
        "created_issues": created_results,
    }


def normalize_title(title: str) -> str:
    normalized = title.strip()
    normalized = re.sub(r"^\[(week\s*\d+|week\d+|w\d+)\]\s*", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"^(week\s*\d+|week\d+|w\d+)\s*[-:]\s*", "", normalized, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", normalized).casefold()


KNOWN_CHALLENGE_NORMALIZED_TITLES = {normalize_title(title) for title in KNOWN_CHALLENGE_TITLES}


def classify_issue_title(title: str) -> str:
    lowered = title.strip().casefold()
    if lowered.startswith("공통") or lowered.startswith("common"):
        return "common"
    if lowered.startswith("basic"):
        return "basic"
    return "weekly"


def infer_track_type(title: str, content: str, category: str) -> str:
    lowered = normalize_title(f"{title} {content}")
    if category == "common":
        return "common"
    if category == "basic":
        return "basic"
    if "extra" in lowered:
        return "extra"
    if "problem-solving" in lowered or "problem solving" in lowered:
        return "problem-solving"
    return "problem-solving"


def infer_requirement_level(
    title: str,
    content: str,
    category: str,
    track_type: str,
    difficulty_level: str,
) -> str:
    lowered = normalize_title(f"{title} {content}")
    normalized_title = normalize_title(title)
    if category == "common":
        return "excluded"
    if category == "basic":
        return "required"
    if normalized_title in KNOWN_CHALLENGE_NORMALIZED_TITLES:
        return "optional"
    if track_type == "extra" or "선택" in lowered:
        return "optional"
    if difficulty_level == "high":
        return "optional"
    return "required"


def infer_difficulty_level(title: str, content: str) -> str:
    lowered = normalize_title(f"{title} {content}")
    if "난이도하" in lowered or re.search(r"(^|[\s\-_[(])하($|[\s\-_)\]])", lowered):
        return "low"
    if "난이도중" in lowered or re.search(r"(^|[\s\-_[(])중($|[\s\-_)\]])", lowered):
        return "medium"
    if "난이도상" in lowered or re.search(r"(^|[\s\-_[(])상($|[\s\-_)\]])", lowered):
        return "high"
    return "unspecified"


def is_common_issue(item: dict) -> bool:
    return item.get("track_type") == "common" or item.get("category") == "common"


def is_challenge_issue(item: dict) -> bool:
    return item.get("requirement_level") == "optional" or item.get("track_type") == "extra"


def is_required_coding_issue(item: dict) -> bool:
    return not is_common_issue(item) and not is_challenge_issue(item)


def extract_week_label(filename: str) -> str:
    match = re.search(r"(week\s*\d+|week\d+|w\d+)", filename.casefold())
    if not match:
        return "common"
    return match.group(1).replace(" ", "")


def determine_active_week(templates: list[dict], matched_issues: list[dict]) -> str | None:
    configured_week = current_app.config.get("ACTIVE_WEEK", "").strip().casefold() if current_app else ""
    if configured_week:
        return configured_week

    available_weeks = sorted(
        {item["week_label"] for item in templates if item["week_label"].startswith("week")},
        key=_week_sort_key,
    )
    if not available_weeks:
        return None

    today = datetime.now().date()
    if today < WEEK3_START_DATE and "week2" in available_weeks:
        return "week2"

    selected_week = available_weeks[0]
    for week_label in available_weeks:
        week_number = _extract_week_number(week_label)
        if week_number <= 2:
            start_date = WEEK3_START_DATE - timedelta(days=7)
        else:
            start_date = WEEK3_START_DATE + timedelta(days=7 * (week_number - 3))
        if today >= start_date:
            selected_week = week_label

    return selected_week


def _week_sort_key(week_label: str) -> tuple[int, str]:
    return (_extract_week_number(week_label), week_label)


def _extract_week_number(week_label: str) -> int:
    match = re.search(r"(\d+)", week_label)
    return int(match.group(1)) if match else 0


def _read_csv_rows(csv_path: Path) -> list[dict]:
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            with csv_path.open("r", encoding=encoding, newline="") as file:
                return list(csv.DictReader(file))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"지원하지 않는 CSV 인코딩입니다: {csv_path}")

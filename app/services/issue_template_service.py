import csv
import re
from pathlib import Path

from app.models.db import get_issues_by_repository_id, record_issue_sync_result, save_issue
from app.services.github_service import create_issue_with_access_token


DEFAULT_TEMPLATE_DIRECTORY = Path("resources/csv")


def load_issue_templates(template_directory: str | Path = DEFAULT_TEMPLATE_DIRECTORY) -> list[dict]:
    directory = Path(template_directory)
    templates = []

    for csv_path in sorted(directory.glob("*.csv")):
        rows = _read_csv_rows(csv_path)
        for row in rows:
            title = str(row.get("title", "")).strip()
            content = str(row.get("content", "")).strip()
            if not title:
                continue

            templates.append(
                {
                    "title": title,
                    "content": content,
                    "normalized_title": normalize_title(title),
                    "category": classify_issue_title(title),
                    "source_file": csv_path.name,
                }
            )

    return templates


def build_template_status(repository_id: int, template_directory: str | Path = DEFAULT_TEMPLATE_DIRECTORY) -> dict:
    templates = load_issue_templates(template_directory)
    saved_issues = get_issues_by_repository_id(repository_id)
    issue_map = {
        normalize_title(issue["title"]): issue
        for issue in saved_issues
    }

    matched = []
    missing = []

    for template in templates:
        issue = issue_map.get(template["normalized_title"])
        if issue:
            matched.append(
                {
                    "title": template["title"],
                    "category": template["category"],
                    "source_file": template["source_file"],
                    "github_issue_id": issue["github_issue_id"],
                    "issue_number": issue["issue_number"],
                    "state": issue["state"],
                }
            )
        else:
            missing.append(
                {
                    "title": template["title"],
                    "content": template["content"],
                    "category": template["category"],
                    "source_file": template["source_file"],
                }
            )

    return {
        "template_count": len(templates),
        "matched_count": len(matched),
        "missing_count": len(missing),
        "matched_issues": matched,
        "missing_issues": missing,
    }


def create_missing_issues(
    repository: dict,
    access_token: str,
    template_directory: str | Path = DEFAULT_TEMPLATE_DIRECTORY,
) -> dict:
    status = build_template_status(repository["id"], template_directory)
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
                "issue_number": created_issue.get("number"),
                "issue_url": created_issue.get("html_url"),
                "state": created_issue.get("state", "open"),
            }
        )

    record_issue_sync_result(
        repository_id=repository["id"],
        week_label="template-missing-issues",
        source_csv_path=str(template_directory),
        requested_count=status["missing_count"],
        created_count=len(created_results),
        missing_count=max(status["missing_count"] - len(created_results), 0),
        status="completed",
        summary={
            "template_count": status["template_count"],
            "matched_count": status["matched_count"],
            "created_count": len(created_results),
        },
    )

    updated_status = build_template_status(repository["id"], template_directory)
    return {
        "template_count": updated_status["template_count"],
        "matched_count": updated_status["matched_count"],
        "missing_count": updated_status["missing_count"],
        "missing_issues": updated_status["missing_issues"],
        "created_issues": created_results,
    }


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip()).casefold()


def classify_issue_title(title: str) -> str:
    lowered = title.strip().casefold()
    if lowered.startswith("공통") or lowered.startswith("common"):
        return "common"
    if lowered.startswith("basic"):
        return "basic"
    week_match = re.match(r"week\s*\d+|w\d+|week\d+", lowered)
    if week_match:
        return "weekly"
    return "weekly"


def _read_csv_rows(csv_path: Path) -> list[dict]:
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            with csv_path.open("r", encoding=encoding, newline="") as file:
                return list(csv.DictReader(file))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"지원하지 않는 CSV 인코딩입니다: {csv_path}")

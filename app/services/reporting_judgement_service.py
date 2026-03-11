from __future__ import annotations

from typing import Callable


STATUS_PRIORITY = {
    "not_started": 0,
    "attempted": 1,
    "possibly_solved": 2,
    "solved": 3,
}


def collapse_judgements_for_reporting(
    judgements: list[dict],
    issues: list[dict],
    issue_matcher: Callable[[str, list[dict]], dict],
) -> tuple[list[dict], list[dict]]:
    issue_state_map = {
        item["issue_number"]: item["state"]
        for item in issues
        if item.get("issue_number") is not None
    }
    best_by_issue = {}
    extras = []

    for judgement in judgements:
        normalized = dict(judgement)
        issue_number = normalized.get("issue_number")

        if issue_number is None:
            inferred = issue_matcher(
                normalized.get("file_path") or normalized.get("problem_key", ""),
                issues,
            )
            matched_issue = inferred.get("issue")
            if matched_issue:
                issue_number = matched_issue.get("issue_number")
                normalized["issue_number"] = issue_number
                normalized["problem_key"] = matched_issue.get("title", normalized["problem_key"])

        if issue_number is None:
            extras.append(normalized)
            continue

        current = best_by_issue.get(issue_number)
        next_status = normalized["judgement_status"]
        if current is None or STATUS_PRIORITY.get(next_status, 0) > STATUS_PRIORITY.get(
            current["judgement_status"],
            0,
        ):
            best_by_issue[issue_number] = normalized

    collapsed = []
    for issue_number, judgement in best_by_issue.items():
        normalized = dict(judgement)
        if issue_state_map.get(issue_number) == "closed":
            normalized["judgement_status"] = "solved"
        collapsed.append(normalized)

    return collapsed, extras


def summarize_judgement_statuses(judgements: list[dict]) -> dict:
    summary = {
        "attempted_count": 0,
        "possibly_solved_count": 0,
        "solved_count": 0,
        "total_count": len(judgements),
    }
    for item in judgements:
        status = item.get("judgement_status")
        if status == "attempted":
            summary["attempted_count"] += 1
        elif status == "possibly_solved":
            summary["possibly_solved_count"] += 1
        elif status == "solved":
            summary["solved_count"] += 1
    return summary


def normalize_project_status(status: str | None) -> str:
    normalized = (status or "").strip().casefold().replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    if normalized == "done":
        return "done"
    if normalized in {"in progress", "inprogress"}:
        return "in_progress"
    if normalized in {"to do", "todo"}:
        return "todo"
    return ""


def resolve_tracked_issue_status(issue: dict, judgement_status: str | None) -> str | None:
    project_status = normalize_project_status(issue.get("project_status"))
    if project_status == "done":
        return "solved"
    if project_status == "in_progress":
        return "attempted"
    if project_status == "todo":
        return None
    if issue.get("state") == "closed":
        return "solved"
    return judgement_status


def build_reporting_issue_entries(
    issues: list[dict],
    judgements: list[dict],
    issue_matcher: Callable[[str, list[dict]], dict],
) -> tuple[list[dict], list[dict]]:
    collapsed, extras = collapse_judgements_for_reporting(judgements, issues, issue_matcher)
    judgement_by_issue = {item.get("issue_number"): item for item in collapsed if item.get("issue_number") is not None}
    tracked = []
    seen_issue_numbers = set()

    for issue in issues:
        matched = judgement_by_issue.get(issue.get("issue_number"), {})
        seen_issue_numbers.add(issue.get("issue_number"))
        tracked.append(
            {
                "issue_number": issue.get("issue_number"),
                "title": issue.get("title", ""),
                "state": issue.get("state", ""),
                "project_status": issue.get("project_status", ""),
                "problem_key": matched.get("problem_key") or issue.get("title", ""),
                "file_path": matched.get("file_path", ""),
                "judgement_status": resolve_tracked_issue_status(issue, matched.get("judgement_status")),
            }
        )

    for issue_number, matched in judgement_by_issue.items():
        if issue_number in seen_issue_numbers:
            continue
        tracked.append(
            {
                "issue_number": issue_number,
                "title": matched.get("problem_key", ""),
                "state": "",
                "project_status": "",
                "problem_key": matched.get("problem_key", ""),
                "file_path": matched.get("file_path", ""),
                "judgement_status": matched.get("judgement_status"),
            }
        )

    return tracked, extras


def normalize_commit_judgements_for_display(
    judgements: list[dict],
    issues: list[dict],
    issue_matcher: Callable[[str, list[dict]], dict],
) -> list[dict]:
    normalized_items = []
    issue_by_number = {item.get("issue_number"): item for item in issues if item.get("issue_number") is not None}

    for judgement in judgements:
        normalized = dict(judgement)
        matched_issue = issue_by_number.get(normalized.get("issue_number"))
        if matched_issue is None:
            inferred = issue_matcher(
                normalized.get("file_path") or normalized.get("problem_key", ""),
                issues,
            )
            matched_issue = inferred.get("issue")
            if matched_issue:
                normalized["issue_number"] = matched_issue.get("issue_number")

        if matched_issue is not None:
            normalized["problem_key"] = matched_issue.get("title", normalized.get("problem_key"))
            normalized["judgement_status"] = resolve_tracked_issue_status(
                matched_issue,
                normalized.get("judgement_status"),
            )

        normalized_items.append(normalized)

    return normalized_items

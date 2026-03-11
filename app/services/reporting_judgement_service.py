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

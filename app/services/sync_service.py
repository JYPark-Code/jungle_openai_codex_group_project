from app.models.db import (
    get_sync_status,
    record_issue_sync_result,
    save_commit,
    save_issue,
    update_repository_last_synced_at,
)
from app.services.github_service import fetch_repository_commits, fetch_repository_issues


def sync_repository_issues_and_commits(repository: dict, access_token: str) -> dict:
    owner = repository["owner"]
    name = repository["name"]
    repository_id = repository["id"]

    issues = fetch_repository_issues(owner, name, access_token)
    commits = fetch_repository_commits(owner, name, access_token)

    new_issue_count = 0
    for issue in issues:
        _, created = save_issue(
            repository_id=repository_id,
            github_issue_id=issue["github_issue_id"],
            issue_number=issue.get("issue_number"),
            title=issue["title"],
            body=issue["body"],
            state=issue["state"],
            github_created_at=issue["created_at"],
        )
        if created:
            new_issue_count += 1

    new_commit_count = 0
    for commit in commits:
        _, created = save_commit(
            repository_id=repository_id,
            sha=commit["sha"],
            message=commit["message"],
            author_name=commit["author_name"],
            committed_at=commit["committed_at"],
            analyzed_at=commit.get("analyzed_at"),
        )
        if created:
            new_commit_count += 1

    update_repository_last_synced_at(repository_id)
    status = get_sync_status(repository_id)

    record_issue_sync_result(
        repository_id=repository_id,
        week_label="repository-sync",
        source_csv_path="github-api",
        requested_count=len(issues),
        created_count=new_issue_count,
        missing_count=0,
        status="completed",
        summary={
            "new_issue_count": new_issue_count,
            "new_commit_count": new_commit_count,
            "issue_total": status["issue_count"],
            "commit_total": status["commit_count"],
        },
    )

    return {
        "new_issue_count": new_issue_count,
        "new_commit_count": new_commit_count,
        "last_synced_at": status["last_synced_at"],
        "issue_total": status["issue_count"],
        "commit_total": status["commit_count"],
    }

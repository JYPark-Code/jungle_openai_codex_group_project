import base64
import os

import requests


GITHUB_API_BASE_URL = "https://api.github.com"


def resolve_repo_target(repo_owner: str = "", repo_name: str = "") -> tuple[str, str]:
    owner = (repo_owner or os.getenv("REPO_OWNER", "")).strip()
    name = (repo_name or os.getenv("REPO_NAME", "")).strip()

    if not owner and "/" in name:
        owner, name = name.split("/", 1)

    return owner, name


def build_github_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_repository(repo_owner: str, repo_name: str) -> dict:
    url = f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}"
    response = requests.get(url, headers=build_github_headers(), timeout=15)
    response.raise_for_status()
    return response.json()


def fetch_repository_issues(repo_owner: str, repo_name: str, access_token: str) -> list[dict]:
    response = requests.get(
        f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/issues",
        headers=_build_user_headers(access_token),
        params={
            "state": "all",
            "per_page": 100,
        },
        timeout=20,
    )
    response.raise_for_status()

    issues = []
    for item in response.json():
        if item.get("pull_request"):
            continue
        issues.append(
            {
                "github_issue_id": str(item.get("id", "")),
                "issue_number": item.get("number"),
                "title": item.get("title", ""),
                "body": item.get("body") or "",
                "state": item.get("state", "open"),
                "created_at": item.get("created_at", ""),
            }
        )
    return issues


def fetch_repository_commits(repo_owner: str, repo_name: str, access_token: str) -> list[dict]:
    response = requests.get(
        f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/commits",
        headers=_build_user_headers(access_token),
        params={"per_page": 100},
        timeout=20,
    )
    response.raise_for_status()

    commits = []
    for item in response.json():
        commit_info = item.get("commit") or {}
        author_info = commit_info.get("author") or {}
        commits.append(
            {
                "sha": item.get("sha", ""),
                "message": commit_info.get("message", ""),
                "author_name": author_info.get("name") or ((item.get("author") or {}).get("login", "")),
                "committed_at": author_info.get("date", ""),
                "analyzed_at": None,
            }
        )
    return commits


def fetch_commit_changed_files(repo_owner: str, repo_name: str, sha: str, access_token: str) -> dict:
    response = requests.get(
        f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/commits/{sha}",
        headers=_build_user_headers(access_token),
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    commit_info = payload.get("commit") or {}
    author_info = commit_info.get("author") or {}

    files = []
    for item in payload.get("files", []):
        files.append(
            {
                "filename": item.get("filename", ""),
                "status": item.get("status", ""),
                "additions": item.get("additions", 0),
                "deletions": item.get("deletions", 0),
                "changes": item.get("changes", 0),
            }
        )

    return {
        "sha": payload.get("sha", sha),
        "message": commit_info.get("message", ""),
        "author_name": author_info.get("name") or ((payload.get("author") or {}).get("login", "")),
        "committed_at": author_info.get("date", ""),
        "files": files,
    }


def fetch_file_content_at_ref(
    repo_owner: str,
    repo_name: str,
    file_path: str,
    ref: str,
    access_token: str,
) -> str:
    response = requests.get(
        f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/contents/{file_path}",
        headers=_build_user_headers(access_token),
        params={"ref": ref},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    encoded_content = payload.get("content", "")
    if payload.get("encoding") != "base64" or not encoded_content:
        return ""
    return base64.b64decode(encoded_content).decode("utf-8", errors="ignore")


def fetch_python_files_from_github(repo_owner: str, repo_name: str, max_files: int = 25) -> list[dict]:
    repository = get_repository(repo_owner, repo_name)
    default_branch = repository.get("default_branch", "main")
    tree_url = f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/git/trees/{default_branch}?recursive=1"
    tree_response = requests.get(tree_url, headers=build_github_headers(), timeout=20)
    tree_response.raise_for_status()

    tree = tree_response.json().get("tree", [])
    python_entries = [
        entry for entry in tree
        if entry.get("type") == "blob" and entry.get("path", "").endswith(".py")
    ][:max_files]

    python_files = []
    for entry in python_entries:
        blob_url = entry.get("url")
        if not blob_url:
            continue

        blob_response = requests.get(blob_url, headers=build_github_headers(), timeout=20)
        blob_response.raise_for_status()
        blob_json = blob_response.json()
        encoded_content = blob_json.get("content", "")
        encoding = blob_json.get("encoding", "")

        if encoding != "base64" or not encoded_content:
            continue

        source_text = base64.b64decode(encoded_content).decode("utf-8", errors="ignore")
        python_files.append(
            {
                "path": entry.get("path", ""),
                "content": source_text,
            }
        )

    return python_files


def create_issue(repo_owner: str, repo_name: str, title: str, body: str = "") -> dict:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise ValueError("GITHUB_TOKEN is not set.")

    return create_issue_with_access_token(token, repo_owner, repo_name, title, body)


def create_issue_with_access_token(
    access_token: str,
    repo_owner: str,
    repo_name: str,
    title: str,
    body: str = "",
) -> dict:
    if not access_token:
        raise ValueError("access_token is required.")

    if not repo_owner or not repo_name or not title:
        raise ValueError("repo_owner, repo_name, and title are required.")

    url = f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/issues"
    headers = _build_user_headers(access_token)
    response = requests.post(
        url,
        headers=headers,
        json={"title": title, "body": body},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _build_user_headers(access_token: str) -> dict:
    if not access_token:
        raise ValueError("access_token is required.")

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

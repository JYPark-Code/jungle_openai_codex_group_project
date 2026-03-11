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

    if not repo_owner or not repo_name or not title:
        raise ValueError("repo_owner, repo_name, and title are required.")

    url = f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/issues"
    headers = build_github_headers()
    headers["Authorization"] = f"Bearer {token}"
    payload = {
        "title": title,
        "body": body,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def create_issues_for_problems(repo_owner: str, repo_name: str, problems: list[str]) -> list[dict]:
    created_issues = []

    for problem in problems:
        issue = create_issue(
            repo_owner=repo_owner,
            repo_name=repo_name,
            title=problem["title"],
            body=problem["body"],
        )
        created_issues.append(issue)

    return created_issues

import requests

from app.utils.errors import ApiError


GITHUB_USER_REPOSITORIES_API_URL = "https://api.github.com/user/repos"


def fetch_user_repositories(access_token: str) -> list[dict]:
    if not access_token:
        raise ApiError("UNAUTHORIZED", "로그인이 필요합니다.", 401)

    response = requests.get(
        GITHUB_USER_REPOSITORIES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        params={
            "sort": "updated",
            "per_page": 100,
        },
        timeout=20,
    )
    response.raise_for_status()

    repositories = []
    for item in response.json():
        owner = (item.get("owner") or {}).get("login", "")
        name = item.get("name", "")
        repositories.append(
            {
                "github_repo_id": str(item.get("id", "")),
                "owner": owner,
                "name": name,
                "full_name": item.get("full_name", f"{owner}/{name}"),
                "default_branch": item.get("default_branch", ""),
                "private": bool(item.get("private", False)),
            }
        )

    return repositories

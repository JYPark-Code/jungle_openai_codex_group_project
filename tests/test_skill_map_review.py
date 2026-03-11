from app.models.db import (
    save_commit,
    save_problem_judgement,
    upsert_repository_for_user,
    upsert_user,
)
from app.services.skill_map_service import (
    build_reverse_taxonomy,
    build_skill_map,
    match_categories_from_text,
)
from app.services.code_review import estimate_time_complexity, evaluate_code_structure


def ensure_review_context(app):
    with app.app_context():
        user_id = upsert_user("7007", "review-user", "리뷰 사용자")
        repository_id = upsert_repository_for_user(
            user_id=user_id,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="777",
            default_branch="main",
        )
        commit_id, _ = save_commit(
            repository_id=repository_id,
            sha="review123",
            message="그래프 풀이 추가",
            author_name="JYPark",
            committed_at="2026-03-11T12:00:00Z",
        )
    return repository_id, commit_id


def login_for_review(client, repository_id):
    with client.session_transaction() as session:
        session["auth_user_id"] = 1
        session["oauth_access_token"] = "review-token"
        session["current_repository_id"] = repository_id
        session["current_repository_full_name"] = "JYPark-Code/SW-AI-W02-05"


def test_category_matching_works():
    categories = match_categories_from_text("week2/graph_bfs_solution.py", "from collections import deque\nvisited = set()")

    assert "그래프" in categories
    assert "BFS" in categories


def test_reverse_taxonomy_mapping():
    reverse_mapping = build_reverse_taxonomy()

    assert reverse_mapping["그래프"] == "자료구조"
    assert reverse_mapping["BFS"] == "탐색"
    assert reverse_mapping["문자열"] == "구현"


def test_skill_map_statistics(app):
    repository_id, commit_id = ensure_review_context(app)

    with app.app_context():
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="그래프 BFS 탐색",
            file_path="week2/graph_bfs.py",
            judgement_status="solved",
            match_score=1.0,
            matched_by_filename=True,
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=2,
            problem_key="문자열 구현",
            file_path="week2/string_impl.py",
            judgement_status="attempted",
            match_score=0.4,
        )

        skill_map = build_skill_map(repository_id)

    domains = {item["name"]: item for item in skill_map["domains"]}
    assert domains["자료구조"]["total"] == 1
    assert domains["자료구조"]["solved"] == 1
    assert domains["탐색"]["total"] == 1
    assert domains["탐색"]["solved"] == 1
    assert domains["구현"]["attempted"] == 1


def test_commit_review_generation(client, app, monkeypatch):
    repository_id, _commit_id = ensure_review_context(app)
    login_for_review(client, repository_id)

    monkeypatch.setattr(
        "app.services.code_review.fetch_commit_changed_files",
        lambda owner, name, sha, access_token: {
            "sha": sha,
            "message": "그래프 풀이 추가",
            "author_name": "JYPark",
            "committed_at": "2026-03-11T12:00:00Z",
            "files": [
                {
                    "filename": "week2/graph_bfs.py",
                    "status": "added",
                    "additions": 20,
                    "deletions": 0,
                    "changes": 20,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.services.code_review.fetch_file_content_at_ref",
        lambda owner, name, file_path, ref, access_token: "from collections import deque\nvisited = set()\nqueue = deque([1])\n",
    )

    response = client.post("/api/commits/review123/review")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["python_file_count"] == 1
    assert "BFS" in payload["data"]["detected_topics"]
    assert payload["data"]["review_summary"]


def test_review_and_skill_map_api_responses(client, app, monkeypatch):
    repository_id, commit_id = ensure_review_context(app)
    login_for_review(client, repository_id)

    with app.app_context():
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="그래프 BFS 탐색",
            file_path="week2/graph_bfs.py",
            judgement_status="possibly_solved",
            match_score=0.8,
            matched_by_filename=True,
        )

    monkeypatch.setattr(
        "app.services.code_review.fetch_commit_changed_files",
        lambda owner, name, sha, access_token: {
            "sha": sha,
            "message": "그래프 풀이 추가",
            "author_name": "JYPark",
            "committed_at": "2026-03-11T12:00:00Z",
            "files": [
                {
                    "filename": "week2/graph_bfs.py",
                    "status": "added",
                    "additions": 20,
                    "deletions": 0,
                    "changes": 20,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.services.code_review.fetch_file_content_at_ref",
        lambda owner, name, file_path, ref, access_token: "from collections import deque\nvisited = set()\nqueue = deque([1])\n",
    )

    create_response = client.post("/api/commits/review123/review")
    review_response = client.get("/api/commits/review123/review")
    skill_map_response = client.get("/api/repositories/current/skill-map")

    assert create_response.status_code == 200
    assert review_response.status_code == 200
    assert skill_map_response.status_code == 200
    assert "review_summary" in review_response.get_json()["data"]
    assert "domains" in skill_map_response.get_json()["data"]


def test_code_review_ignores_docstring_when_estimating_complexity():
    source = '''"""
for i in range(n):
    for j in range(n):
        pass
"""

def solve():
    for value in range(10):
        print(value)
'''

    complexity = estimate_time_complexity(source, ["구현"])
    assert complexity == "O(N) 내외"


def test_code_review_does_not_overpraise_single_long_function():
    source = """
def solve():
    total = 0
    for number in range(10):
        total += number
    for number in range(10):
        total += number
    for number in range(10):
        total += number
    for number in range(10):
        total += number
    for number in range(10):
        total += number
    for number in range(10):
        total += number
    for number in range(10):
        total += number
    for number in range(10):
        total += number
    return total
"""

    structure = evaluate_code_structure(source)
    assert "함수 분리가 되어 있어 구조가 비교적 명확합니다." != structure

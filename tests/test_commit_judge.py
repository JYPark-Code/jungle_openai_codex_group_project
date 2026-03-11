from app.models.db import (
    get_commit_by_sha,
    get_problem_judgements_by_commit_id,
    save_commit,
    save_issue,
    save_problem_judgement,
    upsert_repository_for_user,
    upsert_user,
)
from app.services.commit_judge_service import (
    evaluate_problem_status,
    get_repository_problem_summary,
    match_issue_by_filename,
    normalize_problem_filename,
)


def ensure_commit_context(app):
    with app.app_context():
        user_id = upsert_user("6006", "judge-user", "판정 사용자")
        repository_id = upsert_repository_for_user(
            user_id=user_id,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="888",
            default_branch="main",
        )
        commit_id, _ = save_commit(
            repository_id=repository_id,
            sha="abc123",
            message="문제 풀이 커밋",
            author_name="JYPark",
            committed_at="2026-03-11T12:00:00Z",
        )
    return repository_id, commit_id


def login_with_repository_and_user(client, repository_id):
    with client.session_transaction() as session:
        session["auth_user_id"] = 1
        session["oauth_access_token"] = "judge-token"
        session["current_repository_id"] = repository_id
        session["current_repository_full_name"] = "JYPark-Code/SW-AI-W02-05"


def test_status_transition_rules():
    assert evaluate_problem_status(True, False, False, False) == "attempted"
    assert evaluate_problem_status(True, True, False, False) == "possibly_solved"
    assert evaluate_problem_status(True, True, True, True) == "solved"


def test_python_file_filtering_and_issue_matching(client, app, monkeypatch):
    repository_id, _commit_id = ensure_commit_context(app)
    login_with_repository_and_user(client, repository_id)

    with app.app_context():
        save_issue(
            repository_id=repository_id,
            github_issue_id="100",
            issue_number=10,
            title="문자열 광고 플래4",
            body="문제 설명",
            state="open",
            github_created_at="2026-03-11T10:00:00Z",
        )

    monkeypatch.setattr(
        "app.services.commit_judge_service.fetch_commit_changed_files",
        lambda owner, name, sha, access_token: {
            "sha": sha,
            "message": "문제 풀이 커밋",
            "author_name": "JYPark",
            "committed_at": "2026-03-11T12:00:00Z",
            "files": [
                {
                    "filename": "week2/문자열_광고_플래4.py",
                    "status": "added",
                    "additions": 10,
                    "deletions": 0,
                    "changes": 10,
                },
                {
                    "filename": "README.md",
                    "status": "modified",
                    "additions": 1,
                    "deletions": 0,
                    "changes": 1,
                },
            ],
        },
    )

    response = client.post("/api/commits/abc123/analyze-files")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["analyzed_file_count"] == 2
    assert payload["data"]["python_file_count"] == 1
    assert payload["data"]["possibly_solved_count"] == 1
    assert payload["data"]["solved_count"] == 0
    assert payload["data"]["analyzed_at"] is not None


def test_file_name_normalization():
    assert normalize_problem_filename("week2/난이도상_문자열_광고_플래4.py") == "문자열 광고"


def test_issue_matching_returns_strong_match():
    issues = [
        {"title": "문자열 광고 플래4", "issue_number": 10},
        {"title": "그래프 순회", "issue_number": 11},
    ]

    result = match_issue_by_filename("week2/문자열_광고_플래4.py", issues)

    assert result["issue"]["issue_number"] == 10
    assert result["is_strong_match"] is True
    assert result["score"] >= 0.6


def test_analysis_result_is_saved_and_can_be_read(client, app, monkeypatch):
    repository_id, commit_id = ensure_commit_context(app)
    login_with_repository_and_user(client, repository_id)

    with app.app_context():
        save_issue(
            repository_id=repository_id,
            github_issue_id="100",
            issue_number=10,
            title="문자열 광고 플래4",
            body="문제 설명",
            state="open",
            github_created_at="2026-03-11T10:00:00Z",
        )

    monkeypatch.setattr(
        "app.services.commit_judge_service.fetch_commit_changed_files",
        lambda owner, name, sha, access_token: {
            "sha": sha,
            "message": "문제 풀이 커밋",
            "author_name": "JYPark",
            "committed_at": "2026-03-11T12:00:00Z",
            "files": [
                {
                    "filename": "week2/문자열_광고_플래4.py",
                    "status": "added",
                    "additions": 10,
                    "deletions": 0,
                    "changes": 10,
                }
            ],
        },
    )

    client.post("/api/commits/abc123/judge")

    with app.app_context():
        judgements = get_problem_judgements_by_commit_id(commit_id)
        commit = get_commit_by_sha(repository_id, "abc123")

    assert len(judgements) == 1
    assert judgements[0]["judgement_status"] == "possibly_solved"
    assert judgements[0]["match_score"] >= 0.6
    assert commit["analyzed_at"] is not None


def test_commit_judge_result_and_repository_summary(client, app, monkeypatch):
    repository_id, _commit_id = ensure_commit_context(app)
    login_with_repository_and_user(client, repository_id)

    with app.app_context():
        save_issue(
            repository_id=repository_id,
            github_issue_id="100",
            issue_number=10,
            title="문자열 광고 플래4",
            body="문제 설명",
            state="open",
            github_created_at="2026-03-11T10:00:00Z",
        )

    monkeypatch.setattr(
        "app.services.commit_judge_service.fetch_commit_changed_files",
        lambda owner, name, sha, access_token: {
            "sha": sha,
            "message": "문제 풀이 커밋",
            "author_name": "JYPark",
            "committed_at": "2026-03-11T12:00:00Z",
            "files": [
                {
                    "filename": "week2/문자열_광고_플래4.py",
                    "status": "added",
                    "additions": 10,
                    "deletions": 0,
                    "changes": 10,
                }
            ],
        },
    )

    client.post("/api/commits/abc123/judge")

    judge_result_response = client.get("/api/commits/abc123/judge-result")
    summary_response = client.get("/api/repositories/current/problem-summary")

    assert judge_result_response.status_code == 200
    assert judge_result_response.get_json()["data"]["possibly_solved_count"] == 1
    assert summary_response.status_code == 200
    assert summary_response.get_json()["data"]["possibly_solved_count"] == 1


def test_repository_problem_summary_counts_all_statuses(app):
    repository_id, commit_id = ensure_commit_context(app)

    with app.app_context():
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="문제 A",
            file_path="week2/problem_a.py",
            judgement_status="attempted",
            match_score=0.2,
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=2,
            problem_key="문제 B",
            file_path="week2/problem_b.py",
            judgement_status="possibly_solved",
            match_score=0.8,
            matched_by_filename=True,
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=3,
            problem_key="문제 C",
            file_path="week2/problem_c.py",
            judgement_status="solved",
            match_score=1.0,
            matched_by_filename=True,
            execution_passed=True,
            sample_output_matched=True,
        )

        summary = get_repository_problem_summary(repository_id)

    assert summary["attempted_count"] == 1
    assert summary["possibly_solved_count"] == 1
    assert summary["solved_count"] == 1
    assert summary["total_count"] == 3


def test_high_difficulty_filename_normalization():
    assert normalize_problem_filename("week2/난이도상_문자열_광고_플래4.py") == "문자열 광고"

from app.models.db import (
    list_recommendations_by_repository_id,
    save_commit,
    save_commit_analysis_result,
    save_problem_judgement,
    upsert_repository_for_user,
    upsert_user,
)
from app.services.recommendation_service import calculate_weak_topics, generate_recommendations, get_recommendations


def ensure_recommendation_context(app):
    with app.app_context():
        user_id = upsert_user("8008", "recommend-user", "추천 사용자")
        repository_id = upsert_repository_for_user(
            user_id=user_id,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="666",
            default_branch="main",
        )
        commit_id, _ = save_commit(
            repository_id=repository_id,
            sha="recommend123",
            message="문자열 풀이 추가",
            author_name="JYPark",
            committed_at="2026-03-11T12:00:00Z",
        )
        save_commit_analysis_result(
            commit_id=commit_id,
            review_summary="문자열 중심 풀이입니다.",
            review_comments=["문자열 처리가 중심입니다."],
            execution_status="not_run",
            execution_output={},
            detected_topics=["문자열"],
        )
    return repository_id, commit_id


def login_for_recommendations(client, repository_id):
    with client.session_transaction() as session:
        session["auth_user_id"] = 1
        session["oauth_access_token"] = "recommend-token"
        session["current_repository_id"] = repository_id
        session["current_repository_full_name"] = "JYPark-Code/SW-AI-W02-05"


def test_calculate_weak_topics(app):
    repository_id, commit_id = ensure_recommendation_context(app)

    with app.app_context():
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="문자열 구현 문제",
            file_path="week2/string_impl.py",
            judgement_status="attempted",
            match_score=0.4,
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=2,
            problem_key="그래프 BFS 문제",
            file_path="week2/graph_bfs.py",
            judgement_status="solved",
            match_score=1.0,
            matched_by_filename=True,
        )

        weak_topics = calculate_weak_topics(repository_id)

    assert "문자열" in weak_topics


def test_generate_recommendations_and_prevent_duplicates(app):
    repository_id, commit_id = ensure_recommendation_context(app)

    with app.app_context():
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="다이나믹프로그래밍 문제",
            file_path="week2/dp_problem.py",
            judgement_status="attempted",
            match_score=0.4,
        )

        first_result = generate_recommendations(repository_id)
        second_result = generate_recommendations(repository_id)
        saved = list_recommendations_by_repository_id(repository_id)

    assert first_result["recommendations"]
    assert second_result["recommendations"] == []
    assert len(saved) == len(first_result["recommendations"])


def test_recommendation_is_saved(app):
    repository_id, commit_id = ensure_recommendation_context(app)

    with app.app_context():
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="이분탐색 문제",
            file_path="week2/binary_search.py",
            judgement_status="attempted",
            match_score=0.4,
        )

        generate_recommendations(repository_id)
        saved = list_recommendations_by_repository_id(repository_id)

    assert saved
    assert "reason" in saved[0]


def test_recommendation_api_returns_saved_items(client, app):
    repository_id, commit_id = ensure_recommendation_context(app)
    login_for_recommendations(client, repository_id)

    with app.app_context():
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="그래프 BFS 문제",
            file_path="week2/graph_bfs.py",
            judgement_status="attempted",
            match_score=0.4,
        )

    generate_response = client.post("/api/repositories/current/recommendations/generate")
    list_response = client.get("/api/repositories/current/recommendations")

    assert generate_response.status_code == 200
    assert "weak_topics" in generate_response.get_json()["data"]
    assert list_response.status_code == 200
    assert "recommendations" in list_response.get_json()["data"]


def test_invalid_legacy_recommendation_is_filtered(app):
    repository_id, _commit_id = ensure_recommendation_context(app)

    with app.app_context():
        from app.models.db import save_recommendation

        save_recommendation(
            repository_id=repository_id,
            topic="구현",
            problem_title="상하좌우",
            problem_url="https://www.acmicpc.net/",
            source_site="baekjoon",
            reason="legacy",
        )
        data = get_recommendations(repository_id)

    assert data["recommendations"] == []

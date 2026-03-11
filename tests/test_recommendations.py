from app.models.db import (
    list_recommendations_by_repository_id,
    save_commit,
    save_commit_analysis_result,
    save_issue,
    save_problem_judgement,
    upsert_repository_for_user,
    upsert_user,
)
from app.services.recommendation_service import calculate_weak_topics, generate_recommendations, get_recommendations, rank_weak_topics


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


def test_rank_weak_topics_treats_closed_issues_as_solved(app):
    repository_id, commit_id = ensure_recommendation_context(app)

    with app.app_context():
        save_issue(
            repository_id=repository_id,
            github_issue_id="closed-1",
            issue_number=1,
            title="[WEEK2] 문자열 - 광고",
            body="",
            state="closed",
            github_created_at="2026-03-11T12:00:00Z",
        )
        save_issue(
            repository_id=repository_id,
            github_issue_id="open-2",
            issue_number=2,
            title="[WEEK2] 문자열 - 압축",
            body="",
            state="open",
            github_created_at="2026-03-11T12:00:00Z",
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="[WEEK2] 문자열 - 광고",
            file_path="week2/problem-solving/문자열_광고.py",
            judgement_status="attempted",
            match_score=0.4,
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=2,
            problem_key="[WEEK2] 문자열 - 압축",
            file_path="week2/problem-solving/문자열_압축.py",
            judgement_status="attempted",
            match_score=0.4,
        )

        ranking = rank_weak_topics(repository_id, limit=10)

    string_topic = next(item for item in ranking if item["topic"] == "문자열")
    assert string_topic["solved"] == 1
    assert string_topic["total"] == 2
    assert string_topic["solved_ratio"] == 0.5


def test_rank_weak_topics_collapses_duplicate_issue_judgements(app):
    repository_id, commit_id = ensure_recommendation_context(app)

    with app.app_context():
        save_issue(
            repository_id=repository_id,
            github_issue_id="open-3",
            issue_number=3,
            title="[WEEK2] 구현 - 달팽이",
            body="",
            state="open",
            github_created_at="2026-03-11T12:00:00Z",
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=3,
            problem_key="[WEEK2] 구현 - 달팽이",
            file_path="week2/basic/구현_달팽이.py",
            judgement_status="attempted",
            match_score=0.4,
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=3,
            problem_key="[WEEK2] 구현 - 달팽이",
            file_path="week2/basic/구현_달팽이.py",
            judgement_status="possibly_solved",
            match_score=0.8,
        )

        ranking = rank_weak_topics(repository_id, limit=10)

    impl_topic = next(item for item in ranking if item["topic"] == "구현")
    assert impl_topic["total"] == 1
    assert impl_topic["solved"] == 0
    assert impl_topic["solved_ratio"] == 0.0


def test_rank_weak_topics_recovers_closed_issue_from_orphan_judgement(app):
    with app.app_context():
        user_id = upsert_user("8010", "recommend-user-orphan", "orphan test")
        repository_id = upsert_repository_for_user(
            user_id=user_id,
            owner="JYPark-Code",
            name="SW-AI-W02-05-orphan",
            full_name="JYPark-Code/SW-AI-W02-05-orphan",
            github_repo_id="667",
            default_branch="main",
        )
        commit_id, _ = save_commit(
            repository_id=repository_id,
            sha="recommend-orphan",
            message="recover orphan judgement",
            author_name="JYPark",
            committed_at="2026-03-11T12:00:00Z",
        )
        save_issue(
            repository_id=repository_id,
            github_issue_id="closed-ipv6",
            issue_number=23,
            title="[WEEK2] 문자열 - IPv6",
            body="",
            state="closed",
            github_created_at="2026-03-11T12:00:00Z",
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=None,
            problem_key="난이도중_문자열_IPv6_골드5.py",
            file_path="week2/problem-solving/난이도중_문자열_IPv6_골드5.py",
            judgement_status="attempted",
            match_score=0.0,
        )

        ranking = rank_weak_topics(repository_id, limit=10)

    assert not any(item["topic"] == "문자열" and item["total"] > 0 for item in ranking)


def test_rank_weak_topics_excludes_recent_only_topics_without_problem_data(app):
    repository_id, commit_id = ensure_recommendation_context(app)

    with app.app_context():
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="[WEEK2] 구현 - 예시",
            file_path="week2/basic/구현_예시.py",
            judgement_status="attempted",
            match_score=0.4,
        )

        ranking = rank_weak_topics(repository_id, limit=10)

    assert all(item["total"] > 0 for item in ranking)


def test_get_recommendations_filters_out_stale_topics(app):
    repository_id, commit_id = ensure_recommendation_context(app)

    with app.app_context():
        save_issue(
            repository_id=repository_id,
            github_issue_id="closed-math",
            issue_number=22,
            title="[WEEK2] 정수론 - 소수 찾기",
            body="",
            state="closed",
            github_created_at="2026-03-11T12:00:00Z",
        )
        save_issue(
            repository_id=repository_id,
            github_issue_id="open-impl",
            issue_number=17,
            title="[WEEK2] 파이썬 문법 - 최댓값",
            body="",
            state="open",
            github_created_at="2026-03-11T12:00:00Z",
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=22,
            problem_key="[WEEK2] 정수론 - 소수 찾기",
            file_path="week2/problem-solving/정수론_소수찾기.py",
            judgement_status="attempted",
            match_score=0.4,
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=17,
            problem_key="[WEEK2] 파이썬 문법 - 최댓값",
            file_path="week2/basic/파이썬문법_최댓값.py",
            judgement_status="attempted",
            match_score=0.4,
        )

        from app.models.db import save_recommendation

        save_recommendation(
            repository_id=repository_id,
            topic="DFS",
            problem_title="타겟 넘버",
            problem_url="https://school.programmers.co.kr/learn/courses/30/lessons/43165",
            source_site="programmers",
            reason="stale",
        )
        save_recommendation(
            repository_id=repository_id,
            topic="수학",
            problem_title="소수 찾기",
            problem_url="https://www.acmicpc.net/problem/1978",
            source_site="baekjoon",
            reason="active",
        )

        data = get_recommendations(repository_id)

    assert all(item["topic"] in data["weak_topics"] for item in data["recommendations"])

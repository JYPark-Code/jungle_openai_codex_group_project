from app.models.db import (
    get_latest_analysis_report,
    save_commit,
    save_commit_analysis_result,
    save_problem_judgement,
    save_recommendation,
    save_issue,
    update_repository_last_synced_at,
    upsert_repository_for_user,
    upsert_user,
)
from app.services.report_service import build_user_report, evaluate_learning_status


def ensure_report_context(app):
    with app.app_context():
        user_id = upsert_user("9009", "report-user", "리포트 사용자")
        repository_id = upsert_repository_for_user(
            user_id=user_id,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="555",
            default_branch="main",
        )
        commit_id, _ = save_commit(
            repository_id=repository_id,
            sha="report123",
            message="주차 풀이 업로드",
            author_name="JYPark",
            committed_at="2026-03-11T12:00:00Z",
        )
        save_commit_analysis_result(
            commit_id=commit_id,
            review_summary="그래프와 BFS 풀이가 중심입니다.",
            review_comments=["그래프 탐색 흐름이 보입니다."],
            execution_status="not_run",
            execution_output={},
            detected_topics=["그래프", "BFS"],
        )
        save_issue(
            repository_id=repository_id,
            github_issue_id="100",
            issue_number=1,
            title="week2 - 그래프 BFS 문제",
            body="content",
            state="open",
            github_created_at="2026-03-11T10:00:00Z",
        )
        save_issue(
            repository_id=repository_id,
            github_issue_id="101",
            issue_number=2,
            title="week3 - 문자열 문제",
            body="content",
            state="open",
            github_created_at="2026-03-11T10:10:00Z",
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="그래프 BFS 문제",
            file_path="week2/graph_bfs.py",
            judgement_status="solved",
            match_score=1.0,
            matched_by_filename=True,
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=2,
            problem_key="문자열 문제",
            file_path="week3/string_problem.py",
            judgement_status="attempted",
            match_score=0.5,
        )
        save_recommendation(
            repository_id=repository_id,
            topic="문자열",
            problem_title="문자열 압축",
            problem_url="https://school.programmers.co.kr/learn/courses/30/lessons/60057",
            source_site="programmers",
            reason="문자열 유형 보강이 필요합니다.",
        )
        update_repository_last_synced_at(repository_id, "2026-03-11T12:30:00Z")
    return repository_id


def login_for_report(client, repository_id):
    with client.session_transaction() as session:
        session["auth_user_id"] = 1
        session["oauth_access_token"] = "report-token"
        session["current_repository_id"] = repository_id
        session["current_repository_full_name"] = "JYPark-Code/SW-AI-W02-05"


def test_report_aggregation(app, monkeypatch):
    repository_id = ensure_report_context(app)

    monkeypatch.setattr(
        "app.services.report_service.build_template_status",
        lambda repository_id: {
            "template_count": 5,
            "matched_count": 3,
            "missing_count": 2,
            "matched_issues": [],
            "missing_issues": [],
        },
    )

    with app.app_context():
        report = build_user_report(repository_id)
        saved_report = get_latest_analysis_report(repository_id, "mypage_report")

    assert report["solved_count"] == 1
    assert report["attempted_count"] == 1
    assert report["week_progress"] == 0.6
    assert saved_report is not None


def test_status_evaluation_rules():
    assert evaluate_learning_status(1.0, 1.0, 3) == "Good"
    assert evaluate_learning_status(0.8, 0.7, 1) == "Good"
    assert evaluate_learning_status(0.3, 0.2, 4) == "Risk"
    assert evaluate_learning_status(0.6, 0.45, 3) == "Watch"


def test_dashboard_summary_api(client, app, monkeypatch):
    repository_id = ensure_report_context(app)
    login_for_report(client, repository_id)

    monkeypatch.setattr(
        "app.services.report_service.build_template_status",
        lambda repository_id: {
            "template_count": 5,
            "matched_count": 4,
            "missing_count": 1,
            "matched_issues": [],
            "missing_issues": [],
        },
    )

    response = client.get("/api/dashboard/summary")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["status"] in {"Good", "Watch", "Risk"}
    assert "skill_map" in payload["data"]


def test_mypage_report_api(client, app, monkeypatch):
    repository_id = ensure_report_context(app)
    login_for_report(client, repository_id)

    monkeypatch.setattr(
        "app.services.report_service.build_template_status",
        lambda repository_id: {
            "template_count": 5,
            "matched_count": 2,
            "missing_count": 3,
            "matched_issues": [],
            "missing_issues": [],
        },
    )

    response = client.get("/api/mypage/report")
    payload = response.get_json()

    assert response.status_code == 200
    assert "ai_summary" in payload["data"]
    assert "domain_analysis" in payload["data"]
    assert "weak_topic_ranking" in payload["data"]
    assert "recommendations" in payload["data"]

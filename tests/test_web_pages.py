from app.models.db import (
    save_commit,
    save_commit_analysis_result,
    save_issue,
    save_problem_judgement,
    save_recommendation,
    upsert_repository_for_user,
    upsert_user,
)


def ensure_web_context(app):
    with app.app_context():
        user_id = upsert_user("4004", "web-user", "웹 사용자")
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
            sha="web123",
            message="그래프 문제 풀이",
            author_name="웹 사용자",
            committed_at="2026-03-11T12:00:00Z",
        )
        save_commit_analysis_result(
            commit_id=commit_id,
            review_summary="그래프와 BFS 위주 풀이입니다.",
            review_comments=["week2/graph_problem.py: 함수 분리를 고려해보세요."],
            execution_status="not_run",
            execution_output={
                "files": [
                    {
                        "file_path": "week2/graph_problem.py",
                        "line_comments": [
                            {
                                "file_path": "week2/graph_problem.py",
                                "start_line": 1,
                                "end_line": 3,
                                "title": "중첩 반복문 확인",
                                "body": "중첩 반복문이 보여 입력 크기에 따라 비용이 커질 수 있습니다.",
                                "snippet": "for x in range(3):\n    for y in range(2):\n        print(x, y)",
                            }
                        ],
                    }
                ],
                "line_comments": [
                    {
                        "file_path": "week2/graph_problem.py",
                        "start_line": 1,
                        "end_line": 3,
                        "title": "중첩 반복문 확인",
                        "body": "중첩 반복문이 보여 입력 크기에 따라 비용이 커질 수 있습니다.",
                        "snippet": "for x in range(3):\n    for y in range(2):\n        print(x, y)",
                    }
                ],
            },
            detected_topics=["그래프", "BFS"],
        )
        save_issue(
            repository_id=repository_id,
            github_issue_id="201",
            issue_number=1,
            title="week2 - 그래프 BFS 문제",
            body="desc",
            state="open",
            github_created_at="2026-03-11T10:00:00Z",
        )
        save_issue(
            repository_id=repository_id,
            github_issue_id="202",
            issue_number=2,
            title="week2 - 구현 문제",
            body="desc",
            state="open",
            github_created_at="2026-03-11T11:00:00Z",
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=1,
            problem_key="그래프 BFS 문제",
            file_path="week2/graph_problem.py",
            judgement_status="solved",
            match_score=1.0,
            matched_by_filename=True,
            execution_passed=True,
            sample_output_matched=True,
        )
        save_recommendation(
            repository_id=repository_id,
            topic="구현",
            problem_title="상하좌우",
            problem_url="https://www.acmicpc.net/",
            source_site="baekjoon",
            reason="구현 영역 보강이 필요합니다.",
        )
    return user_id, repository_id


def login_for_web(client, user_id, repository_id):
    with client.session_transaction() as session:
        session["auth_user_id"] = user_id
        session["oauth_access_token"] = "web-token"
        session["current_repository_id"] = repository_id
        session["current_repository_full_name"] = "JYPark-Code/SW-AI-W02-05"


def test_login_page_renders(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert "GitHub 계정으로 시작" in response.get_data(as_text=True)
    assert "데모로 둘러보기" in response.get_data(as_text=True)


def test_dashboard_page_renders(client, app, monkeypatch):
    user_id, repository_id = ensure_web_context(app)
    login_for_web(client, user_id, repository_id)

    monkeypatch.setattr(
        "app.routes.web.fetch_user_repositories",
        lambda access_token: [
            {
                "github_repo_id": "777",
                "owner": "JYPark-Code",
                "name": "SW-AI-W02-05",
                "full_name": "JYPark-Code/SW-AI-W02-05",
                "default_branch": "main",
                "private": False,
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.web_app_service.build_template_status",
        lambda repository_id: {
            "template_count": 4,
            "matched_count": 2,
            "missing_count": 2,
            "matched_issues": [],
            "missing_issues": [{"title": "week2 - 새 문제"}],
        },
    )
    monkeypatch.setattr(
        "app.services.report_service.build_template_status",
        lambda repository_id: {
            "template_count": 4,
            "matched_count": 2,
            "missing_count": 2,
            "matched_issues": [],
            "missing_issues": [],
        },
    )

    response = client.get("/app/dashboard")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "이번주 액티비티" in html
    assert "AI 추천 문제" in html
    assert "누락 이슈 생성" in html


def test_profile_page_renders(client, app, monkeypatch):
    user_id, repository_id = ensure_web_context(app)
    login_for_web(client, user_id, repository_id)

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

    response = client.get("/app/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "AI 종합 분석" in html
    assert "약점 랭킹" in html


def test_reviews_page_renders(client, app, monkeypatch):
    user_id, repository_id = ensure_web_context(app)
    login_for_web(client, user_id, repository_id)

    monkeypatch.setattr(
        "app.services.web_app_service.fetch_commit_changed_files",
        lambda owner, name, sha, access_token: {
            "sha": sha,
            "message": "그래프 문제 풀이",
            "author_name": "웹 사용자",
            "committed_at": "2026-03-11T12:00:00Z",
            "files": [{"filename": "week2/graph_problem.py"}],
        },
    )
    monkeypatch.setattr(
        "app.services.web_app_service.fetch_file_content_at_ref",
        lambda owner, name, file_path, ref, access_token: "for x in range(3):\n    for y in range(2):\n        print(x, y)\n",
    )

    response = client.get("/app/reviews?sha=web123")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "AI 종합 리뷰" in html
    assert "graph_problem.py" in html
    assert "라인 단위 코멘트" in html


def test_create_missing_issues_web_redirects_to_dashboard(client, app, monkeypatch):
    user_id, repository_id = ensure_web_context(app)
    login_for_web(client, user_id, repository_id)

    monkeypatch.setattr(
        "app.routes.web.create_missing_issues",
        lambda repository, access_token: {
            "template_count": 3,
            "matched_count": 3,
            "missing_count": 0,
            "missing_issues": [],
            "created_issues": [],
        },
    )

    response = client.post("/app/issues/create-missing", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/app/dashboard")


def test_demo_login_creates_session_and_redirects(client):
    response = client.post("/auth/demo-login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/app/dashboard")

    with client.session_transaction() as session:
        assert session["auth_user_id"] == 1
        assert session["current_repository_full_name"] == "demo-org/homeschool-algorithms"

from __future__ import annotations

from app.models.db import (
    save_commit,
    save_commit_analysis_result,
    save_issue,
    save_problem_judgement,
    save_recommendation,
    upsert_repository_for_user,
    upsert_user,
)


def ensure_demo_workspace() -> dict:
    user_id = upsert_user("demo-user-1", "demo-student", "Demo Student")
    repository_id = upsert_repository_for_user(
        user_id=user_id,
        owner="demo-org",
        name="homeschool-algorithms",
        full_name="demo-org/homeschool-algorithms",
        github_repo_id="demo-repo-1",
        default_branch="main",
    )

    commit_id, _created = save_commit(
        repository_id=repository_id,
        sha="demo-commit-123",
        message="week2 graph and implementation practice",
        author_name="Demo Student",
        committed_at="2026-03-11T09:30:00Z",
    )
    save_commit_analysis_result(
        commit_id=commit_id,
        review_summary="그래프와 구현 풀이가 섞여 있고, 반복문 비용과 탐색 상태 관리 점검이 필요합니다.",
        review_comments=[
            "week2/graph_bfs.py: 함수 분리는 괜찮지만 방문 처리 시점을 다시 확인해보세요.",
            "week2/impl_grid.py: 중첩 반복 비용을 줄일 수 있는지 확인해보세요.",
        ],
        execution_status="not_run",
        execution_output={
            "files": [
                {
                    "file_path": "week2/graph_bfs.py",
                    "line_comments": [
                        {
                            "file_path": "week2/graph_bfs.py",
                            "start_line": 5,
                            "end_line": 7,
                            "title": "탐색 상태 관리 점검",
                            "body": "BFS처럼 보이는데 방문 처리 흐름이 약합니다. 큐에 넣는 시점과 방문 체크 시점을 맞춰보세요.",
                            "snippet": "for nxt in graph[cur]:\n    queue.append(nxt)\n    distance[nxt] = distance[cur] + 1",
                        }
                    ],
                },
                {
                    "file_path": "week2/impl_grid.py",
                    "line_comments": [
                        {
                            "file_path": "week2/impl_grid.py",
                            "start_line": 8,
                            "end_line": 10,
                            "title": "중첩 반복문 확인",
                            "body": "격자 전체를 매 단계 순회해 비용이 커질 수 있습니다. 필요한 좌표만 갱신하는 구조로 줄일 수 있는지 확인해보세요.",
                            "snippet": "for i in range(n):\n    for j in range(m):\n        total += board[i][j]",
                        }
                    ],
                },
            ],
            "line_comments": [
                {
                    "file_path": "week2/graph_bfs.py",
                    "start_line": 5,
                    "end_line": 7,
                    "title": "탐색 상태 관리 점검",
                    "body": "BFS처럼 보이는데 방문 처리 흐름이 약합니다. 큐에 넣는 시점과 방문 체크 시점을 맞춰보세요.",
                    "snippet": "for nxt in graph[cur]:\n    queue.append(nxt)\n    distance[nxt] = distance[cur] + 1",
                },
                {
                    "file_path": "week2/impl_grid.py",
                    "start_line": 8,
                    "end_line": 10,
                    "title": "중첩 반복문 확인",
                    "body": "격자 전체를 매 단계 순회해 비용이 커질 수 있습니다. 필요한 좌표만 갱신하는 구조로 줄일 수 있는지 확인해보세요.",
                    "snippet": "for i in range(n):\n    for j in range(m):\n        total += board[i][j]",
                },
            ],
        },
        detected_topics=["그래프", "BFS", "구현"],
    )

    seed_issues = [
        (1, "week2 - 그래프 BFS 문제", "open"),
        (2, "week2 - 구현 시뮬레이션 문제", "open"),
        (3, "week2 - 정렬 문제", "open"),
        (4, "week3 - 수학 문제", "open"),
    ]
    for issue_number, title, state in seed_issues:
        save_issue(
            repository_id=repository_id,
            github_issue_id=f"demo-issue-{issue_number}",
            issue_number=issue_number,
            title=title,
            body="demo issue body",
            state=state,
            github_created_at="2026-03-11T08:00:00Z",
        )

    seed_judgements = [
        (1, "그래프 BFS 문제", "solved", "week2/graph_bfs.py", 1.0, True, True, True),
        (2, "구현 시뮬레이션 문제", "attempted", "week2/impl_grid.py", 0.61, True, False, False),
        (3, "정렬 문제", "not_used", "", 0.0, False, False, False),
    ]
    for issue_number, key, status, file_path, score, matched, execution_passed, sample_output_matched in seed_judgements:
        if status == "not_used":
            continue
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=issue_number,
            problem_key=key,
            file_path=file_path,
            judgement_status=status,
            match_score=score,
            matched_by_filename=matched,
            execution_passed=execution_passed,
            sample_output_matched=sample_output_matched,
        )

    save_recommendation(
        repository_id=repository_id,
        topic="정렬",
        problem_title="K번째 수",
        problem_url="https://school.programmers.co.kr/learn/courses/30/lessons/42748",
        source_site="programmers",
        reason="정렬 풀이 수가 낮아 보강이 필요합니다.",
    )
    save_recommendation(
        repository_id=repository_id,
        topic="수학",
        problem_title="소수 찾기",
        problem_url="https://school.programmers.co.kr/learn/courses/30/lessons/12921",
        source_site="programmers",
        reason="수학 영역 노출이 적어 기초 문제로 보강하는 편이 좋습니다.",
    )

    return {
        "user_id": user_id,
        "repository_id": repository_id,
        "full_name": "demo-org/homeschool-algorithms",
    }

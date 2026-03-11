from app.models.db import (
    get_commit_analysis_result,
    get_commit_by_sha,
    save_commit,
    save_commit_analysis_result,
    update_commit_files,
)
from app.services.github_service import fetch_commit_changed_files, fetch_file_content_at_ref
from app.services.skill_map_service import match_categories_from_text
from app.utils.errors import ApiError


def create_commit_review(repository: dict, sha: str, access_token: str) -> dict:
    commit_payload = fetch_commit_changed_files(repository["owner"], repository["name"], sha, access_token)
    commit_id, _created = save_commit(
        repository_id=repository["id"],
        sha=commit_payload["sha"],
        message=commit_payload["message"],
        author_name=commit_payload["author_name"],
        committed_at=commit_payload["committed_at"],
    )
    update_commit_files(repository["id"], sha, commit_payload["files"])

    python_files = [item for item in commit_payload["files"] if item.get("filename", "").endswith(".py")]
    file_reviews = []
    detected_topics = set()
    review_comments = []

    for file_info in python_files:
        source = fetch_file_content_at_ref(
            repository["owner"],
            repository["name"],
            file_info["filename"],
            sha,
            access_token,
        )
        categories = match_categories_from_text(file_info["filename"], source)
        detected_topics.update(categories)
        structure = evaluate_code_structure(source)
        complexity = estimate_time_complexity(source, categories)
        suggestion = suggest_improvement(source, categories)

        file_reviews.append(
            {
                "file_path": file_info["filename"],
                "detected_categories": categories,
                "code_structure": structure,
                "estimated_time_complexity": complexity,
                "suggestion": suggestion,
            }
        )
        review_comments.append(f"{file_info['filename']}: {structure}, 예상 시간 복잡도 {complexity}")

    if not python_files:
        review_comments.append("분석할 Python 파일이 없습니다.")

    review_summary = build_review_summary(sorted(detected_topics), file_reviews)
    save_commit_analysis_result(
        commit_id=commit_id,
        review_summary=review_summary,
        review_comments=review_comments,
        execution_status="not_run",
        execution_output={},
        detected_topics=sorted(detected_topics),
    )

    return {
        "commit_sha": sha,
        "python_file_count": len(python_files),
        "detected_topics": sorted(detected_topics),
        "review_summary": review_summary,
        "review_comments": review_comments,
        "files": file_reviews,
    }


def get_commit_review(repository_id: int, sha: str) -> dict:
    commit = get_commit_by_sha(repository_id, sha)
    if not commit:
        raise ApiError("COMMIT_NOT_FOUND", "요청한 commit 정보를 찾을 수 없습니다.", 404)

    review = get_commit_analysis_result(commit["id"])
    if not review:
        raise ApiError("COMMIT_REVIEW_NOT_FOUND", "아직 생성된 commit 리뷰가 없습니다.", 404)

    return {
        "commit_sha": sha,
        "review_summary": review["review_summary"],
        "review_comments": review["review_comments"],
        "detected_topics": review["detected_topics"],
        "execution_status": review["execution_status"],
        "analyzed_at": review["analyzed_at"],
    }


def evaluate_code_structure(source: str) -> str:
    stripped_lines = [line.strip() for line in source.splitlines() if line.strip()]
    if not stripped_lines:
        return "코드가 비어 있어 구조를 평가하기 어렵습니다."
    if any(line.startswith("def ") for line in stripped_lines):
        return "함수 분리가 되어 있어 구조가 비교적 명확합니다."
    if len(stripped_lines) > 25:
        return "로직이 한 파일에 길게 이어져 있어 함수 분리를 고려할 수 있습니다."
    return "짧은 풀이 구조로 빠르게 확인하기 좋습니다."


def estimate_time_complexity(source: str, categories: list[str]) -> str:
    lowered = source.lower()
    if "이분탐색" in categories or "mid" in lowered and "left" in lowered and "right" in lowered:
        return "O(log N)"
    if "정렬" in categories or ".sort(" in lowered or "sorted(" in lowered:
        return "O(N log N)"
    if {"BFS", "DFS", "그래프"} & set(categories):
        return "O(V + E)"
    if lowered.count("for ") >= 2 or lowered.count("while ") >= 2:
        return "O(N^2) 이상"
    return "O(N) 내외"


def suggest_improvement(source: str, categories: list[str]) -> str:
    lowered = source.lower()
    if "input()" in lowered and "sys.stdin.readline" not in lowered:
        return "입력이 많은 문제라면 sys.stdin.readline 사용을 고려해보세요."
    if "다이나믹프로그래밍" in categories and "memo" not in lowered and "dp" not in lowered:
        return "중복 계산이 있다면 메모이제이션이나 DP 배열을 명시해보세요."
    if {"BFS", "DFS"} & set(categories) and "visited" not in lowered:
        return "탐색 문제라면 방문 처리 위치를 한 번 더 점검해보세요."
    return "현재 풀이 방향은 유지하되 변수명과 함수 분리만 다듬어도 가독성이 좋아집니다."


def build_review_summary(detected_topics: list[str], file_reviews: list[dict]) -> str:
    if not file_reviews:
        return "이번 commit에서는 Python 풀이 파일이 없어 리뷰를 생성하지 못했습니다."
    if not detected_topics:
        return "이번 commit은 구현 중심 풀이로 보이며, 구조와 입출력 처리 위주로 점검이 필요합니다."
    return f"이번 commit은 {', '.join(detected_topics[:4])} 유형 풀이가 중심이며, 총 {len(file_reviews)}개 Python 파일을 검토했습니다."

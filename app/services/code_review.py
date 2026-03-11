import ast
import io
import tokenize

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
    sanitized_lines = _get_meaningful_lines(source)
    if not sanitized_lines:
        return "코드가 비어 있어 구조를 평가하기 어렵습니다."

    function_metrics = _get_function_metrics(source)
    function_count = function_metrics["function_count"]
    longest_function_line_count = function_metrics["longest_function_line_count"]

    if function_count >= 2 and longest_function_line_count <= 30:
        return "함수 분리가 되어 있어 구조가 비교적 명확합니다."
    if function_count >= 2 and longest_function_line_count > 30:
        return "함수는 나뉘어 있지만 핵심 함수 길이가 길어 추가 분리 여지가 있습니다."
    if function_count == 1 and longest_function_line_count > 35:
        return "단일 함수 중심 구조이며 함수 길이가 길어 분리 여지가 있습니다."
    if function_count == 1:
        return "단일 함수 중심 구조로 작성되어 있어 흐름은 보이지만 함수 분리 여지가 있습니다."
    if len(sanitized_lines) > 25:
        return "로직이 한 파일에 길게 이어져 있어 함수 분리를 고려할 수 있습니다."
    return "짧은 풀이 구조로 빠르게 확인하기 좋습니다."


def estimate_time_complexity(source: str, categories: list[str]) -> str:
    sanitized_source = _strip_comments_and_docstrings(source)
    lowered = sanitized_source.lower()
    category_set = set(categories)

    if "이분탐색" in category_set or ("mid" in lowered and "left" in lowered and "right" in lowered):
        return "O(log N)"
    if "정렬" in category_set or ".sort(" in lowered or "sorted(" in lowered:
        return "O(N log N)"
    if {"BFS", "DFS", "그래프"} & category_set:
        return "O(V + E)"

    loop_depth = _get_loop_nesting_depth(sanitized_source)
    if loop_depth >= 2:
        return "O(N^2) 이상"
    if loop_depth == 1:
        return "O(N) 내외"
    return "O(N) 내외"


def suggest_improvement(source: str, categories: list[str]) -> str:
    lowered = _strip_comments_and_docstrings(source).lower()
    category_set = set(categories)

    if "input()" in lowered and "sys.stdin.readline" not in lowered:
        return "입력이 많은 문제라면 sys.stdin.readline 사용을 고려해보세요."
    if "다이나믹프로그래밍" in category_set and "memo" not in lowered and "dp" not in lowered:
        return "중복 계산이 있다면 메모이제이션이나 DP 배열을 명시해보세요."
    if {"BFS", "DFS"} & category_set and "visited" not in lowered:
        return "탐색 문제라면 방문 처리 위치를 한 번 더 점검해보세요."
    return "변수명과 함수 역할을 조금만 더 드러내면 가독성이 더 좋아질 수 있습니다."


def build_review_summary(detected_topics: list[str], file_reviews: list[dict]) -> str:
    if not file_reviews:
        return "이번 commit에서는 Python 대상 파일이 없어 리뷰를 생성하지 못했습니다."
    if not detected_topics:
        return "이번 commit은 구현 중심 풀이로 보이며, 구조와 입출력 처리 위주로 확인이 필요합니다."
    return f"이번 commit은 {', '.join(detected_topics[:4])} 유형 풀이가 중심이며, 총 {len(file_reviews)}개 Python 파일을 검토했습니다."


def _strip_comments_and_docstrings(source: str) -> str:
    try:
        token_stream = tokenize.generate_tokens(io.StringIO(source).readline)
    except (tokenize.TokenError, IndentationError):
        return source

    pieces = []
    prev_token_type = tokenize.INDENT
    last_lineno = 1
    last_col = 0

    for token_type, token_string, start, end, _line in token_stream:
        start_line, start_col = start
        end_line, end_col = end

        if token_type == tokenize.COMMENT:
            continue

        is_docstring = token_type == tokenize.STRING and prev_token_type in {
            tokenize.INDENT,
            tokenize.NEWLINE,
            tokenize.DEDENT,
            tokenize.ENCODING,
        }
        if is_docstring:
            prev_token_type = token_type
            last_lineno = end_line
            last_col = end_col
            continue

        if start_line > last_lineno:
            pieces.append("\n" * (start_line - last_lineno))
            last_col = 0
        if start_col > last_col:
            pieces.append(" " * (start_col - last_col))

        pieces.append(token_string)
        prev_token_type = token_type
        last_lineno = end_line
        last_col = end_col

    return "".join(pieces)


def _get_meaningful_lines(source: str) -> list[str]:
    sanitized_source = _strip_comments_and_docstrings(source)
    return [line.rstrip() for line in sanitized_source.splitlines() if line.strip()]


def _get_function_metrics(source: str) -> dict:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"function_count": 0, "longest_function_line_count": 0}

    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not functions:
        return {"function_count": 0, "longest_function_line_count": 0}

    lines = source.splitlines()
    longest_function_line_count = 0
    for function_node in functions:
        start_line = function_node.lineno
        end_line = getattr(function_node, "end_lineno", function_node.lineno)
        function_source = "\n".join(lines[start_line - 1:end_line])
        meaningful_lines = _get_meaningful_lines(function_source)
        longest_function_line_count = max(longest_function_line_count, len(meaningful_lines))

    return {
        "function_count": len(functions),
        "longest_function_line_count": longest_function_line_count,
    }


def _get_loop_nesting_depth(source: str) -> int:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0

    return max((_measure_loop_depth(node) for node in ast.walk(tree)), default=0)


def _measure_loop_depth(node) -> int:
    if not isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
        return 0

    child_depth = 0
    for child in ast.iter_child_nodes(node):
        child_depth = max(child_depth, _measure_loop_depth(child))
    return 1 + child_depth

import ast
import io
import tokenize

from app.models.db import (
    get_commit_analysis_result,
    get_commit_by_sha,
    get_issues_by_repository_id,
    get_problem_judgements_by_commit_id,
    save_commit,
    save_commit_analysis_result,
    update_commit_files,
)
from app.services.commit_judge_service import match_issue_by_filename
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
    issues = get_issues_by_repository_id(repository["id"])
    judgements = get_problem_judgements_by_commit_id(commit_id)
    judgement_map = _build_judgement_map(judgements)

    file_reviews = []
    detected_topics = set()
    review_comments = []
    line_comments = []

    for file_info in python_files:
        file_path = file_info["filename"]
        source = fetch_file_content_at_ref(
            repository["owner"],
            repository["name"],
            file_path,
            sha,
            access_token,
        )
        categories = match_categories_from_text(file_path, source)
        detected_topics.update(categories)

        issue_context = _resolve_issue_context(file_path, issues, judgement_map)
        structure = evaluate_code_structure(source)
        complexity = estimate_time_complexity(source, categories)
        suggestion = suggest_improvement(source, categories)
        strengths = build_problem_review_strengths(issue_context, structure, complexity)
        risks = build_problem_review_risks(issue_context, source, categories)
        summary = build_problem_review_summary(issue_context, categories, structure, complexity, strengths, risks)
        file_line_comments = build_line_comments(file_path, issue_context, source, suggestion, risks)

        file_review = {
            "file_path": file_path,
            "issue_number": issue_context["issue_number"],
            "issue_title": issue_context["issue_title"],
            "judgement_status": issue_context["judgement_status"],
            "match_score": issue_context["match_score"],
            "detected_categories": categories,
            "code_structure": structure,
            "estimated_time_complexity": complexity,
            "suggestion": suggestion,
            "summary": summary,
            "strengths": strengths,
            "risks": risks,
            "line_comments": file_line_comments,
        }
        file_reviews.append(file_review)
        line_comments.extend(file_line_comments)
        review_comments.append(build_problem_review_comment(file_review))

    if not python_files:
        review_comments.append("이 commit에는 Python 파일이 없어 문제 중심 리뷰를 만들지 못했습니다.")

    review_summary = build_review_summary(sorted(detected_topics), file_reviews)
    execution_output = {
        "files": file_reviews,
        "line_comments": line_comments,
    }

    save_commit_analysis_result(
        commit_id=commit_id,
        review_summary=review_summary,
        review_comments=review_comments,
        execution_status="not_run",
        execution_output=execution_output,
        detected_topics=sorted(detected_topics),
    )

    return {
        "commit_sha": sha,
        "python_file_count": len(python_files),
        "detected_topics": sorted(detected_topics),
        "review_summary": review_summary,
        "review_comments": review_comments,
        "files": file_reviews,
        "line_comments": line_comments,
    }


def get_commit_review(repository_id: int, sha: str) -> dict:
    commit = get_commit_by_sha(repository_id, sha)
    if not commit:
        raise ApiError("COMMIT_NOT_FOUND", "요청한 commit을 찾을 수 없습니다.", 404)

    review = get_commit_analysis_result(commit["id"])
    if not review:
        raise ApiError("COMMIT_REVIEW_NOT_FOUND", "저장된 commit 리뷰가 아직 없습니다.", 404)

    execution_output = review.get("execution_output") or {}
    return {
        "commit_sha": sha,
        "review_summary": review["review_summary"],
        "review_comments": review["review_comments"],
        "detected_topics": review["detected_topics"],
        "execution_status": review["execution_status"],
        "analyzed_at": review["analyzed_at"],
        "files": execution_output.get("files", []),
        "line_comments": execution_output.get("line_comments", []),
    }


def evaluate_code_structure(source: str) -> str:
    sanitized_lines = _get_meaningful_lines(source)
    if not sanitized_lines:
        return "파일 내용이 비어 있어 풀이 구조를 판단하기 어렵습니다."

    function_metrics = _get_function_metrics(source)
    function_count = function_metrics["function_count"]
    longest_function_line_count = function_metrics["longest_function_line_count"]

    if function_count >= 2 and longest_function_line_count <= 30:
        return "함수 단위로 적절히 나뉘어 있어 풀이 흐름을 따라가기 비교적 쉽습니다."
    if function_count >= 2 and longest_function_line_count > 30:
        return "함수 분리는 되어 있지만 일부 함수에 로직이 많이 몰려 있어 추가 분리 여지가 있습니다."
    if function_count == 1 and longest_function_line_count > 35:
        return "하나의 긴 함수에 핵심 로직이 몰려 있어 풀이를 검증하거나 수정하기가 다소 어렵습니다."
    if function_count == 1:
        return "단일 함수 중심 풀이여서 흐름은 읽히지만 구조적으로 크게 나뉘어 있지는 않습니다."
    if len(sanitized_lines) > 25:
        return "로직이 한 흐름으로 길게 이어져 있어 작은 함수로 나누면 검토하기 더 좋아질 수 있습니다."
    return "짧고 응집된 풀이여서 핵심 흐름을 빠르게 파악할 수 있습니다."


def estimate_time_complexity(source: str, categories: list[str]) -> str:
    sanitized_source = _strip_comments_and_docstrings(source)
    lowered = sanitized_source.lower()
    category_set = set(categories)

    if "binary_search" in lowered or ("mid" in lowered and "left" in lowered and "right" in lowered):
        return "O(log N)"
    if "sort(" in lowered or "sorted(" in lowered:
        return "O(N log N)"
    if {"BFS", "DFS"} & category_set:
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
        return "입력이 많은 문제라면 sys.stdin.readline을 쓰는 편이 더 안정적일 수 있습니다."
    if "DP" in category_set and "memo" not in lowered and "dp" not in lowered:
        return "중복 부분 문제가 있다면 상태 정의나 메모이제이션을 더 분명하게 드러내면 좋습니다."
    if {"BFS", "DFS"} & category_set and "visited" not in lowered:
        return "탐색 문제라면 visited 처리 위치와 방식이 충분한지 한 번 더 확인해보는 것이 좋습니다."
    return "핵심 분기나 상태 변화 지점을 조금만 더 드러내면 풀이 의도를 검증하기 쉬워집니다."


def build_review_summary(detected_topics: list[str], file_reviews: list[dict]) -> str:
    if not file_reviews:
        return "이 commit에는 Python 풀이 파일이 없어 문제 중심 AI 리뷰를 만들지 못했습니다."

    primary_review = file_reviews[0]
    issue_title = primary_review.get("issue_title")
    if issue_title:
        return (
            f"이 리뷰는 `{issue_title}` 풀이를 중심으로 작성되었습니다. "
            f"{primary_review['summary']}"
        )

    if not detected_topics:
        return "이 commit은 Python 문제 풀이로 보이지만, 어떤 문제에 대한 코드인지 특정할 정보가 아직 충분하지 않습니다."

    return (
        f"이 commit은 {', '.join(detected_topics[:4])} 유형의 문제 풀이로 보입니다. "
        f"아래 리뷰는 일반적인 Python 문법 평보다, 이 코드가 문제를 어떻게 풀고 있는지에 초점을 둡니다."
    )


def build_problem_review_summary(
    issue_context: dict,
    categories: list[str],
    structure: str,
    complexity: str,
    strengths: list[str],
    risks: list[str],
) -> str:
    category_text = ", ".join(categories[:3]) if categories else "구현"
    issue_title = issue_context.get("issue_title") or "매칭된 문제"
    status_text = _translate_judgement_status(issue_context.get("judgement_status"))
    strength_text = strengths[0] if strengths else "전체적인 풀이 방향은 문제 의도와 맞아 보입니다."
    risk_text = risks[0] if risks else "정답 여부를 더 확신하려면 실행 근거가 추가로 필요합니다."
    return (
        f"이 코드는 `{issue_title}` 문제를 {category_text} 관점에서 풀이한 것으로 보입니다. "
        f"현재 판정은 {status_text}입니다. "
        f"구조 측면에서는 {structure} "
        f"예상 시간 복잡도는 {complexity}로 보입니다. "
        f"강점은 {strength_text} "
        f"리스크는 {risk_text}"
    )


def build_problem_review_strengths(issue_context: dict, structure: str, complexity: str) -> list[str]:
    strengths = []
    judgement_status = issue_context.get("judgement_status")
    if judgement_status == "solved":
        strengths.append("이미 solved로 분류되어 있어 구현 방향과 문제 매칭이 잘 맞는 편입니다.")
    elif judgement_status == "possibly_solved":
        strengths.append("파일명과 문제 매칭 점수가 높아, 의도한 문제에 대한 실제 제출 코드일 가능성이 높습니다.")

    if "쉽습니다" in structure or "빠르게" in structure:
        strengths.append("풀이 흐름이 비교적 단순해 핵심 아이디어를 따라가기 어렵지 않습니다.")
    if complexity in {"O(log N)", "O(N log N)", "O(V + E)"}:
        strengths.append(f"예상 복잡도 {complexity}는 이 유형에서 흔히 기대하는 접근과 잘 맞습니다.")

    if not strengths:
        strengths.append("문제 풀이 코드로서의 형태가 비교적 분명해 의도를 파악하기 어렵지 않습니다.")
    return strengths[:2]


def build_problem_review_risks(issue_context: dict, source: str, categories: list[str]) -> list[str]:
    risks = []
    judgement_status = issue_context.get("judgement_status")
    lowered = _strip_comments_and_docstrings(source).lower()

    if judgement_status == "attempted":
        risks.append("현재 attempted로 분류되어 있어, 이 코드만으로는 정답 근거가 충분하지 않습니다.")
    elif judgement_status == "possibly_solved":
        risks.append("문제 매칭은 강하지만, 모든 예외 케이스까지 맞는지는 실행 검증 없이 확정하기 어렵습니다.")
    elif judgement_status is None:
        risks.append("이 파일이 어떤 판정 결과와 연결되는지 확실하지 않아 리뷰 신뢰도가 제한됩니다.")

    if {"BFS", "DFS"} & set(categories) and "visited" not in lowered:
        risks.append("탐색 로직은 보이지만 visited 처리가 코드에서 분명하게 드러나지 않습니다.")
    if "input()" in lowered and "sys.stdin.readline" not in lowered:
        risks.append("입력 크기가 큰 문제라면 input() 사용이 병목이 될 가능성이 있습니다.")

    if not risks:
        risks.append("전체 방향보다는 세부 예외 케이스를 얼마나 잘 처리했는지가 남은 확인 포인트입니다.")
    return risks[:2]


def build_problem_review_comment(file_review: dict) -> str:
    issue_title = file_review.get("issue_title") or "매칭되지 않은 문제"
    status_text = _translate_judgement_status(file_review.get("judgement_status"))
    strengths = file_review.get("strengths") or []
    risks = file_review.get("risks") or []
    strength_text = strengths[0] if strengths else "풀이 방향은 문제 의도와 크게 어긋나지 않아 보입니다."
    risk_text = risks[0] if risks else "정답 여부를 확신하려면 추가 검증이 더 필요합니다."
    return (
        f"{file_review['file_path']}: `{issue_title}` 풀이 리뷰입니다. "
        f"현재 상태는 {status_text}이며, 강점은 {strength_text} "
        f"리스크는 {risk_text}"
    )


def build_line_comments(file_path: str, issue_context: dict, source: str, suggestion: str, risks: list[str]) -> list[dict]:
    snippet, start_line, end_line = _extract_focus_snippet(source)
    if not snippet:
        return []

    issue_title = issue_context.get("issue_title") or file_path.split("/")[-1]
    body_parts = []
    if risks:
        body_parts.append(risks[0])
    if suggestion:
        body_parts.append(suggestion)

    return [
        {
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "title": f"{issue_title} 풀이 포인트",
            "body": " ".join(body_parts).strip(),
            "snippet": snippet,
        }
    ]


def _resolve_issue_context(file_path: str, issues: list[dict], judgement_map: dict) -> dict:
    judgement = judgement_map.get(file_path) or {}
    matched_issue = None

    issue_number = judgement.get("issue_number")
    if issue_number is not None:
        for issue in issues:
            if issue.get("issue_number") == issue_number:
                matched_issue = issue
                break

    match_score = judgement.get("match_score", 0.0)
    if matched_issue is None:
        matched = match_issue_by_filename(file_path, issues)
        matched_issue = matched.get("issue")
        match_score = matched.get("score", 0.0)

    return {
        "issue_number": issue_number if issue_number is not None else (matched_issue or {}).get("issue_number"),
        "issue_title": judgement.get("problem_key") or (matched_issue or {}).get("title"),
        "judgement_status": judgement.get("judgement_status"),
        "match_score": match_score,
    }


def _build_judgement_map(judgements: list[dict]) -> dict:
    result = {}
    for item in judgements:
        file_path = item.get("file_path")
        if file_path:
            result[file_path] = item
    return result


def _translate_judgement_status(status: str | None) -> str:
    mapping = {
        "solved": "해결된 풀이로 보입니다",
        "possibly_solved": "정답 가능성은 높지만 실행 검증은 아직 없습니다",
        "attempted": "시도 단계로 보입니다",
        None: "아직 판정 정보가 없습니다",
    }
    return mapping.get(status, status or "아직 판정 정보가 없습니다")


def _extract_focus_snippet(source: str, max_lines: int = 6) -> tuple[str, int, int]:
    lines = source.splitlines()
    meaningful_indexes = [index for index, line in enumerate(lines, start=1) if line.strip()]
    if not meaningful_indexes:
        return "", 0, 0

    start_line = meaningful_indexes[0]
    end_line = min(start_line + max_lines - 1, len(lines))
    snippet = "\n".join(lines[start_line - 1:end_line]).strip()
    return snippet, start_line, end_line


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

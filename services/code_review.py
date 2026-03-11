from pathlib import Path

from services.github_service import fetch_python_files_from_github
from services.problem_generator import generate_problems


SUPPORTED_TOPICS = [
    "recursion",
    "backtracking",
    "graph",
    "bfs",
    "dfs",
    "dynamic programming",
    "brute force",
    "binary search",
]


def review_repository(repo_path: str) -> dict:
    repository = Path(repo_path)
    if not repository.exists() or not repository.is_dir():
        raise ValueError("유효한 저장소 경로가 필요합니다.")

    python_files = list(repository.rglob("*.py"))
    detected_topics = set()

    for file_path in python_files:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        file_topics = detect_topics_in_source(source)
        detected_topics.update(file_topics)

    detected_list = sorted(detected_topics)
    missing_list = [topic for topic in SUPPORTED_TOPICS if topic not in detected_topics]

    return {
        "detected_topics": detected_list,
        "missing_topics": missing_list,
    }


def analyze_github_repository(repo_owner: str, repo_name: str) -> dict:
    python_files = fetch_python_files_from_github(repo_owner, repo_name)
    return analyze_python_files(python_files)


def analyze_python_files(python_files: list[dict]) -> dict:
    detected_topics = set()
    review_comments = []

    for file_info in python_files:
        file_topics = detect_topics_in_source(file_info.get("content", ""))
        detected_topics.update(file_topics)

        if file_topics:
            review_comments.append(
                f"{file_info.get('path', '알 수 없는 파일')}: {', '.join(file_topics)} 관련 풀이 패턴이 감지되었습니다."
            )

    detected_list = sorted(detected_topics)
    weak_or_missing_topics = [topic for topic in SUPPORTED_TOPICS if topic not in detected_topics]
    recommended_next_topics = weak_or_missing_topics[:3]

    if not review_comments:
        review_comments.append("스캔한 Python 파일에서 뚜렷한 알고리즘 풀이 패턴을 찾지 못했습니다.")

    if detected_list:
        review_comments.append(f"현재는 {', '.join(detected_list[:4])} 유형 풀이 경험이 비교적 잘 쌓여 있습니다.")

    if weak_or_missing_topics:
        review_comments.append(f"다음 학습 주제로는 {', '.join(recommended_next_topics)}를 추천합니다.")

    recommended_practice_problems = []
    for topic in recommended_next_topics:
        recommended_practice_problems.extend(generate_problems(topic, limit=2))

    return {
        "analyzed_files_count": len(python_files),
        "detected_topics": detected_list,
        "weak_or_missing_topics": weak_or_missing_topics,
        "simple_review_comments": review_comments[:6],
        "recommended_next_topics": recommended_next_topics,
        "recommended_practice_problems": recommended_practice_problems,
    }


def detect_topics_in_source(source: str) -> list[str]:
    lowered = source.lower()
    detected_topics = set()

    if _looks_like_recursion(lowered):
        detected_topics.add("recursion")

    if _looks_like_backtracking(lowered):
        detected_topics.add("backtracking")

    if _looks_like_graph(lowered):
        detected_topics.add("graph")

    if _looks_like_bfs(lowered):
        detected_topics.add("bfs")

    if _looks_like_dfs(lowered):
        detected_topics.add("dfs")

    if _looks_like_dp(lowered):
        detected_topics.add("dynamic programming")

    if _looks_like_brute_force(lowered):
        detected_topics.add("brute force")

    if _looks_like_binary_search(lowered):
        detected_topics.add("binary search")

    return sorted(detected_topics)


def _looks_like_recursion(source: str) -> bool:
    function_names = []

    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("def ") and "(" in stripped:
            function_name = stripped[4:stripped.index("(")].strip()
            if function_name:
                function_names.append(function_name)

    for function_name in function_names:
        if f"{function_name}(" in source[source.find(f"def {function_name}(") + 1:]:
            return True

    return False


def _looks_like_backtracking(source: str) -> bool:
    return (
        ("visited" in source and "dfs" in source)
        or ("backtrack" in source)
        or ("append(path" in source and "pop()" in source)
    )


def _looks_like_graph(source: str) -> bool:
    return (
        "adj" in source
        or "graph = {" in source
        or "collections.deque" in source
        or "deque(" in source
        or "bfs" in source
    )


def _looks_like_dp(source: str) -> bool:
    return (
        "memo" in source
        or "dp = [" in source
        or "cache" in source
        or "@lru_cache" in source
        or "tabulation" in source
    )


def _looks_like_bfs(source: str) -> bool:
    return (
        "bfs" in source
        or "deque(" in source
        or "popleft(" in source
        or "queue.append(" in source
    )


def _looks_like_dfs(source: str) -> bool:
    return (
        "dfs" in source
        or ("stack" in source and "pop()" in source)
        or ("visited" in source and _looks_like_recursion(source))
    )


def _looks_like_brute_force(source: str) -> bool:
    return (
        "itertools.permutations" in source
        or "itertools.product" in source
        or ("for " in source and "for " in source[source.find("for ") + 1:])
        or "exhaustive" in source
    )


def _looks_like_binary_search(source: str) -> bool:
    return (
        "binary_search" in source
        or ("left" in source and "right" in source and "mid" in source)
        or "bisect_left" in source
        or "bisect_right" in source
    )

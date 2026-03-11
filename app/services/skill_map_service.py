import re
from collections import defaultdict

from app.models.db import (
    get_issues_by_repository_id,
    get_problem_summary_by_repository_id,
    list_problem_judgements_by_repository_id,
)


ALGORITHM_TAXONOMY = {
    "구현": ["구현", "문자열", "사고력", "시뮬레이션", "재귀"],
    "수학": ["수학"],
    "자료구조": ["그래프", "배열", "스택", "큐", "트리", "해시", "힙"],
    "정렬": ["정렬"],
    "탐색": ["BFS", "DFS", "그리디", "다이나믹프로그래밍", "완전탐색", "이분탐색", "최단경로", "탐색"],
}

CATEGORY_KEYWORDS = {
    "구현": ["구현", "implementation"],
    "문자열": ["문자열", "string"],
    "사고력": ["사고력", "아이디어", "관찰"],
    "시뮬레이션": ["시뮬레이션", "simulation"],
    "재귀": ["재귀", "recursion"],
    "수학": ["수학", "math", "정수론", "소수", "조합", "제곱"],
    "그래프": ["그래프", "graph"],
    "배열": ["배열", "array", "list"],
    "스택": ["스택", "stack"],
    "큐": ["큐", "queue", "deque"],
    "트리": ["트리", "tree"],
    "해시": ["해시", "hash", "dictionary", "dict"],
    "힙": ["힙", "heap", "priority queue"],
    "정렬": ["정렬", "sort"],
    "BFS": ["bfs", "너비 우선"],
    "DFS": ["dfs", "깊이 우선"],
    "그리디": ["그리디", "greedy"],
    "다이나믹프로그래밍": ["다이나믹프로그래밍", "동적 계획법", "dynamic programming", "dp"],
    "완전탐색": ["완전탐색", "brute force", "브루트포스"],
    "이분탐색": ["이분탐색", "binary search", "bisect"],
    "최단경로": ["최단경로", "다익스트라", "플로이드", "bellman", "dijkstra"],
    "탐색": ["탐색", "search"],
}


def build_reverse_taxonomy() -> dict[str, str]:
    return {
        category: domain
        for domain, categories in ALGORITHM_TAXONOMY.items()
        for category in categories
    }


def normalize_matching_text(text: str) -> str:
    normalized = re.sub(r"[_/\-\\]+", " ", text or "")
    normalized = re.sub(r"\s+", " ", normalized).strip().casefold()
    return normalized


def match_categories_from_text(*texts: str) -> list[str]:
    haystack = normalize_matching_text(" ".join(texts))
    matched = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(normalize_matching_text(keyword) in haystack for keyword in keywords):
            matched.append(category)

    if not matched:
        matched.append("구현")

    return sorted(set(matched))


def build_skill_map(repository_id: int) -> dict:
    judgements = list_problem_judgements_by_repository_id(repository_id)
    issues = get_issues_by_repository_id(repository_id)
    issue_state_map = {item["issue_number"]: item["state"] for item in issues if item.get("issue_number") is not None}
    reverse_mapping = build_reverse_taxonomy()
    domain_stats = defaultdict(lambda: {"name": "", "total": 0, "solved": 0, "possibly_solved": 0, "attempted": 0})

    for judgement in _collapse_judgements(judgements, issue_state_map):
        categories = match_categories_from_text(judgement["problem_key"], judgement.get("file_path", ""))
        domains = {reverse_mapping[category] for category in categories if category in reverse_mapping}
        for domain in domains:
            domain_stats[domain]["name"] = domain
            domain_stats[domain]["total"] += 1
            status = judgement["judgement_status"]
            if status == "solved":
                domain_stats[domain]["solved"] += 1
            elif status == "possibly_solved":
                domain_stats[domain]["possibly_solved"] += 1
            else:
                domain_stats[domain]["attempted"] += 1

    summary = get_problem_summary_by_repository_id(repository_id)
    domains = sorted(domain_stats.values(), key=lambda item: item["name"])

    return {
        "domains": domains,
        "summary": summary,
    }


def _collapse_judgements(judgements: list[dict], issue_state_map: dict[int, str]) -> list[dict]:
    priority = {"attempted": 1, "possibly_solved": 2, "solved": 3}
    best_by_issue = {}
    extras = []

    for judgement in judgements:
        issue_number = judgement.get("issue_number")
        if issue_number is None:
            extras.append(judgement)
            continue

        current = best_by_issue.get(issue_number)
        next_status = judgement["judgement_status"]
        if current is None or priority.get(next_status, 0) > priority.get(current["judgement_status"], 0):
            best_by_issue[issue_number] = dict(judgement)

    collapsed = []
    for issue_number, judgement in best_by_issue.items():
        normalized = dict(judgement)
        if issue_state_map.get(issue_number) == "closed":
            normalized["judgement_status"] = "solved"
        collapsed.append(normalized)

    collapsed.extend(extras)
    return collapsed

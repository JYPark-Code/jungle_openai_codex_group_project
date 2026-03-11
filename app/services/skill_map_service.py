import re
from collections import defaultdict

from app.models.db import (
    get_issues_by_repository_id,
    list_problem_judgements_by_repository_id,
)
from app.services.commit_judge_service import match_issue_by_filename
from app.services.reporting_judgement_service import collapse_judgements_for_reporting, summarize_judgement_statuses


ALGORITHM_TAXONOMY = {
    "구현": ["구현", "문자열", "사고력", "시뮬레이션", "재귀"],
    "수학": ["수학"],
    "자료구조": ["그래프", "배열", "스택", "큐", "트리", "해시", "힙"],
    "정렬": ["정렬"],
    "탐색": ["BFS", "DFS", "그리디", "다이나믹프로그래밍", "완전탐색", "이분탐색", "최단경로", "탐색"],
}

CATEGORY_KEYWORDS = {
    "구현": [
        "구현",
        "implementation",
    ],
    "문자열": [
        "문자열",
        "string",
        "ipv6",
        "광고",
        "단어 공부",
        "문자열 반복",
        "palindrome",
        "회문",
    ],
    "사고력": [
        "사고력",
        "아이디어",
        "관찰",
    ],
    "시뮬레이션": [
        "시뮬레이션",
        "simulation",
    ],
    "재귀": [
        "재귀",
        "재귀함수",
        "recursion",
        "하노이",
        "팩토리얼",
        "피보나치",
        "pow(x,n)",
        "pow x n",
    ],
    "수학": [
        "수학",
        "math",
        "정수론",
        "소수",
        "골드바흐",
        "최대공약수",
        "최소공배수",
        "조합",
        "옷조합",
        "제곱",
    ],
    "그래프": [
        "그래프",
        "graph",
    ],
    "배열": [
        "배열",
        "array",
        "list",
    ],
    "스택": [
        "스택",
        "stack",
    ],
    "큐": [
        "큐",
        "queue",
        "deque",
    ],
    "트리": [
        "트리",
        "tree",
    ],
    "해시": [
        "해시",
        "hash",
        "dictionary",
        "dict",
        "counter",
    ],
    "힙": [
        "힙",
        "heap",
        "priority queue",
    ],
    "정렬": [
        "정렬",
        "sort",
    ],
    "BFS": [
        "bfs",
        "너비 우선",
    ],
    "DFS": [
        "dfs",
        "깊이 우선",
        "백트래킹",
        "backtracking",
        "nqueen",
        "n queen",
        "bishop",
        "비숍",
        "외판원 순회",
        "word search",
        "순열만들기",
        "토핑선택",
        "핸드폰 문자조합",
    ],
    "그리디": [
        "그리디",
        "greedy",
    ],
    "다이나믹프로그래밍": [
        "다이나믹프로그래밍",
        "동적 계획법",
        "dynamic programming",
        "dp",
    ],
    "완전탐색": [
        "완전탐색",
        "brute force",
        "브루트포스",
    ],
    "이분탐색": [
        "이분탐색",
        "binary search",
        "bisect",
    ],
    "최단경로": [
        "최단경로",
        "다익스트라",
        "플로이드",
        "bellman",
        "dijkstra",
    ],
    "탐색": [
        "탐색",
        "search",
    ],
}


def build_reverse_taxonomy() -> dict[str, str]:
    return {
        category: domain
        for domain, categories in ALGORITHM_TAXONOMY.items()
        for category in categories
    }


def normalize_matching_text(text: str) -> str:
    normalized = re.sub(r"[_/\-\\]+", " ", text or "")
    normalized = re.sub(r"[^0-9A-Za-z가-힣\s]+", " ", normalized)
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
    issues = get_issues_by_repository_id(repository_id)
    collapsed, extras = collapse_judgements_for_reporting(
        list_problem_judgements_by_repository_id(repository_id),
        issues,
        match_issue_by_filename,
    )
    reverse_mapping = build_reverse_taxonomy()
    domain_stats = defaultdict(lambda: {"name": "", "total": 0, "solved": 0, "possibly_solved": 0, "attempted": 0})

    normalized_judgements = collapsed + extras
    for judgement in normalized_judgements:
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

    summary = summarize_judgement_statuses(normalized_judgements)
    domains = sorted(domain_stats.values(), key=lambda item: item["name"])

    return {
        "domains": domains,
        "summary": summary,
    }

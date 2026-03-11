from collections import Counter

from app.models.db import (
    get_issues_by_repository_id,
    list_problem_judgements_by_repository_id,
    list_recent_commit_topics_by_repository_id,
    list_recommendations_by_repository_id,
    save_recommendation,
)
from app.services.commit_judge_service import match_issue_by_filename
from app.services.reporting_judgement_service import build_reporting_issue_entries
from app.services.skill_map_service import CATEGORY_KEYWORDS, match_categories_from_text


RECOMMENDATION_POOL = {
    "구현": [
        {
            "title": "상하좌우",
            "topic": "구현",
            "url": "https://www.acmicpc.net/problem/14503",
            "source": "baekjoon",
        },
        {
            "title": "문자열 압축",
            "topic": "구현",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/60057",
            "source": "programmers",
        },
    ],
    "문자열": [
        {
            "title": "광고",
            "topic": "문자열",
            "url": "https://www.acmicpc.net/problem/1305",
            "source": "baekjoon",
        },
        {
            "title": "문자열 압축",
            "topic": "문자열",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/60057",
            "source": "programmers",
        },
    ],
    "사고력": [
        {
            "title": "Project Euler 1",
            "topic": "사고력",
            "url": "https://projecteuler.net/problem=1",
            "source": "project-euler",
        },
    ],
    "시뮬레이션": [
        {
            "title": "로봇 청소기",
            "topic": "시뮬레이션",
            "url": "https://www.acmicpc.net/problem/14503",
            "source": "baekjoon",
        },
    ],
    "재귀": [
        {
            "title": "재귀함수가 뭔가요?",
            "topic": "재귀",
            "url": "https://www.acmicpc.net/problem/17478",
            "source": "baekjoon",
        },
        {
            "title": "하노이 탑",
            "topic": "재귀",
            "url": "https://www.acmicpc.net/problem/1914",
            "source": "baekjoon",
        },
    ],
    "수학": [
        {
            "title": "소수 찾기",
            "topic": "수학",
            "url": "https://www.acmicpc.net/problem/1978",
            "source": "baekjoon",
        },
        {
            "title": "골드바흐의 추측",
            "topic": "수학",
            "url": "https://www.acmicpc.net/problem/9020",
            "source": "baekjoon",
        },
    ],
    "그래프": [
        {
            "title": "유기농 배추",
            "topic": "그래프",
            "url": "https://www.acmicpc.net/problem/1012",
            "source": "baekjoon",
        },
    ],
    "배열": [
        {
            "title": "두 개 뽑아서 더하기",
            "topic": "배열",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/68644",
            "source": "programmers",
        },
    ],
    "스택": [
        {
            "title": "올바른 괄호",
            "topic": "스택",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/12909",
            "source": "programmers",
        },
    ],
    "큐": [
        {
            "title": "카드2",
            "topic": "큐",
            "url": "https://www.acmicpc.net/problem/2164",
            "source": "baekjoon",
        },
    ],
    "트리": [
        {
            "title": "Maximum Depth of Binary Tree",
            "topic": "트리",
            "url": "https://leetcode.com/problems/maximum-depth-of-binary-tree/",
            "source": "leetcode",
        },
    ],
    "해시": [
        {
            "title": "완주하지 못한 선수",
            "topic": "해시",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/42576",
            "source": "programmers",
        },
    ],
    "힙": [
        {
            "title": "더 맵게",
            "topic": "힙",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/42626",
            "source": "programmers",
        },
    ],
    "정렬": [
        {
            "title": "K번째수",
            "topic": "정렬",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/42748",
            "source": "programmers",
        },
    ],
    "BFS": [
        {
            "title": "미로 탐색",
            "topic": "BFS",
            "url": "https://www.acmicpc.net/problem/2178",
            "source": "baekjoon",
        },
    ],
    "DFS": [
        {
            "title": "타겟 넘버",
            "topic": "DFS",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/43165",
            "source": "programmers",
        },
        {
            "title": "N-Queen",
            "topic": "DFS",
            "url": "https://www.acmicpc.net/problem/9663",
            "source": "baekjoon",
        },
    ],
    "그리디": [
        {
            "title": "큰 수 만들기",
            "topic": "그리디",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/42883",
            "source": "programmers",
        },
    ],
    "다이나믹프로그래밍": [
        {
            "title": "정수 삼각형",
            "topic": "다이나믹프로그래밍",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/43105",
            "source": "programmers",
        },
    ],
    "완전탐색": [
        {
            "title": "모의고사",
            "topic": "완전탐색",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/42840",
            "source": "programmers",
        },
    ],
    "이분탐색": [
        {
            "title": "랜선 자르기",
            "topic": "이분탐색",
            "url": "https://www.acmicpc.net/problem/1654",
            "source": "baekjoon",
        },
    ],
    "최단경로": [
        {
            "title": "최단경로",
            "topic": "최단경로",
            "url": "https://www.acmicpc.net/problem/1753",
            "source": "baekjoon",
        },
    ],
    "탐색": [
        {
            "title": "Binary Search",
            "topic": "탐색",
            "url": "https://leetcode.com/problems/binary-search/",
            "source": "leetcode",
        },
    ],
}


def calculate_weak_topics(repository_id: int, limit: int = 3) -> list[str]:
    ranked_topics = rank_weak_topics(repository_id, limit=limit)
    return [item["topic"] for item in ranked_topics]


def rank_weak_topics(repository_id: int, limit: int = 5) -> list[dict]:
    issues = get_issues_by_repository_id(repository_id)
    tracked_entries, extras = build_reporting_issue_entries(
        issues,
        list_problem_judgements_by_repository_id(repository_id),
        match_issue_by_filename,
    )
    judgements = tracked_entries + extras
    recent_topics = Counter(list_recent_commit_topics_by_repository_id(repository_id))
    category_stats = {
        category: {"total": 0, "solved": 0, "attempted_like": 0}
        for category in CATEGORY_KEYWORDS.keys()
    }

    for judgement in judgements:
        categories = match_categories_from_text(
            judgement.get("problem_key") or judgement.get("title", ""),
            judgement.get("file_path", ""),
        )
        for category in categories:
            stats = category_stats[category]
            stats["total"] += 1
            if judgement["judgement_status"] == "solved":
                stats["solved"] += 1
            elif judgement["judgement_status"] in {"attempted", "possibly_solved"}:
                stats["attempted_like"] += 1

    scored_topics = []
    for category, stats in category_stats.items():
        if stats["total"] == 0:
            continue

        solved_ratio = stats["solved"] / stats["total"] if stats["total"] else 0.0
        attempted_gap = 0.0
        if stats["attempted_like"] > 0:
            attempted_gap = 1 - (stats["solved"] / max(stats["attempted_like"], 1))
        recency_penalty = 0.35 if recent_topics[category] == 0 and solved_ratio < 1.0 else 0.0
        base_penalty = 1 - solved_ratio
        score = base_penalty + attempted_gap + recency_penalty

        if score <= 0:
            continue

        scored_topics.append(
            {
                "topic": category,
                "score": round(score, 2),
                "solved_ratio": round(solved_ratio, 2),
                "recent_count": recent_topics[category],
                "total": stats["total"],
                "solved": stats["solved"],
            }
        )

    scored_topics.sort(key=lambda item: (-item["score"], item["topic"]))
    return scored_topics[:limit]


def generate_recommendations(repository_id: int, limit: int = 3) -> dict:
    weak_topics = calculate_weak_topics(repository_id, limit=limit)
    existing_urls = {
        item["url"]
        for item in list_recommendations_by_repository_id(repository_id)
        if is_valid_recommendation(item)
    }
    created_recommendations = []

    for topic in weak_topics:
        for candidate in RECOMMENDATION_POOL.get(topic, []):
            if candidate["url"] in existing_urls:
                continue

            reason = build_recommendation_reason(topic)
            save_recommendation(
                repository_id=repository_id,
                topic=topic,
                problem_title=candidate["title"],
                problem_url=candidate["url"],
                source_site=candidate["source"],
                reason=reason,
            )
            existing_urls.add(candidate["url"])
            created_recommendations.append(
                {
                    **candidate,
                    "reason": reason,
                }
            )
            break

    return {
        "weak_topics": weak_topics,
        "recommendations": created_recommendations,
    }


def get_recommendations(repository_id: int) -> dict:
    weak_topics = calculate_weak_topics(repository_id)
    weak_topic_set = set(weak_topics)
    recommendations = [
        item
        for item in list_recommendations_by_repository_id(repository_id)
        if is_valid_recommendation(item) and item.get("topic") in weak_topic_set
    ]
    return {
        "weak_topics": weak_topics,
        "recommendations": recommendations,
    }


def build_recommendation_reason(topic: str) -> str:
    return f"{topic} 유형의 풀이 비율이 낮아 보강이 필요합니다."


def is_valid_recommendation(item: dict) -> bool:
    url = str(item.get("url", "")).strip()
    title = str(item.get("title", "")).strip()
    if not url or not title:
        return False
    if url == "https://www.acmicpc.net/":
        return False
    return True

from collections import Counter

from app.models.db import (
    list_problem_judgements_by_repository_id,
    list_recent_commit_topics_by_repository_id,
    list_recommendations_by_repository_id,
    save_recommendation,
)
from app.services.skill_map_service import CATEGORY_KEYWORDS, match_categories_from_text


RECOMMENDATION_POOL = {
    "재귀": [
        {
            "title": "재귀함수가 뭔가요?",
            "topic": "재귀",
            "url": "https://www.acmicpc.net/problem/17478",
            "source": "baekjoon",
        }
    ],
    "그래프": [
        {
            "title": "The Maze",
            "topic": "그래프",
            "url": "https://leetcode.com/problems/the-maze/",
            "source": "leetcode",
        }
    ],
    "배열": [
        {
            "title": "두 개 뽑아서 더하기",
            "topic": "배열",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/68644",
            "source": "programmers",
        }
    ],
    "스택": [
        {
            "title": "올바른 괄호",
            "topic": "스택",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/12909",
            "source": "programmers",
        }
    ],
    "큐": [
        {
            "title": "카드2",
            "topic": "큐",
            "url": "https://www.acmicpc.net/problem/2164",
            "source": "baekjoon",
        }
    ],
    "트리": [
        {
            "title": "Maximum Depth of Binary Tree",
            "topic": "트리",
            "url": "https://leetcode.com/problems/maximum-depth-of-binary-tree/",
            "source": "leetcode",
        }
    ],
    "해시": [
        {
            "title": "완주하지 못한 선수",
            "topic": "해시",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/42576",
            "source": "programmers",
        }
    ],
    "힙": [
        {
            "title": "더 맵게",
            "topic": "힙",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/42626",
            "source": "programmers",
        }
    ],
    "정렬": [
        {
            "title": "K번째 수",
            "topic": "정렬",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/42748",
            "source": "programmers",
        }
    ],
    "BFS": [
        {
            "title": "미로 탐색",
            "topic": "BFS",
            "url": "https://www.acmicpc.net/problem/2178",
            "source": "baekjoon",
        }
    ],
    "DFS": [
        {
            "title": "타겟 넘버",
            "topic": "DFS",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/43165",
            "source": "programmers",
        }
    ],
    "그리디": [
        {
            "title": "Greedy Gift Givers",
            "topic": "그리디",
            "url": "https://projecteuler.net/",
            "source": "project-euler",
        }
    ],
    "다이나믹프로그래밍": [
        {
            "title": "N-Queens",
            "topic": "다이나믹프로그래밍",
            "url": "https://leetcode.com/problems/n-queens/",
            "source": "leetcode",
        }
    ],
    "완전탐색": [
        {
            "title": "모의고사",
            "topic": "완전탐색",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/42840",
            "source": "programmers",
        }
    ],
    "이분탐색": [
        {
            "title": "랜선 자르기",
            "topic": "이분탐색",
            "url": "https://www.acmicpc.net/problem/1654",
            "source": "baekjoon",
        }
    ],
    "최단경로": [
        {
            "title": "Network Delay Time",
            "topic": "최단경로",
            "url": "https://leetcode.com/problems/network-delay-time/",
            "source": "leetcode",
        }
    ],
    "탐색": [
        {
            "title": "Binary Search",
            "topic": "탐색",
            "url": "https://leetcode.com/problems/binary-search/",
            "source": "leetcode",
        }
    ],
    "문자열": [
        {
            "title": "문자열 압축",
            "topic": "문자열",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/60057",
            "source": "programmers",
        }
    ],
    "구현": [
        {
            "title": "상하좌우",
            "topic": "구현",
            "url": "https://www.acmicpc.net/",
            "source": "baekjoon",
        }
    ],
}


def calculate_weak_topics(repository_id: int, limit: int = 3) -> list[str]:
    ranked_topics = rank_weak_topics(repository_id, limit=limit)
    return [item["topic"] for item in ranked_topics]


def rank_weak_topics(repository_id: int, limit: int = 5) -> list[dict]:
    judgements = list_problem_judgements_by_repository_id(repository_id)
    recent_topics = Counter(list_recent_commit_topics_by_repository_id(repository_id))
    category_stats = {
        category: {"total": 0, "solved": 0, "attempted_like": 0}
        for category in CATEGORY_KEYWORDS.keys()
    }

    for judgement in judgements:
        categories = match_categories_from_text(judgement["problem_key"], judgement.get("file_path", ""))
        for category in categories:
            stats = category_stats[category]
            stats["total"] += 1
            if judgement["judgement_status"] == "solved":
                stats["solved"] += 1
            else:
                stats["attempted_like"] += 1

    scored_topics = []
    for category, stats in category_stats.items():
        if stats["total"] == 0 and recent_topics[category] > 0:
            continue

        solved_ratio = stats["solved"] / stats["total"] if stats["total"] else 0.0
        attempted_gap = 0.0
        if stats["attempted_like"] > 0:
            attempted_gap = 1 - (stats["solved"] / max(stats["attempted_like"], 1))
        recency_penalty = 0.35 if recent_topics[category] == 0 else 0.0
        base_penalty = 1 - solved_ratio
        score = base_penalty + attempted_gap + recency_penalty

        if stats["total"] == 0 and recent_topics[category] == 0:
            score += 0.15

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
    existing_urls = {item["url"] for item in list_recommendations_by_repository_id(repository_id)}
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
    return {
        "weak_topics": weak_topics,
        "recommendations": list_recommendations_by_repository_id(repository_id),
    }


def build_recommendation_reason(topic: str) -> str:
    return f"{topic} 유형의 solved 비율이 낮아 보강이 필요합니다."

TOPIC_PROBLEMS = {
    "recursion": [
        {
            "title": "재귀로 모든 부분집합 구하기",
            "body": "작은 배열을 입력으로 받아 모든 부분집합을 재귀적으로 구해보세요.",
        },
        {
            "title": "재귀로 팩토리얼과 피보나치 구현하기",
            "body": "기저 조건과 재귀 호출 흐름이 잘 보이도록 함수를 작성해보세요.",
        },
        {
            "title": "하노이의 탑 작은 입력 해결하기",
            "body": "원판 이동 순서를 재귀로 출력하면서 문제 구조를 익혀보세요.",
        },
    ],
    "backtracking": [
        {
            "title": "백트래킹으로 N-Queens 풀기",
            "body": "행 단위로 퀸을 배치하고 불가능할 때 이전 상태로 되돌아가며 해결해보세요.",
        },
        {
            "title": "미로의 모든 경로 찾기",
            "body": "방문 처리를 하며 가능한 경로를 탐색하고 복귀 시 상태를 되돌려보세요.",
        },
        {
            "title": "조합 합 문제 해결하기",
            "body": "후보 조합을 재귀적으로 만들고 목표값을 넘는 경로는 가지치기해보세요.",
        },
    ],
    "graph": [
        {
            "title": "무방향 그래프의 연결 요소 개수 세기",
            "body": "각 노드 그룹을 한 번씩만 순회하며 분리된 그룹 개수를 구해보세요.",
        },
        {
            "title": "격자 최단 경로 찾기",
            "body": "큐 기반 BFS로 목표 지점까지의 최소 이동 횟수를 구해보세요.",
        },
        {
            "title": "방향 그래프에서 사이클 찾기",
            "body": "방문 상태와 현재 경로 상태를 함께 관리하며 사이클 존재 여부를 확인해보세요.",
        },
    ],
}

DEFAULT_TEMPLATES = [
    {
        "title": "{topic} 기초 문제 풀기",
        "body": "{topic}의 핵심 개념을 익힐 수 있는 짧은 Python 문제로 시작해보세요.",
    },
    {
        "title": "{topic} 핵심 패턴 구현하기",
        "body": "대표적인 {topic} 풀이 패턴을 Python으로 단계별 구현해보세요.",
    },
    {
        "title": "{topic} 응용 문제 해결하기",
        "body": "조금 더 어려운 {topic} 문제를 풀고 왜 이 접근이 맞는지 설명해보세요.",
    },
]


def generate_problems(topic: str, limit: int = 3) -> list[dict]:
    normalized_topic = topic.strip().lower()
    if not normalized_topic:
        return []

    if normalized_topic in TOPIC_PROBLEMS:
        return TOPIC_PROBLEMS[normalized_topic][:limit]

    return [
        {
            "title": template["title"].format(topic=normalized_topic),
            "body": template["body"].format(topic=normalized_topic),
        }
        for template in DEFAULT_TEMPLATES[:limit]
    ]

# API_REFERENCE

프론트엔드 연동용 백엔드 API 문서입니다.

- Base URL: `http://localhost:5000`
- 응답 형식: `application/json`
- 인증 방식: `GitHub OAuth + Flask Session`
- 세션 기반 인증이므로 브라우저/FE 요청 시 쿠키를 함께 보내야 합니다.

## 공통 응답 형식

### 성공

```json
{
  "success": true,
  "message": "요청이 성공했습니다.",
  "data": {}
}
```

### 실패

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "에러 메시지",
    "details": {}
  }
}
```

## 공통 에러 코드

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`
- `404 REPOSITORY_NOT_FOUND`
- `404 COMMIT_NOT_FOUND`
- `404 COMMIT_REVIEW_NOT_FOUND`
- `400 INVALID_REPOSITORY_PAYLOAD`
- `400 INVALID_PROJECT_PAYLOAD`
- `500 GITHUB_OAUTH_NOT_CONFIGURED`

---

## 1. 인증

### GitHub OAuth 흐름

1. `GET /api/auth/github/login`
2. 응답의 `authorization_url`로 GitHub 로그인
3. GitHub가 `/api/auth/github/callback`으로 리다이렉트
4. 서버가 세션 생성
5. `GET /api/auth/me`로 사용자 확인

### GET `/api/auth/github/login`

- 설명: GitHub OAuth 시작 URL 생성
- 인증 필요 여부: 아니오
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "GitHub OAuth 시작 URL을 생성했습니다.",
  "data": {
    "provider": "github",
    "authorization_url": "https://github.com/login/oauth/authorize?...",
    "state": "random-state"
  }
}
```

에러 케이스:

- `500 GITHUB_OAUTH_NOT_CONFIGURED`

### GET `/api/auth/github/callback`

- 설명: GitHub authorization code 교환 및 로그인 세션 생성
- 인증 필요 여부: 아니오
- 요청 파라미터:
  - `code`
  - `state`
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "GitHub 로그인이 완료되었습니다.",
  "data": {
    "user": {
      "id": 1,
      "github_user_id": "2002",
      "github_login": "oauth-user",
      "github_name": "OAuth User",
      "created_at": "2026-03-11T12:00:00+00:00",
      "updated_at": "2026-03-11T12:00:00+00:00"
    }
  }
}
```

에러 케이스:

- 잘못된 `code`
- 잘못된 `state`

### GET `/api/auth/me`

- 설명: 현재 로그인 사용자 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "현재 로그인 사용자 정보를 조회했습니다.",
  "data": {
    "user": {
      "id": 1,
      "github_user_id": "2002",
      "github_login": "oauth-user",
      "github_name": "OAuth User",
      "created_at": "2026-03-11T12:00:00+00:00",
      "updated_at": "2026-03-11T12:00:00+00:00"
    }
  }
}
```

에러 케이스:

- `401 UNAUTHORIZED`

---

## 2. Repository API

### GET `/api/repositories`

- 설명: 로그인한 GitHub 사용자의 저장소 목록 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "저장소 목록을 조회했습니다.",
  "data": {
    "repositories": [
      {
        "github_repo_id": "12345",
        "owner": "JYPark-Code",
        "name": "SW-AI-W02-05",
        "full_name": "JYPark-Code/SW-AI-W02-05",
        "default_branch": "main",
        "private": false
      }
    ]
  }
}
```

### POST `/api/repositories/select`

- 설명: 분석 대상 저장소를 DB와 세션에 저장
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body:

```json
{
  "owner": "JYPark-Code",
  "name": "SW-AI-W02-05",
  "full_name": "JYPark-Code/SW-AI-W02-05",
  "github_repo_id": "12345",
  "default_branch": "main"
}
```

응답 예시:

```json
{
  "success": true,
  "message": "분석 대상 저장소가 선택되었습니다.",
  "data": {
    "repository": {
      "id": 1,
      "user_id": 1,
      "owner": "JYPark-Code",
      "name": "SW-AI-W02-05",
      "full_name": "JYPark-Code/SW-AI-W02-05",
      "created_at": "2026-03-11T12:00:00+00:00",
      "last_synced_at": null
    }
  }
}
```

에러 케이스:

- `401 UNAUTHORIZED`
- `400 INVALID_REPOSITORY_PAYLOAD`

### GET `/api/repositories/current`

- 설명: 현재 세션 기준 저장소 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "현재 선택된 저장소를 조회했습니다.",
  "data": {
    "repository": {
      "id": 1,
      "user_id": 1,
      "owner": "JYPark-Code",
      "name": "SW-AI-W02-05",
      "full_name": "JYPark-Code/SW-AI-W02-05",
      "created_at": "2026-03-11T12:00:00+00:00",
      "last_synced_at": "2026-03-11T12:30:00+00:00"
    }
  }
}
```

에러 케이스:

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`
- `404 REPOSITORY_NOT_FOUND`

---

## 3. Sync API

### POST `/api/repositories/current/sync`

- 설명: 현재 저장소의 GitHub issues / commits를 DB에 동기화
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "저장소 동기화가 완료되었습니다.",
  "data": {
    "new_issue_count": 12,
    "new_commit_count": 8,
    "last_synced_at": "2026-03-11T12:30:00+00:00",
    "issue_total": 24,
    "commit_total": 16
  }
}
```

### GET `/api/repositories/current/sync-status`

- 설명: 현재 저장소의 동기화 상태 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "저장소 동기화 상태를 조회했습니다.",
  "data": {
    "repository_id": 1,
    "issue_count": 24,
    "commit_count": 16,
    "last_synced_at": "2026-03-11T12:30:00+00:00"
  }
}
```

---

## 4. Issue Template API

운영 규칙:

- `basic`, `common`: 필수
- `problem-solving`: 기본적으로 필수
- `problem-solving 상`, `Extra`: 선택
- `ACTIVE_WEEK` 또는 `week` 파라미터 기준으로 현재 주차 계산 가능

### GET `/api/issues/template-status`

- 설명: CSV 템플릿 기준 이슈 상태 조회
- 인증 필요 여부: 예
- 요청 파라미터:
  - `week` (optional): 예 `week2`, `week3`
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "CSV 템플릿 기준 이슈 상태를 조회했습니다.",
  "data": {
    "template_count": 129,
    "matched_count": 80,
    "missing_count": 49,
    "active_week": "week3",
    "active_week_template_count": 20,
    "required_template_count": 12,
    "required_matched_count": 7,
    "required_progress": 0.58,
    "matched_issues": [
      {
        "title": "basic - 배열 연습",
        "category": "basic",
        "track_type": "basic",
        "difficulty_level": "unspecified",
        "requirement_level": "required",
        "week_label": "week3",
        "source_file": "week3_issues_complete.csv",
        "github_issue_id": "100",
        "issue_number": 1,
        "state": "open"
      }
    ],
    "missing_issues": []
  }
}
```

### POST `/api/issues/create-missing`

- 설명: 누락 issue를 GitHub에 일괄 생성
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body:

```json
{
  "week": "week3"
}
```

`week`를 생략하면 `ACTIVE_WEEK` 또는 내부 active week 판단 기준을 사용합니다.

응답 예시:

```json
{
  "success": true,
  "message": "누락 이슈 생성을 완료했습니다.",
  "data": {
    "template_count": 129,
    "matched_count": 129,
    "missing_count": 0,
    "active_week": "week3",
    "required_template_count": 12,
    "required_matched_count": 12,
    "required_progress": 1.0,
    "missing_issues": [],
    "created_issues": [
      {
        "title": "problem-solving 하 - 그래프",
        "category": "weekly",
        "track_type": "problem-solving",
        "difficulty_level": "low",
        "requirement_level": "required",
        "week_label": "week3",
        "issue_number": 91,
        "issue_url": "https://github.com/owner/repo/issues/91",
        "state": "open"
      }
    ]
  }
}
```

---

## 5. Commit Analysis API

### GET `/api/commits`

- 설명: 동기화된 commit 목록 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

### POST `/api/commits/{sha}/analyze-files`

- 설명: 특정 commit의 changed files 분석
- 인증 필요 여부: 예
- 요청 파라미터:
  - `sha`
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "commit 파일 분석을 완료했습니다.",
  "data": {
    "commit_sha": "abc123",
    "analyzed_at": "2026-03-11T12:40:00+00:00",
    "analyzed_file_count": 2,
    "python_file_count": 1,
    "matched_problems": [
      {
        "file_path": "week2/graph_bfs.py",
        "normalized_filename": "graph bfs",
        "matched_issue_title": "week2 - 그래프 BFS 문제",
        "issue_number": 1,
        "match_score": 0.85,
        "judgement_status": "possibly_solved"
      }
    ],
    "attempted_count": 0,
    "possibly_solved_count": 1,
    "solved_count": 0
  }
}
```

---

## 6. Judge API

### POST `/api/commits/{sha}/judge`

- 설명: commit 기준 풀이 상태 판정 저장
- 인증 필요 여부: 예
- 요청 파라미터:
  - `sha`
- 요청 body: 없음

### GET `/api/commits/{sha}/judge-result`

- 설명: commit 기준 판정 결과 조회
- 인증 필요 여부: 예
- 요청 파라미터:
  - `sha`
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "commit 판정 결과를 조회했습니다.",
  "data": {
    "commit_sha": "abc123",
    "results": [
      {
        "id": 1,
        "repository_id": 1,
        "commit_id": 1,
        "issue_number": 1,
        "problem_key": "week2 - 그래프 BFS 문제",
        "file_path": "week2/graph_bfs.py",
        "judgement_status": "possibly_solved",
        "match_score": 0.85,
        "matched_by_filename": 1,
        "execution_passed": 0,
        "sample_output_matched": 0,
        "judged_at": "2026-03-11T12:40:00+00:00",
        "notes": "title 토큰 유사도 0.85로 매칭했습니다."
      }
    ],
    "attempted_count": 0,
    "possibly_solved_count": 1,
    "solved_count": 0
  }
}
```

---

## 7. Review API

### POST `/api/commits/{sha}/review`

- 설명: commit 기반 코드 리뷰 생성
- 인증 필요 여부: 예
- 요청 파라미터:
  - `sha`
- 요청 body: 없음

### GET `/api/commits/{sha}/review`

- 설명: 이미 생성된 commit 리뷰 조회
- 인증 필요 여부: 예
- 요청 파라미터:
  - `sha`
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "commit 코드 리뷰를 조회했습니다.",
  "data": {
    "commit_sha": "review123",
    "review_summary": "이번 commit은 BFS, 그래프 유형 풀이가 중심이며, 총 1개 Python 파일을 검토했습니다.",
    "review_comments": [
      "week2/graph_bfs.py: 함수 분리가 되어 있어 구조가 비교적 명확합니다., 예상 시간 복잡도 O(V + E)"
    ],
    "detected_topics": ["BFS", "그래프"],
    "execution_status": "not_run",
    "analyzed_at": "2026-03-11T12:50:00+00:00"
  }
}
```

---

## 8. Skill Map API

### GET `/api/repositories/current/skill-map`

- 설명: 저장소 기준 Skill Map 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "repository Skill Map을 조회했습니다.",
  "data": {
    "domains": [
      {
        "name": "탐색",
        "total": 3,
        "solved": 2,
        "possibly_solved": 1,
        "attempted": 0
      }
    ],
    "summary": {
      "attempted_count": 1,
      "possibly_solved_count": 1,
      "solved_count": 2,
      "total_count": 4
    }
  }
}
```

---

## 9. Recommendation API

### POST `/api/repositories/current/recommendations/generate`

- 설명: 약점 기반 추천 생성 및 저장
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

### GET `/api/repositories/current/recommendations`

- 설명: 저장된 추천 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "저장된 추천 문제를 조회했습니다.",
  "data": {
    "weak_topics": ["문자열", "다이나믹프로그래밍"],
    "recommendations": [
      {
        "id": 1,
        "repository_id": 1,
        "report_id": null,
        "topic": "문자열",
        "source": "programmers",
        "title": "문자열 압축",
        "url": "https://school.programmers.co.kr/learn/courses/30/lessons/60057",
        "reason": "문자열 유형의 solved 비율이 낮아 보강이 필요합니다.",
        "recommended_at": "2026-03-11T13:00:00+00:00"
      }
    ]
  }
}
```

---

## 10. Dashboard API

### GET `/api/dashboard/summary`

- 설명: 메인 대시보드 요약 정보 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "대시보드 요약 정보를 조회했습니다.",
  "data": {
    "status": "Watch",
    "active_week": "week3",
    "solved_count": 25,
    "attempted_count": 40,
    "extra_practice_count": 3,
    "week_progress": 0.6,
    "last_synced_at": "2026-03-11T12:30:00+00:00",
    "skill_map": {},
    "weak_topics": ["문자열"],
    "recommendations": [],
    "current_project": {
      "id": 1,
      "repository_id": 1,
      "week_label": "week3",
      "project_title": "Week 3 Tracking",
      "project_url": "https://github.com/orgs/example/projects/3",
      "project_number": "3",
      "is_active": 1
    }
  }
}
```

---

## 11. MyPage API

### GET `/api/mypage/report`

- 설명: 사용자 분석 리포트 전체 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "마이페이지 분석 리포트를 조회했습니다.",
  "data": {
    "repository": {
      "id": 1,
      "user_id": 1,
      "owner": "JYPark-Code",
      "name": "SW-AI-W02-05",
      "full_name": "JYPark-Code/SW-AI-W02-05",
      "created_at": "2026-03-11T12:00:00+00:00",
      "last_synced_at": "2026-03-11T12:30:00+00:00"
    },
    "active_week": "week3",
    "status": "Watch",
    "solved_count": 25,
    "attempted_count": 40,
    "possibly_solved_count": 5,
    "extra_practice_count": 3,
    "week_progress": 0.6,
    "required_template_count": 12,
    "required_matched_count": 7,
    "last_synced_at": "2026-03-11T12:30:00+00:00",
    "current_project": null,
    "skill_map": {},
    "ai_summary": "현재 상태는 Watch입니다. 필수 과제 진행률은 60%, tracked solved 비율은 38%이며, 우선 보강이 필요한 영역은 문자열입니다.",
    "domain_analysis": [],
    "weak_topics": ["문자열"],
    "weak_topic_ranking": [],
    "recommendations": []
  }
}
```

---

## 운영용 Project API

### POST `/api/repositories/current/projects/track`

- 설명: 현재 주차 GitHub Project 추적 대상을 저장
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body:

```json
{
  "week_label": "week3",
  "project_title": "Week 3 Tracking",
  "project_url": "https://github.com/orgs/example/projects/3",
  "project_number": "3"
}
```

응답 예시:

```json
{
  "success": true,
  "message": "현재 주차 GitHub Project 추적 대상을 저장했습니다.",
  "data": {
    "project_id": 1,
    "project": {
      "id": 1,
      "repository_id": 1,
      "week_label": "week3",
      "project_title": "Week 3 Tracking",
      "project_url": "https://github.com/orgs/example/projects/3",
      "project_number": "3",
      "is_active": 1,
      "created_at": "2026-03-11T13:10:00+00:00",
      "updated_at": "2026-03-11T13:10:00+00:00"
    }
  }
}
```

### GET `/api/repositories/current/projects/current`

- 설명: 현재 추적 중인 GitHub Project 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "현재 추적 중인 GitHub Project를 조회했습니다.",
  "data": {
    "project": {
      "id": 1,
      "repository_id": 1,
      "week_label": "week3",
      "project_title": "Week 3 Tracking",
      "project_url": "https://github.com/orgs/example/projects/3",
      "project_number": "3",
      "is_active": 1
    }
  }
}
```

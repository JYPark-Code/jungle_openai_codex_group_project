# API Reference

기준 백엔드: Flask + Session + SQLite  
기본 주소: `http://127.0.0.1:5000`

## 공통 규칙

- 모든 응답은 JSON입니다.
- 인증이 필요한 API는 GitHub OAuth 로그인 후 session cookie가 필요합니다.
- 프론트엔드에서 호출할 때는 `credentials: "include"`를 사용해야 합니다.

### 성공 응답

```json
{
  "success": true,
  "message": "요청이 성공했습니다.",
  "data": {}
}
```

### 실패 응답

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

## 1. 인증

### GitHub OAuth 흐름

1. `GET /api/auth/github/login`
2. GitHub 로그인
3. `GET /api/auth/github/callback`
4. session 생성
5. `GET /api/auth/me`

### GET `/api/auth/github/login`

- 설명: GitHub OAuth 시작 URL을 생성하거나 바로 리다이렉트합니다.
- 인증 필요 여부: 아니오
- 요청 파라미터:
  - `mode` optional, `json` 또는 `redirect`
  - `next` optional, 로그인 성공 후 프론트엔드로 돌아갈 URL
- 요청 body: 없음

기본 JSON 응답 예시:

```json
{
  "success": true,
  "message": "GitHub OAuth 시작 URL을 생성했습니다.",
  "data": {
    "provider": "github",
    "authorization_url": "https://github.com/login/oauth/authorize?...",
    "state": "random-state",
    "mode": "json",
    "next_url": "http://127.0.0.1:3000/auth/callback"
  }
}
```

로컬 FE 권장 사용 예시:

```text
GET /api/auth/github/login?mode=redirect&next=http://127.0.0.1:3000/auth/callback
```

에러 케이스:

- `500 GITHUB_OAUTH_NOT_CONFIGURED`

### GET `/api/auth/github/callback`

- 설명: GitHub authorization code를 access token으로 교환하고 session을 생성합니다.
- 인증 필요 여부: 아니오
- 요청 파라미터:
  - `code`
  - `state`
- 요청 body: 없음

JSON 모드 응답 예시:

```json
{
  "success": true,
  "message": "GitHub 로그인이 완료되었습니다.",
  "data": {
    "user": {
      "id": 1,
      "github_user_id": "2002",
      "github_login": "oauth-user",
      "github_name": "OAuth 사용자",
      "created_at": "2026-03-11T12:00:00+00:00",
      "updated_at": "2026-03-11T12:00:00+00:00"
    }
  }
}
```

리다이렉트 모드 동작:

- 성공 시: `FRONTEND_OAUTH_SUCCESS_URL` 또는 `next`로 `status=success`와 함께 이동
- 실패 시: `FRONTEND_OAUTH_FAILURE_URL`로 `status=error&code=...`와 함께 이동

에러 케이스:

- `400 GITHUB_CODE_MISSING`
- `400 GITHUB_STATE_MISMATCH`
- `400 GITHUB_TOKEN_EXCHANGE_FAILED`
- `400 GITHUB_USER_FETCH_FAILED`
- `500 GITHUB_OAUTH_NOT_CONFIGURED`

### GET `/api/auth/me`

- 설명: 현재 로그인한 사용자 정보를 조회합니다.
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "현재 로그인한 사용자 정보를 조회했습니다.",
  "data": {
    "user": {
      "id": 1,
      "github_user_id": "2002",
      "github_login": "oauth-user",
      "github_name": "OAuth 사용자"
    }
  }
}
```

에러 케이스:

- `401 UNAUTHORIZED`

### POST `/api/auth/logout`

- 설명: 현재 session을 종료합니다.
- 인증 필요 여부: 아니오
- 요청 파라미터: 없음
- 요청 body: 없음

응답 예시:

```json
{
  "success": true,
  "message": "로그아웃되었습니다.",
  "data": {}
}
```

## 2. Repository API

### GET `/api/repositories`

- 설명: 로그인한 사용자의 GitHub 저장소 목록을 조회합니다.
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

### POST `/api/repositories/select`

- 설명: 분석 대상 저장소를 선택하고 DB와 session에 저장합니다.
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

### GET `/api/repositories/current`

- 설명: 현재 session 기준 선택된 저장소를 조회합니다.
- 인증 필요 여부: 예

## 3. Sync API

### POST `/api/repositories/current/sync`

- 설명: 현재 저장소의 issues와 commits를 GitHub에서 읽어 DB에 동기화합니다.
- 인증 필요 여부: 예

주요 응답 필드:

- `new_issue_count`
- `new_commit_count`
- `last_synced_at`
- `issue_total`
- `commit_total`

### GET `/api/repositories/current/sync-status`

- 설명: 현재 저장소의 마지막 동기화 상태를 조회합니다.
- 인증 필요 여부: 예

## 4. Issue Template API

### GET `/api/issues/template-status`

- 설명: CSV 템플릿 기준으로 현재 저장소의 이슈 상태를 계산합니다.
- 인증 필요 여부: 예
- 요청 파라미터:
  - `week` optional, 예: `week3`

주요 응답 필드:

- `template_count`
- `matched_count`
- `missing_count`
- `active_week`
- `required_template_count`
- `required_matched_count`
- `required_progress`
- `missing_issues`

### POST `/api/issues/create-missing`

- 설명: 누락된 템플릿 이슈를 GitHub에 일괄 생성하고 DB에 반영합니다.
- 인증 필요 여부: 예
- 요청 body:

```json
{
  "week": "week3"
}
```

## 5. Commit Analysis API

### GET `/api/commits`

- 설명: 현재 저장소에 동기화된 commit 목록을 조회합니다.
- 인증 필요 여부: 예

### GET `/api/commits/{sha}`

- 설명: 특정 commit 메타데이터를 조회합니다.
- 인증 필요 여부: 예

### POST `/api/commits/{sha}/analyze-files`

- 설명: 특정 commit의 changed files를 기준으로 Python 파일과 문제 매칭 결과를 분석합니다.
- 인증 필요 여부: 예

주요 응답 필드:

- `commit_sha`
- `analyzed_file_count`
- `python_file_count`
- `matched_problems`
- `attempted_count`
- `possibly_solved_count`
- `solved_count`

## 6. Judge API

### POST `/api/commits/{sha}/judge`

- 설명: 분석 결과를 기준으로 attempted / possibly_solved / solved 상태를 갱신합니다.
- 인증 필요 여부: 예

### GET `/api/commits/{sha}/judge-result`

- 설명: 특정 commit의 판정 결과를 조회합니다.
- 인증 필요 여부: 예

## 7. Review API

### POST `/api/commits/{sha}/review`

- 설명: 특정 commit의 Python 파일을 기준으로 코드 리뷰를 생성합니다.
- 인증 필요 여부: 예

### GET `/api/commits/{sha}/review`

- 설명: 저장된 commit 리뷰 결과를 조회합니다.
- 인증 필요 여부: 예

## 8. Skill Map API

### GET `/api/repositories/current/skill-map`

- 설명: 저장소 단위 Skill Map 통계를 반환합니다.
- 인증 필요 여부: 예

응답 예시:

```json
{
  "success": true,
  "message": "Skill Map을 조회했습니다.",
  "data": {
    "domains": [
      {
        "name": "탐색",
        "total": 8,
        "solved": 3
      },
      {
        "name": "자료구조",
        "total": 7,
        "solved": 4
      }
    ]
  }
}
```

## 9. Recommendation API

### POST `/api/repositories/current/recommendations/generate`

- 설명: 약점 토픽을 계산하고 추천 문제를 생성합니다.
- 인증 필요 여부: 예

### GET `/api/repositories/current/recommendations`

- 설명: 저장된 추천 문제 목록을 조회합니다.
- 인증 필요 여부: 예

## 10. Dashboard API

### GET `/api/dashboard/summary`

- 설명: 운영 대시보드에 필요한 핵심 요약 정보를 반환합니다.
- 인증 필요 여부: 예

주요 응답 필드:

- `status`
- `active_week`
- `solved_count`
- `attempted_count`
- `extra_practice_count`
- `week_progress`
- `last_synced_at`
- `skill_map`
- `weak_topics`
- `recommendations`
- `current_project`

## 11. MyPage API

### GET `/api/mypage/report`

- 설명: 마이페이지 리포트 전체 데이터를 반환합니다.
- 인증 필요 여부: 예

주요 응답 필드:

- `repository`
- `active_week`
- `status`
- `solved_count`
- `attempted_count`
- `possibly_solved_count`
- `extra_practice_count`
- `week_progress`
- `required_template_count`
- `required_matched_count`
- `last_synced_at`
- `current_project`
- `skill_map`
- `ai_summary`
- `domain_analysis`
- `weak_topics`
- `weak_topic_ranking`
- `recommendations`

## 추가 운영 API

### POST `/api/repositories/current/projects/track`

- 설명: 현재 주차 GitHub Project 추적 대상을 저장합니다.
- 인증 필요 여부: 예

### GET `/api/repositories/current/projects/current`

- 설명: 현재 추적 중인 GitHub Project 정보를 조회합니다.
- 인증 필요 여부: 예

# API_REFERENCE

프론트엔드 연동용 백엔드 API 문서입니다.

- Base URL: `http://localhost:5000`
- 응답 형식: `application/json`
- 인증 방식: `GitHub OAuth + Flask Session`
- 세션 기반 인증이므로 FE 요청 시 쿠키를 함께 보내야 합니다.

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

### GET `/api/auth/me`

- 설명: 현재 로그인 사용자 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

---

## 2. Repository API

### GET `/api/repositories`

- 설명: 로그인한 GitHub 사용자의 저장소 목록 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

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

### GET `/api/repositories/current`

- 설명: 현재 세션 기준 저장소 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

---

## 3. Sync API

### POST `/api/repositories/current/sync`

- 설명: 현재 저장소의 GitHub issues / commits를 DB에 동기화
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 주요 필드:

- `new_issue_count`
- `new_commit_count`
- `last_synced_at`
- `issue_total`
- `commit_total`

### GET `/api/repositories/current/sync-status`

- 설명: 현재 저장소의 동기화 상태 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

---

## 4. Issue Template API

운영 규칙:

- `week2`는 이미 반영된 상태로 간주
- `2026-03-13 금요일`부터 `week3`, 이후 매주 금요일마다 `week4`, `week5`로 자동 전환
- `basic`, `common`은 필수
- `problem-solving`은 기본적으로 필수
- `problem-solving 상`, `Extra`는 선택
- 현재 자동 추적 범위는 `week2~week5`

### GET `/api/issues/template-status`

- 설명: CSV 템플릿 기준 이슈 상태 조회
- 인증 필요 여부: 예
- 요청 파라미터:
  - `week` (optional): 예 `week2`, `week3`
- 요청 body: 없음

응답 주요 필드:

- `template_count`
- `matched_count`
- `missing_count`
- `active_week`
- `active_week_template_count`
- `required_template_count`
- `required_matched_count`
- `required_progress`
- `matched_issues`
- `missing_issues`

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

`week`를 생략하면 서버 날짜 기준 자동 주차를 사용합니다.

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

응답 주요 필드:

- `commit_sha`
- `analyzed_at`
- `analyzed_file_count`
- `python_file_count`
- `matched_problems`
- `attempted_count`
- `possibly_solved_count`
- `solved_count`

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

---

## 8. Skill Map API

### GET `/api/repositories/current/skill-map`

- 설명: 저장소 기준 Skill Map 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

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

---

## 10. Dashboard API

### GET `/api/dashboard/summary`

- 설명: 메인 대시보드 요약 정보 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 주요 필드:

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

---

## 11. MyPage API

### GET `/api/mypage/report`

- 설명: 사용자 분석 리포트 전체 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

응답 주요 필드:

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

### GET `/api/repositories/current/projects/current`

- 설명: 현재 추적 중인 GitHub Project 조회
- 인증 필요 여부: 예
- 요청 파라미터: 없음
- 요청 body: 없음

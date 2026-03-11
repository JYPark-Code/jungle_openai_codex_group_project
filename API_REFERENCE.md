# API_REFERENCE

정글 알고리즘 학습 운영 대시보드 백엔드 API 문서입니다.  
기준 코드는 현재 Flask 백엔드 구현 상태이며, 프론트엔드가 바로 연동할 수 있도록 실제 응답 구조 기준으로 정리했습니다.

## 기본 정보

- Base URL: `http://localhost:5000`
- 응답 형식: `application/json`
- 인증 방식: `GitHub OAuth + Flask Session`
- 토큰 저장 위치: 서버 세션
- FE 주의사항: 로그인 이후 요청에서는 세션 쿠키를 함께 보내야 합니다.

## 공통 응답 형식

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

## 공통 에러 케이스

- `401 UNAUTHORIZED`
  - 로그인 세션이 없을 때
- `404 REPOSITORY_NOT_SELECTED`
  - 현재 선택된 저장소가 없을 때
- `404 REPOSITORY_NOT_FOUND`
  - 세션에 저장된 저장소를 DB에서 찾지 못할 때
- `404 COMMIT_NOT_FOUND`
  - 요청한 commit이 없을 때
- `404 COMMIT_REVIEW_NOT_FOUND`
  - commit 리뷰가 아직 생성되지 않았을 때
- `400 INVALID_REPOSITORY_PAYLOAD`
  - 저장소 선택 요청 body가 잘못되었을 때
- `500 GITHUB_OAUTH_NOT_CONFIGURED`
  - GitHub OAuth 환경변수가 빠졌을 때

---

## 1. 인증

### GitHub OAuth 로그인 흐름

1. `GET /api/auth/github/login` 호출
2. 응답으로 받은 `authorization_url`로 GitHub 로그인 페이지 이동
3. GitHub가 `GET /api/auth/github/callback?code=...&state=...`로 리다이렉트
4. 서버가 access token을 세션에 저장하고 사용자 정보를 DB에 저장
5. 이후 `GET /api/auth/me`로 로그인 사용자 정보 확인

### 1-1. GitHub OAuth 시작

- 설명: GitHub OAuth 로그인 시작 URL을 생성합니다.
- Method: `GET`
- URL: `/api/auth/github/login`
- 인증 필요 여부: `아니오`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "GitHub OAuth 시작 URL을 생성했습니다.",
  "data": {
    "provider": "github",
    "authorization_url": "https://github.com/login/oauth/authorize?client_id=...&redirect_uri=...&scope=read:user&state=...",
    "state": "random-state-string"
  }
}
```

#### 에러 케이스

- `500 GITHUB_OAUTH_NOT_CONFIGURED`

### 1-2. GitHub OAuth Callback

- 설명: GitHub에서 전달한 `code`와 `state`를 검증하고 로그인 세션을 생성합니다.
- Method: `GET`
- URL: `/api/auth/github/callback`
- 인증 필요 여부: `아니오`
- 요청 파라미터:
  - `code`: GitHub authorization code
  - `state`: 로그인 시작 시 발급받은 state
- 요청 body: 없음

#### 응답 예시

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

#### 에러 케이스

- `400`: 잘못된 `code` 또는 `state`
- `500`: GitHub OAuth 설정 누락 또는 GitHub API 호출 실패

### 1-3. 현재 로그인 사용자 조회

- 설명: 현재 세션 기준 로그인 사용자 정보를 반환합니다.
- Method: `GET`
- URL: `/api/auth/me`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

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

#### 에러 케이스

- `401 UNAUTHORIZED`

---

## 2. Repository API

### 2-1. GitHub 저장소 목록 조회

- 설명: 로그인한 GitHub 사용자의 저장소 목록을 조회합니다.
- Method: `GET`
- URL: `/api/repositories`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

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

#### 에러 케이스

- `401 UNAUTHORIZED`
- GitHub API 인증 실패 시 HTTP 에러

### 2-2. 분석 대상 저장소 선택

- 설명: 사용자가 분석할 저장소를 DB와 세션에 저장합니다.
- Method: `POST`
- URL: `/api/repositories/select`
- 인증 필요 여부: `예`
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

#### 응답 예시

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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `400 INVALID_REPOSITORY_PAYLOAD`

### 2-3. 현재 선택된 저장소 조회

- 설명: 현재 세션에 저장된 저장소를 조회합니다.
- Method: `GET`
- URL: `/api/repositories/current`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`
- `404 REPOSITORY_NOT_FOUND`

---

## 3. Sync API

### 3-1. 현재 저장소 동기화

- 설명: 선택한 GitHub 저장소의 issues와 commits를 DB에 동기화합니다.
- Method: `POST`
- URL: `/api/repositories/current/sync`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`
- GitHub API 호출 실패

### 3-2. 현재 저장소 동기화 상태 조회

- 설명: 동기화된 issue/commit 수와 마지막 동기화 시각을 반환합니다.
- Method: `GET`
- URL: `/api/repositories/current/sync-status`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`

---

## 4. Issue Template API

### 4-1. CSV 템플릿 기준 이슈 상태 조회

- 설명: `resources/csv` 기준으로 템플릿 이슈와 현재 저장소 이슈를 title 기준으로 매칭합니다.
- Method: `GET`
- URL: `/api/issues/template-status`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "CSV 템플릿 기준 이슈 상태를 조회했습니다.",
  "data": {
    "template_count": 129,
    "matched_count": 80,
    "missing_count": 49,
    "matched_issues": [
      {
        "title": "week2 - 그래프 BFS 문제",
        "category": "weekly",
        "source_file": "week2_issues_complete.csv",
        "github_issue_id": "100",
        "issue_number": 1,
        "state": "open"
      }
    ],
    "missing_issues": [
      {
        "title": "week3 - 문자열 문제",
        "content": "문제 설명",
        "category": "weekly",
        "source_file": "week3_issues_complete.csv"
      }
    ]
  }
}
```

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`

### 4-2. 누락 이슈 일괄 생성

- 설명: CSV 템플릿 기준 누락된 issue를 GitHub에 일괄 생성하고 DB에도 반영합니다.
- Method: `POST`
- URL: `/api/issues/create-missing`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "누락 이슈 생성을 완료했습니다.",
  "data": {
    "template_count": 129,
    "matched_count": 129,
    "missing_count": 0,
    "missing_issues": [],
    "created_issues": [
      {
        "title": "week3 - 문자열 문제",
        "category": "weekly",
        "issue_number": 99,
        "issue_url": "https://github.com/JYPark-Code/SW-AI-W02-05/issues/99",
        "state": "open"
      }
    ]
  }
}
```

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`
- GitHub issue 생성 실패

---

## 5. Commit Analysis API

### 5-1. Commit 목록 조회

- 설명: 현재 저장소에 동기화된 commit 목록을 조회합니다.
- Method: `GET`
- URL: `/api/commits`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "commit 목록을 조회했습니다.",
  "data": {
    "commits": [
      {
        "id": 1,
        "sha": "abc123",
        "author_name": "JYPark",
        "message": "week2 solution",
        "committed_at": "2026-03-11T11:00:00Z",
        "analyzed_at": "2026-03-11T12:00:00+00:00",
        "file_count": 2
      }
    ]
  }
}
```

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`

### 5-2. Commit 파일 분석

- 설명: 특정 commit의 changed files를 조회하고 Python 파일만 추려 문제 매칭용 분석을 수행합니다.
- Method: `POST`
- URL: `/api/commits/{sha}/analyze-files`
- 인증 필요 여부: `예`
- 요청 파라미터:
  - `sha`: commit SHA
- 요청 body: 없음

#### 응답 예시

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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`
- `404 COMMIT_NOT_FOUND`에 준하는 GitHub commit 조회 실패

---

## 6. Judge API

### 6-1. Commit 판정 실행

- 설명: commit 파일 분석 결과를 기반으로 `attempted / possibly_solved / solved` 상태를 계산하여 저장합니다.
- Method: `POST`
- URL: `/api/commits/{sha}/judge`
- 인증 필요 여부: `예`
- 요청 파라미터:
  - `sha`: commit SHA
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "commit 판정을 완료했습니다.",
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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`

### 6-2. Commit 판정 결과 조회

- 설명: 특정 commit에 저장된 판정 결과를 조회합니다.
- Method: `GET`
- URL: `/api/commits/{sha}/judge-result`
- 인증 필요 여부: `예`
- 요청 파라미터:
  - `sha`: commit SHA
- 요청 body: 없음

#### 응답 예시

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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 COMMIT_NOT_FOUND`

---

## 7. Review API

### 7-1. Commit 코드 리뷰 생성

- 설명: 특정 commit의 Python 파일 내용을 읽어서 알고리즘 유형, 코드 구조, 시간 복잡도, 개선 제안을 생성합니다.
- Method: `POST`
- URL: `/api/commits/{sha}/review`
- 인증 필요 여부: `예`
- 요청 파라미터:
  - `sha`: commit SHA
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "commit 코드 리뷰를 생성했습니다.",
  "data": {
    "commit_sha": "review123",
    "python_file_count": 1,
    "detected_topics": ["BFS", "그래프"],
    "review_summary": "이번 commit은 BFS, 그래프 유형 풀이가 중심이며, 총 1개 Python 파일을 검토했습니다.",
    "review_comments": [
      "week2/graph_bfs.py: 함수 분리가 되어 있어 구조가 비교적 명확합니다., 예상 시간 복잡도 O(V + E)"
    ],
    "files": [
      {
        "file_path": "week2/graph_bfs.py",
        "detected_categories": ["BFS", "그래프"],
        "code_structure": "함수 분리가 되어 있어 구조가 비교적 명확합니다.",
        "estimated_time_complexity": "O(V + E)",
        "suggestion": "탐색 문제라면 방문 처리 위치를 한 번 더 점검해보세요."
      }
    ]
  }
}
```

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`
- GitHub file content 조회 실패

### 7-2. Commit 코드 리뷰 조회

- 설명: 이미 생성된 commit 리뷰를 조회합니다.
- Method: `GET`
- URL: `/api/commits/{sha}/review`
- 인증 필요 여부: `예`
- 요청 파라미터:
  - `sha`: commit SHA
- 요청 body: 없음

#### 응답 예시

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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 COMMIT_NOT_FOUND`
- `404 COMMIT_REVIEW_NOT_FOUND`

---

## 8. Skill Map API

### 8-1. 저장소 Skill Map 조회

- 설명: 저장소의 문제 판정 데이터를 기반으로 영역별 알고리즘 Skill Map을 생성합니다.
- Method: `GET`
- URL: `/api/repositories/current/skill-map`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "repository Skill Map을 조회했습니다.",
  "data": {
    "domains": [
      {
        "name": "구현",
        "total": 2,
        "solved": 1,
        "possibly_solved": 0,
        "attempted": 1
      },
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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`

---

## 9. Recommendation API

### 9-1. 약점 기반 추천 생성

- 설명: Skill Map과 판정 결과를 기반으로 약한 토픽을 계산하고 외부 문제 추천을 생성해 DB에 저장합니다.
- Method: `POST`
- URL: `/api/repositories/current/recommendations/generate`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "약점 기반 추천 문제를 생성했습니다.",
  "data": {
    "weak_topics": ["문자열", "다이나믹프로그래밍", "이분탐색"],
    "recommendations": [
      {
        "title": "문자열 압축",
        "topic": "문자열",
        "url": "https://school.programmers.co.kr/learn/courses/30/lessons/60057",
        "source": "programmers",
        "reason": "문자열 유형의 solved 비율이 낮아 보강이 필요합니다."
      }
    ]
  }
}
```

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`

### 9-2. 저장된 추천 조회

- 설명: 현재 저장소에 저장된 추천 문제 목록과 현재 약점 토픽을 조회합니다.
- Method: `GET`
- URL: `/api/repositories/current/recommendations`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "저장된 추천 문제를 조회했습니다.",
  "data": {
    "weak_topics": ["문자열", "다이나믹프로그래밍", "이분탐색"],
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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`

---

## 10. Dashboard API

### 10-1. 대시보드 요약 조회

- 설명: 메인 대시보드에서 사용하는 핵심 요약 데이터를 반환합니다.
- Method: `GET`
- URL: `/api/dashboard/summary`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

```json
{
  "success": true,
  "message": "대시보드 요약 정보를 조회했습니다.",
  "data": {
    "status": "Watch",
    "solved_count": 25,
    "attempted_count": 40,
    "week_progress": 0.6,
    "last_synced_at": "2026-03-11T12:30:00+00:00",
    "skill_map": {
      "domains": [],
      "summary": {
        "attempted_count": 10,
        "possibly_solved_count": 15,
        "solved_count": 25,
        "total_count": 50
      }
    },
    "weak_topics": ["문자열", "다이나믹프로그래밍"],
    "recommendations": []
  }
}
```

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`

---

## 11. MyPage API

### 11-1. 마이페이지 분석 리포트 조회

- 설명: 마이페이지에서 사용하는 전체 분석 리포트를 반환합니다.
- Method: `GET`
- URL: `/api/mypage/report`
- 인증 필요 여부: `예`
- 요청 파라미터: 없음
- 요청 body: 없음

#### 응답 예시

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
    "status": "Watch",
    "solved_count": 25,
    "attempted_count": 40,
    "possibly_solved_count": 5,
    "week_progress": 0.6,
    "last_synced_at": "2026-03-11T12:30:00+00:00",
    "skill_map": {
      "domains": [],
      "summary": {
        "attempted_count": 10,
        "possibly_solved_count": 15,
        "solved_count": 25,
        "total_count": 50
      }
    },
    "ai_summary": "현재 상태는 Watch입니다. 주차 진행률은 60%, solved 비율은 38%이며, 우선 보강이 필요한 영역은 문자열, 다이나믹프로그래밍입니다.",
    "domain_analysis": [
      {
        "name": "탐색",
        "total": 8,
        "solved": 3,
        "status": "보강 필요",
        "solved_ratio": 0.38
      }
    ],
    "weak_topics": ["문자열", "다이나믹프로그래밍"],
    "weak_topic_ranking": [
      {
        "topic": "문자열",
        "score": 1.35,
        "solved_ratio": 0.2,
        "recent_count": 0,
        "total": 5,
        "solved": 1
      }
    ],
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

#### 에러 케이스

- `401 UNAUTHORIZED`
- `404 REPOSITORY_NOT_SELECTED`

---

## 부록: 현재 구현된 추가 API

요청하신 본문 목록 외에 현재 코드에 실제로 존재하는 API입니다.

### 로그아웃

- Method: `POST`
- URL: `/api/auth/logout`
- 인증 필요 여부: `아니오`
- 설명: 세션을 모두 비웁니다.

### 루트 헬스용 API

- Method: `GET`
- URL: `/`
- 인증 필요 여부: `아니오`
- 설명: API 서버 기본 상태를 반환합니다.

### 상세 commit 조회

- Method: `GET`
- URL: `/api/commits/{sha}`
- 인증 필요 여부: `예`
- 설명: DB에 저장된 특정 commit 상세 정보와 파일 목록을 반환합니다.

### 저장소 문제 판정 요약

- Method: `GET`
- URL: `/api/repositories/current/problem-summary`
- 인증 필요 여부: `예`
- 설명: 저장소 전체의 `attempted / possibly_solved / solved` 카운트를 반환합니다.

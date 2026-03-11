# 정글 알고리즘 학습 운영 대시보드 API

GitHub 저장소를 기준으로 과제 진행도, 이슈 상태, 커밋 분석, 풀이 판정, Skill Map, 추천 문제를 제공하는 Flask 백엔드입니다.

## 핵심 기능

- GitHub OAuth 로그인
- 분석 대상 저장소 선택
- GitHub issues / commits 동기화
- CSV 템플릿 기반 주차 과제 매칭
- commit 기반 풀이 분석 및 판정
- 알고리즘 Skill Map / 약점 분석 / 추천 문제 생성
- 대시보드 / 마이페이지 리포트 API 제공

## 코드 리뷰 기준

현재 커밋 리뷰는 Python 파일을 기준으로 다음 항목을 휴리스틱하게 분석합니다.

- 사용 알고리즘 추정
- 코드 구조 평가
- 예상 시간 복잡도 추정
- 개선 제안

리뷰 정확도를 높이기 위해 주석과 triple quote 형태의 문제 설명 문자열은 구조 평가와 복잡도 추정에서 제외합니다.

## 로컬 실행

```bash
python -m pip install -r requirements.txt
python run.py
```

기본 주소:

- 백엔드: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 환경 변수

`.env.example`를 복사해서 `.env`를 만든 뒤 값을 채워주세요.

```env
SECRET_KEY=change-me-for-local-dev

GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
GITHUB_REDIRECT_URI=http://127.0.0.1:5000/api/auth/github/callback
GITHUB_OAUTH_SCOPE=read:user

FRONTEND_OAUTH_SUCCESS_URL=http://127.0.0.1:3000/auth/callback
FRONTEND_OAUTH_FAILURE_URL=http://127.0.0.1:3000/login
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_SECURE=false

GITHUB_TOKEN=optional_github_token
REPO_OWNER=JYPark-Code
REPO_NAME=SW-AI-W02-05
```

## GitHub OAuth 로컬 테스트 방법

### 1. GitHub OAuth App 생성

GitHub에서 OAuth App을 만들고 아래처럼 설정합니다.

- Homepage URL: `http://127.0.0.1:3000`
- Authorization callback URL: `http://127.0.0.1:5000/api/auth/github/callback`

### 2. `.env` 설정

아래 값은 실제 GitHub OAuth App 값으로 채워야 합니다.

- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`
- `GITHUB_REDIRECT_URI`

### 3. FE 연동 방식

프론트엔드는 아래 흐름으로 붙이면 됩니다.

1. 브라우저를 `GET /api/auth/github/login?mode=redirect&next=http://127.0.0.1:3000/auth/callback`로 이동
2. 백엔드가 GitHub 로그인 화면으로 리다이렉트
3. 로그인 성공 후 GitHub가 백엔드 callback으로 복귀
4. 백엔드가 session을 만든 뒤 FE callback 페이지로 다시 리다이렉트
5. FE는 `credentials: "include"`로 `GET /api/auth/me` 호출
6. 로그인 사용자 정보를 받아 상태를 갱신

로그아웃은 `POST /api/auth/logout`를 `credentials: "include"`와 함께 호출하면 됩니다.

## 운영 규칙 반영

현재 백엔드는 아래 규칙을 기준으로 동작합니다.

- `week2`는 이미 반영된 상태로 간주
- `2026-03-13`부터 `week3`, 이후 매주 금요일마다 `week4`, `week5` 순으로 자동 전환
- 자동 추적 범위는 현재 `resources/csv`에 있는 `week2 ~ week5`
- `basic`, `common`은 필수 과제
- `problem-solving`은 기본적으로 필수 과제
- `problem-solving 상`, `Extra`는 선택 과제
- 이슈와 매칭되지 않은 별도 연습 커밋은 `extra_practice_count`로 분리 집계

## 테스트

```bash
python -m pytest -q
```

현재 기준 테스트 통과 수:

- `49 passed`

## 문서

- API 상세 문서: [API_REFERENCE.md](C:\jungle\openai\mini-hackathon-web\API_REFERENCE.md)

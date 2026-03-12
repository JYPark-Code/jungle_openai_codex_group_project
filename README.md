# 정글 알고리즘 학습 대시보드

GitHub 저장소의 이슈, 커밋, GitHub Project 상태를 바탕으로 알고리즘 학습 진행 현황을 시각화하는 Flask 기반 웹 애플리케이션입니다.

발표 시연에서는 다음 흐름을 한 번에 보여줄 수 있습니다.

1. GitHub OAuth 로그인
2. 분석 대상 저장소 선택
3. 이슈/커밋/Project 상태 동기화
4. 대시보드와 마이페이지에서 학습 통계 확인
5. 커밋 리뷰에서 문제 추적 결과와 코드 리뷰 확인

## 핵심 기능

- GitHub OAuth 로그인
- 분석 대상 저장소 선택 및 세션 유지
- GitHub Issues / Commits 동기화
- GitHub Project 상태 연동
- 커밋 기준 문제 추적과 판정 요약
- 영역별 통계, 약점 랭킹, 추천 문제 제공
- 커밋 리뷰 및 파일별 리뷰 코멘트 확인

## 현재 반영된 주요 기준

- 통계는 GitHub Project 상태를 최우선으로 반영합니다.
- `Done`은 해결, `In Progress`는 진행 중, `To-do`는 미해결로 처리합니다.
- 커밋 리뷰의 문제 추적 결과도 같은 기준을 따르도록 맞춰져 있습니다.
- `localhost`와 `127.0.0.1` 혼용으로 인한 OAuth `state mismatch`를 막기 위해 로컬 실행 기준 호스트를 `127.0.0.1`로 통일했습니다.

## 기술 스택

- Backend: Flask
- Database: SQLite
- Auth: GitHub OAuth
- Test: pytest

## 로컬 실행

```bash
python -m pip install -r requirements.txt
python run.py
```

기본 접속 주소:

- 웹 앱: [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)
- API 기준 주소: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 환경 변수

`.env.example`을 복사해 `.env`를 만든 뒤 값을 채워서 사용합니다.

```env
SECRET_KEY=change-me-for-local-dev

GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
GITHUB_REDIRECT_URI=http://127.0.0.1:5000/auth/github/callback
GITHUB_OAUTH_SCOPE=read:user

FRONTEND_OAUTH_SUCCESS_URL=http://127.0.0.1:3000/auth/callback
FRONTEND_OAUTH_FAILURE_URL=http://127.0.0.1:3000/login
CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000

SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_SECURE=false

GITHUB_TOKEN=optional_github_token
REPO_OWNER=JYPark-Code
REPO_NAME=SW-AI-W02-05
```

## GitHub OAuth 설정

GitHub OAuth App에서 아래처럼 맞추면 됩니다.

- Homepage URL: `http://127.0.0.1:5000/login` 또는 프런트 앱 주소
- Authorization callback URL: `http://127.0.0.1:5000/auth/github/callback`

주의:

- 로컬 시연 시 `localhost` 대신 `127.0.0.1`로 접속하는 것을 권장합니다.
- OAuth callback URL과 실제 접속 호스트가 섞이면 로그인 세션이 끊길 수 있습니다.

## 발표 시연 추천 흐름

1. `http://127.0.0.1:5000/login` 접속
2. GitHub 로그인
3. 저장소 선택
4. 동기화 실행
5. 대시보드에서 전체 진행 상황 확인
6. 마이페이지에서 영역별 상세, 약점 랭킹, 추천 문제 확인
7. 커밋 리뷰에서 문제 추적 결과와 리뷰 내용 확인

## 배포 관련 메모

- 현재 구조는 `Flask + SQLite` 기반이므로 가장 안정적인 시연 방식은 로컬 실행입니다.
- 발표용 단기 데모 배포는 가능하지만, 운영 환경에서는 SQLite보다 Postgres 같은 서버형 DB가 더 적합합니다.
- OAuth UX를 안정적으로 제공하려면 배포 환경에서도 고정된 도메인과 callback URL을 사용하는 것이 좋습니다.

## 테스트

```bash
python -m pytest -q
```

현재 기준 전체 테스트 통과:

- `92 passed`

## 문서

- API 문서: `API_REFERENCE.md`

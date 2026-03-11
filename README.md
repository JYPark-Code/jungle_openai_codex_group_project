# 정글 알고리즘 학습 운영 대시보드 API

정글 알고리즘 학습 운영 대시보드의 백엔드 API 프로젝트입니다.  
GitHub 저장소를 기준으로 주차별 과제 진행도, 이슈 누락 여부, commit 기반 풀이 분석, 풀이 판정, 알고리즘 Skill Map, 약점 기반 추천, 대시보드/마이페이지 리포트를 제공합니다.

## 핵심 기능

- GitHub OAuth 로그인
- 분석 대상 GitHub 저장소 선택
- GitHub issues / commits 동기화
- CSV 템플릿 기반 주차별 과제 issue 매칭 및 누락 issue 생성
- commit 기반 파일 분석 및 풀이 판정
- 알고리즘 taxonomy 기반 Skill Map 분석
- 약점 유형 기반 외부 문제 추천
- 대시보드 요약 API
- 마이페이지 분석 리포트 API

## 현재 기술 스택

- Backend: Flask
- Database: SQLite
- Test: pytest
- External API: GitHub REST API

## 디렉토리 구조

```text
mini-hackathon-web/
├─ app/
│  ├─ models/
│  ├─ routes/
│  ├─ services/
│  └─ utils/
├─ resources/
│  └─ csv/
├─ tests/
├─ API_REFERENCE.md
├─ config.py
├─ pytest.ini
├─ requirements.txt
└─ run.py
```

## 실행 방법

```bash
python -m pip install -r requirements.txt
python run.py
```

기본 실행 주소:

- [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 환경변수

실행 전 `.env` 파일을 준비해야 합니다.  
`.env.example`은 필요한 환경변수 이름을 공유하기 위한 예시 파일로 유지하는 것을 권장합니다.

예시:

```env
SECRET_KEY=your_secret_key
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
GITHUB_REDIRECT_URI=http://127.0.0.1:5000/api/auth/github/callback
GITHUB_OAUTH_SCOPE=read:user
GITHUB_TOKEN=optional_github_token
REPO_OWNER=JYPark-Code
REPO_NAME=SW-AI-W02-05
```

설명:

- `SECRET_KEY`: Flask session 서명용
- `GITHUB_CLIENT_ID`: GitHub OAuth 앱 Client ID
- `GITHUB_CLIENT_SECRET`: GitHub OAuth 앱 Client Secret
- `GITHUB_REDIRECT_URI`: GitHub OAuth callback URL
- `GITHUB_OAUTH_SCOPE`: 기본 OAuth scope
- `GITHUB_TOKEN`: 일부 개발/운영용 GitHub API 호출용
- `REPO_OWNER`, `REPO_NAME`: 기본 저장소 설정값

## API 개요

주요 API 범위:

- 인증
  - `/api/auth/github/login`
  - `/api/auth/github/callback`
  - `/api/auth/me`
- 저장소
  - `/api/repositories`
  - `/api/repositories/select`
  - `/api/repositories/current`
- 동기화
  - `/api/repositories/current/sync`
  - `/api/repositories/current/sync-status`
- 이슈 템플릿
  - `/api/issues/template-status`
  - `/api/issues/create-missing`
- commit 분석 / 판정 / 리뷰
  - `/api/commits`
  - `/api/commits/{sha}/analyze-files`
  - `/api/commits/{sha}/judge`
  - `/api/commits/{sha}/judge-result`
  - `/api/commits/{sha}/review`
  - `/api/commits/{sha}/review`
- Skill Map / 추천 / 리포트
  - `/api/repositories/current/skill-map`
  - `/api/repositories/current/recommendations/generate`
  - `/api/repositories/current/recommendations`
  - `/api/dashboard/summary`
  - `/api/mypage/report`

상세 스펙은 [API_REFERENCE.md](C:\jungle\openai\mini-hackathon-web\API_REFERENCE.md) 문서를 참고하면 됩니다.

## 테스트 실행

```bash
python -m pytest -q
```

현재 프로젝트에는 아래 테스트가 포함되어 있습니다.

- OAuth 로그인 테스트
- 저장소 선택/조회 테스트
- GitHub 동기화 테스트
- CSV 이슈 템플릿 테스트
- commit 판정 테스트
- Skill Map / 코드 리뷰 테스트
- 추천 로직 테스트
- 대시보드 / 마이페이지 리포트 테스트

## 발표 관점 요약

이 프로젝트는 단순 문제 생성기가 아니라, GitHub 저장소를 학습 운영 데이터의 원본으로 사용해 학습 상태를 한 곳에서 보여주는 운영 대시보드입니다.

주요 데모 흐름:

1. GitHub OAuth 로그인
2. 분석할 저장소 선택
3. issues / commits 동기화
4. CSV 템플릿 기준 과제 누락 확인
5. commit 분석 및 풀이 판정
6. Skill Map과 약점 분석 확인
7. 추천 문제 및 마이페이지 리포트 확인

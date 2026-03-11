# 정글 알고리즘 학습 운영 대시보드 API

정글 알고리즘 학습 운영 대시보드의 백엔드 API 프로젝트입니다.

이 서비스는 GitHub 저장소를 기준으로 아래 흐름을 지원합니다.

- GitHub OAuth 로그인
- 분석 대상 저장소 선택
- Issues / Commits 동기화
- CSV 템플릿 기반 주차별 과제 관리
- Commit 기반 풀이 분석 및 판정
- 알고리즘 Skill Map 생성
- 약점 기반 추천 문제 제공
- 대시보드 / 마이페이지 리포트 제공

## 운영 규칙 반영 범위

현재 백엔드는 정글 운영 규칙 1차를 반영하고 있습니다.

- `week2`는 이미 반영된 상태로 간주
- `2026-03-13 금요일`부터 `week3` 활성화
- 이후 매주 금요일마다 `week4`, `week5`로 자동 전환
- 현재 자동 추적 범위는 `resources/csv`에 있는 `week2~week5`까지만 포함
- `basic`, `common` 항목은 필수 과제
- `problem-solving`은 기본적으로 필수 과제
- `problem-solving 상`, `Extra`는 선택 과제
- 이슈와 매칭되지 않은 임의 연습 commit은 `extra_practice_count`로 별도 집계
- 현재 주차 GitHub Project 추적 메타데이터 저장 지원

현재 제외된 범위:

- GitHub Project 실제 자동 생성
- 백준 예제 입력/출력 기반 solved 최종 판정
- week6 이후 다른 레포 운영 일정

## 기술 스택

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

`.env.example`을 참고해서 `.env`를 구성하면 됩니다.

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

주요 값 설명:

- `SECRET_KEY`: Flask session 서명용
- `GITHUB_CLIENT_ID`: GitHub OAuth 앱 Client ID
- `GITHUB_CLIENT_SECRET`: GitHub OAuth 앱 Client Secret
- `GITHUB_REDIRECT_URI`: GitHub OAuth callback URL
- `GITHUB_OAUTH_SCOPE`: 기본 OAuth scope
- `GITHUB_TOKEN`: 일부 운영/관리성 GitHub API 호출용
- `REPO_OWNER`, `REPO_NAME`: 기본 저장소 설정값

주차는 수동 환경변수로 넣지 않습니다. 서버 날짜 기준으로 자동 판정합니다.

## 주요 API 범위

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
- Skill Map / 추천 / 리포트
  - `/api/repositories/current/skill-map`
  - `/api/repositories/current/recommendations/generate`
  - `/api/repositories/current/recommendations`
  - `/api/dashboard/summary`
  - `/api/mypage/report`
- 운영용 Project 추적
  - `/api/repositories/current/projects/track`
  - `/api/repositories/current/projects/current`

상세 명세는 [API_REFERENCE.md](C:\jungle\openai\mini-hackathon-web\API_REFERENCE.md)를 참고하면 됩니다.

## 테스트 실행

```bash
python -m pytest -q
```

현재 포함된 테스트:

- OAuth 로그인 테스트
- 저장소 선택/조회 테스트
- GitHub 동기화 테스트
- CSV 템플릿 이슈 테스트
- Commit 판정 테스트
- Skill Map / 코드 리뷰 테스트
- 추천 로직 테스트
- 리포트 테스트
- 운영 규칙 반영 테스트

## 데모 흐름 예시

1. GitHub OAuth 로그인
2. 분석 대상 저장소 선택
3. Issues / Commits 동기화
4. 현재 주차 기준 필수 과제 진행률 확인
5. 누락 필수 이슈 생성
6. Commit 분석 및 풀이 판정
7. Skill Map과 약점 영역 확인
8. 추천 문제 및 마이페이지 리포트 확인

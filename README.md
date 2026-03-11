# 깃허브 알고리즘 스터디 도우미

깃허브 알고리즘 스터디 도우미는 학생이 알고리즘 학습 주제를 입력하면 연습 문제를 만들고, 이를 GitHub 이슈로 등록하며, 저장소에 커밋된 Python 풀이 코드를 분석해 다음 학습 방향까지 추천해주는 해커톤 MVP입니다.

## 프로젝트 한 줄 소개

알고리즘 스터디 저장소를 기반으로 현재 학습 상태를 빠르게 진단하고, 다음에 풀어야 할 문제를 바로 제안하는 학습 보조 웹 서비스입니다.

## 해결하려는 문제

- 알고리즘 공부를 할 때 어떤 주제를 먼저 연습해야 할지 판단하기 어렵습니다.
- 문제를 따로 정리하고 GitHub 이슈로 등록하는 과정이 번거롭습니다.
- 내가 이미 어떤 유형을 많이 풀었고, 어떤 유형이 비어 있는지 한눈에 보기 어렵습니다.

## 핵심 기능

### 1. 알고리즘 연습 문제 생성

- 사용자가 `recursion`, `backtracking`, `graph`, `dp` 같은 주제를 입력합니다.
- 서버가 미리 정의된 템플릿을 기반으로 연습 문제를 생성합니다.
- 생성된 문제는 제목과 설명이 함께 표시됩니다.

### 2. GitHub 이슈 자동 생성

- `.env`에 설정한 `REPO_OWNER`, `REPO_NAME`, `GITHUB_TOKEN`을 사용합니다.
- 생성된 연습 문제를 지정한 GitHub 저장소의 이슈로 바로 등록합니다.
- 화면에서 각 문제별 이슈 생성 결과, 이슈 번호, 이슈 링크를 확인할 수 있습니다.

### 3. 저장소 풀이 분석

- 연결된 GitHub 저장소의 Python 파일을 읽어 간단한 정적 분석을 수행합니다.
- 재귀, 백트래킹, 그래프, BFS, DFS, 동적 계획법, 완전탐색, 이분 탐색 패턴을 휴리스틱으로 감지합니다.
- 감지된 주제, 부족한 주제, 짧은 분석 코멘트, 다음 추천 주제와 추천 문제를 보여줍니다.

## 발표용 데모 흐름

1. 메인 화면에서 알고리즘 주제를 입력합니다.
2. 연습 문제를 생성하고 GitHub 이슈 생성 결과를 확인합니다.
3. 저장소 풀이 분석 버튼을 눌러 현재 저장소의 학습 패턴을 확인합니다.
4. 부족한 주제와 다음 추천 문제를 보며 학습 방향을 설명합니다.

## 기술 스택

- Backend: Flask
- Frontend: Jinja2 템플릿 기반 서버 사이드 렌더링
- API: GitHub REST API
- 분석 대상: Python 파일
- 데이터 저장: 별도 데이터베이스 없음

## 폴더 구조

```text
mini-hackathon-web/
├─ app.py
├─ requirements.txt
├─ .env.example
├─ services/
│  ├─ github_service.py
│  ├─ problem_generator.py
│  └─ code_review.py
├─ templates/
│  ├─ base.html
│  └─ index.html
└─ README.md
```

## 실행 방법

```bash
python -m pip install -r requirements.txt
python run.py
```

실행 후 브라우저에서 아래 주소로 접속합니다.

- [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 환경 변수 설정

`.env.example`를 참고해 `.env` 파일을 만들고 아래 값을 설정합니다.

```env
GITHUB_TOKEN=your_github_token_here
REPO_OWNER=JYPark-Code
REPO_NAME=SW-AI-W02-05
```

또는 다음과 같이 `owner/repo` 형식으로도 사용할 수 있습니다.

```env
GITHUB_TOKEN=your_github_token_here
REPO_NAME=JYPark-Code/SW-AI-W02-05
```

## GitHub 토큰 안내

- classic token을 사용하는 경우 `repo` 권한이 필요합니다.
- 이 앱은 저장소 조회, Python 파일 읽기, 이슈 생성을 위해 GitHub API를 사용합니다.

## 테스트 실행 방법

```bash
python -m pytest
```

현재는 API 서버 스모크 테스트와 공통 에러 응답 테스트가 포함되어 있습니다.

## 기대 효과

- 알고리즘 학습을 GitHub 저장소 중심으로 정리할 수 있습니다.
- 현재까지 푼 문제의 유형을 빠르게 파악할 수 있습니다.
- 부족한 주제를 기반으로 다음 학습 문제를 자연스럽게 추천받을 수 있습니다.

## 현재 MVP 범위

- 문제 생성
- GitHub 이슈 생성
- 저장소 Python 풀이 분석
- 다음 학습 주제 및 추천 문제 제안

복잡한 인증 화면, 데이터베이스, 고급 코드 리뷰, 실시간 기능은 이번 MVP 범위에서 제외했습니다.

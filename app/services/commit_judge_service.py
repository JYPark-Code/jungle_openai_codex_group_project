import json
import re
from pathlib import Path

from app.models.db import (
    clear_problem_judgements_for_commit,
    get_commit_by_sha,
    get_issues_by_repository_id,
    get_problem_judgements_by_commit_id,
    list_problem_judgements_by_repository_id,
    now_iso,
    save_commit,
    save_problem_judgement,
    update_commit_files,
)
from app.services.github_service import fetch_commit_changed_files
from app.services.reporting_judgement_service import build_reporting_issue_entries, summarize_judgement_statuses
from app.utils.errors import ApiError


GENERIC_MATCH_TOKENS = {
    "basic",
    "extra",
    "common",
    "problem",
    "solving",
    "problem-solving",
    "week",
    "week2",
    "week3",
    "week4",
    "week5",
    "연습문제",
    "난이도상",
    "난이도중",
    "난이도하",
    "파이썬",
    "문법",
    "배열",
    "문자열",
    "완전탐색",
    "재귀함수",
    "백트래킹",
    "정렬",
    "정수론",
    "구현",
    "그래프",
    "bfs",
    "dfs",
}


def list_repository_commits(repository_id: int) -> list[dict]:
    from app.models.db import list_commits_by_repository_id

    return list_commits_by_repository_id(repository_id)


def get_commit_detail(repository_id: int, sha: str) -> dict:
    commit = get_commit_by_sha(repository_id, sha)
    if not commit:
        raise ApiError("COMMIT_NOT_FOUND", "요청한 commit 정보를 찾을 수 없습니다.", 404)

    files = []
    raw_files = commit.get("files_json") or "[]"
    try:
        files = json.loads(raw_files)
    except json.JSONDecodeError:
        files = []

    return {
        **commit,
        "files": files,
    }


def judge_commit_files(repository: dict, sha: str, access_token: str) -> dict:
    commit_payload = fetch_commit_changed_files(repository["owner"], repository["name"], sha, access_token)
    commit_id, _created = save_commit(
        repository_id=repository["id"],
        sha=commit_payload["sha"],
        message=commit_payload["message"],
        author_name=commit_payload["author_name"],
        committed_at=commit_payload["committed_at"],
    )

    files = commit_payload["files"]
    analyzed_at = now_iso()
    update_commit_files(repository["id"], sha, files, analyzed_at=analyzed_at)

    python_files = [item for item in files if item.get("filename", "").endswith(".py")]
    issues = get_issues_by_repository_id(repository["id"])

    clear_problem_judgements_for_commit(commit_id)

    matched_problem_results = []
    attempted_count = 0
    possibly_solved_count = 0
    solved_count = 0

    for file_info in python_files:
        filename = file_info["filename"]
        best_match = match_issue_by_filename(filename, issues)
        status = evaluate_problem_status(
            has_related_file=True,
            strong_title_match=best_match["is_strong_match"],
            execution_passed=False,
            sample_output_matched=False,
        )

        save_problem_judgement(
            repository_id=repository["id"],
            commit_id=commit_id,
            issue_number=best_match["issue"]["issue_number"] if best_match["issue"] else None,
            problem_key=best_match["issue"]["title"] if best_match["issue"] else Path(filename).name,
            file_path=filename,
            judgement_status=status,
            match_score=best_match["score"],
            matched_by_filename=best_match["is_strong_match"],
            execution_passed=False,
            sample_output_matched=False,
            notes=best_match["reason"],
        )

        matched_problem_results.append(
            {
                "file_path": filename,
                "normalized_filename": normalize_problem_filename(filename),
                "matched_issue_title": best_match["issue"]["title"] if best_match["issue"] else None,
                "issue_number": best_match["issue"]["issue_number"] if best_match["issue"] else None,
                "match_score": best_match["score"],
                "judgement_status": status,
            }
        )

        if status == "attempted":
            attempted_count += 1
        elif status == "possibly_solved":
            possibly_solved_count += 1
        elif status == "solved":
            solved_count += 1

    return {
        "commit_sha": sha,
        "analyzed_at": analyzed_at,
        "analyzed_file_count": len(files),
        "python_file_count": len(python_files),
        "matched_problems": matched_problem_results,
        "attempted_count": attempted_count,
        "possibly_solved_count": possibly_solved_count,
        "solved_count": solved_count,
    }


def get_commit_judge_result(repository_id: int, sha: str) -> dict:
    commit = get_commit_by_sha(repository_id, sha)
    if not commit:
        raise ApiError("COMMIT_NOT_FOUND", "요청한 commit 정보를 찾을 수 없습니다.", 404)

    judgements = get_problem_judgements_by_commit_id(commit["id"])
    summary = summarize_judgements(judgements)
    return {
        "commit_sha": sha,
        "results": judgements,
        **summary,
    }


def get_repository_problem_summary(repository_id: int) -> dict:
    issues = get_issues_by_repository_id(repository_id)
    tracked_entries, extras = build_reporting_issue_entries(
        issues,
        list_problem_judgements_by_repository_id(repository_id),
        match_issue_by_filename,
    )
    return summarize_judgement_statuses(tracked_entries + extras)


def normalize_problem_filename(file_path: str) -> str:
    stem = Path(file_path).stem
    raw_tokens = [token for token in re.split(r"[_\-\s]+", stem) if token]
    cleaned_tokens = []

    for index, token in enumerate(raw_tokens):
        lowered = token.casefold()
        if index == 0 and (
            lowered.startswith("week")
            or lowered.startswith("basic")
            or lowered.startswith("common")
            or lowered.startswith("extra")
            or "난이도" in token
            or "연습문제" in token
        ):
            continue
        if lowered == "문제":
            continue

        token = re.sub(
            r"(백준|leetcode|리트코드|브론즈|실버|골드|플래|플래티넘)\d*$",
            "",
            token,
            flags=re.IGNORECASE,
        )
        token = re.sub(r"^\d+|\d+$", "", token)
        token = token.strip()
        if token:
            cleaned_tokens.append(token)

    normalized = " ".join(cleaned_tokens)
    normalized = re.sub(r"\s+", " ", normalized).strip().casefold()
    return normalized


def normalize_issue_title(title: str) -> str:
    normalized = re.sub(r"\s+", " ", title.strip()).casefold()
    normalized = re.sub(r"^\[(week\s*\d+|w\d+)\]\s*", "", normalized, flags=re.IGNORECASE)
    normalized = normalized.replace("공통 - ", "").replace("basic - ", "").replace("extra - ", "")
    normalized = re.sub(r"^(난이도상|난이도중|난이도하)[_\-\s]+", "", normalized)
    return normalized


def match_issue_by_filename(file_path: str, issues: list[dict]) -> dict:
    normalized_filename = normalize_problem_filename(file_path)
    filename_tokens = set(_tokenize_for_matching(normalized_filename))
    compact_filename = _compact_for_matching(normalized_filename)

    best_issue = None
    best_score = 0.0
    best_reason = "연관된 issue를 찾지 못했습니다."

    for issue in issues:
        normalized_title = normalize_issue_title(issue["title"])
        title_tokens = set(_tokenize_for_matching(normalized_title))
        compact_title = _compact_for_matching(normalized_title)
        if not title_tokens:
            continue

        intersection_count = len(filename_tokens & title_tokens)
        denominator = max(len(filename_tokens), len(title_tokens), 1)
        score = intersection_count / denominator
        meaningful_overlap = {
            token for token in (filename_tokens & title_tokens)
            if token not in GENERIC_MATCH_TOKENS
        }

        if compact_filename and compact_filename == compact_title:
            score = 1.0
        elif compact_filename and compact_title and (
            compact_filename in compact_title or compact_title in compact_filename
        ):
            score = max(score, 0.85)
        elif not meaningful_overlap:
            score = min(score, 0.15)
        else:
            score = max(score, 0.45 + (0.15 * min(len(meaningful_overlap), 2)))

        if score > best_score:
            best_score = score
            best_issue = issue
            best_reason = f"title 토큰 유사도 {score:.2f}로 매칭했습니다."

    if best_score < 0.45:
        return {
            "issue": None,
            "score": round(best_score, 2),
            "is_strong_match": False,
            "reason": "파일명과 issue 제목의 의미 있는 겹침이 부족해 자동 매칭하지 않았습니다.",
        }

    return {
        "issue": best_issue,
        "score": round(best_score, 2),
        "is_strong_match": best_score >= 0.6,
        "reason": best_reason,
    }


def evaluate_problem_status(
    has_related_file: bool,
    strong_title_match: bool,
    execution_passed: bool,
    sample_output_matched: bool,
) -> str:
    if strong_title_match and execution_passed and sample_output_matched:
        return "solved"
    if has_related_file and strong_title_match:
        return "possibly_solved"
    if has_related_file:
        return "attempted"
    return "attempted"


def summarize_judgements(judgements: list[dict]) -> dict:
    summary = {
        "attempted_count": 0,
        "possibly_solved_count": 0,
        "solved_count": 0,
    }
    for item in judgements:
        if item["judgement_status"] == "attempted":
            summary["attempted_count"] += 1
        elif item["judgement_status"] == "possibly_solved":
            summary["possibly_solved_count"] += 1
        elif item["judgement_status"] == "solved":
            summary["solved_count"] += 1
    return summary


def _tokenize_for_matching(value: str) -> list[str]:
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", " ", value)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return [_compact_for_matching(token) for token in normalized.split(" ") if _compact_for_matching(token)]


def _compact_for_matching(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", value).casefold()

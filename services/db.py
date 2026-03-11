import json
import os
import sqlite3
from datetime import datetime, timezone

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS github_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_user_id TEXT UNIQUE,
    login TEXT NOT NULL,
    name TEXT,
    avatar_url TEXT,
    access_token_ref TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_repo_id TEXT,
    owner_login TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    full_name TEXT NOT NULL UNIQUE,
    default_branch TEXT,
    selected_by_user_id INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (selected_by_user_id) REFERENCES github_users (id)
);

CREATE TABLE IF NOT EXISTS issue_sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    week_label TEXT,
    source_csv_path TEXT,
    requested_count INTEGER NOT NULL DEFAULT 0,
    created_count INTEGER NOT NULL DEFAULT 0,
    missing_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    summary_json TEXT,
    synced_at TEXT NOT NULL,
    FOREIGN KEY (repository_id) REFERENCES repositories (id)
);

CREATE TABLE IF NOT EXISTS commit_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    github_commit_sha TEXT NOT NULL UNIQUE,
    author_login TEXT,
    commit_message TEXT,
    committed_at TEXT,
    file_count INTEGER NOT NULL DEFAULT 0,
    files_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (repository_id) REFERENCES repositories (id)
);

CREATE TABLE IF NOT EXISTS commit_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_id INTEGER NOT NULL UNIQUE,
    review_summary TEXT,
    review_comments_json TEXT,
    execution_status TEXT,
    execution_output_json TEXT,
    detected_topics_json TEXT,
    analyzed_at TEXT NOT NULL,
    FOREIGN KEY (commit_id) REFERENCES commit_metadata (id)
);

CREATE TABLE IF NOT EXISTS problem_judgements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    commit_id INTEGER,
    issue_number INTEGER,
    problem_key TEXT NOT NULL,
    file_path TEXT,
    judgement_status TEXT NOT NULL,
    matched_by_filename INTEGER NOT NULL DEFAULT 0,
    execution_passed INTEGER NOT NULL DEFAULT 0,
    sample_output_matched INTEGER NOT NULL DEFAULT 0,
    judged_at TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (repository_id) REFERENCES repositories (id),
    FOREIGN KEY (commit_id) REFERENCES commit_metadata (id)
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    report_scope TEXT NOT NULL,
    solved_count INTEGER NOT NULL DEFAULT 0,
    attempted_count INTEGER NOT NULL DEFAULT 0,
    status_label TEXT,
    summary_text TEXT,
    topic_breakdown_json TEXT,
    weak_topics_json TEXT,
    generated_at TEXT NOT NULL,
    FOREIGN KEY (repository_id) REFERENCES repositories (id)
);

CREATE TABLE IF NOT EXISTS recommendation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    report_id INTEGER,
    topic TEXT NOT NULL,
    source_site TEXT,
    problem_title TEXT NOT NULL,
    problem_url TEXT NOT NULL,
    reason TEXT,
    recommended_at TEXT NOT NULL,
    FOREIGN KEY (repository_id) REFERENCES repositories (id),
    FOREIGN KEY (report_id) REFERENCES analysis_reports (id)
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        database_path = current_app.config["DATABASE"]
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        connection = sqlite3.connect(database_path)
        connection.row_factory = dict_factory
        g.db = connection
    return g.db


def close_db(_error=None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    connection = get_db()
    connection.executescript(SCHEMA)
    connection.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def upsert_github_user(
    github_user_id: str,
    login: str,
    name: str = "",
    avatar_url: str = "",
    access_token_ref: str = "",
) -> int:
    connection = get_db()
    timestamp = now_iso()
    connection.execute(
        """
        INSERT INTO github_users (
            github_user_id, login, name, avatar_url, access_token_ref, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(github_user_id) DO UPDATE SET
            login = excluded.login,
            name = excluded.name,
            avatar_url = excluded.avatar_url,
            access_token_ref = excluded.access_token_ref,
            updated_at = excluded.updated_at
        """,
        (github_user_id, login, name, avatar_url, access_token_ref, timestamp, timestamp),
    )
    connection.commit()
    row = connection.execute(
        "SELECT id FROM github_users WHERE github_user_id = ?",
        (github_user_id,),
    ).fetchone()
    return row["id"]


def upsert_repository(
    owner_login: str,
    repo_name: str,
    github_repo_id: str = "",
    default_branch: str = "",
    selected_by_user_id: int | None = None,
) -> int:
    connection = get_db()
    timestamp = now_iso()
    full_name = f"{owner_login}/{repo_name}"
    connection.execute(
        """
        INSERT INTO repositories (
            github_repo_id, owner_login, repo_name, full_name, default_branch,
            selected_by_user_id, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(full_name) DO UPDATE SET
            github_repo_id = excluded.github_repo_id,
            default_branch = excluded.default_branch,
            selected_by_user_id = excluded.selected_by_user_id,
            is_active = 1,
            updated_at = excluded.updated_at
        """,
        (
            github_repo_id,
            owner_login,
            repo_name,
            full_name,
            default_branch,
            selected_by_user_id,
            timestamp,
            timestamp,
        ),
    )
    connection.commit()
    row = connection.execute(
        "SELECT id FROM repositories WHERE full_name = ?",
        (full_name,),
    ).fetchone()
    return row["id"]


def record_issue_sync_result(
    repository_id: int,
    week_label: str,
    source_csv_path: str,
    requested_count: int,
    created_count: int,
    missing_count: int,
    status: str,
    summary: dict | None = None,
) -> int:
    connection = get_db()
    cursor = connection.execute(
        """
        INSERT INTO issue_sync_runs (
            repository_id, week_label, source_csv_path, requested_count,
            created_count, missing_count, status, summary_json, synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            repository_id,
            week_label,
            source_csv_path,
            requested_count,
            created_count,
            missing_count,
            status,
            json.dumps(summary or {}, ensure_ascii=False),
            now_iso(),
        ),
    )
    connection.commit()
    return cursor.lastrowid


def save_commit_metadata(
    repository_id: int,
    github_commit_sha: str,
    author_login: str = "",
    commit_message: str = "",
    committed_at: str = "",
    files: list | None = None,
) -> int:
    connection = get_db()
    cursor = connection.execute(
        """
        INSERT INTO commit_metadata (
            repository_id, github_commit_sha, author_login, commit_message,
            committed_at, file_count, files_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(github_commit_sha) DO UPDATE SET
            author_login = excluded.author_login,
            commit_message = excluded.commit_message,
            committed_at = excluded.committed_at,
            file_count = excluded.file_count,
            files_json = excluded.files_json
        """,
        (
            repository_id,
            github_commit_sha,
            author_login,
            commit_message,
            committed_at,
            len(files or []),
            json.dumps(files or [], ensure_ascii=False),
            now_iso(),
        ),
    )
    connection.commit()
    if cursor.lastrowid:
        return cursor.lastrowid
    row = connection.execute(
        "SELECT id FROM commit_metadata WHERE github_commit_sha = ?",
        (github_commit_sha,),
    ).fetchone()
    return row["id"]


def save_commit_analysis(
    commit_id: int,
    review_summary: str = "",
    review_comments: list | None = None,
    execution_status: str = "",
    execution_output: dict | None = None,
    detected_topics: list | None = None,
) -> int:
    connection = get_db()
    cursor = connection.execute(
        """
        INSERT INTO commit_analysis_results (
            commit_id, review_summary, review_comments_json, execution_status,
            execution_output_json, detected_topics_json, analyzed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(commit_id) DO UPDATE SET
            review_summary = excluded.review_summary,
            review_comments_json = excluded.review_comments_json,
            execution_status = excluded.execution_status,
            execution_output_json = excluded.execution_output_json,
            detected_topics_json = excluded.detected_topics_json,
            analyzed_at = excluded.analyzed_at
        """,
        (
            commit_id,
            review_summary,
            json.dumps(review_comments or [], ensure_ascii=False),
            execution_status,
            json.dumps(execution_output or {}, ensure_ascii=False),
            json.dumps(detected_topics or [], ensure_ascii=False),
            now_iso(),
        ),
    )
    connection.commit()
    return cursor.lastrowid or commit_id


def save_problem_judgement(
    repository_id: int,
    problem_key: str,
    judgement_status: str,
    commit_id: int | None = None,
    issue_number: int | None = None,
    file_path: str = "",
    matched_by_filename: bool = False,
    execution_passed: bool = False,
    sample_output_matched: bool = False,
    notes: str = "",
) -> int:
    connection = get_db()
    cursor = connection.execute(
        """
        INSERT INTO problem_judgements (
            repository_id, commit_id, issue_number, problem_key, file_path,
            judgement_status, matched_by_filename, execution_passed,
            sample_output_matched, judged_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            repository_id,
            commit_id,
            issue_number,
            problem_key,
            file_path,
            judgement_status,
            int(matched_by_filename),
            int(execution_passed),
            int(sample_output_matched),
            now_iso(),
            notes,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def save_analysis_report(
    repository_id: int,
    report_scope: str,
    solved_count: int,
    attempted_count: int,
    status_label: str,
    summary_text: str,
    topic_breakdown: dict | None = None,
    weak_topics: list | None = None,
) -> int:
    connection = get_db()
    cursor = connection.execute(
        """
        INSERT INTO analysis_reports (
            repository_id, report_scope, solved_count, attempted_count,
            status_label, summary_text, topic_breakdown_json, weak_topics_json, generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            repository_id,
            report_scope,
            solved_count,
            attempted_count,
            status_label,
            summary_text,
            json.dumps(topic_breakdown or {}, ensure_ascii=False),
            json.dumps(weak_topics or [], ensure_ascii=False),
            now_iso(),
        ),
    )
    connection.commit()
    return cursor.lastrowid


def save_recommendation_history(
    repository_id: int,
    topic: str,
    problem_title: str,
    problem_url: str,
    source_site: str = "",
    reason: str = "",
    report_id: int | None = None,
) -> int:
    connection = get_db()
    cursor = connection.execute(
        """
        INSERT INTO recommendation_history (
            repository_id, report_id, topic, source_site, problem_title,
            problem_url, reason, recommended_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            repository_id,
            report_id,
            topic,
            source_site,
            problem_title,
            problem_url,
            reason,
            now_iso(),
        ),
    )
    connection.commit()
    return cursor.lastrowid

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_user_id TEXT UNIQUE,
    github_login TEXT NOT NULL,
    github_name TEXT,
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
    last_synced_at TEXT,
    FOREIGN KEY (selected_by_user_id) REFERENCES users (id)
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

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    github_issue_id TEXT NOT NULL,
    issue_number INTEGER,
    title TEXT NOT NULL,
    body TEXT,
    state TEXT NOT NULL,
    project_status TEXT,
    github_created_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(repository_id, github_issue_id),
    FOREIGN KEY (repository_id) REFERENCES repositories (id)
);

CREATE TABLE IF NOT EXISTS commit_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    github_commit_sha TEXT NOT NULL UNIQUE,
    author_login TEXT,
    commit_message TEXT,
    committed_at TEXT,
    analyzed_at TEXT,
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
    match_score REAL NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS github_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    week_label TEXT NOT NULL,
    project_title TEXT NOT NULL,
    project_url TEXT,
    project_number TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (repository_id) REFERENCES repositories (id)
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        database_path = current_app.config["DATABASE"]
        database_dir = os.path.dirname(database_path)
        if database_dir:
            os.makedirs(database_dir, exist_ok=True)
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
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    _ensure_legacy_columns(connection)
    connection.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def database_health() -> bool:
    try:
        get_db().execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False


def get_table_names() -> list[str]:
    rows = get_db().execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def upsert_user(
    github_user_id: str,
    github_login: str,
    github_name: str = "",
) -> int:
    connection = get_db()
    timestamp = now_iso()
    connection.execute(
        """
        INSERT INTO users (
            github_user_id, github_login, github_name, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(github_user_id) DO UPDATE SET
            github_login = excluded.github_login,
            github_name = excluded.github_name,
            updated_at = excluded.updated_at
        """,
        (github_user_id, github_login, github_name, timestamp, timestamp),
    )
    connection.commit()
    return connection.execute(
        "SELECT id FROM users WHERE github_user_id = ?",
        (github_user_id,),
    ).fetchone()["id"]


def get_user_by_id(user_id: int) -> dict | None:
    return get_db().execute(
        """
        SELECT id, github_user_id, github_login, github_name, created_at, updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


def get_user_by_github_user_id(github_user_id: str) -> dict | None:
    return get_db().execute(
        """
        SELECT id, github_user_id, github_login, github_name, created_at, updated_at
        FROM users
        WHERE github_user_id = ?
        """,
        (github_user_id,),
    ).fetchone()


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
    return connection.execute(
        "SELECT id FROM repositories WHERE full_name = ?",
        (full_name,),
    ).fetchone()["id"]


def upsert_repository_for_user(
    user_id: int,
    owner: str,
    name: str,
    full_name: str,
    github_repo_id: str = "",
    default_branch: str = "",
) -> int:
    connection = get_db()
    timestamp = now_iso()
    existing = connection.execute(
        """
        SELECT id FROM repositories
        WHERE full_name = ?
        """,
        (full_name,),
    ).fetchone()

    if existing:
        connection.execute(
            """
            UPDATE repositories
            SET github_repo_id = ?, owner_login = ?, repo_name = ?, default_branch = ?,
                selected_by_user_id = ?, is_active = 1, updated_at = ?
            WHERE id = ?
            """,
            (github_repo_id, owner, name, default_branch, user_id, timestamp, existing["id"]),
        )
        connection.commit()
        return existing["id"]

    cursor = connection.execute(
        """
        INSERT INTO repositories (
            github_repo_id, owner_login, repo_name, full_name, default_branch,
            selected_by_user_id, is_active, created_at, updated_at, last_synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, NULL)
        """,
        (
            github_repo_id,
            owner,
            name,
            full_name,
            default_branch,
            user_id,
            timestamp,
            timestamp,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def get_repository_by_id(repository_id: int) -> dict | None:
    row = get_db().execute(
        """
        SELECT
            id,
            selected_by_user_id AS user_id,
            owner_login AS owner,
            repo_name AS name,
            full_name,
            created_at,
            last_synced_at
        FROM repositories
        WHERE id = ?
        """,
        (repository_id,),
    ).fetchone()
    return row


def get_latest_repository_by_user_id(user_id: int) -> dict | None:
    return get_db().execute(
        """
        SELECT
            id,
            selected_by_user_id AS user_id,
            owner_login AS owner,
            repo_name AS name,
            full_name,
            created_at,
            last_synced_at
        FROM repositories
        WHERE selected_by_user_id = ? AND is_active = 1
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()


def get_issues_by_repository_id(repository_id: int) -> list[dict]:
    return get_db().execute(
        """
        SELECT
            id,
            repository_id,
            github_issue_id,
            issue_number,
            title,
            body,
            state,
            project_status,
            github_created_at,
            created_at
        FROM issues
        WHERE repository_id = ?
        ORDER BY issue_number ASC, id ASC
        """,
        (repository_id,),
    ).fetchall()


def _ensure_legacy_columns(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(repositories)").fetchall()
    column_names = {row["name"] for row in rows}
    if "last_synced_at" not in column_names:
        connection.execute("ALTER TABLE repositories ADD COLUMN last_synced_at TEXT")

    commit_rows = connection.execute("PRAGMA table_info(commit_metadata)").fetchall()
    commit_column_names = {row["name"] for row in commit_rows}
    if "analyzed_at" not in commit_column_names:
        connection.execute("ALTER TABLE commit_metadata ADD COLUMN analyzed_at TEXT")

    judgement_rows = connection.execute("PRAGMA table_info(problem_judgements)").fetchall()
    judgement_column_names = {row["name"] for row in judgement_rows}
    if "match_score" not in judgement_column_names:
        connection.execute("ALTER TABLE problem_judgements ADD COLUMN match_score REAL NOT NULL DEFAULT 0")

    issue_rows = connection.execute("PRAGMA table_info(issues)").fetchall()
    issue_column_names = {row["name"] for row in issue_rows}
    if "project_status" not in issue_column_names:
        connection.execute("ALTER TABLE issues ADD COLUMN project_status TEXT")


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


def save_issue(
    repository_id: int,
    github_issue_id: str,
    title: str,
    body: str,
    state: str,
    github_created_at: str,
    issue_number: int | None = None,
    project_status: str = "",
) -> tuple[int, bool]:
    connection = get_db()
    existing = connection.execute(
        """
        SELECT id FROM issues
        WHERE repository_id = ? AND github_issue_id = ?
        """,
        (repository_id, github_issue_id),
    ).fetchone()

    if existing:
        connection.execute(
            """
            UPDATE issues
            SET issue_number = ?, title = ?, body = ?, state = ?, project_status = ?, github_created_at = ?
            WHERE id = ?
            """,
            (issue_number, title, body, state, project_status, github_created_at, existing["id"]),
        )
        connection.commit()
        return existing["id"], False

    cursor = connection.execute(
        """
        INSERT INTO issues (
            repository_id, github_issue_id, issue_number, title, body, state, project_status,
            github_created_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            repository_id,
            github_issue_id,
            issue_number,
            title,
            body,
            state,
            project_status,
            github_created_at,
            now_iso(),
        ),
    )
    connection.commit()
    return cursor.lastrowid, True


def save_commit(
    repository_id: int,
    sha: str,
    message: str,
    author_name: str,
    committed_at: str,
    analyzed_at: str | None = None,
) -> tuple[int, bool]:
    connection = get_db()
    existing = connection.execute(
        """
        SELECT id FROM commit_metadata
        WHERE repository_id = ? AND github_commit_sha = ?
        """,
        (repository_id, sha),
    ).fetchone()

    if existing:
        connection.execute(
            """
            UPDATE commit_metadata
            SET author_login = ?, commit_message = ?, committed_at = ?, analyzed_at = ?
            WHERE id = ?
            """,
            (author_name, message, committed_at, analyzed_at, existing["id"]),
        )
        connection.commit()
        return existing["id"], False

    cursor = connection.execute(
        """
        INSERT INTO commit_metadata (
            repository_id, github_commit_sha, author_login, commit_message,
            committed_at, analyzed_at, file_count, files_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, '[]', ?)
        """,
        (
            repository_id,
            sha,
            author_name,
            message,
            committed_at,
            analyzed_at,
            now_iso(),
        ),
    )
    connection.commit()
    return cursor.lastrowid, True


def update_commit_files(
    repository_id: int,
    sha: str,
    files: list[dict],
    analyzed_at: str | None = None,
) -> None:
    connection = get_db()
    connection.execute(
        """
        UPDATE commit_metadata
        SET file_count = ?, files_json = ?, analyzed_at = COALESCE(?, analyzed_at)
        WHERE repository_id = ? AND github_commit_sha = ?
        """,
        (len(files), json.dumps(files, ensure_ascii=False), analyzed_at, repository_id, sha),
    )
    connection.commit()


def get_commit_by_sha(repository_id: int, sha: str) -> dict | None:
    return get_db().execute(
        """
        SELECT
            id,
            repository_id,
            github_commit_sha AS sha,
            author_login AS author_name,
            commit_message AS message,
            committed_at,
            analyzed_at,
            file_count,
            files_json,
            created_at
        FROM commit_metadata
        WHERE repository_id = ? AND github_commit_sha = ?
        """,
        (repository_id, sha),
    ).fetchone()


def list_commits_by_repository_id(repository_id: int, limit: int = 100) -> list[dict]:
    return get_db().execute(
        """
        SELECT
            id,
            github_commit_sha AS sha,
            author_login AS author_name,
            commit_message AS message,
            committed_at,
            analyzed_at,
            file_count
        FROM commit_metadata
        WHERE repository_id = ?
        ORDER BY committed_at DESC, id DESC
        LIMIT ?
        """,
        (repository_id, limit),
    ).fetchall()


def clear_problem_judgements_for_commit(commit_id: int) -> None:
    connection = get_db()
    connection.execute("DELETE FROM problem_judgements WHERE commit_id = ?", (commit_id,))
    connection.commit()


def update_repository_last_synced_at(repository_id: int, synced_at: str | None = None) -> None:
    connection = get_db()
    connection.execute(
        "UPDATE repositories SET last_synced_at = ?, updated_at = ? WHERE id = ?",
        (synced_at or now_iso(), now_iso(), repository_id),
    )
    connection.commit()


def get_sync_status(repository_id: int) -> dict:
    connection = get_db()
    repository = connection.execute(
        """
        SELECT id, full_name, last_synced_at
        FROM repositories
        WHERE id = ?
        """,
        (repository_id,),
    ).fetchone()
    issue_count = connection.execute(
        "SELECT COUNT(*) AS count FROM issues WHERE repository_id = ?",
        (repository_id,),
    ).fetchone()["count"]
    commit_count = connection.execute(
        "SELECT COUNT(*) AS count FROM commit_metadata WHERE repository_id = ?",
        (repository_id,),
    ).fetchone()["count"]
    return {
        "repository": repository,
        "issue_count": issue_count,
        "commit_count": commit_count,
        "last_synced_at": repository["last_synced_at"] if repository else None,
    }


def save_problem_judgement(
    repository_id: int,
    problem_key: str,
    judgement_status: str,
    commit_id: int | None = None,
    issue_number: int | None = None,
    file_path: str = "",
    match_score: float = 0.0,
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
            judgement_status, match_score, matched_by_filename, execution_passed,
            sample_output_matched, judged_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            repository_id,
            commit_id,
            issue_number,
            problem_key,
            file_path,
            judgement_status,
            match_score,
            int(matched_by_filename),
            int(execution_passed),
            int(sample_output_matched),
            now_iso(),
            notes,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def get_problem_judgements_by_commit_id(commit_id: int) -> list[dict]:
    return get_db().execute(
        """
        SELECT
            id,
            repository_id,
            commit_id,
            issue_number,
            problem_key,
            file_path,
            judgement_status,
            match_score,
            matched_by_filename,
            execution_passed,
            sample_output_matched,
            judged_at,
            notes
        FROM problem_judgements
        WHERE commit_id = ?
        ORDER BY id ASC
        """,
        (commit_id,),
    ).fetchall()


def get_problem_summary_by_repository_id(repository_id: int) -> dict:
    rows = get_db().execute(
        """
        SELECT judgement_status, COUNT(*) AS count
        FROM problem_judgements
        WHERE repository_id = ?
        GROUP BY judgement_status
        """,
        (repository_id,),
    ).fetchall()
    counts = {row["judgement_status"]: row["count"] for row in rows}
    return {
        "attempted_count": counts.get("attempted", 0),
        "possibly_solved_count": counts.get("possibly_solved", 0),
        "solved_count": counts.get("solved", 0),
        "total_count": sum(counts.values()),
    }


def list_problem_judgements_by_repository_id(repository_id: int) -> list[dict]:
    return get_db().execute(
        """
        SELECT
            id,
            repository_id,
            commit_id,
            issue_number,
            problem_key,
            file_path,
            judgement_status,
            match_score,
            matched_by_filename,
            execution_passed,
            sample_output_matched,
            judged_at,
            notes
        FROM problem_judgements
        WHERE repository_id = ?
        ORDER BY judged_at DESC, id DESC
        """,
        (repository_id,),
    ).fetchall()


def save_commit_analysis_result(
    commit_id: int,
    review_summary: str,
    review_comments: list[str],
    execution_status: str,
    execution_output: dict | None,
    detected_topics: list[str],
) -> int:
    connection = get_db()
    timestamp = now_iso()
    existing = connection.execute(
        """
        SELECT id FROM commit_analysis_results
        WHERE commit_id = ?
        """,
        (commit_id,),
    ).fetchone()

    payload = (
        review_summary,
        json.dumps(review_comments, ensure_ascii=False),
        execution_status,
        json.dumps(execution_output or {}, ensure_ascii=False),
        json.dumps(detected_topics, ensure_ascii=False),
        timestamp,
    )

    if existing:
        connection.execute(
            """
            UPDATE commit_analysis_results
            SET review_summary = ?, review_comments_json = ?, execution_status = ?,
                execution_output_json = ?, detected_topics_json = ?, analyzed_at = ?
            WHERE commit_id = ?
            """,
            (*payload, commit_id),
        )
        connection.commit()
        return existing["id"]

    cursor = connection.execute(
        """
        INSERT INTO commit_analysis_results (
            commit_id, review_summary, review_comments_json, execution_status,
            execution_output_json, detected_topics_json, analyzed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (commit_id, *payload),
    )
    connection.commit()
    return cursor.lastrowid


def get_commit_analysis_result(commit_id: int) -> dict | None:
    row = get_db().execute(
        """
        SELECT
            id,
            commit_id,
            review_summary,
            review_comments_json,
            execution_status,
            execution_output_json,
            detected_topics_json,
            analyzed_at
        FROM commit_analysis_results
        WHERE commit_id = ?
        """,
        (commit_id,),
    ).fetchone()
    if not row:
        return None

    return {
        **row,
        "review_comments": json.loads(row["review_comments_json"] or "[]"),
        "execution_output": json.loads(row["execution_output_json"] or "{}"),
        "detected_topics": json.loads(row["detected_topics_json"] or "[]"),
    }


def list_recent_commit_topics_by_repository_id(repository_id: int, limit: int = 5) -> list[str]:
    rows = get_db().execute(
        """
        SELECT car.detected_topics_json
        FROM commit_analysis_results car
        INNER JOIN commit_metadata cm ON cm.id = car.commit_id
        WHERE cm.repository_id = ?
        ORDER BY cm.committed_at DESC, cm.id DESC
        LIMIT ?
        """,
        (repository_id, limit),
    ).fetchall()

    topics = []
    for row in rows:
        topics.extend(json.loads(row["detected_topics_json"] or "[]"))
    return topics


def save_recommendation(
    repository_id: int,
    topic: str,
    problem_title: str,
    problem_url: str,
    source_site: str,
    reason: str,
    report_id: int | None = None,
) -> tuple[int, bool]:
    connection = get_db()
    existing = connection.execute(
        """
        SELECT id FROM recommendation_history
        WHERE repository_id = ? AND problem_url = ?
        """,
        (repository_id, problem_url),
    ).fetchone()

    if existing:
        return existing["id"], False

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
    return cursor.lastrowid, True


def list_recommendations_by_repository_id(repository_id: int) -> list[dict]:
    return get_db().execute(
        """
        SELECT
            id,
            repository_id,
            report_id,
            topic,
            source_site AS source,
            problem_title AS title,
            problem_url AS url,
            reason,
            recommended_at
        FROM recommendation_history
        WHERE repository_id = ?
        ORDER BY recommended_at DESC, id DESC
        """,
        (repository_id,),
    ).fetchall()


def save_analysis_report(
    repository_id: int,
    report_scope: str,
    solved_count: int,
    attempted_count: int,
    status_label: str,
    summary_text: str,
    topic_breakdown: dict | list,
    weak_topics: list[str],
) -> int:
    connection = get_db()
    cursor = connection.execute(
        """
        INSERT INTO analysis_reports (
            repository_id, report_scope, solved_count, attempted_count, status_label,
            summary_text, topic_breakdown_json, weak_topics_json, generated_at
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
            json.dumps(topic_breakdown, ensure_ascii=False),
            json.dumps(weak_topics, ensure_ascii=False),
            now_iso(),
        ),
    )
    connection.commit()
    return cursor.lastrowid


def get_latest_analysis_report(repository_id: int, report_scope: str) -> dict | None:
    row = get_db().execute(
        """
        SELECT
            id,
            repository_id,
            report_scope,
            solved_count,
            attempted_count,
            status_label,
            summary_text,
            topic_breakdown_json,
            weak_topics_json,
            generated_at
        FROM analysis_reports
        WHERE repository_id = ? AND report_scope = ?
        ORDER BY generated_at DESC, id DESC
        LIMIT 1
        """,
        (repository_id, report_scope),
    ).fetchone()
    if not row:
        return None

    return {
        **row,
        "topic_breakdown": json.loads(row["topic_breakdown_json"] or "{}"),
        "weak_topics": json.loads(row["weak_topics_json"] or "[]"),
    }


def save_github_project_tracking(
    repository_id: int,
    week_label: str,
    project_title: str,
    project_url: str = "",
    project_number: str = "",
    is_active: bool = True,
) -> int:
    connection = get_db()
    timestamp = now_iso()
    if is_active:
        connection.execute(
            "UPDATE github_projects SET is_active = 0, updated_at = ? WHERE repository_id = ?",
            (timestamp, repository_id),
        )

    existing = connection.execute(
        """
        SELECT id FROM github_projects
        WHERE repository_id = ? AND week_label = ? AND project_title = ?
        """,
        (repository_id, week_label, project_title),
    ).fetchone()

    if existing:
        connection.execute(
            """
            UPDATE github_projects
            SET project_url = ?, project_number = ?, is_active = ?, updated_at = ?
            WHERE id = ?
            """,
            (project_url, project_number, int(is_active), timestamp, existing["id"]),
        )
        connection.commit()
        return existing["id"]

    cursor = connection.execute(
        """
        INSERT INTO github_projects (
            repository_id, week_label, project_title, project_url, project_number,
            is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            repository_id,
            week_label,
            project_title,
            project_url,
            project_number,
            int(is_active),
            timestamp,
            timestamp,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def get_active_github_project(repository_id: int) -> dict | None:
    return get_db().execute(
        """
        SELECT
            id,
            repository_id,
            week_label,
            project_title,
            project_url,
            project_number,
            is_active,
            created_at,
            updated_at
        FROM github_projects
        WHERE repository_id = ? AND is_active = 1
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (repository_id,),
    ).fetchone()

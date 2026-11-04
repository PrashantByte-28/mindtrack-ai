"""Safe, idempotent SQLite database migration for MindTrack AI.

Safely adds the `users` table, security question/recovery key columns, and `user_id` ownership
columns to `mood_entries` and `conversations` tables, associates pre-existing legacy records
with a designated default user, and automatically creates a timestamped database backup prior to migration.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MIGRATION_USER = "mindtrack_user"
DEFAULT_MIGRATION_PASSWORD = "MindTrack2026!"
DEFAULT_SECURITY_QUESTION = "What is the name of this wellness companion?"
DEFAULT_SECURITY_ANSWER = "mindtrack"
DEFAULT_RECOVERY_KEY = "MT-MIND-TRACK-2026"


def _create_database_backup(db_path: Path) -> Path | None:
    """Create a timestamped backup copy of the SQLite database file if it exists."""
    if not db_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}.backup_{timestamp}{db_path.suffix}"

    try:
        shutil.copy2(db_path, backup_path)
        logger.info("Database backup created at %s", backup_path)
        return backup_path
    except Exception as exc:
        logger.error("Failed to create database backup: %s", exc)
        raise RuntimeError(f"Could not create database backup: {exc}") from exc


def migrate_database(
    db_path: Path | str,
    default_username: str = DEFAULT_MIGRATION_USER,
    default_password: str = DEFAULT_MIGRATION_PASSWORD,
    create_backup: bool = True,
) -> dict[str, Any]:
    """Execute a safe, idempotent SQLite database migration.

    - Inspects database schema to verify if migration is necessary.
    - Creates timestamped backup if requested and database requires migration.
    - Creates `users` table if missing with security question & recovery key fields.
    - Adds `security_question`, `security_answer_hash`, and `recovery_key_hash` columns if missing.
    - Adds `user_id` column to `mood_entries` if missing.
    - Adds `user_id` column to `conversations` if missing.
    - Assigns existing records without a user_id to `default_username`.
    """
    path = Path(db_path).resolve()
    result: dict[str, Any] = {
        "status": "noop",
        "backup_path": None,
        "users_table_created": False,
        "security_cols_added": False,
        "mood_user_id_added": False,
        "convo_user_id_added": False,
        "default_user_created": False,
        "legacy_user_id": None,
        "migrated_moods": 0,
        "migrated_convos": 0,
        "users_with_defaults": 0,
    }

    if not path.exists():
        logger.info("Database file %s does not exist yet. Migration skipped.", path)
        result["status"] = "skipped_new_db"
        return result

    # Check whether migration is needed before creating a backup
    con_check = sqlite3.connect(path)
    try:
        cur_check = con_check.cursor()
        tables = [
            row[0]
            for row in cur_check.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]

        needs_users_table = "users" not in tables

        needs_sec_q = False
        needs_sec_a = False
        needs_rec_k = False
        null_sec_count = 0
        if not needs_users_table:
            user_cols = [
                row[1] for row in cur_check.execute("PRAGMA table_info(users)").fetchall()
            ]
            needs_sec_q = "security_question" not in user_cols
            needs_sec_a = "security_answer_hash" not in user_cols
            needs_rec_k = "recovery_key_hash" not in user_cols

            if not (needs_sec_q or needs_sec_a or needs_rec_k):
                null_sec_count = cur_check.execute(
                    "SELECT COUNT(*) FROM users WHERE security_question IS NULL OR security_answer_hash IS NULL;"
                ).fetchone()[0]

        needs_mood_col = False
        orphan_moods = 0
        if "mood_entries" in tables:
            mood_cols = [
                row[1]
                for row in cur_check.execute("PRAGMA table_info(mood_entries)").fetchall()
            ]
            needs_mood_col = "user_id" not in mood_cols
            if not needs_mood_col:
                orphan_moods = cur_check.execute(
                    "SELECT COUNT(*) FROM mood_entries WHERE user_id IS NULL;"
                ).fetchone()[0]

        needs_convo_col = False
        orphan_convos = 0
        if "conversations" in tables:
            convo_cols = [
                row[1]
                for row in cur_check.execute("PRAGMA table_info(conversations)").fetchall()
            ]
            needs_convo_col = "user_id" not in convo_cols
            if not needs_convo_col:
                orphan_convos = cur_check.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id IS NULL;"
                ).fetchone()[0]

        if not (
            needs_users_table
            or needs_sec_q
            or needs_sec_a
            or needs_rec_k
            or null_sec_count > 0
            or needs_mood_col
            or needs_convo_col
            or orphan_moods > 0
            or orphan_convos > 0
        ):
            result["status"] = "already_up_to_date"
            return result
    finally:
        con_check.close()

    # Import password hashing and recovery key generator
    from mindtrack_ai.security import (
        hash_password,
        normalize_answer,
        normalize_recovery_key,
    )

    # Step 1: Backup since changes are needed
    if create_backup:
        backup = _create_database_backup(path)
        result["backup_path"] = str(backup) if backup else None

    # Step 2: Connect to SQLite directly for atomic schema modification
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()

        # 1. Create `users` table if missing
        if needs_users_table:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    security_question VARCHAR(255),
                    security_answer_hash VARCHAR(255),
                    recovery_key_hash VARCHAR(255),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);"
            )
            result["users_table_created"] = True
            logger.info("Created 'users' table with security fields.")
        else:
            # Add missing security columns if users table exists
            if needs_sec_q:
                cur.execute("ALTER TABLE users ADD COLUMN security_question VARCHAR(255);")
            if needs_sec_a:
                cur.execute("ALTER TABLE users ADD COLUMN security_answer_hash VARCHAR(255);")
            if needs_rec_k:
                cur.execute("ALTER TABLE users ADD COLUMN recovery_key_hash VARCHAR(255);")

            if needs_sec_q or needs_sec_a or needs_rec_k:
                result["security_cols_added"] = True
                logger.info("Added security question and recovery key columns to 'users'.")

        # Set default security question and answer for any users lacking them
        default_ans_hash = hash_password(normalize_answer(DEFAULT_SECURITY_ANSWER))
        default_rec_hash = hash_password(normalize_recovery_key(DEFAULT_RECOVERY_KEY))

        cur.execute(
            """
            UPDATE users
            SET security_question = COALESCE(security_question, ?),
                security_answer_hash = COALESCE(security_answer_hash, ?),
                recovery_key_hash = COALESCE(recovery_key_hash, ?)
            WHERE security_question IS NULL OR security_answer_hash IS NULL OR recovery_key_hash IS NULL;
            """,
            (DEFAULT_SECURITY_QUESTION, default_ans_hash, default_rec_hash),
        )
        result["users_with_defaults"] = cur.rowcount

        # 2. Check and migrate `mood_entries`
        if needs_mood_col:
            cur.execute(
                "ALTER TABLE mood_entries ADD COLUMN user_id INTEGER REFERENCES users(id);"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_mood_entries_user_id ON mood_entries(user_id);"
            )
            result["mood_user_id_added"] = True
            logger.info("Added 'user_id' column to 'mood_entries'.")

        # 3. Check and migrate `conversations`
        if needs_convo_col:
            cur.execute(
                "ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id);"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);"
            )
            result["convo_user_id_added"] = True
            logger.info("Added 'user_id' column to 'conversations'.")

        # 4. Check for orphan records where user_id IS NULL
        if "mood_entries" in tables:
            orphan_moods = cur.execute(
                "SELECT COUNT(*) FROM mood_entries WHERE user_id IS NULL;"
            ).fetchone()[0]

        if "conversations" in tables:
            orphan_convos = cur.execute(
                "SELECT COUNT(*) FROM conversations WHERE user_id IS NULL;"
            ).fetchone()[0]

        if orphan_moods > 0 or orphan_convos > 0:
            logger.info(
                "Found orphan records to migrate: %d mood entries, %d conversations.",
                orphan_moods,
                orphan_convos,
            )

            # Ensure default migration user exists
            cur.execute(
                "SELECT id FROM users WHERE LOWER(username) = LOWER(?);",
                (default_username,),
            )
            user_row = cur.fetchone()

            if user_row is None:
                pw_hash = hash_password(default_password)
                cur.execute(
                    """
                    INSERT INTO users (
                        username, password_hash, security_question, security_answer_hash, recovery_key_hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        default_username,
                        pw_hash,
                        DEFAULT_SECURITY_QUESTION,
                        default_ans_hash,
                        default_rec_hash,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                legacy_user_id = cur.lastrowid
                result["default_user_created"] = True
                logger.info(
                    "Created default user '%s' with id %d for orphan records.",
                    default_username,
                    legacy_user_id,
                )
            else:
                legacy_user_id = user_row[0]

            result["legacy_user_id"] = legacy_user_id

            # Associate orphan records
            if orphan_moods > 0:
                cur.execute(
                    "UPDATE mood_entries SET user_id = ? WHERE user_id IS NULL;",
                    (legacy_user_id,),
                )
                result["migrated_moods"] = orphan_moods

            if orphan_convos > 0:
                cur.execute(
                    "UPDATE conversations SET user_id = ? WHERE user_id IS NULL;",
                    (legacy_user_id,),
                )
                result["migrated_convos"] = orphan_convos

        con.commit()
        result["status"] = "success"
        logger.info("Database migration completed successfully.")
        return result

    except Exception as exc:
        con.rollback()
        logger.exception("Database migration failed.")
        raise RuntimeError(f"Database migration failed: {exc}") from exc
    finally:
        con.close()


if __name__ == "__main__":
    import sys

    db_path = Path(__file__).resolve().parents[2] / "mindtrack.db"
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])

    print(f"Running migration for: {db_path}")
    res = migrate_database(db_path)
    print("Migration result:", res)

"""Unit tests for safe, idempotent SQLite database migration."""

import sqlite3
from pathlib import Path

from mindtrack_ai.migration import migrate_database


def test_migration_on_legacy_database(tmp_path: Path):
    db_file = tmp_path / "legacy_test.db"

    # Create a legacy database without users table and without user_id columns
    con = sqlite3.connect(db_file)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE mood_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date DATE,
        mood VARCHAR(30),
        intensity INTEGER,
        note TEXT,
        created_at DATETIME
    );
    """)
    cur.execute("""
    CREATE TABLE conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(100),
        created_at DATETIME,
        updated_at DATETIME
    );
    """)
    cur.execute("""
    CREATE TABLE chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER REFERENCES conversations(id),
        role VARCHAR(20),
        content TEXT,
        created_at DATETIME
    );
    """)

    # Insert sample legacy records
    cur.execute(
        "INSERT INTO mood_entries (entry_date, mood, intensity, note, created_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-10-20", "Happy", 4, "Old legacy checkin", "2026-10-20 12:00:00"),
    )
    cur.execute(
        "INSERT INTO mood_entries (entry_date, mood, intensity, note, created_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-10-21", "Stressed", 3, "Another legacy checkin", "2026-10-21 12:00:00"),
    )
    cur.execute(
        "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
        ("Old legacy conversation", "2026-10-20 12:00:00", "2026-10-20 12:00:00"),
    )
    convo_id = cur.lastrowid
    cur.execute(
        "INSERT INTO chat_messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (convo_id, "user", "Legacy message", "2026-10-20 12:01:00"),
    )
    con.commit()
    con.close()

    # Run migration
    result = migrate_database(
        db_path=db_file,
        default_username="migrated_legacy_user",
        default_password="LegacySecret2026!",
        create_backup=True,
    )

    assert result["status"] == "success"
    assert result["users_table_created"] is True
    assert result["mood_user_id_added"] is True
    assert result["convo_user_id_added"] is True
    assert result["default_user_created"] is True
    assert result["migrated_moods"] == 2
    assert result["migrated_convos"] == 1
    assert result["backup_path"] is not None
    assert Path(result["backup_path"]).exists()

    # Verify database contents post-migration
    con2 = sqlite3.connect(db_file)
    cur2 = con2.cursor()

    # Users table has the legacy user and security fields
    user_row = cur2.execute(
        "SELECT id, username, security_question, security_answer_hash FROM users WHERE username = 'migrated_legacy_user'"
    ).fetchone()
    assert user_row is not None
    legacy_uid = user_row[0]
    assert user_row[2] is not None  # security_question populated
    assert user_row[3] is not None  # security_answer_hash populated

    # Mood entries have valid user_id
    mood_rows = cur2.execute(
        "SELECT id, user_id, mood FROM mood_entries"
    ).fetchall()
    assert len(mood_rows) == 2
    assert all(row[1] == legacy_uid for row in mood_rows)

    # Conversation has valid user_id
    convo_rows = cur2.execute(
        "SELECT id, user_id, title FROM conversations"
    ).fetchall()
    assert len(convo_rows) == 1
    assert convo_rows[0][1] == legacy_uid

    # No orphan records remain
    null_moods = cur2.execute(
        "SELECT COUNT(*) FROM mood_entries WHERE user_id IS NULL"
    ).fetchone()[0]
    null_convos = cur2.execute(
        "SELECT COUNT(*) FROM conversations WHERE user_id IS NULL"
    ).fetchone()[0]
    assert null_moods == 0
    assert null_convos == 0

    con2.close()

    # Idempotence: running migration a second time should not fail and migrate 0 rows
    result2 = migrate_database(
        db_path=db_file,
        default_username="migrated_legacy_user",
        create_backup=False,
    )
    assert result2["status"] == "already_up_to_date"
    assert result2["users_table_created"] is False
    assert result2["mood_user_id_added"] is False
    assert result2["convo_user_id_added"] is False
    assert result2["migrated_moods"] == 0
    assert result2["migrated_convos"] == 0

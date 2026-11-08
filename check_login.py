"""MindTrack diagnostic: why does my account disappear / login fail after a restart?

Put this file next to app.py (the project root) and run:

    python check_login.py

It never changes or deletes your data. It shows:
  1. which database this process uses,
  2. every MindTrack database file found in the project folder (including
     backups and stray copies) and who is inside each one,
  3. whether the username you type exists, and whether the password works.

Run it once, restart your server / terminal, run it again, and compare.
"""

from __future__ import annotations

import getpass
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in (str(ROOT / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

SKIP_DIRS = {".venv", "venv", "env", "node_modules", ".git", "__pycache__", "site-packages"}


def find_db_files() -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.lower().endswith((".db", ".sqlite", ".sqlite3")):
                found.append(Path(dirpath) / name)
    return sorted(found)


def describe_sqlite(path: Path) -> str:
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "users" not in tables:
                return "no users table"
            rows = con.execute("SELECT id, username FROM users ORDER BY id").fetchall()
            moods = (
                con.execute("SELECT COUNT(*) FROM mood_entries").fetchone()[0]
                if "mood_entries" in tables
                else 0
            )
            names = ", ".join(f"{u} (id {i})" for i, u in rows) or "none"
            return f"{len(rows)} user(s): {names} | {moods} mood entries"
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        return f"could not read ({exc})"


def main() -> None:
    print("=" * 70)
    print("Project folder:", ROOT)
    print("DATABASE_URL set in this terminal:", bool(os.getenv("DATABASE_URL")))
    print("=" * 70)

    # Importing the database module runs the same startup code as the app.
    from mindtrack_ai import database  # prints the "[MindTrack] Database:" line

    # The file the app REALLY uses is whatever the engine points to (this can differ
    # from the default mindtrack.db when DATABASE_URL is set).
    in_use: Path | None = None
    if database.database_backend == "sqlite":
        in_use = Path(database.engine.url.database).resolve()
    else:
        print(f"\nNOTE: the app is using {database.database_backend} (NOT a local file).")
        print("      Local .db files below are NOT being used by the app.")

    print("\nDatabase files found in the project folder:")
    files = find_db_files()
    if not files:
        print("  (none)")
    for f in files:
        mark = "  <-- IN USE" if in_use is not None and f.resolve() == in_use else ""
        print(f"  {f.relative_to(ROOT)}{mark}\n      {describe_sqlite(f)}")

    from mindtrack_ai.auth import authenticate_user, get_user_by_username

    print("\n--- Login test (nothing is changed) ---")
    username = input("Username to test: ").strip()
    user = get_user_by_username(username)
    if user is None:
        print(f"RESULT: no user named '{username}' exists in the database in use.")
        print("        -> the app is reading a database that does not contain this account.")
        return
    print(f"User '{user['username']}' EXISTS (id {user['id']}, created {user['created_at']}).")

    password = getpass.getpass("Password to test (hidden, optional - press Enter to skip): ")
    if not password:
        return
    ok, err = authenticate_user(username, password)
    if ok:
        print("RESULT: password is CORRECT. Login works in this process.")
    else:
        print(f"RESULT: login failed -> {err}")
        print("        The user exists, so this is a password problem, not a missing account.")


if __name__ == "__main__":
    main()
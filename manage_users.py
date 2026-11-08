"""Manage MindTrack AI users from the command line.

Put this file next to app.py (the project root).

    python manage_users.py list              show users and how much data each owns
    python manage_users.py reset             back up, then DELETE ALL users and their data
    python manage_users.py add               add one or more new users (interactive)
    python manage_users.py reset-and-add     reset, then add new users

It works on whichever database the app itself would use (the local mindtrack.db,
or the file named by MINDTRACK_DB_PATH, which is /data/mindtrack.db in Docker).

WARNING: deleting a user also deletes that user's mood check-ins and chat
conversations. A backup copy of the SQLite file is made first.
"""

from __future__ import annotations

import argparse
import getpass
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for _p in (str(ROOT / "src"), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sqlalchemy import delete, func, select, text  # noqa: E402

from mindtrack_ai import database  # noqa: E402  (prints which database is in use)
from mindtrack_ai.auth import register_user  # noqa: E402
from mindtrack_ai.database import ChatMessage, Conversation, MoodEntry, User  # noqa: E402
from mindtrack_ai.security import DEFAULT_SECURITY_QUESTIONS  # noqa: E402

CONFIRM_PHRASE = "DELETE ALL USERS"


def _counts() -> dict[str, int]:
    with database.SessionLocal() as db:
        return {
            "users": db.scalar(select(func.count()).select_from(User)) or 0,
            "mood check-ins": db.scalar(select(func.count()).select_from(MoodEntry)) or 0,
            "conversations": db.scalar(select(func.count()).select_from(Conversation)) or 0,
            "chat messages": db.scalar(select(func.count()).select_from(ChatMessage)) or 0,
        }


def cmd_list() -> None:
    with database.SessionLocal() as db:
        users = db.scalars(select(User).order_by(User.id)).all()
        if not users:
            print("No users in this database.")
            return
        print(f"{'id':>4}  {'username':<30} {'check-ins':>9} {'chats':>6}  created")
        for u in users:
            moods = db.scalar(
                select(func.count()).select_from(MoodEntry).where(MoodEntry.user_id == u.id)
            )
            chats = db.scalar(
                select(func.count()).select_from(Conversation).where(Conversation.user_id == u.id)
            )
            print(f"{u.id:>4}  {u.username:<30} {moods:>9} {chats:>6}  {u.created_at:%Y-%m-%d %H:%M}")


def _backup_sqlite() -> Path | None:
    if database.database_backend != "sqlite":
        print("NOTE: this is not a SQLite database, so no automatic backup was made.")
        return None
    src = Path(database.engine.url.database)
    if not src.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = src.parent / f"{src.stem}.backup_before_reset_{stamp}{src.suffix}"
    # sqlite's backup API gives a consistent copy even if the app is running.
    with sqlite3.connect(src) as source, sqlite3.connect(dest) as target:
        source.backup(target)
    return dest


def cmd_reset(assume_yes: bool = False) -> bool:
    counts = _counts()
    print("\nThis will permanently delete:")
    for name, n in counts.items():
        print(f"  - {n} {name}")
    if counts["users"] == 0 and sum(counts.values()) == 0:
        print("\nNothing to delete.")
        return True

    if not assume_yes:
        typed = input(f'\nType "{CONFIRM_PHRASE}" to continue (anything else cancels): ').strip()
        if typed != CONFIRM_PHRASE:
            print("Cancelled. Nothing was changed.")
            return False

    backup = _backup_sqlite()
    if backup:
        print(f"Backup saved: {backup}")

    with database.SessionLocal() as db:
        # Children first, so this works whether or not the DB enforces cascades.
        db.execute(delete(ChatMessage))
        db.execute(delete(Conversation))
        db.execute(delete(MoodEntry))
        db.execute(delete(User))
        db.commit()

    if database.database_backend == "sqlite":
        try:  # start user ids from 1 again
            with database.engine.begin() as conn:
                conn.execute(text("DELETE FROM sqlite_sequence WHERE name = 'users'"))
        except Exception:
            pass

    print("All users and their data were deleted.")
    return True


def _choose_question() -> str:
    print("\nSecurity question (used if the password is forgotten):")
    for i, q in enumerate(DEFAULT_SECURITY_QUESTIONS, 1):
        print(f"  {i}. {q}")
    custom = len(DEFAULT_SECURITY_QUESTIONS) + 1
    print(f"  {custom}. Write my own question")
    while True:
        choice = input("Choose a number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= custom:
            n = int(choice)
            return input("Your question: ").strip() if n == custom else DEFAULT_SECURITY_QUESTIONS[n - 1]
        print("Please enter one of the numbers above.")


def _add_one() -> bool:
    print("\n--- New user ---")
    username = input("Username (3-30 letters, numbers, _ . -): ").strip()
    password = getpass.getpass("Password (min 8 characters, hidden): ")
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match. User not created.")
        return False

    # A security question is required here on purpose: accounts without one get a
    # well-known default question/answer filled in by the startup migration.
    question = _choose_question()
    answer = input("Security answer: ").strip()

    user, err = register_user(username, password, security_question=question, security_answer=answer)
    if not user:
        print(f"Could not create user: {err}")
        return False

    print(f"\nCreated user '{user['username']}' (id {user['id']}).")
    print(f"EMERGENCY RECOVERY KEY (shown only once, write it down): {user['recovery_key']}")
    return True


def cmd_add() -> None:
    while True:
        _add_one()
        if input("\nAdd another user? [y/N]: ").strip().lower() != "y":
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage MindTrack AI users.")
    parser.add_argument("command", choices=["list", "reset", "add", "reset-and-add"])
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the typed confirmation for reset (dangerous; for scripts only)",
    )
    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "reset":
        cmd_reset(args.yes)
    elif args.command == "add":
        cmd_add()
    elif args.command == "reset-and-add":
        if cmd_reset(args.yes):
            cmd_add()

    print("\nCurrent state:")
    cmd_list()


if __name__ == "__main__":
    main()
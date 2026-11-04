from datetime import date
from typing import Any

from sqlalchemy import select

from mindtrack_ai import database
from mindtrack_ai.database import MoodEntry

ALLOWED_MOODS = {
    "Happy",
    "Calm",
    "Neutral",
    "Sad",
    "Stressed",
    "Anxious",
    "Overwhelmed",
}


def save_mood_entry(
    user_id: int,
    entry_date: date,
    mood: str,
    intensity: int,
    note: str = "",
) -> int:
    """Save a mood entry with user ownership."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if mood not in ALLOWED_MOODS:
        raise ValueError("Invalid mood selection.")

    if not 1 <= intensity <= 5:
        raise ValueError("Intensity must be between 1 and 5.")

    if len(note) > 2000:
        raise ValueError("The note cannot exceed 2000 characters.")

    with database.SessionLocal() as session:
        entry = MoodEntry(
            user_id=user_id,
            entry_date=entry_date,
            mood=mood,
            intensity=intensity,
            note=note.strip(),
        )

        session.add(entry)
        session.commit()
        session.refresh(entry)

        return entry.id


def get_mood_entries(user_id: int) -> list[dict[str, Any]]:
    """Retrieve all mood entries belonging to the specified user, newest first."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    with database.SessionLocal() as session:
        statement = (
            select(MoodEntry)
            .where(MoodEntry.user_id == user_id)
            .order_by(
                MoodEntry.entry_date.desc(),
                MoodEntry.id.desc(),
            )
        )

        entries = session.scalars(statement).all()

        return [
            {
                "id": entry.id,
                "user_id": entry.user_id,
                "date": entry.entry_date,
                "mood": entry.mood,
                "intensity": entry.intensity,
                "note": entry.note,
                "created_at": entry.created_at,
            }
            for entry in entries
        ]


def get_mood_entry(user_id: int, entry_id: int) -> dict[str, Any] | None:
    """Retrieve a single mood entry with per-user ownership verification."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(entry_id, int) or entry_id <= 0:
        raise ValueError("A valid entry ID is required.")

    with database.SessionLocal() as session:
        entry = session.get(MoodEntry, entry_id)

        if entry is None:
            return None

        if entry.user_id != user_id:
            raise PermissionError("Access denied: You do not own this mood entry.")

        return {
            "id": entry.id,
            "user_id": entry.user_id,
            "date": entry.entry_date,
            "mood": entry.mood,
            "intensity": entry.intensity,
            "note": entry.note,
            "created_at": entry.created_at,
        }


def delete_mood_entry(user_id: int, entry_id: int) -> bool:
    """Delete a mood entry with strict ownership verification."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(entry_id, int) or entry_id <= 0:
        raise ValueError("A valid entry ID is required.")

    with database.SessionLocal() as session:
        entry = session.get(MoodEntry, entry_id)

        if entry is None:
            return False

        if entry.user_id != user_id:
            raise PermissionError("Access denied: You do not own this mood entry.")

        session.delete(entry)
        session.commit()
        return True

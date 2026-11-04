"""User authentication and user account management for MindTrack AI.

Provides registration, authentication, user retrieval, password change operations,
and secure password recovery via security questions and emergency recovery keys.
Cryptographic primitives are imported from mindtrack_ai.security.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, select

from mindtrack_ai import database
from mindtrack_ai.database import User
from mindtrack_ai.security import (
    generate_recovery_key,
    hash_password,
    normalize_answer,
    normalize_recovery_key,
    validate_password,
    validate_security_answer,
    validate_security_question,
    validate_username,
    verify_password,
)

logger = logging.getLogger(__name__)

__all__ = [
    "authenticate_user",
    "change_user_password",
    "get_security_question",
    "get_user_by_id",
    "get_user_by_username",
    "hash_password",
    "regenerate_recovery_key",
    "register_user",
    "reset_password_with_recovery_key",
    "reset_password_with_security_answer",
    "update_security_credentials",
    "validate_password",
    "validate_username",
    "verify_password",
]


def register_user(
    username: str,
    password: str,
    security_question: str | None = None,
    security_answer: str | None = None,
) -> tuple[dict | None, str | None]:
    """Register a new user with a hashed password, optional security question/answer,

    and an emergency recovery key.

    Returns (user_dict, None) on success, or (None, error_message) on failure.
    The created user_dict includes the plain 'recovery_key' so the UI can display it once.
    """
    is_valid_user, user_err = validate_username(username)
    if not is_valid_user:
        return None, user_err

    is_valid_pw, pw_err = validate_password(password)
    if not is_valid_pw:
        return None, pw_err

    sec_q: str | None = None
    sec_ans_hash: str | None = None

    if security_question or security_answer:
        if not security_question:
            return None, "Please select or provide a security question."
        if not security_answer:
            return None, "Please provide an answer to your security question."

        valid_q, q_err = validate_security_question(security_question)
        if not valid_q:
            return None, q_err

        valid_a, a_err = validate_security_answer(security_answer)
        if not valid_a:
            return None, a_err

        sec_q = security_question.strip()
        sec_ans_hash = hash_password(normalize_answer(security_answer))

    clean_username = username.strip()

    with database.SessionLocal() as db:
        # Check for case-insensitive existing username
        existing = db.scalars(
            select(User).where(func.lower(User.username) == clean_username.lower())
        ).first()

        if existing is not None:
            return None, "That username is already taken. Please choose another."

        password_hash = hash_password(password)
        raw_recovery_key = generate_recovery_key()
        recovery_key_hash = hash_password(normalize_recovery_key(raw_recovery_key))

        new_user = User(
            username=clean_username,
            password_hash=password_hash,
            security_question=sec_q,
            security_answer_hash=sec_ans_hash,
            recovery_key_hash=recovery_key_hash,
            created_at=datetime.now(),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return (
            {
                "id": new_user.id,
                "username": new_user.username,
                "security_question": new_user.security_question,
                "recovery_key": raw_recovery_key,
                "created_at": new_user.created_at,
            },
            None,
        )


def authenticate_user(username: str, password: str) -> tuple[dict | None, str | None]:
    """Authenticate a user by username and password.

    Returns (user_dict, None) on success, or (None, error_message) on failure.
    """
    if not username or not password:
        return None, "Please enter both username and password."

    clean_username = username.strip()

    with database.SessionLocal() as db:
        user = db.scalars(
            select(User).where(func.lower(User.username) == clean_username.lower())
        ).first()

        if user is None:
            return None, "Invalid username or password."

        if not verify_password(password, user.password_hash):
            return None, "Invalid username or password."

        return (
            {
                "id": user.id,
                "username": user.username,
                "security_question": user.security_question,
                "created_at": user.created_at,
            },
            None,
        )


def get_user_by_id(user_id: int) -> dict | None:
    """Retrieve user dictionary by ID."""
    if not isinstance(user_id, int) or user_id <= 0:
        return None

    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "security_question": user.security_question,
            "created_at": user.created_at,
        }


def get_user_by_username(username: str) -> dict | None:
    """Retrieve user dictionary by username (case-insensitive)."""
    if not username or not isinstance(username, str):
        return None

    clean_username = username.strip()
    with database.SessionLocal() as db:
        user = db.scalars(
            select(User).where(func.lower(User.username) == clean_username.lower())
        ).first()

        if user is None:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "security_question": user.security_question,
            "created_at": user.created_at,
        }


def get_security_question(username: str) -> tuple[str | None, str | None]:
    """Retrieve the configured security question for a given username.

    Returns (question, None) or (None, error_message).
    """
    if not username or not isinstance(username, str) or not username.strip():
        return None, "Please enter your username."

    clean_username = username.strip()
    with database.SessionLocal() as db:
        user = db.scalars(
            select(User).where(func.lower(User.username) == clean_username.lower())
        ).first()

        if user is None:
            return None, "No account was found with that username."

        if not user.security_question:
            return None, "No security question is configured for this account. Please use your Emergency Recovery Key."

        return user.security_question, None


def reset_password_with_security_answer(
    username: str, security_answer: str, new_password: str
) -> tuple[bool, str | None]:
    """Reset a forgotten password by verifying the user's security question answer.

    Returns (success, error_message).
    """
    if not username or not isinstance(username, str) or not username.strip():
        return False, "Please enter your username."

    if not security_answer or not isinstance(security_answer, str) or not security_answer.strip():
        return False, "Please enter the answer to your security question."

    is_valid_pw, pw_err = validate_password(new_password)
    if not is_valid_pw:
        return False, pw_err

    clean_username = username.strip()

    with database.SessionLocal() as db:
        user = db.scalars(
            select(User).where(func.lower(User.username) == clean_username.lower())
        ).first()

        if user is None:
            return False, "No account was found with that username."

        if not user.security_answer_hash:
            return (
                False,
                "No security question is configured for this account. Use your Recovery Key instead.",
            )

        norm_answer = normalize_answer(security_answer)
        if not verify_password(norm_answer, user.security_answer_hash):
            return False, "Incorrect security answer. Please check your answer and try again."

        user.password_hash = hash_password(new_password)
        db.commit()
        return True, None


def reset_password_with_recovery_key(
    username: str, recovery_key: str, new_password: str
) -> tuple[bool, str | None, str | None]:
    """Reset a forgotten password by verifying the single-use emergency recovery key.

    Rotates and returns a fresh recovery key upon successful reset.
    Returns (success, error_message, new_recovery_key).
    """
    if not username or not isinstance(username, str) or not username.strip():
        return False, "Please enter your username.", None

    if not recovery_key or not isinstance(recovery_key, str) or not recovery_key.strip():
        return False, "Please enter your Emergency Recovery Key.", None

    is_valid_pw, pw_err = validate_password(new_password)
    if not is_valid_pw:
        return False, pw_err, None

    clean_username = username.strip()

    with database.SessionLocal() as db:
        user = db.scalars(
            select(User).where(func.lower(User.username) == clean_username.lower())
        ).first()

        if user is None:
            return False, "No account was found with that username.", None

        if not user.recovery_key_hash:
            return False, "No emergency recovery key is configured for this account.", None

        norm_key = normalize_recovery_key(recovery_key)
        if not verify_password(norm_key, user.recovery_key_hash):
            return False, "Invalid Emergency Recovery Key. Please check the code and try again.", None

        # Rotate recovery key for single-use protection
        fresh_key = generate_recovery_key()
        user.recovery_key_hash = hash_password(normalize_recovery_key(fresh_key))
        user.password_hash = hash_password(new_password)
        db.commit()

        return True, None, fresh_key


def change_user_password(
    user_id: int, current_password: str, new_password: str
) -> tuple[bool, str | None]:
    """Change a user's password after verifying the current password."""
    if not isinstance(user_id, int) or user_id <= 0:
        return False, "Invalid user identifier."

    is_valid_pw, pw_err = validate_password(new_password)
    if not is_valid_pw:
        return False, pw_err

    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            return False, "User not found."

        if not verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect."

        user.password_hash = hash_password(new_password)
        db.commit()
        return True, None


def update_security_credentials(
    user_id: int,
    current_password: str,
    security_question: str,
    security_answer: str,
) -> tuple[bool, str | None]:
    """Update a user's security question and answer after verifying current password."""
    if not isinstance(user_id, int) or user_id <= 0:
        return False, "Invalid user identifier."

    valid_q, q_err = validate_security_question(security_question)
    if not valid_q:
        return False, q_err

    valid_a, a_err = validate_security_answer(security_answer)
    if not valid_a:
        return False, a_err

    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            return False, "User not found."

        if not verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect."

        user.security_question = security_question.strip()
        user.security_answer_hash = hash_password(normalize_answer(security_answer))
        db.commit()
        return True, None


def regenerate_recovery_key(
    user_id: int, current_password: str
) -> tuple[str | None, str | None]:
    """Generate and store a new emergency recovery key after verifying password."""
    if not isinstance(user_id, int) or user_id <= 0:
        return None, "Invalid user identifier."

    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            return None, "User not found."

        if not verify_password(current_password, user.password_hash):
            return None, "Current password is incorrect."

        fresh_key = generate_recovery_key()
        user.recovery_key_hash = hash_password(normalize_recovery_key(fresh_key))
        db.commit()

        return fresh_key, None

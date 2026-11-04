"""Cryptographic security utilities for MindTrack AI.

Provides secure password hashing via scrypt (OWASP-recommended),
constant-time password verification against timing attacks,
recovery key generation, and input validation.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets

logger = logging.getLogger(__name__)

# scrypt parameters following OWASP recommendations:
# N=16384 (2^14), r=8, p=1, dklen=64 bytes, 16-byte random salt.
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
SALT_BYTES = 16
MAX_MEM = 33554432  # 32 MB limit

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]+$")

DEFAULT_SECURITY_QUESTIONS: list[str] = [
    "What was the name of your first pet?",
    "What is the name of your favorite book or movie?",
    "In what city or town was your first job?",
    "What was the model of your first car?",
    "What was your childhood nickname?",
    "What is your favorite comfort food?",
]


def hash_password(password: str) -> str:
    """Hash a plaintext password using scrypt with a cryptographically secure random salt."""
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")

    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=MAX_MEM,
        dklen=SCRYPT_DKLEN,
    )
    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$"
        f"{salt.hex()}${derived.hex()}"
    )


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored hash using constant-time comparison."""
    if not password or not hashed or not isinstance(password, str) or not isinstance(hashed, str):
        return False

    try:
        parts = hashed.split("$")
        scheme = parts[0]

        if scheme == "scrypt" and len(parts) == 6:
            _, n_str, r_str, p_str, salt_hex, expected_hex = parts
            computed = hashlib.scrypt(
                password.encode("utf-8"),
                salt=bytes.fromhex(salt_hex),
                n=int(n_str),
                r=int(r_str),
                p=int(p_str),
                maxmem=MAX_MEM,
                dklen=len(bytes.fromhex(expected_hex)),
            )
            return hmac.compare_digest(computed.hex(), expected_hex)

        if scheme == "pbkdf2_sha256" and len(parts) == 4:
            _, iterations_str, salt_hex, expected_hex = parts
            computed = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations_str),
            )
            return hmac.compare_digest(computed.hex(), expected_hex)

        # Fallback for bcrypt if present and hash starts with $2
        if hashed.startswith(("$2a$", "$2b$", "$2y$")):
            try:
                import bcrypt

                return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
            except ImportError:
                logger.warning("Encountered bcrypt hash but bcrypt package is not installed.")
                return False

        return False
    except Exception:
        logger.exception("Error during password verification.")
        return False


def validate_username(username: str) -> tuple[bool, str]:
    """Validate username requirements.

    Returns (is_valid, error_message).
    """
    if not username or not isinstance(username, str):
        return False, "Username cannot be empty."

    clean = username.strip()
    if len(clean) < 3 or len(clean) > 30:
        return False, "Username must be between 3 and 30 characters."

    if not USERNAME_REGEX.match(clean):
        return (
            False,
            "Username may only contain letters, numbers, underscores, dashes, and periods.",
        )

    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password requirements.

    Returns (is_valid, error_message).
    """
    if not password or not isinstance(password, str):
        return False, "Password cannot be empty."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."

    if password.strip() != password or not password.strip():
        return False, "Password cannot consist entirely of whitespace."

    return True, ""


def normalize_answer(answer: str) -> str:
    """Normalize a security answer for case- and whitespace-insensitive comparison."""
    if not answer or not isinstance(answer, str):
        return ""
    return " ".join(answer.strip().lower().split())


def validate_security_question(question: str) -> tuple[bool, str]:
    """Validate security question."""
    if not question or not isinstance(question, str):
        return False, "Security question cannot be empty."
    clean = question.strip()
    if len(clean) < 5:
        return False, "Security question must be at least 5 characters long."
    if len(clean) > 200:
        return False, "Security question cannot exceed 200 characters."
    return True, ""


def validate_security_answer(answer: str) -> tuple[bool, str]:
    """Validate security answer."""
    if not answer or not isinstance(answer, str):
        return False, "Security answer cannot be empty."
    clean = answer.strip()
    if len(clean) < 2:
        return False, "Security answer must be at least 2 characters long."
    if len(clean) > 100:
        return False, "Security answer cannot exceed 100 characters."
    return True, ""


def generate_recovery_key() -> str:
    """Generate a user-friendly 16-character alphanumeric emergency recovery key.

    Example: 'MT-4F1A-98BC-2E03'
    """
    raw = secrets.token_hex(6).upper()  # 12 hex chars
    return f"MT-{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def normalize_recovery_key(key: str) -> str:
    """Normalize emergency recovery key for comparison."""
    if not key or not isinstance(key, str):
        return ""
    return key.strip().upper()

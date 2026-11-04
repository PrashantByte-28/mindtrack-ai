"""Unit tests for user authentication, password hashing, and credentials management."""

from mindtrack_ai.auth import (
    authenticate_user,
    change_user_password,
    get_security_question,
    regenerate_recovery_key,
    register_user,
    reset_password_with_recovery_key,
    reset_password_with_security_answer,
    update_security_credentials,
)
from mindtrack_ai.security import (
    hash_password,
    validate_password,
    validate_username,
    verify_password,
)


def test_password_hashing_and_verification():
    pw = "SuperSecure@2026"
    hashed = hash_password(pw)

    assert hashed.startswith("scrypt$16384$8$1$")
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(pw, "") is False
    assert verify_password(pw, "invalid_hash_string") is False


def test_password_salt_uniqueness():
    pw = "SamePassword123"
    hash1 = hash_password(pw)
    hash2 = hash_password(pw)

    # Different salts must yield different hash strings
    assert hash1 != hash2
    assert verify_password(pw, hash1) is True
    assert verify_password(pw, hash2) is True


def test_username_validation():
    assert validate_username("alice")[0] is True
    assert validate_username("john_doe-99")[0] is True
    assert validate_username("a.b_c")[0] is True

    # Invalid usernames
    assert validate_username("")[0] is False
    assert validate_username("ab")[0] is False  # Too short
    assert validate_username("a" * 31)[0] is False  # Too long
    assert validate_username("user with spaces")[0] is False
    assert validate_username("user@domain")[0] is False


def test_password_validation():
    assert validate_password("validPassword123")[0] is True
    assert validate_password("short")[0] is False  # < 8 chars
    assert validate_password("")[0] is False
    assert validate_password("   ")[0] is False  # Whitespace only


def test_user_registration_and_authentication():
    import uuid

    uname = f"user_{uuid.uuid4().hex[:8]}"
    pw = "StrongPass#2026"

    # Register
    user_dict, err = register_user(uname, pw)
    assert err is None
    assert user_dict is not None
    assert user_dict["username"] == uname
    assert user_dict["id"] > 0

    # Duplicate registration should fail
    dup, dup_err = register_user(uname, pw)
    assert dup is None
    assert "already taken" in dup_err

    # Case-insensitive collision check
    dup_upper, dup_upper_err = register_user(uname.upper(), pw)
    assert dup_upper is None
    assert "already taken" in dup_upper_err

    # Successful authentication
    auth_user, auth_err = authenticate_user(uname, pw)
    assert auth_err is None
    assert auth_user is not None
    assert auth_user["id"] == user_dict["id"]

    # Authentication case-insensitive username match
    auth_upper, _ = authenticate_user(uname.upper(), pw)
    assert auth_upper is not None
    assert auth_upper["id"] == user_dict["id"]

    # Failed authentication with wrong password
    fail_user, fail_err = authenticate_user(uname, "WrongPassword!")
    assert fail_user is None
    assert "Invalid username or password" in fail_err

    # Failed authentication with non-existent username
    non_user, non_err = authenticate_user("non_existent_user_999", pw)
    assert non_user is None
    assert "Invalid username or password" in non_err


def test_change_user_password():
    import uuid

    uname = f"pwd_user_{uuid.uuid4().hex[:8]}"
    old_pw = "OldPassword123"
    new_pw = "NewPassword456"

    user_dict, _ = register_user(uname, old_pw)
    uid = user_dict["id"]

    # Wrong current password
    ok, err = change_user_password(uid, "WrongOldPassword", new_pw)
    assert ok is False
    assert "Current password is incorrect" in err

    # Weak new password
    ok, err = change_user_password(uid, old_pw, "short")
    assert ok is False
    assert "at least 8 characters" in err

    # Successful password change
    ok, err = change_user_password(uid, old_pw, new_pw)
    assert ok is True
    assert err is None

    # Authenticate with new password
    auth_user, _ = authenticate_user(uname, new_pw)
    assert auth_user is not None

    # Old password no longer works
    fail_user, _ = authenticate_user(uname, old_pw)
    assert fail_user is None


def test_forgot_password_with_security_answer():
    import uuid

    uname = f"rec_user_{uuid.uuid4().hex[:8]}"
    initial_pw = "InitialSecret123!"
    question = "What was the name of your first pet?"
    answer = "Fluffy McCloud"

    user_dict, err = register_user(
        uname,
        initial_pw,
        security_question=question,
        security_answer=answer,
    )
    assert err is None
    assert user_dict is not None
    assert user_dict["recovery_key"].startswith("MT-")

    # Look up security question
    fetched_q, q_err = get_security_question(uname)
    assert q_err is None
    assert fetched_q == question

    # Failed reset with wrong answer
    reset_ok, reset_err = reset_password_with_security_answer(
        uname, "Wrong Answer", "BrandNewPass2026!"
    )
    assert reset_ok is False
    assert "Incorrect security answer" in reset_err

    # Failed reset with weak password
    reset_ok, reset_err = reset_password_with_security_answer(
        uname, answer, "short"
    )
    assert reset_ok is False
    assert "at least 8 characters" in reset_err

    # Successful reset with matching answer (testing case-insensitivity and extra whitespace)
    reset_ok, reset_err = reset_password_with_security_answer(
        uname, "   fluffy   mccloud   ", "BrandNewPass2026!"
    )
    assert reset_ok is True
    assert reset_err is None

    # Verify old password is now invalid
    auth_old, _ = authenticate_user(uname, initial_pw)
    assert auth_old is None

    # Verify new password is active
    auth_new, auth_err = authenticate_user(uname, "BrandNewPass2026!")
    assert auth_err is None
    assert auth_new is not None


def test_forgot_password_with_recovery_key():
    import uuid

    uname = f"key_user_{uuid.uuid4().hex[:8]}"
    initial_pw = "InitialKeyPass123!"

    user_dict, err = register_user(uname, initial_pw)
    assert err is None
    recovery_key = user_dict["recovery_key"]
    assert recovery_key.startswith("MT-")

    # Failed reset with bad recovery key
    reset_ok, reset_err, _ = reset_password_with_recovery_key(
        uname, "MT-INVALID-KEY-1234", "NextSecret2026!"
    )
    assert reset_ok is False
    assert "Invalid Emergency Recovery Key" in reset_err

    # Successful reset with recovery key (testing lowercase / whitespace normalization)
    reset_ok, reset_err, new_key = reset_password_with_recovery_key(
        uname, f"  {recovery_key.lower()}  ", "NextSecret2026!"
    )
    assert reset_ok is True
    assert reset_err is None
    assert new_key is not None
    assert new_key != recovery_key  # Key was rotated for single-use protection
    assert new_key.startswith("MT-")

    # Old recovery key should now be exhausted / invalid
    reset_fail, _, _ = reset_password_with_recovery_key(
        uname, recovery_key, "AnotherSecret123!"
    )
    assert reset_fail is False

    # New recovery key works
    reset_second, _, _ = reset_password_with_recovery_key(
        uname, new_key, "AnotherSecret123!"
    )
    assert reset_second is True

    # New password is valid
    auth_user, _ = authenticate_user(uname, "AnotherSecret123!")
    assert auth_user is not None


def test_update_security_credentials_and_regen_key():
    import uuid

    uname = f"upd_user_{uuid.uuid4().hex[:8]}"
    pw = "SecureP@ssword123"

    user_dict, _ = register_user(uname, pw)
    uid = user_dict["id"]

    # Update security question
    new_q = "What was the model of your first car?"
    new_a = "Honda Civic"

    # Fails with wrong password
    ok, err = update_security_credentials(uid, "WrongPass", new_q, new_a)
    assert ok is False
    assert "Current password is incorrect" in err

    # Succeeds with correct password
    ok, err = update_security_credentials(uid, pw, new_q, new_a)
    assert ok is True
    assert err is None

    # Check updated question is reflected
    fetched_q, _ = get_security_question(uname)
    assert fetched_q == new_q

    # Regenerate recovery key
    fresh_key, key_err = regenerate_recovery_key(uid, pw)
    assert key_err is None
    assert fresh_key is not None
    assert fresh_key.startswith("MT-")

    # Recover with fresh key
    reset_ok, _, _ = reset_password_with_recovery_key(
        uname, fresh_key, "UpdatedSecret2026!"
    )
    assert reset_ok is True

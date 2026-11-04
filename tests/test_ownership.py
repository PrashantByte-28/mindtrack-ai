"""Unit tests for per-user data ownership and authorization checks."""

import uuid
from datetime import date

import pytest

from mindtrack_ai.auth import register_user
from mindtrack_ai.chat_service import (
    create_conversation,
    delete_conversation,
    get_conversation,
    get_conversation_messages,
    list_conversations,
    save_message,
)
from mindtrack_ai.mood_service import (
    delete_mood_entry,
    get_mood_entries,
    get_mood_entry,
    save_mood_entry,
)


@pytest.fixture
def test_users():
    u1_name = f"user_a_{uuid.uuid4().hex[:6]}"
    u2_name = f"user_b_{uuid.uuid4().hex[:6]}"
    u1, _ = register_user(u1_name, "PasswordA123!")
    u2, _ = register_user(u2_name, "PasswordB123!")
    return u1["id"], u2["id"]


def test_mood_ownership_isolation(test_users):
    user_a_id, user_b_id = test_users

    # User A saves a mood
    entry_id = save_mood_entry(
        user_id=user_a_id,
        entry_date=date.today(),
        mood="Calm",
        intensity=4,
        note="Peaceful afternoon",
    )

    # User A can retrieve their entry
    entries_a = get_mood_entries(user_a_id)
    assert any(e["id"] == entry_id for e in entries_a)

    single_a = get_mood_entry(user_a_id, entry_id)
    assert single_a is not None
    assert single_a["note"] == "Peaceful afternoon"

    # User B CANNOT see User A's mood in list
    entries_b = get_mood_entries(user_b_id)
    assert not any(e["id"] == entry_id for e in entries_b)

    # User B CANNOT retrieve User A's mood by ID
    with pytest.raises(PermissionError) as exc_info:
        get_mood_entry(user_b_id, entry_id)
    assert "Access denied" in str(exc_info.value)

    # User B CANNOT delete User A's mood
    with pytest.raises(PermissionError) as exc_info:
        delete_mood_entry(user_b_id, entry_id)
    assert "Access denied" in str(exc_info.value)

    # User A CAN delete their own mood
    assert delete_mood_entry(user_a_id, entry_id) is True
    assert get_mood_entry(user_a_id, entry_id) is None


def test_conversation_ownership_isolation(test_users):
    user_a_id, user_b_id = test_users

    # User A creates a conversation
    convo_id = create_conversation(user_id=user_a_id, title="User A Private Chat")
    save_message(user_a_id, convo_id, "user", "I am feeling anxious today.")
    save_message(user_a_id, convo_id, "assistant", "Take a deep breath.")

    # User A can list and view messages
    convos_a = list_conversations(user_a_id)
    assert any(c["id"] == convo_id for c in convos_a)

    msgs_a = get_conversation_messages(user_a_id, convo_id)
    assert len(msgs_a) == 2
    assert msgs_a[0]["content"] == "I am feeling anxious today."

    # User B CANNOT list User A's conversation
    convos_b = list_conversations(user_b_id)
    assert not any(c["id"] == convo_id for c in convos_b)

    # User B CANNOT view User A's conversation
    with pytest.raises(PermissionError) as exc_info:
        get_conversation(user_b_id, convo_id)
    assert "Access denied" in str(exc_info.value)

    # User B CANNOT read User A's messages
    with pytest.raises(PermissionError) as exc_info:
        get_conversation_messages(user_b_id, convo_id)
    assert "Access denied" in str(exc_info.value)

    # User B CANNOT post a message to User A's conversation
    with pytest.raises(PermissionError) as exc_info:
        save_message(user_b_id, convo_id, "user", "Unauthorized message injection")
    assert "Access denied" in str(exc_info.value)

    # User B CANNOT delete User A's conversation
    with pytest.raises(PermissionError) as exc_info:
        delete_conversation(user_b_id, convo_id)
    assert "Access denied" in str(exc_info.value)

    # User A CAN delete their conversation
    assert delete_conversation(user_a_id, convo_id) is True
    assert get_conversation_messages(user_a_id, convo_id) == []

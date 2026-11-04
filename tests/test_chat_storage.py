"""Test conversation and message persistence."""

from mindtrack_ai.auth import register_user
from mindtrack_ai.chat_service import (
    create_conversation,
    delete_conversation,
    get_conversation_messages,
    list_conversations,
    save_message,
)


def test_chat_storage():
    # Ensure test user exists
    user_dict, _ = register_user("test_chat_user", "ValidPassword123!")
    if user_dict is None:
        from mindtrack_ai.auth import get_user_by_username

        user_dict = get_user_by_username("test_chat_user")

    user_id = user_dict["id"]
    conversation_id = create_conversation(user_id=user_id)

    save_message(
        user_id,
        conversation_id,
        "user",
        "I've been stressed about assignments.",
    )
    save_message(
        user_id,
        conversation_id,
        "assistant",
        "Try breaking your assignments into smaller tasks.",
    )

    messages = get_conversation_messages(user_id, conversation_id)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    conversations = list_conversations(user_id)
    assert any(item["id"] == conversation_id for item in conversations)

    assert delete_conversation(user_id, conversation_id) is True
    assert get_conversation_messages(user_id, conversation_id) == []

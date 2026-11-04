from datetime import datetime
from typing import Any

from mindtrack_ai import database
from mindtrack_ai.database import (
    ChatMessage,
    Conversation,
)


def create_conversation(user_id: int, title: str = "New conversation") -> int:
    """Create a conversation owned by user_id and return its database ID."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    clean_title = title.strip() or "New conversation"

    with database.SessionLocal() as db:
        conversation = Conversation(
            user_id=user_id,
            title=clean_title[:100],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation.id


def list_conversations(user_id: int) -> list[dict[str, Any]]:
    """Return conversations owned by user_id, newest activity first."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    with database.SessionLocal() as db:
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(
                Conversation.updated_at.desc(),
                Conversation.id.desc(),
            )
            .all()
        )

        return [
            {
                "id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
            }
            for conversation in conversations
        ]


def get_conversation(user_id: int, conversation_id: int) -> dict[str, Any] | None:
    """Get a single conversation with per-user ownership verification."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(conversation_id, int) or conversation_id <= 0:
        raise ValueError("A valid conversation ID is required.")

    with database.SessionLocal() as db:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None:
            return None

        if conversation.user_id != user_id:
            raise PermissionError("Access denied: You do not own this conversation.")

        return {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }


def get_conversation_messages(
    user_id: int,
    conversation_id: int,
) -> list[dict[str, str]]:
    """Load persisted messages in chronological order with ownership verification."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(conversation_id, int) or conversation_id <= 0:
        raise ValueError("A valid conversation ID is required.")

    with database.SessionLocal() as db:
        conversation = db.get(Conversation, conversation_id)

        if conversation is None:
            return []

        if conversation.user_id != user_id:
            raise PermissionError("Access denied: You do not own this conversation.")

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            .all()
        )

        return [
            {"role": message.role, "content": message.content}
            for message in messages
        ]


def save_message(
    user_id: int,
    conversation_id: int,
    role: str,
    content: str,
) -> None:
    """Persist one user or assistant message with ownership check."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if role not in {"user", "assistant"}:
        raise ValueError("Role must be 'user' or 'assistant'.")

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Message content cannot be empty.")

    clean_content = content.strip()

    with database.SessionLocal() as db:
        conversation = db.get(Conversation, conversation_id)

        if conversation is None:
            raise ValueError("Conversation does not exist.")

        if conversation.user_id != user_id:
            raise PermissionError("Access denied: You do not own this conversation.")

        message = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=clean_content,
            created_at=datetime.now(),
        )
        db.add(message)

        # Give a new chat a useful title based on the first user message.
        if role == "user" and conversation.title == "New conversation":
            title = " ".join(clean_content.split())
            conversation.title = (
                title[:57] + "..."
                if len(title) > 60
                else title
            )

        conversation.updated_at = datetime.now()
        db.commit()


def delete_conversation(user_id: int, conversation_id: int) -> bool:
    """Delete one conversation and its related messages with ownership verification."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(conversation_id, int) or conversation_id <= 0:
        raise ValueError("A valid conversation ID is required.")

    with database.SessionLocal() as db:
        conversation = db.get(Conversation, conversation_id)

        if conversation is None:
            return False

        if conversation.user_id != user_id:
            raise PermissionError("Access denied: You do not own this conversation.")

        db.delete(conversation)
        db.commit()
        return True

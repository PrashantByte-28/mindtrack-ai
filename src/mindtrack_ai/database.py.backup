from datetime import date, datetime
from pathlib import Path

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

# Store the database in the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "mindtrack.db"

engine = create_engine(
    f"sqlite:///{DATABASE_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# 1. User authentication model

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    security_question: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    security_answer_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    recovery_key_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    mood_entries = relationship(
        "MoodEntry",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )


# 2. Mood tracking model with per-user ownership

class MoodEntry(Base):
    __tablename__ = "mood_entries"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    mood: Mapped[str] = mapped_column(String(30))
    intensity: Mapped[int] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    user = relationship("User", back_populates="mood_entries")


# 3. Conversation model with per-user ownership

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(
        String(100), nullable=False, default="New conversation"
    )
    created_at = Column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


# 4. Individual chat messages

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime, default=datetime.now, nullable=False
    )

    conversation = relationship(
        "Conversation", back_populates="messages"
    )


# 5. Initialize AFTER every model is registered and run migrations
def init_db() -> None:
    from mindtrack_ai.migration import migrate_database

    migrate_database(DATABASE_PATH)
    Base.metadata.create_all(bind=engine)


init_db()

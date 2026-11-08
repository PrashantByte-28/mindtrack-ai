import os
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
from sqlalchemy.engine import make_url
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

# Project configuration
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Where the local SQLite file lives. Set MINDTRACK_DB_PATH to keep it somewhere
# that survives restarts (for example a Docker volume mounted at /data).
DATABASE_PATH = Path(
    os.getenv("MINDTRACK_DB_PATH") or (PROJECT_ROOT / "mindtrack.db")
).expanduser().resolve()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Use PostgreSQL in production when DATABASE_URL is configured.
# Otherwise, use the existing local SQLite database.
database_url = os.getenv("DATABASE_URL")

if not database_url:
    database_url = f"sqlite:///{DATABASE_PATH.as_posix()}"

# Normalize PostgreSQL URLs for Psycopg 3.
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql+psycopg://",
        1,
    )
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

database_backend = make_url(database_url).get_backend_name()

# SQLite-specific connection settings.
connect_args = (
    {"check_same_thread": False}
    if database_backend == "sqlite"
    else {}
)

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# Enable foreign keys only for SQLite.
if database_backend == "sqlite":

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


# 2. Mood tracking model

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


# 3. Conversation model

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


# 5. Database initialization

def init_db() -> None:
    if database_backend == "sqlite":
        # Keep the existing SQLite migration for local development.
        from mindtrack_ai.migration import migrate_database

        migrate_database(DATABASE_PATH)

    # Create missing tables for either database backend.
    Base.metadata.create_all(bind=engine)

def _describe_database() -> str:
    """Return a safe, human-readable description of the active database."""
    url = make_url(database_url)
    if database_backend == "sqlite":
        db_file = Path(url.database).resolve()
        size = db_file.stat().st_size if db_file.exists() else 0
        return f"SQLite file {db_file} (exists={db_file.exists()}, {size} bytes)"
    # Never print the password.
    return f"{database_backend} at {url.host}:{url.port}/{url.database}"


def _print_database_target() -> None:
    """Print which database this run is using, so it is obvious after a restart."""
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        print(
            f"[MindTrack] Database: {_describe_database()} | users: {user_count} | "
            f"DATABASE_URL env var set: {bool(os.getenv('DATABASE_URL'))}",
            flush=True,
        )
    except Exception as exc:  # diagnostics must never stop the app
        print(f"[MindTrack] Could not describe database: {exc}", flush=True)


init_db()
_print_database_target()
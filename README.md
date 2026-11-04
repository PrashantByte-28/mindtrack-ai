# 🌿 MindTrack AI

MindTrack AI is an AI-powered personal wellness space designed for daily mood tracking, reflective journaling, conversational support, and longitudinal wellness insights.

---

## ✨ Features

- **🌤️ Daily Check-ins**: Log your daily mood with intensity levels (1–5) and optional personal reflection notes.
- **💬 AI Companion**: Empathetic conversational partner powered by LLMs with integrated safety crisis checks.
- **📊 Longitudinal Insights**: Advanced analytics with rolling averages, weekday patterns, intensity trends, and downloadable PDF reports.
- **🔐 User Authentication**: Multi-user account registration, secure sign-in, session isolation, and password updates.
- **❓ Forgot Password & Account Recovery**: Comprehensive self-service recovery during sign-in using either **Security Questions & Answers** or **Emergency Recovery Keys** (`MT-XXXX-XXXX-XXXX`).
- **🛡️ Strict Per-User Ownership**: Database records (mood check-ins, conversations, and messages) are strictly isolated per user and guarded by authorization checks.
- **🔒 Secure Password Hashing**: Utilizes OWASP-recommended **scrypt** with cryptographically secure random salts and constant-time digest verification.
- **📦 Safe SQLite Migration**: Zero data loss database migration that automatically creates timestamped backups and safely upgrades existing records and schemas.

---

## 🔐 Authentication & Account Recovery

### 1. Password Hashing (`mindtrack_ai.security`)
- **Algorithm**: `hashlib.scrypt` (OWASP-recommended standard).
- **Parameters**: `N=16384` ($2^{14}$), `r=8`, `p=1`, `dklen=64`.
- **Salt**: 16 cryptographically secure random bytes via `secrets.token_bytes(16)`.
- **Verification**: Constant-time comparison with `hmac.compare_digest` to prevent timing attacks.
- **Validation**: Enforces minimum 8-character passwords and valid alphanumeric/symbolic usernames.

### 2. Forgot Password & Recovery (`mindtrack_ai.auth`, `app.py`)
- **Sign-In Recovery Tab**: The sign-in interface features a dedicated **❓ Forgot Password** tab offering two secure recovery pathways:
  1. **Security Question & Answer**: Users answer their chosen security question. Answers are securely hashed with scrypt and matched case-insensitively. An interactive question lookup tool is provided if the user forgets which question was configured.
  2. **Emergency Recovery Key**: Users can enter their 16-character alphanumeric recovery key (`MT-XXXX-XXXX-XXXX`). To ensure single-use protection, keys are automatically rotated upon successful recovery.
- **Authenticated Management**: Signed-in users can update their security question or generate new emergency recovery keys from the sidebar at any time.

### 3. Per-User Ownership Checks (`mindtrack_ai.mood_service`, `mindtrack_ai.chat_service`)
- All records in `mood_entries` and `conversations` require a foreign key `user_id`.
- Service layer methods enforce ownership verification on all operations:
  - `get_mood_entries(user_id)` / `get_mood_entry(user_id, entry_id)`
  - `delete_mood_entry(user_id, entry_id)`
  - `list_conversations(user_id)` / `get_conversation(user_id, conversation_id)`
  - `get_conversation_messages(user_id, conversation_id)`
  - `save_message(user_id, conversation_id, role, content)`
  - `delete_conversation(user_id, conversation_id)`
- Unauthorized attempts to read, modify, or delete another user's records raise explicit `PermissionError` exceptions.

### 4. Safe Database Migration (`mindtrack_ai.migration`)
- Automatically creates a timestamped database backup (`mindtrack.backup_<timestamp>.db`) before altering any schema.
- Idempotently creates the `users` table and adds `security_question`, `security_answer_hash`, `recovery_key_hash`, and `user_id` foreign keys.
- Legacy records that existed prior to multi-user authentication are automatically migrated and associated with the default legacy account:
  - **Username**: `mindtrack_user`
  - **Default Password**: `MindTrack2026!`
  - **Default Security Question**: *"What is the name of this wellness companion?"* (Answer: `MindTrack`)
- Can be invoked manually via:
  ```bash
  python -m mindtrack_ai.migration
  ```
  or runs automatically upon application initialization.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.14+
- `uv` package manager (or virtualenv)

### Installation
```bash
# Clone the repository and install dependencies
uv sync
```

### Running the Application
```bash
uv run streamlit run app.py
```

### Running Tests
The test suite includes complete test isolation with ephemeral SQLite databases:
```bash
uv run pytest -v
```

---

## 📂 Project Structure

```
mindtrack-ai/
├── app.py                      # Streamlit application UI & session handling
├── mindtrack.db                # SQLite database with users and records
├── pyproject.toml              # Dependencies & pytest configuration
├── src/
│   └── mindtrack_ai/
│       ├── auth.py             # User registration, authentication, & password recovery services
│       ├── security.py         # scrypt password hashing, recovery key generation & validation utilities
│       ├── migration.py        # Safe, idempotent SQLite migration & backup runner
│       ├── database.py         # SQLAlchemy models (User, MoodEntry, Conversation, ChatMessage)
│       ├── mood_service.py     # Mood check-in CRUD with ownership verification
│       ├── chat_service.py     # AI chat history CRUD with ownership verification
│       ├── llm_service.py      # LLM response generation
│       ├── safety.py           # Crisis keyword detection & safety responses
│       ├── insight_service.py  # Trend analysis & reflection prompts
│       └── report_service.py   # PDF report generation via ReportLab
└── tests/
    ├── conftest.py             # Isolated SQLite test database fixture
    ├── test_auth.py            # Authentication, hashing, recovery & validation tests
    ├── test_ownership.py       # Per-user ownership & authorization isolation tests
    ├── test_migration.py       # Database migration & idempotence tests
    ├── test_chat_storage.py    # Conversation persistence tests
    └── test_safety.py          # Safety filter test suite
```

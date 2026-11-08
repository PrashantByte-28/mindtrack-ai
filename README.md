# 🌿 MindTrack AI

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://mindtrack-wellness-ai.streamlit.app)

**Live demo: [mindtrack-wellness-ai.streamlit.app](https://mindtrack-wellness-ai.streamlit.app)**

MindTrack AI is an interactive mental wellness and analytics app. It is a private, personal daily companion where you can log how you feel, talk with a supportive AI assistant, and see your mood patterns over time on a data-driven dashboard.

> **Disclaimer:** MindTrack AI is a wellness companion and self-reflection tool. It is not a diagnostic tool and not a replacement for professional mental healthcare. If you are in crisis or thinking about harming yourself, please contact local emergency services or a crisis helpline.

---

## ✨ Features

- **Secure accounts and recovery:** sign-up and sign-in with passwords hashed using scrypt. If you forget your password you can recover your account with a security question or a single-use emergency recovery key (format `MT-XXXX-XXXX-XXXX`). You can change your password and update your recovery options from the sidebar.
- **Daily check-in:** choose a mood, set an intensity from 1 to 5, and add an optional private note. Recent check-ins are listed on the same page.
- **AI companion:** a conversational assistant powered by Groq for reflecting on your day, with saved conversation history. A safety layer detects crisis-level messages and responds with support resources.
- **Mood insights dashboard:** KPIs, mood-distribution charts, weekly breakdowns, and trend analysis with a 7-day rolling average, filtered by a date range you choose.
- **AI-generated insights:** personalized written reflections based on the data you have filtered on the dashboard.
- **Reports:** download your mood records as CSV or as a formatted PDF.
- **Midnight Glow interface:** a dark, modern UI with time-aware greetings, toast notifications, and friendly empty states.

---

## 🛠️ Tech stack

| Area | Technology |
| --- | --- |
| App and UI | Python, Streamlit |
| Data processing | Pandas, NumPy |
| Charts | Plotly (Express and Graph Objects) |
| Database access | SQLAlchemy |
| Database | SQLite for local use, PostgreSQL for the hosted app (Neon) |
| AI | Groq API |
| Security | scrypt password hashing |
| Reports | ReportLab (PDF) |

---

## 🌐 Live deployment

The app is hosted on **Streamlit Community Cloud** at **https://mindtrack-wellness-ai.streamlit.app**, with user data stored in a free **Neon PostgreSQL** database.

Things to know about the demo:

- Free apps go to sleep when nobody has used them for a while. The first visit after a quiet period can take a little longer while the app wakes up.
- Accounts and check-ins are stored in the database, so they survive restarts and redeploys.
- It is a public demo. Please do not enter sensitive personal information.

---

## 🚀 Run it locally

You need **Python 3.14** (the version this project is built and deployed with) and a [Groq API key](https://console.groq.com).

### 1. Clone the repository

```bash
git clone https://github.com/PrashantByte-28/mindtrack-ai.git
cd mindtrack-ai
```

### 2. Install dependencies

With [uv](https://docs.astral.sh/uv/) (uses the included `uv.lock`):

```bash
uv sync
```

Or with pip:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables

Create a file named `.env` in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=your_groq_model_name
```

| Variable | Required | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes | Key for the AI companion and insights |
| `GROQ_MODEL` | No | Groq model to use (a default is built in) |
| `GOOGLE_API_KEY` | No | Optional Google key |
| `DATABASE_URL` | No | PostgreSQL connection string. If it is not set, the app uses a local SQLite file (`mindtrack.db`) |
| `MINDTRACK_DB_PATH` | No | Custom location for the SQLite file (used by Docker) |

Never commit your `.env` file. It is already listed in `.gitignore`.

### 4. Start the app

```bash
streamlit run app.py
```

(or `uv run streamlit run app.py`). Open **http://localhost:8501**.

When the app starts, the terminal prints a line like `[MindTrack] Database: ... | users: N`. It shows which database is in use and how many accounts it contains.

---

## 🐳 Run with Docker

Docker keeps the SQLite database on a named volume, so accounts survive container restarts. Put your keys in a `.env` file first, then run:

```bash
docker compose up --build
```

Open **http://localhost:8501**. Stop the app with `Ctrl+C` or `docker compose down`. Do **not** use `docker compose down -v`, because that deletes the volume and all accounts.

---

## ☁️ Deploy your own copy on Streamlit Community Cloud

Streamlit Community Cloud does not keep files between restarts, so a local SQLite file would lose all accounts. Use a free hosted PostgreSQL database instead.

1. **Create a free PostgreSQL database**, for example on [Neon](https://neon.com), and copy its connection string (it starts with `postgresql://`).
2. **Push this repository to your GitHub account.**
3. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, and choose **Create app**. Select your repository, branch `main`, and main file `app.py`.
4. Open **Advanced settings**:
   - Set the **Python version** to **3.14**.
   - Paste your secrets (see `.streamlit/secrets.toml.example` for the template):

     ```toml
     GROQ_API_KEY = "your-groq-api-key"
     GROQ_MODEL = "your-groq-model-name"
     DATABASE_URL = "postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require"
     ```
5. Click **Deploy**. In the app logs, look for `[MindTrack] Database: postgresql at ...` to confirm the database connection.

The app copies Streamlit secrets into environment variables on startup, so the same code runs locally and in the cloud. Every `git push` to the deployed branch redeploys the app automatically.

---

## 📂 Project structure

```text
mindtrack-ai/
├── app.py                      # Streamlit application entry point
├── pyproject.toml              # Project metadata and dependencies
├── uv.lock                     # Locked dependency versions
├── requirements.txt            # Dependency list for pip
├── Dockerfile                  # Container image
├── docker-compose.yml          # Container setup with a persistent data volume
├── .streamlit/
│   └── secrets.toml.example    # Template for Streamlit Cloud secrets
├── src/
│   └── mindtrack_ai/
│       ├── auth.py             # Registration, sign-in, password recovery
│       ├── security.py         # Password hashing and input validation
│       ├── database.py         # Database models and connection (SQLite / PostgreSQL)
│       ├── migration.py        # Safe SQLite schema migration
│       ├── mood_service.py     # Mood check-in storage
│       ├── chat_service.py     # Conversation and message storage
│       ├── llm_service.py      # Groq integration and prompts
│       ├── insight_service.py  # AI-generated insights
│       ├── trend_service.py    # Mood trend calculations
│       ├── report_service.py   # CSV and PDF reports
│       ├── safety.py           # Crisis detection and support resources
│       ├── config.py           # API key loading
│       └── schemas.py          # Data schemas
└── tests/                      # Automated tests (pytest)
```

---

## ✅ Tests

```bash
pytest
```

The tests use their own temporary database, so they never touch your real data.

---

## 📄 License

Released under the MIT License.

---

## 👤 Author

Built by [PrashantByte-28](https://github.com/PrashantByte-28).
🌿 MindTrack AI

MindTrack AI is an interactive mental wellness and analytics platform. It serves as a secure, personalized daily wellness companion that empowers users to log their emotions, converse with an empathetic AI agent, and visualize long-term mood patterns through a data-driven dashboard.

Disclaimer: MindTrack AI is a wellness companion and self-reflection tool, not a diagnostic tool or a replacement for professional mental healthcare.

✨ Features

🔒 Secure User Authentication & Recovery: Custom auth system with secure profile management. Includes recovery via hashed custom security questions and auto-generated, single-use 16-character emergency recovery keys.

📝 Daily Mood Check-ins: Log your emotional state by selecting categorized moods (Happy, Calm, Anxious, etc.), setting an intensity level (1-5), and adding an optional private journal note.

💬 Persistent AI Wellness Companion: A context-aware conversational AI that provides a safe space to reflect on your day. Includes a critical safety layer that intercepts crisis-level messages and provides automated safety resources.

📊 Advanced Mood Analytics Dashboard: Interactive data visualizations using custom date ranges. Features include KPIs, time-series tracking with a 7-day rolling average, and check-in frequency distributions mapped by weekday.

🧠 Automated AI Insights & Reporting: Leverages LLMs to analyze your filtered dashboard data and generate personalized, descriptive reflections. Export your records easily to CSV or formatted PDF reports.

🎨 Dynamic "Midnight Glow" UI: A modern, vibrant interface built with micro-animations, time-aware greetings, non-blocking toast notifications, and conversational empty states to make the app feel alive and welcoming.

🛠️ Tech Stack

Frontend & Application Logic: Python and Streamlit

Data Processing: Pandas

Data Visualization: Plotly Express & Graph Objects

Database: SQLite (Lightweight, local relational data storage)

AI / LLM Integration: Groq API (for conversational agent and automated insights)

🚀 Installation and Setup

Follow these steps to get the project running on your local machine.

1. Clone the repository

git clone https://github.com/yourusername/mindtrack-ai.git
cd mindtrack-ai


2. Create and activate a virtual environment

# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate


3. Install dependencies

pip install -r requirements.txt


4. Configure Environment Variables

Create a .env file in the root directory and add your necessary API keys (e.g., Groq API key) and database configurations:

GROQ_API_KEY=your_groq_api_key_here
# Add any other required environment variables here


5. Run the application

streamlit run app.py


The application will launch in your default web browser, typically at http://localhost:8501.

📂 Project Structure

mindtrack-ai/
│
├── app.py                  # Main Streamlit application entry point
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables file
└── src/
    └── mindtrack_ai/       # Core application logic and services
        ├── auth.py         # Authentication and recovery logic
        ├── chat_service.py # Database interactions for chat history
        ├── insight_service.py # AI insight generation logic
        ├── llm_service.py  # LLM integration and prompt handling
        ├── mood_service.py # Mood entry database operations
        ├── report_service.py # PDF/CSV report generation
        ├── safety.py       # Message safety checking & crisis resources
        ├── security.py     # Encryption and security defaults
        └── trend_service.py# Data processing for mood trends


This project is licensed under the MIT License - see the LICENSE file for details.# mindtrack-ai

import logging
import sys
from datetime import date
from pathlib import Path

# Ensure 'src' and project root are always on sys.path regardless of how Streamlit or Python is launched
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
for _p in (str(SRC_DIR), str(PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pandas as pd
import plotly.express as px
import streamlit as st

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
from mindtrack_ai.chat_service import (
    create_conversation,
    delete_conversation,
    get_conversation_messages,
    list_conversations,
    save_message,
)
from mindtrack_ai.insight_service import generate_mood_insights
from mindtrack_ai.llm_service import generate_response
from mindtrack_ai.mood_service import (
    delete_mood_entry,
    get_mood_entries,
    save_mood_entry,
)
from mindtrack_ai.report_service import build_mood_pdf_report
from mindtrack_ai.safety import (
    CRISIS_MESSAGE,
    check_message_safety,
)
from mindtrack_ai.security import DEFAULT_SECURITY_QUESTIONS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="MindTrack AI",
    page_icon="🌿",
    layout="wide",
)

# Modern, responsive theme
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    :root{--mt-primary:#8ED6B0;--mt-primary-dark:#B1E8C8;--mt-mint:#223B32;--mt-cream:#172B25;--mt-text:#F0F4EC;--mt-muted:#B4C7BC;--mt-border:#3B584B;--mt-glass:rgba(34,59,50,.58);--mt-glow:rgba(142,214,176,.35);--mt-ease:cubic-bezier(.22,.8,.3,1)}
    html{scroll-behavior:smooth}
    ::selection{background:rgba(142,214,176,.35);color:#fff}
    ::-webkit-scrollbar{width:10px;height:10px}
    ::-webkit-scrollbar-track{background:transparent}
    ::-webkit-scrollbar-thumb{background:#3B584B;border-radius:10px;border:2px solid transparent;background-clip:padding-box}
    ::-webkit-scrollbar-thumb:hover{background:#557966;background-clip:padding-box}
    @keyframes mtRise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
    @keyframes mtFloat{0%,100%{transform:translate(0,0)}50%{transform:translate(-30px,40px)}}
    @keyframes mtSpin{to{transform:rotate(360deg)}}
    @keyframes mtPulse{0%{box-shadow:0 0 0 0 rgba(142,214,176,.6)}100%{box-shadow:0 0 0 10px rgba(142,214,176,0)}}
    @keyframes mtSway{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(8deg)}}
    @keyframes mtShimmer{from{background-position:0% 50%}to{background-position:100% 50%}}
    @keyframes mtCycle{0%{opacity:0;transform:translateY(8px)}5%,30%{opacity:1;transform:none}35%,100%{opacity:0;transform:translateY(-8px)}}

    .stApp{isolation:isolate;color:var(--mt-text);background:radial-gradient(900px 500px at 5% -5%,rgba(142,214,176,.16),transparent 60%),radial-gradient(800px 500px at 100% 10%,rgba(169,164,216,.12),transparent 60%),radial-gradient(700px 500px at 50% 110%,rgba(242,184,128,.10),transparent 60%),linear-gradient(145deg,#12221B 0%,#1A2F27 55%,#20382E 100%);background-attachment:fixed}
    .stApp::before,.stApp::after{content:"";position:fixed;border-radius:50%;filter:blur(40px);pointer-events:none;z-index:-1;animation:mtFloat 16s ease-in-out infinite}
    .stApp::before{width:420px;height:420px;top:-120px;right:-100px;background:radial-gradient(circle,rgba(142,214,176,.20),transparent 70%)}
    .stApp::after{width:360px;height:360px;bottom:-120px;left:-100px;background:radial-gradient(circle,rgba(169,164,216,.16),transparent 70%);animation-delay:-6s}
    [data-testid="stHeader"]{background:transparent}
    footer{visibility:hidden}
    .block-container{max-width:1450px;padding-top:1.6rem;padding-bottom:5rem}
    .stApp,.stApp p,.stApp label,.stApp li,.stApp button,.stApp input,.stApp textarea,.stApp h1,.stApp h2,.stApp h3,.stApp h4{font-family:'Plus Jakarta Sans','Segoe UI',system-ui,-apple-system,sans-serif!important}
    h1,h2,h3,h4,[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,label{color:var(--mt-text)!important}
    h2,h3,h4{font-weight:750!important;letter-spacing:-.01em}
    [data-testid="stCaptionContainer"],[data-testid="stMetricLabel"]{color:var(--mt-muted)!important}
    hr{border:none!important;height:1px;background:linear-gradient(90deg,transparent,#3B584B,transparent)!important}

    /* Hero */
    .mt-hero{position:relative;overflow:hidden;isolation:isolate;padding:clamp(20px,3.5vw,34px) clamp(18px,3.5vw,38px);margin-bottom:18px;border-radius:26px;background:linear-gradient(125deg,rgba(41,72,58,.94),rgba(27,48,40,.94) 55%,rgba(38,56,64,.88));border:1px solid rgba(142,214,176,.28);box-shadow:0 20px 60px rgba(0,0,0,.32),inset 0 1px 0 rgba(255,255,255,.06);transition:transform .3s var(--mt-ease),box-shadow .3s;animation:mtRise .6s var(--mt-ease) both}
    .mt-hero::before{content:"";position:absolute;inset:-60%;z-index:-1;background:conic-gradient(from 0deg,transparent 0,rgba(142,214,176,.16) 12%,transparent 30%);animation:mtSpin 20s linear infinite}
    .mt-hero:hover{transform:translateY(-3px);box-shadow:0 26px 70px rgba(0,0,0,.4),0 0 40px var(--mt-glow)}
    .mt-leaf{position:absolute;top:14px;right:clamp(14px,4vw,40px);font-size:clamp(40px,7vw,76px);transform-origin:bottom center;animation:mtSway 6s ease-in-out infinite;filter:drop-shadow(0 8px 18px rgba(142,214,176,.4));user-select:none}
    .mt-eyebrow{display:inline-flex;align-items:center;gap:8px;padding:6px 13px;border-radius:999px;font-size:11.5px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;color:#8ED6B0;background:rgba(142,214,176,.12);border:1px solid rgba(142,214,176,.3)}
    .mt-dot{width:8px;height:8px;border-radius:50%;background:#8ED6B0;animation:mtPulse 2s infinite}
    .mt-title{margin:12px 0 6px;font-size:clamp(30px,5vw,50px);font-weight:800;line-height:1.1;letter-spacing:-.02em;color:transparent;background:linear-gradient(90deg,#F0F4EC,#B1E8C8 40%,#8ED6B0 65%,#F2B880 100%);background-size:200% auto;-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;animation:mtShimmer 6s ease-in-out infinite alternate}
    .mt-sub{margin-bottom:10px;font-size:clamp(14px,1.8vw,17px);color:#B4C7BC}
    .mt-affirm{position:relative;min-height:1.8em;margin-bottom:14px;font-size:clamp(13px,1.6vw,15px);font-weight:600;color:#F2B880}
    .mt-affirm span{position:absolute;left:0;right:0;top:0;opacity:0;animation:mtCycle 12s infinite}
    .mt-affirm span:nth-child(2){animation-delay:4s}
    .mt-affirm span:nth-child(3){animation-delay:8s}
    .mt-chips{display:flex;flex-wrap:wrap;gap:10px}
    .mt-chip{cursor:default;padding:8px 15px;border-radius:999px;font-size:14px;font-weight:600;color:#E6EFE8;background:rgba(255,255,255,.05);border:1px solid rgba(142,214,176,.24);transition:transform .3s cubic-bezier(.34,1.56,.64,1),background .2s,border-color .2s,box-shadow .2s}
    .mt-chip:hover{transform:translateY(-4px) scale(1.07) rotate(-2deg);background:rgba(142,214,176,.2);border-color:#8ED6B0;box-shadow:0 8px 22px rgba(142,214,176,.28)}

    /* Tabs as a pill switcher */
    [data-baseweb="tab-list"]{gap:6px;padding:6px;overflow-x:auto;scrollbar-width:none;border-radius:18px;background:rgba(23,43,37,.72);border:1px solid var(--mt-border);backdrop-filter:blur(10px)}
    [data-baseweb="tab-list"]::-webkit-scrollbar{display:none}
    [data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none!important}
    button[data-baseweb="tab"]{flex:1 1 auto;justify-content:center;height:auto;padding:10px 18px;white-space:nowrap;border-radius:13px;background:transparent;color:var(--mt-muted);font-weight:700;transition:all .25s var(--mt-ease)}
    button[data-baseweb="tab"] p{color:inherit!important;font-weight:700}
    button[data-baseweb="tab"]:hover{background:rgba(142,214,176,.13);color:#fff;transform:translateY(-1px)}
    button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(135deg,#8ED6B0,#B1E8C8);color:#0E1F18!important;box-shadow:0 6px 18px rgba(142,214,176,.35)}
    button[data-baseweb="tab"][aria-selected="true"] p{color:#0E1F18!important}
    [data-baseweb="tab-panel"]{padding-top:1.2rem;animation:mtRise .5s var(--mt-ease) both}

    /* Cards */
    [data-testid="stForm"]{padding:1.4rem 1.4rem 1rem;border-radius:22px;background:var(--mt-glass);border:1px solid var(--mt-border)!important;backdrop-filter:blur(14px);box-shadow:0 10px 40px rgba(0,0,0,.22);transition:border-color .3s,box-shadow .3s}
    [data-testid="stForm"]:hover{border-color:rgba(142,214,176,.5)!important;box-shadow:0 14px 48px rgba(0,0,0,.3),0 0 24px rgba(142,214,176,.12)}
    [data-testid="stMetric"]{position:relative;overflow:hidden;padding:18px 20px;border-radius:18px;background:linear-gradient(160deg,rgba(41,72,58,.8),rgba(34,59,50,.6));border:1px solid var(--mt-border);box-shadow:0 6px 20px rgba(0,0,0,.16);transition:transform .25s var(--mt-ease),box-shadow .25s,border-color .25s}
    [data-testid="stMetric"]::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,#8ED6B0,#F2B880,#A9A4D8)}
    [data-testid="stMetric"]:hover{transform:translateY(-4px);border-color:#8ED6B0;box-shadow:0 16px 34px rgba(0,0,0,.3),0 0 22px var(--mt-glow)}
    [data-testid="stMetricValue"]{color:#8ED6B0!important;font-weight:800}
    [data-testid="stMetricValue"] > div{white-space:normal!important;overflow-wrap:anywhere}
    [data-testid="stPlotlyChart"]{padding:10px 8px 4px;overflow:hidden;border-radius:20px;background:var(--mt-glass);border:1px solid var(--mt-border);backdrop-filter:blur(8px);box-shadow:0 8px 26px rgba(0,0,0,.18);transition:transform .25s var(--mt-ease),box-shadow .25s,border-color .25s}
    [data-testid="stPlotlyChart"]:hover{transform:translateY(-3px);border-color:rgba(142,214,176,.55);box-shadow:0 16px 36px rgba(0,0,0,.3),0 0 22px rgba(142,214,176,.18)}
    .js-plotly-plot .main-svg,.js-plotly-plot .svg-container{background:transparent!important}
    .js-plotly-plot .plotly .bg{fill:transparent!important}
    .js-plotly-plot .plotly .gtitle,.js-plotly-plot .plotly .xtitle,.js-plotly-plot .plotly .ytitle,.js-plotly-plot .plotly .xtick text,.js-plotly-plot .plotly .ytick text,.js-plotly-plot .plotly .legendtext{fill:#DCE8E0!important}
    .js-plotly-plot .plotly .gridlayer path,.js-plotly-plot .plotly .zerolinelayer path{stroke:rgba(180,199,188,.16)!important}
    [data-testid="stDataFrame"]{overflow:hidden;border-radius:16px;border:1px solid var(--mt-border);box-shadow:0 6px 20px rgba(0,0,0,.16);transition:border-color .25s,box-shadow .25s}
    [data-testid="stDataFrame"]:hover{border-color:rgba(142,214,176,.5);box-shadow:0 10px 28px rgba(0,0,0,.26)}
    [data-testid="stExpander"]{background:transparent;border:none!important}
    [data-testid="stExpander"] details{overflow:hidden;border-radius:16px;background:var(--mt-glass);border:1px solid var(--mt-border)!important;transition:border-color .25s,box-shadow .25s}
    [data-testid="stExpander"] details:hover{border-color:rgba(142,214,176,.5)!important;box-shadow:0 8px 24px rgba(0,0,0,.2)}
    [data-testid="stExpander"] summary{padding:.85rem 1rem;font-weight:650;transition:background .2s}
    [data-testid="stExpander"] summary:hover{background:rgba(142,214,176,.10)}
    [data-testid="stExpander"] summary:hover p{color:#8ED6B0!important}
    [data-testid="stAlert"]{border-radius:16px;border:1px solid rgba(255,255,255,.08);backdrop-filter:blur(6px);box-shadow:0 6px 22px rgba(0,0,0,.18);animation:mtRise .4s var(--mt-ease) both;transition:transform .2s}
    [data-testid="stAlert"]:hover{transform:translateY(-2px)}

    /* Buttons */
    .stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button{position:relative;overflow:hidden;min-height:46px;padding:.6rem 1.1rem;border-radius:14px;border:1px solid #557966;background:linear-gradient(180deg,#2F5242,#29483A);color:#F0F4EC;font-weight:700;transition:transform .2s var(--mt-ease),box-shadow .2s,border-color .2s,background .2s}
    .stButton>button::after,.stDownloadButton>button::after,[data-testid="stFormSubmitButton"]>button::after{content:"";position:absolute;top:0;left:-120%;width:60%;height:100%;pointer-events:none;background:linear-gradient(120deg,transparent,rgba(255,255,255,.22),transparent);transform:skewX(-20deg);transition:left .6s ease}
    .stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stFormSubmitButton"]>button:hover{background:linear-gradient(180deg,#3B6350,#365B48);border-color:#8ED6B0;color:#fff;transform:translateY(-2px);box-shadow:0 10px 24px rgba(0,0,0,.28),0 0 18px rgba(142,214,176,.22)}
    .stButton>button:hover::after,.stDownloadButton>button:hover::after,[data-testid="stFormSubmitButton"]>button:hover::after{left:140%}
    .stButton>button:active,.stDownloadButton>button:active,[data-testid="stFormSubmitButton"]>button:active{transform:translateY(0) scale(.97)}
    [data-testid^="stBaseButton-primary"],button[kind^="primary"]{background:linear-gradient(135deg,#8ED6B0,#B1E8C8)!important;border:none!important;box-shadow:0 8px 22px rgba(142,214,176,.28)}
    [data-testid^="stBaseButton-primary"] p,button[kind^="primary"] p{color:#0E1F18!important;font-weight:800}
    [data-testid^="stBaseButton-primary"]:hover,button[kind^="primary"]:hover{box-shadow:0 12px 30px rgba(142,214,176,.5)!important}
    button:focus-visible,[role="slider"]:focus-visible{outline:3px solid rgba(142,214,176,.55)!important;outline-offset:2px}

    /* Inputs */
    input,textarea,[data-baseweb="select"]>div,[data-baseweb="base-input"]{background-color:#223B32!important;color:#F0F4EC!important;border-color:#557966!important;border-radius:10px!important;transition:border-color .2s,box-shadow .2s}
    [data-baseweb="select"]>div:hover,[data-baseweb="input"]:hover,[data-baseweb="textarea"]:hover{border-color:#8ED6B0!important}
    [data-baseweb="select"]>div:focus-within,[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within{border-color:#8ED6B0!important;box-shadow:0 0 0 3px rgba(142,214,176,.22)!important}
    [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"]{background:#223B32!important;color:#F0F4EC!important;border-radius:12px!important}
    [role="option"]{transition:background .15s}
    [role="option"]:hover{background:rgba(142,214,176,.18)!important}
    [data-testid="stSlider"] [role="slider"]{background:#8ED6B0!important;box-shadow:0 0 0 4px rgba(142,214,176,.25);transition:box-shadow .2s}
    [data-testid="stSlider"] [role="slider"]:hover{box-shadow:0 0 0 9px rgba(142,214,176,.25)}
    [data-testid="stSliderThumbValue"]{color:#8ED6B0!important;font-weight:800}

    /* Chat */
    [data-testid="stChatMessage"]{margin-bottom:.6rem;padding:1rem 1.1rem;border-radius:18px;background:var(--mt-glass);border:1px solid var(--mt-border);backdrop-filter:blur(8px);animation:mtRise .4s var(--mt-ease) both;transition:border-color .2s,transform .2s}
    [data-testid="stChatMessage"]:hover{border-color:rgba(142,214,176,.5);transform:translateX(3px)}
    [data-testid="stChatMessage"][aria-label*="user"]{background:linear-gradient(135deg,rgba(169,164,216,.18),rgba(34,59,50,.6));border-color:rgba(169,164,216,.38)}
    [data-testid="stChatMessage"][aria-label*="assistant"]{background:linear-gradient(135deg,rgba(142,214,176,.15),rgba(34,59,50,.6))}
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p{color:#F0F4EC!important}
    [data-testid="stBottom"]>div{background:linear-gradient(to top,#15281F 60%,rgba(21,40,31,0))!important}
    [data-testid="stChatInput"]{border-radius:18px;border:1px solid #557966;background:#223B32;box-shadow:0 8px 30px rgba(0,0,0,.25);transition:border-color .2s,box-shadow .2s}
    [data-testid="stChatInput"]:focus-within{border-color:#8ED6B0;box-shadow:0 0 0 3px rgba(142,214,176,.22),0 10px 34px rgba(0,0,0,.3)}
    [data-testid="stChatInput"] textarea,[data-testid="stChatInput"] [data-baseweb="base-input"]{background-color:transparent!important;border:none!important}
    [data-testid="stChatInputSubmitButton"]{background:#8ED6B0!important;color:#0E1F18!important;border-radius:12px;transition:transform .2s}
    [data-testid="stChatInputSubmitButton"]:hover{transform:scale(1.1)}
    [data-testid="stSpinner"] p{color:var(--mt-primary-dark)!important}

    /* Responsive */
    @media (max-width:1024px){.block-container{padding-left:1.4rem!important;padding-right:1.4rem!important}}
    @media (max-width:900px){
    [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;row-gap:1rem!important}
    [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])>[data-testid="stColumn"],[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])>[data-testid="column"]{flex:1 1 calc(50% - 1rem)!important;min-width:calc(50% - 1rem)!important}
    [data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"])>[data-testid="stColumn"],[data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"])>[data-testid="column"]{flex:1 1 100%!important;min-width:100%!important}
    }
    @media (max-width:768px){
    .block-container{padding:1rem .8rem 5rem!important}
    button[data-baseweb="tab"]{padding:8px 12px;font-size:.84rem}
    [data-testid="stForm"]{padding:1rem .9rem .6rem;border-radius:18px}
    .mt-hero{border-radius:20px}
    .mt-affirm{min-height:3.2em}
    .mt-chip{font-size:13px;padding:7px 12px}
    }
    @media (max-width:480px){
    [data-testid="stMetric"]{padding:14px}
    [data-testid="stMetricValue"]{font-size:1.4rem!important}
    .mt-eyebrow{font-size:10px;letter-spacing:.1em}
    .mt-leaf{opacity:.45}
    }
    @media (hover:none){[data-testid="stMetric"]:hover,[data-testid="stPlotlyChart"]:hover,[data-testid="stChatMessage"]:hover{transform:none}}
    @media (prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
    </style>
    """,
    unsafe_allow_html=True,
)

px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = [
    "#8ED6B0",
    "#F2B880",
    "#A9A4D8",
    "#E58F91",
    "#77A9D1",
    "#B4C987",
    "#76B7A0",
]

st.markdown(
    """
    <div class="mt-hero">
      <div class="mt-leaf" aria-hidden="true">🌿</div>
      <span class="mt-eyebrow"><span class="mt-dot"></span>Your personal wellness space</span>
      <div class="mt-title" role="heading" aria-level="1">MindTrack AI</div>
      <div class="mt-sub">Pause. Reflect. Understand yourself a little better.</div>
      <div class="mt-affirm">
        <span>🌱 Small steps still move you forward.</span>
        <span>🫶 Whatever you feel today is allowed.</span>
        <span>🌤️ Check in with yourself, gently.</span>
      </div>
      <div class="mt-chips">
        <span class="mt-chip" title="Log your mood in under a minute">🌤️ Daily check-in</span>
        <span class="mt-chip" title="Talk things through any time">💬 AI companion</span>
        <span class="mt-chip" title="See your patterns over time">📊 Mood insights</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "💚 MindTrack AI is a wellness companion, not a diagnostic tool "
    "or a replacement for professional mental healthcare."
)

# Session state initialization for authentication
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

# If not authenticated, display login & registration
if st.session_state.authenticated_user is None:
    st.markdown("### 🔐 Welcome to MindTrack AI")
    st.caption(
        "Please sign in or create an account to securely access your personal mood check-ins and AI companion."
    )

    auth_tab_login, auth_tab_register, auth_tab_forgot = st.tabs(
        ["🔑 Sign In", "✨ Create Account", "❓ Forgot Password"]
    )

    with auth_tab_login, st.form("login_form"):
        login_username = st.text_input("Username", key="login_username_input").strip()
        login_password = st.text_input(
            "Password", type="password", key="login_password_input"
        )
        login_submitted = st.form_submit_button(
            "🔑 Sign In", type="primary", width="stretch"
        )

        if login_submitted:
            user_obj, err = authenticate_user(login_username, login_password)
            if user_obj:
                st.session_state.authenticated_user = user_obj
                st.success(f"Welcome back, {user_obj['username']}! 🌿")
                st.rerun()
            else:
                st.error(err or "Invalid username or password.")

    with auth_tab_login:
        st.caption(
            "🔒 **Forgot your password?** Switch to the **❓ Forgot Password** tab above to recover your account using your security question or emergency recovery key."
        )

    with auth_tab_register:
        with st.form("register_form"):
            reg_username = st.text_input(
                "Choose a username",
                help="3–30 characters, letters, numbers, underscores, or hyphens.",
                key="reg_username_input",
            ).strip()
            reg_password = st.text_input(
                "Choose a password",
                type="password",
                help="At least 8 characters.",
                key="reg_password_input",
            )
            reg_confirm = st.text_input(
                "Confirm password",
                type="password",
                key="reg_confirm_input",
            )

            st.markdown("##### 🛡️ Account Recovery Configuration")
            reg_sec_q_select = st.selectbox(
                "Select a Security Question",
                options=DEFAULT_SECURITY_QUESTIONS + ["Custom question..."],
                key="reg_sec_q_select",
                help="You will be asked this question if you ever forget your password.",
            )
            reg_custom_sec_q = ""
            if reg_sec_q_select == "Custom question...":
                reg_custom_sec_q = st.text_input(
                    "Write your custom security question",
                    key="reg_custom_sec_q_input",
                    placeholder="e.g., What was the name of your favorite school teacher?",
                ).strip()

            reg_sec_a = st.text_input(
                "Security Answer",
                key="reg_sec_a_input",
                help="Answers are stored securely as cryptographic hashes and verified case-insensitively.",
            ).strip()

            reg_submitted = st.form_submit_button(
                "✨ Create Account", type="primary", width="stretch"
            )

            if reg_submitted:
                if reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                else:
                    chosen_question = (
                        reg_custom_sec_q
                        if reg_sec_q_select == "Custom question..."
                        else reg_sec_q_select
                    )
                    user_obj, err = register_user(
                        reg_username,
                        reg_password,
                        security_question=chosen_question,
                        security_answer=reg_sec_a,
                    )
                    if user_obj:
                        st.session_state.authenticated_user = user_obj
                        if user_obj.get("recovery_key"):
                            st.session_state["new_recovery_key"] = user_obj[
                                "recovery_key"
                            ]
                        st.success(
                            f"Account created successfully! Welcome, {user_obj['username']}! 🌿"
                        )
                        st.rerun()
                    else:
                        st.error(err or "Registration failed.")

    with auth_tab_forgot:
        st.markdown("#### ❓ Reset Forgotten Password")
        st.caption(
            "Recover access to your account using your security question or single-use emergency recovery key."
        )

        with st.expander("🔍 Look up your security question"):
            lookup_user = st.text_input(
                "Enter your username to view your configured question:",
                key="lookup_username_input",
            ).strip()
            if st.button("Check Question", key="lookup_question_btn"):
                if lookup_user:
                    q_found, q_err = get_security_question(lookup_user)
                    if q_found:
                        st.info(
                            f"**Security Question for `{lookup_user}`:**\n\n💬 *{q_found}*"
                        )
                    else:
                        st.error(q_err or "Could not find a security question.")
                else:
                    st.warning("Please enter your username.")

        recovery_method = st.radio(
            "Choose verification method:",
            options=["🛡️ Security Question", "🔑 Emergency Recovery Key"],
            horizontal=True,
            key="forgot_recovery_method",
        )

        with st.form("forgot_password_form"):
            forgot_user = st.text_input(
                "Username",
                key="forgot_username_input",
                placeholder="Enter your username",
            ).strip()

            if recovery_method == "🛡️ Security Question":
                forgot_sec_answer = st.text_input(
                    "Security Answer",
                    key="forgot_sec_answer_input",
                    placeholder="Enter the answer to your security question",
                    help="Verification is case-insensitive.",
                ).strip()
                forgot_recovery_key = ""
            else:
                forgot_sec_answer = ""
                forgot_recovery_key = st.text_input(
                    "Emergency Recovery Key",
                    key="forgot_recovery_key_input",
                    placeholder="MT-XXXX-XXXX-XXXX",
                    help="Enter the 16-character emergency recovery key.",
                ).strip()

            forgot_new_pass = st.text_input(
                "New Password",
                type="password",
                key="forgot_new_pass_input",
                help="At least 8 characters.",
            )
            forgot_confirm_pass = st.text_input(
                "Confirm New Password",
                type="password",
                key="forgot_confirm_pass_input",
            )

            forgot_submit = st.form_submit_button(
                "🔄 Reset Password",
                type="primary",
                width="stretch",
            )

            if forgot_submit:
                if not forgot_user:
                    st.error("Please enter your username.")
                elif forgot_new_pass != forgot_confirm_pass:
                    st.error("New passwords do not match.")
                elif recovery_method == "🛡️ Security Question":
                    if not forgot_sec_answer:
                        st.error(
                            "Please enter the answer to your security question."
                        )
                    else:
                        ok, err_msg = reset_password_with_security_answer(
                            forgot_user, forgot_sec_answer, forgot_new_pass
                        )
                        if ok:
                            st.success(
                                "🎉 Password reset successfully! You can now switch to the **🔑 Sign In** tab and log in."
                            )
                        else:
                            st.error(err_msg or "Password reset failed.")
                else:
                    if not forgot_recovery_key:
                        st.error("Please enter your Emergency Recovery Key.")
                    else:
                        ok, err_msg, new_key = reset_password_with_recovery_key(
                            forgot_user, forgot_recovery_key, forgot_new_pass
                        )
                        if ok:
                            st.success(
                                "🎉 Password reset successfully! You can now switch to the **🔑 Sign In** tab and log in."
                            )
                            if new_key:
                                st.info(
                                    f"🔑 **Your new single-use Recovery Key is:** `{new_key}`\n\n"
                                    "Please write this code down and store it in a secure location."
                                )
                        else:
                            st.error(err_msg or "Password reset failed.")

    # Notice for safe migration of existing data
    st.markdown("---")
    st.info(
        "💡 **Notice for existing users:** If you previously had saved check-ins or conversations before user accounts, "
        "your data has been safely preserved under the account **`mindtrack_user`** (Default password: **`MindTrack2026!`**).\n\n"
        "If you ever forget your password, the default security question for legacy accounts is: "
        "**'What is the name of this wellness companion?'** (Answer: **`MindTrack`**)."
    )
    st.stop()
    sys.exit(0)

# Authenticated user session
current_user = st.session_state.get("authenticated_user")
if current_user is None:
    st.stop()
    sys.exit(0)

# Sidebar user account controls
with st.sidebar:
    st.markdown(f"### 🌿 **{current_user['username']}**")
    st.caption("Your private wellness space")

    # Display newly generated emergency recovery key alert if present
    if "new_recovery_key" in st.session_state:
        rec_key = st.session_state["new_recovery_key"]
        st.warning(
            f"🔑 **Emergency Recovery Key:** `{rec_key}`\n\n"
            "Please copy and store this key safely. You can use it to reset your password if you ever forget it."
        )
        if st.button("I have saved my key", key="dismiss_recovery_key_btn"):
            st.session_state.pop("new_recovery_key", None)
            st.rerun()

    if st.button("🚪 Sign Out", key="sign_out_button", width="stretch"):
        st.session_state.authenticated_user = None
        st.session_state.pop("active_conversation_id", None)
        st.session_state.pop("conversation_selector", None)
        st.session_state.pop("chat_notice", None)
        st.session_state.pop("new_recovery_key", None)
        st.rerun()

    with st.expander("🔒 Change Password"):
        with st.form("change_pw_form", clear_on_submit=True):
            curr_pass = st.text_input("Current password", type="password")
            new_pass = st.text_input("New password (min 8 chars)", type="password")
            confirm_new_pass = st.text_input("Confirm new password", type="password")
            pw_change_submitted = st.form_submit_button(
                "Update Password", width="stretch"
            )

            if pw_change_submitted:
                if new_pass != confirm_new_pass:
                    st.error("New passwords do not match.")
                else:
                    ok, change_err = change_user_password(
                        current_user["id"], curr_pass, new_pass
                    )
                    if ok:
                        st.success("Password updated successfully!")
                    else:
                        st.error(change_err or "Failed to change password.")

    with st.expander("🛡️ Security Question & Recovery Key"):
        st.caption(
            "Configure how you recover your account if you forget your password."
        )
        with st.form("update_sec_q_form", clear_on_submit=True):
            st.markdown("**Update Security Question**")
            curr_pw_sec = st.text_input(
                "Current password", type="password", key="sec_curr_pw"
            )
            new_sec_q_select = st.selectbox(
                "Choose question",
                options=DEFAULT_SECURITY_QUESTIONS + ["Custom question..."],
                key="sidebar_sec_q_select",
            )
            new_sec_q_custom = ""
            if new_sec_q_select == "Custom question...":
                new_sec_q_custom = st.text_input(
                    "Custom question", key="sidebar_custom_sec_q"
                ).strip()

            new_sec_a = st.text_input(
                "New security answer", key="sidebar_sec_a"
            ).strip()
            submit_sec_q = st.form_submit_button(
                "Save Recovery Question", width="stretch"
            )

            if submit_sec_q:
                chosen_q = (
                    new_sec_q_custom
                    if new_sec_q_select == "Custom question..."
                    else new_sec_q_select
                )
                ok, err = update_security_credentials(
                    current_user["id"], curr_pw_sec, chosen_q, new_sec_a
                )
                if ok:
                    st.success("Security question updated successfully!")
                else:
                    st.error(err or "Failed to update security question.")

        with st.form("regen_rec_key_form", clear_on_submit=True):
            st.markdown("**Regenerate Recovery Key**")
            st.caption("Generates a new single-use 16-character recovery key.")
            curr_pw_rec = st.text_input(
                "Current password", type="password", key="rec_curr_pw"
            )
            submit_rec_key = st.form_submit_button(
                "Generate New Recovery Key", width="stretch"
            )

            if submit_rec_key:
                new_k, err = regenerate_recovery_key(
                    current_user["id"], curr_pw_rec
                )
                if new_k:
                    st.success("New Emergency Recovery Key generated!")
                    st.info(f"🔑 **`{new_k}`**\nPlease copy and store this safely.")
                else:
                    st.error(err or "Failed to generate recovery key.")

# Application tabs
checkin_tab, chat_tab, dashboard_tab = st.tabs(
    ["🌤️ Daily Check-in", "💬 AI Companion", "📊 Mood Insights"]
)

# ==================================================
# Daily Check-in
# ==================================================

with checkin_tab:
    st.subheader("🌤️ How are you feeling today?")
    st.caption("Take a quiet moment. There are no right or wrong answers.")

    with st.form("mood_checkin", clear_on_submit=True):
        selected_date = st.date_input(
            "Date",
            value=date.today(),
        )

        mood_emojis = {
            "Happy": "😄",
            "Calm": "😌",
            "Neutral": "😐",
            "Sad": "😔",
            "Stressed": "😣",
            "Anxious": "😟",
            "Overwhelmed": "🥺",
        }

        mood = st.selectbox(
            "✨ Choose the mood that best describes how you feel",
            options=list(mood_emojis.keys()),
            format_func=lambda value: f"{mood_emojis[value]}  {value}",
            help="Choose the mood that feels closest to your experience.",
        )

        intensity = st.slider(
            "💚 How intense is this feeling?",
            min_value=1,
            max_value=5,
            value=3,
            help=(
                "1 = Very mild, 5 = Very intense. "
                "Intensity is personal, not good or bad."
            ),
        )

        intensity_labels = {
            1: "Very mild",
            2: "Mild",
            3: "Moderate",
            4: "Strong",
            5: "Very strong",
        }

        st.caption(
            f"Selected intensity: {intensity}/5 — "
            f"{intensity_labels[intensity]}"
        )

        note = st.text_area(
            "Optional journal note",
            max_chars=2000,
            help="Avoid including identifying or highly sensitive information.",
        )

        submitted = st.form_submit_button(
            "💾 Save check-in",
            type="primary",
        )

    if submitted:
        try:
            with st.spinner("Saving your check-in..."):
                entry_id = save_mood_entry(
                    user_id=current_user["id"],
                    entry_date=selected_date,
                    mood=mood,
                    intensity=intensity,
                    note=note,
                )

            st.success(
                f"Check-in saved successfully. Entry ID: {entry_id}"
            )

        except ValueError as exc:
            st.error(str(exc))

        except Exception:
            logger.exception("Failed to save mood check-in.")
            st.error("The check-in could not be saved. Please try again.")

    st.subheader("🕰️ Recent check-ins")

    with st.spinner("Loading your saved mood check-ins..."):
        entries = get_mood_entries(user_id=current_user["id"])

    if entries:
        recent_df = pd.DataFrame(entries)

        display_columns = [
            column
            for column in ["date", "mood", "intensity", "note"]
            if column in recent_df.columns
        ]

        st.dataframe(
            recent_df[display_columns].head(10),
            hide_index=True,
            width="stretch",
        )

        with st.expander("🗑️ Delete a check-in"):
            entry_options = {
                f"#{entry['id']} · {entry['date']} · {entry['mood']}":
                entry["id"]
                for entry in entries
            }

            selected_entry = st.selectbox(
                "Select an entry",
                options=list(entry_options.keys()),
            )

            if st.button("🗑️ Delete selected entry"):
                try:
                    with st.spinner("Deleting check-in..."):
                        deleted = delete_mood_entry(
                            user_id=current_user["id"],
                            entry_id=entry_options[selected_entry],
                        )

                    if deleted:
                        st.success("Check-in deleted.")
                        st.rerun()
                    else:
                        st.warning("That entry no longer exists.")

                except Exception:
                    logger.exception("Failed to delete mood check-in.")
                    st.error("Could not delete the selected check-in.")

    else:
        st.info("🌱 Your saved check-ins will appear here.")


    # ==================================================
# Persistent AI Chatbot
# ==================================================

with chat_tab:
    st.subheader("💬 Your AI wellness companion")

    st.caption(
        "Share what's on your mind. You can skip any question "
        "and stop chatting whenever you wish."
    )

    st.warning(
        "AI responses may be imperfect. This is a wellness tool, "
        "not a therapist or an emergency service."
    )

    # Display notices after Streamlit reruns.
    notice = st.session_state.pop("chat_notice", None)
    if notice:
        st.warning(notice)

    # Load saved conversations.
    try:
        with st.spinner("Loading your saved conversations..."):
            conversations = list_conversations(user_id=current_user["id"])

        if not conversations:
            create_conversation(user_id=current_user["id"])
            conversations = list_conversations(user_id=current_user["id"])

        if not conversations:
            st.error("Could not create a conversation.")
            st.stop()

    except Exception:
        logger.exception("Failed to load conversations.")
        st.error(
            "Chat history could not be loaded. "
            "Please check your database configuration."
        )
        st.stop()

    conversation_ids = [item["id"] for item in conversations]

    # Restore the selected conversation.
    active_id = st.session_state.get("active_conversation_id")

    if active_id not in conversation_ids:
        active_id = conversation_ids[0]
        st.session_state.active_conversation_id = active_id

    # New conversation and delete controls.
    col_new, col_delete = st.columns(2)

    with col_new:
        if st.button("✨ New conversation", width="stretch"):
            try:
                with st.spinner("Creating a new conversation..."):
                    new_id = create_conversation(user_id=current_user["id"])

                st.session_state.active_conversation_id = new_id
                st.session_state.pop("conversation_selector", None)
                st.rerun()

            except Exception:
                logger.exception("Failed to create conversation.")
                st.error("Could not create a new conversation.")

    with col_delete:
        if st.button("🗑️ Delete current chat", width="stretch"):
            try:
                current_id = st.session_state.active_conversation_id

                with st.spinner("Deleting conversation..."):
                    deleted = delete_conversation(
                        user_id=current_user["id"],
                        conversation_id=current_id,
                    )

                if deleted:
                    remaining = list_conversations(user_id=current_user["id"])

                    if not remaining:
                        create_conversation(user_id=current_user["id"])
                        remaining = list_conversations(user_id=current_user["id"])

                    st.session_state.active_conversation_id = (
                        remaining[0]["id"]
                    )

                    st.session_state.pop("conversation_selector", None)
                    st.session_state["chat_notice"] = (
                        "The selected conversation was deleted."
                    )
                    st.rerun()

                else:
                    st.warning("The conversation no longer exists.")

            except Exception:
                logger.exception("Failed to delete conversation.")
                st.error("Could not delete this conversation.")

    # Refresh conversation list.
    with st.spinner("Refreshing conversation list..."):
        conversations = list_conversations(user_id=current_user["id"])

    if not conversations:
        st.info("Create a conversation to begin chatting.")
        st.stop()

    labels = {
        f"{item['title']} · #{item['id']}": item["id"]
        for item in conversations
    }

    active_id = st.session_state.active_conversation_id

    active_label = next(
        (
            label
            for label, conversation_id in labels.items()
            if conversation_id == active_id
        ),
        next(iter(labels)),
    )

    selected_label = st.selectbox(
        "Your conversations",
        options=list(labels.keys()),
        index=list(labels.keys()).index(active_label),
        key="conversation_selector",
    )

    selected_id = labels[selected_label]
    st.session_state.active_conversation_id = selected_id

    st.divider()

    # Load and display saved messages.
    try:
        with st.spinner("Loading conversation messages..."):
            messages = get_conversation_messages(
                user_id=current_user["id"],
                conversation_id=selected_id,
            )

        if not messages:
            st.markdown(
                """
                ### 🌱 Welcome to your wellness space

                Talk about your day, reflect on your mood, or explore
                simple everyday wellness strategies.

                **Not sure where to start?**
                - 🌤️ Managing a stressful day
                - 📝 Reflecting on your emotions
                - 🌿 Building a calming routine

                What has been on your mind lately?
                """
            )

        for message in messages:
            avatar = (
                "🌿"
                if message["role"] == "assistant"
                else "🙂"
            )

            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

    except Exception:
        logger.exception("Failed to load conversation messages.")
        st.error("Could not load messages for this conversation.")
        messages = []

    # Chat input.
    prompt = st.chat_input(
        "How have you been feeling lately?",
        max_chars=4000,
        key="wellness_chat_input",
    )

    if prompt:
        user_message_saved = False

        # Save the user message before calling the AI.
        try:
            save_message(
                user_id=current_user["id"],
                conversation_id=selected_id,
                role="user",
                content=prompt,
            )
            user_message_saved = True

        except Exception:
            logger.exception("Failed to save user message.")
            st.error(
                "Your message could not be saved. "
                "Please check your database and try again."
            )

        if user_message_saved:
            answer = None
            notice_to_show = None

            # Check safety before calling the language model.
            if check_message_safety(prompt):
                answer = CRISIS_MESSAGE

            else:
                try:
                    # Use persisted conversation history as context.
                    conversation_messages = get_conversation_messages(
                        user_id=current_user["id"],
                        conversation_id=selected_id,
                    )

                    with st.spinner("Thinking..."):
                        answer = generate_response(
                            conversation_messages
                        )

                except Exception:
                    logger.exception("AI response generation failed.")

                    answer = (
                        "I'm sorry, but I couldn't generate a response "
                        "right now. Please try again in a moment. "
                        "Your message has been saved."
                    )

                    notice_to_show = (
                        "The AI service did not respond successfully. "
                        "Check your API configuration or connection."
                    )

            # Save the assistant response to persistent history.
            try:
                save_message(
                    user_id=current_user["id"],
                    conversation_id=selected_id,
                    role="assistant",
                    content=answer,
                )

            except Exception:
                logger.exception("Failed to save assistant response.")

                notice_to_show = (
                    "The response could not be saved to chat history. "
                    "Please check your database configuration."
                )

            if notice_to_show:
                st.session_state["chat_notice"] = notice_to_show

            # Display the new messages by rerunning the app.
            st.rerun()


    # ==================================================
# Mood Dashboard and Advanced Analytics
# ==================================================

with dashboard_tab:
    st.subheader("📊 Advanced Mood Analytics")

    st.caption(
        "Explore your recorded mood patterns and intensity over time. "
        "These summaries describe your entries; they are not diagnoses."
    )

    with st.spinner("Preparing your mood analytics..."):
        entries = get_mood_entries(user_id=current_user["id"])

    if not entries:
        st.info(
            "No mood entries yet. Save a Daily Check-in to start "
            "building your personal mood dashboard."
        )

    else:
        df = pd.DataFrame(entries)

        required_columns = {"date", "mood", "intensity"}
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            st.error(
                "Mood data is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        else:
            df["date"] = pd.to_datetime(
                df["date"], errors="coerce"
            ).dt.normalize()

            df["intensity"] = pd.to_numeric(
                df["intensity"], errors="coerce"
            )

            df = df.dropna(
                subset=["date", "mood", "intensity"]
            ).copy()

            if df.empty:
                st.warning(
                    "No valid mood records are available for analysis."
                )

            else:
                df["mood"] = df["mood"].astype(str).str.strip()
                df = df[df["mood"] != ""].copy()

                if df.empty:
                    st.warning("No valid mood labels were found.")

                else:
                    min_date = df["date"].min().date()
                    max_date = df["date"].max().date()

                    # Date range filters.
                    st.markdown("### 🗓️ Date range")

                    period = st.selectbox(
                        "Choose an analysis period",
                        [
                            "Last 7 days",
                            "Last 30 days",
                            "Last 90 days",
                            "All recorded data",
                            "Custom range",
                        ],
                        index=1,
                        key="mood_analytics_period",
                    )

                    if period == "All recorded data":
                        start_date = min_date
                        end_date = max_date

                    elif period == "Custom range":
                        default_start = max(
                            min_date,
                            max_date
                            - pd.Timedelta(days=29).to_pytimedelta(),
                        )

                        selected_dates = st.date_input(
                            "Select start and end dates",
                            value=(default_start, max_date),
                            min_value=min_date,
                            max_value=max_date,
                            key="mood_custom_date_range",
                        )

                        if (
                            not isinstance(
                                selected_dates, (tuple, list)
                            )
                            or len(selected_dates) != 2
                        ):
                            st.info(
                                "Select both a start date and an end date."
                            )
                            st.stop()

                        start_date, end_date = selected_dates

                        if start_date > end_date:
                            st.error(
                                "The start date must be before the end date."
                            )
                            st.stop()

                    else:
                        days = {
                            "Last 7 days": 7,
                            "Last 30 days": 30,
                            "Last 90 days": 90,
                        }[period]

                        end_date = max_date

                        start_date = max(
                            min_date,
                            end_date
                            - pd.Timedelta(
                                days=days - 1
                            ).to_pytimedelta(),
                        )

                    start_ts = pd.Timestamp(start_date)
                    end_ts = pd.Timestamp(end_date)

                    filtered = df[
                        (df["date"] >= start_ts)
                        & (df["date"] <= end_ts)
                    ].copy()

                    st.caption(
                        f"Showing {start_date:%d %b %Y} to "
                        f"{end_date:%d %b %Y}"
                    )

                    if filtered.empty:
                        st.info(
                            "There are no check-ins in this date range. "
                            "Try a different period."
                        )

                    else:
                        # Key performance indicators.
                        total_entries = len(filtered)
                        unique_days = filtered["date"].nunique()
                        average_intensity = filtered["intensity"].mean()
                        most_common_mood = (
                            filtered["mood"].mode().iloc[0]
                        )

                        metric1, metric2, metric3, metric4 = (
                            st.columns(4)
                        )

                        metric1.metric(
                            "Total check-ins",
                            f"{total_entries:,}",
                        )

                        metric2.metric(
                            "Average intensity",
                            f"{average_intensity:.1f}/5",
                        )

                        metric3.metric(
                            "Most recorded mood",
                            most_common_mood,
                        )

                        metric4.metric(
                            "Days with check-ins",
                            f"{unique_days:,}",
                        )

                        st.divider()

                        # Advanced trend analysis.
                        st.subheader("📈 Advanced Mood Trend Analysis")

                        st.caption(
                            "Explore changes in recorded intensity and "
                            "check-in patterns. These summaries describe "
                            "your entries and are not diagnoses."
                        )

                        from mindtrack_ai.trend_service import (
                            build_mood_trend_analysis,
                        )

                        with st.spinner(
                            "Analyzing your recorded mood trends..."
                        ):
                            trend_result = build_mood_trend_analysis(
                                filtered
                            )

                        daily_trend = trend_result["daily_trend"]
                        weekday_summary = trend_result["weekday_summary"]

                        if daily_trend.empty:
                            st.info(
                                "Not enough valid records to calculate trends."
                            )

                        else:
                            st.markdown(
                                "#### Daily intensity and rolling average"
                            )

                            fig_trend = px.line(
                                daily_trend,
                                x="date",
                                y=[
                                    "average_intensity",
                                    "rolling_7_day",
                                ],
                                markers=True,
                                labels={
                                    "date": "Date",
                                    "value": "Intensity (1–5)",
                                    "variable": "Measure",
                                    "average_intensity": "Daily average",
                                    "rolling_7_day": "7-day rolling average",
                                },
                                title="Recorded intensity over time",
                            )

                            fig_trend.update_yaxes(
                                range=[0.5, 5.5],
                                dtick=1,
                            )

                            st.plotly_chart(
                                fig_trend,
                                width="stretch",
                                key="advanced_mood_trend_chart",
                            )

                            st.caption(
                                "The rolling average smooths daily "
                                "fluctuations. Days without check-ins are "
                                "not treated as zero-intensity days."
                            )

                            st.markdown(
                                "#### Check-in patterns by weekday"
                            )

                            if weekday_summary.empty:
                                st.info("No weekday data is available.")

                            else:
                                weekday_col, intensity_col = st.columns(2)

                                with weekday_col:
                                    fig_weekdays = px.bar(
                                        weekday_summary,
                                        x="weekday",
                                        y="check_ins",
                                        title="Check-ins by weekday",
                                        labels={
                                            "weekday": "Weekday",
                                            "check_ins": (
                                                "Number of check-ins"
                                            ),
                                        },
                                    )

                                    st.plotly_chart(
                                        fig_weekdays,
                                        width="stretch",
                                        key="weekday_checkin_chart",
                                    )

                                with intensity_col:
                                    fig_weekday_intensity = px.bar(
                                        weekday_summary,
                                        x="weekday",
                                        y="average_intensity",
                                        title=(
                                            "Average intensity by weekday"
                                        ),
                                        labels={
                                            "weekday": "Weekday",
                                            "average_intensity": (
                                                "Average intensity"
                                            ),
                                        },
                                    )

                                    fig_weekday_intensity.update_yaxes(
                                        range=[0.5, 5.5],
                                        dtick=1,
                                    )

                                    st.plotly_chart(
                                        fig_weekday_intensity,
                                        width="stretch",
                                        key="weekday_intensity_chart",
                                    )

                            st.markdown("#### 💡 Your trend reflections")

                            for trend_insight in trend_result["insights"]:
                                st.markdown(f"- {trend_insight}")

                        # Personalized AI mood insights.
                        st.divider()
                        st.subheader("🧠 Personalized AI Mood Insights")

                        st.caption(
                            "Discover reflections based on your recorded "
                            "mood patterns. Insights are descriptive, "
                            "not diagnostic."
                        )

                        if st.button(
                            "✨ Generate my mood insights",
                            type="primary",
                            width="stretch",
                            key="generate_personalized_mood_insights",
                        ):
                            with st.spinner(
                                "Reflecting on your recorded mood patterns..."
                            ):
                                try:
                                    st.session_state[
                                        "personalized_mood_insights"
                                    ] = generate_mood_insights(filtered)

                                    st.session_state[
                                        "mood_insights_error"
                                    ] = None

                                except (ValueError, KeyError) as exc:
                                    st.session_state[
                                        "mood_insights_error"
                                    ] = str(exc)

                                    st.session_state.pop(
                                        "personalized_mood_insights",
                                        None,
                                    )

                                except Exception:
                                    logger.exception(
                                        "Failed to generate mood insights."
                                    )

                                    st.session_state[
                                        "mood_insights_error"
                                    ] = (
                                        "Insights could not be generated. "
                                        "Please try again."
                                    )

                                    st.session_state.pop(
                                        "personalized_mood_insights",
                                        None,
                                    )

                        insight_error = st.session_state.get(
                            "mood_insights_error"
                        )

                        if insight_error:
                            st.warning(insight_error)

                        insight_text = st.session_state.get(
                            "personalized_mood_insights"
                        )

                        if insight_text:
                            st.markdown(insight_text)

                            st.caption(
                                "Your reflection is based on recorded "
                                "check-ins and may not capture everything "
                                "you are experiencing."
                            )

                        # Mood distribution.
                        st.markdown("### 🎨 Mood distribution")

                        mood_counts = (
                            filtered["mood"]
                            .value_counts()
                            .rename_axis("Mood")
                            .reset_index(name="Check-ins")
                        )

                        mood_counts["Percentage"] = (
                            mood_counts["Check-ins"]
                            / mood_counts["Check-ins"].sum()
                            * 100
                        )

                        chart1, chart2 = st.columns(2)

                        with chart1:
                            fig_distribution = px.bar(
                                mood_counts.sort_values("Check-ins"),
                                x="Check-ins",
                                y="Mood",
                                orientation="h",
                                text="Check-ins",
                                title=(
                                    "How often each mood was recorded"
                                ),
                                hover_data={"Percentage": ":.1f"},
                            )

                            fig_distribution.update_layout(
                                xaxis_title="Number of check-ins",
                                yaxis_title="",
                                margin=dict(
                                    l=10, r=10, t=60, b=10
                                ),
                            )

                            st.plotly_chart(
                                fig_distribution,
                                width="stretch",
                            )

                        with chart2:
                            fig_pie = px.pie(
                                mood_counts,
                                names="Mood",
                                values="Check-ins",
                                hole=0.52,
                                title="Your Mood Distribution",
                                color_discrete_sequence=[
                                    "#8ED6B0",
                                    "#F2B880",
                                    "#A9A4D8",
                                    "#E58F91",
                                    "#77A9D1",
                                    "#B4C987",
                                    "#76B7A0",
                                ],
                            )

                            fig_pie.update_traces(
                                textposition="inside",
                                textinfo="percent+label",
                                marker=dict(line=dict(color="#172B25", width=2)),
                            )

                            st.plotly_chart(
                                fig_pie,
                                width="stretch",
                            )


                                                # Daily intensity trend.
                        st.markdown("### 📈 Mood intensity over time")

                        daily_intensity = (
                            filtered.groupby("date", as_index=False)
                            .agg(
                                average_intensity=("intensity", "mean"),
                                check_ins=("intensity", "size"),
                            )
                            .sort_values("date")
                        )

                        fig_intensity = px.line(
                            daily_intensity,
                            x="date",
                            y="average_intensity",
                            markers=True,
                            title="Average recorded intensity by day",
                            hover_data={
                                "check_ins": True,
                                "average_intensity": ":.2f",
                            },
                            labels={
                                "date": "Date",
                                "average_intensity": (
                                    "Average intensity (1–5)"
                                ),
                                "check_ins": "Check-ins",
                            },
                        )

                        fig_intensity.update_yaxes(
                            range=[0.5, 5.5],
                            dtick=1,
                        )

                        st.plotly_chart(
                            fig_intensity,
                            width="stretch",
                        )

                        st.caption(
                            "Intensity represents the rating you recorded "
                            "from 1 to 5. A higher score does not necessarily "
                            "mean a worse mood."
                        )

                        # Weekly mood patterns.
                        st.markdown("### 🗓️ Weekly mood patterns")

                        weekly_data = filtered.copy()

                        weekly_data["week"] = (
                            weekly_data["date"]
                            .dt.to_period("W")
                            .dt.start_time
                        )

                        weekly_counts = (
                            weekly_data.groupby(
                                ["week", "mood"],
                                as_index=False,
                            )
                            .size()
                            .rename(columns={"size": "Check-ins"})
                        )

                        if not weekly_counts.empty:
                            fig_weekly = px.bar(
                                weekly_counts,
                                x="week",
                                y="Check-ins",
                                color="mood",
                                barmode="stack",
                                title="Recorded moods by week",
                                labels={
                                    "week": "Week starting",
                                    "mood": "Mood",
                                },
                            )

                            st.plotly_chart(
                                fig_weekly,
                                width="stretch",
                            )

                        # Intensity by mood.
                        st.markdown("### 💚 Intensity by recorded mood")

                        fig_box = px.box(
                            filtered,
                            x="mood",
                            y="intensity",
                            points="all",
                            title=(
                                "Intensity ratings for each mood"
                            ),
                            labels={
                                "mood": "Recorded mood",
                                "intensity": "Intensity (1–5)",
                            },
                        )

                        fig_box.update_yaxes(
                            range=[0.5, 5.5],
                            dtick=1,
                        )

                        fig_box.update_layout(xaxis_title="")

                        st.plotly_chart(
                            fig_box,
                            width="stretch",
                        )

                        # Automatic descriptive insights.
                        st.markdown("### 💭 Personal reflection insights")

                        top_mood_row = mood_counts.sort_values(
                            "Check-ins",
                            ascending=False,
                        ).iloc[0]

                        st.write(
                            f"- **Most frequently recorded mood:** "
                            f"{top_mood_row['Mood']} "
                            f"({int(top_mood_row['Check-ins'])} "
                            f"check-ins, "
                            f"{top_mood_row['Percentage']:.1f}% "
                            f"of this period)."
                        )

                        st.write(
                            f"- **Check-in frequency:** You recorded "
                            f"{total_entries} check-in(s) across "
                            f"{unique_days} distinct day(s)."
                        )

                        if len(daily_intensity) >= 2:
                            first_intensity = daily_intensity[
                                "average_intensity"
                            ].iloc[0]

                            last_intensity = daily_intensity[
                                "average_intensity"
                            ].iloc[-1]

                            difference = (
                                last_intensity - first_intensity
                            )

                            if difference > 0.05:
                                trend_text = "higher"
                            elif difference < -0.05:
                                trend_text = "lower"
                            else:
                                trend_text = "similar"

                            st.write(
                                f"- **Recorded intensity comparison:** "
                                f"The latest recorded day's average "
                                f"intensity was {trend_text} than the "
                                f"first recorded day's average "
                                f"({first_intensity:.1f} versus "
                                f"{last_intensity:.1f})."
                            )

                        else:
                            st.write(
                                "- Record check-ins on additional days "
                                "to compare intensity over time."
                            )

                        st.info(
                            "Reflection prompt: What was happening in "
                            "your life on the days when you recorded "
                            "these moods? Looking at your own notes may "
                            "help you reflect on possible patterns. "
                            "These charts show associations in your "
                            "entries, not causes or diagnoses."
                        )

                        # Filtered records.
                        with st.expander("View filtered mood records"):
                            display_columns = [
                                column
                                for column in [
                                    "date",
                                    "mood",
                                    "intensity",
                                    "note",
                                ]
                                if column in filtered.columns
                            ]

                            display_df = filtered[
                                display_columns
                            ].sort_values(
                                "date",
                                ascending=False,
                            ).copy()

                            display_df["date"] = (
                                display_df["date"].dt.strftime("%Y-%m-%d")
                            )

                            st.dataframe(
                                display_df,
                                hide_index=True,
                                width="stretch",
                            )

                        # CSV export.
                        export_df = filtered.copy()

                        export_df["date"] = (
                            export_df["date"].dt.strftime("%Y-%m-%d")
                        )

                        csv_data = export_df.to_csv(
                            index=False
                        ).encode("utf-8-sig")

                        st.download_button(
                            label="⬇️ Download filtered mood data (CSV)",
                            data=csv_data,
                            file_name=(
                                f"mindtrack_mood_{start_date}_"
                                f"{end_date}.csv"
                            ),
                            mime="text/csv",
                        )

                        # PDF report export.
                        st.divider()
                        st.subheader("📄 Download your mood report")

                        st.caption(
                            "Export the records currently selected by "
                            "your dashboard filters."
                        )

                        try:
                            with st.spinner(
                                "Preparing your PDF mood report..."
                            ):
                                pdf_bytes = build_mood_pdf_report(
                                    filtered,
                                    report_title=(
                                        f"MindTrack AI — Mood Report ({current_user['username']})"
                                    ),
                                )

                            st.download_button(
                                label="⬇️ Download PDF Mood Report",
                                data=pdf_bytes,
                                file_name=f"mindtrack_mood_report_{current_user['username']}.pdf",
                                mime="application/pdf",
                                type="primary",
                                width="stretch",
                                key="download_mood_pdf_report",
                            )

                            st.caption(
                                f"Your report includes {len(filtered)} "
                                "check-in records from the selected "
                                "dashboard period."
                            )

                        except (ValueError, KeyError) as exc:
                            st.warning(
                                f"Could not generate the report: {exc}"
                            )

                        except Exception:
                            logger.exception(
                                "PDF mood report generation failed."
                            )
                            st.error(
                                "The PDF report could not be generated. "
                                "Check the terminal for details."
                            )
import logging
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure 'src' and project root are always on sys.path regardless of how Streamlit or Python is launched
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
for _p in (str(SRC_DIR), str(PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
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

# Theme
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,400..800&family=Figtree:wght@400;500;600;700&display=swap');
    :root{
      /* Midnight Slate Theme */
      --mt-bg: #0F172A;
      --mt-surface: #1E293B;
      --mt-field: #0B1120;
      --mt-line: #334155;
      --mt-text: #F8FAFC;
      --mt-muted: #94A3B8;
      
      /* Vibrant Accents */
      --mt-accent: #3B82F6; /* Bright Blue */
      --mt-accent-hover: #60A5FA;
      --mt-on-accent: #FFFFFF;
      --mt-sage: #10B981; /* Emerald */
      --mt-rose: #F43F5E; /* Rose */
    }
    
    @keyframes slideUpFade {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .block-container {
      animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      max-width:1180px;
      padding-top:2rem;
      padding-bottom:5rem;
    }

    html{scroll-behavior:smooth}
    ::selection{background:rgba(59,130,246,.35);color:#fff}
    ::-webkit-scrollbar{width:9px;height:9px}
    ::-webkit-scrollbar-track{background:transparent}
    ::-webkit-scrollbar-thumb{background:var(--mt-line);border-radius:9px}
    ::-webkit-scrollbar-thumb:hover{background:#475569}

    .stApp{background:var(--mt-bg);color:var(--mt-text)}
    [data-testid="stHeader"]{background:transparent}
    footer{visibility:hidden}
    [data-testid="stSidebar"]{background:var(--mt-surface);border-right:1px solid var(--mt-line)}

    /* Type. Spans are left alone on purpose: Streamlit's icons are font-based spans. */
    .stApp,.stApp p,.stApp label,.stApp li,.stApp button,.stApp input,.stApp textarea{font-family:'Figtree','Segoe UI',system-ui,-apple-system,sans-serif!important}
    .stApp h1,.stApp h2,.stApp h3,.stApp h4,.mt-name,.mt-day,[data-testid="stMetricValue"],[data-testid="stMetricValue"] div{font-family:'Bricolage Grotesque','Figtree',system-ui,sans-serif!important;letter-spacing:-.015em}
    h1,h2,h3,h4,h5,[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,label{color:var(--mt-text)!important}
    h2,h3{font-weight:700!important}
    h3{font-size:1.5rem!important}
    h4{font-size:1.18rem!important;font-weight:650!important}
    h5{font-weight:600!important}
    [data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:var(--mt-muted)!important}
    hr{border:none!important;height:1px;background:var(--mt-line)!important}

    /* Masthead */
    .mt-masthead{display:grid;grid-template-columns:auto 1fr;align-items:end;column-gap:clamp(18px,3vw,34px);padding:.25rem 0 1.5rem;margin-bottom:1.4rem;border-bottom:1px solid var(--mt-line)}
    .mt-day{font-weight:800;font-size:clamp(76px,11vw,118px);line-height:.78;letter-spacing:-.05em;color:var(--mt-accent);font-variation-settings:'wdth' 78}
    .mt-daymeta{margin-top:10px;font-size:15px;line-height:1.3;color:var(--mt-muted)}
    .mt-daymeta b{display:block;font-size:17px;font-weight:600;color:var(--mt-text)}
    .mt-name{margin:0 0 6px;font-size:clamp(26px,3.6vw,38px);font-weight:700;line-height:1.1;color:var(--mt-text)}
    .mt-tag{max-width:46ch;font-size:clamp(15px,1.7vw,17px);line-height:1.5;color:var(--mt-muted)}

    /* Tabs */
    [data-baseweb="tab-list"]{gap:6px;overflow-x:auto;scrollbar-width:none}
    [data-baseweb="tab-list"]::-webkit-scrollbar{display:none}
    [data-baseweb="tab-border"]{background:var(--mt-line)!important;height:1px!important}
    [data-baseweb="tab-highlight"]{background:var(--mt-accent)!important;height:3px!important}
    button[data-baseweb="tab"]{height:auto;padding:12px 18px;white-space:nowrap;background:transparent;color:var(--mt-muted);transition:color .15s}
    button[data-baseweb="tab"] p{color:inherit!important;font-weight:600;font-size:1rem}
    button[data-baseweb="tab"]:hover{background:transparent;color:var(--mt-text)}
    button[data-baseweb="tab"][aria-selected="true"]{color:var(--mt-text)}
    [data-baseweb="tab-panel"]{padding-top:1.5rem}

    /* Surfaces */
    [data-testid="stForm"]{padding:1.5rem 1.5rem 1.1rem;border-radius:12px;background:var(--mt-surface);border:1px solid var(--mt-line)!important}
    [data-testid="stMetric"]{padding:2px 0 2px 16px;border-left:3px solid var(--mt-accent)}
    [data-testid="stMetricValue"]{font-size:2.1rem;font-weight:700;color:var(--mt-text)!important}
    [data-testid="stMetricValue"] > div{white-space:normal!important;overflow-wrap:anywhere}
    [data-testid="stMetricLabel"]{color:var(--mt-muted)!important}
    [data-testid="stPlotlyChart"]{padding:14px 10px 6px;overflow:hidden;border-radius:12px;background:var(--mt-surface)}
    .js-plotly-plot .main-svg,.js-plotly-plot .svg-container{background:transparent!important}
    [data-testid="stDataFrame"]{overflow:hidden;border-radius:10px;border:1px solid var(--mt-line)}
    [data-testid="stExpander"]{background:transparent;border:none!important}
    [data-testid="stExpander"] details{overflow:hidden;border-radius:10px;background:transparent;border:1px solid var(--mt-line)!important}
    [data-testid="stExpander"] summary{padding:.8rem 1rem;font-weight:600}
    [data-testid="stExpander"] summary:hover{background:rgba(248,250,252,.04)}
    [data-testid="stAlert"]{border-radius:8px;border-left:3px solid var(--mt-muted)}
    [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]){border-left-color:#3B82F6}
    [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]){border-left-color:var(--mt-sage)}
    [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]){border-left-color:#F59E0B}
    [data-testid="stAlert"]:has([data-testid="stAlertContentError"]){border-left-color:var(--mt-rose)}

    /* Buttons */
    .stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button{
      min-height:42px;padding:.5rem 1.1rem;border-radius:8px;border:1px solid var(--mt-line);
      background:transparent;color:var(--mt-text);font-weight:600;
      transition: all .2s ease-in-out;
    }
    .stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stFormSubmitButton"]>button:hover{
      background:rgba(248,250,252,.07);border-color:var(--mt-muted);color:var(--mt-text);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(59,130,246,.15);
    }
    .stButton>button:active,.stDownloadButton>button:active,[data-testid="stFormSubmitButton"]>button:active{transform:translateY(1px)}
    [data-testid^="stBaseButton-primary"],button[kind^="primary"]{background:var(--mt-accent)!important;border:1px solid var(--mt-accent)!important}
    [data-testid^="stBaseButton-primary"] p,button[kind^="primary"] p{color:var(--mt-on-accent)!important;font-weight:700}
    [data-testid^="stBaseButton-primary"]:hover,button[kind^="primary"]:hover{background:var(--mt-accent-hover)!important;border-color:var(--mt-accent-hover)!important}
    button:focus-visible,[role="slider"]:focus-visible{outline:2px solid var(--mt-accent)!important;outline-offset:2px}

    /* Inputs */
    input,textarea,[data-baseweb="select"]>div,[data-baseweb="base-input"]{background-color:var(--mt-field)!important;color:var(--mt-text)!important;border-color:var(--mt-line)!important;border-radius:8px!important}
    [data-baseweb="select"]>div:hover,[data-baseweb="input"]:hover,[data-baseweb="textarea"]:hover{border-color:var(--mt-muted)!important}
    [data-baseweb="select"]>div:focus-within,[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within{border-color:var(--mt-accent)!important;box-shadow:0 0 0 2px rgba(59,130,246,.22)!important}
    [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"]{background:var(--mt-surface)!important;color:var(--mt-text)!important;border-radius:8px!important}
    [role="option"]:hover{background:rgba(59,130,246,.14)!important}
    [data-testid="stSlider"] [role="slider"]{background:var(--mt-accent)!important}
    [data-testid="stSliderThumbValue"]{color:var(--mt-accent)!important;font-weight:700}

    /* Chat */
    [data-testid="stChatMessage"]{margin-bottom:.6rem;padding:1rem 1.2rem;border-radius:12px;background:var(--mt-surface);border:1px solid var(--mt-line);border-left:3px solid var(--mt-sage)}
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),[data-testid="stChatMessage"][aria-label*="user"]{background:var(--mt-field);border-left-color:var(--mt-accent)}
    [data-testid="stBottom"]>div{background:var(--mt-bg)!important}
    [data-testid="stChatInput"]{border-radius:10px;border:1px solid var(--mt-line);background:var(--mt-field)}
    [data-testid="stChatInput"]:focus-within{border-color:var(--mt-accent);box-shadow:0 0 0 2px rgba(59,130,246,.22)}
    [data-testid="stChatInput"] textarea,[data-testid="stChatInput"] [data-baseweb="base-input"]{background-color:transparent!important;border:none!important}
    [data-testid="stChatInputSubmitButton"]{background:var(--mt-accent)!important;color:var(--mt-on-accent)!important;border-radius:8px}
    [data-testid="stSpinner"] p{color:var(--mt-muted)!important}

    /* Responsive */
    @media (max-width:1024px){.block-container{padding-left:1.4rem!important;padding-right:1.4rem!important}}
    @media (max-width:900px){
    [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;row-gap:1rem!important}
    [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])>[data-testid="stColumn"],[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])>[data-testid="column"]{flex:1 1 calc(50% - 1rem)!important;min-width:calc(50% - 1rem)!important}
    [data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"])>[data-testid="stColumn"],[data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"])>[data-testid="column"]{flex:1 1 100%!important;min-width:100%!important}
    }
    @media (max-width:768px){
    .block-container{padding:1rem .8rem 5rem!important}
    button[data-baseweb="tab"]{padding:10px 12px;font-size:.84rem}
    [data-testid="stForm"]{padding:1rem .9rem .6rem}
    }
    @media (max-width:640px){
    .mt-masthead{grid-template-columns:1fr;row-gap:14px}
    }
    @media (max-width:480px){
    [data-testid="stMetricValue"]{font-size:1.5rem!important}
    }
    @media (prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
    </style>
    """,
    unsafe_allow_html=True,
)

# New vibrant, colorful palette for charts
CHART_COLORS = [
    "#3B82F6", # Bright Blue
    "#8B5CF6", # Purple
    "#EC4899", # Pink
    "#F59E0B", # Amber
    "#10B981", # Emerald
    "#06B6D4", # Cyan
    "#F43F5E", # Rose
]

_chart_template = go.layout.Template(pio.templates["plotly_dark"])
_chart_template.layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=CHART_COLORS,
    font=dict(family="Figtree, system-ui, sans-serif", color="#F8FAFC", size=13),
    title=dict(
        font=dict(
            family="Bricolage Grotesque, Figtree, sans-serif",
            size=18,
            color="#F8FAFC",
        )
    ),
    xaxis=dict(
        gridcolor="rgba(148,163,184,.14)",
        zerolinecolor="rgba(148,163,184,.14)",
        linecolor="#334155",
    ),
    yaxis=dict(
        gridcolor="rgba(148,163,184,.14)",
        zerolinecolor="rgba(148,163,184,.14)",
        linecolor="#334155",
    ),
    hoverlabel=dict(
        bgcolor="#1E293B",
        bordercolor="#334155",
        font=dict(family="Figtree, system-ui, sans-serif", color="#F8FAFC"),
    ),
)
px.defaults.template = _chart_template
px.defaults.color_discrete_sequence = CHART_COLORS

_today = date.today()
st.markdown(
    f"""
    <header class="mt-masthead">
      <div>
        <div class="mt-day" aria-hidden="true">{_today.day}</div>
        <div class="mt-daymeta"><b>{_today.strftime("%A")}</b>{_today.strftime("%B %Y")}</div>
      </div>
      <div>
        <div class="mt-name" role="heading" aria-level="1">MindTrack AI</div>
        <div class="mt-tag">Log how you feel, talk it through, and see how your weeks add up.</div>
      </div>
    </header>
    """,
    unsafe_allow_html=True,
)

st.info(
    "MindTrack AI is a wellness companion, not a diagnostic tool "
    "or a replacement for professional mental healthcare."
)

# Session state initialization for authentication
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

# If not authenticated, display login & registration
if st.session_state.authenticated_user is None:
    st.markdown("### Sign in or create an account")
    st.caption(
        "Sign in to pick up your check-ins and chats, or create an account to get started."
    )

    auth_tab_login, auth_tab_register, auth_tab_forgot = st.tabs(
        ["Sign in", "Create account", "Forgot password"]
    )

    with auth_tab_login, st.form("login_form"):
        login_username = st.text_input("Username", key="login_username_input").strip()
        login_password = st.text_input(
            "Password", type="password", key="login_password_input"
        )
        login_submitted = st.form_submit_button(
            "Sign in", type="primary", width="stretch"
        )

        if login_submitted:
            user_obj, err = authenticate_user(login_username, login_password)
            if user_obj:
                st.session_state.authenticated_user = user_obj
                st.toast(f"👋 Welcome back, {user_obj['username']}.")
                st.rerun()
            else:
                st.error(err or "Invalid username or password.")

    with auth_tab_login:
        st.caption(
            "**Forgot your password?** Open the **Forgot password** tab above to recover your account with your security question or emergency recovery key."
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

            st.markdown("##### Account recovery")
            reg_sec_q_select = st.selectbox(
                "Select a security question",
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
                "Security answer",
                key="reg_sec_a_input",
                help="Answers are stored securely as cryptographic hashes and verified case-insensitively.",
            ).strip()

            reg_submitted = st.form_submit_button(
                "Create account", type="primary", width="stretch"
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
                            f"Account created successfully! Welcome, {user_obj['username']}!"
                        )
                        st.rerun()
                    else:
                        st.error(err or "Registration failed.")

    with auth_tab_forgot:
        st.markdown("#### Reset your password")
        st.caption(
            "Recover access to your account using your security question or single-use emergency recovery key."
        )

        with st.expander("Look up your security question"):
            lookup_user = st.text_input(
                "Enter your username to view your configured question:",
                key="lookup_username_input",
            ).strip()
            if st.button("Check Question", key="lookup_question_btn"):
                if lookup_user:
                    q_found, q_err = get_security_question(lookup_user)
                    if q_found:
                        st.info(
                            f"**Security question for `{lookup_user}`:**\n\n*{q_found}*"
                        )
                    else:
                        st.error(q_err or "Could not find a security question.")
                else:
                    st.warning("Please enter your username.")

        recovery_method = st.radio(
            "Choose verification method:",
            options=["Security question", "Emergency recovery key"],
            horizontal=True,
            key="forgot_recovery_method",
        )

        with st.form("forgot_password_form"):
            forgot_user = st.text_input(
                "Username",
                key="forgot_username_input",
                placeholder="Enter your username",
            ).strip()

            if recovery_method == "Security question":
                forgot_sec_answer = st.text_input(
                    "Security answer",
                    key="forgot_sec_answer_input",
                    placeholder="Enter the answer to your security question",
                    help="Verification is case-insensitive.",
                ).strip()
                forgot_recovery_key = ""
            else:
                forgot_sec_answer = ""
                forgot_recovery_key = st.text_input(
                    "Emergency recovery key",
                    key="forgot_recovery_key_input",
                    placeholder="MT-XXXX-XXXX-XXXX",
                    help="Enter the 16-character emergency recovery key.",
                ).strip()

            forgot_new_pass = st.text_input(
                "New password",
                type="password",
                key="forgot_new_pass_input",
                help="At least 8 characters.",
            )
            forgot_confirm_pass = st.text_input(
                "Confirm new password",
                type="password",
                key="forgot_confirm_pass_input",
            )

            forgot_submit = st.form_submit_button(
                "Reset password",
                type="primary",
                width="stretch",
            )

            if forgot_submit:
                if not forgot_user:
                    st.error("Please enter your username.")
                elif forgot_new_pass != forgot_confirm_pass:
                    st.error("New passwords do not match.")
                elif recovery_method == "Security question":
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
                                "Password reset successfully. Switch to the **Sign in** tab to log in."
                            )
                        else:
                            st.error(err_msg or "Password reset failed.")
                else:
                    if not forgot_recovery_key:
                        st.error("Please enter your emergency recovery key.")
                    else:
                        ok, err_msg, new_key = reset_password_with_recovery_key(
                            forgot_user, forgot_recovery_key, forgot_new_pass
                        )
                        if ok:
                            st.success(
                                "Password reset successfully. Switch to the **Sign in** tab to log in."
                            )
                            if new_key:
                                st.info(
                                    f"**Your new single-use recovery key is:** `{new_key}`\n\n"
                                    "Please write this code down and store it in a secure location."
                                )
                        else:
                            st.error(err_msg or "Password reset failed.")

    # Notice for safe migration of existing data
    st.markdown("---")
    st.info(
        "**Notice for existing users:** If you previously had saved check-ins or conversations before user accounts, "
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
    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting = "Good morning"
    elif current_hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    st.markdown(f"### {greeting}, {current_user['username']} 👋")
    st.caption("Your private wellness space")

    # Display newly generated emergency recovery key alert if present
    if "new_recovery_key" in st.session_state:
        rec_key = st.session_state["new_recovery_key"]
        st.warning(
            f"**Emergency recovery key:** `{rec_key}`\n\n"
            "Please copy and store this key safely. You can use it to reset your password if you ever forget it."
        )
        if st.button("I have saved my key", key="dismiss_recovery_key_btn"):
            st.session_state.pop("new_recovery_key", None)
            st.rerun()

    if st.button("Sign out", key="sign_out_button", width="stretch"):
        st.session_state.authenticated_user = None
        st.session_state.pop("active_conversation_id", None)
        st.session_state.pop("conversation_selector", None)
        st.session_state.pop("chat_notice", None)
        st.session_state.pop("new_recovery_key", None)
        st.rerun()

    with st.expander("Change password"):
        with st.form("change_pw_form", clear_on_submit=True):
            curr_pass = st.text_input("Current password", type="password")
            new_pass = st.text_input("New password (min 8 chars)", type="password")
            confirm_new_pass = st.text_input("Confirm new password", type="password")
            pw_change_submitted = st.form_submit_button(
                "Update password", width="stretch"
            )

            if pw_change_submitted:
                if new_pass != confirm_new_pass:
                    st.error("New passwords do not match.")
                else:
                    ok, change_err = change_user_password(
                        current_user["id"], curr_pass, new_pass
                    )
                    if ok:
                        st.toast("✅ Password updated successfully!")
                    else:
                        st.error(change_err or "Failed to change password.")

    with st.expander("Security question and recovery key"):
        st.caption(
            "Configure how you recover your account if you forget your password."
        )
        with st.form("update_sec_q_form", clear_on_submit=True):
            st.markdown("**Update security question**")
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
                "Save recovery question", width="stretch"
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
                    st.toast("✅ Security question updated successfully!")
                else:
                    st.error(err or "Failed to update security question.")

        with st.form("regen_rec_key_form", clear_on_submit=True):
            st.markdown("**Regenerate recovery key**")
            st.caption("Generates a new single-use 16-character recovery key.")
            curr_pw_rec = st.text_input(
                "Current password", type="password", key="rec_curr_pw"
            )
            submit_rec_key = st.form_submit_button(
                "Generate new recovery key", width="stretch"
            )

            if submit_rec_key:
                new_k, err = regenerate_recovery_key(
                    current_user["id"], curr_pw_rec
                )
                if new_k:
                    st.toast("🔑 New emergency recovery key generated.")
                    st.info(f"**`{new_k}`**\nPlease copy and store this safely.")
                else:
                    st.error(err or "Failed to generate recovery key.")

# Application tabs
checkin_tab, chat_tab, dashboard_tab = st.tabs(
    ["Daily check-in", "AI companion", "Mood insights"]
)

# ==================================================
# Daily Check-in
# ==================================================

with checkin_tab:
    st.subheader("How are you feeling today?")
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
            "Choose the mood that best describes how you feel",
            options=list(mood_emojis.keys()),
            format_func=lambda value: f"{mood_emojis[value]}  {value}",
            help="Choose the mood that feels closest to your experience.",
        )

        intensity = st.slider(
            "How intense is this feeling?",
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
            "Save check-in",
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

            st.toast("🌿 Check-in saved successfully!")

        except ValueError as exc:
            st.toast(f"⚠️ {str(exc)}")

        except Exception:
            logger.exception("Failed to save mood check-in.")
            st.toast("⚠️ The check-in could not be saved. Please try again.")

    st.subheader("Recent check-ins")

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

        with st.expander("Delete a check-in"):
            entry_options = {
                f"#{entry['id']} · {entry['date']} · {entry['mood']}":
                entry["id"]
                for entry in entries
            }

            selected_entry = st.selectbox(
                "Select an entry",
                options=list(entry_options.keys()),
            )

            if st.button("Delete selected entry"):
                try:
                    with st.spinner("Deleting check-in..."):
                        deleted = delete_mood_entry(
                            user_id=current_user["id"],
                            entry_id=entry_options[selected_entry],
                        )

                    if deleted:
                        st.toast("🗑️ Check-in deleted.")
                        st.rerun()
                    else:
                        st.toast("⚠️ That entry no longer exists.")

                except Exception:
                    logger.exception("Failed to delete mood check-in.")
                    st.toast("⚠️ Could not delete the selected check-in.")

    else:
        st.markdown(
            """
            <div style="text-align: center; padding: 3rem 1rem; opacity: 0.7;">
                <h3 style="margin-bottom: 0.5rem;">🌱 It's quiet in here</h3>
                <p>You haven't logged any check-ins yet. Take a moment to reflect on your day and add your first entry above.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )


# ==================================================
# Persistent AI Chatbot
# ==================================================

with chat_tab:
    st.subheader("Your AI wellness companion")

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
        if st.button("New conversation", width="stretch"):
            try:
                with st.spinner("Creating a new conversation..."):
                    new_id = create_conversation(user_id=current_user["id"])

                st.session_state.active_conversation_id = new_id
                st.session_state.pop("conversation_selector", None)
                st.rerun()

            except Exception:
                logger.exception("Failed to create conversation.")
                st.toast("⚠️ Could not create a new conversation.")

    with col_delete:
        if st.button("Delete current chat", width="stretch"):
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
                    st.toast("🗑️ Conversation deleted.")
                    st.rerun()

                else:
                    st.toast("⚠️ The conversation no longer exists.")

            except Exception:
                logger.exception("Failed to delete conversation.")
                st.toast("⚠️ Could not delete this conversation.")

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
                ### Welcome to your wellness space

                Talk about your day, reflect on your mood, or explore
                simple everyday wellness strategies.

                **Not sure where to start?**
                - Managing a stressful day
                - Reflecting on your emotions
                - Building a calming routine

                What has been on your mind lately?
                """
            )

        for message in messages:
            avatar = (
                ":material/spa:"
                if message["role"] == "assistant"
                else ":material/person:"
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
    st.subheader("Mood analytics")

    st.caption(
        "Explore your recorded mood patterns and intensity over time. "
        "These summaries describe your entries; they are not diagnoses."
    )

    with st.spinner("Preparing your mood analytics..."):
        entries = get_mood_entries(user_id=current_user["id"])

    if not entries:
        st.markdown(
            """
            <div style="text-align: center; padding: 3rem 1rem; opacity: 0.7;">
                <h3 style="margin-bottom: 0.5rem;">📊 Data is gathering</h3>
                <p>No mood entries yet. Save a check-in in the Daily check-in tab to start building your personal mood dashboard.</p>
            </div>
            """, 
            unsafe_allow_html=True
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
                    st.markdown("### Date range")

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
                            delta="relative to overall average",
                            delta_color="inverse"
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
                        st.subheader("Mood trend analysis")

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

                            st.markdown("#### Your trend reflections")

                            for trend_insight in trend_result["insights"]:
                                st.markdown(f"- {trend_insight}")

                        # Personalized AI mood insights.
                        st.divider()
                        st.subheader("Personalized AI mood insights")

                        st.caption(
                            "Discover reflections based on your recorded "
                            "mood patterns. Insights are descriptive, "
                            "not diagnostic."
                        )

                        if st.button(
                            "Generate my mood insights",
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
                        st.markdown("### Mood distribution")

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
                                title="Your mood distribution",
                                color_discrete_sequence=CHART_COLORS,
                            )

                            fig_pie.update_traces(
                                textposition="inside",
                                textinfo="percent+label",
                                marker=dict(line=dict(color="#1E293B", width=2)),
                            )

                            st.plotly_chart(
                                fig_pie,
                                width="stretch",
                            )


                                                # Daily intensity trend.
                        st.markdown("### Mood intensity over time")

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
                        st.markdown("### Weekly mood patterns")

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
                        st.markdown("### Intensity by recorded mood")

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
                        st.markdown("### Personal reflection insights")

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
                            label="Download filtered mood data (CSV)",
                            data=csv_data,
                            file_name=(
                                f"mindtrack_mood_{start_date}_"
                                f"{end_date}.csv"
                            ),
                            mime="text/csv",
                        )

                        # PDF report export.
                        st.divider()
                        st.subheader("Download your mood report")

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
                                label="Download PDF mood report",
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
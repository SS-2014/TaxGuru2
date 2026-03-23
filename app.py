import streamlit as st
import os
from gemini_integration import call_agent, analyze_document

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="TaxGuru", layout="wide")

api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Missing GEMINI_API_KEY")
    st.stop()

# =========================
# THEME TOGGLE
# =========================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

def toggle_theme():
    st.session_state.dark_mode = not st.session_state.dark_mode

# =========================
# CSS (LIGHT + DARK)
# =========================
if st.session_state.dark_mode:
    bg = "#0b0f1a"
    card = "#111827"
    text = "#e5e7eb"
    border = "#7c3aed"
else:
    bg = "#f9fafb"
    card = "#ffffff"
    text = "#111827"
    border = "#7c3aed"

st.markdown(f"""
<style>
body {{
    background-color: {bg};
    color: {text};
}}

.stApp {{
    background-color: {bg};
}}

.card {{
    background: {card};
    padding: 20px;
    border-radius: 12px;
    border: 1px solid {border};
    margin-bottom: 15px;
}}

.big-title {{
    font-size: 36px;
    font-weight: 700;
}}

.subtitle {{
    color: gray;
}}

.nav {{
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
}}

.nav button {{
    border-radius: 20px;
}}
</style>
""", unsafe_allow_html=True)

# =========================
# NAVBAR
# =========================
col1, col2 = st.columns([8,2])

with col1:
    st.markdown("### 🛡️ TaxGuru")

with col2:
    st.button("🌙 Toggle Theme", on_click=toggle_theme)

tabs = st.tabs([
    "Home",
    "Tax Profile",
    "Calculator",
    "Savings",
    "Updates"
])

# =========================
# SESSION STATE
# =========================
if "profile" not in st.session_state:
    st.session_state.profile = {}

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =========================
# HOME TAB
# =========================
with tabs[0]:
    st.markdown('<div class="big-title">Stop overpaying your taxes.</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">AI that knows Indian tax law</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="card">📊 Tax Calculator<br><br>Compare old vs new regime</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">🔍 What-if Scenarios<br><br>See impact of decisions</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="card">💡 Savings Finder<br><br>Maximize deductions</div>', unsafe_allow_html=True)

# =========================
# TAX PROFILE
# =========================
with tabs[1]:
    st.subheader("Upload Payslip / Form 16")

    uploaded_file = st.file_uploader("Upload document", type=["png","jpg","jpeg"])

    if uploaded_file:
        st.info("Analyzing...")

        result = analyze_document(
            uploaded_file.read(),
            api_key=api_key,
            mime_type="image/png"
        )

        if "error" in result:
            st.error(result["error"])
        else:
            st.success("Processed successfully")
            st.json(result)

            multiplier = 12 if result.get("period") == "monthly" else 1

            st.session_state.profile = {
                "salary": result.get("gross_salary", 0) * multiplier,
                "hra": result.get("hra", 0) * multiplier,
                "tds": result.get("tds_deducted", 0) * multiplier
            }

# =========================
# CHAT
# =========================
with tabs[0]:

    st.subheader("💬 Ask TaxGuru")

    user_input = st.chat_input("Ask anything about tax...")

    if user_input:
        response = call_agent(
            user_input,
            api_key=api_key,
            user_profile=st.session_state.profile
        )

        st.chat_message("user").write(user_input)
        st.chat_message("assistant").write(response)

        st.session_state.chat_history.append((user_input, response))

# =========================
# SAVINGS TAB
# =========================
with tabs[3]:
    st.subheader("Tax Savings Insights")

    if st.session_state.profile:
        st.markdown('<div class="card">💰 You may save more tax using 80C, 80D, NPS</div>', unsafe_allow_html=True)
    else:
        st.info("Upload payslip first")

# =========================
# UPDATES TAB
# =========================
with tabs[4]:
    st.subheader("Recent Tax Updates")

    updates = [
        "Income up to ₹12.75L tax-free (new regime)",
        "Capital gains tax changes",
        "AIS alerts introduced"
    ]

    for u in updates:
        st.markdown(f'<div class="card">{u}</div>', unsafe_allow_html=True)

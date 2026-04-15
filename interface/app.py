import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from interface.api import GridMindAPI

st.set_page_config(page_title="GRIDMIND OS", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Mandatory Color System */
    :root {
        --bg-primary: #0B0F14;
        --bg-secondary: #11161C;
        --accent: #1F6FEB;
        --text-primary: #E6EDF3;
        --text-secondary: #9BA7B4;
        --border: #1C2128;
        --highlight: #2EA043;
    }

    .stApp {
        background-color: var(--bg-primary);
        color: var(--text-primary);
        font-family: "SF Pro Display", -apple-system, blinkmacsystemfont, "Segoe UI", roboto, sans-serif;
    }
    
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary) !important;
        border-right: 1px solid var(--border);
    }
    
    [data-testid="stHeader"] {
        background-color: var(--bg-primary) !important;
    }

    h1, h2, h3, h4, h5, h6, p, li, span, div {
        color: var(--text-primary) !important;
    }

    /* Minimalist Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background-color: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 4px;
        transition: border 0.3s ease;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border: 1px solid var(--accent) !important;
        box-shadow: none !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: var(--bg-secondary);
        color: var(--text-primary);
        border: 1px solid var(--border);
        border-radius: 4px;
        transition: all 0.2s ease-in-out;
        font-family: monospace;
    }
    .stButton > button:hover {
        border-color: var(--accent);
        color: var(--accent) !important;
    }

    /* Chat Interface */
    .stChatMessage {
        background-color: var(--bg-secondary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    [data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {
        display: none !important;
    }
    
    /* Logo styling */
    .gridmind-logo {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 24px;
        font-weight: 800;
        letter-spacing: 4px;
        color: var(--text-primary) !important;
        padding: 20px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 20px;
    }
    .gridmind-logo span {
        color: #D4AF37 !important; /* Golden accent */
    }
    
    hr {
        border-color: var(--border) !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("""
<div class="gridmind-logo">
    <span style="color: #D4AF37;">GRID</span>MIND
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("**STATUS:** OFFLINE")
st.sidebar.markdown("**SYS:** ACTIVE")
st.sidebar.markdown("---")
top_k = st.sidebar.slider("Context Depth (Top K)", min_value=1, max_value=6, value=3)

# Initialize API
@st.cache_resource
def load_api():
    return GridMindAPI()

api = load_api()

st.title("TERMINAL")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Enter command sequence..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Replace emojis in status with textual states
        with st.status("[SYS] Analyzing vectors...", expanded=False) as status:
            st.write("[SYS] Querying FAISS index...")
            try:
                response_stream = api.query(prompt, top_k=top_k)
                status.update(label="[SYS] Streaming...", state="running")
                
                for chunk in response_stream:
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                
                status.update(label="[SYS] Output complete.", state="complete")
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                status.update(label="[ERR] Critical Failure", state="error")
                st.error(f"FAILURE: {str(e)}")
                
        st.session_state.messages.append({"role": "assistant", "content": full_response})

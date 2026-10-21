"""
The key lives only in st.session_state for the current session.\
It is never written to disk, never put in os.environ.
"""

import streamlit as st

API_KEY = ""

def mask(key: str) -> str:
    """Return a safe-to-display version of an api key 123...789"""
    if not key:
        return ""
    return f"{key[:4]}…{key[-4:]}"

def render_api_key() -> str | None:
    """Render the key input in the sidebar and return key/None"""
    with st.sidebar:
        st.subheader("API Key")
        key = st.session_state.get(API_KEY, "")
        if key:
            st.caption(f"Using key {mask(key)}")
            if st.button("Forget key"):
                del st.session_state[API_KEY]
                st.rerun()
            return key

        entered = st.text_input(
            "Enter your key",
            type="password",
            placeholder="gsk_..."
        ).strip()

        if not entered:
            st.info("Enter an api key to start chatting")
            return None

        st.session_state[API_KEY] = entered
        st.rerun()

import streamlit as st

class APIKey:
    """An API key stored in st.session_state, not written to disk"""
    def __init__(self, provider: str, prefix: str):
        self.provider = provider
        self.prefix = prefix
        self.state_key = f"{provider.lower()}_api_key"

    @property
    def value(self) -> str | None:
        return st.session_state.get(self.state_key)

    def forget(self):
        st.session_state.pop(self.state_key, None)

    @staticmethod
    def mask(key: str) -> str:
        """Return a safe-to-display version of an api key gsk_…789a"""
        return f"{key[:4]}…{key[-4:]}"


    def render(self) -> str | None:
        """Render the key input in the sidebar and return key/None"""
        with st.sidebar:
            st.subheader(f"{self.provider} API Key")
            if self.value:
                st.caption(f"Using key {self.mask(self.value)}")
                if st.button("Forget key"):
                    self.forget()
                    st.rerun()
                return self.value

            entered = st.text_input("Enter your key",type="password",placeholder=f"{self.prefix}").strip()

            if not entered:
                st.info(f"Enter a {self.provider} api key to start chatting")
                return None

            st.session_state[self.state_key] = entered
            st.rerun()

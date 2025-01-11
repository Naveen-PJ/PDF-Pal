import streamlit as st

def get_session_state():
    if 'pdf_text' not in st.session_state:
        st.session_state.pdf_text = None
    return st.session_state
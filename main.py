import streamlit as st
from utils.pdf_processing import extract_text_from_pdf
from utils.chat_engine import ChatEngine
from utils.session_state import get_session_state

st.title("PDF Chatbot")

# API Key Input
api_key = st.text_input("Enter your OpenAI API key:", type="password")
if not api_key:
    st.error("API key is required to proceed.")
    st.stop()

# PDF Upload
uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
if uploaded_file is not None:
    pdf_text = extract_text_from_pdf(uploaded_file)
    st.session_state.pdf_text = pdf_text

# Chat Interface
if "pdf_text" in st.session_state:
    chat_engine = ChatEngine(api_key, st.session_state.pdf_text)
    user_input = st.text_input("Ask a question about the PDF:")
    if user_input:
        response = chat_engine.get_response(user_input)
        st.write(response)

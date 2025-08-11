# =============================================================================
# Updated PDF_Pal.py
# This file contains the Streamlit UI and logic to run the application.
# =============================================================================

import streamlit as st
import uuid
import re
from src.src_PDF_Pal import PDFPal, log_message

# =============================================================================
# Step 1: Initialize Logging and Page Configuration
# =============================================================================
try:
    with open("PDF_Pal.log", "w") as f:
        f.write("Starting new application run.\n")
except IOError as e:
    st.error(f"Error initializing log file: {e}")

log_message("Application started. Setting Streamlit page config.")

# Configure Streamlit page
st.set_page_config(
    page_title="PDF-Pal",
    page_icon="📄",
    layout="centered"
)

# =============================================================================
# Step 2: Session State Management
# =============================================================================
if "pdf_pal" not in st.session_state:
    try:
        groq_api_key = st.secrets["groq"]["API_KEY"]
        st.session_state.pdf_pal = PDFPal(groq_api_key)
        log_message("PDFPal instance created and stored in session state.")
    except KeyError:
        st.error("Groq API key not found. Please add it to `secrets.toml`.")
        log_message("ERROR: Groq API key not found.")
        st.stop()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    log_message("Chat history initialized.")

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    log_message(f"Unique session ID created: {st.session_state.session_id}")


# =============================================================================
# Step 3: Main Application UI with Fixed Top Bar
# =============================================================================
def main():
    # Inject CSS for a fixed top bar containing the title and expander
    st.markdown("""
        <style>
            /* Hide the Streamlit header */
            .stApp header {
                visibility: hidden;
                height: 0;
            }

            /* Main container for the fixed top bar */
            .fixed-top-bar {
                position: fixed;
                top: 0;
                width: 100%;
                z-index: 999;
                background-color: #0e1117; /* Use your app's background color */
                padding: .1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,.1);
                hieght: 3;
            }

            /* Padding for the content below the fixed bar */
            .content-padding {
                padding-top: .1rem; /* Adjust this value to match the height of your fixed top bar */
                position: fixed;;
            }
                
            .dropdown-content {
                position: fixed;
                top: 0;
                }
        </style>
    """, unsafe_allow_html=True)
    
    # Create the fixed top bar using a container
    with st.container():
        st.markdown('<div class="fixed-top-bar">', unsafe_allow_html=True)
        st.title("PDF-Pal 📄")
        
        
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Chat History Container with Padding ---
    with st.container():
        st.markdown('<div class="content-padding">', unsafe_allow_html=True)
        if st.session_state.vector_store:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        st.markdown('<div class= "dropdown-content">', unsafe_allow_html=True)
        # --- Upload/Control Section (replaces the sidebar) ---
        with st.expander("Upload PDFs"):
            uploaded_files = st.file_uploader(
                "Choose PDF files",
                type="pdf",
                accept_multiple_files=True
            )

            if uploaded_files:
                with st.spinner('Processing PDFs...'):
                    raw_text = st.session_state.pdf_pal.extract_text_from_pdfs(uploaded_files)
                    text_chunks = st.session_state.pdf_pal.get_text_chunks(raw_text)
                    st.session_state.vector_store = st.session_state.pdf_pal.get_vector_store(text_chunks)
                st.success("PDFs processed successfully")
                log_message("PDF processing complete and vector store created.")

            st.markdown("---") # Add a separator

            if st.button("Erase & Start Over"):
                st.session_state.chat_history = []
                st.session_state.vector_store = None
                st.session_state.session_id = str(uuid.uuid4())
                st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- User Input and Response Generation ---
    user_question = st.chat_input(
        "Ask questions about your uploaded PDFs...",
        disabled=st.session_state.vector_store is None
    )

    if user_question:
        if st.session_state.vector_store is None:
            st.error("Please upload and process a PDF first.")
            log_message("ERROR: User tried to ask a question before uploading a PDF.")
            return

        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.write(user_question)

        with st.spinner('Generating response...'):
            response = st.session_state.pdf_pal.get_response(
                user_question,
                st.session_state.vector_store,
                st.session_state.session_id
            )
            
            if response:
                cleaned_response = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', response, flags=re.DOTALL)
                with st.chat_message("assistant"):
                    st.write(cleaned_response)
                
                st.session_state.chat_history.append({"role": "assistant", "content": cleaned_response})


if __name__ == "__main__":
    main()
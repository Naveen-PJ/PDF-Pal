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
# Step 3: Main Application UI with Fixed Top & Bottom Bars
# =============================================================================
def main():
    # --- Inject CSS for fixed top and bottom containers ---
    st.markdown("""
        <style>
            .stApp header {visibility: hidden; height: 0;}
            
            /* Main container to hold all content */
            .main-container {
                display: flex;
                flex-direction: column;
                height: 100vh;
            }

            /* Fixed Top Bar */
            .fixed-top-bar {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                z-index: 999;
                background-color: #0e1117;
                padding: 0.8rem 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,.2);
            }
            .app-title {
                font-size: 1.8rem;
                font-weight: bold;
                color: white;
            }

            /* Main chat content area, takes all available space and scrolls */
            .main-chat-area {
                flex-grow: 1; 
                overflow-y: auto;
                padding: 1rem;
                min-height: calc(100vh - 120px); /* This line fixes the initial positioning */
            }

            /* Fixed Bottom Bar */
            .fixed-bottom-bar {
                position: sticky;
                bottom: 0;
                left: 0;
                width: 100%;
                z-index: 999;
                background-color: #0e1117;
                padding: 0.5rem 1rem;
                box-shadow: 0 -2px 4px rgba(0,0,0,.2);
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            
            /* Hide the default Streamlit footer */
            footer {
                visibility: hidden;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- Fixed Top Bar: Title ---
    st.markdown("""
        <div class="fixed-top-bar">
            <span class="app-title">📄 PDF-Pal</span>
        </div>
    """, unsafe_allow_html=True)
    
    # --- Main Chat Area: Scrolling Chat History ---
    chat_placeholder = st.empty()

    # --- Fixed Bottom Bar: Input & Upload ---
    st.markdown('<div class="fixed-bottom-bar">', unsafe_allow_html=True)
    
    # Track upload status
    upload_success = False

    # Upload menu
    with st.expander("📂 Upload PDFs", expanded=False):
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type="pdf",
            accept_multiple_files=True
        )

        if uploaded_files:
            # Only set a flag here — don't display messages yet
            process_pdfs = True
        else:
            process_pdfs = False

    # Now show processing messages outside the expander
    if process_pdfs :
        with st.spinner('Processing PDFs...'):
            raw_text = st.session_state.pdf_pal.extract_text_from_pdfs(uploaded_files)
            text_chunks = st.session_state.pdf_pal.get_text_chunks(raw_text)
            st.session_state.vector_store = st.session_state.pdf_pal.get_vector_store(text_chunks)
        st.success("✅ PDFs processed successfully")
        log_message("PDF processing complete and vector store created.")


    # Chat input
    user_question = st.chat_input(
        "Ask questions about your uploaded PDFs...",
        disabled=st.session_state.vector_store is None
    )

    st.markdown('</div>', unsafe_allow_html=True) # Close fixed-bottom-bar
    
    # User question handling logic
    if user_question:
        if st.session_state.vector_store is None:
            st.error("Please upload and process a PDF first.")
            return
        
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        
        with st.spinner('Generating response...'):
            response = st.session_state.pdf_pal.get_response(
                user_question,
                st.session_state.vector_store,
                st.session_state.session_id
            )
            
            if response:
                cleaned_response = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', response, flags=re.DOTALL)
                st.session_state.chat_history.append({"role": "assistant", "content": cleaned_response})
    
    # Display chat history in the placeholder container
    with chat_placeholder.container():
        st.markdown('<div class="main-chat-area">', unsafe_allow_html=True)
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
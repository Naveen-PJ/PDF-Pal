import streamlit as st
from src.PDF_Pal import PDFPal
import re

# Configure Streamlit page
st.set_page_config(
    page_title="PDF-Pal",
    page_icon="📄",
    layout="centered"
)

# Initialize PDFPal
pal = PDFPal()

def PDF_Pal():
    # Title and description
    st.title("PDF-Pal 📄")
    st.write("Ask questions about your uploaded PDFs")

    # Sidebar for PDF upload
    st.sidebar.header("Upload PDFs")
    uploaded_files = st.sidebar.file_uploader(
        "Choose PDF files", 
        type="pdf", 
        accept_multiple_files=True
    )

    # Process PDFs if uploaded
    if uploaded_files:
        with st.spinner('Processing PDFs...'):
            pal.extract_text_from_pdfs(uploaded_files)
        st.sidebar.success("PDFs processed successfully")

    
    # Create columns for input and button
    # Create a row with the text input and button aligned
    col1, col2 = st.columns([7, 1])

    with col1:
        st.markdown("<br>", unsafe_allow_html=True)
        user_question = st.text_input(
            "", 
            placeholder="What would you like to know?", 
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Adds some vertical alignment padding
        submit_button = st.button("Ask", use_container_width=True, key="ask_button")


    # Response area
    response_container = st.container()

    # Query processing
    if submit_button and user_question:
        # Check if PDFs are uploaded
        if not pal.text.strip():
            st.error("Please upload a PDF first")
            return

        # Generate response
        with st.spinner('Thinking...'):
            # Use the existing query method
            model = 'deepseek-r1-distill-llama-70b'
            conversational_memory_length = 10
            
            answer = pal.query(user_question, model, conversational_memory_length, pal.text)
            
            # Clean up response (remove any think tags)
            clean_response = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
            
            # Display response
            with response_container:
                st.info(clean_response)

if __name__ == "__main__":
    PDF_Pal()
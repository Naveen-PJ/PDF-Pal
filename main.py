import streamlit as st
from src.PDF_Pal import PDFPal

pal = PDFPal()  # Correct instantiation

def PDF_Pal():
    st.title("PDF-Pal")

    st.sidebar.title('Upload PDF files')
    st.sidebar.write("**Note:** This application can only process text-based PDFs. PDFs with scanned images or non-text elements are prone to errors and may not be fully processed.")
    
    uploaded_files = st.sidebar.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)
    
    if uploaded_files:
        pal.extract_text_from_pdfs(uploaded_files)
        
        st.sidebar.success("PDFs processed successfully.")
        st.sidebar.write("You can now ask questions about the PDFs.")
        if st.sidebar.button("Read"):
            pal.convert_to_speech(pal.text)


    
    model = 'llama-3.3-70b-versatile'
    conversational_memory_length = 10

    user_question = st.text_input("Ask a question:")  # Decrease the height

    # Initialize the conversation with the prompt
    if 'initialized' not in st.session_state:
        initial_prompt = "You are PDF-Pal, an AI assistant that helps users with information from PDF documents and general assistance."
        pal.query(initial_prompt, model, conversational_memory_length, pal.text)
        st.session_state.initialized = True

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    else:
        for message in st.session_state.chat_history:
            pal.query(message['human'], model, conversational_memory_length, pal.text)

    if st.button("Submit"):
        if not pal.text.strip():
            st.error("No text extracted from the PDF. Please upload a valid text-based PDF.")
            return "No text extracted from the PDF."
        if user_question:
            answer = pal.query(user_question, model, conversational_memory_length, pal.text)
            st.session_state.chat_history.append({'human': user_question, 'AI': answer})
            st.write("PDF-Pal:\n", answer)

if __name__ == "__main__":
    PDF_Pal()

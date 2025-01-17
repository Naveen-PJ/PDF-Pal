import logging
from PyPDF2 import PdfReader
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
import pyttsx3
import streamlit as st

groq_api_key = st.secrets["groq"]["API_KEY"]

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class PDFPal:
    def __init__(self):
        self.text = ""
        self.chat_history = []

    def extract_text_from_pdfs(self, uploaded_files):
        for uploaded_file in uploaded_files:
            try:
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    self.text += page.extract_text()
            except Exception as e:
                
                logging.error(f"Error extracting text from {uploaded_file.name}: {e}")
                st.error(f"Error extracting text from {uploaded_file.name}: {e}")
            

    def query(self, query, model, memory_length, pdf_text):
        try:
            memory = ConversationBufferWindowMemory(k=memory_length)
            for message in self.chat_history:
                memory.save_context({'input': message['human']}, {'output': message['AI']})

            groq_chat = ChatGroq(
                groq_api_key=groq_api_key,
                model_name=model
            )

            conversation = ConversationChain(
                llm=groq_chat,
                memory=memory
            )

            full_query = f"PDF Content:\n{pdf_text}\n\nUser Query:\n{query}"
            response = conversation(full_query)
            message = {'human': query, 'AI': response['response']}
            self.chat_history.append(message)
            return response['response']
        except Exception as e:
            logging.error(f"Error during query processing: {e}")
            st.error(f"Error during query processing: {e}")
            return "An error occurred during query processing."

    def convert_to_speech(self,text):
        if not text.strip():
            logging.error("No text available for conversion to speech.")
            st.error("No text available for conversion to speech.")
            return

        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            engine.setProperty('voice', voices[1].id)
            engine.setProperty('rate', 180)
            engine.setProperty('volume', 1.0)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logging.error(f"Error converting text to speech: {e}")
            st.error(f"Error converting text to speech: {e}")

# Example usage:
# pdf_pal = PDFPal()
# uploaded_files = [...] # List of uploaded PDF files
# pdf_pal.extract_text_from_pdfs(uploaded_files)
# response = pdf_pal.query("What is the summary?", "groq-model", 5, pdf_pal.text)
# pdf_pal.convert_to_speech()

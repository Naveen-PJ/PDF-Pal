from PyPDF2 import PdfReader
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
import pyttsx3
import streamlit as st

groq_api_key = st.secrets["groq"]["API_KEY"]

class PDFPal:
    def __init__(self):
        self.text = ""
        self.chat_history = []  # Initialize chat history

    def extract_text_from_pdfs(self, uploaded_files):
        for uploaded_file in uploaded_files:
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                self.text += page.extract_text()
        
    def query(self, query, model, memory_length, pdf_text):
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
    
    def convert_to_speech(self):
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[1].id)
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 1.0)
        engine.say(self.text)
        engine.runAndWait()

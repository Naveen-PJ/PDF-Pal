import logging
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

import pyttsx3
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq

groq_api_key = st.secrets["groq"]["API_KEY"]

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class PDFPal:
    def __init__(self):
        self.text = ""
        self.chat_history = []
        
        # Initialize embedding model
        try:
            # Use Langchain's HuggingFace embeddings
            self.embedding = HuggingFaceEmbeddings(
                model_name='all-MiniLM-L6-v2'
            )
        except Exception as e:
            logging.error(f"Error loading embedding model: {e}")
            st.error(f"Failed to load embedding model: {e}")
            self.embedding = None
        
        # Vector store
        self.vectorstore = None

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

    def extract_text_from_pdfs(self, uploaded_files):
        self.text = ""  # Reset text
        for uploaded_file in uploaded_files:
            try:
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    self.text += page.extract_text()
            except Exception as e:
                logging.error(f"Error extracting text from {uploaded_file.name}: {e}")
                st.error(f"Error extracting text from {uploaded_file.name}: {e}")
        
        # Create vector store after text extraction
        self._create_vector_store()

    def _create_vector_store(self):
        # Check if embedding is initialized
        if not self.embedding:
            st.warning("Embedding model not initialized. Skipping vectorization.")
            return
        
        try:
            # Split text into chunks
            text_chunks = self.text_splitter.split_text(self.text)
            
            # Create FAISS vector store in memory
            self.vectorstore = FAISS.from_texts(
                texts=text_chunks, 
                embedding=self.embedding
            )
            
            #st.sidebar.success(f"Vectorized {len(text_chunks)} text chunks.")
        except Exception as e:
            logging.error(f"Error creating vector store: {e}")
            st.error(f"Failed to create vector store: {e}")

    def query(self, query, model, memory_length, pdf_text):
        try:
            # Perform similarity search if vector store exists
            if self.vectorstore:
                # Perform similarity search
                results = self.vectorstore.similarity_search(
                    query, 
                    k=5  # Top 5 most relevant chunks
                )
                
                # Combine relevant chunks
                context = "\n".join([doc.page_content for doc in results])
                full_query = f"Relevant Context:\n{context}\n\nUser Query:\n{query}"
            else:
                # Fallback to original method if no vector store
                full_query = f"PDF Content:\n{pdf_text}\n\nUser Query:\n{query}"

            # Setup conversation memory
            memory = ConversationBufferWindowMemory(k=memory_length)
            for message in self.chat_history:
                memory.save_context({'input': message['human']}, {'output': message['AI']})

            # Initialize Groq chat
            groq_chat = ChatGroq(
                groq_api_key=groq_api_key,
                model_name=model
            )

            # Create conversation chain
            conversation = ConversationChain(
                llm=groq_chat,
                memory=memory
            )

            # Get response
            response = conversation(full_query)
            message = {'human': query, 'AI': response['response']}
            self.chat_history.append(message)
            return response['response']
        except Exception as e:
            logging.error(f"Error during query processing: {e}")
            st.error(f"Error during query processing: {e}")
            return "An error occurred during query processing."

    def convert_to_speech(self, text):
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

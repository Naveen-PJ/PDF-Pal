# =============================================================================
# Updated src_PDF_Pal.py
# This file contains the core logic for processing PDFs and generating responses.
# =============================================================================

# Updated imports for modern LangChain and related libraries
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage
import os
import re

# New imports for conversational memory in LCEL
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from typing import List, Dict, Any, Union

# Global dictionary to store chat message history for each session
store: Dict[str, ChatMessageHistory] = {}


# Function to log messages to a file
def log_message(message: str):
    """
    Writes a message to the PDF_Pal.log file.
    The file is cleared on every run.
    """
    with open("PDF_Pal.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


class PDFPal:
    def __init__(self, groq_api_key: str):
        # Initialize Groq LLM with a modern model and API key
        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=groq_api_key,
            model_name="llama3-8b-8192"
        )
        log_message("PDFPal initialized with ChatGroq model: llama3-8b-8192")
        
    def extract_text_from_pdfs(self, pdf_docs: List[Any]) -> str:
        """
        Extracts text from a list of PDF documents using pypdf.
        
        Args:
            pdf_docs: A list of uploaded PDF files from Streamlit.
            
        Returns:
            A single string containing all text extracted from the PDFs.
        """
        log_message(f"Starting text extraction from {len(pdf_docs)} PDFs.")
        raw_text = ""
        for pdf in pdf_docs:
            try:
                reader = PdfReader(pdf)
                for page in reader.pages:
                    if page.extract_text():
                        raw_text += page.extract_text()
            except Exception as e:
                log_message(f"Error extracting text from a PDF: {e}")
                
        log_message("Text extraction complete.")
        return raw_text

    def get_text_chunks(self, text: str) -> List[str]:
        """
        Splits a single string of text into smaller, overlapping chunks.
        
        Args:
            text: The full text extracted from the PDFs.
            
        Returns:
            A list of text chunks.
        """
        log_message("Splitting text into chunks.")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        log_message(f"Text split into {len(chunks)} chunks.")
        return chunks

    def get_vector_store(self, text_chunks: List[str]) -> FAISS:
        """
        Creates a FAISS vector store from text chunks.
        
        Args:
            text_chunks: A list of text chunks.
            
        Returns:
            A FAISS vector store.
        """
        log_message("Creating vector store from text chunks.")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
        log_message("Vector store creation complete.")
        return vector_store

    def get_conversational_chain(self) -> RunnableWithMessageHistory:
        """
        Builds a conversational retrieval chain using LangChain Expression Language (LCEL).
        
        This new approach replaces the deprecated `ConversationChain`.
        
        Returns:
            A `RunnableWithMessageHistory` object.
        """
        log_message("Building conversational chain with LCEL.")

        # Define the system prompt with clear instructions for the LLM
        system_template = """
        You are a helpful AI assistant. You have been provided with a document to assist with. Answer the user's questions based on the provided context, but also use your general knowledge.
        Do not add the tag `<|im_start|>thought` or `<|im_end|>`.
        Chat History:
        {history}
        
        Provided Context:
        {context}
        
        Question:
        {question}
        
        Your Answer:
        """

        # Create a new prompt template
        prompt = PromptTemplate.from_template(system_template)

        # Build the document chain
        document_chain = (
            {
                "context": RunnablePassthrough(),
                "history": lambda x: x["history"],
                "question": lambda x: x["question"],
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )

        def get_session_history(session_id: str) -> ChatMessageHistory:
            """
            Retrieves or creates a session history.
            """
            if session_id not in store:
                store[session_id] = ChatMessageHistory()
            return store[session_id]

        # Use RunnableWithMessageHistory to manage the conversation
        conversational_chain = RunnableWithMessageHistory(
            document_chain,
            get_session_history,
            input_messages_key="question",
            history_messages_key="history",
        )
        
        log_message("Conversational chain built successfully.")
        return conversational_chain

    def get_response(self, user_question: str, vector_store: FAISS, session_id: str) -> Union[str, None]:
        """
        Generates a response to the user's question using the conversational chain.
        
        Args:
            user_question: The question from the user.
            vector_store: The FAISS vector store with document embeddings.
            session_id: The unique session ID for conversation history.
            
        Returns:
            The generated response from the LLM or None if an error occurs.
        """
        log_message(f"Retrieving response for question: '{user_question}'")
        try:
            # Retrieve relevant documents from the vector store
            docs = vector_store.similarity_search(user_question)
            
            # Format the documents into a single context string
            context = "\n".join([doc.page_content for doc in docs])
            
            # Get the session history from the global store
            history = store.get(session_id, ChatMessageHistory())
            
            # Prepare the input for the chain, including context and history
            chain_input = {
                "question": user_question,
                "context": context,
                "history": [
                    (message.content, "User") if isinstance(message, HumanMessage) else (message.content, "AI")
                    for message in history.messages
                ],
            }

            # Get the conversational chain
            conversational_chain = self.get_conversational_chain()

            # Invoke the chain to get the response.
            # The StrOutputParser makes the chain return a string, not a dictionary.
            response = conversational_chain.invoke(
                chain_input,
                config={"configurable": {"session_id": session_id}}
            )

            # --- CORRECTION STARTS HERE ---
            # The 'response' variable is already the string output.
            # There is no need to access a ['response'] key.
            cleaned_response = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', response, flags=re.DOTALL)
            
            log_message(f"Generated response: {cleaned_response}")
            return cleaned_response
            # --- CORRECTION ENDS HERE ---
            
        except Exception as e:
            log_message(f"An error occurred while generating a response: {e}")
            return None
from src.schemas import Promptschema
from src.config import config, load
from src.logger import logger

import json
from pathlib import Path
from groq import Groq
import chromadb
import uuid
from pypdf import PdfReader
from typing import List, Any
from chonkie import RecursiveChunker

class PDF_Pal_Brain:
    """
    This class serves as the core "brain" of the PDF_Pal application. 
    It is responsible for managing interactions with the LLM, maintaining conversation history, 
    and providing methods for chatting and clearing history.
    """
    def __init__(self)-> None  :
        logger.info("Initializing PDF_Pal_Brain class.")
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.system_prompt = Path(Path(__file__).resolve().parent / "prompts" / "PDF_Pal_prompt.md").read_text()
        
        # Modified to handle multiple sessions mapped by ID
        self.history = {}
        logger.success("PDF_Pal_Brain class initialized successfully.")

    def clear_history(self, session_id: str = "default")-> None:
        """
        Clears the conversation history for a specific session.
        
        Args:
            session_id (str): The unique identifier for the user session whose history should be cleared. 
                              Defaults to "default".
                              
        Returns:
            None
        """
        logger.info(f"Clearing conversation history for session: {session_id}")
        if session_id in self.history:
            self.history[session_id] = []
        logger.success(f"Conversation history cleared for session: {session_id}")

    def chat(self,query: str, context: str = None , temperature: float = None, context_window: int = None, session_id: str = "default") -> str:
        """
        This function is used to call the LLM with the given query and context. 
        It also maintains a history of the conversation per session.
        
        Args:
            query (str): The user query to be sent to the LLM.
            context (str, optional): The retrieved RAG context to be sent to the LLM to ground its knowledge.
            temperature (float, optional): The creativity/randomness setting to be used for the LLM response.
            context_window (int, optional): The max number of previous messages to be sent as history context.
                                            Used to prevent exceeding context window limits.
            session_id (str, optional): The unique identifier for the user session to map conversation history.
                                        Defaults to "default".
                                        
        Returns:
            str: The text response generated from the LLM.
        """
        logger.info(f"Calling LLM with query: {query} for session: {session_id}")
        
        # Initialize history for this session if it doesn't exist
        if session_id not in self.history:
            self.history[session_id] = []

        current_history = self.history[session_id]

        if not current_history:
            current_history = Promptschema(
                system=self.system_prompt,
                user=query,
                context=context
            ).format()
        else:
            # Update the system prompt (first message) with the new context for the current turn
            if context and len(current_history) > 0 and current_history[0].get("role") == "system":
                current_history[0]["content"] = self.system_prompt.format(context=context)
                
            current_history.append({"role": "user", "content": query})

        history_to_send = []

        if context_window and len(current_history) > context_window:
            history_to_send = [current_history[0]] + current_history[-context_window:]
        else:
            history_to_send = current_history

        kwargs = {
            "model": load.LLM_MODEL,
            "messages": history_to_send 
        }
        if temperature:
            kwargs["temperature"] = temperature

        chat = self.client.chat.completions.create(**kwargs)
        output = str(chat.choices[0].message.content)
        
        # Clean output in case the model leaks chat tags
        output = output.replace("<|im_start|>", "").replace("<|im_end|>", "")
        
        current_history.append({"role": "assistant", "content": output})
        
        # Save it back to the dictionary
        self.history[session_id] = current_history
        
        logger.success(f"LLM responded with: {output}")
        return output


class RAG_Memory:
    """
    This class is responsible for managing the RAG (Retrieval-Augmented Generation) memory using ChromaDB.
    It initializes the ChromaDB client and sets up a collection for storing conversation history and retrieved documents.
    """
    def __init__(self):
        self.client = chromadb.Client()
        # Create a collection configured for cosine similarity via HNSW
        self.collection = self.client.get_or_create_collection(
            name="pdf_pal_memory",
            metadata={"hnsw:space": "cosine"}
        )

    def index(self, chunks: List[Any], session_id: str, file_name: str = "Unknown", chunk_type: str = "content") -> None:
        """
        Indexes a list of chunks into the ChromaDB collection.
        This operation acts as saving to the in-memory RAG.
        
        Args:
            chunks (List[Any]): A list of chunk objects generated by the Semantic Chunker.
            session_id (str): The unique identifier for the user session uploading the document.
            file_name (str, optional): The name of the file these chunks originated from.
            chunk_type (str, optional): The classification of chunk (e.g., 'content' or 'summary').
        
        Returns:
            None
        """
        if not chunks:
            logger.warning("No chunks to index in ChromaDB.")
            return

        logger.info(f"Indexing {len(chunks)} chunks into ChromaDB for session {session_id} from {file_name} (Type: {chunk_type}).")
        documents = [chunk.text for chunk in chunks]
        # Generate a unique ID for each chunk to prevent overwriting
        ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
        # Safely extract token_count if it exists, otherwise estimate it, and deploy metadata payload
        metadatas = [
            {
                "token_count": getattr(chunk, "token_count", len(chunk.text) // 4), 
                "session_id": session_id, 
                "file_name": file_name, 
                "type": chunk_type
            } 
            for chunk in chunks
        ]

        # Use the add method to insert chunk documents and their metadata
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.success("Successfully indexed chunks into RAG memory.")

    def retrieve(self, query: str, session_id: str, n_results: int = 3, chunk_type: str = "content") -> List[str]:
        """
        Retrieves the top 'n_results' most relevant chunks for the given query using cosine similarity.
        
        Args:
            query: The search query.
            session_id: The unique session identifier to filter matching chunks.
            n_results: Number of top results to return.
            chunk_type: Filters results strictly to 'content' chunks or 'summary' chunks.
            
        Returns:
            A list of retrieved document strings.
        """
        logger.info(f"Retrieving top {n_results} results for query: '{query}' in session: {session_id} (Type filtering: {chunk_type})")
        
        # Use logical $and operator to filter by both session boundary and chunk type precisely!
        # This completely guarantees summaries aren't accidentally pulled into normal queries and vice versa.
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"$and": [{"session_id": session_id}, {"type": chunk_type}]}
        )
        
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        if documents:
            logger.success(f"Retrieved {len(documents)} relevant chunks.")
            formatted_chunks = []
            for doc, meta in zip(documents, metadatas):
                fname = meta.get("file_name", "Unknown File")
                formatted_chunks.append(f"[Source File: {fname}]\n{doc}")
            return formatted_chunks
        
        logger.warning("No relevant chunks retrieved.")
        return []
    
    def dump_memory_to_json(self, session_id: str) -> None:
        """
        Extracts all indexed chunks associated with a specific session and physically writes 
        them to a local JSON file. This provides absolute transparency for RAG debugging.
        """
        
        logger.info(f"Executing deep memory dump for session {session_id}...")
        try:
            results = self.collection.get(
                where={"session_id": session_id},
                include=["documents", "metadatas"]
            )
            
            docs = results.get("documents", [])
            metas = results.get("metadatas", [])
            
            if not docs:
                logger.warning(f"No memory found to dump for session {session_id}.")
                return
                
            dump_data = []
            for doc, meta in zip(docs, metas):
                dump_data.append({
                    "metadata": meta,
                    "text": doc
                })
                
            data_dir = Path.cwd() / "Data"
            data_dir.mkdir(exist_ok=True)
            dump_path = data_dir / f"rag_memory_dump_{session_id}.json"
            
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=4, ensure_ascii=False)
                
            logger.success(f"Successfully exported {len(dump_data)} chunks to {dump_path}")
        except Exception as e:
            logger.error(f"Failed to dump memory to JSON: {e}")
    
class Read_PDF_Content:
    """
    This class is responsible for reading the content of a PDF file.
    """
    def __init__(self):
       self.content = ""

    def extract_text_from_pdfs(self, pdf_docs: List[Any]) -> str:
        """
        Extracts text from a list of PDF documents using pypdf.
        
        Args:
            pdf_docs (List[Any]): A list of uploaded PDF file byte-streams or paths (e.g., from Streamlit).
            
        Returns:
            str: A single concatenated string containing all text extracted from the provided PDFs.
        """
        logger.info(f"Extracting text from {len(pdf_docs)} PDF documents.")
        # Reset internal content on a new run to prevent duplicate buildup if called multiple times
        self.content = ""
        
        for pdf in pdf_docs:
            try:
                reader = PdfReader(pdf)
                for page in reader.pages:
                    if page.extract_text():
                        # Add a newline at the end so words don't get mashed up across pages
                        self.content += page.extract_text() + "\n"
            except Exception as e:
                logger.error(f"Error extracting text from a PDF: {e}")

        logger.success("Text extraction from PDFs completed.")
        logger.trace(f"Extracted content: {self.content[:500]}...")  # Log the first 500 characters of the extracted content
        return self.content
    
    def chunking(self, text: str) -> List[Any]:
        """
        Splits the extracted text into smaller, overlapping chunks using the recursive chunker.
        
        Args:
            text (str): The large string of text extracted from the PDF(s) to be chunked.
            
        Returns:
            List[Any]: A list of chunk objects, each containing semantic text fragments and token counts.
        """
        logger.info("Chunking extracted text into smaller pieces.")
        logger.trace(f"Original text length: {len(text)} characters.")
        chunker = RecursiveChunker() # Set a small enough chunk_size to see the split in our test
        chunks = chunker.chunk(text)
        for chunk in chunks:
            logger.trace(f"Chunk text: {chunk.text}")
            logger.trace(f"Token count: {chunk.token_count}")
        logger.success(f"Chunking completed. Total chunks created: {len(chunks)}.")
        return chunks

class PDF_Pal_App:
    """
    Wrapper class to tie together the document extractor, RAG memory, and LLM chat.
    This provides a single interface for your frontend (like Streamlit) to interact with.
    """
    def __init__(self):
        self.brain = PDF_Pal_Brain()
        self.rag = RAG_Memory()
        self.extractor = Read_PDF_Content()

    def process_pdfs(self, pdf_docs: List[Any], session_id: str) -> bool:
        """
        Extracts text from PDFs, chunks it, and indexes it into the RAG memory store.
        Processes each document separately to precisely attach file name tags via metadata.
        
        Args:
            pdf_docs (List[Any]): A list of uploaded PDF files to process.
            session_id (str): The unique identifier for the user session.
            
        Returns:
            bool: True if processing and indexing were successful, False otherwise.
        """
        success = False
        for pdf in pdf_docs:
            extracted_text = self.extractor.extract_text_from_pdfs([pdf])
            if extracted_text:
                chunks = self.extractor.chunking(extracted_text)
                file_name = getattr(pdf, "name", "Unknown Document")
                self.rag.index(chunks, session_id, file_name=file_name, chunk_type="content")
                
                # Fire the async Map-Reduce summarize loop autonomously so it doesn't block UI interactions
                import threading
                threading.Thread(
                    target=self.generate_document_summary, 
                    args=(chunks, session_id, file_name),
                    daemon=True
                ).start()
                
                success = True
                
        # Trigger the transparent memory dump if debugging toggle is active
        if success and load.MEMORY_DUMP:
            self.rag.dump_memory_to_json(session_id)
            
        return success

    def generate_document_summary(self, chunks: List[Any], session_id: str, file_name: str) -> None:
        """
        Background Map-Reduce thread that synthesizes a single global summary chunk 
        from all individual document fragments to power overarching user questions.
        """
        logger.info(f"Starting background map-reduce summarization for {file_name}")
        
        try:
            # Map Phase: To bypass heavy API rate limits, cap sampling payload natively
            sample_chunks = chunks[:15] if len(chunks) > 15 else chunks
            
            # Load external Map Prompt
            map_prompt_template = Path(Path(__file__).resolve().parent / "prompts" / "map_summary_prompt.md").read_text()
            
            mini_summaries = []
            for chunk in sample_chunks:
                prompt = map_prompt_template.format(text=chunk.text)
                try:
                    response = self.brain.client.chat.completions.create(
                        model=load.LLM_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3
                    )
                    mini_summaries.append(response.choices[0].message.content)
                except Exception as e:
                    logger.warning(f"Failed to cleanly summarize sub-chunk: {e}")
                    
            if not mini_summaries:
                logger.warning(f"No valid mapped summaries generated for {file_name}, aborting thread reduction phase.")
                return
                
            # Reduce Phase: Merge arrays uniformly into a highly compressed final block
            combined_text = " ".join(mini_summaries)
            
            # Load external Reduce Prompt
            reduce_prompt_template = Path(Path(__file__).resolve().parent / "prompts" / "reduce_summary_prompt.md").read_text()
            reduce_prompt = reduce_prompt_template.format(combined_text=combined_text)
            
            final_res = self.brain.client.chat.completions.create(
                model=load.LLM_MODEL,
                messages=[{"role": "user", "content": reduce_prompt}],
                temperature=0.3
            )
            
            global_summary_text = f"[GLOBAL DOCUMENT SUMMARY TARGET]\n{final_res.choices[0].message.content}"
            
            # Construct synthetic chunk vector mapping to bypass Semantic Chunker explicitly
            class SummaryChunk:
                def __init__(self, text):
                    self.text = text
                    self.token_count = len(text) // 4
            
            summary_chunk = SummaryChunk(global_summary_text)
            
            # Permanently stamp back into ChromaDB under isolated Type partition
            self.rag.index([summary_chunk], session_id, file_name=file_name, chunk_type="summary")
            logger.success(f"Background global summary completed and indexed for {file_name}. Summary cache ready.")
            
            # Re-trigger memory dump so it updates the JSON with the newly injected summary chunk!
            if load.MEMORY_DUMP:
                self.rag.dump_memory_to_json(session_id)
            
        except Exception as e:
            logger.error(f"Critical error in background summarizer thread payload: {e}")

    def ask(self, query: str, session_id: str = "default", temperature: float = None, context_window: int = None, file_names: List[str] = None) -> str:
        """
        Retrieves relevant context from RAG, formats it, and orchestrates the chat with the LLM.
        
        Args:
            query (str): The specific question or prompt the user is asking.
            session_id (str, optional): The unique identifier for the user session. Defaults to "default".
            temperature (float, optional): Adjusts the creativity/randomness of the LLM responses.
            context_window (int, optional): The max number of historical messages to inject as context.
            file_names (List[str], optional): The list of filenames uploaded to this specific chat session.
            
        Returns:
            str: The final textual response generated by the LLM.
        """
        # Intelligent Intent Routing
        query_lower = query.lower()
        is_summary = any(kw in query_lower for kw in ["summarize", "summary", "overview", "tldr", "main points"])
        
        target_type = "summary" if is_summary else "content"
        n_res = len(file_names) if (is_summary and file_names) else 3
        if n_res == 0: n_res = 3
        
        # Route memory fetch through strictly partitioned metadata channel
        retrieved_chunks = self.rag.retrieve(query, session_id=session_id, n_results=n_res, chunk_type=target_type)
        
        # Protective failover bound: if the async map-reduce thread is still executing, fall back to pure cosine semantic search
        if is_summary and not retrieved_chunks:
            logger.warning("Targeted summary chunk missing (map-reduce thread incomplete). Failing over to standard unstructured semantic search.")
            retrieved_chunks = self.rag.retrieve(query, session_id=session_id, n_results=3, chunk_type="content")
            
        context_text = "\n\n".join(retrieved_chunks) if retrieved_chunks else "No relevant context found."
        
        # Inject metadata about uploaded files into the context window wrapper
        if file_names:
            files_str = ", ".join(f"'{f}'" for f in file_names)
            context = f"[Attached Files Document Metadata: {files_str}]\n\n{context_text}"
        else:
            context = context_text
            
        # Send everything to the LLM utilizing session_id
        return self.brain.chat(
            query=query, 
            context=context, 
            session_id=session_id,
            temperature=temperature,
            context_window=context_window
        )
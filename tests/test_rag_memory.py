import pytest
from src.PDF_Pal import RAG_Memory

class FakeChunk:
    def __init__(self, text):
        self.text = text
        self.token_count = len(text) // 4

def test_index_attaches_metadata(mocker):
    """Verify that RAG_Memory.index correctly injects session_id & file_name payload attributes."""
    # Mock ChromaDB client collection
    mock_coll = mocker.MagicMock()
    mocker.patch("src.PDF_Pal.chromadb.Client")
    
    rag = RAG_Memory()
    rag.collection = mock_coll  # Hijack with mock 
    
    chunks = [FakeChunk("Hello chunk"), FakeChunk("World chunk")]
    rag.index(chunks, session_id="test_session_123", file_name="sample.pdf")
    
    # Assert collection.add() was called with populated metadata matrices
    called_args = mock_coll.add.call_args[1]
    
    assert len(called_args["documents"]) == 2
    assert called_args["metadatas"][0]["session_id"] == "test_session_123"
    assert called_args["metadatas"][0]["file_name"] == "sample.pdf"
    assert called_args["metadatas"][0]["type"] == "content"

def test_retrieve_applies_session_and_type_filter(mocker):
    """Verify that RAG_Memory.retrieve restricts vector searches strictly within $and logical bounds."""
    mock_coll = mocker.MagicMock()
    # Stub dummy chroma dict output
    mock_coll.query.return_value = {
        "documents": [["[Source: sample.pdf]\nFake Content"]],
        "metadatas": [[{"file_name": "sample.pdf"}]]
    }
    
    mocker.patch("src.PDF_Pal.chromadb.Client")
    rag = RAG_Memory()
    rag.collection = mock_coll
    
    rag.retrieve("Who am I?", session_id="session_xyz", chunk_type="summary")
    
    # Assert metadata logical filter integrity
    called_args = mock_coll.query.call_args[1]
    where_clause = called_args["where"]
    
    assert "$and" in where_clause
    assert where_clause["$and"][0] == {"session_id": "session_xyz"}
    assert where_clause["$and"][1] == {"type": "summary"}

def test_dump_memory_creates_data_directory(mocker, tmp_path):
    """Verify that deep memory dumps safely generate local insulated /Data folders."""
    mock_coll = mocker.MagicMock()
    mock_coll.get.return_value = {"documents": ["docs"], "metadatas": [{"session_id": "xyz"}]}
    
    mocker.patch("src.PDF_Pal.chromadb.Client")
    rag = RAG_Memory()
    rag.collection = mock_coll
    
    # Mock Path.cwd() to return a temporary pytest directory to avoid cluttering local workspaces
    mocker.patch("src.PDF_Pal.Path.cwd", return_value=tmp_path)
    
    rag.dump_memory_to_json("test_session")
    
    # Verify directory traversal spawned
    data_dir = tmp_path / "Data"
    assert data_dir.exists()
    assert (data_dir / "rag_memory_dump_test_session.json").exists()

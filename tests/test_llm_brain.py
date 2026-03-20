import pytest
from src.PDF_Pal import PDF_Pal_Brain, PDF_Pal_App

def test_brain_chat_appends_history(mocker):
    """Verify that Groq interface correctly pushes dictionary payloads into session buffers."""
    brain = PDF_Pal_Brain()
    
    # Mock out Groq client .completions endpoint
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = "Response from AL"
    brain.client.chat.completions.create = mocker.MagicMock(return_value=mock_response)
    
    brain.chat(query="Hello AI", session_id="sess_1")
    
    # Confirm history tracking accurately populated
    assert "sess_1" in brain.history
    assert len(brain.history["sess_1"]) >= 2
    assert brain.history["sess_1"][-2]["content"] == "Hello AI"
    assert brain.history["sess_1"][-1]["content"] == "Response from AL"

def test_app_generate_summary_trigger(mocker):
    """Verify global background summarizer reducers fire indexing buffers correctly."""
    app = PDF_Pal_App()
    
    # Mock RAG isolation indexing payloads
    app.rag.index = mocker.MagicMock()
    
    # Mock Groq syntheses 
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = "Synthetic Summary"
    app.brain.client.chat.completions.create = mocker.MagicMock(return_value=mock_response)
    
    # Create fake chunk payload arrays
    class FakeChunk:
        def __init__(self, text): self.text = text
    chunks = [FakeChunk("Line 1")]
    
    # Force single-threaded execution trigger for absolute determinism inside pytest
    app.generate_document_summary(chunks, session_id="session_1", file_name="demo.pdf")
    
    # Assert successful summarizer buffer committed strictly into 'summary' channel
    app.rag.index.assert_called_once()
    called_args = app.rag.index.call_args[1]
    assert called_args["chunk_type"] == "summary"

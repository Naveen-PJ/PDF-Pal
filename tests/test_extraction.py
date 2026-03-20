import pytest
from src.PDF_Pal import Read_PDF_Content

def test_extract_text_from_pdfs_concatenation(mocker):
    """Verify text concatenation loops through multiple document payload byte streams safely."""
    extractor = Read_PDF_Content()
    
    # Mock the PdfReader class to return isolated synthetic mock page arrays
    mock_page = mocker.MagicMock()
    mock_page.extract_text.return_value = "Hello World"
    
    mock_reader = mocker.MagicMock()
    mock_reader.pages = [mock_page, mock_page]
    
    mocker.patch("src.PDF_Pal.PdfReader", return_value=mock_reader)
    
    # Run extractor against 2 isolated mock file streams
    result = extractor.extract_text_from_pdfs(["file1.pdf", "file2.pdf"])
    
    # Total pages: 2 docs * 2 pages = 4 pages. "Hello World\n" * 4 
    assert result.count("Hello World") == 4

def test_chunking_token_counts():
    """Verify recursive chunker produces list of objects containing text metadata explicitly."""
    extractor = Read_PDF_Content()
    fake_text = "This is a sentence. This is another sentence. It is designed to test chunking thresholds accurately."
    
    chunks = extractor.chunking(fake_text)
    
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert hasattr(chunks[0], "text")
    assert hasattr(chunks[0], "token_count")

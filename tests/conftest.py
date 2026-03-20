import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def mock_settings_env(mocker):
    """
    Automatically mock Pydantic settings loading so that tests don't 
    accidentally crash trying to find a valid .streamlit/secrets.toml file.
    """
    # Create static mock objects representing the core configuration schema
    mocker.patch("src.config.Config_env.GROQ_API_KEY", new_callable=mocker.PropertyMock, return_value="fake_testing_key")
    mocker.patch("src.config.load.LLM_MODEL", "llama-3.1-8b-instant")
    mocker.patch("src.config.load.MEMORY_DUMP", False)

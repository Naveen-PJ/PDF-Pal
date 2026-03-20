from pathlib import Path
from src.config import load, LoadModelConfig
from pydantic_settings import SettingsConfigDict

def test_load_model_config_defaults():
    """Verify that Pydantic properly loads standard defaults if file parsing defaults triggered."""
    config = LoadModelConfig()
    # Check fallback assignment triggers
    assert config.LLM_MODEL == "llama-3.1-8b-instant"
    assert config.MEMORY_DUMP is False

def test_config_md_resolution():
    """Verify that settings correctly point to the root directory's config.md file location."""
    env_file = str(LoadModelConfig.model_config.get("env_file"))
    # Verify it resolves to the appended root folder file definition 
    assert env_file.endswith("config.md")

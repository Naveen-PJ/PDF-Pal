from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, TomlConfigSettingsSource
from pathlib import Path

# Get the absolute path to the project root
ROOT_DIR = Path(__file__).resolve().parent.parent
SECRETS_PATH = ROOT_DIR / ".streamlit" / "secrets.toml"

class GroqConfig(BaseModel):
    API_KEY: str

class Config_env(BaseSettings):
    groq: GroqConfig

    @property
    def GROQ_API_KEY(self) -> str:
        return self.groq.API_KEY

    # Point to the correct Streamlit secrets file using absolute path
    model_config = SettingsConfigDict(toml_file=str(SECRETS_PATH))

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            TomlConfigSettingsSource(settings_cls),
        )

# Instantiate the config so it can be imported elsewhere
config = Config_env()


class LoadModelConfig(BaseSettings):
    LLM_MODEL: str = Field(default="llama-3.1-8b-instant")
    MEMORY_DUMP: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / "config.md")
    )

load = LoadModelConfig()
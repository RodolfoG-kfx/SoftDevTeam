from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    max_iterations: int = Field(default=5, alias="MAX_ITERATIONS")
    exec_timeout_seconds: int = Field(default=15, alias="EXEC_TIMEOUT_SECONDS")
    pytest_timeout_seconds: int = Field(default=20, alias="PYTEST_TIMEOUT_SECONDS")
    workspace_path: Path = Field(default=Path("workspace"), alias="WORKSPACE_PATH")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )


def get_settings() -> Settings:
    return Settings()

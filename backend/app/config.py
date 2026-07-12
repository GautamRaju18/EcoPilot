"""Central configuration. Reads from environment / .env (all AI keys optional)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Auth
    SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12h — comfy for a demo day

    # Database
    DATABASE_URL: str = "sqlite:///./ecopilot.db"

    # ESG scoring weights (configurable per org — Business Rule 1)
    WEIGHT_ENVIRONMENTAL: float = 0.40
    WEIGHT_SOCIAL: float = 0.30
    WEIGHT_GOVERNANCE: float = 0.30

    # Feature toggles (Business Rules 2 & 3)
    AUTO_EMISSION_CALC: bool = True
    EVIDENCE_REQUIRED: bool = True

    # --- LLM providers (priority: gemini -> openrouter -> ollama -> template) ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # Embeddings backend: "gemini" or "tfidf" (local fallback)
    EMBEDDINGS_BACKEND: str = "tfidf"


settings = Settings()

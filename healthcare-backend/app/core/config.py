"""Backend-only configuration, independent of the current working directory."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_TITLE = (
    "Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn"
)
DEVELOPMENT_JWT_SECRET = "development-only-change-before-production-2026"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    frontend_origin: str = "http://localhost:5173"
    jwt_secret: SecretStr = SecretStr(DEVELOPMENT_JWT_SECRET)
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    dev_auth_enabled: bool = True
    cookie_secure: bool = False
    access_cookie_name: str = "healthcare_access"
    refresh_cookie_name: str = "healthcare_refresh"
    csrf_cookie_name: str = "healthcare_csrf"
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = None
    gemini_timeout_seconds: float = 20.0
    tool_timeout_seconds: float = 10.0
    tool_confirmation_minutes: int = 5
    embedding_model: str = "BAAI/bge-m3"
    embedding_batch_size: int = 8
    rag_top_k: int = 5
    rag_max_cosine_distance: float = 0.65
    rag_strategy: Literal["exact_dense", "hnsw_dense", "hybrid_rrf", "hybrid_rerank"] = "hnsw_dense"
    rag_dense_candidates: int = 20
    rag_sparse_candidates: int = 20
    rag_rrf_k: int = 60
    rag_hnsw_ef_search: int = 40
    rag_bm25_k1: float = 1.5
    rag_bm25_b: float = 0.75
    rag_reranker_model: str = "BAAI/bge-reranker-v2-m3"
    rag_reranker_device: Literal["cpu", "cuda"] = "cpu"
    rag_reranker_batch_size: int = 4
    rag_rerank_candidates: int = 20
    rag_chunk_max_chars: int = 1200
    rag_chunk_overlap_chars: int = 150
    rag_max_file_bytes: int = 2_000_000_000
    stt_model: str = "small"
    stt_device: Literal["cpu", "cuda", "auto"] = "cpu"
    stt_compute_type: str = "int8"
    stt_timeout_seconds: float = 90.0
    stt_max_file_bytes: int = 10_000_000
    rate_limit_enabled: bool = True
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 300
    register_rate_limit: int = 5
    refresh_rate_limit: int = 30
    chat_rate_limit: int = 30
    voice_rate_limit: int = 10
    ingestion_rate_limit: int = 5
    common_rate_window_seconds: int = 60

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
        except ArgumentError:
            raise ValueError("DATABASE_URL must be a PostgreSQL psycopg URL") from None
        if url.drivername != "postgresql+psycopg" or not url.database:
            raise ValueError("DATABASE_URL must use postgresql+psycopg and name a database")
        return value

    @field_validator("frontend_origin")
    @classmethod
    def validate_frontend_origin(cls, value: str) -> str:
        try:
            parts = urlsplit(value)
            port = parts.port
        except ValueError:
            raise ValueError("FRONTEND_ORIGIN must be one exact HTTP(S) origin") from None
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or "*" in value
            or parts.username is not None
            or parts.password is not None
            or parts.path not in {"", "/"}
            or parts.query
            or parts.fragment
            or port == 0
        ):
            raise ValueError("FRONTEND_ORIGIN must be one exact HTTP(S) origin")
        return value.rstrip("/")

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        return value

    @field_validator("access_token_minutes")
    @classmethod
    def validate_access_token_minutes(cls, value: int) -> int:
        if not 1 <= value <= 60:
            raise ValueError("ACCESS_TOKEN_MINUTES must be between 1 and 60")
        return value

    @field_validator("refresh_token_days")
    @classmethod
    def validate_refresh_token_days(cls, value: int) -> int:
        if not 1 <= value <= 30:
            raise ValueError("REFRESH_TOKEN_DAYS must be between 1 and 30")
        return value

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def normalize_optional_gemini_key(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("gemini_model", mode="before")
    @classmethod
    def normalize_optional_gemini_model(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("GEMINI_MODEL must be a model identifier")
        model = value.strip()
        if not model:
            return None
        if len(model) > 120 or any(character.isspace() for character in model):
            raise ValueError("GEMINI_MODEL must be a valid model identifier")
        return model

    @field_validator("gemini_timeout_seconds")
    @classmethod
    def validate_gemini_timeout(cls, value: float) -> float:
        if not 1 <= value <= 120:
            raise ValueError("GEMINI_TIMEOUT_SECONDS must be between 1 and 120")
        return value

    @field_validator("tool_timeout_seconds")
    @classmethod
    def validate_tool_timeout(cls, value: float) -> float:
        if not 1 <= value <= 30:
            raise ValueError("TOOL_TIMEOUT_SECONDS must be between 1 and 30")
        return value

    @field_validator("tool_confirmation_minutes")
    @classmethod
    def validate_tool_confirmation_minutes(cls, value: int) -> int:
        if not 1 <= value <= 15:
            raise ValueError("TOOL_CONFIRMATION_MINUTES must be between 1 and 15")
        return value

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 160 or any(character.isspace() for character in value):
            raise ValueError("EMBEDDING_MODEL must be a valid model identifier")
        return value

    @field_validator("embedding_batch_size")
    @classmethod
    def validate_embedding_batch_size(cls, value: int) -> int:
        if not 1 <= value <= 128:
            raise ValueError("EMBEDDING_BATCH_SIZE must be between 1 and 128")
        return value

    @field_validator("rag_top_k")
    @classmethod
    def validate_rag_top_k(cls, value: int) -> int:
        if not 1 <= value <= 20:
            raise ValueError("RAG_TOP_K must be between 1 and 20")
        return value

    @field_validator("rag_max_cosine_distance")
    @classmethod
    def validate_rag_max_cosine_distance(cls, value: float) -> float:
        if not 0 <= value <= 2:
            raise ValueError("RAG_MAX_COSINE_DISTANCE must be between 0 and 2")
        return value

    @field_validator(
        "rag_dense_candidates",
        "rag_sparse_candidates",
        "rag_rrf_k",
        "rag_hnsw_ef_search",
        "rag_reranker_batch_size",
        "rag_rerank_candidates",
    )
    @classmethod
    def validate_positive_rag_tuning_integer(cls, value: int) -> int:
        if not 1 <= value <= 1000:
            raise ValueError("RAG tuning integer must be between 1 and 1000")
        return value

    @field_validator("rag_bm25_k1")
    @classmethod
    def validate_bm25_k1(cls, value: float) -> float:
        if not 0 < value <= 3:
            raise ValueError("RAG_BM25_K1 must be greater than 0 and at most 3")
        return value

    @field_validator("rag_bm25_b")
    @classmethod
    def validate_bm25_b(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("RAG_BM25_B must be between 0 and 1")
        return value

    @field_validator("rag_reranker_model")
    @classmethod
    def validate_reranker_model(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 160 or any(character.isspace() for character in value):
            raise ValueError("RAG_RERANKER_MODEL must be a valid model identifier")
        return value

    @field_validator("rag_chunk_max_chars")
    @classmethod
    def validate_rag_chunk_max_chars(cls, value: int) -> int:
        if not 200 <= value <= 8000:
            raise ValueError("RAG_CHUNK_MAX_CHARS must be between 200 and 8000")
        return value

    @field_validator("rag_chunk_overlap_chars")
    @classmethod
    def validate_rag_chunk_overlap_chars(cls, value: int) -> int:
        if not 0 <= value <= 1000:
            raise ValueError("RAG_CHUNK_OVERLAP_CHARS must be between 0 and 1000")
        return value

    @field_validator("rag_max_file_bytes")
    @classmethod
    def validate_rag_max_file_bytes(cls, value: int) -> int:
        if not 1_000_000 <= value <= 5_000_000_000:
            raise ValueError("RAG_MAX_FILE_BYTES must be between 1 MB and 5 GB")
        return value

    @field_validator("stt_model")
    @classmethod
    def validate_stt_model(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 120 or any(character.isspace() for character in value):
            raise ValueError("STT_MODEL must be a valid faster-whisper model identifier")
        return value

    @field_validator("stt_compute_type")
    @classmethod
    def validate_stt_compute_type(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 40 or any(character.isspace() for character in value):
            raise ValueError("STT_COMPUTE_TYPE must be a valid CTranslate2 compute type")
        return value

    @field_validator("stt_timeout_seconds")
    @classmethod
    def validate_stt_timeout(cls, value: float) -> float:
        if not 5 <= value <= 300:
            raise ValueError("STT_TIMEOUT_SECONDS must be between 5 and 300")
        return value

    @field_validator("stt_max_file_bytes")
    @classmethod
    def validate_stt_max_file_bytes(cls, value: int) -> int:
        if not 100_000 <= value <= 50_000_000:
            raise ValueError("STT_MAX_FILE_BYTES must be between 100 KB and 50 MB")
        return value

    @field_validator(
        "login_rate_limit",
        "register_rate_limit",
        "refresh_rate_limit",
        "chat_rate_limit",
        "voice_rate_limit",
        "ingestion_rate_limit",
    )
    @classmethod
    def validate_rate_limit(cls, value: int) -> int:
        if not 1 <= value <= 10_000:
            raise ValueError("Rate limits must be between 1 and 10000")
        return value

    @field_validator("login_rate_window_seconds", "common_rate_window_seconds")
    @classmethod
    def validate_rate_window(cls, value: int) -> int:
        if not 1 <= value <= 86_400:
            raise ValueError("Rate-limit windows must be between 1 and 86400 seconds")
        return value

    @model_validator(mode="after")
    def validate_rag_chunking(self) -> "Settings":
        if self.rag_chunk_overlap_chars >= self.rag_chunk_max_chars:
            raise ValueError("RAG_CHUNK_OVERLAP_CHARS must be smaller than RAG_CHUNK_MAX_CHARS")
        return self

    @model_validator(mode="after")
    def validate_rag_candidate_sizes(self) -> "Settings":
        if self.rag_dense_candidates < self.rag_top_k:
            raise ValueError("RAG_DENSE_CANDIDATES must be at least RAG_TOP_K")
        if self.rag_sparse_candidates < self.rag_top_k:
            raise ValueError("RAG_SPARSE_CANDIDATES must be at least RAG_TOP_K")
        if self.rag_rerank_candidates < self.rag_top_k:
            raise ValueError("RAG_RERANK_CANDIDATES must be at least RAG_TOP_K")
        return self

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env == "production":
            if self.jwt_secret.get_secret_value() == DEVELOPMENT_JWT_SECRET:
                raise ValueError("JWT_SECRET must be changed in production")
            if self.dev_auth_enabled:
                raise ValueError("DEV_AUTH_ENABLED must be false in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            if not self.frontend_origin.startswith("https://"):
                raise ValueError("FRONTEND_ORIGIN must use HTTPS in production")
            if not self.rate_limit_enabled:
                raise ValueError("RATE_LIMIT_ENABLED must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

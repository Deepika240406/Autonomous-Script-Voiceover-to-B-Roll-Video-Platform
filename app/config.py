from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional
import os


class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "IncuBrix B-Roll Video Engine"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Server Bindings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security & Idempotency
    IDEMPOTENCY_TTL_SECONDS: int = 86400  # 24 hours
    HMAC_SECRET: str = "incubrix-super-secret-hmac-key"
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024  # 100MB
    MAX_AUDIO_DURATION_SECONDS: float = 600.0  # 10 minutes
    REQUEST_TIMEOUT_SECONDS: int = 30

    # Workers & Storage
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    LOCAL_STORAGE_PATH: str = "./storage_root"
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ACCESS_KEY: Optional[str] = "minioadmin"
    S3_SECRET_KEY: Optional[str] = "minioadmin"
    S3_BUCKET_NAME: str = "incubrix-videos"
    S3_REGION: str = "us-east-1"

    # Redis / Celery (Fallback to internal Asyncio Worker if redis unavailable)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    USE_INTERNAL_WORKER: bool = True
    MAX_CONCURRENT_JOBS: int = 4

    # AI Models & Providers
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_DEVICE: str = "cpu"
    DEFAULT_TTS_PROVIDER: str = "edge_tts"  # "edge_tts", "pyttsx3", "mock"
    DEFAULT_VOICE: str = "en-IN-female"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDINGS_DEVICE: str = "cpu"
    USE_LIGHTWEIGHT_EMBEDDINGS: bool = False  # Set to True on memory-constrained (512MB RAM) servers

    # External Stock Footage Providers (Optional keys; fallback to mock/local if absent)
    PEXELS_API_KEY: Optional[str] = None
    PIXABAY_API_KEY: Optional[str] = None
    ENABLE_MOCK_FALLBACK: bool = True

    # FFmpeg Configuration
    FFMPEG_BINARY: str = "ffmpeg"
    FFPROBE_BINARY: str = "ffprobe"
    DEFAULT_FPS: int = 30
    DEFAULT_VIDEO_BITRATE: str = "4000k"
    DEFAULT_AUDIO_BITRATE: str = "192k"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

"""
Application configuration settings.

Manages environment variables and application settings using Pydantic.
"""

from pydantic_settings import BaseSettings
from typing import Union, List
from pydantic import field_validator

class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    APP_NAME: str = "N8N Tools API"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # File handling settings
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    TEMP_DIR: str = "/tmp/n8n-tools"
    
    # CORS settings
    CORS_ORIGINS: Union[str, List[str]] = ["*"]  # Override in production
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = True
    LOG_CORRELATION_ID: bool = True
    
    # AI/ML API Keys
    AI_PDF_MISTRAL_API_KEY: str = ""
    
    # MinIO/S3 Configuration
    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET_NAME: str = ""
    MINIO_REGION: str = ""
    
    # Qdrant Configuration
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    
    @field_validator('CORS_ORIGINS')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            # Split comma-separated values
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Configuration
    app_name: str = "RAG Document Assistant"
    debug: bool = False
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"
    
    # Database Configuration - PostgreSQL
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/rag_db"
    
    # File Upload Configuration
    upload_folder: str = "uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: set = {"txt", "pdf", "docx", "json"}
    
    # Weaviate Configuration
    weaviate_url: str = "http://localhost:8080"
    
    # OpenAI Configuration (optional)
    openai_api_key: Optional[str] = None
    
    # RAG Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_retrieval_results: int = 5
    
    # CORS Configuration
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create settings instance
settings = Settings()
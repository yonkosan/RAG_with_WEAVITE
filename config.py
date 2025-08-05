import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///rag_app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Upload Configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'json'}
    
    # Weaviate Configuration
    WEAVIATE_URL = os.environ.get('WEAVIATE_URL') or 'http://localhost:8080'
    
    # OpenAI Configuration (optional, for better embeddings)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # RAG Configuration
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    MAX_RETRIEVAL_RESULTS = 5
# RAG Application

A comprehensive Retrieval-Augmented Generation (RAG) application with user authentication, file processing, and intelligent document search capabilities.

## Features

### 🔐 Authentication & Authorization
- User registration and login with JWT tokens
- Secure password hashing with bcrypt
- Role-based access control
- Session management

### 📁 File Processing
- **Multiple file format support**: PDF, DOCX, TXT, CSV, XLSX, Images (JPG, PNG, TIFF, BMP), JSON
- **Advanced text extraction**: 
  - PDF text and table extraction
  - DOCX text and table extraction
  - OCR for images using Tesseract
  - Excel/CSV data processing
- **Automatic chunking**: Text is split into overlapping chunks for better retrieval
- **Background processing**: Files are processed asynchronously after upload

### 🤖 AI-Powered Search
- **Vector embeddings**: Uses sentence-transformers or OpenAI embeddings
- **Similarity search**: PostgreSQL with pgvector for efficient vector operations
- **LLM integration**: OpenAI GPT or Hugging Face models for response generation
- **Query history**: Track and review past searches

### 💾 Database
- **PostgreSQL** with pgvector extension for vector operations
- **Async SQLAlchemy** for database operations
- **Redis** for caching (optional)

### 🎨 Modern UI
- **Responsive design** with Bootstrap 5
- **Drag-and-drop file upload**
- **Real-time processing indicators**
- **Interactive search interface**

## Architecture

```
├── main.py                 # FastAPI application entry point
├── database/              # Database models and configuration
│   ├── models.py          # SQLAlchemy models
│   └── connection.py      # Database connection and configuration
├── auth/                  # Authentication system
│   ├── models.py          # Pydantic models for auth
│   ├── security.py        # Password hashing and JWT handling
│   ├── dependencies.py    # Auth dependencies for FastAPI
│   └── router.py          # Auth API endpoints
├── files/                 # File processing system
│   ├── models.py          # Pydantic models for files
│   ├── processors.py      # File processing utilities
│   └── router.py          # File API endpoints
├── rag/                   # RAG system
│   ├── models.py          # Pydantic models for RAG
│   ├── embeddings.py      # Embedding services
│   ├── retrieval.py       # Vector search and retrieval
│   ├── llm.py             # Language model integration
│   └── router.py          # RAG API endpoints
└── templates/             # HTML templates
    ├── base.html          # Base template
    ├── index.html         # Home page
    ├── login.html         # Login page
    ├── register.html      # Registration page
    ├── dashboard.html     # User dashboard
    ├── upload.html        # File upload page
    └── search.html        # Document search page
```

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Redis (optional)
- Tesseract OCR

### 1. Clone the Repository
```bash
git clone <repository-url>
cd rag-application
```

### 2. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib redis-server tesseract-ocr poppler-utils libmagic1
```

**macOS:**
```bash
brew install postgresql redis tesseract poppler libmagic
```

### 3. Set up PostgreSQL with pgvector

```bash
# Install pgvector extension
sudo apt-get install postgresql-server-dev-all
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

Create database and user:
```sql
CREATE DATABASE ragapp;
CREATE USER raguser WITH PASSWORD 'ragpassword';
GRANT ALL PRIVILEGES ON DATABASE ragapp TO raguser;

-- Connect to ragapp database and enable pgvector
\c ragapp
CREATE EXTENSION vector;
```

### 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 5. Environment Configuration
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key (minimum 32 characters)
- `OPENAI_API_KEY`: OpenAI API key (optional, for better responses)

### 6. Run with Docker (Alternative)
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run the application
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or run everything with Docker:
```bash
docker-compose up --build
```

## Usage

### 1. Start the Application
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Access the Web Interface
Open http://localhost:8000 in your browser

### 3. Register and Login
- Create a new account or login with existing credentials
- JWT tokens are stored in localStorage for authentication

### 4. Upload Documents
- Navigate to "Upload Files"
- Drag and drop files or click to browse
- Supported formats: PDF, DOCX, TXT, CSV, XLSX, Images, JSON
- Files are processed in the background

### 5. Search Documents
- Navigate to "Search Documents"
- Ask questions about your uploaded documents
- Adjust similarity threshold and max results as needed
- View relevant document sections and AI-generated responses

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `GET /auth/me` - Get current user info

### File Management
- `POST /files/upload` - Upload file
- `GET /files/documents` - List user documents
- `GET /files/documents/{id}` - Get document details
- `GET /files/documents/{id}/status` - Get processing status
- `DELETE /files/documents/{id}` - Delete document

### RAG Operations
- `POST /rag/query` - Search documents and generate response
- `GET /rag/history` - Get query history
- `GET /rag/statistics` - Get user statistics
- `DELETE /rag/history/{id}` - Delete query from history

## Configuration

### Embedding Models
The application supports multiple embedding options:

1. **Sentence Transformers (Default)**
   - Model: `all-MiniLM-L6-v2`
   - Runs locally, no API key required
   - 384-dimensional embeddings

2. **OpenAI Embeddings**
   - Model: `text-embedding-ada-002`
   - Requires OpenAI API key
   - 1536-dimensional embeddings

### LLM Services
1. **OpenAI GPT (Recommended)**
   - Model: `gpt-3.5-turbo`
   - Requires OpenAI API key
   - High-quality responses

2. **Hugging Face Transformers**
   - Local models (e.g., `microsoft/DialoGPT-medium`)
   - No API key required
   - Limited by local compute

3. **Fallback Mode**
   - Simple extractive responses
   - Works without LLM integration

### File Processing Settings
- **Max file size**: 16MB (configurable)
- **Chunk size**: 1000 characters with 200 character overlap
- **OCR**: Tesseract for image text extraction
- **Table extraction**: pdfplumber for PDFs, python-docx for DOCX

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black .
isort .
```

### Database Migrations
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Production Deployment

### Environment Variables
- Set `DEBUG=False`
- Use strong `SECRET_KEY`
- Configure proper database URLs
- Set up SSL/TLS

### Performance Optimization
- Use connection pooling
- Enable Redis caching
- Configure proper indexes
- Use CDN for static files

### Security Considerations
- Enable HTTPS
- Configure CORS properly
- Use environment variables for secrets
- Regular security updates

## Troubleshooting

### Common Issues

1. **pgvector not found**
   - Ensure pgvector extension is installed and enabled
   - Check PostgreSQL version compatibility

2. **Tesseract OCR errors**
   - Install tesseract-ocr package
   - Verify tesseract is in PATH

3. **Memory issues with large files**
   - Reduce max file size
   - Increase system memory
   - Use streaming for large files

4. **Slow embedding generation**
   - Use GPU acceleration if available
   - Consider OpenAI embeddings for speed
   - Reduce embedding batch size

### Logs and Monitoring
- Application logs: Check FastAPI logs
- Database logs: Monitor PostgreSQL performance
- Processing errors: Check background task logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the web framework
- pgvector for vector database operations
- sentence-transformers for embeddings
- OpenAI for LLM services
- Bootstrap for UI components

# RAG Document Assistant

A comprehensive Retrieval-Augmented Generation (RAG) system built with **FastAPI** and **PostgreSQL** that allows users to upload documents, ask questions, and get intelligent responses based on their document content.

## 🚀 Features

- **Multi-format Document Support**: PDF, DOCX, TXT, and JSON files
- **Secure Authentication**: JWT-based user authentication and authorization
- **Vector Search**: Advanced semantic search using Weaviate vector database
- **AI-Powered Responses**: Intelligent answers using RAG technology with optional OpenAI integration
- **PostgreSQL Database**: Robust and scalable data persistence
- **Modern API**: FastAPI with automatic API documentation
- **User Isolation**: Each user has their own secure document space
- **Real-time Processing**: Async document processing and query handling

## 🏗️ Architecture

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Vector Store**: Weaviate
- **Authentication**: JWT tokens
- **Document Processing**: Multi-format parsing with chunking
- **Embeddings**: Sentence Transformers (with OpenAI option)
- **Containerization**: Docker & Docker Compose

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL (if running locally)

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd rag-document-assistant
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - PostgreSQL: localhost:5432
   - Weaviate: http://localhost:8080

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL**:
   ```bash
   # Start PostgreSQL (example with Docker)
   docker run -d \
     --name postgres \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=password \
     -e POSTGRES_DB=rag_db \
     -p 5432:5432 \
     postgres:15
   ```

3. **Start Weaviate**:
   ```bash
   docker-compose up weaviate -d
   ```

4. **Run the application**:
   ```bash
   uvicorn main:app --reload
   ```

## 📚 API Usage

### Authentication

1. **Register a new user**:
   ```bash
   curl -X POST "http://localhost:8000/api/auth/register" \
        -H "Content-Type: application/json" \
        -d '{
          "username": "testuser",
          "email": "test@example.com",
          "password": "password123"
        }'
   ```

2. **Login and get access token**:
   ```bash
   curl -X POST "http://localhost:8000/api/auth/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=testuser&password=password123"
   ```

### Document Management

3. **Upload a document**:
   ```bash
   curl -X POST "http://localhost:8000/api/documents/upload" \
        -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
        -F "file=@/path/to/your/document.pdf"
   ```

4. **List documents**:
   ```bash
   curl -X GET "http://localhost:8000/api/documents/" \
        -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

### Querying

5. **Ask a question**:
   ```bash
   curl -X POST "http://localhost:8000/api/queries/" \
        -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
          "query_text": "What are the main topics in my documents?"
        }'
   ```

6. **Get query history**:
   ```bash
   curl -X GET "http://localhost:8000/api/queries/history" \
        -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

### Dashboard

7. **Get dashboard data**:
   ```bash
   curl -X GET "http://localhost:8000/api/dashboard/" \
        -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

## 🔧 Configuration

The application can be configured using environment variables. See `.env.example` for all available options:

### Key Configuration Options

- **SECRET_KEY**: JWT signing secret (change in production!)
- **DATABASE_URL**: PostgreSQL connection string
- **WEAVIATE_URL**: Weaviate instance URL
- **OPENAI_API_KEY**: Optional OpenAI API key for better responses
- **MAX_FILE_SIZE**: Maximum upload file size in bytes
- **CHUNK_SIZE**: Text chunk size for vector embeddings

## 📊 API Documentation

Once the application is running, you can access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🗂️ Project Structure

```
rag-document-assistant/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── database.py            # Database models and setup
├── schemas.py             # Pydantic schemas for validation
├── auth.py                # Authentication logic
├── routes.py              # API route handlers
├── document_processor.py  # Document parsing and processing
├── rag_system.py          # RAG query processing
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Multi-service setup
├── .env.example          # Environment variables template
└── README.md             # This file
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **User Isolation**: Each user's documents are completely isolated
- **Input Validation**: Comprehensive request validation using Pydantic
- **File Type Validation**: Only allowed file types can be uploaded
- **Size Limits**: Configurable file size restrictions
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries

## 🚀 Deployment

### Production Deployment

1. **Set strong secrets**:
   ```bash
   export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

2. **Use environment-specific settings**:
   ```bash
   export DEBUG=false
   export DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/rag_db
   ```

3. **Deploy with Docker**:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

### Scaling Considerations

- Use a load balancer for multiple FastAPI instances
- Implement Redis for session storage if needed
- Consider read replicas for PostgreSQL
- Use cloud storage for uploaded files in production

## 🧪 Testing

Run tests using pytest:

```bash
pytest
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🐛 Troubleshooting

### Common Issues

1. **Database connection errors**:
   - Ensure PostgreSQL is running
   - Check DATABASE_URL configuration
   - Verify network connectivity

2. **Weaviate connection errors**:
   - Ensure Weaviate is running on the correct port
   - Check WEAVIATE_URL configuration

3. **Document processing errors**:
   - Verify file format is supported
   - Check file size limits
   - Ensure sufficient disk space

4. **Authentication errors**:
   - Verify JWT token is valid
   - Check SECRET_KEY configuration
   - Ensure clock synchronization

### Getting Help

- Check the API documentation at `/docs`
- Review application logs
- Open an issue on GitHub

## 🎯 Roadmap

- [ ] Web frontend interface
- [ ] Advanced query filters
- [ ] Document metadata extraction
- [ ] Multi-language support
- [ ] Real-time collaboration features
- [ ] Advanced analytics dashboard

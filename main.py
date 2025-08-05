import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from config import settings
from database import create_tables
from routes import (
    auth_router,
    user_router, 
    document_router,
    query_router,
    dashboard_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting up RAG Document Assistant...")
    
    # Create upload directory
    os.makedirs(settings.upload_folder, exist_ok=True)
    
    # Create database tables
    try:
        await create_tables()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down RAG Document Assistant...")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A RAG (Retrieval Augmented Generation) system for document Q&A with user authentication",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(document_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": settings.app_name}

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API information"""
    html_content = f"""
    <html>
        <head>
            <title>{settings.app_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; text-align: center; }}
                .api-info {{ background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .endpoint {{ background: #3498db; color: white; padding: 10px; margin: 5px 0; border-radius: 3px; }}
                .method {{ background: #27ae60; padding: 2px 8px; border-radius: 3px; font-size: 12px; }}
                a {{ color: #3498db; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .feature {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #3498db; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 {settings.app_name}</h1>
                <p style="text-align: center; font-size: 18px; color: #7f8c8d;">
                    A powerful RAG system for intelligent document Q&A with secure user authentication
                </p>
                
                <div class="feature">
                    <h3>✨ Features</h3>
                    <ul>
                        <li><strong>Multi-format Support:</strong> PDF, DOCX, TXT, JSON documents</li>
                        <li><strong>Secure Authentication:</strong> JWT-based user authentication</li>
                        <li><strong>Vector Search:</strong> Advanced semantic search with Weaviate</li>
                        <li><strong>AI-Powered:</strong> Intelligent responses using RAG technology</li>
                        <li><strong>PostgreSQL:</strong> Robust data persistence</li>
                    </ul>
                </div>
                
                <div class="api-info">
                    <h3>📚 API Documentation</h3>
                    <p>Explore the interactive API documentation:</p>
                    <div class="endpoint">
                        <a href="/docs" style="color: white;">📖 Swagger UI - /docs</a>
                    </div>
                    <div class="endpoint">
                        <a href="/redoc" style="color: white;">📋 ReDoc - /redoc</a>
                    </div>
                </div>
                
                <div class="api-info">
                    <h3>🚀 API Endpoints</h3>
                    
                    <h4>Authentication</h4>
                    <div class="endpoint">
                        <span class="method">POST</span> /api/auth/register - Register new user
                    </div>
                    <div class="endpoint">
                        <span class="method">POST</span> /api/auth/token - Login and get access token
                    </div>
                    
                    <h4>Documents</h4>
                    <div class="endpoint">
                        <span class="method">POST</span> /api/documents/upload - Upload document
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span> /api/documents/ - List user documents
                    </div>
                    <div class="endpoint">
                        <span class="method">DELETE</span> /api/documents/{{id}} - Delete document
                    </div>
                    
                    <h4>Queries</h4>
                    <div class="endpoint">
                        <span class="method">POST</span> /api/queries/ - Ask question
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span> /api/queries/history - Get query history
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span> /api/queries/suggestions - Get query suggestions
                    </div>
                    
                    <h4>Dashboard</h4>
                    <div class="endpoint">
                        <span class="method">GET</span> /api/dashboard/ - Get dashboard data
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span> /api/users/me - Get current user info
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px; color: #7f8c8d;">
                    <p>💡 Start by registering a user, then upload documents and ask questions!</p>
                </div>
            </div>
        </body>
    </html>
    """
    return html_content

# Serve uploaded files (with authentication in production)
if os.path.exists(settings.upload_folder):
    app.mount("/uploads", StaticFiles(directory=settings.upload_folder), name="uploads")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
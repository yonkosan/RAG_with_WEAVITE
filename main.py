import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from decouple import config
import uvicorn

from database.models import Base
from database.connection import get_db, engine
from auth.dependencies import get_current_user
from auth.router import auth_router
from files.router import files_router
from rag.router import rag_router
from database.models import User

# Configuration
DATABASE_URL = config('DATABASE_URL', default='postgresql+asyncpg://raguser:ragpassword@localhost:5432/ragapp')
SECRET_KEY = config('SECRET_KEY', default='your-secret-key-change-in-production')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Database is configured in database.connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

# FastAPI app
app = FastAPI(
    title="RAG Application",
    description="A comprehensive RAG application with user authentication and file processing",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(files_router, prefix="/files", tags=["files"])
app.include_router(rag_router, prefix="/rag", tags=["rag"])

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "user": current_user}
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "RAG Application"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query as QueryParam
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import timedelta

from database import get_db, User, Document, Query
from schemas import (
    UserCreate, UserResponse, Token, DocumentResponse, DocumentUpload,
    QueryCreate, QueryResponse, QueryResult, DashboardData, DashboardStats,
    SuccessResponse, ErrorResponse
)
from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    get_user_by_username, get_user_by_email, create_user
)
from config import settings
from document_processor import get_document_processor
from rag_system import RAGSystem

# Create routers
auth_router = APIRouter(prefix="/auth", tags=["authentication"])
user_router = APIRouter(prefix="/users", tags=["users"])
document_router = APIRouter(prefix="/documents", tags=["documents"])
query_router = APIRouter(prefix="/queries", tags=["queries"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Initialize services
doc_processor = get_document_processor()
rag_system = RAGSystem(doc_processor, settings) if doc_processor else None

# Authentication Routes
@auth_router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    # Check if username exists
    if await get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Check if email exists
    if await get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create user
    db_user = await create_user(db, user.username, user.email, user.password)
    return UserResponse.from_orm(db_user)

@auth_router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Login and get access token"""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# User Routes
@user_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse.from_orm(current_user)

# Document Routes
@document_router.post("/upload", response_model=DocumentUpload)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload and process a document"""
    if not doc_processor:
        raise HTTPException(status_code=500, detail="Document processor not available")
    
    # Validate file type
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_extension not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file_extension}' not allowed. Allowed types: {', '.join(settings.allowed_extensions)}"
        )
    
    # Validate file size
    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_file_size / (1024*1024):.1f}MB"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.upload_folder, unique_filename)
    
    # Ensure upload directory exists
    os.makedirs(settings.upload_folder, exist_ok=True)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create database record
    db_document = Document(
        filename=unique_filename,
        original_filename=file.filename,
        file_type=file_extension,
        file_size=len(content),
        user_id=current_user.id
    )
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    # Process document asynchronously
    try:
        chunk_count = await doc_processor.process_and_store_document(file_path, db_document)
        await db.commit()
        
        return DocumentUpload(
            message=f"Document uploaded and processed successfully. {chunk_count} chunks created.",
            document_id=db_document.id
        )
    except Exception as e:
        # Clean up file if processing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        await db.delete(db_document)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@document_router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List user's documents"""
    result = await db.execute(
        select(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(desc(Document.upload_date))
        .offset(skip)
        .limit(limit)
    )
    documents = result.scalars().all()
    return [DocumentResponse.from_orm(doc) for doc in documents]

@document_router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific document"""
    result = await db.execute(
        select(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.from_orm(document)

@document_router.delete("/{document_id}", response_model=SuccessResponse)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    result = await db.execute(
        select(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from Weaviate
    if doc_processor:
        doc_processor.delete_document_chunks(document_id, current_user.id)
    
    # Delete file
    file_path = os.path.join(settings.upload_folder, document.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database
    await db.delete(document)
    await db.commit()
    
    return SuccessResponse(message="Document deleted successfully")

# Query Routes
@query_router.post("/", response_model=QueryResult)
async def ask_question(
    query: QueryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Ask a question about documents"""
    if not rag_system:
        raise HTTPException(status_code=500, detail="RAG system not available")
    
    # Process query
    result = rag_system.process_query(query.query_text, current_user.id)
    
    # Save query to database
    db_query = Query(
        query_text=query.query_text,
        response=result['response'],
        processing_time=result['processing_time'],
        retrieved_chunks_count=result['retrieved_chunks_count'],
        confidence_score=result['confidence_score'],
        user_id=current_user.id
    )
    db.add(db_query)
    await db.commit()
    
    return QueryResult(**result)

@query_router.get("/history", response_model=List[QueryResponse])
async def get_query_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """Get user's query history"""
    result = await db.execute(
        select(Query)
        .filter(Query.user_id == current_user.id)
        .order_by(desc(Query.timestamp))
        .offset(skip)
        .limit(limit)
    )
    queries = result.scalars().all()
    return [QueryResponse.from_orm(q) for q in queries]

@query_router.get("/suggestions")
async def get_query_suggestions(
    current_user: User = Depends(get_current_active_user)
):
    """Get query suggestions"""
    if not rag_system:
        return {"suggestions": []}
    
    suggestions = rag_system.get_query_suggestions(current_user.id)
    return {"suggestions": suggestions}

# Dashboard Routes
@dashboard_router.get("/", response_model=DashboardData)
async def get_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard data"""
    # Get statistics
    total_docs_result = await db.execute(
        select(func.count(Document.id)).filter(Document.user_id == current_user.id)
    )
    total_documents = total_docs_result.scalar()
    
    processed_docs_result = await db.execute(
        select(func.count(Document.id)).filter(
            Document.user_id == current_user.id,
            Document.processed == True
        )
    )
    processed_documents = processed_docs_result.scalar()
    
    total_chunks_result = await db.execute(
        select(func.sum(Document.chunk_count)).filter(Document.user_id == current_user.id)
    )
    total_chunks = total_chunks_result.scalar() or 0
    
    total_queries_result = await db.execute(
        select(func.count(Query.id)).filter(Query.user_id == current_user.id)
    )
    total_queries = total_queries_result.scalar()
    
    stats = DashboardStats(
        total_documents=total_documents,
        processed_documents=processed_documents,
        total_queries=total_queries,
        total_chunks=total_chunks
    )
    
    # Get recent documents
    recent_docs_result = await db.execute(
        select(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(desc(Document.upload_date))
        .limit(5)
    )
    recent_documents = [DocumentResponse.from_orm(doc) for doc in recent_docs_result.scalars().all()]
    
    # Get recent queries
    recent_queries_result = await db.execute(
        select(Query)
        .filter(Query.user_id == current_user.id)
        .order_by(desc(Query.timestamp))
        .limit(5)
    )
    recent_queries = [QueryResponse.from_orm(q) for q in recent_queries_result.scalars().all()]
    
    # Get suggestions
    suggestions = []
    if rag_system:
        suggestions = rag_system.get_query_suggestions(current_user.id)
    
    return DashboardData(
        stats=stats,
        recent_documents=recent_documents,
        recent_queries=recent_queries,
        suggestions=suggestions
    )
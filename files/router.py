import os
import uuid
import aiofiles
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.connection import get_db
from database.models import User as DBUser, Document as DBDocument, DocumentChunk
from auth.dependencies import get_current_user
from files.models import FileUploadResponse, DocumentResponse, ProcessingStatus
from files.processors import FileProcessor, UniversalFileProcessor

files_router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# File size limit (16MB)
MAX_FILE_SIZE = 16 * 1024 * 1024

@files_router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file and queue it for processing."""
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024)}MB"
        )
    
    # Check if file type is supported
    if not FileProcessor.is_supported(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not supported"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    # Detect file type
    file_type = FileProcessor.get_file_type(file_path)
    
    # Create database record
    db_document = DBDocument(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_type=file_type,
        file_size=len(file_content),
        owner_id=current_user.id,
        is_processed=False
    )
    
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    # Queue background processing
    background_tasks.add_task(process_document, db_document.id, file_path)
    
    return FileUploadResponse(
        message="File uploaded successfully and queued for processing",
        document_id=db_document.id,
        filename=file.filename,
        file_size=len(file_content),
        is_processed=False
    )

async def process_document(document_id: uuid.UUID, file_path: str):
    """Background task to process uploaded document."""
    from database.connection import async_session_maker
    from rag.embeddings import EmbeddingService
    
    async with async_session_maker() as db:
        try:
            # Get document from database
            result = await db.execute(select(DBDocument).filter(DBDocument.id == document_id))
            document = result.scalar_one_or_none()
            
            if not document:
                return
            
            # Process file
            processor = UniversalFileProcessor()
            processed_data = processor.process_file(file_path)
            
            if 'error' in processed_data:
                print(f"Error processing document {document_id}: {processed_data['error']}")
                return
            
            # Extract text content
            content = ""
            if 'text' in processed_data:
                content = processed_data['text']
            elif 'data' in processed_data:
                content = str(processed_data['data'])
            
            # Update document with extracted content
            document.content = content
            document.summary = content[:500] + "..." if len(content) > 500 else content
            
            # Create text chunks
            if content:
                chunks = processor.chunk_text(content)
                embedding_service = EmbeddingService()
                
                for i, chunk in enumerate(chunks):
                    # Generate embedding
                    embedding = await embedding_service.create_embedding(chunk)
                    
                    # Create chunk record
                    db_chunk = DocumentChunk(
                        document_id=document_id,
                        chunk_index=i,
                        content=chunk,
                        embedding=embedding,
                        metadata=f"chunk_{i}"
                    )
                    db.add(db_chunk)
            
            # Mark as processed
            document.is_processed = True
            await db.commit()
            
        except Exception as e:
            print(f"Error processing document {document_id}: {str(e)}")
            # Mark as failed (you might want to add a status field)
            await db.rollback()

@files_router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's documents."""
    
    # Get documents with chunk count
    result = await db.execute(
        select(
            DBDocument,
            func.count(DocumentChunk.id).label('chunks_count')
        )
        .outerjoin(DocumentChunk)
        .filter(DBDocument.owner_id == current_user.id)
        .group_by(DBDocument.id)
        .order_by(DBDocument.created_at.desc())
    )
    
    documents = []
    for row in result:
        doc = row[0]
        chunks_count = row[1] or 0
        
        doc_response = DocumentResponse.model_validate(doc)
        doc_response.chunks_count = chunks_count
        documents.append(doc_response)
    
    return documents

@files_router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific document details."""
    
    result = await db.execute(
        select(
            DBDocument,
            func.count(DocumentChunk.id).label('chunks_count')
        )
        .outerjoin(DocumentChunk)
        .filter(
            DBDocument.id == document_id,
            DBDocument.owner_id == current_user.id
        )
        .group_by(DBDocument.id)
    )
    
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    doc = row[0]
    chunks_count = row[1] or 0
    
    doc_response = DocumentResponse.model_validate(doc)
    doc_response.chunks_count = chunks_count
    
    return doc_response

@files_router.get("/documents/{document_id}/status", response_model=ProcessingStatus)
async def get_processing_status(
    document_id: uuid.UUID,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document processing status."""
    
    result = await db.execute(
        select(
            DBDocument,
            func.count(DocumentChunk.id).label('chunks_count')
        )
        .outerjoin(DocumentChunk)
        .filter(
            DBDocument.id == document_id,
            DBDocument.owner_id == current_user.id
        )
        .group_by(DBDocument.id)
    )
    
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    doc = row[0]
    chunks_count = row[1] or 0
    
    status_text = "completed" if doc.is_processed else "processing"
    message = f"Document processed successfully with {chunks_count} chunks" if doc.is_processed else "Document is being processed"
    
    return ProcessingStatus(
        document_id=document_id,
        status=status_text,
        message=message,
        chunks_created=chunks_count
    )

@files_router.delete("/documents/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document and its associated files."""
    
    # Get document
    result = await db.execute(
        select(DBDocument).filter(
            DBDocument.id == document_id,
            DBDocument.owner_id == current_user.id
        )
    )
    
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file from filesystem
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except Exception as e:
        print(f"Error deleting file {document.file_path}: {e}")
    
    # Delete from database (chunks will be deleted automatically due to cascade)
    await db.delete(document)
    await db.commit()
    
    return {"message": "Document deleted successfully"}

@files_router.get("/upload", response_class=HTMLResponse)
async def upload_page(
    request: Request,
    current_user: DBUser = Depends(get_current_user)
):
    """File upload page."""
    return templates.TemplateResponse("upload.html", {"request": request, "user": current_user})
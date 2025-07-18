import json
from typing import List
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.connection import get_db
from database.models import User as DBUser, QueryHistory as DBQueryHistory
from auth.dependencies import get_current_user
from rag.models import QueryRequest, QueryResponse, QueryHistory
from rag.retrieval import RetrievalService
from rag.llm import get_llm_service


rag_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@rag_router.post("/query", response_model=QueryResponse)
async def query_documents(
    query_request: QueryRequest,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query user's documents and get AI-generated response."""
    
    # Initialize services
    retrieval_service = RetrievalService()
    llm_service = get_llm_service()
    
    # Search for relevant chunks
    relevant_chunks, processing_time = await retrieval_service.search_similar_chunks(
        query=query_request.query,
        user_id=str(current_user.id),
        db=db,
        max_results=query_request.max_results,
        similarity_threshold=query_request.similarity_threshold
    )
    
    # Generate response using LLM
    answer = await llm_service.generate_response(
        query=query_request.query,
        relevant_chunks=relevant_chunks
    )
    
    # Save query to history
    relevant_doc_ids = [str(chunk.document_id) for chunk in relevant_chunks]
    db_query = DBQueryHistory(
        user_id=current_user.id,
        query=query_request.query,
        response=answer,
        relevant_documents=json.dumps(relevant_doc_ids)
    )
    
    db.add(db_query)
    await db.commit()
    
    return QueryResponse(
        query=query_request.query,
        answer=answer,
        relevant_chunks=relevant_chunks,
        total_chunks_found=len(relevant_chunks),
        processing_time=processing_time
    )

@rag_router.get("/history", response_model=List[QueryHistory])
async def get_query_history(
    limit: int = 20,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's query history."""
    
    result = await db.execute(
        select(DBQueryHistory)
        .filter(DBQueryHistory.user_id == current_user.id)
        .order_by(DBQueryHistory.created_at.desc())
        .limit(limit)
    )
    
    history = []
    for db_query in result.scalars():
        relevant_docs = []
        if db_query.relevant_documents:
            try:
                relevant_docs = json.loads(db_query.relevant_documents)
            except json.JSONDecodeError:
                pass
        
        query_history = QueryHistory(
            id=db_query.id,
            query=db_query.query,
            response=db_query.response,
            created_at=db_query.created_at,
            relevant_document_count=len(relevant_docs)
        )
        history.append(query_history)
    
    return history

@rag_router.get("/statistics")
async def get_rag_statistics(
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get RAG-related statistics for the user."""
    
    retrieval_service = RetrievalService()
    
    # Get document statistics
    doc_stats = await retrieval_service.get_document_statistics(
        user_id=str(current_user.id),
        db=db
    )
    
    # Get query history count
    query_count_result = await db.execute(
        select(DBQueryHistory)
        .filter(DBQueryHistory.user_id == current_user.id)
    )
    total_queries = len(query_count_result.fetchall())
    
    return {
        "document_statistics": doc_stats,
        "total_queries": total_queries,
        "user_id": str(current_user.id)
    }

@rag_router.delete("/history/{query_id}")
async def delete_query_history(
    query_id: str,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific query from history."""
    
    result = await db.execute(
        select(DBQueryHistory).filter(
            DBQueryHistory.id == query_id,
            DBQueryHistory.user_id == current_user.id
        )
    )
    
    query_history = result.scalar_one_or_none()
    if not query_history:
        return {"error": "Query not found"}
    
    await db.delete(query_history)
    await db.commit()
    
    return {"message": "Query deleted from history"}

@rag_router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    current_user: DBUser = Depends(get_current_user)
):
    """RAG search page."""
    return templates.TemplateResponse("search.html", {"request": request, "user": current_user})

@rag_router.post("/search-documents")
async def search_specific_documents(
    query: str,
    document_ids: List[str],
    max_results: int = 5,
    similarity_threshold: float = 0.7,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search within specific documents only."""
    
    retrieval_service = RetrievalService()
    llm_service = get_llm_service()
    
    # Search in specific documents
    relevant_chunks, processing_time = await retrieval_service.search_in_specific_documents(
        query=query,
        document_ids=document_ids,
        user_id=str(current_user.id),
        db=db,
        max_results=max_results,
        similarity_threshold=similarity_threshold
    )
    
    # Generate response
    answer = await llm_service.generate_response(
        query=query,
        relevant_chunks=relevant_chunks
    )
    
    return QueryResponse(
        query=query,
        answer=answer,
        relevant_chunks=relevant_chunks,
        total_chunks_found=len(relevant_chunks),
        processing_time=processing_time
    )
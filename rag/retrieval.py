import time
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pgvector.sqlalchemy import Vector

from database.models import DocumentChunk, Document as DBDocument
from rag.embeddings import get_embedding_service
from rag.models import RelevantChunk


class RetrievalService:
    """Service for retrieving relevant document chunks based on similarity search."""
    
    def __init__(self, embedding_service=None):
        """Initialize the retrieval service."""
        self.embedding_service = embedding_service or get_embedding_service()
    
    async def search_similar_chunks(
        self,
        query: str,
        user_id: str,
        db: AsyncSession,
        max_results: int = 5,
        similarity_threshold: float = 0.7
    ) -> Tuple[List[RelevantChunk], float]:
        """
        Search for document chunks similar to the query.
        
        Returns:
            Tuple of (relevant_chunks, processing_time)
        """
        start_time = time.time()
        
        # Create embedding for the query
        query_embedding = await self.embedding_service.create_embedding(query)
        
        # Perform vector similarity search using pgvector
        # We join with documents to ensure user ownership and get document names
        similarity_query = text("""
            SELECT 
                dc.id,
                dc.document_id,
                dc.content,
                dc.chunk_index,
                d.original_filename,
                (dc.embedding <=> :query_embedding) as distance
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.owner_id = :user_id
                AND dc.embedding IS NOT NULL
                AND (dc.embedding <=> :query_embedding) < :distance_threshold
            ORDER BY dc.embedding <=> :query_embedding
            LIMIT :max_results
        """)
        
        # Convert similarity threshold to distance threshold
        # pgvector uses distance (lower is more similar), so we convert
        # similarity_threshold of 0.7 to distance_threshold of 0.3
        distance_threshold = 1.0 - similarity_threshold
        
        result = await db.execute(
            similarity_query,
            {
                "query_embedding": query_embedding,
                "user_id": user_id,
                "distance_threshold": distance_threshold,
                "max_results": max_results
            }
        )
        
        relevant_chunks = []
        for row in result:
            # Convert distance back to similarity score
            similarity_score = 1.0 - row.distance
            
            relevant_chunk = RelevantChunk(
                document_id=row.document_id,
                document_name=row.original_filename,
                chunk_content=row.content,
                similarity_score=similarity_score,
                chunk_index=row.chunk_index
            )
            relevant_chunks.append(relevant_chunk)
        
        processing_time = time.time() - start_time
        return relevant_chunks, processing_time
    
    async def search_in_specific_documents(
        self,
        query: str,
        document_ids: List[str],
        user_id: str,
        db: AsyncSession,
        max_results: int = 5,
        similarity_threshold: float = 0.7
    ) -> Tuple[List[RelevantChunk], float]:
        """
        Search for chunks in specific documents only.
        """
        start_time = time.time()
        
        # Create embedding for the query
        query_embedding = await self.embedding_service.create_embedding(query)
        
        # Create placeholder string for document IDs
        document_placeholders = ', '.join([f"'{doc_id}'" for doc_id in document_ids])
        
        similarity_query = text(f"""
            SELECT 
                dc.id,
                dc.document_id,
                dc.content,
                dc.chunk_index,
                d.original_filename,
                (dc.embedding <=> :query_embedding) as distance
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.owner_id = :user_id
                AND d.id IN ({document_placeholders})
                AND dc.embedding IS NOT NULL
                AND (dc.embedding <=> :query_embedding) < :distance_threshold
            ORDER BY dc.embedding <=> :query_embedding
            LIMIT :max_results
        """)
        
        distance_threshold = 1.0 - similarity_threshold
        
        result = await db.execute(
            similarity_query,
            {
                "query_embedding": query_embedding,
                "user_id": user_id,
                "distance_threshold": distance_threshold,
                "max_results": max_results
            }
        )
        
        relevant_chunks = []
        for row in result:
            similarity_score = 1.0 - row.distance
            
            relevant_chunk = RelevantChunk(
                document_id=row.document_id,
                document_name=row.original_filename,
                chunk_content=row.content,
                similarity_score=similarity_score,
                chunk_index=row.chunk_index
            )
            relevant_chunks.append(relevant_chunk)
        
        processing_time = time.time() - start_time
        return relevant_chunks, processing_time
    
    async def get_document_statistics(self, user_id: str, db: AsyncSession) -> dict:
        """Get statistics about user's documents and chunks."""
        
        # Count documents
        doc_count_query = select(DBDocument).filter(DBDocument.owner_id == user_id)
        doc_result = await db.execute(doc_count_query)
        total_documents = len(doc_result.fetchall())
        
        # Count chunks
        chunk_count_query = text("""
            SELECT COUNT(dc.id) as total_chunks
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.owner_id = :user_id
                AND dc.embedding IS NOT NULL
        """)
        
        chunk_result = await db.execute(chunk_count_query, {"user_id": user_id})
        total_chunks = chunk_result.scalar() or 0
        
        # Count processed documents
        processed_query = select(DBDocument).filter(
            DBDocument.owner_id == user_id,
            DBDocument.is_processed == True
        )
        processed_result = await db.execute(processed_query)
        processed_documents = len(processed_result.fetchall())
        
        return {
            "total_documents": total_documents,
            "processed_documents": processed_documents,
            "total_chunks": total_chunks,
            "average_chunks_per_document": total_chunks / max(processed_documents, 1)
        }
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class QueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5
    similarity_threshold: Optional[float] = 0.7

class RelevantChunk(BaseModel):
    document_id: uuid.UUID
    document_name: str
    chunk_content: str
    similarity_score: float
    chunk_index: int

class QueryResponse(BaseModel):
    query: str
    answer: str
    relevant_chunks: List[RelevantChunk]
    total_chunks_found: int
    processing_time: float

class QueryHistory(BaseModel):
    id: uuid.UUID
    query: str
    response: str
    created_at: datetime
    relevant_document_count: int

    class Config:
        from_attributes = True

class EmbeddingRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    text_length: int
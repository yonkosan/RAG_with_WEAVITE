from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

# Document schemas
class DocumentBase(BaseModel):
    original_filename: str
    file_type: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    filename: str
    file_size: int
    upload_date: datetime
    processed: bool
    chunk_count: int
    content_preview: Optional[str] = None
    
    class Config:
        from_attributes = True

class DocumentUpload(BaseModel):
    message: str
    document_id: int

# Query schemas
class QueryCreate(BaseModel):
    query_text: str = Field(..., min_length=5, max_length=1000)

class QueryResponse(BaseModel):
    id: int
    query_text: str
    response: Optional[str]
    timestamp: datetime
    processing_time: Optional[float]
    retrieved_chunks_count: int
    confidence_score: Optional[float]
    
    class Config:
        from_attributes = True

class QueryResult(BaseModel):
    response: str
    retrieved_chunks_count: int
    processing_time: float
    confidence_score: float
    sources: List[str]

# Dashboard schemas
class DashboardStats(BaseModel):
    total_documents: int
    processed_documents: int
    total_queries: int
    total_chunks: int

class DashboardData(BaseModel):
    stats: DashboardStats
    recent_documents: List[DocumentResponse]
    recent_queries: List[QueryResponse]
    suggestions: List[str]

# Error schemas
class ErrorResponse(BaseModel):
    detail: str
    
class SuccessResponse(BaseModel):
    message: str
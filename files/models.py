from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

class DocumentBase(BaseModel):
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    content: Optional[str] = None
    summary: Optional[str] = None

class DocumentCreate(DocumentBase):
    file_path: str
    owner_id: uuid.UUID

class DocumentInDB(DocumentBase):
    id: uuid.UUID
    file_path: str
    is_processed: bool
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Document(DocumentInDB):
    pass

class DocumentResponse(Document):
    chunks_count: Optional[int] = 0

class FileUploadResponse(BaseModel):
    message: str
    document_id: uuid.UUID
    filename: str
    file_size: int
    is_processed: bool

class ProcessingStatus(BaseModel):
    document_id: uuid.UUID
    status: str  # "pending", "processing", "completed", "failed"
    message: Optional[str] = None
    chunks_created: Optional[int] = 0
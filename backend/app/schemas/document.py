from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentPageInfo(BaseModel):
    id: str
    page_number: int
    image_url: str
    preview_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class DocumentResponse(BaseModel):
    id: str
    title: str
    original_filename: str
    file_size: int
    mime_type: str
    document_type: str
    status: str
    error_message: Optional[str] = None
    pages: List[DocumentPageInfo] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentProcessingStatus(BaseModel):
    document_id: str
    status: str
    progress_percentage: int
    stage: str
    error_message: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    title: str
    original_filename: str
    status: str
    message: str


class DocumentUpdatePayload(BaseModel):
    title: Optional[str] = None
    document_type: Optional[str] = None

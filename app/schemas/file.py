from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FileUpload(BaseModel):
    """Schema for file upload metadata."""
    filename: str
    content_type: Optional[str] = None
    size: Optional[int] = None


class FileResponse(BaseModel):
    """Schema for file response."""
    id: str
    filename: str
    object_name: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    url: Optional[str] = None
    bucket: str
    created_at: datetime
    user_id: str
    
    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """Schema for file list response."""
    files: list[FileResponse]
    total: int
    page: int
    per_page: int


from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class EvidenceInfo(BaseModel):
    """Schema for evidence information stored in JSON column."""
    type: str
    name: str
    description: str
    uploadDate: str
    fileSize: str
    tags: List[str]
    duration: Optional[str] = None
    thumbnail: Optional[str] = None


class EvidenceResponse(BaseModel):
    """Schema for evidence response with flattened structure."""
    id: str
    caseId: str
    type: str
    name: str
    description: str
    uploadDate: str
    fileSize: str
    tags: List[str]
    duration: Optional[str] = None
    thumbnail: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EvidenceCreate(BaseModel):
    """Schema for creating new evidence."""
    id: str
    case_id: str
    evidence_info: EvidenceInfo


class EvidenceUpdate(BaseModel):
    """Schema for updating evidence."""
    evidence_info: Optional[EvidenceInfo] = None
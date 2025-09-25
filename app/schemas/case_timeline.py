from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TimelineInfo(BaseModel):
    """Schema for timeline information stored in JSON column."""
    timestamp: str
    title: str
    description: str
    source: str
    evidenceId: Optional[str] = None
    evidenceType: Optional[str] = None


class CaseTimelineResponse(BaseModel):
    """Schema for case timeline response with flattened structure."""
    id: str
    caseId: str
    timestamp: str
    title: str
    description: str
    source: str
    evidenceId: Optional[str] = None
    evidenceType: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CaseTimelineCreate(BaseModel):
    """Schema for creating new timeline entry."""
    id: str
    case_id: str
    timeline_info: TimelineInfo


class CaseTimelineUpdate(BaseModel):
    """Schema for updating timeline entry."""
    timeline_info: Optional[TimelineInfo] = None
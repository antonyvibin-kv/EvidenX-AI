from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TimelineDate(BaseModel):
    """Schema for timeline date."""
    day: int
    month: int


class TimelineInfo(BaseModel):
    """Schema for timeline information stored in JSON column."""
    time: float
    duration: float
    actor: str
    date: TimelineDate
    title: str
    type: str
    confidence: int
    evidence: str
    description: str


class CaseTimelineResponse(BaseModel):
    """Schema for case timeline response with new format."""
    id: int
    time: float
    duration: float
    actor: str
    date: TimelineDate
    title: str
    type: str
    confidence: int
    evidence: str
    description: str
    
    class Config:
        from_attributes = True


class CaseTimelineCreate(BaseModel):
    """Schema for creating new timeline entry."""
    id: int
    case_id: str
    timeline_info: TimelineInfo


class CaseTimelineUpdate(BaseModel):
    """Schema for updating timeline entry."""
    timeline_info: Optional[TimelineInfo] = None
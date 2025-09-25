from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class AudioComparisonWitness(BaseModel):
    """Schema for witness information in audio comparison."""
    id: str
    witnessName: str
    witnessImage: str
    audioId: str
    summary: str
    transcript: str
    contradictions: List[str]
    similarities: List[str]
    grayAreas: List[str]


class DetailedAnalysis(BaseModel):
    """Schema for detailed analysis of audio comparison."""
    topic: str
    witness1: str
    witness2: str
    status: str  # "contradiction", "similarity", "gray_area"
    details: str


class AudioComparisonResponse(BaseModel):
    """Schema for audio comparison response."""
    id: str
    caseId: str
    mediaId1: str
    mediaId2: str
    witnesses: List[AudioComparisonWitness]
    detailedAnalysis: List[DetailedAnalysis]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AudioComparisonCreate(BaseModel):
    """Schema for creating audio comparison."""
    caseId: str
    mediaId1: str
    mediaId2: str


class AudioComparisonRequest(BaseModel):
    """Schema for audio comparison request."""
    caseId: str
    mediaId1: str
    mediaId2: str
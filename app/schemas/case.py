from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CaseInfo(BaseModel):
    """Schema for case information stored in JSON column."""
    firNumber: str
    title: str
    summary: str
    petitioner: str
    accused: str
    investigatingOfficer: str
    registeredDate: str
    status: str
    visibility: str
    location: str


class MediaInfo(BaseModel):
    """Schema for media information in case response."""
    id: str
    type: str
    url: str
    title: str
    description: str
    fileSize: Optional[str] = None
    format: Optional[str] = None
    uploadDate: Optional[str] = None
    duration: Optional[str] = None
    transcript: Optional[str] = None
    speakers: Optional[int] = None
    confidence: Optional[int] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    thumbnail: Optional[str] = None
    camera: Optional[str] = None
    location: Optional[str] = None
    pages: Optional[int] = None
    author: Optional[str] = None


class EvidenceInfo(BaseModel):
    """Schema for evidence information in case response."""
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


class AudioComparisonInfo(BaseModel):
    """Schema for audio comparison information in case response."""
    id: str
    caseId: str
    mediaId1: str
    mediaId2: str
    witnesses: List[AudioComparisonWitness]
    detailedAnalysis: List[DetailedAnalysis]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CaseResponse(BaseModel):
    """Schema for case response with flattened structure."""
    id: str
    firNumber: str
    title: str
    summary: str
    petitioner: str
    accused: str
    investigatingOfficer: str
    registeredDate: str
    status: str
    visibility: str
    location: str
    media: Optional[List[MediaInfo]] = None
    evidence: Optional[List[EvidenceInfo]] = None
    audioComparisons: Optional[List[AudioComparisonInfo]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CaseCreate(BaseModel):
    """Schema for creating a new case."""
    id: str
    case_info: CaseInfo


class CaseUpdate(BaseModel):
    """Schema for updating a case."""
    case_info: Optional[CaseInfo] = None
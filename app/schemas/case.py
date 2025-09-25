from pydantic import BaseModel
from typing import Optional
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
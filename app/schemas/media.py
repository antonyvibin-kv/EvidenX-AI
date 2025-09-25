from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MediaInfo(BaseModel):
    """Schema for media information stored in JSON column."""
    type: str = Field(..., description="Media type (audio, video, image, document)")
    url: str = Field(..., description="URL of the media file")
    title: str = Field(..., description="Title of the media")
    description: str = Field(..., description="Description of the media")
    fileSize: Optional[str] = Field(None, description="File size in human readable format")
    format: Optional[str] = Field(None, description="File format (mp3, mp4, jpg, pdf, etc.)")
    uploadDate: Optional[str] = Field(None, description="Upload date")
    
    # Audio specific fields
    duration: Optional[str] = Field(None, description="Duration for audio/video files")
    transcript: Optional[str] = Field(None, description="Transcript for audio files")
    speakers: Optional[int] = Field(None, description="Number of speakers in audio")
    confidence: Optional[int] = Field(None, description="Transcription confidence score")
    
    # Video specific fields
    resolution: Optional[str] = Field(None, description="Video resolution")
    fps: Optional[int] = Field(None, description="Frames per second")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL for video")
    
    # Image specific fields
    camera: Optional[str] = Field(None, description="Camera used for image")
    location: Optional[str] = Field(None, description="Location where image was taken")
    
    # Document specific fields
    pages: Optional[int] = Field(None, description="Number of pages in document")
    author: Optional[str] = Field(None, description="Author of document")


class MediaResponse(BaseModel):
    """Schema for media response."""
    id: str = Field(..., description="Media ID")
    caseId: str = Field(..., description="Case ID")
    type: str = Field(..., description="Media type")
    url: str = Field(..., description="Media URL")
    title: str = Field(..., description="Media title")
    description: str = Field(..., description="Media description")
    fileSize: Optional[str] = Field(None, description="File size")
    format: Optional[str] = Field(None, description="File format")
    uploadDate: Optional[str] = Field(None, description="Upload date")
    duration: Optional[str] = Field(None, description="Duration")
    transcript: Optional[str] = Field(None, description="Transcript")
    speakers: Optional[int] = Field(None, description="Number of speakers")
    confidence: Optional[int] = Field(None, description="Confidence score")
    resolution: Optional[str] = Field(None, description="Resolution")
    fps: Optional[int] = Field(None, description="FPS")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL")
    camera: Optional[str] = Field(None, description="Camera")
    location: Optional[str] = Field(None, description="Location")
    pages: Optional[int] = Field(None, description="Pages")
    author: Optional[str] = Field(None, description="Author")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")
    
    class Config:
        from_attributes = True


class MediaCreate(BaseModel):
    """Schema for creating new media."""
    id: str
    case_id: str
    media_info: MediaInfo


class MediaUpdate(BaseModel):
    """Schema for updating media."""
    media_info: Optional[MediaInfo] = None
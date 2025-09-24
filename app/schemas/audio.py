from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class SpeakerSegment(BaseModel):
    """Individual speaker segment in the transcript."""
    speaker: int = Field(..., description="Speaker identifier (0, 1, 2, etc.)")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")
    confidence: float = Field(..., description="Confidence score (0-1)")


class SpeakerInfo(BaseModel):
    """Information about a speaker."""
    speaker_id: int = Field(..., description="Speaker identifier")
    total_speaking_time: float = Field(..., description="Total speaking time in seconds")
    segment_count: int = Field(..., description="Number of segments for this speaker")
    average_confidence: float = Field(..., description="Average confidence score")


class AudioTranscriptionRequest(BaseModel):
    """Request model for audio transcription."""
    language: Optional[str] = Field(
        default="en", 
        description="Language code (e.g., 'en', 'es', 'fr')",
        example="en"
    )
    model: Optional[str] = Field(
        default="nova-2", 
        description="Deepgram model to use",
        example="nova-2"
    )
    diarize: bool = Field(
        default=True, 
        description="Enable speaker diarization",
        example=True
    )
    punctuate: bool = Field(
        default=True, 
        description="Add punctuation to transcript",
        example=True
    )
    smart_format: bool = Field(
        default=True, 
        description="Apply smart formatting",
        example=True
    )
    redact: Optional[List[str]] = Field(
        default=None, 
        description="Redact sensitive information (e.g., ['pii', 'numbers'])",
        example=None
    )
    search: Optional[List[str]] = Field(
        default=None, 
        description="Search terms to highlight",
        example=None
    )
    
    class Config:
        schema_extra = {
            "example": {
                "language": "en",
                "model": "nova-2",
                "diarize": True,
                "punctuate": True,
                "smart_format": True,
                "redact": None,
                "search": None
            }
        }


class AudioTranscriptionResponse(BaseModel):
    """Response model for audio transcription."""
    transcript: str = Field(..., description="Full transcript text")
    segments: List[SpeakerSegment] = Field(..., description="Segmented transcript with speaker identification")
    speakers: List[SpeakerInfo] = Field(..., description="Information about each speaker")
    duration: float = Field(..., description="Total audio duration in seconds")
    language: str = Field(..., description="Detected language")
    confidence: float = Field(..., description="Overall confidence score")
    processing_time: float = Field(..., description="Processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of transcription")
    
    class Config:
        schema_extra = {
            "example": {
                "transcript": "Hello, this is a test transcription. How are you today?",
                "segments": [
                    {
                        "speaker": 0,
                        "start": 0.0,
                        "end": 2.5,
                        "text": "Hello, this is a test transcription.",
                        "confidence": 0.95
                    },
                    {
                        "speaker": 1,
                        "start": 3.0,
                        "end": 5.2,
                        "text": "How are you today?",
                        "confidence": 0.92
                    }
                ],
                "speakers": [
                    {
                        "speaker_id": 0,
                        "total_speaking_time": 2.5,
                        "segment_count": 1,
                        "average_confidence": 0.95
                    },
                    {
                        "speaker_id": 1,
                        "total_speaking_time": 2.2,
                        "segment_count": 1,
                        "average_confidence": 0.92
                    }
                ],
                "duration": 5.2,
                "language": "en",
                "confidence": 0.935,
                "processing_time": 3.2,
                "created_at": "2025-09-24T10:00:00Z"
            }
        }


class AudioUploadResponse(BaseModel):
    """Response model for audio file upload."""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the file")
    upload_url: Optional[str] = Field(None, description="URL to access the uploaded file")
    transcription_id: Optional[str] = Field(None, description="ID of the transcription job")


class TranscriptionJob(BaseModel):
    """Model for tracking transcription jobs."""
    job_id: str = Field(..., description="Unique job identifier")
    file_id: str = Field(..., description="Associated file ID")
    status: str = Field(..., description="Job status (pending, processing, completed, failed)")
    progress: float = Field(default=0.0, description="Progress percentage (0-100)")
    result: Optional[AudioTranscriptionResponse] = Field(None, description="Transcription result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")


class AudioFileInfo(BaseModel):
    """Information about an uploaded audio file."""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    channels: Optional[int] = Field(None, description="Number of audio channels")
    sample_rate: Optional[int] = Field(None, description="Audio sample rate")
    bit_rate: Optional[int] = Field(None, description="Audio bit rate")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    user_id: str = Field(..., description="User who uploaded the file")


class SpeakerDiarizationConfig(BaseModel):
    """Configuration for speaker diarization."""
    min_speakers: int = Field(default=2, description="Minimum number of speakers")
    max_speakers: int = Field(default=10, description="Maximum number of speakers")
    speaker_change_sensitivity: float = Field(default=0.5, description="Sensitivity for speaker changes (0-1)")
    enable_speaker_embedding: bool = Field(default=True, description="Enable speaker embedding analysis")
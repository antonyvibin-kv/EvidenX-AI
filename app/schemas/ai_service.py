from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime


class VisualSearchRequest(BaseModel):
    """Request model for visual search API"""
    user_query: str
    s3_url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "girl with pink shirt",
                "s3_url": "https://s3.amazonaws.com/bucket/video.mp4"
            }
        }


class DetectionResult(BaseModel):
    """Individual detection result"""
    label: str
    confidence: float
    bounding_box: List[float]  # [x1, y1, x2, y2]
    timestamp: float
    frame_id: int


class VisualSearchResponse(BaseModel):
    """Response model for visual search API"""
    query: str
    video_url: str
    total_frames_processed: int
    processing_time: float
    detections: List[DetectionResult]
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "girl with pink shirt",
                "video_url": "https://s3.amazonaws.com/bucket/video.mp4",
                "total_frames_processed": 15,
                "processing_time": 45.2,
                "detections": [
                    {
                        "label": "girl with pink shirt",
                        "confidence": 0.85,
                        "bounding_box": [100, 150, 200, 300],
                        "timestamp": 120.5,
                        "frame_id": 3605
                    }
                ],
                "created_at": "2024-01-15T10:30:00Z"
            }
        }

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from app.schemas.ai_service import VisualSearchRequest, VisualSearchResponse, DetectionResult
from app.services.visual_search_service import VisualSearch
import logging
import time
import tempfile
import os
import requests
from datetime import datetime
from typing import List
import torch

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize the visual search service
visual_search_service = VisualSearch()


async def download_video_from_s3(s3_url: str) -> str:
    """Download video from S3 URL to a temporary file"""
    try:
        response = requests.get(s3_url, stream=True)
        response.raise_for_status()
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        
        # Download the video content
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        
        temp_file.close()
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Error downloading video from S3: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to download video from S3: {str(e)}"
        )


def cleanup_temp_file(file_path: str):
    """Clean up temporary file"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {e}")


@router.post("/visual-search", response_model=VisualSearchResponse)
async def perform_visual_search(
    request: VisualSearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Perform visual search on a video using AI object detection.
    
    This endpoint downloads a video from the provided S3 URL and performs
    visual search using the specified query to detect objects/people in the video.
    """
    temp_video_path = None
    
    try:
        logger.info(f"Starting visual search for query: '{request.user_query}' on video: {request.s3_url}")
        
        # Download video from S3
        # temp_video_path = await download_video_from_s3(str(request.s3_url))\
        detections = []
        visual_searcher = VisualSearch()
        current_dir = os.getcwd()
        video_location = os.path.join(current_dir, "app", "storage", "short_cctv.mp4")
        start_time = time.time()
        detections = visual_searcher.fetch_timestamp(request.user_query, video_location)
        detections = [] # pr_delete
        processing_time = time.time() - start_time
        return VisualSearchResponse(
            query=request.user_query,
            video_url=str(request.s3_url),
            total_frames_processed=len(detections),
            processing_time=processing_time,
            detections=detections,
            created_at=datetime.utcnow()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in visual search: {e}")
        # Cleanup temp file in case of error
        if temp_video_path:
            cleanup_temp_file(temp_video_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visual search failed: {str(e)}"
        )





@router.get("/health")
async def health_check():
    """Health check endpoint for the AI service"""
    try:
        # Check if CUDA is available
        device_info = {
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
        
        return {
            "status": "healthy",
            "service": "AI Visual Search Service",
            "device_info": device_info,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service unhealthy"
        )

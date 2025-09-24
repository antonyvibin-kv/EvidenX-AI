from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
import uuid
import time
import logging
import os
import glob

from app.schemas.audio import (
    AudioTranscriptionRequest,
    AudioTranscriptionResponse,
    AudioUploadResponse,
    TranscriptionJob,
    AudioFileInfo,
    SpeakerDiarizationConfig
)
from app.services.deepgram_service import DeepgramService
from app.services.audio_service import AudioService
from app.core.config import settings
from app.api.auth import get_current_user

# In-memory storage for temp file paths (in production, use Redis or database)
temp_file_storage = {}

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
deepgram_service = None
audio_service = AudioService()


def get_deepgram_service() -> DeepgramService:
    """Get Deepgram service instance."""
    global deepgram_service
    if deepgram_service is None:
        if not hasattr(settings, 'deepgram_api_key') or not settings.deepgram_api_key:
            raise HTTPException(
                status_code=500,
                detail="Deepgram API key not configured"
            )
        deepgram_service = DeepgramService(settings.deepgram_api_key)
    return deepgram_service


@router.post("/upload", 
             response_model=AudioUploadResponse,
             summary="Upload Audio File",
             description="Upload an audio file for transcription. Supports various audio formats including WAV, MP3, MP4, M4A, FLAC, OGG, WEBM, AAC, M4B, 3GP, and AMR.",
             tags=["Audio Upload"])
async def upload_audio_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file to upload (max 2GB recommended)"),
    # current_user: dict = Depends(get_current_user)  # Disabled for testing
):
    """
    Upload an audio file for transcription.
    
    **Supported Formats:**
    - WAV, MP3, MP4, M4A, FLAC, OGG, WEBM, AAC, M4B, 3GP, AMR
    
    **File Size:**
    - Maximum: 2GB
    - Recommended: Under 50MB for optimal performance
    
    **Returns:**
    - File ID for use in transcription requests
    - File metadata (size, type, etc.)
    """
    try:
        # Validate file (more lenient for testing)
        if file.content_type and not file.content_type.startswith('audio/'):
            # Check if it's a known audio file by extension
            audio_extensions = ['.wav', '.mp3', '.mp4', '.m4a', '.flac', '.ogg', '.webm', '.aac', '.m4b', '.3gp', '.amr']
            file_ext = '.' + file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            if file_ext not in audio_extensions:
                raise HTTPException(
                    status_code=400,
                    detail="File must be an audio file"
                )
        
        # Read file data
        audio_data = await file.read()
        
        # Validate with Deepgram service
        deepgram = get_deepgram_service()
        validation_result = await deepgram.validate_audio_file(audio_data, file.filename)
        
        # Log file size for debugging
        file_size_mb = len(audio_data) / (1024 * 1024)
        logger.info(f"Audio file size: {file_size_mb:.2f} MB")
        
        if file_size_mb > 50:
            logger.warning(f"Large audio file detected ({file_size_mb:.2f} MB). This may cause timeout issues. Consider using a smaller file for testing.")
        
        # Store audio data temporarily for processing
        # In production, you'd store this in S3 or local storage
        import tempfile
        import os
        
        # Create a temporary file to store the audio data
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}")
        temp_file.write(audio_data)
        temp_file.close()
        
        # Upload to database
        upload_response = await audio_service.upload_audio_file(
            filename=file.filename,
            content_type=file.content_type,
            size=len(audio_data)
            # No user_id for testing
        )
        
        # Store temp file path in memory
        temp_file_storage[upload_response.file_id] = temp_file.name
        
        logger.info(f"Audio file uploaded: {file.filename} ({len(audio_data)} bytes)")
        
        return upload_response
        
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/transcribe/{file_id}", 
             response_model=TranscriptionJob,
             summary="Start Audio Transcription",
             description="Start transcription of an uploaded audio file with speaker diarization. The transcription runs in the background and can be monitored using the job ID.",
             tags=["Audio Transcription"])
async def transcribe_audio(
    file_id: str,
    request: AudioTranscriptionRequest,
    background_tasks: BackgroundTasks,
    # current_user: dict = Depends(get_current_user)  # Disabled for testing
):
    """
    Start transcription of an uploaded audio file.
    
    **Features:**
    - Speaker diarization (identify different speakers)
    - Multiple language support
    - Smart formatting and punctuation
    - Background processing
    
    **Parameters:**
    - `file_id`: ID of the uploaded audio file
    - `language`: Language code (e.g., 'en', 'es', 'fr')
    - `model`: Deepgram model ('nova-2', 'nova-3', 'nova-2-general')
    - `diarize`: Enable speaker diarization (recommended)
    - `punctuate`: Add punctuation to transcript
    - `smart_format`: Apply smart formatting
    
    **Returns:**
    - Job ID for monitoring progress
    - Initial job status and metadata
    """
    try:
        # Create transcription job in database
        job = await audio_service.create_transcription_job(
            file_id=file_id
            # No user_id for testing
        )
        
        # Start background transcription
        background_tasks.add_task(
            process_transcription,
            job.job_id,
            file_id,
            request
        )
        
        logger.info(f"Transcription job started: {job.job_id} for file: {file_id}")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription start failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


async def process_transcription(
    job_id: str,
    file_id: str,
    request: AudioTranscriptionRequest
):
    """Background task to process transcription."""
    try:
        # Update job status to processing
        await audio_service.update_transcription_job(
            job_id=job_id,
            status="processing",
            progress=10.0
        )
        
        logger.info(f"Processing transcription for job: {job_id}")
        
        # Get Deepgram service
        deepgram = get_deepgram_service()
        
        # Get the actual audio file data from the temp file storage
        try:
            # Get temp file path from in-memory storage
            temp_file_path = temp_file_storage.get(file_id)
            if not temp_file_path:
                logger.warning(f"Temp file not found in memory for {file_id}, checking if file exists...")
                # Try to find the temp file by searching common temp directories
                temp_patterns = [
                    f"/tmp/tmp*{file_id}*",
                    f"/tmp/tmp*{file_id.split('-')[0]}*",
                    f"/tmp/*{file_id}*"
                ]
                for pattern in temp_patterns:
                    matches = glob.glob(pattern)
                    if matches:
                        temp_file_path = matches[0]
                        temp_file_storage[file_id] = temp_file_path
                        logger.info(f"Found temp file: {temp_file_path}")
                        break
                
                if not temp_file_path:
                    raise Exception(f"Audio file not found for {file_id}. Please re-upload the file.")
            
            if not os.path.exists(temp_file_path):
                raise Exception(f"Audio file not found at {temp_file_path}")
            
            # Read the actual audio data from the temp file
            with open(temp_file_path, 'rb') as f:
                audio_data = f.read()
            
            logger.info(f"Read audio data: {len(audio_data)} bytes from {temp_file_path}")
            
            # Get audio file info for filename
            audio_file_info = await audio_service.get_audio_file_info(file_id)
            if not audio_file_info:
                raise Exception(f"Audio file {file_id} not found in database")
            
        except Exception as e:
            logger.error(f"Failed to get audio file data: {e}")
            raise Exception(f"Cannot process transcription: {e}")
        
        await audio_service.update_transcription_job(
            job_id=job_id,
            status="processing",
            progress=50.0
        )
        
        # Configure speaker diarization
        diarization_config = SpeakerDiarizationConfig(
            min_speakers=2,
            max_speakers=10,
            speaker_change_sensitivity=0.5,
            enable_speaker_embedding=True
        )
        
        # Perform transcription
        result = await deepgram.transcribe_audio(
            audio_data=audio_data,
            filename=audio_file_info.get('filename', 'unknown.wav'),
            request=request,
            diarization_config=diarization_config
        )
        
        await audio_service.update_transcription_job(
            job_id=job_id,
            status="processing",
            progress=90.0
        )
        
        # Save transcription result to database
        await audio_service.save_transcription_result(
            job_id=job_id,
            transcription_result=result
        )
        
        # Clean up temp file
        try:
            temp_file_path = temp_file_storage.get(file_id)
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                del temp_file_storage[file_id]
                logger.info(f"Cleaned up temp file: {temp_file_path}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
        
        logger.info(f"Transcription completed for job: {job_id}")
        
    except Exception as e:
        logger.error(f"Transcription processing failed for job {job_id}: {str(e)}")
        await audio_service.update_transcription_job(
            job_id=job_id,
            status="failed",
            error_message=str(e)
        )
        
        # Clean up temp file even on failure
        try:
            temp_file_path = temp_file_storage.get(file_id)
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                del temp_file_storage[file_id]
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup temp file after error: {cleanup_error}")


@router.get("/jobs/{job_id}", 
            response_model=TranscriptionJob,
            summary="Get Transcription Job Status",
            description="Get the current status and results of a transcription job. Returns detailed information including transcript, speaker segments, and processing metadata.",
            tags=["Job Management"])
async def get_transcription_job(
    job_id: str,
    # current_user: dict = Depends(get_current_user)  # Disabled for testing
):
    """
    Get transcription job status and result.
    
    **Returns:**
    - Job status (pending, processing, completed, failed)
    - Progress percentage
    - Full transcript text (when completed)
    - Speaker segments with timestamps
    - Speaker information and statistics
    - Processing metadata (duration, confidence, etc.)
    - Error messages (if failed)
    """
    job = await audio_service.get_transcription_job(
        job_id=job_id
        # No user_id for testing
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Transcription job not found")
    
    return job


@router.get("/jobs", 
            response_model=List[TranscriptionJob],
            summary="List Transcription Jobs",
            description="List all transcription jobs with optional filtering by status. Returns paginated results with job details and status information.",
            tags=["Job Management"])
async def list_transcription_jobs(
    # current_user: dict = Depends(get_current_user),  # Disabled for testing
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List transcription jobs for the current user.
    
    **Parameters:**
    - `status`: Filter by job status (pending, processing, completed, failed)
    - `limit`: Maximum number of jobs to return (default: 50)
    - `offset`: Number of jobs to skip for pagination (default: 0)
    
    **Returns:**
    - List of transcription jobs with status and metadata
    - Paginated results for large datasets
    - Jobs ordered by creation date (newest first)
    """
    # For testing, get all jobs without user filtering
    jobs = await audio_service.list_all_transcription_jobs(
        status=status,
        limit=limit,
        offset=offset
    )
    
    return jobs


@router.get("/files", response_model=List[AudioFileInfo])
async def list_audio_files(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """
    List uploaded audio files for the current user.
    
    Args:
        current_user: Current authenticated user
        limit: Maximum number of files to return
        offset: Number of files to skip
        
    Returns:
        List of AudioFileInfo objects
    """
    files = await audio_service.list_audio_files(
        user_id=current_user.get('id', 'anonymous'),
        limit=limit,
        offset=offset
    )
    
    return files


@router.delete("/files/{file_id}")
async def delete_audio_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an uploaded audio file.
    
    Args:
        file_id: File identifier
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    success = await audio_service.delete_audio_file(
        file_id=file_id,
        user_id=current_user.get('id', 'anonymous')
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    logger.info(f"Audio file deleted: {file_id}")
    
    return {"message": "Audio file deleted successfully"}


@router.get("/formats",
           summary="Get Supported Audio Formats",
           description="Get a list of all supported audio file formats for transcription. Includes common formats like WAV, MP3, MP4, and more.",
           tags=["Audio Information"])
async def get_supported_formats():
    """
    Get list of supported audio formats.
    
    **Supported Formats:**
    - WAV, MP3, MP4, M4A, FLAC, OGG, WEBM, AAC, M4B, 3GP, AMR
    
    **Returns:**
    - List of supported audio format extensions
    - Format compatibility information
    """
    try:
        deepgram = get_deepgram_service()
        formats = await deepgram.get_supported_formats()
        return {"supported_formats": formats}
    except Exception as e:
        logger.error(f"Failed to get supported formats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get supported formats")
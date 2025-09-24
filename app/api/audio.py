from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
from datetime import datetime
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
    TranscriptResponse,
    CaseTranscriptsResponse,
    SpeakerDiarizationConfig,
    TranscriptAnalysis,
    ComparisonItem
)
from app.services.deepgram_service import DeepgramService
from app.services.audio_service import AudioService
from app.services.openai_service import OpenAIService
from app.core.config import settings
from app.api.auth import get_current_user

# In-memory storage for temp file paths (in production, use Redis or database)
temp_file_storage = {}

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
deepgram_service = None
audio_service = AudioService()
openai_service = OpenAIService()


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
            file_id=file_id,
            case_id=request.case_id
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


@router.get("/jobs/case/{case_id}", 
            response_model=List[TranscriptionJob],
            summary="Get Transcriptions by Case ID",
            description="Get all transcription jobs for a specific case ID. Returns all jobs associated with the case, including their status and results.",
            tags=["Job Management"])
async def get_transcriptions_by_case_id(
    case_id: str,
    # current_user: dict = Depends(get_current_user),  # Disabled for testing
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get all transcription jobs for a specific case ID.
    
    **Parameters:**
    - `case_id`: The case identifier to filter by
    - `status`: Optional filter by job status (pending, processing, completed, failed)
    - `limit`: Maximum number of jobs to return (default: 50)
    - `offset`: Number of jobs to skip for pagination (default: 0)
    
    **Returns:**
    - List of transcription jobs for the specified case
    - Jobs ordered by creation date (newest first)
    - Includes job status, progress, and results
    """
    try:
        jobs = await audio_service.get_transcriptions_by_case_id(
            case_id=case_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Retrieved {len(jobs)} transcription jobs for case: {case_id}")
        return jobs
        
    except Exception as e:
        logger.error(f"Failed to get transcriptions for case {case_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transcriptions for case: {str(e)}"
        )


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


@router.get("/transcripts/case/{case_id}", 
            response_model=CaseTranscriptsResponse,
            summary="Get Transcripts by Case ID",
            description="Get all transcripts for a specific case ID. Returns only the transcript text from completed jobs. Optionally includes AI analysis of the transcripts.",
            tags=["Transcripts"])
async def get_transcripts_by_case_id(
    case_id: str,
    # current_user: dict = Depends(get_current_user),  # Disabled for testing
    status: Optional[str] = "completed",
    limit: int = 50,
    offset: int = 0,
    include_analysis: bool = False
):
    """
    Get transcripts for a specific case ID.
    
    Returns an array of transcripts from completed transcription jobs for the given case.
    Each transcript includes the job ID, transcript text, and timestamps.
    Optionally includes AI analysis of the transcripts to identify similarities, 
    contradictions, gray areas, and suggest follow-up questions.
    
    **Parameters:**
    - `case_id`: Case identifier
    - `status`: Job status filter (default: "completed")
    - `limit`: Maximum number of transcripts to return (default: 50)
    - `offset`: Number of transcripts to skip (default: 0)
    - `include_analysis`: Whether to include AI analysis (default: false)
    
    **Response with Analysis (`include_analysis=true`):**
    - `case_id`: Case identifier
    - `transcripts`: Array of transcript objects
    - `total_count`: Total number of transcripts found
    - `analysis`: AI analysis object containing:
      - `comparisons`: Topic-by-topic comparisons between transcripts
      - `followUpQuestions`: Specific questions for both witnesses
      - `analysis_timestamp`: When analysis was performed
    """
    try:
        # Get transcripts from audio service
        transcripts_data = await audio_service.get_transcripts_by_case_id(
            case_id=case_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        transcript_responses = []
        for transcript_data in transcripts_data:
            transcript_responses.append(TranscriptResponse(
                job_id=transcript_data['job_id'],
                transcript=transcript_data['transcript'],
                created_at=datetime.fromisoformat(transcript_data['created_at'].replace('Z', '+00:00')),
                completed_at=datetime.fromisoformat(transcript_data['completed_at'].replace('Z', '+00:00')) if transcript_data.get('completed_at') else None
            ))
        
        # Initialize response without analysis
        response = CaseTranscriptsResponse(
            case_id=case_id,
            transcripts=transcript_responses,
            total_count=len(transcript_responses)
        )
        
        # Perform AI analysis if requested and we have transcripts
        if include_analysis and transcript_responses:
            try:
                logger.info(f"Starting AI analysis for case {case_id} with {len(transcript_responses)} transcripts")
                
                # Extract transcript texts for analysis
                transcript_texts = [t.transcript for t in transcript_responses]
                
                # Perform OpenAI analysis
                analysis_result = await openai_service.analyze_transcripts(
                    transcripts=transcript_texts,
                    case_id=case_id
                )
                
                # Convert analysis result to Pydantic models
                comparisons = [
                    ComparisonItem(
                        topic=item['topic'],
                        witness1=item['witness1'],
                        witness2=item['witness2'],
                        status=item['status'],
                        details=item['details']
                    ) for item in analysis_result.get('comparisons', [])
                ]
                
                # Create analysis object
                analysis = TranscriptAnalysis(
                    comparisons=comparisons,
                    followUpQuestions=analysis_result.get('followUpQuestions', [])
                )
                
                # Add analysis to response
                response.analysis = analysis
                
                logger.info(f"Successfully completed AI analysis for case {case_id}")
                
            except Exception as analysis_error:
                logger.error(f"Failed to perform AI analysis for case {case_id}: {str(analysis_error)}")
                # Continue without analysis rather than failing the entire request
                logger.info(f"Returning transcripts without analysis for case {case_id}")
        
        logger.info(f"Retrieved {len(transcript_responses)} transcripts for case: {case_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to get transcripts for case {case_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transcripts for case: {str(e)}"
        )


@router.post("/transcripts/case/{case_id}/analyze", 
            response_model=TranscriptAnalysis,
            summary="Analyze Transcripts for Case",
            description="Perform AI analysis on all transcripts for a specific case to identify similarities, contradictions, gray areas, and suggest follow-up questions.",
            tags=["Transcripts"])
async def analyze_transcripts_for_case(
    case_id: str,
    # current_user: dict = Depends(get_current_user),  # Disabled for testing
    status: Optional[str] = "completed",
    limit: int = 50,
    offset: int = 0
):
    """
    Analyze transcripts for a specific case ID.
    
    Performs comprehensive AI analysis on all transcripts for the given case,
    identifying similarities, contradictions, gray areas, and suggesting follow-up questions.
    
    **Response Format:**
    - `comparisons`: Array of topic-by-topic comparisons between transcripts
      - `topic`: The topic being compared (e.g., "Time of incident", "Suspect description")
      - `witness1`: Statement from first witness/transcript
      - `witness2`: Statement from second witness/transcript
      - `status`: "similarity", "contradiction", or "gray_area"
      - `details`: Brief explanation of the comparison result
    - `followUpQuestions`: Array of specific questions that can be asked to both witnesses
    - `analysis_timestamp`: When the analysis was performed
    
    **Example Response:**
    ```json
    {
      "comparisons": [
        {
          "topic": "Time of incident",
          "witness1": "Around 2:30 AM",
          "witness2": "Approximately 2:15 AM",
          "status": "contradiction",
          "details": "15-minute discrepancy in reported time"
        }
      ],
      "followUpQuestions": [
        "What was the exact time of the incident?",
        "Can you provide more details about the suspect's appearance?"
      ],
      "analysis_timestamp": "2024-01-01T10:10:00Z"
    }
    ```
    """
    try:
        # Get transcripts from audio service
        transcripts_data = await audio_service.get_transcripts_by_case_id(
            case_id=case_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        if not transcripts_data:
            raise HTTPException(
                status_code=404,
                detail=f"No transcripts found for case {case_id}"
            )
        
        # Extract transcript texts for analysis
        transcript_texts = [transcript_data['transcript'] for transcript_data in transcripts_data]
        
        logger.info(f"Starting AI analysis for case {case_id} with {len(transcript_texts)} transcripts")
        
        # Perform OpenAI analysis
        analysis_result = await openai_service.analyze_transcripts(
            transcripts=transcript_texts,
            case_id=case_id
        )
        
        # Convert analysis result to Pydantic models
        comparisons = [
            ComparisonItem(
                topic=item['topic'],
                witness1=item['witness1'],
                witness2=item['witness2'],
                status=item['status'],
                details=item['details']
            ) for item in analysis_result.get('comparisons', [])
        ]
        
        # Create analysis object
        analysis = TranscriptAnalysis(
            comparisons=comparisons,
            followUpQuestions=analysis_result.get('followUpQuestions', [])
        )
        
        logger.info(f"Successfully completed AI analysis for case {case_id}")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze transcripts for case {case_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze transcripts for case: {str(e)}"
        )


@router.post("/debug/case/{case_id}", 
            summary="Debug Case Data",
            description="Debug endpoint to see what data exists for a case ID",
            tags=["Debug"])
async def debug_case_data(case_id: str):
    """Debug endpoint to see what data exists for a case ID."""
    try:
        # Get raw data from transcription_jobs table
        result = audio_service.client.table('transcription_jobs').select('*').eq('case_id', case_id).execute()
        
        return {
            "case_id": case_id,
            "total_jobs": len(result.data),
            "jobs": result.data
        }
    except Exception as e:
        return {
            "error": str(e),
            "case_id": case_id
        }
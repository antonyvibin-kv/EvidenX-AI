from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks, Form
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import time
import logging

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
    ComparisonItem,
    AudioAnalyzeRequest,
    AudioAnalyzeResponse,
    AudioInfo
)
from app.services.deepgram_service import DeepgramService
from app.services.audio_service import AudioService
from app.services.openai_service import OpenAIService
from app.core.config import settings
from app.api.auth import get_current_user

# No longer needed - using S3 for file storage

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
        
        # Get the actual audio file data from S3
        try:
            # Get audio data from S3
            audio_data = await audio_service.get_audio_data_from_s3(file_id)
            if not audio_data:
                raise Exception(f"Audio file not found in S3 for {file_id}. Please re-upload the file.")
            
            logger.info(f"Downloaded audio data: {len(audio_data)} bytes from S3")
            
            # Get audio file info for filename
            audio_file_info = await audio_service.get_audio_file_info(file_id)
            if not audio_file_info:
                raise Exception(f"Audio file {file_id} not found in database")
            
        except Exception as e:
            logger.error(f"Failed to get audio file data from S3: {e}")
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
        
        # Also save to media table if we have case information
        try:
            # Get job details to extract case_id if available
            job_details = await audio_service.get_transcription_job(job_id)
            if job_details and hasattr(job_details, 'case_id') and job_details.case_id:
                # Generate title and summary with OpenAI
                from app.services.openai_service import OpenAIService
                openai_service = OpenAIService()
                
                title, summary = await openai_service.generate_audio_title_and_summary(
                    transcript=result.transcript,
                    case_id=job_details.case_id
                )
                
                # Generate follow-up questions
                follow_up_questions = await openai_service.generate_follow_up_questions(
                    transcript=result.transcript,
                    case_id=job_details.case_id
                )
                
                # Get audio file info for URL
                audio_file_info = await audio_service.get_audio_file_info(file_id)
                audio_url = audio_file_info.get('s3_key', '') if audio_file_info else ''
                
                # Save to media table
                import uuid
                media_id = str(uuid.uuid4())
                await audio_service.save_audio_to_media_table(
                    media_id=media_id,
                    case_id=job_details.case_id,
                    url=audio_url,
                    transcript=result.transcript,
                    title=title,
                    summary=summary,
                    duration=result.duration,
                    speakers=len(result.speakers),
                    confidence=result.confidence,
                    follow_up_questions=follow_up_questions
                )
                logger.info(f"Audio saved to media table for case {job_details.case_id}")
        except Exception as e:
            logger.warning(f"Failed to save to media table: {e}")
        
        # No cleanup needed - files are stored in S3
        
        logger.info(f"Transcription completed for job: {job_id}")
        
    except Exception as e:
        logger.error(f"Transcription processing failed for job {job_id}: {str(e)}")
        await audio_service.update_transcription_job(
            job_id=job_id,
            status="failed",
            error_message=str(e)
        )
        
        # No cleanup needed - files are stored in S3


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


@router.post("/analyze", 
            response_model=AudioAnalyzeResponse,
            summary="Analyze Audio File",
            description="Analyze an audio file by URL and case ID. Returns transcript and follow-up questions. Checks for existing analysis first.",
            tags=["Audio Analysis"])
async def analyze_audio(
    request: AudioAnalyzeRequest,
    # current_user: dict = Depends(get_current_user)  # Disabled for testing
):
    """
    Analyze an audio file by URL and case ID.
    
    **Features:**
    - Checks for existing analysis first
    - Downloads audio from URL if needed
    - Performs Deepgram transcription
    - Generates follow-up questions with OpenAI
    - Stores results in database for future use
    
    **Parameters:**
    - `case_id`: Case identifier
    - `url`: URL of the audio file to analyze
    
    **Returns:**
    - URL of the analyzed audio file
    - Full transcript with speaker identification
    - AI-generated follow-up questions
    """
    try:
        # Check if analysis already exists in audio_files table
        existing_audio = await audio_service.get_audio_by_case_and_url(
            case_id=request.case_id,
            url=request.url
        )
        
        if existing_audio and existing_audio.get('audio_info'):
            # Return existing analysis
            audio_info = existing_audio['audio_info']
            logger.info(f"Returning existing analysis for case {request.case_id}")
            
            return AudioAnalyzeResponse(
                url=request.url,
                transcript=audio_info['transcript'],
                follow_up_questions=audio_info['follow_up_questions']
            )
        
        # Check if media record exists with this URL and case_id
        from app.core.database import supabase_client
        client = supabase_client.get_client()
        
        media_response = client.table("media").select("*").eq("case_id", request.case_id).execute()
        existing_media = None
        
        if media_response.data:
            for media in media_response.data:
                media_info = media.get("media_info", {})
                if media_info.get("url") == request.url:
                    existing_media = media
                    break
        
        if existing_media and existing_media.get("media_info", {}).get("transcript"):
            # Return existing media analysis
            media_info = existing_media["media_info"]
            logger.info(f"Returning existing media analysis for case {request.case_id}")
            
            return AudioAnalyzeResponse(
                url=request.url,
                transcript=media_info.get("transcript", ""),
                follow_up_questions=media_info.get("follow_up_questions", [])
            )
        
        # Download audio from URL
        logger.info(f"Downloading audio from URL: {request.url}")
        import requests as http_requests
        
        try:
            audio_response = http_requests.get(request.url, timeout=30)
            audio_response.raise_for_status()
            audio_data = audio_response.content
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to download audio from URL: {str(e)}"
            )
        
        # Extract filename from URL for proper format detection
        import urllib.parse
        parsed_url = urllib.parse.urlparse(request.url)
        filename = parsed_url.path.split('/')[-1] if parsed_url.path else "audio_file"
        
        # If no extension, try to detect from content type
        if '.' not in filename:
            content_type = audio_response.headers.get('content-type', '')
            if 'audio/mp3' in content_type:
                filename += '.mp3'
            elif 'audio/wav' in content_type:
                filename += '.wav'
            elif 'audio/mp4' in content_type or 'audio/m4a' in content_type:
                filename += '.m4a'
            else:
                filename += '.mp3'  # Default fallback
        
        # Validate audio with Deepgram
        deepgram = get_deepgram_service()
        validation_result = await deepgram.validate_audio_file(audio_data, filename)
        
        # Perform transcription
        logger.info("Starting Deepgram transcription...")
        transcription_request = AudioTranscriptionRequest(
            language="en",
            model="nova-2",
            diarize=True,
            punctuate=True,
            smart_format=True,
            case_id=request.case_id
        )
        
        # Configure speaker diarization
        diarization_config = SpeakerDiarizationConfig(
            min_speakers=2,
            max_speakers=10,
            speaker_change_sensitivity=0.5,
            enable_speaker_embedding=True
        )
        
        # Perform transcription
        transcription_result = await deepgram.transcribe_audio(
            audio_data=audio_data,
            filename=filename,
            request=transcription_request,
            diarization_config=diarization_config
        )
        
        # Generate follow-up questions with OpenAI
        logger.info("Generating follow-up questions with OpenAI...")
        try:
            openai_service = OpenAIService()
            follow_up_questions = await openai_service.generate_follow_up_questions(
                transcript=transcription_result.transcript,
                case_id=request.case_id
            )
        except Exception as e:
            logger.warning(f"Failed to generate follow-up questions: {e}")
            # Fallback to basic questions
            follow_up_questions = [
                "Can you provide more details about what happened?",
                "What was the sequence of events?",
                "Were there any other people present?",
                "What was the exact time this occurred?",
                "Can you describe the location in more detail?"
            ]
        
        # Generate title and summary with OpenAI
        logger.info("Generating title and summary with OpenAI...")
        try:
            title, summary = await openai_service.generate_audio_title_and_summary(
                transcript=transcription_result.transcript,
                case_id=request.case_id
            )
        except Exception as e:
            logger.warning(f"Failed to generate title and summary: {e}")
            title = "Audio Recording"
            summary = "Audio recording from investigation"
        
        # Create audio info object
        audio_info = AudioInfo(
            transcript=transcription_result.transcript,
            follow_up_questions=follow_up_questions
        )
        
        # Store in database (both audio_files and media tables)
        await audio_service.create_audio_analysis_record(
            case_id=request.case_id,
            url=request.url,
            audio_info=audio_info
        )
        
        # Update or create media record
        if existing_media:
            # Update existing media record with transcript and follow-up questions
            logger.info(f"Updating existing media record: {existing_media['id']}")
            
            # Update the media_info with transcript and follow-up questions
            updated_media_info = existing_media["media_info"].copy()
            updated_media_info.update({
                "transcript": transcription_result.transcript,
                "follow_up_questions": follow_up_questions,
                "duration": transcription_result.duration,
                "speakers": len(transcription_result.speakers),
                "confidence": int(transcription_result.confidence * 100) if transcription_result.confidence else None
            })
            
            # Update the media record
            update_result = client.table("media").update({
                "media_info": updated_media_info
            }).eq("id", existing_media["id"]).execute()
            
            if update_result.data:
                logger.info(f"Media record updated successfully: {existing_media['id']}")
            else:
                logger.error(f"Failed to update media record: {existing_media['id']}")
        else:
            # Create new media record
            import uuid
            media_id = str(uuid.uuid4())
            await audio_service.save_audio_to_media_table(
                media_id=media_id,
                case_id=request.case_id,
                url=request.url,
                transcript=transcription_result.transcript,
                title=title,
                summary=summary,
                duration=transcription_result.duration,
                speakers=len(transcription_result.speakers),
                confidence=transcription_result.confidence,
                follow_up_questions=follow_up_questions
            )
        
        logger.info(f"Audio analysis completed for case {request.case_id}")
        
        return AudioAnalyzeResponse(
            url=request.url,
            transcript=transcription_result.transcript,
            follow_up_questions=follow_up_questions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Audio analysis failed: {str(e)}"
        )
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from app.schemas.media import MediaResponse, MediaCreate, MediaUpdate
from app.schemas.audio import AudioUploadResponse
from app.core.database import supabase_client
from app.services.audio_service import AudioService
from app.services.s3_service import s3_service
from typing import Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[MediaResponse])
async def get_media():
    """Get all media."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("media").select("*").order("created_at", desc=True).execute()
        
        media_list = []
        for media_data in response.data:
            media_info = media_data["media_info"]
            media_list.append(MediaResponse(
                id=media_data["id"],
                caseId=media_data["case_id"],
                type=media_info["type"],
                url=media_info["url"],
                title=media_info["title"],
                description=media_info["description"],
                fileSize=media_info.get("fileSize"),
                format=media_info.get("format"),
                uploadDate=media_info.get("uploadDate"),
                duration=media_info.get("duration"),
                transcript=media_info.get("transcript"),
                speakers=media_info.get("speakers"),
                confidence=media_info.get("confidence"),
                resolution=media_info.get("resolution"),
                fps=media_info.get("fps"),
                thumbnail=media_info.get("thumbnail"),
                camera=media_info.get("camera"),
                location=media_info.get("location"),
                pages=media_info.get("pages"),
                author=media_info.get("author"),
                created_at=media_data.get("created_at"),
                updated_at=media_data.get("updated_at")
            ))
        
        return media_list
        
    except Exception as e:
        logger.error(f"Error fetching media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch media"
        )


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media_by_id(media_id: str):
    """Get a specific media by ID."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("media").select("*").eq("id", media_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        media_data = response.data[0]
        media_info = media_data["media_info"]
        
        return MediaResponse(
            id=media_data["id"],
            caseId=media_data["case_id"],
            type=media_info["type"],
            url=media_info["url"],
            title=media_info["title"],
            description=media_info["description"],
            fileSize=media_info.get("fileSize"),
            format=media_info.get("format"),
            uploadDate=media_info.get("uploadDate"),
            duration=media_info.get("duration"),
            transcript=media_info.get("transcript"),
            speakers=media_info.get("speakers"),
            confidence=media_info.get("confidence"),
            resolution=media_info.get("resolution"),
            fps=media_info.get("fps"),
            thumbnail=media_info.get("thumbnail"),
            camera=media_info.get("camera"),
            location=media_info.get("location"),
            pages=media_info.get("pages"),
            author=media_info.get("author"),
            created_at=media_data.get("created_at"),
            updated_at=media_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching media {media_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch media"
        )


@router.get("/case/{case_id}", response_model=list[MediaResponse])
async def get_media_by_case_id(case_id: str):
    """Get all media for a specific case."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("media").select("*").eq("case_id", case_id).order("created_at", desc=True).execute()
        
        media_list = []
        for media_data in response.data:
            media_info = media_data["media_info"]
            media_list.append(MediaResponse(
                id=media_data["id"],
                caseId=media_data["case_id"],
                type=media_info["type"],
                url=media_info["url"],
                title=media_info["title"],
                description=media_info["description"],
                fileSize=media_info.get("fileSize"),
                format=media_info.get("format"),
                uploadDate=media_info.get("uploadDate"),
                duration=media_info.get("duration"),
                transcript=media_info.get("transcript"),
                speakers=media_info.get("speakers"),
                confidence=media_info.get("confidence"),
                resolution=media_info.get("resolution"),
                fps=media_info.get("fps"),
                thumbnail=media_info.get("thumbnail"),
                camera=media_info.get("camera"),
                location=media_info.get("location"),
                pages=media_info.get("pages"),
                author=media_info.get("author"),
                created_at=media_data.get("created_at"),
                updated_at=media_data.get("updated_at")
            ))
        
        return media_list
        
    except Exception as e:
        logger.error(f"Error fetching media for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch media for case"
        )


@router.post("/", response_model=MediaResponse)
async def create_media(media_create: MediaCreate):
    """Create new media."""
    try:
        client = supabase_client.get_client()
        
        # Check if media with this ID already exists
        existing_response = client.table("media").select("id").eq("id", media_create.id).execute()
        if existing_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Media with this ID already exists"
            )
        
        # Check if the case exists
        case_response = client.table("cases").select("id").eq("id", media_create.case_id).execute()
        if not case_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case not found"
            )
        
        # Insert new media
        response = client.table("media").insert({
            "id": media_create.id,
            "case_id": media_create.case_id,
            "media_info": media_create.media_info.dict()
        }).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create media"
            )
        
        media_data = response.data[0]
        media_info = media_data["media_info"]
        
        return MediaResponse(
            id=media_data["id"],
            caseId=media_data["case_id"],
            type=media_info["type"],
            url=media_info["url"],
            title=media_info["title"],
            description=media_info["description"],
            fileSize=media_info.get("fileSize"),
            format=media_info.get("format"),
            uploadDate=media_info.get("uploadDate"),
            duration=media_info.get("duration"),
            transcript=media_info.get("transcript"),
            speakers=media_info.get("speakers"),
            confidence=media_info.get("confidence"),
            resolution=media_info.get("resolution"),
            fps=media_info.get("fps"),
            thumbnail=media_info.get("thumbnail"),
            camera=media_info.get("camera"),
            location=media_info.get("location"),
            pages=media_info.get("pages"),
            author=media_info.get("author"),
            created_at=media_data.get("created_at"),
            updated_at=media_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create media"
        )


@router.put("/{media_id}", response_model=MediaResponse)
async def update_media(
    media_id: str, 
    media_update: MediaUpdate
):
    """Update media."""
    try:
        client = supabase_client.get_client()
        
        # Check if media exists
        existing_response = client.table("media").select("*").eq("id", media_id).execute()
        if not existing_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        # Prepare update data
        update_data = {}
        if media_update.media_info:
            update_data["media_info"] = media_update.media_info.dict()
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update media
        response = client.table("media").update(update_data).eq("id", media_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        media_data = response.data[0]
        media_info = media_data["media_info"]
        
        return MediaResponse(
            id=media_data["id"],
            caseId=media_data["case_id"],
            type=media_info["type"],
            url=media_info["url"],
            title=media_info["title"],
            description=media_info["description"],
            fileSize=media_info.get("fileSize"),
            format=media_info.get("format"),
            uploadDate=media_info.get("uploadDate"),
            duration=media_info.get("duration"),
            transcript=media_info.get("transcript"),
            speakers=media_info.get("speakers"),
            confidence=media_info.get("confidence"),
            resolution=media_info.get("resolution"),
            fps=media_info.get("fps"),
            thumbnail=media_info.get("thumbnail"),
            camera=media_info.get("camera"),
            location=media_info.get("location"),
            pages=media_info.get("pages"),
            author=media_info.get("author"),
            created_at=media_data.get("created_at"),
            updated_at=media_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating media {media_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update media"
        )


@router.delete("/{media_id}")
async def delete_media(media_id: str):
    """Delete media."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("media").delete().eq("id", media_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        return {"message": "Media deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting media {media_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete media"
        )


@router.post("/upload", 
             response_model=AudioUploadResponse,
             summary="Upload Media File",
             description="Upload any media file (audio, video, image, document) with metadata. Supports various formats and automatically saves to media table.",
             tags=["Media Upload"])
async def upload_media_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Media file to upload (max 2GB recommended)"),
    case_id: str = Form(..., description="Case identifier"),
    title: Optional[str] = Form(None, description="Title for the media file"),
    description: Optional[str] = Form(None, description="Description of the media file"),
    type: str = Form(default="audio", description="Media type (audio, video, image, document)"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    location: Optional[str] = Form(None, description="Location where media was recorded"),
    author: Optional[str] = Form(None, description="Author/creator of the media"),
    # current_user: dict = Depends(get_current_user)  # Disabled for testing
):
    """
    Upload any media file with metadata.
    
    **Supported Media Types:**
    - Audio: WAV, MP3, MP4, M4A, FLAC, OGG, WEBM, AAC, M4B, 3GP, AMR
    - Video: MP4, AVI, MOV, WMV, FLV, WEBM, MKV
    - Images: JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP
    - Documents: PDF, DOC, DOCX, TXT, RTF
    
    **File Size:**
    - Maximum: 2GB
    - Recommended: Under 50MB for optimal performance
    
    **Returns:**
    - File ID for use in transcription requests (for audio)
    - Media ID for media table record
    - File metadata (size, type, etc.)
    """
    try:
        # Basic file validation
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="File must have a filename"
            )
        
        # Read file data
        file_data = await file.read()
        
        # Log file size for debugging
        file_size_mb = len(file_data) / (1024 * 1024)
        logger.info(f"Media file size: {file_size_mb:.2f} MB")
        
        if file_size_mb > 50:
            logger.warning(f"Large media file detected ({file_size_mb:.2f} MB). This may cause timeout issues.")
        
        # Upload to S3 and database using audio service (it handles S3 upload)
        audio_service = AudioService()
        upload_response = await audio_service.upload_audio_file(
            filename=file.filename,
            content_type=file.content_type,
            size=len(file_data),
            audio_data=file_data
        )
        
        # Generate S3 URL for the uploaded file
        s3_url = s3_service.generate_presigned_url(
            object_name=upload_response.s3_key,
            expiration=604800  # 7 days
        )
        
        # Save to media table
        try:
            media_id = str(uuid.uuid4())
            
            # Parse tags if provided
            tag_list = []
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            # Determine file format
            file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'
            
            # Prepare media info with proper S3 URL
            media_info = {
                "type": type,
                "url": s3_url or upload_response.s3_key,  # Use S3 URL if available, fallback to key
                "title": title or f"{type.title()} File - {file.filename}",
                "description": description or f"{type.title()} file: {file.filename}",
                "fileSize": f"{len(file_data) / (1024 * 1024):.2f} MB",
                "format": file_extension,
                "uploadDate": datetime.now().strftime("%Y-%m-%d"),
                "tags": tag_list,
                "location": location,
                "author": author
            }
            
            # Save to media table
            media_saved = await audio_service.save_audio_to_media_table(
                media_id=media_id,
                case_id=case_id,
                url=s3_url or upload_response.s3_key,  # Use S3 URL if available, fallback to key
                transcript="",  # Will be filled after transcription for audio
                title=media_info["title"],
                summary=media_info["description"],
                duration=None,
                speakers=None,
                confidence=None,
                follow_up_questions=[]
            )
            
            if media_saved:
                # Add media_id and S3 URL to response
                upload_response.media_id = media_id
                upload_response.upload_url = s3_url  # Add S3 URL to response
                logger.info(f"Media file uploaded and saved to media table: {file.filename} (media_id: {media_id})")
                logger.info(f"S3 URL generated: {s3_url}")
            else:
                logger.error(f"Failed to save to media table for file: {file.filename}")
                upload_response.media_id = None
            
        except Exception as e:
            logger.error(f"Failed to save to media table: {e}")
            upload_response.media_id = None
            # Continue with upload even if media save fails
        
        logger.info(f"Media file uploaded: {file.filename} ({len(file_data)} bytes)")
        
        return upload_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Media upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
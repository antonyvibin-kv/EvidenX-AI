from fastapi import APIRouter, HTTPException, status
from app.schemas.media import MediaResponse, MediaCreate, MediaUpdate
from app.core.database import supabase_client
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
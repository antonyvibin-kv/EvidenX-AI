from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from typing import List, Optional
from app.schemas.file import FileResponse, FileListResponse
from app.api.auth import get_current_user
from app.services.s3_service import s3_service
from app.core.database import supabase_client
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a file to S3 and save metadata to Supabase."""
    try:
        # Generate unique object name
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
        object_name = f"{current_user['id']}/{uuid.uuid4()}.{file_extension}"
        
        # Upload to S3
        upload_result = await s3_service.upload_file(
            file_obj=file.file,
            object_name=object_name,
            content_type=file.content_type
        )
        
        if not upload_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {upload_result.get('error', 'Unknown error')}"
            )
        
        # Save file metadata to Supabase
        client = supabase_client.get_client()
        file_data = {
            "id": str(uuid.uuid4()),
            "filename": file.filename,
            "object_name": object_name,
            "content_type": file.content_type,
            "size": file.size,
            "url": upload_result["url"],
            "bucket": upload_result["bucket"],
            "user_id": current_user["id"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = client.table("files").insert(file_data).execute()
        
        if not response.data:
            # If database insert fails, clean up S3 file
            await s3_service.delete_file(object_name)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file metadata"
            )
        
        return FileResponse(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )


@router.get("/", response_model=FileListResponse)
async def get_files(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get user's files with pagination."""
    try:
        client = supabase_client.get_client()
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get files for current user
        response = client.table("files").select("*").eq("user_id", current_user["id"]).range(offset, offset + per_page - 1).execute()
        
        # Get total count
        count_response = client.table("files").select("id", count="exact").eq("user_id", current_user["id"]).execute()
        total = count_response.count or 0
        
        files = [FileResponse(**file_data) for file_data in response.data]
        
        return FileListResponse(
            files=files,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Error fetching files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch files"
        )


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific file by ID."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("files").select("*").eq("id", file_id).eq("user_id", current_user["id"]).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch file"
        )


@router.get("/{file_id}/download")
async def download_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """Download a file from S3."""
    try:
        client = supabase_client.get_client()
        
        # Get file metadata
        response = client.table("files").select("*").eq("id", file_id).eq("user_id", current_user["id"]).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        file_data = response.data[0]
        
        # Download file from S3
        file_content = await s3_service.download_file(file_data["object_name"])
        
        if file_content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in storage"
            )
        
        # Generate presigned URL for download
        download_url = s3_service.generate_presigned_url(
            file_data["object_name"],
            expiration=3600  # 1 hour
        )
        
        return {
            "download_url": download_url,
            "filename": file_data["filename"],
            "content_type": file_data["content_type"],
            "size": file_data["size"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )


@router.delete("/{file_id}")
async def delete_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a file from both S3 and database."""
    try:
        client = supabase_client.get_client()
        
        # Get file metadata
        response = client.table("files").select("*").eq("id", file_id).eq("user_id", current_user["id"]).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        file_data = response.data[0]
        
        # Delete from S3
        s3_success = await s3_service.delete_file(file_data["object_name"])
        
        # Delete from database
        client.table("files").delete().eq("id", file_id).execute()
        
        if not s3_success:
            logger.warning(f"File {file_id} deleted from database but not from S3")
        
        return {"message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )


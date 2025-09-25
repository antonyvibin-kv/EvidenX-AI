from fastapi import APIRouter, HTTPException, status
from app.schemas.case import CaseResponse, CaseCreate, CaseUpdate, MediaInfo, EvidenceInfo, AudioComparisonInfo
from app.core.database import supabase_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_media_for_case(case_id: str) -> list[MediaInfo]:
    """Get media information for a specific case."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("media").select("*").eq("case_id", case_id).order("created_at", desc=True).execute()
        
        media_list = []
        for media_data in response.data:
            media_info = media_data["media_info"]
            
            # Convert duration to string if it's a number
            duration = media_info.get("duration")
            if duration is not None and isinstance(duration, (int, float)):
                duration = str(duration)
            
            media_list.append(MediaInfo(
                id=media_data["id"],
                type=media_info["type"],
                url=media_info["url"],
                title=media_info["title"],
                description=media_info["description"],
                fileSize=media_info.get("fileSize"),
                format=media_info.get("format"),
                uploadDate=media_info.get("uploadDate"),
                duration=duration,
                transcript=media_info.get("transcript"),
                speakers=media_info.get("speakers"),
                confidence=media_info.get("confidence"),
                resolution=media_info.get("resolution"),
                fps=media_info.get("fps"),
                thumbnail=media_info.get("thumbnail"),
                camera=media_info.get("camera"),
                location=media_info.get("location"),
                pages=media_info.get("pages"),
                author=media_info.get("author")
            ))
        
        return media_list
        
    except Exception as e:
        logger.error(f"Error fetching media for case {case_id}: {e}")
        return []


async def get_evidence_for_case(case_id: str) -> list[EvidenceInfo]:
    """Get evidence information for a specific case."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("evidence").select("*").eq("case_id", case_id).order("created_at", desc=True).execute()
        
        evidence_list = []
        for evidence_data in response.data:
            evidence_info = evidence_data["evidence_info"]
            evidence_list.append(EvidenceInfo(
                id=evidence_data["id"],
                caseId=evidence_data["case_id"],
                type=evidence_info["type"],
                name=evidence_info["name"],
                description=evidence_info["description"],
                uploadDate=evidence_info["uploadDate"],
                fileSize=evidence_info["fileSize"],
                tags=evidence_info["tags"],
                duration=evidence_info.get("duration"),
                thumbnail=evidence_info.get("thumbnail"),
                created_at=evidence_data.get("created_at"),
                updated_at=evidence_data.get("updated_at")
            ))
        
        return evidence_list
        
    except Exception as e:
        logger.error(f"Error fetching evidence for case {case_id}: {e}")
        return []


async def get_audio_comparisons_for_case(case_id: str) -> list[AudioComparisonInfo]:
    """Get audio comparison information for a specific case."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("case_audio_comparison").select("*").eq("case_id", case_id).order("created_at", desc=True).execute()
        
        comparisons_list = []
        for comparison_data in response.data:
            comparisons_list.append(AudioComparisonInfo(
                id=comparison_data["id"],
                caseId=comparison_data["case_id"],
                mediaId1=comparison_data["media_id1"],
                mediaId2=comparison_data["media_id2"],
                witnesses=comparison_data["witnesses"],
                detailedAnalysis=comparison_data["detailed_analysis"],
                created_at=comparison_data.get("created_at"),
                updated_at=comparison_data.get("updated_at")
            ))
        
        return comparisons_list
        
    except Exception as e:
        logger.error(f"Error fetching audio comparisons for case {case_id}: {e}")
        return []


@router.get("/", response_model=list[CaseResponse])
async def get_cases():
    """Get all cases."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("cases").select("*").execute()
        
        cases = []
        for case_data in response.data:
            case_info = case_data["case_info"]
            
            # Get media, evidence, and audio comparisons for this case
            media = await get_media_for_case(case_data["id"])
            evidence = await get_evidence_for_case(case_data["id"])
            audio_comparisons = await get_audio_comparisons_for_case(case_data["id"])
            
            cases.append(CaseResponse(
                id=case_data["id"],
                firNumber=case_info["firNumber"],
                title=case_info["title"],
                summary=case_info["summary"],
                petitioner=case_info["petitioner"],
                accused=case_info["accused"],
                investigatingOfficer=case_info["investigatingOfficer"],
                registeredDate=case_info["registeredDate"],
                status=case_info["status"],
                visibility=case_info["visibility"],
                location=case_info["location"],
                media=media,
                evidence=evidence,
                audioComparisons=audio_comparisons,
                created_at=case_data.get("created_at"),
                updated_at=case_data.get("updated_at")
            ))
        
        return cases
        
    except Exception as e:
        logger.error(f"Error fetching cases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch cases"
        )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case_by_id(case_id: str):
    """Get a specific case by ID."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("cases").select("*").eq("id", case_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        case_data = response.data[0]
        case_info = case_data["case_info"]
        
        # Get media, evidence, and audio comparisons for this case
        media = await get_media_for_case(case_data["id"])
        evidence = await get_evidence_for_case(case_data["id"])
        audio_comparisons = await get_audio_comparisons_for_case(case_data["id"])
        
        return CaseResponse(
            id=case_data["id"],
            firNumber=case_info["firNumber"],
            title=case_info["title"],
            summary=case_info["summary"],
            petitioner=case_info["petitioner"],
            accused=case_info["accused"],
            investigatingOfficer=case_info["investigatingOfficer"],
            registeredDate=case_info["registeredDate"],
            status=case_info["status"],
            visibility=case_info["visibility"],
            location=case_info["location"],
            media=media,
            evidence=evidence,
            audioComparisons=audio_comparisons,
            created_at=case_data.get("created_at"),
            updated_at=case_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch case"
        )


@router.post("/", response_model=CaseResponse)
async def create_case(case_create: CaseCreate):
    """Create a new case."""
    try:
        client = supabase_client.get_client()
        
        # Check if case with this ID already exists
        existing_response = client.table("cases").select("id").eq("id", case_create.id).execute()
        if existing_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case with this ID already exists"
            )
        
        # Insert new case
        response = client.table("cases").insert({
            "id": case_create.id,
            "case_info": case_create.case_info.dict()
        }).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create case"
            )
        
        case_data = response.data[0]
        case_info = case_data["case_info"]
        
        return CaseResponse(
            id=case_data["id"],
            firNumber=case_info["firNumber"],
            title=case_info["title"],
            summary=case_info["summary"],
            petitioner=case_info["petitioner"],
            accused=case_info["accused"],
            investigatingOfficer=case_info["investigatingOfficer"],
            registeredDate=case_info["registeredDate"],
            status=case_info["status"],
            visibility=case_info["visibility"],
            location=case_info["location"],
            created_at=case_data.get("created_at"),
            updated_at=case_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create case"
        )


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str, 
    case_update: CaseUpdate
):
    """Update a case."""
    try:
        client = supabase_client.get_client()
        
        # Check if case exists
        existing_response = client.table("cases").select("*").eq("id", case_id).execute()
        if not existing_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Prepare update data
        update_data = {}
        if case_update.case_info:
            update_data["case_info"] = case_update.case_info.dict()
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update case
        response = client.table("cases").update(update_data).eq("id", case_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        case_data = response.data[0]
        case_info = case_data["case_info"]
        
        return CaseResponse(
            id=case_data["id"],
            firNumber=case_info["firNumber"],
            title=case_info["title"],
            summary=case_info["summary"],
            petitioner=case_info["petitioner"],
            accused=case_info["accused"],
            investigatingOfficer=case_info["investigatingOfficer"],
            registeredDate=case_info["registeredDate"],
            status=case_info["status"],
            visibility=case_info["visibility"],
            location=case_info["location"],
            created_at=case_data.get("created_at"),
            updated_at=case_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update case"
        )


@router.delete("/{case_id}")
async def delete_case(case_id: str):
    """Delete a case."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("cases").delete().eq("id", case_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        return {"message": "Case deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete case"
        )
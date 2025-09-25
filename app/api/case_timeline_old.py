from fastapi import APIRouter, HTTPException, status
from app.schemas.case_timeline import CaseTimelineResponse, CaseTimelineCreate, CaseTimelineUpdate
from app.core.database import supabase_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[CaseTimelineResponse])
async def get_timeline():
    """Get all timeline entries."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("case_timeline").select("*").order("timeline_info->timestamp").execute()
        
        timeline_list = []
        for timeline_data in response.data:
            timeline_info = timeline_data["timeline_info"]
            timeline_list.append(CaseTimelineResponse(
                id=timeline_data["id"],
                caseId=timeline_data["case_id"],
                timestamp=timeline_info["timestamp"],
                title=timeline_info["title"],
                description=timeline_info["description"],
                source=timeline_info["source"],
                evidenceId=timeline_info.get("evidenceId"),
                evidenceType=timeline_info.get("evidenceType"),
                created_at=timeline_data.get("created_at"),
                updated_at=timeline_data.get("updated_at")
            ))
        
        return timeline_list
        
    except Exception as e:
        logger.error(f"Error fetching timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch timeline"
        )


@router.get("/{timeline_id}", response_model=CaseTimelineResponse)
async def get_timeline_by_id(timeline_id: str):
    """Get a specific timeline entry by ID."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("case_timeline").select("*").eq("id", timeline_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline entry not found"
            )
        
        timeline_data = response.data[0]
        timeline_info = timeline_data["timeline_info"]
        
        return CaseTimelineResponse(
            id=timeline_data["id"],
            caseId=timeline_data["case_id"],
            timestamp=timeline_info["timestamp"],
            title=timeline_info["title"],
            description=timeline_info["description"],
            source=timeline_info["source"],
            evidenceId=timeline_info.get("evidenceId"),
            evidenceType=timeline_info.get("evidenceType"),
            created_at=timeline_data.get("created_at"),
            updated_at=timeline_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timeline entry {timeline_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch timeline entry"
        )


@router.get("/case/{case_id}", response_model=list[CaseTimelineResponse])
async def get_timeline_by_case_id(case_id: str):
    """Get all timeline entries for a specific case."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("case_timeline").select("*").eq("case_id", case_id).order("timeline_info->timestamp").execute()
        
        timeline_list = []
        for timeline_data in response.data:
            timeline_info = timeline_data["timeline_info"]
            timeline_list.append(CaseTimelineResponse(
                id=timeline_data["id"],
                caseId=timeline_data["case_id"],
                timestamp=timeline_info["timestamp"],
                title=timeline_info["title"],
                description=timeline_info["description"],
                source=timeline_info["source"],
                evidenceId=timeline_info.get("evidenceId"),
                evidenceType=timeline_info.get("evidenceType"),
                created_at=timeline_data.get("created_at"),
                updated_at=timeline_data.get("updated_at")
            ))
        
        return timeline_list
        
    except Exception as e:
        logger.error(f"Error fetching timeline for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch timeline for case"
        )


@router.post("/", response_model=CaseTimelineResponse)
async def create_timeline_entry(timeline_create: CaseTimelineCreate):
    """Create new timeline entry."""
    try:
        client = supabase_client.get_client()
        
        # Check if timeline entry with this ID already exists
        existing_response = client.table("case_timeline").select("id").eq("id", timeline_create.id).execute()
        if existing_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timeline entry with this ID already exists"
            )
        
        # Check if the case exists
        case_response = client.table("cases").select("id").eq("id", timeline_create.case_id).execute()
        if not case_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case not found"
            )
        
        # Insert new timeline entry
        response = client.table("case_timeline").insert({
            "id": timeline_create.id,
            "case_id": timeline_create.case_id,
            "timeline_info": timeline_create.timeline_info.dict()
        }).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create timeline entry"
            )
        
        timeline_data = response.data[0]
        timeline_info = timeline_data["timeline_info"]
        
        return CaseTimelineResponse(
            id=timeline_data["id"],
            caseId=timeline_data["case_id"],
            timestamp=timeline_info["timestamp"],
            title=timeline_info["title"],
            description=timeline_info["description"],
            source=timeline_info["source"],
            evidenceId=timeline_info.get("evidenceId"),
            evidenceType=timeline_info.get("evidenceType"),
            created_at=timeline_data.get("created_at"),
            updated_at=timeline_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating timeline entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create timeline entry"
        )


@router.put("/{timeline_id}", response_model=CaseTimelineResponse)
async def update_timeline_entry(
    timeline_id: str, 
    timeline_update: CaseTimelineUpdate
):
    """Update timeline entry."""
    try:
        client = supabase_client.get_client()
        
        # Check if timeline entry exists
        existing_response = client.table("case_timeline").select("*").eq("id", timeline_id).execute()
        if not existing_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline entry not found"
            )
        
        # Prepare update data
        update_data = {}
        if timeline_update.timeline_info:
            update_data["timeline_info"] = timeline_update.timeline_info.dict()
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update timeline entry
        response = client.table("case_timeline").update(update_data).eq("id", timeline_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline entry not found"
            )
        
        timeline_data = response.data[0]
        timeline_info = timeline_data["timeline_info"]
        
        return CaseTimelineResponse(
            id=timeline_data["id"],
            caseId=timeline_data["case_id"],
            timestamp=timeline_info["timestamp"],
            title=timeline_info["title"],
            description=timeline_info["description"],
            source=timeline_info["source"],
            evidenceId=timeline_info.get("evidenceId"),
            evidenceType=timeline_info.get("evidenceType"),
            created_at=timeline_data.get("created_at"),
            updated_at=timeline_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating timeline entry {timeline_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update timeline entry"
        )


@router.delete("/{timeline_id}")
async def delete_timeline_entry(timeline_id: str):
    """Delete timeline entry."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("case_timeline").delete().eq("id", timeline_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline entry not found"
            )
        
        return {"message": "Timeline entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting timeline entry {timeline_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete timeline entry"
        )
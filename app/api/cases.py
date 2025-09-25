from fastapi import APIRouter, HTTPException, status
from app.schemas.case import CaseResponse, CaseCreate, CaseUpdate
from app.core.database import supabase_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[CaseResponse])
async def get_cases():
    """Get all cases."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("cases").select("*").execute()
        
        cases = []
        for case_data in response.data:
            case_info = case_data["case_info"]
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
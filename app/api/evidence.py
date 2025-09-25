from fastapi import APIRouter, HTTPException, status
from app.schemas.evidence import EvidenceResponse, EvidenceCreate, EvidenceUpdate
from app.core.database import supabase_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[EvidenceResponse])
async def get_evidence():
    """Get all evidence."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("evidence").select("*").execute()
        
        evidence_list = []
        for evidence_data in response.data:
            evidence_info = evidence_data["evidence_info"]
            evidence_list.append(EvidenceResponse(
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
        logger.error(f"Error fetching evidence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch evidence"
        )


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence_by_id(evidence_id: str):
    """Get a specific evidence by ID."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("evidence").select("*").eq("id", evidence_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence not found"
            )
        
        evidence_data = response.data[0]
        evidence_info = evidence_data["evidence_info"]
        
        return EvidenceResponse(
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
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching evidence {evidence_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch evidence"
        )


@router.get("/case/{case_id}", response_model=list[EvidenceResponse])
async def get_evidence_by_case_id(case_id: str):
    """Get all evidence for a specific case."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("evidence").select("*").eq("case_id", case_id).execute()
        
        evidence_list = []
        for evidence_data in response.data:
            evidence_info = evidence_data["evidence_info"]
            evidence_list.append(EvidenceResponse(
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch evidence for case"
        )


@router.post("/", response_model=EvidenceResponse)
async def create_evidence(evidence_create: EvidenceCreate):
    """Create new evidence."""
    try:
        client = supabase_client.get_client()
        
        # Check if evidence with this ID already exists
        existing_response = client.table("evidence").select("id").eq("id", evidence_create.id).execute()
        if existing_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Evidence with this ID already exists"
            )
        
        # Check if the case exists
        case_response = client.table("cases").select("id").eq("id", evidence_create.case_id).execute()
        if not case_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case not found"
            )
        
        # Insert new evidence
        response = client.table("evidence").insert({
            "id": evidence_create.id,
            "case_id": evidence_create.case_id,
            "evidence_info": evidence_create.evidence_info.dict()
        }).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create evidence"
            )
        
        evidence_data = response.data[0]
        evidence_info = evidence_data["evidence_info"]
        
        return EvidenceResponse(
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
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating evidence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create evidence"
        )


@router.put("/{evidence_id}", response_model=EvidenceResponse)
async def update_evidence(
    evidence_id: str, 
    evidence_update: EvidenceUpdate
):
    """Update evidence."""
    try:
        client = supabase_client.get_client()
        
        # Check if evidence exists
        existing_response = client.table("evidence").select("*").eq("id", evidence_id).execute()
        if not existing_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence not found"
            )
        
        # Prepare update data
        update_data = {}
        if evidence_update.evidence_info:
            update_data["evidence_info"] = evidence_update.evidence_info.dict()
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update evidence
        response = client.table("evidence").update(update_data).eq("id", evidence_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence not found"
            )
        
        evidence_data = response.data[0]
        evidence_info = evidence_data["evidence_info"]
        
        return EvidenceResponse(
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
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating evidence {evidence_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update evidence"
        )


@router.delete("/{evidence_id}")
async def delete_evidence(evidence_id: str):
    """Delete evidence."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("evidence").delete().eq("id", evidence_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence not found"
            )
        
        return {"message": "Evidence deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting evidence {evidence_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete evidence"
        )
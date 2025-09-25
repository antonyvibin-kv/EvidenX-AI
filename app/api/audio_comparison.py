from fastapi import APIRouter, HTTPException, status
from app.schemas.audio_comparison import AudioComparisonResponse, AudioComparisonRequest, AudioComparisonWitness, DetailedAnalysis
from app.core.database import supabase_client
from app.services.openai_service import OpenAIService
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize OpenAI service
openai_service = OpenAIService()


@router.post("/compare", 
            response_model=AudioComparisonResponse,
            summary="Compare Two Audio Files",
            description="Compare two audio files from a case and generate detailed analysis including contradictions, similarities, and gray areas.",
            tags=["Audio Comparison"])
async def compare_audio_files(request: AudioComparisonRequest):
    """
    Compare two audio files and generate detailed analysis.
    
    **Features:**
    - Fetches transcripts from media table
    - Generates AI-powered comparison analysis
    - Identifies contradictions, similarities, and gray areas
    - Saves analysis to database for future reference
    
    **Parameters:**
    - `caseId`: Case identifier
    - `mediaId1`: First media file ID
    - `mediaId2`: Second media file ID
    
    **Returns:**
    - Detailed witness analysis
    - Topic-by-topic comparison
    - Contradictions and similarities
    """
    try:
        client = supabase_client.get_client()
        
        # Check if comparison already exists
        existing_comparison = client.table("case_audio_comparison").select("*").eq("case_id", request.caseId).eq("media_id1", request.mediaId1).eq("media_id2", request.mediaId2).execute()
        
        if existing_comparison.data:
            logger.info(f"Returning existing comparison for case {request.caseId}")
            comparison_data = existing_comparison.data[0]
            
            return AudioComparisonResponse(
                id=comparison_data["id"],
                caseId=comparison_data["case_id"],
                mediaId1=comparison_data["media_id1"],
                mediaId2=comparison_data["media_id2"],
                witnesses=comparison_data["witnesses"],
                detailedAnalysis=comparison_data["detailed_analysis"],
                created_at=comparison_data.get("created_at"),
                updated_at=comparison_data.get("updated_at")
            )
        
        # Fetch media records
        media1_response = client.table("media").select("*").eq("id", request.mediaId1).execute()
        media2_response = client.table("media").select("*").eq("id", request.mediaId2).execute()
        
        if not media1_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Media file {request.mediaId1} not found"
            )
        
        if not media2_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Media file {request.mediaId2} not found"
            )
        
        media1 = media1_response.data[0]
        media2 = media2_response.data[0]
        
        # Extract transcripts
        transcript1 = media1["media_info"].get("transcript", "")
        transcript2 = media2["media_info"].get("transcript", "")
        
        if not transcript1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No transcript available for media {request.mediaId1}"
            )
        
        if not transcript2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No transcript available for media {request.mediaId2}"
            )
        
        # Generate witness names from media titles
        witness1_name = media1["media_info"].get("title", "Witness 1")
        witness2_name = media2["media_info"].get("title", "Witness 2")
        
        # Generate AI analysis
        logger.info(f"Generating AI analysis for audio comparison...")
        witnesses_analysis, detailed_analysis = await openai_service.analyze_audio_comparison(
            transcript1=transcript1,
            transcript2=transcript2,
            witness1_name=witness1_name,
            witness2_name=witness2_name
        )
        
        # Update witness analysis with correct media IDs
        for witness in witnesses_analysis:
            if witness["audioId"] == "media1":
                witness["audioId"] = request.mediaId1
            elif witness["audioId"] == "media2":
                witness["audioId"] = request.mediaId2
        
        # Save to database
        comparison_id = str(uuid.uuid4())
        insert_data = {
            "id": comparison_id,
            "case_id": request.caseId,
            "media_id1": request.mediaId1,
            "media_id2": request.mediaId2,
            "witnesses": witnesses_analysis,
            "detailed_analysis": detailed_analysis
        }
        
        result = client.table("case_audio_comparison").insert(insert_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save audio comparison"
            )
        
        logger.info(f"Audio comparison completed for case {request.caseId}")
        
        return AudioComparisonResponse(
            id=comparison_id,
            caseId=request.caseId,
            mediaId1=request.mediaId1,
            mediaId2=request.mediaId2,
            witnesses=witnesses_analysis,
            detailedAnalysis=detailed_analysis,
            created_at=result.data[0].get("created_at"),
            updated_at=result.data[0].get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio comparison failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio comparison failed: {str(e)}"
        )


@router.get("/case/{case_id}", 
           response_model=list[AudioComparisonResponse],
           summary="Get Audio Comparisons for Case",
           description="Get all audio comparisons for a specific case.",
           tags=["Audio Comparison"])
async def get_audio_comparisons_for_case(case_id: str):
    """Get all audio comparisons for a specific case."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("case_audio_comparison").select("*").eq("case_id", case_id).order("created_at", desc=True).execute()
        
        comparisons = []
        for comparison_data in response.data:
            comparisons.append(AudioComparisonResponse(
                id=comparison_data["id"],
                caseId=comparison_data["case_id"],
                mediaId1=comparison_data["media_id1"],
                mediaId2=comparison_data["media_id2"],
                witnesses=comparison_data["witnesses"],
                detailedAnalysis=comparison_data["detailed_analysis"],
                created_at=comparison_data.get("created_at"),
                updated_at=comparison_data.get("updated_at")
            ))
        
        return comparisons
        
    except Exception as e:
        logger.error(f"Error fetching audio comparisons for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch audio comparisons"
        )


@router.get("/{comparison_id}", 
           response_model=AudioComparisonResponse,
           summary="Get Audio Comparison by ID",
           description="Get a specific audio comparison by ID.",
           tags=["Audio Comparison"])
async def get_audio_comparison_by_id(comparison_id: str):
    """Get a specific audio comparison by ID."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("case_audio_comparison").select("*").eq("id", comparison_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio comparison not found"
            )
        
        comparison_data = response.data[0]
        
        return AudioComparisonResponse(
            id=comparison_data["id"],
            caseId=comparison_data["case_id"],
            mediaId1=comparison_data["media_id1"],
            mediaId2=comparison_data["media_id2"],
            witnesses=comparison_data["witnesses"],
            detailedAnalysis=comparison_data["detailed_analysis"],
            created_at=comparison_data.get("created_at"),
            updated_at=comparison_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching audio comparison {comparison_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch audio comparison"
        )
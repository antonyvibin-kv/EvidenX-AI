from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user import UserResponse, UserUpdate
from app.api.auth import get_current_user
from app.core.database import supabase_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[UserResponse])
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users (admin only - implement role checking as needed)."""
    try:
        client = supabase_client.get_client()
        
        # This is a simple example - in production, you'd want proper role-based access control
        response = client.table("users").select("*").execute()
        
        users = []
        for user_data in response.data:
            users.append(UserResponse(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data.get("full_name"),
                created_at=user_data["created_at"],
                updated_at=user_data.get("updated_at")
            ))
        
        return users
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific user by ID."""
    try:
        client = supabase_client.get_client()
        
        response = client.table("users").select("*").eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = response.data[0]
        return UserResponse(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data.get("full_name"),
            created_at=user_data["created_at"],
            updated_at=user_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, 
    user_update: UserUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Update a user (users can only update their own profile)."""
    try:
        # Check if user is updating their own profile
        if current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this user"
            )
        
        client = supabase_client.get_client()
        
        # Prepare update data
        update_data = {}
        if user_update.email:
            update_data["email"] = user_update.email
        if user_update.full_name:
            update_data["full_name"] = user_update.full_name
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        response = client.table("users").update(update_data).eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = response.data[0]
        return UserResponse(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data.get("full_name"),
            created_at=user_data["created_at"],
            updated_at=user_data.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a user (users can only delete their own account)."""
    try:
        # Check if user is deleting their own account
        if current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this user"
            )
        
        client = supabase_client.get_client()
        
        response = client.table("users").delete().eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


from typing import Optional, Dict, Any
from app.core.database import supabase_client
import logging

logger = logging.getLogger(__name__)


class UserService:
    """User service for user-related operations."""
    
    def __init__(self):
        self.client = supabase_client.get_client()
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID from Supabase."""
        try:
            response = self.client.table("users").select("*").eq("id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email from Supabase."""
        try:
            response = self.client.table("users").select("*").eq("email", email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {e}")
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user in Supabase."""
        try:
            response = self.client.table("users").insert(user_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user in Supabase."""
        try:
            response = self.client.table("users").update(update_data).eq("id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return None
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user from Supabase."""
        try:
            response = self.client.table("users").delete().eq("id", user_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False


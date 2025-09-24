import os
from supabase import create_client, Client
from app.core.config import settings


class SupabaseClient:
    """Supabase client wrapper for database operations."""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        self.service_client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
    
    def get_client(self) -> Client:
        """Get the regular Supabase client."""
        return self.client
    
    def get_service_client(self) -> Client:
        """Get the service role Supabase client (for admin operations)."""
        return self.service_client


# Global Supabase client instance
supabase_client = SupabaseClient()


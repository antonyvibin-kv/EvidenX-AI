from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.core.database import supabase_client
from app.core.security import create_access_token, verify_password, get_password_hash
from app.services.user_service import UserService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()
user_service = UserService()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user."""
    try:
        # Verify the token with Supabase
        client = supabase_client.get_client()
        user = client.auth.get_user(credentials.credentials)
        return user.user.model_dump()
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Register a new user."""
    try:
        client = supabase_client.get_client()
        
        # Create user with Supabase Auth
        response = client.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name
                }
            }
        })
        
        if response.user:
            return UserResponse(
                id=response.user.id,
                email=response.user.email,
                full_name=user_data.full_name,
                created_at=response.user.created_at
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Login user and return access token."""
    try:
        client = supabase_client.get_client()
        
        # Authenticate with Supabase
        response = client.auth.sign_in_with_password({
            "email": user_credentials.email,
            "password": user_credentials.password
        })
        
        if response.user and response.session:
            return Token(
                access_token=response.session.access_token,
                token_type="bearer"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout current user."""
    try:
        client = supabase_client.get_client()
        client.auth.sign_out()
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("user_metadata", {}).get("full_name"),
        created_at=current_user["created_at"]
    )


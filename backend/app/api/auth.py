"""Authentication API endpoints."""
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session


router = APIRouter(prefix="/auth", tags=["authentication"])


# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_info: dict


class TokenPayload(BaseModel):
    """JWT token payload model."""
    sub: str  # Subject (user ID)
    username: str
    role: str
    exp: int  # Expiration time
    iat: int  # Issued at


class UserInfo(BaseModel):
    """User information model."""
    username: str
    role: str
    permissions: list[str]


# Demo user credentials (in production, these would be validated against Keycloak)
DEMO_USERS = {
    "admin": {
        "password": "admin123",  # Demo password only - change in production
        "role": "admin",
        "permissions": ["skills:read", "skills:write", "analyze:read", "config:generate"]
    },
    "operator": {
        "password": "operator123",  # Demo password only - change in production
        "role": "operator",
        "permissions": ["skills:read", "analyze:read", "config:generate"]
    },
    "viewer": {
        "password": "viewer123",  # Demo password only - change in production
        "role": "viewer",
        "permissions": ["skills:read", "analyze:read"]
    }
}


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    
    to_encode = data.copy()
    
    # Set expiration time (1 hour by default)
    expire = datetime.now(UTC) + timedelta(minutes=settings.token_expiry_minutes)
    to_encode.update({"exp": expire.timestamp()})
    
    # Encode the token
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.token_secret_key, 
        algorithm=settings.token_algorithm
    )
    
    return encoded_jwt


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """Login and get access token.
    
    In production, this would validate credentials against Keycloak.
    For demo mode, it uses hardcoded credentials.
    """
    settings = get_settings()
    
    # Check if demo mode is enabled
    if settings.demo_mode:
        # Demo mode authentication
        user_info = DEMO_USERS.get(login_data.username)
        if not user_info or user_info["password"] != login_data.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        
        # Create token payload
        token_data = {
            "sub": login_data.username,
            "username": login_data.username,
            "role": user_info["role"]
        }
        
        # Create token
        access_token = create_access_token(token_data)
        
        # Calculate expiration
        expire = datetime.now(UTC) + timedelta(minutes=settings.token_expiry_minutes)
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_at=expire,
            user_info={
                "username": login_data.username,
                "role": user_info["role"],
                "permissions": user_info["permissions"]
            }
        )
    else:
        # In production, validate against Keycloak
        # This is a placeholder for Keycloak integration
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Keycloak integration required for production use",
        )


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """Logout and invalidate token."""
    # In production, this would invalidate the token in Keycloak
    # For now, we just accept the logout request
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> UserInfo:
    """Get current user information from token."""
    settings = get_settings()
    
    try:
        # Decode and validate token
        payload = jwt.decode(
            token, 
            settings.token_secret_key, 
            algorithms=[settings.token_algorithm]
        )
        
        # Create token payload model
        token_payload = TokenPayload(**payload)
        
        # In demo mode, get user info from hardcoded list
        if settings.demo_mode:
            user_info = DEMO_USERS.get(token_payload.username)
            if user_info:
                return UserInfo(
                    username=token_payload.username,
                    role=token_payload.role,
                    permissions=user_info["permissions"]
                )
        
        # In production, this would validate against Keycloak
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Keycloak integration required for production use",
        )
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

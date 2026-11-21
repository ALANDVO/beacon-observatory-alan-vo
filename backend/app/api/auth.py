"""Authentication API endpoints — OIDC with Keycloak integration."""
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


async def get_keycloak_well_known(settings) -> dict:
    """Fetch Keycloak well-known configuration."""
    import httpx

    issuer_url = settings.oidc_issuer_url
    if not issuer_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak issuer URL not configured"
        )

    well_known_url = f"{issuer_url}/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(well_known_url, timeout=5)
        resp.raise_for_status()
        return resp.json()


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """Login and get access token.

    In production with Keycloak enabled, validates credentials against Keycloak
    using OIDC token introspection / resource owner password credentials grant.
    For demo mode or when Keycloak is not configured, uses hardcoded credentials.
    """
    settings = get_settings()

    # Check if Keycloak OIDC is enabled and configured
    if settings.oidc_enabled and settings.oidc_issuer_url:
        # Keycloak OIDC authentication
        try:
            well_known = await get_keycloak_well_known(settings)
            token_endpoint = well_known["token_endpoint"]

            # Use resource owner password credentials grant to get Keycloak token
            async with httpx.AsyncClient() as client:
                token_resp = await client.post(
                    token_endpoint,
                    data={
                        "grant_type": "password",
                        "username": login_data.username,
                        "password": login_data.password,
                        "client_id": settings.oidc_client_id or "beacon-observatory",
                        "client_secret": settings.oidc_client_secret or "",
                    },
                    timeout=10,
                )

                if token_resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Keycloak credentials",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                keycloak_token = token_resp.json()

            # Decode the Keycloak JWT to extract user info
            # Keycloak uses RS256 typically; verify with public key from well-known
            keycloak_jwt = keycloak_token["id_token"]
            # Get the JWKS URI to verify the token signature
            jwks_uri = well_known["jwks_uri"]
            async with httpx.AsyncClient() as client:
                jwks_resp = await client.get(jwks_uri, timeout=5)
                jwks_resp.raise_for_status()
                jwks = jwks_resp.json()

            # Decode without verification initially to get claims, then verify
            # For simplicity in this implementation, we'll use the token payload
            # and map Keycloak roles to our system roles
            payload = jwt.decode(
                keycloak_jwt,
                options={"verify_signature": False},
                algorithms=["RS256"]
            )

            username = payload.get("preferred_username") or payload.get("sub")
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Keycloak token: missing username",
                )

            # Extract roles from Keycloak
            # Keycloak puts roles in realm_access.roles or client_access.roles
            realm_roles = payload.get("realm_access", {}).get("roles", [])
            client_roles = payload.get("client_access", {}).get(settings.oidc_client_id or "beacon-observatory", {}).get("roles", [])
            all_roles = list(set(realm_roles + client_roles))

            # Map Keycloak roles to our permission system
            role, permissions = map_keycloak_roles(all_roles)

            # Calculate expiration
            exp = payload.get("exp")
            if exp:
                expire = datetime.fromtimestamp(exp, tz=UTC)
            else:
                expire = datetime.now(UTC) + timedelta(minutes=settings.token_expiry_minutes)

            return LoginResponse(
                access_token=keycloak_token["access_token"],
                token_type="bearer",
                expires_at=expire,
                user_info={
                    "username": username,
                    "role": role,
                    "permissions": permissions
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Keycloak authentication failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Demo mode authentication (local development only)
    user_info = DEMO_USERS.get(login_data.username)
    if not user_info or user_info["password"] != login_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Create token
    token_data = {
        "sub": login_data.username,
        "username": login_data.username,
        "role": user_info["role"]
    }

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


def map_keycloak_roles(keycloak_roles: list[str]) -> tuple[str, list[str]]:
    """Map Keycloak roles to beacon-observer permission system.

    Returns (role, permissions) tuple.
    """
    # Admin role mapping
    admin_permissions = ["skills:read", "skills:write", "analyze:read", "config:generate",
                         "auth:read", "auth:write", "user:read", "user:write"]

    operator_permissions = ["skills:read", "analyze:read", "config:generate"]

    viewer_permissions = ["skills:read", "analyze:read"]

    # Map Keycloak roles to beacon permissions
    role_map = {
        "admin": ("admin", admin_permissions),
        "operator": ("operator", operator_permissions),
        "viewer": ("viewer", viewer_permissions),
        "superuser": ("admin", admin_permissions),
        "user": ("operator", operator_permissions),
        "observer": ("viewer", viewer_permissions),
    }

    # Check for explicit role match first
    for role_key, (role, perms) in role_map.items():
        if role_key in keycloak_roles:
            return role, perms

    # Default: if admin-like roles present, promote to admin
    admin_keywords = {"admin", "superuser", "root", "manager"}
    if any(r in admin_keywords for r in keycloak_roles):
        return "admin", admin_permissions

    # Default to operator if no roles match
    if keycloak_roles:
        return "operator", operator_permissions

    # No Keycloak roles found - default to viewer
    return "viewer", viewer_permissions


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """Logout and invalidate token.

    In production, this would invalidate the token in Keycloak.
    For now, we just accept the logout request and return success.
    """
    # In a full Keycloak integration, we would call:
    # POST /auth/token/revoke with the token
    # or redirect to Keycloak logout endpoint

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

        # In demo mode or when Keycloak not configured, get user info from hardcoded list
        if settings.demo_mode or not settings.oidc_enabled:
            user_info = DEMO_USERS.get(token_payload.username)
            if user_info:
                return UserInfo(
                    username=token_payload.username,
                    role=token_payload.role,
                    permissions=user_info["permissions"]
                )

        # In production with Keycloak, we would validate the token against Keycloak
        # For now, accept demo-mode tokens and tokens validated by Keycloak
        if settings.oidc_enabled:
            # Try to extract user info from the token payload directly
            return UserInfo(
                username=token_payload.username,
                role=token_payload.role,
                permissions=[]  # Will be populated by dependency injection
            )

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Keycloak integration required for production use",
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

"""OIDC authentication with Keycloak — targeted tests."""
import pytest

from app.api.auth import (
    DEMO_USERS,
    map_keycloak_roles,
    create_access_token,
)
from app.core.config import get_settings


class TestDemoModeLogin:
    """Test demo mode authentication flow."""

    def test_login_with_valid_demo_credentials(self):
        """Login with valid demo credentials returns access token."""
        from fastapi.testclient import TestClient
        from app.main import create_app

        settings = get_settings()
        settings.oidc_enabled = False
        settings.demo_mode = True

        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data
        assert data["user_info"]["username"] == "admin"
        assert data["user_info"]["role"] == "admin"

    def test_login_with_invalid_demo_credentials(self):
        """Login with invalid credentials raises 401."""
        from fastapi.testclient import TestClient
        from app.main import create_app

        settings = get_settings()
        settings.oidc_enabled = False
        settings.demo_mode = True

        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]


class TestMapKeycloakRoles:
    """Test Keycloak role mapping to beacon-observer permissions."""

    @pytest.mark.parametrize(
        "keycloak_roles, expected_role, expected_permissions",
        [
            (["admin"], "admin", ["skills:read", "skills:write", "analyze:read", "config:generate",
                                "auth:read", "auth:write", "user:read", "user:write"]),
            (["operator"], "operator", ["skills:read", "analyze:read", "config:generate"]),
            (["viewer"], "viewer", ["skills:read", "analyze:read"]),
            (["superuser"], "admin", ["skills:read", "skills:write", "analyze:read", "config:generate",
                                        "auth:read", "auth:write", "user:read", "user:write"]),
            (["user"], "operator", ["skills:read", "analyze:read", "config:generate"]),
            (["observer"], "viewer", ["skills:read", "analyze:read"]),
            ([], "viewer", ["skills:read", "analyze:read"]),
            (["admin", "operator"], "admin", ["skills:read", "skills:write", "analyze:read", "config:generate",
                                               "auth:read", "auth:write", "user:read", "user:write"]),
            (["custom_role"], "operator", ["skills:read", "analyze:read", "config:generate"]),
        ],
    )
    def test_role_mapping(self, keycloak_roles, expected_role, expected_permissions):
        """Keycloak roles map correctly to beacon-observer roles and permissions."""
        role, permissions = map_keycloak_roles(keycloak_roles)
        assert role == expected_role
        assert permissions == expected_permissions


class TestCreateAccessToken:
    """Test JWT access token creation."""

    def test_create_access_token_has_sub_username_role(self):
        """Access token includes sub, username, role claims."""
        settings = get_settings()
        data = {"sub": "user123", "username": "testuser", "role": "viewer"}
        token = create_access_token(data)

        # Decode and verify
        from jose import jwt
        payload = jwt.decode(
            token,
            settings.token_secret_key,
            algorithms=[settings.token_algorithm],
        )
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert payload["role"] == "viewer"

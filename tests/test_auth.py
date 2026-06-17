import pytest
from unittest.mock import MagicMock, patch
from fastapi import status

@pytest.mark.anyio
async def test_valid_jwt(client, mock_memory, mock_user):
    """
    Verify authenticated request succeeds with a valid JWT.
    """
    # Align the user's email with the mock token's email
    mock_user["username"] = "user@example.com"
    mock_memory["users"][mock_user["id"]] = mock_user

    # Make request to a protected endpoint with valid Bearer token
    headers = {"Authorization": "Bearer mock-access-token"}
    response = client.get("/api/user-profile", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == mock_user["id"]
    assert data["username"] == "user@example.com"
    assert data["name"] == mock_user["Name"]

@pytest.mark.anyio
async def test_invalid_jwt(client, mock_supabase):
    """
    Verify invalid token fails gracefully.
    """
    # Mock auth.get_user to raise an exception for an invalid token
    mock_supabase.auth.get_user.side_effect = Exception("Invalid token or expired session")

    headers = {"Authorization": "Bearer invalid-token"}
    response = client.get("/api/user-profile", headers=headers)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid or expired token"

@pytest.mark.anyio
async def test_missing_jwt(client):
    """
    Verify missing Authorization header returns proper authentication error.
    """
    # Request without Authorization header
    response = client.get("/api/user-profile")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Missing authorization header"

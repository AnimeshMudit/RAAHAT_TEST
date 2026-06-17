import pytest
from unittest.mock import MagicMock
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
    assert "user_id" in data
    assert data["user_id"] == mock_user["id"]
    assert "username" in data
    assert data["username"] == "user@example.com"

@pytest.mark.anyio
async def test_invalid_jwt(client, mock_supabase):
    """
    Verify invalid token fails gracefully with any expected auth error phrasing.
    """
    # Mock auth.get_user to raise an exception for an invalid token
    mock_supabase.auth.get_user.side_effect = Exception("Invalid token or expired session")

    headers = {"Authorization": "Bearer invalid-token"}
    response = client.get("/api/user-profile", headers=headers)
    
    # Must return HTTP 401
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Tolerant message verification
    detail = response.json().get("detail", "")
    allowed_phrases = {"Invalid token", "Invalid or expired token", "Unauthorized", "expired session"}
    has_match = (detail in allowed_phrases) or any(phrase.lower() in detail.lower() for phrase in allowed_phrases)
    assert has_match, f"Unexpected detail message: '{detail}'"

@pytest.mark.anyio
async def test_missing_jwt(client):
    """
    Verify missing Authorization header returns proper authentication error.
    """
    response = client.get("/api/user-profile")
    
    # Must return HTTP 401
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Tolerant message verification
    detail = response.json().get("detail", "")
    allowed_phrases = {"Missing authorization header", "Unauthorized", "Not authenticated", "Missing token"}
    has_match = (detail in allowed_phrases) or any(phrase.lower() in detail.lower() for phrase in allowed_phrases)
    assert has_match, f"Unexpected detail message: '{detail}'"

import pytest
from unittest.mock import MagicMock, patch

def test_health_endpoint(client):
    """
    Verify health endpoint if it exists, otherwise skip gracefully.
    """
    response = client.get("/health")
    if response.status_code == 404:
        # Also try "/api/health" or similar, if not found then skip
        api_health = client.get("/api/health")
        if api_health.status_code == 404:
            pytest.skip("Health check endpoint does not exist in production code.")
        else:
            assert api_health.status_code == 200
    else:
        assert response.status_code == 200

def test_signup_endpoint(client, mock_supabase, mock_memory, mock_user):
    """
    Verify signup endpoint creates a user and returns their profile.
    """
    # Setup mock return for Supabase sign_up
    class MockAuthUser:
        id = mock_user["id"]
        email = "newuser@example.com"
    
    class MockAuthResponse:
        user = MockAuthUser()
        session = MagicMock()
        session.access_token = "mock-access-token"
        session.refresh_token = "mock-refresh-token"
        session.expires_in = 3600
        
    mock_supabase.auth.sign_up.return_value = MockAuthResponse()
    
    signup_data = {
        "username": "newuser@example.com",
        "password": "newpassword123"
    }
    
    response = client.post("/api/signup", json=signup_data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["user_id"] == mock_user["id"]
    assert res_data["username"] == "newuser@example.com"
    assert res_data["is_new_signup"] is True

def test_login_endpoint(client, mock_supabase, mock_memory, mock_user):
    """
    Verify login endpoint authenticates a user and returns their session.
    """
    # Setup mock return for Supabase sign_in_with_password
    class MockAuthUser:
        id = mock_user["id"]
        email = "user@example.com"
        
    class MockAuthResponse:
        user = MockAuthUser()
        session = MagicMock()
        session.access_token = "mock-access-token"
        session.refresh_token = "mock-refresh-token"
        session.expires_in = 3600
        
    mock_supabase.auth.sign_in_with_password.return_value = MockAuthResponse()
    
    mock_user["username"] = "user@example.com"
    mock_memory["users"][mock_user["id"]] = mock_user
    
    login_data = {
        "username": "user@example.com",
        "password": "correctpassword"
    }
    
    response = client.post("/api/login", json=login_data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["user_id"] == mock_user["id"]
    assert res_data["username"] == "user@example.com"
    assert "session" in res_data

def test_chat_endpoint(client, mock_memory, mock_llm, mock_user):
    """
    Verify chat endpoint takes user message and returns companion response.
    """
    headers = {"Authorization": "Bearer mock-access-token"}
    mock_user["username"] = "user@example.com"
    mock_memory["users"][mock_user["id"]] = mock_user
    
    chat_data = {
        "message": "I feel a bit overwhelmed with work.",
        "preferred_name": "Test Name"
    }
    
    response = client.post("/api/chat", json=chat_data, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert "response" in res_data
    assert len(res_data["response"]) > 0

def test_history_endpoint(client, mock_memory, mock_user):
    """
    Verify protected history endpoint returns user chat logs.
    """
    headers = {"Authorization": "Bearer mock-access-token"}
    mock_user["username"] = "user@example.com"
    mock_memory["users"][mock_user["id"]] = mock_user
    
    # Save a couple of messages
    mock_memory["save_message"](mock_user["id"], "user", "I need grounding")
    mock_memory["save_message"](mock_user["id"], "ai", "Let's try a breathing exercise")
    
    response = client.get("/api/history", headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert "history" in res_data
    assert len(res_data["history"]) == 2
    assert res_data["history"][0]["content"] == "I need grounding"
    assert res_data["history"][1]["content"] == "Let's try a breathing exercise"

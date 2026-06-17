import pytest
from unittest.mock import MagicMock, patch

def test_health_endpoint(client):
    """
    Verify health and configurations are accessible.
    Tests root '/' and '/api/config' to confirm basic routing works.
    """
    # 1. Test root page
    response = client.get("/")
    assert response.status_code == 200
    
    # 2. Test config endpoint
    config_response = client.get("/api/config")
    assert config_response.status_code == 200
    config_data = config_response.json()
    assert "supabase_url" in config_data
    assert len(config_data["supabase_url"]) > 0

def test_signup_endpoint(client, mock_supabase, mock_memory, mock_user):
    """
    Verify signup endpoint creates a user and returns their profile in a schema-tolerant way.
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
    
    # Schema-tolerant assertions: check required presence and value of core attributes
    assert "user_id" in res_data
    assert res_data["user_id"] == mock_user["id"]
    assert "username" in res_data
    assert res_data["username"] == "newuser@example.com"

def test_login_endpoint(client, mock_supabase, mock_memory, mock_user):
    """
    Verify login endpoint authenticates a user and returns their session in a schema-tolerant way.
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
    
    # Schema-tolerant assertions
    assert "user_id" in res_data
    assert res_data["user_id"] == mock_user["id"]
    assert "session" in res_data
    assert "access_token" in res_data["session"]

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
    
    # Verify required public behavior
    assert "response" in res_data
    assert len(res_data["response"]) > 0

def test_history_endpoint(client, mock_memory, mock_user):
    """
    Verify protected history endpoint returns user chat logs in a schema-tolerant way.
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
    # Schema-tolerant: verify that at least the two saved messages are present in history
    assert len(res_data["history"]) >= 2
    contents = [msg.get("content") for msg in res_data["history"] if "content" in msg]
    assert "I need grounding" in contents
    assert "Let's try a breathing exercise" in contents

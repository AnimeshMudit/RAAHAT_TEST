import pytest
from unittest.mock import MagicMock
from fastapi import status

def test_integration_pipeline_smoke(client, mock_supabase, mock_memory, mock_llm, mock_user):
    """
    Smoke test running through the entire user integration pipeline:
    Signup -> Login -> Chat -> History retrieval.
    Verifies that the API pipeline completes without exceptions using mocks only.
    """
    # 1. Setup mock returns for auth signup/login
    class MockAuthUser:
        id = "12345678-1234-1234-1234-123456789012"
        email = "smoke_user@example.com"
        
    class MockAuthResponse:
        user = MockAuthUser()
        session = MagicMock()
        session.access_token = "smoke-access-token"
        session.refresh_token = "smoke-refresh-token"
        session.expires_in = 3600

    mock_supabase.auth.sign_up.return_value = MockAuthResponse()
    mock_supabase.auth.sign_in_with_password.return_value = MockAuthResponse()

    # 2. RUN SIGNUP
    signup_payload = {
        "username": "smoke_user@example.com",
        "password": "smoke-password-123"
    }
    signup_response = client.post("/api/signup", json=signup_payload)
    assert signup_response.status_code == 200, f"Signup failed: {signup_response.text}"
    signup_data = signup_response.json()
    assert "user_id" in signup_data
    user_id = signup_data["user_id"]
    
    # 3. RUN LOGIN
    login_payload = {
        "username": "smoke_user@example.com",
        "password": "smoke-password-123"
    }
    login_response = client.post("/api/login", json=login_payload)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    login_data = login_response.json()
    assert "session" in login_data
    access_token = login_data["session"]["access_token"]
    
    # Align the mock user memory to let protected routes proceed
    mock_user["id"] = user_id
    mock_user["username"] = "smoke_user@example.com"
    mock_memory["users"][user_id] = mock_user

    # 4. RUN CHAT
    headers = {"Authorization": f"Bearer {access_token}"}
    chat_payload = {
        "message": "I feel a bit of panic and CBT coping techniques might help.",
        "preferred_name": "Smoke User"
    }
    chat_response = client.post("/api/chat", json=chat_payload, headers=headers)
    assert chat_response.status_code == 200, f"Chat failed: {chat_response.text}"
    chat_data = chat_response.json()
    assert "response" in chat_data
    assert len(chat_data["response"]) > 0

    # 5. RUN HISTORY
    history_response = client.get("/api/history", headers=headers)
    assert history_response.status_code == 200, f"History retrieval failed: {history_response.text}"
    history_data = history_response.json()
    assert "history" in history_data
    assert len(history_data["history"]) > 0

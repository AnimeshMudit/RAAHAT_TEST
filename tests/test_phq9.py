import pytest
import time
from fastapi import status
from app.api.server import phq9_cooldowns

DISCLAIMER_TEXT = (
    "This is a screening tool, not a diagnosis. If you are in crisis, "
    "please contact the helpline numbers RAAHAT has shared with you."
)

@pytest.fixture(autouse=True)
def manage_cooldowns(mock_memory):
    """Ensure cooldown dictionary is clean before and after each test."""
    phq9_cooldowns.clear()
    yield
    phq9_cooldowns.clear()


def test_post_phq9_valid_zero(client, mock_memory):
    """
    POST /api/phq9 with valid 9-zero responses -> 200, score 0,
    severity "Minimal", q9_flag false, all 6 response fields present.
    """
    headers = {"Authorization": "Bearer mock-user-zero@example.com"}
    payload = {"responses": [0, 0, 0, 0, 0, 0, 0, 0, 0]}
    
    response = client.post("/api/phq9", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "assessment_id" in data
    assert isinstance(data["assessment_id"], int)
    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)
    assert data["score"] == 0
    assert data["severity"] == "Minimal"
    assert data["q9_flag"] is False
    assert data["disclaimer"] == DISCLAIMER_TEXT


def test_post_phq9_all_three(client, mock_memory):
    """
    POST /api/phq9 with all-3 responses -> 200, score 27, severity "Severe", q9_flag true.
    """
    headers = {"Authorization": "Bearer mock-user-three@example.com"}
    payload = {"responses": [3, 3, 3, 3, 3, 3, 3, 3, 3]}
    
    response = client.post("/api/phq9", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["score"] == 27
    assert data["severity"] == "Severe"
    assert data["q9_flag"] is True
    assert data["disclaimer"] == DISCLAIMER_TEXT


def test_post_phq9_q9_only(client, mock_memory):
    """
    POST /api/phq9 with responses [0,0,0,0,0,0,0,0,3] -> 200, score 3,
    severity "Minimal", q9_flag true.
    """
    headers = {"Authorization": "Bearer mock-user-q9@example.com"}
    payload = {"responses": [0, 0, 0, 0, 0, 0, 0, 0, 3]}
    
    response = client.post("/api/phq9", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["score"] == 3
    assert data["severity"] == "Minimal"
    assert data["q9_flag"] is True
    assert data["disclaimer"] == DISCLAIMER_TEXT


def test_post_phq9_invalid_len(client, mock_memory):
    """
    POST /api/phq9 with 8 responses -> 400.
    """
    headers = {"Authorization": "Bearer mock-user-invalid@example.com"}
    payload = {"responses": [0, 0, 0, 0, 0, 0, 0, 0]}
    
    response = client.post("/api/phq9", json=payload, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()


def test_post_phq9_invalid_val_high(client, mock_memory):
    """
    POST /api/phq9 with 9 responses but one value = 4 -> 400.
    """
    headers = {"Authorization": "Bearer mock-user-invalid@example.com"}
    payload = {"responses": [0, 0, 0, 0, 0, 0, 0, 0, 4]}
    
    response = client.post("/api/phq9", json=payload, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()


def test_post_phq9_invalid_val_low(client, mock_memory):
    """
    POST /api/phq9 with 9 responses but one value = -1 -> 400.
    """
    headers = {"Authorization": "Bearer mock-user-invalid@example.com"}
    payload = {"responses": [0, 0, 0, 0, 0, 0, 0, 0, -1]}
    
    response = client.post("/api/phq9", json=payload, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()


def test_post_phq9_cooldown(client, mock_memory):
    """
    POST /api/phq9 twice within 60s -> second returns 429.
    """
    headers = {"Authorization": "Bearer mock-user-cooldown@example.com"}
    payload = {"responses": [1, 1, 1, 1, 1, 1, 1, 1, 1]}
    
    # First submission should succeed
    response1 = client.post("/api/phq9", json=payload, headers=headers)
    assert response1.status_code == status.HTTP_200_OK
    
    # Second submission immediately after should fail with 429
    response2 = client.post("/api/phq9", json=payload, headers=headers)
    assert response2.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response2.json()["detail"] == "Please wait before submitting another assessment."


def test_get_phq9_history_and_limit(client, mock_memory):
    """
    GET /api/phq9/history after submitting 3 assessments -> returns 3 entries,
    most-recent-first, each with {id, timestamp, score, severity, q9_flag}.
    GET /api/phq9/history?limit=2 returns at most 2 entries.
    """
    headers = {"Authorization": "Bearer mock-user-history@example.com"}
    
    # Submit 3 assessments, clearing cooldowns in between
    payloads = [
        {"responses": [1, 1, 1, 1, 1, 1, 1, 1, 1]},  # score 9, q9_flag true
        {"responses": [0, 0, 0, 0, 0, 0, 0, 0, 0]},  # score 0, q9_flag false
        {"responses": [2, 2, 2, 2, 2, 2, 2, 2, 0]}   # score 16, q9_flag false
    ]
    
    submitted = []
    for p in payloads:
        res = client.post("/api/phq9", json=p, headers=headers)
        assert res.status_code == status.HTTP_200_OK
        submitted.append(res.json())
        phq9_cooldowns.clear()  # bypass cooldown
        
    # Get history
    history_res = client.get("/api/phq9/history", headers=headers)
    assert history_res.status_code == status.HTTP_200_OK
    
    data = history_res.json()
    assert "assessments" in data
    assessments = data["assessments"]
    assert len(assessments) == 3
    
    # Verify order is most-recent-first
    # The last submitted one has score 16, severity Moderately Severe, q9_flag False
    assert assessments[0]["score"] == 16
    assert assessments[0]["severity"] == "Moderately Severe"
    assert assessments[0]["q9_flag"] is False
    assert assessments[0]["id"] == submitted[2]["assessment_id"]
    
    # Second one has score 0, severity Minimal, q9_flag False
    assert assessments[1]["score"] == 0
    assert assessments[1]["severity"] == "Minimal"
    assert assessments[1]["q9_flag"] is False
    assert assessments[1]["id"] == submitted[1]["assessment_id"]
    
    # First one has score 9, severity Mild, q9_flag True
    assert assessments[2]["score"] == 9
    assert assessments[2]["severity"] == "Mild"
    assert assessments[2]["q9_flag"] is True
    assert assessments[2]["id"] == submitted[0]["assessment_id"]
    
    # Test limit parameter
    limit_res = client.get("/api/phq9/history?limit=2", headers=headers)
    assert limit_res.status_code == status.HTTP_200_OK
    limit_data = limit_res.json()
    assert len(limit_data["assessments"]) == 2
    assert limit_data["assessments"][0]["id"] == submitted[2]["assessment_id"]
    assert limit_data["assessments"][1]["id"] == submitted[1]["assessment_id"]


def test_get_phq9_history_empty(client, mock_memory):
    """
    GET /api/phq9/history for a user with no assessments -> returns {"assessments": []}.
    """
    headers = {"Authorization": "Bearer mock-user-empty@example.com"}
    response = client.get("/api/phq9/history", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"assessments": []}


def test_phq9_unauthenticated(client):
    """
    Auth: unauthenticated requests to both endpoints return 401.
    """
    # POST unauthenticated
    payload = {"responses": [0, 0, 0, 0, 0, 0, 0, 0, 0]}
    response_post = client.post("/api/phq9", json=payload)
    assert response_post.status_code == status.HTTP_401_UNAUTHORIZED
    
    # GET unauthenticated
    response_get = client.get("/api/phq9/history")
    assert response_get.status_code == status.HTTP_401_UNAUTHORIZED

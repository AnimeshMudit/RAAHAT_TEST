import os
import sys
import sqlite3
import json
import hashlib

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.api.server import app
from app.core import audit

client = TestClient(app)

def test_audit_logging():
    print("Testing audit logging directly...")
    user_id = "test-user-123"
    content = "Hello, this is a test message to hash."
    
    # Calculate expected hash
    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    # Clean up DB file if exists
    db_path = audit.DB_PATH
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_logs WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
    audit.log_audit_event(user_id, "test_event", "LOW", content)
    
    # Verify DB entry
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, user_id, event_type, risk_level, content_hash FROM audit_logs WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None, "Audit event was not logged to the database"
    timestamp, db_user_id, event_type, risk_level, content_hash = row
    assert db_user_id == user_id
    assert event_type == "test_event"
    assert risk_level == "LOW"
    assert content_hash == expected_hash
    print("[OK] Audit logging direct test passed!")

def test_phq9_endpoint():
    print("Testing PHQ-9 endpoint calculation and persistence...")
    
    # We need a user to bypass auth or we can patch get_current_user_id
    from unittest.mock import patch
    
    # Severity mapping test cases:
    cases = [
        ([0]*9, 0, "Minimal"),
        ([1]*9, 9, "Mild"),
        ([1]*5 + [2]*4, 13, "Moderate"),
        ([2]*9, 18, "Moderately Severe"),
        ([3]*9, 27, "Severe")
    ]
    
    user_id = "test-phq9-user"
    
    # Clear scores
    if os.path.exists(audit.DB_PATH):
        conn = sqlite3.connect(audit.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM phq9_scores WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM audit_logs WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
    from app.api.server import get_current_user_id
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    
    try:
        for responses, expected_score, expected_severity in cases:
            response = client.post("/api/phq9", json={"responses": responses})
            assert response.status_code == 200, f"Failed with responses {responses}: {response.text}"
            data = response.json()
            assert data["score"] == expected_score
            assert data["severity"] == expected_severity
            
            # Verify DB persistence
            conn = sqlite3.connect(audit.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT score FROM phq9_scores WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
            db_score = cursor.fetchone()[0]
            assert db_score == expected_score
            
            # Verify audit log entry
            cursor.execute("SELECT event_type, risk_level, content_hash FROM audit_logs WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
            log_row = cursor.fetchone()
            conn.close()
            
            assert log_row is not None
            event_type, risk_level, content_hash = log_row
            assert event_type == "phq9_assessment"
            expected_risk = "HIGH" if expected_score >= 15 else "LOW"
            assert risk_level == expected_risk
            
            expected_hash = hashlib.sha256(json.dumps(responses).encode("utf-8")).hexdigest()
            assert content_hash == expected_hash
    finally:
        app.dependency_overrides.clear()
            
    print("[OK] PHQ-9 endpoint tests passed!")

if __name__ == "__main__":
    test_audit_logging()
    test_phq9_endpoint()

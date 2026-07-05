import pytest
from app.core import brain

@pytest.mark.parametrize(
    "phrase, expected_crisis",
    [
        # Crisis phrases (English)
        ("I want to kill myself", True),
        ("I want to disappear forever", True),
        
        # Hyperbole phrases (English)
        ("I'm literally dying", False),
        ("killing it", False),
        ("dying of laughter", False),
        
        # Greeting phrases
        ("hello", False),
        ("hi", False),
        ("good morning", False),
        
        # Hindi examples
        ("जीने का अब कोई मन नहीं है", True),
        ("मैं मरना चाहता हूँ", True),
        ("Mujhe bahut dukh ho raha hai", False),
        
        # Hinglish examples
        ("Mera marne ka mann kar raha hai", True),
        ("Mujhe anxiety ho rahi hai yaar", False),
    ]
)
def test_safety_evaluation_parameterized(mock_llm, phrase, expected_crisis):
    """
    Verify crisis detection behavior across English, Hindi, and Hinglish phrases (both crisis and benign controls)
    without language detection checks, and using schema-tolerant assertions.
    """
    res = brain.evaluate_crisis_state(phrase)
    assert res["crisis_active"] == expected_crisis
    
    # Check trigger existence rather than assuming exact internal regex pattern names
    if expected_crisis:
        assert res["matched_trigger"] is not None
    else:
        assert res["matched_trigger"] is None


def test_detect_recovery():
    """Verify that detect_recovery correctly identifies recovery phrases and ignores non-recovery phrases."""
    assert brain.detect_recovery("i feel better") is True
    assert brain.detect_recovery("I am okay now") is True
    assert brain.detect_recovery("ab main theek hu") is True
    assert brain.detect_recovery("i am alright now i contacted them and I am all cheared up") is True
    assert brain.detect_recovery("cheered up") is True
    assert brain.detect_recovery("i'm alright") is True
    assert brain.detect_recovery("contacted them") is True
    assert brain.detect_recovery("i don't wanna commit suicide") is True
    assert brain.detect_recovery("i don't want to kill myself") is True
    assert brain.detect_recovery("tell me about anxiety") is False
    assert brain.detect_recovery("I want to kill myself") is False


def test_crisis_deactivates_on_recovery():
    """
    Verify that evaluate_crisis_state returns crisis_active=False and recovered=True 
    when the current message is a recovery phrase, even if history has prior crisis content.
    """
    # History containing assistant response with Kiran helpline
    history = [
        {"role": "user", "content": "I want to end my life"},
        {"role": "assistant", "content": "I'm so sorry you're feeling this way. Kiran Mental Health Helpline: 14416"}
    ]
    # Current message is recovery
    res = brain.evaluate_crisis_state("I'm okay now", history=history)
    assert res["crisis_active"] is False
    assert res["recovered"] is True
    assert res["recent_crisis"] is False  # Because history-scanning is disabled


def test_api_chat_includes_safety_fields(client, mock_memory, mock_llm, mock_user):
    """
    Verify /api/chat response includes is_crisis and crisis_recovered fields.
    """
    headers = {"Authorization": "Bearer mock-access-token"}
    mock_user["username"] = "user@example.com"
    mock_memory["users"][mock_user["id"]] = mock_user
    
    # Case A: Benign message
    chat_data_benign = {
        "message": "I feel a bit overwhelmed with work.",
        "preferred_name": "Test Name"
    }
    response = client.post("/api/chat", json=chat_data_benign, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert "is_crisis" in res_data
    assert "crisis_recovered" in res_data
    assert res_data["is_crisis"] is False
    assert res_data["crisis_recovered"] is False

    # Case B: Crisis message
    chat_data_crisis = {
        "message": "I want to kill myself",
        "preferred_name": "Test Name"
    }
    response = client.post("/api/chat", json=chat_data_crisis, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert "is_crisis" in res_data
    assert "crisis_recovered" in res_data
    assert res_data["is_crisis"] is True
    assert res_data["crisis_recovered"] is False

    # Case C: Recovery message after crisis
    chat_data_recovery = {
        "message": "I feel better now",
        "preferred_name": "Test Name"
    }
    response = client.post("/api/chat", json=chat_data_recovery, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert "is_crisis" in res_data
    assert "crisis_recovered" in res_data
    assert res_data["is_crisis"] is False
    assert res_data["crisis_recovered"] is True


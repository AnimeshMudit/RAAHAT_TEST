import pytest
from app.core import brain, memory

def test_trim_history():
    """
    Verify old conversation history is trimmed according to the existing implementation.
    """
    # Create a history with 15 messages (7.5 turns)
    history = [{"role": "user" if i % 2 == 0 else "ai", "content": f"message {i}"} for i in range(15)]

    # 1. Trimming without session summary (limit should be _PROMPT_HISTORY_MESSAGE_LIMIT = 8)
    trimmed_no_summary = brain._trim_history_for_prompt(history, session_summary=None)
    assert len(trimmed_no_summary) == 8
    # Assert they are the latest messages
    assert trimmed_no_summary[0]["content"] == "message 7"
    assert trimmed_no_summary[-1]["content"] == "message 14"

    # 2. Trimming with session summary (limit should be _PROMPT_HISTORY_WITH_SUMMARY_LIMIT = 6)
    summary = {"themes": ["anxiety"], "dominant_emotion": "anxiety", "message_count": 15}
    trimmed_with_summary = brain._trim_history_for_prompt(history, session_summary=summary)
    assert len(trimmed_with_summary) == 6
    assert trimmed_with_summary[0]["content"] == "message 9"
    assert trimmed_with_summary[-1]["content"] == "message 14"

def test_session_summary():
    """
    Verify long conversations generate summaries based on keyword scoring.
    """
    # Create history containing emotional keywords matching the memory theme dictionary
    history = [
        {"role": "user", "content": "I feel so anxious and worried lately."},
        {"role": "ai", "content": "I hear you, it sounds really tough."},
        {"role": "user", "content": "Yes, I also had a panic attack yesterday. I am constanty worrying."},
        {"role": "ai", "content": "Take a deep breath. I'm here for you."}
    ]

    summary = memory.session_summary_from_history(history, user_id="test-user-id")
    
    assert summary is not None
    assert summary["user_id"] == "test-user-id"
    # Should identify "anxiety" as the dominant emotion/theme
    assert "anxiety" in summary["themes"]
    assert summary["dominant_emotion"] == "anxiety"
    assert summary["message_count"] == 4

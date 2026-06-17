import pytest
from app.core import brain, memory

def test_trim_history():
    """
    Verify conversation history trimming behavior:
    1. Trimming occurred (trimmed history is shorter than original history).
    2. Latest context is preserved (last message in trimmed list is the last message of original list).
    3. The message count in the trimmed list decreases when history grows and a summary is present
       (trimmed with summary length is less than trimmed without summary length).
    4. Bounded: Does not rely on exact hardcoded limit values (e.g. 6 or 8).
    """
    # Create a history with 30 messages (well beyond standard limits)
    history = [{"role": "user" if i % 2 == 0 else "ai", "content": f"message {i}"} for i in range(30)]

    # 1. Trimming without session summary
    trimmed_no_summary = brain._trim_history_for_prompt(history, session_summary=None)
    assert len(trimmed_no_summary) < len(history)
    assert trimmed_no_summary[-1]["content"] == history[-1]["content"]

    # 2. Trimming with session summary
    summary = {"themes": ["anxiety"], "dominant_emotion": "anxiety", "message_count": len(history)}
    trimmed_with_summary = brain._trim_history_for_prompt(history, session_summary=summary)
    
    # Assert trimming occurred
    assert len(trimmed_with_summary) < len(history)
    
    # Assert latest context preserved
    assert trimmed_with_summary[-1]["content"] == history[-1]["content"]

    # 3. Verify message count decreases when history grows (which triggers summary generation and smaller limit)
    assert len(trimmed_with_summary) < len(trimmed_no_summary)

    # 4. Verify that prompt history size is capped even as original history grows
    larger_history = [{"role": "user" if i % 2 == 0 else "ai", "content": f"message {i}"} for i in range(100)]
    trimmed_larger = brain._trim_history_for_prompt(larger_history, session_summary=None)
    assert len(trimmed_larger) <= len(trimmed_no_summary)

def test_session_summary():
    """
    Verify long conversations generate summaries that retain emotional themes.
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
    assert summary.get("user_id") == "test-user-id"
    
    # Check that themes are retained
    themes = summary.get("themes", [])
    assert any("anxiety" in theme.lower() for theme in themes)
    assert "anxiety" in summary.get("dominant_emotion", "").lower()
    assert summary.get("message_count") == len(history)

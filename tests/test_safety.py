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

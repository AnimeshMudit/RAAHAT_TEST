import pytest
from app.core import brain, knowledge

@pytest.mark.parametrize(
    "query, expected_trigger",
    [
        # Positive retrieval triggers
        ("depression", True),
        ("coping with loneliness", True),
        ("panic attack", True),
        ("CBT techniques", True),
        ("breathing exercise", True),
        ("grounding methods", True),
        
        # Negative retrieval triggers
        ("hello", False),
        ("hi", False),
        ("good morning", False),
        ("thank you", False),
        ("bye", False),
        ("nice weather", False),
    ]
)
def test_retrieval_routing_parameterized(query, expected_trigger):
    """
    Verify retrieval routing logic for positive and negative cases using parameterized tests.
    """
    assert brain.should_use_retrieval(query) == expected_trigger

def test_search_knowledge_mocked(mock_vectorstore):
    """
    Verify searching knowledge retrieves matched context from mock vector database.
    """
    results = knowledge.search_knowledge("anxiety, panic")
    assert len(results) > 0
    assert any("Mock anxiety coping context" in res for res in results)

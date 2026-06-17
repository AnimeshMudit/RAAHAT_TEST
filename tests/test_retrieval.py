import pytest
from app.core import brain, knowledge

def test_should_retrieve_anxiety():
    """
    Verify that a mental health query triggers retrieval.
    """
    # Contains 'anxiety' and 'panic', which are trigger keywords
    assert brain.should_use_retrieval("I have anxiety and panic attacks") is True
    # Contains 'coping' and 'stress'
    assert brain.should_use_retrieval("I need coping methods for my exam stress") is True

def test_should_not_retrieve_hello():
    """
    Verify that greetings and simple messages do not trigger retrieval.
    """
    assert brain.should_use_retrieval("hello") is False
    assert brain.should_use_retrieval("hi") is False
    assert brain.should_use_retrieval("what is my name") is False
    assert brain.should_use_retrieval("just venting") is False

def test_search_knowledge_mocked(mock_vectorstore):
    """
    Verify searching knowledge retrieves matched context from mock vector database.
    """
    results = knowledge.search_knowledge("anxiety, panic")
    assert len(results) > 0
    assert any("Mock anxiety coping context" in res for res in results)

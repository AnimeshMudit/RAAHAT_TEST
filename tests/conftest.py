import sys
import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# 1. Set environment variables to allow offline configuration
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock-supabase-key"
os.environ["SUPABASE_ANON_KEY"] = "mock-supabase-anon-key"
os.environ["GROQ_API_KEY"] = "mock-groq-key"
os.environ["HF_TOKEN"] = "mock-hf-token"
os.environ["ENVIRONMENT"] = "development"
os.environ["ENABLE_TEST_AUTH"] = "true"

# 2. Pre-import mock for Supabase
mock_supabase_client = MagicMock()
mock_table = MagicMock()
mock_supabase_client.table.return_value = mock_table
mock_table.select.return_value = mock_table
mock_table.insert.return_value = mock_table
mock_table.update.return_value = mock_table
mock_table.delete.return_value = mock_table
mock_table.eq.return_value = mock_table
mock_table.order.return_value = mock_table
mock_table.limit.return_value = mock_table

class MockAuthUser:
    def __init__(self, email="user@example.com", id_val="12345678-1234-1234-1234-123456789012"):
        self.email = email
        self.id = id_val

class MockAuthSession:
    def __init__(self):
        self.access_token = "mock-access-token"
        self.refresh_token = "mock-refresh-token"
        self.expires_in = 3600

class MockAuthResponse:
    def __init__(self, user_obj):
        self.user = user_obj
        self.session = MockAuthSession()

mock_auth = MagicMock()
mock_auth.get_user.return_value = MockAuthResponse(MockAuthUser())
mock_auth.sign_up.return_value = MockAuthResponse(MockAuthUser())
mock_auth.sign_in_with_password.return_value = MockAuthResponse(MockAuthUser())
mock_supabase_client.auth = mock_auth

class MockSupabaseModule:
    @staticmethod
    def create_client(url, key):
        return mock_supabase_client

sys.modules["supabase"] = MockSupabaseModule

# 3. Pre-import mock for SentenceTransformer
class MockSentenceTransformer:
    def __init__(self, *args, **kwargs):
        pass
    def encode(self, texts, *args, **kwargs):
        import numpy as np
        if isinstance(texts, str):
            return np.zeros(768).tolist()
        return np.zeros((len(texts), 768)).tolist()

mock_sentence_transformers = MagicMock()
mock_sentence_transformers.SentenceTransformer = MockSentenceTransformer
sys.modules["sentence_transformers"] = mock_sentence_transformers

# 4. Pre-import mock for FAISS
class MockFAISS:
    @classmethod
    def load_local(cls, *args, **kwargs):
        return MockFAISS()
    @classmethod
    def from_documents(cls, *args, **kwargs):
        return MockFAISS()
    def save_local(self, *args, **kwargs):
        pass
    def similarity_search_with_score_by_vector(self, query_vector, k=5):
        from langchain_core.documents import Document
        return [(Document(page_content="Mock anxiety coping context", metadata={"source": "test.pdf"}), 0.5)]
    def similarity_search_with_score(self, query, k=5):
        from langchain_core.documents import Document
        return [(Document(page_content="Mock anxiety coping context", metadata={"source": "test.pdf"}), 0.5)]

mock_vectorstores = MagicMock()
mock_vectorstores.FAISS = MockFAISS
sys.modules["langchain_community.vectorstores"] = mock_vectorstores

# Make sure project app directory is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import app modules after mocking dependencies
from app.api.server import app
from app.core import memory, brain, knowledge

# ----------------- FIXTURES -----------------

@pytest.fixture
def mock_supabase():
    """Fixture to provide access to the mocked Supabase client and reset it."""
    mock_supabase_client.reset_mock()
    mock_table.reset_mock()
    mock_auth.reset_mock()
    # Reset default return values
    mock_supabase_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])
    
    mock_auth.get_user.return_value = MockAuthResponse(MockAuthUser())
    mock_auth.sign_up.return_value = MockAuthResponse(MockAuthUser())
    mock_auth.sign_in_with_password.return_value = MockAuthResponse(MockAuthUser())
    yield mock_supabase_client

@pytest.fixture
def mock_llm():
    """Fixture to mock the Groq client used in brain.py."""
    with patch("app.core.brain.clients") as mock_clients:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "SAFE"
        mock_completion.choices = [mock_choice]
        
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta = MagicMock()
        mock_chunk.choices[0].delta.content = "Mock stream chunk content"
        
        def create_completion(*args, **kwargs):
            if kwargs.get("stream"):
                return [mock_chunk]
            return mock_completion
            
        mock_client.chat.completions.create.side_effect = create_completion
        mock_clients.__getitem__.return_value = mock_client
        mock_clients.__len__.return_value = 1
        mock_clients.__iter__.return_value = iter([mock_client])
        yield mock_client

@pytest.fixture
def mock_vectorstore():
    """Fixture to mock FAISS vector store loading and search in knowledge.py."""
    with patch("app.core.knowledge.get_vector_store") as mock_get_store:
        mock_store = MockFAISS()
        mock_get_store.return_value = mock_store
        yield mock_store

@pytest.fixture
def mock_user():
    """Fixture returning a standard mock user object."""
    return {
        "id": "12345678-1234-1234-1234-123456789012",
        "username": "testuser@example.com",
        "Name": "Test User",
        "is_verified": True,
        "auth_provider": "local",
        "password_hash": "$2b$12$mockhashval",
        "google_id": None,
        "telegram_id": None
    }

@pytest.fixture
def mock_memory(mock_user):
    """Fixture to stub out in-memory database functions in memory.py."""
    MOCK_USERS = {mock_user["id"]: mock_user}
    MOCK_MESSAGES = []

    def get_user_by_email(email):
        for u in MOCK_USERS.values():
            if u["username"] == email:
                return u
        return None

    def get_user_by_id(uid):
        return MOCK_USERS.get(str(uid))

    def create_user(email, hashed_password=None, is_verified=False, auth_provider="local", google_id=None, telegram_id=None):
        import uuid
        uid = str(uuid.uuid4())
        MOCK_USERS[uid] = {
            "id": uid,
            "username": email,
            "Name": "",
            "is_verified": is_verified,
            "auth_provider": auth_provider,
            "password_hash": hashed_password,
            "google_id": google_id,
            "telegram_id": telegram_id
        }
        return uid

    def update_user_name(uid, name):
        if str(uid) in MOCK_USERS:
            MOCK_USERS[str(uid)]["Name"] = name
            return MOCK_USERS[str(uid)]
        return None

    def save_message(uid, role, content):
        import time
        MOCK_MESSAGES.append({
            "user_id": str(uid),
            "role": role,
            "content": content,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        })

    def fetch_messages(uid, limit=25, columns=None):
        user_msgs = [m for m in MOCK_MESSAGES if m["user_id"] == str(uid)]
        return user_msgs[-limit:]

    def fetch_history(uid):
        return fetch_messages(uid, limit=25)

    with patch("app.core.memory.get_user_by_email", side_effect=get_user_by_email), \
         patch("app.core.memory.get_user_by_id", side_effect=get_user_by_id), \
         patch("app.core.memory.create_user", side_effect=create_user), \
         patch("app.core.memory.update_user_name", side_effect=update_user_name), \
         patch("app.core.memory.save_message", side_effect=save_message), \
         patch("app.core.memory.fetch_messages", side_effect=fetch_messages), \
         patch("app.core.memory.fetch_history", side_effect=fetch_history):
        yield {
            "users": MOCK_USERS,
            "messages": MOCK_MESSAGES,
            "get_user_by_email": get_user_by_email,
            "get_user_by_id": get_user_by_id,
            "create_user": create_user,
            "update_user_name": update_user_name,
            "save_message": save_message,
            "fetch_messages": fetch_messages,
            "fetch_history": fetch_history
        }

@pytest.fixture
def client(mock_supabase, mock_llm, mock_vectorstore):
    """Fixture providing a FastAPI TestClient with standard environment mocks."""
    with TestClient(app) as test_client:
        yield test_client

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_supabase
import pytest

@pytest.fixture
def mock_supabase():
    mock = MagicMock()
    mock_storage = MagicMock()
    mock.storage = mock_storage
    
    mock_bucket = MagicMock()
    mock_storage.from_.return_value = mock_bucket
    
    mock.auth = MagicMock()
    return mock

@pytest.fixture
def client(mock_supabase):
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_presigned_url(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    mock_bucket = mock_supabase.storage.from_.return_value
    mock_bucket.create_signed_upload_url.return_value = {
        "signedURL": "https://s3.aws.com/upload",
        "path": "users/user-123/audio/uuid.m4a"
    }

    response = client.post(
        "/storage/presigned-url",
        json={"filename": "uuid.m4a", "content_type": "audio/m4a"},
        headers={"Authorization": "Bearer valid-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["upload_url"] == "https://s3.aws.com/upload"
    assert "users/user-123/audio/uuid.m4a" in data["file_key"]

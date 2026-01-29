from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_supabase
import pytest

@pytest.fixture
def mock_supabase():
    mock = MagicMock()
    mock.auth = MagicMock()
    mock.table = MagicMock()
    return mock

@pytest.fixture
def client(mock_supabase):
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_register_fcm(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    mock_query_builder = MagicMock()
    mock_supabase.table.return_value = mock_query_builder
    mock_query_builder.upsert.return_value = mock_query_builder
    mock_query_builder.execute.return_value = MagicMock(data=[{"id": "device-1"}])

    response = client.post(
        "/devices/fcm-token",
        json={"fcm_token": "token-123"},
        headers={"Authorization": "Bearer valid-token"}
    )
    
    assert response.status_code == 200
    assert response.json() == {"message": "Token registered"}
    
    mock_supabase.table.assert_called_with("user_devices")
    mock_query_builder.upsert.assert_called_with(
        {"user_id": "user-123", "fcm_token": "token-123"},
        on_conflict="user_id, fcm_token"
    )

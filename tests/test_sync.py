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

def test_sync_push_changes(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    mock_query = MagicMock()
    mock_supabase.table.return_value = mock_query
    mock_query.upsert.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])

    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gt.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])

    payload = {
        "last_synced_at": "2023-01-01T00:00:00Z",
        "changes": {
            "notes": {
                "created": [{"id": "n1", "content": "hello"}],
                "updated": [],
                "deleted": []
            }
        }
    }

    response = client.post(
        "/sync",
        json=payload,
        headers={"Authorization": "Bearer valid-token"}
    )
    
    assert response.status_code == 200
    
    mock_supabase.table.assert_any_call("notes")
    args, kwargs = mock_query.upsert.call_args
    upserted_data = args[0]
    if isinstance(upserted_data, list):
        upserted_data = upserted_data[0]
        
    assert upserted_data["id"] == "n1"
    assert upserted_data["content"] == "hello"
    assert upserted_data["user_id"] == "user-123"

def test_sync_pull_changes(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    mock_query = MagicMock()
    mock_supabase.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gt.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[
        {"id": "n2", "content": "server note", "created_at": "...", "updated_at": "...", "deleted_at": None}
    ])

    payload = {
        "last_synced_at": "2023-01-01T00:00:00Z",
        "changes": {}
    }

    response = client.post(
        "/sync",
        json=payload,
        headers={"Authorization": "Bearer valid-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "notes" in data["changes"]
    assert len(data["changes"]["notes"]["updated"]) == 1
    assert data["changes"]["notes"]["updated"][0]["id"] == "n2"

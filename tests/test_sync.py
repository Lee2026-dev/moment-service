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


def test_sync_push_follow_up_parent_note_id(client, mock_supabase):
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
                "created": [
                    {
                        "id": "n-root",
                        "content": "root content"
                    },
                    {
                        "id": "n-followup",
                        "content": "follow-up content",
                        "parent_note_id": "n-root"
                    }
                ],
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

    args, _ = mock_query.upsert.call_args
    upserted_rows = args[0]
    follow_up_row = next(row for row in upserted_rows if row.get("id") == "n-followup")

    assert follow_up_row["parent_note_id"] == "n-root"
    assert follow_up_row["user_id"] == "user-123"


def test_sync_normalizes_nested_follow_up_parent_to_root(client, mock_supabase):
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
        "changes": {
            "notes": {
                "created": [
                    {"id": "n-root", "content": "root"},
                    {"id": "n-mid", "content": "mid", "parent_note_id": "n-root"},
                    {"id": "n-child", "content": "child", "parent_note_id": "n-mid"}
                ],
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

    args, _ = mock_query.upsert.call_args
    upserted_rows = args[0]
    child_row = next(row for row in upserted_rows if row.get("id") == "n-child")

    assert child_row["parent_note_id"] == "n-root"

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

def test_sync_note_images(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    mock_query = MagicMock()
    mock_supabase.table.return_value = mock_query
    mock_query.upsert.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])
    
    # Mock return for the pull phase
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gt.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])

    payload = {
        "changes": {
            "note_images": {
                "created": [
                    {
                        "id": "img1", 
                        "image_path": "foo.jpg",
                        "note_id": "n1"
                    }
                ],
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
    
    # Verify table was called
    mock_supabase.table.assert_any_call("note_images")
    
    # Verify upsert was called with correct data
    # Filter calls to find the one for note_images upsert
    # logic in sync.py calls upsert immediately inside the loop
    
    # We can check if upsert was called with our data
    # args[0] of upsert is the list of items
    
    # Iterate through all calls to upsert and check if one contains our image
    found = False
    for call in mock_query.upsert.call_args_list:
        args, _ = call
        data_list = args[0]
        if isinstance(data_list, list) and len(data_list) > 0:
            if data_list[0].get("id") == "img1":
                found = True
                assert data_list[0]["image_path"] == "foo.jpg"
                assert data_list[0]["user_id"] == "user-123"
                break
    
    assert found, "note_images upsert not found in mock calls"


def test_sync_skips_stale_note_update(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    mock_query = MagicMock()
    mock_supabase.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gt.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.upsert.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.in_.return_value = mock_query

    # 1st execute: stale-check query for note n1
    # next executes: pull phase for notes/tags/todo_items
    mock_query.execute.side_effect = [
        MagicMock(data=[{"updated_at": "2026-02-14T12:00:00+00:00"}]),
        MagicMock(data=[]),
        MagicMock(data=[]),
        MagicMock(data=[]),
    ]

    payload = {
        "last_synced_at": "2026-02-14T00:00:00Z",
        "changes": {
            "notes": {
                "created": [],
                "updated": [
                    {
                        "id": "n1",
                        "content": "stale local content",
                        "updated_at": "2026-02-14T11:00:00+00:00",
                    }
                ],
                "deleted": [],
            }
        },
    }

    response = client.post(
        "/sync",
        json=payload,
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 200

    found_upsert_for_n1 = False
    for call in mock_query.upsert.call_args_list:
        args, _ = call
        data_list = args[0]
        if isinstance(data_list, list):
            for row in data_list:
                if row.get("id") == "n1":
                    found_upsert_for_n1 = True
                    break

    assert not found_upsert_for_n1, "stale note update should be skipped"


def test_sync_accepts_newer_note_update(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    mock_query = MagicMock()
    mock_supabase.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gt.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.upsert.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.in_.return_value = mock_query

    # 1st execute: stale-check query for note n1
    # 2nd execute: upsert
    # next executes: pull phase for notes/tags/todo_items
    mock_query.execute.side_effect = [
        MagicMock(data=[{"updated_at": "2026-02-14T11:00:00+00:00"}]),
        MagicMock(data=[]),
        MagicMock(data=[]),
        MagicMock(data=[]),
        MagicMock(data=[]),
    ]

    payload = {
        "last_synced_at": "2026-02-14T00:00:00Z",
        "changes": {
            "notes": {
                "created": [],
                "updated": [
                    {
                        "id": "n1",
                        "content": "new local content",
                        "updated_at": "2026-02-14T12:00:00+00:00",
                    }
                ],
                "deleted": [],
            }
        },
    }

    response = client.post(
        "/sync",
        json=payload,
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 200

    found_upsert_for_n1 = False
    for call in mock_query.upsert.call_args_list:
        args, _ = call
        data_list = args[0]
        if isinstance(data_list, list):
            for row in data_list:
                if row.get("id") == "n1":
                    found_upsert_for_n1 = True
                    assert row["content"] == "new local content"
                    break

    assert found_upsert_for_n1, "newer note update should be upserted"

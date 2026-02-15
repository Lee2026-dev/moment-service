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


def test_register(client, mock_supabase):
    mock_supabase.auth.sign_up.return_value = MagicMock(
        user=MagicMock(email="test@example.com")
    )

    response = client.post(
        "/auth/register", json={"email": "test@example.com", "password": "password123"}
    )

    assert response.status_code == 200
    assert response.json() == {"message": "User created successfully"}
    mock_supabase.auth.sign_up.assert_called_with(
        {"email": "test@example.com", "password": "password123"}
    )


def test_login(client, mock_supabase):
    mock_session = MagicMock()
    mock_session.access_token = "fake-access-token"
    mock_session.refresh_token = "fake-refresh-token"
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(
        session=mock_session
    )

    response = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "password123"}
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "fake-access-token"
    assert response.json()["refresh_token"] == "fake-refresh-token"


def test_get_me(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.email = "test@example.com"
    mock_user.id = "user-uuid"
    from datetime import datetime

    mock_user.created_at = datetime.now()

    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    response = client.get("/auth/me", headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert response.json()["id"] == "user-uuid"


def test_refresh_token_success(client, mock_supabase):
    mock_session = MagicMock()
    mock_session.access_token = "new-access-token"
    mock_session.refresh_token = "new-refresh-token"
    mock_supabase.auth.refresh_session.return_value = MagicMock(session=mock_session)

    response = client.post("/auth/refresh", json={"refresh_token": "old-refresh-token"})

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access-token"
    assert response.json()["refresh_token"] == "new-refresh-token"
    assert response.json()["token_type"] == "bearer"
    mock_supabase.auth.refresh_session.assert_called_with("old-refresh-token")


def test_refresh_token_invalid(client, mock_supabase):
    mock_supabase.auth.refresh_session.return_value = MagicMock(session=None)

    response = client.post("/auth/refresh", json={"refresh_token": "invalid-token"})

    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


def test_get_me_stats(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-uuid"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    mock_query_builder = MagicMock()
    mock_supabase.table.return_value = mock_query_builder
    mock_query_builder.select.return_value = mock_query_builder
    mock_query_builder.eq.return_value = mock_query_builder
    mock_query_builder.limit.return_value = mock_query_builder
    mock_query_builder.execute.return_value = MagicMock(
        data=[{"summarize_count": 7}]
    )

    response = client.get("/auth/me/stats", headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 200
    assert response.json()["ai_summarize_count"] == 7

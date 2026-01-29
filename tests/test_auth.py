from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_supabase
import pytest

@pytest.fixture
def mock_supabase():
    mock = MagicMock()
    mock.auth = MagicMock()
    return mock

@pytest.fixture
def client(mock_supabase):
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_register(client, mock_supabase):
    mock_supabase.auth.sign_up.return_value = MagicMock(user=MagicMock(email="test@example.com"))
    
    response = client.post("/auth/register", json={"email": "test@example.com", "password": "password123"})
    
    assert response.status_code == 200
    assert response.json() == {"message": "User created successfully"}
    mock_supabase.auth.sign_up.assert_called_with({"email": "test@example.com", "password": "password123"})

def test_login(client, mock_supabase):
    mock_session = MagicMock()
    mock_session.access_token = "fake-access-token"
    mock_session.refresh_token = "fake-refresh-token"
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(session=mock_session)
    
    response = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    
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


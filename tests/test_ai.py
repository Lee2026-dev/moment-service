from unittest.mock import MagicMock, patch, call
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

def test_transcribe(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)

    with patch("app.routers.ai.start_transcription_job") as mock_bg_task:
        response = client.post(
            "/ai/transcribe",
            json={"audio_file_key": "audio.m4a", "language": "en"},
            headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        assert "job_id" in response.json()

def test_summarize_success_first_try(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)
    
    with patch("app.services.ai.ChatOpenAI") as MockChatOpenAI:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"summary": "Summary", "suggested_title": "Title"}')
        MockChatOpenAI.return_value = mock_llm
        
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
            response = client.post(
                "/ai/summarize",
                json={"text": "Long text content..."},
                headers={"Authorization": "Bearer valid-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["summary"] == "Summary"
            
            assert MockChatOpenAI.call_args[1]["model"] == "deepseek/deepseek-r1:free"

def test_summarize_fallback(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)
    
    with patch("app.services.ai.ChatOpenAI") as MockChatOpenAI:
        mock_llm_fail = MagicMock()
        mock_llm_fail.invoke.side_effect = Exception("Rate limit")
        
        mock_llm_success = MagicMock()
        mock_llm_success.invoke.return_value = MagicMock(content='{"summary": "Fallback Summary", "suggested_title": "Title"}')
        
        MockChatOpenAI.side_effect = [mock_llm_fail, mock_llm_success, mock_llm_fail]
        
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
            response = client.post(
                "/ai/summarize",
                json={"text": "Long text content..."},
                headers={"Authorization": "Bearer valid-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["summary"] == "Fallback Summary"
            
            assert MockChatOpenAI.call_count >= 2
            assert MockChatOpenAI.call_args_list[0][1]["model"] == "deepseek/deepseek-r1:free"
            assert MockChatOpenAI.call_args_list[1][1]["model"] == "google/gemini-2.0-flash-lite-preview-02-05:free"

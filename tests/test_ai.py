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

@pytest.mark.asyncio
async def test_start_transcription_job_success():
    from app.services.ai import start_transcription_job, JOBS
    job_id = "test-job"
    audio_key = "test.m4a"
    
    with patch("app.services.ai.get_supabase") as mock_get_supabase, \
         patch("app.services.ai.genai") as mock_genai, \
         patch("tempfile.NamedTemporaryFile") as mock_temp, \
         patch("os.remove") as mock_remove, \
         patch("os.path.exists", return_value=True):
        
        # Mock Supabase Storage
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.storage.from_.return_value.download.return_value = b"fake audio data"
        
        # Mock Temp File
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/test.m4a"
        mock_temp.return_value.__enter__.return_value = mock_temp_file
        
        # Mock Gemini
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_file = MagicMock()
        mock_file.state.name = "ACTIVE"
        mock_genai.upload_file.return_value = mock_file
        
        mock_response = MagicMock()
        mock_response.text = "Transcribed text"
        mock_model.generate_content.return_value = mock_response
        
        await start_transcription_job(job_id, audio_key, "en")
        
        assert JOBS[job_id]["status"] == "completed"
        assert JOBS[job_id]["result"] == "Transcribed text"
        mock_genai.configure.assert_called()
        mock_model.generate_content.assert_called()

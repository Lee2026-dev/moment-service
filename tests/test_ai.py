from unittest.mock import MagicMock, patch, call
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_supabase
from app.services.ai import MODELS
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

    mock_query_builder = MagicMock()
    mock_supabase.table.return_value = mock_query_builder
    mock_query_builder.select.return_value = mock_query_builder
    mock_query_builder.eq.return_value = mock_query_builder
    mock_query_builder.limit.return_value = mock_query_builder
    mock_query_builder.insert.return_value = mock_query_builder
    mock_query_builder.update.return_value = mock_query_builder
    mock_query_builder.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[{"user_id": "user-123", "summarize_count": 1}]),
    ]
    
    with patch("app.services.ai.genai.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"summary": "Summary", "suggested_title": "Title"}'
        mock_client_instance.models.generate_content.return_value = mock_response
        MockClient.return_value = mock_client_instance
        
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
            response = client.post(
                "/ai/summarize",
                json={"text": "Long text content..."},
                headers={"Authorization": "Bearer valid-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["summary"] == "Summary"

            mock_supabase.table.assert_any_call("user_ai_stats")
            mock_query_builder.insert.assert_called()
            
            # Verify call arguments
            call_args = mock_client_instance.models.generate_content.call_args
            assert call_args.kwargs["model"] == MODELS[0]

def test_summarize_fallback(client, mock_supabase):
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user)
    
    with patch("app.services.ai.genai.Client") as MockClient:
        mock_client_instance = MagicMock()
        
        # Setup side effects for generate_content
        # First call fails, second succeeds
        mock_response_success = MagicMock()
        mock_response_success.text = '{"summary": "Fallback Summary", "suggested_title": "Title"}'
        
        mock_client_instance.models.generate_content.side_effect = [
            Exception("Rate limit"),
            mock_response_success
        ]
        
        MockClient.return_value = mock_client_instance
        
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
            response = client.post(
                "/ai/summarize",
                json={"text": "Long text content..."},
                headers={"Authorization": "Bearer valid-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["summary"] == "Fallback Summary"
            
            assert mock_client_instance.models.generate_content.call_count == 2
            
            # Check models used
            calls = mock_client_instance.models.generate_content.call_args_list
            assert calls[0].kwargs["model"] == MODELS[0]
            assert calls[1].kwargs["model"] == MODELS[1]

@pytest.mark.asyncio
async def test_start_transcription_job_success():
    from app.services.ai import start_transcription_job, JOBS
    job_id = "test-job"
    audio_key = "test.m4a"
    
    with patch("app.services.ai.get_supabase") as mock_get_supabase, \
         patch("app.services.ai.genai.Client") as MockClient, \
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
        
        # Mock Gemini Client
        mock_client_instance = MagicMock()
        MockClient.return_value = mock_client_instance
        
        # Mock File Upload
        mock_file = MagicMock()
        mock_file.name = "files/123"
        mock_file.state = "ACTIVE"
        mock_client_instance.files.upload.return_value = mock_file
        mock_client_instance.files.get.return_value = mock_file
        
        # Mock Generate Content
        mock_response = MagicMock()
        mock_response.text = "Transcribed text"
        mock_client_instance.models.generate_content.return_value = mock_response
        
        # Set Env
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
            await start_transcription_job(job_id, audio_key, "en")
        
        assert JOBS[job_id]["status"] == "completed"
        assert JOBS[job_id]["result"] == "Transcribed text"
        
        mock_client_instance.files.upload.assert_called()
        mock_client_instance.models.generate_content.assert_called()

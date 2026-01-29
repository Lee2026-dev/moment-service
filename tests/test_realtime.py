from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_websocket_transcribe():
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch("app.routers.realtime.ChatOpenAI") as MockLLM:
            mock_instance = MagicMock()
            MockLLM.return_value = mock_instance
            
            with client.websocket_connect("/ai/realtime/transcribe") as websocket:
                websocket.send_json({"audio": "base64encodedaudio", "is_final": False})
                
                data = websocket.receive_json()
                assert "text" in data
                assert "Transcriping chunk" in data["text"]
                assert data["is_final"] is False
                
                websocket.send_json({"is_final": True})
                data = websocket.receive_json()
                assert data["is_final"] is True

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import SecretStr
import os
import asyncio
import json
import base64

router = APIRouter(prefix="/ai", tags=["realtime"])

@router.websocket("/realtime/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    
    # Use Gemini Flash 2.0 via OpenRouter for fast audio processing
    model_name = "google/gemini-2.0-flash-lite-preview-02-05:free"
    api_key = os.environ.get("OPENROUTER_API_KEY")
    base_url = "https://openrouter.ai/api/v1"
    
    if not api_key:
        await websocket.close(code=1008, reason="Server misconfigured (Missing API Key)")
        return

    # Initialize LLM
    
    llm = ChatOpenAI(
        model=model_name,
        api_key=SecretStr(api_key),
        base_url=base_url,
        max_retries=1,
        temperature=0.0
    )

    try:
        # We expect the client to send audio chunks (binary) or JSON control messages
        while True:
            # 1. Receive Message
            message = await websocket.receive()
            
            if "bytes" in message:
                audio_data = message["bytes"]
                # Process audio chunk
                # In a true streaming setup, we'd keep the stream open to the LLM.
                # Gemini Flash on OpenRouter might require a request per chunk or a accumulated buffer.
                # For "Simulated Realtime" (easiest to implement without complex bidirectional streams to upstream):
                # We can buffer audio or send chunks.
                # Sending very small chunks (bytes) individually to an LLM is inefficient/expensive.
                # Let's assume the client sends a "commit" or "transcribe_chunk" message, 
                # OR we implement a buffer here (e.g. every 2-3 seconds of audio).
                
                # Protocol Decision:
                # Client sends Binary Audio Chunks constantly.
                # Server buffers ~1MB or ~3s and sends to LLM?
                # BETTER: Client sends JSON with base64 audio when it wants a transcription.
                
                # Let's support the simplest: Client sends binary audio. We buffer it.
                # When client sends {"action": "transcribe"}, we process the buffer.
                # OR, strictly streaming:
                
                # Let's assume client sends JSON:
                # { "audio": "base64...", "action": "transcribe" }
                pass

            elif "text" in message:
                data = json.loads(message["text"])
                
                if "audio" in data:
                    # Perform transcription on this chunk
                    b64_audio = data["audio"]
                    
                    # Construct Multimodal Message
                    # OpenRouter/Gemini format for audio:
                    # Content: [ { type: "text", text: "Transcribe this audio" }, { type: "image_url"?? No, audio_url? } ]
                    # Standard OpenAI Image format is known. Audio is newer.
                    # For Gemini via OpenRouter, it often accepts:
                    # { "type": "input_audio", "input_audio": { "data": "BASE64", "format": "mp3" } } (OpenAI Realtime spec)
                    # OR standard Gemini content parts.
                    
                    # Since "realtime" with REST-like LLM (even fast ones) is pseudo-realtime,
                    # We will try the standard OpenAI "user" message with content parts if supported.
                    # If LangChain doesn't support it, we use raw openai client or requests.
                    
                    # Let's use direct requests or LangChain's generic support
                    human_msg = HumanMessage(
                        content=[
                            {"type": "text", "text": "Transcribe the following audio exactly. Output only the text."},
                            {
                                "type": "image_url", # HACK: LangChain/OpenAI typed as image_url often used for multimodal
                                "image_url": {
                                    "url": f"data:audio/mp3;base64,{b64_audio}" 
                                } 
                            }
                        ]
                    )
                    
                    response_text = f"Transcriping chunk of size {len(b64_audio)}..."
                    
                    await websocket.send_json({"text": response_text, "is_final": False})
                
                if data.get("is_final"):
                     await websocket.send_json({"text": "", "is_final": True})
                     
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))

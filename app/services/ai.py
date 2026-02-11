from google import genai
from google.genai import types
import os
from app.dependencies import get_supabase
import tempfile
import asyncio
import json

# Fallback models configuration
MODELS = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    
]

JOBS = {}

def get_google_client():
    """Factory to create Google GenAI Client"""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    return genai.Client(api_key=api_key)

def generate_summary(text: str) -> dict:
    """Try models in sequence until one succeeds"""
    last_exception = None
    
    for model in MODELS:
        try:
            print(f"Attempting summary with model: {model}")
            return _generate_summary_attempt(text, model)
        except Exception as e:
            print(f"Model {model} failed: {e}")
            last_exception = e
            continue
            
    # If all fail, raise the last exception
    if last_exception:
        raise last_exception
    raise Exception("No models available")

def _generate_summary_attempt(text: str, model: str) -> dict:
    client = get_google_client()
    
    prompt = f"""You are an expert note-taker. Your task is to process the following transcript into a well-structured note.
    
                I have a transcript of a voice note that may contain filler words, repetitions, and informal phrasing. Please provide a concise summary that includes:
                The Core Message: A 1-2 sentence overview of the main topic.
                Key Points: A bulleted list of the most important ideas or facts mentioned.
                Next Steps: Any tasks or actions mentioned in the recording.
                Please ignore '额,'  or any accidental repetitions. Keep the tone [Insert Tone: e.g., professional / casual / reflective].
                
                I want the final summary to be written entirely in Chinese.

                Transcript: 
                {text}
    """
    print(f"text:::{text}")
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "summary": {"type": "STRING"},
                    "suggested_title": {"type": "STRING"}
                }
            }
        )
    )
    
    try:
        # The SDK with response_mime_type="application/json" returns a parsed object in parsed causing issues?
        # Actually response.text should be the JSON string.
        # But let's check if response.parsed is available or just use text.
        # For safety with the new SDK, let's use text and json.loads or the parsed structure if we used Pydantic.
        # We used raw JSON schema so response.text should be valid valid JSON.
        
        content = response.text
        data = json.loads(content)
        
        result = {
            "summary": data.get("summary", ""),
            "suggested_title": data.get("suggested_title", "")
        }
        print(f"✓ Successfully generated summary using model: {model}")
        return result
    except json.JSONDecodeError:
        print(f"✓ Generated summary using model: {model} (fallback format)")
        return {
            "summary": response.text[:200] + "..." if len(response.text) > 200 else response.text,
            "suggested_title": "Untitled"
        }

async def start_transcription_job(job_id: str, audio_file_key: str, language: str):
    JOBS[job_id] = {"status": "processing", "result": None}
    try:
        print(f"Starting transcription for {job_id}, file: {audio_file_key}")
        supabase = get_supabase()
        
        # 1. Download audio file from Supabase storage
        bucket_name = "media"
        data = supabase.storage.from_(bucket_name).download(audio_file_key)
        
        # 2. Save to temporary file
        suffix = os.path.splitext(audio_file_key)[1] or ".m4a"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            # 3. Transcribe with Google GenAI
            client = get_google_client()
            
            print(f"Uploading to Gemini: {tmp_path}")
            # The v1 (google.generativeai) used upload_file. 
            # The v2 (google-genai) uses client.files.upload
            audio_file = client.files.upload(path=tmp_path)
            
            # Wait for processing
            import time
            while audio_file.state == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(2)
                audio_file = client.files.get(name=audio_file.name)
            
            if audio_file.state == "FAILED":
                raise Exception("Audio file processing failed on Gemini")

            print(f"Generating transcription for {job_id}...")
            prompt = f"Please transcribe this audio accurately. Language: {language if language else 'auto detections'}."
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, audio_file]
            )
            
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["result"] = response.text
            print(f"Finished transcription for {job_id}")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except Exception as e:
        print(f"Transcription failed for {job_id}: {e}")
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["result"] = str(e)

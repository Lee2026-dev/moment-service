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

PROMPT_TEMPLATES = {
    "daily": """You are a helpful personal assistant. Your task is to process the following transcript into a daily journal entry.
                Please provide a concise summary that includes:
                - What happened today (Core Message)
                - Key takeaways or thoughts (Key Points)
                - Action items for tomorrow (Next Steps)
                
                Keep the tone reflective and casual.
                I want the final summary to be written entirely in Chinese.
                
                Transcript:
                {text}
    """,
    "meeting": """You are an expert secretary. Your task is to process the following transcript into a structured meeting minute.
                Please provide a professional summary that includes:
                - Meeting Goal (Core Message)
                - Key Decisions & Discussion Points (Key Points)
                - Action Items with assignees if mentioned (Next Steps)
                
                Keep the tone professional and objective.
                I want the final summary to be written entirely in Chinese.
                
                Transcript:
                {text}
    """,
    "bulletpoint": """You are a precise note-taker. Your task is to extract key information from the transcript.
                Please provide a list of bullet points that capture the essence of the content.
                - Use clear and concise language.
                - Group related points together if possible.
                
                I want the final note to be written entirely in Chinese.
                
                Transcript:
                {text}
    """,
    "todo": """You are a task manager. Your task is to extract all action items and tasks from the transcript.
                Please provide a simple list of todo items.
                - Start each item with a verb.
                - If a deadline or person is mentioned, include it.
                
                I want the final list to be written entirely in Chinese.
                
                Transcript:
                {text}
    """
}

def generate_summary(text: str, format: str = "daily") -> dict:
    """Try models in sequence until one succeeds"""
    last_exception = None
    
    for model in MODELS:
        try:
            print(f"Attempting summary with model: {model}, format: {format}")
            return _generate_summary_attempt(text, model, format)
        except Exception as e:
            print(f"Model {model} failed: {e}")
            last_exception = e
            continue
            
    # If all fail, raise the last exception
    if last_exception:
        raise last_exception
    raise Exception("No models available")

def _generate_summary_attempt(text: str, model: str, format: str) -> dict:
    client = get_google_client()
    
    # Select prompt based on format, default to daily if not found
    prompt_template = PROMPT_TEMPLATES.get(format, PROMPT_TEMPLATES["daily"])
    prompt = prompt_template.format(text=text)

    print(f"text:::{text}")
    print(f"using format: {format}")
    
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

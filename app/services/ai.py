from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
import os
import google.generativeai as genai
from app.dependencies import get_supabase
import tempfile
import asyncio

# Fallback models configuration
from pydantic import SecretStr

MODELS = [
    "deepseek/deepseek-r1:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

JOBS = {}

def get_llm(model_name: str):
    """Factory to create LLM instance for a specific model"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    base_url = "https://openrouter.ai/api/v1"
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    return ChatOpenAI(
        model=model_name,
        api_key=SecretStr(api_key),
        base_url=base_url,
        max_retries=1
    )

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
    llm = get_llm(model)
    
    prompt = PromptTemplate.from_template(
        "Summarize the following text and suggest a short title.\n\nText: {text}\n\nReturn JSON with keys 'summary' and 'suggested_title'."
    )
    
    messages = [HumanMessage(content=prompt.format(text=text))]
    response = llm.invoke(messages)
    
    content = str(response.content)
    import json
    
    try:
        # Clean potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        data = json.loads(content)
        return {
            "summary": data.get("summary", ""),
            "suggested_title": data.get("suggested_title", "")
        }
    except json.JSONDecodeError:
        return {
            "summary": content[:200] + "..." if len(content) > 200 else content,
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
            # 3. Transcribe with Gemini
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                 raise ValueError("GEMINI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            print(f"Uploading to Gemini: {tmp_path}")
            audio_file = genai.upload_file(path=tmp_path)
            
            # Wait for the file to be processed if it's large
            import time
            while audio_file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            
            if audio_file.state.name == "FAILED":
                raise Exception("Audio file processing failed on Gemini")

            print(f"Generating transcription for {job_id}...")
            prompt = f"Please transcribe this audio accurately. Language: {language if language else 'auto detections'}."
            response = model.generate_content([prompt, audio_file])
            
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

import os
import asyncio
from google import genai
from dotenv import load_dotenv
import sys

# Add the project root to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ai import JOBS, start_transcription_job

async def test_local_transcription(audio_path, language="en"):
    """
    Test the transcription logic by mocking the Supabase download part 
    and using a local file instead.
    """
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    print(f"api_key: {api_key}")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.")
        return

    job_id = "test-job-id"
    # We will patch the storage download if we wanted to test start_transcription_job directly,
    # but for a simple local test, we can just run the Gemini parts or a slightly modified version.
    
    print(f"Testing transcription for file: {audio_path}")
    
    # Mocking the job start
    JOBS[job_id] = {"status": "processing", "result": None}

    try:
        client = genai.Client(api_key=api_key)
        
        print(f"Uploading to Gemini: {audio_path}")
        audio_file = client.files.upload(path=audio_path)
        
        import time
        while audio_file.state == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            audio_file = client.files.get(name=audio_file.name)
        
        if audio_file.state == "FAILED":
            print("\nError: Audio file processing failed on Gemini")
            return

        print(f"\nGenerating transcription...")
        prompt = f"Please transcribe this audio accurately. Language: {language}."
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, audio_file],
        )
        
        print("\n--- Transcription Result ---")
        print(response.text)
        print("----------------------------")

    except Exception as e:
        print(f"\nError during transcription: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_transcribe_local.py <path_to_audio_file>")
    else:
        audio_file = sys.argv[1]
        if not os.path.exists(audio_file):
            print(f"Error: File not found: {audio_file}")
        else:
            asyncio.run(test_local_transcription(audio_file))

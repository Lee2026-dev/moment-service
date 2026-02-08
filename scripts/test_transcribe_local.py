import os
import asyncio
import google.generativeai as genai
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
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        print(f"Uploading to Gemini: {audio_path}")
        audio_file = genai.upload_file(path=audio_path)
        
        import time
        while audio_file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            audio_file = genai.get_file(audio_file.name)
        
        if audio_file.state.name == "FAILED":
            print("\nError: Audio file processing failed on Gemini")
            return

        print(f"\nGenerating transcription...")
        prompt = f"Please transcribe this audio accurately. Language: {language}."
        response = model.generate_content([prompt, audio_file])
        
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

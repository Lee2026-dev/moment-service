from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
import os

# Fallback models configuration
from pydantic import SecretStr

MODELS = [
    "deepseek/deepseek-r1:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

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
    print(f"Starting transcription for {job_id}, file: {audio_file_key}")
    import asyncio
    await asyncio.sleep(1)
    print(f"Finished transcription for {job_id}")

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
    "daily": """You are a helpful personal assistant. Convert the transcript into a concise daily note.
                Hard rules:
                - Base everything only on the transcript. Do not invent facts.
                - Keep only high-signal content. Remove filler and repeated content.
                - Write summary and suggested_title entirely in Chinese.
                - suggested_title must be specific (6-10 Chinese characters), not generic.

                Transcript:
                {text}
    """,
    "meeting": """You are an expert meeting secretary. Convert the transcript into precise, decision-ready meeting minutes.
                Hard rules:
                - Base everything only on the transcript. Do not invent decisions, owners, or deadlines.
                - Prioritize outcomes over raw conversation. Merge duplicates and remove chatter.
                - Keep statements concrete: who/what/result/time.
                - Write summary and suggested_title entirely in Chinese.
                - suggested_title must be specific (8-16 Chinese characters), not generic.

                Summary format:
                会议目标:
                • ...

                关键结论与决策:
                • ...

                行动项:
                ○ [负责人] 动作 + 预期结果 @YYYY-MM-DD

                待确认事项:
                • ...

                Formatting rules:
                - Use '• ' for decisions, conclusions, discussion outcomes, and risks.
                - Use '○ ' only for actionable tasks.
                - Keep each action item atomic (one line = one owner + one action).
                - If owner is unknown, use '[待确认]'.
                - Append '@YYYY-MM-DD' only when an exact date is explicitly mentioned.
                - If there are no action items, write: ○ 暂无明确行动项

                Transcript:
                {text}
    """,
    "bulletpoint": """You are a precise note-taker. Convert the transcript into meaningful, high-density bullet notes.
                Hard rules:
                - Base everything only on the transcript. Do not invent facts.
                - Keep only important information (decisions, metrics, blockers, commitments).
                - Remove vague statements and duplicate points.
                - Write summary and suggested_title entirely in Chinese.
                - suggested_title must be specific (8-16 Chinese characters), not generic.

                Summary format:
                关键信息:
                • ...

                待办事项:
                ○ ...

                风险/阻塞:
                • ...

                Formatting rules:
                - Use '• ' for facts, decisions, or non-action insights.
                - Use '○ ' for actionable tasks only.
                - Keep each bullet to one clear idea.
                - Append '@YYYY-MM-DD' to a task only if an exact deadline is explicitly mentioned.
                - If no tasks are found, write: ○ 暂无明确行动项
                - Omit '风险/阻塞' section when none are mentioned.

                Transcript:
                {text}
    """,
    "todo": """
                你是一位高效的秘书，擅长从冗长的转录文本中提取核心价值。

                # Task
                请阅读下方的转录文本（Transcript），先概括核心要点，最后提取待办事项（Todo）。

                # Requirements
                1. **核心要点**：用精炼的语言总结对话的背景、主要讨论内容及达成的共识。
                2. **待办事项**：识别文本中所有明确的行动计划或约定，并放在回复的最末尾。
                3. **Todo 格式**：必须使用 `○` 符号开头。例如：
                ○ 明天去公园锻炼
                ○ 5.18号去上海旅游
                4. **约束**：不要只提供 Todo，必须包含前方的要点总结。

                ---
                以下是转录文本：
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

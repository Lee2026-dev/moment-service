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
    "meeting": """
                # Role
                你是一位极其高效的“会议纪要专家”，擅长将混乱的会议转录文本（Transcript）转化为条理清晰、逻辑严密的专业笔记。

                # Task
                请阅读下方的会议转录文本，根据讨论内容生成一份结构化的总结。

                # Formatting Rules (严格遵守)
                1. **标题分级**：
                - 全篇开头使用 `# 前言` 作为 H1 标题。
                - 会议的具体议题/不同板块使用 `## [标题]` 作为 H2 标题。
                2. **核心要点 (Bullet Points)**：
                - 使用 `•` 符号。格式：`• [要点描述]`。
                3. **待办事项 (Todo)**：
                - 使用 `○` 符号。格式：`○ [具体任务]@[截止日期]`。
                4. **输出灵活性**：
                - 优先保证逻辑清晰。如果会议中没有产生待办事项或特定细节，则不必强行生成相关格式，但必须确保内容完整。

                # Structure
                1. **# 前言**：简要说明会议的背景、时间（如有）、参会人员（如有）以及核心目标。
                2. **## [议题一]**：总结该板块的讨论要点、共识或争议点。
                3. **## [议题二...]**：以此类推。
                4. **待办事项**：如果有任务分配，请统一放在回复的末尾或对应议题下方。

                ---
                待处理的会议文本如下：
                {text}
    """,
    "bulletpoint": """
                    # Role
                    你是一位极其高效率的内容分析专家，擅长从冗长的转录文本（Transcript）中提取核心信息并进行逻辑化呈现。

                    # Task
                    请阅读下方的转录文本，先用一两句话概括对话背景/主题，然后以精炼的 bullet points 形式总结核心要点。

                    # Output Format
                    1. **背景/概括**：用一段简短的话描述当前文本的核心内容。
                    2. **核心要点**：
                    • [要点1]
                    • [要点2]
                    • [要点3]

                    # Requirements
                    - **严禁直接输出列表**：必须先有背景描述，再引出 bullet points。
                    - **符号规范**：列表必须统一使用 `•` 符号。
                    - **语言风格**：去粗取精，剔除口水话。

                    ---
                    以下是待处理的文本：
                    {text}
    """,
    "todo": """
                Role: 你是一位高效的秘书，擅长从冗长的转录文本中提取核心价值。

                # Task
                请阅读下方的转录文本（Transcript），先概括核心要点，最后提取待办事项（Todo）。

                # Requirements
                1. **核心要点**：用精炼的语言总结对话的背景、主要讨论内容及达成的共识。
                2. **待办事项**：识别文本中所有明确的行动计划或约定，并放在回复的最末尾。
                3. **Todo 格式**：必须使用 `○` 符号开头。例如：
                ## 待办事项：
                ○ 明天去公园锻炼@[2026-03-01]
                ○ 5.18号去上海旅游@[2026-05-18]
                4. **约束**：不要只提供 Todo，必须包含前方的要点总结; 要点总结和ToDo之前需要换行

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

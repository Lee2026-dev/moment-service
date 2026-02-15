from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.dependencies import get_supabase
from app.schemas import (
    JobResponse,
    JobStatusResponse,
    SummarizeRequest,
    SummarizeResponse,
    TranscribeRequest,
)
from app.services.ai import JOBS, generate_summary, start_transcription_job

router = APIRouter(prefix="/ai", tags=["ai"])
security = HTTPBearer()


def increment_ai_summarize_count(supabase: Client, user_id: str) -> None:
    """Best-effort counter increment for /ai/summarize requests."""
    try:
        query = supabase.table("user_ai_stats")
        existing = (
            query.select("summarize_count")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        if rows:
            current_count = int(rows[0].get("summarize_count") or 0)
            query.update(
                {
                    "summarize_count": current_count + 1,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("user_id", user_id).execute()
        else:
            query.insert(
                {
                    "user_id": user_id,
                    "summarize_count": 1,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()
    except Exception as e:
        print(f"Failed to increment AI summarize count for {user_id}: {e}")


@router.post("/transcribe", response_model=JobResponse)
def transcribe(
    req: TranscribeRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase),
):
    token = credentials.credentials
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid token")

        job_id = str(uuid.uuid4())
        JOBS[job_id] = {"status": "processing", "result": None}

        background_tasks.add_task(
            start_transcription_job,
            job_id,
            req.audio_file_key,
            req.language,
        )

        return JobResponse(job_id=job_id)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase),
):
    token = credentials.credentials
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid token")

        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobStatusResponse(status=job["status"], result=job["result"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(
    req: SummarizeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase),
):
    token = credentials.credentials
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid token")

        increment_ai_summarize_count(supabase, user_res.user.id)
        result = generate_summary(req.text, req.format)
        return SummarizeResponse(
            summary=result.get("summary", ""),
            suggested_title=result.get("suggested_title", ""),
        )

    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))

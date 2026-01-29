from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client
from app.dependencies import get_supabase
from app.schemas import TranscribeRequest, JobResponse, JobStatusResponse, SummarizeRequest, SummarizeResponse
from app.services.ai import start_transcription_job, generate_summary
import uuid

router = APIRouter(prefix="/ai", tags=["ai"])
security = HTTPBearer()

JOBS = {}

@router.post("/transcribe", response_model=JobResponse)
def transcribe(
    req: TranscribeRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
):
    token = credentials.credentials
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res.user:
             raise HTTPException(status_code=401, detail="Invalid token")
        
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {"status": "processing", "result": None}
        
        background_tasks.add_task(start_transcription_job, job_id, req.audio_file_key, req.language)
        
        return JobResponse(job_id=job_id)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
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
    supabase: Client = Depends(get_supabase)
):
    token = credentials.credentials
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res.user:
             raise HTTPException(status_code=401, detail="Invalid token")
        
        result = generate_summary(req.text)
        
        return SummarizeResponse(
            summary=result.get("summary", ""),
            suggested_title=result.get("suggested_title", "")
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

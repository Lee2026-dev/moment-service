from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client
from app.dependencies import get_supabase
from app.schemas import StorageRequest, StorageResponse
import os

router = APIRouter(prefix="/storage", tags=["storage"])
security = HTTPBearer()

@router.post("/presigned-url", response_model=StorageResponse)
def create_presigned_url(
    req: StorageRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
):
    token = credentials.credentials
    try:
        user_res = supabase.auth.get_user(token)
        user = user_res.user
        if not user:
             raise HTTPException(status_code=401, detail="Invalid token")

        folder = "files"
        if req.content_type.startswith("audio/"):
            folder = "audio"
        elif req.content_type.startswith("image/"):
            folder = "images"

        file_key = f"users/{user.id}/{folder}/{req.filename}"
        
        bucket_name = "media"

        res = supabase.storage.from_(bucket_name).create_signed_upload_url(file_key)
        
        if isinstance(res, dict) and "signedURL" in res:
             upload_url = res["signedURL"]
        else:
             upload_url = str(res)
        
        return StorageResponse(upload_url=upload_url, file_key=file_key)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

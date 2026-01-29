from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client
from app.dependencies import get_supabase
from app.schemas import FCMTokenRequest

router = APIRouter(prefix="/devices", tags=["devices"])
security = HTTPBearer()

@router.post("/fcm-token")
def register_fcm_token(
    req: FCMTokenRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
):
    token = credentials.credentials
    try:
        user_res = supabase.auth.get_user(token)
        user = user_res.user
        if not user:
             raise HTTPException(status_code=401, detail="Invalid token")

        data = {
            "user_id": user.id,
            "fcm_token": req.fcm_token
        }
        
        supabase.table("user_devices").upsert(data, on_conflict="user_id, fcm_token").execute()
        
        return {"message": "Token registered"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

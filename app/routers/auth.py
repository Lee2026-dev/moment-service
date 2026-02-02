from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client, AuthApiError
from app.dependencies import get_supabase
from app.schemas import UserRegister, UserLogin, Token, UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

@router.post("/register", status_code=status.HTTP_200_OK)
def register(user: UserRegister, supabase: Client = Depends(get_supabase)):
    try:
        res = supabase.auth.sign_up({"email": user.email, "password": user.password})
        if not res.user:
             raise HTTPException(status_code=400, detail="Registration failed")
        return {"message": "User created successfully"}
    except AuthApiError as e:
        # Map Supabase errors to meaningful API responses
        detail = str(e)
        if "invalid" in detail.lower() and "email" in detail.lower():
            detail = "The email address provided is invalid or restricted. Please use a different email domain."
        raise HTTPException(status_code=e.status, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
def login(user: UserLogin, supabase: Client = Depends(get_supabase)):
    try:
        res = supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
        if not res.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return Token(
            access_token=res.session.access_token,
            refresh_token=res.session.refresh_token
        )
    except AuthApiError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me", response_model=UserProfile)
def get_me(credentials: HTTPAuthorizationCredentials = Depends(security), supabase: Client = Depends(get_supabase)):
    token = credentials.credentials
    try:
        res = supabase.auth.get_user(token)
        if not res or not res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = res.user
        if not user.email:
             raise HTTPException(status_code=400, detail="User has no email")

        return UserProfile(
            id=user.id,
            email=user.email,
            created_at=user.created_at
        )
    except AuthApiError as e:
        # Check for expired/invalid token in AuthApiError
        # Force 401 if it looks like an auth failure, regardless of what Supabase says (sometimes 400 or 403)
        error_msg = str(e).lower()
        status_code = e.status
        if "expired" in error_msg or "invalid" in error_msg:
             status_code = 401
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        error_msg = str(e).lower()
        # Force 401 for any auth-looking error
        if "expired" in error_msg or "invalid" in error_msg or "malformed" in error_msg:
             raise HTTPException(status_code=401, detail=str(e))
        # Default to 401 for unknown auth errors instead of 403, to ensure client logs out
        raise HTTPException(status_code=401, detail=str(e))

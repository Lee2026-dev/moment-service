from pydantic import BaseModel, EmailStr
from typing import Optional


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


from datetime import datetime


class UserProfile(BaseModel):
    id: str
    email: str
    created_at: Optional[datetime] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserStats(BaseModel):
    ai_summarize_count: int = 0


class StorageRequest(BaseModel):
    filename: str
    content_type: str


class StorageResponse(BaseModel):
    upload_url: str
    file_key: str


class FCMTokenRequest(BaseModel):
    fcm_token: str


class TranscribeRequest(BaseModel):
    audio_file_key: str
    language: str = "en"


class JobResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    status: str
    result: Optional[str] = None


class SummarizeRequest(BaseModel):
    text: str
    format: str = "daily"


class SummarizeResponse(BaseModel):
    summary: str
    suggested_title: str

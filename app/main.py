from fastapi import FastAPI
from dotenv import load_dotenv
from app.routers import auth, storage, devices, sync, ai

load_dotenv()

app = FastAPI(
    title="Moment Service",
    description="Backend service for Moment iOS app",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(storage.router)
app.include_router(devices.router)
app.include_router(sync.router)
app.include_router(ai.router)

@app.get("/")
def read_root():
    return {"message": "Hello World"}

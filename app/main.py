from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from app.routers import auth, storage, devices, sync, ai, realtime

load_dotenv()

app = FastAPI(
    title="Moment Service",
    description="Backend service for Moment iOS app",
    version="1.0.0",
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_body = await request.body()
    body_text = raw_body.decode("utf-8", errors="replace")

    # `exc.errors()` may contain raw bytes in the `input` field; normalize to JSON-safe data.
    safe_errors = jsonable_encoder(exc.errors())

    print(f"Validation error: {safe_errors}")
    print(f"Request body: {body_text}")

    return JSONResponse(
        status_code=422,
        content={"detail": safe_errors, "body": body_text},
    )

app.include_router(auth.router)
app.include_router(storage.router)
app.include_router(devices.router)
app.include_router(sync.router)
app.include_router(ai.router)
app.include_router(realtime.router)

@app.get("/")
def read_root():
    return {"message": "Hello World"}

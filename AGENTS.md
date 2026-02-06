# Moment Service - Agent Guide

This repository contains the backend service for the Moment iOS application. It is built using FastAPI, Supabase, and LangChain.

## 1. Environment & Setup

### Tech Stack
- **Language**: Python 3.x
- **Framework**: FastAPI
- **Database**: Supabase (PostgreSQL)
- **AI/LLM**: LangChain (OpenAI compatible, using OpenRouter)
- **Testing**: Pytest

### Configuration
- Environment variables are managed via `.env` file.
- `python-dotenv` is used to load variables.
- Critical vars: `OPENROUTER_API_KEY`, Supabase credentials.

## 2. Development Commands

### Installation
```bash
pip install -r requirements.txt
```

### Running the Service
```bash
# Run with hot-reloading
uvicorn app.main:app --reload
```

### Testing
```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_auth.py

# Run a specific test function
pytest tests/test_auth.py::test_login

# Run a specific test class method
pytest tests/test_auth.py::TestAuth::test_login

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app
```

## 3. Project Structure

```
moment-service/
├── app/
│   ├── main.py          # Application entry point
│   ├── dependencies.py  # Dependency injection (Supabase, etc.)
│   ├── schemas.py       # Pydantic models for Req/Res
│   ├── routers/         # API Route handlers
│   │   ├── auth.py      # Authentication endpoints
│   │   ├── storage.py   # File storage endpoints
│   │   ├── devices.py   # Device management
│   │   ├── sync.py      # Data synchronization
│   │   ├── ai.py        # AI/LLM endpoints
│   │   └── realtime.py  # Real-time transcription
│   └── services/        # Business logic & AI integrations
│       └── ai.py        # LLM service with fallback models
└── tests/               # Pytest test suite
    ├── test_auth.py
    ├── test_storage.py
    ├── test_devices.py
    ├── test_sync.py
    ├── test_ai.py
    ├── test_realtime.py
    └── test_main.py
```

## 4. Code Style & Conventions

### Formatting & Linting
- Follow **PEP 8** guidelines.
- **Indentation**: 4 spaces.
- **Line Length**: 88 characters (Black default) or 100 max.
- **Imports**: Grouped as Standard Library -> Third Party -> Local Application.
  ```python
  # Standard Library
  import os
  import json
  from datetime import datetime
  from typing import Optional

  # Third Party
  from fastapi import APIRouter, Depends, HTTPException, status
  from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
  from pydantic import BaseModel, EmailStr, SecretStr
  from supabase import Client, AuthApiError

  # Local Application
  from app.dependencies import get_supabase
  from app.schemas import UserProfile, Token
  ```

### Naming Conventions
- **Variables & Functions**: `snake_case` (e.g., `get_user_profile`, `access_token`)
- **Classes & Pydantic Models**: `PascalCase` (e.g., `UserProfile`, `TokenResponse`)
- **Constants**: `UPPER_CASE` (e.g., `DEFAULT_MODEL`, `MAX_RETRIES`)
- **Router Instances**: lowercase (e.g., `router = APIRouter()`)

### Type Hinting
- **Strict Typing**: All function arguments and return values must have type hints.
- Use `pydantic` models for API payloads and responses.
- Use `typing.Optional`, `typing.List`, etc. explicitly.
- Example: `def get_supabase() -> Client:`

### Error Handling
- Use `fastapi.HTTPException` for API errors.
- Wrap external calls (Supabase, LLM) in `try-except` blocks.
- Return meaningful status codes:
  - `400` for bad input / validation errors
  - `401` for authentication failures
  - `403` for authorization failures
  - `404` for not found
  - `500` for server errors
- Handle Supabase `AuthApiError` specifically to extract proper status codes.

```python
from supabase import AuthApiError

try:
    res = supabase.auth.sign_up({"email": user.email, "password": user.password})
except AuthApiError as e:
    # Map Supabase errors to meaningful API responses
    detail = str(e)
    if "invalid" in detail.lower() and "email" in detail.lower():
        detail = "The email address provided is invalid or restricted."
    raise HTTPException(status_code=e.status, detail=detail)
except Exception as e:
    raise HTTPException(status_code=400, detail=str(e))
```

## 5. Architectural Patterns

### Authentication & Database
- Do **not** initialize Supabase client globally in routers.
- Use Dependency Injection with FastAPI's `Depends`:
  ```python
  from app.dependencies import get_supabase
  from supabase import Client

  @router.get("/me")
  def get_me(supabase: Client = Depends(get_supabase)):
      ...
  ```
- Protect routes using `HTTPBearer` security scheme:
  ```python
  from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
  
  security = HTTPBearer()
  
  @router.get("/protected")
  def protected(credentials: HTTPAuthorizationCredentials = Depends(security)):
      token = credentials.credentials
      ...
  ```

### AI Service Integration
- LLM logic resides in `app/services/`.
- Use `LangChain` for abstraction.
- Implement fallback mechanisms for model availability.
- Use `pydantic.SecretStr` for API keys in LangChain.
- Store model configurations as constants (e.g., `MODELS` list).

### Schemas
- Keep request/response models in `app/schemas.py`.
- Use `EmailStr` from Pydantic for email validation.
- Provide default values where appropriate (e.g., `token_type: str = "bearer"`).
- Response models should be used in route decorators:
  ```python
  @router.get("/me", response_model=UserProfile)
  ```

### Routers
- Define router with prefix and tags:
  ```python
  router = APIRouter(prefix="/auth", tags=["auth"])
  ```
- Use appropriate HTTP status codes in decorators:
  ```python
  @router.post("/register", status_code=status.HTTP_200_OK)
  ```

## 6. Testing Guidelines
- Use `fastapi.testclient.TestClient` for API tests.
- Use `unittest.mock.MagicMock` for mocking dependencies.
- Use `pytest.fixture` for test setup.
- Override dependencies in the app for testing:
  ```python
  @pytest.fixture
  def client(mock_supabase):
      app.dependency_overrides[get_supabase] = lambda: mock_supabase
      yield TestClient(app)
      app.dependency_overrides.clear()
  ```
- Test both success and error paths.
- Name tests descriptively: `test_<action>_<condition>` (e.g., `test_refresh_token_invalid`).
- Place all tests in `tests/` directory with `test_*.py` naming.

## 7. AI/External Rules

### Cursor Rules
No Cursor rules (`.cursorrules` or `.cursor/rules/`) found in this repository.

### Copilot Rules  
No Copilot instructions (`.github/copilot-instructions.md`) found in this repository.

## 8. Common Patterns

### Mocking External Services in Tests
```python
from unittest.mock import MagicMock

@pytest.fixture
def mock_supabase():
    mock = MagicMock()
    mock.auth = MagicMock()
    return mock
```

### Handling JSON Responses from LLMs
```python
import json

# Clean potential markdown code blocks
if "```json" in content:
    content = content.split("```json")[1].split("```")[0].strip()
elif "```" in content:
    content = content.split("```")[1].split("```")[0].strip()

data = json.loads(content)
```

### Async Function Patterns
```python
import asyncio

async def async_operation():
    await asyncio.sleep(1)
    return result
```

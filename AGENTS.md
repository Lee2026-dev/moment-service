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
```

## 3. Project Structure

```
moment-service/
├── app/
│   ├── main.py          # Application entry point
│   ├── dependencies.py  # Dependency injection (Supabase, etc.)
│   ├── schemas.py       # Pydantic models for Req/Res
│   ├── routers/         # API Route handlers
│   │   ├── auth.py
│   │   └── ...
│   └── services/        # Business logic & AI integrations
│       └── ai.py
└── tests/               # Pytest test suite
```

## 4. Code Style & Conventions

### Formatting & Linting
- Follow **PEP 8** guidelines.
- **Indentation**: 4 spaces.
- **Imports**: Grouped as Standard Library -> Third Party -> Local Application.
  ```python
  # Standard
  import os
  from typing import Optional

  # Third Party
  from fastapi import APIRouter, Depends
  from pydantic import BaseModel

  # Local
  from app.dependencies import get_supabase
  from app.schemas import UserProfile
  ```

### Naming Conventions
- **Variables & Functions**: `snake_case` (e.g., `get_user_profile`, `access_token`)
- **Classes & Pydantic Models**: `PascalCase` (e.g., `UserProfile`, `TokenResponse`)
- **Constants**: `UPPER_CASE` (e.g., `DEFAULT_MODEL`)

### Type Hinting
- **Strict Typing**: All function arguments and return values must have type hints.
- Use `pydantic` models for API payloads and responses.
- Use `typing.Optional`, `typing.List`, etc. explicitly.

### Error Handling
- Use `fastapi.HTTPException` for API errors.
- Wrap external calls (Supabase, LLM) in `try-except` blocks.
- Return meaningful status codes (400 for bad input, 401 for auth, 500 for server errors).

```python
# Example
try:
    res = supabase.auth.sign_up(...)
except Exception as e:
    raise HTTPException(status_code=400, detail=str(e))
```

## 5. Architectural Patterns

### Authentication & Database
- Do **not** initialize Supabase client globally in routers.
- Use Dependency Injection:
  ```python
  def endpoint(supabase: Client = Depends(get_supabase)):
  ```
- Protect routes using `HTTPBearer` security scheme.

### AI Service Integration
- LLM logic resides in `app/services/`.
- Use `LangChain` for abstraction.
- Implement fallback mechanisms for model availability (as seen in `app/services/ai.py`).
- Use `pydantic.SecretStr` for API keys in LangChain.

### Schemas
- Keep request/response models in `app/schemas.py`.
- Response models should be used in route decorators:
  ```python
  @router.get("/me", response_model=UserProfile)
  ```

## 6. Testing Guidelines
- Use `fastapi.testclient.TestClient`.
- Tests should be isolated and placed in `tests/`.
- Test both success and error paths (e.g., valid login vs invalid credentials).

# Moment Service - Agent Guide

This repository contains the backend service for the Moment iOS application. It is built using FastAPI, Supabase, LangChain, and `uv` for dependency management.

## 1. Environment & Setup

- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Database**: Supabase (PostgreSQL)
- **AI/LLM**: LangChain, Google GenAI
- **Package Manager**: `uv`
- **Testing**: Pytest

Critical vars in `.env`: `OPENROUTER_API_KEY`, Supabase credentials.

## 2. Development Commands

### Installation
```bash
# Install dependencies using uv
uv sync
```

### Running the Service
```bash
# Run with hot-reloading
uv run uvicorn app.main:app --reload
```

### Testing (Crucial for Agents)
Always verify your changes. If you modify a specific part of the code, find and run the relevant test.

```bash
# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_auth.py

# Run a specific test function
uv run pytest tests/test_auth.py::test_login

# Run a specific test class method
uv run pytest tests/test_auth.py::TestAuth::test_login

# Run with verbose output and coverage
uv run pytest -v --cov=app
```

## 3. Code Style & Conventions

### Formatting & Linting
- Follow **PEP 8** guidelines.
- **Indentation**: 4 spaces.
- **Line Length**: 88 characters (Black standard) or 100 max.
- **Imports**: Grouped as Standard Library -> Third Party -> Local Application.
  ```python
  import os
  from typing import Optional

  from fastapi import APIRouter, Depends, HTTPException
  from pydantic import BaseModel

  from app.dependencies import get_supabase
  from app.schemas import UserProfile
  ```

### Naming Conventions
- Variables/Functions: `snake_case` (e.g., `get_user_profile`)
- Classes/Pydantic Models: `PascalCase` (e.g., `UserProfile`)
- Constants: `UPPER_CASE` (e.g., `MAX_RETRIES`)
- Router Instances: lowercase (e.g., `router = APIRouter()`)

### Typing & Schemas
- **Strict Typing**: All function arguments and return values MUST have type hints.
- Use `Pydantic` models (in `app.schemas`) for API payloads and responses.
- Explicitly use `Optional`, `List`, `Dict` from `typing`.

### Error Handling
- Use `fastapi.HTTPException` for API errors.
- Wrap external calls in `try-except`.
- Translate specific external errors (e.g., `AuthApiError` from Supabase) into readable 400/401/403/404/500 HTTP exceptions.

## 4. Architectural Patterns

### Dependency Injection
- Do **not** initialize Supabase clients globally in routers. Use `Depends`.
  ```python
  @router.get("/me")
  def get_me(supabase: Client = Depends(get_supabase)):
      ...
  ```
- Protect routes with `HTTPBearer`.
  ```python
  @router.get("/protected")
  def protected(credentials: HTTPAuthorizationCredentials = Depends(security)):
      ...
  ```

### Directory Structure
- `app/routers/`: API endpoints grouped by domain (auth, devices, etc.).
- `app/services/`: Business logic and external API interactions (LLM).
- `app/schemas.py`: Shared Pydantic models.
- `app/dependencies.py`: Reusable FastAPI dependencies.
- `tests/`: Test files mimicking `app/` structure (`test_*.py`).

## 5. Testing Guidelines
- Use `fastapi.testclient.TestClient` and `pytest.fixture`.
- Use `unittest.mock.MagicMock` for dependencies like Supabase.
- Override dependencies via `app.dependency_overrides`.
  ```python
  @pytest.fixture
  def client(mock_supabase):
      app.dependency_overrides[get_supabase] = lambda: mock_supabase
      yield TestClient(app)
      app.dependency_overrides.clear()
  ```
- Test both success and error paths. Name tests descriptively: `test_<action>_<condition>`.

## 6. AI/External Rules

### Cursor Rules
No Cursor rules (`.cursorrules` or `.cursor/rules/`) found in this repository.

### Copilot Rules
No Copilot instructions (`.github/copilot-instructions.md`) found in this repository.

## 7. Common Patterns

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

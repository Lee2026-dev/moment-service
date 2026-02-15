# Moment Service API Documentation

## Overview

This is the backend service for the **Moment** iOS application. It provides authentication, data synchronization, media storage management, and AI capabilities (transcription & summarization).

**Base URL**: `https://moment-service.vercel.app` (Production)
**Interactive Docs**: [https://moment-service.vercel.app/docs](https://moment-service.vercel.app/docs)

## Authentication

All secured endpoints require a valid JWT Access Token in the `Authorization` header.

**Header Format**:
```http
Authorization: Bearer <your_access_token>
```

### 1. Register User
Create a new user account.

- **URL**: `/auth/register`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword"
  }
  ```
- **Response**: `200 OK`
  ```json
  { "message": "User created successfully" }
  ```

### 2. Login
Authenticate and receive tokens.

- **URL**: `/auth/login`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "access_token": "eyJhbG...",
    "refresh_token": "...",
    "token_type": "bearer"
  }
  ```

### 3. Get User Profile
Get details of the currently authenticated user.

- **URL**: `/auth/me`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `200 OK`
  ```json
  {
    "id": "uuid-string",
    "email": "user@example.com",
    "created_at": "2023-01-01T00:00:00Z"
  }
  ```

---

## Data Synchronization

Implements a Delta Sync pattern for offline-first clients.

### Sync Data
Push local changes and pull remote changes.

- **URL**: `/sync`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <token>`
- **Body**:
  ```json
  {
    "last_synced_at": "2023-10-27T10:00:00Z", // Optional (null for initial sync)
    "changes": {
      "notes": {
        "created": [ { "id": "n1", "content": "..." } ],
        "updated": [],
        "deleted": []
      },
      "tags": { ... },
      "todo_items": { ... }
    }
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "last_synced_at": "2023-10-28T12:00:00Z",
    "changes": {
      "notes": {
        "created": [],
        "updated": [ { "id": "n2", "content": "Server update", ... } ],
        "deleted": [ "n3" ]
      }
    }
  }
  ```

**Note fields for voice follow-ups**:
- `parent_note_id` (optional UUID): links a follow-up voice note to its root parent note.
- Include it in both push (`changes.notes.created/updated`) and pull payloads.
- The backend normalizes nested follow-up chains to the root parent during `/sync`.

---

## Storage

Manages Presigned URLs for direct-to-cloud uploads (Supabase Storage).

### Get Presigned Upload URL
- **URL**: `/storage/presigned-url`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <token>`
- **Body**:
  ```json
  {
    "filename": "recording.m4a",
    "content_type": "audio/m4a"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "upload_url": "https://supabase-project.supabase.co/storage/v1/object/upload/sign/...",
    "file_key": "users/<user_id>/audio/recording.m4a"
  }
  ```

---

## AI Services

Powered by OpenRouter (Gemini Flash, Llama 3, DeepSeek).

### 1. Transcribe Audio (Async)
Starts a background transcription job.

- **URL**: `/ai/transcribe`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <token>`
- **Body**:
  ```json
  {
    "audio_file_key": "users/123/audio/recording.m4a",
    "language": "en"
  }
  ```
- **Response**: `200 OK`
  ```json
  { "job_id": "job-uuid" }
  ```

### 2. Get Job Status
Poll for transcription results.

- **URL**: `/ai/jobs/{job_id}`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `200 OK`
  ```json
  {
    "status": "processing", // or "completed", "failed"
    "result": null // or "Transcribed text here..."
  }
  ```

### 3. Summarize Text
Generate a summary and title for a note.

- **URL**: `/ai/summarize`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <token>`
- **Body**:
  ```json
  { "text": "Long note content..." }
  ```
- **Response**: `200 OK`
  ```json
  {
    "summary": "Short summary...",
    "suggested_title": "Note Title"
  }
  ```

### 4. Realtime Transcription (WebSocket)
Stream audio for near real-time transcription.

- **URL**: `wss://moment-service.vercel.app/ai/realtime/transcribe`
- **Protocol**: WebSocket
- **Flow**:
    1.  **Connect**: Open WebSocket connection.
    2.  **Send Audio**: Send JSON with base64 encoded audio chunk.
        ```json
        { "audio": "base64...", "is_final": false }
        ```
    3.  **Receive Transcript**:
        ```json
        { "text": "Partial transcript...", "is_final": false }
        ```
    4.  **Finish**: Send `is_final: true` to close.

---

## Push Notifications

### Register FCM Token
Register a device for push notifications.

- **URL**: `/devices/fcm-token`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <token>`
- **Body**:
  ```json
  { "fcm_token": "device-token-123" }
  ```
- **Response**: `200 OK`
  ```json
  { "message": "Token registered" }
  ```

# Backend API Specification for `moment`

This document outlines the necessary backend APIs to support the `moment` iOS application features, including data synchronization, media storage, and AI processing.

## Base URL
`https://api.moment-app.com/v1`

## 1. Authentication
Standard JWT-based authentication to secure user data.
| Method | Endpoint | Description | | :--- | :--- | :--- | | `POST` | `/auth/register` | Create a new user account with email/password. |
| `POST` | `/auth/login` | Authenticate user and return `access_token` and `refresh_token`. |
| `POST` | `/auth/refresh` | Obtain a new `access_token` using a valid `refresh_token`. |
| `POST` | `/auth/logout` | Invalidate the current session/token. |
| `GET` | `/auth/me` | Get current user profile information. |
| `DELETE` | `/auth/me` | Delete user account and all associated data (GDPR compliance). |

## 2. Note Synchronization (Data Sync)
To keep local Core Data in sync with the cloud. This uses a "Delta Sync" approach: clients send their local changes and request changes that happened since their last sync.

**Entities**: Notes, Tags, TodoItems.

| Method | Endpoint | Description |å
| :--- | :--- | :--- |
| `POST` | `/sync` | **Main Sync Endpoint**. Accepts a batch of changes (creates, updates, deletes) and a `last_synced_timestamp`. Returns new server-side changes since that timestamp. |
| `GET` | `/notes` | Fetch all notes (paginated). Useful for initial device setup or "restore". |
| `GET` | `/notes/:id` | Fetch a specific note's full details. |

### Sync Payload Example
```json
{
  "last_synced_at": "2023-10-27T10:00:00Z",
  "changes": {
    "notes": { "created": [...], "updated": [...], "deleted": ["uuid-1"] },
    "tags": { ... }
  }
}
```

## 3. Media Management (Audio & Images)
Direct file uploads to the server are often slow and resource-intensive. The recommended "Real World" pattern is to use **Presigned URLs** (e.g., AWS S3, Google Cloud Storage) to let the client upload directly to cloud storage.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/storage/presigned-url` | Request a temporary URL to upload a file (Audio or Image). <br>Input: `{ "filename": "uuid.m4a", "content_type": "audio/m4a" }` <br>Output: `{ "upload_url": "https://s3.aws...", "file_key": "users/123/audio/uuid.m4a" }` |
| `GET` | `/storage/file/:file_key` | Get a temporary download URL for a private file. |

**Workflow**:
1. App requests Presigned URL from Backend.
2. App uploads file directly to Cloud Storage (S3).
3. App syncs the `file_key` (path) in the `Note` entity via the `/sync` endpoint.

## 4. AI Services (Transcription & Summary)
Offloading heavy AI tasks to the backend allows for higher quality models (e.g., Whisper Large) than what's possible on-device.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/ai/transcribe` | **Async Transcription**. <br>Input: `{ "audio_file_key": "path/to/audio.m4a", "language": "en" }`. <br>Starts a background job and returns a `job_id`. |
| `GET` | `/ai/jobs/:id` | Poll status of a transcription/summary job. <br>Returns: `{ "status": "processing" | "completed", "result": "Transcribed text..." }` |
| `POST` | `/ai/summarize` | Generate a summary/title from text. <br>Input: `{ "text": "..." }` <br>Returns: `{ "summary": "...", "suggested_title": "..." }` |

## 5. Webhooks (Optional but Recommended)
Instead of polling `/ai/jobs/:id`, the server can push updates.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/devices/fcm-token` | Register a Firebase Cloud Messaging (FCM) token to receive push notifications when transcription completes. |

---

## Why these APIs?

1.  **Sync vs CRUD**: For an offline-first app like `moment` (Core Data), a `/sync` endpoint is far superior to individual GET/POST/PUT endpoints for every note. It ensures data consistency even if the user goes offline and comes back.
2.  **Presigned URLs**: Uploading large audio files (50MB+) through your API server will block threads and crash it. Offloading to S3 is the industry standard.
3.  **Async AI**: Transcription takes time (e.g., 30s audio takes ~3s). Keeping the HTTP connection open is risky (timeouts). An Async Job pattern (Start -> Poll/Notify) is reliable.

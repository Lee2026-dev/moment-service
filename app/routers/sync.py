from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.dependencies import get_supabase
from app.schemas_sync import EntityChanges, SyncRequest, SyncResponse

router = APIRouter(tags=["sync"])
security = HTTPBearer()


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def should_apply_updated_item(
    supabase: Client,
    entity_name: str,
    user_id: str,
    item_data: dict[str, Any],
) -> bool:
    item_id = item_data.get("id")
    if not item_id:
        return True

    incoming_updated_at = parse_iso_datetime(item_data.get("updated_at"))
    if incoming_updated_at is None:
        return True

    existing_res = (
        supabase.table(entity_name)
        .select("updated_at")
        .eq("id", item_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    existing_rows = existing_res.data or []
    if not existing_rows:
        return True

    existing_updated_at = parse_iso_datetime(existing_rows[0].get("updated_at"))
    if existing_updated_at is None:
        return True

    return incoming_updated_at >= existing_updated_at


def fetch_note_for_parent_lookup(
    supabase: Client,
    user_id: str,
    note_id: str,
    cache: dict[str, Optional[dict[str, Any]]],
) -> Optional[dict[str, Any]]:
    if note_id in cache:
        return cache[note_id]

    res = (
        supabase.table("notes")
        .select("id,parent_note_id,deleted_at")
        .eq("id", note_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    cache[note_id] = rows[0] if rows else None
    return cache[note_id]


def normalize_note_parent_link(
    supabase: Client,
    user_id: str,
    item_data: dict[str, Any],
    payload_note_map: dict[str, dict[str, Any]],
    payload_deleted_ids: set[str],
    note_lookup_cache: dict[str, Optional[dict[str, Any]]],
) -> None:
    parent_note_id = item_data.get("parent_note_id")
    if not isinstance(parent_note_id, str) or not parent_note_id:
        return

    note_id = item_data.get("id")
    if isinstance(note_id, str) and note_id == parent_note_id:
        item_data["parent_note_id"] = None
        return

    visited_ids: set[str] = set()
    if isinstance(note_id, str) and note_id:
        visited_ids.add(note_id)

    current_parent_id = parent_note_id
    while True:
        if current_parent_id in visited_ids:
            item_data["parent_note_id"] = None
            return
        visited_ids.add(current_parent_id)

        if current_parent_id in payload_deleted_ids:
            item_data["parent_note_id"] = None
            return

        payload_parent_note = payload_note_map.get(current_parent_id)
        if payload_parent_note is not None:
            next_parent_id = payload_parent_note.get("parent_note_id")
            if not isinstance(next_parent_id, str) or not next_parent_id:
                item_data["parent_note_id"] = current_parent_id
                return
            current_parent_id = next_parent_id
            continue

        server_parent_note = fetch_note_for_parent_lookup(
            supabase=supabase,
            user_id=user_id,
            note_id=current_parent_id,
            cache=note_lookup_cache,
        )
        if not server_parent_note or server_parent_note.get("deleted_at"):
            item_data["parent_note_id"] = None
            return

        next_parent_id = server_parent_note.get("parent_note_id")
        if not isinstance(next_parent_id, str) or not next_parent_id:
            item_data["parent_note_id"] = current_parent_id
            return

        current_parent_id = next_parent_id


@router.post("/sync", response_model=SyncResponse)
def sync_data(
    req: SyncRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase),
):
    token = credentials.credentials

    print("req::::::", req)

    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = user_res.user

        notes_changes = req.changes.get("notes")
        payload_note_map: dict[str, dict[str, Any]] = {}
        payload_deleted_note_ids: set[str] = set()
        if notes_changes is not None:
            for note_item in notes_changes.created + notes_changes.updated:
                note_id = note_item.get("id")
                if isinstance(note_id, str) and note_id:
                    payload_note_map[note_id] = note_item
            for deleted_note_id in notes_changes.deleted:
                if isinstance(deleted_note_id, str) and deleted_note_id:
                    payload_deleted_note_ids.add(deleted_note_id)

        note_lookup_cache: dict[str, Optional[dict[str, Any]]] = {}

        # Define strict processing order to satisfy Foreign Key constraints
        # 1. Parents (Notes) -> 2. Children (Todos, Images) -> 3. Independent/Related (Tags)
        processing_order = ["notes", "tags", "todo_items", "note_images"]

        # Process entities in strict order
        for entity_name in processing_order:
            if entity_name not in req.changes:
                continue

            changes = req.changes[entity_name]

            items_to_upsert = []
            for item in changes.created:
                item_data = item.copy()
                item_data["user_id"] = user.id
                if not item_data.get("updated_at"):
                    item_data["updated_at"] = datetime.now(timezone.utc).isoformat()

                if entity_name == "notes":
                    normalize_note_parent_link(
                        supabase=supabase,
                        user_id=user.id,
                        item_data=item_data,
                        payload_note_map=payload_note_map,
                        payload_deleted_ids=payload_deleted_note_ids,
                        note_lookup_cache=note_lookup_cache,
                    )
                items_to_upsert.append(item_data)

            for item in changes.updated:
                item_data = item.copy()
                item_data["user_id"] = user.id
                if not item_data.get("updated_at"):
                    item_data["updated_at"] = datetime.now(timezone.utc).isoformat()

                if should_apply_updated_item(supabase, entity_name, user.id, item_data):
                    if entity_name == "notes":
                        normalize_note_parent_link(
                            supabase=supabase,
                            user_id=user.id,
                            item_data=item_data,
                            payload_note_map=payload_note_map,
                            payload_deleted_ids=payload_deleted_note_ids,
                            note_lookup_cache=note_lookup_cache,
                        )
                    items_to_upsert.append(item_data)
                else:
                    print(f"Skip stale update for {entity_name}:{item_data.get('id')}")

            if items_to_upsert:
                supabase.table(entity_name).upsert(items_to_upsert).execute()

            if changes.deleted:
                deleted_at = datetime.now(timezone.utc).isoformat()
                (
                    supabase.table(entity_name)
                    .update({"deleted_at": deleted_at, "updated_at": deleted_at})
                    .in_("id", changes.deleted)
                    .eq("user_id", user.id)
                    .execute()
                )

        server_changes = {}
        tables = ["notes", "tags", "todo_items"]

        current_time = datetime.now(timezone.utc)
        for table in tables:
            query = supabase.table(table).select("*").eq("user_id", user.id)
            if req.last_synced_at:
                query = query.gt("updated_at", req.last_synced_at.isoformat())

            res = query.execute()
            rows = res.data

            entity_changes = EntityChanges()

            for row in rows:
                if row.get("deleted_at"):
                    entity_changes.deleted.append(row["id"])
                else:
                    # Sanitize row to prevent null values for fields the client expects to be non-optional Strings
                    if table == "notes":
                        if row.get("content") is None:
                            row["content"] = ""
                        if row.get("title") is None:
                            row["title"] = ""
                        if row.get("transcript") is None:
                            row["transcript"] = ""
                        if row.get("transcript_segments") is None:
                            row["transcript_segments"] = ""
                    elif table == "todo_items":
                        if row.get("text") is None:
                            row["text"] = ""
                    elif table == "tags":
                        if row.get("name") is None:
                            row["name"] = ""

                    entity_changes.updated.append(row)

            if (
                entity_changes.created
                or entity_changes.updated
                or entity_changes.deleted
            ):
                server_changes[table] = entity_changes
        return SyncResponse(changes=server_changes, last_synced_at=current_time)

    except Exception as e:
        print(e)
        error_msg = str(e).lower()
        if (
            "expired" in error_msg
            or "invalid token" in error_msg
            or "invalid jwt" in error_msg
        ):
            raise HTTPException(status_code=401, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client
from app.dependencies import get_supabase
from app.schemas_sync import SyncRequest, SyncResponse, EntityChanges
from datetime import datetime, timezone

router = APIRouter(tags=["sync"])
security = HTTPBearer()

@router.post("/sync", response_model=SyncResponse)
def sync_data(
    req: SyncRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
):
    token = credentials.credentials

    print("req::::::", req)

    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
             raise HTTPException(status_code=401, detail="Invalid token")
        user = user_res.user

        # Define strict processing order to satisfy Foreign Key constraints
        # 1. Parents (Notes) -> 2. Children (Todos, Images) -> 3. Independent/Related (Tags)
        processing_order = ["notes", "tags", "todo_items", "note_images"]
        
        # Process entities in strict order
        for entity_name in processing_order:
            if entity_name not in req.changes:
                continue
                
            changes = req.changes[entity_name]
            
            items_to_upsert = []
            for item in changes.created + changes.updated:
                item_data = item.copy()
                item_data["user_id"] = user.id
                item_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                items_to_upsert.append(item_data)
            
            if items_to_upsert:
                supabase.table(entity_name).upsert(items_to_upsert).execute()
            
            if changes.deleted:
                 deleted_at = datetime.now(timezone.utc).isoformat()
                 supabase.table(entity_name)\
                    .update({"deleted_at": deleted_at, "updated_at": deleted_at})\
                    .in_("id", changes.deleted)\
                    .eq("user_id", user.id)\
                    .execute()

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
                        if row.get("content") is None: row["content"] = ""
                        if row.get("title") is None: row["title"] = ""
                        if row.get("transcript") is None: row["transcript"] = ""
                    elif table == "todo_items":
                        if row.get("text") is None: row["text"] = ""
                    elif table == "tags":
                        if row.get("name") is None: row["name"] = ""
                    
                    entity_changes.updated.append(row)
            
                        
            if entity_changes.created or entity_changes.updated or entity_changes.deleted:
                server_changes[table] = entity_changes
        return SyncResponse(
            changes=server_changes,
            last_synced_at=current_time
        )

    except Exception as e:
        print(e)
        error_msg = str(e).lower()
        if "expired" in error_msg or "invalid token" in error_msg or "invalid jwt" in error_msg:
             raise HTTPException(status_code=401, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

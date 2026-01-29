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
    try:
        user_res = supabase.auth.get_user(token)
        user = user_res.user
        if not user:
             raise HTTPException(status_code=401, detail="Invalid token")

        for entity_name, changes in req.changes.items():
            if entity_name not in ["notes", "tags", "todo_items"]:
                continue
            
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
                    entity_changes.updated.append(row)
            
            if entity_changes.created or entity_changes.updated or entity_changes.deleted:
                server_changes[table] = entity_changes
                
        return SyncResponse(
            changes=server_changes,
            last_synced_at=current_time
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

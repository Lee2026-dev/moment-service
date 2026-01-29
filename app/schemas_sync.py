from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime

class EntityChanges(BaseModel):
    created: List[Dict[str, Any]] = []
    updated: List[Dict[str, Any]] = []
    deleted: List[str] = []

class SyncRequest(BaseModel):
    last_synced_at: Optional[datetime] = None
    changes: Dict[str, EntityChanges] = {}

class SyncResponse(BaseModel):
    changes: Dict[str, EntityChanges]
    last_synced_at: datetime

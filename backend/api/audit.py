from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from models.database import get_db
from models.db_models import AuditLog

router = APIRouter()


@router.get("/")
async def list_audit_logs(
    limit: int = 100,
    offset: int = 0,
    lineage_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
    if lineage_id:
        query = query.where(AuditLog.lineage_id == lineage_id)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp.isoformat(),
            "analyst_hash": l.analyst_hash[:8] + "****",
            "action": l.action,
            "lineage_id": l.lineage_id,
            "detail": l.detail,
            "system_hash": l.system_hash[:16] + "...",
        }
        for l in logs
    ]

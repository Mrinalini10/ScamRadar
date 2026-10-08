from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from models.database import get_db
from models.db_models import Lineage, Complaint, Identifier, Alert, AuditLog
from ml.nowcasting import run_nowcast_for_lineage
from ml.cusum import analyze_lineage_alerts
from utils.helpers import compute_audit_hash

router = APIRouter()


@router.get("/")
async def list_lineages(
    status: Optional[str] = None,
    growth_rate: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all lineages with optional filters."""
    query = select(Lineage).order_by(Lineage.last_updated.desc())
    if status:
        query = query.where(Lineage.status == status)
    if growth_rate:
        query = query.where(Lineage.growth_rate == growth_rate)
    
    result = await db.execute(query)
    lineages = result.scalars().all()
    
    return [_lineage_summary(l) for l in lineages]


@router.get("/{lineage_id}")
async def get_lineage_detail(lineage_id: str, db: AsyncSession = Depends(get_db)):
    """Full lineage detail including complaints, identifiers, nowcast, and CUSUM."""
    result = await db.execute(select(Lineage).where(Lineage.id == lineage_id))
    lineage = result.scalar_one_or_none()
    if not lineage:
        raise HTTPException(404, "Lineage not found")
    
    # Get complaints
    r = await db.execute(
        select(Complaint).where(Complaint.lineage_id == lineage_id)
        .order_by(Complaint.reported_date.desc()).limit(100)
    )
    complaints = r.scalars().all()
    
    # Get identifiers
    r2 = await db.execute(
        select(Identifier).where(Identifier.lineage_id == lineage_id)
    )
    identifiers = r2.scalars().all()
    
    # Run nowcasting
    complaints_dict = [{"reported_date": c.reported_date.isoformat()} for c in complaints]
    nowcast = run_nowcast_for_lineage(complaints_dict)

    # Run CUSUM
    cross_bank = len(lineage.banks_involved) if lineage.banks_involved else 1
    alert_analysis = analyze_lineage_alerts(
        lineage_id=lineage_id,
        nowcast_result=nowcast,
        cross_bank_count=cross_bank,
        churn_rate=lineage.churn_rate,
        complaint_count=lineage.complaint_count,
    )

    # Persist nowcast + growth rate back to DB
    from datetime import datetime as _dt
    lineage.nowcast_count = nowcast["total_nowcast"]
    lineage.growth_rate = alert_analysis["growth_rate"]
    lineage.last_updated = _dt.utcnow()
    await db.commit()

    return {
        "id": lineage.id,
        "name": lineage.name,
        "script_type": lineage.script_type,
        "act_sequence": lineage.act_sequence,
        "created_date": lineage.created_date.isoformat(),
        "complaint_count": lineage.complaint_count,
        "nowcast_count": round(nowcast["total_nowcast"], 1),
        "growth_rate": alert_analysis["growth_rate"],
        "status": lineage.status,
        "churn_rate": lineage.churn_rate,
        "language_distribution": lineage.language_distribution,
        "banks_count": cross_bank,
        "rt": nowcast["rt"],
        "daily_counts": nowcast["daily_counts"],
        "cusum_series": alert_analysis.get("cusum_series", []),
        "cusum_triggered": alert_analysis["cusum_triggered"],
        "identifiers": [
            {
                "id": i.id,
                "type": i.id_type,
                "display_value": i.display_value,
                "first_seen": i.first_seen.isoformat(),
                "last_seen": i.last_seen.isoformat(),
                "complaint_count": i.complaint_count,
            }
            for i in identifiers
        ],
        "complaints": [
            {
                "id": c.id,
                "raw_text": c.raw_text[:80] + "..." if len(c.raw_text) > 80 else c.raw_text,
                "reported_date": c.reported_date.isoformat(),
                "source_bank": c.source_bank,
                "language": c.language,
                "analyst_tags": c.analyst_tags,
            }
            for c in complaints
        ],
    }


@router.patch("/{lineage_id}/status")
async def update_lineage_status(
    lineage_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update lineage status (Mark as Variant of Concern, Resolve, etc.)."""
    result = await db.execute(select(Lineage).where(Lineage.id == lineage_id))
    lineage = result.scalar_one_or_none()
    if not lineage:
        raise HTTPException(404, "Lineage not found")
    
    new_status = body.get("status")
    analyst_hash = body.get("analyst_hash", "anonymous")
    note = body.get("note", "")
    
    if new_status:
        lineage.status = new_status
    if body.get("growth_rate"):
        lineage.growth_rate = body["growth_rate"]
    
    # Write audit log
    from datetime import datetime
    ts = datetime.utcnow().isoformat()
    audit = AuditLog(
        analyst_hash=analyst_hash,
        action=f"STATUS_UPDATE:{new_status}",
        lineage_id=lineage_id,
        detail=note,
        system_hash=compute_audit_hash(analyst_hash, f"STATUS_UPDATE:{new_status}", lineage_id, note, ts),
    )
    db.add(audit)
    await db.commit()
    
    return {"ok": True, "lineage_id": lineage_id, "new_status": new_status}


def _lineage_summary(l: Lineage) -> dict:
    return {
        "id": l.id,
        "name": l.name,
        "script_type": l.script_type,
        "language_mix": list(l.language_distribution.keys()) if l.language_distribution else [],
        "complaint_count": l.complaint_count,
        "nowcast_count": l.nowcast_count,
        "growth_rate": l.growth_rate,
        "status": l.status,
        "churn_rate": l.churn_rate,
        "banks_count": len(l.banks_involved) if l.banks_involved else 0,
        "last_updated": l.last_updated.isoformat(),
    }

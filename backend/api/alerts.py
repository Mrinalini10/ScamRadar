from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from models.database import get_db
from models.db_models import Alert, Lineage, AuditLog
from utils.helpers import compute_audit_hash

router = APIRouter()


@router.get("/")
async def list_alerts(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(Alert).order_by(Alert.created_at.desc()).limit(100)
    if status:
        query = query.where(Alert.status == status)
    result = await db.execute(query)
    alerts = result.scalars().all()
    return [_alert_dict(a) for a in alerts]


@router.post("/generate")
async def generate_alerts(db: AsyncSession = Depends(get_db)):
    """Scan all lineages and generate alerts for rising/critical ones."""
    from ml.nowcasting import run_nowcast_for_lineage
    from ml.cusum import analyze_lineage_alerts

    result = await db.execute(
        select(Lineage).where(Lineage.status != "Resolved")
    )
    lineages = result.scalars().all()

    from models.db_models import Complaint
    generated = 0

    for lineage in lineages:
        r = await db.execute(
            select(Complaint).where(Complaint.lineage_id == lineage.id)
        )
        complaints = r.scalars().all()
        complaints_dict = [{"reported_date": c.reported_date.isoformat()} for c in complaints]

        nowcast = run_nowcast_for_lineage(complaints_dict)
        cross_bank = len(lineage.banks_involved) if lineage.banks_involved else 1
        analysis = analyze_lineage_alerts(
            lineage_id=lineage.id,
            nowcast_result=nowcast,
            cross_bank_count=cross_bank,
            churn_rate=lineage.churn_rate,
            complaint_count=lineage.complaint_count,
        )

        # Update lineage growth rate
        lineage.growth_rate = analysis["growth_rate"]
        lineage.nowcast_count = nowcast["total_nowcast"]

        if analysis["should_alert"]:
            # Check if active alert already exists for this lineage
            existing = await db.execute(
                select(Alert).where(
                    Alert.lineage_id == lineage.id,
                    Alert.status == "Active",
                )
            )
            if not existing.scalar_one_or_none():
                alert = Alert(
                    lineage_id=lineage.id,
                    lineage_name=lineage.name,
                    trigger_reason=analysis["trigger_reason"],
                    script_type=lineage.script_type,
                    nowcast_count=nowcast["total_nowcast"],
                    recommended_action=analysis["recommended_action"],
                    status="Active",
                )
                db.add(alert)
                generated += 1

    await db.commit()
    return {"generated": generated}


@router.patch("/{alert_id}")
async def update_alert(alert_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")

    new_status = body.get("status")
    analyst_hash = body.get("analyst_hash", "anonymous")
    reason = body.get("dismissed_reason")

    if new_status:
        alert.status = new_status
    if reason:
        alert.dismissed_reason = reason
    if analyst_hash:
        alert.acknowledged_by = analyst_hash
    alert.updated_at = datetime.utcnow()

    ts = datetime.utcnow().isoformat()
    db.add(AuditLog(
        analyst_hash=analyst_hash,
        action=f"ALERT_{new_status}",
        lineage_id=alert.lineage_id,
        detail=reason or new_status,
        system_hash=compute_audit_hash(analyst_hash, f"ALERT_{new_status}", alert.lineage_id, reason, ts),
    ))

    await db.commit()
    return {"ok": True}


def _alert_dict(a: Alert) -> dict:
    return {
        "id": a.id,
        "lineage_id": a.lineage_id,
        "lineage_name": a.lineage_name,
        "trigger_reason": a.trigger_reason,
        "script_type": a.script_type,
        "nowcast_count": a.nowcast_count,
        "recommended_action": a.recommended_action,
        "status": a.status,
        "dismissed_reason": a.dismissed_reason,
        "acknowledged_by": a.acknowledged_by,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from models.database import get_db
from models.db_models import Complaint, Lineage, Alert, AuditLog
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Dashboard overview stats."""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    # Total complaints today
    result = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.ingested_date >= today_start)
    )
    complaints_today = result.scalar() or 0

    # Active lineages
    result = await db.execute(
        select(func.count(Lineage.id)).where(Lineage.status != "Resolved")
    )
    active_lineages = result.scalar() or 0

    # Variants of concern (Critical)
    result = await db.execute(
        select(func.count(Lineage.id)).where(Lineage.growth_rate == "Critical")
    )
    variants_of_concern = result.scalar() or 0

    # Total nowcast vs observed
    result = await db.execute(
        select(func.sum(Lineage.nowcast_count), func.sum(Lineage.complaint_count))
    )
    row = result.first()
    nowcast_total = float(row[0] or 0)
    observed_total = int(row[1] or 0)
    estimated_unreported = max(0, round(nowcast_total - observed_total))

    # Active alerts
    result = await db.execute(
        select(func.count(Alert.id)).where(Alert.status == "Active")
    )
    active_alerts = result.scalar() or 0

    # Recent lineages (last 10)
    result = await db.execute(
        select(Lineage).order_by(Lineage.last_updated.desc()).limit(10)
    )
    recent_lineages = result.scalars().all()

    lineages_data = []
    for l in recent_lineages:
        lineages_data.append({
            "id": l.id,
            "name": l.name,
            "script_type": l.script_type,
            "language_mix": list(l.language_distribution.keys()) if l.language_distribution else [],
            "complaint_count": l.complaint_count,
            "nowcast_count": l.nowcast_count,
            "growth_rate": l.growth_rate,
            "status": l.status,
            "churn_rate": l.churn_rate,
            "banks_involved": len(l.banks_involved) if l.banks_involved else 0,
        })

    return {
        "complaints_today": complaints_today,
        "active_lineages": active_lineages,
        "variants_of_concern": variants_of_concern,
        "estimated_unreported": estimated_unreported,
        "active_alerts": active_alerts,
        "lineages": lineages_data,
    }


@router.get("/activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)):
    """Last 7 days complaint activity for chart."""
    results = []
    for i in range(6, -1, -1):
        d = datetime.utcnow().date() - timedelta(days=i)
        d_start = datetime.combine(d, datetime.min.time())
        d_end = d_start + timedelta(days=1)
        r = await db.execute(
            select(func.count(Complaint.id)).where(
                Complaint.reported_date >= d_start,
                Complaint.reported_date < d_end,
            )
        )
        results.append({"date": str(d), "count": r.scalar() or 0})
    return results

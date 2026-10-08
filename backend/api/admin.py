from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_db
from models.db_models import AdminConfig

router = APIRouter()


@router.get("/config")
async def get_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AdminConfig).where(AdminConfig.id == "global"))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = AdminConfig(id="global")
        db.add(cfg)
        await db.commit()
    return {
        "delay_instant_pct": cfg.delay_instant_pct,
        "delay_normal_pct": cfg.delay_normal_pct,
        "delay_tail_pct": cfg.delay_tail_pct,
        "alert_threshold_daily": cfg.alert_threshold_daily,
        "psi_min_banks": cfg.psi_min_banks,
        "psi_min_complaints": cfg.psi_min_complaints,
        "poison_report_cap": cfg.poison_report_cap,
    }


@router.put("/config")
async def update_config(body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AdminConfig).where(AdminConfig.id == "global"))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = AdminConfig(id="global")
        db.add(cfg)

    for key, val in body.items():
        if hasattr(cfg, key):
            setattr(cfg, key, val)

    await db.commit()
    return {"ok": True}

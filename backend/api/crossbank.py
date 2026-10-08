from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_db
from models.db_models import Lineage, Complaint, AdminConfig
from utils.helpers import find_cross_bank_lineages, psi_hash_identifier

router = APIRouter()


@router.get("/")
async def get_cross_bank_intelligence(db: AsyncSession = Depends(get_db)):
    """Identify campaigns spanning multiple banks (PSI-based, privacy-preserving)."""
    
    # Load admin config for thresholds
    cfg_result = await db.execute(select(AdminConfig).where(AdminConfig.id == "global"))
    cfg = cfg_result.scalar_one_or_none()
    min_banks = cfg.psi_min_banks if cfg else 2
    min_complaints = cfg.psi_min_complaints if cfg else 10

    # Build lineage → banks mapping
    result = await db.execute(select(Complaint))
    complaints = result.scalars().all()

    lineage_banks: dict[str, list[str]] = {}
    for c in complaints:
        if c.lineage_id:
            lineage_banks.setdefault(c.lineage_id, []).append(c.source_bank)

    # Find cross-bank lineages
    cross_bank = find_cross_bank_lineages(lineage_banks, min_banks, min_complaints)

    # Enrich with lineage metadata
    enriched = []
    for item in cross_bank:
        r = await db.execute(select(Lineage).where(Lineage.id == item["lineage_id"]))
        lineage = r.scalar_one_or_none()
        if lineage:
            enriched.append({
                "lineage_id": item["lineage_id"],
                "lineage_name": lineage.name,
                "script_type": lineage.script_type,
                "bank_count": item["bank_count"],         # count only, never which banks
                "total_complaints": item["total_complaints"],
                "overlap_score": item["overlap_score"],
                "growth_rate": lineage.growth_rate,
            })

    return {
        "privacy_notice": "No raw complaint data is shared between institutions. Only anonymised campaign sketches are compared.",
        "threshold": {"min_banks": min_banks, "min_complaints": min_complaints},
        "campaigns": enriched,
    }

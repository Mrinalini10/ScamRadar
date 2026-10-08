from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import asyncio

from models.database import get_db, AsyncSessionLocal
from models.db_models import Complaint, Lineage
from ml.dataset import load_dataset, preprocess_and_save
from ml.tagger import tag_complaint
from ml.lineage import assign_complaint_to_lineage, register_lineage_in_lsh, text_to_minhash, minhash_to_list, get_or_create_profile
from utils.helpers import extract_identifiers, hash_value, mask_value, generate_reporter_hash, generate_lineage_name
from datetime import datetime

router = APIRouter()

_ingest_progress = {"total": 0, "done": 0, "status": "idle"}


@router.get("/status")
async def dataset_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count(Complaint.id)))
    complaint_count = result.scalar() or 0
    result2 = await db.execute(select(func.count(Lineage.id)))
    lineage_count = result2.scalar() or 0
    return {
        "complaint_count": complaint_count,
        "lineage_count": lineage_count,
        "ingest_progress": _ingest_progress,
    }


@router.post("/load")
async def load_and_ingest(background_tasks: BackgroundTasks):
    """Load the Mendeley + synthetic dataset and ingest all complaints in background."""
    if _ingest_progress["status"] == "running":
        return {"status": "already_running", "progress": _ingest_progress}
    background_tasks.add_task(_run_ingest)
    return {"status": "started"}


async def _run_ingest():
    global _ingest_progress
    _ingest_progress = {"total": 0, "done": 0, "status": "running"}

    try:
        raw = load_dataset()
        _ingest_progress["total"] = len(raw)

        async with AsyncSessionLocal() as db:
            for item in raw:
                try:
                    tagged = tag_complaint(item["raw_text"], item.get("language", "auto"))

                    result = await db.execute(select(Lineage))
                    lineages = result.scalars().all()
                    lineages_dict = [
                        {"id": l.id, "act_sequence": l.act_sequence, "minhash_signature": l.minhash_signature}
                        for l in lineages
                    ]

                    lineage_id, confidence = assign_complaint_to_lineage(tagged.act_sequence, lineages_dict)

                    if lineage_id is None:
                        new_lineage = Lineage(
                            name=generate_lineage_name(tagged.script_type),
                            script_type=tagged.script_type,
                            act_sequence=tagged.act_sequence,
                            complaint_count=1,
                            nowcast_count=1.0,
                            growth_rate="Slow",
                            status="Monitoring",
                            churn_rate="Low",
                            language_distribution={tagged.language: 1},
                            banks_involved=[item.get("source_bank", "Bank_A")],
                            minhash_signature=minhash_to_list(text_to_minhash(tagged.act_sequence)),
                        )
                        db.add(new_lineage)
                        await db.flush()
                        lineage_id = new_lineage.id
                        register_lineage_in_lsh(lineage_id, tagged.act_sequence)
                        get_or_create_profile(lineage_id, tagged.act_sequence)
                    else:
                        r = await db.execute(select(Lineage).where(Lineage.id == lineage_id))
                        lineage = r.scalar_one()
                        lineage.complaint_count += 1
                        lang_dist = lineage.language_distribution or {}
                        lang_dist[tagged.language] = lang_dist.get(tagged.language, 0) + 1
                        lineage.language_distribution = lang_dist

                    ids = extract_identifiers(item["raw_text"])
                    complaint = Complaint(
                        raw_text=item["raw_text"],
                        reported_date=datetime.fromisoformat(item["reported_date"]),
                        source_bank=item.get("source_bank", "Bank_A"),
                        language=tagged.language,
                        script_type=tagged.script_type,
                        act_sequence=tagged.act_sequence,
                        lineage_id=lineage_id,
                        lineage_confidence=confidence,
                        phone_hash=hash_value(ids["phones"][0]) if ids["phones"] else None,
                        phone_last4=mask_value(ids["phones"][0]) if ids["phones"] else None,
                        upi_hash=hash_value(ids["upis"][0]) if ids["upis"] else None,
                        upi_last4=mask_value(ids["upis"][0]) if ids["upis"] else None,
                        url_hash=hash_value(ids["urls"][0]) if ids["urls"] else None,
                        reporter_hash=item.get("reporter_hash", "auto"),
                        label=item.get("label", "smishing"),
                    )
                    db.add(complaint)

                    _ingest_progress["done"] += 1

                    # Commit in batches
                    if _ingest_progress["done"] % 50 == 0:
                        await db.commit()
                        await asyncio.sleep(0)

                except Exception as e:
                    continue

            await db.commit()

        _ingest_progress["status"] = "done"

    except Exception as e:
        _ingest_progress["status"] = f"error: {str(e)}"

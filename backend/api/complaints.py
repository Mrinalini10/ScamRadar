from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import csv
import io

from models.database import get_db
from models.db_models import Complaint, Lineage, Identifier, AuditLog
from ml.tagger import tag_complaint
from ml.lineage import assign_complaint_to_lineage, register_lineage_in_lsh, text_to_minhash, minhash_to_list, get_or_create_profile
from utils.helpers import extract_identifiers, hash_value, mask_value, generate_reporter_hash, generate_lineage_name, compute_audit_hash

router = APIRouter()


class ComplaintCreate(BaseModel):
    raw_text: str
    reported_date: str  # ISO format
    source_bank: str
    language: Optional[str] = "auto"


class ComplaintBulkItem(BaseModel):
    raw_text: str
    reported_date: str
    source_bank: str
    language: Optional[str] = "auto"


@router.post("/ingest")
async def ingest_complaint(data: ComplaintCreate, db: AsyncSession = Depends(get_db)):
    """Ingest a single complaint, tag, and assign to lineage."""
    
    # Tag the complaint
    tagged = tag_complaint(data.raw_text, data.language)
    
    # Extract identifiers
    ids = extract_identifiers(data.raw_text)
    
    phone_hash = hash_value(ids["phones"][0]) if ids["phones"] else None
    phone_last4 = mask_value(ids["phones"][0]) if ids["phones"] else None
    upi_hash = hash_value(ids["upis"][0]) if ids["upis"] else None
    upi_last4 = mask_value(ids["upis"][0]) if ids["upis"] else None
    url_hash = hash_value(ids["urls"][0]) if ids["urls"] else None
    
    reporter_hash = generate_reporter_hash(data.raw_text, data.source_bank)
    
    # Fetch existing lineages
    result = await db.execute(select(Lineage))
    lineages = result.scalars().all()
    lineages_dict = [{"id": l.id, "act_sequence": l.act_sequence, "minhash_signature": l.minhash_signature} for l in lineages]
    
    # Assign to lineage
    lineage_id, confidence = assign_complaint_to_lineage(tagged.act_sequence, lineages_dict)
    
    # If no match, create new lineage
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
            banks_involved=[data.source_bank],
            minhash_signature=minhash_to_list(text_to_minhash(tagged.act_sequence)),
        )
        db.add(new_lineage)
        await db.flush()
        lineage_id = new_lineage.id
        register_lineage_in_lsh(lineage_id, tagged.act_sequence)
        get_or_create_profile(lineage_id, tagged.act_sequence)
    else:
        # Update existing lineage
        result = await db.execute(select(Lineage).where(Lineage.id == lineage_id))
        lineage = result.scalar_one()
        lineage.complaint_count += 1
        lang_dist = lineage.language_distribution or {}
        lang_dist[tagged.language] = lang_dist.get(tagged.language, 0) + 1
        lineage.language_distribution = lang_dist
        if data.source_bank not in (lineage.banks_involved or []):
            banks = lineage.banks_involved or []
            banks.append(data.source_bank)
            lineage.banks_involved = banks
        # Recompute nowcast_count: apply a simple 1.5x correction for recent complaints
        # (full recalculation happens in lineage detail / alert scan)
        lineage.nowcast_count = round(lineage.complaint_count * 1.2, 1)
    
    # Create complaint record
    complaint = Complaint(
        raw_text=data.raw_text,
        reported_date=datetime.fromisoformat(data.reported_date),
        source_bank=data.source_bank,
        language=tagged.language,
        script_type=tagged.script_type,
        act_sequence=tagged.act_sequence,
        lineage_id=lineage_id,
        lineage_confidence=confidence,
        phone_hash=phone_hash,
        upi_hash=upi_hash,
        url_hash=url_hash,
        phone_last4=phone_last4,
        upi_last4=upi_last4,
        reporter_hash=reporter_hash,
    )
    db.add(complaint)
    
    # Update identifiers table
    if phone_hash:
        db.add(Identifier(id_type="phone", value_hash=phone_hash, display_value=phone_last4, lineage_id=lineage_id))
    if upi_hash:
        db.add(Identifier(id_type="upi", value_hash=upi_hash, display_value=upi_last4, lineage_id=lineage_id))
    if url_hash:
        db.add(Identifier(id_type="url", value_hash=url_hash, display_value="****", lineage_id=lineage_id))
    
    await db.commit()
    await db.refresh(complaint)
    
    return {
        "id": complaint.id,
        "lineage_id": lineage_id,
        "lineage_confidence": confidence,
        "script_type": tagged.script_type,
        "language": tagged.language,
        "act_sequence": tagged.act_sequence,
        "created_new_lineage": confidence < 0.35,
    }


@router.get("/")
async def list_complaints(
    limit: int = 50,
    offset: int = 0,
    lineage_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List complaints with pagination."""
    query = select(Complaint).order_by(Complaint.ingested_date.desc()).offset(offset).limit(limit)
    if lineage_id:
        query = query.where(Complaint.lineage_id == lineage_id)
    
    result = await db.execute(query)
    complaints = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "raw_text": c.raw_text[:100] + "..." if len(c.raw_text) > 100 else c.raw_text,
            "reported_date": c.reported_date.isoformat(),
            "ingested_date": c.ingested_date.isoformat(),
            "source_bank": c.source_bank,
            "language": c.language,
            "script_type": c.script_type,
            "lineage_id": c.lineage_id,
            "phone_last4": c.phone_last4,
            "upi_last4": c.upi_last4,
        }
        for c in complaints
    ]


@router.get("/{complaint_id}")
async def get_complaint(complaint_id: str, db: AsyncSession = Depends(get_db)):
    """Get full complaint details."""
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    
    return {
        "id": complaint.id,
        "raw_text": complaint.raw_text,
        "reported_date": complaint.reported_date.isoformat(),
        "ingested_date": complaint.ingested_date.isoformat(),
        "source_bank": complaint.source_bank,
        "language": complaint.language,
        "script_type": complaint.script_type,
        "act_sequence": complaint.act_sequence,
        "lineage_id": complaint.lineage_id,
        "lineage_confidence": complaint.lineage_confidence,
        "phone_last4": complaint.phone_last4,
        "upi_last4": complaint.upi_last4,
        "analyst_tags": complaint.analyst_tags,
    }


@router.post("/bulk")
async def bulk_ingest_csv(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Bulk ingest complaints from CSV. Expected columns: raw_text, reported_date, source_bank, language (optional)."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files supported")

    contents = await file.read()
    text_data = contents.decode('utf-8')
    lines = list(csv.DictReader(io.StringIO(text_data)))

    ingested = []
    failed = []

    for idx, row in enumerate(lines):
        try:
            raw_text = row.get('raw_text', '').strip()
            reported_date_str = row.get('reported_date', '').strip()
            source_bank = row.get('source_bank', 'Bank_A').strip()
            language = row.get('language', 'auto').strip()

            if not raw_text or not reported_date_str:
                failed.append({"row": idx + 1, "reason": "missing raw_text or reported_date"})
                continue

            # Tag and assign
            tagged = tag_complaint(raw_text, language)
            ids = extract_identifiers(raw_text)

            phone_hash = hash_value(ids["phones"][0]) if ids["phones"] else None
            phone_last4 = mask_value(ids["phones"][0]) if ids["phones"] else None
            upi_hash = hash_value(ids["upis"][0]) if ids["upis"] else None
            upi_last4 = mask_value(ids["upis"][0]) if ids["upis"] else None
            url_hash = hash_value(ids["urls"][0]) if ids["urls"] else None
            reporter_hash = generate_reporter_hash(raw_text, source_bank)

            result = await db.execute(select(Lineage))
            lineages = result.scalars().all()
            lineages_dict = [{"id": l.id, "act_sequence": l.act_sequence, "minhash_signature": l.minhash_signature} for l in lineages]

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
                    banks_involved=[source_bank],
                    minhash_signature=minhash_to_list(text_to_minhash(tagged.act_sequence)),
                )
                db.add(new_lineage)
                await db.flush()
                lineage_id = new_lineage.id
                register_lineage_in_lsh(lineage_id, tagged.act_sequence)
                get_or_create_profile(lineage_id, tagged.act_sequence)
            else:
                result = await db.execute(select(Lineage).where(Lineage.id == lineage_id))
                lineage = result.scalar_one()
                lineage.complaint_count += 1
                lang_dist = lineage.language_distribution or {}
                lang_dist[tagged.language] = lang_dist.get(tagged.language, 0) + 1
                lineage.language_distribution = lang_dist
                if source_bank not in (lineage.banks_involved or []):
                    banks = lineage.banks_involved or []
                    banks.append(source_bank)
                    lineage.banks_involved = banks
                lineage.nowcast_count = round(lineage.complaint_count * 1.2, 1)

            complaint = Complaint(
                raw_text=raw_text,
                reported_date=datetime.fromisoformat(reported_date_str),
                source_bank=source_bank,
                language=tagged.language,
                script_type=tagged.script_type,
                act_sequence=tagged.act_sequence,
                lineage_id=lineage_id,
                lineage_confidence=confidence,
                phone_hash=phone_hash,
                upi_hash=upi_hash,
                url_hash=url_hash,
                phone_last4=phone_last4,
                upi_last4=upi_last4,
                reporter_hash=reporter_hash,
            )
            db.add(complaint)

            if phone_hash:
                db.add(Identifier(id_type="phone", value_hash=phone_hash, display_value=phone_last4, lineage_id=lineage_id))
            if upi_hash:
                db.add(Identifier(id_type="upi", value_hash=upi_hash, display_value=upi_last4, lineage_id=lineage_id))
            if url_hash:
                db.add(Identifier(id_type="url", value_hash=url_hash, display_value="****", lineage_id=lineage_id))

            ingested.append(idx + 1)

            # Commit in batches
            if len(ingested) % 50 == 0:
                await db.commit()

        except Exception as e:
            failed.append({"row": idx + 1, "reason": str(e)})

    await db.commit()

    return {
        "ingested": len(ingested),
        "failed": len(failed),
        "failed_rows": failed[:10],  # return first 10 failures
    }


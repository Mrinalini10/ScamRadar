"""
Utility functions for ScamRadar.
Hashing, audit trail generation, PSI simulation, poisoning detection.
"""
import re
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Optional


SECRET_SALT = "scamradar-psi-salt-v1"


# ---------------------------------------------------------------------------
# Identifier extraction and hashing
# ---------------------------------------------------------------------------

PHONE_PATTERN = re.compile(r'(?:\+91|91|0)?[6-9]\d{9}')
UPI_PATTERN = re.compile(r'[\w.\-]+@(?:ybl|oksbi|okaxis|okicici|paytm|upi|okhdfcbank|ibl|axl|timecosmos|waicici|waaxis|wasbi|yesbank|sbi|cnrb|barodampay|kotak)\b', re.IGNORECASE)
URL_PATTERN = re.compile(r'https?://\S+|(?:www\.)?\w+\.(?:com|in|xyz|net|org|co\.in|info|online|site|click)\b', re.IGNORECASE)


def extract_identifiers(text: str) -> dict:
    """Extract phone numbers, UPI IDs, and URLs from complaint text."""
    phones = list(set(PHONE_PATTERN.findall(text)))
    upis = list(set(UPI_PATTERN.findall(text)))
    urls = list(set(URL_PATTERN.findall(text)))

    return {
        "phones": phones[:3],  # cap at 3 each
        "upis": upis[:3],
        "urls": urls[:3],
    }


def hash_value(value: str) -> str:
    """SHA-256 hash of a value with salt."""
    return hashlib.sha256(f"{SECRET_SALT}:{value}".encode()).hexdigest()


def mask_value(value: str) -> str:
    """Return masked display version (last 4 chars visible)."""
    if not value:
        return "****"
    clean = value.strip()
    if len(clean) <= 4:
        return "****"
    return "*" * (len(clean) - 4) + clean[-4:]


def generate_reporter_hash(text: str, bank: str) -> str:
    """Deterministic reporter hash from message + bank (anonymous)."""
    combo = f"{bank}:{text[:50]}"
    return hashlib.sha256(combo.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

def compute_audit_hash(
    analyst_hash: str,
    action: str,
    lineage_id: Optional[str],
    detail: Optional[str],
    timestamp: str,
) -> str:
    """Generate HMAC-SHA256 audit hash for tamper detection."""
    payload = json.dumps({
        "analyst": analyst_hash,
        "action": action,
        "lineage": lineage_id,
        "detail": detail,
        "ts": timestamp,
    }, sort_keys=True)
    return hmac.new(SECRET_SALT.encode(), payload.encode(), hashlib.sha256).hexdigest()  # type: ignore


# ---------------------------------------------------------------------------
# Private Set Intersection (PSI) simulation
# ---------------------------------------------------------------------------

def psi_hash_identifier(value: str, bank_id: str) -> str:
    """
    Keyed hash for PSI: same identifier from different banks
    produces the same hash (because key is shared salt, not bank-specific).
    In production this would use proper OPRF-based PSI.
    """
    return hashlib.sha256(f"{SECRET_SALT}:psi:{value}".encode()).hexdigest()


def compute_psi_overlap(
    bank_a_hashes: list[str],
    bank_b_hashes: list[str],
) -> dict:
    """
    Simulate PSI cardinality computation.
    Returns overlap count without revealing which identifiers match.
    """
    set_a = set(bank_a_hashes)
    set_b = set(bank_b_hashes)
    overlap = len(set_a & set_b)
    union = len(set_a | set_b)

    return {
        "overlap_count": overlap,
        "overlap_pct": round(overlap / union * 100, 1) if union > 0 else 0.0,
        "bank_a_count": len(set_a),
        "bank_b_count": len(set_b),
    }


def find_cross_bank_lineages(
    lineage_banks: dict[str, list[str]],
    min_banks: int = 2,
    min_complaints: int = 10,
) -> list[dict]:
    """
    Identify lineages seen in multiple banks.
    lineage_banks: {lineage_id: [list of bank_ids that reported it]}
    """
    results = []
    for lineage_id, banks in lineage_banks.items():
        unique_banks = list(set(banks))
        total_complaints = len(banks)
        if len(unique_banks) >= min_banks and total_complaints >= min_complaints:
            results.append({
                "lineage_id": lineage_id,
                "bank_count": len(unique_banks),
                "total_complaints": total_complaints,
                "overlap_score": round(len(unique_banks) / 3 * 100, 1),  # out of 3 banks
            })
    return results


# ---------------------------------------------------------------------------
# Poisoning detection
# ---------------------------------------------------------------------------

def check_poisoning(
    reporter_hash: str,
    lineage_id: str,
    recent_reports: list[dict],  # [{reporter_hash, lineage_id, timestamp}]
    time_window_hours: int = 24,
    cap: int = 5,
) -> bool:
    """
    Detect if a reporter is filing excessive complaints against one lineage
    (poisoning attempt to smear a legitimate merchant/account).
    """
    from datetime import timedelta
    now = datetime.utcnow()
    window_start = now - timedelta(hours=time_window_hours)

    count = sum(
        1 for r in recent_reports
        if r.get("reporter_hash") == reporter_hash
        and r.get("lineage_id") == lineage_id
        and datetime.fromisoformat(r.get("timestamp", "2000-01-01")) > window_start
    )

    return count >= cap


# ---------------------------------------------------------------------------
# Name generation for new lineages
# ---------------------------------------------------------------------------

LINEAGE_PREFIXES = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta",
    "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu",
    "Nu", "Xi", "Omicron", "Pi", "Rho", "Sigma",
    "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
]

_lineage_counter = {}


def generate_lineage_name(script_type: str) -> str:
    """Generate a unique lineage name like 'KYC_Fraud-Alpha-01'."""
    short = script_type.replace("_", "").upper()[:8]
    count = _lineage_counter.get(script_type, 0)
    prefix_idx = count % len(LINEAGE_PREFIXES)
    suffix = count // len(LINEAGE_PREFIXES) + 1
    _lineage_counter[script_type] = count + 1
    return f"{script_type}-{LINEAGE_PREFIXES[prefix_idx]}-{suffix:02d}"

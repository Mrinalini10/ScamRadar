"""
Lineage Engine for ScamRadar.
Uses MinHash for fast approximate similarity between act-sequence n-grams,
with a Profile HMM-inspired scoring model to assign complaints to lineages
and detect evolving script variants.
"""
import json
import hashlib
import numpy as np
from datasketch import MinHash, MinHashLSH
from collections import defaultdict
from typing import Optional
from ml.tagger import act_sequence_to_ngrams, tag_complaint

# MinHash configuration
NUM_PERM = 64           # lower perm count = faster, still accurate for short act seqs
SIMILARITY_THRESHOLD = 0.15  # Jaccard threshold (tuned for short 3-6 act sequences)
LSH_THRESHOLD = 0.1

# Global in-memory LSH index (backed by DB for persistence)
_lsh_index: Optional[MinHashLSH] = None
_lineage_minhashes: dict[str, MinHash] = {}  # lineage_id -> representative MinHash


def get_lsh() -> MinHashLSH:
    global _lsh_index
    if _lsh_index is None:
        _lsh_index = MinHashLSH(threshold=LSH_THRESHOLD, num_perm=NUM_PERM)
    return _lsh_index


def text_to_minhash(act_sequence: list[str]) -> MinHash:
    """Convert act sequence to MinHash signature via n-gram shingles."""
    m = MinHash(num_perm=NUM_PERM)
    ngrams = act_sequence_to_ngrams(act_sequence, n=2)
    # Also add unigrams
    ngrams += act_sequence_to_ngrams(act_sequence, n=1)
    for ng in ngrams:
        m.update(ng.encode("utf-8"))
    return m


def minhash_to_list(m: MinHash) -> list[int]:
    """Serialize MinHash to list for JSON storage."""
    return m.hashvalues.tolist()


def list_to_minhash(values: list[int]) -> MinHash:
    """Deserialize MinHash from stored list."""
    m = MinHash(num_perm=NUM_PERM)
    m.hashvalues = np.array(values, dtype=np.uint64)
    return m


def jaccard_similarity(m1: MinHash, m2: MinHash) -> float:
    """Estimate Jaccard similarity between two MinHash signatures."""
    return m1.jaccard(m2)


# ---------------------------------------------------------------------------
# Profile HMM-inspired lineage scoring
# ---------------------------------------------------------------------------

class LineageProfile:
    """
    Lightweight Profile HMM analog for a scam script lineage.
    Tracks the frequency of each act at each position in the sequence,
    allowing flexible matching (insertions/deletions in script structure).
    """

    def __init__(self, lineage_id: str, seed_sequence: list[str]):
        self.lineage_id = lineage_id
        self.act_counts = defaultdict(lambda: defaultdict(int))
        self.total_sequences = 0
        self.max_len = 0
        self.add_sequence(seed_sequence)

    def add_sequence(self, sequence: list[str]):
        """Update profile with a new observed act sequence."""
        self.total_sequences += 1
        self.max_len = max(self.max_len, len(sequence))
        for pos, act in enumerate(sequence):
            self.act_counts[pos][act] += 1

    def score_sequence(self, sequence: list[str]) -> float:
        """
        Score how well a sequence fits this profile.
        Uses emission probability at each position (like HMM emission).
        Returns log-likelihood normalized by sequence length.
        """
        if self.total_sequences == 0:
            return 0.0

        score = 0.0
        matched = 0

        for pos, act in enumerate(sequence):
            pos_counts = self.act_counts.get(pos, {})
            total_at_pos = sum(pos_counts.values())
            if total_at_pos > 0:
                # Laplace smoothed probability
                prob = (pos_counts.get(act, 0) + 0.1) / (total_at_pos + len(ACT_VOCAB) * 0.1)
                score += np.log(prob)
                matched += 1

        if matched == 0:
            return 0.0

        # Normalize
        normalized = score / max(len(sequence), 1)
        # Convert log-likelihood to 0-1 confidence
        confidence = 1.0 / (1.0 + np.exp(-normalized - 2))
        return float(confidence)

    def to_dict(self) -> dict:
        return {
            "lineage_id": self.lineage_id,
            "act_counts": {str(k): dict(v) for k, v in self.act_counts.items()},
            "total_sequences": self.total_sequences,
            "max_len": self.max_len,
        }


ACT_VOCAB = [
    "GREET", "IMPERSONATE", "URGENCY", "THREAT", "PRIZE",
    "PAYMENT_REQUEST", "LINK", "OTP_REQUEST", "PERSONAL_INFO_REQUEST",
    "CLOSE", "UNKNOWN"
]

# In-memory lineage profiles
_lineage_profiles: dict[str, LineageProfile] = {}


def get_or_create_profile(lineage_id: str, seed_sequence: list[str]) -> LineageProfile:
    if lineage_id not in _lineage_profiles:
        _lineage_profiles[lineage_id] = LineageProfile(lineage_id, seed_sequence)
    return _lineage_profiles[lineage_id]


def update_profile(lineage_id: str, act_sequence: list[str]):
    if lineage_id in _lineage_profiles:
        _lineage_profiles[lineage_id].add_sequence(act_sequence)


# ---------------------------------------------------------------------------
# Lineage assignment
# ---------------------------------------------------------------------------

def register_lineage_in_lsh(lineage_id: str, act_sequence: list[str]):
    """Add or update a lineage's MinHash in the LSH index."""
    lsh = get_lsh()
    m = text_to_minhash(act_sequence)
    _lineage_minhashes[lineage_id] = m
    try:
        lsh.insert(lineage_id, m)
    except ValueError:
        # Already inserted — remove and reinsert
        try:
            lsh.remove(lineage_id)
        except Exception:
            pass
        lsh.insert(lineage_id, m)


def find_matching_lineages(act_sequence: list[str]) -> list[tuple[str, float]]:
    """
    Find candidate lineages via LSH, then score each with Profile HMM.
    Returns list of (lineage_id, confidence) sorted by confidence desc.
    """
    if not act_sequence:
        return []

    lsh = get_lsh()
    query_m = text_to_minhash(act_sequence)

    # Step 1: LSH candidate retrieval (fast approximate)
    try:
        candidates = lsh.query(query_m)
    except Exception:
        candidates = list(_lineage_minhashes.keys())

    if not candidates:
        return []

    # Step 2: Profile HMM scoring on candidates
    scored = []
    for lineage_id in candidates:
        # MinHash similarity check
        stored_m = _lineage_minhashes.get(lineage_id)
        if stored_m:
            jaccard = jaccard_similarity(query_m, stored_m)
        else:
            jaccard = 0.0

        # Profile HMM emission score
        profile = _lineage_profiles.get(lineage_id)
        if profile:
            hmm_score = profile.score_sequence(act_sequence)
        else:
            hmm_score = 0.0

        # Combined score (weighted)
        combined = 0.5 * jaccard + 0.5 * hmm_score
        if combined > 0.1:
            scored.append((lineage_id, round(combined, 4)))

    return sorted(scored, key=lambda x: x[1], reverse=True)


def should_create_new_lineage(
    act_sequence: list[str],
    best_match_score: float
) -> bool:
    """Decide if this complaint starts a new lineage."""
    return best_match_score < SIMILARITY_THRESHOLD


def assign_complaint_to_lineage(
    act_sequence: list[str],
    existing_lineages: list[dict]  # [{id, act_sequence, minhash_signature}]
) -> tuple[Optional[str], float]:
    """
    Main assignment function.
    Returns (lineage_id, confidence) — lineage_id is None if new lineage needed.
    """
    # Load stored MinHashes into memory if not present
    for lineage in existing_lineages:
        lid = lineage["id"]
        if lid not in _lineage_minhashes and lineage.get("minhash_signature"):
            _lineage_minhashes[lid] = list_to_minhash(lineage["minhash_signature"])
            lsh = get_lsh()
            try:
                lsh.insert(lid, _lineage_minhashes[lid])
            except ValueError:
                pass
        if lid not in _lineage_profiles and lineage.get("act_sequence"):
            _lineage_profiles[lid] = LineageProfile(lid, lineage["act_sequence"])

    matches = find_matching_lineages(act_sequence)

    if not matches:
        return None, 0.0

    best_id, best_score = matches[0]

    if should_create_new_lineage(act_sequence, best_score):
        return None, best_score

    # Update the matched lineage's profile
    update_profile(best_id, act_sequence)
    return best_id, best_score


def compute_churn_rate(identifier_history: list[dict]) -> str:
    """
    Estimate identifier churn rate within a lineage.
    identifier_history: [{value_hash, complaint_count, first_seen, last_seen}]
    """
    if not identifier_history:
        return "Low"

    unique_ids = len(identifier_history)
    total_complaints = sum(i.get("complaint_count", 1) for i in identifier_history)

    if total_complaints == 0:
        return "Low"

    # Reuse ratio: if each identifier used only once, churn is high
    avg_reuse = total_complaints / unique_ids

    if avg_reuse < 2:
        return "High"    # Each identifier used once → burner mode
    elif avg_reuse < 5:
        return "Medium"
    else:
        return "Low"     # Same identifiers reused → amateur


if __name__ == "__main__":
    # Quick test
    seq1 = ["GREET", "IMPERSONATE", "URGENCY", "LINK", "PERSONAL_INFO_REQUEST"]
    seq2 = ["IMPERSONATE", "URGENCY", "LINK", "OTP_REQUEST"]
    seq3 = ["PRIZE", "PAYMENT_REQUEST", "URGENCY"]

    register_lineage_in_lsh("L001", seq1)
    register_lineage_in_lsh("L002", seq3)
    get_or_create_profile("L001", seq1)
    get_or_create_profile("L002", seq3)

    lineages = [
        {"id": "L001", "act_sequence": seq1, "minhash_signature": minhash_to_list(text_to_minhash(seq1))},
        {"id": "L002", "act_sequence": seq3, "minhash_signature": minhash_to_list(text_to_minhash(seq3))},
    ]

    result = assign_complaint_to_lineage(seq2, lineages)
    print(f"Sequence {seq2}")
    print(f"→ Assigned to: {result}")

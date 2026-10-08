"""
Dialog-Act Tagger for ScamRadar.
Converts raw scam SMS text into a sequence of manipulation acts.
Uses rule-based pattern matching (fast, language-agnostic) with
optional multilingual BERT for enhanced accuracy.

Acts: GREET | IMPERSONATE | URGENCY | THREAT | PRIZE |
      PAYMENT_REQUEST | LINK | OTP_REQUEST | PERSONAL_INFO_REQUEST | CLOSE
"""
import re
import json
from dataclasses import dataclass
from typing import Optional
from langdetect import detect, LangDetectException

# ---------------------------------------------------------------------------
# Act definitions and multilingual keyword patterns
# ---------------------------------------------------------------------------

ACT_PATTERNS = {
    "GREET": [
        r"\b(dear|hello|hi|congrat|namaste|priya|प्रिय|வணக்கம்|నమస్కారం)\b",
    ],
    "IMPERSONATE": [
        r"\b(sbi|hdfc|icici|axis|paytm|phonepe|gpay|rbi|npci|irdai|sebi|"
        r"income.?tax|aadhaar|uidai|epfo|irctc|bsnl|airtel|jio|trai|"
        r"cybercrime|police|court|cbi|ed\b|enforcement)\b",
        r"\b(bank|बैंक|வங்கி|బ్యాంక్)\b",
    ],
    "URGENCY": [
        r"\b(urgent|immediately|within \d+ hours?|last chance|expire|"
        r"today only|limited time|अभी|तुरंत|உடனே|వెంటనే)\b",
        r"\b(block|suspend|deactivat|restrict|freeze|बंद हो|நிறுத்த)\b",
    ],
    "THREAT": [
        r"\b(legal action|arrest|fir|lawsuit|penalty|fine|jail|"
        r"illegal|criminal|कानूनी कार्रवाई|கைது)\b",
        r"\b(your account (will be|has been) (block|suspend|deactivat|closed?))\b",
    ],
    "PRIZE": [
        r"\b(won|winner|prize|reward|lucky draw|cashback|bonus|"
        r"₹\s*\d+|rs\.?\s*\d+|inr\s*\d+|जीत|पुरस्कार|பரிசு)\b",
    ],
    "PAYMENT_REQUEST": [
        r"\b(pay|send|transfer|deposit|upi|paytm|gpay|phonepe|neft|imps|"
        r"account number|ifsc|भेजें|भुगतान|அனுப்பு|చెల్లించు)\b",
    ],
    "LINK": [
        r"https?://\S+",
        r"\b\w+\.(com|in|xyz|net|org|co\.in|info|online|site|click)\b",
        r"\b(click here|tap here|यहाँ क्लिक|இங்கே கிளிக்)\b",
    ],
    "OTP_REQUEST": [
        r"\b(otp|one.?time.?password|verification code|pin|पिन|OTP दर्ज)\b",
    ],
    "PERSONAL_INFO_REQUEST": [
        r"\b(kyc|aadh(a|ā)ar|pan card|dob|date of birth|address|"
        r"mobile number|email|update|verify|आधार|पैन)\b",
    ],
    "CLOSE": [
        r"\b(thank you|regards|team|helpline|contact us|customer care|"
        r"धन्यवाद|நன்றி)\b",
    ],
}

SCRIPT_TYPE_SIGNATURES = {
    "KYC_Fraud": ["IMPERSONATE", "PERSONAL_INFO_REQUEST", "LINK"],
    "Prize_Scam": ["PRIZE", "PAYMENT_REQUEST", "URGENCY"],
    "Bank_Impersonation": ["IMPERSONATE", "THREAT", "PERSONAL_INFO_REQUEST"],
    "Aadhaar_Threat": ["IMPERSONATE", "THREAT", "PERSONAL_INFO_REQUEST"],
    "Tax_Refund": ["IMPERSONATE", "PRIZE", "LINK"],
    "Wallet_Suspension": ["IMPERSONATE", "URGENCY", "LINK"],
    "OTP_Phishing": ["IMPERSONATE", "OTP_REQUEST", "PERSONAL_INFO_REQUEST"],
    "Loan_Fraud": ["PRIZE", "PAYMENT_REQUEST", "LINK"],
    "Unknown": [],
}


@dataclass
class TaggedComplaint:
    text: str
    language: str
    acts: list[str]
    act_sequence: list[str]  # deduplicated, ordered
    script_type: str
    confidence: float


def detect_language(text: str) -> str:
    """Detect language of text."""
    # Check for Indic scripts first (faster than langdetect)
    if re.search(r'[\u0900-\u097F]', text):
        return "Hindi"
    if re.search(r'[\u0B80-\u0BFF]', text):
        return "Tamil"
    if re.search(r'[\u0C00-\u0C7F]', text):
        return "Telugu"
    if re.search(r'[\u0C80-\u0CFF]', text):
        return "Kannada"
    # Check for Hinglish (Hindi words in Latin script)
    hinglish_markers = r'\b(aapka|khata|band|abhi|turant|yahan|karo|kijiye|nahi|hai)\b'
    if re.search(hinglish_markers, text, re.IGNORECASE):
        return "Hinglish"
    try:
        lang = detect(text)
        return {"en": "English", "hi": "Hindi", "ta": "Tamil",
                "te": "Telugu", "kn": "Kannada"}.get(lang, "English")
    except LangDetectException:
        return "English"


def extract_acts(text: str) -> list[str]:
    """Extract all dialog acts present in text (with repetition for position)."""
    text_lower = text.lower()
    acts_found = []

    # Split into rough sentences/clauses for ordering
    clauses = re.split(r'[.!?\n;]', text_lower)

    for clause in clauses:
        for act, patterns in ACT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, clause, re.IGNORECASE):
                    acts_found.append(act)
                    break  # one act per clause per type

    return acts_found


def deduplicate_sequence(acts: list[str]) -> list[str]:
    """Remove consecutive duplicates while preserving order."""
    if not acts:
        return []
    seq = [acts[0]]
    for act in acts[1:]:
        if act != seq[-1]:
            seq.append(act)
    return seq


def classify_script_type(act_sequence: list[str]) -> tuple[str, float]:
    """Match act sequence against known script signatures."""
    best_type = "Unknown"
    best_score = 0.0

    act_set = set(act_sequence)

    for script_type, signature in SCRIPT_TYPE_SIGNATURES.items():
        if not signature:
            continue
        sig_set = set(signature)
        overlap = len(act_set & sig_set)
        score = overlap / len(sig_set) if sig_set else 0
        if score > best_score:
            best_score = score
            best_type = script_type

    return best_type, round(best_score, 3)


def tag_complaint(text: str, language: Optional[str] = None) -> TaggedComplaint:
    """Full dialog-act tagging pipeline for a single complaint."""
    if not language or language == "auto":
        language = detect_language(text)

    acts = extract_acts(text)
    act_sequence = deduplicate_sequence(acts)

    if not act_sequence:
        act_sequence = ["UNKNOWN"]

    script_type, confidence = classify_script_type(act_sequence)

    return TaggedComplaint(
        text=text,
        language=language,
        acts=acts,
        act_sequence=act_sequence,
        script_type=script_type,
        confidence=confidence,
    )


def batch_tag(texts: list[str]) -> list[TaggedComplaint]:
    """Tag a batch of complaints."""
    return [tag_complaint(t) for t in texts]


def act_sequence_to_ngrams(act_sequence: list[str], n: int = 2) -> list[str]:
    """Convert act sequence to n-grams for MinHash."""
    if len(act_sequence) < n:
        return [" ".join(act_sequence)]
    return [" ".join(act_sequence[i:i+n]) for i in range(len(act_sequence) - n + 1)]


if __name__ == "__main__":
    # Quick test
    test_messages = [
        "Dear customer, your SBI account will be blocked. Update KYC immediately at sbi-kyc.xyz or call 9876543210",
        "Congratulations! You won ₹50,000 in BSNL lucky draw. Send UPI to pay.1234@ybl within 2 hours.",
        "आपका बैंक खाता बंद हो जाएगा। अभी KYC अपडेट करें।",
        "உங்கள் வங்கி கணக்கு நிறுத்தப்படும். உடனே KYC புதுப்பிக்கவும்",
    ]

    print("Dialog-Act Tagger Test")
    print("=" * 50)
    for msg in test_messages:
        result = tag_complaint(msg)
        print(f"\nText: {msg[:60]}...")
        print(f"  Language: {result.language}")
        print(f"  Acts: {result.act_sequence}")
        print(f"  Script: {result.script_type} ({result.confidence:.0%})")

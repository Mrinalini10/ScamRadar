"""
Dataset fetcher and preprocessor for ScamRadar.
Downloads and preprocesses the Mendeley SMS Phishing Dataset
(DOI: 10.17632/f45bkkt8pr.1) and supplements with synthetic
Indian-language metadata for demonstration.
"""
import os
import csv
import json
import random
import hashlib
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PROCESSED_FILE = DATA_DIR / "processed_complaints.json"
RAW_CSV = DATA_DIR / "mendeley_smishing.csv"

# Mendeley dataset - public CSV export via Kaggle mirror (CC BY 4.0)
DATASET_URLS = [
    "https://raw.githubusercontent.com/AcidOP/phishing-sms-dataset/main/dataset.csv",
    "https://raw.githubusercontent.com/T-SOD000/SMS-Spam-Collection/master/SMSSpamCollection",
]

INDIAN_SCAM_TEMPLATES = [
    "Dear customer, your SBI account will be blocked. Update KYC immediately at {url} or call {phone}",
    "Congratulations! You won ₹50,000 in BSNL lucky draw. Send UPI ID {upi} to claim within 2 hours.",
    "URGENT: Your Aadhaar is linked to illegal activity. Contact cybercrime at {phone} immediately.",
    "Your PhonePe account has been suspended. Verify now: {url} UPI: {upi}",
    "RBI alert: Suspicious transaction detected on your account. Verify at {url}",
    "आपका बैंक खाता बंद हो जाएगा। अभी KYC अपडेट करें: {url} या {phone} पर कॉल करें",
    "உங்கள் வங்கி கணக்கு நிறுத்தப்படும். உடனே {url} இல் KYC புதுப்பிக்கவும்",
    "Mee bank account block avutundi. Verify cheyyandi: {url}",
    "PAYTM: Your wallet is suspended. Complete verification: {url} within 6 hours or lose funds.",
    "Income Tax dept: Refund of ₹8,240 pending. Claim here: {url} Enter OTP sent to your number.",
    "IRCTC: Your ticket is cancelled. Refund to UPI {upi}. Confirm at {url}",
    "Dear user, CIBIL score updated. Download free report: {url}. Login with Aadhaar.",
]

LANGUAGES = ["English", "Hindi", "Tamil", "Telugu", "Hinglish", "Kannada"]
BANKS = ["Bank_A", "Bank_B", "Bank_C"]
SCRIPT_TYPES = [
    "KYC_Fraud", "Prize_Scam", "Bank_Impersonation",
    "Aadhaar_Threat", "Tax_Refund", "Wallet_Suspension", "Loan_Fraud"
]

FAKE_PHONES = [f"98{random.randint(10000000, 99999999)}" for _ in range(50)]
FAKE_UPIS = [f"pay.{random.randint(1000, 9999)}@ybl" for _ in range(50)]
FAKE_URLS = [
    f"sbi-kyc-verify-{random.randint(100, 999)}.xyz",
    f"verify-aadhaar-{random.randint(100, 999)}.in",
    f"rbi-refund-{random.randint(100, 999)}.com",
]


def generate_reporting_delay() -> timedelta:
    """Empirical reporting delay distribution for Indian fraud victims."""
    r = random.random()
    if r < 0.20:
        return timedelta(hours=random.uniform(0, 6))
    elif r < 0.80:
        return timedelta(days=random.uniform(2, 5))
    else:
        return timedelta(days=random.uniform(10, 30))


def hash_identifier(value: str) -> tuple[str, str]:
    """Returns (sha256_hash, last_4_display)."""
    h = hashlib.sha256(value.encode()).hexdigest()
    display = "****" + value[-4:] if len(value) >= 4 else "****"
    return h, display


def generate_synthetic_complaints(n: int = 300) -> list[dict]:
    """Generate realistic synthetic Indian scam complaints with metadata."""
    complaints = []
    base_date = datetime.now() - timedelta(days=60)

    # Create lineage clusters - same script, rotating identifiers
    lineage_groups = {
        "KYC_Fraud": (FAKE_PHONES[:10], FAKE_UPIS[:5], FAKE_URLS[:3]),
        "Prize_Scam": (FAKE_PHONES[10:20], FAKE_UPIS[5:10], FAKE_URLS[1:3]),
        "Bank_Impersonation": (FAKE_PHONES[20:35], FAKE_UPIS[10:20], FAKE_URLS[:2]),
        "Aadhaar_Threat": (FAKE_PHONES[35:45], FAKE_UPIS[20:25], FAKE_URLS[2:]),
        "Tax_Refund": (FAKE_PHONES[45:], FAKE_UPIS[25:30], FAKE_URLS[:2]),
    }

    for i in range(n):
        script_type = random.choice(list(lineage_groups.keys()))
        phones, upis, urls = lineage_groups[script_type]

        phone = random.choice(phones)
        upi = random.choice(upis)
        url = random.choice(urls)

        template = random.choice([t for t in INDIAN_SCAM_TEMPLATES])
        try:
            text = template.format(phone=phone, upi=upi, url=url)
        except KeyError:
            text = template

        language = random.choice(LANGUAGES)
        if "आपका" in text or "कॉल" in text:
            language = "Hindi"
        elif "வங்கி" in text:
            language = "Tamil"
        elif "అవుతుంది" in text:
            language = "Telugu"

        event_date = base_date + timedelta(days=random.uniform(0, 55))
        delay = generate_reporting_delay()
        reported_date = event_date + delay

        phone_hash, phone_display = hash_identifier(phone)
        upi_hash, upi_display = hash_identifier(upi)
        url_hash, url_display = hash_identifier(url)

        complaints.append({
            "raw_text": text,
            "reported_date": reported_date.isoformat(),
            "source_bank": random.choice(BANKS),
            "language": language,
            "script_type": script_type,
            "phone_hash": phone_hash,
            "phone_last4": phone_display,
            "upi_hash": upi_hash,
            "upi_last4": upi_display,
            "url_hash": url_hash,
            "reporter_hash": hashlib.sha256(f"user_{i}".encode()).hexdigest()[:16],
            "label": "smishing",
            "synthetic": True,
        })

    return complaints


def fetch_mendeley_dataset() -> list[dict]:
    """Try to fetch real dataset, fall back to synthetic if unavailable."""
    print("📥 Attempting to fetch Mendeley SMS Phishing Dataset...")

    for url in DATASET_URLS:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                print(f"✅ Downloaded from {url}")
                lines = resp.text.strip().split("\n")
                complaints = []
                for line in lines[1:]:  # skip header
                    parts = line.strip().split(",", 1)
                    if len(parts) >= 2:
                        label, text = parts[0].strip().lower(), parts[1].strip().strip('"')
                        if label in ("spam", "smishing", "ham") and len(text) > 10:
                            delay = generate_reporting_delay()
                            reported = (datetime.now() - timedelta(days=random.uniform(1, 60)) + delay)
                            complaints.append({
                                "raw_text": text,
                                "reported_date": reported.isoformat(),
                                "source_bank": random.choice(BANKS),
                                "language": "English",
                                "script_type": "unknown",
                                "phone_hash": None,
                                "phone_last4": None,
                                "upi_hash": None,
                                "upi_last4": None,
                                "url_hash": None,
                                "reporter_hash": hashlib.sha256(text[:20].encode()).hexdigest()[:16],
                                "label": label,
                                "synthetic": False,
                            })
                print(f"   Loaded {len(complaints)} messages")
                return complaints
        except Exception as e:
            print(f"   ⚠️  Could not fetch from {url}: {e}")

    print("⚠️  Real dataset unavailable. Using synthetic Indian SMS corpus.")
    return []


def preprocess_and_save():
    """Main entry point: fetch + supplement + save processed dataset."""
    print("\n🔄 ScamRadar Dataset Preprocessor")
    print("=" * 40)

    real = fetch_mendeley_dataset()
    synthetic = generate_synthetic_complaints(300)

    combined = real + synthetic
    random.shuffle(combined)

    with open(PROCESSED_FILE, "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\n✅ Dataset ready: {len(combined)} total complaints")
    print(f"   Real: {len(real)} | Synthetic Indian corpus: {len(synthetic)}")
    print(f"   Saved to: {PROCESSED_FILE}")
    return combined


def load_dataset() -> list[dict]:
    """Load processed dataset, building it if not present."""
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return json.load(f)
    return preprocess_and_save()


if __name__ == "__main__":
    preprocess_and_save()

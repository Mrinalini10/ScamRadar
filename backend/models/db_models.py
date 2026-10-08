from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String, primary_key=True, default=gen_uuid)
    raw_text = Column(Text, nullable=False)
    reported_date = Column(DateTime, nullable=False)
    ingested_date = Column(DateTime, server_default=func.now())
    source_bank = Column(String, nullable=False)
    language = Column(String, default="unknown")
    script_type = Column(String, default="unknown")
    act_sequence = Column(JSON, default=list)
    lineage_id = Column(String, nullable=True)
    lineage_confidence = Column(Float, default=0.0)
    phone_hash = Column(String, nullable=True)
    upi_hash = Column(String, nullable=True)
    url_hash = Column(String, nullable=True)
    phone_last4 = Column(String, nullable=True)
    upi_last4 = Column(String, nullable=True)
    reporter_hash = Column(String, nullable=False)
    analyst_tags = Column(JSON, default=list)
    is_poisoning_suspect = Column(Boolean, default=False)
    label = Column(String, default="smishing")  # ham/spam/smishing


class Lineage(Base):
    __tablename__ = "lineages"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    script_type = Column(String, nullable=False)
    act_sequence = Column(JSON, default=list)
    created_date = Column(DateTime, server_default=func.now())
    complaint_count = Column(Integer, default=0)
    nowcast_count = Column(Float, default=0.0)
    growth_rate = Column(String, default="Slow")  # Slow/Rising/Critical
    status = Column(String, default="Monitoring")  # Monitoring/Alert/Resolved
    churn_rate = Column(String, default="Low")   # Low/Medium/High
    language_distribution = Column(JSON, default=dict)
    banks_involved = Column(JSON, default=list)
    minhash_signature = Column(JSON, default=list)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Identifier(Base):
    __tablename__ = "identifiers"

    id = Column(String, primary_key=True, default=gen_uuid)
    id_type = Column(String, nullable=False)  # phone/upi/url
    value_hash = Column(String, nullable=False)
    display_value = Column(String, nullable=False)  # last 4 chars only
    lineage_id = Column(String, nullable=False)
    first_seen = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, server_default=func.now())
    complaint_count = Column(Integer, default=1)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=gen_uuid)
    lineage_id = Column(String, nullable=False)
    lineage_name = Column(String, nullable=False)
    trigger_reason = Column(String, nullable=False)
    script_type = Column(String, nullable=False)
    nowcast_count = Column(Float, default=0.0)
    recommended_action = Column(String, default="Monitor")
    status = Column(String, default="Active")  # Active/Acknowledged/Escalated/Dismissed
    dismissed_reason = Column(String, nullable=True)
    acknowledged_by = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    timestamp = Column(DateTime, server_default=func.now())
    analyst_hash = Column(String, nullable=False)
    action = Column(String, nullable=False)
    lineage_id = Column(String, nullable=True)
    complaint_id = Column(String, nullable=True)
    detail = Column(Text, nullable=True)
    system_hash = Column(String, nullable=False)


class NowcastState(Base):
    __tablename__ = "nowcast_states"

    id = Column(String, primary_key=True, default=gen_uuid)
    lineage_id = Column(String, nullable=False, unique=True)
    daily_counts = Column(JSON, default=list)        # [{date, observed, corrected}]
    rt_history = Column(JSON, default=list)          # [{date, rt}]
    delay_params = Column(JSON, default=dict)        # p_instant, p_delayed, p_tail
    last_updated = Column(DateTime, server_default=func.now())


class AdminConfig(Base):
    __tablename__ = "admin_config"

    id = Column(String, primary_key=True, default="global")
    delay_instant_pct = Column(Float, default=0.20)
    delay_normal_pct = Column(Float, default=0.60)
    delay_tail_pct = Column(Float, default=0.20)
    alert_threshold_daily = Column(Integer, default=5)
    psi_min_banks = Column(Integer, default=2)
    psi_min_complaints = Column(Integer, default=10)
    poison_report_cap = Column(Integer, default=5)

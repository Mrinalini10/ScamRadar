"""
CUSUM Early Warning System for ScamRadar.
Detects statistically significant increases in a lineage's complaint rate
using Cumulative Sum (CUSUM) control charts.

CUSUM is calibrated so false-alarm rate is controlled (h parameter).
Also implements Bayesian Online Changepoint Detection (BOCD) as fallback.
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class CUSUMState:
    """State of a CUSUM monitor for one lineage."""
    lineage_id: str
    cusum_pos: float = 0.0      # upper CUSUM (detects upward shifts)
    cusum_neg: float = 0.0      # lower CUSUM (detects downward shifts)
    baseline_mean: float = 1.0  # expected daily complaint rate (nowcast-corrected)
    baseline_std: float = 0.5
    k: float = 0.5              # allowable slack (in std devs)
    h: float = 5.0              # decision threshold (in std devs)
    n_samples: int = 0
    last_alarm: Optional[int] = None  # sample index of last alarm


def cusum_update(state: CUSUMState, new_value: float) -> tuple[CUSUMState, bool]:
    """
    Update CUSUM state with new observation.
    Returns updated state and whether an alarm was triggered.
    
    Uses standardized CUSUM: xi = (x - mu) / sigma
    S+ = max(0, S+_prev + xi - k)
    Alarm when S+ > h
    """
    if state.baseline_std < 0.01:
        state.baseline_std = 0.01

    # Standardize
    xi = (new_value - state.baseline_mean) / state.baseline_std

    # CUSUM update
    state.cusum_pos = max(0.0, state.cusum_pos + xi - state.k)
    state.cusum_neg = max(0.0, state.cusum_neg - xi - state.k)
    state.n_samples += 1

    alarm = state.cusum_pos > state.h

    if alarm:
        # Reset after alarm
        state.last_alarm = state.n_samples
        state.cusum_pos = 0.0
        state.cusum_neg = 0.0

    return state, alarm


def run_cusum_on_series(
    series: list[float],
    k: float = 0.5,
    h: float = 4.0,
    warmup: int = 7
) -> dict:
    """
    Run CUSUM on a time series of (nowcast-corrected) daily complaint counts.
    
    warmup: number of initial samples used to estimate baseline.
    Returns alarm indices and final CUSUM values.
    """
    if len(series) < warmup + 1:
        return {
            "alarms": [],
            "cusum_series": series,
            "triggered": False,
            "final_cusum": 0.0,
        }

    # Estimate baseline from warmup period
    warmup_data = np.array(series[:warmup])
    baseline_mean = float(np.mean(warmup_data))
    baseline_std = float(np.std(warmup_data)) + 0.1  # add small floor

    state = CUSUMState(
        lineage_id="",
        baseline_mean=baseline_mean,
        baseline_std=baseline_std,
        k=k,
        h=h,
    )

    alarms = []
    cusum_values = [0.0] * warmup

    for i, val in enumerate(series[warmup:], start=warmup):
        state, alarm = cusum_update(state, val)
        cusum_values.append(round(state.cusum_pos, 3))
        if alarm:
            alarms.append(i)

    return {
        "alarms": alarms,
        "cusum_series": cusum_values,
        "triggered": len(alarms) > 0,
        "final_cusum": round(state.cusum_pos, 3),
        "baseline_mean": round(baseline_mean, 2),
        "baseline_std": round(baseline_std, 2),
    }


# ---------------------------------------------------------------------------
# Bayesian Online Changepoint Detection (BOCD) — Adams & MacKay 2007
# Simplified scalar version for complaint rate monitoring
# ---------------------------------------------------------------------------

def bocd_update(
    run_length_probs: np.ndarray,
    new_value: float,
    alpha: float = 1.0,   # prior shape for Normal-Gamma
    beta: float = 1.0,    # prior rate
    kappa: float = 1.0,   # prior precision scaling
    mu: float = 1.0,      # prior mean
    hazard: float = 1/50  # expected run length = 1/hazard
) -> tuple[np.ndarray, float]:
    """
    Single step of BOCD.
    Returns updated run-length posterior and MAP run length.
    """
    t = len(run_length_probs)
    new_probs = np.zeros(t + 1)

    # Predictive probability under Student-t (conjugate for Normal-Gamma)
    from scipy.stats import t as t_dist
    pred_probs = np.zeros(t)
    for r in range(t):
        df = 2 * alpha
        scale = np.sqrt(beta * (kappa + 1) / (alpha * kappa))
        pred_probs[r] = t_dist.pdf(new_value, df=df, loc=mu, scale=scale)

    # Growth probability
    growth = run_length_probs[:t] * pred_probs * (1 - hazard)
    new_probs[1:t+1] = growth

    # Changepoint probability
    new_probs[0] = np.sum(run_length_probs[:t] * pred_probs * hazard)

    # Normalize
    total = new_probs.sum()
    if total > 0:
        new_probs /= total

    map_run_length = float(np.argmax(new_probs))
    return new_probs, map_run_length


# ---------------------------------------------------------------------------
# Alert generation
# ---------------------------------------------------------------------------

ALERT_REASONS = {
    "cusum_trigger": "CUSUM alarm: complaint rate exceeded statistical threshold",
    "rt_critical": "Reproduction number Rt > 1.5 — campaign growing rapidly",
    "rt_rising": "Reproduction number Rt > 1.2 — campaign showing growth",
    "rapid_doubling": "Complaint count doubled in under 24 hours",
    "new_variant": "New script variant detected — possible LLM-generated mutation",
    "cross_bank": "Campaign confirmed across {n} banks",
    "high_churn": "Identifier churn rate elevated — organized rotation detected",
}


def determine_alert_level(
    rt: float,
    cusum_triggered: bool,
    cross_bank_count: int,
    churn_rate: str,
    complaint_count: int,
    daily_threshold: int = 5,
) -> tuple[str, str, str]:
    """
    Returns (growth_rate, recommended_action, trigger_reason).
    """
    # Critical conditions
    if rt > 1.5 or (cusum_triggered and rt > 1.2):
        growth_rate = "Critical"
        action = "Escalate to I4C"
        reason = ALERT_REASONS["rt_critical"]
        return growth_rate, action, reason

    if cross_bank_count >= 3:
        growth_rate = "Critical"
        action = "File DPIP Report"
        reason = ALERT_REASONS["cross_bank"].format(n=cross_bank_count)
        return growth_rate, action, reason

    # Rising conditions
    if rt > 1.2 or cusum_triggered:
        growth_rate = "Rising"
        action = "Monitor Closely"
        reason = ALERT_REASONS["rt_rising"] if rt > 1.2 else ALERT_REASONS["cusum_trigger"]
        return growth_rate, action, reason

    if churn_rate == "High" and complaint_count > 10:
        growth_rate = "Rising"
        action = "Monitor Closely"
        reason = ALERT_REASONS["high_churn"]
        return growth_rate, action, reason

    # Slow / stable
    return "Slow", "Monitor", "Lineage is stable — no immediate action required"


def analyze_lineage_alerts(
    lineage_id: str,
    nowcast_result: dict,
    cross_bank_count: int = 1,
    churn_rate: str = "Low",
    complaint_count: int = 0,
    daily_threshold: int = 5,
) -> dict:
    """
    Full alert analysis for a lineage. Returns alert dict if alarm, else None.
    """
    rt = nowcast_result.get("rt", 1.0)
    daily_counts_list = nowcast_result.get("daily_counts", [])

    # Extract nowcast series
    series = [d["nowcast"] for d in daily_counts_list]

    # Run CUSUM
    cusum_result = run_cusum_on_series(series, h=4.0)

    growth_rate, action, reason = determine_alert_level(
        rt=rt,
        cusum_triggered=cusum_result["triggered"],
        cross_bank_count=cross_bank_count,
        churn_rate=churn_rate,
        complaint_count=complaint_count,
        daily_threshold=daily_threshold,
    )

    should_alert = growth_rate in ("Rising", "Critical")

    return {
        "lineage_id": lineage_id,
        "growth_rate": growth_rate,
        "recommended_action": action,
        "trigger_reason": reason,
        "rt": rt,
        "cusum_triggered": cusum_result["triggered"],
        "cusum_final": cusum_result.get("final_cusum", 0.0),
        "should_alert": should_alert,
        "cusum_series": cusum_result.get("cusum_series", []),
    }


if __name__ == "__main__":
    # Simulate a growing campaign
    import random
    baseline = [random.uniform(1, 3) for _ in range(7)]
    spike = [random.uniform(8, 15) for _ in range(7)]
    series = baseline + spike

    result = run_cusum_on_series(series)
    print(f"CUSUM alarms at: {result['alarms']}")
    print(f"Final CUSUM: {result['final_cusum']}")
    print(f"Triggered: {result['triggered']}")

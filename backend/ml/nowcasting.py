"""
Nowcasting Engine for ScamRadar.
Corrects right-censored complaint counts using Bayesian nowcasting
adapted from epidemic surveillance (EpiEstim-style).

The core insight: victims report fraud 2-5 days late on average.
Today's complaint count is always an undercount. We estimate
the "true" count by inverting the delay distribution.
"""
import numpy as np
from datetime import date, datetime, timedelta
from collections import defaultdict
from typing import Optional


# ---------------------------------------------------------------------------
# Default delay distribution (empirically motivated for Indian fraud victims)
# Fraction of complaints reported at each lag (days 0-30)
# ---------------------------------------------------------------------------

def build_delay_pmf(
    p_instant: float = 0.20,   # reported day 0 (0-6 hours)
    p_delayed: float = 0.60,   # reported day 2-5
    p_tail: float = 0.20,      # reported day 10-30
    max_lag: int = 30
) -> np.ndarray:
    """
    Build a probability mass function over reporting delays.
    Returns array of length max_lag+1 where pmf[d] = P(reporting at lag d days).
    """
    pmf = np.zeros(max_lag + 1)

    # Instant: day 0 (truncated normal around 0)
    pmf[0] = p_instant

    # Delayed: days 2-5 (uniform)
    for d in range(2, 6):
        pmf[d] += p_delayed / 4

    # Tail: days 10-30 (exponential decay)
    tail_days = list(range(10, min(31, max_lag + 1)))
    if tail_days:
        decay = np.exp(-0.1 * np.arange(len(tail_days)))
        decay /= decay.sum()
        for i, d in enumerate(tail_days):
            pmf[d] += p_tail * decay[i]

    # Normalize to ensure sums to 1
    if pmf.sum() > 0:
        pmf /= pmf.sum()

    return pmf


def nowcast_counts(
    observed_by_date: dict[str, int],  # {"2024-01-01": 5, ...}
    reference_date: Optional[date] = None,
    delay_pmf: Optional[np.ndarray] = None,
    max_lag: int = 30
) -> dict[str, dict]:
    """
    Bayesian nowcasting: estimate true counts correcting for reporting lag.

    For each date d, the observed count n_obs(d) is related to true count n_true(d) by:
      n_obs(d) = sum_{l=0}^{min(today-d, max_lag)} pmf[l] * n_true(d)

    We invert this using a simple ratio correction:
      correction_factor(d) = 1 / sum_{l=0}^{today-d} pmf[l]
      n_nowcast(d) = n_obs(d) * correction_factor(d)

    Returns dict of {date_str: {observed, nowcast, correction_factor}}
    """
    if reference_date is None:
        reference_date = date.today()

    if delay_pmf is None:
        delay_pmf = build_delay_pmf()

    results = {}

    # Cumulative PMF: P(reported within l days)
    cumulative_pmf = np.cumsum(delay_pmf)

    for date_str, obs_count in observed_by_date.items():
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        lag = (reference_date - d).days

        if lag < 0:
            # Future date — skip
            continue
        elif lag >= max_lag:
            # Far past — assume fully reported
            correction = 1.0
        else:
            # Fraction of reports expected by now
            fraction_reported = cumulative_pmf[min(lag, len(cumulative_pmf) - 1)]
            if fraction_reported < 0.01:
                fraction_reported = 0.01  # floor to avoid division by zero
            correction = 1.0 / fraction_reported

        nowcast = obs_count * correction

        results[date_str] = {
            "observed": obs_count,
            "nowcast": round(nowcast, 1),
            "correction_factor": round(correction, 3),
            "lag_days": lag,
        }

    return results


def estimate_rt(
    daily_counts: list[float],
    window: int = 7,
    serial_interval_mean: float = 3.0,
    serial_interval_sd: float = 1.5
) -> list[float]:
    """
    Estimate the effective reproduction number Rt for a scam lineage.
    Adapted from Cori et al. (2013) EpiEstim method.

    Rt represents how many new victims each complaint "spawns" on average.
    Rt > 1.0 → growing campaign, Rt < 1.0 → shrinking campaign.

    Uses gamma-distributed serial interval (time between "parent" and
    "child" complaint in a campaign wave).
    """
    if len(daily_counts) < window + 1:
        return [1.0] * len(daily_counts)

    # Gamma-distributed serial interval PMF
    from scipy.stats import gamma
    si_mean = serial_interval_mean
    si_sd = serial_interval_sd
    si_shape = (si_mean / si_sd) ** 2
    si_scale = (si_sd ** 2) / si_mean
    max_si = min(14, len(daily_counts))
    si_pmf = gamma.pdf(np.arange(1, max_si + 1), a=si_shape, scale=si_scale)
    si_pmf /= si_pmf.sum()

    rt_series = [None] * window
    counts = np.array(daily_counts, dtype=float)

    for t in range(window, len(counts)):
        # Numerator: incidence at time t
        numerator = counts[t]

        # Denominator: weighted sum of past incidence (infectiousness profile)
        denominator = 0.0
        for s_idx, w in enumerate(si_pmf):
            s = t - (s_idx + 1)
            if s >= 0:
                denominator += w * counts[s]

        if denominator < 1e-6:
            rt = 1.0
        else:
            rt = numerator / denominator

        rt_series.append(round(float(rt), 3))

    return rt_series


def classify_growth_rate(rt: float) -> str:
    """Classify a lineage's growth rate from its Rt estimate."""
    if rt < 0.8:
        return "Slow"
    elif rt < 1.3:
        return "Rising"
    else:
        return "Critical"


def build_daily_counts(
    complaints: list[dict],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> dict[str, int]:
    """Aggregate complaints by reported date."""
    counts = defaultdict(int)
    for c in complaints:
        try:
            d = datetime.fromisoformat(c["reported_date"]).date()
            counts[str(d)] += 1
        except (KeyError, ValueError):
            continue

    if start_date and end_date:
        # Fill in zeros for missing dates
        current = start_date
        while current <= end_date:
            date_str = str(current)
            if date_str not in counts:
                counts[date_str] = 0
            current += timedelta(days=1)

    return dict(counts)


def run_nowcast_for_lineage(
    lineage_complaints: list[dict],
    delay_params: Optional[dict] = None
) -> dict:
    """
    Full nowcasting pipeline for one lineage.
    Returns summary with daily corrected counts and current Rt.
    """
    if delay_params:
        pmf = build_delay_pmf(
            p_instant=delay_params.get("p_instant", 0.20),
            p_delayed=delay_params.get("p_delayed", 0.60),
            p_tail=delay_params.get("p_tail", 0.20),
        )
    else:
        pmf = build_delay_pmf()

    if not lineage_complaints:
        return {
            "daily_counts": [],
            "rt": 1.0,
            "growth_rate": "Slow",
            "total_nowcast": 0.0,
            "total_observed": 0,
        }

    # Build observed counts
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    observed = build_daily_counts(lineage_complaints, start_date, end_date)

    # Nowcast
    corrected = nowcast_counts(observed, reference_date=end_date, delay_pmf=pmf)

    # Build sorted timeline
    sorted_dates = sorted(corrected.keys())
    daily_counts_list = []
    corrected_series = []

    for d in sorted_dates:
        entry = corrected[d]
        daily_counts_list.append({
            "date": d,
            "observed": entry["observed"],
            "nowcast": entry["nowcast"],
            "correction_factor": entry["correction_factor"],
        })
        corrected_series.append(entry["nowcast"])

    # Estimate Rt from nowcast-corrected series
    rt_series = estimate_rt(corrected_series)
    current_rt = rt_series[-1] if rt_series else 1.0
    if current_rt is None:
        current_rt = 1.0

    return {
        "daily_counts": daily_counts_list,
        "rt": round(float(current_rt), 3),
        "rt_series": rt_series,
        "growth_rate": classify_growth_rate(current_rt),
        "total_nowcast": round(sum(corrected_series), 1),
        "total_observed": sum(observed.values()),
    }


if __name__ == "__main__":
    # Quick test
    from datetime import date, timedelta
    import random

    test_complaints = []
    base = date.today() - timedelta(days=20)
    for i in range(40):
        report_date = base + timedelta(days=i // 2, hours=random.randint(0, 48))
        test_complaints.append({"reported_date": str(report_date)})

    result = run_nowcast_for_lineage(test_complaints)
    print(f"Rt: {result['rt']} → {result['growth_rate']}")
    print(f"Observed: {result['total_observed']}, Nowcast: {result['total_nowcast']}")

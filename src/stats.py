"""Statistical methods for A/B experiment sizing and significance read-out."""

import math
from typing import Dict, Any
from scipy import stats


def calculate_sample_size(
    baseline_rate: float,
    mde_relative: float,
    alpha: float = 0.05,
    power: float = 0.80,
    daily_traffic: int = 150,
) -> Dict[str, Any]:
    """Calculate sample size per arm for a two-proportion test.

    Args:
        baseline_rate: Current baseline conversion/save rate (e.g., 0.18 for 18%).
        mde_relative: Minimum Detectable Effect relative to baseline (e.g., 0.15 for +15%).
        alpha: Type I error rate (significance level, default 0.05).
        power: Statistical power (1 - Type II error, default 0.80).
        daily_traffic: Daily eligible users for estimating experiment duration.

    Returns:
        Dictionary with sample size per variant, total sample, and required duration.
    """
    if not (0 < baseline_rate < 1):
        raise ValueError("baseline_rate must be between 0 and 1.")
    if mde_relative == 0:
        raise ValueError("mde_relative must be non-zero.")

    p1 = baseline_rate
    p2 = baseline_rate * (1.0 + mde_relative)
    p2 = min(0.999, max(0.001, p2))

    delta = abs(p2 - p1)
    p_bar = (p1 + p2) / 2.0

    z_alpha = stats.norm.ppf(1.0 - alpha / 2.0)
    z_beta = stats.norm.ppf(power)

    numerator = (
        z_alpha * math.sqrt(2.0 * p_bar * (1.0 - p_bar))
        + z_beta * math.sqrt(p1 * (1.0 - p1) + p2 * (1.0 - p2))
    ) ** 2
    denominator = delta ** 2

    n_per_variant = int(math.ceil(numerator / denominator))
    total_sample = n_per_variant * 2
    days_required = int(math.ceil(total_sample / daily_traffic)) if daily_traffic > 0 else 0

    return {
        "baseline_rate": round(p1, 4),
        "target_rate": round(p2, 4),
        "absolute_mde": round(delta, 4),
        "relative_mde_pct": round(mde_relative * 100, 1),
        "alpha": alpha,
        "power": power,
        "sample_size_per_variant": n_per_variant,
        "total_sample_size": total_sample,
        "estimated_days": days_required,
    }


def two_proportion_z_test(
    control_successes: int,
    control_total: int,
    variant_successes: int,
    variant_total: int,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Perform a two-sample two-sided z-test for comparing two proportions.

    Args:
        control_successes: Number of successful outcomes in control.
        control_total: Total sample count in control.
        variant_successes: Number of successful outcomes in variant.
        variant_total: Total sample count in variant.
        alpha: Significance threshold (default 0.05).

    Returns:
        Dictionary containing difference, standard error, z-score, p-value, and confidence interval.
    """
    if control_total <= 0 or variant_total <= 0:
        raise ValueError("Sample sizes must be greater than zero.")

    p_ctrl = control_successes / control_total
    p_var = variant_successes / variant_total
    diff = p_var - p_ctrl

    # Relative change
    rel_change_pct = (diff / p_ctrl * 100.0) if p_ctrl > 0 else 0.0

    # Pooled proportion under H0: p1 = p2
    p_pooled = (control_successes + variant_successes) / (control_total + variant_total)
    se_pooled = math.sqrt(p_pooled * (1.0 - p_pooled) * (1.0 / control_total + 1.0 / variant_total))

    # Standard error for unpooled confidence interval
    se_unpooled = math.sqrt(
        (p_ctrl * (1.0 - p_ctrl) / control_total) + (p_var * (1.0 - p_var) / variant_total)
    )

    if se_pooled == 0:
        z_stat = 0.0
        p_val = 1.0
    else:
        z_stat = diff / se_pooled
        p_val = 2.0 * (1.0 - stats.norm.cdf(abs(z_stat)))

    z_crit = stats.norm.ppf(1.0 - alpha / 2.0)
    ci_lower = diff - z_crit * se_unpooled
    ci_upper = diff + z_crit * se_unpooled
    is_significant = p_val < alpha

    return {
        "control_rate": round(p_ctrl, 4),
        "variant_rate": round(p_var, 4),
        "absolute_difference": round(diff, 4),
        "relative_change_pct": round(rel_change_pct, 2),
        "z_statistic": round(z_stat, 4),
        "p_value": round(p_val, 5),
        "is_significant": is_significant,
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "alpha": alpha,
    }

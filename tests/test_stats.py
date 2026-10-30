"""Tests for statistical methods."""

import pytest
from src.stats import calculate_sample_size, two_proportion_z_test


def test_calculate_sample_size():
    """Verify sample size calculation properties."""
    res = calculate_sample_size(baseline_rate=0.20, mde_relative=0.10, alpha=0.05, power=0.80)
    assert res["sample_size_per_variant"] > 0
    assert res["total_sample_size"] == 2 * res["sample_size_per_variant"]

    # Higher power should require more sample
    res_high_power = calculate_sample_size(baseline_rate=0.20, mde_relative=0.10, alpha=0.05, power=0.90)
    assert res_high_power["sample_size_per_variant"] > res["sample_size_per_variant"]

    # Smaller MDE should require more sample
    res_small_mde = calculate_sample_size(baseline_rate=0.20, mde_relative=0.05, alpha=0.05, power=0.80)
    assert res_small_mde["sample_size_per_variant"] > res["sample_size_per_variant"]


def test_two_proportion_z_test():
    """Verify hypothesis test properties."""
    # Clearly significant lift
    sig_res = two_proportion_z_test(
        control_successes=200,
        control_total=2000,
        variant_successes=280,
        variant_total=2000,
    )
    assert sig_res["is_significant"] == True
    assert sig_res["p_value"] < 0.05
    assert sig_res["absolute_difference"] > 0

    # Non-significant difference
    null_res = two_proportion_z_test(
        control_successes=200,
        control_total=2000,
        variant_successes=202,
        variant_total=2000,
    )
    assert null_res["is_significant"] == False
    assert null_res["p_value"] > 0.05

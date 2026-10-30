"""Integration and smoke tests for all 5 app page views using Streamlit AppTest."""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from app.views import overview, risk_queue, segments_playbook, experiment_planner, model_threshold
from app.data import get_scores, get_metrics, get_funnel, get_retention_cohorts, get_time_to_first_trade

MAIN_PY = str(Path(__file__).resolve().parent.parent / "app" / "main.py")


def test_data_loaders_return_valid_data():
    """Verify that all data loading helpers return non-empty datasets."""
    scores = get_scores()
    assert not scores.empty
    assert len(scores) == 20000

    metrics = get_metrics()
    assert "models" in metrics
    assert "gradient_boosting" in metrics["models"]

    funnel = get_funnel()
    assert not funnel.empty
    assert "total_signups" in funnel.columns

    retention = get_retention_cohorts()
    assert not retention.empty
    assert "cohort_month" in retention.columns

    timing = get_time_to_first_trade()
    assert not timing.empty
    assert "time_bucket" in timing.columns


def test_views_have_render_functions():
    """Verify that each page module exposes a callable render function."""
    for module in [overview, risk_queue, segments_playbook, experiment_planner, model_threshold]:
        assert hasattr(module, "render")
        assert callable(module.render)


@pytest.mark.parametrize("page_name", [
    "overview",
    "risk_queue",
    "segments_playbook",
    "experiment_planner",
    "model_threshold",
])
def test_apptest_renders_each_page_without_exceptions(page_name: str):
    """Render each page in Streamlit AppTest harness and verify zero unhandled exceptions."""
    at = AppTest.from_file(MAIN_PY)
    at.session_state["active_page"] = page_name
    at.run(timeout=30)
    assert len(at.exception) == 0, f"Page {page_name} raised exceptions: {[e.value for e in at.exception]}"

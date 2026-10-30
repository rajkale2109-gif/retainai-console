"""End-to-end pipeline runner for RetainAI.

Executes data generation, SQLite database initialization, day-14 feature extraction,
model training, 5-fold out-of-fold scoring, segmentation, and expected value calculation.
"""

import time
import sqlite3
from src.config import DB_PATH, METRICS_PATH, SCORES_PATH
from src.build_db import build_database, print_stage_2_report
from src.train import train_and_evaluate


def run_pipeline() -> None:
    """Run the complete pipeline from scratch."""
    start_time = time.time()
    print("=" * 72)
    print("RETAINAI END-TO-END PIPELINE")
    print("=" * 72)

    # 1. Build database
    print("\n[Step 1/2] Generating data and building SQLite database...")
    conn = build_database(DB_PATH)

    # Validate database integrity and metrics
    print_stage_2_report(conn)

    # 2. Train model and score users
    print("\n[Step 2/2] Training models, extracting day-14 features, and scoring...")
    metrics, scores = train_and_evaluate(conn)
    conn.close()

    elapsed = time.time() - start_time
    print("\n" + "=" * 72)
    print(f"PIPELINE RUN COMPLETED SUCCESSFULLY in {elapsed:.1f}s")
    print(f"Processed scores : {SCORES_PATH} ({len(scores):,} rows)")
    print(f"Model metrics    : {METRICS_PATH}")
    print(f"Hold-out ROC AUC : {metrics['models']['gradient_boosting']['roc_auc']:.4f}")
    print("=" * 72)


if __name__ == "__main__":
    run_pipeline()

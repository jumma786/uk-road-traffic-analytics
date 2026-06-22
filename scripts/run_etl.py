"""
Full ETL orchestrator. Runs extract, load, quality checks, and visualizations.
Can be scheduled via cron/Task Scheduler for automated runs.

Usage:
    python scripts/run_etl.py                 # full pipeline
    python scripts/run_etl.py --skip-extract  # reload + reports only
    python scripts/run_etl.py --incremental   # only load new years
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def run_step(name: str, cmd: list[str]) -> bool:
    logger.info("--- %s ---", name)
    start = time.time()
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error("%s FAILED (%.1fs)", name, time.time() - start)
        logger.error("STDERR: %s", result.stderr[-500:] if result.stderr else "")
        return False

    logger.info("%s completed (%.1fs)", name, time.time() - start)
    return True


def main():
    parser = argparse.ArgumentParser(description="Run ETL pipeline")
    parser.add_argument("--skip-extract", action="store_true", help="Skip API download")
    parser.add_argument("--incremental", action="store_true", help="Incremental fact load")
    parser.add_argument("--skip-viz", action="store_true", help="Skip visualization generation")
    args = parser.parse_args()

    start = time.time()
    steps_passed = 0
    steps_failed = 0

    if not args.skip_extract:
        if run_step("Extract: Direction Data", [PYTHON, "src/extract/download_traffic_flow_by_direction.py"]):
            steps_passed += 1
        else:
            steps_failed += 1
            logger.warning("Extract failed, continuing with existing data...")

    if args.incremental:
        step = run_step("Load: Incremental Facts", [PYTHON, "src/load/load_incremental.py"])
    else:
        if run_step("Load: Dimensions", [PYTHON, "src/load/load_dimensions.py"]):
            steps_passed += 1
        else:
            steps_failed += 1
            logger.error("Dimension load failed. Aborting.")
            sys.exit(1)
        step = run_step("Load: Fact Table", [PYTHON, "src/load/load_fact_table.py"])

    if step:
        steps_passed += 1
    else:
        steps_failed += 1
        logger.error("Fact load failed. Aborting.")
        sys.exit(1)

    if run_step("Quality: Data Checks", [PYTHON, "scripts/data_quality.py"]):
        steps_passed += 1
    else:
        steps_failed += 1
        logger.warning("Quality checks had issues.")

    if run_step("Export: Reports", [PYTHON, "scripts/export_reports.py"]):
        steps_passed += 1
    else:
        steps_failed += 1

    if not args.skip_viz:
        if run_step("Visualize: Charts", [PYTHON, "scripts/visualize.py"]):
            steps_passed += 1
        else:
            steps_failed += 1

    elapsed = time.time() - start
    logger.info("=== ETL COMPLETE ===")
    logger.info("Passed: %d | Failed: %d | Time: %.0fs", steps_passed, steps_failed, elapsed)

    if steps_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

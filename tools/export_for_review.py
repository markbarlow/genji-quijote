"""export_for_review.py — export review_pool.json to a CSV for manual curation.

Writes one row per pair with columns: id, genji_half, quijote_half, review.
Leave the review column blank to keep a pair; mark x/X/n/N to remove it.

Usage:
    python3 tools/export_for_review.py
    python3 tools/export_for_review.py --pool review_pool.json --output review_pool.csv
"""

import argparse
import csv
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent


def main() -> None:
    """Read the pool JSON and write a review CSV with one pair per row.

    Returns
    -------
    None
    """
    parser = argparse.ArgumentParser(
        description="Export a pair pool JSON to a CSV for manual review."
    )
    parser.add_argument(
        "--pool",
        default=str(_REPO_ROOT / "review_pool.json"),
        help="Path to the pool JSON file (default: review_pool.json).",
    )
    parser.add_argument(
        "--output",
        default=str(_REPO_ROOT / "review_pool.csv"),
        help="Path for the output CSV file (default: review_pool.csv).",
    )
    args = parser.parse_args()

    pool_path = Path(args.pool)
    output_path = Path(args.output)

    with pool_path.open(encoding="utf-8") as f:
        data = json.load(f)

    pairs = data["pairs"]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "genji_half", "quijote_half", "review"])
        for pair in pairs:
            writer.writerow([
                pair["id"],
                pair["genji_half"],
                pair["quijote_half"],
                "",  # review column — fill in x/X/n/N to remove
            ])

    print(f"Wrote {len(pairs)} rows to {output_path}")
    print("Mark rows to REMOVE with x (or X/n/N) in the 'review' column.")
    print("Leave blank (or mark y/Y) to keep a pair.")


if __name__ == "__main__":
    main()

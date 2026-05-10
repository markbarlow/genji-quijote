"""apply_review.py — apply a marked review CSV to produce the final sentences.json.

Reads the marked review_pool.csv and review_pool.json, excludes rows marked for
removal, re-numbers the surviving pairs from gq-0001, and writes sentences.json
with the standard meta envelope.

Removal convention:
    x, X, n, N  → remove
    blank, y, Y → keep

Usage:
    python3 tools/apply_review.py
    python3 tools/apply_review.py --count 1021 --output sentences.json
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent

_REMOVE_MARKERS = {"x", "X", "n", "N"}
_EDIT_MARKERS = {"e", "E"}


def main() -> None:
    """Read the marked CSV, filter pairs, and write the final output JSON.

    Returns
    -------
    None
        Exits with code 1 if any referenced id is missing from the pool.
    """
    parser = argparse.ArgumentParser(
        description="Apply a marked review CSV to produce the final sentences.json."
    )
    parser.add_argument(
        "--csv",
        default=str(_REPO_ROOT / "review_pool.csv"),
        help="Path to the marked review CSV (default: review_pool.csv).",
    )
    parser.add_argument(
        "--pool",
        default=str(_REPO_ROOT / "review_pool.json"),
        help="Path to the pool JSON file (default: review_pool.json).",
    )
    parser.add_argument(
        "--output",
        default=str(_REPO_ROOT / "sentences.json"),
        help="Output path for the final JSON (default: sentences.json).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1021,
        help="Maximum number of pairs to keep (default: 1021). "
             "If more survive review, the top N by score are kept.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    pool_path = Path(args.pool)
    output_path = Path(args.output)

    # Load the full pool indexed by id.
    with pool_path.open(encoding="utf-8") as f:
        pool_data = json.load(f)
    pool_by_id = {p["id"]: p for p in pool_data["pairs"]}

    # Read the CSV. Collect ids to keep; for E rows, store the edited half texts.
    kept_ids: list[str] = []
    edits: dict[str, tuple[str, str]] = {}  # id → (genji_half, quijote_half)
    removed_count = 0
    edited_count = 0
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            marker = row.get("review", "").strip()
            if marker in _REMOVE_MARKERS:
                removed_count += 1
            else:
                kept_ids.append(row["id"])
                if marker in _EDIT_MARKERS:
                    edits[row["id"]] = (
                        " ".join(row["genji_half"].split()),
                        " ".join(row["quijote_half"].split()),
                    )
                    edited_count += 1

    print(
        f"Kept: {len(kept_ids)}  Removed: {removed_count}  Edited: {edited_count}",
        file=sys.stderr,
    )

    # Build reverse lookups so edited halves can find the correct source sentence
    # even when copied from a different row or trimmed.
    pool_pairs = pool_data["pairs"]
    source_by_genji_half = {p["genji_half"]: p["genji_source"] for p in pool_pairs}
    source_by_quijote_half = {p["quijote_half"]: p["quijote_source"] for p in pool_pairs}
    chapter_by_genji_half = {p["genji_half"]: p["genji_meta"]["chapter"] for p in pool_pairs}
    chapter_by_quijote_half = {p["quijote_half"]: p["quijote_meta"]["chapter"] for p in pool_pairs}

    def _resolve_genji(half: str) -> tuple[str, str]:
        """Return (genji_source, chapter) for a possibly-trimmed Genji half.

        Tries exact match first, then prefix match — handles the case where
        words were removed from the end of the original half text.
        """
        if half in source_by_genji_half:
            return source_by_genji_half[half], chapter_by_genji_half[half]
        # Prefix match: find pool halves that start with the edited text.
        candidates = [p for p in pool_pairs if p["genji_half"].startswith(half)]
        if candidates:
            best = min(candidates, key=lambda p: len(p["genji_half"]))
            return best["genji_source"], best["genji_meta"]["chapter"]
        return half, "pinned"

    def _resolve_quijote(half: str) -> tuple[str, str]:
        """Return (quijote_source, chapter) for a possibly-trimmed Quijote half.

        Tries exact match first, then suffix match — handles the case where
        words were removed from the start of the original half text.
        """
        if half in source_by_quijote_half:
            return source_by_quijote_half[half], chapter_by_quijote_half[half]
        # Suffix match: find pool halves that end with the edited text.
        candidates = [p for p in pool_pairs if p["quijote_half"].endswith(half)]
        if candidates:
            best = min(candidates, key=lambda p: len(p["quijote_half"]))
            return best["quijote_source"], best["quijote_meta"]["chapter"]
        return half, "pinned"

    # Resolve ids to pair dicts, preserving pool order.
    # For edited rows, replace the half texts, rebuild display, and update source
    # attribution to match the new half text (handles cross-row half swaps).
    surviving = []
    missing = []
    for pid in kept_ids:
        if pid not in pool_by_id:
            missing.append(pid)
            continue
        pair = dict(pool_by_id[pid])  # shallow copy so we don't mutate the pool
        if pid in edits:
            new_genji, new_quijote = edits[pid]
            pair["genji_half"] = new_genji
            pair["quijote_half"] = new_quijote
            pair["display"] = new_genji + " " + new_quijote
            # Update source attribution to follow the (possibly trimmed) half text.
            g_source, g_chapter = _resolve_genji(new_genji)
            q_source, q_chapter = _resolve_quijote(new_quijote)
            pair["genji_source"] = g_source
            pair["quijote_source"] = q_source
            pair["genji_meta"] = dict(pair["genji_meta"])
            pair["genji_meta"]["chapter"] = g_chapter
            pair["quijote_meta"] = dict(pair["quijote_meta"])
            pair["quijote_meta"]["chapter"] = q_chapter
        surviving.append(pair)

    if missing:
        print(f"ERROR: {len(missing)} ids in CSV not found in pool:", file=sys.stderr)
        for pid in missing[:10]:
            print(f"  {pid}", file=sys.stderr)
        sys.exit(1)

    # If more pairs survive than the target count, keep the top N by score.
    if len(surviving) > args.count:
        surviving.sort(key=lambda p: p["score"], reverse=True)
        surviving = surviving[: args.count]
        print(
            f"Trimmed to top {args.count} by score ({len(kept_ids) - args.count} dropped).",
            file=sys.stderr,
        )
    elif len(surviving) < args.count:
        print(
            f"Warning: only {len(surviving)} pairs survive review (target was {args.count}).",
            file=sys.stderr,
        )

    # Re-number pairs sequentially from gq-0001 in score order.
    surviving.sort(key=lambda p: p["score"], reverse=True)
    for i, pair in enumerate(surviving, start=1):
        pair["id"] = f"gq-{i:04d}"

    # Write output with the standard meta envelope.
    output = {
        "meta": {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(surviving),
            "window_size": 30,
        },
        "pairs": surviving,
    }
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Written {len(surviving)} pairs to {output_path}", file=sys.stderr)
    print(f"\nNext step: cp {output_path} web/data/pairs.json", file=sys.stderr)


if __name__ == "__main__":
    main()

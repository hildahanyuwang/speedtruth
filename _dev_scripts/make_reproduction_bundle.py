#!/usr/bin/env python
"""SpeedTruth, build the public reproduction bundle.

WHY THIS EXISTS
---------------
reproduce.py recomputes every published figure from the committed outputs, and the
README says a reviewer can run it. That was not true of the public repository: the two
files it reads, output/speed_safety_score.geojson and output/speed_safety_score_cv.geojson,
are per-segment tables carrying the posted limit and the 85th-percentile speed, so the
Fair Data Use Agreement keeps them out of the repository and .gitignore blocks them.
The check therefore exited with "missing committed output(s)" for anyone who cloned it.

This script writes the largest artefact that fits inside the licence: one row per scored
segment carrying only classifications and flags, no coordinates, and no speed value of
any kind.

WHAT IS DELIBERATELY NOT IN IT
------------------------------
speed_limit, p85, median speed, sample size, excess_kmh, limit_gap_kmh,
ped_fatality_pct, safe_threshold, the three score components, and geometry. Each of
those either is a probe-derived measurement or inverts to one: ped_fatality_pct is a
monotonic function of the observed speed and would return it exactly, and limit_gap_kmh
is the posted limit minus a threshold that is reconstructible from open data.

WHAT IT DOES DISCLOSE, STATED PLAINLY
-------------------------------------
severity is the observed speed minus the survivable speed placed in one of four bands,
so a reader who reconstructs the survivable speed from OpenStreetMap can bound the
observed speed on that segment to a range. That is a band, not a value, and it is the
same reduction in detail that the published map layers already show.

Run:  python _dev_scripts/make_reproduction_bundle.py
Out:  output/reproduction_bundle.csv   (one row per scored segment)
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "output" / "speed_safety_score.geojson"        # rule-based score
CV = ROOT / "output" / "speed_safety_score_cv.geojson"       # imagery-corrected score
OUT = ROOT / "output" / "reproduction_bundle.csv"

# The two validation result files carry speed_limit, p85, lat and lon per image, so they
# stay local. Their headline counts do not, and .gitignore already allows aggregate-only
# summaries, so the counts are written out separately. A figure checked against one of
# these is checked, not recomputed, and reproduce.py labels it that way.
BLINDTEST = ROOT / "output" / "blindtest_results.json"
ROADAUDIT = ROOT / "output" / "cv_validation.json"
BLINDTEST_SUM = ROOT / "output" / "blindtest_summary.json"
ROADAUDIT_SUM = ROOT / "output" / "roadaudit_summary.json"

# Every column here is either an identifier, an open-data attribute, or a band.
KEEP_BASE = ["seg_id", "region", "road_class", "has_school_market", "severity", "tier"]
KEEP_CV = ["seg_id", "has_cv", "severity_v3", "tier_v3"]

# Anything on this list must never reach the bundle. Checked at the end rather than
# trusted, because the cost of getting it wrong is a licence breach, not a bug.
FORBIDDEN = {
    "speed_limit", "p85", "median_speed", "speed_median", "speed_p85", "sample_size",
    "SampleSizeTotal", "traffic_pct", "pct_over", "oper_over", "excess_kmh",
    "limit_gap_kmh", "ped_fatality_pct", "ped_fatal_pct", "safe_threshold",
    "safe_threshold_v3", "safe_speed", "score", "speed_safety_score", "score_v3",
    "c_oper", "c_limit", "c_vru", "limit_excess", "oper_excess", "dev_gap", "dev_abs",
    "dev_ratio", "expected_limit", "geometry", "street_link", "imagery_bbox",
}


def write_validation_summaries():
    """Counts only, from the two local per-image result files."""
    import json

    if BLINDTEST.exists():
        rows = json.loads(BLINDTEST.read_text(encoding="utf-8"))
        agree = sum(1 for r in rows if r.get("agree"))
        BLINDTEST_SUM.write_text(json.dumps({
            "source": "output/blindtest_results.json (kept local: carries per-image "
                      "speed_limit, p85, lat, lon)",
            "n_rated": len(rows),
            "n_agreed": agree,
            "pct_agreed": round(100 * agree / len(rows), 1),
            "note": "blind human rating vs the vision model, one image per segment",
        }, indent=2), encoding="utf-8")
        print(f"wrote {BLINDTEST_SUM.relative_to(ROOT)}  ({agree}/{len(rows)})")

    if ROADAUDIT.exists():
        recs = json.loads(ROADAUDIT.read_text(encoding="utf-8"))
        ROADAUDIT_SUM.write_text(json.dumps({
            "source": "output/cv_validation.json (kept local: same reason)",
            "n_rated": len(recs),
            "note": "blind road-condition audit, stratified sample",
        }, indent=2), encoding="utf-8")
        print(f"wrote {ROADAUDIT_SUM.relative_to(ROOT)}  (n={len(recs)})")


def main():
    import geopandas as gpd

    missing = [p for p in (BASE, CV) if not p.exists()]
    if missing:
        sys.exit("this script runs where the restricted outputs live, not in the public "
                 "repository. Missing: " + ", ".join(p.name for p in missing))

    g = gpd.read_file(BASE)[KEEP_BASE]
    c = gpd.read_file(CV)[KEEP_CV]
    b = g.merge(c, on="seg_id", how="inner", validate="one_to_one")
    if len(b) != len(g):
        sys.exit(f"join lost rows: {len(g)} -> {len(b)}")

    b["has_school_market"] = b["has_school_market"].astype(bool)
    b["has_cv"] = b["has_cv"].fillna(False).astype(bool)

    # The Phase 1 outputs on disk still carry the old tier words. The bundle is a public
    # artefact and should speak the same vocabulary as the published map layers, so the
    # rename recorded in CHANGELOG_PHASE2.md is applied here rather than left to the
    # reader to discover.
    b[["tier", "tier_v3"]] = b[["tier", "tier_v3"]].replace(
        {"Monitor": "Watch", "Compliant": "Lower priority"})

    leaked = sorted(FORBIDDEN & set(b.columns))
    if leaked:
        sys.exit(f"REFUSING TO WRITE: restricted columns present: {leaked}")

    b.to_csv(OUT, index=False)
    write_validation_summaries()

    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  rows    {len(b):,}   (one per scored segment)")
    print(f"  columns {list(b.columns)}")
    print(f"  size    {OUT.stat().st_size/1e6:.2f} MB")
    print("\n  by region: " + ", ".join(f"{k} {v:,}" for k, v in b.region.value_counts().items()))
    print("  no coordinates, no speed values, no thresholds. See the module docstring "
          "for what the severity band does and does not reveal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

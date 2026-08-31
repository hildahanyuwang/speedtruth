#!/usr/bin/env python
"""SpeedTruth, Maharashtra external validation, statistics recovery + road-class axis.

WHY THIS EXISTS
---------------
The district-level external validation was already built and run in Phase 1
(src/validate_maharashtra.py, June 2026): our scored segments were spatially joined
to district boundaries and compared against the Maharashtra Highway Traffic Police
"Black Spots 2021-2023" counts. Two problems were found on 2026-08-17:

  1. THE NUMBERS WERE NEVER RECORDED. The original script only PRINTED the
     correlations; output/validation_maharashtra.csv keeps the per-district table but
     not a single correlation coefficient. The finding exists nowhere in the project.
  2. THE ORIGINAL SCRIPT NO LONGER RUNS. It reads district boundaries from a session
     scratchpad directory that has since been deleted, so nobody, including us, can
     reproduce it.

This script fixes both without needing the boundary file: the spatial join is already
baked into the published per-district table, so the correlations can be recomputed from
output/validation_maharashtra.csv alone. Keyless, no confidential data, third-party
runnable, same discipline as reproduce.py.

It also adds the second validation axis, which needs no boundaries at all: the official
source says 85.9% of black spots sit on national + state highways. Do our high-priority
segments concentrate the same way?

Run: python _dev_scripts/maharashtra_validation_stats.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
DISTRICTS = ROOT / "output" / "validation_maharashtra.csv"
BLACKSPOTS = ROOT / "output" / "external_validation" / "maharashtra_blackspots_2021_2023.csv"
SEGMENTS = ROOT / "output" / "egis" / "speedtruth_segments_maharashtra.geojson"
OUT = ROOT / "output" / "validation_maharashtra_stats.json"

# OSM highway class -> Indian administrative road category.
# THIS MAPPING IS AN ASSUMPTION AND IT IS NOT CLEAN. In Indian OSM, national highways
# are usually 'trunk' but sometimes 'primary'; state highways are usually 'primary' but
# sometimes 'secondary'. So the NH-vs-SH split below must NOT be quoted as a result.
# What survives the ambiguity is the combined bucket: trunk+primary ~ NH+SH, which is
# the comparison this script actually leads with.
CLASS_MAP = {
    "motorway": "Expressway", "motorway_link": "Expressway",
    "trunk": "NH (assumed)", "trunk_link": "NH (assumed)",
    "primary": "SH (assumed)", "primary_link": "SH (assumed)",
    "secondary": "MDR/other", "secondary_link": "MDR/other",
    "tertiary": "MDR/other", "tertiary_link": "MDR/other",
    "unclassified": "MDR/other", "residential": "MDR/other",
}
HIGHWAY_BUCKET = {"NH (assumed)", "SH (assumed)", "Expressway"}


def resid_rank(y, x):
    """Rank residuals of y after removing a linear fit on rank(x). Used for the partial
    correlation, so that 'district has more road' cannot manufacture agreement."""
    rx, ry = pd.Series(x).rank(), pd.Series(y).rank()
    b = np.polyfit(rx, ry, 1)
    return ry - (b[0] * rx + b[1])


def district_axis(out):
    d = pd.read_csv(DISTRICTS)
    d["bs_per_100km"] = d["black_spots"] / d["covered_km"] * 100
    print(f"AXIS 1, district level, n = {len(d)} districts "
          f"(Mumbai Suburban already excluded as an outlier in Phase 1)")

    tests = [
        ("absolute", "black_spots ~ n_priority1", "black_spots", "n_p1",
         "confounded by district network size, shown for transparency"),
        ("absolute", "black_spots ~ n_scored (exposure proxy)", "black_spots", "n_scored",
         "how much of any agreement is just 'more road, more of everything'"),
        ("normalised", "bs_per_100km ~ mean_score", "bs_per_100km", "mean_score",
         "the fair test: intensity vs intensity"),
        ("normalised", "bs_per_100km ~ frac_priority1", "bs_per_100km", "frac_p1",
         "the fair test, on the tier the product actually publishes"),
    ]
    res = {}
    for kind, label, a, b, note in tests:
        rho, p = spearmanr(d[a], d[b])
        res[label] = {"kind": kind, "spearman_rho": round(float(rho), 3),
                      "p_value": round(float(p), 4), "n": len(d), "note": note}
        print(f"  [{kind:10s}] {label:42s} rho = {rho:+.3f}  (p = {p:.3f})")

    rho, p = spearmanr(resid_rank(d["n_p1"], d["n_scored"]),
                       resid_rank(d["black_spots"], d["n_scored"]))
    res["partial: n_priority1 ~ black_spots | n_scored"] = {
        "kind": "partial", "spearman_rho": round(float(rho), 3),
        "p_value": round(float(p), 4), "n": len(d),
        "note": "does our flagging track black spots BEYOND simply having more road"}
    print(f"  [{'partial':10s}] {'n_priority1 ~ black_spots | n_scored':42s} "
          f"rho = {rho:+.3f}  (p = {p:.3f})")

    # The six zero-reporting units are a data-quality fact, not a safety fact.
    zeros = sorted(d.loc[d.black_spots == 0, "district"])
    print(f"\n  districts officially reporting ZERO black spots: {len(zeros)} -> {', '.join(zeros)}")
    print("  ^ zero almost certainly means 'not reported', not 'safe'. These stay in the")
    print("    correlation (dropping them would be cherry-picking) but must be named in the app.")
    out["axis1_district"] = {"n_districts": len(d), "tests": res,
                             "zero_reporting_districts": zeros}
    return d


def roadclass_axis(out):
    bs = pd.read_csv(BLACKSPOTS)
    tot = int(bs["total"].sum())
    official = {"NH": int(bs.NH.sum()), "SH": int(bs.SH.sum()),
                "Other": int(bs.other_roads.sum()), "MDR": int(bs.MDR.sum()),
                "Expressway": int(bs.expressway.sum())}
    off_hwy = (official["NH"] + official["SH"] + official["Expressway"]) / tot
    print(f"\nAXIS 2, road-class concentration, needs no boundaries")
    print(f"  official black spots, n = {tot}: " +
          "  ".join(f"{k} {v}" for k, v in official.items()))
    print(f"  official share on national + state highway + expressway: {off_hwy:.1%}")

    with open(SEGMENTS, encoding="utf-8") as fh:
        seg = pd.DataFrame([f["properties"] for f in json.load(fh)["features"]])
    seg["cat"] = seg["road_class"].map(CLASS_MAP).fillna("MDR/other")
    seg["is_hwy"] = seg["cat"].isin(HIGHWAY_BUCKET)

    rows = {}
    for label, sub in (("all scored segments", seg),
                       ("Priority 1", seg[seg.priority == "Priority 1"]),
                       ("severity = Critical", seg[seg.severity == "Critical"])):
        share = float(sub["is_hwy"].mean()) if len(sub) else float("nan")
        # length-weighted too: a share of segments and a share of network km can differ
        share_km = float(sub.loc[sub.is_hwy, "length_km"].sum() / sub["length_km"].sum())
        rows[label] = {"n": len(sub), "share_on_highway_by_count": round(share, 3),
                       "share_on_highway_by_km": round(share_km, 3)}
        print(f"  ours, {label:22s} n = {len(sub):>5,}  on NH/SH/expressway: "
              f"{share:.1%} of segments, {share_km:.1%} of km")

    out["axis2_roadclass"] = {
        "official_counts": official, "official_total": tot,
        "official_share_highway": round(off_hwy, 3),
        "ours": rows,
        "caveat": "OSM highway classes are mapped to Indian road categories by assumption; "
                  "the NH-vs-SH split is NOT reliable and is not reported. Only the "
                  "combined NH+SH+expressway bucket is compared.",
    }


def main():
    if not DISTRICTS.exists():
        sys.exit(f"missing {DISTRICTS}")
    out = {"generated_by": "_dev_scripts/maharashtra_validation_stats.py",
           "source_official": "Maharashtra Highway Traffic Police, Black Spots 2021-2023 "
                              "(779 black spots, counts by police unit, no coordinates)",
           "note": "district joins were performed in Phase 1 by src/validate_maharashtra.py; "
                   "that script is no longer runnable (its boundary file lived in a deleted "
                   "scratchpad). This script recomputes the statistics from the published "
                   "per-district table, which already contains the join."}
    district_axis(out)
    roadclass_axis(out)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

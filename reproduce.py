#!/usr/bin/env python3
"""
SpeedTruth, single-command reproduction of every published number.

    python reproduce.py

Recomputes each headline figure that appears in the report, the front page and the
published map layers, straight from the committed outputs, and checks it against the
value that was actually published. Exits non-zero if any of them has drifted.

WHY THIS EXISTS
    The ADB technical review noted: "The pipeline was not re-executed for this review.
    The assessment is based on code inspection and the committed outputs... The specific
    verification figures were not independently reproduced," and suggested "a single top
    level script that regenerates exactly the report's numbers." This is that script.

WHAT IT NEEDS
    Nothing but this repository. No API keys, no credentials, and none of the
    confidential challenge data. It reads only the committed outputs in output/.
    That is deliberate: a reviewer has to be able to run it.

WHAT IT DOES NOT DO
    It does not re-derive the scores from the raw challenge data. That upstream chain
    (harmonise -> VRU -> score -> imagery pull -> imagery classify -> re-score ->
    corridors) needs the FDUA-restricted source data, a Mapillary token and a vision
    model key, so it cannot be run by a third party. `--chain` prints that chain, with
    the script and the input each stage needs, so the path is at least unambiguous.

USAGE
    python reproduce.py                 # recompute, check, report
    python reproduce.py --json          # same, machine-readable
    python reproduce.py --chain         # print the upstream pipeline order and exit
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")

# Console encodings vary; never let a glyph kill the run.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- committed inputs -------------------------------------------------------------
BASE = "output/speed_safety_score.geojson"        # rule-based score, all raw factor inputs
CV = "output/speed_safety_score_cv.geojson"       # imagery-corrected thresholds and score
CORRIDORS_SUMMARY = "output/corridors_summary.json"
BLINDTEST = "output/blindtest_results.json"
ROADAUDIT = "output/cv_validation.json"

# The priority-tier vocabulary was renamed for Phase 2 (see CHANGELOG_PHASE2.md).
# Phase 1 outputs on disk still carry the old words, so normalise on load and the
# script keeps working whichever vintage of the outputs it is pointed at.
TIER_RENAME = {"Monitor": "Watch", "Compliant": "Lower priority"}
LOWEST_TIER = "Lower priority"


def load():
    import geopandas as gpd

    missing = [p for p in (BASE, CV) if not os.path.exists(p)]
    if missing:
        sys.exit(f"missing committed output(s): {', '.join(missing)}\n"
                 f"run this from the repository root.")
    g = gpd.read_file(BASE)
    c = gpd.read_file(CV)
    for df in (g, c):
        for col in ("tier", "tier_v3"):
            if col in df.columns:
                df[col] = df[col].replace(TIER_RENAME)
    return g, c


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --- the claims -------------------------------------------------------------------
# Each entry: what was published, where it was published, and how to recompute it.
# `tol` is absolute tolerance; rounded/approximate published figures get a real one
# rather than being quietly reported as exact.
def build_claims(g, c, corr, blind, audit):
    def sev_base(v):
        return int((g.severity == v).sum())

    def sev_v3(v):
        return int((c.severity_v3 == v).sum())

    changed = (c.severity != c.severity_v3)
    covered = c.has_cv.fillna(False).astype(bool)
    gap = c.speed_limit - c.safe_threshold_v3
    sm = g[g.has_school_market]

    claims = [
        dict(id="segments_scored", published=14711, tol=0,
             where="index.html, FINDINGS sec.1",
             label="Road segments scored",
             value=len(g)),

        dict(id="critical_after_imagery", published=4861, tol=0,
             where="index.html headline, published ArcGIS layer (severity = Critical)",
             label="Critical severity, after imagery correction",
             value=sev_v3("Critical")),

        dict(id="critical_after_THA", published=4652, tol=0,
             where="EGIS layer, Thailand",
             label="  of which Thailand",
             value=int(((c.severity_v3 == "Critical") & (c.region == "THA")).sum())),

        dict(id="critical_after_MAH", published=209, tol=0,
             where="EGIS layer, Maharashtra",
             label="  of which Maharashtra",
             value=int(((c.severity_v3 == "Critical") & (c.region == "MAH")).sum())),

        # The gap between the posted limit and the survivable speed, published as
        # limit_gap_kmh on the segment layer. Unclipped, so a negative value means the
        # sign is already at or below the survivable speed and the excess is a
        # compliance or design problem rather than a signing one.
        dict(id="limit_above_survivable", published=10944, tol=0,
             where="EGIS layer (limit_gap_kmh > 0); StoryMap ch.1",
             label="Segments whose posted limit exceeds the survivable speed",
             value=int((gap > 0).sum())),

        dict(id="limit_above_survivable_pct_THA", published=91.7, tol=0.1,
             where="StoryMap ch.7 (Thailand)",
             label="  Thailand, % of its network",
             value=round(100 * (gap[c.region == "THA"] > 0).mean(), 1)),

        dict(id="limit_above_survivable_pct_MAH", published=20.5, tol=0.1,
             where="StoryMap ch.7 (Maharashtra)",
             label="  Maharashtra, % of its network",
             value=round(100 * (gap[c.region == "MAH"] > 0).mean(), 1)),

        dict(id="limit_gap_median_THA", published=30, tol=0,
             where="StoryMap ch.1 (Thailand's median gap, km/h)",
             label="  Thailand, median gap (km/h)",
             value=int(gap[c.region == "THA"].median())),

        dict(id="limit_gap_median_MAH", published=-15, tol=0,
             where="StoryMap ch.7 (Maharashtra's median gap is negative)",
             label="  Maharashtra, median gap (km/h)",
             value=int(gap[c.region == "MAH"].median())),

        dict(id="critical_before_imagery", published=5973, tol=0,
             where="Phase 1 FINDINGS (the 'before' value; see CHANGELOG_PHASE2.md item 4)",
             label="Critical severity, rule score before imagery",
             value=sev_base("Critical")),

        dict(id="imagery_covered", published=3537, tol=0,
             where="FINDINGS, IMAGERY_VERIFICATION",
             label="Segments with imagery",
             value=int(covered.sum())),

        dict(id="imagery_coverage_pct", published=24.0, tol=0.5,
             where="index.html, IMAGERY_VERIFICATION (~24% of the network)",
             label="Imagery coverage, %",
             value=round(100 * covered.mean(), 1)),

        dict(id="rebanded", published=1736, tol=0,
             where="index.html headline (fourth number)",
             label="Segments the imagery moved to a different severity band",
             value=int(changed.sum())),

        dict(id="rebanded_share_of_covered", published=49.1, tol=1.0,
             where="index.html (about half of those it covered)",
             label="  as a share of covered segments, %",
             value=round(100 * changed[covered].mean(), 1)),

        dict(id="critical_net_change", published=-1112, tol=0,
             where="RESUME_HERE, number reconciliation",
             label="  net change in Critical (negative = downgrade)",
             value=sev_v3("Critical") - sev_base("Critical")),

        dict(id="compliant_net_change", published=501, tol=0,
             where="RESUME_HERE, number reconciliation",
             label="  net change in Compliant severity",
             value=sev_v3("Compliant") - sev_base("Compliant")),

        dict(id="school_market", published=4017, tol=0,
             where="index.html",
             label="Segments beside a school or market",
             value=len(sm)),

        dict(id="school_market_ped_fatality_median", published=52.0, tol=1.0,
             where='index.html (median ~52% pedestrian fatality risk, modelled)',
             label="  median modelled pedestrian fatality probability at P85, %",
             value=round(float(sm.ped_fatality_pct.median()), 1)),

        dict(id="critical_but_lowest_tier", published=1192, tol=0,
             where="FINDINGS sec.3.1",
             label="Critical severity yet lowest priority tier in its own region",
             value=int(((g.severity == "Critical") & (g.tier == LOWEST_TIER)).sum())),

        dict(id="priority1_THA", published=1115, tol=0,
             where="published ArcGIS layer, Thailand",
             label="Priority 1, Thailand (after imagery)",
             value=int(((c.tier_v3 == "Priority 1") & (c.region == "THA")).sum())),

        dict(id="priority1_MAH", published=358, tol=0,
             where="published ArcGIS layer, Maharashtra",
             label="Priority 1, Maharashtra (after imagery)",
             value=int(((c.tier_v3 == "Priority 1") & (c.region == "MAH")).sum())),
    ]

    if corr:
        reg = corr.get("by_region", {})

        def rg(r, k):
            return reg.get(r, {}).get(k)

        claims += [
            dict(id="corridor_units_total", published=2869, tol=0,
                 where="CORRIDORS, corridor map",
                 label="Flagged units (corridors + unlinked stretches)",
                 value=int(corr["n_corridors"])),

            # A corridor is two or more contiguous flagged segments of the same named
            # road. A single flagged segment with no named neighbour stays on its own
            # and is an "unlinked stretch", not a corridor: the longest runs 179.7 km.
            dict(id="corridors_linked", published=405, tol=0,
                 where="CORRIDORS sec.1 (405 multi-segment routes)",
                 label="  of which linked corridors",
                 value=int(corr["n_multi_segment"])),
            dict(id="corridors_linked_THA", published=337, tol=0,
                 where="CORRIDORS, corridor layer (unit_type = Corridor)",
                 label="    Thailand",
                 value=rg("THA", "n_corridors")),
            dict(id="corridors_linked_MAH", published=68, tol=0,
                 where="CORRIDORS, corridor layer (unit_type = Corridor)",
                 label="    Maharashtra",
                 value=rg("MAH", "n_corridors")),
            dict(id="corridors_unnamed", published=0, tol=0,
                 where="CORRIDORS (every linked corridor carries a road name)",
                 label="  linked corridors with no road name",
                 value=(rg("THA", "corridors_unnamed") or 0) + (rg("MAH", "corridors_unnamed") or 0)),

            # The single most important asymmetry in the corridor layer, and the reason
            # the application must not default to a corridors-only view: the same filter
            # keeps most of Thailand's problem and almost none of Maharashtra's.
            dict(id="corridor_harm_share_THA", published=54.0, tol=1.0,
                 where="StoryMap ch.7; CORRIDORS",
                 label="Share of Thailand's avoidable harm on linked corridors, %",
                 value=round(100 * rg("THA", "corridor_harm_share"), 1)),
            dict(id="corridor_harm_share_MAH", published=7.0, tol=1.0,
                 where="StoryMap ch.7; CORRIDORS",
                 label="  same for Maharashtra, %",
                 value=round(100 * rg("MAH", "corridor_harm_share"), 1)),

            dict(id="top20pct_benefit_share", published=76.0, tol=1.0,
                 where="index.html (top 20% carry ~76% of the avoidable harm)",
                 label="Avoidable harm in the top 20% of all flagged units, %",
                 value=round(100 * float(corr["top20pct_benefit_share"]), 1)),
            dict(id="top20pct_benefit_share_corridors", published=67.0, tol=1.0,
                 where="StoryMap ch.7 (the corridors-only reading of the figure above)",
                 label="  same, counting linked corridors only, %",
                 value=round(100 * float(corr["top20pct_benefit_share_corridors_only"]), 1)),

            # Flagged, deliberately not merged: the proximity-and-length test cannot
            # tell a divided road from two genuinely parallel ones. Published as a
            # caution. Was 499 while the test compared centroids, which for a line are
            # not on the line; it now compares the halfway point along each road
            # (AUDIT-C7), and two Maharashtra units fall out.
            dict(id="dual_pair_units", published=497, tol=0,
                 where="corridor layer (possible_dual_pair = Yes)",
                 label="Units possibly counting one road twice",
                 value=int(corr["dual_pair_units"])),
            dict(id="dual_pair_units_that_are_corridors", published=0, tol=0,
                 where="CORRIDORS (the flag falls entirely on unlinked stretches)",
                 label="  of which linked corridors",
                 value=int(corr["dual_pair_units_that_are_corridors"])),
        ]

    if blind:
        agree = sum(1 for b in blind if b.get("agree"))
        claims += [
            dict(id="blindtest_n", published=24, tol=0,
                 where="index.html, IMAGERY_VERIFICATION Part B",
                 label="Blind imagery test, segments rated",
                 value=len(blind)),
            dict(id="blindtest_agree", published=19, tol=0,
                 where="index.html (19 of 24)",
                 label="  on which the blind human rating agreed",
                 value=agree),
            dict(id="blindtest_agree_pct", published=79.0, tol=1.0,
                 where="index.html, IMAGERY_VERIFICATION (79%)",
                 label="  agreement, %",
                 value=round(100 * agree / len(blind), 1)),
        ]

    if audit:
        claims.append(dict(id="roadaudit_n", published=32, tol=0,
                           where="IMAGERY_VERIFICATION Part D",
                           label="Blind road-condition audit, segments rated",
                           value=len(audit)))
    return claims


# --- things worth stating that are not single numbers ------------------------------
def structural_notes(g, c):
    """Facts a reader should have alongside the table, each recomputed here."""
    covered = c.has_cv.fillna(False).astype(bool)
    changed = (c.severity != c.severity_v3)
    notes = []

    n_before = int((g.tier == "Priority 1").sum())
    n_after = int((c.tier_v3 == "Priority 1").sum())
    moved = int(((g.tier == "Priority 1") != (c.tier_v3 == "Priority 1")).sum())
    notes.append(
        f"Priority tier is a within-region percentile rank, so the imagery correction "
        f"cannot change how many segments are Priority 1 ({n_before} before, {n_after} "
        f"after), only which ones ({moved} segments entered or left). Absolute "
        f"severity is where the correction actually shows: see critical_net_change."
    )

    down = int((changed & covered & (c.severity_v3.map(SEV_RANK) < c.severity.map(SEV_RANK))).sum())
    up = int((changed & covered & (c.severity_v3.map(SEV_RANK) > c.severity.map(SEV_RANK))).sum())
    notes.append(
        f"Of the segments the imagery moved, {down} moved to a less severe band and "
        f"{up} to a more severe one. The correction mostly found the rule threshold too "
        f"harsh; it did not mostly uncover hidden danger."
    )

    notes.append(
        f"Every figure above is computed on the {int(covered.sum()):,} segments that have "
        f"imagery ({100*covered.mean():.0f}% of the network) or on the full "
        f"{len(g):,}, as labelled. One image per segment. The evidence supports the "
        f"direction of the correction, not its precision."
    )
    return notes


SEV_RANK = {"Compliant": 0, "Marginal": 1, "Serious": 2, "Critical": 3}

CHAIN = """\
Upstream chain (needs FDUA-restricted source data and API keys; not runnable by a third party)

  1  src/harmonize.py             challenge road + speed data  ->  harmonised segments
  2  src/vru.py                   OSM VRU exposure             ->  vru_per_km, school/market
  3  src/scoring.py               harmonised + VRU             ->  output/speed_safety_score.geojson
  4  src/imagery_pull.py          Mapillary API (MLY_TOKEN)    ->  output/cv_images*, cv_manifest*
     --scope stratified  fixed validation sample (quota strata)
     --scope priority    every Priority 1/2 segment + a lower-tier sample
     --scope lower       busiest lower-tier segments, to catch under-flagged roads
  5  src/imagery_cv_classify.py   vision model (ANTHROPIC_API_KEY) -> output/cv_labels_full.json
  6  src/scoring_cv.py            score + imagery labels       ->  output/speed_safety_score_cv.geojson
  7  src/corridors.py             corrected score              ->  output/corridors.geojson
  8  _dev_scripts/prepare_egis_uploads.py                      ->  output/egis/*.geojson (published layers)

  Validation, independent of the chain above:
     src/imagery_blindtest.py     blind human vs model         ->  output/blindtest_results.json
     src/imagery_roadaudit.py     blind road-condition audit   ->  output/cv_validation.json
     src/validate_thairsc.py      external validation, Thailand
     src/sensitivity_samplesize.py  probe sample-size sensitivity

  This script (reproduce.py) starts at the committed outputs of stages 3, 6 and 7.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--chain", action="store_true", help="print the upstream pipeline and exit")
    args = ap.parse_args()

    if args.chain:
        print(CHAIN)
        return 0

    g, c = load()
    claims = build_claims(g, c,
                          read_json(CORRIDORS_SUMMARY),
                          read_json(BLINDTEST),
                          read_json(ROADAUDIT))

    for cl in claims:
        cl["ok"] = abs(float(cl["value"]) - float(cl["published"])) <= cl["tol"]

    failed = [cl for cl in claims if not cl["ok"]]

    if args.json:
        print(json.dumps({"checked": len(claims),
                          "failed": len(failed),
                          "claims": [{k: v for k, v in cl.items()} for cl in claims],
                          "notes": structural_notes(g, c)},
                         ensure_ascii=False, indent=2, default=str))
        return 1 if failed else 0

    w = max(len(cl["label"]) for cl in claims)
    print(f"\nSpeedTruth, published figures recomputed from committed outputs\n")
    print(f"  {'':{w}}  {'recomputed':>12}  {'published':>10}")
    print(f"  {'-'*w}  {'-'*12}  {'-'*10}")
    for cl in claims:
        mark = " " if cl["ok"] else "  <-- MISMATCH"
        print(f"  {cl['label']:{w}}  {cl['value']:>12}  {cl['published']:>10}{mark}")
    print(f"\n  {len(claims)} figures checked, {len(failed)} mismatched.")

    print("\nWhere each figure is published")
    for cl in claims:
        print(f"  {cl['id']:<34} {cl['where']}")

    print("\nRead alongside the table")
    for n in structural_notes(g, c):
        print(f"  - {n}\n")

    if failed:
        print("MISMATCH. A published number no longer matches the outputs. Either the "
              "outputs changed and the text was not updated, or the reverse. "
              "Record the resolution in CHANGELOG_PHASE2.md.")
        return 1
    print("All published figures reproduce from the committed outputs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

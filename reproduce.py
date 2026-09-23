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
VALIDATION_MAH = "output/validation_maharashtra.csv"   # per-district table, Phase 1 join
# The public stand-in for the two files above: classifications and flags only, no
# coordinates and no speed values. Built by _dev_scripts/make_reproduction_bundle.py.
BUNDLE = "output/reproduction_bundle.csv"
# Aggregate stand-ins for the two per-image validation tables, which carry the posted
# limit, P85 and coordinates and so stay local. A figure taken from one of these is
# CHECKED against a committed aggregate, not recomputed, and the table says so.
BLINDTEST_SUM = "output/blindtest_summary.json"
ROADAUDIT_SUM = "output/roadaudit_summary.json"

# OSM highway class -> Indian road category, for the external-validation road-class axis.
# The mapping is an assumption and it is not clean: in Indian OSM a national highway is
# usually 'trunk' but sometimes 'primary', and a state highway usually 'primary' but
# sometimes 'secondary'. The NH-vs-SH split is therefore never reported; only the
# combined bucket below, which is immune to that particular ambiguity.
HIGHWAY_BUCKET = {"motorway", "motorway_link", "trunk", "trunk_link",
                  "primary", "primary_link"}

# The priority-tier vocabulary was renamed for Phase 2 (see CHANGELOG_PHASE2.md).
# Phase 1 outputs on disk still carry the old words, so normalise on load and the
# script keeps working whichever vintage of the outputs it is pointed at.
TIER_RENAME = {"Monitor": "Watch", "Compliant": "Lower priority"}
LOWEST_TIER = "Lower priority"


def load():
    """Return (g, c, restricted).

    Two ways in. If the per-segment outputs are present, every figure can be
    recomputed and `restricted` is True. Those two files carry the posted limit and
    the 85th-percentile speed, so the Fair Data Use Agreement keeps them out of the
    public repository. A reader who cloned the repository instead gets
    output/reproduction_bundle.csv, which holds the classifications and flags but no
    speed value of any kind; `restricted` is then False and the handful of figures
    that need a speed are reported as not recomputable rather than silently dropped.
    """
    if all(os.path.exists(p) for p in (BASE, CV)):
        import geopandas as gpd

        g = gpd.read_file(BASE)
        c = gpd.read_file(CV)
        for df in (g, c):
            for col in ("tier", "tier_v3"):
                if col in df.columns:
                    df[col] = df[col].replace(TIER_RENAME)
        return g, c, True

    if os.path.exists(BUNDLE):
        import pandas as pd

        b = pd.read_csv(BUNDLE)
        for col in ("tier", "tier_v3"):
            b[col] = b[col].replace(TIER_RENAME)
        g = b[["seg_id", "region", "road_class", "has_school_market", "severity", "tier"]]
        c = b[["seg_id", "region", "severity", "severity_v3", "tier_v3", "has_cv"]]
        return g, c, False

    sys.exit(f"found neither the per-segment outputs ({BASE}, {CV}) nor the public "
             f"bundle ({BUNDLE}).\nrun this from the repository root.")


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def district_correlations(path=VALIDATION_MAH):
    """Recompute the Maharashtra district-level correlations from the published
    per-district table. The Phase 1 spatial join to district boundaries is already
    baked into that table, so no boundary file is needed and this runs for a third
    party. Returns None if the table or scipy is absent."""
    if not os.path.exists(path):
        return None
    try:
        from scipy.stats import spearmanr
    except ImportError:
        return None
    import numpy as np
    import pandas as pd

    d = pd.read_csv(path)
    d["bs_per_100km"] = d["black_spots"] / d["covered_km"] * 100

    def resid_rank(y, x):
        rx, ry = pd.Series(x).rank(), pd.Series(y).rank()
        b = np.polyfit(rx, ry, 1)
        return ry - (b[0] * rx + b[1])

    rho = lambda a, b: round(float(spearmanr(d[a], d[b])[0]), 3)
    return {
        "n": len(d),
        "abs_p1": rho("black_spots", "n_p1"),
        "abs_scored": rho("black_spots", "n_scored"),
        "norm_score": rho("bs_per_100km", "mean_score"),
        "norm_frac_p1": rho("bs_per_100km", "frac_p1"),
        "partial": round(float(spearmanr(resid_rank(d["n_p1"], d["n_scored"]),
                                         resid_rank(d["black_spots"], d["n_scored"]))[0]), 3),
        "zero_reporting": int((d["black_spots"] == 0).sum()),
    }


def highway_share_mah(g, c):
    """Share of Maharashtra segments sitting on the national highway / state highway /
    expressway bucket, at three levels of selection. Recomputed from the two committed
    geojsons: road class comes from the rule-based output, the tier and severity from
    the imagery-corrected one, joined on seg_id."""
    m = g[["seg_id", "region", "road_class"]].merge(
        c[["seg_id", "tier_v3", "severity_v3"]], on="seg_id", how="inner")
    m = m[m.region == "MAH"]
    hwy = m.road_class.isin(HIGHWAY_BUCKET)
    share = lambda mask: round(100 * float(hwy[mask].mean()), 1)
    return {
        "all": share(m.index == m.index),
        "p1": share(m.tier_v3 == "Priority 1"),
        "critical": share(m.severity_v3 == "Critical"),
    }


# --- the claims -------------------------------------------------------------------
# Each entry: what was published, where it was published, and how to recompute it.
# `tol` is absolute tolerance; rounded/approximate published figures get a real one
# rather than being quietly reported as exact.
def build_claims(g, c, corr, blind, audit, restricted, skipped, blind_sum, audit_sum):
    def sev_base(v):
        return int((g.severity == v).sum())

    def sev_v3(v):
        return int((c.severity_v3 == v).sum())

    changed = (c.severity != c.severity_v3)
    covered = c.has_cv.fillna(False).astype(bool)
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

    # --- figures that need a speed value -----------------------------------------
    # These six are the ones the licence keeps out of the public bundle. The gap is
    # the posted limit minus the survivable speed, published as limit_gap_kmh on the
    # segment layer; unclipped, so a negative value means the sign is already at or
    # below the survivable speed and the excess is a compliance or design problem
    # rather than a signing one. The pedestrian figure is a function of the observed
    # speed. Anyone holding the challenge data can recompute all six by running this
    # script where the per-segment outputs live.
    RESTRICTED_IDS = ["limit_above_survivable", "limit_above_survivable_pct_THA",
                      "limit_above_survivable_pct_MAH", "limit_gap_median_THA",
                      "limit_gap_median_MAH", "school_market_ped_fatality_median",
                      "critical_THA_limit_above", "critical_THA_gap_median", "flagged_THA",
                      "flagged_THA_limit_above_pct", "flagged_MAH_limit_needs_no_change",
                      "threshold_floor30_share_THA", "threshold_floor50_pct_above_THA",
                      "threshold_plus10_pct_above_THA", "threshold_plus20_pct_above_THA",
                      "flagged_MAH_enforcement_km", "flagged_MAH_enforcement_median_excess"]
    if restricted:
        gap = c.speed_limit - c.safe_threshold_v3
        claims += [
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

            dict(id="school_market_ped_fatality_median", published=52.0, tol=1.0,
                 where='index.html (median ~52% pedestrian fatality risk, modelled)',
                 label="  median modelled pedestrian fatality probability at P85, %",
                 value=round(float(sm.ped_fatality_pct.median()), 1)),

            # The narrative leans on these five and none of them was checked here
            # before 11 September 2026. Three related figures carried in the drafting
            # notes turned out to be stale when recomputed on that date, so anything
            # the text asserts now has to be in this table or be marked as unchecked.
            dict(id="critical_THA_limit_above", published=4539, tol=0,
                 where="StoryMap ch.3 (of the Critical segments in Thailand)",
                 label="Thai Critical segments also posted above the survivable speed",
                 value=int(((c.severity_v3 == "Critical") & (c.region == "THA")
                            & (gap > 0)).sum())),
            dict(id="critical_THA_gap_median", published=40, tol=0,
                 where="StoryMap ch.3 (the middle of that distribution)",
                 label="  their median gap (km/h)",
                 value=int(gap[(c.severity_v3 == "Critical") & (c.region == "THA")].median())),
            dict(id="flagged_THA", published=2785, tol=0,
                 where="StoryMap ch.7 (segments flagged as priorities in Thailand)",
                 label="Flagged segments, Thailand (Priority 1 or 2)",
                 value=int((c.tier_v3.isin(["Priority 1", "Priority 2"]) & (c.region == "THA")).sum())),
            dict(id="flagged_THA_limit_above_pct", published=100.0, tol=0.1,
                 where="StoryMap ch.7 (every single one)",
                 label="  of which posted above the survivable speed, %",
                 value=round(100 * float((gap[c.tier_v3.isin(["Priority 1", "Priority 2"])
                                              & (c.region == "THA")] > 0).mean()), 1)),
            # The counterweight to the sentence above, and the reason the application
            # does not tell a ministry to lower every limit it flags.
            dict(id="flagged_MAH_limit_needs_no_change", published=282, tol=0,
                 where="StoryMap ch.7 (the limit needs no change at all)",
                 label="Flagged segments in Maharashtra already at or below survivable",
                 value=int((c.tier_v3.isin(["Priority 1", "Priority 2"]) & (c.region == "MAH")
                            & (gap <= 0)).sum())),

            # Every one of those 282 is also a segment where the observed speed already
            # exceeds the posted limit, which is what turns a negative finding into a
            # list someone can act on. Published after an adversarial review pointed out
            # that the Maharashtra reader was being handed seven statements about what
            # their problem is not, and nothing they could fund.
            dict(id="flagged_MAH_enforcement_km", published=3861, tol=2,
                 where="StoryMap ch.7 (3,861 kilometres)",
                 label="  their length, km",
                 value=int(round(g.length_m[c.tier_v3.isin(["Priority 1", "Priority 2"])
                                            & (c.region == "MAH") & (gap <= 0)].sum() / 1000))),
            # 36.5, not 37. The narrative first carried 37 because an exploratory
            # print used a zero-decimal format and the rounded display was copied into
            # the text. Published to one decimal so the rounding cannot be repeated,
            # and the sentence on screen says "more than 36", which is true of more
            # than half the traffic on those segments.
            dict(id="flagged_MAH_enforcement_median_excess", published=36.5, tol=0.1,
                 where="StoryMap ch.7 (half the traffic at least 36 km/h over)",
                 label="  median observed speed above the posted limit there, km/h",
                 value=round(float((c.p85 - c.speed_limit)[c.tier_v3.isin(["Priority 1", "Priority 2"])
                                                          & (c.region == "MAH") & (gap <= 0)].median()), 1)),

            # The survivable speed is the input the headline rests on, so the headline
            # has to be reported against alternative rulers rather than one. Full run in
            # _dev_scripts/threshold_sensitivity.py; these four are the ones the
            # narrative quotes. The first answers the specific objection that the 30
            # km/h pedestrian floor is producing the result: it is not, because it
            # applies to a fifth of the Thai network.
            dict(id="threshold_floor30_share_THA", published=20.1, tol=0.1,
                 where="StoryMap ch.6 (the 30 km/h floor applies to a fifth of it)",
                 label="Thai segments whose survivable speed is 30 km/h, %",
                 value=round(100 * float((c.safe_threshold_v3[c.region == "THA"]
                                          .round(0) == 30).mean()), 1)),
            dict(id="threshold_floor50_pct_above_THA", published=91.2, tol=0.1,
                 where="StoryMap ch.6 (raise the floor to 50 and it barely moves)",
                 label="  share posted above, if the floor were 50 km/h, %",
                 value=round(100 * float(((c.speed_limit
                                           - c.safe_threshold_v3.clip(lower=50)) > 0)
                                         [c.region == "THA"].mean()), 1)),
            dict(id="threshold_plus10_pct_above_THA", published=78.8, tol=0.1,
                 where="StoryMap ch.6 (add 10 km/h to every threshold)",
                 label="  share posted above, if every threshold rose 10 km/h, %",
                 value=round(100 * float(((gap - 10) > 0)[c.region == "THA"].mean()), 1)),
            dict(id="threshold_plus20_pct_above_THA", published=52.3, tol=0.1,
                 where="StoryMap ch.6 (and 20)",
                 label="  share posted above, if every threshold rose 20 km/h, %",
                 value=round(100 * float(((gap - 20) > 0)[c.region == "THA"].mean()), 1)),
        ]
    else:
        skipped.extend(RESTRICTED_IDS)

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

    if blind or blind_sum:
        if blind:
            n, agree, basis = len(blind), sum(1 for b in blind if b.get("agree")), "recomputed"
        else:
            n, agree, basis = blind_sum["n_rated"], blind_sum["n_agreed"], "aggregate"
        claims += [
            dict(id="blindtest_n", published=24, tol=0, basis=basis,
                 where="index.html, IMAGERY_VERIFICATION Part B",
                 label="Blind imagery test, segments rated",
                 value=n),
            dict(id="blindtest_agree", published=19, tol=0, basis=basis,
                 where="index.html (19 of 24)",
                 label="  on which the blind human rating agreed",
                 value=agree),
            dict(id="blindtest_agree_pct", published=79.0, tol=1.0, basis=basis,
                 where="index.html, IMAGERY_VERIFICATION (79%)",
                 label="  agreement, %",
                 value=round(100 * agree / n, 1)),
        ]

    if audit or audit_sum:
        n = len(audit) if audit else audit_sum["n_rated"]
        claims.append(dict(id="roadaudit_n", published=32, tol=0,
                           basis="recomputed" if audit else "aggregate",
                           where="IMAGERY_VERIFICATION Part D",
                           label="Blind road-condition audit, segments rated",
                           value=n))

    # --- external validation, Maharashtra ---------------------------------------
    # Ground truth: Maharashtra Highway Traffic Police, "Black Spots 2021-2023", 779
    # black spots counted by police unit with no coordinates. Two axes, and they do not
    # agree with each other. Both are recomputed here so neither can drift quietly.
    WHERE_MAH = ("external validation, Maharashtra; full run in "
                 "_dev_scripts/maharashtra_validation_stats.py")
    dc = district_correlations()
    if dc:
        claims += [
            dict(id="mah_val_districts", published=34, tol=0, where=WHERE_MAH,
                 label="Maharashtra validation, districts compared",
                 value=dc["n"]),
            dict(id="mah_val_rho_absolute_p1", published=0.332, tol=0.002, where=WHERE_MAH,
                 label="  rho, black spots ~ Priority 1 segments (absolute)",
                 value=dc["abs_p1"]),
            dict(id="mah_val_rho_absolute_scored", published=0.495, tol=0.002, where=WHERE_MAH,
                 label="  rho, black spots ~ scored segments (network size)",
                 value=dc["abs_scored"]),
            dict(id="mah_val_rho_norm_score", published=0.290, tol=0.002, where=WHERE_MAH,
                 label="  rho, black spots per 100 km ~ mean score",
                 value=dc["norm_score"]),
            dict(id="mah_val_rho_norm_frac_p1", published=-0.029, tol=0.002, where=WHERE_MAH,
                 label="  rho, black spots per 100 km ~ Priority 1 share",
                 value=dc["norm_frac_p1"]),
            # The one that matters: once district network size is removed, the
            # agreement disappears. Reported because it is the expected result for a
            # tool that looks for misaligned limits rather than for past crashes.
            dict(id="mah_val_rho_partial", published=-0.103, tol=0.002, where=WHERE_MAH,
                 label="  rho, partial, controlling for network size",
                 value=dc["partial"]),
            dict(id="mah_val_zero_districts", published=5, tol=0, where=WHERE_MAH,
                 label="  districts officially reporting zero black spots",
                 value=dc["zero_reporting"]),
        ]

    hs = highway_share_mah(g, c)
    claims += [
        dict(id="mah_hwy_share_all", published=61.8, tol=0.2, where=WHERE_MAH,
             label="Maharashtra segments on NH/SH/expressway, all scored, %",
             value=hs["all"]),
        dict(id="mah_hwy_share_p1", published=84.4, tol=0.2, where=WHERE_MAH,
             label="  Priority 1 only, %",
             value=hs["p1"]),
        dict(id="mah_hwy_share_critical", published=93.3, tol=0.2, where=WHERE_MAH,
             label="  severity Critical only, %",
             value=hs["critical"]),
    ]

    # Two different strengths of check, and the table should not blur them. Most figures
    # are recomputed from per-segment data here. The corridor figures are read from
    # output/corridors_summary.json, which src/corridors.py wrote: that catches a
    # published number drifting from the outputs, but it does not re-derive the number
    # from the segments, so it is a weaker check and is labelled as one.
    FROM_AGGREGATE = {
        "corridor_units_total", "corridors_linked", "corridors_linked_THA",
        "corridors_linked_MAH", "corridors_unnamed", "corridor_harm_share_THA",
        "corridor_harm_share_MAH", "top20pct_benefit_share",
        "top20pct_benefit_share_corridors", "dual_pair_units",
        "dual_pair_units_that_are_corridors",
    }
    for cl in claims:
        cl.setdefault("basis", "aggregate" if cl["id"] in FROM_AGGREGATE else "recomputed")
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

    g, c, restricted = load()
    corr, blind, audit = (read_json(CORRIDORS_SUMMARY), read_json(BLINDTEST),
                          read_json(ROADAUDIT))

    blind_sum = read_json(BLINDTEST_SUM) if not blind else None
    audit_sum = read_json(ROADAUDIT_SUM) if not audit else None

    skipped = []
    if not corr:
        skipped += ["corridor_units_total", "corridors_linked", "corridors_linked_THA",
                    "corridors_linked_MAH", "corridors_unnamed", "corridor_harm_share_THA",
                    "corridor_harm_share_MAH", "top20pct_benefit_share",
                    "top20pct_benefit_share_corridors", "dual_pair_units",
                    "dual_pair_units_that_are_corridors"]
    if not blind and not blind_sum:
        skipped += ["blindtest_n", "blindtest_agree", "blindtest_agree_pct"]
    if not audit and not audit_sum:
        skipped += ["roadaudit_n"]

    claims = build_claims(g, c, corr, blind, audit, restricted, skipped,
                          blind_sum, audit_sum)

    for cl in claims:
        cl["ok"] = abs(float(cl["value"]) - float(cl["published"])) <= cl["tol"]

    failed = [cl for cl in claims if not cl["ok"]]

    if args.json:
        print(json.dumps({"checked": len(claims),
                          "failed": len(failed),
                          "not_recomputable": skipped,
                          "restricted_inputs_present": restricted,
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
        star = "~" if cl["basis"] == "aggregate" else " "
        print(f" {star}{cl['label']:{w}}  {cl['value']:>12}  {cl['published']:>10}{mark}")
    n_agg = sum(1 for cl in claims if cl["basis"] == "aggregate")
    print(f"\n  {len(claims)} figures checked, {len(failed)} mismatched.")
    if n_agg:
        print(f"  ~ marks the {n_agg} figures CHECKED against a committed aggregate rather "
              f"than recomputed\n    from per-segment data. That catches drift between the "
              f"text and the outputs, but it\n    does not re-derive the number, so it is "
              f"the weaker of the two checks.")

    if skipped:
        print(f"\n  {len(skipped)} figures could NOT be recomputed here, and are named "
              f"rather than dropped:")
        for i in skipped:
            print(f"    {i}")
        if not restricted:
            print(f"\n  Why: this run used {BUNDLE}, which carries the classifications "
                  f"and flags\n  but no speed value of any kind. The posted limit and the "
                  f"85th-percentile speed are\n  probe-derived and the Fair Data Use "
                  f"Agreement keeps them out of this repository.\n  Anyone holding the "
                  f"challenge data can recompute all of them by running this script\n  "
                  f"where the per-segment outputs live. See REPRODUCIBILITY.md.")

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
    if skipped:
        print(f"\nAll {len(claims)} figures reproducible from the inputs present here do "
              f"reproduce. {len(skipped)} were not attempted, and are listed above.")
        return 0
    print("All published figures reproduce from the committed outputs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

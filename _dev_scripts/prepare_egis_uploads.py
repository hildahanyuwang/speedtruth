"""
SpeedTruth, Phase 2 Step 1: prepare the ArcGIS Online (ADB EGIS) upload layers.

Single parameterised entry point that turns the Phase 1 analysis outputs into the
two layers that are actually published in the application, per the ADB Phase 2
Guidelines: "Only upload final data you will use in products, ensure it only
contains attributes needed, provide clear field aliases and complete metadata."

What it does, and why:

  1. SLIMS the attribute set. Phase 1 outputs carry intermediate and superseded
     columns (dropped factors, v2/v3 duplicates, diagnostics). Those stay in the
     analysis repo; they do not go to a ministry-facing map.

  2. MAKES THE SCORE SELF-EXPLAINING. The reviewer asked us to "keep the per
     segment factor attribution explicit". No Phase 1 output actually carried it:
     speed_safety_score_cv.geojson holds only the composite. Here the three
     weighted factor contributions are recomputed with the SAME functions the
     scoring module uses (imported, not reimplemented) so they sum to the score.
     A planner clicking a segment can see why it scored what it scored.

  3. KEEPS THE IMAGERY EFFECT VISIBLE AND CAVEATED. The base (rule-threshold) and
     final (imagery-corrected) scores are both published, plus a plain-language
     field saying what the imagery did to this segment and on what evidence.
     Evidence strength travels with the number, at the same volume.

  4. SHRINKS THE GEOMETRY. Source coordinates carry 15 decimal places (sub-nanometre).
     Six decimals is ~0.1 m, far finer than the road centrelines justify.

  5. EMITS FIELD ALIASES as JSON, so the ArcGIS Online layer configuration is
     reproducible rather than hand-typed.

Run:
    python _dev_scripts/prepare_egis_uploads.py                  # both layers
    python _dev_scripts/prepare_egis_uploads.py --layer segments
    python _dev_scripts/prepare_egis_uploads.py --precision 5 --outdir output/egis

Inputs : output/speed_safety_score.geojson       (base scores + all raw factor inputs)
         output/speed_safety_score_cv.geojson    (imagery-corrected thresholds/scores)
         output/corridors.geojson                (fundable corridor aggregation)
Outputs: <outdir>/speedtruth_segments.geojson
         <outdir>/speedtruth_corridors.geojson
         <outdir>/field_aliases.json
         <outdir>/prepare_report.json            (row counts, size deltas, checks)
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
import geopandas as gpd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from scoring import WEIGHTS, _norm_region, severity_band  # noqa: E402  single source of truth

TIER_RENAME = {"Monitor": "Watch", "Compliant": "Lower priority"}

BASE = "output/speed_safety_score.geojson"
CV = "output/speed_safety_score_cv.geojson"
CORRIDORS = "output/corridors.geojson"
WEIGHTS_CSV = "output/weight_scenarios_segments.csv"

# Scenario columns as weight_scenarios.py writes them -> the names published on the layer.
# W0 is deliberately NOT carried: it is identical to `priority` and a duplicated column is
# exactly the kind of attribute the Guidelines tell us not to upload.
SCENARIO_FIELDS = {
    "tier_W1_equal": "pri_equal",
    "tier_W2_operating": "pri_oper",
    "tier_W3_regulatory": "pri_limit",
    "tier_W4_vru": "pri_vru",
}

REGION_LABEL = {"THA": "Thailand", "MAH": "Maharashtra, India"}

# ---------------------------------------------------------------------------
# Field aliases. Left = field name written to the layer, right = the label a
# government planner sees in the popup / attribute table. Units always stated.
# ---------------------------------------------------------------------------
SEGMENT_ALIASES = {
    "seg_id":          "Segment ID",
    "region":          "Country / state",
    "road_name":       "Road name",
    "road_class":      "Road class (OpenStreetMap)",
    "setting":         "Setting",
    "length_km":       "Segment length (km)",

    "speed_limit":     "Posted speed limit (km/h, estimated)",
    "speed_p85":       "Observed 85th-percentile speed (km/h)",
    "speed_median":    "Observed median speed (km/h)",
    "safe_speed":      "Safe System survivable speed (km/h)",
    "excess_kmh":      "Operating speed above survivable speed (km/h)",
    # Published unclipped, so the sign carries meaning: positive = the limit itself
    # permits a speed the road environment cannot survive; negative = the limit is
    # already at or below the survivable speed and any excess is a compliance or
    # design problem, not a signing one. c_limit uses the clipped version.
    "limit_gap_kmh":   "Posted limit above (+) or below (-) the survivable speed (km/h)",

    "score":           "Speed Safety Score (0-100)",
    "severity":        "Safe System severity",
    "priority":        "Priority tier (within country/state)",

    # Weight-sensitivity fields. The reviewer left the weighting of the three factors as
    # the one open item, and the planned live weight slider is not possible in the
    # sandbox. These fields are the replacement and are a stronger answer: the weighting
    # was varied offline across 2,000 random weightings, and the result travels with the
    # data instead of being asserted in prose. See _dev_scripts/weight_scenarios.py.
    "robustness":      "Does this Priority 1 depend on the chosen weights?",
    "robust_pct":      "Share of 2,000 weightings ranking this Priority 1 (%)",
    "pri_equal":       "Priority tier if all three factors weighted equally",
    "pri_oper":        "Priority tier if measured speed weighted highest",
    "pri_limit":       "Priority tier if the posted limit weighted highest",
    "pri_vru":         "Priority tier if vulnerable road user exposure weighted highest",

    "c_oper":          "Score from: operating speed above survivable speed (points)",
    "c_limit":         "Score from: posted limit itself permits unsafe speed (points)",
    "c_vru":           "Score from: vulnerable road user exposure (points)",

    "score_base":      "Speed Safety Score before street imagery (0-100)",
    "safe_speed_base": "Survivable speed before street imagery (km/h)",
    "imagery_used":    "Road condition read from street imagery?",
    "imagery_effect":  "Effect of street imagery on the survivable speed",
    "evidence":        "Evidence behind the survivable speed",

    "ped_fatal_pct":   "Pedestrian fatality risk if struck at observed speed (%)",
    "vru_per_km":      "Vulnerable road user generators per km",
    "school_market":   "School or market on this segment",
    "probe_obs":       "Probe vehicle observations behind the speed estimate",
    "limit_diagnosis": "Why the limit looks misaligned",
    "imagery_bbox":    "Street imagery lookup extent (W,S,E,N)",
}

CORRIDOR_ALIASES = {
    "corridor_id":     "Corridor ID",
    # A "Corridor" is two or more contiguous flagged segments of the same named road.
    # An "Unlinked stretch" is a single flagged segment with no named neighbour to join.
    "unit_type":       "Corridor (linked) or unlinked stretch",
    "region":          "Country / state",
    "road_name":       "Road name",
    "rank":            "Investment priority rank (within country/state, by unit type)",
    "length_km":       "Corridor length (km)",
    "n_segments":      "Flagged segments in this corridor",
    "n_critical":      "Segments at Critical severity",
    "n_serious":       "Segments at Serious severity",
    # AUDIT-P1 (2026-08-28): one label per unit became a set of actions, because the
    # three underlying tests can be true at once. Each is rebuildable from published
    # segment fields: lower the limit from limit_gap_kmh > 0, enforcement from
    # speed_p85 > speed_limit, protection from school_market.
    "intervention":    "Indicative actions needed (from the most demanding segment)",
    "cost_tier":       "Indicative cost tier of the most demanding segment (1 = lowest)",
    "benefit_index":   "Relative avoidable-harm index, total (unitless)",
    # Total benefit scales with length, so a long mildly misaligned road outranks a
    # short severe one.
    "benefit_per_km":  "Relative avoidable-harm index per km (unitless)",
    "bcr_index":       "Relative benefit-cost index (unitless, not an economic appraisal)",
    # Flagged on centroid proximity and matching length, which cannot distinguish a
    # dual carriageway from two genuinely parallel roads.
    "possible_dual_pair": "Possibly the same road counted twice (verify before funding)",
    "inspect_at":      "Suggested inspection point (lat,lon)",
}

# Rounding: attribute precision that is defensible, not what float64 happens to hold.
SEGMENT_ROUND = {
    "length_km": 2, "speed_limit": 0, "speed_p85": 1, "speed_median": 1,
    "safe_speed": 0, "safe_speed_base": 0, "excess_kmh": 1, "limit_gap_kmh": 0,
    "score": 1, "score_base": 1, "c_oper": 1, "c_limit": 1, "c_vru": 1,
    "ped_fatal_pct": 1, "vru_per_km": 3, "probe_obs": 0, "robust_pct": 1,
}
CORRIDOR_ROUND = {"length_km": 1, "benefit_index": 3, "benefit_per_km": 3, "bcr_index": 2}


# The caveat that must travel with every imagery-adjusted number. It is NOT repeated
# into every feature (that would add megabytes of identical prose and make a popup
# unreadable); it goes into the layer description and the popup template, where it is
# actually read. Written out to layer_notes.md for pasting into the ArcGIS item.
EVIDENCE_NOTES = {
    "Street imagery (1 image)":
        "The survivable speed for this segment was adjusted using ONE street-level image, "
        "classified by a declared vision model and validated by a blind test against human "
        "rating. One image per segment supports the DIRECTION of the adjustment, not its "
        "precision. Reference road-assessment systems inspect imagery at 100 m intervals or "
        "finer. Treat imagery-adjusted segments as candidates for inspection, not as verified "
        "road-condition measurements.",
    "Rule-based (no imagery)":
        "No street imagery was available for this segment, so the survivable speed comes from "
        "the rule-based method (road class, setting, and presence of vulnerable road user "
        "generators). It has not been checked against what the road actually looks like.",
}


def _imagery_effect(row):
    """Short coded value; the reasoning lives in the popup template, not in every row."""
    if not row["imagery_used"]:
        return "None - no imagery"
    d = row["safe_speed"] - row["safe_speed_base"]
    if d > 0.5:
        return "Raised - road better than the rule assumed"
    if d < -0.5:
        return "Lowered - road worse than the rule assumed"
    return "Agreed with the rule-based value"


def build_segments(precision):
    base = gpd.read_file(BASE)
    cv = gpd.read_file(CV)[
        ["seg_id", "safe_threshold_v3", "score_v3", "severity_v3", "tier_v3", "has_cv"]
    ]
    base["seg_id"] = base["seg_id"].astype(str)
    cv["seg_id"] = cv["seg_id"].astype(str)
    g = base.merge(cv, on="seg_id", how="left", validate="one_to_one")

    missing = int(g["score_v3"].isna().sum())
    if missing:
        raise SystemExit(f"{missing} segments have no imagery-corrected score; join is unsound.")

    # Recompute the three weighted contributions on the FINAL (v3) threshold, using the
    # scoring module's own normalisation so the parts reconstruct the published score.
    g["_limit_excess"] = (g["speed_limit"] - g["safe_threshold_v3"]).clip(lower=0)
    g["_oper_excess"] = (g["p85"] - g["safe_threshold_v3"]).clip(lower=0)
    g["_oper_over"] = g["p85"] - g["safe_threshold_v3"]
    n_oper = _norm_region(g, "_oper_excess")
    n_limit = _norm_region(g, "_limit_excess")
    n_vru = _norm_region(g, "vru_per_km")
    g["c_oper"] = WEIGHTS["oper_excess"] * n_oper * 100
    g["c_limit"] = WEIGHTS["limit_excess"] * n_limit * 100
    g["c_vru"] = WEIGHTS["vru_exposure"] * n_vru * 100

    recon = (g["c_oper"] + g["c_limit"] + g["c_vru"] - g["score_v3"]).abs().max()
    if recon > 0.05:
        raise SystemExit(f"Factor contributions do not reconstruct the score (max gap {recon:.3f}).")

    out = pd.DataFrame({
        "seg_id":          g["seg_id"],
        "region":          g["region"].map(REGION_LABEL).fillna(g["region"]),
        "road_name":       g["name"].fillna("(unnamed road)"),
        "road_class":      g["road_class"],
        "setting":         g["land_use"].str.title(),
        "length_km":       g["length_m"] / 1000.0,
        "speed_limit":     g["speed_limit"],
        "speed_p85":       g["p85"],
        "speed_median":    g["median_speed"],
        "safe_speed":      g["safe_threshold_v3"],
        "excess_kmh":      g["_oper_over"],
        "limit_gap_kmh":   g["speed_limit"] - g["safe_threshold_v3"],
        "score":           g["score_v3"],
        "severity":        g["severity_v3"],
        # Priority-tier vocabulary renamed 2026-08-10 (author's decision): the Phase 1
        # labels "Monitor" / "Compliant" became "Watch" / "Lower priority". "Compliant"
        # was wrong for "bottom half of the within-region ranking", and a segment can be
        # severity=Critical and priority=Compliant at once, which reads as a contradiction
        # to a non-technical user. Applied here so layers built from Phase 1 outputs carry
        # the product vocabulary without re-running the whole pipeline; src/scoring.py now
        # emits the new labels directly. See CHANGELOG_PHASE2.md.
        "priority":        g["tier_v3"].replace(TIER_RENAME),
        "c_oper":          g["c_oper"],
        "c_limit":         g["c_limit"],
        "c_vru":           g["c_vru"],
        "score_base":      g["speed_safety_score"],
        "safe_speed_base": g["safe_threshold"],
        "imagery_used":    g["has_cv"].fillna(False).astype(bool),
        "ped_fatal_pct":   g["ped_fatality_pct"],
        "vru_per_km":      g["vru_per_km"],
        "school_market":   g["has_school_market"].fillna(False).astype(bool),
        "probe_obs":       g["sample_size"],
        "limit_diagnosis": g["governance_flag"].fillna(""),
        "imagery_bbox":    g["street_link"].fillna(""),
    })
    # Weight-sensitivity fields, joined from the sensitivity run. Hard-failing here is
    # deliberate: shipping the layer without them would silently drop the answer to the
    # reviewer's one open item.
    if not os.path.exists(WEIGHTS_CSV):
        raise SystemExit(f"{WEIGHTS_CSV} not found. Run "
                         f"`python _dev_scripts/weight_scenarios.py` first.")
    ws = pd.read_csv(WEIGHTS_CSV)
    ws["seg_id"] = ws["seg_id"].astype(str)
    ws = ws.rename(columns=SCENARIO_FIELDS)
    ws["robustness"] = ws["p1_robustness"]
    ws["robust_pct"] = ws["p1_frequency"] * 100
    keep = ["seg_id", "robustness", "robust_pct"] + list(SCENARIO_FIELDS.values())
    out = out.merge(ws[keep], on="seg_id", how="left", validate="one_to_one")
    if out["robustness"].isna().any():
        raise SystemExit("weight-scenario join left gaps; the two runs are out of sync.")

    out["imagery_effect"] = out.apply(_imagery_effect, axis=1)
    out["evidence"] = np.where(out["imagery_used"],
                               "Street imagery (1 image)", "Rule-based (no imagery)")

    # Em dash and pipe in the free-text diagnosis: readable in GeoJSON, brittle the
    # moment anyone round-trips the layer through CSV or shapefile. Normalise now.
    out["limit_diagnosis"] = (out["limit_diagnosis"]
                              .str.replace("—", "-", regex=False)
                              .str.replace(" | ", "; ", regex=False))

    out = out[list(SEGMENT_ALIASES.keys())]
    for c, nd in SEGMENT_ROUND.items():
        out[c] = out[c].astype(float).round(nd)
    return gpd.GeoDataFrame(out, geometry=g.geometry.values, crs=g.crs)


def build_corridors(precision):
    c = gpd.read_file(CORRIDORS)
    region = c["corridor"].str.slice(0, 3)
    out = pd.DataFrame({
        "corridor_id":  c["corridor"],
        "unit_type":    c["unit_type"],
        "region":       region.map(REGION_LABEL).fillna(region),
        "road_name":    c["road"].replace("(unnamed)", "(unnamed road)"),
        "rank":         c["rank"],
        "length_km":    c["length_km"],
        "n_segments":   c["n_segments"],
        "n_critical":   c["n_critical"],
        "n_serious":    c["n_serious"],
        "intervention": c["dominant_intervention"],
        "cost_tier":    c["cost_tier"],
        "benefit_index": c["benefit"],
        "benefit_per_km": c["benefit_per_km"],
        "bcr_index":    c["mean_bcr_index"],
        # GeoJSON carries real booleans, but ArcGIS Online reads them back as a numeric
        # 0/1 field and renders a graded legend (the same trap as `imagery_used`, see
        # the 8/23 platform report). Written as text so the popup and filter read plainly.
        "possible_dual_pair": c["possible_dual_pair"].map({True: "Yes", False: "No"}),
        "inspect_at":   c["inspect_at"],
    })
    for col, nd in CORRIDOR_ROUND.items():
        out[col] = out[col].astype(float).round(nd)
    return gpd.GeoDataFrame(out[list(CORRIDOR_ALIASES.keys())],
                            geometry=c.geometry.values, crs=c.crs)


def write_layer(gdf, path, precision, simplify_m=0.0):
    """Coordinate precision alone does not get these layers small enough; vertex count
    does. Simplification is per-feature and topology-preserving, so a segment cannot
    self-intersect, but neighbouring segments may develop sub-metre gaps at shared
    ends. That is acceptable for a planning-scale visualisation and unacceptable for
    network analysis, so the analysis repo keeps the full-precision geometry."""
    if simplify_m > 0:
        tol_deg = simplify_m / 111_320.0  # degrees of latitude; conservative at these latitudes
        gdf = gdf.set_geometry(gdf.geometry.simplify(tol_deg, preserve_topology=True))
    try:
        gdf.to_file(path, driver="GeoJSON", COORDINATE_PRECISION=precision)
    except Exception:  # older GDAL/fiona without the creation option
        from shapely import set_precision
        gdf = gdf.set_geometry(set_precision(gdf.geometry.values, 10.0 ** -precision))
        gdf.to_file(path, driver="GeoJSON")
    return os.path.getsize(path)


def vertex_count(gdf):
    return sum(len(ls.coords) for geom in gdf.geometry
               for ls in (geom.geoms if geom.geom_type.startswith("Multi") else [geom]))


def _emit(gdf, stem, a, aliases_key, report, source_mb):
    """Write one logical layer, optionally split by region, and record real sizes."""
    groups = ([(stem, gdf)] if not a.split_region
              else [(f"{stem}_{r.split(',')[0].strip().lower().replace(' ', '_')}", sub)
                    for r, sub in gdf.groupby("region")])
    entries = []
    for name, sub in groups:
        p = os.path.join(a.outdir, f"{name}.geojson")
        size = write_layer(sub, p, a.precision, a.simplify)
        entries.append({"file": f"{name}.geojson", "features": int(len(sub)),
                        "mb": round(size / 1e6, 1)})
        print(f"  {name:38s} {len(sub):>7,} features  {size/1e6:6.1f} MB")
    report[aliases_key] = {
        "fields": int(gdf.shape[1] - 1),
        "source_mb": round(source_mb / 1e6, 1),
        "simplify_m": a.simplify,
        "coordinate_precision": a.precision,
        "outputs": entries,
        "total_mb": round(sum(e["mb"] for e in entries), 1),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--layer", choices=["segments", "corridors", "both"], default="both")
    ap.add_argument("--precision", type=int, default=6,
                    help="coordinate decimal places (6 = ~0.1 m; default 6)")
    ap.add_argument("--simplify", type=float, default=5.0,
                    help="geometry simplification tolerance in metres (0 = off; default 5)")
    ap.add_argument("--split-region", action="store_true", default=True,
                    help="write one file per country/state (default on; planners work in one)")
    ap.add_argument("--no-split-region", dest="split_region", action="store_false")
    ap.add_argument("--outdir", default="output/egis")
    ap.add_argument("--no-scenarios", dest="scenarios", action="store_false", default=True,
                    help="drop the six weight-sensitivity fields. Escape hatch only, for "
                         "when the portal refuses the file size; the layer then no longer "
                         "carries the answer to the reviewer's open item.")
    a = ap.parse_args()

    if not a.scenarios:
        for f in ["robustness", "robust_pct", *SCENARIO_FIELDS.values()]:
            SEGMENT_ALIASES.pop(f, None)
        print("WARNING: weight-sensitivity fields dropped (--no-scenarios).\n")

    os.makedirs(a.outdir, exist_ok=True)
    report, aliases = {}, {}
    print(f"precision={a.precision} dp, simplify={a.simplify} m, split_region={a.split_region}\n")

    if a.layer in ("segments", "both"):
        seg = build_segments(a.precision)
        aliases["speedtruth_segments"] = SEGMENT_ALIASES
        _emit(seg, "speedtruth_segments", a, "segments", report, os.path.getsize(BASE))
        report["segments"]["imagery_coverage_pct"] = round(100 * float(seg["imagery_used"].mean()), 1)
        report["segments"]["by_severity"] = seg["severity"].value_counts().to_dict()
        report["segments"]["source_fields"] = 34

    if a.layer in ("corridors", "both"):
        cor = build_corridors(a.precision)
        aliases["speedtruth_corridors"] = CORRIDOR_ALIASES
        _emit(cor, "speedtruth_corridors", a, "corridors", report, os.path.getsize(CORRIDORS))

    with open(os.path.join(a.outdir, "field_aliases.json"), "w", encoding="utf-8") as f:
        json.dump(aliases, f, ensure_ascii=False, indent=2)
    with open(os.path.join(a.outdir, "prepare_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(os.path.join(a.outdir, "layer_notes.md"), "w", encoding="utf-8") as f:
        f.write("# Layer notes for the ArcGIS Online item description and popup\n\n"
                "Paste these into the hosted layer's description. They carry the evidence\n"
                "caveats that are deliberately NOT repeated into every feature.\n\n")
        for k, v in EVIDENCE_NOTES.items():
            f.write(f"## {k}\n\n{v}\n\n")
        f.write("## Score composition\n\n"
                "Speed Safety Score = "
                + " + ".join(f"{w:.2f} x {k}" for k, w in WEIGHTS.items())
                + ", each factor normalised within its own country/state and scaled to 0-100. "
                "The three `Score from:` fields are those weighted contributions and sum to "
                "the score, so any segment's rank can be traced to its causes.\n")
    print(f"\naliases, report and layer notes written to {a.outdir}/")


if __name__ == "__main__":
    main()

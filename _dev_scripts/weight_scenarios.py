#!/usr/bin/env python
"""SpeedTruth, weight-scenario sensitivity.

WHY THIS EXISTS
---------------
The Phase 1 technical review left exactly one item "open": the weights of the three
scoring factors (0.45 operating-speed excess / 0.35 limit excess / 0.20 VRU exposure)
are asserted, not derived. The original plan was a live weight slider in the app; the
ADB EGIS sandbox cannot recompute a score client-side, so the slider is dead.

This script is the replacement, and it is a better answer than the slider was: instead
of inviting the user to fiddle, it measures how much the ranking actually depends on the
weights, and publishes the result as fields the app can switch between. A slider is a
toy; a sensitivity analysis is evidence.

WHAT IT DOES
------------
1. VALIDATION FIRST. Recomputes the published v2 and v3 scores from the published
   per-segment factors and checks them against the published values. If the offline
   recompute cannot reproduce what is already published, every number below is
   meaningless and the script exits non-zero. Nothing is reported until this passes.
2. Named scenarios: four alternative, defensible weightings plus the baseline.
3. A Dirichlet ensemble (fixed seed) over the weight simplex, giving each segment a
   "how often is this Priority 1 under a random defensible weighting" frequency.
   Segments that are Priority 1 under nearly all weightings are a *robust core* that
   does not depend on our choice of weights. That is the field worth putting on the map.

NO API KEYS, NO CONFIDENTIAL DATA. Reads only the published output/ files, like
reproduce.py, so a third party can re-run it.

Run: python _dev_scripts/weight_scenarios.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "output" / "speed_safety_score.geojson"
CV = ROOT / "output" / "speed_safety_score_cv.geojson"
OUT_JSON = ROOT / "output" / "weight_scenarios.json"
OUT_CSV = ROOT / "output" / "weight_scenarios_segments.csv"

# Baseline, from src/scoring.py WEIGHTS. Kept as a literal so this script stays
# runnable without the src/ pipeline (and so a diff shows if the two ever drift).
BASELINE = {"oper_excess": 0.45, "limit_excess": 0.35, "vru_exposure": 0.20}

# Alternative weightings. Each one has to be defensible out loud to a jury, otherwise
# it is padding: "we tried 20 weightings" means nothing if 16 of them are arbitrary.
SCENARIOS = {
    "W0_baseline": {
        "w": BASELINE,
        "label": "Baseline",
        "rationale": "Published weighting. Operating speed weighted highest as the hardest "
                     "measured safety signal, VRU exposure lowest as the most proxy-dependent.",
    },
    "W1_equal": {
        "w": {"oper_excess": 1 / 3, "limit_excess": 1 / 3, "vru_exposure": 1 / 3},
        "label": "Equal weights",
        "rationale": "The null position: no published evidence establishes a ratio between "
                     "these three factors, so weight them equally and see what changes.",
    },
    "W2_operating": {
        "w": {"oper_excess": 0.60, "limit_excess": 0.25, "vru_exposure": 0.15},
        "label": "Measured-speed first",
        "rationale": "An engineer's reading: only the observed P85 is measured; the limit is "
                     "an administrative artefact and VRU exposure is an OSM proxy.",
    },
    "W3_regulatory": {
        "w": {"oper_excess": 0.30, "limit_excess": 0.50, "vru_exposure": 0.20},
        "label": "Regulatory-lever first",
        "rationale": "A ministry's reading: the posted limit is the lever an authority can "
                     "actually pull this year; operating speed is downstream of design.",
    },
    "W4_vru": {
        "w": {"oper_excess": 0.35, "limit_excess": 0.25, "vru_exposure": 0.40},
        "label": "VRU-first",
        "rationale": "A Safe System / equity reading: exposure of the most vulnerable user "
                     "should dominate, since they bear the consequence of the mismatch.",
    },
}

# Ensemble settings. Floor keeps draws inside the space of weightings anyone would
# actually defend: a weighting that zeroes out a factor is a different model, not a
# perturbation of this one.
N_DRAWS = 2000
WEIGHT_FLOOR = 0.10
SEED = 20260817

PCT_BREAKS = [(0.50, "Watch"), (0.75, "Priority 2"), (0.90, "Priority 1")]
TIER_ORDER = ["Priority 1", "Priority 2", "Watch", "Lower priority"]

# The published output/*.geojson still carry the pre-2026-08-10 tier labels: the rename
# to Watch / Lower priority is applied at EGIS export time, not in the scoring pipeline
# (see _dev_scripts/prepare_egis_uploads.py). Normalise before comparing, otherwise the
# validation gate reports 11,032 spurious "mismatches" that are only a naming difference.
TIER_RENAME = {"Monitor": "Watch", "Compliant": "Lower priority"}


# ---------------------------------------------------------------- core recompute
def load_props(path):
    """Read a GeoJSON's properties into a DataFrame. Geometry is irrelevant here and
    dropping it makes this run in seconds without geopandas/GDAL."""
    with open(path, encoding="utf-8") as fh:
        gj = json.load(fh)
    return pd.DataFrame([f["properties"] for f in gj["features"]])


def soft(x, k):
    """Smooth saturating normalisation, identical to scoring._soft."""
    x = np.maximum(np.asarray(x, dtype=float), 0.0)
    return x / (x + k) if k > 0 else np.clip(x, 0, 1)


def norm_region(df, col):
    """Within-region normalisation with k = median of positive values.
    Identical to scoring._norm_region."""
    out = pd.Series(0.0, index=df.index)
    for _, sub in df.groupby("region"):
        v = df.loc[sub.index, col]
        pos = v[v > 0]
        k = float(pos.median()) if len(pos) else 1.0
        out.loc[sub.index] = soft(v.values, k)
    return out


def score_from_factors(n_oper, n_limit, n_vru, w):
    return ((w["oper_excess"] * n_oper
             + w["limit_excess"] * n_limit
             + w["vru_exposure"] * n_vru) * 100).round(2)


def assign_tiers(df, score):
    """Within-region percentile tiering, identical to scoring.assign_tiers /
    scoring_cv.reassign_tiers."""
    out = pd.Series("Lower priority", index=df.index)
    for _, sub in df.groupby("region"):
        r = score.loc[sub.index].rank(pct=True)
        t = pd.Series("Lower priority", index=sub.index)
        for q, name in PCT_BREAKS:
            t[r >= q] = name
        out.loc[sub.index] = t
    return out


def spearman(a, b):
    """Rank correlation without a scipy dependency: Pearson on ranks."""
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


# ---------------------------------------------------------------- validation gate
def validate(df, factors, published_score, published_tier, which):
    """Reproduce the published score and tier with the baseline weights.

    A score match within 0.01 is exact for our purposes (published values are rounded
    to 2dp). Tiers must match exactly, since a tier is what the map shows.
    """
    s = score_from_factors(*factors, BASELINE)
    t = assign_tiers(df, s)
    dscore = (s - df[published_score]).abs()
    pub_tier = df[published_tier].replace(TIER_RENAME)
    tier_mismatch = int((t != pub_tier).sum())
    ok = bool(dscore.max() <= 0.011 and tier_mismatch == 0)
    print(f"  {which}: max |Δscore| = {dscore.max():.4f} | tier mismatches = {tier_mismatch} "
          f"| {'OK' if ok else 'FAILED'}")
    return ok, s, t


def main():
    base = load_props(BASE)
    cv = load_props(CV)

    # v3 (imagery-corrected) is the version the app publishes, but the imagery-corrected
    # file drops vru_per_km, so join it back from the v2 file on seg_id.
    df = cv.merge(
        base[["seg_id", "vru_per_km"]], on="seg_id", how="left", validate="one_to_one"
    )
    if df["vru_per_km"].isna().any():
        sys.exit("FAILED: vru_per_km did not join onto every segment")

    print(f"Segments: {len(df):,}  (Thailand {int((df.region == 'THA').sum()):,} / "
          f"Maharashtra {int((df.region == 'MAH').sum()):,})")

    # --- v2 factors: rebuilt from the published v2 threshold
    base["limit_excess_v2"] = (base["speed_limit"] - base["safe_threshold"]).clip(lower=0)
    base["oper_excess_v2"] = (base["p85"] - base["safe_threshold"]).clip(lower=0)
    f_v2 = (norm_region(base, "oper_excess_v2"),
            norm_region(base, "limit_excess_v2"),
            norm_region(base, "vru_per_km"))

    # --- v3 factors: same, on the imagery-corrected threshold
    df["limit_excess_v3"] = (df["speed_limit"] - df["safe_threshold_v3"]).clip(lower=0)
    df["oper_excess_v3"] = (df["p85"] - df["safe_threshold_v3"]).clip(lower=0)
    f_v3 = (norm_region(df, "oper_excess_v3"),
            norm_region(df, "limit_excess_v3"),
            norm_region(df, "vru_per_km"))

    print("\nVALIDATION, can the published numbers be reproduced offline?")
    ok2, _, _ = validate(base, f_v2, "speed_safety_score", "tier", "v2 (rule-based)")
    ok3, s3, t3 = validate(df, f_v3, "score_v3", "tier_v3", "v3 (imagery-corrected)")
    if not (ok2 and ok3):
        sys.exit("\nFAILED: offline recompute does not reproduce the published scores. "
                 "Every sensitivity number below would be untrustworthy. Stopping.")
    print("  -> the offline recompute is exact; sensitivity results below are on the same "
          "footing as the published numbers.\n")

    # ------------------------------------------------------------ collinearity check
    # A jury's first counter to "the ranking is stable under reweighting" is: of course it
    # is, your three factors measure the same thing. Answer it before it is asked. If the
    # factors were near-collinear the weights could not matter, and the stability result
    # would be an artefact rather than a finding.
    fac = pd.DataFrame({"n_oper": f_v3[0], "n_limit": f_v3[1], "n_vru": f_v3[2],
                        "region": df["region"]})
    collin = {}
    for r in sorted(df.region.unique()):
        c = fac.loc[fac.region == r, ["n_oper", "n_limit", "n_vru"]].corr(method="spearman")
        collin[r] = {f"{a}~{b}": round(float(c.loc[a, b]), 3)
                     for i, a in enumerate(c.columns) for b in c.columns[i + 1:]}
    print("FACTOR COLLINEARITY (Spearman, within region), is the stability an artefact?")
    for r, d in collin.items():
        print(f"  {r}: " + "  ".join(f"{k} {v:+.2f}" for k, v in d.items()))
    print()

    # ------------------------------------------------------------ named scenarios
    base_p1 = set(df.loc[t3 == "Priority 1", "seg_id"])
    results = {}
    seg_out = pd.DataFrame({"seg_id": df["seg_id"], "region": df["region"],
                            "tier_W0_baseline": t3})

    print("NAMED SCENARIOS (all on the imagery-corrected score, the one the app publishes)")
    print(f"{'scenario':<16}{'weights':<20}{'rank corr':>10}{'P1 kept':>10}{'tier moved':>12}")
    for key, spec in SCENARIOS.items():
        w = spec["w"]
        s = score_from_factors(*f_v3, w)
        t = assign_tiers(df, s)
        seg_out[f"tier_{key}"] = t
        p1 = set(df.loc[t == "Priority 1", "seg_id"])
        kept = len(base_p1 & p1) / len(base_p1)
        moved = int((t != t3).sum())
        rho = spearman(s3, s)
        # within-region rank correlation matters more than pooled: tiers are assigned
        # within region, so a pooled correlation can hide a country-level reshuffle.
        rho_reg = {r: spearman(s3[df.region == r], s[df.region == r])
                   for r in sorted(df.region.unique())}
        results[key] = {
            "label": spec["label"], "rationale": spec["rationale"],
            "weights": w,
            "spearman_vs_baseline": round(rho, 4),
            "spearman_by_region": {r: round(v, 4) for r, v in rho_reg.items()},
            "priority1_n": len(p1),
            "priority1_retained_pct": round(kept * 100, 1),
            "segments_changing_tier": moved,
            "segments_changing_tier_pct": round(moved / len(df) * 100, 1),
        }
        wstr = "/".join(f"{w[k]:.2f}" for k in ("oper_excess", "limit_excess", "vru_exposure"))
        print(f"{key:<16}{wstr:<20}{rho:>10.3f}{kept * 100:>9.1f}%{moved:>12,}")

    # ------------------------------------------------------------ Dirichlet ensemble
    # Random weightings on the simplex with each weight >= WEIGHT_FLOOR. Answers the
    # question a jury actually asks: not "what if we used your four alternatives" but
    # "what if you had picked differently at all".
    rng = np.random.default_rng(SEED)
    raw = rng.dirichlet(np.ones(3), size=N_DRAWS)
    draws = WEIGHT_FLOOR + (1 - 3 * WEIGHT_FLOOR) * raw   # rescale into the floored simplex

    p1_hits = np.zeros(len(df), dtype=int)
    rhos = []
    n_oper, n_limit, n_vru = (f.to_numpy() for f in f_v3)
    for wo, wl, wv in draws:
        s = pd.Series((wo * n_oper + wl * n_limit + wv * n_vru) * 100, index=df.index)
        t = assign_tiers(df, s)
        p1_hits += (t == "Priority 1").to_numpy().astype(int)
        rhos.append(spearman(s3, s))
    freq = p1_hits / N_DRAWS
    seg_out["p1_frequency"] = freq.round(3)

    in_base = (t3 == "Priority 1").to_numpy()
    robust_core = int(((freq >= 0.95) & in_base).sum())
    contested = int(((freq > 0.05) & (freq < 0.95)).sum())
    never = int(((freq <= 0.05) & in_base).sum())
    always_not_base = int(((freq >= 0.95) & ~in_base).sum())

    # A three-way label the map can colour by directly.
    seg_out["p1_robustness"] = np.where(
        freq >= 0.95, "Robust: Priority 1 under nearly any weighting",
        np.where(freq <= 0.05, "Not Priority 1 under nearly any weighting",
                 "Weight-dependent: Priority 1 only under some weightings"))

    rhos = np.array(rhos)
    print(f"\nENSEMBLE, {N_DRAWS:,} random weightings (each weight >= {WEIGHT_FLOOR:.2f}, seed {SEED})")
    print(f"  rank correlation with the published ranking: "
          f"min {rhos.min():.3f} | median {np.median(rhos):.3f} | max {rhos.max():.3f}")
    print(f"  baseline Priority 1 segments: {int(in_base.sum()):,}")
    print(f"    of which robust (Priority 1 in >=95% of weightings): {robust_core:,} "
          f"({robust_core / in_base.sum() * 100:.1f}%)")
    print(f"    of which weight-dependent: {int(in_base.sum()) - robust_core - never:,}")
    print(f"    of which Priority 1 in <=5% of weightings (fragile): {never:,}")
    print(f"  segments Priority 1 in >=95% of weightings but NOT in the published tiering: "
          f"{always_not_base:,}")
    print(f"  contested segments (Priority 1 in 5-95% of weightings): {contested:,}")

    summary = {
        "generated_by": "_dev_scripts/weight_scenarios.py",
        "basis": "imagery-corrected score (score_v3), the version published in the app",
        "validation": {"v2_reproduced": ok2, "v3_reproduced": ok3},
        "n_segments": len(df),
        "baseline_weights": BASELINE,
        "factor_collinearity_spearman": collin,
        "scenarios": results,
        "ensemble": {
            "n_draws": N_DRAWS, "weight_floor": WEIGHT_FLOOR, "seed": SEED,
            "spearman_min": round(float(rhos.min()), 4),
            "spearman_median": round(float(np.median(rhos)), 4),
            "spearman_max": round(float(rhos.max()), 4),
            "baseline_p1": int(in_base.sum()),
            "robust_core": robust_core,
            "weight_dependent": int(in_base.sum()) - robust_core - never,
            "fragile": never,
            "p1_only_under_other_weightings": always_not_base,
            "contested": contested,
        },
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    seg_out.to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"\nWrote {OUT_JSON.relative_to(ROOT)} and {OUT_CSV.relative_to(ROOT)} "
          f"({len(seg_out.columns) - 2} scenario/robustness fields for the EGIS layer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

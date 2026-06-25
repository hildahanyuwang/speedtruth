"""SpeedTruth, Speed Safety Score.

Design principle: not anomaly detection of "P85 deviating from the limit", but a
Safe System anchor: a safe limit should not exceed the speed the most vulnerable
user on the road can survive in a crash.

Safe System survivable speed thresholds (WHO / Towards Zero):
  - pedestrians/cyclists mixing, dense VRU        : 30 km/h
  - intersection / side-impact risk (urban)       : 50 km/h
  - head-on risk (two-way rural)                  : 70 km/h
  - separated, no VRU (motorway)                  : 100+ km/h

The score measures two things:
  (1) does the limit itself permit unsafe speed   limit_excess = SpeedLimit - safe_threshold
  (2) is the operating speed unsafe               oper_excess  = P85       - safe_threshold
combined into a 0-100 composite over three independent factors, banded into four tiers.
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from harmonize import load_all, factor_speed_deviation, factor_function_mismatch
from vru import attach_vru_all, safe_threshold_v1, safe_threshold_v2

# ============================================================================
# v2 scoring (model rebuild, fixing internal audit F1-F12). Design changes and why:
#  - Dropped dev_gap (F7: collinear with oper-limit, corr 0.80) and func_mismatch
#    (F8: zero for 60% of segments, rewards conformity not safety) from the composite,
#    keeping them as governance diagnostics only.
#  - Removed the per-segment helmet multiplier (F2: a 2-value constant dominated by the
#    urban/rural base gap, within-region corr negative; F3: faked segment-level precision).
#    Motorcycle/three-wheeler/modified-vehicle lethality is now a stratum "lethality_context"
#    overlay + the vulnerable-mixed-traffic dimension, not a faked per-segment multiplier.
#  - Smooth saturating normalisation x/(x+k) replaces the hard /40 clip (F10: under the old
#    method 65-74% of Priority-1 segments' main factors saturated to 1, losing discrimination);
#    k is the within-region median of positive values, so the top tier stays rank-ordered.
#  - Presence-based threshold + grade-separated trunk heuristic (F1/F5/F9, see vru.safe_threshold_v2).
#  - Two-axis tiering (F12): absolute Safe-System severity + within-country priority tier.
# ============================================================================
WEIGHTS = {              # three independent factors, sum to 1 (renormalised after removing redundancy)
    "oper_excess":   0.45,   # operating speed above the Safe System threshold (hardest safety signal)
    "limit_excess":  0.35,   # the limit itself permits unsafe speed (permissive limit-setting)
    "vru_exposure":  0.20,   # segment VRU exposure (OSM pedestrian generators, length-robust)
}

def _clip01(x):
    return np.clip(x, 0, 1)

def _soft(x, k):
    """Smooth saturating normalisation: strictly monotonic, asymptotes to 1 without
    clipping, so the top tier keeps its ordering (fixes F10)."""
    x = np.maximum(np.asarray(x, dtype=float), 0.0)
    return x / (x + k) if k > 0 else _clip01(x)

def _norm_region(df, col):
    """Smooth normalisation by the within-region median of positive values (k=median),
    avoiding scale contamination from differing national limit regimes."""
    out = pd.Series(0.0, index=df.index)
    for _, sub in df.groupby("region"):
        v = df.loc[sub.index, col]
        pos = v[v > 0]
        k = float(pos.median()) if len(pos) else 1.0
        out.loc[sub.index] = _soft(v.values, k)
    return out

# Absolute Safe-System severity: how many km/h operating speed exceeds the survivable
# speed (a physical quantity, comparable across countries)
def severity_band(oper_over):
    if oper_over >= 30:  return "Critical"
    if oper_over >= 15:  return "Serious"
    if oper_over > 0:    return "Marginal"
    return "Compliant"

# --- tiering modes ---
# absolute: by absolute score breakpoints (cross-country comparable, but affected by each
#   country's limit regime, so has regional bias)
# within_region: by within-region score percentile (removes regional bias, matches the
#   decision logic of each transport ministry prioritising within its own network)
TIER_MODE = "within_region"
ABS_BREAKS = [(60, "Priority 1"), (40, "Priority 2"), (20, "Monitor")]
PCT_BREAKS = [(0.50, "Monitor"), (0.75, "Priority 2"), (0.90, "Priority 1")]  # low->high, cumulative

def assign_tiers(df, mode=TIER_MODE):
    if mode == "absolute":
        def t(s):
            for thr, name in ABS_BREAKS:
                if s >= thr:
                    return name
            return "Compliant"
        return df["speed_safety_score"].apply(t)
    # within_region: tier by score percentile within each region
    out = pd.Series("Compliant", index=df.index)
    for _, sub in df.groupby("region"):
        r = sub["speed_safety_score"].rank(pct=True)
        tier = pd.Series("Compliant", index=sub.index)
        for q, name in PCT_BREAKS:
            tier[r >= q] = name
        out.loc[sub.index] = tier
    return out

def compute_score(df, weights=None):
    w = weights if weights is not None else WEIGHTS
    df = df.copy()
    # v2 threshold: presence-based + grade-separated trunk heuristic (returns threshold + flag)
    res = df.apply(lambda r: safe_threshold_v2(r), axis=1)
    df["safe_threshold"]      = [t[0] for t in res]
    df["grade_sep_uncertain"] = [t[1] for t in res]

    df["limit_excess"] = (df["speed_limit"] - df["safe_threshold"]).clip(lower=0)
    df["oper_excess"]  = (df["p85"] - df["safe_threshold"]).clip(lower=0)
    df["oper_over"]    = df["p85"] - df["safe_threshold"]            # may be negative: used for absolute severity
    df["dev_gap"]      = (df["p85"] - df["speed_limit"]).abs()       # governance diagnostic only, not in composite

    # smooth saturating normalisation (F10); three independent factors only
    n_oper  = _norm_region(df, "oper_excess")
    n_limit = _norm_region(df, "limit_excess")
    n_vru   = _norm_region(df, "vru_per_km")

    base = (w["oper_excess"] * n_oper
            + w["limit_excess"] * n_limit
            + w["vru_exposure"] * n_vru)
    df["speed_safety_score"] = (base * 100).round(2)   # no helmet multiplier anymore

    # helmet no longer enters the score: reported only as a stratum "lethality context" overlay
    # (honest: a 2-value urban/rural constant, not segment-level)
    df["lethality_context"] = (1 + 0.6 * df["helmet_norate"].fillna(0)).round(3)

    # citable auxiliary indicator: pedestrian fatality probability when struck by a car
    # front at P85. Rosen & Sander (2009). Relative indicator only (German passenger-car
    # calibration; actual risk higher in Thailand/India, see SOURCES.md).
    df["ped_fatality_pct"] = ((1 / (1 + np.exp(6.9 - 0.090 * df["p85"]))) * 100).round(1)

    # --- two-axis tiering (F12) ---
    df["severity"] = df["oper_over"].apply(severity_band)     # absolute Safe-System severity
    df["tier"]     = assign_tiers(df, TIER_MODE)              # within-country priority (decision sequencing)
    return df

# --- governance flags: why a limit may be unmaintained (rule-based, explainable) ---
def governance_flag(row):
    """Rule-based, probabilistic diagnosis of why the limit may be unmaintained.
    Language deliberately hedged ('may', 'probable'), these are inferences, not facts."""
    sl, p85, exp, thr = row["speed_limit"], row["p85"], row["expected_limit"], row["safe_threshold"]
    flags = []
    if sl - thr >= 10:
        flags.append("Limit exceeds Safe System safe speed, limit setting is itself permissive")
    if p85 - sl >= 15:
        flags.append("Operating speed far exceeds limit, road design encourages speed; limit likely not updated after road upgrade / weak enforcement feedback")
    if sl - p85 >= 20:
        flags.append("Limit far above actual operating speed, inflated limit; possible road reclassification without limit downgrade")
    if pd.notna(exp) and abs(sl - exp) >= 15:
        flags.append("Limit deviates markedly from class norm, classification inconsistency")
    if row["land_use"] == "URBAN" and p85 - thr >= 15 and row["helmet_norate"] >= 0.5:
        flags.append("Unsafe operating speed in high-VRU-lethality (low helmet use) urban context, priority downgrade candidate")
    return " | ".join(flags) if flags else "No clear governance anomaly"

def build():
    df = load_all()
    df = factor_speed_deviation(df)
    df = factor_function_mismatch(df)
    df = df.dropna(subset=["speed_limit", "p85"]).copy()
    df = attach_vru_all(df)              # OSM VRU exposure (regions without POIs degrade to 0 exposure)
    df = compute_score(df)
    df["governance_flag"] = df.apply(governance_flag, axis=1)
    return gpd.GeoDataFrame(df, geometry="geometry", crs=4326)

if __name__ == "__main__":
    g = build()
    print(f"Scored segments: {len(g):,}")
    print("\n--- Speed Safety Score distribution ---")
    print(g["speed_safety_score"].describe(percentiles=[.5,.75,.9,.95]).round(1).to_string())
    print("\n--- Tier counts (by region) ---")
    print(pd.crosstab(g["tier"], g["region"]).reindex(
        ["Priority 1","Priority 2","Monitor","Compliant"]).to_string())
    print("\n--- Priority 1 share by region ---")
    for r in ["THA","MAH"]:
        sub = g[g["region"]==r]
        p1 = (sub["tier"]=="Priority 1").mean()*100
        print(f"  {r}: {p1:.1f}%  (n={len(sub):,})")

    print("\n--- School/market segments: pedestrian fatality probability at P85 (Rosen & Sander 2009) ---")
    sm = g[g["has_school_market"]]
    if len(sm):
        print(f"  {len(sm):,} such segments | fatality prob median {sm['ped_fatality_pct'].median():.1f}% "
              f"mean {sm['ped_fatality_pct'].mean():.1f}% max {sm['ped_fatality_pct'].max():.1f}%")
    print("\n--- Absolute Safe-System severity (cross-country comparable) ---")
    print(pd.crosstab(g["severity"], g["region"]).reindex(
        ["Critical","Serious","Marginal","Compliant"]).to_string())
    print(f"\n--- Possible grade-separated trunk (grade_sep_uncertain, F5 flag for review): {int(g['grade_sep_uncertain'].sum())} segments ---")

    # audit regression: confirm v2 fixed the key defects
    print("\n--- v2 self-check (against the audit) ---")
    p1 = g[g["tier"]=="Priority 1"]
    print(f"  F1 'limit>safe' share in P1 (was 96%): {(p1['limit_excess']>0).mean():.0%}  | safe==30 share of P1 (was 94%): {(p1['safe_threshold']==30).mean():.0%}")
    SCALE_CHK = (p1['oper_excess']>0)
    print(f"  F10 top-tier saturation: old method n_oper==1 was 65%; v2 smooth norm has no hard cap (max score={g['speed_safety_score'].max():.1f})")
    for r in ['MAH','THA']:
        s=g[g.region==r]
        c=s[['speed_safety_score','helmet_norate']].corr().iloc[0,1]
        print(f"  F2 within-{r} corr(score,helmet_norate): {c:+.2f}  (helmet not in score, overlay only)")

    g.to_file("output/speed_safety_score.geojson", driver="GeoJSON")
    print(f"\nWrote output/speed_safety_score.geojson")

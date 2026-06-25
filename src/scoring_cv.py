"""
SpeedTruth, v3 score with CV-derived road-condition thresholds.

Replaces the rule/OSM-proxy safe threshold with the imagery-derived safe speed
(from the automated road-condition classifier) wherever street imagery exists
and the model is confident; falls back to the v2 rule elsewhere. Recomputes the
Speed Safety Score and tiers, and reports the v2 -> v3 change: how many flags
the imagery removes (over-assigned), how many it adds (under-assigned), and how
the danger-magnitude shrinks once thresholds are real.

HONEST: only segments with Mapillary coverage get a CV threshold; the rest keep
the rule-based one. Coverage is reported, not hidden.

Run: python src/scoring_cv.py
"""
import json
import numpy as np, pandas as pd, geopandas as gpd
from scoring import WEIGHTS, _norm_region, severity_band

LABELS = "output/cv_labels_full.json"

def reassign_tiers(df, score_col):
    out = pd.Series("Compliant", index=df.index)
    for _, sub in df.groupby("region"):
        r = df.loc[sub.index, score_col].rank(pct=True)
        t = pd.Series("Compliant", index=sub.index)
        t[r >= 0.50] = "Monitor"; t[r >= 0.75] = "Priority 2"; t[r >= 0.90] = "Priority 1"
        out.loc[sub.index] = t
    return out

def main():
    g = gpd.read_file("output/speed_safety_score.geojson")
    labels = json.load(open(LABELS))
    cv_thr = {}
    for d in labels.values():
        cv = d.get("cv", {})
        iss = cv.get("implied_safe_speed_kmh")
        if cv.get("road_visible") and cv.get("confidence") != "low" and isinstance(iss, (int, float)):
            cv_thr[str(d["seg_id"])] = float(iss)

    g["sid"] = g["seg_id"].astype(str)
    g["cv_threshold"] = g["sid"].map(cv_thr)
    g["has_cv"] = g["cv_threshold"].notna()
    g["safe_threshold_v3"] = g["cv_threshold"].fillna(g["safe_threshold"])

    g["limit_excess"] = (g["speed_limit"] - g["safe_threshold_v3"]).clip(lower=0)
    g["oper_excess"]  = (g["p85"] - g["safe_threshold_v3"]).clip(lower=0)
    g["oper_over"]    = g["p85"] - g["safe_threshold_v3"]
    n_oper, n_limit, n_vru = _norm_region(g, "oper_excess"), _norm_region(g, "limit_excess"), _norm_region(g, "vru_per_km")
    g["score_v3"] = ((WEIGHTS["oper_excess"]*n_oper + WEIGHTS["limit_excess"]*n_limit
                      + WEIGHTS["vru_exposure"]*n_vru) * 100).round(2)
    g["severity_v3"] = g["oper_over"].apply(severity_band)
    g["tier_v3"] = reassign_tiers(g, "score_v3")

    cov = g["has_cv"].mean()
    print(f"CV coverage: {g['has_cv'].sum():,}/{len(g):,} segments ({cov:.0%}) have imagery-derived thresholds")
    cvseg = g[g.has_cv]
    print(f"\n--- Among the {len(cvseg):,} CV-covered segments ---")
    raised = (cvseg.cv_threshold > cvseg.safe_threshold).mean()
    lowered = (cvseg.cv_threshold < cvseg.safe_threshold).mean()
    print(f"  threshold raised by CV (proxy too strict): {raised:.0%} | lowered (proxy too lax): {lowered:.0%}")
    print(f"  mean safe threshold: v2 {cvseg.safe_threshold.mean():.0f} -> v3 {cvseg.safe_threshold_v3.mean():.0f} km/h")

    print("\n--- Tier change v2 -> v3 (whole network; non-CV segments unchanged) ---")
    print(pd.crosstab(g.tier, g.tier_v3).reindex(
        index=["Priority 1","Priority 2","Monitor","Compliant"],
        columns=["Priority 1","Priority 2","Monitor","Compliant"]).to_string())
    demoted = ((g.tier=="Priority 1") & (g.tier_v3!="Priority 1")).sum()
    promoted = ((g.tier!="Priority 1") & (g.tier_v3=="Priority 1")).sum()
    print(f"\n  Priority 1 demoted (over-flag removed): {demoted} | promoted (under-flag caught): {promoted}")
    p1_cv = g[(g.tier=="Priority 1") & g.has_cv]
    if len(p1_cv):
        dem = ((p1_cv.tier_v3!="Priority 1")).mean()
        print(f"  Of CV-covered Priority-1 ({len(p1_cv)}): {dem:.0%} demoted once threshold is imagery-real")

    keep = ["seg_id","region","name","tier","tier_v3","severity","severity_v3","safe_threshold",
            "safe_threshold_v3","has_cv","speed_limit","p85","speed_safety_score","score_v3","geometry"]
    gpd.GeoDataFrame(g[keep], geometry="geometry", crs=4326).to_file("output/speed_safety_score_cv.geojson", driver="GeoJSON")
    summary = {
        "cv_coverage_pct": round(cov, 3), "cv_covered": int(g.has_cv.sum()), "total": len(g),
        "threshold_raised_pct": round(float((cvseg.cv_threshold>cvseg.safe_threshold).mean()), 3),
        "threshold_lowered_pct": round(float((cvseg.cv_threshold<cvseg.safe_threshold).mean()), 3),
        "mean_safe_v2": round(float(cvseg.safe_threshold.mean()), 1), "mean_safe_v3": round(float(cvseg.safe_threshold_v3.mean()), 1),
        "p1_demoted": int(demoted), "p1_promoted": int(promoted),
    }
    json.dump(summary, open("output/scoring_cv_summary.json","w"), ensure_ascii=False, indent=2)
    print("\nWrote output/speed_safety_score_cv.geojson + scoring_cv_summary.json")

if __name__ == "__main__":
    main()

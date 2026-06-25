"""SpeedTruth, SampleSizeTotal sensitivity analysis.

Directly addresses the challenge FAQ's explicit recommendation:
  "Variations in sample density ... can skew the results. We recommend performing a
   sensitivity analysis: check if your findings hold true when you filter for segments
   with a higher SampleSizeTotal."

We test three things, per region (Thailand has high probe coverage, Maharashtra much
lower, per the FAQ), using only DERIVED outputs (no raw probe values are reproduced):

  A. Is the Speed Safety Score an artefact of low sample size? -> correlation of the
     score (and operating-speed excess) with log(sample_size). A strong negative
     correlation would mean high scores come from noisy, low-sample segments.
  B. Are Priority-1 flags concentrated on low-sample (unreliable) segments? -> compare
     the sample-size distribution of Priority-1 vs the rest.
  C. Do the Priority-1 conclusions hold when we keep only high-confidence segments?
     -> restrict to sample_size >= the region median (and >= 75th pct), re-rank tiers
     within that trusted subset, and measure how much the Priority-1 set is retained.
  D. Do the headline findings (Critical severity, school/market exposure) survive the
     same high-confidence filter?

Outputs: console report + output/sensitivity_samplesize.json (aggregate, FDUA-safe)
+ output/sensitivity_samplesize.png (figure for the submission).
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PCT_BREAKS = [(0.50, "Monitor"), (0.75, "Priority 2"), (0.90, "Priority 1")]  # within-region, low->high

def rerank(sub):
    """Re-assign within-region tier by score percentile on a (filtered) subset."""
    r = sub["speed_safety_score"].rank(pct=True)
    tier = pd.Series("Compliant", index=sub.index)
    for q, name in PCT_BREAKS:
        tier[r >= q] = name
    return tier

def main():
    g = gpd.read_file("output/speed_safety_score.geojson")
    g = g.reset_index(drop=True)
    g["ss"] = g["sample_size"].astype(float)
    g["logss"] = np.log10(g["ss"].clip(lower=1))
    report = {}

    print("=" * 74)
    print("SpeedTruth, SampleSizeTotal sensitivity analysis (FAQ-recommended)")
    print("=" * 74)

    for region in ["THA", "MAH"]:
        s = g[g["region"] == region].copy()
        med = s["ss"].median()
        q75 = s["ss"].quantile(0.75)
        rr = {}

        # --- A. score vs sample size (is a high score a low-sample artefact?) ---
        cor_score = s["speed_safety_score"].corr(s["logss"])
        cor_oper  = s["oper_excess"].corr(s["logss"])
        rr["corr_score_logsample"] = round(float(cor_score), 3)
        rr["corr_operexcess_logsample"] = round(float(cor_oper), 3)

        # --- B. are Priority-1 flags on low-sample segments? ---
        p1 = s[s["tier"] == "Priority 1"]
        rest = s[s["tier"] != "Priority 1"]
        rr["p1_median_sample"] = int(p1["ss"].median())
        rr["rest_median_sample"] = int(rest["ss"].median())
        rr["p1_share_below_region_median"] = round(float((p1["ss"] < med).mean()), 3)

        # --- C. Priority-1 retention under high-confidence filters ---
        orig_p1 = set(s.index[s["tier"] == "Priority 1"])
        for tag, thr in [("median", med), ("p75", q75)]:
            H = s[s["ss"] >= thr].copy()
            H_tier = rerank(H)
            new_p1 = set(H.index[H_tier == "Priority 1"])
            orig_in_H = orig_p1 & set(H.index)
            inter = orig_in_H & new_p1
            union = orig_in_H | new_p1
            retention = len(inter) / len(orig_in_H) if orig_in_H else float("nan")
            jacc = len(inter) / len(union) if union else float("nan")
            rr[f"retain_{tag}"] = {
                "threshold_sample": int(thr),
                "orig_p1_total": len(orig_p1),
                "orig_p1_survive_filter": len(orig_in_H),
                "orig_p1_retained_as_p1": len(inter),
                "retention_of_surviving": round(retention, 3),
                "jaccard": round(jacc, 3),
            }

        # --- D. headline-finding robustness on the high-confidence (>= median) subset ---
        H = s[s["ss"] >= med]
        def crit_share(d): return float((d["severity"] == "Critical").mean())
        rr["critical_share_full"] = round(crit_share(s), 3)
        rr["critical_share_highsample"] = round(crit_share(H), 3)
        sm_full = s[s["has_school_market"]]
        sm_hi = H[H["has_school_market"]]
        rr["schoolmkt_p85median_full"] = round(float(sm_full["p85"].median()), 1) if len(sm_full) else None
        rr["schoolmkt_p85median_highsample"] = round(float(sm_hi["p85"].median()), 1) if len(sm_hi) else None

        report[region] = rr

        print(f"\n### {region}  (region median sample = {int(med):,}; n = {len(s):,})")
        print(f"  A. corr(score, log sample)      = {cor_score:+.3f}   "
              f"corr(oper-excess, log sample) = {cor_oper:+.3f}")
        print(f"     -> {'NOT a low-sample artefact' if cor_score > -0.15 else 'CHECK: score leans on low sample'}")
        print(f"  B. Priority-1 median sample     = {int(p1['ss'].median()):,}   "
              f"vs rest = {int(rest['ss'].median()):,}")
        print(f"     Priority-1 share below region median sample = {(p1['ss'] < med).mean():.0%}")
        for tag in ["median", "p75"]:
            d = rr[f"retain_{tag}"]
            print(f"  C. keep sample >= {tag:6} ({d['threshold_sample']:>10,}): "
                  f"{d['orig_p1_survive_filter']}/{d['orig_p1_total']} P1 survive filter, "
                  f"{d['retention_of_surviving']:.0%} stay P1 (Jaccard {d['jaccard']:.2f})")
        print(f"  D. Critical share: full {rr['critical_share_full']:.1%} -> "
              f"high-sample {rr['critical_share_highsample']:.1%}  |  "
              f"school/market median P85: full {rr['schoolmkt_p85median_full']} -> "
              f"high-sample {rr['schoolmkt_p85median_highsample']}")

    json.dump(report, open("output/sensitivity_samplesize.json", "w"),
              ensure_ascii=False, indent=2)
    print("\nWrote output/sensitivity_samplesize.json")

    # --- figure ---
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, region, color in [(axes[0], "THA", "#0a7d5a"), (axes[0], "MAH", "#c0144c")]:
        s = g[g["region"] == region]
        ax.scatter(s["logss"], s["speed_safety_score"], s=3, alpha=0.15, color=color, label=region)
    axes[0].set_xlabel("log10(SampleSizeTotal)")
    axes[0].set_ylabel("Speed Safety Score")
    axes[0].set_title("A. Score vs sample size\n(no strong negative trend = not a low-sample artefact)")
    axes[0].legend(markerscale=4, fontsize=8)

    tags = ["median", "p75"]
    x = np.arange(len(tags)); w = 0.35
    for i, region in enumerate(["THA", "MAH"]):
        vals = [report[region][f"retain_{t}"]["retention_of_surviving"] * 100 for t in tags]
        axes[1].bar(x + i * w, vals, w, label=region,
                    color="#0a7d5a" if region == "THA" else "#c0144c")
        for xi, v in zip(x + i * w, vals):
            axes[1].text(xi, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
    axes[1].set_xticks(x + w / 2); axes[1].set_xticklabels(["keep >= median", "keep >= 75th pct"])
    axes[1].set_ylim(0, 105)
    axes[1].set_ylabel("% of surviving Priority-1 retained")
    axes[1].set_title("C. Priority-1 stability under\nhigh-confidence (high-sample) filter")
    axes[1].legend(fontsize=8)
    plt.tight_layout()
    plt.savefig("output/sensitivity_samplesize.png", dpi=130)
    print("Wrote output/sensitivity_samplesize.png")

if __name__ == "__main__":
    main()

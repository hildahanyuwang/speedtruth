"""SpeedTruth, evaluation (no crash ground truth available).

Validates the Speed Safety Score's construct via converging checks, honestly:
  1. Internal consistency, tiers should rise monotonically with Safe System excess & VRU exposure.
  2. Convergent validity, score should correlate with an independent in-data risk signal
     (PercentOverLimit), which is NOT a scoring input.
  3. Sensitivity, perturb factor weights; report stability of the Priority 1 set (Jaccard).
  4. Coverage honesty, report what was excluded.
See METHODOLOGY.md §5. We do NOT claim to predict crashes.
"""
import numpy as np
import pandas as pd
from scoring import build, compute_score, WEIGHTS

def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a | b) else 1.0

def internal_consistency(g):
    print("\n[1] Internal consistency, mean factor by tier (expect monotonic ↑ toward Priority 1)")
    order = ["Compliant", "Monitor", "Priority 2", "Priority 1"]
    cols = ["oper_excess", "limit_excess", "vru_per_km", "dev_gap", "speed_safety_score"]
    t = g.groupby("tier")[cols].mean().reindex(order).round(2)
    print(t.to_string())

def convergent_validity(g):
    print("\n[2] Convergent validity, Spearman corr with PercentOverLimit")
    # PercentOverLimit is in the data but is NOT a scoring input -> a genuine independent check.
    # (helmet SPI is deliberately excluded here: it IS a scoring input, so correlating with it
    #  would be circular, not independent validation.)
    sub = g[["speed_safety_score", "pct_over"]].dropna()
    r = sub["speed_safety_score"].corr(sub["pct_over"], method="spearman")
    print(f"    PercentOverLimit (independent of scoring)   rho = {r:+.3f}  (n={len(sub):,})")
    # report within-region too, since absolute scores differ by country speed-limit regime
    for reg in ["THA", "MAH"]:
        s = g[g["region"] == reg][["speed_safety_score", "pct_over"]].dropna()
        if len(s) > 10:
            print(f"      within {reg}: rho = {s['speed_safety_score'].corr(s['pct_over'], method='spearman'):+.3f} (n={len(s):,})")

def sensitivity(g):
    print("\n[3] Sensitivity, Priority 1 set stability under weight perturbation (Jaccard vs baseline)")
    base = compute_score(g)
    base_p1 = base.index[base["tier"] == "Priority 1"]
    print(f"    baseline Priority 1 count: {len(base_p1):,}")
    rng_keys = list(WEIGHTS.keys())
    for k in rng_keys:
        for sign, tag in [(1.3, "+30%"), (0.7, "-30%")]:
            w = dict(WEIGHTS); w[k] = WEIGHTS[k] * sign
            s = sum(w.values()); w = {kk: vv / s for kk, vv in w.items()}  # renormalise
            alt = compute_score(g, w)
            p1 = alt.index[alt["tier"] == "Priority 1"]
            print(f"    {k:<14} {tag}:  Jaccard {jaccard(base_p1, p1):.3f}  (n={len(p1):,})")

def coverage(g_scored, n_valid):
    print("\n[4] Coverage honesty")
    print(f"    Valid segments (with probe data): {n_valid:,}")
    print(f"    Scored: {len(g_scored):,}  |  excluded (zero/invalid limit or P85): {n_valid - len(g_scored):,}")
    print("    VRU exposure is a lower bound (OSM crowdsourced).")

if __name__ == "__main__":
    from harmonize import load_all
    n_valid = len(load_all())          # all AnalysisStatus=Valid, before dropping na limit/P85
    g = build()
    internal_consistency(g)
    convergent_validity(g)
    sensitivity(g)
    coverage(g, n_valid)
    print("\nNote: no crash ground truth in provided data, see METHODOLOGY.md §5.")

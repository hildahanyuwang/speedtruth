"""
Robustness: does our Priority ranking depend on the UNVALIDATED posted-limit field?

The data guide flags SpeedLimit as a commercial probe data estimate, "not validated". In this
dataset the limits also look largely DEFAULTED by class (THA: 89% are 80 or 90;
MAH: 67% are exactly 55, identical median across primary/secondary/trunk). A fair
reviewer will ask whether "the limit is unsafe" is a real finding or a default-value
artifact.

Test: recompute the Speed Safety Score with the limit-dependent factors removed and
check whether the within-region top-decile (Priority 1) set is stable. The score's
hardest signal, oper_excess = P85 (MEASURED operating speed) - Safe System safe
speed, does not use the posted limit at all.
"""
import numpy as np, pandas as pd, geopandas as gpd

SCALE = 40.0
def c01(x): return np.clip(x, 0, 1)

W = {"oper_excess":.35, "limit_excess":.25, "vru_exposure":.15, "dev_gap":.15, "func_mismatch":.10}

def score(df, w, vru_hi):
    n_oper  = c01(df["oper_excess"]/SCALE)
    n_limit = c01(df["limit_excess"]/SCALE)
    n_func  = c01(df["func_mismatch"].abs()/SCALE)
    n_dev   = c01(df["dev_gap"]/SCALE)
    n_vru   = c01(df["vru_per_km"]/(vru_hi if vru_hi<1e9 else 1))
    base = (w.get("oper_excess",0)*n_oper + w.get("limit_excess",0)*n_limit
            + w.get("vru_exposure",0)*n_vru + w.get("dev_gap",0)*n_dev
            + w.get("func_mismatch",0)*n_func)
    mult = 1 + 0.6*df["helmet_norate"].fillna(0)
    return c01(base*mult)*100

def renorm(w):
    s = sum(w.values()); return {k: v/s for k, v in w.items()}

def top_decile(df, s):
    """within-region top 10% (matches scoring.assign_tiers within_region)."""
    idx = set()
    df = df.assign(_s=s)
    for _, sub in df.groupby("region"):
        thr = sub["_s"].rank(pct=True)
        idx |= set(sub.index[thr >= 0.90])
    return idx

def jac(a, b): return len(a & b)/len(a | b) if (a | b) else 1.0

def main():
    g = gpd.read_file("output/speed_safety_score.geojson")
    vru_hi = float(g.loc[g["vru_per_km"]>0, "vru_per_km"].quantile(0.75))

    base = score(g, W, vru_hi)
    P0 = top_decile(g, base)

    variants = {
        "drop limit factor (redistribute 0.25)":
            renorm({"oper_excess":.35, "vru_exposure":.15, "dev_gap":.15, "func_mismatch":.10}),
        "drop ALL limit-derived factors (oper+VRU only, fully limit-independent)":
            renorm({"oper_excess":.35, "vru_exposure":.15}),
    }
    print("=== Posted-limit dependence of the Priority-1 (top-decile) set ===")
    print(f"Baseline Priority-1 segments: {len(P0)}\n")
    for name, w in variants.items():
        Pv = top_decile(g, score(g, w, vru_hi))
        print(f"- {name}")
        print(f"    weights: { {k: round(v,3) for k,v in w.items()} }")
        print(f"    Jaccard with baseline Priority-1: {jac(P0, Pv):.3f}  "
              f"(retained {len(P0 & Pv)}/{len(P0)})\n")

    # the hard, limit-free fact
    p1 = g[g["tier"]=="Priority 1"]
    print("=== Why it is robust: the flag is driven by MEASURED speed, not the limit ===")
    print(f"Priority-1 with P85 (measured) > Safe System safe speed : "
          f"{(p1['p85']>p1['safe_threshold']).mean()*100:.0f}%")
    print(f"Priority-1 flagged ONLY by the posted limit (P85 within safe speed): "
          f"{((p1['speed_limit']>p1['safe_threshold'])&(p1['p85']<=p1['safe_threshold'])).mean()*100:.0f}%")

    print("\n=== Honest characterisation of the posted-limit field (it is largely a default) ===")
    for reg in ["THA","MAH"]:
        d = g[g.region==reg]
        top2 = d["speed_limit"].value_counts(normalize=True).head(2)
        share = top2.sum()*100
        vals = ", ".join(f"{int(v)}({s*100:.0f}%)" for v, s in top2.items())
        print(f"  {reg}: top-2 limit values = {vals}  -> {share:.0f}% of segments")

if __name__ == "__main__":
    main()

"""SpeedTruth, external outcome convergence vs Thailand provincial road-death rates.

The challenge provides no crash data, the central validation gap. As a first external
outcome anchor we test whether the Speed Safety Score, aggregated to province level,
ranks consistently with *independently published* provincial road-traffic-death rates.

Death-rate data (2022, deaths per 100,000 population) are from ThaiRSC as reported in
Ratovoson et al., "Spatial association and modeling of road traffic deaths in Thailand,
2022", Population Health Metrics (2026), DOI 10.1186/s12963-026-00462-9. Only the five
highest and five lowest provinces are publicly reported, so this is a deliberately
small-n (10-province) EXTREMES test, not a full 77-province regression.

Method: assign each scored Thailand segment to its province (gpkg ProvinceID ->
Province boundary NAME_ENG1), aggregate SpeedTruth severity per province, and compute
(a) Spearman rank correlation between the published death rate and our severity across
the 10 provinces, and (b) the high-5 vs low-5 contrast.

HONEST FRAMING: death rate per population is an ecological outcome shaped by exposure
and urbanisation, so a positive result is *convergent* (not causal) validity. We use
only DERIVED, province-aggregated outputs (no raw per-segment probe values), FDUA-safe.
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import warnings
warnings.filterwarnings("ignore")
from scipy.stats import spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GPKG = "Archive/Road_Safety_Performance_Indicators__Thailand_(Feature).gpkg"

# Published 2022 road-traffic-death rate (per 100,000 pop), ThaiRSC via Pop Health Metrics 2026.
DEATH_RATE = {
    "RAYONG": 48.58, "SARABURI": 43.17, "PHRA NAKHON SI AYUTTHAYA": 39.85,
    "TRAT": 37.66, "CHON BURI": 37.13,                                   # 5 highest
    "YALA": 10.88, "PATTANI": 11.10, "NAKHON PHANOM": 12.55,
    "NARATHIWAT": 12.84, "KALASIN": 13.74,                               # 5 lowest
}
HIGH = ["RAYONG", "SARABURI", "PHRA NAKHON SI AYUTTHAYA", "TRAT", "CHON BURI"]
LOW  = ["YALA", "PATTANI", "NAKHON PHANOM", "NARATHIWAT", "KALASIN"]

def main():
    # join segments -> province
    m = gpd.read_file(GPKG, layer="ADB_Results_D4")[["OvertureID", "ProvinceID"]]
    m["OvertureID"] = m["OvertureID"].astype(str)
    m["ProvinceID"] = m["ProvinceID"].astype(str)
    b = gpd.read_file(GPKG, layer="Thailand_Province_Boundaries")[["ADMIN_ID1", "NAME_ENG1"]]
    b["ADMIN_ID1"] = b["ADMIN_ID1"].astype(str)

    g = gpd.read_file("output/speed_safety_score.geojson")
    g = g[g["region"] == "THA"].copy()
    g["seg_id"] = g["seg_id"].astype(str)
    g = g.merge(m, left_on="seg_id", right_on="OvertureID", how="left")
    g = g.merge(b, left_on="ProvinceID", right_on="ADMIN_ID1", how="left")

    # aggregate SpeedTruth severity per province
    def agg(d):
        return pd.Series({
            "n_seg": len(d),
            "pct_critical": (d["severity"] == "Critical").mean() * 100,
            "pct_priority1": (d["tier"] == "Priority 1").mean() * 100,
            "mean_score": d["speed_safety_score"].mean(),
            "mean_oper_over": d["oper_over"].mean(),
        })
    prov = g.groupby("NAME_ENG1").apply(agg)

    rows = []
    for name, rate in DEATH_RATE.items():
        if name in prov.index:
            r = prov.loc[name]
            rows.append({"province": name, "death_rate_2022": rate, "group": "high" if name in HIGH else "low",
                         "n_seg": int(r["n_seg"]), "pct_critical": round(r["pct_critical"], 1),
                         "pct_priority1": round(r["pct_priority1"], 1),
                         "mean_score": round(r["mean_score"], 1),
                         "mean_oper_over": round(r["mean_oper_over"], 1)})
    df = pd.DataFrame(rows).sort_values("death_rate_2022", ascending=False)

    print("=" * 78)
    print("SpeedTruth, external outcome convergence vs Thailand provincial death rates")
    print("(2022, deaths/100k, ThaiRSC via Population Health Metrics 2026; 10-province extremes)")
    print("=" * 78)
    print(df.to_string(index=False))

    out = {"note": "10-province extremes test; death rates 2022 per 100k (ThaiRSC via Pop Health Metrics 2026)",
           "provinces": rows, "correlations": {}, "group_contrast": {}}
    print("\n--- Spearman rank correlation (death rate vs SpeedTruth severity, n=10) ---")
    for metric in ["pct_critical", "pct_priority1", "mean_score", "mean_oper_over"]:
        rho, p = spearmanr(df["death_rate_2022"], df[metric])
        out["correlations"][metric] = {"spearman_rho": round(float(rho), 3), "p_value": round(float(p), 4)}
        print(f"  death_rate vs {metric:16}: rho = {rho:+.3f}  (p = {p:.4f})")

    print("\n--- High-5 vs Low-5 contrast (mean of province aggregates) ---")
    for metric in ["pct_critical", "pct_priority1", "mean_score", "mean_oper_over"]:
        hi = df[df["group"] == "high"][metric].mean()
        lo = df[df["group"] == "low"][metric].mean()
        out["group_contrast"][metric] = {"high5_mean": round(float(hi), 1), "low5_mean": round(float(lo), 1),
                                          "ratio": round(float(hi / lo), 2) if lo else None}
        print(f"  {metric:16}: high-5 = {hi:6.1f}  vs  low-5 = {lo:6.1f}   (x{hi/lo:.2f})" if lo else
              f"  {metric:16}: high-5 = {hi:6.1f}  vs  low-5 = {lo:6.1f}")

    json.dump(out, open("output/validate_thairsc.json", "w"), ensure_ascii=False, indent=2)
    print("\nWrote output/validate_thairsc.json")

    # figure: death rate vs % Critical, coloured by group
    fig, ax = plt.subplots(figsize=(7, 5))
    for grp, col in [("high", "#c0144c"), ("low", "#0a7d5a")]:
        d = df[df["group"] == grp]
        ax.scatter(d["death_rate_2022"], d["pct_critical"], s=70, color=col,
                   label=f"{grp}-death provinces", zorder=3)
        for _, r in d.iterrows():
            ax.annotate(r["province"].title(), (r["death_rate_2022"], r["pct_critical"]),
                        fontsize=7, xytext=(4, 3), textcoords="offset points")
    rho, p = spearmanr(df["death_rate_2022"], df["pct_critical"])
    ax.set_xlabel("Published road-traffic-death rate, 2022 (per 100,000 pop)")
    ax.set_ylabel("SpeedTruth: % of province's segments rated Critical")
    ax.set_title(f"External outcome convergence (Thailand, 10-province extremes)\n"
                 f"Spearman rho = {rho:+.2f} (p = {p:.3f})")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig("output/validate_thairsc.png", dpi=130)
    print("Wrote output/validate_thairsc.png")

if __name__ == "__main__":
    main()

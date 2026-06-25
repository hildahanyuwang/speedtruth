"""
External validation (Maharashtra): do the districts SpeedTruth flags as high-risk
also carry more officially-designated accident BLACK SPOTS?

Ground-truth source: Maharashtra Highway Traffic Police, "Black Spots 2021-2023"
(779 black spots aggregated by police unit; district-level COUNTS only, no coords).
Downloaded PDF parsed to the BLACKSPOT dict below.

This is an ECOLOGICAL (district-level) cross-check, NOT a per-segment proof:
  - black-spot counts are absolute (a bigger road network -> more black spots),
  - our scored segments are the commercial probe data-Valid subset only (uneven district coverage).
So we lead with Spearman RANK correlations and report exposure-normalized variants,
and we flag the structural confounds honestly. The claim is convergence of an
independent official source with our risk ranking, at the resolution the data allows.
"""
import geopandas as gpd
import pandas as pd
import numpy as np
from scipy.stats import spearmanr, pearsonr

SP = ("C:/Users/DELL/AppData/Local/Temp/claude/"
      "D--BaiduNetdiskDownload-ADB/500caf04-5df1-44ba-a73a-f756d26de23f/scratchpad/")

# --- Official black spots per police unit (Maharashtra Police 2021-2023, TOTAL col) ---
# Mapped to geoBoundaries ADM2 district spellings; City+Rural+commissionerates summed.
# Source rows verified from parsed PDF (scratchpad/bs_dump.txt).
BLACKSPOT = {
    "Amravati": 0 + 15,                 # Amravati City 0 + Amravati Rural 15
    "Aurangabad": 47 + 36,              # Ch. Sambhajinagar City + Rural (renamed)
    "Nagpur": 5 + 18,                   # Nagpur City + Rural
    "Nashik": 21 + 75,                  # Nashik City + Rural
    "Pune": 12 + 24 + 6,               # Pimpari-Chichwad + Pune City + Pune Rural
    "Solapur": 18 + 13,                # Solapur City + Rural
    "Thane": 21 + 9 + 30,              # Thane City + Rural + Navi Mumbai (in Thane dist.)
    "Palghar": 14 + 13,                # Palghar + M-B-V-V (Vasai-Virar/Mira-Bhayandar)
    "Ahmadnagar": 43,
    "Akola": 0,
    "Bid": 28,                          # "Beed"
    "Bhandara": 6,
    "Buldana": 0,                       # "Buldhana"
    "Chandrapur": 11,
    "Osmanabad": 0,                     # "Dharashiv" (renamed)
    "Dhule": 60,
    "Gadchiroli": 0,
    "Gondiya": 16,                      # "Gondia"
    "Hingoli": 28,
    "Jalgaon": 2,
    "Jalna": 15,
    "Kolhapur": 46,
    "Latur": 0,
    "Nanded": 23,
    "Nandurbar": 10,
    "Parbhani": 6,
    "Raigarh": 26,                      # "Raigad"
    "Ratnagiri": 3,
    "Sangli": 12,
    "Satara": 8,
    "Sindhudurg": 1,
    "Wardha": 20,
    "Washim": 1,
    "Yavatmal": 7,
    # Mumbai City 30 -> Mumbai/Mumbai Suburban: dense urban, ~no highway probe segments.
    # Treated as a known outlier (excluded from the core fit, reported separately).
    "Mumbai Suburban": 30,
}
OUTLIERS = {"Mumbai Suburban", "North Goa"}   # urban / cross-border edge, not comparable

def main():
    seg = gpd.read_file("output/speed_safety_score.geojson")
    mah = seg[seg["region"] == "MAH"].copy()
    mah["geometry"] = mah.geometry.representative_point()
    if mah.crs is None:
        mah = mah.set_crs(4326)
    mah = mah.to_crs(4326)

    dist = gpd.read_file(SP + "ind_adm2.geojson")[["shapeName", "geometry"]].to_crs(4326)
    j = gpd.sjoin(mah, dist, how="left", predicate="within")
    j = j.rename(columns={"shapeName": "district"})

    g = j.groupby("district")
    agg = pd.DataFrame({
        "n_scored":  g.size(),
        "n_p1":      g["tier"].apply(lambda s: (s == "Priority 1").sum()),
        "mean_score": g["speed_safety_score"].mean(),
        "covered_km": g["length_m"].sum() / 1000.0,
    }).reset_index()
    agg["frac_p1"] = agg["n_p1"] / agg["n_scored"]
    agg["black_spots"] = agg["district"].map(BLACKSPOT)

    # districts with both our data and a black-spot figure
    m = agg.dropna(subset=["black_spots"]).copy()
    core = m[~m["district"].isin(OUTLIERS)].copy()

    # exposure-normalised intensities
    core["bs_per_100km"] = core["black_spots"] / core["covered_km"] * 100

    print(f"Districts matched (both sources): {len(m)}  | core (excl. outliers): {len(core)}")
    print("\n=== Per-district table (core, sorted by official black spots) ===")
    show = core.sort_values("black_spots", ascending=False)[
        ["district", "black_spots", "n_scored", "n_p1", "frac_p1", "mean_score", "bs_per_100km"]
    ]
    print(show.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    def report(label, a, b, d):
        rho, p = spearmanr(d[a], d[b])
        r, _ = pearsonr(d[a], d[b])
        print(f"  {label:55s} Spearman rho={rho:+.3f} (p={p:.3f})  Pearson r={r:+.3f}")

    print("\n=== Correlations: our risk vs official black spots (core districts) ===")
    print("[Absolute counts, confounded by district network size, shown for transparency]")
    report("black_spots vs n_priority1", "black_spots", "n_p1", core)
    report("black_spots vs n_scored (exposure proxy)", "black_spots", "n_scored", core)
    print("[Exposure-normalised, the fair test]")
    report("bs_per_100km vs mean_score", "bs_per_100km", "mean_score", core)
    report("bs_per_100km vs frac_priority1", "bs_per_100km", "frac_p1", core)

    # Partial: does our flagging track black spots BEYOND just having more road?
    # rank-correlate residuals of n_p1 and black_spots after removing n_scored.
    from numpy.polynomial import polynomial as P
    def resid_rank(y, x):
        rx = pd.Series(x).rank(); ry = pd.Series(y).rank()
        b = np.polyfit(rx, ry, 1)
        return ry - (b[0]*rx + b[1])
    r_p1 = resid_rank(core["n_p1"].values, core["n_scored"].values)
    r_bs = resid_rank(core["black_spots"].values, core["n_scored"].values)
    rho, p = spearmanr(r_p1, r_bs)
    print("[Partial, n_priority1 vs black_spots, controlling for n_scored]")
    print(f"  partial rank rho={rho:+.3f} (p={p:.3f})")

    core.sort_values("black_spots", ascending=False).to_csv(
        "output/validation_maharashtra.csv", index=False)
    print("\nSaved -> output/validation_maharashtra.csv")

if __name__ == "__main__":
    main()

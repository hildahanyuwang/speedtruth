"""SpeedTruth, WorldPop population-density cross-check of VRU exposure.

The challenge FAQ explicitly invites supplementary open data and lists WorldPop. Our
VRU-exposure factor is built from OSM points of interest (schools/markets), which are a
known *lower bound* (crowd-sourced, sparse). Here we cross-check and strengthen it with
WorldPop 2020 1km population density (open data, CC BY 4.0), sampled at each segment's
midpoint (Thailand and India rasters, EPSG:4326).

Three questions:
  1. Convergent validity, do segments our OSM layer flags as high-exposure (school/market
     present, higher vru_per_km) also sit in higher-population areas? If yes, the OSM
     signal is real, not noise.
  2. Coverage gain, how many segments have NO OSM VRU point at all yet sit in the top
     population quartile, i.e. exposure the POI layer structurally misses?
  3. Corroboration, do Priority-1 segments sit in above-median population?

Outputs aggregate, derived metrics only (no raw probe values), FDUA-safe. The WorldPop
rasters are open data downloaded at runtime (see README); they are not redistributed here.
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import warnings
warnings.filterwarnings("ignore")
from scipy.stats import spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RASTER = {"THA": "worldpop/tha_pd_2020_1km.tif", "MAH": "worldpop/ind_pd_2020_1km.tif"}

def sample_pop(g):
    g = g.copy()
    mid = g.geometry.interpolate(0.5, normalized=True)
    g["lon"], g["lat"] = mid.x.values, mid.y.values
    g["pop_density"] = np.nan
    for region, path in RASTER.items():
        sub = g[g["region"] == region]
        if not len(sub):
            continue
        with rasterio.open(path) as r:
            vals = np.array([v[0] for v in r.sample(list(zip(sub["lon"], sub["lat"])))], dtype=float)
        vals[vals < 0] = np.nan          # nodata -99999 and any negatives
        g.loc[sub.index, "pop_density"] = vals
    return g

def main():
    g = gpd.read_file("output/speed_safety_score.geojson")
    g = sample_pop(g)
    cov = g["pop_density"].notna().mean()
    print("=" * 76)
    print("SpeedTruth, WorldPop population-density cross-check of VRU exposure")
    print("=" * 76)
    print(f"Sampled population density for {cov:.1%} of segments (WorldPop 2020 1km)\n")

    report = {}
    for region in ["THA", "MAH"]:
        s = g[(g["region"] == region) & g["pop_density"].notna()].copy()
        med_pop = s["pop_density"].median()
        rr = {}

        # 1. convergent validity
        rho_vru, _ = spearmanr(s["pop_density"], s["vru_per_km"])
        sm = s[s["has_school_market"]]; nosm = s[~s["has_school_market"]]
        rr["spearman_pop_vs_vru_per_km"] = round(float(rho_vru), 3)
        rr["pop_median_schoolmarket"] = round(float(sm["pop_density"].median()), 1) if len(sm) else None
        rr["pop_median_no_schoolmarket"] = round(float(nosm["pop_density"].median()), 1) if len(nosm) else None

        # 2. coverage gain: no OSM VRU point but top-quartile population
        q75 = s["pop_density"].quantile(0.75)
        no_osm = s[s["vru_weight"] == 0]
        missed = no_osm[no_osm["pop_density"] >= q75]
        rr["pct_segments_no_osm_vru"] = round(float((s["vru_weight"] == 0).mean()) * 100, 1)
        rr["n_no_osm_but_high_pop"] = int(len(missed))
        rr["pop_q75"] = round(float(q75), 1)

        # 3. Priority-1 corroboration
        p1 = s[s["tier"] == "Priority 1"]
        rr["p1_share_above_median_pop"] = round(float((p1["pop_density"] >= med_pop).mean()), 3) if len(p1) else None

        report[region] = rr
        print(f"### {region}  (median pop density = {med_pop:,.0f}/km^2; n sampled = {len(s):,})")
        print(f"  1. Convergent validity:")
        print(f"     Spearman(pop density, vru_per_km)      = {rho_vru:+.3f}")
        print(f"     median pop density, school/market present = {rr['pop_median_schoolmarket']:,} "
              f"vs absent = {rr['pop_median_no_schoolmarket']:,}")
        print(f"  2. Coverage gain (OSM POI misses):")
        print(f"     {rr['pct_segments_no_osm_vru']}% of segments have NO OSM VRU point; of those, "
              f"{rr['n_no_osm_but_high_pop']:,} sit in the top population quartile (>= {q75:,.0f}/km^2)")
        print(f"     -> real pedestrian exposure the POI layer structurally misses")
        print(f"  3. Priority-1 corroboration: {rr['p1_share_above_median_pop']:.0%} of Priority-1 "
              f"segments sit in above-median population\n")

    json.dump(report, open("output/worldpop_exposure.json", "w"), ensure_ascii=False, indent=2)
    print("Wrote output/worldpop_exposure.json")

    # figure: population density by school/market presence (log scale), per region
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    for ax, region in zip(axes, ["THA", "MAH"]):
        s = g[(g["region"] == region) & g["pop_density"].notna() & (g["pop_density"] > 0)]
        data = [np.log10(s[~s["has_school_market"]]["pop_density"].clip(lower=1)),
                np.log10(s[s["has_school_market"]]["pop_density"].clip(lower=1))]
        ax.boxplot(data, labels=["no school/\nmarket", "school/\nmarket"], showfliers=False)
        ax.set_title(f"{region}: population density by OSM exposure")
        ax.set_ylabel("log10(people / km^2)")
    plt.suptitle("WorldPop cross-check: OSM-flagged exposure segments sit in denser population",
                 fontsize=10)
    plt.tight_layout()
    plt.savefig("output/worldpop_exposure.png", dpi=130)
    print("Wrote output/worldpop_exposure.png")

if __name__ == "__main__":
    main()

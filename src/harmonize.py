"""SpeedTruth, two-country data harmonisation + cleaning + factors 1-2 scoring.

Outputs a unified-schema GeoDataFrame, keeping only segments with AnalysisStatus=Valid
and valid speed data. The two countries use different field names, mapped here to a
unified schema.
"""
import geopandas as gpd
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# gpkg data sources: (path, main road-network layer, boundary layer). gpkg is already
# projected to each country's UTM and includes the boundary layer the geojson lacks.
GPKG = {
    "THA": ("Archive/Road_Safety_Performance_Indicators__Thailand_(Feature).gpkg",
            "ADB_Results_D4", "Thailand_Province_Boundaries"),
    "MAH": ("Archive/Road_Safety_Performance_Indicators__Maharashtra_(Feature).gpkg",
            "OvertureNetwork_wResults", "Boundaries_4helmet"),
}
HELMET = "Archive/Road_Safety_Performance_Indicators_(Helmet_Wearing_results)_(adb_dashboard_data_v02).xlsx"
REGION_NAME = {"THA": "Thailand", "MAH": "Maharashtra"}
UTM = {"THA": 32647, "MAH": 32643}   # Thailand UTM47N, Maharashtra UTM43N (gpkg native projection)

# field map: unified name -> (Thailand field, Maharashtra field)
FIELD_MAP = {
    "seg_id":       ("OvertureID", "DISSOLVE_ID"),
    "name":         ("english_ro", "names_primary"),
    "road_class":   ("RoadClass", "RoadClass"),
    "land_use":     ("LandUse", "LandUse"),
    "speed_limit":  ("SpeedLimit", "SpeedLimit"),
    "p85":          ("F85thPercentileSpeed", "F85thPercentileSpeed"),
    "median_speed": ("MedianSpeed", "MedianSpeed"),
    "pct_over":     ("PercentOverLimit", "PercentOverLimit"),
    "sample_size":  ("SampleSizeTotal", "Sample_Size_Total"),
    "traffic_pct":  ("RankedPercentile", "RankedPercentile"),
    "street_link":  ("StreetImageLink", "StreetImageLink"),  # "lon,lat,lon,lat" start/end, for street-view checks
    # length_m is not taken from a field, computed directly from UTM geometry (see load_region)
}

def _num(s):
    return pd.to_numeric(s, errors="coerce")

def load_region(region):
    path, layer, _ = GPKG[region]
    gdf = gpd.read_file(path, layer=layer)
    gdf = gdf[gdf["AnalysisStatus"] == "Valid"].copy()
    length_m = gdf.geometry.length.values       # gpkg is UTM, length unit = metres
    gdf = gdf.to_crs(4326)                       # store uniformly as lon/lat
    out = gpd.GeoDataFrame(geometry=gdf.geometry.values, crs=4326)
    col = 0 if region == "THA" else 1
    for uni, pair in FIELD_MAP.items():
        out[uni] = gdf[pair[col]].values
    out["length_m"] = length_m
    out["region"] = region

    # --- cleaning ---
    for c in ["speed_limit", "p85", "median_speed", "pct_over",
              "sample_size", "traffic_pct", "length_m"]:
        out[c] = _num(out[c])
    # speed field 0 treated as missing (Thailand codes missing as 0)
    out.loc[out["p85"] == 0, "p85"] = np.nan
    out.loc[out["speed_limit"] == 0, "speed_limit"] = np.nan
    # standardise the traffic percentile to 0-100 (Maharashtra raw is 0-1)
    if region == "MAH":
        out["traffic_pct"] = out["traffic_pct"] * 100.0
    # standardise urban/rural to uppercase
    out["land_use"] = out["land_use"].astype(str).str.upper()
    return out

def load_helmet():
    """Helmet-wearing SPI: by region x urban/rural, taking 'All Riders'/Year='All'. Returns {(region,land_use): spi}."""
    h = pd.read_excel(HELMET)
    h = h[(h["User"] == "All Riders") & (h["Year"].astype(str) == "All")]
    out = {}
    for reg, name in REGION_NAME.items():
        sub = h[h["Location"] == name]
        for lu_src, lu_dst in [("Urban", "URBAN"), ("Rural", "RURAL")]:
            row = sub[sub["LandUse"] == lu_src]
            if len(row):
                out[(reg, lu_dst)] = float(row["SPI"].iloc[0])
        comb = sub[sub["LandUse"] == "Combined"]
        if len(comb):
            out[(reg, "_COMBINED")] = float(comb["SPI"].iloc[0])
    return out

def load_all():
    df = pd.concat([load_region("THA"), load_region("MAH")], ignore_index=True)
    # attach helmet SPI -> non-wearing rate (VRU lethality proxy)
    helmet = load_helmet()
    df["helmet_spi"] = df.apply(
        lambda r: helmet.get((r["region"], r["land_use"]),
                             helmet.get((r["region"], "_COMBINED"), np.nan)), axis=1)
    df["helmet_norate"] = 1 - df["helmet_spi"]   # non-wearing share, higher = higher VRU lethality
    return gpd.GeoDataFrame(df, geometry="geometry", crs=4326)

# -------- factor 1: speed-deviation index --------
def factor_speed_deviation(df):
    """Difference between P85 and the limit. Positive = operating speed above the limit (road design out of step with the limit)."""
    df["dev_abs"] = df["p85"] - df["speed_limit"]          # km/h
    df["dev_ratio"] = df["dev_abs"] / df["speed_limit"]    # relative
    return df

# -------- factor 2: road-function mismatch --------
def factor_function_mismatch(df):
    """Limit vs the expected limit for the same country/urban-rural/road class (median baseline)."""
    grp = ["region", "land_use", "road_class"]
    baseline = (df.dropna(subset=["speed_limit"])
                  .groupby(grp)["speed_limit"]
                  .agg(lambda s: s.median()).rename("expected_limit"))
    df = df.merge(baseline, on=grp, how="left")
    df["func_mismatch"] = df["speed_limit"] - df["expected_limit"]
    return df

if __name__ == "__main__":
    df = load_all()
    df = factor_speed_deviation(df)
    df = factor_function_mismatch(df)

    print(f"Total harmonised segments (Valid): {len(df):,}")
    print(df.groupby("region").size().to_string())
    print("\n--- key-field missing rates ---")
    for c in ["speed_limit", "p85", "dev_abs", "func_mismatch"]:
        print(f"  {c:<14} missing {df[c].isna().mean()*100:5.1f}%")

    print("\n--- factor 1 speed deviation dev_abs (km/h) percentiles ---")
    print(df["dev_abs"].describe(percentiles=[.1,.25,.5,.75,.9]).round(1).to_string())

    print("\n--- expected-limit baseline by road class (median) ---")
    bl = (df.dropna(subset=["expected_limit"])
            .groupby(["region","land_use","road_class"])["expected_limit"].first())
    print(bl.to_string())

    print("\n--- helmet non-wearing rate (VRU lethality proxy) ---")
    print(df.groupby(["region","land_use"])["helmet_norate"].first().round(3).to_string())

    # save intermediate result
    keep = df.dropna(subset=["speed_limit", "p85"]).copy()
    keep.to_file("output/segments_factors.geojson", driver="GeoJSON")
    print(f"\nWrote output/segments_factors.geojson ({len(keep):,} scorable segments)")

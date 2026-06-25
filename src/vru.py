"""SpeedTruth, VRU exposure spatial join + VRU-based Safe System threshold rebuild.

Aggregates OSM VRU POIs to each segment by buffer, producing:
  - vru_weight   : weighted sum of VRU POIs within the buffer
  - vru_per_km   : weighted exposure per unit length
  - has_school_market : whether a school/market exists in the buffer (strongest pedestrian-mixing signal)
and re-derives safe_threshold from these (fixing v0's misclassification of separated expressways as high-risk).
"""
import os
import numpy as np
import geopandas as gpd
from harmonize import UTM

BUFFER_M = 150          # 150 m either side of a segment counts as VRU exposure range
SCHOOL_MARKET = {"school", "kindergarten", "college", "university", "marketplace"}

def attach_vru(g, region):
    """Attach VRU exposure fields to one region's segments. Returns 0 exposure when POIs are missing (degrades to v0)."""
    # reset_index is critical: ensures seg / seg_u / buffer share the same 0..n RangeIndex,
    # otherwise building the buffer from a filtered global index misaligns geometry into NaN (empty buffers).
    seg = g[g["region"] == region].copy().reset_index(drop=True)
    path = f"output/vru_poi_{region}.gpkg"
    if not os.path.exists(path):
        seg["vru_weight"] = 0.0
        seg["vru_per_km"] = 0.0
        seg["has_school_market"] = False
        return seg

    utm = UTM[region]
    poi = gpd.read_file(path).to_crs(utm)
    poi["is_sm"] = poi["vru_type"].isin(SCHOOL_MARKET)
    seg_u = seg.to_crs(utm)
    buf = gpd.GeoDataFrame(
        {"sid": seg_u.index.values},
        geometry=seg_u.geometry.buffer(BUFFER_M).values, crs=utm)  # .values avoids the index-alignment trap

    j = gpd.sjoin(poi, buf, predicate="within", how="inner")
    agg = j.groupby("sid").agg(
        vru_weight=("weight", "sum"),
        sm=("is_sm", "max")).reindex(seg.index)
    seg["vru_weight"] = agg["vru_weight"].fillna(0.0).values
    seg["has_school_market"] = agg["sm"].fillna(False).astype(bool).values
    # 0.5 km length floor: prevents very short segments from mechanically inflating vru_per_km
    # (audit F9: vru_per_km correlated +0.58 with 1/segment-length)
    seg["vru_per_km"] = seg["vru_weight"] / (seg["length_m"] / 1000).clip(lower=0.5)
    return seg

def attach_vru_all(g):
    import pandas as pd
    parts = [attach_vru(g, r) for r in ["THA", "MAH"]]
    return gpd.GeoDataFrame(
        pd.concat(parts, ignore_index=True), geometry="geometry", crs=4326)

def safe_threshold_v1(row, vru_hi):
    """Safe System threshold based on real VRU exposure.
    vru_hi: the high-exposure cutoff for vru_per_km (passed at runtime as a percentile)."""
    rc = row["road_class"]
    if rc == "motorway":
        return 110                                  # separated, no VRU
    # school/market present, or high VRU density -> pedestrian mixing, 30
    if row["has_school_market"] or row["vru_per_km"] >= vru_hi:
        return 30
    if row["land_use"] == "URBAN":
        return 50                                   # urban intersection / side-impact
    return 70                                        # rural head-on; low-VRU separated arterial


# --- v2: fix the threshold defects found in the audit ---
# F1: removed the near-automatic "any POI density -> 30" trigger (density was contaminated by
#     segment length); now only true pedestrian generators (school/market) = presence-based,
#     no longer using vru_per_km percentile.
# F5: a separated expressway tagged "trunk" (high P85, no pedestrian generator, low VRU) is
#     flagged rather than misclassified as 30/70; grade_sep_uncertain is set for manual/OSM
#     review (honest, not silent).
def is_grade_sep_likely(row):
    """Heuristic: tagged "trunk" but very likely a separated / access-controlled expressway.
    Criteria: trunk class + high operating speed + no school/market + low VRU. A probabilistic
    inference, so it only sets an uncertainty flag."""
    return (row["road_class"] in ("trunk", "motorway")
            and row["p85"] >= 90
            and not row["has_school_market"]
            and row["vru_per_km"] < 1.0)

def safe_threshold_v2(row):
    """Safe System threshold v2 (presence-based). Returns (threshold, grade_sep_uncertain).

    F5 handling (honest, not silent): the blind-test separated-expressway false positives are
    already fixed by the presence-based threshold, they have no school/market, so they are no
    longer pulled down to 30 by the old density trigger and cannot rank into high priority
    (empirically 0 grade_sep candidates reach P1). So here we do NOT raise the threshold from a
    weak heuristic (that would wrongly demote and hide dangerous rural two-lane trunks); we only
    set grade_sep_uncertain: conservative by default (better not to hide a potentially dangerous
    road), listed separately in severity stats, leaving OSM access/dual_carriageway data to settle
    it at the refinement stage."""
    rc = row["road_class"]
    flag = is_grade_sep_likely(row)                  # flag only, does not change the threshold
    if rc == "motorway":
        return 110, flag                            # clearly separated
    if row["has_school_market"]:                     # only a true pedestrian generator pulls to 30 (F1)
        return 30, flag
    if row["land_use"] == "URBAN":
        return 50, flag                             # urban intersection / side-impact
    return 70, flag                                  # rural head-on (suspected-separated kept at 70, flag only)

"""SpeedTruth, corridor aggregation, from segments to fundable investment corridors.

A development bank funds *corridors*, not isolated 150 m segments. This groups the
flagged Priority-1/2 segments into contiguous investment corridors and ranks them by
where avoidable harm concentrates, so the output is an investment plan, not a segment list.

Method: two flagged segments join the same corridor if they are spatially contiguous
(within 60 m in metric UTM) AND share a road name (unnamed stretches link only to other
unnamed neighbours). Connected components of that graph are corridors. Each corridor is
ranked by total avoidable-harm benefit (sum of segment ksi_reduction x exposure, the same
Power-Model proxy used elsewhere).

FDUA: outputs are DERIVED, corridor-level aggregates (severity counts, intervention class,
cost tier, benefit, length, a representative coordinate). No raw probe values (P85, posted
limit, thresholds) are written.
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import warnings
warnings.filterwarnings("ignore")

UTM = {"THA": 32647, "MAH": 32643}
PROX_M = 60          # two segments within 60 m count as contiguous

def build_corridors(region, g):
    s = g[g["region"] == region].copy().reset_index(drop=True)
    if not len(s):
        return s.assign(corridor=[])
    su = s.to_crs(UTM[region])
    s["len_km"] = su.geometry.length.values / 1000.0
    buf = gpd.GeoDataFrame({"i": su.index.values},
                           geometry=su.geometry.buffer(PROX_M / 2).values, crs=UTM[region])
    pairs = gpd.sjoin(buf, buf, predicate="intersects")
    pairs = pairs[pairs["i_left"] < pairs["i_right"]]

    name = s["name"].fillna("").astype(str).str.strip().str.upper()
    G = nx.Graph(); G.add_nodes_from(s.index)
    unnamed = {"", "(UNNAMED ROAD)", "NONE", "NAN"}
    for a, b in zip(pairs["i_left"], pairs["i_right"]):
        na, nb = name.iloc[a], name.iloc[b]
        # link only contiguous segments of the SAME NAMED road; unnamed flagged
        # segments stay as single-segment spots (avoids chaining unrelated stretches)
        if na == nb and na not in unnamed:
            G.add_edge(a, b)
    comp = {n: i for i, c in enumerate(nx.connected_components(G)) for n in c}
    s["corridor"] = s.index.map(comp)
    s["corridor"] = region + "_" + s["corridor"].astype(str)
    return s

def main():
    g = gpd.read_file("output/intervention_priorities.geojson")
    parts = [build_corridors(r, g) for r in ["THA", "MAH"]]
    s = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=4326)

    def rep_name(d):
        nm = d["name"].fillna("(unnamed)").astype(str)
        nm = nm[nm.str.strip().ne("") & nm.ne("(unnamed road)")]
        return nm.mode().iloc[0] if len(nm) else "(unnamed corridor)"

    rows = []
    for cid, d in s.groupby("corridor"):
        cen = d.to_crs(UTM[d["region"].iloc[0]]).geometry.unary_union.centroid
        cen = gpd.GeoSeries([cen], crs=UTM[d["region"].iloc[0]]).to_crs(4326).iloc[0]
        interv = d["intervention"].mode().iloc[0] if "intervention" in d else ""
        rows.append({
            "corridor_id": cid,
            "region": d["region"].iloc[0],
            "road": rep_name(d),
            "n_segments": len(d),
            "length_km": round(float(d["len_km"].sum()), 1),
            "n_critical": int((d["severity"] == "Critical").sum()),
            "n_serious": int((d["severity"] == "Serious").sum()),
            "school_or_market": bool(d.get("has_school_market", pd.Series([False]*len(d))).any())
                                if "has_school_market" in d else None,
            "dominant_intervention": interv,
            "cost_tier": int(d["cost"].max()) if "cost" in d else None,
            "total_benefit": round(float(d["benefit"].sum()), 1) if "benefit" in d else None,
            "mean_bcr_index": round(float(d["bc_score"].mean()), 0) if "bc_score" in d else None,
            "mean_ksi_reduction_pct": round(float(d["ksi_reduction"].mean()) * 100, 0) if "ksi_reduction" in d else None,
            "inspect_at": f"{cen.y:.5f},{cen.x:.5f}",
        })
    C = pd.DataFrame(rows).sort_values("total_benefit", ascending=False).reset_index(drop=True)
    C.insert(0, "rank", C.index + 1)

    n_corr = len(C)
    multi = C[C["n_segments"] >= 2]
    print("=" * 80)
    print("SpeedTruth, corridor aggregation (flagged Priority-1/2 segments -> investment corridors)")
    print("=" * 80)
    print(f"{len(s):,} flagged segments grouped into {n_corr:,} corridors "
          f"({len(multi):,} multi-segment, the rest single-segment spots).")
    tot = C["total_benefit"].sum()
    top20 = C.head(max(1, int(n_corr * 0.2)))["total_benefit"].sum()
    print(f"Top 20% of corridors hold {top20/tot:.0%} of total avoidable-harm benefit, "
          f"the investment short-list.\n")
    print("--- Top 12 corridors by avoidable-harm benefit ---")
    show = ["rank", "region", "road", "n_segments", "length_km", "n_critical",
            "dominant_intervention", "cost_tier", "mean_bcr_index", "inspect_at"]
    print(C[show].head(12).to_string(index=False))

    # outputs (FDUA-safe: derived aggregates only)
    C.to_csv("output/corridors_summary.csv", index=False)
    json.dump({"n_flagged_segments": int(len(s)), "n_corridors": int(n_corr),
               "n_multi_segment": int(len(multi)),
               "top20pct_benefit_share": round(float(top20/tot), 3),
               "top_corridors": C.head(20).to_dict(orient="records")},
              open("output/corridors_summary.json", "w"), ensure_ascii=False, indent=2)

    # dissolved corridor geometries with safe attributes only (no raw probe fields)
    safe_cols = ["corridor", "region", "severity", "intervention", "cost", "benefit",
                 "bc_score", "ksi_reduction", "name", "geometry"]
    s2 = s[[c for c in safe_cols if c in s.columns]]
    diss = s2.dissolve(by="corridor", aggfunc={"benefit": "sum"} if "benefit" in s2 else None)
    diss = diss.reset_index().merge(C[["corridor_id", "rank", "road", "length_km",
                                       "n_critical", "dominant_intervention", "cost_tier",
                                       "mean_bcr_index", "inspect_at"]],
                                    left_on="corridor", right_on="corridor_id", how="left")
    keep = ["corridor", "rank", "region", "road", "length_km", "n_critical",
            "dominant_intervention", "cost_tier", "benefit", "mean_bcr_index", "inspect_at", "geometry"]
    diss[[c for c in keep if c in diss.columns]].to_file("output/corridors.geojson", driver="GeoJSON")
    print("\nWrote output/corridors_summary.csv, corridors_summary.json, corridors.geojson")

if __name__ == "__main__":
    main()

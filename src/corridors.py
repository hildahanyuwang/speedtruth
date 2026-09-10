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
import math
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
from shapely.ops import linemerge
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

def _flag_dual_pairs(C, max_m=100.0, len_tol=0.05):
    """Flag units that look like the two carriageways of one divided road.

    Test: centroids within `max_m`, lengths within `len_tol` (or 0.5 km, whichever is
    looser). Units are grouped, not just paired, so a road split into three parallel
    links is caught as one group.
    """
    C = C.copy()
    C["possible_dual_pair"] = False
    for reg, idx in C.groupby("region").groups.items():
        sub = C.loc[idx].sort_values("_lat")
        ids = list(sub.index)
        lat = sub["_lat"].tolist(); lon = sub["_lon"].tolist(); ln = sub["length_km"].tolist()
        parent = {i: i for i in ids}

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        n = len(ids)
        for i in range(n):
            for j in range(i + 1, n):
                if (lat[j] - lat[i]) * 111000.0 > max_m:      # sorted by lat, so stop
                    break
                if abs(ln[i] - ln[j]) > max(0.5, len_tol * max(ln[i], ln[j])):
                    continue
                dm = math.hypot((lat[i] - lat[j]) * 111000.0,
                                (lon[i] - lon[j]) * 111000.0 * math.cos(math.radians(lat[i])))
                if dm <= max_m:
                    ra, rb = find(ids[i]), find(ids[j])
                    if ra != rb:
                        parent[rb] = ra

        groups = {}
        for i in ids:
            groups.setdefault(find(i), []).append(i)
        for members in groups.values():
            if len(members) >= 2:
                C.loc[members, "possible_dual_pair"] = True
    return C


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
        # AUDIT-C7 (2026-08-27): inspect_at was the centroid of the unit's geometry,
        # and the centroid of a line does not lie on that line. Across the 2,869 units
        # it sat over 100 m off its own road in 1,198 of them and over 1 km in 231;
        # Maharashtra's rank 1 pointed at farmland 7,796 m from the road it names. An
        # external visual check of three flagged dual-carriageway pairs was inspecting
        # the wrong places because of it. Now the halfway point measured ALONG the
        # road, which is on the road by construction.
        gu = d.to_crs(UTM[d["region"].iloc[0]]).geometry.unary_union
        line = linemerge(gu) if gu.geom_type == "MultiLineString" else gu
        if line.geom_type != "LineString":   # branches or gaps: take the longest run
            line = max(line.geoms, key=lambda p: p.length)
        cen = gpd.GeoSeries([line.interpolate(0.5, normalized=True)],
                            crs=UTM[d["region"].iloc[0]]).to_crs(4326).iloc[0]
        # AUDIT-C1 (2026-08-25): intervention and cost_tier were read off different
        # rows, the modal intervention but the maximum cost. Five corridors ended up
        # labelled "medium cost" while carrying tier 4. Both now come from the single
        # most demanding segment, so the label and the tier can no longer disagree.
        if "cost" in d:
            imax = d["cost"].idxmax()
            interv, ctier = d.loc[imax, "intervention"], int(d.loc[imax, "cost"])
        else:
            interv, ctier = "", None
        rows.append({
            "corridor_id": cid,
            # AUDIT-C2 (2026-08-25): build_corridors never links unnamed segments
            # (deliberate, it avoids chaining unrelated stretches), so every unnamed
            # flagged segment became a one-segment "corridor". In Maharashtra that is
            # 70% of the units, and because benefit scales with length while
            # Maharashtra segments are dissolved (up to 180 km), those single spots
            # took all 20 top ranks and pushed out all 68 genuine corridors. Naming
            # the two kinds apart fixes the short list without discarding them.
            # "Unlinked stretch", not "spot": the longest single unit in Maharashtra
            # runs 179.7 km, so calling it a spot would misdescribe it.
            "unit_type": "Corridor" if len(d) >= 2 else "Unlinked stretch",
            "region": d["region"].iloc[0],
            "road": rep_name(d),
            "n_segments": len(d),
            "length_km": round(float(d["len_km"].sum()), 1),
            "n_critical": int((d["severity"] == "Critical").sum()),
            "n_serious": int((d["severity"] == "Serious").sum()),
            "school_or_market": bool(d.get("has_school_market", pd.Series([False]*len(d))).any())
                                if "has_school_market" in d else None,
            "dominant_intervention": interv,
            "cost_tier": ctier,
            "total_benefit": round(float(d["benefit"].sum()), 1) if "benefit" in d else None,
            "mean_bcr_index": round(float(d["bc_score"].mean()), 0) if "bc_score" in d else None,
            "mean_ksi_reduction_pct": round(float(d["ksi_reduction"].mean()) * 100, 0) if "ksi_reduction" in d else None,
            "inspect_at": f"{cen.y:.5f},{cen.x:.5f}",
            "_lat": float(cen.y), "_lon": float(cen.x),
        })
    # AUDIT-C3 (2026-08-25): rank was pooled across both regions while the published
    # alias read "within country/state". Maharashtra's best unit was rank 19 and the
    # region had no rank 1 at all. Ranked within region AND unit type now, which also
    # brings the corridor layer back in line with the two-axis design already used on
    # the segment layer (absolute severity vs in-region priority).
    C = pd.DataFrame(rows).sort_values(["region", "total_benefit"],
                                       ascending=[True, False]).reset_index(drop=True)
    C["rank"] = C.groupby(["region", "unit_type"]).cumcount() + 1
    C.insert(0, "rank", C.pop("rank"))

    # AUDIT-C5 (2026-08-25): benefit is ksi_reduction x traffic x LENGTH, so a long
    # mildly misaligned road outranks a short severely misaligned one.
    C["benefit_per_km"] = (C["total_benefit"] / C["length_km"].clip(lower=0.1)).round(3)

    # AUDIT-C6 (2026-08-25): the two carriageways of a divided road are separate
    # links with separate speed data and, being unnamed, never join into one unit.
    # Maharashtra's ranks 1+2 sit 13 m apart at identical length, as do 4+5. Both
    # pairs were checked geometrically on 2026-08-27: over 125.4 km and 86.6 km the
    # two lines never diverge by more than 33 m (Hausdorff), so they are one road.
    C = _flag_dual_pairs(C)
    C = C.drop(columns=["_lat", "_lon"])

    n_corr = len(C)
    multi = C[C["unit_type"] == "Corridor"]
    print("=" * 80)
    print("SpeedTruth, corridor aggregation (flagged Priority-1/2 segments -> investment corridors)")
    print("=" * 80)
    print(f"{len(s):,} flagged segments grouped into {n_corr:,} units: "
          f"{len(multi):,} multi-segment CORRIDORS and {n_corr - len(multi):,} UNLINKED STRETCHES.")
    for reg, d in C.groupby("region"):
        m = d[d["unit_type"] == "Corridor"]
        unnamed = (m["road"].astype(str).str.contains("unnamed")).sum()
        share = d[d["unit_type"] == "Corridor"]["total_benefit"].sum() / d["total_benefit"].sum()
        dup = int(d["possible_dual_pair"].sum())
        print(f"  {reg}: {len(m):,} corridors ({unnamed} unnamed, holding {share:.0%} of this "
              f"region's avoidable harm), {len(d) - len(m):,} unlinked stretches")
        print(f"       {dup:,} units flagged as a possible dual-carriageway pair "
              f"- VERIFY ON A MAP")
    tot = C["total_benefit"].sum()
    top20 = C.nlargest(max(1, int(n_corr * 0.2)), "total_benefit")["total_benefit"].sum()
    print(f"Top 20% of units hold {top20/tot:.0%} of total avoidable-harm benefit.\n")
    print("--- Top 12 CORRIDORS by avoidable-harm benefit (spots excluded) ---")
    show = ["rank", "region", "road", "n_segments", "length_km", "n_critical", "n_serious",
            "dominant_intervention", "cost_tier", "mean_bcr_index", "inspect_at"]
    print(multi.nlargest(12, "total_benefit")[show].to_string(index=False))

    # outputs (FDUA-safe: derived aggregates only)
    # AUDIT-F1 (2026-09-10): mean_ksi_reduction_pct was published in both summaries and
    # should not have been. For a single-segment unit it is that segment's own
    # ksi_reduction, and ksi_reduction = 1 - (safe/p85)**3 inverts to p85 as soon as
    # safe is reconstructed, which open data allows. On a test segment, the rounded
    # percentage returned p85 to within 1 km/h. 2,464 of the 2,869 units are
    # single-segment, so the column is dropped from what gets written. It stays in the
    # frame above, where it is only printed.
    PUBLISHED = C.drop(columns=["mean_ksi_reduction_pct"], errors="ignore")
    PUBLISHED.to_csv("output/corridors_summary.csv", index=False)
    # `n_corridors` stays the count of ALL units for continuity with the published
    # figure; `n_multi_segment` is the linked-corridor count. The per-region harm
    # shares are the reason the app cannot simply default to corridors-only: the same
    # filter keeps 54% of Thailand's avoidable harm and 7% of Maharashtra's.
    cb = multi["total_benefit"].sort_values(ascending=False)
    by_region = {}
    for reg, d in C.groupby("region"):
        m = d[d["unit_type"] == "Corridor"]
        by_region[reg] = {
            "n_corridors": int(len(m)),
            "corridor_harm_share": round(float(m["total_benefit"].sum() / d["total_benefit"].sum()), 3),
            "corridors_unnamed": int(m["road"].astype(str).str.contains("unnamed").sum()),
        }
    json.dump({"n_flagged_segments": int(len(s)), "n_corridors": int(n_corr),
               "n_multi_segment": int(len(multi)),
               "top20pct_benefit_share": round(float(top20 / tot), 3),
               "top20pct_benefit_share_corridors_only":
                   round(float(cb.head(max(1, int(len(cb) * 0.2))).sum() / cb.sum()), 3),
               "by_region": by_region,
               "dual_pair_units": int(C["possible_dual_pair"].sum()),
               "dual_pair_units_that_are_corridors":
                   int((C["possible_dual_pair"] & (C["unit_type"] == "Corridor")).sum()),
               "top_corridors": multi.drop(columns=["mean_ksi_reduction_pct"], errors="ignore")
                                     .nlargest(20, "total_benefit").to_dict(orient="records")},
              open("output/corridors_summary.json", "w"), ensure_ascii=False, indent=2)

    # dissolved corridor geometries with safe attributes only (no raw probe fields)
    safe_cols = ["corridor", "region", "severity", "intervention", "cost", "benefit",
                 "bc_score", "ksi_reduction", "name", "geometry"]
    s2 = s[[c for c in safe_cols if c in s.columns]]
    diss = s2.dissolve(by="corridor", aggfunc={"benefit": "sum"} if "benefit" in s2 else None)
    # AUDIT-C4 (2026-08-25): n_segments and n_serious were computed above but dropped
    # here, so a reader saw a bare "Critical: 0" with no way to tell that the corridor
    # still holds five flagged Serious segments. Both are carried through now, together
    # with unit_type.
    diss = diss.reset_index().merge(C[["corridor_id", "unit_type", "rank",
                                       "road", "n_segments", "length_km",
                                       "n_critical", "n_serious", "dominant_intervention",
                                       "cost_tier", "benefit_per_km", "mean_bcr_index",
                                       "possible_dual_pair", "inspect_at"]],
                                    left_on="corridor", right_on="corridor_id", how="left")
    keep = ["corridor", "unit_type", "rank", "region", "road",
            "n_segments", "length_km", "n_critical", "n_serious",
            "dominant_intervention", "cost_tier", "benefit", "benefit_per_km",
            "mean_bcr_index", "possible_dual_pair", "inspect_at", "geometry"]
    diss[[c for c in keep if c in diss.columns]].to_file("output/corridors.geojson", driver="GeoJSON")
    print("\nWrote output/corridors_summary.csv, corridors_summary.json, corridors.geojson")

if __name__ == "__main__":
    main()

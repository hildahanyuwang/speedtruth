"""SpeedTruth, interactive map of Speed-Unsafe Segments.

Decision-maker oriented: tier-coloured network, governance flag in tooltip.
Single GeoJson layer per region (compact) instead of per-feature objects.
"""
import folium
from folium.features import GeoJsonTooltip
import geopandas as gpd

TIER_COLOR = {"Priority 1": "#c0144c", "Priority 2": "#f07814",
              "Monitor": "#e8b800", "Compliant": "#9fb89f"}
TIER_WEIGHT = {"Priority 1": 4, "Priority 2": 3, "Monitor": 2, "Compliant": 1}
CENTER = {"THA": (15.0, 101.5, 6), "MAH": (19.0, 76.0, 7)}
TITLE = {"THA": "Thailand", "MAH": "Maharashtra (India)"}

# FDUA-safe: publish ONLY derived outputs (Speed Safety Score, tier, severity,
# governance flag). NEVER embed raw probe fields (posted limit, P85, speed
# distributions, probe counts) or anything that allows reconstructing them
# (ped_fatality_pct, oper_excess, safe_threshold paired with excess). See FDUA §4.4.
def build_map(region):
    g = gpd.read_file("output/speed_safety_score.geojson")
    g = g[g["region"] == region].copy()
    g["geometry"] = g.geometry.simplify(0.0004)
    g["speed_safety_score"] = g["speed_safety_score"].round(0)
    g["name"] = g["name"].fillna("(unnamed road)")
    keep = ["name", "speed_safety_score", "tier", "severity", "governance_flag", "geometry"]
    g = g[keep]

    lat, lon, z = CENTER[region]
    m = folium.Map(location=[lat, lon], zoom_start=z, tiles="CartoDB positron")

    # draw low→high so Priority sits on top; separate layers for toggling
    for tier in ["Compliant", "Monitor", "Priority 2", "Priority 1"]:
        sub = g[g["tier"] == tier]
        if not len(sub):
            continue
        color, weight = TIER_COLOR[tier], TIER_WEIGHT[tier]
        folium.GeoJson(
            sub.__geo_interface__,
            name=f"{tier} ({len(sub):,})",
            show=(tier != "Compliant"),
            style_function=lambda x, c=color, w=weight: {
                "color": c, "weight": w, "opacity": 0.85},
            tooltip=GeoJsonTooltip(
                fields=["name", "speed_safety_score", "tier", "severity", "governance_flag"],
                aliases=["Road", "Speed Safety Score (0-100)", "Priority tier",
                         "Safe-System severity", "Why flagged (governance)"],
                sticky=True, max_width=420),
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    legend = """<div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:white;
      padding:10px 14px;border:1px solid #999;border-radius:6px;font:13px sans-serif">
      <b>Speed Safety Score</b><br>
      <span style="color:#c0144c">&#9608;</span> Priority 1, review now<br>
      <span style="color:#f07814">&#9608;</span> Priority 2, schedule review<br>
      <span style="color:#e8b800">&#9608;</span> Monitor<br>
      <span style="color:#9fb89f">&#9608;</span> Compliant</div>"""
    title = f"""<div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:9999;
      background:white;padding:6px 18px;border-radius:6px;font:bold 16px sans-serif;border:1px solid #999">
      SpeedTruth, {TITLE[region]} · Speed-Unsafe Segments</div>"""
    m.get_root().html.add_child(folium.Element(legend))
    m.get_root().html.add_child(folium.Element(title))

    out = f"output/map_{region}.html"
    m.save(out)
    import os
    print(f"  {out}  ({os.path.getsize(out)/1e6:.1f} MB, {len(g):,} segments)")

if __name__ == "__main__":
    for r in ["THA", "MAH"]:
        build_map(r)

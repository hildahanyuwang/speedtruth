"""SpeedTruth, intervention-priority map = a decision tool.

Colour by what the fix costs (green quick-wins on top); CLICK any segment for a
decision card: the misalignment, why the limit is wrong (governance diagnosis),
the recommended intervention, the return, and a coordinate to inspect on the
ground. Hover gives a one-line summary."""
import folium
from folium.features import GeoJsonTooltip, GeoJsonPopup
import geopandas as gpd

COST_COLOR = {1: "#2e9e4f", 2: "#f0a000", 4: "#c0144c"}      # green / amber / red
COST_WEIGHT = {1: 5, 2: 3, 4: 2}
CENTER = {"THA": (15.0, 101.5, 6), "MAH": (19.0, 76.0, 7)}
TITLE = {"THA": "Thailand", "MAH": "Maharashtra (India)"}

def first_coord(s):
    try:
        p = str(s).split(",")
        return f"{float(p[1]):.5f}, {float(p[0]):.5f}"      # "lat, lon" to paste into Maps
    except Exception:
        return "n/a"

def build_map(region):
    g = gpd.read_file("output/intervention_priorities.geojson")
    g = g[g["region"] == region].copy()
    g["geometry"] = g.geometry.simplify(0.0004)
    g["name"] = g["name"].fillna("(unnamed road)")
    # FDUA-safe decision card: DERIVED outputs only (Speed Safety Score classification,
    # governance diagnosis, recommendation, model-output ratios). NO raw probe fields
    # (posted limit, P85, distributions) and nothing that reconstructs them
    # (ped_fatality_pct, safe_threshold). See FDUA §4.4.
    g["bc_score"] = g["bc_score"].round(0)
    g["Why the limit is flagged"] = g["governance_flag"].astype(str).map(lambda s: s.split(" | ")[0][:160])
    g["Recommended action"] = g["intervention"]
    g["Avoidable KSI"] = (g["ksi_reduction"] * 100).round(0).map(lambda x: f"~{x:.0f}% if brought to a safe speed")
    g["Investment return (0-100)"] = g["bc_score"]
    g["Inspect at"] = g["street_link"].map(first_coord)
    g["Road"] = g["name"] + "  (Safe-System severity: " + g["severity"].astype(str) + ")"

    pop_fields = ["Road", "Why the limit is flagged", "Recommended action",
                  "Avoidable KSI", "Investment return (0-100)", "Inspect at"]
    g["hover"] = g["name"] + ", " + g["intervention"]
    keep = pop_fields + ["hover", "cost", "geometry"]
    g = g[keep]

    lat, lon, z = CENTER[region]
    m = folium.Map(location=[lat, lon], zoom_start=z, tiles="CartoDB positron")
    for c in [4, 2, 1]:                                     # high-cost first, quick-wins on top
        sub = g[g["cost"] == c]
        if not len(sub):
            continue
        folium.GeoJson(
            sub.__geo_interface__,
            name={1: "Quick win, re-set limit (low cost)",
                  2: "Enforcement + calming (medium)",
                  4: "Physical protection (high cost)"}[c] + f"  ({len(sub):,})",
            style_function=lambda x, col=COST_COLOR[c], w=COST_WEIGHT[c]: {
                "color": col, "weight": w, "opacity": 0.85},
            tooltip=GeoJsonTooltip(fields=["hover"], labels=False, sticky=True),
            popup=GeoJsonPopup(fields=pop_fields, aliases=[f + ":" for f in pop_fields],
                               max_width=460),
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    legend = """<div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:white;
      padding:10px 14px;border:1px solid #999;border-radius:6px;font:13px sans-serif">
      <b>Intervention priority (by cost)</b><br>
      <span style="color:#2e9e4f">&#9608;</span> Quick win, re-set limit (low cost)<br>
      <span style="color:#f0a000">&#9608;</span> Enforcement + calming (medium)<br>
      <span style="color:#c0144c">&#9608;</span> Physical protection (high cost)<br>
      <span style="font-size:11px;color:#666">Click a segment for its decision card &middot;
      top 20% hold ~70% of avoidable harm</span></div>"""
    title = f"""<div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:9999;
      background:white;padding:6px 18px;border-radius:6px;font:bold 16px sans-serif;border:1px solid #999">
      SpeedTruth, {TITLE[region]} · Where to invest first (click to inspect)</div>"""
    m.get_root().html.add_child(folium.Element(legend))
    m.get_root().html.add_child(folium.Element(title))

    out = f"output/priority_map_{region}.html"
    m.save(out)
    import os
    print(f"  {out}  ({os.path.getsize(out)/1e6:.1f} MB, {len(g):,} segments)")

if __name__ == "__main__":
    for r in ["THA", "MAH"]:
        build_map(r)

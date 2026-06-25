"""SpeedTruth, street-level verification.

Turns each priority segment into a clickable Google Street View pano at the
segment midpoint, so a reviewer can SEE the road condition behind the score.
Exports two evidence shortlists (Markdown) for the Findings report:
  1. Top priority segments per region.
  2. The highest-impact cases: high-speed arterials passing schools/markets.
No API key needed, links open the public Street View pano.
"""
import geopandas as gpd
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

def sv_url(lat, lon):
    return f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat:.6f},{lon:.6f}"

def gmap_url(lat, lon):
    return f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}"

def load():
    g = gpd.read_file("output/speed_safety_score.geojson")
    mid = g.geometry.interpolate(0.5, normalized=True)   # representative point ON the road
    g["mlat"], g["mlon"] = mid.y.values, mid.x.values
    g["name"] = g["name"].fillna("(unnamed road)")
    return g

def table(df, cols_header):
    lines = ["| " + " | ".join(cols_header) + " |",
             "|" + "|".join(["---"] * len(cols_header)) + "|"]
    for _, r in df.iterrows():
        sv = f"[Street View]({sv_url(r['mlat'], r['mlon'])})"
        lines.append("| " + " | ".join([
            r["region"], str(r["name"])[:28], r["road_class"], r["land_use"],
            f"{r['speed_limit']:.0f}", f"{r['p85']:.0f}", f"{r['safe_threshold']:.0f}",
            f"{r['speed_safety_score']:.0f}", f"{r['ped_fatality_pct']:.0f}%", sv]) + " |")
    return "\n".join(lines)

def main():
    g = load()
    hdr = ["Region", "Road", "Class", "Land", "Limit", "P85", "Safe", "Score", "PedFatal@P85", "Verify"]
    out = ["# SpeedTruth, Street-Level Verification Shortlist\n",
           "*Each link opens the Google Street View panorama at the segment midpoint. "
           "Use it to visually confirm the condition behind the score.*\n"]

    out.append("\n## A. Top priority segments (per region)\n")
    for reg in ["THA", "MAH"]:
        top = (g[(g.region == reg) & (g.tier == "Priority 1")]
               .sort_values("speed_safety_score", ascending=False).head(10))
        out.append(f"\n### {reg}, top 10 Priority 1\n")
        out.append(table(top, hdr))

    sm = g[(g.tier == "Priority 1") & (g.has_school_market)]
    p85_med = sm["p85"].median()
    pf_med = sm["ped_fatality_pct"].median()
    n_extreme = int((sm["p85"] > 110).sum())
    out.append("\n\n## B. School/market-adjacent priority segments, the core governance story\n")
    out.append(f"**{len(sm):,} Priority-1 segments lie within 150 m of a school or market.** "
               f"Their P85 operating speed has a **median of {p85_med:.0f} km/h**, against a Safe System "
               f"pedestrian-survivable speed of 30 km/h, implying a **median pedestrian fatality risk at P85 of "
               f"~{pf_med:.0f}%** (Rosén & Sander 2009), versus ~7% at 30 km/h. This is the headline finding, "
               f"and it rests on the median, not on outliers.\n")
    out.append(f"> **Honest caveat:** 150 m proximity to a school/market POI does not by itself prove pedestrian "
               f"crossing/mixing. A minority ({n_extreme} segments) have very high P85 (>110 km/h) and may be "
               f"grade-separated arterials where the POI does not imply conflict. Every case below carries a "
               f"Street View link for visual confirmation, which is precisely what street-level verification is for.\n")
    cases = sm.sort_values("speed_safety_score", ascending=False).head(15)
    out.append(table(cases, hdr))

    # one governance flag example block for the report
    out.append("\n\n## C. Example governance diagnoses (top 5 cases)\n")
    for _, r in cases.head(5).iterrows():
        out.append(f"- **{r['name']}** ({r['region']}, {r['road_class']}): limit {r['speed_limit']:.0f}, "
                   f"P85 {r['p85']:.0f}, Safe System {r['safe_threshold']:.0f} km/h, "
                   f"pedestrian fatality risk @P85 ≈ {r['ped_fatality_pct']:.0f}%.\n"
                   f"  - *{r['governance_flag']}*\n"
                   f"  - [Verify on Street View]({sv_url(r['mlat'], r['mlon'])})")

    with open("output/streetview_shortlist.md", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"Wrote output/streetview_shortlist.md")
    print(f"  Top-priority links + {len(cases)} school/market high-impact cases")
    print(f"\nHighest-impact case sample:")
    for _, r in cases.head(3).iterrows():
        print(f"  [{r['region']}] {str(r['name'])[:26]:<26} limit{r['speed_limit']:.0f} P85={r['p85']:.0f} "
              f"pedFatal={r['ped_fatality_pct']:.0f}% {sv_url(r['mlat'], r['mlon'])}")

if __name__ == "__main__":
    main()

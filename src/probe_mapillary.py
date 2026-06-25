"""Probe Mapillary coverage on top priority segments before committing to street-view CV."""
import os, json, time, urllib.request, urllib.parse
import geopandas as gpd, warnings
warnings.filterwarnings("ignore")

TOKEN = os.environ["MLY_TOKEN"]

def imgs_near(lon, lat, d=0.0012):
    bbox = f"{lon-d},{lat-d},{lon+d},{lat+d}"
    url = ("https://graph.mapillary.com/images?"
           + urllib.parse.urlencode({"access_token": TOKEN,
                                     "fields": "id,captured_at",
                                     "bbox": bbox, "limit": 3}))
    try:
        r = json.load(urllib.request.urlopen(url, timeout=25))
        return len(r.get("data", []))
    except Exception as e:
        return f"ERR:{str(e)[:40]}"

g = gpd.read_file("output/speed_safety_score.geojson")
p1 = g[g.tier == "Priority 1"].copy()
mid = p1.geometry.interpolate(0.5, normalized=True)
p1["lon"], p1["lat"] = mid.x.values, mid.y.values
sel = (p1[(p1.helmet_norate >= 0.70) | (p1.has_school_market)]
       .sort_values("speed_safety_score", ascending=False).head(24))

hit = 0
for _, r in sel.iterrows():
    n = imgs_near(r["lon"], r["lat"])
    ok = isinstance(n, int) and n > 0
    hit += ok
    print(f"[{r['region']}] {str(r['name'])[:20]:20} ({r['lat']:.4f},{r['lon']:.4f}) imgs={n}")
    time.sleep(0.3)
print(f"\nCoverage: {hit}/{len(sel)} segments have Mapillary imagery within ~130 m")

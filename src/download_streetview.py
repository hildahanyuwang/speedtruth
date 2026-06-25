"""Download Mapillary street-level images for top priority segments (for visual verification)."""
import os, json, time, urllib.request, urllib.parse
import geopandas as gpd, warnings
warnings.filterwarnings("ignore")

TOKEN = os.environ["MLY_TOKEN"]
OUT = "output/streetview_images"
os.makedirs(OUT, exist_ok=True)

def get_img(lon, lat, d=0.0015):
    bbox = f"{lon-d},{lat-d},{lon+d},{lat+d}"
    url = ("https://graph.mapillary.com/images?"
           + urllib.parse.urlencode({"access_token": TOKEN,
                                     "fields": "id,thumb_1024_url,computed_geometry",
                                     "bbox": bbox, "limit": 1}))
    try:
        r = json.load(urllib.request.urlopen(url, timeout=25))
        d = r.get("data", [])
        return d[0] if d else None
    except Exception:
        return None

g = gpd.read_file("output/speed_safety_score.geojson")
p1 = g[g.tier == "Priority 1"].copy()
mid = p1.geometry.interpolate(0.5, normalized=True)
p1["lon"], p1["lat"] = mid.x.values, mid.y.values
sel = (p1[(p1.helmet_norate >= 0.70) | (p1.has_school_market)]
       .sort_values("speed_safety_score", ascending=False))

meta = []
for _, r in sel.iterrows():
    if len(meta) >= 8:
        break
    im = get_img(r["lon"], r["lat"])
    if not im or not im.get("thumb_1024_url"):
        time.sleep(0.2); continue
    fn = f"{OUT}/{len(meta):02d}_{r['region']}.jpg"
    try:
        urllib.request.urlretrieve(im["thumb_1024_url"], fn)
    except Exception:
        time.sleep(0.2); continue
    meta.append({
        "file": fn, "region": r["region"], "name": str(r["name"]),
        "road_class": r["road_class"], "land_use": r["land_use"],
        "speed_limit": float(r["speed_limit"]), "p85": float(r["p85"]),
        "safe_threshold": float(r["safe_threshold"]),
        "helmet_norate": round(float(r["helmet_norate"]), 2),
        "has_school_market": bool(r["has_school_market"]),
        "ped_fatality_pct": round(float(r["ped_fatality_pct"]), 1),
        "governance_flag": r["governance_flag"],
        "lat": round(float(r["lat"]), 5), "lon": round(float(r["lon"]), 5),
    })
    print("saved", fn, "|", r["region"], str(r["name"])[:20], "limit", int(r["speed_limit"]), "P85", int(r["p85"]))
    time.sleep(0.3)

json.dump(meta, open(f"{OUT}/meta.json", "w"), ensure_ascii=False, indent=2)
print(f"\nDownloaded {len(meta)} street-view images + meta.json")

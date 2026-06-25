"""
SpeedTruth, CV pull for LOWER tiers (Monitor/Compliant), to test the other
direction: does imagery-derived road condition find roads the OSM proxy
UNDER-flagged? A segment with no school/market POI gets a high safe threshold
(50/70) and ranks low, but if imagery shows a genuine pedestrian-mixing street,
the proxy missed it. Finding these = real discovery, not re-ranking.

Samples Monitor/Compliant by traffic (urban, busier = better imagery coverage
and more likely pedestrian environments). Appends to cv_manifest_full.json
(skips seg_ids already pulled). Images (c) Mapillary, CC BY-SA.
Run: MLY_TOKEN=... python src/streetview_cv_pull_lower.py
"""
import os, json, time, urllib.request, urllib.parse
import geopandas as gpd, pandas as pd, warnings
warnings.filterwarnings("ignore")

TOKEN = os.environ["MLY_TOKEN"]
OUT = "output/cv_images_full"
MAN = "output/cv_manifest_full.json"
os.makedirs(OUT, exist_ok=True)
N_CAND = 4000          # candidate budget across Monitor+Compliant

def get_img(lon, lat, d=0.0015):
    bbox = f"{lon-d},{lat-d},{lon+d},{lat+d}"
    url = ("https://graph.mapillary.com/images?"
           + urllib.parse.urlencode({"access_token": TOKEN,
                                     "fields": "id,thumb_1024_url", "bbox": bbox, "limit": 1}))
    try:
        r = json.load(urllib.request.urlopen(url, timeout=25))
        dd = r.get("data", [])
        return dd[0] if dd else None
    except Exception:
        return None

g = gpd.read_file("output/speed_safety_score.geojson")
mid = g.geometry.interpolate(0.5, normalized=True)
g["lon"], g["lat"] = mid.x.values, mid.y.values
cand = g[g.tier.isin(["Monitor", "Compliant"])].sort_values("traffic_pct", ascending=False).head(N_CAND)
print(f"Lower-tier candidates (by traffic): {len(cand)}", flush=True)

manifest = json.load(open(MAN, encoding="utf-8")) if os.path.exists(MAN) else {}
done_ids = {v["seg_id"] for v in manifest.values()}
idx = max([int(k.split("_")[1]) for k in manifest] + [-1]) + 1
pulled = 0
for _, r in cand.iterrows():
    sid = str(r["seg_id"])
    if sid in done_ids:
        continue
    im = get_img(r["lon"], r["lat"]); time.sleep(0.13)
    if not im or not im.get("thumb_1024_url"):
        continue
    iid = f"cvf_{idx:05d}"; fn = f"{OUT}/{iid}.jpg"
    try:
        urllib.request.urlretrieve(im["thumb_1024_url"], fn)
    except Exception:
        continue
    manifest[iid] = {
        "seg_id": sid, "stratum": r["tier"], "region": r["region"], "name": str(r["name"]),
        "road_class": r["road_class"], "land_use": r["land_use"],
        "speed_limit": float(r["speed_limit"]), "p85": float(r["p85"]),
        "safe_threshold": float(r["safe_threshold"]),
        "has_school_market": bool(r["has_school_market"]),
        "grade_sep_uncertain": bool(r["grade_sep_uncertain"]),
        "tier": r["tier"], "severity": r["severity"],
        "speed_safety_score": round(float(r["speed_safety_score"]), 2),
        "lat": round(float(r["lat"]), 5), "lon": round(float(r["lon"]), 5), "file": fn,
    }
    idx += 1; pulled += 1
    if pulled % 25 == 0:
        json.dump(manifest, open(MAN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  pulled {pulled} lower-tier (manifest {len(manifest)})", flush=True)
    time.sleep(0.1)

json.dump(manifest, open(MAN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
from collections import Counter
print(f"\nManifest now {len(manifest)} | by tier: {dict(Counter(v['tier'] for v in manifest.values()))}")

"""
SpeedTruth, stage 1 of automated road-condition CV: pull imagery + manifest.

Pulls one Mapillary image per segment for a sample focused on the safe=30
segments (where the OSM school/market proxy over-assigns the pedestrian
threshold, audit F1, confirmed by the manual road-condition audit). Stage 2
(streetview_cv_classify.py) runs a vision model over these to derive the real
road condition and a corrected safe-threshold, at a scale hand review cannot.

Saves images to output/cv_images/ and a manifest output/cv_manifest.json.
Images (c) Mapillary contributors, CC BY-SA.  Run: python src/streetview_cv_pull.py
"""
import os, json, time, urllib.request, urllib.parse
import geopandas as gpd, warnings
warnings.filterwarnings("ignore")

TOKEN = os.environ["MLY_TOKEN"]
OUT = "output/cv_images"
os.makedirs(OUT, exist_ok=True)

# quotas (filled only where Mapillary coverage exists; pools oversampled)
QUOTA = {"P1_safe30": 120, "gradesep": 25, "control": 25}

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

def midpoints(df):
    mid = df.geometry.interpolate(0.5, normalized=True)
    df = df.copy(); df["lon"], df["lat"] = mid.x.values, mid.y.values
    return df

g = gpd.read_file("output/speed_safety_score.geojson")
pools = {
    "P1_safe30": midpoints(g[(g.safe_threshold == 30) & (g.has_school_market)
                             & (g.tier == "Priority 1")]
                           .sort_values("speed_safety_score", ascending=False)).head(600),
    "gradesep":  midpoints(g[g.grade_sep_uncertain].sort_values("p85", ascending=False)).head(200),
    "control":   midpoints(g[g.tier == "Compliant"].sort_values("traffic_pct", ascending=False)).head(300),
}

manifest, idx = {}, 0
for label, df in pools.items():
    got = 0
    print(f"Pulling {label} (target {QUOTA[label]})…", flush=True)
    for _, r in df.iterrows():
        if got >= QUOTA[label]:
            break
        im = get_img(r["lon"], r["lat"]); time.sleep(0.2)
        if not im or not im.get("thumb_1024_url"):
            continue
        iid = f"cv_{idx:03d}"; fn = f"{OUT}/{iid}.jpg"
        try:
            urllib.request.urlretrieve(im["thumb_1024_url"], fn)
        except Exception:
            continue
        manifest[iid] = {
            "stratum": label, "region": r["region"], "name": str(r["name"]),
            "road_class": r["road_class"], "land_use": r["land_use"],
            "speed_limit": float(r["speed_limit"]), "p85": float(r["p85"]),
            "safe_threshold": float(r["safe_threshold"]),
            "has_school_market": bool(r["has_school_market"]),
            "grade_sep_uncertain": bool(r["grade_sep_uncertain"]),
            "tier": r["tier"], "severity": r["severity"],
            "lat": round(float(r["lat"]), 5), "lon": round(float(r["lon"]), 5),
            "file": fn,
        }
        idx += 1; got += 1
        if got % 10 == 0:
            print(f"  {label}: {got}/{QUOTA[label]}", flush=True)
        time.sleep(0.15)
    print(f"  {label}: collected {got}", flush=True)

json.dump(manifest, open("output/cv_manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
from collections import Counter
print(f"\nStaged {len(manifest)} images -> {OUT}/ | strata: {dict(Counter(v['stratum'] for v in manifest.values()))}")
print("Manifest: output/cv_manifest.json. Run streetview_cv_classify.py with ANTHROPIC_API_KEY next.")

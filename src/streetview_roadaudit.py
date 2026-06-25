"""
SpeedTruth, scaled ROAD-CONDITION audit via street imagery (blind).

Purpose (corrected from vehicle-spotting): street imagery's rigorous use is to
read the STATIC ROAD CONDITION that determines whether a posted limit is
appropriate, separation, footpath, roadside development, genuine pedestrian
mixing, NOT to count transient traffic. This directly tests the model's
safe-threshold ASSUMPTIONS, which are otherwise inferred from OSM proxies (the
"definitional" weakness, audit F1).

We pull one image per segment for three strata and shuffle them blind:
  A. safe=30 assigned via a school/market within 150 m (does imagery confirm a
     real pedestrian-mixing road, or did the OSM proxy mis-trigger?)
  B. grade_sep_uncertain trunk (is it actually access-controlled / separated?)
  C. Compliant controls (are they genuinely safer / separated?)

The rater (Claude vision) scores each anonymised image on a road-condition
rubric BEFORE seeing the model's assumption (key written separately), then we
measure agreement. Validates the score against VISIBLE road condition, not crash
outcomes. Images (c) Mapillary contributors, CC BY-SA.

Run:  MLY_TOKEN=<token> python src/streetview_roadaudit.py
"""
import os, json, time, random, urllib.request, urllib.parse
import geopandas as gpd, warnings
warnings.filterwarnings("ignore")

TOKEN = os.environ["MLY_TOKEN"]
OUT = "output/roadaudit_images"
os.makedirs(OUT, exist_ok=True)
random.seed(7)

QUOTA = {"A_school30": 16, "B_gradesep": 8, "C_control": 8}

def get_img(lon, lat, d=0.0015):
    bbox = f"{lon-d},{lat-d},{lon+d},{lat+d}"
    url = ("https://graph.mapillary.com/images?"
           + urllib.parse.urlencode({"access_token": TOKEN,
                                     "fields": "id,thumb_1024_url,computed_geometry,captured_at",
                                     "bbox": bbox, "limit": 1}))
    try:
        r = json.load(urllib.request.urlopen(url, timeout=25))
        dd = r.get("data", [])
        return dd[0] if dd else None
    except Exception:
        return None

def midpoints(df):
    mid = df.geometry.interpolate(0.5, normalized=True)
    df = df.copy()
    df["lon"], df["lat"] = mid.x.values, mid.y.values
    return df

g = gpd.read_file("output/speed_safety_score.geojson")

# strata candidate pools (oversample; many segments lack Mapillary coverage)
pools = {
    "A_school30": midpoints(g[(g.safe_threshold == 30) & (g.has_school_market)
                              & (g.tier.isin(["Priority 1", "Priority 2"]))]
                            .sort_values("speed_safety_score", ascending=False)).head(120),
    "B_gradesep": midpoints(g[g.grade_sep_uncertain]
                            .sort_values("p85", ascending=False)).head(120),
    "C_control":  midpoints(g[g.tier == "Compliant"]
                            .sort_values("traffic_pct", ascending=False)).head(200),
}

def collect(df, label, quota):
    got = []
    for _, r in df.iterrows():
        if len(got) >= quota:
            break
        im = get_img(r["lon"], r["lat"]); time.sleep(0.22)
        if not im or not im.get("thumb_1024_url"):
            continue
        got.append({
            "url": im["thumb_1024_url"], "stratum": label,
            "region": r["region"], "name": str(r["name"]),
            "road_class": r["road_class"], "land_use": r["land_use"],
            "speed_limit": float(r["speed_limit"]), "p85": float(r["p85"]),
            "safe_threshold": float(r["safe_threshold"]),
            "has_school_market": bool(r["has_school_market"]),
            "grade_sep_uncertain": bool(r["grade_sep_uncertain"]),
            "tier": r["tier"], "severity": r["severity"],
            "score": round(float(r["speed_safety_score"]), 1),
            "lat": round(float(r["lat"]), 5), "lon": round(float(r["lon"]), 5),
        })
        print(f"  [{label}] {r['region']} {str(r['name'])[:24]:24} safe={r['safe_threshold']:.0f} P85={r['p85']:.0f}")
    return got

items = []
for label, df in pools.items():
    print(f"Collecting {label} (target {QUOTA[label]})…")
    items += collect(df, label, QUOTA[label])

random.shuffle(items)
key = {}
for i, it in enumerate(items):
    iid = f"ra_{i:02d}"
    fn = f"{OUT}/{iid}.jpg"
    try:
        urllib.request.urlretrieve(it["url"], fn)
    except Exception:
        continue
    key[iid] = {k: v for k, v in it.items() if k != "url"}
    key[iid]["file"] = fn
    time.sleep(0.18)

json.dump(key, open("output/roadaudit_key.json", "w"), ensure_ascii=False, indent=2)
from collections import Counter
cnt = Counter(v["stratum"] for v in key.values())
print(f"\nDownloaded {len(key)} images -> {OUT}/  | strata: {dict(cnt)}")
print("Key saved to output/roadaudit_key.json, rate road condition BEFORE opening it.")

"""
SpeedTruth, blind street-level verification WITH CONTROLS.

Upgrade over the first 8-image spot check: this builds a DISCRIMINATIVE test.
We pull Mapillary imagery for BOTH:
  - TREATMENT: top Priority-1 segments (high score, the roads we flag as unsafe), and
  - CONTROL:   Compliant segments (low score, the roads we call safe).
Images are saved with ANONYMISED ids (img_01..img_NN) in a shuffled order; the
tier/score key is written to a SEPARATE file the rater does not open until after
rating each image purely on its visible content. Then we ask: can the model's
flag be recovered from the road's appearance alone, i.e. do flagged roads show
VRU mixing / speed-mismatch conditions more than the roads we call safe?

This tests whether the score corresponds to VISIBLE reality (road condition),
NOT crash outcomes. We state that boundary plainly. Images (c) Mapillary
contributors, CC BY-SA.

Run:  MLY_TOKEN=<token> python src/streetview_blindtest.py
"""
import os, json, time, random, urllib.request, urllib.parse
import geopandas as gpd, warnings
warnings.filterwarnings("ignore")

TOKEN = os.environ["MLY_TOKEN"]
OUT = "output/blindtest_images"
os.makedirs(OUT, exist_ok=True)
random.seed(42)

N_TREAT, N_CTRL = 16, 8          # quotas (filled only where imagery exists)

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

# TREATMENT, policy-relevant Priority 1 (motorcycle corridors or school/market), top score
treat = midpoints(
    g[(g.tier == "Priority 1") & ((g.helmet_norate >= 0.70) | (g.has_school_market))]
    .sort_values("speed_safety_score", ascending=False)
).head(60)

# CONTROL, the model's "safe" calls, but HARD controls: busy/trafficked roads the
# model still scores Compliant (these have street-view coverage AND look like they
# *could* be flagged, a fairer discriminative test than empty rural roads).
ctrl = midpoints(
    g[g.tier == "Compliant"].sort_values("traffic_pct", ascending=False)
).head(250)

def collect(df, label, quota):
    got = []
    for _, r in df.iterrows():
        if len(got) >= quota:
            break
        im = get_img(r["lon"], r["lat"])
        time.sleep(0.25)
        if not im or not im.get("thumb_1024_url"):
            continue
        got.append({
            "url": im["thumb_1024_url"], "group": label,
            "region": r["region"], "name": str(r["name"]),
            "road_class": r["road_class"], "land_use": r["land_use"],
            "speed_limit": float(r["speed_limit"]), "p85": float(r["p85"]),
            "safe_threshold": float(r["safe_threshold"]), "tier": r["tier"],
            "score": round(float(r["speed_safety_score"]), 1),
            "helmet_norate": round(float(r["helmet_norate"]), 2),
            "has_school_market": bool(r["has_school_market"]),
            "ped_fatality_pct": round(float(r["ped_fatality_pct"]), 1),
            "lat": round(float(r["lat"]), 5), "lon": round(float(r["lon"]), 5),
        })
        print(f"  [{label}] {r['region']} {str(r['name'])[:22]:22} score={float(r['speed_safety_score']):.0f}")
    return got

print("Collecting treatment (Priority 1)…")
t = collect(treat, "TREAT", N_TREAT)
print("Collecting control (Compliant)…")
c = collect(ctrl, "CTRL", N_CTRL)

# shuffle together, assign anonymised ids, download, split visible images from key
items = t + c
random.shuffle(items)
key = {}
for i, it in enumerate(items):
    iid = f"img_{i:02d}"
    fn = f"{OUT}/{iid}.jpg"
    try:
        urllib.request.urlretrieve(it["url"], fn)
    except Exception:
        continue
    key[iid] = {k: v for k, v in it.items() if k != "url"}
    key[iid]["file"] = fn
    time.sleep(0.2)

json.dump(key, open("output/blindtest_key.json", "w"), ensure_ascii=False, indent=2)
n_t = sum(1 for v in key.values() if v["group"] == "TREAT")
n_c = sum(1 for v in key.values() if v["group"] == "CTRL")
print(f"\nDownloaded {len(key)} images: {n_t} treatment + {n_c} control -> {OUT}/")
print("Key (tier/score) saved to output/blindtest_key.json, DO NOT open until after rating.")

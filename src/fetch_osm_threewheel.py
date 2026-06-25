"""SpeedTruth, pull three-wheeler / informal paratransit stop POIs.

Motivation: three-wheelers (Indian auto-rickshaws, Thai tuk-tuk/songthaew, human-powered
cycle-rickshaws) are a major VRU class in South/Southeast Asia, but appear neither in the
commercial probe-speed sample (slow, not fleet) nor in our VRU pedestrian-generator layer.
This script makes a best effort to pull their stop/gathering points from OSM as an exposure proxy.

Honest note: OSM tags informal stops sparsely, and human-powered rickshaws are barely tagged.
This layer is a LOWER-BOUND proxy, not a census. We report whatever we pull, without extrapolation.
"""
import urllib.request, urllib.error, json, time, sys, math
import geopandas as gpd
from shapely.geometry import Point

ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]

# cover OSM conventions for three-wheeler / informal transport tags (slim version, drops the expensive name regex)
QUERY = """[out:json][timeout:120];
(
 nwr[amenity=taxi]({bbox});
 nwr[amenity=motorcycle_taxi]({bbox});
 nwr[route=share_taxi]({bbox});
);
out center tags;"""

def classify(tags):
    """Returns (type, whether explicitly a three-wheeler)."""
    name = (tags.get("name", "") or "").lower()
    taxi = (tags.get("taxi", "") or "").lower()
    am = tags.get("amenity", "")
    explicit = any(k in name for k in ("rickshaw", "tuk tuk", "tuk-tuk", "tuktuk", "auto stand", "songthaew")) \
        or any(k in taxi for k in ("auto_rickshaw", "rickshaw", "tuk")) \
        or am == "motorcycle_taxi"
    if am == "taxi":
        return ("taxi_stand", explicit)
    if am == "motorcycle_taxi":
        return ("motorcycle_taxi", True)
    if tags.get("route") == "share_taxi":
        return ("share_taxi", explicit)
    if explicit:
        return ("named_paratransit", True)
    if "taxi" in tags:
        return ("taxi_tagged", explicit)
    return (None, False)

def fetch_bbox(bbox, attempt=0, ep_start=0):
    q = QUERY.format(bbox=f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}")
    url = ENDPOINTS[(ep_start + attempt) % len(ENDPOINTS)]
    try:
        req = urllib.request.Request(url, data=q.encode(),
                                     headers={"User-Agent": "SpeedTruth-ADB/1.0"})
        data = json.load(urllib.request.urlopen(req, timeout=180))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        if attempt < 4:
            time.sleep(5 * (attempt + 1))
            return fetch_bbox(bbox, attempt + 1)
        print(f"    !! giving up on {bbox}: {e}")
        return []
    out = []
    for el in data["elements"]:
        t, explicit = classify(el.get("tags", {}))
        if not t: continue
        if el["type"] == "node":
            lon, lat = el.get("lon"), el.get("lat")
        else:
            c = el.get("center")
            if not c: continue
            lon, lat = c["lon"], c["lat"]
        if lon is None: continue
        out.append((lon, lat, t, explicit, el.get("tags", {}).get("name", "")))
    return out

def occupied_cells(gdf, size=1.0):
    cells = set()
    for geom in gdf.geometry:
        gb = geom.bounds
        for x in range(int(math.floor(gb[0]/size)), int(math.floor(gb[2]/size))+1):
            for y in range(int(math.floor(gb[1]/size)), int(math.floor(gb[3]/size))+1):
                cells.add((x, y))
    pad = 0.03
    return [(y*size-pad, x*size-pad, (y+1)*size+pad, (x+1)*size+pad) for (x, y) in sorted(cells)]

def run(region):
    g = gpd.read_file("output/speed_safety_score.geojson")
    g = g[g["region"] == region]
    cells = occupied_cells(g)
    print(f"{region}: {len(g):,} segments -> {len(cells)} occupied grid cells to query")
    seen, rows = set(), []
    for i, bbox in enumerate(cells, 1):
        t0 = time.time()
        pois = fetch_bbox(bbox, ep_start=i)
        new = 0
        for lon, lat, t, explicit, name in pois:
            key = (round(lon, 6), round(lat, 6), t)
            if key in seen: continue
            seen.add(key); rows.append((lon, lat, t, explicit, name)); new += 1
        print(f"  [{i}/{len(cells)}] +{new} (cumulative {len(rows)}) {time.time()-t0:.0f}s", flush=True)
        # incremental save: every 5 cells + at the end, to avoid losing everything on timeout
        if rows and (i % 5 == 0 or i == len(cells)):
            gpd.GeoDataFrame(
                {"tw_type": [r[2] for r in rows],
                 "explicit_3w": [r[3] for r in rows],
                 "name": [r[4] for r in rows]},
                geometry=[Point(r[0], r[1]) for r in rows], crs=4326
            ).to_file(f"output/threewheel_{region}.gpkg", driver="GPKG")
        time.sleep(0.5)
    if not rows:
        print(f"{region}: 0 three-wheeler / informal-transport POIs (untagged in OSM)")
        return
    gdf = gpd.GeoDataFrame(
        {"tw_type": [r[2] for r in rows],
         "explicit_3w": [r[3] for r in rows],
         "name": [r[4] for r in rows]},
        geometry=[Point(r[0], r[1]) for r in rows], crs=4326)
    out = f"output/threewheel_{region}.gpkg"
    gdf.to_file(out, driver="GPKG")
    print(f"{region}: {len(gdf):,} total -> {out}")
    print("--- type distribution ---")
    print(gdf["tw_type"].value_counts().to_string())
    print(f"--- of which explicitly three-wheeler (name/tag confirmed): {int(gdf['explicit_3w'].sum())} ---")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "MAH")

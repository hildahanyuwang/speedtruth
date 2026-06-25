"""SpeedTruth, pull OSM VRU *infrastructure* (not just generators).

Generators (schools/markets, fetch_osm_vru.py) tell us WHERE vulnerable users
gather. Infrastructure tells us whether the road actually PROVIDES for them:
  - pedestrian crossings   -> real, designed pedestrian access across the road
                              (the key signal that a POI nearby means true mixing,
                               not a grade-separated road with frontage)
  - cycleways              -> cycling provision; its ABSENCE on a busy road is a gap
  - traffic calming        -> speed is actively managed here

Crossings are the load-bearing signal for the separation-aware safe-speed fix:
a school 150 m from an expressway with NO crossing is likely grade-separated;
a school by an at-grade road WITH a crossing is genuine pedestrian mixing.

Only queries 1-degree cells that contain scored segments. Points only
(ways via 'out center') to stay light vs. full footway geometry.
"""
import urllib.request, urllib.error, json, time, sys, math
import geopandas as gpd
from shapely.geometry import Point

ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]

# infra type -> weight (used later as access evidence, not exposure)
INFRA_WEIGHT = {"crossing": 1.0, "cycleway": 1.0, "traffic_calming": 1.0,
                "footway": 1.0}

QUERY = """[out:json][timeout:150];
(
 node[highway=crossing]({bbox});
 node[footway=crossing]({bbox});
 way[highway=cycleway]({bbox});
 way[cycleway~"^(lane|track|opposite_track|opposite_lane)$"]({bbox});
 node[traffic_calming]({bbox});
 way[highway=footway][bridge]({bbox});
 way[highway=footway][tunnel]({bbox});
);
out center tags;"""

def infra_type(tags):
    if tags.get("highway") == "crossing" or tags.get("footway") == "crossing":
        return "crossing"
    if tags.get("highway") == "cycleway" or tags.get("cycleway") in (
            "lane", "track", "opposite_track", "opposite_lane"):
        return "cycleway"
    if tags.get("traffic_calming"):
        return "traffic_calming"
    if tags.get("highway") == "footway" and (tags.get("bridge") or tags.get("tunnel")):
        return "footway"          # grade-separated pedestrian crossing structure
    return None

def fetch_bbox(bbox, attempt=0, ep_start=0):
    q = QUERY.format(bbox=f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}")
    url = ENDPOINTS[(ep_start + attempt) % len(ENDPOINTS)]
    try:
        req = urllib.request.Request(url, data=q.encode(),
                                     headers={"User-Agent": "SpeedTruth-ADB/1.0"})
        data = json.load(urllib.request.urlopen(req, timeout=210))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        if attempt < 4:
            time.sleep(5 * (attempt + 1))
            return fetch_bbox(bbox, attempt + 1, ep_start)
        print(f"    !! give up {bbox}: {e}", flush=True)
        return []
    out = []
    for el in data["elements"]:
        t = infra_type(el.get("tags", {}))
        if not t:
            continue
        if el["type"] == "node":
            lon, lat = el.get("lon"), el.get("lat")
        else:
            c = el.get("center")
            if not c:
                continue
            lon, lat = c["lon"], c["lat"]
        if lon is None:
            continue
        out.append((lon, lat, t))
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
    print(f"{region}: {len(g):,} segs -> {len(cells)} occupied cells", flush=True)
    seen, rows = set(), []
    for i, bbox in enumerate(cells, 1):
        t0 = time.time()
        items = fetch_bbox(bbox, ep_start=i)
        new = 0
        for lon, lat, t in items:
            key = (round(lon, 6), round(lat, 6), t)
            if key in seen:
                continue
            seen.add(key); rows.append((lon, lat, t)); new += 1
        print(f"  [{i}/{len(cells)}] +{new} (total {len(rows)}) {time.time()-t0:.0f}s", flush=True)
        time.sleep(0.5)
    gdf = gpd.GeoDataFrame(
        {"infra_type": [r[2] for r in rows],
         "weight": [INFRA_WEIGHT[r[2]] for r in rows]},
        geometry=[Point(r[0], r[1]) for r in rows], crs=4326)
    out = f"output/vru_infra_{region}.gpkg"
    gdf.to_file(out, driver="GPKG")
    print(f"{region}: {len(gdf):,} infra features -> {out}", flush=True)
    print(gdf["infra_type"].value_counts().to_string(), flush=True)

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "MAH")

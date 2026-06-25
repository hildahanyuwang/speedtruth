"""SpeedTruth, pull VRU (vulnerable road user) generator POIs from OpenStreetMap.

Queries Overpass only on the 1-degree grid cells that have scored-segment coverage,
avoiding needless requests and rate limiting.
VRU generators = places where pedestrians/cyclists gather: schools, markets, hospitals, transit, places of worship, etc.
"""
import urllib.request, urllib.error, json, time, sys, math
import geopandas as gpd
from shapely.geometry import Point

ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]

# VRU generator type -> exposure weight (children / dense crowds weighted higher)
VRU_WEIGHT = {
    "school": 3.0, "kindergarten": 3.0, "college": 2.0, "university": 2.0,
    "marketplace": 2.5, "hospital": 2.0, "clinic": 1.5,
    "place_of_worship": 1.5, "bus_station": 2.0, "bus_stop": 1.0,
    "station": 1.5, "mall": 2.0,
}

QUERY = """[out:json][timeout:120];
(
 nwr[amenity~"^(school|college|university|kindergarten|marketplace|hospital|clinic|bus_station|place_of_worship)$"]({bbox});
 nwr[highway=bus_stop]({bbox});
 nwr[public_transport=station]({bbox});
 nwr[railway=station]({bbox});
 nwr[shop=mall]({bbox});
);
out center tags;"""

def poi_type(tags):
    for k in ("amenity", "shop", "railway", "public_transport", "highway"):
        v = tags.get(k)
        if v in VRU_WEIGHT:
            return v
    if tags.get("highway") == "bus_stop": return "bus_stop"
    if tags.get("public_transport") == "station": return "station"
    return None

def fetch_bbox(bbox, attempt=0, ep_start=0):
    """bbox=(s,w,n,e). Returns a list of (lon,lat,type). With retries + endpoint rotation (spreads rate limiting)."""
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
        t = poi_type(el.get("tags", {}))
        if not t: continue
        if el["type"] == "node":
            lon, lat = el["lon"], el["lat"]
        else:
            c = el.get("center")
            if not c: continue
            lon, lat = c["lon"], c["lat"]
        out.append((lon, lat, t))
    return out

def occupied_cells(gdf, size=1.0):
    """Returns the list of grid-cell bboxes (s,w,n,e) that have segment coverage."""
    b = gdf.total_bounds
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
        pois = fetch_bbox(bbox, ep_start=i)   # rotate endpoints per cell to spread rate limiting
        new = 0
        for lon, lat, t in pois:
            key = (round(lon, 6), round(lat, 6), t)
            if key in seen: continue
            seen.add(key); rows.append((lon, lat, t)); new += 1
        print(f"  [{i}/{len(cells)}] +{new} (cumulative {len(rows)}) {time.time()-t0:.0f}s", flush=True)
        time.sleep(0.5)
    gdf = gpd.GeoDataFrame(
        {"vru_type": [r[2] for r in rows],
         "weight": [VRU_WEIGHT[r[2]] for r in rows]},
        geometry=[Point(r[0], r[1]) for r in rows], crs=4326)
    out = f"output/vru_poi_{region}.gpkg"
    gdf.to_file(out, driver="GPKG")
    print(f"{region}: {len(gdf):,} VRU POIs total -> {out}")
    print(gdf["vru_type"].value_counts().to_string())

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "MAH")

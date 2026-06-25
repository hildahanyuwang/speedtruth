# SpeedTruth, Data Inventory Report (Day 1)

*Generated 2026-06-22 from the ADB-provided dataset. Reproducible via `inventory.py`.*

---

## 1. Files received

| File | Size | Format | Role |
|---|---|---|---|
| `ADB_Innovation_Thailand.geojson` | 86 MB | GeoJSON (EPSG:4326, LineString) | **Primary**, Thailand road sections + commercial probe data speed summaries |
| `ADB_Innovation_Maharashtra.geojson` | 43 MB | GeoJSON (EPSG:4326, LineString) | **Primary**, Maharashtra (India) road sections + speed summaries |
| `Archive/…_Maharashtra_(Feature).gpkg` | 23 MB | GeoPackage | Same data as the Maharashtra GeoJSON, GIS-native format |
| `Archive/…_Thailand_(Feature).gpkg` | 48 MB | GeoPackage | Same data as the Thailand GeoJSON |
| `Archive/…_(Helmet_Wearing_results)_…v02.xlsx` | 16 KB | Excel | Helmet-wearing survey results (VRU context, aggregate) |
| `AI for Safer Roads 2026 - Data User Guide v1.0.pdf` |  | PDF | Field dictionary (Thailand schema) |
| `drive-download-…zip` | 75 MB | Zip | **Redundant**, duplicate of the above; can be deleted |

The two GeoJSONs and the two GPKGs are the same content in two formats. Work from the GeoJSONs (or GPKGs once GDAL is installed); ignore the zip.

---

## 2. Coverage & scale

| | Thailand | Maharashtra |
|---|---|---|
| Total road sections | **55,884** | **14,082** |
| Geometry | LineString (lon/lat) | LineString (lon/lat) |
| Network source | Overture, Dec 2024 | Overture, May 2025 |
| Road classes | motorway / trunk / primary / secondary | same |
| **Sections with speed data** (`AnalysisStatus = Valid`) | **11,544 (20.7%)** | **4,010 (28.5%)** |
|, usable after dropping zero/null P85 & limit | **~11,134** | **~3,576** |

**The analyzable universe is the `AnalysisStatus = Valid` subset only** (~15.5k segments across both regions). The other ~80% are network geometry with no commercial probe data and must be excluded from scoring (or shown greyed-out on the map).

Spatial extent: Thailand sample seen around Surin province (lon ~103.4, lat ~14.8). Province breakdown available via `ProvinceID` (Thailand, 78 values).

---

## 3. Field dictionary, the fields that matter for scoring

Common analytical core (present in both, after harmonization):

| Field | Meaning | Notes |
|---|---|---|
| `F85thPercentileSpeed` | **P85 operating speed** | The key operating-speed signal. km/h. |
| `MedianSpeed` | 50th-pctile speed | km/h |
| `SpeedLimit` | Posted limit | **commercial-probe-derived, "Not validated" (per guide).** See §4. |
| `RoadClass` | Overture functional class | motorway/trunk/primary/secondary |
| `LandUse` | URBAN / RURAL | From NASA GRUMP; only on Valid segments |
| `PercentOverLimit` | Est. fraction of vehicles over limit | 0–1 |
| `NumberOverLimit` | Est. annual count over limit | Not a true count (no AADF) |
| `Percentile` / `RankedPercentile` | Traffic-volume percentile | Used to target "roads carrying 75% of travel" |
| `SampleSize_avg` / `WeightedSample` | Probe sample size / length-weighted | Confidence weighting |
| `StreetImageLink` | `startLon,startLat,endLon,endLat` | StreetView coords + usable as segment endpoints |
| `Shape_Length` | Geometric length | Use this, **not** `RoadLength` (per guide) |

---

## 4. Schema differences between the two countries (must harmonize)

The two files are **not** the same schema, a harmonization mapping is required before joint analysis:

| Concept | Thailand field | Maharashtra field |
|---|---|---|
| Segment id | `OvertureID` | `DISSOLVE_ID` (string identifier) |
| Local name | `english_ro` | `names_primary` (may be in Devanagari script) |
| **Speed limit dtype** | `SpeedLimit` = **int** | `SpeedLimit` = **string** (`"20".."80"`), must cast |
| Urban flag | `LandUse` only | `LandUse` **and** `UrbanPC` (0/1) |
| Total sample | `SampleSizeTotal` | `Sample_Size_Total` |
| Extra flags | `ForAnalysis`, `InvPercentile`, `NO_OF_Result_Segments`, `ProvinceID` | `Pass`, `ExcludeFromSpeedSPI` |

**Speed-limit regimes differ:** Thailand limits range 0–120 km/h; Maharashtra is a discrete set {20,30,40,45,50,55,60,70,80}. Expected-limit-by-class baselines (for the Road Function Mismatch factor) must be country-specific.

---

## 5. Data-quality issues

1. **Missing-coded-as-zero (Thailand):** 410 `Valid` segments have `SpeedLimit = 0` **and** `F85thPercentileSpeed = 0`. These are junk, drop them. Treat `0` as null for speed fields.
2. **Null limits (Maharashtra):** 433 of 4,010 `Valid` segments have `SpeedLimit = null` (limit ~11% missing even where speed data exists).
3. **Speed limit is unvalidated.** The guide explicitly states `SpeedLimit` is "obtained by commercial probe data… not validated." This is the single most important caveat for this challenge: **our task is to judge whether posted limits are appropriate, but the posted-limit field itself is an unverified estimate.** SpeedTruth must (a) flag this as a methodological risk and (b) lean on P85-vs-class and VRU context rather than treating `SpeedLimit` as ground truth.
4. **CRS / length units to verify:** coordinates are EPSG:4326 (degrees), but `Shape_Length` (~11,600 for a 3.7 km road) is not in degrees or plain metres, confirm the source CRS before computing any distance-based metric (e.g. VRU proximity). Likely a projected CRS used by the source dashboard.
5. **`PercentOverLimit` / `Percentile` typing:** parsed as int in Maharashtra due to leading 0/1 values; cast to float on load.

---

## 6. Gaps vs. the briefing's assumptions (important)

The briefing (§3) anticipated richer inputs than were actually delivered. **Not present in the provided files:**

- ❌ **Mapillary street-level imagery / ML-identified road features & signs**, only a `StreetImageLink` (Google StreetView lon/lat string) exists. No image features, no sign detections.
- ❌ **Crash / collision history**, none. This removes the briefing's preferred evaluation path ("holdout validation on segments with known crash history"). Evaluation must instead use Safe System threshold logic + internal consistency, or supplement with open crash data if any exists for these regions.
- ❌ **Contextual VRU layers** (schools, markets, transit stops, population density, land use beyond URBAN/RURAL, powered-two-wheeler indicators). The **VRU Exposure Index** (a core differentiator of the Speed Safety Score) has **no source in the provided data**, it must be built from external open data (e.g. OSM POIs for schools/markets, WorldPop/GHSL for population, OSM for intersection density).

The only VRU-adjacent provided dataset is the **helmet-wearing survey xlsx** (aggregate, not segment-level; requires `openpyxl` to read).

---

## 7. Environment status

- Python 3.13, **pandas 2.2.3** present.
- **Missing:** `geopandas`, `shapely`, `fiona`/`pyogrio`, GDAL/`ogrinfo`, `openpyxl`. These are needed for spatial joins, GPKG reading, distance computation, and the Excel file.
- Action: `pip install geopandas openpyxl` (pulls shapely/pyogrio/pyproj) before modeling begins.

---

## 8. Implications for the Speed Safety Score

| Score factor (briefing §6) | Data availability | Verdict |
|---|---|---|
| 1. Speed Deviation Index (P85 − limit) | ✅ `F85thPercentileSpeed`, `SpeedLimit` | Build now, but treat limit as estimate |
| 2. Road Function Mismatch (limit vs class) | ✅ `RoadClass` + `SpeedLimit` | Build now, country-specific baselines |
| 3. VRU Exposure Index | ❌ Not in data | **Needs external open data** (OSM/WorldPop) |
| 4. Environmental Risk (intersections, urban/rural) | ⚠️ `LandUse` only; intersection density absent | Partial; derive intersection density from network/OSM |
| 5. Temporal Consistency | ❌ No time-of-day breakdown | Not feasible with provided data |

**Bottom line:** Factors 1–2 are immediately buildable from the provided data. The differentiating factors (3, 4) require an external-data ingestion step, this should be planned into Day 2 rather than discovered on Day 4.

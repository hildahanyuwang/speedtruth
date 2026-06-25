# SpeedTruth, Investment Corridor Short-list

*From flagged segments to fundable corridors. A development bank invests in corridors, not isolated 150 m segments, so SpeedTruth groups the flagged Priority-1/2 segments into contiguous, same-road investment corridors and ranks them by where avoidable harm concentrates.*
*ADB AI for Safer Roads 2026 · Thailand & Maharashtra (India) · derived outputs only (FDUA-safe)*

---

## The headline for an investment committee
- **3,679 flagged segments collapse into 2,869 corridors** (405 multi-segment routes; the rest single-segment spots).
- **The top 20% of corridors carry ~76% of the total avoidable-harm benefit.** Funding flows to a short-list, not a 3,679-line spreadsheet.
- Each corridor carries a dominant **intervention class**, a **cost tier**, an **iRAP-style benefit-cost index**, and a coordinate to inspect on the ground.

## Method (transparent, reproducible, `src/corridors.py`)
Two flagged segments join the same corridor if they are **spatially contiguous** (within 60 m, metric UTM) **and share a road name**; connected components of that graph are corridors. Corridors are ranked by **total avoidable-harm benefit** = sum over segments of (Power-Model KSI-reduction x exposure), the same proxy used in the investment case (`FINDINGS.md` §4). This is a transparent, relative prioritisation signal, not a casualty forecast (no crash data; see `FINDINGS.md` §6).

## Top 15 corridors by avoidable-harm benefit
| Rank | Corridor (road) | Region | Segs | Length (km) | Critical segs | Dominant intervention | BCR index | Inspect at |
|---|---|---|---|---|---|---|---|---|
| 1 | Phahonyothin Road | THA | 4 | 175.3 | 4 | Footways / crossings / separation | ~24 | `17.23462,99.13542` |
| 2 | Si Khio-Det Udom Road | THA | 10 | 179.2 | 10 | Footways / crossings / separation | ~9 | `14.61997,103.28428` |
| 3 | Phetkasem Road | THA | 5 | 163.5 | 5 | Footways / crossings / separation | ~18 | `10.99824,99.32187` |
| 4 | Phahon Yothin Road | THA | 5 | 168.7 | 5 | Footways / crossings / separation | ~18 | `14.13177,100.64946` |
| 5 | Suwannason Road | THA | 8 | 167.5 | 8 | Footways / crossings / separation | ~11 | `13.81547,102.16090` |
| 6 | Debaratna Road | THA | 4 | 163.9 | 4 | Footways / crossings / separation | ~21 | `13.60145,100.80185` |
| 7 | Phahon Yothin Road | THA | 11 | 160.2 | 11 | Footways / crossings / separation | ~8 | `16.00510,99.82070` |
| 8 | Mittraphap Road | THA | 6 | 161.2 | 6 | Footways / crossings / separation | ~14 | `14.92241,101.90390` |
| 9 | Nittayo Road | THA | 4 | 159.7 | 4 | Footways / crossings / separation | ~21 | `17.31559,104.42867` |
| 10 | Rama II Road | THA | 4 | 155.1 | 4 | Footways / crossings / separation | ~20 | `13.59204,100.32433` |
| 11 | Maliwan Road | THA | 11 | 158.8 | 11 | Footways / crossings / separation | ~7 | `16.49846,102.40268` |
| 12 | (unnamed corridor) | THA | 1 | 152.2 | 1 | Footways / crossings / separation | ~80 | `16.95463,103.55928` |
| 13 | Sukhumvit Road | THA | 6 | 147.2 | 6 | Footways / crossings / separation | ~13 | `12.73480,101.74502` |
| 14 | Rangsit-Nakhon Nayok Road | THA | 4 | 142.0 | 4 | Footways / crossings / separation | ~19 | `14.10239,100.90959` |
| 15 | Asian Highway | THA | 4 | 134.3 | 4 | Footways / crossings / separation | ~18 | `7.91071,99.92769` |

*Full ranked list: `output/corridors_summary.csv` (2,869 corridors). Interactive map: `output/corridor_map.html`. Geometry: `output/corridors.geojson`.*

## How a ministry / ADB uses this
1. **Fund the short-list.** Start at rank 1 and work down until the budget is exhausted; the benefit concentration means a few corridors capture most of the avoidable harm.
2. **Match the instrument to the corridor.** Green corridors are near-zero-cost limit re-sets (immediate quick wins); red corridors need physical protection (footways, crossings, separated motorcycle lanes) and a capital line.
3. **Inspect before committing.** Every corridor has a coordinate; open it in street imagery (the same `StreetImageLink` the model reads) to confirm before funding.
4. **Worked example:** `PILOT_CORRIDOR.md` takes one corridor end-to-end, from flag to costed action.

"""SpeedTruth, quantified impact & benefit-cost scenario.

Turns the priority list into a magnitude a development bank can weigh, WITHOUT
fabricating a casualty figure we do not have. We have NO segment-level crash
counts, so we DO NOT claim an absolute "X lives saved". Instead we publish:

  1. Robust, internally-computed metrics (mileage, exposure share, Power-Model
     avoidable-KSI fraction, benefit concentration).
  2. An ILLUSTRATIVE absolute scenario presented as a TRANSPARENT SENSITIVITY
     TABLE over an explicit, reader-adjustable assumption (what share of the
     region's road deaths occur on the flagged network). No single hidden number.
  3. A benefit-cost anchor taken from iRAP's OWN Indian deployments (verified
     BCRs), so the "return" claim rests on the field's gold-standard precedent,
     not on our arithmetic.

Every external constant below is sourced in SOURCES.md. Honest caveats printed
at the end and carried into FINDINGS.
"""
import numpy as np
import geopandas as gpd

# ---- External, cited reference constants (see SOURCES.md) -------------------
REGION_DEATHS = {
    # region : (annual road deaths, year, source)
    "MAH": (15224, 2022, "MoRTH Road Accidents in India 2022 (Maharashtra state total)"),
    "THA": (18218, 2021, "WHO Global Status Report on Road Safety 2023 (Thailand, modelled est.)"),
}
COST_PER_DEATH_USD = 93400      # iRAP India Four States 2011 (INR 4.9135m); 2011 prices, undervalued today
IRAP_INDIA_BCR = {"footpath": 14.0, "crossing": 12.9}   # iRAP India Four States 2011, verified
KSI_EXPONENT = 3.0              # Nilsson/Elvik Power Model, KSI

# Reader-adjustable assumption: what share of the region's TOTAL road deaths
# plausibly occur on the flagged high-priority network. We do NOT know this;
# we show a spread so the reader can pick / discount. Deliberately conservative.
ATTRIB_SHARES = [0.05, 0.10, 0.20]

def region_metrics(g, region):
    s = g[g["region"] == region].copy()
    s["len_km"] = s["length_m"] / 1000.0
    s["expo"] = (s["traffic_pct"].fillna(s["traffic_pct"].median()) / 100.0) * s["len_km"]
    pri = s[s["tier"].isin(["Priority 1", "Priority 2"])].copy()
    vb = pri["p85"].clip(lower=1)
    va = np.minimum(pri["safe_threshold"], pri["p85"])
    pri["ksi_red"] = 1 - (va / vb) ** KSI_EXPONENT
    pri["benefit"] = pri["ksi_red"] * pri["expo"]
    return {
        "net_km": s["len_km"].sum(),
        "n_pri": len(pri),
        "pri_km": pri["len_km"].sum(),
        "pri_mileage_share": pri["len_km"].sum() / s["len_km"].sum(),
        "pri_expo_share": pri["expo"].sum() / s["expo"].sum(),
        "ksi_red_mean": pri["ksi_red"].mean(),
        "ksi_red_median": pri["ksi_red"].median(),
        "top20_benefit": pri["benefit"].sort_values(ascending=False)
                          .head(int(len(pri) * 0.2)).sum() / pri["benefit"].sum(),
    }

def main():
    g = gpd.read_file("output/speed_safety_score.geojson")
    print("=" * 74)
    print("SpeedTruth, Quantified impact & benefit-cost scenario")
    print("=" * 74)
    for region in ["MAH", "THA"]:
        m = region_metrics(g, region)
        deaths, yr, src = REGION_DEATHS[region]
        print(f"\n### {region}  (baseline: {deaths:,} road deaths/yr, {yr}; {src})")
        print(f"  Assessed network            : {m['net_km']:,.0f} km, {len(g[g.region==region]):,} segments")
        print(f"  High-priority segments      : {m['n_pri']:,}  ({m['pri_km']:,.0f} km, "
              f"{m['pri_mileage_share']:.0%} of mileage, {m['pri_expo_share']:.0%} of exposure)")
        print(f"  Avoidable-KSI fraction*     : mean {m['ksi_red_mean']:.0%}, median {m['ksi_red_median']:.0%}  "
              f"(*Power Model, theoretical ceiling at large speed cuts)")
        print(f"  Benefit concentration       : top 20% of priority segments hold "
              f"{m['top20_benefit']:.0%} of total avoidable-KSI benefit")

        # Illustrative absolute scenario, transparent sensitivity over attribution share.
        # Use the CONSERVATIVE central reduction = median, then discount to a realistic
        # 'achievable' band (we DO NOT use the inflated mean/ceiling for the headline).
        achievable = min(m["ksi_red_median"], 0.40)   # cap realistic reduction at 40% (honesty floor)
        print(f"  Illustrative avoidable deaths/yr (if interventions reach a realistic "
              f"{achievable:.0%} cut on the flagged network):")
        for sh in ATTRIB_SHARES:
            avoided = deaths * sh * achievable
            usd = avoided * COST_PER_DEATH_USD
            print(f"      if {sh:>4.0%} of {region} deaths are on this network -> "
                  f"~{avoided:,.0f} deaths/yr avoided  (~US${usd/1e6:,.1f}M/yr, @US$93.4k/death, 2011)")

    print("\n" + "-" * 74)
    print("Benefit-cost anchor (iRAP's OWN Indian deployments, not our arithmetic):")
    print(f"  Pedestrian footpath BCR = {IRAP_INDIA_BCR['footpath']}, "
          f"pedestrian crossing BCR = {IRAP_INDIA_BCR['crossing']}  (iRAP India Four States, 2011)")
    print("  => the intervention classes SpeedTruth prioritises return ~13-14x in the Indian context.")
    print("\nHONEST CAVEATS:")
    print("  - No segment-level crash data exists; the absolute figures above are ILLUSTRATIVE")
    print("    scenarios over an explicit, reader-adjustable attribution share, NOT a forecast.")
    print("  - The Power-Model avoidable-KSI fraction inflates at large speed reductions; the")
    print("    headline uses a capped, realistic 40% achievable cut, not the theoretical ceiling.")
    print("  - Cost-per-death is iRAP India 2011 (US$93.4k); real 2026 value is higher (undercount).")
    print("  - Deaths-on-network share is unknown for these regions; hence the sensitivity spread.")

if __name__ == "__main__":
    main()

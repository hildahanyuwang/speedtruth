"""SpeedTruth, benefit-cost intervention prioritisation.

Turns the diagnosis ("where is the limit wrong") into an investment case
("fix what, in what order, for what return"), the question a development
bank actually asks.

Method: the Nilsson/Elvik Power Model, the authoritative speed-injury
relationship cited by WHO and the World Bank GRSF. If operating speed on a
segment were brought down to its Safe System safe speed, the relative change
in killed-and-seriously-injured (KSI) is approximately (v_after / v_before)^3.
We weight that avoidable-KSI fraction by traffic exposure to get a relative
safety benefit, divide by an intervention-cost tier, and rank.

HONEST LIMITS: no baseline casualty counts were provided, so this is a
RELATIVE avoidable-KSI potential per unit exposure, not an absolute lives
figure. The Power Model assumes speed is the operative variable (Elvik notes
real-world scatter). Results are an investment-prioritisation signal, not a
casualty forecast.
"""
import numpy as np
import geopandas as gpd
from scoring import build

KSI_EXPONENT = 3.0          # killed-and-seriously-injured (Elvik 2009; fatal alone ~4)

# AUDIT-P1 (2026-08-28): this was an if/elif/else cascade, so each segment could carry
# only one label. The three conditions are not alternatives - 1,271 Thai segments satisfy
# all three at once - and because has_school_market is true on 94% of Thailand's flagged
# segments the last branch absorbed 93.6% of them. The result was that "re-set the limit"
# appeared on 4 of 2,785 Thai segments, in a study whose subject is whether the posted
# limit is right, and on all 2,785 of which it is above the survivable speed. The three
# are now reported together; cost is the most demanding action that applies.
#
# Each test reads only published attributes, so a reader can rebuild this column from the
# layer: A from limit_gap_kmh > 0, B from speed_p85 > speed_limit, C from school_market.
ACTIONS = [
    # (flag name, cost tier, phrase). Phrases are lowercase and joined with " + ";
    # the first letter of the finished label is capitalised, so every combination
    # reads as a sentence fragment on its own.
    ("limit",   1, "lower the limit"),
    ("enforce", 2, "enforcement"),
    ("protect", 4, "protection for people on foot"),
]

def diagnose(row):
    applies = [
        row["speed_limit"] > row["safe_threshold"],      # the sign itself permits an unsurvivable speed
        row["p85"] > row["speed_limit"],                 # nobody is keeping to the sign
        bool(row["has_school_market"]),                  # people on foot make the consequence worse
    ]
    parts = [a for a, ok in zip(ACTIONS, applies) if ok]
    if not parts:                                        # not observed in either region; kept explicit
        return 2, "Review: flagged on exposure alone"
    label = " + ".join(p[2] for p in parts)
    return max(p[1] for p in parts), label[0].upper() + label[1:]

def main():
    g = build()
    hi = g[g["tier"].isin(["Priority 1", "Priority 2"])].copy()

    v_before = hi["p85"].clip(lower=1)
    v_after = np.minimum(hi["safe_threshold"], hi["p85"])     # only ever a reduction
    hi["ksi_reduction"] = 1 - (v_after / v_before) ** KSI_EXPONENT   # avoidable KSI fraction

    # exposure proxy: traffic percentile (share of travel) x segment length (km)
    tp = hi["traffic_pct"].fillna(hi["traffic_pct"].median()) / 100.0
    hi["exposure"] = tp * (hi["length_m"] / 1000.0)
    hi["benefit"] = hi["ksi_reduction"] * hi["exposure"]            # relative safety benefit

    tiers = hi.apply(diagnose, axis=1)
    hi["cost"] = [t[0] for t in tiers]
    hi["intervention"] = [t[1] for t in tiers]
    hi["bc_ratio"] = hi["benefit"] / hi["cost"]

    # normalise benefit to a readable 0-100 "priority points" within the set
    hi["bc_score"] = 100 * hi["bc_ratio"] / hi["bc_ratio"].max()

    print(f"High-priority segments costed: {len(hi):,}")
    print(f"\nMean avoidable-KSI fraction (if brought to safe speed): {hi['ksi_reduction'].mean():.0%}")
    print("\n--- Intervention mix (how the fix breaks down) ---")
    print(hi["intervention"].value_counts().to_string())
    print("\n--- Where the safety benefit concentrates (top 20% of segments hold what share of benefit) ---")
    s = hi["benefit"].sort_values(ascending=False)
    top20 = s.head(int(len(s) * 0.2)).sum() / s.sum()
    print(f"  Top 20% of segments by benefit hold {top20:.0%} of total avoidable-KSI potential")
    print("\n--- Top 10 best-return interventions (benefit / cost) ---")
    cols = ["region", "name", "road_class", "speed_limit", "p85", "safe_threshold",
            "ksi_reduction", "intervention", "bc_score"]
    top = hi.sort_values("bc_ratio", ascending=False).head(10)
    for _, r in top.iterrows():
        print(f"  [{r['region']}] {str(r['name'])[:22]:22} limit{r['speed_limit']:.0f} P85 {r['p85']:.0f} "
              f"-> safe {r['safe_threshold']:.0f} | KSI-{r['ksi_reduction']:.0%} | {r['intervention'][:28]} | pts {r['bc_score']:.0f}")

    keep = ["seg_id", "region", "name", "road_class", "land_use", "speed_limit", "p85",
            "safe_threshold", "severity", "ped_fatality_pct", "governance_flag", "street_link",
            "ksi_reduction", "exposure", "benefit", "cost", "intervention", "bc_score", "geometry"]
    out = gpd.GeoDataFrame(hi[keep], geometry="geometry", crs=4326)
    out.to_file("output/intervention_priorities.geojson", driver="GeoJSON")
    print("\nWrote output/intervention_priorities.geojson")

if __name__ == "__main__":
    main()

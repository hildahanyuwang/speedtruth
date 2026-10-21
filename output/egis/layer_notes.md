# Layer notes for the ArcGIS Online item description and popup

Paste these into the hosted layer's description. They carry the evidence
caveats that are deliberately NOT repeated into every feature.

The first three go on the SEGMENT layers. The fourth goes on the CORRIDOR
layers, which are the only ones carrying a benefit index.

## Street imagery (1 image)

The survivable speed for this segment was adjusted using ONE street-level image, classified by a declared vision model and validated by a blind test against human rating. One image per segment supports the DIRECTION of the adjustment, not its precision. Reference road-assessment systems inspect imagery at 100 m intervals or finer. Treat imagery-adjusted segments as candidates for inspection, not as verified road-condition measurements.

## Rule-based (no imagery)

No street imagery was available for this segment, so the survivable speed comes from the rule-based method (road class, setting, and presence of vulnerable road user generators). It has not been checked against what the road actually looks like.

## Score composition

Speed Safety Score = 0.45 x oper_excess + 0.35 x limit_excess + 0.20 x vru_exposure, each factor normalised within its own country/state and scaled to 0-100. The three `Score from:` fields are those weighted contributions and sum to the score, so any segment's rank can be traced to its causes.

## What the benefit index sums (corridor layers)

The benefit index is the sum, over the flagged segments in this unit, of the avoidable killed-and-seriously-injured fraction multiplied by an exposure proxy. The avoidable fraction follows the Nilsson power model with an exponent of 3.0 (Elvik 2009), comparing the observed 85th-percentile speed with the survivable speed for that segment; it is never negative. The exposure proxy is the segment's traffic percentile multiplied by its length in kilometres. The index therefore has no units and is only meaningful against other units in the same country or state.

Only flagged segments count: those in the Watch and Lower priority tiers contribute nothing. A unit appears here because it contains Priority 1 or Priority 2 segments, which is a ranking within its own country or state, and NOT because it contains segments at Critical severity, which is an absolute Safe System measure. The two are different axes and a unit can score on one without scoring on the other. In Maharashtra 611 of the 813 units contain no Critical segment at all, and those units still carry 47.5% of the state's total benefit index. The count of Critical segments is published for every unit, so a reader who wants only the units containing them can filter on it.

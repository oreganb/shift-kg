# Rule and CQ latency: Apache Jena Fuseki vs rdflib

Engine: **Apache Jena Fuseki 6.1.0 (in-memory dataset, no reasoner)**, OpenJDK 23 (Homebrew). 7 repeats, median reported. client-side wall clock over HTTP, including result serialisation; median of repeats.

The rdfs:subClassOf type closure is materialised client-side and uploaded, matching what `eval/run_rules.py` does in-process, so this compares query execution rather than inference strategy.

## Per scale

| Scale | Actors | ABox triples | Loaded (with TBox + closure) | Upload ms | 13 rules, median ms | 26 CQs, median ms | Inferred |
|---|--:|--:|--:|--:|--:|--:|--:|
| aran | 26 | 11607 | 14728 | 102 | 56.4 | 190.6 | 657 |
| s100 | 100 | 28772 | 33824 | 215 | 72.0 | 559.8 | 1428 |
| s250 | 250 | 50195 | 59677 | 430 | 114.2 | 1158.8 | 1956 |
| s500 | 500 | 84836 | 101594 | 670 | 150.4 | 2213.6 | 2726 |

## Against the rdflib baseline (13 rules)

rdflib figures are `shift-kg/eval/scaling.json`. Its triple counts predate the v1.0 ABox enrichment, so they differ slightly from the current graphs; the enrichment was designed not to change rule output, and the inferred counts below confirm it.

| Scale | rdflib rule total ms | Fuseki rule total ms | Fuseki faster by | rdflib inferred | Fuseki inferred | Agree |
|---|--:|--:|--:|--:|--:|:--:|
| aran | 508.9 | 56.4 | 9.0× | 657 | 657 | ✓ |
| s100 | 1590.0 | 72.0 | 22.1× | 1428 | 1428 | ✓ |
| s250 | 6214.8 | 114.2 | 54.4× | 1956 | 1956 | ✓ |
| s500 | 18873.0 | 150.4 | 125.4× | 2726 | 2726 | ✓ |

**Both engines infer exactly the same triples at every scale.** That is a cross-engine check on the rules themselves, independent of the generator's oracle.

## Scaling exponents

Least-squares slope of log(time) on log(size).

| Fit | Exponent vs triples | R² | Exponent vs actors | R² |
|---|--:|--:|--:|--:|
| Fuseki rule_total | 0.508 | 0.951 | 0.339 | 0.9536 |
| Fuseki cq_total | 1.236 | 0.9996 | 0.823 | 0.999 |
| Fuseki combined_total | 1.139 | 0.998 | 0.758 | 0.9972 |
| rdflib rule total (baseline) | 1.832 | — | 1.219 | — |

The rule-total exponent is not a complexity estimate. Across the four scales Fuseki's 13 rule queries cost 4.33, 5.54, 8.78, 11.57 ms each, so rule time carries a large fixed per-request component (HTTP round trip plus result serialisation) alongside the data-dependent work. The cq_total fit (R2 0.9996) is the one that mostly reflects data-dependent cost, and a single query dominates it: CQ-25 costs 1992 of the 2214 ms CQ total at s500, because of its nested aggregation. Timings are medians of 3 runs after a discarded warmup; without the warmup the same measurement drifts materially on a cold JVM.


The rule-total exponent is sensitive to repeat count, because the 13 rule queries are individually cheap and the total carries a large fixed per-request component. At 3 repeats it varied across runs (0.248 / 0.598 / 0.315, R2 0.55-0.97). At 7 repeats it settles with R2 > 0.99. Quote the 7-repeat figures; the 3-repeat run is not reliable for this measure. The CQ-total and combined fits were stable at both repeat counts.


CQ VALUES defaults are calibrated to the aran graph clock (EPOCH+7d). At s100/s250/s500 (14 days) the clock literal is rescaled. Individual-scoped defaults (e.g. service/S000) are aran-specific, so CQ row counts at larger scales are indicative, not validated against gold; gold validation is done by run_cqs.py at aran scale.


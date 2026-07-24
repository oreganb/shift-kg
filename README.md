# SHIFT Knowledge Graph v1.0.0

An executable knowledge graph for the SHIFT Ontology (Semantic Hierarchy for
Intelligent Flexibility & Trading), with a reproducible instance generator, a
SPARQL rule set, and an evaluation harness.

**All instance data in this release is synthetic.** Nothing here is measured, and
nothing here records a deployment. See [Honest limitations](#honest-limitations).

- Ontology namespace: **<https://w3id.org/shift>** (`shift-core` and `shift-ext`
  resolve under `https://w3id.org/shift/core#` and `.../ext#`)
- Ontology documentation and website: **[oreganb/shift](https://github.com/oreganb/shift)**
- This repository: the citable **artefact** — TBox, ABox, rules, evaluation
  harness, competency questions and benchmark results.

---

## What this adds to the prior SHIFT artefacts

Before v0.1.0, SHIFT consisted of a TBox and a set of rule descriptions. It had
no ABox, so it was an ontology but not a knowledge graph, and none of its rules
could be evaluated. Three things blocked execution:

1. **No instances.** 43 classes, 109 object properties, 245 datatype properties,
   **0 individuals**.
2. **No executable rules.** The 35 `SHIFT-RR-*.owl` files are `owl:Axiom`
   annotation stubs carrying rule conditions as prose string literals. There is
   no SWRL anywhere in the repository.
3. **Undeclared vocabulary.** 101 of the 134 terms used in the rule bodies were
   never declared in the TBox, including `ownsAsset` and `assetFunction`.

This release addresses all three, and reports what happened when the rules were
run for the first time.

## Contents

```
ontology/shift-core.ttl      normalised TBox: proper owl:Ontology header, version
                             IRI, licence, provenance. Two dangling class refs
                             (GridService, FlexibilityProduct) repaired.
ontology/shift-ext.ttl       100 terms required by the rules and previously
                             undeclared. Every term carries a skos:note naming
                             the rule that requires it.
generator/build_tbox.py      rebuilds the two files above from the legacy RDF/XML.
generator/generate_abox.py   parametrised, seeded synthetic ABox generator.
rules/sparql/*.rq            13 rules as executable SPARQL CONSTRUCT.
eval/run_rules.py            executes, times, and scores the rules.
eval/report_*.json           per-rule results at each scale.
eval/scaling.json            the scaling fit.
docs/RULES.md                expressibility analysis. Read this one.
kg/shift-kg-*.ttl            four generated graphs (26 to 500 actors).
eval/verify.py               seven adversarial release checks (V1-V5, V7).

cq/                          26 competency questions, locked, + SPARQL per CQ in
                             SHIFT, SAREF, SAREF+ext and SEAS vocabulary.
comparison/                  mapped test graphs for the four-way comparison.
                             Instance data only -- these reference SAREF/SEAS
                             IRIs, they do not copy those ontologies.
results/                     cq_shift.json, cq_matrix.{csv,md,json},
                             rules_shift.json, mapping_effort.json,
                             fuseki_scaling.{json,md}
scripts/                     the evaluation harness (see Reproducing).
external/PROVENANCE.md       what the external ontologies were, and where from.
```

**External ontologies are not redistributed here.** SAREF is ETSI-published under
its own licence terms; the SEAS copies are omitted for the same reason and for
simplicity. `external/PROVENANCE.md` records every source URI with the triple,
class and property counts the published results were computed against, and
`scripts/fetch_external.py` + `scripts/fetch_seas_closure.py` retrieve them and
report any drift from those counts.

## Reproducing

```bash
pip install rdflib
python3 generator/build_tbox.py
python3 generator/generate_abox.py --actors 26 --days 7 --seed 42 \
        --out kg/shift-kg-aran.ttl
python3 eval/run_rules.py --kg kg/shift-kg-aran.ttl --repeats 3
```

The generator is seeded. Same seed, same graph, bit for bit. `build_tbox.py`
needs the legacy RDF/XML artefacts, which are not part of this release; point
`$SHIFT_LEGACY_SRC` at them, or skip that step and use the shipped
`ontology/*.ttl`. Two consecutive TBox builds are byte-identical.

To reproduce the evaluation layer as well:

```bash
python3 eval/verify.py                      # seven release checks, exits non-zero on any issue
python3 scripts/run_cqs.py                  # results/cq_shift.json  (22/22 graded + 4/4 group F)
python3 scripts/fetch_external.py           # SAREF + SEAS, not redistributed here
python3 scripts/fetch_seas_closure.py       # the 40-module SEAS closure
python3 scripts/build_comparison_graphs.py  # comparison/*.ttl
python3 scripts/run_comparison.py           # results/cq_matrix.{csv,md,json}
python3 scripts/run_fuseki.py               # results/fuseki_scaling.{json,md}
```

Only the last four need the external ontologies; `verify.py` and `run_cqs.py`
run against this repository alone.

## Results

### Rule correctness

The generator computes ground truth in plain Python from the same parameters that
drive generation, and writes it to a sidecar JSON. The rule engine never sees it.
All 13 implemented rules reproduce the oracle exactly at every scale
(macro-F1 = 1.000, 0 false positives, 0 false negatives).

**This number is a regression test, not a scientific result.** The rules and the
oracle encode the same intent, so agreement shows the SPARQL is a faithful
transcription of the pseudocode. It says nothing about whether the rules are
*useful*, and it must not be reported in the paper as validation of SHIFT.

### Rule evaluation latency

| actors | ABox triples | rules | end-to-end | of a 30-min window |
|---:|---:|---:|---:|---:|
| 26 | 11,537 | 0.51 s | **1.17 s** | 0.07% |
| 100 | 28,628 | 1.59 s | **3.17 s** | 0.18% |
| 250 | 49,901 | 6.21 s | **9.31 s** | 0.52% |
| 500 | 84,292 | 18.87 s | **24.29 s** | 1.35% |

(v1.0.0 numbers, measured against the repaired TBox; per-scale detail incl.
load and closure time in `eval/report_*.json`.)

Rule time scales as **triples^1.83** (log-log fit, R² = 0.977), i.e. clearly
superlinear. Extrapolating on actor count (t ~ actors^1.23): ~730 s at 10,000
actors, or 40% of a 30-minute trade window. SHIFT's reasoning loop therefore
fits its stated window at community and district scale on this stack, with
headroom shrinking well before national scale.

Caveat that must travel with these numbers: **rdflib is an in-memory reference
implementation, not a production triplestore.** These are an upper bound on
latency and a lower bound on achievable scale. The same measurement on GraphDB,
Stardog or Virtuoso would very likely be an order of magnitude faster and should
be run before publication.

### Two findings worth more than the timings

**One rule dominated, and it was a query-plan artefact.** The direct transcription
of RR-03's pseudocode cost 148 ms at 26 actors, 8.9 s at 100, and 147 s at 250 —
roughly cubic. It builds the cross product of every asset pair per actor before
filtering on type. Rewritten with existential subqueries, semantics unchanged and
output identical, it drops to 41 ms at 26 actors and 7.1 s at 500. The naive form
is kept at `rules/sparql/_rr03_naive.rq.txt`. **The rule text, not the graph size,
was the scaling limit.**

**SHIFT's own data typing silently broke SHIFT's own rules.** Four of the 13 rules
initially fired zero times. The ABox types every string as `xsd:string`; the rule
bodies used untyped literals. Under RDF 1.1 a simple literal *is* `xsd:string`,
but triple-pattern matching and the `IN` operator use term equality, so
`shift:tradeStatus "Pending"` matched nothing — and raised no error. A rule that
silently matches nothing is worse than one that crashes. This is precisely the
class of defect the SHIFT paper says SHIFT exists to prevent, occurring inside
SHIFT.

## Verification (v1.0.0)

`eval/verify.py` runs seven checks; all pass on this release:

- **V1 vocabulary closure** — every class and predicate used in the ABox is
  declared in the TBox.
- **V2/V2b domain and range integrity** — no property carries conflicting
  `rdfs:domain` or `rdfs:range` declarations. v0.1.0 had **46 such defects**:
  39 multi-domain and 7 multi-range properties, of which 43 were inherited from
  the legacy artefacts and **3 were introduced by v0.1.0's own extension module**
  (`isActive`, `lastAuditDate`, `hasMember` collided with core declarations).
  Multiple domains/ranges are an intersection in OWL, so e.g. `validatedBy`
  implied its object was simultaneously a SmartMeterAsset and a
  FlexibilityServiceProvider. All 46 repaired with `owl:unionOf` expressions;
  each repaired property carries a `skos:note`. The ext collisions were resolved
  by renaming (`lastAuditDate`→`complianceAuditDate`, `hasMember`→
  `hasBundleMember`) and by widening `isActive`'s domain to
  `Actor ∪ FlexibilityService`.
- **V3 datatype conformance** — every typed literal matches its declared range.
- **V4 reproducibility** — regenerating with the same seed yields an isomorphic
  graph and identical ground truth.
- **V5 oracle soundness** — the ground-truth oracle omits the 30/90-day window
  filters that RR-28/RR-17 apply; verified harmless for the shipped parameters
  (oldest events fall inside both windows) and flagged as fragile.
- **V7 release version consistency** — the `version` in `CITATION.cff`, the
  `owl:versionInfo` of both TBox modules and their `owl:versionIRI` path
  segments all agree. Added after v0.1.1 shipped with its TTL stamps left at
  `0.1.0` while `CITATION.cff` and this README said `0.1.1`; the check exists so
  that drift cannot recur silently. (There is no V6: the docstring reserved one
  for re-running the shipped eval reports, which is not implemented.)

Rule output after the repair is **identical at every scale** (657 / 1,428 /
1,956 / 2,726 inferred triples), confirming the repair is semantics-preserving
for the implemented rule set: the closure used by the runner materialises
subclass types only, not domain/range inference. A reasoner that does
domain/range inference would have produced wrong types from v0.1.0. That is the
point of the repair.

## Honest limitations

- **Synthetic data.** No measured data. The graph is generated, not observed. Any
  claim about real energy outcomes is unsupported by this artefact.
- **F1 = 1.000 is circular** and is reported only as a regression check. See above.
- **13 of 35 rules implemented.** The other 22 are not executable. The
  expressibility verdicts for those 22 in `eval/swrl_expressibility.json` are
  keyword-derived and unverified.
- **Monotonicity unresolved.** Four rules overwrite a status property; RDF cannot
  overwrite, so the trade ends up with two statuses. `docs/RULES.md` §3 sets out
  the three options. None is implemented.
- **Rule interaction untested.** Rules run independently. No stratification, no
  fixpoint, no confluence testing. Rules that match the same trade will conflict.
- **No external alignment.** The claim that SHIFT "extends CIM, SAREF, SEAS and
  OpenADR" remains prose. There is still no `owl:imports`, no
  `owl:equivalentClass`, and no SKOS mapping to any external vocabulary. An
  alignment module is the obvious next artefact and is **not** in this release.
- **No competency questions.** The comparison against SAREF/SEAS/CIM that the
  paper needs is not here.
- **Single reasoner, single machine.** No cross-store comparison.

## Citing

See `CITATION.cff`. Cite the Zenodo DOI for the version you used, not the concept
DOI, so the numbers above resolve to the code that produced them.

## Licence

Ontology, graph and rules: CC BY 4.0. Code: Apache 2.0. See `LICENSE`.

Funded under the CET Partnership Joint Call 2023, ref Cetp-FP2023-00114,
co-funded by the European Commission (GA No. 101069750) and national funding
organisations including SEAI (Ireland).

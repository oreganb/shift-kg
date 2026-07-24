# SHIFT Reasoning Rules — expressibility and execution

## 1. What the rules were, before this release

The published SHIFT paper states that reasoning is "expressed in SWRL" and that
SWRL rules execute "during each Trade Window". The artefacts do not support that
statement. What exists in `Reasoning Rules/*.owl` is 35 files of this shape:

```xml
<rdf:Description rdf:about="http://shift-ontology.org/core#SHIFT-RR-00">
  <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Axiom"/>
  <rdfs:label>SHIFT-RR-00: Infer Flexumer from Asset Ownership</rdfs:label>
  <shift:condition1>ownsAsset(?a, ?cAsset) ∧ assetFunction(?cAsset, 'consumption')</shift:condition1>
  <shift:result>rdf:type(?a, Flexumer)</shift:result>
</rdf:Description>
```

The conditions are **string literals**. There is no `swrl:Imp`, no `swrl:body`,
no `swrl:head`, no rule atom anywhere in the repository. `grep -ril swrl` across
all 216 files matches exactly one: a PDF. No reasoner can execute any of this.
The internal documentation is more careful than the paper: it labels these
blocks "SWRL-Like Pseudocode", which is accurate.

A second, independent blocker: **101 of the 134 distinct terms** used across the
35 rule bodies were never declared in the TBox. `ownsAsset` and `assetFunction`
— the two predicates in RR-00, the simplest rule — were among them. Even a
correct SWRL serialisation would have bound nothing.

## 2. Whether the rules *could* be SWRL

They were converted here to SPARQL rather than SWRL. That was not a convenience
choice. Roughly a third of the rule set is outside SWRL's expressive power, and
no serialisation effort changes that:

| blocker | why SWRL cannot do it | rules affected |
|---|---|---|
| aggregation | SWRL has no `COUNT`/`SUM`/`AVG` | RR-01, RR-14, RR-15, RR-17, RR-19, RR-28, RR-31 |
| ratio of two aggregates | as above, twice | RR-28, RR-32 |
| negation as failure | SWRL is monotonic; "owns no battery" is not expressible under the open-world assumption | RR-21, RR-22, RR-08 |
| `now()` | no temporal built-in; the host must inject the evaluation instant | RR-04, RR-06, RR-09, RR-12, RR-17, RR-25, RR-26 |
| individual creation | SWRL cannot mint new individuals (RR-34 creates a `FlexibilityBundle`) | RR-34 |
| inequality | needs `owl:differentFrom` or a unique-name assumption, neither of which the ABox asserts | RR-01, RR-11, RR-13, RR-27 |

Hand-verified verdicts for the 13 rules implemented in this release:

| rule | SWRL | note |
|---|---|---|
| RR-00 | YES | plain conjunction |
| RR-01 | NO | `COUNT(DISTINCT ?t) >= 3`. The docs work around this by writing `?t1,?t2,?t3` with pairwise `≠`, which tests exactly 3 and does not generalise to *n* |
| RR-02 | YES | `swrlb:greaterThan` / `lessThan` |
| RR-03 | YES | |
| RR-04 | PARTIAL | needs `now()` from the host |
| RR-09 | PARTIAL | needs `now()` |
| RR-16 | YES | |
| RR-17 | NO | count + temporal window |
| RR-21 | NO | negation as failure |
| RR-23 | YES | |
| RR-27 | PARTIAL | needs `owl:differentFrom` on CMC individuals |
| RR-28 | NO | ratio of two aggregates |
| RR-29 | YES | |

Verdicts for the remaining 22 rules in `eval/swrl_expressibility.json` are
**keyword-derived and not hand-verified**. They should not be quoted as a result
until each is implemented and checked. The classifier is known to be wrong on at
least RR-00 and RR-27, which is why the 13 above are overridden by hand.

**The defensible claim** is therefore not "SHIFT uses SWRL". It is: *SHIFT's rule
set was specified in a SWRL-like pseudocode, approximately a third of which lies
outside SWRL's expressive power; it is executed here as SPARQL CONSTRUCT, with
the evaluation instant injected by the host.* That is a more interesting finding
than the original claim, and it generalises: any flexibility ontology whose rules
count events, compute ratios, or reason about absence will hit the same wall.

## 3. Monotonicity problem (unresolved)

RR-04, RR-09, RR-16 and RR-27 all **overwrite** a status: `tradeStatus` goes from
`"Pending"` to `"Expired"`. RDF has no overwrite. A `CONSTRUCT` that asserts
`"Expired"` leaves `"Pending"` in place, and the trade now has two statuses. The
rules as specified assume an update semantics that the formalism does not have.

Three ways out, none of them free:

1. **SPARQL UPDATE** (`DELETE`/`INSERT`) rather than `CONSTRUCT`. Executable, but
   destroys the audit trail the paper claims as a benefit, and makes rule order
   significant.
2. **Reified status with validity intervals** — `StatusAssertion` with
   `validFrom`/`validUntil`. Preserves auditability, costs a large TBox change
   and roughly doubles triple count.
3. **Named graphs per trade window** — inferences land in a per-window graph,
   base facts stay immutable. Cheapest, fits the 30-minute window model, and is
   the recommended option.

This release does option 0: it constructs into a separate result set and does not
merge. **The choice has to be made before the ontology can be called operational,
and it must be made in the paper, not deferred.**

## 4. Rule interaction (untested)

Rules are evaluated independently here. In a real reasoning loop they interact:
RR-16 approves a trade, RR-04 may expire it, RR-27 may block it, and all three
match the same trade. There is no stratification, no fixpoint, no priority order.
Confluence has not been tested. This is a known gap.

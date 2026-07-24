# SHIFT Competency Questions — v1.0 LOCKED (24 Jul 2026)

Reviewed by Brian O'Regan (practitioner-validity pass, 24 Jul). Verdict: 22-24
of 26 immediately authentic; wording and threshold parameterisation applied
below per that review.

26 competency questions (CQs) derived from the conference paper's claims and
the SHIFT-RR rule intents. Each CQ will be expressed as SPARQL and evaluated
against SHIFT, SAREF Core v4.1.1 and SEAS; the paper reports the
answerable / partial / not-expressible matrix with the blocking term named for
every failure. Review pass needed from Brian: domain validity, missing
concerns, anything a reviewer would consider cherry-picked.

Design rule: the set must contain questions SHIFT is expected to LOSE
(CQ-21 to CQ-24), otherwise the comparison reads as self-serving.

## A. Actors and roles
- CQ-01 Which actors both consume and produce or store electricity? (RR-00 basis)
- CQ-02 Which actors are regular sellers (repeated confirmed sales in a period)? (RR-01; count parameterised)
- CQ-03 What market role does a given actor hold, and in which region?
- CQ-04 Which actors belong to the same community/trust group as actor X? (CMC)
- CQ-05 Which aggregators currently satisfy the platform's participation requirements? (RR-14; the individual criteria are query parameters, see note 6)

## B. Assets and flexibility
- CQ-06 Which controllable assets at node N can respond within T milliseconds?
- CQ-07 Which assets of actor X are storage-capable and currently available?
- CQ-08 Which assets show an unacceptable activation failure rate over recent activations? (RR-28; threshold parameterised)
- CQ-09 Which buildings host a heat pump but no battery? (RR-21 shape)

## C. Services, contracts, obligations
- CQ-10 Which flexibility services are active at node N and what capacity is committed in window W? (RR-19)
- CQ-11 Which services are persistently under-delivering against commitments? (RR-17; delivery ratio, count and window parameterised)
- CQ-12 Which contracts end before date D, and which services do they govern? (RR-09/12)
- CQ-13 What penalty rate applies to a given trade via its contract?

## D. Trading and market operations
- CQ-14 Which pending trades in window W are between mutually trusted same-community parties? (RR-16)
- CQ-15 Which trades crossed community boundaries without consent? (RR-27)
- CQ-16 Which trades were still pending/in-progress after their delivery window closed? (RR-04)
- CQ-17 What total energy volume cleared per trade window across a day?

## E. Tariffs, pricing, forecasts
- CQ-18 Which actors on a flat tariff exceed the consumption threshold for a dynamic plan? (RR-20)
- CQ-19 Which tariff plans carry contradictory pricing attributes? (RR-23)
- CQ-20 Which nodes have forecasted load exceeding current DER capacity in the next window? (RR-05/02)

## F. Questions SHIFT is expected to fail or answer only partially
- CQ-21 What is the electrical topology path between two assets? (CIM territory; SHIFT has no conducting-equipment model)
- CQ-22 What sequence of device commands implements a curtailment instruction? (SAREF function/command territory)
- CQ-23 What was the observed time-series value of property P of device D at time T? (SAREF/SOSA observation territory; SHIFT stores last-capture attributes only)
- CQ-24 Which activities (forecasting, planning, optimisation) is actor X currently performing? (SEAS activity reification; SHIFT has no activity class)

## G. Added in self-review (v0.2)
- CQ-25 (group C/D) Which actors' share of trade opportunities deviates most from their community's mean? (RR-19 / FAIRNESS; retained solely because fairness is an explicit paper claim — flagged in review as the least operator-natural question)
- CQ-26 (group D) For a failed trade, which backup trade replaced it and with which seller? (RR-08; the paper's "backup sellers and clearing logic" claim)

## Method notes (for the paper)
1. One SPARQL query per CQ per ontology, written in that ontology's own
   vocabulary; a CQ counts as answerable only if the query returns the
   gold-standard result on a common test graph mapped into each vocabulary.
2. "Partial" = expressible only with vocabulary extension or host-side
   computation; the missing term is named in every case.
3. Test graph: the v1.0 synthetic KG (26-actor Aran-shaped instance), mapped
   into SAREF and SEAS terms where their vocabularies permit — the mapping
   effort per ontology is itself reported.
4. Disclosure: CQ-04, 05, 08, 11, 14, 15, 18, 19, 25 and 26 depend on
   vocabulary introduced in the v0.1.0 rule-vocabulary extension module (not
   present in the pre-v0.1.0 artefacts). The paper states this explicitly:
   the benchmark evaluates SHIFT as released at v1.0, and the extension is
   itself part of the contribution, not a benchmark-fitting exercise.
5. Thresholds are query parameters, not question content: each CQ's SPARQL
   takes its thresholds via VALUES/BIND with defaults drawn from the
   corresponding rule (e.g. 3 sales, 0.8 delivery ratio, 0.2 failure ratio,
   90-day window). Questions are phrased as an operator would ask them;
   tuning lives in the rule layer. (Applied after practitioner review, which
   flagged embedded thresholds as benchmark-flavoured.)
6. Expected headline (to be confirmed by the runs, not asserted before):
   SHIFT answers A-E and G, fails F; SAREF answers most of B and CQ-22/23,
   little of C-D; SEAS answers CQ-24 and parts of A, little of C-E. The
   published claim is complementary coverage, not superiority.

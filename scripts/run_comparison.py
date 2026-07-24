#!/usr/bin/env python3
"""
run_comparison.py -- score the 26 competency questions against SHIFT, SAREF
Core v4.1.1 and SEAS, and emit the paper's coverage matrix.

Verdicts (method note 2):
  ANSWERABLE      the query returns the gold answer, and every constraint in
                  the question is enforced by the query itself
  PARTIAL         answerable only with a vocabulary extension or host-side
                  computation; the missing term is named
  NOT-EXPRESSIBLE the concept the question turns on is absent; it is named

A verdict is an analytical claim about a vocabulary, so it is declared in
VERDICTS below and the run CONFIRMS it: every ANSWERABLE row must actually
return gold, and the script fails loudly if one does not. Row-matching alone is
not sufficient for ANSWERABLE -- a query can return the right rows while
leaving a constraint unenforced because the mapping, not the vocabulary,
supplied it. Those cases are marked PARTIAL and the reason is recorded in
`constraint_not_enforced`.

Usage:
    .venv/bin/python scripts/run_comparison.py
"""
import csv
import json
import pathlib
import time

from rdflib import Graph
from rdflib.namespace import RDF, RDFS

REPO = pathlib.Path(__file__).resolve().parent.parent
A, P, N = "ANSWERABLE", "PARTIAL", "NOT-EXPRESSIBLE"
SYM = {A: "✓", P: "~", N: "✗"}

# (verdict, blocker). Blocker is "" for ANSWERABLE.
VERDICTS = {
    "CQ-01": {
        "saref": (N, "No agent class. SAREF Core has no Actor, Person or Organisation, and no ownership property."),
        "seas":  (A, ""),
    },
    "CQ-02": {
        "saref": (N, "No agent class and no market-transaction class."),
        "seas":  (P, "seas:Selling/Trading/Transaction exist as classes but carry no properties: nothing links a transaction to its seller, its volume, its time or a confirmation status."),
    },
    "CQ-03": {
        "saref": (N, "No agent class, no role model, no region or location term in Core."),
        "seas":  (P, "seas:Role/hasRole and seas:Operator/Aggregator/EndUser give the market role, but no property associates an Actor with a region or zone (seas:location is a PropertyKey on FeatureOfInterest; seas:Actor is an AbstractEntity)."),
    },
    "CQ-04": {
        "saref": (N, "No agent class, no group or community class, no trust relation."),
        "seas":  (N, "No community or group class and no membership property for actors; seas:GroupManager exists but the group it manages does not. No trust relation."),
    },
    "CQ-05": {
        "saref": (N, "No agent or aggregator class."),
        "seas":  (P, "seas:Aggregator exists, but SEAS declares no compliance, trust or prequalification properties, so participation requirements cannot be tested."),
    },
    "CQ-06": {
        "saref": (P, "Controllability is expressible (saref:Actuator/Function/Command). Missing: a siting term for node N (saref4bldg:BuildingSpace is an extension) and any response-time property (s4ener territory)."),
        "seas":  (P, "Siting is expressible via seas:ConnectionPoint/Zone. Missing: any response-time property, and a device-level controllability flag (seas:ControlActivity describes the act, not the capability)."),
    },
    "CQ-07": {
        "saref": (N, "No agent class or ownership property, and no storage-capability term in Core."),
        "seas":  (P, "seas:owns plus seas:Battery/EnergyStorage give the storage-capable assets of an actor. Missing: availability -- the seas operating codelist carries ratings (op-Nominal, op-Min, op-Maximum-*), not an available/unavailable state."),
    },
    "CQ-08": {
        "saref": (P, "saref:CommandExecution with saref:hasTimestamp supplies the denominator. Missing: any outcome or status property on an execution, so failures cannot be counted."),
        "seas":  (P, "seas:Failure and seas:failure can mark a failed feature of interest. Missing: an activation-attempt event class, so the denominator of a failure ratio has no term."),
    },
    "CQ-09": {
        "saref": (N, "No building class in SAREF Core (saref4bldg:Building is an extension) and no heat-pump or battery device kinds in Core (s4ener/s4bldg)."),
        "seas":  (A, ""),
    },
    "CQ-10": {
        "saref": (N, "saref:Service exists but there is no siting term and no committed-capacity property."),
        "seas":  (P, "Committed capacity is expressible as a seas:Evaluation interpreted through the flexibility codelist. Missing: a service activity status and any service-to-node siting property."),
    },
    "CQ-11": {
        "saref": (N, "No model of a commitment against which delivery is measured."),
        "seas":  (P, "Committed and measured values are both expressible as evaluations. Missing: a delivery-event class binding the pair so the two can be compared per event."),
    },
    "CQ-12": {
        "saref": (N, "No contract class."),
        "seas":  (P, "seas:Contract exists and seas:player links it to an actor. Missing: a contract end-date property and any contract-governs-service relation."),
    },
    "CQ-13": {
        "saref": (N, "No contract class, no trade class, no penalty term."),
        "seas":  (P, "seas:Contract exists. Missing: a trade-to-contract association and any penalty-rate property."),
    },
    "CQ-14": {
        "saref": (N, "No trade class, no community, no trust relation."),
        "seas":  (N, "No trade class carrying its parties, no community class, no trust relation."),
    },
    "CQ-15": {
        "saref": (N, "No trade class, no community, no consent term."),
        "seas":  (N, "No trade class carrying its parties, no community class, no consent term."),
    },
    "CQ-16": {
        "saref": (N, "No trade class and no delivery window."),
        "seas":  (N, "seas:Transaction has no status property and there is no delivery-window term."),
    },
    "CQ-17": {
        "saref": (N, "No trade class and no market clearing window."),
        "seas":  (P, "seas:Transaction, seas:Clearing and seas:Market give the market frame. Missing: a traded-volume property and any window-to-transaction link."),
    },
    "CQ-18": {
        "saref": (N, "No agent class; saref:Profile carries a price via profileHasPrice but no tariff structure."),
        "seas":  (P, "seas:Price/PricePerEnergy/BasePrice and seas:Profile express a tariff price. Missing: flat-versus-dynamic structural flags, and an actor-level consumption property (nominalEnergyConsumption is on systems)."),
    },
    "CQ-19": {
        "saref": (N, "No tariff-structure flags, so there is nothing that can contradict."),
        "seas":  (N, "No tariff-structure flags, so there is nothing that can contradict."),
    },
    "CQ-20": {
        "saref": (N, "No forecast class, no node, no DER-capacity property."),
        "seas":  (P, "seas:NetworkNode/ElectricPowerSystem give the node and SEAS has forecasting classes. Missing: forecasting is weather-specific (WeatherForecast, WeatherForecasting) with no load-forecast value bound to a node, and no DER-capacity property."),
    },
    "CQ-21": {
        "saref": (N, "No electrical connectivity model; saref:consistsOf is mereological composition, not connection."),
        "seas":  (A, ""),
    },
    "CQ-22": {
        "saref": (P, "saref:Function/Command/hasCommand return the commands. Missing: any ordering, step or successor property, so the sequence the question asks for cannot be expressed."),
        "seas":  (P, "seas:ControlActivity/ActuatingActivity/OnOffActivity express the control act. Missing: a Command class for the individual instruction and any ordering property."),
    },
    "CQ-23": {
        "saref": (A, ""),
        "seas":  (A, ""),
    },
    "CQ-24": {
        "saref": (N, "No agent class and no activity taxonomy."),
        "seas":  (P, "SEAS is the only one of the three with the activity taxonomy (seas:Activity, ForecastingActivity, PlanningActivity, OptimizationActivity). Missing: any agency property -- no property has domain seas:Actor or range seas:Activity, so the link can only be the untyped transitive seas:contains -- and no way to say 'currently', since seas:temporalContext has domain TimeContextualizedEvaluation."),
    },
    "CQ-25": {
        "saref": (N, "No agent class, no community, no trade class."),
        "seas":  (N, "No trade class carrying its parties, and no community class to average over."),
    },
    "CQ-26": {
        "saref": (N, "No trade class and no replacement relation."),
        "seas":  (N, "No trade class and no backup or replacement relation."),
    },
}

# SAREF Core + SAREF4ENER v2.1.1 + SAREF4BLDG v2.1.1, merged as one vocabulary.
# Only the deltas from Core are spelled out; everything else is Core's blocker,
# which the extensions do not touch.
NO_AGENT = ("Neither extension adds an agent class. s4ener:Role is a DEVICE role "
            "codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and "
            "s4ener:hasRole has domain saref:Device, so it cannot carry an actor.")
VERDICTS_EXT = {
    "CQ-01": (N, NO_AGENT + " No ownership property either."),
    "CQ-02": (N, NO_AGENT + " No market-transaction class."),
    "CQ-03": (N, NO_AGENT + " No region term."),
    "CQ-04": (N, NO_AGENT + " No community class and no trust relation."),
    "CQ-05": (N, NO_AGENT + " No aggregator class."),
    "CQ-06": (P, "s4ener:hasActivationDelay (xsd:duration, no declared domain) supplies the response-time constraint Core lacked. Still missing: a grid-node term -- s4bldg adds Building and BuildingSpace, which are spatial containers, not network nodes."),
    "CQ-07": (P, "s4ener:Storage and the RoleType individual EnergyStorage supply the storage capability Core lacked; availability comes from saref:hasState. Still missing: " + NO_AGENT),
    "CQ-08": (A, ""),
    "CQ-09": (P, "s4bldg:Building, s4bldg:contains and s4bldg:ElectricFlowStorageDevice make the building and the battery exact. Still missing: a heat-pump class -- NEITHER extension declares one (zero occurrences in both files); the nearest, s4bldg:EnergyConversionDevice, is far broader and also subsumes s4bldg:SolarDevice."),
    "CQ-10": (P, "s4ener:PowerLimit, PowerEnvelope and FlexOffer express a committed capacity, which Core could not. Still missing: a grid-node siting term and a service-activity status."),
    "CQ-11": (P, "s4ener power profiles express a commitment and Core observations express the measured value. Still missing: a delivery-event class binding a commitment to its measured outcome so the pair can be compared per event."),
    "CQ-12": (N, "s4ener:ContractualPowerLimit is a power limit, not a contract. No contract class, no end date, no governed-service relation."),
    "CQ-13": (N, "No contract class and no trade class, so no path from a trade to a penalty rate. s4ener has no penalty term."),
    "CQ-14": (N, NO_AGENT + " No trade class, no community, no trust relation."),
    "CQ-15": (N, NO_AGENT + " No trade class, no community, no consent term."),
    "CQ-16": (N, "s4ener:FlexOffer/FlexRequest describe offers, not concluded trades with a status and a delivery window."),
    "CQ-17": (P, "s4ener:FlexOffer/FlexRequest with hasEnergy and Slot timing express traded energy per slot. Still missing: a market-clearing-window class and any trade-to-window link."),
    "CQ-18": (N, NO_AGENT + " s4ener:Incentive and IncentiveTableTier give tariff structure, but with no actor there is no consumption to threshold."),
    "CQ-19": (P, "s4ener:IncentiveTableProfile, IncentiveTableTier and IncentiveType give real tariff structure, which Core lacked entirely. Still missing: flat-versus-dynamic flags, so there is still nothing that can contradict."),
    "CQ-20": (P, "s4ener:hasDemandRateForecast and hasUsageForecast supply the forecast Core lacked. Still missing: a grid-node term and any DER-capacity property."),
    "CQ-21": (N, "s4bldg:contains is spatial containment, not electrical connection. Neither extension adds a connectivity or conducting-equipment model."),
    "CQ-22": (A, ""),
    "CQ-23": (A, ""),
    "CQ-24": (N, NO_AGENT + " No activity taxonomy in either extension."),
    "CQ-25": (N, NO_AGENT + " No community class and no trade class."),
    "CQ-26": (N, "No trade class and no replacement or backup relation."),
}

# Where a query returns gold but the vocabulary did not enforce every
# constraint, record why the verdict stays PARTIAL.
CONSTRAINT_NOT_ENFORCED = {
    ("seas", "CQ-24"): "Rows match, but seas:contains asserts containment, not "
                       "performance, and 'currently' is unenforceable.",
    ("saref_ext", "CQ-09"): "Rows match, but s4bldg:EnergyConversionDevice is "
                            "broader than a heat pump and also subsumes "
                            "s4bldg:SolarDevice.",
}

ONTOLOGIES = ("shift", "saref", "saref_ext", "seas")
LABELS = {"shift": "SHIFT", "saref": "SAREF Core", "saref_ext": "SAREF Core+ext",
          "seas": "SEAS"}

GROUPS = {**{f"CQ-{i:02d}": g for i, g in
             [(1, "A"), (2, "A"), (3, "A"), (4, "A"), (5, "A"),
              (6, "B"), (7, "B"), (8, "B"), (9, "B"),
              (10, "C"), (11, "C"), (12, "C"), (13, "C"),
              (14, "D"), (15, "D"), (16, "D"), (17, "D"),
              (18, "E"), (19, "E"), (20, "E"),
              (21, "F"), (22, "F"), (23, "F"), (24, "F"),
              (25, "G"), (26, "G")]}}
GROUP_TITLES = {
    "A": "Actors and roles", "B": "Assets and flexibility",
    "C": "Services, contracts, obligations", "D": "Trading and market operations",
    "E": "Tariffs, pricing, forecasts", "F": "Expected losses for SHIFT",
    "G": "Added in self-review",
}


def norm(v):
    from decimal import Decimal
    from rdflib import URIRef
    import datetime as dt
    if v is None:
        return None
    if isinstance(v, URIRef):
        return ("str", str(v))
    if hasattr(v, "toPython"):
        v = v.toPython()
    if isinstance(v, bool):
        return ("bool", v)
    if isinstance(v, (int, float, Decimal)):
        return ("num", float(v))
    if isinstance(v, (dt.datetime, dt.date)):
        return ("str", v.isoformat())
    return ("str", str(v))


def key(row):
    return [(0, "", 0.0) if c is None else
            (1, "", round(c[1], 4)) if c[0] == "num" else
            (2, str(c[1]), 0.0) if c[0] == "bool" else (3, c[1], 0.0)
            for c in row]


def rows_equal(a, b):
    if len(a) != len(b):
        return False
    for ra, rb in zip(sorted(a, key=key), sorted(b, key=key)):
        if len(ra) != len(rb):
            return False
        for ca, cb in zip(ra, rb):
            if ca is None or cb is None:
                if ca is not cb:
                    return False
            elif ca[0] != cb[0]:
                return False
            elif ca[0] == "num":
                if abs(ca[1] - cb[1]) > 1e-4:
                    return False
            elif ca[1] != cb[1]:
                return False
    return True


def closure(g):
    changed, rounds = True, 0
    while changed and rounds < 10:
        changed, rounds = False, rounds + 1
        new = [(s, RDF.type, sup)
               for s, _, c in g.triples((None, RDF.type, None))
               for sup in g.objects(c, RDFS.subClassOf)
               if (s, RDF.type, sup) not in g]
        for t in new:
            g.add(t)
            changed = True
    return g


def load(paths):
    g = Graph()
    for p in paths:
        g.parse(str(p), format="turtle")
    return closure(g)


def main():
    gold = json.load(open(REPO / "shift-kg" / "kg" / "shift-kg-aran.cq_truth.json"))["cq_truth"]
    gold.update(json.load(open(REPO / "comparison" / "scenario_gold.json")))
    gold = {k: [[norm(c) for c in r] for r in v] for k, v in gold.items()}

    graphs = {
        "shift": load([REPO / "shift-kg" / "ontology" / "shift-core.ttl",
                       REPO / "shift-kg" / "ontology" / "shift-ext.ttl",
                       REPO / "shift-kg" / "kg" / "shift-kg-aran.ttl"]),
        "saref": load([REPO / "external" / "saref.ttl",
                       REPO / "comparison" / "saref-test.ttl"]),
        "saref_ext": load([REPO / "external" / "saref.ttl",
                           REPO / "external" / "saref4ener.ttl",
                           REPO / "external" / "saref4bldg.ttl",
                           REPO / "comparison" / "saref-ext-test.ttl"]),
        "seas": load(sorted((REPO / "external" / "seas-modules").glob("*.ttl"))
                     + [REPO / "comparison" / "seas-test.ttl"]),
    }
    qdirs = {"shift": REPO / "cq" / "shift", "saref": REPO / "cq" / "saref",
             "saref_ext": REPO / "cq" / "saref-ext", "seas": REPO / "cq" / "seas"}

    rows, failures = [], []
    for i in range(1, 27):
        cq = f"CQ-{i:02d}"
        rec = {"cq": cq, "group": GROUPS[cq]}
        for onto in ONTOLOGIES:
            if onto == "shift":
                verdict = A if GROUPS[cq] != "F" else N
                blocker = "" if verdict == A else "See cq/shift/%s.rq -- blocking term named in the query header." % f"cq{i:02d}"
            elif onto == "saref_ext":
                verdict, blocker = VERDICTS_EXT[cq]
            else:
                verdict, blocker = VERDICTS[cq][onto]

            qf = qdirs[onto] / f"cq{i:02d}.rq"
            n, matched, ms = None, None, None
            if qf.exists():
                t0 = time.perf_counter()
                res = [[norm(c) for c in r] for r in graphs[onto].query(qf.read_text())]
                ms = round((time.perf_counter() - t0) * 1000, 2)
                n = len(res)
                matched = rows_equal(res, gold.get(cq, []))

            if verdict == A and matched is not True:
                failures.append(f"{onto} {cq}: declared ANSWERABLE but "
                                f"{'no query file' if n is None else 'returned %d rows, gold %d' % (n, len(gold.get(cq, [])))}")

            rec[onto] = {
                "verdict": verdict, "blocker": blocker,
                "query": str(qf.relative_to(REPO)) if qf.exists() else "",
                "rows": n, "gold": len(gold.get(cq, [])), "matched": matched,
                "runtime_ms": ms,
                "constraint_not_enforced": CONSTRAINT_NOT_ENFORCED.get((onto, cq), ""),
            }
        rows.append(rec)

    # ---- CSV ----
    csv_path = REPO / "results" / "cq_matrix.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        head = ["cq", "group", "gold_rows"]
        for o in ONTOLOGIES:
            head += [f"{o}_verdict", f"{o}_blocker", f"{o}_rows",
                     f"{o}_matched", f"{o}_constraint_not_enforced"]
        w.writerow(head)
        for r in rows:
            line = [r["cq"], r["group"], r["shift"]["gold"]]
            for o in ONTOLOGIES:
                line += [r[o]["verdict"], r[o]["blocker"], r[o]["rows"],
                         r[o]["matched"], r[o]["constraint_not_enforced"]]
            w.writerow(line)

    json.dump(rows, open(REPO / "results" / "cq_matrix.json", "w"), indent=1)

    tally = {o: {v: sum(1 for r in rows if r[o]["verdict"] == v) for v in (A, P, N)}
             for o in ONTOLOGIES}
    write_markdown(rows, tally)

    print(f"{'CQ':7}{'grp':5}" + "".join(f"{LABELS[o]:16}" for o in ONTOLOGIES))
    print("-" * 76)
    for r in rows:
        print(f"{r['cq']:7}{r['group']:5}"
              + "".join(f"{SYM[r[o]['verdict']]:16}" for o in ONTOLOGIES))
    print("-" * 76)
    for o in ONTOLOGIES:
        print(f"{LABELS[o]:16} answerable {tally[o][A]:2}   partial {tally[o][P]:2}   "
              f"not-expressible {tally[o][N]:2}")
    if failures:
        print("\nFAILED CONFIRMATION:")
        for f in failures:
            print("  " + f)
        raise SystemExit(1)
    print("\nall ANSWERABLE verdicts confirmed against gold")
    print(f"wrote {csv_path.relative_to(REPO)}, results/cq_matrix.md")


def write_markdown(rows, tally):
    eff = json.load(open(REPO / "results" / "mapping_effort.json"))
    L = []
    L.append("# Competency-question coverage: SHIFT vs SAREF vs SEAS\n")
    L.append("Legend: **✓ ANSWERABLE** — returns the gold answer with every "
             "constraint enforced by the query. **~ PARTIAL** — needs a "
             "vocabulary extension or host-side computation; the missing term "
             "is named. **✗ NOT-EXPRESSIBLE** — the concept the question turns "
             "on is absent; it is named.\n")
    L.append(f"- **SHIFT** v1.0, `kg/shift-kg-aran.ttl` "
             f"({eff['source_triples']} triples)")
    L.append(f"- **SAREF Core** v4.1.1, `external/saref.ttl` — mapped graph "
             f"{eff['saref']['triples']} triples, "
             f"{eff['saref']['term_mapping_count']} term mappings, "
             f"{eff['saref']['not_representable_count']} recorded gaps")
    L.append(f"- **SAREF Core+ext** = Core v4.1.1 + SAREF4ENER v2.1.1 + "
             f"SAREF4BLDG v2.1.1, merged as one vocabulary — mapped graph "
             f"{eff['saref_ext']['triples']} triples, "
             f"{eff['saref_ext']['term_mapping_count']} term mappings, "
             f"{eff['saref_ext']['not_representable_count']} recorded gaps. "
             f"Both extensions version independently of Core and their latest "
             f"published version is v2.1.1, not v4.1.1.")
    L.append(f"- **SEAS** merged closure, 40 modules — mapped graph "
             f"{eff['seas']['triples']} triples, "
             f"{eff['seas']['term_mapping_count']} term mappings, "
             f"{eff['seas']['not_representable_count']} recorded gaps. "
             f"StatisticsVocabulary is excluded: it is truncated upstream "
             f"(see `external/PROVENANCE.md`).\n")
    L.append("All three graphs use the **same instance IRIs**, so a gold row is "
             "directly comparable across ontologies; only the vocabulary "
             "changes. Group F is scored against scenario facts SHIFT cannot "
             "represent (topology, command order, observation history, actor "
             "activities), not against SHIFT's empty result.\n")

    L.append("## Matrix\n")
    L.append("| CQ | Group | SHIFT | SAREF Core | SAREF Core+ext | SEAS |")
    L.append("|---|---|:--:|:--:|:--:|:--:|")
    cur = None
    for r in rows:
        if r["group"] != cur:
            cur = r["group"]
            L.append(f"| | **{cur} — {GROUP_TITLES[cur]}** | | | | |")
        L.append(f"| {r['cq']} | {r['group']} | "
                 + " | ".join(SYM[r[o]["verdict"]] for o in ONTOLOGIES) + " |")

    L.append("\n## Subtotals by group\n")
    L.append("| Group | n | SHIFT ✓/~/✗ | SAREF Core ✓/~/✗ | SAREF Core+ext ✓/~/✗ | SEAS ✓/~/✗ |")
    L.append("|---|--:|:--:|:--:|:--:|:--:|")
    for grp in "ABCDEFG":
        gr = [r for r in rows if r["group"] == grp]
        if not gr:
            continue
        cells = []
        for o in ONTOLOGIES:
            c = {v: sum(1 for r in gr if r[o]["verdict"] == v) for v in (A, P, N)}
            cells.append(f"{c[A]}/{c[P]}/{c[N]}")
        L.append(f"| {grp} — {GROUP_TITLES[grp]} | {len(gr)} | " + " | ".join(cells) + " |")
    L.append("| **Total** | **26** | " + " | ".join(
        f"**{tally[o][A]}/{tally[o][P]}/{tally[o][N]}**" for o in ONTOLOGIES) + " |")

    L.append("\n## Blocking terms\n")
    for onto, label in (("saref", "SAREF Core v4.1.1"),
                        ("saref_ext", "SAREF Core + 4ENER + 4BLDG"),
                        ("seas", "SEAS")):
        L.append(f"### {label}\n")
        L.append("| CQ | Verdict | Blocking term |")
        L.append("|---|:--:|---|")
        for r in rows:
            if r[onto]["verdict"] == A:
                continue
            note = r[onto]["blocker"]
            if r[onto]["constraint_not_enforced"]:
                note += " " + r[onto]["constraint_not_enforced"]
            L.append(f"| {r['cq']} | {SYM[r[onto]['verdict']]} | {note} |")
        L.append("")
    L.append("### SHIFT\n")
    L.append("| CQ | Verdict | Blocking term |")
    L.append("|---|:--:|---|")
    for r in rows:
        if r["shift"]["verdict"] == A:
            continue
        L.append(f"| {r['cq']} | {SYM[r['shift']['verdict']]} | "
                 f"{r['shift']['blocker']} |")

    L.append("\n## Mapping effort\n")
    for onto, label in (("saref", "SAREF Core v4.1.1"),
                        ("saref_ext", "SAREF Core + 4ENER + 4BLDG"),
                        ("seas", "SEAS")):
        L.append(f"**{label}** — {eff[onto]['term_mapping_count']} term "
                 f"mappings made:\n")
        for m in eff[onto]["term_mappings"]:
            L.append(f"- {m}")
        L.append(f"\n**{label}** — {eff[onto]['not_representable_count']} "
                 f"things the vocabulary could not represent:\n")
        for m in eff[onto]["not_representable"]:
            L.append(f"- {m}")
        L.append("")
    (REPO / "results" / "cq_matrix.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

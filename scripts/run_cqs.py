#!/usr/bin/env python3
"""
run_cqs.py -- run the 26 SHIFT competency questions against the aran KG and
score each against the generator's independently-computed gold answers.

The gold answers come from generate_abox.py's cq_oracle(), which is plain
Python over the generation registries. It never reads the RDF graph and never
reads the SPARQL. A disagreement between the two is therefore a real result.

Graph loading mirrors eval/run_rules.py exactly, including the rdfs:subClassOf
materialisation -- several CQs match on ?x a shift:Actor / shift:Asset /
shift:FlexibilityService, which are asserted only as subclasses in the ABox.

Usage:
    .venv/bin/python scripts/run_cqs.py
"""
import argparse
import datetime
import json
import pathlib
import time
from decimal import Decimal

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

REPO = pathlib.Path(__file__).resolve().parent.parent

# Group membership, question text, and -- for the group F questions SHIFT is
# designed to lose -- the specific term whose absence blocks the query. The
# blocking term is named for every failure, per method note 2.
CQ_META = {
    "CQ-01": ("A", "Which actors both consume and produce or store electricity?", None),
    "CQ-02": ("A", "Which actors are regular sellers (repeated confirmed sales in a period)?", None),
    "CQ-03": ("A", "What market role does a given actor hold, and in which region?", None),
    "CQ-04": ("A", "Which actors belong to the same community/trust group as actor X?", None),
    "CQ-05": ("A", "Which aggregators currently satisfy the platform's participation requirements?", None),
    "CQ-06": ("B", "Which controllable assets at node N can respond within T milliseconds?", None),
    "CQ-07": ("B", "Which assets of actor X are storage-capable and currently available?", None),
    "CQ-08": ("B", "Which assets show an unacceptable activation failure rate over recent activations?", None),
    "CQ-09": ("B", "Which buildings host a heat pump but no battery?", None),
    "CQ-10": ("C", "Which flexibility services are active at node N and what capacity is committed in window W?", None),
    "CQ-11": ("C", "Which services are persistently under-delivering against commitments?", None),
    "CQ-12": ("C", "Which contracts end before date D, and which services do they govern?", None),
    "CQ-13": ("C", "What penalty rate applies to a given trade via its contract?", None),
    "CQ-14": ("D", "Which pending trades in window W are between mutually trusted same-community parties?", None),
    "CQ-15": ("D", "Which trades crossed community boundaries without consent?", None),
    "CQ-16": ("D", "Which trades were still pending/in-progress after their delivery window closed?", None),
    "CQ-17": ("D", "What total energy volume cleared per trade window across a day?", None),
    "CQ-18": ("E", "Which actors on a flat tariff exceed the consumption threshold for a dynamic plan?", None),
    "CQ-19": ("E", "Which tariff plans carry contradictory pricing attributes?", None),
    "CQ-20": ("E", "Which nodes have forecasted load exceeding current DER capacity in the next window?",
              "No property associates shift:ForecastData with shift:Node in either "
              "direction. informedByForecast has domain ControlAsset|TradeWindow, "
              "linkedToForecast domain Asset|FlexibilitySchedule, referencedInForecast "
              "domain TariffPlan, usedInForecast domain SensorAsset|SmartMeterAsset. "
              "Missing term: a direct forecast-to-node association, e.g. "
              "shift:forecastForNode (domain ForecastData, range Node)."),
    "CQ-21": ("F", "What is the electrical topology path between two assets?",
              "No conducting-equipment model. SHIFT has no Terminal, "
              "ConnectivityNode, ACLineSegment, Switch or Busbar class, so assets "
              "have no electrical endpoints and no conductor exists between them. "
              "shift:connectedTo (Asset->Asset) carries no impedance, phase or "
              "direction. Missing terms: cim:ConductingEquipment, cim:Terminal, "
              "cim:ConnectivityNode, cim:ACLineSegment."),
    "CQ-22": ("F", "What sequence of device commands implements a curtailment instruction?",
              "No command model. SHIFT has shift:ControlAsset and the datatype "
              "shift:activationSignalType (a signal TYPE string), but no Command "
              "class to represent an individual instruction, no Function class "
              "binding a command to a device capability, and no ordering property, "
              "so 'sequence' is inexpressible. Missing terms: saref:Command, "
              "saref:Function, plus a step-ordering property."),
    "CQ-23": ("F", "What was the observed time-series value of property P of device D at time T?",
              "No observation model. SHIFT stores last-capture scalars only "
              "(shift:lastDataCaptureTime, shift:lastReadTime), overwritten on each "
              "read, so the graph holds no history at all. There is no Observation "
              "or Measurement class pairing a value with a time, and no "
              "observed-property term to name P. Missing terms: saref:Measurement "
              "(hasTimestamp, hasValue, relatesToProperty) or sosa:Observation "
              "(resultTime, hasSimpleResult, observedProperty)."),
    "CQ-24": ("F", "Which activities (forecasting, planning, optimisation) is actor X currently performing?",
              "No activity reification. SHIFT models artefacts "
              "(shift:ForecastData, shift:FlexibilitySchedule) but has no Activity "
              "class, no ForecastingActivity / PlanningActivity / "
              "OptimizationActivity, and no performs/executes property from Actor to "
              "activity. The forecast artefact carries no agent, so even its "
              "producer is unrecoverable. Missing terms: seas:Activity and its "
              "subclasses, plus an actor-to-activity link."),
    "CQ-25": ("G", "Which actors' share of trade opportunities deviates most from their community's mean?", None),
    "CQ-26": ("G", "For a failed trade, which backup trade replaced it and with which seller?", None),
}

NUM_TOLERANCE = 1e-4


def norm_cell(v):
    """Normalise a result cell to a comparable tagged value.

    bool is checked before the numeric branch on purpose: in Python bool is a
    subclass of int, so a True would otherwise compare as 1.0 and a genuine
    type mismatch would pass silently.
    """
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
    if isinstance(v, (datetime.datetime, datetime.date)):
        # str(datetime) separates date and time with a space; the oracle emits
        # isoformat with a "T". Compare on isoformat so they agree.
        return ("str", v.isoformat())
    return ("str", str(v))


def sort_key(row):
    out = []
    for c in row:
        if c is None:
            out.append((0, "", 0.0))
        elif c[0] == "num":
            out.append((1, "", round(c[1], 4)))
        elif c[0] == "bool":
            out.append((2, str(c[1]), 0.0))
        else:
            out.append((3, c[1], 0.0))
    return out


def rows_equal(a, b):
    """Multiset equality with a tolerance on numeric cells."""
    if len(a) != len(b):
        return False
    for ra, rb in zip(sorted(a, key=sort_key), sorted(b, key=sort_key)):
        if len(ra) != len(rb):
            return False
        for ca, cb in zip(ra, rb):
            if ca is None or cb is None:
                if ca is not cb:
                    return False
                continue
            if ca[0] != cb[0]:
                return False
            if ca[0] == "num":
                if abs(ca[1] - cb[1]) > NUM_TOLERANCE:
                    return False
            elif ca[1] != cb[1]:
                return False
    return True


def load_graph(kg_path, ontology_dir):
    t0 = time.perf_counter()
    g = Graph()
    g.parse(str(ontology_dir / "shift-core.ttl"), format="turtle")
    g.parse(str(ontology_dir / "shift-ext.ttl"), format="turtle")
    g.parse(str(kg_path), format="turtle")
    load_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    changed, rounds = True, 0
    while changed and rounds < 10:
        changed, rounds = False, rounds + 1
        new = []
        for s, _, c in g.triples((None, RDF.type, None)):
            for sup in g.objects(c, RDFS.subClassOf):
                if (s, RDF.type, sup) not in g:
                    new.append((s, RDF.type, sup))
        for t in new:
            g.add(t)
            changed = True
    closure_ms = (time.perf_counter() - t0) * 1000
    return g, load_ms, closure_ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kg", default="kg/shift-kg-aran.ttl")
    ap.add_argument("--queries", default="cq/shift")
    ap.add_argument("--ontology", default="ontology")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", default="results/cq_shift.json")
    a = ap.parse_args()

    kg_path = REPO / a.kg
    gold_path = kg_path.with_suffix(".cq_truth.json")
    if not gold_path.exists():
        raise SystemExit(
            f"missing {gold_path.name}; run generator/generate_abox.py first")
    gold_all = json.load(open(gold_path))["cq_truth"]

    g, load_ms, closure_ms = load_graph(kg_path, REPO / a.ontology)

    results = {}
    for f in sorted((REPO / a.queries).glob("cq*.rq")):
        cq_id = f"CQ-{f.stem[2:]}"
        group, title, missing = CQ_META[cq_id]
        query = f.read_text()
        gold = [[norm_cell(c) for c in row] for row in gold_all.get(cq_id, [])]

        times, rows, error = [], None, None
        for _ in range(a.repeats):
            t0 = time.perf_counter()
            try:
                out = g.query(query)
                rows = [[norm_cell(c) for c in row] for row in out]
            except Exception as exc:  # noqa: BLE001 - recorded, not raised
                error = f"{type(exc).__name__}: {exc}"
                break
            times.append((time.perf_counter() - t0) * 1000)

        if error is not None:
            status, match, n = "error", False, 0
        else:
            n = len(rows)
            match = rows_equal(rows, gold)
            if not match:
                status = "mismatch"
            elif not gold:
                # Query and oracle agree on the empty set. That is consistent,
                # but it demonstrates nothing about expressive power, so it is
                # NOT counted as answerable.
                status = "vacuous"
            else:
                status = "answerable"

        results[cq_id] = {
            "group": group,
            "question": title,
            "query_file": f"{a.queries}/{f.name}",
            "answerable": status == "answerable",
            "status": status,
            "result_count": n,
            "gold_count": len(gold),
            "match": match,
            "runtime_ms": round(sorted(times)[len(times) // 2], 2) if times else None,
            "expected_to_fail": group == "F",
            "missing_term": missing,
            "error": error,
        }

    graded = [v for v in results.values() if not v["expected_to_fail"]]
    report = {
        "kg": a.kg,
        "queries": a.queries,
        "graph_triples_with_tbox_and_closure": len(g),
        "load_ms": round(load_ms, 1),
        "rdfs_closure_ms": round(closure_ms, 1),
        "cqs_evaluated": len(results),
        "summary": {
            "answerable": sum(1 for v in results.values() if v["status"] == "answerable"),
            "vacuous": sum(1 for v in results.values() if v["status"] == "vacuous"),
            "mismatch": sum(1 for v in results.values() if v["status"] == "mismatch"),
            "error": sum(1 for v in results.values() if v["status"] == "error"),
            "graded_cqs_matching_gold": sum(1 for v in graded if v["match"]),
            "graded_cqs": len(graded),
            "group_f_correctly_empty": sum(
                1 for v in results.values()
                if v["expected_to_fail"] and v["result_count"] == 0),
        },
        "total_cq_ms": round(sum(v["runtime_ms"] or 0 for v in results.values()), 2),
        "per_cq": results,
    }
    (REPO / a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(REPO / a.out, "w"), indent=1)

    hdr = f"{'CQ':7} {'grp':4} {'rows':>6} {'gold':>6} {'match':>6} {'status':>12} {'ms':>9}"
    print(f"KG {a.kg}   triples+TBox+closure {len(g)}")
    print(f"load {load_ms:.0f} ms   rdfs closure {closure_ms:.0f} ms\n")
    print(hdr)
    print("-" * len(hdr))
    for cq_id in sorted(results):
        v = results[cq_id]
        ms = f"{v['runtime_ms']:.2f}" if v["runtime_ms"] is not None else "-"
        print(f"{cq_id:7} {v['group']:4} {v['result_count']:6} {v['gold_count']:6} "
              f"{str(v['match']):>6} {v['status']:>12} {ms:>9}")
    print("-" * len(hdr))
    s = report["summary"]
    print(f"answerable {s['answerable']}   vacuous {s['vacuous']}   "
          f"mismatch {s['mismatch']}   error {s['error']}")
    print(f"graded (non-F) CQs matching gold: {s['graded_cqs_matching_gold']}"
          f"/{s['graded_cqs']}")
    print(f"group F correctly empty: {s['group_f_correctly_empty']}/4")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
run_rules.py — execute the SHIFT reasoning rules over a knowledge graph, time
them, and score the inferences against the generator's ground truth.

Scoring is per-rule precision/recall against an oracle computed independently in
the generator. A rule that fires on everything scores badly; a rule that never
fires scores badly. This is the number the paper needs.
"""
import json, pathlib, sys, time, argparse
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD
import datetime as dt

SHIFT = Namespace("https://w3id.org/shift/core#")
ROOT = pathlib.Path(__file__).resolve().parents[1]

# what each rule's output SUBJECT set should be compared against
TARGET = {
    "rr00": ("RR-00", "subject"), "rr01": ("RR-01", "subject"),
    "rr02": ("RR-02", "subject"), "rr03": ("RR-03", "subject"),
    "rr04": ("RR-04", "subject"), "rr09": ("RR-09", "subject"),
    "rr16": ("RR-16", "subject"), "rr17": ("RR-17", "subject"),
    "rr21": ("RR-21", "subject"), "rr23": ("RR-23", "subject"),
    "rr27": ("RR-27", "subject"), "rr28": ("RR-28", "subject"),
    "rr29": ("RR-29", "subject"),
}


def prf(pred, gold):
    tp = len(pred & gold); fp = len(pred - gold); fn = len(gold - pred)
    # Vacuous case: the graph contains no positives and the rule fired on none.
    # That is a correct result, not a failure. Scoring it 0 (as naive
    # precision/recall does) silently depresses the macro average.
    if not pred and not gold:
        return dict(tp=0, fp=0, fn=0, precision=1.0, recall=1.0, f1=1.0,
                    vacuous=True)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return dict(tp=tp, fp=fp, fn=fn, precision=round(p, 4),
                recall=round(r, 4), f1=round(f, 4), vacuous=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kg", default="kg/shift-kg-aran.ttl")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--report", default="eval/rule_report.json")
    a = ap.parse_args()

    kg_path = ROOT / a.kg
    truth = json.load(open(kg_path.with_suffix(".truth.json")))
    manifest = json.load(open(kg_path.with_suffix(".manifest.json")))
    days = truth["params"]["days"]
    NOW = dt.datetime(2026, 3, 2) + dt.timedelta(days=days)

    t0 = time.perf_counter()
    g = Graph()
    g.parse(str(ROOT / "ontology" / "shift-core.ttl"), format="turtle")
    g.parse(str(ROOT / "ontology" / "shift-ext.ttl"), format="turtle")
    g.parse(str(kg_path), format="turtle")
    load_ms = (time.perf_counter() - t0) * 1000

    # rdflib does no subclass materialisation; assert rdfs:subClassOf closure for
    # the types the rules match on (?a a shift:Actor, ?a a shift:Asset).
    from rdflib.namespace import RDFS
    t0 = time.perf_counter()
    changed = True
    rounds = 0
    while changed and rounds < 10:
        changed = False; rounds += 1
        new = []
        for s, _, c in g.triples((None, RDF.type, None)):
            for sup in g.objects(c, RDFS.subClassOf):
                if (s, RDF.type, sup) not in g:
                    new.append((s, RDF.type, sup))
        for t in new:
            g.add(t); changed = True
    closure_ms = (time.perf_counter() - t0) * 1000

    binds = {
        "NOW": Literal(NOW.isoformat(), datatype=XSD.dateTime),
        "CUTOFF90": Literal((NOW - dt.timedelta(days=90)).isoformat(),
                            datatype=XSD.dateTime),
        "CUTOFF30": Literal((NOW - dt.timedelta(days=30)).isoformat(),
                            datatype=XSD.dateTime),
    }

    results = {}
    total_inferred = 0
    for f in sorted((ROOT / "rules" / "sparql").glob("*.rq")):
        rid = f.stem
        q = f.read_text()
        times = []
        out = None
        for _ in range(a.repeats):
            t0 = time.perf_counter()
            out = g.query(q, initBindings=binds)
            triples = list(out)
            times.append((time.perf_counter() - t0) * 1000)
        subjects = {str(t[0]) for t in triples}
        total_inferred += len(triples)
        key, _ = TARGET[rid]
        gold = set(truth["truth"].get(key, []))
        results[rid] = {
            "rule": key,
            "inferred_triples": len(triples),
            "inferred_subjects": len(subjects),
            "gold_subjects": len(gold),
            "median_ms": round(sorted(times)[len(times) // 2], 2),
            "min_ms": round(min(times), 2),
            **prf(subjects, gold),
        }

    report = {
        "kg": a.kg,
        "kg_triples": manifest["triples"],
        "graph_triples_with_tbox_and_closure": len(g),
        "load_ms": round(load_ms, 1),
        "rdfs_closure_ms": round(closure_ms, 1),
        "rules_evaluated": len(results),
        "total_inferred_triples": total_inferred,
        "total_rule_ms": round(sum(v["median_ms"] for v in results.values()), 2),
        "per_rule": results,
    }
    macro_f1 = sum(v["f1"] for v in results.values()) / len(results)
    report["macro_f1"] = round(macro_f1, 4)
    (ROOT / a.report).parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(ROOT / a.report, "w"), indent=1)

    # console table
    print(f"KG: {a.kg}   ABox triples {manifest['triples']}   "
          f"with TBox+closure {len(g)}")
    print(f"load {load_ms:.0f} ms   rdfs closure {closure_ms:.0f} ms\n")
    hdr = f"{'rule':7} {'fired':>6} {'gold':>6} {'tp':>5} {'fp':>4} {'fn':>4} " \
          f"{'prec':>6} {'rec':>6} {'f1':>6} {'ms':>8}"
    print(hdr); print("-" * len(hdr))
    for rid in sorted(results):
        v = results[rid]
        print(f"{v['rule']:7} {v['inferred_subjects']:6} {v['gold_subjects']:6} "
              f"{v['tp']:5} {v['fp']:4} {v['fn']:4} {v['precision']:6.3f} "
              f"{v['recall']:6.3f} {v['f1']:6.3f} {v['median_ms']:8.2f}")
    print("-" * len(hdr))
    print(f"{'TOTAL':7} {total_inferred:6} {'':6} {'':5} {'':4} {'':4} {'':6} "
          f"{'':6} {macro_f1:6.3f} {report['total_rule_ms']:8.2f}")


if __name__ == "__main__":
    main()

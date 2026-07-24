#!/usr/bin/env python3
"""
verify.py — adversarial verification of the SHIFT KG release.

Checks:
  V1  every class and predicate used in the ABox is declared in the TBox
  V2  no property carries conflicting rdfs:domain declarations across modules
      (multiple domains = intersection semantics in OWL: silent wrong inference)
  V3  every literal's datatype matches the declared rdfs:range
  V4  generator reproducibility: same seed => isomorphic graph, identical truth
  V5  ground-truth oracle vs rule temporal windows: the oracle for RR-17/RR-28
      ignores the 90/30-day windows; verify no event falls outside them, i.e.
      the simplification is currently harmless (and flag it as fragile)
  V6  (reserved, not implemented) shipped eval reports match a fresh re-run
  V7  release version consistency: CITATION.cff version == owl:versionInfo of
      both TBox modules == the version segment of their owl:versionIRI
"""
import json, pathlib, subprocess, sys, tempfile
from collections import defaultdict
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
from rdflib.compare import isomorphic

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHIFT = "https://w3id.org/shift/core#"
issues = []


def issue(code, msg):
    issues.append((code, msg))
    print(f"  [{code}] {msg}")


print("== loading TBox ==")
tbox = Graph()
tbox.parse(str(ROOT / "ontology/shift-core.ttl"), format="turtle")
tbox.parse(str(ROOT / "ontology/shift-ext.ttl"), format="turtle")
declared_cls = set(tbox.subjects(RDF.type, OWL.Class))
declared_op = set(tbox.subjects(RDF.type, OWL.ObjectProperty))
declared_dp = set(tbox.subjects(RDF.type, OWL.DatatypeProperty))
declared_props = declared_op | declared_dp

abox = Graph()
abox.parse(str(ROOT / "kg/shift-kg-aran.ttl"), format="turtle")

print("\n== V1: vocabulary closure ==")
used_cls = {o for o in abox.objects(None, RDF.type)
            if str(o).startswith(SHIFT)}
used_props = {p for _, p, _ in abox
              if str(p).startswith(SHIFT)}
for c in sorted(used_cls - declared_cls):
    issue("V1-CLASS", f"ABox uses undeclared class {c}")
for p in sorted(used_props - declared_props):
    issue("V1-PROP", f"ABox uses undeclared property {p}")
if not (used_cls - declared_cls) and not (used_props - declared_props):
    print("  OK — every ABox class and predicate is declared")

print("\n== V2: conflicting rdfs:domain declarations ==")
doms = defaultdict(set)
for p, d in tbox.subject_objects(RDFS.domain):
    doms[p].add(d)
conflicts = {p: ds for p, ds in doms.items() if len(ds) > 1}
# multiple domains that sit on one subclass chain are fine; disjoint branches are not
sub = defaultdict(set)
for s, o in tbox.subject_objects(RDFS.subClassOf):
    sub[s].add(o)
def ancestors(c, seen=None):
    seen = seen or set()
    for p in sub.get(c, ()):
        if p not in seen:
            seen.add(p); ancestors(p, seen)
    return seen
for p, ds in sorted(conflicts.items(), key=lambda kv: str(kv[0])):
    dl = list(ds)
    related = any(a in ancestors(b) or b in ancestors(a) or a == b
                  for i, a in enumerate(dl) for b in dl[i+1:])
    if not related:
        issue("V2-DOMAIN", f"{p.split('#')[-1]} has unrelated domains "
              f"{{{', '.join(sorted(d.split('#')[-1] for d in map(str, ds)))}}} "
              "=> OWL intersection semantics: every subject is inferred to be "
              "ALL of these classes")

print("\n== V2b: conflicting rdfs:range on object properties ==")
op = set(tbox.subjects(RDF.type, OWL.ObjectProperty))
rngs2 = defaultdict(set)
for p_, r_ in tbox.subject_objects(RDFS.range):
    if p_ in op:
        rngs2[p_].add(r_)
n2b = 0
for p_, rs_ in sorted(rngs2.items(), key=lambda kv: str(kv[0])):
    named = [r for r in rs_ if isinstance(r, URIRef)]
    if len(named) > 1:
        n2b += 1
        issue("V2b-RANGE", f"{p_.split('#')[-1]} has multiple named ranges "
              f"{{{', '.join(sorted(r.split('#')[-1] for r in map(str, named)))}}}")
if n2b == 0:
    print("  OK — no object property carries conflicting named ranges")

print("\n== V3: literal datatype vs declared range ==")
rng = {}
for p, r in tbox.subject_objects(RDFS.range):
    if p in declared_dp:
        rng[p] = r
bad = 0
for s, p, o in abox:
    if p in rng and isinstance(o, Literal):
        want = rng[p]
        got = o.datatype or XSD.string
        if str(want).startswith(str(XSD)) and got != want:
            bad += 1
            if bad <= 5:
                issue("V3-RANGE", f"{p.split('#')[-1]} declared {want.split('#')[-1]} "
                      f"but literal {o!r} is {got.split('#')[-1]}")
if bad == 0:
    print(f"  OK — all typed literals conform to declared ranges")
elif bad > 5:
    issue("V3-RANGE", f"... and {bad-5} more")

print("\n== V4: generator reproducibility (seed 42) ==")
with tempfile.TemporaryDirectory() as td:
    out = pathlib.Path(td) / "regen.ttl"
    r = subprocess.run([sys.executable, str(ROOT / "generator/generate_abox.py"),
                        "--actors", "26", "--days", "7", "--seed", "42",
                        "--out", str(out)],
                       capture_output=True, text=True, cwd=str(ROOT))
    # generate_abox resolves --out relative to ROOT; handle absolute path
    candidates = [out, ROOT / str(out)]
    regen_path = next((c for c in candidates if c.exists()), None)
    if regen_path is None:
        issue("V4-RUN", f"regeneration failed: {r.stderr[-300:]}")
    else:
        g2 = Graph(); g2.parse(str(regen_path), format="turtle")
        if isomorphic(abox, g2):
            print(f"  OK — regenerated graph is isomorphic ({len(g2)} triples)")
        else:
            issue("V4-ISO", f"regenerated graph NOT isomorphic: "
                  f"{len(abox)} vs {len(g2)} triples")
        t1 = json.load(open(ROOT / "kg/shift-kg-aran.truth.json"))["truth"]
        t2 = json.load(open(regen_path.with_suffix(".truth.json")))["truth"]
        if t1 == t2:
            print("  OK — ground truth identical")
        else:
            issue("V4-TRUTH", "ground truth differs between runs")

print("\n== V5: oracle temporal-window simplification ==")
import datetime as dt
NOW = dt.datetime(2026, 3, 2) + dt.timedelta(days=7)
SH = Namespace(SHIFT)
worst_act = worst_del = None
for e in abox.subjects(RDF.type, SH.ActivationEvent):
    ts = dt.datetime.fromisoformat(str(next(abox.objects(e, SH.eventTimestamp))))
    worst_act = min(worst_act or ts, ts)
for e in abox.subjects(RDF.type, SH.DeliveryEvent):
    ts = dt.datetime.fromisoformat(str(next(abox.objects(e, SH.eventTimestamp))))
    worst_del = min(worst_del or ts, ts)
act_ok = worst_act > NOW - dt.timedelta(days=30)
del_ok = worst_del > NOW - dt.timedelta(days=90)
print(f"  oldest activation event: {(NOW-worst_act).days}d ago "
      f"(rule window 30d) -> {'inside' if act_ok else 'OUTSIDE'}")
print(f"  oldest delivery event:   {(NOW-worst_del).days}d ago "
      f"(rule window 90d) -> {'inside' if del_ok else 'OUTSIDE'}")
if act_ok and del_ok:
    print("  OK for current parameters — but the oracle omits the window filter, "
          "so it breaks if generation spreads widen. FRAGILE, documented.")
else:
    issue("V5-WINDOW", "oracle simplification is UNSOUND for current data")

print("\n== V7: release version consistency ==")
# v0.1.1 shipped with CITATION.cff and README saying 0.1.1 while both TTLs still
# stamped 0.1.0. Nothing caught it, so it is caught here. CITATION.cff is read
# line-wise rather than with a YAML parser to avoid adding a dependency for one
# scalar; the top-level `version:` key is unindented, which is what anchors it.
import re
cff_path = ROOT / "CITATION.cff"
cff_version = None
for line in cff_path.read_text().splitlines():
    m = re.match(r"^version:\s*(\S+)\s*$", line)
    if m:
        cff_version = m.group(1).strip('"\'')
        break
if cff_version is None:
    issue("V7-CFF", f"no top-level `version:` key found in {cff_path.name}")
else:
    print(f"  CITATION.cff version: {cff_version}")

for mod_iri in (URIRef("https://w3id.org/shift/core"),
                URIRef("https://w3id.org/shift/ext")):
    name = str(mod_iri).rsplit("/", 1)[-1]
    infos = list(tbox.objects(mod_iri, OWL.versionInfo))
    viris = list(tbox.objects(mod_iri, OWL.versionIRI))
    if len(infos) != 1:
        issue("V7-INFO", f"{name}: expected exactly 1 owl:versionInfo, found {len(infos)}")
        continue
    if len(viris) != 1:
        issue("V7-VIRI", f"{name}: expected exactly 1 owl:versionIRI, found {len(viris)}")
        continue
    info = str(infos[0])
    viri_seg = str(viris[0]).rsplit("/", 1)[-1]
    print(f"  {name}: versionInfo {info}, versionIRI .../{viri_seg}")
    if info != viri_seg:
        issue("V7-SELF", f"{name}: owl:versionInfo {info!r} != versionIRI segment {viri_seg!r}")
    if cff_version is not None and info != cff_version:
        issue("V7-DRIFT", f"{name}: owl:versionInfo {info!r} != CITATION.cff version {cff_version!r}")
if not any(c.startswith("V7") for c, _ in issues):
    print("  OK — CITATION.cff, both versionInfo stamps and both versionIRIs agree")

print(f"\n== SUMMARY: {len(issues)} issue(s) ==")
for c, m in issues:
    print(f"  {c}: {m.split(chr(10))[0][:110]}")
sys.exit(1 if issues else 0)

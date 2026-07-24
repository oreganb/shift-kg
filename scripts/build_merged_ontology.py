#!/usr/bin/env python3
"""Build the merged single-graph serialisation published at https://w3id.org/shift.

The release ships the TBox as two modules — `ontology/shift-core.ttl` and
`ontology/shift-ext.ttl` — because they have distinct provenance: core is the
normalised legacy vocabulary, ext is the vocabulary the rules require and the
legacy artefacts never declared. That split is right for the artefact.

It is wrong for a dereference target. A client resolving
`https://w3id.org/shift/core` with `Accept: text/turtle` gets exactly one
document and does not follow `owl:imports`, so serving core alone would silently
hide every ext term — and ext is where `ownsAsset`, `assetFunction` and 98 other
terms used by the rules live. This merges both into one graph.

Both `owl:Ontology` headers are kept. They are separate ontologies with separate
version IRIs and that remains true after merging; collapsing them would assert
something false about where a term was defined. `rdfs:isDefinedBy` on every term
still distinguishes them, and ext's `owl:imports core` is satisfied within the
document.

Usage:
    python3 scripts/build_merged_ontology.py                 # -> dist/shift.ttl
    python3 scripts/build_merged_ontology.py --out PATH
"""

import argparse
import re
import sys
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "ontology" / "shift-core.ttl"
EXT = REPO / "ontology" / "shift-ext.ttl"
CITATION = REPO / "CITATION.cff"

SHIFT = "https://w3id.org/shift/core#"

PREFIXES = {
    "shift": SHIFT,
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dcterms": "http://purl.org/dc/terms/",
    "vann": "http://purl.org/vocab/vann/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


def release_version():
    """The single source of truth for the version; eval/verify.py V7 keeps the
    TTL stamps in step with it."""
    for line in CITATION.read_text().splitlines():
        m = re.match(r"^version:\s*(\S+)\s*$", line)
        if m:
            return m.group(1).strip('"\'')
    sys.exit(f"no top-level `version:` key in {CITATION.name}")


def named(graph, kind):
    return {s for s in graph.subjects(RDF.type, kind) if isinstance(s, URIRef)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "dist" / "shift.ttl"))
    args = ap.parse_args()

    version = release_version()

    g = Graph()
    for src in (CORE, EXT):
        before = len(g)
        g.parse(str(src), format="turtle")
        print(f"  {src.name:<20} +{len(g) - before} triples")

    for p, ns in PREFIXES.items():
        g.bind(p, ns, override=True)

    classes = named(g, OWL.Class)
    props = (named(g, OWL.ObjectProperty) | named(g, OWL.DatatypeProperty)
             | named(g, OWL.AnnotationProperty))
    ontologies = sorted(str(s) for s in named(g, OWL.Ontology))

    # Sanity: the merge is only useful if ext actually came through.
    if URIRef(SHIFT + "ownsAsset") not in props:
        sys.exit("ERROR: shift:ownsAsset missing — ext did not merge correctly")

    body = g.serialize(format="turtle")

    # Kept deliberately tight: `curl … | head -20` on the published namespace
    # should reach the first @prefix, not run out of screen inside a banner.
    header = f"""\
# SHIFT Ontology — merged serialisation (core + rule vocabulary extension)
#
# GENERATED — DO NOT EDIT. Regenerated each release; hand edits are overwritten.
#   Source   : https://github.com/oreganb/shift-kg  release v{version}
#   Built by : python3 scripts/build_merged_ontology.py
#   From     : ontology/shift-core.ttl + ontology/shift-ext.ttl
#   Contains : {len(g)} triples, {len(classes)} named classes, {len(props)} named properties
#
# Dereference target of https://w3id.org/shift/core. The two release modules are
# merged because a client resolving the namespace receives one document and does
# not follow owl:imports; rdfs:isDefinedBy on each term records its module.
#
# Licence CC-BY-4.0. Cite via CITATION.cff in oreganb/shift-kg, which also holds
# the populated knowledge graph, SPARQL rules, CQs and evaluation harness.

"""

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + body)

    # Re-parse what was written: a header typo would otherwise ship silently.
    check = Graph()
    check.parse(str(out), format="turtle")
    if len(check) != len(g):
        sys.exit(f"ERROR: wrote {len(g)} triples but re-parsed {len(check)}")

    print(f"\n  merged -> {out}")
    print(f"  {len(g)} triples, {len(classes)} named classes, "
          f"{len(props)} named properties")
    print(f"  re-parsed clean at {len(check)} triples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

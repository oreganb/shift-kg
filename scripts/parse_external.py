#!/usr/bin/env python3
"""Parse the external benchmark ontologies with rdflib and report term counts.

Integrity check for external/: confirms each file parses as Turtle and reports
how many classes and properties it declares. Query-level benchmarking is scoped
to SAREF and SEAS, so these are the files that must be intact.

Usage:
    .venv/bin/python scripts/parse_external.py [files_or_dirs ...]

With no arguments, parses external/*.ttl.
"""

import sys
from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS, URIRef

REPO = Path(__file__).resolve().parent.parent

CLASS_TYPES = [OWL.Class, RDFS.Class]
PROPERTY_TYPES = [
    ("owl:ObjectProperty", OWL.ObjectProperty),
    ("owl:DatatypeProperty", OWL.DatatypeProperty),
    ("owl:AnnotationProperty", OWL.AnnotationProperty),
    ("rdf:Property", RDF.Property),
]


def named(graph, rdf_type):
    """Named (non-blank) subjects of the given rdf:type.

    Blank nodes are excluded: they are anonymous restrictions and unions, not
    vocabulary terms, and counting them inflates the totals.
    """
    return {s for s in graph.subjects(RDF.type, rdf_type) if isinstance(s, URIRef)}


def report(path):
    graph = Graph()
    graph.parse(path, format="turtle")

    classes = set()
    for t in CLASS_TYPES:
        classes |= named(graph, t)

    prop_counts = []
    all_props = set()
    for label, t in PROPERTY_TYPES:
        found = named(graph, t)
        all_props |= found
        prop_counts.append((label, len(found)))

    ontologies = list(graph.subjects(RDF.type, OWL.Ontology))
    imports = list(graph.objects(None, OWL.imports))

    print(f"\n{path.name}")
    print(f"  {'triples':<22} {len(graph)}")
    print(f"  {'named classes':<22} {len(classes)}")
    for label, n in prop_counts:
        print(f"  {'  ' + label:<22} {n}")
    print(f"  {'distinct properties':<22} {len(all_props)}")
    print(f"  {'owl:Ontology decls':<22} {len(ontologies)}")
    print(f"  {'owl:imports':<22} {len(imports)}")
    for o in ontologies:
        version = next(graph.objects(o, OWL.versionInfo), None)
        version_iri = next(graph.objects(o, OWL.versionIRI), None)
        print(f"  ontology: {o}")
        if version:
            print(f"    versionInfo: {version}")
        if version_iri:
            print(f"    versionIRI:  {version_iri}")

    return {
        "file": path.name,
        "triples": len(graph),
        "classes": len(classes),
        "properties": len(all_props),
        "imports": len(imports),
    }


def main(argv):
    targets = []
    for arg in argv or [str(REPO / "external")]:
        p = Path(arg)
        if p.is_dir():
            targets.extend(sorted(p.glob("*.ttl")))
        else:
            targets.append(p)

    if not targets:
        print("no .ttl files found", file=sys.stderr)
        return 1

    rows = [report(t) for t in targets]

    print("\n" + "=" * 68)
    print(f"{'file':<32}{'triples':>10}{'classes':>10}{'props':>8}{'imports':>8}")
    print("-" * 68)
    for r in rows:
        print(f"{r['file']:<32}{r['triples']:>10}{r['classes']:>10}"
              f"{r['properties']:>8}{r['imports']:>8}")
    print("=" * 68)
    print(f"{len(rows)} file(s) parsed without error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

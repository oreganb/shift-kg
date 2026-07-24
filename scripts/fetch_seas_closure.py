#!/usr/bin/env python3
"""Fetch the owl:imports closure of the SEAS hub ontology.

https://w3id.org/seas/ declares no terms of its own -- it is a hub that imports
43 modules. Query-level benchmarking needs the modules, so this walks the
imports transitively and writes each module to external/seas-modules/.

Usage:
    .venv/bin/python scripts/fetch_seas_closure.py
"""

import sys
import urllib.request
from pathlib import Path

from rdflib import Graph, OWL

REPO = Path(__file__).resolve().parent.parent
SEAS_HUB = REPO / "external" / "seas.ttl"
OUT_DIR = REPO / "external" / "seas-modules"

HEADERS = {"Accept": "text/turtle"}


def slug(iri):
    """Filename for a module IRI: last non-empty path segment."""
    parts = [p for p in iri.rstrip("/").split("/") if p]
    return f"{parts[-1]}.ttl"


def fetch(iri):
    req = urllib.request.Request(iri, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    hub = Graph()
    hub.parse(SEAS_HUB, format="turtle")

    queue = [str(o) for o in hub.objects(None, OWL.imports)]
    seen = set()
    failed = []
    written = 0

    while queue:
        iri = queue.pop(0)
        if iri in seen:
            continue
        seen.add(iri)

        target = OUT_DIR / slug(iri)
        try:
            body = fetch(iri)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failed.append((iri, str(exc)))
            print(f"FAIL  {iri}\n      {exc}")
            continue

        # Verify it parses before keeping it; a 200 can still be an error page.
        probe = Graph()
        try:
            probe.parse(data=body, format="turtle")
        except Exception as exc:  # noqa: BLE001
            failed.append((iri, f"unparseable: {exc}"))
            print(f"FAIL  {iri}\n      unparseable: {exc}")
            continue

        target.write_bytes(body)
        written += 1
        print(f"ok    {target.name:<45} {len(probe):>6} triples")

        # Transitive: modules may import further modules.
        queue.extend(str(o) for o in probe.objects(None, OWL.imports))

    print(f"\n{written} module(s) written to {OUT_DIR.relative_to(REPO)}")
    if failed:
        print(f"{len(failed)} failed:")
        for iri, err in failed:
            print(f"  {iri}  --  {err}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

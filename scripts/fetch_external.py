#!/usr/bin/env python3
"""Fetch the external ontologies SHIFT is benchmarked against.

These files are deliberately NOT redistributed in this repository. SAREF is
published by ETSI under its own licence terms, and the cleanest way to respect
those — and to avoid shipping a silently stale copy of anyone's ontology — is to
fetch from the authoritative source at reproduction time.

`external/PROVENANCE.md` records exactly what was retrieved on 2026-07-24, with
per-file triple/class/property counts, so a later fetch can be checked against
the numbers the published results were computed from. Upstream ontologies do
change; if the counts drift, that is a finding, not a failure of this script.

Usage:
    .venv/bin/python scripts/fetch_external.py        # SAREF + SEAS hub
    .venv/bin/python scripts/fetch_seas_closure.py    # then the SEAS modules
    .venv/bin/python scripts/parse_external.py        # integrity counts

Two upstream defects are expected and documented in PROVENANCE.md:
  * https://ci.mines-stetienne.fr/seas/seas.ttl returns 404; the hub resolves at
    https://w3id.org/seas/ instead.
  * The SEAS hub declares no terms of its own — it imports 43 modules, of which
    4 do not resolve. SEAS competency questions must load the 40-module closure.
"""

import sys
import urllib.request
from pathlib import Path

from rdflib import Graph

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "external"

HEADERS = {"Accept": "text/turtle"}

# (filename, source URI). URIs are the ones recorded in PROVENANCE.md.
SOURCES = [
    ("saref.ttl", "https://saref.etsi.org/core/v4.1.1/saref.ttl"),
    ("saref4ener.ttl", "https://saref.etsi.org/saref4ener/v2.1.1/"),
    ("saref4bldg.ttl", "https://saref.etsi.org/saref4bldg/v2.1.1/"),
    ("seas.ttl", "https://w3id.org/seas/"),
    ("seas-ActorOntology.ttl", "https://w3id.org/seas/ActorOntology"),
]

# Counts as retrieved 2026-07-24, from PROVENANCE.md. Reported, not enforced:
# a mismatch means upstream moved, which the reproducer needs to know about.
EXPECTED = {
    "saref.ttl": 1324,
    "saref4ener.ttl": 2164,
    "saref4bldg.ttl": 2203,
    "seas.ttl": 68,
    "seas-ActorOntology.ttl": 98,
}


def fetch(iri):
    req = urllib.request.Request(iri, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failed, drifted = [], []

    for name, iri in SOURCES:
        try:
            body = fetch(iri)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failed.append((name, str(exc)))
            print(f"FAIL  {name:<28} {exc}")
            continue

        # A 200 can still be an error page; keep it only if it parses.
        probe = Graph()
        try:
            probe.parse(data=body, format="turtle")
        except Exception as exc:  # noqa: BLE001
            failed.append((name, f"unparseable: {exc}"))
            print(f"FAIL  {name:<28} unparseable: {exc}")
            continue

        (OUT_DIR / name).write_bytes(body)
        want = EXPECTED.get(name)
        flag = ""
        if want is not None and len(probe) != want:
            flag = f"  <- DRIFTED from {want} recorded in PROVENANCE.md"
            drifted.append((name, want, len(probe)))
        print(f"ok    {name:<28} {len(probe):>6} triples{flag}")

    print(f"\n{len(SOURCES) - len(failed)}/{len(SOURCES)} written to "
          f"{OUT_DIR.relative_to(REPO)}")
    print("Next: scripts/fetch_seas_closure.py to walk the SEAS imports closure.")

    if drifted:
        print(f"\n{len(drifted)} file(s) differ from the recorded provenance:")
        for name, want, got in drifted:
            print(f"  {name}: recorded {want}, fetched {got}")
        print("The published results were computed against the recorded counts.")
    if failed:
        print(f"\n{len(failed)} failed:")
        for name, err in failed:
            print(f"  {name}  --  {err}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

# External ontology sources

Retrieved 2026-07-24. All files fetched with `Accept: text/turtle` and verified
by parsing with rdflib 7.6.0 before being kept.

Query-level benchmarking is scoped to SAREF and SEAS, the two OWL ontologies of
comparable scope. CIM is assessed at alignment level owing to its scale and
UML/RDFS heritage; SGAM, a reference architecture rather than an ontology, is
treated through architectural placement. Neither therefore appears here.

**The ontology files themselves are not redistributed in this repository.** SAREF
is published by ETSI under its own licence terms, and shipping a frozen copy of
anyone's ontology invites silent staleness besides. Only this provenance record
and the fetch scripts are included. Everything below is reproducible from the
authoritative sources:

```
.venv/bin/python scripts/fetch_external.py        # SAREF Core/4ENER/4BLDG, SEAS hub
.venv/bin/python scripts/fetch_seas_closure.py    # SEAS modules
.venv/bin/python scripts/parse_external.py        # integrity counts
```

`fetch_external.py` compares what it retrieves against the triple counts recorded
below and reports any drift. The published results were computed against these
counts; upstream ontologies do change, so a mismatch is information, not a bug.

## Files

| File | Source URI | HTTP | Triples | Classes | Properties |
|---|---|---|---|---|---|
| `saref.ttl` | `https://saref.etsi.org/core/v4.1.1/saref.ttl` | 200 | 1324 | 32 | 86 |
| `saref4ener.ttl` | `https://saref.etsi.org/saref4ener/v2.1.1/` | 200 | 2164 | 81 | 176 |
| `saref4bldg.ttl` | `https://saref.etsi.org/saref4bldg/v2.1.1/` | 200 | 2203 | 66 | 100 |
| `seas-ActorOntology.ttl` | `https://ci.mines-stetienne.fr/seas/ActorOntology` | 200 | 98 | 10 | 3 |
| `seas.ttl` | `https://ci.mines-stetienne.fr/seas/` | 200 | 68 | 0 | 0 |
| `seas-modules/*.ttl` (40 files) | `owl:imports` closure of `seas.ttl` | 200 | 6298 | 323 | 216 |

Counts are named (non-blank) subjects of `owl:Class`/`rdfs:Class` and of
`owl:ObjectProperty`/`owl:DatatypeProperty`/`owl:AnnotationProperty`/`rdf:Property`.
Blank nodes are excluded: they are anonymous restrictions and unions, not terms.

Versions declared by the sources: SAREF Core `v4.1.1` (versionIRI
`https://saref.etsi.org/core/v4.1.1/`), SAREF4ENER `v2.1.1`, SAREF4BLDG
`v2.1.1`, SEAS hub `v1.0` (versionIRI `https://w3id.org/seas/seas-1.0`), SEAS
ActorOntology `v0.10`.

## The SAREF extensions version independently of Core

**The extensions are at v2.1.1, not v4.1.1.** SAREF Core is v4.1.1, and it is
easy to assume the extensions track it — they do not. Both
`https://saref.etsi.org/saref4ener/` and `https://saref.etsi.org/saref4bldg/`
content-negotiate to a document whose `owl:versionIRI` is `.../v2.1.1/`, and
every extension link on their landing pages points at `v2.1.1`. The `v4.1.1`
strings that do appear on those pages refer to the Core release the extension
imports, not to the extension.

Two consequences for anyone reproducing this:

- `https://saref.etsi.org/saref4ener/v4.1.1/saref4ener.ttl` returns **404**, as
  does the `v4.1.1` directory form. So does the `<name>.ttl` filename at any
  version — the versioned *directory* URL is what resolves, e.g.
  `https://saref.etsi.org/saref4ener/v2.1.1/` with `Accept: text/turtle`.
- The URLs above are pinned to `v2.1.1` rather than to the bare base, so a
  future release cannot silently change what the benchmark ran against.

## Two things worth knowing about the SEAS files

**1. `seas.ttl` is a hub, not a vocabulary.** The URL given in the task,
`https://ci.mines-stetienne.fr/seas/seas.ttl`, returns HTTP 404 (a GlassFish
error page). The ontology resolves at `https://ci.mines-stetienne.fr/seas/`,
equivalently `https://w3id.org/seas/`, and that document declares **no classes
and no properties of its own** — it is 68 triples of metadata plus 43
`owl:imports`. It parses cleanly, but on its own it cannot carry a query-level
benchmark.

`scripts/fetch_seas_closure.py` therefore walks the imports transitively into
`seas-modules/`. The merged union of those 40 modules is the artefact to load
into Fuseki for SEAS competency questions: **6298 triples, 323 named classes
(299 in the `seas:` namespace), 216 properties (145 in `seas:`)**.

**2. Four declared imports do not resolve.** These are upstream publishing
defects, recorded rather than worked around:

| Import IRI | Failure |
|---|---|
| `https://w3id.org/rdfp/` | HTTP 404. No versioned variant found (`rdfp-1.0/1.1/0.1.ttl` all 404). |
| `https://w3id.org/seas/GraphOntology` | HTTP 404. |
| `https://w3id.org/seas/BuildingCategoriesOntology` | HTTP 404. Note the *Vocabulary* of the same name does resolve and is included. |
| `https://w3id.org/seas/StatisticsVocabulary` | HTTP 200 but the Turtle is **truncated**: 181 lines, 8849 bytes, ending mid-statement on `seas:rank` with a trailing `;` and no `.`. |

The raw truncated `StatisticsVocabulary` response is kept verbatim at
`_unparseable/StatisticsVocabulary.ttl.raw`. It has **not** been repaired.
Appending a single `.` would make it parse, but that is an edit to a cited
external source and should be a deliberate, documented decision rather than a
silent fix — flagging it here for that call to be made.

Two filenames in `seas-modules/` do not follow the last-path-segment rule the
fetch script applies. `w3c-time.ttl` is the W3C Time ontology, pulled in
transitively from `http://www.w3.org/2006/time#`, and was renamed by hand from
the `time#.ttl` the script produced. `pep.ttl` is described below.

`https://w3id.org/pep/` also fails content negotiation (returns an HTML
documentation page for `Accept: text/turtle`). It was recovered from the
`pep-1.1.ttl` link on that page and is present as `seas-modules/pep.ttl`.

Net effect on coverage: of 43 declared SEAS imports plus the recovered `pep`,
40 modules are present. The three missing SEAS modules cover graph structure,
building categories (ontology layer only), and statistics — none of which is
central to the flexibility and trading terms the competency questions target,
but the gap is stated so the benchmark's denominator is honest.

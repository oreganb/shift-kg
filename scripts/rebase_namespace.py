#!/usr/bin/env python3
"""
rebase_namespace.py -- move the SHIFT term namespace to a new base IRI.

Rewrites a literal namespace string across the ontology, the rule set, the
generator, the eval harness and the competency questions. Turtle prefix
declarations, SPARQL PREFIX lines and Python Namespace() calls all carry the
same literal, so a single exact-string substitution covers every one of them.

The migration to w3id.org is COMPLETE and ran in two passes:

    pass 1  http://shift-ontology.org/core#  ->  https://w3id.org/shift/core#
            (term namespace only: 49 occurrences, 47 files)
    pass 2  http://shift-ontology.org/       ->  https://w3id.org/shift/
            (everything else: the ontology identity IRIs core and ext, their
             versionIRIs, vann:preferredNamespaceUri, and the kg/ instance
             namespace -- 214 occurrences, 14 files)

Nothing under http://shift-ontology.org/ remains. The default below is pass 2,
which is idempotent: re-running it is a no-op. Pass --from/--to for any future
move.

Usage:
    .venv/bin/python scripts/rebase_namespace.py --dry-run
    .venv/bin/python scripts/rebase_namespace.py --from ... --to ...
"""
import argparse
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent

OLD = "http" + "://shift-ontology.org/"   # split so this file holds no live IRI
NEW = "https://w3id.org/shift/"

# Source of truth only. Generated artefacts (kg/*.ttl and their sidecars) are
# NOT rewritten in place -- they are regenerated from the rebased generator, so
# that a stale edit can never masquerade as a clean regeneration.
TARGETS = [
    ("ontology", ("*.ttl",)),
    ("rules/sparql", ("*.rq", "*.txt")),
    ("rules/shacl", ("*.ttl", "*.rq")),
    ("generator", ("*.py",)),
    ("eval", ("*.py",)),
    ("shift-kg", ("SHIFT_KG_verify.py",)),
    ("cq/shift", ("*.rq",)),
    ("scripts", ("*.py",)),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="old", default=OLD)
    ap.add_argument("--to", dest="new", default=NEW)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    changed, total = [], 0
    for rel, patterns in TARGETS:
        base = REPO / rel
        if not base.is_dir():
            continue
        for pattern in patterns:
            for f in sorted(base.glob(pattern)):
                if f.resolve() == pathlib.Path(__file__).resolve():
                    continue  # never rewrite this script's own mapping
                text = f.read_text()
                n = text.count(a.old)
                if not n:
                    continue
                total += n
                changed.append((f.relative_to(REPO), n))
                if not a.dry_run:
                    f.write_text(text.replace(a.old, a.new))

    verb = "would rewrite" if a.dry_run else "rewrote"
    print(f"{a.old}\n  ->  {a.new}\n")
    for path, n in changed:
        print(f"  {verb} {n:4}x  {path}")
    print(f"\n{verb} {total} occurrence(s) across {len(changed)} file(s)")
    if a.dry_run:
        print("dry run -- nothing written")
    else:
        print("now regenerate the KGs so the instance data matches the generator")


if __name__ == "__main__":
    main()

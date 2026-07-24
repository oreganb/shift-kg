#!/usr/bin/env python3
"""
build_tbox.py — SHIFT Ontology TBox normalisation and extension.

Reads the legacy RDF/XML modules, emits:
  ontology/shift-core.ttl   : the 43 legacy classes + 354 properties, with a
                              proper owl:Ontology header, version IRI, licence
                              and provenance. Dangling class references fixed.
  ontology/shift-ext.ttl    : vocabulary referenced by SHIFT-RR-00..34 but never
                              declared in the legacy artefacts.

Provenance note: every term in shift-ext.ttl carries rdfs:isDefinedBy and a
skos:note recording which rule required it. Nothing is invented silently.
"""
import rdflib
from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import OWL, RDF, RDFS, XSD, DCTERMS, SKOS
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Legacy RDF/XML modules. Overridable because this path is machine-specific: the
# artefacts live outside the release tree and are not redistributed with it.
SRC = pathlib.Path(os.environ.get(
    "SHIFT_LEGACY_SRC",
    "/Users/brianoregan/Dropbox/00-IERC/Project-OPTIX/SHIFT Ontology/SHIFT owl"))

SHIFT = Namespace("https://w3id.org/shift/core#")
VANN = Namespace("http://purl.org/vocab/vann/")

# Release version, stamped into the owl:Ontology header of both modules. Must
# match CITATION.cff — eval/verify.py V7 fails the build if it drifts.
VERSION = "1.0.0"

# The version a term was first DECLARED in, recorded in its skos:note. This is
# deliberately not VERSION: every term in the EXT table below was introduced in
# v0.1.0, and the note is a provenance statement about that term's history, not
# a restatement of the current release. Bumping VERSION must not rewrite it.
TERM_VERSION = "0.1.0"

BASE = URIRef("https://w3id.org/shift/core")
VERSION_IRI = URIRef(f"https://w3id.org/shift/core/{VERSION}")


LEGACY_NS = "http://shift-ontology.org/"
CURRENT_NS = "https://w3id.org/shift/"


def rebase(term):
    """Map a legacy-namespace URIRef onto the w3id namespace; pass anything else
    through untouched (literals and blank nodes included)."""
    if isinstance(term, URIRef) and str(term).startswith(LEGACY_NS):
        return URIRef(CURRENT_NS + str(term)[len(LEGACY_NS):])
    return term


def header(g, iri, title, desc, version_iri):
    g.add((iri, RDF.type, OWL.Ontology))
    g.add((iri, OWL.versionIRI, version_iri))
    g.add((iri, OWL.versionInfo, Literal(VERSION)))
    g.add((iri, DCTERMS.title, Literal(title, lang="en")))
    g.add((iri, DCTERMS.description, Literal(desc, lang="en")))
    g.add((iri, DCTERMS.creator, Literal("Brian O'Regan")))
    g.add((iri, DCTERMS.publisher, Literal(
        "Tyndall National Institute / IERC, University College Cork")))
    g.add((iri, DCTERMS.license, URIRef(
        "https://creativecommons.org/licenses/by/4.0/")))
    g.add((iri, DCTERMS.issued, Literal("2026-07-15", datatype=XSD.date)))
    g.add((iri, DCTERMS.modified, Literal("2026-07-24", datatype=XSD.date)))
    g.add((iri, VANN.preferredNamespacePrefix, Literal("shift")))
    g.add((iri, VANN.preferredNamespaceUri, Literal(str(SHIFT))))
    g.add((iri, RDFS.comment, Literal(
        "Funded under the CET Partnership Joint Call 2023, ref Cetp-FP2023-00114. "
        "Co-funded by the European Commission (GA No. 101069750) and national "
        "funding organisations including SEAI (Ireland).", lang="en")))


# ---------------------------------------------------------------- core
def build_core():
    src = Graph()
    src.parse(str(SRC / "shift_combined_ontology_complete.owl"), format="xml")

    g = Graph()
    g.bind("shift", SHIFT); g.bind("owl", OWL); g.bind("dcterms", DCTERMS)
    g.bind("vann", VANN); g.bind("skos", SKOS)
    header(g, BASE, "SHIFT Ontology — Core",
           "Semantic Hierarchy for Intelligent Flexibility & Trading. Core TBox: "
           "actors, assets, flexibility services, contracts, trades, schedules, "
           "forecasts, tariffs, trade windows, nodes and platforms.",
           VERSION_IRI)

    # The legacy artefacts still carry the pre-rebase term namespace. Map it on
    # the way in, exactly as scripts/rebase_namespace.py did to the shipped TTL
    # (--from http://shift-ontology.org/ --to https://w3id.org/shift/). Without
    # this, re-running the generator silently reverts the release to the dead
    # namespace, which is a one-line change that invalidates every IRI.
    for t in src:
        g.add(tuple(rebase(x) for x in t))

    # -- fix 1: owl:Thing must not be asserted as a superclass target without decl
    # -- fix 2: dangling class references (declared nowhere, used as range)
    fixes = {
        SHIFT.GridService: ("GridService",
                            "Grid-facing service target of usedForGridStabilization. "
                            "Referenced as a range by FrequencyRegulationService in the "
                            "legacy artefacts but never declared; declared here to "
                            "restore OWL 2 DL consistency.",
                            SHIFT.FlexibilityService),
        SHIFT.FlexibilityProduct: ("FlexibilityProduct",
                                   "Tradable product abstraction referenced as a range in "
                                   "the legacy artefacts but never declared; declared here "
                                   "to restore OWL 2 DL consistency.",
                                   OWL.Thing),
    }
    for iri, (label, note, parent) in fixes.items():
        g.add((iri, RDF.type, OWL.Class))
        g.add((iri, RDFS.label, Literal(label, lang="en")))
        g.add((iri, RDFS.subClassOf, parent))
        g.add((iri, SKOS.note, Literal("Defect repair v0.1.0: " + note, lang="en")))
        g.add((iri, RDFS.isDefinedBy, BASE))

    # -- fix 3: multi-domain repair. The legacy TBox reuses property names
    # across unrelated classes (isDispatchable on 4, validatedBy on 6, ...)
    # by asserting several rdfs:domain triples. OWL semantics makes multiple
    # domains an INTERSECTION: any subject of the property is inferred to be
    # every listed class simultaneously — silent wrong inference. Repaired by
    # replacing the set with a single owl:unionOf class expression, which is
    # what the modeller plainly meant.
    from collections import defaultdict as _dd
    from rdflib.collection import Collection
    # rules RR-19/RR-34 apply isActive to FlexibilityService; widen before repair
    g.add((SHIFT.isActive, RDFS.domain, SHIFT.FlexibilityService))
    doms = _dd(set)
    for prop, d in g.subject_objects(RDFS.domain):
        doms[prop].add(d)
    repaired = 0
    for prop, ds in doms.items():
        if len(ds) < 2:
            continue
        for d in ds:
            g.remove((prop, RDFS.domain, d))
        u = BNode()
        g.add((u, RDF.type, OWL.Class))
        lst = BNode()
        Collection(g, lst, sorted(ds, key=str))
        g.add((u, OWL.unionOf, lst))
        g.add((prop, RDFS.domain, u))
        g.add((prop, SKOS.note, Literal(
            "Domain repair v0.1.1: legacy artefacts asserted "
            f"{len(ds)} separate rdfs:domain triples (intersection semantics); "
            "replaced with owl:unionOf.", lang="en")))
        repaired += 1
    print(f"  domain union-repair: {repaired} properties")

    # -- fix 4: same repair for multi-range OBJECT properties (ranges on
    # datatype properties are left alone; none are multiple). validatedBy with
    # ranges {SmartMeterAsset, FlexibilityServiceProvider} otherwise infers its
    # object to be both simultaneously.
    obj_props = set(g.subjects(RDF.type, OWL.ObjectProperty))
    rngs = _dd(set)
    for prop, r in g.subject_objects(RDFS.range):
        if prop in obj_props:
            rngs[prop].add(r)
    rrepaired = 0
    for prop, rs in rngs.items():
        if len(rs) < 2:
            continue
        for r in rs:
            g.remove((prop, RDFS.range, r))
        u = BNode(); lst = BNode()
        g.add((u, RDF.type, OWL.Class))
        Collection(g, lst, sorted(rs, key=str))
        g.add((u, OWL.unionOf, lst))
        g.add((prop, RDFS.range, u))
        g.add((prop, SKOS.note, Literal(
            "Range repair v0.1.1: legacy artefacts asserted "
            f"{len(rs)} separate rdfs:range triples (intersection semantics); "
            "replaced with owl:unionOf.", lang="en")))
        rrepaired += 1
    print(f"  range union-repair:  {rrepaired} properties")

    # Every NAMED class gets a label if it has none. Blank nodes are skipped:
    # the union class expressions built above are typed owl:Class, and labelling
    # them took str(bnode).split("#")[-1] — i.e. the bnode identifier itself —
    # producing 46 triples of the form `_:b rdfs:label "N6d576cc1eb..."@en`.
    # Those labels are meaningless, and because rdflib mints a fresh bnode id per
    # run they also made the TBox build non-reproducible: two builds of identical
    # input differed in 46 triples. An anonymous class expression has no name to
    # label and no defining ontology, so it gets neither.
    for c in set(g.subjects(RDF.type, OWL.Class)):
        if isinstance(c, BNode):
            continue
        if not list(g.objects(c, RDFS.label)):
            g.add((c, RDFS.label, Literal(str(c).split("#")[-1], lang="en")))
        g.add((c, RDFS.isDefinedBy, BASE))

    out = ROOT / "ontology" / "shift-core.ttl"
    g.serialize(destination=str(out), format="turtle")
    return g, out


# ---------------------------------------------------------------- ext
# (term, kind, domain, range, rules_requiring_it, comment)
C, OP, DP = "class", "op", "dp"
T = OWL.Thing

EXT = [
    # --- classes ---
    ("CommunityMarketCircle", C, None, SHIFT.Actor, "RR-16, RR-27",
     "A bounded trust/governance group of Actors within which trades may be "
     "fast-tracked. The legacy rule documentation asserts CMC 'is a defined "
     "concept in the ontology'; it was not."),
    ("FlexibilityBundle", C, None, T, "RR-34",
     "A geographically and temporally coherent group of FlexibilityService "
     "instances dispatched together."),
    ("DeliveryEvent", C, None, T, "RR-17, RR-26",
     "A single observed delivery of a FlexibilityService, carrying committed vs "
     "measured values and a timestamp. Required for any performance rule."),
    ("ActivationEvent", C, None, T, "RR-28",
     "A single activation attempt against an Asset, with outcome and timestamp."),
    ("BatteryAsset", C, None, SHIFT.StorageAsset, "RR-18, RR-21", ""),
    ("SolarPVAsset", C, None, SHIFT.GenerationAsset, "RR-18, RR-21", ""),
    ("HeatPumpAsset", C, None, SHIFT.ThermalAsset, "RR-18", ""),
    ("BaseDynamicPlan", C, None, SHIFT.TariffPlan, "RR-20", ""),

    # --- object properties ---
    ("ownsAsset", OP, SHIFT.Actor, SHIFT.Asset, "RR-00, RR-03, RR-20, RR-21",
     "The single most load-bearing relation in the rule set; undeclared in the "
     "legacy artefacts, which is why RR-00 could never have fired."),
    ("buyerActor", OP, SHIFT.FlexibilityTrade, SHIFT.Actor, "RR-16, RR-27", ""),
    ("sellerActor", OP, SHIFT.FlexibilityTrade, SHIFT.Actor, "RR-01, RR-16, RR-27", ""),
    ("assignedAsset", OP, SHIFT.FlexibilityTrade, SHIFT.Asset, "RR-07", ""),
    ("associatedActor", OP, SHIFT.FlexibilityContract, SHIFT.Actor, "RR-26", ""),
    ("associatedContract", OP, SHIFT.FlexibilityService, SHIFT.FlexibilityContract,
     "RR-09, RR-12", ""),
    ("backupTrade", OP, SHIFT.FlexibilityTrade, SHIFT.FlexibilityTrade, "RR-08",
     "Renamed from the documentation's 'backupTradeList': RDF has no list-valued "
     "object properties; multiplicity is expressed by repeated triples."),
    ("belongsToCMC", OP, SHIFT.Actor, SHIFT.CommunityMarketCircle, "RR-16, RR-27", ""),
    ("hasActivationEvent", OP, SHIFT.Asset, SHIFT.ActivationEvent, "RR-28", ""),
    ("hasDeliveryEvent", OP, SHIFT.FlexibilityService, SHIFT.DeliveryEvent, "RR-17", ""),
    ("hasTariffPlan", OP, SHIFT.Actor, SHIFT.TariffPlan, "RR-15, RR-20, RR-31", ""),
    ("linkedToService", OP, SHIFT.FlexibilityTrade, SHIFT.FlexibilityService, "RR-25", ""),
    ("linkedToTrade", OP, SHIFT.TariffPlan, SHIFT.FlexibilityTrade, "RR-31", ""),
    ("mutuallyTrusted", OP, SHIFT.Actor, SHIFT.Actor, "RR-16",
     "Symmetric. The documentation assumes symmetry; it is asserted here."),
    ("hasBundleMember", OP, SHIFT.FlexibilityBundle, SHIFT.FlexibilityService, "RR-34",
     "Renamed from the documentation's 'hasMember' (v0.1.1): core already "
     "declares hasMember with domain EnergyCommunity."),
    ("recommendedTariffPlan", OP, SHIFT.Actor, SHIFT.TariffPlan, "RR-20", ""),

    # --- datatype properties ---
    ("assetFunction", DP, SHIFT.Asset, XSD.string, "RR-00, RR-18",
     "One of consumption | generation | storage | thermal."),
    ("atRiskOfOvercommitment", DP, SHIFT.Node, XSD.boolean, "RR-19", ""),
    ("committedValue_kW", DP, SHIFT.DeliveryEvent, XSD.float, "RR-17, RR-19", ""),
    ("measuredResponse_kW", DP, SHIFT.DeliveryEvent, XSD.float, "RR-17", ""),
    ("eventTimestamp", DP, None, XSD.dateTime, "RR-17, RR-25, RR-28",
     "Domain left open: applies to DeliveryEvent and ActivationEvent."),
    ("eventStatus", DP, SHIFT.ActivationEvent, XSD.string, "RR-28", ""),
    ("tradeStatus", DP, SHIFT.FlexibilityTrade, XSD.string, "RR-01, RR-04, RR-06, RR-07, RR-08, RR-16, RR-22, RR-25, RR-27, RR-30", ""),
    ("tradeOutcome", DP, SHIFT.FlexibilityTrade, XSD.string, "RR-07, RR-08, RR-22", ""),
    ("tradeBlockReason", DP, SHIFT.FlexibilityTrade, XSD.string, "RR-27", ""),
    ("tradeRevenue_EUR", DP, SHIFT.FlexibilityTrade, XSD.float, "RR-31", ""),
    ("deliveryStartTime", DP, SHIFT.FlexibilityTrade, XSD.dateTime, "RR-22", ""),
    ("deliveryEndTime", DP, SHIFT.FlexibilityTrade, XSD.dateTime, "RR-04, RR-06, RR-12, RR-22", ""),
    ("hasMultiWindowApproval", DP, SHIFT.FlexibilityTrade, XSD.boolean, "RR-22", ""),
    ("hasCMCConsent", DP, SHIFT.FlexibilityTrade, XSD.boolean, "RR-27", ""),
    ("serviceStatus", DP, SHIFT.FlexibilityService, XSD.string, "RR-09, RR-25", ""),
    ("isUnderperforming", DP, SHIFT.FlexibilityService, XSD.boolean, "RR-17", ""),
    ("servicePerformanceScore", DP, SHIFT.FlexibilityService, XSD.decimal, "RR-12", ""),
    ("activationReason", DP, SHIFT.FlexibilityService, XSD.string, "RR-05", ""),
    ("activationWindowStart", DP, SHIFT.FlexibilityService, XSD.dateTime, "RR-34",
     "The documentation's 'activationWindow' is an interval; split into start/end "
     "because SPARQL/SWRL cannot compare opaque interval literals."),
    ("activationWindowEnd", DP, SHIFT.FlexibilityService, XSD.dateTime, "RR-34", ""),
    ("bundleActivationWindowStart", DP, SHIFT.FlexibilityBundle, XSD.dateTime, "RR-34", ""),
    ("bundleActivationWindowEnd", DP, SHIFT.FlexibilityBundle, XSD.dateTime, "RR-34", ""),
    ("contractEndDate", DP, SHIFT.FlexibilityContract, XSD.dateTime, "RR-09, RR-12", ""),
    ("contractDeliveryWindow_min", DP, SHIFT.FlexibilityContract, XSD.integer, "RR-26", ""),
    ("deliveryComplianceScore", DP, SHIFT.FlexibilityContract, XSD.decimal, "RR-26", ""),
    ("recommendRenewal", DP, SHIFT.FlexibilityService, XSD.boolean, "RR-12", ""),
    ("isFlexEligible", DP, SHIFT.ControlAsset, XSD.boolean, "RR-10", ""),
    ("isRemotelyControllable", DP, SHIFT.ControlAsset, XSD.boolean, "RR-10", ""),
    ("isControllable", DP, SHIFT.Asset, XSD.boolean, "RR-18", ""),
    ("isAvailable", DP, SHIFT.Asset, XSD.boolean, "RR-07", ""),
    ("isMobile", DP, SHIFT.Asset, XSD.boolean, "RR-18", ""),
    ("isStationary", DP, SHIFT.Asset, XSD.boolean, "RR-18", ""),
    ("canStoreEnergy", DP, SHIFT.Asset, XSD.boolean, "RR-18", ""),
    ("usesThermalEnergy", DP, SHIFT.Asset, XSD.boolean, "RR-18", ""),
    ("reliabilityStatus", DP, SHIFT.Asset, XSD.string, "RR-28", ""),
    ("lastReliabilityCheckDate", DP, SHIFT.Asset, XSD.dateTime, "RR-28", ""),
    ("nodeCategory", DP, SHIFT.Node, XSD.string, "RR-11", ""),
    ("predictedLoad_kW", DP, SHIFT.ForecastData, XSD.float, "RR-05", ""),
    ("eligibleForDynamicTariff", DP, SHIFT.Actor, XSD.boolean, "RR-03", ""),
    ("complianceScore", DP, SHIFT.Actor, XSD.decimal, "RR-14", ""),
    ("isCompliant", DP, SHIFT.Actor, XSD.boolean, "RR-26", ""),
    ("isTrustedAggregator", DP, SHIFT.Aggregator, XSD.boolean, "RR-14", ""),
    ("hasUnresolvedDisputes", DP, SHIFT.Actor, XSD.boolean, "RR-14", ""),
    ("averageDeliveryRate_percent", DP, SHIFT.Actor, XSD.decimal, "RR-14", ""),
    ("complianceAuditDate", DP, SHIFT.Actor, XSD.dateTime, "RR-14",
     "Renamed from the documentation's 'auditDate' / core's 'lastAuditDate' "
     "(v0.1.1): the core property of that name has domain "
     "PeerFlexClearingMechanism; reusing it for Actors would create an "
     "intersection-domain defect."),
    ("isAggregated", DP, SHIFT.Actor, XSD.boolean, "RR-24", ""),
    ("userType", DP, SHIFT.Actor, XSD.string, "RR-20", ""),
    ("avgMonthlyConsumption_kWh", DP, SHIFT.Actor, XSD.float, "RR-20, RR-21", ""),
    ("avgMonthlyGeneration_kWh", DP, SHIFT.Actor, XSD.float, "RR-21", ""),
    ("monthlyImport_kWh", DP, SHIFT.Actor, XSD.float, "RR-29", ""),
    ("monthlyExport_kWh", DP, SHIFT.Actor, XSD.float, "RR-29", ""),
    ("monthlyCarbonBalance_kgCO2", DP, SHIFT.Actor, XSD.float, "RR-33", ""),
    ("totalConsumption_kWh", DP, SHIFT.Actor, XSD.float, "RR-32", ""),
    ("fossilEnergy_kWh", DP, SHIFT.Actor, XSD.float, "RR-32", ""),
    ("sustainabilityScore", DP, SHIFT.Actor, XSD.decimal, "RR-32", ""),
    ("sustainabilityBadge", DP, SHIFT.Actor, XSD.string, "RR-33", ""),
    ("eligibleForGreenRewards", DP, SHIFT.Actor, XSD.boolean, "RR-33", ""),
    ("recommendGreenUpgrade", DP, SHIFT.Actor, XSD.boolean, "RR-32", ""),
    ("recommendBatteryStorage", DP, SHIFT.Actor, XSD.boolean, "RR-21", ""),
    ("recommendAggregatorEnrollment", DP, SHIFT.Actor, XSD.boolean, "RR-24", ""),
    ("totalMonthlyTradeVolume_kWh", DP, SHIFT.Actor, XSD.float, "RR-24", ""),
    ("eligibleForBonus", DP, SHIFT.Actor, XSD.boolean, "RR-29, RR-30", ""),
    ("bonusStatus", DP, SHIFT.Actor, XSD.string, "RR-30", ""),
    ("rewardEligibilityStatus", DP, SHIFT.Actor, XSD.string, "RR-29", ""),
    ("maxMonthlyTrades", DP, SHIFT.TariffPlan, XSD.integer, "RR-15", ""),
    ("tradeCapReached", DP, SHIFT.Actor, XSD.boolean, "RR-15", ""),
    ("hasDynamicPricing", DP, SHIFT.TariffPlan, XSD.boolean, "RR-23", ""),
    ("hasFlatRate", DP, SHIFT.TariffPlan, XSD.boolean, "RR-23", ""),
    ("hasTariffConflict", DP, SHIFT.TariffPlan, XSD.boolean, "RR-23", ""),
    ("conflictType", DP, SHIFT.TariffPlan, XSD.string, "RR-23", ""),
    ("tariffPerformanceStatus", DP, SHIFT.TariffPlan, XSD.string, "RR-31", ""),
    ("recommendTariffReview", DP, SHIFT.TariffPlan, XSD.boolean, "RR-31", ""),
    ("hasScheduleConflict", DP, SHIFT.FlexibilitySchedule, XSD.boolean, "RR-13", ""),
    ("latitude_deg", DP, SHIFT.FlexibilityService, XSD.decimal, "RR-34",
     "geoDistance in the documentation is a computed function, not a stored "
     "property; coordinates are stored and distance computed at query time."),
    ("longitude_deg", DP, SHIFT.FlexibilityService, XSD.decimal, "RR-34", ""),
]

EXT_BASE = URIRef("https://w3id.org/shift/ext")


def build_ext():
    g = Graph()
    g.bind("shift", SHIFT); g.bind("owl", OWL); g.bind("dcterms", DCTERMS)
    g.bind("skos", SKOS); g.bind("vann", VANN)
    header(g, EXT_BASE, "SHIFT Ontology — Rule Vocabulary Extension",
           "Vocabulary referenced by reasoning rules SHIFT-RR-00 to SHIFT-RR-34 "
           "but not declared in the legacy SHIFT artefacts. Without this module "
           "no SHIFT rule can be evaluated, because the terms in the rule bodies "
           "do not resolve.", URIRef(f"https://w3id.org/shift/ext/{VERSION}"))
    g.add((EXT_BASE, OWL.imports, BASE))

    kindmap = {C: OWL.Class, OP: OWL.ObjectProperty, DP: OWL.DatatypeProperty}
    for name, kind, dom, rng, rules, comment in EXT:
        iri = SHIFT[name]
        g.add((iri, RDF.type, kindmap[kind]))
        g.add((iri, RDFS.label, Literal(name, lang="en")))
        g.add((iri, RDFS.isDefinedBy, EXT_BASE))
        g.add((iri, SKOS.note, Literal(
            f"Declared in SHIFT v{TERM_VERSION} to support {rules}. "
            f"Not present in the pre-v{TERM_VERSION} artefacts.", lang="en")))
        if comment:
            g.add((iri, RDFS.comment, Literal(comment, lang="en")))
        if kind == C:
            g.add((iri, RDFS.subClassOf, rng if rng is not None else T))
        else:
            if dom is not None:
                g.add((iri, RDFS.domain, dom))
            g.add((iri, RDFS.range, rng))
    g.add((SHIFT.mutuallyTrusted, RDF.type, OWL.SymmetricProperty))

    # Added in v1.0.0, after the EXT table above was locked at v0.1.0, so it is
    # declared here rather than in that table: its skos:note has to record v1.0.0
    # while every entry in EXT records v0.1.0. Closes the one genuine VOCABULARY
    # gap found by the CQ sweep (CQ-20 was vacuous without it).
    g.add((SHIFT.forecastForNode, RDF.type, OWL.ObjectProperty))
    g.add((SHIFT.forecastForNode, RDFS.label, Literal("forecastForNode", lang="en")))
    g.add((SHIFT.forecastForNode, RDFS.isDefinedBy, EXT_BASE))
    g.add((SHIFT.forecastForNode, RDFS.domain, SHIFT.ForecastData))
    g.add((SHIFT.forecastForNode, RDFS.range, SHIFT.Node))
    g.add((SHIFT.forecastForNode, RDFS.comment, Literal(
        "Associates a forecast with the grid node it forecasts for. Before this "
        "term SHIFT had no property relating ForecastData to Node in either "
        "direction: informedByForecast has domain ControlAsset or TradeWindow, "
        "linkedToForecast Asset or FlexibilitySchedule, referencedInForecast "
        "TariffPlan, and usedInForecast SensorAsset or SmartMeterAsset. The only "
        "available route was the two-hop indirection ForecastData -> "
        "FlexibilityService -> Node.", lang="en")))
    g.add((SHIFT.forecastForNode, SKOS.note, Literal(
        "Declared in SHIFT v1.0.0 to support CQ-20 (RR-02, RR-05). "
        "Not present in the pre-v1.0.0 artefacts.", lang="en")))

    out = ROOT / "ontology" / "shift-ext.ttl"
    g.serialize(destination=str(out), format="turtle")
    return g, out


if __name__ == "__main__":
    core, cpath = build_core()
    ext, epath = build_ext()
    n = lambda k, gg: len({s for s in gg.subjects(RDF.type, k)
                           if isinstance(s, URIRef)})  # exclude union bnodes
    print(f"core -> {cpath}")
    print(f"   triples {len(core)}  classes {n(OWL.Class, core)}  "
          f"objprops {n(OWL.ObjectProperty, core)}  dataprops {n(OWL.DatatypeProperty, core)}")
    print(f"ext  -> {epath}")
    print(f"   triples {len(ext)}   classes {n(OWL.Class, ext)}  "
          f"objprops {n(OWL.ObjectProperty, ext)}  dataprops {n(OWL.DatatypeProperty, ext)}")

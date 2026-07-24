#!/usr/bin/env python3
"""
build_comparison_graphs.py -- map the enriched SHIFT scenario into SAREF Core
v4.1.1 and into SEAS, and record what the mapping cost.

Method note 3 requires the same test graph in each vocabulary. Three rules keep
the comparison honest:

1. SAME INSTANCE IRIs. Every graph reuses the kg: individuals from
   shift-kg-aran.ttl, so a gold row is directly comparable across ontologies.
   Only the vocabulary changes.

2. MAP ONLY WHAT THE VOCABULARY LEGITIMATELY EXPRESSES. No term is invented in
   SAREF or SEAS, and no term is used outside its declared domain and range.
   Anything the target cannot say is left out and recorded in the mapping
   report rather than smuggled in under a loosely-related term.

3. THE SCENARIO IS LARGER THAN ANY ONE ONTOLOGY. Group F (CQ-21..24) asks about
   electrical topology, command sequences, observation history and actor
   activities. Those facts are part of the modelled situation but SHIFT cannot
   represent them -- that is precisely what group F tests. They are declared
   here, in SCENARIO_EXTENSION, so that SAREF and SEAS can be scored on them
   against a real answer instead of against SHIFT's empty result.

Usage:
    .venv/bin/python scripts/build_comparison_graphs.py
"""
import json
import pathlib

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

REPO = pathlib.Path(__file__).resolve().parent.parent

KG = Namespace("https://w3id.org/shift/kg/")
SHIFT = Namespace("https://w3id.org/shift/core#")
SAREF = Namespace("https://saref.etsi.org/core/")
SEAS = Namespace("https://w3id.org/seas/")
TIME = Namespace("http://www.w3.org/2006/time#")

OUT = REPO / "comparison"

# --------------------------------------------------------------------------
# Scenario facts that SHIFT cannot express. Deterministic, and the gold answers
# for CQ-21..24 are derived from exactly these.
# --------------------------------------------------------------------------
SCENARIO_EXTENSION = {
    # CQ-21: electrical connectivity. Both assets sit at node Inishmore and are
    # wired to it, so a path LOAD-000 -- Inishmore -- METER-000 exists.
    "topology": [
        ("asset/LOAD-000", "node/Inishmore"),
        ("asset/METER-000", "node/Inishmore"),
        ("asset/PV-001", "node/Inishmaan"),
    ],
    # CQ-22: the command sequence implementing a curtailment on service S000.
    "commands": [
        ("command/CURT-1", "SetPointReduce", 1),
        ("command/CURT-2", "ConfirmReduction", 2),
        ("command/CURT-3", "ReleaseSetPoint", 3),
    ],
    "command_service": "service/S000",
    "command_device": "asset/CTRL-000",
    # CQ-23: an observation history for one meter, so a value at a given time
    # is recoverable rather than overwritten.
    "observations": [
        ("obs/METER-000-1", "property/ActivePower", 2.4, "2026-03-05T11:30:00"),
        ("obs/METER-000-2", "property/ActivePower", 3.1, "2026-03-05T12:00:00"),
        ("obs/METER-000-3", "property/ActivePower", 2.8, "2026-03-05T12:30:00"),
    ],
    "observation_device": "asset/METER-000",
    # CQ-24: activities actor A000 is performing.
    "activities": [
        ("activity/FC-000", "Forecasting"),
        ("activity/PL-000", "Planning"),
        ("activity/OP-000", "Optimization"),
    ],
    "activity_actor": "actor/A000",
}


def u(local):
    return KG[local]


class Mapper:
    def __init__(self, shift_graph):
        self.s = shift_graph
        self.report = {}

    def _rec(self, target, mapped, unmapped):
        self.report[target] = {
            "term_mappings": mapped,
            "not_representable": unmapped,
            "term_mapping_count": len(mapped),
            "not_representable_count": len(unmapped),
        }

    # ------------------------------------------------------------------ SAREF
    def saref(self):
        g = Graph()
        g.bind("saref", SAREF)
        g.bind("kg", KG)

        mapped = [
            "shift:Asset -> saref:Device",
            "shift:SmartMeterAsset -> saref:Meter",
            "shift:ControlAsset -> saref:Actuator",
            "shift:assetID -> saref:hasIdentifier",
            "shift:operatingStatus -> saref:hasState + saref:State individual",
            "control command sequence -> saref:Function / saref:Command / saref:hasCommand",
            "activation event -> saref:CommandExecution + saref:hasTimestamp",
            "meter reading -> saref:PropertyValue (isValueOfProperty, hasValue, hasTimestamp)",
            "observed quantity -> saref:Property, linked by saref:hasProperty",
        ]
        unmapped = [
            "shift:Actor and all subclasses -- SAREF Core has no agent, person or organisation class",
            "shift:ownsAsset -- no ownership property in SAREF Core",
            "shift:Node / shift:locatedAt -- no siting or topology term in SAREF Core (saref4bldg:BuildingSpace is an extension)",
            "shift:CommunityMarketCircle, shift:belongsToCMC, shift:mutuallyTrusted -- no group or trust model",
            "shift:FlexibilityTrade and all trade properties -- no market transaction class",
            "shift:FlexibilityContract, shift:penaltyRate_EURperkWh -- no contract class",
            "shift:TariffPlan structure (isDynamic / hasFlatRate) -- saref:Profile carries a price via profileHasPrice but no tariff structure",
            "shift:ForecastData -- no forecast class",
            "shift:canStoreEnergy, shift:responseTime_ms -- no storage-capability or response-time property (s4ener territory)",
            "shift:BuildingAsset -- no building class in SAREF Core (saref4bldg:Building is an extension)",
            "shift:eventStatus on activations -- saref:CommandExecution has no outcome or status property",
            "command ordering -- SAREF Core has no sequence or step property",
            "shift:Aggregator participation criteria -- no compliance, trust or prequalification terms",
        ]

        # Devices
        for a, _, cls in self.s.triples((None, RDF.type, None)):
            if not str(a).startswith(str(KG) + "asset/"):
                continue
            local = str(cls).split("#")[-1]
            if local == "SmartMeterAsset":
                g.add((a, RDF.type, SAREF.Meter))
            elif local == "ControlAsset":
                g.add((a, RDF.type, SAREF.Actuator))
            elif local.endswith("Asset"):
                g.add((a, RDF.type, SAREF.Device))
        for a, _, v in self.s.triples((None, SHIFT.assetID, None)):
            g.add((a, SAREF.hasIdentifier, Literal(str(v), datatype=XSD.string)))
        # Operating status as a saref:State individual
        online = KG["state/Online"]
        g.add((online, RDF.type, SAREF.State))
        for a, _, v in self.s.triples((None, SHIFT.operatingStatus, None)):
            if str(v) == "Online":
                g.add((a, SAREF.hasState, online))

        # Activation events -> CommandExecution. Outcome is NOT mapped: SAREF
        # Core has no term for it, which is what makes CQ-08 partial.
        for asset, _, ev in self.s.triples((None, SHIFT.hasActivationEvent, None)):
            g.add((ev, RDF.type, SAREF.CommandExecution))
            g.add((ev, SAREF.madeBy, asset))
            for _, _, ts in self.s.triples((ev, SHIFT.eventTimestamp, None)):
                g.add((ev, SAREF.hasTimestamp, Literal(str(ts), datatype=XSD.dateTime)))

        # CQ-22 command sequence
        fn = KG["function/Curtailment"]
        g.add((fn, RDF.type, SAREF.Function))
        dev = u(SCENARIO_EXTENSION["command_device"])
        g.add((dev, SAREF.hasFunction, fn))
        for local, label, _order in SCENARIO_EXTENSION["commands"]:
            c = u(local)
            g.add((c, RDF.type, SAREF.Command))
            g.add((c, SAREF.isCommandOf, fn))
            g.add((fn, SAREF.hasCommand, c))
            g.add((c, RDFS.label, Literal(label, lang="en")))
            # NOTE: the step order (1,2,3) is deliberately NOT written. SAREF
            # Core has no ordering property; inventing one would fake the result.

        # CQ-23 observation history
        odev = u(SCENARIO_EXTENSION["observation_device"])
        for local, prop, val, ts in SCENARIO_EXTENSION["observations"]:
            pv, p = u(local), u(prop)
            g.add((p, RDF.type, SAREF.Property))
            g.add((odev, SAREF.hasProperty, p))
            g.add((pv, RDF.type, SAREF.PropertyValue))
            g.add((pv, SAREF.isValueOfProperty, p))
            g.add((pv, SAREF.hasValue, Literal(val, datatype=XSD.float)))
            g.add((pv, SAREF.hasTimestamp, Literal(ts, datatype=XSD.dateTime)))
            g.add((odev, SAREF.hasPropertyValue, pv))

        self._rec("saref", mapped, unmapped)
        self.saref_core_graph = g
        return g

    # -------------------------------------------------- SAREF Core + extensions
    def saref_ext(self):
        """Core mapping plus everything SAREF4ENER v2.1.1 and SAREF4BLDG v2.1.1
        add. Same rules: no invented terms, nothing used outside its declared
        domain and range."""
        # COPY the Core mapping -- mutating it in place would contaminate the
        # Core-only column, which exists precisely to show what the extensions add.
        g = Graph()
        for t in self.saref_core_graph:
            g.add(t)
        S4E = Namespace("https://saref.etsi.org/saref4ener/")
        S4B = Namespace("https://saref.etsi.org/saref4bldg/")
        g.bind("s4ener", S4E)
        g.bind("s4bldg", S4B)

        mapped = list(self.report["saref"]["term_mappings"]) + [
            "shift:BatteryAsset -> s4bldg:ElectricFlowStorageDevice + s4ener:Storage",
            "shift:EVAsset -> s4ener:Storage",
            "shift:SolarPVAsset -> s4bldg:SolarDevice",
            "shift:ControlAsset -> s4bldg:Controller",
            "shift:BuildingAsset -> s4bldg:Building",
            "shift:connectedToBuilding -> s4bldg:contains",
            "asset function -> s4ener:hasRole + s4ener:Role with s4ener:hasRoleType "
            "(EnergyConsumer / EnergyProducer / EnergyStorage)",
            "shift:responseTime_ms -> s4ener:hasActivationDelay (xsd:duration, no declared domain)",
            "activation outcome -> s4ener:hasInstructionStatus with the s4ener "
            "InstructionStatus individuals Succeeded / Aborted -- the term SAREF Core lacks",
            "activation event -> s4ener:FlexibilityInstruction + s4ener:hasExecutionTime",
            "command order -> s4ener:hasIndex (xsd:integer, no declared domain, "
            "purpose is indexing array elements) -- the ordering SAREF Core lacks",
        ]
        unmapped = [
            "shift:Actor and all subclasses -- neither extension adds an agent, person or "
            "organisation class. s4ener:Role is a DEVICE role codelist (EnergyConsumer, "
            "EnergyProducer, EnergyStorage) and s4ener:hasRole has domain saref:Device, so it "
            "cannot carry an actor's market role",
            "shift:ownsAsset -- still no ownership property",
            "shift:marketRole -- s4ener:hasRole has domain saref:Device, not an agent",
            "shift:Node / shift:locatedAt -- s4bldg adds Building and BuildingSpace, which are "
            "spatial containers, not grid nodes; there is still no network-node term",
            "shift:HeatPumpAsset -- NEITHER extension declares a heat-pump class (0 occurrences "
            "in both files); the nearest is the much broader s4bldg:EnergyConversionDevice, "
            "which also subsumes s4bldg:SolarDevice",
            "shift:CommunityMarketCircle, belongsToCMC, mutuallyTrusted -- no group or trust model",
            "shift:FlexibilityTrade and all trade properties -- s4ener:FlexOffer/FlexRequest "
            "describe flexibility offers, not concluded trades with parties, status and consent",
            "shift:FlexibilityContract -- s4ener:ContractualPowerLimit is a limit, not a contract; "
            "no contract class, end date, governed service or penalty rate",
            "shift:TariffPlan isDynamic / hasFlatRate -- s4ener:IncentiveTableProfile and "
            "IncentiveType give tariff structure but no flat-versus-dynamic flags that could contradict",
            "shift:totalDERCapacity_kW on a node -- no DER-capacity property",
            "electrical connectivity -- s4bldg:contains is spatial containment, not connection",
            "actor activities -- no Activity taxonomy in either extension",
        ]

        by_kind = {}
        for a, _, cls in self.s.triples((None, RDF.type, None)):
            by_kind.setdefault(str(cls).split("#")[-1], []).append(a)

        for cls, targets in {
            "BatteryAsset": [S4B.ElectricFlowStorageDevice, S4E.Storage],
            "EVAsset": [S4E.Storage],
            "SolarPVAsset": [S4B.SolarDevice],
            "HeatPumpAsset": [S4B.EnergyConversionDevice],
            "ControlAsset": [S4B.Controller],
            "BuildingAsset": [S4B.Building],
        }.items():
            for a in by_kind.get(cls, []):
                for t in targets:
                    g.add((a, RDF.type, t))

        # Device roles from the asset function
        ROLE = {"consumption": "EnergyConsumer", "generation": "EnergyProducer",
                "storage": "EnergyStorage"}
        for a, _, fn in self.s.triples((None, SHIFT.assetFunction, None)):
            rt = ROLE.get(str(fn))
            if not rt:
                continue
            role = URIRef(str(a) + "/role")
            g.add((role, RDF.type, S4E.Role))
            g.add((role, S4E.hasRoleType, S4E[rt]))
            g.add((a, S4E.hasRole, role))

        # Response time
        for a, _, ms in self.s.triples((None, SHIFT.responseTime_ms, None)):
            g.add((a, S4E.hasActivationDelay,
                   Literal(f"PT{int(ms) / 1000:.3f}S", datatype=XSD.duration)))

        # Activation outcome -- the term Core lacked
        for asset, _, ev in self.s.triples((None, SHIFT.hasActivationEvent, None)):
            g.add((ev, RDF.type, S4E.FlexibilityInstruction))
            for _, _, st in self.s.triples((ev, SHIFT.eventStatus, None)):
                g.add((ev, S4E.hasInstructionStatus,
                       S4E.Aborted if str(st) == "Failed" else S4E.Succeeded))
            for _, _, ts in self.s.triples((ev, SHIFT.eventTimestamp, None)):
                g.add((ev, S4E.hasExecutionTime,
                       Literal(str(ts), datatype=XSD.dateTimeStamp)))

        # Buildings contain their devices
        for asset, _, b in self.s.triples((None, SHIFT.connectedToBuilding, None)):
            g.add((b, S4B.contains, asset))

        # Command order -- the ordering Core lacked
        for local, _label, order in SCENARIO_EXTENSION["commands"]:
            g.add((u(local), S4E.hasIndex, Literal(order, datatype=XSD.integer)))

        self._rec("saref_ext", mapped, unmapped)
        return g

    # ------------------------------------------------------------------- SEAS
    def seas(self):
        g = Graph()
        g.bind("seas", SEAS)
        g.bind("kg", KG)
        g.bind("time", TIME)

        mapped = [
            "shift:Actor -> seas:Actor / seas:ElectricityPlayer",
            "shift:Aggregator -> seas:Aggregator",
            "shift:ownsAsset -> seas:owns",
            "shift:LoadAsset -> seas:ElectricPowerConsumer",
            "shift:SolarPVAsset -> seas:PhotovoltaicPanel (+ seas:ElectricPowerProducer)",
            "shift:BatteryAsset -> seas:Battery (+ seas:ElectricPowerStorageSystem)",
            "shift:EVAsset -> seas:ElectricVehicle (+ seas:ElectricPowerStorageSystem)",
            "shift:HeatPumpAsset -> seas:HeatPump",
            "shift:BuildingAsset -> seas:Building",
            "shift:connectedToBuilding -> seas:hasPart (building contains device)",
            "shift:Node -> seas:ElectricPowerSystem",
            "electrical connectivity -> seas:connectedTo (System->System, symmetric)",
            "meter reading -> seas:Evaluation (evaluatedValue) + seas:temporalContext -> time:Instant",
            "observed quantity -> seas:Property, linked by seas:hasProperty",
            "actor activity -> seas:ForecastingActivity / PlanningActivity / OptimizationActivity, attached only by the untyped seas:contains",
            "shift:FlexibilityContract -> seas:Contract (class only)",
            "shift:marketRole -> seas:hasRole + seas:Role individual",
        ]
        unmapped = [
            "shift:contractEndDate / shift:associatedContract direction -- seas:Contract carries only seas:player (Contract -> Actor); no dates and no governed service",
            "shift:CommunityMarketCircle / belongsToCMC -- SEAS has seas:GroupManager but no group or community class and no membership property",
            "shift:mutuallyTrusted -- no trust relation",
            "shift:FlexibilityTrade parties, volume, price, status -- seas:Transaction/Bid/Offer are bare seas:MarketArtifact subclasses with no properties at all",
            "shift:tradeStatus, shift:hasCMCConsent -- no status or consent term",
            "shift:assignedToWindow / shift:TradeWindow -- no market-window class linking transactions to a clearing period",
            "shift:backupTrade -- no replacement or backup relation",
            "shift:penaltyRate_EURperkWh -- no penalty term",
            "shift:isDynamic / hasFlatRate -- no tariff-structure flags",
            "shift:isAvailable -- the seas operating codelist carries ratings (op-Nominal, op-Min, op-Maximum-*), not availability",
            "shift:responseTime_ms -- no response-time property",
            "shift:eventStatus on activations -- seas:failure marks a failed feature but there is no activation-attempt event to divide by",
            "shift:predictedLoad_kW bound to a node -- seas forecasting is weather-specific (WeatherForecast, WeatherForecasting); no load forecast for a node",
            "shift:totalDERCapacity_kW -- no DER-capacity property on a node",
            "actor -> activity agency -- no property has domain seas:Actor or range seas:Activity; only the untyped transitive seas:contains is available",
            "device command sequence -- no Command class and no ordering property (ControlActivity expresses the act, not the instruction)",
        ]

        CLASS_MAP = {
            "LoadAsset": [SEAS.ElectricPowerConsumer],
            "SolarPVAsset": [SEAS.PhotovoltaicPanel, SEAS.ElectricPowerProducer],
            "BatteryAsset": [SEAS.Battery, SEAS.ElectricPowerStorageSystem],
            "EVAsset": [SEAS.ElectricVehicle, SEAS.ElectricPowerStorageSystem],
            "HeatPumpAsset": [SEAS.HeatPump],
            "SmartMeterAsset": [SEAS.Device],
            "ControlAsset": [SEAS.Device],
            "BuildingAsset": [SEAS.Building],
        }
        for a, _, cls in self.s.triples((None, RDF.type, None)):
            local = str(cls).split("#")[-1]
            for target in CLASS_MAP.get(local, []):
                g.add((a, RDF.type, target))

        # Actors and ownership
        for a in self.s.subjects(RDF.type, SHIFT.Consumer):
            g.add((a, RDF.type, SEAS.ElectricityPlayer))
        for a, _, asset in self.s.triples((None, SHIFT.ownsAsset, None)):
            g.add((a, SEAS.owns, asset))
        # Aggregators
        for a in self.s.subjects(RDF.type, SHIFT.Aggregator):
            g.add((a, RDF.type, SEAS.Aggregator))

        # Buildings contain their devices
        for asset, _, b in self.s.triples((None, SHIFT.connectedToBuilding, None)):
            g.add((b, SEAS.hasPart, asset))

        # Nodes as electric power systems, assets wired to them
        for n in self.s.subjects(RDF.type, SHIFT.Node):
            g.add((n, RDF.type, SEAS.ElectricPowerSystem))
        for local_a, local_n in SCENARIO_EXTENSION["topology"]:
            a, n = u(local_a), u(local_n)
            g.add((a, RDF.type, SEAS.ElectricPowerSystem))
            g.add((a, SEAS.connectedTo, n))
            g.add((n, SEAS.connectedTo, a))   # seas:connectedTo is symmetric

        # Contracts
        for s_, _, c in self.s.triples((None, SHIFT.associatedContract, None)):
            g.add((c, RDF.type, SEAS.Contract))

        # Market roles. seas:hasRole has range seas:Role and no declared domain,
        # so attaching a role to an actor is within the vocabulary. The region
        # half of CQ-03 remains unmappable, which is what keeps it PARTIAL.
        for a, _, role_name in self.s.triples((None, SHIFT.marketRole, None)):
            role = URIRef(str(a) + "/role")
            g.add((role, RDF.type, SEAS.Role))
            g.add((role, RDFS.label, Literal(str(role_name), lang="en")))
            g.add((a, SEAS.hasRole, role))

        # CQ-23 observation history as time-contextualised evaluations
        odev = u(SCENARIO_EXTENSION["observation_device"])
        for local, prop, val, ts in SCENARIO_EXTENSION["observations"]:
            ev, p = u(local), u(prop)
            inst = URIRef(str(ev) + "/instant")
            g.add((p, RDF.type, SEAS.Property))
            g.add((odev, SEAS.hasProperty, p))
            g.add((p, SEAS.evaluation, ev))
            g.add((ev, RDF.type, SEAS.TimeContextualizedEvaluation))
            g.add((ev, SEAS.evaluationOf, p))
            g.add((ev, SEAS.evaluatedValue, Literal(val, datatype=XSD.float)))
            g.add((ev, SEAS.temporalContext, inst))
            g.add((inst, RDF.type, TIME.Instant))
            g.add((inst, TIME.inXSDDateTime, Literal(ts, datatype=XSD.dateTime)))

        # CQ-24 activities. Attached with the generic seas:contains because SEAS
        # declares no actor-to-activity property -- that is the finding, so the
        # weakness of the link is preserved rather than papered over.
        actor = u(SCENARIO_EXTENSION["activity_actor"])
        act_cls = {"Forecasting": SEAS.ForecastingActivity,
                   "Planning": SEAS.PlanningActivity,
                   "Optimization": SEAS.OptimizationActivity}
        for local, kind in SCENARIO_EXTENSION["activities"]:
            act = u(local)
            g.add((act, RDF.type, act_cls[kind]))
            g.add((actor, SEAS.contains, act))

        self._rec("seas", mapped, unmapped)
        return g


def scenario_gold():
    """Gold answers for CQ-21..24, from SCENARIO_EXTENSION alone."""
    ext = SCENARIO_EXTENSION
    return {
        # path exists between the two co-located assets
        "CQ-21": [[str(u("asset/LOAD-000")), str(u("asset/METER-000"))]],
        # the three curtailment commands WITH their step order. The order is
        # part of the answer -- the question asks for a sequence -- so an
        # ontology that can only return the unordered set does not answer it.
        "CQ-22": sorted([[str(u(l)), order] for l, _lab, order in ext["commands"]]),
        # the reading of ActivePower on METER-000 at 12:00
        "CQ-23": [[str(u(ext["observation_device"])),
                   str(u("property/ActivePower")), 3.1,
                   "2026-03-05T12:00:00"]],
        # the three activities of A000
        "CQ-24": sorted([[str(u(l))] for l, _k in ext["activities"]]),
    }


def main():
    OUT.mkdir(exist_ok=True)
    shift = Graph()
    shift.parse(REPO / "shift-kg" / "kg" / "shift-kg-aran.ttl", format="turtle")

    m = Mapper(shift)
    sa = m.saref()
    sx = m.saref_ext()
    se = m.seas()
    sa.serialize(destination=str(OUT / "saref-test.ttl"), format="turtle")
    sx.serialize(destination=str(OUT / "saref-ext-test.ttl"), format="turtle")
    se.serialize(destination=str(OUT / "seas-test.ttl"), format="turtle")

    gold = scenario_gold()
    json.dump(gold, open(OUT / "scenario_gold.json", "w"), indent=1)

    report = {
        "source_graph": "kg/shift-kg-aran.ttl",
        "source_triples": len(shift),
        "scenario_extension": {
            "why": "Facts the modelled situation contains that SHIFT cannot "
                   "express. Group F is scored against these, not against "
                   "SHIFT's empty result.",
            "topology_links": len(SCENARIO_EXTENSION["topology"]),
            "commands": len(SCENARIO_EXTENSION["commands"]),
            "observations": len(SCENARIO_EXTENSION["observations"]),
            "activities": len(SCENARIO_EXTENSION["activities"]),
        },
        "saref": {**m.report["saref"], "triples": len(sa),
                  "vocabulary": "SAREF Core v4.1.1 (external/saref.ttl)"},
        "saref_ext": {**m.report["saref_ext"], "triples": len(sx),
                      "vocabulary": "SAREF Core v4.1.1 + SAREF4ENER v2.1.1 + "
                                    "SAREF4BLDG v2.1.1, merged as one vocabulary "
                                    "(external/saref.ttl, saref4ener.ttl, saref4bldg.ttl)"},
        "seas": {**m.report["seas"], "triples": len(se),
                 "vocabulary": "SEAS merged closure, 40 modules "
                               "(external/seas-modules/), StatisticsVocabulary "
                               "excluded -- truncated upstream, see "
                               "external/PROVENANCE.md"},
    }
    (REPO / "results").mkdir(exist_ok=True)
    json.dump(report, open(REPO / "results" / "mapping_effort.json", "w"), indent=1)

    print(f"SHIFT source          {len(shift):6} triples")
    print(f"comparison/saref-test.ttl  {len(sa):6} triples   "
          f"{len(m.report['saref']['term_mappings'])} mappings, "
          f"{len(m.report['saref']['not_representable'])} gaps")
    print(f"comparison/saref-ext-test.ttl {len(sx):6} triples   "
          f"{len(m.report['saref_ext']['term_mappings'])} mappings, "
          f"{len(m.report['saref_ext']['not_representable'])} gaps")
    print(f"comparison/seas-test.ttl   {len(se):6} triples   "
          f"{len(m.report['seas']['term_mappings'])} mappings, "
          f"{len(m.report['seas']['not_representable'])} gaps")
    print("wrote results/mapping_effort.json, comparison/scenario_gold.json")


if __name__ == "__main__":
    main()

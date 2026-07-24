# Competency-question coverage: SHIFT vs SAREF vs SEAS

Legend: **✓ ANSWERABLE** — returns the gold answer with every constraint enforced by the query. **~ PARTIAL** — needs a vocabulary extension or host-side computation; the missing term is named. **✗ NOT-EXPRESSIBLE** — the concept the question turns on is absent; it is named.

- **SHIFT** v1.0, `shift-kg/kg/shift-kg-aran.ttl` (11607 triples)
- **SAREF Core** v4.1.1, `external/saref.ttl` — mapped graph 1253 triples, 9 term mappings, 13 recorded gaps
- **SAREF Core+ext** = Core v4.1.1 + SAREF4ENER v2.1.1 + SAREF4BLDG v2.1.1, merged as one vocabulary — mapped graph 2474 triples, 20 term mappings, 12 recorded gaps. Both extensions version independently of Core and their latest published version is v2.1.1, not v4.1.1.
- **SEAS** merged closure, 40 modules — mapped graph 425 triples, 17 term mappings, 16 recorded gaps. StatisticsVocabulary is excluded: it is truncated upstream (see `external/PROVENANCE.md`).

All three graphs use the **same instance IRIs**, so a gold row is directly comparable across ontologies; only the vocabulary changes. Group F is scored against scenario facts SHIFT cannot represent (topology, command order, observation history, actor activities), not against SHIFT's empty result.

## Matrix

| CQ | Group | SHIFT | SAREF Core | SAREF Core+ext | SEAS |
|---|---|:--:|:--:|:--:|:--:|
| | **A — Actors and roles** | | | | |
| CQ-01 | A | ✓ | ✗ | ✗ | ✓ |
| CQ-02 | A | ✓ | ✗ | ✗ | ~ |
| CQ-03 | A | ✓ | ✗ | ✗ | ~ |
| CQ-04 | A | ✓ | ✗ | ✗ | ✗ |
| CQ-05 | A | ✓ | ✗ | ✗ | ~ |
| | **B — Assets and flexibility** | | | | |
| CQ-06 | B | ✓ | ~ | ~ | ~ |
| CQ-07 | B | ✓ | ✗ | ~ | ~ |
| CQ-08 | B | ✓ | ~ | ✓ | ~ |
| CQ-09 | B | ✓ | ✗ | ~ | ✓ |
| | **C — Services, contracts, obligations** | | | | |
| CQ-10 | C | ✓ | ✗ | ~ | ~ |
| CQ-11 | C | ✓ | ✗ | ~ | ~ |
| CQ-12 | C | ✓ | ✗ | ✗ | ~ |
| CQ-13 | C | ✓ | ✗ | ✗ | ~ |
| | **D — Trading and market operations** | | | | |
| CQ-14 | D | ✓ | ✗ | ✗ | ✗ |
| CQ-15 | D | ✓ | ✗ | ✗ | ✗ |
| CQ-16 | D | ✓ | ✗ | ✗ | ✗ |
| CQ-17 | D | ✓ | ✗ | ~ | ~ |
| | **E — Tariffs, pricing, forecasts** | | | | |
| CQ-18 | E | ✓ | ✗ | ✗ | ~ |
| CQ-19 | E | ✓ | ✗ | ~ | ✗ |
| CQ-20 | E | ✓ | ✗ | ~ | ~ |
| | **F — Expected losses for SHIFT** | | | | |
| CQ-21 | F | ✗ | ✗ | ✗ | ✓ |
| CQ-22 | F | ✗ | ~ | ✓ | ~ |
| CQ-23 | F | ✗ | ✓ | ✓ | ✓ |
| CQ-24 | F | ✗ | ✗ | ✗ | ~ |
| | **G — Added in self-review** | | | | |
| CQ-25 | G | ✓ | ✗ | ✗ | ✗ |
| CQ-26 | G | ✓ | ✗ | ✗ | ✗ |

## Subtotals by group

| Group | n | SHIFT ✓/~/✗ | SAREF Core ✓/~/✗ | SAREF Core+ext ✓/~/✗ | SEAS ✓/~/✗ |
|---|--:|:--:|:--:|:--:|:--:|
| A — Actors and roles | 5 | 5/0/0 | 0/0/5 | 0/0/5 | 1/3/1 |
| B — Assets and flexibility | 4 | 4/0/0 | 0/2/2 | 1/3/0 | 1/3/0 |
| C — Services, contracts, obligations | 4 | 4/0/0 | 0/0/4 | 0/2/2 | 0/4/0 |
| D — Trading and market operations | 4 | 4/0/0 | 0/0/4 | 0/1/3 | 0/1/3 |
| E — Tariffs, pricing, forecasts | 3 | 3/0/0 | 0/0/3 | 0/2/1 | 0/2/1 |
| F — Expected losses for SHIFT | 4 | 0/0/4 | 1/1/2 | 2/0/2 | 2/2/0 |
| G — Added in self-review | 2 | 2/0/0 | 0/0/2 | 0/0/2 | 0/0/2 |
| **Total** | **26** | **22/0/4** | **1/3/22** | **3/8/15** | **4/15/7** |

## Blocking terms

### SAREF Core v4.1.1

| CQ | Verdict | Blocking term |
|---|:--:|---|
| CQ-01 | ✗ | No agent class. SAREF Core has no Actor, Person or Organisation, and no ownership property. |
| CQ-02 | ✗ | No agent class and no market-transaction class. |
| CQ-03 | ✗ | No agent class, no role model, no region or location term in Core. |
| CQ-04 | ✗ | No agent class, no group or community class, no trust relation. |
| CQ-05 | ✗ | No agent or aggregator class. |
| CQ-06 | ~ | Controllability is expressible (saref:Actuator/Function/Command). Missing: a siting term for node N (saref4bldg:BuildingSpace is an extension) and any response-time property (s4ener territory). |
| CQ-07 | ✗ | No agent class or ownership property, and no storage-capability term in Core. |
| CQ-08 | ~ | saref:CommandExecution with saref:hasTimestamp supplies the denominator. Missing: any outcome or status property on an execution, so failures cannot be counted. |
| CQ-09 | ✗ | No building class in SAREF Core (saref4bldg:Building is an extension) and no heat-pump or battery device kinds in Core (s4ener/s4bldg). |
| CQ-10 | ✗ | saref:Service exists but there is no siting term and no committed-capacity property. |
| CQ-11 | ✗ | No model of a commitment against which delivery is measured. |
| CQ-12 | ✗ | No contract class. |
| CQ-13 | ✗ | No contract class, no trade class, no penalty term. |
| CQ-14 | ✗ | No trade class, no community, no trust relation. |
| CQ-15 | ✗ | No trade class, no community, no consent term. |
| CQ-16 | ✗ | No trade class and no delivery window. |
| CQ-17 | ✗ | No trade class and no market clearing window. |
| CQ-18 | ✗ | No agent class; saref:Profile carries a price via profileHasPrice but no tariff structure. |
| CQ-19 | ✗ | No tariff-structure flags, so there is nothing that can contradict. |
| CQ-20 | ✗ | No forecast class, no node, no DER-capacity property. |
| CQ-21 | ✗ | No electrical connectivity model; saref:consistsOf is mereological composition, not connection. |
| CQ-22 | ~ | saref:Function/Command/hasCommand return the commands. Missing: any ordering, step or successor property, so the sequence the question asks for cannot be expressed. |
| CQ-24 | ✗ | No agent class and no activity taxonomy. |
| CQ-25 | ✗ | No agent class, no community, no trade class. |
| CQ-26 | ✗ | No trade class and no replacement relation. |

### SAREF Core + 4ENER + 4BLDG

| CQ | Verdict | Blocking term |
|---|:--:|---|
| CQ-01 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. No ownership property either. |
| CQ-02 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. No market-transaction class. |
| CQ-03 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. No region term. |
| CQ-04 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. No community class and no trust relation. |
| CQ-05 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. No aggregator class. |
| CQ-06 | ~ | s4ener:hasActivationDelay (xsd:duration, no declared domain) supplies the response-time constraint Core lacked. Still missing: a grid-node term -- s4bldg adds Building and BuildingSpace, which are spatial containers, not network nodes. |
| CQ-07 | ~ | s4ener:Storage and the RoleType individual EnergyStorage supply the storage capability Core lacked; availability comes from saref:hasState. Still missing: Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. |
| CQ-09 | ~ | s4bldg:Building, s4bldg:contains and s4bldg:ElectricFlowStorageDevice make the building and the battery exact. Still missing: a heat-pump class -- NEITHER extension declares one (zero occurrences in both files); the nearest, s4bldg:EnergyConversionDevice, is far broader and also subsumes s4bldg:SolarDevice. Rows match, but s4bldg:EnergyConversionDevice is broader than a heat pump and also subsumes s4bldg:SolarDevice. |
| CQ-10 | ~ | s4ener:PowerLimit, PowerEnvelope and FlexOffer express a committed capacity, which Core could not. Still missing: a grid-node siting term and a service-activity status. |
| CQ-11 | ~ | s4ener power profiles express a commitment and Core observations express the measured value. Still missing: a delivery-event class binding a commitment to its measured outcome so the pair can be compared per event. |
| CQ-12 | ✗ | s4ener:ContractualPowerLimit is a power limit, not a contract. No contract class, no end date, no governed-service relation. |
| CQ-13 | ✗ | No contract class and no trade class, so no path from a trade to a penalty rate. s4ener has no penalty term. |
| CQ-14 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. No trade class, no community, no trust relation. |
| CQ-15 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. No trade class, no community, no consent term. |
| CQ-16 | ✗ | s4ener:FlexOffer/FlexRequest describe offers, not concluded trades with a status and a delivery window. |
| CQ-17 | ~ | s4ener:FlexOffer/FlexRequest with hasEnergy and Slot timing express traded energy per slot. Still missing: a market-clearing-window class and any trade-to-window link. |
| CQ-18 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. s4ener:Incentive and IncentiveTableTier give tariff structure, but with no actor there is no consumption to threshold. |
| CQ-19 | ~ | s4ener:IncentiveTableProfile, IncentiveTableTier and IncentiveType give real tariff structure, which Core lacked entirely. Still missing: flat-versus-dynamic flags, so there is still nothing that can contradict. |
| CQ-20 | ~ | s4ener:hasDemandRateForecast and hasUsageForecast supply the forecast Core lacked. Still missing: a grid-node term and any DER-capacity property. |
| CQ-21 | ✗ | s4bldg:contains is spatial containment, not electrical connection. Neither extension adds a connectivity or conducting-equipment model. |
| CQ-24 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. No activity taxonomy in either extension. |
| CQ-25 | ✗ | Neither extension adds an agent class. s4ener:Role is a DEVICE role codelist (EnergyConsumer / EnergyProducer / EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor. No community class and no trade class. |
| CQ-26 | ✗ | No trade class and no replacement or backup relation. |

### SEAS

| CQ | Verdict | Blocking term |
|---|:--:|---|
| CQ-02 | ~ | seas:Selling/Trading/Transaction exist as classes but carry no properties: nothing links a transaction to its seller, its volume, its time or a confirmation status. |
| CQ-03 | ~ | seas:Role/hasRole and seas:Operator/Aggregator/EndUser give the market role, but no property associates an Actor with a region or zone (seas:location is a PropertyKey on FeatureOfInterest; seas:Actor is an AbstractEntity). |
| CQ-04 | ✗ | No community or group class and no membership property for actors; seas:GroupManager exists but the group it manages does not. No trust relation. |
| CQ-05 | ~ | seas:Aggregator exists, but SEAS declares no compliance, trust or prequalification properties, so participation requirements cannot be tested. |
| CQ-06 | ~ | Siting is expressible via seas:ConnectionPoint/Zone. Missing: any response-time property, and a device-level controllability flag (seas:ControlActivity describes the act, not the capability). |
| CQ-07 | ~ | seas:owns plus seas:Battery/EnergyStorage give the storage-capable assets of an actor. Missing: availability -- the seas operating codelist carries ratings (op-Nominal, op-Min, op-Maximum-*), not an available/unavailable state. |
| CQ-08 | ~ | seas:Failure and seas:failure can mark a failed feature of interest. Missing: an activation-attempt event class, so the denominator of a failure ratio has no term. |
| CQ-10 | ~ | Committed capacity is expressible as a seas:Evaluation interpreted through the flexibility codelist. Missing: a service activity status and any service-to-node siting property. |
| CQ-11 | ~ | Committed and measured values are both expressible as evaluations. Missing: a delivery-event class binding the pair so the two can be compared per event. |
| CQ-12 | ~ | seas:Contract exists and seas:player links it to an actor. Missing: a contract end-date property and any contract-governs-service relation. |
| CQ-13 | ~ | seas:Contract exists. Missing: a trade-to-contract association and any penalty-rate property. |
| CQ-14 | ✗ | No trade class carrying its parties, no community class, no trust relation. |
| CQ-15 | ✗ | No trade class carrying its parties, no community class, no consent term. |
| CQ-16 | ✗ | seas:Transaction has no status property and there is no delivery-window term. |
| CQ-17 | ~ | seas:Transaction, seas:Clearing and seas:Market give the market frame. Missing: a traded-volume property and any window-to-transaction link. |
| CQ-18 | ~ | seas:Price/PricePerEnergy/BasePrice and seas:Profile express a tariff price. Missing: flat-versus-dynamic structural flags, and an actor-level consumption property (nominalEnergyConsumption is on systems). |
| CQ-19 | ✗ | No tariff-structure flags, so there is nothing that can contradict. |
| CQ-20 | ~ | seas:NetworkNode/ElectricPowerSystem give the node and SEAS has forecasting classes. Missing: forecasting is weather-specific (WeatherForecast, WeatherForecasting) with no load-forecast value bound to a node, and no DER-capacity property. |
| CQ-22 | ~ | seas:ControlActivity/ActuatingActivity/OnOffActivity express the control act. Missing: a Command class for the individual instruction and any ordering property. |
| CQ-24 | ~ | SEAS is the only one of the three with the activity taxonomy (seas:Activity, ForecastingActivity, PlanningActivity, OptimizationActivity). Missing: any agency property -- no property has domain seas:Actor or range seas:Activity, so the link can only be the untyped transitive seas:contains -- and no way to say 'currently', since seas:temporalContext has domain TimeContextualizedEvaluation. Rows match, but seas:contains asserts containment, not performance, and 'currently' is unenforceable. |
| CQ-25 | ✗ | No trade class carrying its parties, and no community class to average over. |
| CQ-26 | ✗ | No trade class and no backup or replacement relation. |

### SHIFT

| CQ | Verdict | Blocking term |
|---|:--:|---|
| CQ-21 | ✗ | See cq/shift/cq21.rq -- blocking term named in the query header. |
| CQ-22 | ✗ | See cq/shift/cq22.rq -- blocking term named in the query header. |
| CQ-23 | ✗ | See cq/shift/cq23.rq -- blocking term named in the query header. |
| CQ-24 | ✗ | See cq/shift/cq24.rq -- blocking term named in the query header. |

## Mapping effort

**SAREF Core v4.1.1** — 9 term mappings made:

- shift:Asset -> saref:Device
- shift:SmartMeterAsset -> saref:Meter
- shift:ControlAsset -> saref:Actuator
- shift:assetID -> saref:hasIdentifier
- shift:operatingStatus -> saref:hasState + saref:State individual
- control command sequence -> saref:Function / saref:Command / saref:hasCommand
- activation event -> saref:CommandExecution + saref:hasTimestamp
- meter reading -> saref:PropertyValue (isValueOfProperty, hasValue, hasTimestamp)
- observed quantity -> saref:Property, linked by saref:hasProperty

**SAREF Core v4.1.1** — 13 things the vocabulary could not represent:

- shift:Actor and all subclasses -- SAREF Core has no agent, person or organisation class
- shift:ownsAsset -- no ownership property in SAREF Core
- shift:Node / shift:locatedAt -- no siting or topology term in SAREF Core (saref4bldg:BuildingSpace is an extension)
- shift:CommunityMarketCircle, shift:belongsToCMC, shift:mutuallyTrusted -- no group or trust model
- shift:FlexibilityTrade and all trade properties -- no market transaction class
- shift:FlexibilityContract, shift:penaltyRate_EURperkWh -- no contract class
- shift:TariffPlan structure (isDynamic / hasFlatRate) -- saref:Profile carries a price via profileHasPrice but no tariff structure
- shift:ForecastData -- no forecast class
- shift:canStoreEnergy, shift:responseTime_ms -- no storage-capability or response-time property (s4ener territory)
- shift:BuildingAsset -- no building class in SAREF Core (saref4bldg:Building is an extension)
- shift:eventStatus on activations -- saref:CommandExecution has no outcome or status property
- command ordering -- SAREF Core has no sequence or step property
- shift:Aggregator participation criteria -- no compliance, trust or prequalification terms

**SAREF Core + 4ENER + 4BLDG** — 20 term mappings made:

- shift:Asset -> saref:Device
- shift:SmartMeterAsset -> saref:Meter
- shift:ControlAsset -> saref:Actuator
- shift:assetID -> saref:hasIdentifier
- shift:operatingStatus -> saref:hasState + saref:State individual
- control command sequence -> saref:Function / saref:Command / saref:hasCommand
- activation event -> saref:CommandExecution + saref:hasTimestamp
- meter reading -> saref:PropertyValue (isValueOfProperty, hasValue, hasTimestamp)
- observed quantity -> saref:Property, linked by saref:hasProperty
- shift:BatteryAsset -> s4bldg:ElectricFlowStorageDevice + s4ener:Storage
- shift:EVAsset -> s4ener:Storage
- shift:SolarPVAsset -> s4bldg:SolarDevice
- shift:ControlAsset -> s4bldg:Controller
- shift:BuildingAsset -> s4bldg:Building
- shift:connectedToBuilding -> s4bldg:contains
- asset function -> s4ener:hasRole + s4ener:Role with s4ener:hasRoleType (EnergyConsumer / EnergyProducer / EnergyStorage)
- shift:responseTime_ms -> s4ener:hasActivationDelay (xsd:duration, no declared domain)
- activation outcome -> s4ener:hasInstructionStatus with the s4ener InstructionStatus individuals Succeeded / Aborted -- the term SAREF Core lacks
- activation event -> s4ener:FlexibilityInstruction + s4ener:hasExecutionTime
- command order -> s4ener:hasIndex (xsd:integer, no declared domain, purpose is indexing array elements) -- the ordering SAREF Core lacks

**SAREF Core + 4ENER + 4BLDG** — 12 things the vocabulary could not represent:

- shift:Actor and all subclasses -- neither extension adds an agent, person or organisation class. s4ener:Role is a DEVICE role codelist (EnergyConsumer, EnergyProducer, EnergyStorage) and s4ener:hasRole has domain saref:Device, so it cannot carry an actor's market role
- shift:ownsAsset -- still no ownership property
- shift:marketRole -- s4ener:hasRole has domain saref:Device, not an agent
- shift:Node / shift:locatedAt -- s4bldg adds Building and BuildingSpace, which are spatial containers, not grid nodes; there is still no network-node term
- shift:HeatPumpAsset -- NEITHER extension declares a heat-pump class (0 occurrences in both files); the nearest is the much broader s4bldg:EnergyConversionDevice, which also subsumes s4bldg:SolarDevice
- shift:CommunityMarketCircle, belongsToCMC, mutuallyTrusted -- no group or trust model
- shift:FlexibilityTrade and all trade properties -- s4ener:FlexOffer/FlexRequest describe flexibility offers, not concluded trades with parties, status and consent
- shift:FlexibilityContract -- s4ener:ContractualPowerLimit is a limit, not a contract; no contract class, end date, governed service or penalty rate
- shift:TariffPlan isDynamic / hasFlatRate -- s4ener:IncentiveTableProfile and IncentiveType give tariff structure but no flat-versus-dynamic flags that could contradict
- shift:totalDERCapacity_kW on a node -- no DER-capacity property
- electrical connectivity -- s4bldg:contains is spatial containment, not connection
- actor activities -- no Activity taxonomy in either extension

**SEAS** — 17 term mappings made:

- shift:Actor -> seas:Actor / seas:ElectricityPlayer
- shift:Aggregator -> seas:Aggregator
- shift:ownsAsset -> seas:owns
- shift:LoadAsset -> seas:ElectricPowerConsumer
- shift:SolarPVAsset -> seas:PhotovoltaicPanel (+ seas:ElectricPowerProducer)
- shift:BatteryAsset -> seas:Battery (+ seas:ElectricPowerStorageSystem)
- shift:EVAsset -> seas:ElectricVehicle (+ seas:ElectricPowerStorageSystem)
- shift:HeatPumpAsset -> seas:HeatPump
- shift:BuildingAsset -> seas:Building
- shift:connectedToBuilding -> seas:hasPart (building contains device)
- shift:Node -> seas:ElectricPowerSystem
- electrical connectivity -> seas:connectedTo (System->System, symmetric)
- meter reading -> seas:Evaluation (evaluatedValue) + seas:temporalContext -> time:Instant
- observed quantity -> seas:Property, linked by seas:hasProperty
- actor activity -> seas:ForecastingActivity / PlanningActivity / OptimizationActivity, attached only by the untyped seas:contains
- shift:FlexibilityContract -> seas:Contract (class only)
- shift:marketRole -> seas:hasRole + seas:Role individual

**SEAS** — 16 things the vocabulary could not represent:

- shift:contractEndDate / shift:associatedContract direction -- seas:Contract carries only seas:player (Contract -> Actor); no dates and no governed service
- shift:CommunityMarketCircle / belongsToCMC -- SEAS has seas:GroupManager but no group or community class and no membership property
- shift:mutuallyTrusted -- no trust relation
- shift:FlexibilityTrade parties, volume, price, status -- seas:Transaction/Bid/Offer are bare seas:MarketArtifact subclasses with no properties at all
- shift:tradeStatus, shift:hasCMCConsent -- no status or consent term
- shift:assignedToWindow / shift:TradeWindow -- no market-window class linking transactions to a clearing period
- shift:backupTrade -- no replacement or backup relation
- shift:penaltyRate_EURperkWh -- no penalty term
- shift:isDynamic / hasFlatRate -- no tariff-structure flags
- shift:isAvailable -- the seas operating codelist carries ratings (op-Nominal, op-Min, op-Maximum-*), not availability
- shift:responseTime_ms -- no response-time property
- shift:eventStatus on activations -- seas:failure marks a failed feature but there is no activation-attempt event to divide by
- shift:predictedLoad_kW bound to a node -- seas forecasting is weather-specific (WeatherForecast, WeatherForecasting); no load forecast for a node
- shift:totalDERCapacity_kW -- no DER-capacity property on a node
- actor -> activity agency -- no property has domain seas:Actor or range seas:Activity; only the untyped transitive seas:contains is available
- device command sequence -- no Command class and no ordering property (ControlActivity expresses the act, not the instruction)


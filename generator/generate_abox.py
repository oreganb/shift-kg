#!/usr/bin/env python3
"""
generate_abox.py — synthetic instance generator for the SHIFT Knowledge Graph.

Produces a reproducible, parametrised ABox: an energy community of Actors owning
DER Assets at Nodes, trading flexibility across 30-minute TradeWindows under
Contracts and TariffPlans, with DeliveryEvents and ActivationEvents.

Two design decisions matter for the evaluation:

1. Inferable facts are NOT asserted. No individual is typed Flexumer or Prosumer,
   no trade is marked Expired, no node is flagged as a congestion point. Those are
   what SHIFT-RR-00..34 are supposed to derive. If the generator asserted them the
   rule evaluation would be circular.

2. Ground truth is computed independently, in plain Python, from the same
   parameters that drive generation, and written to a sidecar JSON. Rule output is
   then scored against it. The reasoner and the oracle never share code paths.

Usage:
    python3 generate_abox.py --actors 26 --days 7 --seed 42 --out kg/shift-kg-aran.ttl
"""
import argparse, json, random, pathlib, datetime as dt
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD, OWL, DCTERMS

SHIFT = Namespace("https://w3id.org/shift/core#")
KG = Namespace("https://w3id.org/shift/kg/")

ROOT = pathlib.Path(__file__).resolve().parents[1]
EPOCH = dt.datetime(2026, 3, 2, 0, 0, 0)   # a Monday

# Aran-like geography: three islands, small lat/lon spread
ISLANDS = [("Inishmore", 53.1230, -9.7500),
           ("Inishmaan", 53.0850, -9.5850),
           ("Inisheer",  53.0620, -9.5200)]


def dtl(x):
    return Literal(x.isoformat(), datatype=XSD.dateTime)


class Gen:
    def __init__(self, n_actors, days, seed):
        self.rng = random.Random(seed)
        self.n_actors = n_actors
        self.days = days
        self.g = Graph()
        self.g.bind("shift", SHIFT)
        self.g.bind("kg", KG)
        self.truth = {f"RR-{i:02d}": [] for i in range(35)}
        self.now = EPOCH + dt.timedelta(days=days)
        # Plain-Python registries of what was generated. These record values the
        # RNG has already produced; they consume no randomness of their own, so
        # the emitted graph stays bit-identical. The CQ oracle reads only these,
        # never the RDF graph and never the SPARQL queries.
        self.node_recs = {}
        self.tariff_recs = {}
        self.asset_recs = {}
        self.act_recs = {}
        self.service_recs = {}
        self.contract_recs = {}
        self.window_recs = {}
        self.trade_recs = []
        self.trust_pairs = set()
        self.cq_truth = {}
        # v1.0 scenario enrichment (see enrich())
        self.aggregator_recs = {}
        self.building_recs = {}
        self.forecast_recs = {}
        self.trade_contract = {}
        self.backup_recs = []
        self.market_role = {}

    def add(self, s, p, o):
        self.g.add((s, p, o))

    def lit(self, s, p, v, dtype):
        self.g.add((s, p, Literal(v, datatype=dtype)))

    # ------------------------------------------------------------------ build
    def build(self):
        self.header()
        self.platform()
        self.nodes()
        self.cmcs()
        self.tariffs()
        self.actors()
        self.assets()
        self.services()
        self.contracts()
        self.windows_and_trades()
        self.forecasts()
        self.enrich()
        return self.g, self.truth

    def header(self):
        o = URIRef("https://w3id.org/shift/kg/shift-kg")
        self.add(o, RDF.type, OWL.Ontology)
        self.add(o, OWL.imports, URIRef("https://w3id.org/shift/ext"))
        self.add(o, DCTERMS.title, Literal(
            "SHIFT Knowledge Graph — synthetic energy community ABox", lang="en"))
        self.add(o, DCTERMS.license,
                 URIRef("https://creativecommons.org/licenses/by/4.0/"))
        self.add(o, RDFS.comment, Literal(
            "SYNTHETIC DATA. Generated instances. Not measured. Not a deployment "
            "record. Parameters and seed are recorded in the accompanying "
            "manifest so the graph is reproducible bit-for-bit.", lang="en"))

    def platform(self):
        self.plat = KG["platform/FLEXUS"]
        self.add(self.plat, RDF.type, SHIFT.TransactivePlatform)
        self.lit(self.plat, SHIFT.platformID, "FLEXUS-001", XSD.string)
        self.lit(self.plat, SHIFT.platformName, "FLEXUS", XSD.string)
        self.lit(self.plat, SHIFT.supportsRealTimePricing, True, XSD.boolean)
        self.lit(self.plat, SHIFT.supportsAutomatedMatching, True, XSD.boolean)
        self.lit(self.plat, SHIFT.marketType, "P2P", XSD.string)

    def nodes(self):
        self.nodes_ = []
        for i, (name, lat, lon) in enumerate(ISLANDS):
            n = KG[f"node/{name}"]
            self.nodes_.append(n)
            self.add(n, RDF.type, SHIFT.Node)
            self.lit(n, SHIFT.nodeID, f"ND-{i:02d}", XSD.string)
            self.lit(n, SHIFT.nodeType, "LVFeeder", XSD.string)
            self.lit(n, SHIFT.latitude, round(lat, 4), XSD.decimal)
            self.lit(n, SHIFT.longitude, round(lon, 4), XSD.decimal)
            self.lit(n, SHIFT.voltageLevel_kV, 0.4, XSD.float)
            self.lit(n, SHIFT.isPeerTradeEnabled, True, XSD.boolean)
            # RR-02 ground truth: congestion point iff load>500 & DER<100 & p2p
            load = self.rng.choice([320.0, 610.0, 780.0, 210.0])
            der = self.rng.choice([40.0, 90.0, 160.0, 260.0])
            self.lit(n, SHIFT.totalConnectedLoad_kW, load, XSD.float)
            self.lit(n, SHIFT.totalDERCapacity_kW, der, XSD.float)
            self.node_recs[n] = {"load": load, "der": der, "name": name}
            if load > 500 and der < 100:
                self.truth["RR-02"].append(str(n))

    def cmcs(self):
        self.cmcs_ = []
        for name, _, _ in ISLANDS:
            c = KG[f"cmc/{name}"]
            self.cmcs_.append(c)
            self.add(c, RDF.type, SHIFT.CommunityMarketCircle)
            self.add(c, RDFS.label, Literal(f"{name} Market Circle", lang="en"))

    def tariffs(self):
        self.tariffs_ = []
        specs = [("FLAT-01", False, True, 30), ("DYN-01", True, False, 200),
                 ("CONFLICT-01", True, True, 100)]
        for tid, dyn, flat, cap in specs:
            t = KG[f"tariff/{tid}"]
            self.tariffs_.append(t)
            self.add(t, RDF.type, SHIFT.TariffPlan)
            self.lit(t, SHIFT.tariffID, tid, XSD.string)
            self.lit(t, SHIFT.isDynamic, dyn, XSD.boolean)
            self.lit(t, SHIFT.hasDynamicPricing, dyn, XSD.boolean)
            self.lit(t, SHIFT.hasFlatRate, flat, XSD.boolean)
            self.lit(t, SHIFT.maxMonthlyTrades, cap, XSD.integer)
            self.lit(t, SHIFT.baseRate_EURperkWh, 0.28, XSD.float)
            self.tariff_recs[t] = {"dyn": dyn, "flat": flat}
            # RR-23 ground truth: both dynamic and flat asserted = conflict
            if dyn and flat:
                self.truth["RR-23"].append(str(t))

    def actors(self):
        self.actors_ = []
        self.profile = {}
        for i in range(self.n_actors):
            a = KG[f"actor/A{i:03d}"]
            self.actors_.append(a)
            isl = i % len(ISLANDS)
            self.add(a, RDF.type, SHIFT.Consumer)      # base type only
            self.add(a, SHIFT.belongsToCMC, self.cmcs_[isl])
            tariff = self.rng.choice(self.tariffs_)
            self.add(a, SHIFT.hasTariffPlan, tariff)
            self.lit(a, SHIFT.actorID, f"A{i:03d}", XSD.string)
            self.lit(a, SHIFT.country, "IE", XSD.string)
            self.lit(a, SHIFT.region, ISLANDS[isl][0], XSD.string)
            self.lit(a, SHIFT.isActive, True, XSD.boolean)
            self.lit(a, SHIFT.userType, "Residential" if i < self.n_actors - 6
                     else "Public", XSD.string)
            cons = round(self.rng.uniform(180, 900), 1)
            gen = round(self.rng.uniform(0, 700), 1)
            self.lit(a, SHIFT.avgMonthlyConsumption_kWh, cons, XSD.float)
            self.lit(a, SHIFT.avgMonthlyGeneration_kWh, gen, XSD.float)
            self.lit(a, SHIFT.monthlyImport_kWh, cons, XSD.float)
            self.lit(a, SHIFT.monthlyExport_kWh, gen, XSD.float)
            self.profile[a] = {"island": isl, "cons": cons, "gen": gen,
                               "cmc": self.cmcs_[isl], "region": ISLANDS[isl][0],
                               "tariff": tariff}
            # RR-29 ground truth: net exporter
            if gen > cons:
                self.truth["RR-29"].append(str(a))
        # trust edges inside each CMC
        for c_i in range(len(ISLANDS)):
            mem = [a for a in self.actors_ if self.profile[a]["island"] == c_i]
            for j in range(0, len(mem) - 1, 2):
                self.add(mem[j], SHIFT.mutuallyTrusted, mem[j + 1])
                self.add(mem[j + 1], SHIFT.mutuallyTrusted, mem[j])
                self.trust_pairs.add((mem[j], mem[j + 1]))
                self.trust_pairs.add((mem[j + 1], mem[j]))

    def assets(self):
        self.assets_ = {}
        self.meters = {}
        self.controls = {}
        for i, a in enumerate(self.actors_):
            owned = []
            isl = self.profile[a]["island"]
            node = self.nodes_[isl]

            def mk(kind, cls, fn, extra=None):
                x = KG[f"asset/{kind}-{i:03d}"]
                self.add(x, RDF.type, cls)
                self.add(a, SHIFT.ownsAsset, x)
                self.add(x, SHIFT.locatedAt, node)
                self.lit(x, SHIFT.assetID, f"{kind}-{i:03d}", XSD.string)
                self.lit(x, SHIFT.assetFunction, fn, XSD.string)
                self.lit(x, SHIFT.operatingStatus, "Online", XSD.string)
                self.lit(x, SHIFT.isAvailable, True, XSD.boolean)
                for p, v, d in (extra or []):
                    self.lit(x, p, v, d)
                owned.append((kind, x))
                self.asset_recs[x] = {
                    "kind": kind, "owner": a, "node": node, "function": fn,
                    "status": "Online", "available": True,
                    "attrs": {str(p).split("#")[-1]: v for p, v, _ in (extra or [])},
                }
                return x

            # every actor: a load and a smart meter
            mk("LOAD", SHIFT.LoadAsset, "consumption")
            m = mk("METER", SHIFT.SmartMeterAsset, "consumption",
                   [(SHIFT.isRemoteReadable, True, XSD.boolean),
                    (SHIFT.isRevenueGrade, True, XSD.boolean),
                    (SHIFT.granularity_sec, 1800, XSD.integer)])
            self.meters[a] = m

            has_pv = self.rng.random() < 0.55
            has_bat = self.rng.random() < 0.30
            has_hp = self.rng.random() < 0.40
            has_ev = self.rng.random() < 0.25
            has_ctrl = self.rng.random() < 0.70

            if has_pv:
                mk("PV", SHIFT.SolarPVAsset, "generation",
                   [(SHIFT.installedCapacity_kW, round(self.rng.uniform(2, 8), 1), XSD.float),
                    (SHIFT.isStationary, True, XSD.boolean)])
            if has_bat:
                mk("BAT", SHIFT.BatteryAsset, "storage",
                   [(SHIFT.powerRating_kW, round(self.rng.uniform(3, 10), 1), XSD.float),
                    (SHIFT.stateOfCharge_percent, round(self.rng.uniform(20, 95), 1), XSD.decimal),
                    (SHIFT.canStoreEnergy, True, XSD.boolean),
                    (SHIFT.isStationary, True, XSD.boolean)])
            if has_hp:
                mk("HP", SHIFT.HeatPumpAsset, "thermal",
                   [(SHIFT.coefficientOfPerformance, round(self.rng.uniform(2.5, 4.2), 2), XSD.decimal),
                    (SHIFT.usesThermalEnergy, True, XSD.boolean),
                    (SHIFT.isStationary, True, XSD.boolean)])
            if has_ev:
                mk("EV", SHIFT.EVAsset, "storage",
                   [(SHIFT.isBidirectional, self.rng.random() < 0.4, XSD.boolean),
                    (SHIFT.isMobile, True, XSD.boolean),
                    (SHIFT.canStoreEnergy, True, XSD.boolean)])
            if has_ctrl:
                c = mk("CTRL", SHIFT.ControlAsset, "control",
                       [(SHIFT.responseTime_ms, self.rng.choice([200, 900, 1400, 4200]), XSD.integer),
                        (SHIFT.isRemotelyControllable, True, XSD.boolean),
                        (SHIFT.isControllable, True, XSD.boolean),
                        (SHIFT.isEdgeDeployed, True, XSD.boolean),
                        (SHIFT.isCyberSecure, self.rng.random() < 0.85, XSD.boolean)])
                self.controls[a] = c

            self.assets_[a] = owned

            # ---- ground truth ----
            fns = {k for k, _ in owned}
            # RR-00: owns consumption AND (generation OR storage)
            if ("LOAD" in fns or "METER" in fns) and (
                    {"PV", "BAT", "EV"} & fns):
                self.truth["RR-00"].append(str(a))
            # RR-03: remote-readable meter + control asset + platform RTP
            if has_ctrl:
                self.truth["RR-03"].append(str(a))
            # RR-21: solar excess, no battery
            p = self.profile[a]
            if has_pv and not has_bat and p["gen"] > p["cons"]:
                self.truth["RR-21"].append(str(a))

        # every actor integrated into the platform
        for a in self.actors_:
            self.add(self.plat, SHIFT.integratesActor, a)

        # activation events: some assets deliberately unreliable (RR-28)
        self.act_events = 0
        for a, owned in self.assets_.items():
            for kind, x in owned:
                if kind not in ("BAT", "HP", "EV", "CTRL"):
                    continue
                n_ev = self.rng.choice([0, 6, 8, 12])
                if n_ev == 0:
                    continue
                fail_rate = self.rng.choice([0.05, 0.10, 0.35, 0.45])
                fails = 0
                for k in range(n_ev):
                    e = KG[f"event/act/{str(x).split('/')[-1]}-{k}"]
                    self.add(e, RDF.type, SHIFT.ActivationEvent)
                    self.add(x, SHIFT.hasActivationEvent, e)
                    failed = self.rng.random() < fail_rate
                    fails += failed
                    self.lit(e, SHIFT.eventStatus, "Failed" if failed else "Success",
                             XSD.string)
                    ts = self.now - dt.timedelta(days=self.rng.uniform(0, 28))
                    self.add(e, SHIFT.eventTimestamp, dtl(ts))
                    self.act_recs.setdefault(x, []).append(
                        {"status": "Failed" if failed else "Success", "ts": ts})
                    self.act_events += 1
                # RR-28: >=5 activations and failure ratio > 0.2
                if n_ev >= 5 and fails / n_ev > 0.2:
                    self.truth["RR-28"].append(str(x))

    def services(self):
        self.services_ = []
        types = [(SHIFT.DemandResponseService, "PeakShaving"),
                 (SHIFT.FrequencyRegulationService, "FFR"),
                 (SHIFT.ThermalInertiaService, "ThermalShift"),
                 (SHIFT.PeerToPeerFlexibilityService, "P2P"),
                 (SHIFT.VoltageSupportService, "VoltSupport")]
        for i, a in enumerate(self.actors_):
            if self.rng.random() < 0.25:
                continue
            cls, kind = self.rng.choice(types)
            s = KG[f"service/S{i:03d}"]
            self.services_.append(s)
            isl = self.profile[a]["island"]
            self.add(s, RDF.type, cls)
            self.add(s, SHIFT.linkedToNode, self.nodes_[isl])
            self.lit(s, SHIFT.serviceID, f"S{i:03d}", XSD.string)
            self.lit(s, SHIFT.isActive, True, XSD.boolean)
            self.lit(s, SHIFT.serviceStatus, "Active", XSD.string)
            self.lit(s, SHIFT.isAutomated, True, XSD.boolean)
            self.lit(s, SHIFT.activationTime_sec, self.rng.choice([5, 30, 120]),
                     XSD.integer)
            lat = ISLANDS[isl][1] + self.rng.uniform(-0.010, 0.010)
            lon = ISLANDS[isl][2] + self.rng.uniform(-0.010, 0.010)
            self.lit(s, SHIFT.latitude_deg, round(lat, 5), XSD.decimal)
            self.lit(s, SHIFT.longitude_deg, round(lon, 5), XSD.decimal)
            st = EPOCH + dt.timedelta(days=self.rng.randrange(self.days),
                                      hours=self.rng.choice([7, 8, 17, 18]))
            self.add(s, SHIFT.activationWindowStart, dtl(st))
            self.add(s, SHIFT.activationWindowEnd, dtl(st + dt.timedelta(hours=2)))
            self.service_recs[s] = {"actor": a, "node": self.nodes_[isl],
                                    "active": True, "status": "Active",
                                    "events": []}

            # delivery events; some services deliberately underperform (RR-17)
            under = self.rng.random() < 0.25
            n_bad = 0
            for k in range(self.rng.randint(3, 8)):
                e = KG[f"event/del/S{i:03d}-{k}"]
                self.add(e, RDF.type, SHIFT.DeliveryEvent)
                self.add(s, SHIFT.hasDeliveryEvent, e)
                committed = round(self.rng.uniform(1.5, 9.0), 2)
                ratio = self.rng.uniform(0.45, 0.75) if (under and self.rng.random() < 0.7) \
                    else self.rng.uniform(0.85, 1.05)
                measured = round(committed * ratio, 2)
                self.lit(e, SHIFT.committedValue_kW, committed, XSD.float)
                self.lit(e, SHIFT.measuredResponse_kW, measured, XSD.float)
                ets = self.now - dt.timedelta(days=self.rng.uniform(0, 60))
                self.add(e, SHIFT.eventTimestamp, dtl(ets))
                self.service_recs[s]["events"].append(
                    {"committed": committed, "measured": measured, "ts": ets})
                if measured / committed < 0.8:
                    n_bad += 1
            # RR-17: three or more under-deliveries inside 90 days
            if n_bad >= 3:
                self.truth["RR-17"].append(str(s))

    def contracts(self):
        self.contracts_ = []
        for i, s in enumerate(self.services_):
            c = KG[f"contract/C{i:03d}"]
            self.contracts_.append(c)
            self.add(c, RDF.type, SHIFT.FlexibilityContract)
            self.add(s, SHIFT.associatedContract, c)
            self.lit(c, SHIFT.contractID, f"C{i:03d}", XSD.string)
            self.lit(c, SHIFT.contractStatus, "Active", XSD.string)
            self.lit(c, SHIFT.pricePerUnit_EURperkWh, round(self.rng.uniform(.05, .25), 3),
                     XSD.float)
            self.lit(c, SHIFT.penaltyRate_EURperkWh, 0.05, XSD.float)
            self.add(c, SHIFT.contractStartTime, dtl(EPOCH))
            # some contracts already ended -> RR-09 should close the service
            ended = self.rng.random() < 0.3
            end = self.now - dt.timedelta(days=2) if ended else self.now + dt.timedelta(days=30)
            self.add(c, SHIFT.contractEndDate, dtl(end))
            self.add(c, SHIFT.contractEndTime, dtl(end))
            self.contract_recs[c] = {"service": s, "end": end, "penalty": 0.05}
            if ended:
                self.truth["RR-09"].append(str(s))

    def windows_and_trades(self):
        self.windows_ = []
        self.trades_ = []
        n_win = self.days * 48
        for w in range(n_win):
            st = EPOCH + dt.timedelta(minutes=30 * w)
            tw = KG[f"window/W{w:05d}"]
            self.windows_.append(tw)
            self.add(tw, RDF.type, SHIFT.TradeWindow)
            self.lit(tw, SHIFT.windowID, f"W{w:05d}", XSD.string)
            self.lit(tw, SHIFT.duration_min, 30, XSD.integer)
            self.lit(tw, SHIFT.isMarketClearingWindow, True, XSD.boolean)
            self.add(tw, SHIFT.startTime, dtl(st))
            self.add(tw, SHIFT.endTime, dtl(st + dt.timedelta(minutes=30)))
            self.window_recs[tw] = {"start": st,
                                    "end": st + dt.timedelta(minutes=30)}

        tid = 0
        seller_counts = {}
        for w, tw in enumerate(self.windows_):
            st = EPOCH + dt.timedelta(minutes=30 * w)
            for _ in range(self.rng.randint(0, 3)):
                b, s = self.rng.sample(self.actors_, 2)
                t = KG[f"trade/T{tid:05d}"]
                self.trades_.append(t)
                self.add(t, RDF.type, SHIFT.FlexibilityTrade)
                self.add(t, SHIFT.buyerActor, b)
                self.add(t, SHIFT.sellerActor, s)
                self.add(t, SHIFT.assignedToWindow, tw)
                self.lit(t, SHIFT.tradeID, f"T{tid:05d}", XSD.string)
                volume = round(self.rng.uniform(0.4, 6.0), 2)
                self.lit(t, SHIFT.energyVolume_kWh, volume, XSD.float)
                self.lit(t, SHIFT.price_EURperkWh, round(self.rng.uniform(.06, .30), 3),
                         XSD.float)
                self.add(t, SHIFT.tradeStartTime, dtl(st))
                self.add(t, SHIFT.deliveryStartTime, dtl(st))
                self.add(t, SHIFT.deliveryEndTime, dtl(st + dt.timedelta(minutes=30)))
                status = self.rng.choices(
                    ["Confirmed", "Pending", "InProgress", "Failed"],
                    weights=[.55, .25, .12, .08])[0]
                self.lit(t, SHIFT.tradeStatus, status, XSD.string)
                same_cmc = self.profile[b]["island"] == self.profile[s]["island"]
                consent = self.rng.random() < 0.5
                self.lit(t, SHIFT.hasCMCConsent, consent, XSD.boolean)
                self.trade_recs.append({
                    "uri": t, "buyer": b, "seller": s, "window": tw,
                    "status": status, "volume": volume, "consent": consent,
                    "start": st, "delivery_end": st + dt.timedelta(minutes=30),
                    "same_cmc": same_cmc,
                })

                # ---- ground truth ----
                # RR-04: Pending/InProgress and delivery already ended
                if status in ("Pending", "InProgress") and \
                        st + dt.timedelta(minutes=30) < self.now:
                    self.truth["RR-04"].append(str(t))
                if status == "Confirmed":
                    seller_counts[s] = seller_counts.get(s, 0) + 1
                tid += 1

        # RR-01: three or more confirmed sales
        for a, c in seller_counts.items():
            if c >= 3:
                self.truth["RR-01"].append(str(a))

        # RR-27: cross-CMC without consent
        for t in self.trades_:
            b = next(self.g.objects(t, SHIFT.buyerActor))
            s = next(self.g.objects(t, SHIFT.sellerActor))
            consent = next(self.g.objects(t, SHIFT.hasCMCConsent)).toPython()
            if self.profile[b]["island"] != self.profile[s]["island"] and not consent:
                self.truth["RR-27"].append(str(t))
        # RR-16: same CMC, mutually trusted, Pending
        for t in self.trades_:
            b = next(self.g.objects(t, SHIFT.buyerActor))
            s = next(self.g.objects(t, SHIFT.sellerActor))
            status = next(self.g.objects(t, SHIFT.tradeStatus)).toPython()
            trusted = (s in set(self.g.objects(b, SHIFT.mutuallyTrusted)))
            if status == "Pending" and trusted and \
                    self.profile[b]["island"] == self.profile[s]["island"]:
                self.truth["RR-16"].append(str(t))

    def forecasts(self):
        for i, n in enumerate(self.nodes_):
            f = KG[f"forecast/F{i:03d}"]
            self.add(f, RDF.type, SHIFT.ForecastData)
            self.lit(f, SHIFT.forecastID, f"F{i:03d}", XSD.string)
            self.lit(f, SHIFT.forecastType, "Load", XSD.string)
            self.lit(f, SHIFT.timeGranularity_min, 30, XSD.integer)
            self.lit(f, SHIFT.forecastAccuracy_percent, round(self.rng.uniform(82, 96), 1),
                     XSD.decimal)
            load = self.node_recs[n]["load"]
            predicted = round(load * self.rng.uniform(.8, 1.3), 1)
            self.lit(f, SHIFT.predictedLoad_kW, predicted, XSD.float)
            self.forecast_recs[f] = {"node": n, "predicted": predicted,
                                     "type": "Load"}


    # ------------------------------------------------------- v1.0 enrichment
    def enrich(self):
        """Deterministic scenario enrichment for CQ-05, 09, 13, 20 and 26.

        The v0.1.1 ABox populated only what the 13 executable rules needed, so
        those five competency questions addressed TBox terms with zero instance
        coverage and scored vacuous -- query and oracle agreeing on the empty
        set, which demonstrates nothing about expressive power.

        Two invariants make this safe to bolt on to a released generator:

        1. It is RNG-FREE. Every choice is a deterministic function of
           already-generated individuals, so the random stream driving the rest
           of the generator is untouched and every pre-existing individual keeps
           its exact values.

        2. None of the added individuals carries a property that the 13 rules or
           the 17 already-answerable CQs match on. The aggregators own no
           assets, hold no tariff, belong to no CMC and trade with no one; the
           buildings are never the object of ownsAsset and carry no activation
           events. Existing ground truth is therefore bit-stable, which the
           post-enrichment rule run verifies.
        """
        # -- CQ-05: aggregators, one of which meets every requirement --------
        # Two near misses so the query has to discriminate rather than just
        # find the only Aggregator in the graph.
        for aid, trusted, score in (("AG-000", True, 0.92),    # passes
                                    ("AG-001", False, 0.95),   # not trusted
                                    ("AG-002", True, 0.61)):   # below threshold
            ag = KG[f"aggregator/{aid}"]
            self.add(ag, RDF.type, SHIFT.Aggregator)
            self.lit(ag, SHIFT.actorID, aid, XSD.string)
            self.lit(ag, SHIFT.isActive, True, XSD.boolean)
            self.lit(ag, SHIFT.isTrustedAggregator, trusted, XSD.boolean)
            self.lit(ag, SHIFT.complianceScore, score, XSD.decimal)
            self.aggregator_recs[ag] = {"trusted": trusted, "score": score,
                                        "active": True}

        # -- CQ-03: market roles -------------------------------------------
        # shift:marketRole was declared in the TBox but asserted on nobody, so
        # CQ-03 returned a row whose role column was permanently unbound. The
        # query "answered" without ever producing a market role -- the same
        # vacuity as an empty result, one column down. Values mirror the type
        # each individual already carries, so nothing is invented.
        for a in self.actors_:
            self.lit(a, SHIFT.marketRole, "Consumer", XSD.string)
            self.market_role[a] = "Consumer"
        for ag in self.aggregator_recs:
            self.lit(ag, SHIFT.marketRole, "Aggregator", XSD.string)
            self.market_role[ag] = "Aggregator"

        # -- CQ-09: buildings, one with a heat pump and no battery -----------
        hps = sorted((x for x, r in self.asset_recs.items() if r["kind"] == "HP"),
                     key=str)
        bats = sorted((x for x, r in self.asset_recs.items() if r["kind"] == "BAT"),
                      key=str)
        # B-000 heat pump only (the answer), B-001 both, B-002 battery only.
        plan = [("B-000", hps[:1], []),
                ("B-001", hps[1:2], bats[:1]),
                ("B-002", [], bats[1:2])]
        for bid, hp_list, bat_list in plan:
            members = list(hp_list) + list(bat_list)
            if not members:
                continue
            b = KG[f"building/{bid}"]
            self.add(b, RDF.type, SHIFT.BuildingAsset)
            self.lit(b, SHIFT.assetID, bid, XSD.string)
            self.lit(b, SHIFT.buildingType, "Residential", XSD.string)
            self.lit(b, SHIFT.floorArea_m2, 120.0, XSD.float)
            self.add(b, SHIFT.locatedAt, self.asset_recs[members[0]]["node"])
            for m in members:
                self.add(m, SHIFT.connectedToBuilding, b)
            self.building_recs[b] = {
                "heat_pumps": [str(x) for x in hp_list],
                "batteries": [str(x) for x in bat_list],
            }

        # -- CQ-13: trades reaching their governing contract -----------------
        # shift:relatedContract (Trade -> Contract) existed but was asserted
        # nowhere, so no trade could reach a penalty rate.
        trades = sorted(self.trade_recs, key=lambda t: str(t["uri"]))
        contracts = sorted(self.contract_recs, key=str)
        for trade, contract in zip(trades[:3], contracts[:3]):
            self.add(trade["uri"], SHIFT.relatedContract, contract)
            self.trade_contract[trade["uri"]] = contract

        # -- CQ-20: forecasts bound to the node they forecast for ------------
        # Uses shift:forecastForNode, declared in shift-ext v1.0. No property
        # previously related ForecastData to Node in either direction.
        for f, rec in self.forecast_recs.items():
            self.add(f, SHIFT.forecastForNode, rec["node"])

        # -- CQ-26: a failed trade and the backup trade that replaced it -----
        failed = [t for t in trades if t["status"] == "Failed"]
        if failed:
            f0 = failed[0]
            replacement = next(
                (t for t in trades
                 if t["status"] == "Confirmed"
                 and t["start"] >= f0["start"]
                 and t["seller"] != f0["seller"]), None)
            if replacement is not None:
                self.add(f0["uri"], SHIFT.backupTrade, replacement["uri"])
                self.backup_recs.append({"failed": f0["uri"],
                                         "backup": replacement["uri"],
                                         "backup_seller": replacement["seller"]})

    # -------------------------------------------------------------- CQ oracle
    def cq_oracle(self):
        """Gold answers for the 26 competency questions.

        Computed in plain Python from the generation registries, exactly as the
        RR-* oracle is. Nothing here reads the RDF graph and nothing here reads
        the SPARQL in cq/shift/*.rq -- if a query and this disagree, that is a
        real finding, not a plumbing artefact.

        Each entry is the list of result rows a correct implementation must
        return, with cells in the same order as that query's SELECT clause.
        Parameter defaults mirror the VALUES blocks in the .rq files; where they
        differ the comparison is meaningless, so they are restated as literals
        here rather than imported.
        """
        U = lambda x: str(x)
        iso = lambda d: d.isoformat()
        now = self.now
        rows = {}

        A000 = KG["actor/A000"]
        INISHMORE = KG["node/Inishmore"]

        # CQ-01  own a consumption asset and a generation or storage asset
        out = []
        for a, owned in self.assets_.items():
            fns = {self.asset_recs[x]["function"] for _, x in owned}
            if "consumption" in fns and ({"generation", "storage"} & fns):
                out.append([U(a)])
        rows["CQ-01"] = sorted(out)

        # CQ-02  >= 3 confirmed sales inside a 90-day window
        cutoff = now - dt.timedelta(days=90)
        sales = {}
        for t in self.trade_recs:
            if t["status"] == "Confirmed" and cutoff <= t["start"] <= now:
                sales[t["seller"]] = sales.get(t["seller"], 0) + 1
        rows["CQ-02"] = sorted([[U(a), n] for a, n in sales.items() if n >= 3])

        # CQ-03  market role and region of one actor
        rows["CQ-03"] = [[U(A000), self.market_role[A000],
                          self.profile[A000]["region"]]]

        # CQ-04  CMC peers of one actor, with the mutual-trust flag
        cmc = self.profile[A000]["cmc"]
        rows["CQ-04"] = sorted(
            [[U(p), U(cmc), (A000, p) in self.trust_pairs]
             for p in self.actors_
             if p != A000 and self.profile[p]["cmc"] == cmc])

        # CQ-05  aggregators meeting every participation requirement
        rows["CQ-05"] = sorted(
            [[U(ag), rec["score"]] for ag, rec in self.aggregator_recs.items()
             if rec["score"] >= 0.8 and rec["trusted"] and rec["active"]])

        # CQ-06  controllable assets at a node responding within 1000 ms
        out = []
        for x, rec in self.asset_recs.items():
            rt = rec["attrs"].get("responseTime_ms")
            if rec["node"] == INISHMORE and rec["attrs"].get("isControllable") \
                    and rt is not None and rt <= 1000:
                out.append([U(x), rt])
        rows["CQ-06"] = sorted(out)

        # CQ-07  storage-capable, available, Online assets of one actor.
        # A002 is the lowest-numbered actor owning any storage-capable asset;
        # A000 owns none, which would make the question vacuous.
        A002 = KG["actor/A002"]
        rows["CQ-07"] = sorted(
            [[U(x)] for _, x in self.assets_[A002]
             if self.asset_recs[x]["attrs"].get("canStoreEnergy")
             and self.asset_recs[x]["available"]
             and self.asset_recs[x]["status"] == "Online"])

        # CQ-08  >= 5 activations in 30 days with failure ratio > 0.2
        cutoff = now - dt.timedelta(days=30)
        out = []
        for x, evs in self.act_recs.items():
            recent = [e for e in evs if e["ts"] > cutoff]
            n = len(recent)
            if not n:
                continue
            fails = sum(1 for e in recent if e["status"] == "Failed")
            if n >= 5 and fails / n > 0.2:
                out.append([U(x), n, fails, fails / n])
        rows["CQ-08"] = sorted(out)

        # CQ-09  buildings hosting a heat pump and no battery
        rows["CQ-09"] = sorted(
            [[U(b)] for b, rec in self.building_recs.items()
             if rec["heat_pumps"] and not rec["batteries"]])

        # CQ-10  committed capacity of active services at a node in the window
        w_start, w_end = now - dt.timedelta(days=90), now
        out = []
        for s, rec in self.service_recs.items():
            if rec["node"] != INISHMORE or not rec["active"] \
                    or rec["status"] != "Active":
                continue
            tot = sum(e["committed"] for e in rec["events"]
                      if w_start <= e["ts"] < w_end)
            if any(w_start <= e["ts"] < w_end for e in rec["events"]):
                out.append([U(s), tot])
        rows["CQ-10"] = sorted(out)

        # CQ-11  >= 3 deliveries below 0.8 of commitment inside 90 days
        cutoff = now - dt.timedelta(days=90)
        out = []
        for s, rec in self.service_recs.items():
            bad = [e for e in rec["events"]
                   if cutoff <= e["ts"] <= now and e["committed"] > 0
                   and e["measured"] / e["committed"] < 0.8]
            if len(bad) >= 3:
                out.append([U(s), len(bad)])
        rows["CQ-11"] = sorted(out)

        # CQ-12  contracts expired before the graph clock, and their services
        rows["CQ-12"] = sorted(
            [[U(c), U(rec["service"]), iso(rec["end"])]
             for c, rec in self.contract_recs.items() if rec["end"] < now])

        # CQ-13  penalty rate reached from one trade via shift:relatedContract
        T00000 = KG["trade/T00000"]
        rows["CQ-13"] = [
            [U(T00000), U(c), self.contract_recs[c]["penalty"]]
            for c in [self.trade_contract.get(T00000)] if c is not None]

        # CQ-14  pending, mutually trusted, same-CMC trades in the window
        rows["CQ-14"] = sorted(
            [[U(t["uri"]), U(t["buyer"]), U(t["seller"])] for t in self.trade_recs
             if t["status"] == "Pending"
             and EPOCH <= t["start"] < now
             and (t["buyer"], t["seller"]) in self.trust_pairs
             and self.profile[t["buyer"]]["cmc"] == self.profile[t["seller"]]["cmc"]])

        # CQ-15  cross-CMC trades without consent
        rows["CQ-15"] = sorted(
            [[U(t["uri"]), U(t["buyer"]), U(t["seller"])] for t in self.trade_recs
             if self.profile[t["buyer"]]["cmc"] != self.profile[t["seller"]]["cmc"]
             and not t["consent"]])

        # CQ-16  still open after the delivery window closed
        rows["CQ-16"] = sorted(
            [[U(t["uri"]), t["status"], iso(t["delivery_end"])]
             for t in self.trade_recs
             if t["status"] in ("Pending", "InProgress")
             and t["delivery_end"] < now])

        # CQ-17  confirmed volume per trade window across day 0
        day_start, day_end = EPOCH, EPOCH + dt.timedelta(days=1)
        per_window = {}
        for t in self.trade_recs:
            ws = self.window_recs[t["window"]]["start"]
            if t["status"] == "Confirmed" and day_start <= ws < day_end:
                per_window.setdefault(t["window"], [ws, 0.0])
                per_window[t["window"]][1] += t["volume"]
        rows["CQ-17"] = sorted(
            [[U(w), iso(v[0]), v[1]] for w, v in per_window.items()],
            key=lambda r: (r[1], r[0]))

        # CQ-18  strictly-flat tariff and monthly consumption above 500 kWh
        out = []
        for a in self.actors_:
            tar = self.profile[a]["tariff"]
            spec = self.tariff_recs[tar]
            if spec["flat"] and not spec["dyn"] and self.profile[a]["cons"] > 500:
                out.append([U(a), self.profile[a]["cons"], U(tar)])
        rows["CQ-18"] = sorted(out)

        # CQ-19  tariff plans asserting both dynamic pricing and a flat rate
        rows["CQ-19"] = sorted(
            [[U(t)] for t, spec in self.tariff_recs.items()
             if spec["dyn"] and spec["flat"]])

        # CQ-20  nodes whose forecast load exceeds installed DER capacity
        rows["CQ-20"] = sorted(
            [[U(rec["node"]), rec["predicted"], self.node_recs[rec["node"]]["der"]]
             for rec in self.forecast_recs.values()
             if rec["type"] == "Load"
             and rec["predicted"] > self.node_recs[rec["node"]]["der"]])

        # CQ-21..24  group F: SHIFT is expected to lose these. Empty by
        # construction -- see the MISSING TERM note in each .rq file.
        rows["CQ-21"] = []
        rows["CQ-22"] = []
        rows["CQ-23"] = []
        rows["CQ-24"] = []

        # CQ-25  per-actor trade share against the CMC mean
        counts, by_cmc = {}, {}
        for t in self.trade_recs:
            for party in (t["buyer"], t["seller"]):
                counts.setdefault(party, set()).add(t["uri"])
        for a, ts in counts.items():
            by_cmc.setdefault(self.profile[a]["cmc"], []).append(len(ts))
        means = {c: sum(v) / len(v) for c, v in by_cmc.items()}
        out = []
        for a, ts in counts.items():
            c = self.profile[a]["cmc"]
            n, mean = len(ts), means[c]
            dev = abs(n - mean) / mean
            if dev >= 0.2:
                out.append([U(a), U(c), n, mean, dev])
        rows["CQ-25"] = sorted(out, key=lambda r: (-r[4], r[0]))

        # CQ-26  failed trades and the backup trade that replaced them
        rows["CQ-26"] = sorted(
            [[U(r["failed"]), U(r["backup"]), U(r["backup_seller"])]
             for r in self.backup_recs])

        self.cq_truth = rows
        return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--actors", type=int, default=26)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="kg/shift-kg-aran.ttl")
    a = ap.parse_args()

    gen = Gen(a.actors, a.days, a.seed)
    g, truth = gen.build()

    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(out), format="turtle")

    truth = {k: sorted(set(v)) for k, v in truth.items() if v}
    tp = out.with_suffix(".truth.json")
    json.dump({"params": vars(a), "truth": truth}, open(tp, "w"), indent=1)

    # CQ gold answers, sidecar to the RR-* oracle above
    cq = gen.cq_oracle()
    json.dump({"params": vars(a), "cq_truth": cq},
              open(out.with_suffix(".cq_truth.json"), "w"), indent=1)

    manifest = {
        "params": vars(a), "triples": len(g),
        "individuals": len(set(g.subjects(RDF.type, None))),
        "actors": len(gen.actors_), "assets": sum(len(v) for v in gen.assets_.values()),
        "services": len(gen.services_), "contracts": len(gen.contracts_),
        "trade_windows": len(gen.windows_), "trades": len(gen.trades_),
        "activation_events": gen.act_events,
        "ground_truth_counts": {k: len(v) for k, v in truth.items()},
    }
    json.dump(manifest, open(out.with_suffix(".manifest.json"), "w"), indent=1)
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()

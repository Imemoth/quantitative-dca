# Quant DCA V1 — Real Data Admission + Recession Risk Dashboard Core

## KIINDULÓ ÁLLAPOT

Dolgozz a következő GitHub repository aktuális `main` branchéből:

`https://github.com/Imemoth/quantitative-dca`

Kiinduló merge commit:

`3ad752a5be7a1141433927ed7b275d8df7261ffc`

Ez a review-zott **Features / Targets / Regimes Task 10 checkpoint** GitHub snapshotja.

A repository aktuális committed forrásai, configjai és riportjai jelentik a technikai alapot.

Ne feltételezd, hogy a checkpoint korábbi belső fejlesztési commit hash-ei megtalálhatók a GitHub historyban; a GitHub repo review-zott snapshotként lett inicializálva.

---

# 0. ELLENŐRZÖTT JELENLEGI STÁTUSZ

A Task 10 checkpoint szerint:

- Foundation software/PIT gate: **PASS**
- Features / Targets / Regimes Task 1–10: **PASS**
- final independent spec/code-quality review: **PASS**
- full suite: **804 PASS**
- feature dictionary: **94 definition**
  - 81 registered base output
  - 5 interpretable regime slot
  - max 8 unsupervised regime slot
- target dictionary: **20 target**
- financial model research runs: **0**
- financial OOS runs: **0**
- retrospective holdout: **NOT RUN**
- true forward lockbox: **NOT STARTED**
- actual admitted PIT development panel: **FALSE**
- panel quality/admission report complete: **FALSE**
- real-panel leakage gate PASS: **FALSE**

Következésképp:

> A kutatási rendszer szoftveres váza elkészült, de a pénzügyi modellkutatás még nem indulhat.

---

# 1. ENNEK A MUNKAMENETNEK A CÉLJA

Ebben a munkamenetben pontosan két dolgot végezz el.

## Phase A — Real Development Data Admission

A tényleges 2010–2023 development adatpanel forrásainak és PIT/admission státuszának auditja, ahol lehetséges tényleges admissionnel és real-panel leakage ellenőrzéssel.

## Phase B — Recession Risk Dashboard V1 Core Diagnostic Scaffold

Építsd meg a recession/macro-risk dashboard **core, read-only diagnosztikai infrastruktúráját** úgy, hogy a későbbi teljes Dashboard és Macro Risk Gate erre építhető legyen.

A Phase B ebben a menetben **nem teljes recession-research projekt**.

A végén:

**STOP + checkpoint + human review.**

---

# 2. KIFEJEZETTEN TILOS EBBEN A FUTÁSBAN

Ne indíts:

- direction-model researchöt;
- expected-return model researchöt;
- better-entry model researchöt;
- quantile model race-t;
- probability calibration race-t;
- NetWaitEV kutatást;
- WAIT/BUY NOW policy optimalizálást;
- DCA threshold tuningot;
- 2015–2023 nested model OOS kutatást;
- DCA benchmark backtestet;
- retrospective holdout futtatást.

Ne bővítsd a befagyasztott V1 model feature setet a Dashboard kedvéért.

A következő fő alprojekt — **Models / Policy / Validation** — csak külön emberi jóváhagyással indulhat.

---

# 3. DEVELOPMENT / HOLDOUT PROTOKOLL

Minden fejlesztési és adatkutatási request maximális pénzügyi dátuma:

**2023-12-31**

A felső határt lehetőség szerint már a hálózati request ELŐTT alkalmazd.

Tilos development célra:

- 2024+ pénzügyi adatok használata;
- retrospective holdout inspection;
- future adatok letöltése, majd utólagos levágása;
- olyan adatendpoint használata developmenthez, amely biztonságosan nem korlátozható az engedélyezett dátumtartományra.

A:

`2024-01-01 → 2026-09-11`

időszak státusza:

**RETROSPECTIVE HOLDOUT — NOT PRISTINE — NOT RUN**

A true forward lockbox csak final V1 config freeze után kezdődhet.

---

# 4. GIT WORKFLOW

Ne dolgozz közvetlenül a `main` branchen.

Hozz létre például:

`research/data-admission-recession-core`

branch-et az aktuális `main`-ből.

Használj logikai checkpoint commitokat.

Ne force-pusholj.

Ne merge-eld vissza `main`-be emberi review előtt.

---

# PHASE A — REAL DEVELOPMENT DATA ADMISSION

# 5. A VALÓDI DEVELOPMENT PANEL AUDITJA

Folytasd és zárd, ahol lehetséges, a valódi development adatpanel auditját.

A jelenlegi provider design vagy korábbi raw probe önmagában nem jelent admissiont.

Ne adj quality tiert vagy PASS státuszt tényleges bizonyíték nélkül.

Auditálandó fő domainek:

## Universe

- historical active US equities
- historical delisted US equities
- historical active EU equities
- historical delisted EU equities
- historical membership
- ticker/name changes
- mergers/acquisitions
- terminal economics

## Market data

- US OHLCV
- EU OHLCV
- corporate actions
- adjusted/unadjusted price semantics
- original-unit volume
- delisting/terminal prices

## FX

- USD/HUF
- EUR/HUF
- szükséges historical cross-rates
- fixing semantics
- PIT availability

## Fundamentals

- US fundamentals
- EU fundamentals
- filing/report publication timestamps
- restatements/revisions
- historical vintages

## Macro

- US macro
- EU macro
- yield curves
- policy rates
- inflation
- unemployment
- credit spreads
- financial conditions
- liquidity

## Market context

- regional broad-market series
- sector benchmarks
- VIX / volatility proxy
- event calendars

---

# 6. DOMAINENKÉNT KÖTELEZŐ AUDITMEZŐK

Minden adatdomainhez dokumentáld:

- provider/source
- historical span
- geographic coverage
- active/delisted coverage
- point-in-time semantics
- publication timestamp availability
- revision/restatement behavior
- corporate-action semantics
- request-time date bounding
- source units
- currency semantics
- licensing/reuse limitations
- API/rate limits
- quality-tier evidence
- admission decision
- known limitations
- remaining blocker.

Tényleges evidence nélkül:

- ne nevezd A/B/C tiernek;
- ne nevezd PIT-safe-nek;
- ne állítsd admittednek.

Használj explicit státuszokat:

- `ADMITTED`
- `RAW_ONLY`
- `MISSING`
- `UNAVAILABLE`
- `UNSUPPORTED_FOR_PIT`
- `REQUIRES_MANUAL_REVIEW`

---

# 7. DATA ADMISSION OUTPUTOK

Készíts vagy frissíts:

`reports/development-panel-admission.md`

`reports/data-source-quality-map.csv`

`reports/readiness-manifest.json`

és külön:

`reports/recession-risk-input-admission.md`

A readiness manifest egyértelműen különítse el:

- software readiness
- data readiness
- research readiness
- holdout status.

---

# 8. REAL-PANEL LEAKAGE GATE

Ahol elegendő admitted adat rendelkezésre áll:

építs vagy futtass real-panel PIT/leakage ellenőrzést.

Legalább:

- feature `available_at <= prediction_timestamp`
- revision correctness
- publication lag
- universe eligibility
- region/calendar consistency
- FX availability
- corporate-action timing
- target isolation
- future observation rejection.

Ha a teljes panel még nem áll rendelkezésre:

ne jelents PASS-t.

Jelents explicit:

`REAL_PANEL_LEAKAGE_GATE_BLOCKED_BY_DATA_ADMISSION`

---

# 9. DCA RESEARCH GATE

A Models / Policy / Validation szakasz csak akkor indulhat később, ha egyszerre teljesül:

1. Features / Targets / Regimes Task 1–10 PASS
2. actual PIT development panel available
3. panel quality/admission report complete
4. real-panel leakage gate PASS.

A jelenlegi munkamenet ezt csak előkészíti / értékeli.

---

# PHASE B — RECESSION RISK DASHBOARD V1 CORE

# 10. CÉL

Építs külön, auditálható:

**Recession Risk Dashboard V1 — Core Diagnostic Scaffold**

alrendszert.

A cél most:

> a meglévő PIT-safe macro/regime infrastruktúrára épülő, regionális makrokockázati diagnosztikai keret létrehozása.

A cél NEM:

- recession ML model;
- calibrated recession probability;
- DCA policy gate;
- historical threshold optimization;
- teljes UI;
- production dashboard.

---

# 11. MODULSTRUKTÚRA

Javasolt:

`src/quant_dca/recession_risk/`

Konfiguráció:

`configs/recession_risk_v1.yaml`

Teszt:

`tests/recession_risk/`

Riport:

`reports/recession-risk-*`

A subsystem legyen elkülönítve a befagyasztott Quant DCA V1 model feature pipeline-tól.

---

# 12. A BEFAGYASZTOTT V1 MODEL CONTRACTOT NE MÓDOSÍTSD

A Dashboard kedvéért NE módosítsd:

- `configs/features_v1.yaml`
- a 94 feature-os V1 contractot
- target dictionaryt
- a 20 targetot
- `configs/regimes_v1.yaml`
- DCA action/policy contractot.

A Dashboard új inputjai külön:

**diagnostic input registryben**

legyenek.

---

# 13. MEGLÉVŐ INFRASTRUKTÚRA ÚJRAHASZNÁLÁSA

Használd újra, ahol helyes:

- canonical Observation contract
- PIT/as-of selection
- `available_at`
- `published_at`
- `revised_at`
- revision/vintage semantics
- QualityTier
- snapshot hashing
- provenance/lineage
- regional mapping
- monetary jurisdiction
- calendar services.

Ne írj ezekből párhuzamos, gyengébb Dashboard-verziót.

---

# 14. JELENLEGI MACRO OUTPUTOK

A befagyasztott Quant DCA feature registry már tartalmaz többek között:

- headline inflation
- core inflation
- unemployment
- policy rate
- 3M policy-rate change
- US 10Y–2Y
- US 10Y–3M
- EU sovereign-curve proxy
- HY spread
- IG spread
- financial conditions
- central-bank liquidity change
- global risk-off proxy.

Ezek definícióját és PIT logikáját használd újra, ha az underlying source admission PASS.

Ne másold át automatikusan security-level model featureként.

A Dashboard region-level diagnosztika.

---

# 15. DASHBOARD-ONLY DIAGNOSTIC INPUTOK

A Dashboardhoz szükség lehet olyan inputokra, amelyek nincsenek a frozen model feature registryben.

Például:

## USA

- real GDP / growth
- PCE
- core PCE
- payroll/employment growth
- activity/new-orders proxy
- Sahm-type labor deterioration indicator.

## EU

- real GDP / growth
- HICP / core HICP
- unemployment/employment
- activity proxy
- ECB policy context.

Ezek:

**nem kerülhetnek automatikusan a `features_v1.yaml` fájlba.**

Külön diagnostic input contract legyen.

---

# 16. PROPRIETARY / NEM BIZONYÍTOTT FORRÁSOK

Ha például PMI vagy bármely más sor:

- fizetős;
- proprietary;
- licence szempontból nem egyértelmű;
- nem PIT-safe;
- vagy request-time nem korlátozható;

akkor ne használd automatikusan.

Keress hivatalos/free proxyt, ha van.

Ha nincs:

`MISSING`

vagy:

`UNSUPPORTED_FOR_PIT`

állapot a helyes.

---

# 17. REGION ÉS MONETARY JURISDICTION

Őrizd meg a Task 10 által rögzített fontos elvet:

> region != monetary jurisdiction.

Például:

- USA → FED
- euro area → ECB
- non-euro EU equity → ne kapjon automatikusan ECB policy inputot.

Ha nincs megfelelő jurisdiction-mapping:

`INSUFFICIENT_EVIDENCE`

vagy explicit unsupported state.

Ne legyen implicit fallback.

---

# 18. CORE PILLAR INTERFACE

V1 Core támogassa legalább a következő pilléreket:

1. Growth / Activity
2. Labor
3. Inflation
4. Monetary / Policy Constraint
5. Yield Curve
6. Credit
7. Financial Conditions / Liquidity
8. Market Stress

Most elsősorban a:

- input contract
- evidence handling
- state interface
- snapshot structure

legyen kész.

Nem szükséges ebben a fázisban minden pillérhez véglegesen optimalizált threshold.

---

# 19. PILLAR STATE CONTRACT

Legyen interpretálható, determinisztikus state contract.

Példa:

## Growth

- HEALTHY
- COOLING
- DETERIORATING
- CONTRACTIONARY
- UNKNOWN

## Labor

- HEALTHY
- COOLING
- DETERIORATING
- STRESS
- UNKNOWN

## Inflation

- BENIGN
- ELEVATED
- STICKY
- ACCELERATING
- UNKNOWN

## Credit

- NORMAL
- WATCH
- STRESS
- CRISIS
- UNKNOWN

Az exact vocabulary verziózott configból jöjjön.

---

# 20. KÖTELEZŐ `UNKNOWN` / `INSUFFICIENT_EVIDENCE`

Missing vagy nem admitted adatokból ne következtess:

- HEALTHY
- NORMAL
- LOW RISK

állapotra.

Legyen explicit:

- `UNKNOWN`
- `INSUFFICIENT_EVIDENCE`
- `PARTIAL_EVIDENCE`

ahol szükséges.

---

# 21. OVERALL MACRO STATE — CSAK CONTRACT

Készíts overall-state interfészt.

Javasolt scenario vocabulary:

- NORMAL_EXPANSION
- SOFT_LANDING
- LATE_CYCLE_SLOWDOWN
- STAGFLATION_RISK
- RECESSION_RISK
- CREDIT_STRESS
- RECOVERY
- INSUFFICIENT_EVIDENCE.

Ebben a fázisban:

- ne kalibráld kvázi-valószínűséggé;
- ne optimalizáld recessziódátumokra;
- ne állíts production scoring rendszert empirikus validáció nélkül.

A cél a contract és determinisztikus aggregation skeleton.

---

# 22. DRIVER EXPLANATION CORE

A Dashboard támogasson strukturált driver outputot.

Például:

Negative drivers:

- unemployment trend deteriorating
- core inflation accelerating
- policy restrictive

Positive drivers:

- HY spread contained
- financial conditions not stressed.

Ez legyen:

- strukturált
- determinisztikus
- input/evidence alapú.

Ne LLM inventálja a gazdasági narratívát.

---

# 23. REGIME ENGINE KAPCSOLAT

A jelenlegi interpretable + HMM/GMM regime engine külön subsystem.

A jelenlegi regime engine inputjai között szerepel:

- broad-market momentum
- VIX
- high-yield spread.

A regime output:

**NEM recession probability.**

A Dashboard megjelenítheti később contextual adatként:

`Current market regime`

de most:

- ne feedelje a recession state-et;
- a recession state ne módosítsa a regime modelt;
- ne legyen circular dependency.

---

# 24. DCA ENGINE KAPCSOLAT

A Dashboard státusza:

**READ-ONLY / DIAGNOSTIC ONLY**

Kifejezetten tilos:

- BUY NOW override
- WAIT override
- NO EDGE override
- confidence multiplier
- STRONG BUY blokkolás
- threshold adjustment
- feature injection
- model weighting
- allocation change.

---

# 25. `MacroRiskSnapshot` CONTRACT

Készíts immutable snapshot contractot.

Legalább:

- `as_of`
- `region`
- `monetary_jurisdiction`
- pillar states
- input measures
- evidence references
- quality/admission state
- dominant scenario
- secondary scenario
- evidence completeness
- data confidence
- structured drivers
- max input availability timestamp
- publication timestamps
- config hash
- source snapshot hashes.

Azonos input + azonos config = azonos output.

Future observations hozzáadása:

**nem módosíthat korábbi snapshot outputot.**

---

# 26. DATA CONFIDENCE

A confidence ne kézi címke legyen.

Legalább ezekből származzon:

- input completeness
- data admission status
- quality tier
- freshness
- publication certainty
- critical input availability.

Software PASS vagy hash existence:

**nem emelhet data-confidence értéket.**

---

# 27. HISTORICAL DIAGNOSTIC — MOST NEM TELJES KUTATÁS

Ebben a munkamenetben ne csinálj teljes recession historical model researchöt.

Ha már vannak admitted macro adatok:

végezz csak egy:

**smoke / sanity historical diagnosticot**

annak ellenőrzésére, hogy:

- snapshot replay működik;
- missing data korrekt;
- transitions determinisztikusak;
- future data nem változtat múltbeli state-et.

Ne:

- tuningolj thresholdot ismert recessziókra;
- optimalizálj false-positive rate-et;
- válassz végleges scenario rule-okat visszatekintő teljesítmény alapján.

Ha nincs elegendő adat:

jelentsd:

`HISTORICAL_DIAGNOSTIC_BLOCKED_BY_DATA_ADMISSION`

---

# 28. KÉSŐBBI FULL DASHBOARD

Készíts rövid design note-ot:

`docs/recession-risk-dashboard-full-v1.md`

amely leírja a későbbi teljes verziót:

- full historical diagnostic
- false-positive analysis
- persistence
- transition stability
- richer UI/reporting
- calibrated risk research.

Ne implementáld most teljesen.

---

# 29. KÉSŐBBI RECESSION PROBABILITY V2

Készíts külön:

`docs/recession-risk-probability-v2.md`

design note-ot.

Potenciális későbbi targetek:

- 3M growth stress
- 6M growth stress
- 12M growth stress
- NBER recession
- negative GDP state
- credit-stress state.

Ne válassz győztes targetet ebben a fázisban.

---

# 30. MACRO RISK GATE — CSAK DESIGN NOTE

Készíts:

`docs/macro-risk-gate-experiment.md`

dokumentumot.

A jövőbeli kérdés:

> ad-e incremental OOS edge-et a validált standalone DCA modellhez képest a macro-risk információ?

Most:

- ne implementáld policy gate-ként;
- ne adj thresholdot production policyba;
- ne backtesteld a holdouton.

---

# 31. KÖTELEZŐ TESZTEK

TDD.

Legalább:

## PIT

- future observation rejection
- future revision rejection
- publication lag
- same-day availability semantics
- past snapshot replay invariance

## Region

- USA/FED
- euro-area/ECB
- non-euro EU no ECB fallback
- unsupported jurisdiction

## Data

- missing input
- stale input
- wrong units
- incomplete pillar
- mixed admission status
- low quality.

## Architecture

- no DCA action dependency
- no target dependency
- no ticker dependency
- no automatic `features_v1` mutation
- no target dictionary mutation
- no `regimes_v1` mutation
- no circular regime/recession dependency.

## Reproducibility

- identical evidence → identical snapshot
- config change → config hash change
- future extension does not rewrite past snapshot
- deterministic driver output.

---

# 32. VERIFICATION

Minden logikai task után:

- focused tests.

Alprojekt végén:

```bash
python -m pytest -q
python -m compileall -q src tests
git diff --check

```

Baseline:

**804 tests PASS**

Az új végső tesztszám legyen legalább ennyi, és várhatóan magasabb.

Kérj:

1. independent spec review
2. independent code-quality review.

Mindkettő PASS nélkül:

**ne zárd le az alprojektet.**

---

# 33. VÉGSŐ CHECKPOINT

A végén add át:

1. development data admission status
2. provider/source blockers
3. real-panel leakage gate status
4. DCA research gate status
5. Recession Risk Core architecture
6. exact diagnostic input dictionary
7. USA source/admission map
8. EU/jurisdiction source/admission map
9. pillar state contract
10. overall scenario contract
11. driver explanation contract
12. MacroRiskSnapshot contract
13. historical smoke diagnostic vagy BLOCKED status
14. test evidence
15. independent reviews
16. known limitations
17. Full Dashboard design note
18. Recession Probability V2 design note
19. Macro Risk Gate experiment design note
20. updated readiness manifest
21. Git commit(s)
22. checkpoint ZIP.

Explicit módon jelentsd:

- financial model research runs
- financial OOS runs
- retrospective holdout status
- whether any 2024+ financial data was accessed
- whether actual PIT development panel is ready
- whether real-panel leakage gate is PASS
- whether Models / Policy / Validation may now start.

---

# 34. KÖTELEZŐ STOP POINT

A Data Admission + Recession Risk Core checkpoint után:

**STOP.**

Ne kezdd el automatikusan a Models / Policy / Validation alprojektet.

Ne futtasd a retrospective holdoutot.

Ne készíts production/Codex handoffot.

Várj emberi review-ra.

---

# 35. FŐ PROJEKTIRÁNY

A további fejlesztési sorrend:

1. Foundation — DONE
2. Features / Targets / Regimes — DONE
3. Real Data Admission — CURRENT
4. Recession Risk Dashboard Core — SIDE-CAR CURRENT
5. Models / Policy / Validation — NEXT AFTER HUMAN APPROVAL
6. 2015–2023 nested development OOS
7. DCA benchmarks / robustness / cost stress
8. evaluate whether genuine edge exists
9. only if justified: Full Recession Dashboard + Macro Risk Gate experiment
10. configuration freeze
11. retrospective holdout
12. true forward validation
13. production/Codex architecture.

A fő cél továbbra is:

> bizonyítani vagy cáfolni, hogy a Quant DCA V1 rendelkezik-e stabil, gazdaságilag érdemi, out-of-sample timing edge-dzsel.

A Recession Risk Dashboard támogató diagnosztikai subsystem, nem helyettesíti és nem késleltetheti indokolatlanul ezt a fő kutatási célt.
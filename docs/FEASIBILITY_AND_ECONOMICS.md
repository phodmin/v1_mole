# Mole Machine — Feasibility & Economics Findings

Conclusions from the August 2026 analysis session, checked against the model in `src/`
and against real-world comparables. Numbers use the model's baseline geometry
(100 mm × 1 m, 0.5 m depth) unless stated; "calibrated" soil is q_s = 100 kPa
(the model's 500 kPa default is flagged in `resistance.py` as conservative).

## 1. Reality check

- **The device class is real and commercial**: pneumatic piercing moles
  (Grundomat, HammerHead) are self-propelled soil-displacing torpedoes,
  50–150 mm diameter — but rated **15–50 m per shot**, not 1 km.
- **Closest attempt at our spec**: DARPA Underminer / GE Research peristaltic
  robot, 10 cm tunnel diameter (same as ours), targeting 500 m. $2.5M / 18 months,
  reached tethered feasibility demo only, never fielded.
- **Model power is optimistic ~1–2 orders of magnitude**: a 3" pneumatic mole
  consumes ~5 kW at the tool (50 CFM @ 90–110 psi); the model predicts 16 W.
- **Missing equation — thrust capacity**: the model demands 2.8–5.9 kN of thrust
  but a screw reacting against remoulded soil can mobilise only ~1–1.8 kN.
  Real machines are **percussive** (react thrust against internal hammer inertia).
  → TODO: add a thrust-capacity check to `src/physics/`.
- **Missing equation — navigation**: unsteerable moles drift ~1% of bore length
  (±10 m at 1 km; ±100 m at 10 km). The model has no drift term.
- **Verdict**: credible engineering project at 100 m; at 1 km the binding
  constraints are navigation and the umbilical, not propulsion.

## 2. Key model-derived numbers

| Quantity | Value |
|---|---|
| Energy at machine bus | 1.4 Wh/m (q_s=100 kPa), 3.2 Wh/m (500 kPa) — energy cost ~€0.01/m |
| Body-length friction penalty | dF/dL = 1,572 N per metre of body → 924 Wh (bus) per body-metre per km of bore |
| Cable (2×2.5 mm² Cu, jacket ×1.5) | 67 g/m, €1.1–1.4k per 1.1 km, drag 314 N/km |
| Conductor tensile stress at 1 km | σ = μ·ρ_Cu·jacket·g·x = 52.7 MPa — **gauge-invariant** (area cancels); 70–85 % of soft-Cu yield. Not modelled. → TODO: tensile check in `cable.py` |
| Tether drag at 1 km (μ=0.4) | power cable 314 N · hydraulic hose 1,570 N · air hose 2,354 N · **comms fibre 59 N** |

Only a comms-only fibre survives long range → any long mole is
**onboard energy + fibre telemetry**.

## 3. Propulsion options

| Concept | 1 km viable? | Why |
|---|---|---|
| Rotary auger, cable (current model) | ✗ | Thrust doesn't close; cable near Cu yield |
| Rotary auger, battery | ✗ thrust | Same shortfall; tether problem solved |
| Pneumatic percussion (COTS) | ✗ hose | Proven ≤50 m; hose drag 2.4 kN/km |
| Hydraulic peristalsis (Underminer) | ✗ hose | TRL 4 at best; hose drag 1.6 kN/km |
| Water-jet / fluidization assist | partial | Attacks q_s directly (~10× reduction) — best lever on the worst parameter |
| Surface thrust (HDD / pipe ram) | ✓ | Routine to 1–2 km. The proven answer |
| **Battery + fibre + percussion + steering** | ✓ (with R&D) | The only self-propelled architecture with no distance-growing term except 59 N/km fibre |

### Combustion (onboard) — ruled out

No oxidizer underground. Shaft energy per kg: diesel+LOX 661 (cryogenic, not worth
1.75×), **Li-SOCl₂ cells 375**, Otto Fuel II ~300, HTP ~190, Li-ion 139.
Every storable monopropellant **loses to a primary lithium cell**, and ~13 m³ of
exhaust must vent into the soil (plus a thermal surface signature).
The correct combustion architecture is a diesel compressor **at the surface** —
i.e. the existing pneumatic product.

## 4. Battery sizing (fixed-point incl. battery-mass feedback)

Derate = /0.85 DoD /0.90 cold ×1.2 reserve. q_s = 100 kPa.

| Config | Derated E | Cell mass | Body length | Cells € |
|---|---|---|---|---|
| Li-SOCl₂, 1 km, Ø10 cm | 2.8 kWh | 6 kg | 1.4 m | €1,930 |
| Li-ion NMC, 1 km, Ø10 cm | 3.9 kWh | 21 kg | 2.2 m | €1,175 |
| **Any chemistry, 10 km, Ø ≤ 20 cm** | **DIVERGES** | — | — | — |
| Li-SOCl₂, 10 km, Ø25 cm | 650 kWh | 1,300 kg | 15.7 m | €455k (€45/m) |

**10 km battery diverges**: more energy → more cells → longer body → more
friction → more energy. Volume, not weight, binds (Ø10 cm body ≈ 7.9 L/m).
Battery ceiling in this geometry is roughly 2–5 km; beyond that only cable
(no feedback loop) or surface methods scale.

## 5. Economics

Unit BOMs: cable mole €5–10k · battery mole €5–12k + cells · pneumatic tool
€8–20k (compressor stays at surface).

### Scenario A — non-recoverable (unit lost per shot), € per metre

| Option | 1 km | 10 km | Notes |
|---|---|---|---|
| Cable mole (unit + cable abandoned) | **€6–12** | **€2–3.5** | Lost unit amortizes with distance; 10 km needs HV supply |
| Battery + fibre mole | **€7–14** | ~€50 min | 10 km divergent except 25 cm monster |
| Pneumatic (tool + hose lost) | €11–26 | (€3.5–7 on paper) | 10 km hose not credible |
| HDD contractor | €50–150 | not offered | ~3 km practical ceiling |
| Trench / mole plough (surface access) | €20–80 / €5–20 | same | Plough is cheapest of all if you can drive the route |

Numbers are per *attempted* metre — divide by success probability. A stuck mole
loses the unit and the bore.

### Scenario B — recoverable: fixed + running

Recovery flips battery chemistry to rechargeable Li-ion (cells become fixed cost).

| Option | Fixed | Running €/m | Shot range |
|---|---|---|---|
| Battery mole, Li-ion | €7–14k | **€0.3–0.6** (fibre + electricity) | 1 km yes, 10 km never |
| Cable mole | €6–12k | **€0.2–0.3** (cable rewound ~10×) | 1 km; 10 km with HV |
| Pneumatic (owned) | €25–50k | €0.5–1.5 | ≤50 m |
| HDD own rig | €150–500k | €10–30 | to 2–3 km |
| HDD hired | — | €50–150 | to 2–3 km |
| Trench / plough hired | — | €20–80 / €5–20 | unlimited |

Breakeven vs hired HDD: ~70–200 m cumulative. Vs trenching: ~150–500 m.

## 6. Headline conclusions

1. **Recoverability dominates all design choices**: same battery mole is
   €7–14/m expendable vs €0.3–0.6/m recoverable — a 20–40× swing. Design for
   retrieval (reception pit, fibre back-winch, reversible gait) first.
2. **Distance is an architecture fork, not a pricing knob**: at 1 km either
   mole works and beats commercial alternatives on cost (not maturity); at
   10 km battery physics diverges and only cable or surface methods remain.
3. **Recommended architecture** (if self-propelled from a small pit is the
   requirement): battery + fibre telemetry + percussive drive + steerable
   nose. €6–17k/unit, €2–4/m consumables, order €200–500k R&D to a 100–200 m
   prototype. **Prove 100 m before arguing about 1 km.**
4. Model TODOs: thrust-capacity check, navigation/drift term, cable tensile
   check, idle-power term; fix README's "few hundred Wh" (actual 3,363 Wh
   baseline) and "cable drag dominant" (actual 7 %) claims; delete the
   duplicate `mole_model/src/` tree.

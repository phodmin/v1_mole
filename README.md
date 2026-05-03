# Mole Machine — Engineering Simulation v0.1

First-pass reduced-order engineering model for an electrically powered
underground boring / self-propelling "mole" device.

---

## What this model does

- Models an auger-type mole (100 mm diameter baseline) that displaces
  and compacts soil radially outward as it advances underground
- Estimates axial force, torque, shaft power, electrical power draw
- Models voltage drop through a trailing permanent cable over distance
- Supports three propulsion architectures (Variants A, B, C)
- Runs longitudinal simulations from x = 0 to x = 1000 m
- Sweeps over length, voltage, cable size, soil resistance, and more
- Identifies stall conditions (electrical and mechanical)

## What this model does NOT do

- This is **not** a geotechnical simulator. Soil parameters are
  order-of-magnitude estimates and empirical placeholders.
- No groundwater, pore pressure, or slurry effects.
- No lateral drift, steering, or 3D trajectory.
- No excavated spoil transport — soil is assumed to compact radially.
- No thermal model (motor/cable heating).
- No structural stress analysis of the mole body.
- No cable buckling, kinking, or management model.
- No fatigue or wear model.

**Do not use this model to make real procurement decisions without
field calibration of the soil parameters.**

---

## Quick start

```bash
# Install
cd mole_model
pip install -e ".[dev]"

# Run baseline demo
python -m src.main

# Run tests
pytest tests/ -v

# Open notebook
jupyter lab notebooks/concept_demo.ipynb
```

---

## Structure

```
mole_model/
  src/
    config.py           — SimulationConfig: all parameters in one place
    models/
      soil.py           — SoilModel (homogeneous + piecewise + noise)
      cable.py          — CableModel (electrical + mechanical drag)
      geometry.py       — MachineGeometry (D, L, pitch)
      propulsion.py     — PropulsionConcept (Variants A / B / C)
      machine.py        — MoleMachine (assembly)
      simulation_result.py — SimulationResult (output container)
    physics/
      resistance.py     — Axial force model (F_nose, F_body, F_cable, F_payload)
      compaction.py     — Soil compaction helpers
      power.py          — Shaft and electrical power chain
      voltage_drop.py   — Cable voltage drop, load-line quadratic solver
      performance.py    — Operating point + feasibility assessment
    sim/
      run_steady.py     — Single-point steady-state calculator
      run_longitudinal.py — Distance-stepping simulation
      sweeps.py         — Parameter sweep utilities
    plots/
      plotting.py       — Matplotlib plotting functions
    main.py             — Entry point / demo runner
  notebooks/
    concept_demo.ipynb  — Jupyter notebook with all key analyses
  tests/
    test_basic.py       — Sanity and regression tests
  pyproject.toml
  README.md
```

---

## Physics summary

### Force model

```
F_total = F_nose + F_body + F_cable + F_payload

F_nose    = q_s × A_nose
F_body    = μ × (k_comp × ρ_soil × g × depth) × π × D × L
F_cable   = μ_cable × λ_cable × g × x          [grows linearly with distance]
F_payload = μ_soil × m_payload × g
```

### Torque / power chain

```
P_shaft = (F_total × v / η_screw + P_body_rot) / α
P_electrical = P_shaft / η_drivetrain
```

where:
- `η_screw` = screw mechanical efficiency (0.70 baseline)
- `α` = anti-rotation effectiveness (0.85 / 0.65 / 0.90 for A / B / C)
- `P_body_rot` = body-rotation drag power (Variant B only)
- `η_drivetrain` = lumped motor + gearbox efficiency (0.75 baseline)

### Cable voltage drop

Solved via load-line quadratic:

```
R_cable × I² - V_supply × I + P_electrical = 0
I = (V_supply - √(V_supply² - 4 × R_cable × P_electrical)) / (2 × R_cable)
V_machine = V_supply - I × R_cable
```

Stall declared when `V_machine < 0.60 × V_supply`.

---

## Propulsion variants

| Variant | Description | α (anti-rot) | Body rot drag |
|---|---|---|---|
| A | Rotating screw nose, non-rotating aft | 0.85 | No |
| B | Full-body auger, all surface rotates | 0.65 | Yes |
| C | Hybrid: rotating cutter + non-rotating aft fins | 0.90 | No |

**Variant C is recommended** as the most efficient and easiest to
manage reaction torque.

---

## Baseline parameters

| Parameter | Value | Notes |
|---|---|---|
| Diameter | 100 mm | Fixed concept |
| Length | 1000 mm | Sweep: 300–3000 mm |
| Pitch | 100 mm | Sweep: 50–200 mm |
| q_s (soil) | 500 kPa | PLACEHOLDER — conservative for soft topsoil |
| μ (body-soil) | 0.30 | PLACEHOLDER |
| k_comp | 2.0 | PLACEHOLDER — ±factor 2 uncertainty |
| Supply voltage | 48 V DC | Generator + rectifier |
| Cable | 4 mm² Cu | Sweep: 2.5–16 mm² |
| Drivetrain η | 0.75 | Lumped BLDC + planetary gearbox |
| η_screw | 0.70 | PLACEHOLDER |
| Operating depth | 0.5 m | Shallow bore |
| Payload | 1.5 kg | Simple friction drag in wake |

---

## Where the assumptions are weakest

1. **q_s = 500 kPa** — The most sensitive parameter in the model.
   For a well-designed cutting auger in soft agricultural topsoil, the
   effective penetration pressure may be 50–200 kPa, not 500 kPa.
   This makes the baseline conservative (pessimistic on power).
   **Calibrate with a simple penetrometer test before trusting results.**

2. **k_comp = 2.0** — The compaction-induced radial stress multiplier.
   This is a rough estimate from cavity expansion theory.
   Could reasonably be 1.0–4.0 depending on soil state and mole speed.

3. **η_screw = 0.70** — Screw mechanical efficiency is highly dependent
   on helix angle, surface finish, soil cohesion, and rotation rate.
   This is a mid-range engineering estimate.

4. **Anti-rotation α** — The variant defaults (0.85, 0.65, 0.90) are
   educated guesses. Real values depend entirely on fin/stabiliser
   design. A poorly designed Variant C could perform worse than Variant A.

5. **Cable drag μ_cable = 0.40** — The cable-soil friction coefficient
   is uncertain by ±50%. The cable may bunch, coil, or be pulled in
   a grooved path, significantly changing drag.

6. **Jacket mass factor = 1.5** — Use actual cable datasheet values
   when available.

---

## Engineering memo (summary)

See `notebooks/concept_demo.ipynb` for detailed plots and analysis.

**Best initial configuration:** Variant C (hybrid) at 48 V, 4–6 mm²
cable, body length ~600–1000 mm.

**Primary range limiter:** Cable mechanical drag (grows linearly with
distance) combined with soil nose resistance. At 1000 m in soft soil,
cable drag adds ~400 N — comparable to body friction for a 1 m body.

**100 m feasibility:** Very plausible. Power demand is modest (<50 W
at 5 m/h), voltage drop is negligible, and no stall expected in soft
topsoil with any of the three variants.

**1000 m feasibility:** Plausible electrically (voltage drop at 48V /
4mm² is well within 60% threshold at low power draw), but mechanically
demanding. Cable drag becomes the dominant resistance term. Total energy
for a 1000 m run at 5 m/h is estimated at a few hundred Wh — feasible
from a generator.

**Speed assessment:**
- 1 m/h: trivially feasible in soft soil
- 5 m/h: feasible, good practical target
- 10 m/h: feasible in soft soil; becomes demanding in medium/hard soil

**Variables that matter most for next iteration:**
1. Actual q_s from penetrometer test data
2. Cable drag measurement (lay a cable and pull it)
3. Anti-rotation mechanism design (determines α)
4. Motor + gearbox selection (determines achievable torque at low RPM)

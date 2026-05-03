"""
Parameter sweep utilities.

Each sweep function returns a list of (label, result_or_dict) pairs
suitable for plotting and tabulation.  All sweeps build on a baseline
machine/soil configuration provided by the caller and vary one parameter
at a time (one-at-a-time / OAT sensitivity analysis).

For global sensitivity analysis, compose sweeps externally using
itertools.product over the parameter lists — this module deliberately
keeps things simple and transparent.
"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any

import numpy as np
import pandas as pd

from ..models.machine import MoleMachine
from ..models.soil import SoilModel
from ..models.geometry import MachineGeometry
from ..models.cable import CableModel
from ..models.propulsion import PropulsionConcept, PropulsionVariant
from .run_longitudinal import run_longitudinal
from .run_steady import steady_state


# ---------------------------------------------------------------------------
# Helper: clone machine with one field changed
# ---------------------------------------------------------------------------

def _clone_machine(machine: MoleMachine, **overrides) -> MoleMachine:
    """Return a copy of machine with specified top-level fields changed."""
    d = dataclasses.asdict(machine)
    # Rebuild sub-objects from their dicts
    geo = MachineGeometry(**{**dataclasses.asdict(machine.geometry),
                              **overrides.pop("geometry", {})})
    prop = PropulsionConcept(**{**dataclasses.asdict(machine.propulsion),
                                **overrides.pop("propulsion", {})})
    cable = CableModel(**{**dataclasses.asdict(machine.cable),
                           **overrides.pop("cable", {})})

    # Top-level overrides
    kw = {k: overrides.get(k, getattr(machine, k))
          for k in ("v_target_ms", "eta_drivetrain", "m_payload", "v_min_fraction")}
    return MoleMachine(geometry=geo, propulsion=prop, cable=cable, **kw)


# ---------------------------------------------------------------------------
# Sweep: body length
# ---------------------------------------------------------------------------

def sweep_length(
    base_machine: MoleMachine,
    soil: SoilModel,
    lengths_m: list[float] | None = None,
    x_max: float = 1000.0,
) -> list[tuple[str, Any]]:
    """Sweep body length.  Returns list of (label, SimulationResult).

    Default sweep: 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0 m
    """
    if lengths_m is None:
        lengths_m = [0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

    results = []
    for L in lengths_m:
        m = _clone_machine(base_machine, geometry={"length": L})
        r = run_longitudinal(m, soil, x_max=x_max)
        results.append((f"L={L*1000:.0f}mm", r))
    return results


# ---------------------------------------------------------------------------
# Sweep: supply voltage
# ---------------------------------------------------------------------------

def sweep_voltage(
    base_machine: MoleMachine,
    soil: SoilModel,
    voltages_V: list[float] | None = None,
    x_max: float = 1000.0,
) -> list[tuple[str, Any]]:
    """Sweep supply voltage.  Returns list of (label, SimulationResult)."""
    if voltages_V is None:
        voltages_V = [24.0, 48.0, 96.0]

    results = []
    for V in voltages_V:
        m = _clone_machine(base_machine, cable={"V_supply": V, "A_conductor": base_machine.cable.A_conductor})
        r = run_longitudinal(m, soil, x_max=x_max)
        results.append((f"V={V:.0f}V", r))
    return results


# ---------------------------------------------------------------------------
# Sweep: cable cross-section
# ---------------------------------------------------------------------------

def sweep_cable_size(
    base_machine: MoleMachine,
    soil: SoilModel,
    areas_mm2: list[float] | None = None,
    x_max: float = 1000.0,
) -> list[tuple[str, Any]]:
    """Sweep cable conductor cross-section."""
    if areas_mm2 is None:
        areas_mm2 = [2.5, 4.0, 6.0, 10.0, 16.0]

    results = []
    for A in areas_mm2:
        m = _clone_machine(base_machine, cable={"A_conductor": A * 1e-6,
                                                  "V_supply": base_machine.cable.V_supply})
        r = run_longitudinal(m, soil, x_max=x_max)
        results.append((f"{A:.1f}mm²", r))
    return results


# ---------------------------------------------------------------------------
# Sweep: propulsion variants A / B / C
# ---------------------------------------------------------------------------

def sweep_propulsion_variants(
    base_machine: MoleMachine,
    soil: SoilModel,
    x_max: float = 1000.0,
) -> list[tuple[str, Any]]:
    """Run all three propulsion variants."""
    results = []
    for factory, label in [
        (PropulsionConcept.variant_a, "A: Screw nose"),
        (PropulsionConcept.variant_b, "B: Full auger"),
        (PropulsionConcept.variant_c, "C: Hybrid"),
    ]:
        prop = factory(eta_screw=base_machine.propulsion.eta_screw)
        m = _clone_machine(
            base_machine,
            propulsion={
                "variant": prop.variant,
                "anti_rotation_alpha": prop.anti_rotation_alpha,
                "body_rotation_drag": prop.body_rotation_drag,
                "rotating_fraction": prop.rotating_fraction,
                "eta_screw": prop.eta_screw,
            }
        )
        r = run_longitudinal(m, soil, x_max=x_max)
        results.append((label, r))
    return results


# ---------------------------------------------------------------------------
# Sweep: speed targets
# ---------------------------------------------------------------------------

def sweep_speed_targets(
    base_machine: MoleMachine,
    soil: SoilModel,
    speeds_mh: list[float] | None = None,
    x_max: float = 1000.0,
) -> list[tuple[str, Any]]:
    """Sweep target forward speed."""
    if speeds_mh is None:
        speeds_mh = [1.0, 5.0, 10.0]

    results = []
    for v_mh in speeds_mh:
        m = _clone_machine(base_machine, v_target_ms=v_mh / 3600.0)
        r = run_longitudinal(m, soil, x_max=x_max)
        results.append((f"{v_mh:.0f} m/h", r))
    return results


# ---------------------------------------------------------------------------
# Sweep: soil penetration resistance
# ---------------------------------------------------------------------------

def sweep_soil_resistance(
    base_machine: MoleMachine,
    q_s_values: list[float] | None = None,
    x_max: float = 1000.0,
) -> list[tuple[str, Any]]:
    """Sweep soil penetration resistance (homogeneous)."""
    if q_s_values is None:
        q_s_values = [200_000.0, 500_000.0, 1_000_000.0, 2_000_000.0]

    results = []
    for q_s in q_s_values:
        soil = SoilModel.homogeneous(x_max=x_max, q_s=q_s)
        r = run_longitudinal(base_machine, soil, x_max=x_max)
        results.append((f"q_s={q_s/1e3:.0f}kPa", r))
    return results


# ---------------------------------------------------------------------------
# Sweep: auger pitch
# ---------------------------------------------------------------------------

def sweep_pitch(
    base_machine: MoleMachine,
    soil: SoilModel,
    pitches_m: list[float] | None = None,
    x_max: float = 1000.0,
) -> list[tuple[str, Any]]:
    """Sweep auger pitch."""
    if pitches_m is None:
        pitches_m = [0.05, 0.075, 0.10, 0.15, 0.20]

    results = []
    for P in pitches_m:
        m = _clone_machine(base_machine, geometry={"pitch": P})
        r = run_longitudinal(m, soil, x_max=x_max)
        results.append((f"P={P*1000:.0f}mm", r))
    return results


# ---------------------------------------------------------------------------
# Sweep: compaction multiplier k_comp
# ---------------------------------------------------------------------------

def sweep_kcomp(
    base_machine: MoleMachine,
    x_max: float = 1000.0,
    k_comp_values: list[float] | None = None,
) -> list[tuple[str, Any]]:
    """Sweep k_comp (soil compaction multiplier)."""
    if k_comp_values is None:
        k_comp_values = [1.0, 2.0, 3.5]

    results = []
    for k in k_comp_values:
        soil = SoilModel.homogeneous(x_max=x_max, k_comp=k)
        r = run_longitudinal(base_machine, soil, x_max=x_max)
        results.append((f"k_comp={k:.1f}", r))
    return results


# ---------------------------------------------------------------------------
# Summary table builder
# ---------------------------------------------------------------------------

def sweep_to_dataframe(
    sweep_results: list[tuple[str, Any]],
    x_targets: list[float] | None = None,
) -> pd.DataFrame:
    """Convert sweep results to a summary DataFrame.

    For each (label, SimulationResult) pair, extracts:
      - label
      - stall_distance
      - stall_reason
      - total_energy_Wh
      - mean_speed_mh
      - V_machine at x_targets (if no stall before that point)
      - P_electrical at x=0

    Parameters
    ----------
    sweep_results : output of any sweep_* function
    x_targets     : distances at which to sample V_machine (default [0, 100, 500, 1000])
    """
    if x_targets is None:
        x_targets = [0, 100, 500, 1000]

    rows = []
    for label, res in sweep_results:
        row = {
            "label": label,
            "stall_distance_m": res.stall_distance,
            "stall_reason": res.stall_reason,
            "total_energy_Wh": round(res.total_energy_Wh, 2),
            "mean_speed_mh": round(res.mean_speed_mh, 2),
        }

        # P at x=0
        if len(res.P_electrical) > 0:
            row["P_elec_0_W"] = round(float(res.P_electrical[0]), 1)

        # V_machine at each x target
        for xt in x_targets:
            idx_arr = np.where(res.x >= xt - 0.5)[0]
            if len(idx_arr) > 0:
                idx = idx_arr[0]
                row[f"V@{xt}m"] = round(float(res.V_machine[idx]), 1)
            else:
                row[f"V@{xt}m"] = None

        rows.append(row)

    return pd.DataFrame(rows)

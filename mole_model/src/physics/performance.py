"""
Performance metrics and feasibility assessment.

Aggregates the force, power, and voltage-drop models into high-level
engineering judgements.
"""

from __future__ import annotations

from typing import Optional
import math

from .resistance import axial_forces
from .power import shaft_power, electrical_power
from .voltage_drop import solve_current, voltage_at_machine

from ..models.machine import MoleMachine
from ..models.soil import SoilModel


def operating_point(
    x: float,
    machine: MoleMachine,
    soil: SoilModel,
    v_ms: Optional[float] = None,
) -> dict:
    """Compute the full operating point at position x.

    Returns a dict with all force, torque, power, and electrical values.

    Parameters
    ----------
    x       : position along bore (m)
    machine : MoleMachine
    soil    : SoilModel
    v_ms    : override speed (m/s); defaults to machine.v_target_ms
    """
    v = v_ms if v_ms is not None else machine.v_target_ms
    geo = machine.geometry
    prop = machine.propulsion
    cable = machine.cable

    # Force breakdown
    forces = axial_forces(x, soil, geo, cable, machine.m_payload)
    F_total = forces["F_total"]
    mu = forces["mu"]
    k_comp = forces["k_comp"]

    # Shaft and electrical power
    P_sh, T_sh = shaft_power(F_total, v, prop, geo, soil, mu, k_comp)
    P_elec = electrical_power(P_sh, machine.eta_drivetrain)

    # Voltage / current
    R_cable = cable.round_trip_resistance(x)
    I = solve_current(P_elec, R_cable, cable.V_supply)

    if I is not None:
        V_machine = voltage_at_machine(I, R_cable, cable.V_supply)
        electrical_stall = V_machine < machine.v_min
        mechanical_stall = False
    else:
        # Discriminant < 0: cable cannot deliver power
        V_machine = 0.0
        I = float("inf")
        electrical_stall = True
        mechanical_stall = False

    # Check mechanical stall: P_shaft > P_available at V_machine
    if not electrical_stall and I is not None and not math.isinf(I):
        P_available_at_terminal = I * V_machine * machine.eta_drivetrain
        if P_sh > P_available_at_terminal * 1.05:  # 5% tolerance
            mechanical_stall = True

    return {
        **forces,
        "T_shaft": T_sh,
        "P_shaft": P_sh,
        "P_electrical": P_elec,
        "I_draw": I if I is not None else float("nan"),
        "V_machine": V_machine,
        "R_cable": R_cable,
        "v": v,
        "electrical_stall": electrical_stall,
        "mechanical_stall": mechanical_stall,
        "stall": electrical_stall or mechanical_stall,
        "stall_reason": (
            "electrical" if electrical_stall
            else "mechanical" if mechanical_stall
            else None
        ),
        "energy_per_m": P_elec / v if v > 0 else float("inf"),
    }


def speed_feasibility(
    machine: MoleMachine,
    soil: SoilModel,
    x: float = 0.0,
    speed_targets_mh: tuple = (1.0, 5.0, 10.0),
) -> list[dict]:
    """Assess feasibility at each speed target.

    Returns a list of dicts, one per speed target, with operating point
    and a feasibility verdict.
    """
    results = []
    for v_mh in speed_targets_mh:
        v_ms = v_mh / 3600.0
        op = operating_point(x, machine, soil, v_ms=v_ms)
        op["v_target_mh"] = v_mh
        op["feasible"] = not op["stall"]
        results.append(op)
    return results

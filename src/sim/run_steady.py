"""
Steady-state point calculator.

Computes the operating point at a single (x, speed) pair.
Useful for quick estimates and sweep tables.
"""

from __future__ import annotations

from ..models.machine import MoleMachine
from ..models.soil import SoilModel
from ..physics.performance import operating_point


def steady_state(
    machine: MoleMachine,
    soil: SoilModel,
    x: float = 0.0,
    v_ms: float | None = None,
) -> dict:
    """Return the full operating point dict for a single (x, v) condition.

    Parameters
    ----------
    machine : MoleMachine
    soil    : SoilModel
    x       : bore position (m), default 0
    v_ms    : forward speed (m/s), defaults to machine.v_target_ms

    Returns
    -------
    dict with keys:
        F_nose, F_body, F_cable, F_payload, F_total,
        T_shaft, P_shaft, P_electrical,
        I_draw, V_machine, R_cable,
        v, q_s, mu, k_comp,
        electrical_stall, mechanical_stall, stall, stall_reason,
        energy_per_m
    """
    return operating_point(x, machine, soil, v_ms=v_ms)


def print_operating_point(op: dict, label: str = "") -> None:
    """Pretty-print a steady-state operating point dict."""
    prefix = f"[{label}] " if label else ""
    print(
        f"{prefix}"
        f"x={op.get('x', 0):.0f} m  "
        f"v={op['v']*3600:.1f} m/h  "
        f"F_total={op['F_total']:.0f} N  "
        f"P_elec={op['P_electrical']:.1f} W  "
        f"I={op['I_draw']:.2f} A  "
        f"V_machine={op['V_machine']:.1f} V  "
        f"stall={op['stall']}({op['stall_reason']})"
    )

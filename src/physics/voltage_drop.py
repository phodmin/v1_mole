"""
Cable voltage-drop and current solver.

The cable has a round-trip resistance R_cable(x).  The machine draws
electrical power P_electrical at its terminals.  This creates a coupled
system: current depends on terminal voltage, which depends on current.

Load-line quadratic
-------------------
Let V = V_machine (terminal voltage at machine), I = current:

    V = V_supply - I × R_cable          ... (1) cable voltage divider
    P_elec = I × V                       ... (2) power at terminal

Substituting (1) into (2):
    P_elec = I × (V_supply - I × R_cable)
    R_cable × I² - V_supply × I + P_elec = 0

Discriminant:
    Δ = V_supply² - 4 × R_cable × P_elec

If Δ < 0: the cable cannot deliver the required power — stall.
If Δ ≥ 0: two solutions; take the *smaller* root (stable operating point):
    I = (V_supply - √Δ) / (2 × R_cable)

Then:
    V_machine = V_supply - I × R_cable
    Power delivered to machine = I × V_machine  (should equal P_elec)

Cable efficiency:
    η_cable = V_machine / V_supply = 1 - (I × R_cable) / V_supply
"""

from __future__ import annotations

import math
from typing import Optional


def solve_current(
    P_elec: float,
    R_cable: float,
    V_supply: float,
) -> Optional[float]:
    """Solve for steady-state current from the load-line quadratic.

    Returns current (A) at the stable operating point, or None if the
    cable cannot deliver the required power (Δ < 0).

    Parameters
    ----------
    P_elec   : required electrical power at machine terminal (W)
    R_cable  : round-trip cable resistance at current distance (Ω)
    V_supply : supply voltage at surface end (V)
    """
    if P_elec <= 0:
        return 0.0

    if R_cable <= 0:
        # Zero resistance — no voltage drop
        return P_elec / V_supply

    discriminant = V_supply**2 - 4.0 * R_cable * P_elec
    if discriminant < 0:
        # Cable cannot deliver required power at this distance
        return None

    # Stable (smaller) root
    I = (V_supply - math.sqrt(discriminant)) / (2.0 * R_cable)
    return I


def voltage_at_machine(I: float, R_cable: float, V_supply: float) -> float:
    """Terminal voltage at the machine (V).

    V_machine = V_supply - I × R_cable

    Parameters
    ----------
    I        : current (A)
    R_cable  : round-trip resistance (Ω)
    V_supply : supply voltage (V)
    """
    return V_supply - I * R_cable


def cable_efficiency(V_machine: float, V_supply: float) -> float:
    """Fraction of supply voltage delivered to machine.

    η_cable = V_machine / V_supply
    """
    return V_machine / V_supply


def max_range_for_power(
    P_elec: float,
    V_supply: float,
    R_per_meter: float,
    V_min_fraction: float = 0.60,
) -> float:
    """Maximum cable length (m) before voltage drops below V_min.

    Solves:
        V_machine(x) ≥ V_min_fraction × V_supply

    At the limit:
        V_machine = V_min = V_min_fraction × V_supply
        I = (V_supply - V_min) / R_cable(x)
        P_elec = I × V_min

    Substituting:
        P_elec = ((V_supply - V_min) / (R_per_m × x)) × V_min
        x_max = (V_supply - V_min) × V_min / (P_elec × R_per_m)

    Parameters
    ----------
    P_elec          : electrical power demand (W)
    V_supply        : supply voltage (V)
    R_per_meter     : round-trip resistance per metre (Ω/m)
    V_min_fraction  : minimum acceptable V_machine / V_supply ratio
    """
    V_min = V_min_fraction * V_supply
    if P_elec <= 0 or R_per_meter <= 0:
        return float("inf")
    numerator = (V_supply - V_min) * V_min
    return numerator / (P_elec * R_per_meter)


def voltage_profile(
    x_array,
    P_elec: float,
    V_supply: float,
    R_per_meter: float,
):
    """Compute V_machine at each position in x_array.

    Returns array of V_machine values (NaN where cable cannot deliver power).

    Parameters
    ----------
    x_array     : array-like of distances (m)
    P_elec      : constant electrical power demand (W)
    V_supply    : supply voltage (V)
    R_per_meter : round-trip resistance per metre (Ω/m)
    """
    import numpy as np
    x_arr = np.asarray(x_array, dtype=float)
    V_out = np.full_like(x_arr, np.nan)

    for i, x in enumerate(x_arr):
        R = R_per_meter * x if x > 0 else 1e-12
        I = solve_current(P_elec, R, V_supply)
        if I is not None:
            V_out[i] = voltage_at_machine(I, R, V_supply)

    return V_out

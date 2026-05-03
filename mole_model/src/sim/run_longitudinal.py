"""
Longitudinal (distance-stepping) simulation.

Marches from x = 0 to x = x_max in steps of dx_m, computing the full
operating point at each step.  Stops early if a stall condition is
detected.

The simulation is quasi-static: no inertia or transient dynamics are
modelled.  Each step is an independent steady-state calculation using the
local soil parameters at that position.

Outputs
-------
Returns a SimulationResult with all arrays populated and scalar summaries
computed.

Optional random noise
---------------------
When the soil model has noise_std_frac > 0, the step size is automatically
reduced to dx_noise (default 0.5 m) for better spatial resolution of the
perturbations.

Energy integration
------------------
Cumulative energy is the trapezoid integral of P_electrical over time:
    ΔE = P_electrical × Δt = P_electrical × (dx / v)
"""

from __future__ import annotations

import math
import numpy as np

from ..models.machine import MoleMachine
from ..models.soil import SoilModel
from ..models.simulation_result import SimulationResult
from ..physics.resistance import axial_forces
from ..physics.power import shaft_power, electrical_power
from ..physics.voltage_drop import solve_current, voltage_at_machine


def run_longitudinal(
    machine: MoleMachine,
    soil: SoilModel,
    x_max: float | None = None,
    dx_m: float = 1.0,
    dx_noise: float = 0.5,
    v_ms: float | None = None,
    stop_on_stall: bool = True,
) -> SimulationResult:
    """Run longitudinal distance-stepping simulation.

    Parameters
    ----------
    machine       : MoleMachine
    soil          : SoilModel
    x_max         : maximum bore distance (m).  Defaults to soil.x_max.
    dx_m          : step size (m).  Default 1.0 m.
    dx_noise      : step size used when noise is enabled (m).  Default 0.5 m.
    v_ms          : forward speed override (m/s).  Defaults to machine.v_target_ms.
    stop_on_stall : stop simulation at first stall detection.  Default True.

    Returns
    -------
    SimulationResult with all arrays and scalar summaries populated.
    """
    if x_max is None:
        x_max = soil.x_max

    v = v_ms if v_ms is not None else machine.v_target_ms

    # Choose step size
    dx = dx_noise if soil.noise_std_frac > 0.0 else dx_m

    geo = machine.geometry
    prop = machine.propulsion
    cable = machine.cable

    # Pre-allocate output lists
    xs, q_s_arr, mu_arr = [], [], []
    F_nose_arr, F_body_arr, F_cable_arr, F_payload_arr, F_total_arr = [], [], [], [], []
    T_arr, P_shaft_arr, P_elec_arr, I_arr, V_arr = [], [], [], [], []
    v_arr, E_cum_arr = [], []

    E_cumulative = 0.0
    stall_distance = None
    stall_reason = None

    x = 0.0
    while x <= x_max + 1e-9:
        # Local soil parameters
        forces = axial_forces(x, soil, geo, cable, machine.m_payload)
        F_total = forces["F_total"]
        mu = forces["mu"]
        k_comp = forces["k_comp"]

        # Shaft and electrical power
        P_sh, T_sh = shaft_power(F_total, v, prop, geo, soil, mu, k_comp)
        P_elec = electrical_power(P_sh, machine.eta_drivetrain)

        # Cable state
        R_cable = cable.round_trip_resistance(x)
        I = solve_current(P_elec, R_cable, cable.V_supply)

        if I is None:
            # Discriminant < 0 — cable cannot deliver required power
            V_mach = 0.0
            I_val = float("nan")
            elec_stall = True
            mech_stall = False
        else:
            V_mach = voltage_at_machine(I, R_cable, cable.V_supply)
            I_val = I
            elec_stall = V_mach < machine.v_min
            # Mechanical stall: required shaft power exceeds available
            P_avail = I * V_mach * machine.eta_drivetrain
            mech_stall = P_sh > P_avail * 1.05

        stall = elec_stall or mech_stall

        # Determine effective speed at this step
        if stall:
            v_actual = 0.0
        else:
            v_actual = v

        # Record step
        xs.append(x)
        q_s_arr.append(forces["q_s"])
        mu_arr.append(mu)
        F_nose_arr.append(forces["F_nose"])
        F_body_arr.append(forces["F_body"])
        F_cable_arr.append(forces["F_cable"])
        F_payload_arr.append(forces["F_payload"])
        F_total_arr.append(F_total)
        T_arr.append(T_sh)
        P_shaft_arr.append(P_sh)
        P_elec_arr.append(P_elec)
        I_arr.append(I_val)
        V_arr.append(V_mach)
        v_arr.append(v_actual)

        # Cumulative energy: ΔE = P_electrical × Δt = P_electrical × dx / v
        if v_actual > 0:
            dt = dx / v_actual
            E_cumulative += P_elec * dt
        E_cum_arr.append(E_cumulative)

        # Stall detection
        if stall and stop_on_stall:
            stall_distance = x
            stall_reason = "electrical" if elec_stall else "mechanical"
            break

        x = round(x + dx, 6)

    # Build result
    result = SimulationResult(
        x=np.array(xs),
        q_s=np.array(q_s_arr),
        mu=np.array(mu_arr),
        F_nose=np.array(F_nose_arr),
        F_body=np.array(F_body_arr),
        F_cable=np.array(F_cable_arr),
        F_payload=np.array(F_payload_arr),
        F_total=np.array(F_total_arr),
        torque=np.array(T_arr),
        P_shaft=np.array(P_shaft_arr),
        P_electrical=np.array(P_elec_arr),
        I_draw=np.array(I_arr),
        V_machine=np.array(V_arr),
        v_actual=np.array(v_arr),
        energy_cumulative=np.array(E_cum_arr),
        stall_distance=stall_distance,
        stall_reason=stall_reason,
    )
    result.compute_summaries()
    return result

"""
Power chain model.

Converts axial force and forward speed into shaft power, then electrical
input power, accounting for screw mechanics, anti-rotation losses, and
drivetrain efficiency.

Power chain
-----------

1. Useful axial mechanical power:
       P_axial = F_total × v

2. Screw shaft power (accounts for helix face friction):
       P_shaft_screw = P_axial / η_screw
       = F_total × v / η_screw

   η_screw (0.70 baseline) captures mechanical losses in the helical
   thread interface (sliding friction, wedging forces).
   PLACEHOLDER — depends on helix angle, surface finish, soil cohesion.

3. Body-rotation drag power (Variant B only):
       P_body_rot = T_body_rot × ω
       T_body_rot = μ × σ_r × π × D × L_rot × (D/2)
       ω = v / pitch × 2π
   where L_rot = rotating_fraction × L_body

4. Anti-rotation penalty:
   Of the total shaft power delivered by the motor, only fraction α
   converts to useful work (the rest is wasted as body/soil churning):
       P_shaft_input = (P_shaft_screw + P_body_rot) / α

5. Electrical input power at machine terminal:
       P_electrical = P_shaft_input / η_drivetrain

Note: This assumes the motor can deliver the required shaft power at
the available terminal voltage.  The voltage-drop solver (voltage_drop.py)
determines whether this is actually feasible given the cable resistance.
If not feasible, the simulation flags a mechanical stall.
"""

from __future__ import annotations

import math
from ..models.propulsion import PropulsionConcept
from ..models.geometry import MachineGeometry
from ..models.soil import SoilModel


def body_rotation_torque(
    mu: float,
    k_comp: float,
    soil: SoilModel,
    geometry: MachineGeometry,
    rotating_fraction: float,
) -> float:
    """Torque required to rotate the body surface against compacted soil (N·m).

    Used only for Variant B (full-body auger).

    T_body_rot = μ × σ_r × π × D × L_rot × (D/2)

    where σ_r = k_comp × σ_geo, L_rot = rotating_fraction × L_body.

    Parameters
    ----------
    mu               : friction coefficient
    k_comp           : compaction multiplier
    soil             : SoilModel (for geostatic pressure)
    geometry         : MachineGeometry
    rotating_fraction: fraction of body length that rotates (0.0–1.0)
    """
    sigma_geo = soil.geostatic_radial_stress()
    sigma_r = k_comp * sigma_geo
    L_rot = rotating_fraction * geometry.length
    # Torque = friction force × moment arm (radius)
    return mu * sigma_r * math.pi * geometry.diameter * L_rot * geometry.radius


def shaft_power(
    F_total: float,
    v_ms: float,
    propulsion: PropulsionConcept,
    geometry: MachineGeometry,
    soil: SoilModel,
    mu: float,
    k_comp: float,
) -> tuple[float, float]:
    """Compute required shaft input power and shaft torque.

    Returns
    -------
    P_shaft : float — total shaft input power delivered by motor (W)
    T_shaft : float — equivalent shaft torque (N·m) at motor output

    Parameters
    ----------
    F_total    : total axial resistance (N)
    v_ms       : target forward speed (m/s)
    propulsion : PropulsionConcept
    geometry   : MachineGeometry
    soil       : SoilModel
    mu         : local friction coefficient
    k_comp     : local compaction multiplier
    """
    if v_ms <= 0:
        return 0.0, 0.0

    # Angular velocity of auger
    omega = geometry.omega_for_speed(v_ms)  # rad/s

    # --- Step 1: Useful axial power ---
    P_axial = F_total * v_ms

    # --- Step 2: Screw shaft power (helix efficiency) ---
    P_screw = P_axial / propulsion.eta_screw

    # --- Step 3: Body-rotation drag (Variant B only) ---
    P_body_rot = 0.0
    if propulsion.body_rotation_drag and omega > 0:
        T_body_rot = body_rotation_torque(
            mu, k_comp, soil, geometry, propulsion.rotating_fraction
        )
        P_body_rot = T_body_rot * omega

    # --- Step 4: Anti-rotation penalty ---
    # α fraction of shaft power becomes useful thrust.
    # Motor must deliver (P_screw + P_body_rot) / α.
    P_shaft_total = (P_screw + P_body_rot) / propulsion.anti_rotation_alpha

    # Equivalent torque at screw shaft
    if omega > 0:
        T_shaft = P_shaft_total / omega
    else:
        T_shaft = 0.0

    return P_shaft_total, T_shaft


def electrical_power(P_shaft: float, eta_drivetrain: float) -> float:
    """Electrical power demanded from cable at machine terminal (W).

    P_electrical = P_shaft / η_drivetrain

    Parameters
    ----------
    P_shaft        : total shaft input power (W)
    eta_drivetrain : lumped motor + gearbox efficiency
    """
    if eta_drivetrain <= 0:
        raise ValueError(f"eta_drivetrain must be > 0, got {eta_drivetrain}")
    return P_shaft / eta_drivetrain


def energy_per_meter(P_electrical: float, v_ms: float) -> float:
    """Electrical energy consumed per metre of advance (J/m).

    E/m = P_electrical / v

    Parameters
    ----------
    P_electrical : electrical input power (W)
    v_ms         : forward speed (m/s)
    """
    if v_ms <= 0:
        return float("inf")
    return P_electrical / v_ms

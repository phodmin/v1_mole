"""
Axial resistance model.

Total forward resistance:
    F_total = F_nose + F_body + F_cable + F_payload

Each term is computed independently and summed.  This decomposition
lets the notebook show force breakdown stacked bars and sensitivity
analyses per term.

Force terms
-----------

F_nose — nose face penetration resistance
    The nose (screw / cutter tip) must continuously penetrate virgin soil.
    We model this as a face bearing pressure × face area:

        F_nose = q_s × A_nose

    where q_s (Pa) is the penetration resistance.

    CALIBRATION NOTE: q_s = 500 kPa is *conservative* for a cutting
    auger in soft topsoil.  A well-designed helical cutter may see
    50–200 kPa.  Treat as first-pass PLACEHOLDER.

    The soil is not excavated and returned to surface — it is compacted
    radially outward.  The q_s term represents the average pressure to
    achieve this compaction at the nose.

F_body — lateral body friction under radial soil stress
    As the mole body occupies the bore, the compacted soil annulus exerts
    radial stress on the body.  This creates normal force → friction.

        σ_r = k_comp × σ_geo          (Pa)
        σ_geo = ρ_soil × g × depth    (geostatic in-situ pressure)
        F_body = μ × σ_r × π × D × L_body

    k_comp is a dimensionless multiplier capturing the elevation of
    radial stress due to soil compaction (k_comp = 2.0 baseline).
    PLACEHOLDER — calibrate with field measurements.

    Key insight: F_body grows *linearly* with L_body.  This is why
    length is a critical design variable — longer bodies have dramatically
    higher drag.

F_cable — trailing cable mechanical drag
    F_cable = μ_cable × λ_cable × g × x

    Grows *linearly* with deployed distance.  At ~300–500 m this term
    can match or exceed F_nose + F_body.

F_payload — payload trailing friction
    Payload travels in the disturbed wake of the mole (no re-penetration).
    Simple friction:
        F_payload = μ_soil × m_payload × g

    Typically < 10 N — negligible relative to F_nose and long-range F_cable.
"""

from __future__ import annotations

import math
from ..models.geometry import MachineGeometry
from ..models.soil import SoilModel
from ..models.cable import CableModel

G: float = 9.81  # m/s²


def nose_force(q_s: float, geometry: MachineGeometry) -> float:
    """Nose face penetration resistance (N).

    F_nose = q_s × A_nose

    Parameters
    ----------
    q_s      : penetration resistance at current position (Pa)
    geometry : MachineGeometry
    """
    return q_s * geometry.nose_area


def body_friction_force(
    mu: float,
    k_comp: float,
    soil: SoilModel,
    geometry: MachineGeometry,
) -> float:
    """Body lateral friction force (N).

    F_body = μ × (k_comp × σ_geo) × π × D × L_body

    where σ_geo = ρ_soil × g × depth  (geostatic radial stress)

    The k_comp factor elevates the geostatic stress to represent the
    increased radial pressure in the compacted soil annulus.

    Parameters
    ----------
    mu       : friction coefficient at current position
    k_comp   : compaction radial-stress multiplier at current position
    soil     : SoilModel (provides ρ_soil, depth)
    geometry : MachineGeometry
    """
    sigma_geo = soil.geostatic_radial_stress()
    sigma_r = k_comp * sigma_geo
    return mu * sigma_r * geometry.lateral_area


def cable_drag_force(x: float, cable: CableModel) -> float:
    """Trailing cable mechanical drag force at distance x (N).

    F_cable = μ_cable × λ_cable × g × x

    Parameters
    ----------
    x     : deployed cable length = bore distance (m)
    cable : CableModel
    """
    return cable.drag_force(x)


def payload_drag_force(
    mu: float,
    m_payload: float,
) -> float:
    """Payload trailing friction in wake of mole (N).

    F_payload = μ_soil × m_payload × g

    Payload travels in the already-disturbed bore wake and does not
    need to re-penetrate virgin soil.  This is a minor term.

    Parameters
    ----------
    mu        : soil friction coefficient (used as friction with bore wall)
    m_payload : payload mass (kg)
    """
    return mu * m_payload * G


def axial_forces(
    x: float,
    soil: SoilModel,
    geometry: MachineGeometry,
    cable: CableModel,
    m_payload: float,
) -> dict[str, float]:
    """Compute all axial force components at position x.

    Returns a dict with keys:
        F_nose, F_body, F_cable, F_payload, F_total

    Parameters
    ----------
    x         : current bore position (m)
    soil      : SoilModel
    geometry  : MachineGeometry
    cable     : CableModel
    m_payload : payload mass (kg)
    """
    q_s, mu, k_comp = soil.parameters_at(x)

    f_nose = nose_force(q_s, geometry)
    f_body = body_friction_force(mu, k_comp, soil, geometry)
    f_cable = cable_drag_force(x, cable)
    f_payload = payload_drag_force(mu, m_payload)
    f_total = f_nose + f_body + f_cable + f_payload

    return {
        "F_nose": f_nose,
        "F_body": f_body,
        "F_cable": f_cable,
        "F_payload": f_payload,
        "F_total": f_total,
        "q_s": q_s,
        "mu": mu,
        "k_comp": k_comp,
    }

"""
Soil compaction and cavity-expansion helpers.

These functions are not directly called by the main force model
(resistance.py handles that), but they provide additional insight
into the compaction physics and can be used in standalone analyses.

Cavity expansion estimate
--------------------------
When the mole advances by dx, it displaces a cylindrical volume:
    dV = A_nose × dx

The work done against soil to create this cavity is approximately:
    dW = p_cavity × dV

where p_cavity is the cavity expansion pressure.  For a simple
Mohr-Coulomb soil model (undrained):
    p_cavity ≈ (1 + ln(E / (2 × c))) × (2 × c / 3)

This is a crude Vesic-type estimate.  For v1 we use a simpler
surrogate: treat q_s as the effective cavity expansion pressure.

Energy to displace soil per metre of advance:
    E_disp_per_m = q_s × k_comp × A_nose   (J/m)

This gives an order-of-magnitude estimate of the minimum mechanical
energy required for the compaction work itself, independent of the
propulsion mechanism efficiency.
"""

from __future__ import annotations
import math


def compaction_energy_per_meter(
    q_s: float,
    k_comp: float,
    nose_area: float,
) -> float:
    """Minimum mechanical energy to compact soil per metre of advance (J/m).

    E_comp = q_s × k_comp × A_nose

    This is a lower bound — it ignores shear and friction losses in
    the propulsion mechanism.

    Parameters
    ----------
    q_s       : penetration resistance (Pa)
    k_comp    : compaction multiplier
    nose_area : nose cross-sectional area (m²)
    """
    return q_s * k_comp * nose_area


def displaced_volume_per_meter(nose_area: float) -> float:
    """Volume of soil displaced per metre of advance (m³/m).

    Equal to the bore cross-sectional area.
    All this volume goes radially outward as compaction.
    """
    return nose_area


def radial_compaction_depth(
    nose_area: float,
    compaction_ratio: float = 0.90,
) -> float:
    """Rough estimate of radial compaction zone thickness (m).

    If the soil compacts to `compaction_ratio` of original void ratio,
    the radial compaction depth r_comp satisfies:

        π × ((r + r_comp)² - r²) × compaction_ratio = π × r²
        → r_comp ≈ r × (1 / sqrt(1 - 1/compaction_ratio) - 1)

    PLACEHOLDER — highly dependent on soil type and stress state.

    Parameters
    ----------
    nose_area        : nose cross-sectional area (m²)
    compaction_ratio : fraction of original volume that remains after
                       compaction (0.9 = 10 % volume reduction).
                       For agricultural topsoil: 0.85–0.95.
    """
    radius = math.sqrt(nose_area / math.pi)
    # Volume balance: π(r + r_c)² - π r² = π r² × (1 - compaction_ratio)
    # (r + r_c)² = r² + r² × (1/compaction_ratio)
    # Simplified linear approximation:
    r_comp = radius * (1.0 / compaction_ratio - 1.0) / 2.0
    return r_comp

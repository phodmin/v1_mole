"""
Cable model — electrical and mechanical properties of the trailing power cable.

The mole drags a permanent two-conductor cable from the surface power
supply (generator + rectifier → 48 V DC bus) to the machine.  As the
mole advances, the deployed cable length grows, increasing both
electrical resistance (voltage drop) and mechanical drag.

Electrical model
----------------
Round-trip resistance:
    R_cable(x) = ρ_Cu × 2 × x / A_conductor

where ρ_Cu = 1.72e-8 Ω·m (annealed copper, 20 °C).

Terminal voltage at machine:
    Solved via the load-line quadratic (see physics/voltage_drop.py):
        R_cable × I² - V_supply × I + P_elec = 0
    Taking the physically stable (smaller) root.

Mechanical model
----------------
Cable drag grows linearly with deployed length:
    F_cable(x) = μ_cable × λ_cable × g × x

where:
    λ_cable  — cable mass per unit length (kg/m), estimated from
                conductor cross-section, copper density, and a jacket
                mass factor.
    μ_cable  — cable-soil friction coefficient.  Baseline 0.40.

Important: at distances > ~300 m cable drag can rival or exceed the
machine's own soil resistance.  This is an expected and intended model
output — it exposes the long-range penalty clearly.

Parameters
----------
A_conductor : float
    Conductor cross-sectional area (m²).  Baseline 4.0e-6 m² (4 mm²).
V_supply    : float
    DC supply voltage at the surface end of the cable (V).  Baseline 48 V.
mu_cable    : float
    Cable–soil friction coefficient.  Baseline 0.40.
jacket_mass_factor : float
    Ratio of (jacket mass) / (copper mass) per unit length.
    1.5 means jacket adds 50 % extra mass on top of copper.
    PLACEHOLDER — varies with cable design; 1.5 is a reasonable estimate.
n_conductors : int
    Number of conductors.  2 for a simple supply + return run.
"""

from __future__ import annotations

import dataclasses
import math


# Copper electrical resistivity (Ω·m) at 20 °C
RHO_COPPER: float = 1.72e-8

# Copper density (kg/m³)
RHO_COPPER_DENSITY: float = 8960.0

G: float = 9.81  # m/s²


@dataclasses.dataclass
class CableModel:
    """Electrical and mechanical model of the trailing power cable.

    Attributes
    ----------
    A_conductor : float
        Single-conductor cross-section (m²).  E.g. 4e-6 for 4 mm².
    V_supply : float
        Surface supply voltage (V DC).
    mu_cable : float
        Cable–soil kinetic friction coefficient.
    jacket_mass_factor : float
        Multiplier on copper mass per metre to account for insulation
        and jacket.  1.5 = jacket adds 50 % extra mass.
        PLACEHOLDER — calibrate from actual cable datasheet.
    n_conductors : int
        Number of conductors in the cable (2 = supply + return).
    """

    A_conductor: float = 4.0e-6      # m²  (4 mm²)
    V_supply: float = 48.0            # V DC
    mu_cable: float = 0.40
    jacket_mass_factor: float = 1.5  # PLACEHOLDER
    n_conductors: int = 2

    # ------------------------------------------------------------------
    # Electrical
    # ------------------------------------------------------------------

    def round_trip_resistance(self, x: float) -> float:
        """Round-trip cable resistance at deployed length x (Ω).

        R = ρ_Cu × (n_conductors × x) / A_conductor

        For a two-conductor cable this is identical to
        ρ_Cu × 2 × x / A_conductor.
        """
        return RHO_COPPER * self.n_conductors * x / self.A_conductor

    def resistance_per_meter(self) -> float:
        """Round-trip resistance per metre of cable (Ω/m)."""
        return RHO_COPPER * self.n_conductors / self.A_conductor

    # ------------------------------------------------------------------
    # Mechanical
    # ------------------------------------------------------------------

    @property
    def mass_per_meter(self) -> float:
        """Cable mass per metre of deployed length (kg/m).

        Estimated from copper volume + jacket factor.
        λ = n_conductors × A_conductor × ρ_Cu × jacket_mass_factor

        PLACEHOLDER: ±30 % uncertainty; use datasheet value when available.
        """
        lambda_copper = self.n_conductors * self.A_conductor * RHO_COPPER_DENSITY
        return lambda_copper * self.jacket_mass_factor

    def drag_force(self, x: float) -> float:
        """Mechanical drag force of trailing cable at deployed length x (N).

        F_cable = μ_cable × λ_cable × g × x

        This assumes the cable lies flat in the bore with full normal
        load from its own weight.  In practice the cable may bunch or
        coil slightly (reducing drag), or the tight annulus may increase
        normal force (increasing drag).  0.40 friction coefficient is a
        mid-range PLACEHOLDER.

        This term grows *linearly* with distance — at ~300–500 m it
        becomes comparable to the machine's own soil resistance.
        """
        return self.mu_cable * self.mass_per_meter * G * x

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def A_conductor_mm2(self) -> float:
        """Conductor cross-section in mm²."""
        return self.A_conductor * 1e6

    @classmethod
    def from_mm2(
        cls,
        A_mm2: float,
        V_supply: float = 48.0,
        mu_cable: float = 0.40,
        jacket_mass_factor: float = 1.5,
        n_conductors: int = 2,
    ) -> "CableModel":
        """Convenience constructor accepting area in mm²."""
        return cls(
            A_conductor=A_mm2 * 1e-6,
            V_supply=V_supply,
            mu_cable=mu_cable,
            jacket_mass_factor=jacket_mass_factor,
            n_conductors=n_conductors,
        )

    def summary(self) -> str:
        lam = self.mass_per_meter
        r_per_m = self.resistance_per_meter()
        return (
            f"Cable: {self.A_conductor_mm2:.1f} mm²  "
            f"V_supply={self.V_supply:.0f} V  "
            f"λ={lam*1000:.1f} g/m  "
            f"R/m={r_per_m*1000:.3f} mΩ/m"
        )

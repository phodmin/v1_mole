"""
SimulationConfig — single object capturing all configurable parameters.

Provides a named, documented home for every parameter that the user
may want to vary.  Instantiating with defaults gives the agreed baseline
configuration from the design session.

Usage
-----
    cfg = SimulationConfig()                    # all defaults
    cfg = SimulationConfig(V_supply=96.0)       # vary one parameter
    machine = cfg.build_machine()
    soil    = cfg.build_soil()
"""

from __future__ import annotations

import dataclasses
from .models.machine import MoleMachine
from .models.geometry import MachineGeometry
from .models.cable import CableModel
from .models.propulsion import PropulsionConcept, PropulsionVariant
from .models.soil import SoilModel


@dataclasses.dataclass
class SimulationConfig:
    """All simulation parameters in one place.

    Geometry
    --------
    diameter_m : float  — outer diameter (m).  Default 0.10 m (100 mm).
    length_m   : float  — body length (m).     Default 1.0 m.
    pitch_m    : float  — auger pitch (m).     Default 0.10 m.

    Cable
    -----
    A_conductor_mm2  : float — conductor cross-section (mm²).  Default 4.0.
    V_supply         : float — DC supply voltage (V).           Default 48.0.
    mu_cable         : float — cable–soil friction.             Default 0.40.
    jacket_factor    : float — cable jacket mass multiplier.    Default 1.5.

    Propulsion
    ----------
    variant          : str — "A_screw_nose" | "B_full_auger" | "C_hybrid".
                             Default "C_hybrid".
    eta_screw        : float — screw mechanical efficiency.     Default 0.70.
    anti_rotation_alpha : float | None — override α; None = use variant default.

    Machine
    -------
    v_target_mh      : float — target forward speed (m/h).     Default 5.0.
    eta_drivetrain   : float — lumped drivetrain efficiency.    Default 0.75.
    m_payload        : float — payload mass (kg).              Default 1.5.
    v_min_fraction   : float — min V_machine / V_supply.       Default 0.60.

    Soil
    ----
    soil_type        : str — "homogeneous" | "three_segment" | "custom".
    q_s              : float — penetration resistance (Pa).     Default 500 kPa.
    mu_soil          : float — body–soil friction.              Default 0.30.
    k_comp           : float — compaction multiplier.           Default 2.0.
    rho_soil         : float — soil bulk density (kg/m³).       Default 1700.
    depth_m          : float — operating depth (m).            Default 0.50.
    noise_std_frac   : float — soil noise std (fractional).    Default 0.0.

    Simulation
    ----------
    x_max            : float — max bore distance (m).           Default 1000.
    dx_m             : float — step size (m).                   Default 1.0.
    """

    # Geometry
    diameter_m: float = 0.10
    length_m: float = 1.00
    pitch_m: float = 0.10

    # Cable
    A_conductor_mm2: float = 4.0
    V_supply: float = 48.0
    mu_cable: float = 0.40
    jacket_factor: float = 1.5

    # Propulsion
    variant: str = "C_hybrid"
    eta_screw: float = 0.70
    anti_rotation_alpha: float | None = None  # None = use variant default

    # Machine
    v_target_mh: float = 5.0
    eta_drivetrain: float = 0.75
    m_payload: float = 1.5
    v_min_fraction: float = 0.60

    # Soil
    soil_type: str = "homogeneous"
    q_s: float = 500_000.0      # Pa
    mu_soil: float = 0.30
    k_comp: float = 2.0
    rho_soil: float = 1700.0
    depth_m: float = 0.50
    noise_std_frac: float = 0.0

    # Simulation run
    x_max: float = 1000.0
    dx_m: float = 1.0

    # ------------------------------------------------------------------

    def build_machine(self) -> MoleMachine:
        """Construct a MoleMachine from this config."""
        geo = MachineGeometry(
            diameter=self.diameter_m,
            length=self.length_m,
            pitch=self.pitch_m,
        )
        prop_variant = PropulsionVariant(self.variant)
        prop = PropulsionConcept.from_variant(prop_variant, eta_screw=self.eta_screw)
        if self.anti_rotation_alpha is not None:
            prop.anti_rotation_alpha = self.anti_rotation_alpha

        cable = CableModel.from_mm2(
            A_mm2=self.A_conductor_mm2,
            V_supply=self.V_supply,
            mu_cable=self.mu_cable,
            jacket_mass_factor=self.jacket_factor,
        )
        return MoleMachine(
            geometry=geo,
            propulsion=prop,
            cable=cable,
            v_target_ms=self.v_target_mh / 3600.0,
            eta_drivetrain=self.eta_drivetrain,
            m_payload=self.m_payload,
            v_min_fraction=self.v_min_fraction,
        )

    def build_soil(self) -> SoilModel:
        """Construct a SoilModel from this config."""
        if self.soil_type == "homogeneous":
            return SoilModel.homogeneous(
                x_max=self.x_max,
                q_s=self.q_s,
                mu=self.mu_soil,
                k_comp=self.k_comp,
                rho_soil=self.rho_soil,
                depth=self.depth_m,
            )
        elif self.soil_type == "three_segment":
            return SoilModel.three_segment_demo(
                x_max=self.x_max,
                rho_soil=self.rho_soil,
                depth=self.depth_m,
                noise_std_frac=self.noise_std_frac,
            )
        else:
            raise ValueError(
                f"Unknown soil_type '{self.soil_type}'. "
                "Use 'homogeneous' or 'three_segment'."
            )

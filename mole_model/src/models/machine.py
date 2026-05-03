"""
MoleMachine — top-level assembly combining geometry, propulsion, and
operational parameters.

This is the object that the simulation engine operates on.  It holds
all fixed machine properties and exposes the parameters needed by the
physics modules.

Operational parameters
----------------------
v_target_ms : float
    Target forward speed (m/s).  This is the *input* to the model.
    RPM, torque, and power are *derived* from it.
    Baseline: 5 m/h = 1.389e-3 m/s.

eta_drivetrain : float
    Lumped motor + gearbox efficiency.  Baseline 0.75.
    Represents: BLDC motor (η_m ≈ 0.88) × planetary gearbox (η_g ≈ 0.85).
    Sweep range: 0.70 – 0.87.

m_payload : float
    Payload mass dragged behind the mole (kg).  Baseline 1.5 kg.

v_min_fraction : float
    Minimum acceptable machine voltage as a fraction of V_supply.
    Below this, declare electrical stall.  Baseline 0.60.
"""

from __future__ import annotations

import dataclasses
from .geometry import MachineGeometry
from .propulsion import PropulsionConcept
from .cable import CableModel


@dataclasses.dataclass
class MoleMachine:
    """Complete mole machine assembly.

    Parameters
    ----------
    geometry : MachineGeometry
        Physical dimensions (diameter, length, pitch).
    propulsion : PropulsionConcept
        Propulsion variant and efficiency parameters.
    cable : CableModel
        Trailing cable electrical and mechanical model.
    v_target_ms : float
        Target forward speed (m/s).  Default = 5 m/h.
    eta_drivetrain : float
        Lumped drivetrain efficiency.  Default 0.75.
    m_payload : float
        Payload mass (kg).  Default 1.5 kg.
    v_min_fraction : float
        Minimum V_machine / V_supply ratio before electrical stall.
        Default 0.60.
    """

    geometry: MachineGeometry = dataclasses.field(
        default_factory=MachineGeometry
    )
    propulsion: PropulsionConcept = dataclasses.field(
        default_factory=PropulsionConcept.variant_c
    )
    cable: CableModel = dataclasses.field(
        default_factory=CableModel
    )
    v_target_ms: float = 5.0 / 3600.0   # 5 m/h in m/s
    eta_drivetrain: float = 0.75
    m_payload: float = 1.5               # kg
    v_min_fraction: float = 0.60

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def v_target_mh(self) -> float:
        """Target speed in m/h."""
        return self.v_target_ms * 3600.0

    @property
    def v_min(self) -> float:
        """Minimum acceptable machine voltage (V)."""
        return self.v_min_fraction * self.cable.V_supply

    @classmethod
    def default(cls) -> "MoleMachine":
        """Construct the baseline 100 mm / 1 m / 48 V / Variant C mole."""
        return cls(
            geometry=MachineGeometry(diameter=0.10, length=1.0, pitch=0.10),
            propulsion=PropulsionConcept.variant_c(),
            cable=CableModel.from_mm2(4.0, V_supply=48.0),
            v_target_ms=5.0 / 3600.0,
            eta_drivetrain=0.75,
            m_payload=1.5,
        )

    def summary(self) -> str:
        lines = [
            "=== MoleMachine ===",
            self.geometry.summary(),
            self.propulsion.summary(),
            self.cable.summary(),
            f"v_target={self.v_target_mh:.1f} m/h  "
            f"η_drive={self.eta_drivetrain:.2f}  "
            f"m_payload={self.m_payload:.1f} kg  "
            f"V_min_frac={self.v_min_fraction:.0%}",
        ]
        return "\n".join(lines)

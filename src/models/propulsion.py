"""
Propulsion concept model.

Three variants are supported, corresponding to different architectural
choices for how the mole generates forward motion and manages reaction torque.

Variant A — Rotating screw nose
--------------------------------
Only the front auger/screw section actively generates thrust.
The aft body is non-rotating and smooth (or lightly finned).
Reaction torque is absorbed by the non-rotating aft body bearing against soil.

  anti_rotation_alpha : 0.85  (good — non-rotating body provides reaction)
  body_rotation_drag  : False  (aft body does not rotate)
  nose_fraction       : 1.0   (all penetration work done by nose screw)

Variant B — Full-body auger
-----------------------------
The entire outer body rotates as a screw/auger.
Maximum traction potential but the entire outer surface churns soil.
Reaction torque must come entirely from fins, tail spikes, or cable tension —
the weakest anti-rotation arrangement.

  anti_rotation_alpha : 0.65  (poor — whole body tries to spin)
  body_rotation_drag  : True   (rotating body adds torque penalty)
  nose_fraction       : 1.0   (nose is part of rotating assembly)

NOTE: For long runs in soft soil this variant may be physically dubious
without some form of active torque reaction.  If alpha < ~0.5, the mole
spins rather than advancing.  Consider this an optimistic scenario
unless a strong reaction torque mechanism is specified.

Variant C — Hybrid (recommended baseline)
------------------------------------------
A rotating front auger / cutter section does the soil work.
The aft body is non-rotating and carries fins / stabiliser pads that
provide the reaction torque against the soil.
Best separation of functions: cutting vs. stabilising.

  anti_rotation_alpha : 0.90  (best — dedicated fin/stabiliser section)
  body_rotation_drag  : False  (aft body does not rotate)
  nose_fraction       : 0.6   (60 % of body length is rotating cutter;
                                40 % is non-rotating aft section)

Parameters
----------
anti_rotation_alpha : float
    Fraction of shaft power that converts to useful forward thrust.
    1 - alpha is wasted as body/soil spin churning.
    Exposed as a tunable sweep parameter.
    Typical defaults: A=0.85, B=0.65, C=0.90.

body_rotation_drag : bool
    Whether to add a body-rotation torque penalty term (Variant B only).
    This represents the additional torque needed to rotate the full
    outer body surface against the compacted soil annulus.

nose_fraction : float
    Fraction of body length that constitutes the active rotating section.
    Used to scale down the body-rotation drag for Variant C (partial rotation).
    1.0 for A and B; 0.6 for C (placeholder — tune as needed).
"""

from __future__ import annotations

import dataclasses
from enum import Enum


class PropulsionVariant(str, Enum):
    """Named propulsion architecture variants."""
    A_SCREW_NOSE = "A_screw_nose"
    B_FULL_AUGER = "B_full_auger"
    C_HYBRID = "C_hybrid"


@dataclasses.dataclass
class PropulsionConcept:
    """Parameters for a specific propulsion architecture.

    Parameters
    ----------
    variant : PropulsionVariant
        Which named variant this represents.
    anti_rotation_alpha : float
        Anti-rotation effectiveness [0, 1].
        Fraction of shaft power converted to useful forward thrust.
        CALIBRATION NOTE: these defaults are educated guesses.  Real
        values depend heavily on fin design and soil cohesion.
    body_rotation_drag : bool
        Add body-rotation torque penalty (Variant B only).
    rotating_fraction : float
        Fraction of body length that rotates against soil.
        Used to scale body-rotation drag.  1.0 for B; ~0.0 for A;
        ~0.5–0.6 for C.
    eta_screw : float
        Screw mechanical efficiency — accounts for helix face friction
        during soil penetration.  Baseline 0.70.
        Sweep: 0.55, 0.70, 0.85.
        PLACEHOLDER — depends on helix angle, surface finish, soil type.
    """

    variant: PropulsionVariant = PropulsionVariant.C_HYBRID
    anti_rotation_alpha: float = 0.90
    body_rotation_drag: bool = False
    rotating_fraction: float = 0.0     # for Variant A default (non-rotating body)
    eta_screw: float = 0.70            # screw mechanical efficiency

    # ------------------------------------------------------------------
    # Factory methods for the three named variants
    # ------------------------------------------------------------------

    @classmethod
    def variant_a(cls, eta_screw: float = 0.70) -> "PropulsionConcept":
        """Variant A — rotating screw nose, non-rotating aft body."""
        return cls(
            variant=PropulsionVariant.A_SCREW_NOSE,
            anti_rotation_alpha=0.85,
            body_rotation_drag=False,
            rotating_fraction=0.0,   # aft body does not rotate
            eta_screw=eta_screw,
        )

    @classmethod
    def variant_b(cls, eta_screw: float = 0.70) -> "PropulsionConcept":
        """Variant B — full-body auger, entire surface rotates."""
        return cls(
            variant=PropulsionVariant.B_FULL_AUGER,
            anti_rotation_alpha=0.65,
            body_rotation_drag=True,
            rotating_fraction=1.0,   # entire outer body rotates
            eta_screw=eta_screw,
        )

    @classmethod
    def variant_c(cls, eta_screw: float = 0.70) -> "PropulsionConcept":
        """Variant C — hybrid: rotating front cutter, non-rotating aft fins."""
        return cls(
            variant=PropulsionVariant.C_HYBRID,
            anti_rotation_alpha=0.90,
            body_rotation_drag=False,
            rotating_fraction=0.0,   # aft section non-rotating
            eta_screw=eta_screw,
        )

    @classmethod
    def from_variant(
        cls,
        variant: PropulsionVariant,
        eta_screw: float = 0.70,
    ) -> "PropulsionConcept":
        """Create a PropulsionConcept from a PropulsionVariant enum value."""
        factories = {
            PropulsionVariant.A_SCREW_NOSE: cls.variant_a,
            PropulsionVariant.B_FULL_AUGER: cls.variant_b,
            PropulsionVariant.C_HYBRID: cls.variant_c,
        }
        return factories[variant](eta_screw=eta_screw)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def summary(self) -> str:
        return (
            f"Propulsion {self.variant.value}: "
            f"α={self.anti_rotation_alpha:.2f}  "
            f"η_screw={self.eta_screw:.2f}  "
            f"body_rot={self.body_rotation_drag}"
        )

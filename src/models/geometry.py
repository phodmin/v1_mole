"""
Machine geometry model.

Captures the physical dimensions of the mole that affect soil resistance,
torque, and packaging.

Key relationships
-----------------
A_nose      = π × (D/2)²                      — nose face area (m²)
A_body_lat  = π × D × L_body                  — lateral body surface area (m²)
helix_angle = arctan(pitch / (π × D))          — auger helix angle (rad)

Length trade-off (design insight target)
----------------------------------------
Longer body → larger A_body_lat → higher F_body (dominant at L > ~1 m)
Longer body → better anti-rotation leverage (fin / stabiliser arm)
Longer body → more payload volume / packaging space
Longer body → stiffer; harder to navigate curves

Shorter body → lower drag
Shorter body → marginal anti-rotation; may spin in place
Shorter body → less payload room

The simulation sweeps L from 300 mm to 3000 mm.

Parameters
----------
diameter : float
    Outer body diameter (m).  Baseline 0.10 m (100 mm).
    This is fixed by the concept; vary only explicitly.
length : float
    Overall body length (m).  Design variable; baseline 1.0 m.
pitch : float
    Auger helix pitch — advance per full revolution (m).
    Baseline 0.10 m (1 × diameter).
"""

from __future__ import annotations

import dataclasses
import math


@dataclasses.dataclass
class MachineGeometry:
    """Physical dimensions of the mole body.

    Parameters
    ----------
    diameter : float
        Outer diameter (m).  Baseline 0.10 m.
    length : float
        Overall body length (m).  Baseline 1.00 m.
    pitch : float
        Auger helix pitch — axial advance per revolution (m).
        Baseline 0.10 m (1 × D).
    """

    diameter: float = 0.10    # m
    length: float = 1.00      # m
    pitch: float = 0.10       # m

    # ------------------------------------------------------------------
    # Derived geometry
    # ------------------------------------------------------------------

    @property
    def radius(self) -> float:
        """Body radius (m)."""
        return self.diameter / 2.0

    @property
    def nose_area(self) -> float:
        """Frontal (nose face) cross-sectional area (m²).

        A_nose = π × r²
        """
        return math.pi * self.radius**2

    @property
    def lateral_area(self) -> float:
        """Outer lateral surface area of the body (m²).

        A_lat = π × D × L

        This is the area that experiences radial soil pressure friction.
        Grows linearly with length — the key driver of length-dependent
        drag penalty.
        """
        return math.pi * self.diameter * self.length

    @property
    def helix_angle(self) -> float:
        """Auger helix angle at the outer diameter (rad).

        θ = arctan(pitch / (π × D))

        Typical values:
          pitch = 0.5 × D  →  θ ≈ 9°
          pitch = 1.0 × D  →  θ ≈ 18°
          pitch = 2.0 × D  →  θ ≈ 33°
        """
        return math.atan(self.pitch / (math.pi * self.diameter))

    @property
    def bore_volume_per_meter(self) -> float:
        """Volume of soil displaced per metre of advance (m³/m).

        Equal to the cross-sectional area of the bore.
        All this volume must be displaced/compacted radially outward.
        """
        return self.nose_area  # m³/m

    def advance_per_revolution(self) -> float:
        """Axial advance per single revolution (m).  Equal to pitch."""
        return self.pitch

    def rpm_for_speed(self, v_ms: float) -> float:
        """Motor / auger RPM required to achieve forward speed v_ms (m/s).

        RPM = v / pitch × 60

        Typical values are very low (< 5 RPM at 10 m/h) — requires a
        high-ratio gearbox from a standard motor.
        """
        return v_ms / self.pitch * 60.0

    def omega_for_speed(self, v_ms: float) -> float:
        """Angular velocity (rad/s) for forward speed v_ms (m/s).

        ω = v / pitch × 2π
        """
        return v_ms / self.pitch * 2.0 * math.pi

    # ------------------------------------------------------------------
    # Convenience display
    # ------------------------------------------------------------------

    def summary(self) -> str:
        return (
            f"Geometry: D={self.diameter*1000:.0f} mm  "
            f"L={self.length*1000:.0f} mm  "
            f"pitch={self.pitch*1000:.0f} mm  "
            f"θ_helix={math.degrees(self.helix_angle):.1f}°"
        )

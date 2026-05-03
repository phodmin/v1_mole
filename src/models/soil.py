"""
Soil model for the mole simulation.

Supports two levels of complexity:
  1. Homogeneous soil  — constant parameters over the full run.
  2. Variable soil     — piecewise constant segments with optional
                         Gaussian random perturbations layered on top.

Modelling philosophy
--------------------
All soil parameters are empirical placeholders calibrated to "soft
agricultural / black topsoil" at 0.3–0.5 m depth.  The absolute
numbers are intentionally uncertain; the purpose is to expose sensitivities,
not to deliver geotechnical truth.

Key parameters
--------------
q_s        : Penetration resistance (Pa).
             Interpreted as the average axial pressure required to advance
             the mole nose through soil.  Think of it as a simplified cone
             resistance.  Baseline 500 kPa is *conservative* for a cutting
             auger in soft topsoil — a well-designed helix nose might see
             50–200 kPa.  Expose as tunable.

mu         : Body–soil friction coefficient (dimensionless).
             Governs the friction of the non-rotating (or slowly rotating)
             body surface against the compacted annular zone.
             Baseline 0.30.

k_comp     : Compaction / radial-stress multiplier (dimensionless).
             Scales the in-situ geostatic pressure to represent the
             elevated radial stress in the compacted annulus around the
             body.  Baseline 2.0; sweep 1.0 – 3.5.
             PLACEHOLDER — calibration data required.

rho_soil   : Bulk density of soil (kg/m³).  Baseline 1700 kg/m³.

depth      : Operating depth below surface (m).  Affects geostatic
             radial stress on the body.  Baseline 0.5 m.
"""

from __future__ import annotations

import dataclasses
from typing import Optional, Sequence
import numpy as np


@dataclasses.dataclass
class SoilSegment:
    """A piecewise-constant soil zone along the run.

    Parameters
    ----------
    x_start, x_end : float
        Start and end distance along the bore (m).  Segments should be
        contiguous and non-overlapping.
    q_s : float
        Penetration resistance (Pa).
    mu : float
        Body–soil friction coefficient.
    k_comp : float
        Compaction / radial-stress multiplier.
    label : str
        Human-readable name, e.g. "soft", "hard patch".
    """
    x_start: float
    x_end: float
    q_s: float = 500_000.0      # Pa  — baseline soft topsoil
    mu: float = 0.30
    k_comp: float = 2.0
    label: str = "soft"


class SoilModel:
    """Soil parameter model along the bore distance.

    Usage
    -----
    Homogeneous (simplest):

        soil = SoilModel.homogeneous(x_max=1000.0)

    Piecewise variable:

        segments = [
            SoilSegment(0, 400, q_s=500e3, label="soft"),
            SoilSegment(400, 500, q_s=1000e3, label="hard patch"),
            SoilSegment(500, 1000, q_s=500e3, label="soft"),
        ]
        soil = SoilModel(segments, rho=1700, depth=0.5)

    With random noise:

        soil = SoilModel(segments, noise_std_frac=0.15, noise_corr_length=10.0)
        soil.seed(42)

    Parameters
    ----------
    segments : sequence of SoilSegment
        Ordered list of soil zones.  Must cover [0, x_max].
    rho_soil : float
        Bulk soil density (kg/m³).
    depth : float
        Mole operating depth below surface (m).
    noise_std_frac : float
        Fractional std-dev of Gaussian noise applied to q_s and mu.
        0.0 = noise disabled (default).
    noise_corr_length : float
        Spatial correlation length of noise (m).  Controls how rapidly
        the random variations change along the bore.
    """

    def __init__(
        self,
        segments: Sequence[SoilSegment],
        rho_soil: float = 1700.0,
        depth: float = 0.50,
        noise_std_frac: float = 0.0,
        noise_corr_length: float = 5.0,
        seed: Optional[int] = None,
    ) -> None:
        self.segments = list(segments)
        self.rho_soil = rho_soil
        self.depth = depth
        self.noise_std_frac = noise_std_frac
        self.noise_corr_length = noise_corr_length
        self._rng = np.random.default_rng(seed)
        self._noise_cache: dict[float, np.ndarray] = {}

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def homogeneous(
        cls,
        x_max: float = 1000.0,
        q_s: float = 500_000.0,
        mu: float = 0.30,
        k_comp: float = 2.0,
        rho_soil: float = 1700.0,
        depth: float = 0.50,
    ) -> "SoilModel":
        """Create a single-segment homogeneous soil over [0, x_max]."""
        seg = SoilSegment(0.0, x_max, q_s=q_s, mu=mu, k_comp=k_comp,
                          label="homogeneous")
        return cls([seg], rho_soil=rho_soil, depth=depth)

    @classmethod
    def three_segment_demo(
        cls,
        x_max: float = 1000.0,
        rho_soil: float = 1700.0,
        depth: float = 0.50,
        noise_std_frac: float = 0.0,
    ) -> "SoilModel":
        """Demo piecewise profile: soft → hard patch → soft.

        Hard patch at 400–500 m with 2× penetration resistance.
        This shows how a hard intercalation spikes power demand and
        can trigger stall.
        """
        segments = [
            SoilSegment(0,   400,  q_s=500_000.0,  mu=0.30, k_comp=2.0, label="soft"),
            SoilSegment(400, 500,  q_s=1_000_000.0, mu=0.40, k_comp=3.0, label="hard patch"),
            SoilSegment(500, x_max, q_s=500_000.0, mu=0.30, k_comp=2.0, label="soft"),
        ]
        return cls(segments, rho_soil=rho_soil, depth=depth,
                   noise_std_frac=noise_std_frac)

    # ------------------------------------------------------------------
    # Core query
    # ------------------------------------------------------------------

    def at(self, x: float) -> SoilSegment:
        """Return the soil segment at position x (m) along the bore."""
        for seg in self.segments:
            if seg.x_start <= x < seg.x_end:
                return seg
        # Return last segment for x exactly at x_max
        return self.segments[-1]

    def parameters_at(self, x: float) -> tuple[float, float, float]:
        """Return (q_s, mu, k_comp) at position x, with optional noise.

        When noise is enabled, q_s and mu are perturbed by spatially
        correlated Gaussian noise using an Ornstein–Uhlenbeck-like
        discretisation.  k_comp is not perturbed (too uncertain already).

        Returns
        -------
        q_s   : float  — penetration resistance (Pa)
        mu    : float  — friction coefficient
        k_comp: float  — compaction multiplier
        """
        seg = self.at(x)
        q_s = seg.q_s
        mu = seg.mu
        k_comp = seg.k_comp

        if self.noise_std_frac > 0.0:
            # Simple position-based deterministic noise via sin/cos mix —
            # not statistically rigorous but fast and reproducible.
            # For a proper correlated field, replace with OU process in
            # run_longitudinal.py where x-steps are available.
            noise_q = self._noise_std_at(x, seed_offset=0)
            noise_mu = self._noise_std_at(x, seed_offset=1)
            q_s = max(q_s * (1.0 + self.noise_std_frac * noise_q), 10_000.0)
            mu = max(mu * (1.0 + self.noise_std_frac * noise_mu), 0.05)

        return q_s, mu, k_comp

    def _noise_std_at(self, x: float, seed_offset: int = 0) -> float:
        """Rough spatially-correlated noise: N(0,1) modulated by position.

        Uses a deterministic pseudo-random function based on position so
        that repeated calls to parameters_at(x) return the same value.
        Replace with proper OU/GP field if higher fidelity is needed.
        """
        freq = 1.0 / self.noise_corr_length
        phase = seed_offset * 1.234
        # Multi-harmonic to avoid perfectly sinusoidal variation
        return (
            0.5 * np.sin(2 * np.pi * freq * x + phase)
            + 0.3 * np.sin(2 * np.pi * freq * 2.7 * x + phase + 0.7)
            + 0.2 * np.sin(2 * np.pi * freq * 5.1 * x + phase + 1.4)
        )

    def geostatic_radial_stress(self) -> float:
        """In-situ geostatic radial stress at operating depth (Pa).

        σ_r_geo = ρ_soil × g × depth

        This is the ambient earth pressure before the mole arrives.
        The body then compacts the surrounding soil, elevating the
        radial stress by the k_comp factor.
        """
        return self.rho_soil * 9.81 * self.depth

    @property
    def x_max(self) -> float:
        """Maximum bore distance covered by segments (m)."""
        return max(seg.x_end for seg in self.segments)

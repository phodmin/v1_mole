"""
SimulationResult — output container for longitudinal simulation runs.

All arrays are indexed by distance step (length = n_steps).
Scalar summary fields are derived at end of post-processing.
"""

from __future__ import annotations

import dataclasses
from typing import Optional
import numpy as np


@dataclasses.dataclass
class SimulationResult:
    """Output of a longitudinal simulation run.

    Array fields (one value per distance step)
    -------------------------------------------
    x            : float[n]  — position along bore (m)
    q_s          : float[n]  — local penetration resistance (Pa)
    mu           : float[n]  — local friction coefficient
    F_nose       : float[n]  — nose penetration force (N)
    F_body       : float[n]  — body radial friction force (N)
    F_cable      : float[n]  — cable drag force (N)
    F_payload    : float[n]  — payload drag force (N)
    F_total      : float[n]  — total axial resistance (N)
    torque       : float[n]  — required shaft torque (N·m)
    P_shaft      : float[n]  — shaft power after screw + anti-rotation (W)
    P_electrical : float[n]  — electrical input power at machine terminal (W)
    I_draw       : float[n]  — current drawn from cable (A)
    V_machine    : float[n]  — voltage at machine terminal (V)
    v_actual     : float[n]  — actual forward speed (m/s)
                               (may be < v_target if power-limited)
    energy_cumulative : float[n]  — cumulative electrical energy (J)

    Scalar summary fields
    ---------------------
    total_energy_J     : total electrical energy consumed (J)
    total_energy_Wh    : total electrical energy consumed (Wh)
    stall_distance     : distance at which stall occurs (m), or None
    stall_reason       : "electrical", "mechanical", or None
    mean_speed_mh      : mean forward speed (m/h), excluding stall
    x_max_achieved     : last x where mole was still advancing (m)
    """

    # --- distance axis ---
    x: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))

    # --- local soil ---
    q_s: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))
    mu: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))

    # --- force breakdown ---
    F_nose: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))
    F_body: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))
    F_cable: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))
    F_payload: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))
    F_total: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))

    # --- drive ---
    torque: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))
    P_shaft: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))

    # --- electrical ---
    P_electrical: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))
    I_draw: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))
    V_machine: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))

    # --- motion ---
    v_actual: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))
    energy_cumulative: np.ndarray = dataclasses.field(default_factory=lambda: np.array([]))

    # --- scalar summaries ---
    total_energy_J: float = 0.0
    total_energy_Wh: float = 0.0
    stall_distance: Optional[float] = None
    stall_reason: Optional[str] = None   # "electrical" | "mechanical" | None
    mean_speed_mh: float = 0.0
    x_max_achieved: float = 0.0

    # ------------------------------------------------------------------
    # Post-processing helpers
    # ------------------------------------------------------------------

    def compute_summaries(self) -> None:
        """Compute scalar summary fields from arrays.

        Call this after populating all array fields.
        """
        if len(self.x) == 0:
            return

        self.x_max_achieved = float(self.x[-1])
        self.total_energy_J = float(self.energy_cumulative[-1]) if len(self.energy_cumulative) > 0 else 0.0
        self.total_energy_Wh = self.total_energy_J / 3600.0

        # Mean speed only over steps where machine was moving
        moving = self.v_actual > 0
        if moving.any():
            self.mean_speed_mh = float(np.mean(self.v_actual[moving])) * 3600.0
        else:
            self.mean_speed_mh = 0.0

    def energy_per_100m(self) -> Optional[float]:
        """Electrical energy consumed per 100 m of advance (Wh / 100m).

        Returns None if the run was shorter than 100 m.
        """
        mask = self.x >= 100.0
        if not mask.any():
            return None
        idx_100 = int(np.argmax(mask))
        if idx_100 == 0:
            return None
        e_100 = float(self.energy_cumulative[idx_100])
        return e_100 / 3600.0  # Wh

    def energy_per_meter_array(self) -> np.ndarray:
        """Instantaneous electrical energy per metre (J/m) at each step."""
        # E/m = P_electrical / v
        result = np.where(
            self.v_actual > 0,
            self.P_electrical / np.maximum(self.v_actual, 1e-9),
            np.nan,
        )
        return result

    def print_summary(self) -> None:
        lines = [
            f"  x_max achieved  : {self.x_max_achieved:.1f} m",
            f"  total energy    : {self.total_energy_Wh:.2f} Wh",
            f"  mean speed      : {self.mean_speed_mh:.2f} m/h",
            f"  stall distance  : {self.stall_distance} m",
            f"  stall reason    : {self.stall_reason}",
        ]
        if len(self.V_machine) > 0:
            lines.append(f"  V_machine range : {self.V_machine.min():.1f} – {self.V_machine.max():.1f} V")
        if len(self.P_electrical) > 0:
            lines.append(f"  P_elec range    : {self.P_electrical.min():.1f} – {self.P_electrical.max():.1f} W")
        print("\n".join(lines))

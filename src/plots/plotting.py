"""
Plotting utilities for the mole simulation.

All functions accept matplotlib Figure/Axes or create their own.
Each function returns the Figure for easy notebook display or saving.

Plot catalogue
--------------
1. plot_longitudinal        — full run: F, V, P, energy vs distance
2. plot_force_breakdown     — stacked area: F_nose / F_body / F_cable / F_payload
3. plot_voltage_vs_distance — V_machine vs x for multiple cable/voltage sweeps
4. plot_sweep_comparison    — generic multi-run overlay (any sweep output)
5. plot_energy_summary      — bar chart: total energy at 100 m and 1000 m
6. plot_length_sweep        — key metrics vs body length
7. plot_variant_comparison  — A/B/C variant metrics side-by-side
8. plot_feasibility_envelope — operating envelope: speed vs distance
"""

from __future__ import annotations

import math
import warnings
from typing import Any, Optional, Sequence

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.gridspec import GridSpec

from ..models.simulation_result import SimulationResult

# Use a clean style that renders well in both light and dark notebooks
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    try:
        plt.style.use("seaborn-whitegrid")
    except OSError:
        pass  # fall back to default

COLORS = plt.rcParams["axes.prop_cycle"].by_key()["color"]


# ---------------------------------------------------------------------------
# 1. Full longitudinal run overview
# ---------------------------------------------------------------------------

def plot_longitudinal(
    result: SimulationResult,
    title: str = "Mole — Longitudinal Run",
    figsize: tuple = (14, 10),
) -> plt.Figure:
    """Four-panel overview of a full longitudinal run.

    Panels:
      (a) Force components vs distance
      (b) Voltage at machine vs distance
      (c) Electrical power vs distance
      (d) Cumulative energy vs distance
    """
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    fig.suptitle(title, fontsize=13, fontweight="bold")

    x = result.x

    # (a) Forces
    ax = axes[0, 0]
    ax.plot(x, result.F_nose / 1000, label="F_nose", color="steelblue")
    ax.plot(x, result.F_body / 1000, label="F_body", color="darkorange")
    ax.plot(x, result.F_cable / 1000, label="F_cable", color="green")
    ax.plot(x, result.F_payload / 1000, label="F_payload", color="purple", linestyle="--")
    ax.plot(x, result.F_total / 1000, label="F_total", color="black", linewidth=2)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Force (kN)")
    ax.set_title("(a) Axial Force Breakdown")
    ax.legend(fontsize=8)
    _mark_stall(ax, result)

    # (b) Voltage at machine
    ax = axes[0, 1]
    ax.plot(x, result.V_machine, color="firebrick", linewidth=2)
    if len(result.V_machine) > 0 and not np.all(np.isnan(result.V_machine)):
        v_supply = result.V_machine[0] + result.I_draw[0] * 0.0  # approximation
        # Add 60% threshold line — derive from first valid I and R
        # Just annotate the minimum observed
        v_min = np.nanmin(result.V_machine)
        ax.axhline(v_min, color="gray", linestyle=":", linewidth=1,
                   label=f"min {v_min:.1f} V")
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("V_machine (V)")
    ax.set_title("(b) Voltage at Machine Terminal")
    ax.legend(fontsize=8)
    _mark_stall(ax, result)

    # (c) Electrical power
    ax = axes[1, 0]
    ax.plot(x, result.P_electrical, color="darkgreen", linewidth=2)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("P_electrical (W)")
    ax.set_title("(c) Electrical Power Draw")
    _mark_stall(ax, result)

    # (d) Cumulative energy
    ax = axes[1, 1]
    ax.plot(x, result.energy_cumulative / 3600, color="navy", linewidth=2)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Energy (Wh)")
    ax.set_title("(d) Cumulative Electrical Energy")
    _mark_stall(ax, result)

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 2. Force breakdown stacked area
# ---------------------------------------------------------------------------

def plot_force_breakdown(
    result: SimulationResult,
    title: str = "Force Breakdown vs Distance",
    figsize: tuple = (10, 5),
) -> plt.Figure:
    """Stacked area chart of force components."""
    fig, ax = plt.subplots(figsize=figsize)
    x = result.x

    labels = ["F_nose", "F_body", "F_cable", "F_payload"]
    arrays = [result.F_nose, result.F_body, result.F_cable, result.F_payload]
    colors = ["steelblue", "darkorange", "green", "purple"]

    ax.stackplot(x, [a / 1000 for a in arrays],
                 labels=labels, colors=colors, alpha=0.75)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Force (kN)")
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=9)
    _mark_stall(ax, result)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 3. Voltage vs distance (multi-run overlay)
# ---------------------------------------------------------------------------

def plot_voltage_vs_distance(
    sweep_results: list[tuple[str, SimulationResult]],
    V_supply: float = 48.0,
    v_min_fraction: float = 0.60,
    title: str = "Voltage at Machine vs Distance",
    figsize: tuple = (10, 5),
) -> plt.Figure:
    """Overlay V_machine vs distance for multiple sweep runs."""
    fig, ax = plt.subplots(figsize=figsize)

    for i, (label, res) in enumerate(sweep_results):
        color = COLORS[i % len(COLORS)]
        ax.plot(res.x, res.V_machine, label=label, color=color, linewidth=2)
        if res.stall_distance is not None:
            ax.axvline(res.stall_distance, color=color, linestyle=":", alpha=0.5)

    # V_min threshold line
    v_min = v_min_fraction * V_supply
    ax.axhline(v_min, color="red", linestyle="--", linewidth=1.5,
               label=f"V_min = {v_min:.0f} V ({v_min_fraction:.0%}×V_supply)")

    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("V_machine (V)")
    ax.set_title(title)
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 4. Generic sweep comparison (P_electrical, energy, or any metric)
# ---------------------------------------------------------------------------

def plot_sweep_comparison(
    sweep_results: list[tuple[str, SimulationResult]],
    metric: str = "P_electrical",
    ylabel: str | None = None,
    title: str | None = None,
    scale: float = 1.0,
    figsize: tuple = (10, 5),
) -> plt.Figure:
    """Overlay a chosen metric vs distance for all sweep runs.

    Parameters
    ----------
    sweep_results : list of (label, SimulationResult)
    metric        : attribute name on SimulationResult (array field)
    ylabel        : y-axis label; auto-generated from metric if None
    title         : figure title; auto-generated if None
    scale         : multiply metric values by this (e.g. 1/3600 for J→Wh)
    """
    fig, ax = plt.subplots(figsize=figsize)

    for i, (label, res) in enumerate(sweep_results):
        color = COLORS[i % len(COLORS)]
        y = getattr(res, metric, None)
        if y is None:
            warnings.warn(f"SimulationResult has no attribute '{metric}'")
            continue
        ax.plot(res.x, np.asarray(y) * scale, label=label, color=color, linewidth=2)
        if res.stall_distance is not None:
            ax.axvline(res.stall_distance, color=color, linestyle=":", alpha=0.5)

    ax.set_xlabel("Distance (m)")
    ax.set_ylabel(ylabel or metric)
    ax.set_title(title or f"{metric} vs Distance")
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 5. Energy summary bar chart
# ---------------------------------------------------------------------------

def plot_energy_summary(
    sweep_results: list[tuple[str, SimulationResult]],
    x_targets: list[float] | None = None,
    title: str = "Total Energy Consumed",
    figsize: tuple = (10, 5),
) -> plt.Figure:
    """Bar chart: cumulative energy at specified distances for each run.

    Parameters
    ----------
    x_targets : distances at which to report energy (default [100, 1000] m)
    """
    if x_targets is None:
        x_targets = [100.0, 1000.0]

    n_runs = len(sweep_results)
    n_targets = len(x_targets)
    width = 0.8 / n_targets
    x_pos = np.arange(n_runs)

    fig, ax = plt.subplots(figsize=figsize)

    for j, xt in enumerate(x_targets):
        energies = []
        for label, res in sweep_results:
            idx_arr = np.where(res.x >= xt - 0.5)[0]
            if len(idx_arr) > 0 and res.stall_distance is None:
                idx = idx_arr[0]
                e = float(res.energy_cumulative[idx]) / 3600.0  # Wh
            else:
                e = float("nan")
            energies.append(e)

        offset = (j - (n_targets - 1) / 2) * width
        bars = ax.bar(x_pos + offset, energies, width=width,
                      label=f"@ {xt:.0f} m",
                      color=COLORS[j % len(COLORS)], alpha=0.8)

    ax.set_xticks(x_pos)
    ax.set_xticklabels([label for label, _ in sweep_results], rotation=20, ha="right")
    ax.set_ylabel("Energy (Wh)")
    ax.set_title(title)
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 6. Length sweep: metrics vs body length
# ---------------------------------------------------------------------------

def plot_length_sweep(
    sweep_results: list[tuple[str, SimulationResult]],
    title: str = "Sensitivity to Body Length",
    figsize: tuple = (12, 8),
) -> plt.Figure:
    """Plot key metrics as a function of body length.

    Shows: F_total at x=0, P_electrical at x=0, stall distance, energy/100m.
    """
    # Parse length values from labels (format "L=Xmm")
    lengths_mm = []
    F0, P0, stall_d, e100 = [], [], [], []

    for label, res in sweep_results:
        try:
            L = float(label.replace("L=", "").replace("mm", ""))
        except ValueError:
            L = float("nan")
        lengths_mm.append(L)

        F0.append(float(res.F_total[0]) / 1000 if len(res.F_total) > 0 else float("nan"))
        P0.append(float(res.P_electrical[0]) if len(res.P_electrical) > 0 else float("nan"))
        stall_d.append(res.stall_distance if res.stall_distance else float(res.x[-1]) if len(res.x) > 0 else float("nan"))
        # Energy at 100m
        idx_arr = np.where(res.x >= 99.5)[0] if len(res.x) > 0 else []
        e = float(res.energy_cumulative[idx_arr[0]]) / 3600.0 if len(idx_arr) > 0 else float("nan")
        e100.append(e)

    fig, axes = plt.subplots(2, 2, figsize=figsize)
    fig.suptitle(title, fontsize=13, fontweight="bold")

    def _plot_metric(ax, y, ylabel, color):
        ax.plot(lengths_mm, y, "o-", color=color, linewidth=2, markersize=7)
        ax.set_xlabel("Body Length (mm)")
        ax.set_ylabel(ylabel)

    _plot_metric(axes[0, 0], F0, "F_total at x=0 (kN)", "steelblue")
    axes[0, 0].set_title("(a) Initial Axial Force")

    _plot_metric(axes[0, 1], P0, "P_electrical at x=0 (W)", "darkorange")
    axes[0, 1].set_title("(b) Initial Electrical Power")

    _plot_metric(axes[1, 0], stall_d, "Stall/end distance (m)", "green")
    axes[1, 0].set_title("(c) Max Range (stall or x_max)")

    _plot_metric(axes[1, 1], e100, "Energy @ 100 m (Wh)", "purple")
    axes[1, 1].set_title("(d) Energy per 100 m")

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 7. Variant comparison (A / B / C)
# ---------------------------------------------------------------------------

def plot_variant_comparison(
    sweep_results: list[tuple[str, SimulationResult]],
    x_sample_points: list[float] | None = None,
    title: str = "Propulsion Variant Comparison",
    figsize: tuple = (14, 8),
) -> plt.Figure:
    """Side-by-side comparison of variants A, B, C.

    Shows P_electrical, V_machine, F_total, and cumulative energy vs distance.
    """
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    fig.suptitle(title, fontsize=13, fontweight="bold")

    metrics = [
        ("P_electrical", "P_electrical (W)", axes[0, 0], "(a) Electrical Power"),
        ("V_machine", "V_machine (V)", axes[0, 1], "(b) Voltage at Machine"),
        ("F_total", "F_total (N)", axes[1, 0], "(c) Total Axial Force"),
        ("energy_cumulative", "Energy (Wh)", axes[1, 1], "(d) Cumulative Energy"),
    ]

    for metric, ylabel, ax, panel_title in metrics:
        for i, (label, res) in enumerate(sweep_results):
            color = COLORS[i % len(COLORS)]
            y = np.asarray(getattr(res, metric))
            if metric == "energy_cumulative":
                y = y / 3600.0  # J → Wh
            ax.plot(res.x, y, label=label, color=color, linewidth=2)
            if res.stall_distance is not None:
                ax.axvline(res.stall_distance, color=color, linestyle=":", alpha=0.5)
        ax.set_xlabel("Distance (m)")
        ax.set_ylabel(ylabel)
        ax.set_title(panel_title)
        ax.legend(fontsize=8)

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 8. Feasibility envelope
# ---------------------------------------------------------------------------

def plot_feasibility_envelope(
    speed_sweep: list[tuple[str, SimulationResult]],
    title: str = "Feasibility Envelope: Speed vs Range",
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """Plot operating envelope showing achievable range for each speed target.

    Each line in speed_sweep is a different target speed.
    The x-axis is the full run; the line shows where stall occurs.
    """
    fig, ax = plt.subplots(figsize=figsize)

    for i, (label, res) in enumerate(speed_sweep):
        color = COLORS[i % len(COLORS)]
        # Show P_electrical normalised: at what distance does power exceed X W?
        ax.plot(res.x, res.P_electrical, label=label, color=color, linewidth=2)
        if res.stall_distance is not None:
            ax.axvline(res.stall_distance, color=color, linestyle="--",
                       linewidth=1.5, alpha=0.8)
            ax.text(res.stall_distance, ax.get_ylim()[1] * 0.9,
                    f"stall\n{res.stall_distance:.0f}m",
                    color=color, fontsize=7, ha="center")

    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("P_electrical (W)")
    ax.set_title(title)
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Convenience: save all baseline plots to disk
# ---------------------------------------------------------------------------

def save_all_baseline_plots(
    result: SimulationResult,
    prefix: str = "mole_baseline",
    dpi: int = 150,
    out_dir: str = ".",
) -> list[str]:
    """Generate and save the standard set of baseline plots.

    Returns list of file paths created.
    """
    import os
    os.makedirs(out_dir, exist_ok=True)
    paths = []

    fig = plot_longitudinal(result, title="Baseline Mole — 1000 m Run")
    p = os.path.join(out_dir, f"{prefix}_longitudinal.png")
    fig.savefig(p, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    fig = plot_force_breakdown(result, title="Baseline — Force Breakdown vs Distance")
    p = os.path.join(out_dir, f"{prefix}_force_breakdown.png")
    fig.savefig(p, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    return paths


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _mark_stall(ax: plt.Axes, result: SimulationResult) -> None:
    """Add a vertical dashed line at stall distance if applicable."""
    if result.stall_distance is not None:
        ax.axvline(result.stall_distance, color="red", linestyle="--",
                   linewidth=1.5, alpha=0.8, label=f"stall @ {result.stall_distance:.0f}m")
        ax.legend(fontsize=7)

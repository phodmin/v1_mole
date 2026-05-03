"""
main.py — quick demonstration entry point.

Run with:
    cd mole_model
    python -m src.main

Produces a baseline 1000 m run and saves plots to ./plots/.
"""

from __future__ import annotations

import os
import sys

# Allow running as: python -m src.main  OR  python src/main.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import MoleMachine
from src.models.soil import SoilModel
from src.sim import run_longitudinal
from src.plots import save_all_baseline_plots


def main() -> None:
    print("=== Mole Machine — Baseline Run ===")

    machine = MoleMachine.default()
    print(machine.summary())

    soil = SoilModel.homogeneous(x_max=1000.0)

    print("\nRunning 1000 m longitudinal simulation...")
    result = run_longitudinal(machine, soil, x_max=1000.0)

    print("\nResults:")
    result.print_summary()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "plots")
    paths = save_all_baseline_plots(result, out_dir=out_dir)
    print(f"\nPlots saved to: {out_dir}")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()

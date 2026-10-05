#!/usr/bin/env python3
"""Recreate common_source_200MHz.roar with public ROAR API calls.

Install the checkout into your environment first (editable installation).
The source snapshot is never read. Expressions, constraints, four tabs,
sixteen graph settings and markers are constructed below. The active trace
colors are preserved; unused historical color-cache entries are not copied.

This reproduces the original equations, not a newly validated amplifier:
fu=200 MHz is the unity-gain target; its loaded bandwidth is about 40 MHz.
The original bare kcgs and cgg1 equation are deliberately left unchanged.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import roar_api as roar

ROOT = Path(__file__).resolve().parents[1]
CORNER = "PDK>SKY130A>n_01v8>150>nfettt27"


def build_design() -> roar.Design:
    """Build a detached native ROAR state, without Qt or loading a design file."""
    design = roar.Design("Sizing")

    # Preserve the saved Expression Editor order, including the backup equation.
    for symbol, expression in (
        ("fu", "200e6"),
        ("av_total", "5"),
        ("wu", "2*pi*fu"),
        ("cload", "5e-12"),
        ("bw", "1/(2*pi*rload*cout)"),
        ("kgm1", "kgm:M1"),
        ("kcgs1", "kcgs:M1"),
        ("kcgd1", "kcgd:M1"),
        ("kcds1", "kcds:M1"),
        ("kcs1", "kcgs + kcgd1*(1 + av_total) + kcds1"),
        ("kcs1_bkup", "kcgs + kcgd1*(1 + av_total) + kcds1"),
        ("kgds1", "kgds:M1"),
        ("idensity1", "iden:M1"),
        ("av1", "kgm1/kgds1"),
        ("ws", "kgm1/kcs1"),
        ("ids0", "(wu*cload)/kgm1"),
        ("i_total", "ids0*(1/(1 - wu/ws))"),
        ("m1_width", "i_total/idensity1"),
        ("cs1", "kcs1*i_total"),
        ("cout", "cload + cs1"),
        ("k", "1.38e-23"),
        ("gm1", "kgm1*i_total"),
        ("gds1", "kgds1*i_total"),
        ("rload", "av_total/gm1"),
        ("vgs1", "vgs:M1"),
        ("vout_bias", "vdd - rload*i_total"),
        ("vdd", "1.8"),
        ("rload_vdrop", "rload*i_total"),
        ("vth1", "vth:M1"),
        ("M1_overdrive", "vgs1 - vth1"),
        ("kcgg1", "kcgs1 + kcgd1"),
        ("av_calc_vperv", "gm1*(1/(gds1 + (1/rload)))"),
        ("cgg1", "kcgd1/i_total + kcgs1/i_total"),
    ):
        design.add_expression(symbol, expression)

    design.add_constraint("min_kcgs", "kcgs1 > 0")
    design.add_constraint("pos_current", "i_total > 0")
    # Global means inherit the corner selected in each plot, not no corners.
    # As in the original design, dimensions are not assigned automatically.
    design.add_instance("M1", corners=None)
    design.set_iterative_solver(enabled=False)

    # y, z, logarithmic Y, attached windows, vertical-marker linear position.
    tabs = (
        ("Sizing", "#c8a62b", (
            ("i_total", "av_total", True, [0, 1], 9.989238811968253),
            ("m1_width", "av_total", True, [1], 9.989238811968253),
            ("rload", "av_total", False, [2], 10.034343661108181),
            ("rload_vdrop", "av_total", False, [3], 10.034343661108181),
        )),
        ("Biasing", "#9cc82b", (
            ("M1_overdrive", "av_total", True, [0, 1], 9.955487472804144),
            ("rload_vdrop", "av_total", False, [1], 9.955487472804144),
            ("vgs1", "wu", False, [2], 9.955487472804144),
            ("vout_bias", "cload", False, [3], 9.955487472804144),
        )),
        ("Circuit Response", "#3465a4", (
            ("av_calc_vperv", "cload", True, [0, 1, 2, 3], 9.984042899561612),
            ("kcgs1", "cload", True, [1], 9.984042899561612),
            ("bw", "cload", False, [2], 9.984042899561612),
            ("av1", "cload", False, [3], 9.984042899561612),
        )),
        ("Small Signal Params", "#a9c82b", (
            ("gm1", "cload", False, [0, 1], 10.081280416588118),
            ("cgg1", "cload", False, [1], 10.081280416588118),
            ("gm1", "cload", False, [2], 10.081280416588118),
            ("gm1", "cload", False, [3], 10.081280416588118),
        )),
    )
    for tab_index, (name, color, windows) in enumerate(tabs):
        if tab_index:
            design.add_tab(name)
        for index, (y, z, log_y, attached, marker) in enumerate(windows):
            graph = design.graph(name, index)
            graph.configure(mode="design", x="kgm1", y=y, z=z, log_y=log_y,
                            locked_windows=attached, corners=[CORNER])
            graph.set_color(CORNER, color)
            graph.add_marker(marker)

    design.graph("Sizing", 0).configure(spin_x=11.5450015, spin_y=0.000871244614)
    design.graph("Circuit Response", 0).configure(spin_x=14.7119002, spin_y=8.98e-10)
    design.select_tab("Circuit Response")
    # Use portable screen coordinates instead of the source's off-screen geometry.
    design.set_window(width=1600, height=1000, theme="dark", console_visible=True)
    return design


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("common_source_200MHz.roar"))
    parser.add_argument("--show", action="store_true", help="Open the constructed design in ROAR")
    parser.add_argument("--exports", type=Path, help="Also write JSON, Python, SPICE, CSV, PNG and SVG exports")
    args = parser.parse_args(argv)
    design = build_design()
    print(f"Saved {design.save(args.output)}")

    if args.exports:
        folder = args.exports
        design.export_design(folder / "common_source_200MHz.json")
        design.export_python(folder / "common_source_200MHz.py")
        # M1 has no assigned values yet, so this initially contains only a header.
        design.export_spice(folder / "common_source_200MHz.params.spice")
        graph = design.graph("Sizing", 0)
        graph.export_csv(folder / "kgm_current.csv", home=ROOT)
        graph.export_plot(folder / "kgm_current.png", home=ROOT)
        graph.export_plot(folder / "kgm_current.svg", home=ROOT)
        result = design.evaluate(["i_total", "m1_width", "bw"], home=ROOT)[0]
        print(f"Constraint-passing samples: {int(result.constraint_mask.sum())}/{len(result.constraint_mask)}")
        print(f"Exported design and graphs to {folder}")

    if args.show:
        return roar.Session(design, home=ROOT).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
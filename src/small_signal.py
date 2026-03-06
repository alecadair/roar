#!/usr/bin/env python3
"""
small_signal.py

Derives small-signal design equations for an **arbitrary** MOSFET circuit by
building and solving a symbolic nodal admittance matrix (Modified Nodal
Analysis) using SymPy.

For every MOSFET the small-signal model comprises:
    gm · Vgs   — voltage-controlled current source  (drain → source)
    gds        — output conductance                  (drain ↔ source)
    Cgs        — gate-source capacitance             (gate  ↔ source)
    Cgd        — gate-drain capacitance              (gate  ↔ drain)
    Cds        — drain-source capacitance            (drain ↔ source)

Supply nets and bias-input nets are treated as AC ground.  The solver
produces fully symbolic transfer functions — no topology templates needed.

Usage
-----
    python small_signal.py                              # cm_ota.spice defaults
    python small_signal.py file.spice
    python small_signal.py file.spice --input inp --output out
    python small_signal.py file.spice --ac-grounds vdd,vss,itail
    python small_signal.py file.spice --latex
    python small_signal.py file.spice --no-simplify
"""

import os
import sys
import argparse
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple

import sympy
from sympy import (
    Symbol, symbols, Matrix, zeros, eye,
    simplify, collect, factor, cancel, fraction,
    Rational, pi, latex, pprint, S,
)

from parse_netlist import (
    MOSFETInstance,
    GenericInstance,
    SpiceNetlist,
    parse_spice_netlist,
)
from topology import (
    TopologyResult,
    identify_topology,
    print_topology_report,
    infer_supply_nets,
    is_supply,
    _net,
)


# ---------------------------------------------------------------------------
# Laplace variable
# ---------------------------------------------------------------------------
s = Symbol("s")


# ---------------------------------------------------------------------------
# Per-MOSFET symbol factory
# ---------------------------------------------------------------------------

@dataclass
class MOSFETSymbols:
    """SymPy symbols for one MOSFET's small-signal parameters."""
    name: str
    gm: Symbol = None
    gds: Symbol = None
    Cgs: Symbol = None
    Cgd: Symbol = None
    Cds: Symbol = None

    def __post_init__(self):
        n = self.name
        self.gm  = Symbol(f"gm_{n}",  positive=True)
        self.gds = Symbol(f"gds_{n}", positive=True)
        self.Cgs = Symbol(f"Cgs_{n}", positive=True)
        self.Cgd = Symbol(f"Cgd_{n}", positive=True)
        self.Cds = Symbol(f"Cds_{n}", positive=True)


# ---------------------------------------------------------------------------
# Node enumeration
# ---------------------------------------------------------------------------

def enumerate_nodes(
    mosfets: List[MOSFETInstance],
    ac_grounds: Set[str],
) -> Tuple[List[str], Dict[str, int]]:
    """Collect all unique nets, remove AC grounds, return ordered node list
    and a {net_name: index} mapping (0-based)."""
    all_nets: OrderedDict[str, None] = OrderedDict()
    for m in mosfets:
        for n in (m.drain, m.gate, m.source):
            nn = _net(n)
            if nn and nn not in ac_grounds:
                all_nets[nn] = None
    node_list = list(all_nets.keys())
    node_idx = {n: i for i, n in enumerate(node_list)}
    return node_list, node_idx


# ---------------------------------------------------------------------------
# Y-matrix stamping
# ---------------------------------------------------------------------------

def _stamp_conductance(Y, ni, nj, value, node_idx, n_nodes):
    """Stamp a conductance *value* between nodes ni and nj.
    If either node is None (AC ground) the corresponding row/col is skipped."""
    i = node_idx.get(ni)
    j = node_idx.get(nj)
    if i is not None:
        Y[i, i] += value
    if j is not None:
        Y[j, j] += value
    if i is not None and j is not None:
        Y[i, j] -= value
        Y[j, i] -= value


def _stamp_vccs(Y, nd, ns, ng, nref, gm, node_idx):
    """Stamp a voltage-controlled current source  gm·V(ng, nref)
    that injects current into nd and extracts from ns.

    MNA stamp:
        Y[nd, ng]  += gm
        Y[nd, nref] -= gm
        Y[ns, ng]  -= gm
        Y[ns, nref] += gm

    Any index that is None (AC ground node) is skipped.
    """
    id_ = node_idx.get(nd)
    is_ = node_idx.get(ns)
    ig  = node_idx.get(ng)
    ir  = node_idx.get(nref)

    if id_ is not None and ig is not None:
        Y[id_, ig] += gm
    if id_ is not None and ir is not None:
        Y[id_, ir] -= gm
    if is_ is not None and ig is not None:
        Y[is_, ig] -= gm
    if is_ is not None and ir is not None:
        Y[is_, ir] += gm


def stamp_mosfet(Y, mosfet: MOSFETInstance, syms: MOSFETSymbols,
                 node_idx: Dict[str, int], n_nodes: int):
    """Stamp the full small-signal model of one MOSFET into Y(s)."""
    d = _net(mosfet.drain)
    g = _net(mosfet.gate)
    src = _net(mosfet.source)

    # gds: conductance between drain and source
    _stamp_conductance(Y, d, src, syms.gds, node_idx, n_nodes)

    # gm·Vgs: VCCS from gate-source voltage, current into drain, out of source
    _stamp_vccs(Y, d, src, g, src, syms.gm, node_idx)

    # Capacitors (frequency-dependent: s·C)
    _stamp_conductance(Y, g, src, s * syms.Cgs, node_idx, n_nodes)
    _stamp_conductance(Y, g, d,   s * syms.Cgd, node_idx, n_nodes)
    _stamp_conductance(Y, d, src, s * syms.Cds, node_idx, n_nodes)


def stamp_resistor(Y, n1: str, n2: str, R: Symbol,
                   node_idx: Dict[str, int], n_nodes: int):
    """Stamp a resistor as conductance 1/R."""
    _stamp_conductance(Y, _net(n1), _net(n2), 1 / R, node_idx, n_nodes)


def stamp_capacitor(Y, n1: str, n2: str, C: Symbol,
                    node_idx: Dict[str, int], n_nodes: int):
    """Stamp a capacitor as s·C."""
    _stamp_conductance(Y, _net(n1), _net(n2), s * C, node_idx, n_nodes)


# ---------------------------------------------------------------------------
# Analysis results
# ---------------------------------------------------------------------------

@dataclass
class SmallSignalResult:
    """Holds the complete symbolic small-signal analysis."""
    # Circuit info
    node_names: List[str] = field(default_factory=list)
    ac_grounds: Set[str] = field(default_factory=set)
    input_node: str = ""
    output_node: str = ""
    mosfet_symbols: Dict[str, MOSFETSymbols] = field(default_factory=dict)

    # Symbolic matrices / solutions
    Y: Optional[Matrix] = None          # nodal admittance matrix Y(s)
    I_vec: Optional[Matrix] = None      # excitation vector
    V_solution: Optional[dict] = None   # node → symbolic voltage expression

    # Transfer functions
    Av: Optional[sympy.Expr] = None     # Vout(s) / Vin(s)
    Av_dc: Optional[sympy.Expr] = None  # Av at s=0
    Gm_eff: Optional[sympy.Expr] = None # effective Gm = Iout_sc / Vin
    Rout: Optional[sympy.Expr] = None   # output resistance (Vout / Itest)

    # Poles / zeros (if extractable)
    poles: Optional[list] = None
    zeros_num: Optional[list] = None

    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core analysis engine
# ---------------------------------------------------------------------------

def build_y_matrix(
    mosfets: List[MOSFETInstance],
    node_list: List[str],
    node_idx: Dict[str, int],
    mosfet_syms: Dict[str, MOSFETSymbols],
    passives: Optional[List[GenericInstance]] = None,
) -> Matrix:
    """Construct the symbolic nodal admittance matrix Y(s)."""
    n = len(node_list)
    Y = zeros(n, n)

    for m in mosfets:
        stamp_mosfet(Y, m, mosfet_syms[m.name], node_idx, n)

    # Stamp passive elements (R and C from GenericInstance)
    if passives:
        for p in passives:
            ptype = p.name[0].upper()
            if ptype == "R" and len(p.nodes) >= 2:
                R_sym = Symbol(f"R_{p.name}", positive=True)
                stamp_resistor(Y, p.nodes[0], p.nodes[1], R_sym, node_idx, n)
            elif ptype == "C" and len(p.nodes) >= 2:
                C_sym = Symbol(f"C_{p.name}", positive=True)
                stamp_capacitor(Y, p.nodes[0], p.nodes[1], C_sym, node_idx, n)

    return Y


def solve_for_voltage_gain(
    Y: Matrix,
    node_list: List[str],
    node_idx: Dict[str, int],
    input_node: str,
    output_node: str,
    do_simplify: bool = True,
) -> Tuple[Optional[sympy.Expr], Optional[sympy.Expr], dict]:
    """Solve Y·V = I for the voltage gain Vout/Vin.

    Applies a unit test voltage at *input_node* by modifying the Y matrix:
    replace the input-node row with a constraint V_input = 1 (Vin).
    Then Vout = H(s).
    """
    n = len(node_list)
    i_in = node_idx.get(input_node)
    i_out = node_idx.get(output_node)

    if i_in is None:
        return None, None, {}
    if i_out is None:
        return None, None, {}

    Vin = Symbol("Vin")

    # Build excitation: set V(input_node) = Vin by replacing the
    # input row with [0...1...0] and RHS with Vin.
    Y_mod = Y.copy()
    I_vec = zeros(n, 1)
    for col in range(n):
        Y_mod[i_in, col] = S.Zero
    Y_mod[i_in, i_in] = S.One
    I_vec[i_in] = Vin

    # Solve Y_mod · V = I_vec
    try:
        V_sol = Y_mod.solve(I_vec)
    except Exception as e:
        return None, None, {"error": str(e)}

    # Build solution dict
    sol_dict = {}
    for idx, name in enumerate(node_list):
        sol_dict[name] = V_sol[idx]

    Vout_expr = V_sol[i_out]

    # Transfer function H(s) = Vout / Vin
    Av_expr = Vout_expr / Vin
    if do_simplify:
        Av_expr = cancel(Av_expr)

    # DC gain: s = 0
    Av_dc = Av_expr.subs(s, 0)
    if do_simplify:
        Av_dc = cancel(Av_dc)

    return Av_expr, Av_dc, sol_dict


def solve_for_output_resistance(
    Y: Matrix,
    node_list: List[str],
    node_idx: Dict[str, int],
    output_node: str,
    input_node: str,
    do_simplify: bool = True,
) -> Optional[sympy.Expr]:
    """Find Rout by injecting a test current at the output with input grounded.

    Sets V(input_node) = 0, injects Itest at output, solves for Vout/Itest.
    """
    n = len(node_list)
    i_out = node_idx.get(output_node)
    i_in = node_idx.get(input_node)

    if i_out is None:
        return None

    Y_mod = Y.copy()
    I_vec = zeros(n, 1)
    Itest = Symbol("I_test")

    # Ground the input node
    if i_in is not None:
        for col in range(n):
            Y_mod[i_in, col] = S.Zero
        Y_mod[i_in, i_in] = S.One
        I_vec[i_in] = S.Zero

    # Inject test current at output
    I_vec[i_out] += Itest

    try:
        V_sol = Y_mod.solve(I_vec)
    except Exception:
        return None

    Rout = V_sol[i_out] / Itest
    if do_simplify:
        Rout = cancel(Rout)

    # DC Rout
    Rout_dc = Rout.subs(s, 0)
    if do_simplify:
        Rout_dc = cancel(Rout_dc)

    return Rout_dc


def extract_poles_zeros(
    H_s: sympy.Expr,
    do_simplify: bool = True,
) -> Tuple[Optional[list], Optional[list]]:
    """Try to extract poles and zeros from a rational transfer function H(s)."""
    try:
        H_cancelled = cancel(H_s)
        num, den = fraction(H_cancelled)

        from sympy import Poly
        try:
            p_den = Poly(den, s)
            poles = p_den.all_roots()
        except Exception:
            poles = None

        try:
            p_num = Poly(num, s)
            zeros_list = p_num.all_roots()
        except Exception:
            zeros_list = None

        return poles, zeros_list
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# High-level analysis orchestrator
# ---------------------------------------------------------------------------

def analyze(
    netlist: SpiceNetlist,
    ac_grounds: Optional[Set[str]] = None,
    input_node: Optional[str] = None,
    output_node: Optional[str] = None,
    do_simplify: bool = True,
) -> SmallSignalResult:
    """Run the full symbolic small-signal analysis on *netlist*.

    Parameters
    ----------
    ac_grounds : set of net names to treat as AC ground (supply + bias).
                 If None, inferred from supply nets.
    input_node : net name of the AC input stimulus.
    output_node : net name of the output.
    do_simplify : apply sympy cancel/simplify to results.
    """
    result = SmallSignalResult()

    # --- Collect MOSFETs ---
    mosfets: List[MOSFETInstance] = []
    passives: List[GenericInstance] = []
    for sc in netlist.subcircuits:
        for inst in sc.instances:
            if isinstance(inst, MOSFETInstance):
                mosfets.append(inst)
            elif isinstance(inst, GenericInstance):
                passives.append(inst)
    for inst in netlist.top_instances:
        if isinstance(inst, MOSFETInstance):
            mosfets.append(inst)
        elif isinstance(inst, GenericInstance):
            passives.append(inst)

    if not mosfets:
        result.notes.append("No MOSFETs found in netlist.")
        return result

    # --- AC grounds ---
    if ac_grounds is None:
        pos, neg = infer_supply_nets(mosfets)
        ac_grounds = pos | neg
        # Also add any bias pins (heuristic: iopin nets that look like bias)
        for p in netlist.iopins:
            pn = _net(p)
            if any(kw in pn for kw in ("bias", "tail", "itail", "ibias", "vbias")):
                ac_grounds.add(pn)
        # Add subcircuit port names that are supply
        for sc in netlist.subcircuits:
            for port in sc.ports:
                pn = _net(port)
                if pn in pos or pn in neg:
                    ac_grounds.add(pn)
    result.ac_grounds = ac_grounds

    # --- Infer input/output if not provided ---
    all_iopins = list(netlist.iopins)
    for sc in netlist.subcircuits:
        for p in sc.ports:
            if _net(p) not in {_net(x) for x in all_iopins}:
                all_iopins.append(p)

    if input_node is None:
        for p in all_iopins:
            pn = _net(p)
            if pn not in ac_grounds and pn in ("inp", "in", "vinp", "in+", "in1"):
                input_node = pn
                break
        if input_node is None:
            # Take first non-supply iopin with 'in' in name
            for p in all_iopins:
                pn = _net(p)
                if pn not in ac_grounds and "in" in pn:
                    input_node = pn
                    break
        if input_node is None:
            result.notes.append("Could not auto-detect input node. Use --input.")
            return result

    if output_node is None:
        for p in all_iopins:
            pn = _net(p)
            if pn not in ac_grounds and pn in ("out", "vout", "output", "outp"):
                output_node = pn
                break
        if output_node is None:
            for p in all_iopins:
                pn = _net(p)
                if pn not in ac_grounds and "out" in pn:
                    output_node = pn
                    break
        if output_node is None:
            result.notes.append("Could not auto-detect output node. Use --output.")
            return result

    # Ground the complementary input for single-ended analysis
    comp_input = None
    for p in all_iopins:
        pn = _net(p)
        if pn not in ac_grounds and pn != input_node and pn != output_node:
            if "in" in pn:
                comp_input = pn
                ac_grounds.add(pn)
                break

    result.input_node = input_node
    result.output_node = output_node

    if comp_input:
        result.notes.append(f"Complementary input '{comp_input}' set to AC ground "
                            f"(single-ended analysis)")

    result.notes.append(f"AC ground nodes: {', '.join(sorted(ac_grounds))}")
    result.notes.append(f"Input node:  {input_node}")
    result.notes.append(f"Output node: {output_node}")

    # --- Enumerate nodes ---
    node_list, node_idx = enumerate_nodes(mosfets, ac_grounds)
    result.node_names = node_list

    if input_node not in node_idx:
        result.notes.append(f"ERROR: input node '{input_node}' is AC ground or not in circuit.")
        return result
    if output_node not in node_idx:
        result.notes.append(f"ERROR: output node '{output_node}' is AC ground or not in circuit.")
        return result

    result.notes.append(f"Signal nodes ({len(node_list)}): {', '.join(node_list)}")

    # --- Create MOSFET symbols ---
    mosfet_syms: Dict[str, MOSFETSymbols] = {}
    for m in mosfets:
        mosfet_syms[m.name] = MOSFETSymbols(name=m.name)
    result.mosfet_symbols = mosfet_syms

    # --- Build Y matrix ---
    Y = build_y_matrix(mosfets, node_list, node_idx, mosfet_syms,
                       passives if passives else None)
    result.Y = Y

    # --- Solve for voltage gain ---
    result.notes.append("")
    result.notes.append("Solving for voltage gain Av(s) = Vout/Vin ...")
    Av_expr, Av_dc, sol_dict = solve_for_voltage_gain(
        Y, node_list, node_idx, input_node, output_node, do_simplify)

    result.Av = Av_expr
    result.Av_dc = Av_dc
    result.V_solution = sol_dict

    # --- Output resistance ---
    result.notes.append("Solving for output resistance Rout ...")
    Rout = solve_for_output_resistance(
        Y, node_list, node_idx, output_node, input_node, do_simplify)
    result.Rout = Rout

    # --- Effective Gm (Av_dc / Rout) ---
    if Av_dc is not None and Rout is not None:
        try:
            Gm_eff = cancel(Av_dc / Rout) if do_simplify else Av_dc / Rout
            result.Gm_eff = Gm_eff
        except Exception:
            pass

    # --- Poles / zeros ---
    if Av_expr is not None:
        result.notes.append("Extracting poles and zeros ...")
        poles, zeros_list = extract_poles_zeros(Av_expr, do_simplify)
        result.poles = poles
        result.zeros_num = zeros_list

    return result


# ---------------------------------------------------------------------------
# Pretty-print
# ---------------------------------------------------------------------------

def print_report(result: SmallSignalResult) -> None:
    """Print a human-readable small-signal analysis report."""
    print()
    print("=" * 70)
    print("  SMALL-SIGNAL ANALYSIS (Symbolic MNA)")
    print("=" * 70)

    for note in result.notes:
        if note:
            print(f"  {note}")
        else:
            print()

    # MOSFET symbol table
    print(f"\n  {'─' * 66}")
    print("  MOSFET Small-Signal Parameters:")
    print(f"  {'─' * 66}")
    for name, syms in result.mosfet_symbols.items():
        print(f"    {name:6s}:  {syms.gm}, {syms.gds}, "
              f"{syms.Cgs}, {syms.Cgd}, {syms.Cds}")

    # Y matrix
    if result.Y is not None:
        n = result.Y.rows
        print(f"\n  {'─' * 66}")
        print(f"  Nodal Admittance Matrix Y(s)  [{n}×{n}]")
        print(f"  Nodes: {result.node_names}")
        print(f"  {'─' * 66}")
        if n <= 8:
            for i in range(n):
                row_strs = []
                for j in range(n):
                    entry = result.Y[i, j]
                    if entry == S.Zero:
                        row_strs.append("0")
                    else:
                        row_strs.append(str(entry))
                print(f"    [{result.node_names[i]:>10s}]  " + "  |  ".join(row_strs))
        else:
            print(f"    (matrix too large to display — {n} nodes)")

    # DC Gain
    if result.Av_dc is not None:
        print(f"\n  {'─' * 66}")
        print("  DC Voltage Gain  Av(0) = Vout / Vin  at s=0:")
        print(f"  {'─' * 66}")
        _print_expr("Av_dc", result.Av_dc)

    # Transfer function
    if result.Av is not None:
        print(f"\n  {'─' * 66}")
        print("  Transfer Function  Av(s) = Vout(s) / Vin(s):")
        print(f"  {'─' * 66}")
        _print_expr("Av(s)", result.Av)

    # Output resistance
    if result.Rout is not None:
        print(f"\n  {'─' * 66}")
        print("  Output Resistance  Rout (at DC, input grounded):")
        print(f"  {'─' * 66}")
        _print_expr("Rout", result.Rout)

    # Effective Gm
    if result.Gm_eff is not None:
        print(f"\n  {'─' * 66}")
        print("  Effective Transconductance  Gm = Av_dc / Rout:")
        print(f"  {'─' * 66}")
        _print_expr("Gm", result.Gm_eff)

    # Poles / zeros
    if result.poles is not None:
        print(f"\n  {'─' * 66}")
        print("  Poles (roots of denominator):")
        print(f"  {'─' * 66}")
        for i, p in enumerate(result.poles):
            print(f"    p{i+1} = {p}")

    if result.zeros_num is not None:
        print(f"\n  {'─' * 66}")
        print("  Zeros (roots of numerator):")
        print(f"  {'─' * 66}")
        for i, z in enumerate(result.zeros_num):
            print(f"    z{i+1} = {z}")

    print()


def _print_expr(label: str, expr: sympy.Expr):
    """Print a symbolic expression, wrapping long lines."""
    expr_str = str(expr)
    if len(expr_str) < 120:
        print(f"    {label} = {expr_str}")
    else:
        # Try factored form
        try:
            expr_f = factor(expr)
            expr_str_f = str(expr_f)
            if len(expr_str_f) < len(expr_str):
                print(f"    {label} = {expr_str_f}")
                return
        except Exception:
            pass
        print(f"    {label} =")
        # Wrap at 100 chars
        for i in range(0, len(expr_str), 100):
            print(f"      {expr_str[i:i+100]}")


def print_latex_report(result: SmallSignalResult) -> None:
    """Print key equations in LaTeX format."""
    print()
    print("% " + "=" * 66)
    print("% Small-Signal Equations (auto-derived via symbolic MNA)")
    print("% " + "=" * 66)
    print(r"\begin{align}")
    if result.Av_dc is not None:
        print(rf"  A_{{v,DC}} &= {latex(result.Av_dc)} \\")
    if result.Rout is not None:
        print(rf"  R_{{out}} &= {latex(result.Rout)} \\")
    if result.Gm_eff is not None:
        print(rf"  G_m &= {latex(result.Gm_eff)} \\")
    if result.Av is not None:
        print(rf"  A_v(s) &= {latex(result.Av)}")
    print(r"\end{align}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Symbolic small-signal analysis of a SPICE netlist.")
    default_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "../design/cm_ota.spice")
    parser.add_argument("netlist", nargs="?", default=default_path,
                        help="Path to SPICE netlist file")
    parser.add_argument("--input", dest="input_node", default=None,
                        help="Input net name (e.g. inp)")
    parser.add_argument("--output", dest="output_node", default=None,
                        help="Output net name (e.g. out)")
    parser.add_argument("--ac-grounds", dest="ac_grounds", default=None,
                        help="Comma-separated AC-ground nets (e.g. vdd,vss,itail)")
    parser.add_argument("--latex", action="store_true",
                        help="Print equations in LaTeX format")
    parser.add_argument("--no-simplify", action="store_true",
                        help="Skip sympy simplification (faster for large circuits)")
    parser.add_argument("--topology", action="store_true",
                        help="Also print the topology identification report")
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.isfile(args.netlist):
        print(f"Error: file not found: {args.netlist}", file=sys.stderr)
        sys.exit(1)

    netlist = parse_spice_netlist(args.netlist)

    # Topology report (optional)
    if args.topology:
        topo = identify_topology(netlist)
        print_topology_report(topo)

    # AC grounds
    ac_grounds = None
    if args.ac_grounds:
        ac_grounds = {_net(g) for g in args.ac_grounds.split(",")}

    # Input / output
    input_node = _net(args.input_node) if args.input_node else None
    output_node = _net(args.output_node) if args.output_node else None

    # Run analysis
    result = analyze(
        netlist,
        ac_grounds=ac_grounds,
        input_node=input_node,
        output_node=output_node,
        do_simplify=not args.no_simplify,
    )

    print_report(result)

    if args.latex:
        print_latex_report(result)


if __name__ == "__main__":
    main()


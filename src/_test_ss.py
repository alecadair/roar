#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from parse_netlist import parse_spice_netlist, MOSFETInstance
from topology import infer_supply_nets
from small_signal import enumerate_nodes, MOSFETSymbols, build_y_matrix, s
from sympy import cancel, Symbol, zeros as sz, S
netlist = parse_spice_netlist("cm_ota.spice")
mosfets = []
for sc in netlist.subcircuits:
    for inst in sc.instances:
        if isinstance(inst, MOSFETInstance):
            mosfets.append(inst)
for inst in netlist.top_instances:
    if isinstance(inst, MOSFETInstance):
        mosfets.append(inst)
print(f"MOSFETs: {len(mosfets)}", flush=True)
pos, neg = infer_supply_nets(mosfets)
ac_grounds = pos | neg | {"itail", "inn"}
print(f"AC grounds: {sorted(ac_grounds)}", flush=True)
node_list, node_idx = enumerate_nodes(mosfets, ac_grounds)
print(f"Nodes ({len(node_list)}): {node_list}", flush=True)
mosfet_syms = {m.name: MOSFETSymbols(name=m.name) for m in mosfets}
print("Building Y...", flush=True)
Y = build_y_matrix(mosfets, node_list, node_idx, mosfet_syms)
print(f"Y: {Y.rows}x{Y.cols}", flush=True)
print("s=0...", flush=True)
Y_dc = Y.subs(s, 0)
n = len(node_list)
i_in = node_idx["inp"]
i_out = node_idx["out"]
Vin = Symbol("Vin")
Y_mod = Y_dc.copy()
I_vec = sz(n, 1)
for col in range(n):
    Y_mod[i_in, col] = S.Zero
Y_mod[i_in, i_in] = S.One
I_vec[i_in] = Vin
print("Solving...", flush=True)
V_sol = Y_mod.solve(I_vec)
Av_dc = cancel(V_sol[i_out] / Vin)
print(f"Av_dc = {Av_dc}", flush=True)

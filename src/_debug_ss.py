#!/usr/bin/env python3
"""Quick debug script to check matrix size and identify the hang."""
import time
from parse_netlist import parse_spice_netlist, MOSFETInstance, GenericInstance
from topology import infer_supply_nets, _net
from small_signal import (
    enumerate_nodes, MOSFETSymbols, build_y_matrix,
    solve_for_voltage_gain, solve_for_output_resistance,
)

netlist = parse_spice_netlist("../design/cm_ota.spice")

mosfets = []
passives = []
for inst in netlist.top_instances:
    if isinstance(inst, MOSFETInstance):
        mosfets.append(inst)
    elif isinstance(inst, GenericInstance):
        passives.append(inst)

pos, neg = infer_supply_nets(mosfets)
ac_grounds = pos | neg
for p in netlist.iopins:
    pn = _net(p)
    if any(kw in pn for kw in ("bias", "tail", "itail", "ibias", "vbias")):
        ac_grounds.add(pn)
ac_grounds.add("inn")  # ground complementary input

print("AC grounds:", sorted(ac_grounds))
node_list, node_idx = enumerate_nodes(mosfets, ac_grounds)
print("Signal nodes:", node_list)
print("Matrix size:", len(node_list), "x", len(node_list))

# Build symbols
mosfet_syms = {}
for m in mosfets:
    mosfet_syms[m.name] = MOSFETSymbols(name=m.name)

# Build Y matrix
t0 = time.time()
print("\nBuilding Y matrix...")
Y = build_y_matrix(mosfets, node_list, node_idx, mosfet_syms, passives if passives else None)
print(f"  Y matrix built in {time.time()-t0:.2f}s")
print(f"  Y shape: {Y.shape}")

# Try solving
input_node = "inp"
output_node = "out"

print(f"\nSolving for Av (input={input_node}, output={output_node})...")
t0 = time.time()
Av_expr, Av_dc, sol_dict = solve_for_voltage_gain(
    Y, node_list, node_idx, input_node, output_node, do_simplify=True)
print(f"  Solved in {time.time()-t0:.2f}s")
if Av_dc is not None:
    print(f"  Av_dc = {Av_dc}")
else:
    print("  Av_dc = None (failed)")

print("\nSolving for Rout...")
t0 = time.time()
Rout = solve_for_output_resistance(
    Y, node_list, node_idx, output_node, input_node, do_simplify=True)
print(f"  Solved in {time.time()-t0:.2f}s")
if Rout is not None:
    print(f"  Rout = {Rout}")


#!/usr/bin/env python3
"""
Auto-generated ROAR design script.

This script reproduces the equations and lookup-table references
defined in the ROAR Design Editor so they can be run, modified,
and version-controlled outside the GUI.
"""

import os, sys, math
import numpy as np

# ── ROAR environment ─────────────────────────────────────────────
ROAR_HOME = os.environ.get("ROAR_HOME", "")
ROAR_SRC = os.environ.get("ROAR_SRC", "")
ROAR_CHARACTERIZATION = os.environ.get("ROAR_CHARACTERIZATION", "")
sys.path.append(ROAR_SRC)
sys.path.append(os.path.join(ROAR_SRC, 'gui'))

from cid import CIDDevice, CIDCorner

# ═══════════════════════════════════════════════════════════════════
#  Device / LUT loading
# ═══════════════════════════════════════════════════════════════════

# --- Adjust the paths below to point at your LUT directories ---
# Each device maps to a directory that contains per-corner CSV files.
devices = {}

# Instance: M1  (PDK=<pdk>, model=<model>, L=<length>)
M1_lut_dir = "<set LUT directory for M1>"  # e.g. os.path.join(ROAR_CHARACTERIZATION, ...)
devices["M1"] = CIDDevice(device_name="M1",
    lut_directory=M1_lut_dir)
M1_corner_names = None  # using all (global) corners

# ═══════════════════════════════════════════════════════════════════
#  Helper: collect corner DataFrames for each device
# ═══════════════════════════════════════════════════════════════════

def get_corner_dfs(device_obj, corner_filter=None):
    """Return {corner_name: DataFrame} for a CIDDevice, optionally filtered."""
    dfs = {}
    for corner in device_obj.corners:
        if corner_filter and corner.corner_name not in corner_filter:
            continue
        dfs[corner.corner_name] = corner.df
    return dfs

# ═══════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════

fu = 200e6
av_total = 5
cload = 5e-12
k = 1.38e-23
vdd = 1.8

# ═══════════════════════════════════════════════════════════════════
#  Device-parameter lookups
# ═══════════════════════════════════════════════════════════════════
#
#  Each lookup extracts a column from every corner DataFrame of the
#  referenced device and stacks the columns into a 2-D NumPy array
#  of shape (n_bias_points, n_corners).
# ═══════════════════════════════════════════════════════════════════

def lookup_param(device_obj, param, corner_filter=None):
    """Extract *param* from every corner of *device_obj* → 2-D array."""
    cols = []
    for corner in device_obj.corners:
        if corner_filter and corner.corner_name not in corner_filter:
            continue
        if param in corner.df.columns:
            cols.append(corner.df[param].values)
    if not cols:
        raise KeyError(f"Parameter '{param}' not found in any corner")
    return np.column_stack(cols)

# ── Lookups for device M1 ──
kgm1 = lookup_param(devices["M1"], "kgm", M1_corner_names)
kcgs1 = lookup_param(devices["M1"], "kcgs", M1_corner_names)
kcgd1 = lookup_param(devices["M1"], "kcgd", M1_corner_names)
kcds1 = lookup_param(devices["M1"], "kcds", M1_corner_names)
kgds1 = lookup_param(devices["M1"], "kgds", M1_corner_names)
idensity1 = lookup_param(devices["M1"], "iden", M1_corner_names)
vgs1 = lookup_param(devices["M1"], "vgs", M1_corner_names)
vth1 = lookup_param(devices["M1"], "vth", M1_corner_names)

# ═══════════════════════════════════════════════════════════════════
#  Equations  (evaluated in dependency order)
# ═══════════════════════════════════════════════════════════════════

wu = 2*pi*fu
bw = 1/(2*pi*rload*cout)
kcs1 = kcgs + kcgd1*(1 + av_total) + kcds1
kcs1_bkup = kcgs + kcgd1*(1 + av_total) + kcds1
av1 = kgm1/kgds1
ws = kgm1/kcs1
ids0 = (wu*cload)/kgm1
i_total = ids0*(1/(1 - wu/ws))
m1_width = i_total/idensity1
cs1 = kcs1*i_total
cout = cload + cs1
gm1 = kgm1*i_total
gds1 = kgds1*i_total
rload = av_total/gm1
vout_bias = vdd - rload*i_total
rload_vdrop = rload*i_total
M1_overdrive = vgs1 - vth1
kcgg1 = kcgs1 + kcgd1
av_calc_vperv = gm1*(1/(gds1 + (1/rload)))
cgg1 = kcgd1/i_total + kcgs1/i_total

# ═══════════════════════════════════════════════════════════════════
#  Constraints  (boolean masks)
# ═══════════════════════════════════════════════════════════════════

min_kcgs = kcgs1 > 0  # constraint
pos_current = i_total > 0  # constraint

# ═══════════════════════════════════════════════════════════════════
#  Instance table summary
# ═══════════════════════════════════════════════════════════════════

instance_info = {
    "M1": {"kgm": "", "ID": "", "W": "", "L": "", "Corners": "[*Global*]"},
}

# ═══════════════════════════════════════════════════════════════════
#  Print results
# ═══════════════════════════════════════════════════════════════════

results = {}
results["fu"] = fu
results["av_total"] = av_total
results["cload"] = cload
results["k"] = k
results["vdd"] = vdd
results["kgm1"] = kgm1
results["kcgs1"] = kcgs1
results["kcgd1"] = kcgd1
results["kcds1"] = kcds1
results["kgds1"] = kgds1
results["idensity1"] = idensity1
results["vgs1"] = vgs1
results["vth1"] = vth1
results["wu"] = wu
results["bw"] = bw
results["kcs1"] = kcs1
results["kcs1_bkup"] = kcs1_bkup
results["av1"] = av1
results["ws"] = ws
results["ids0"] = ids0
results["i_total"] = i_total
results["m1_width"] = m1_width
results["cs1"] = cs1
results["cout"] = cout
results["gm1"] = gm1
results["gds1"] = gds1
results["rload"] = rload
results["vout_bias"] = vout_bias
results["rload_vdrop"] = rload_vdrop
results["M1_overdrive"] = M1_overdrive
results["kcgg1"] = kcgg1
results["av_calc_vperv"] = av_calc_vperv
results["cgg1"] = cgg1

for name, val in results.items():
    if isinstance(val, np.ndarray):
        print(f"{name}: shape={val.shape}, min={np.min(val):.6g}, max={np.max(val):.6g}")
    else:
        print(f"{name} = {val}")

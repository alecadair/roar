![ROAR Logo](images/png/ROAR_LOGO.png)

# ROAR Lookup Table (LUT) Specification

## Overview

ROAR uses pre-characterized transistor lookup tables (LUTs) stored as CSV files
to enable gm/Id-based analog design exploration.  This document describes the
directory layout, CSV file format, column naming conventions, and registration
steps required so that users can generate LUTs from **any** PDK — including
proprietary ones — and load them into ROAR.

---

## 1  Directory Structure

ROAR expects a strict three-level directory hierarchy.  The top-level directory
is called the **LUT root** and is what gets registered in `tech_list.txt`.

```
<LUT_ROOT>/
├── <model_1>/                        # Device model directory
│   ├── LUT_<N|P>_<length_token>/     # Length directory
│   │   ├── <corner_file_1>.csv
│   │   ├── <corner_file_2>.csv
│   │   └── ...
│   ├── LUT_<N|P>_<length_token>/
│   │   └── ...
│   └── ...
├── <model_2>/
│   └── ...
└── ...
```

### 1.1  LUT Root Directory

The LUT root directory name is arbitrary.  It is the path that appears in
`tech_list.txt` (see Section 5).  ROAR iterates every **immediate
sub-directory** of this root and treats each one as a *device model*.

**Examples from shipped PDKs:**

| PDK | LUT Root |
|-----|----------|
| SKY130 | `characterization/sky130/LUTs_SKY130` |
| IHP SG13G2 | `characterization/ihp130/LUTs_IHP130` |

### 1.2  Model Directories (Level 1)

Each sub-directory of the LUT root represents a distinct **device model**
(sometimes called a device *flavor*).  The directory name becomes the model name
shown in the ROAR Tech Browser tree.

Typical naming conventions (not enforced — any name works):

| PDK | NMOS model dir | PMOS model dir |
|-----|----------------|----------------|
| SKY130 RVT | `n_01v8` | `p_01v8` |
| SKY130 LVT | `n_01v8_lvt` | `p_01v8_lvt` |
| IHP SG13G2 | `nfet_sg13_lv` | `pfet_sg13_lv` |

### 1.3  Length Directories (Level 2)

Inside each model directory, create one sub-directory **per channel length**.
The directory name **must** follow the pattern:

```
LUT_<N|P>_<length_token>
```

The `<length_token>` is parsed by splitting the directory name on `_` and
taking the **last token**.  This token becomes the length label shown in the
Tech Browser.

**Examples:**

| Directory Name | Extracted Length Token |
|----------------|-----------------------|
| `LUT_N_150`    | `150`   |
| `LUT_P_500`    | `500`   |
| `LUT_N_130u`   | `130u`  |
| `LUT_N_1.5u`   | `1.5u`  |
| `LUT_P_1000`   | `1000`  |

> **Note:** The length token is a display label only.  The actual electrical
> length value used for calculations is read from the `L` column inside each
> CSV file.

### 1.4  Corner CSV Files (Level 3 — Leaf Files)

Each length directory contains one CSV file **per PVT corner**.  Every `.csv`
file in the directory is loaded as a separate corner.  The **file name**
(without the `.csv` extension) becomes the corner name in the Tech Browser.

**Naming convention (recommended but not enforced):**

```
<device_prefix><process_corner><temperature>.csv
```

Examples:

| File Name | Corner Name (in browser) | Meaning |
|-----------|--------------------------|---------|
| `nfettt27.csv` | `nfettt27` | NFET, typical-typical, 27 °C |
| `nfetss-25.csv` | `nfetss-25` | NFET, slow-slow, −25 °C |
| `pfetff75.csv` | `pfetff75` | PFET, fast-fast, 75 °C |
| `nfetmos_tt27.csv` | `nfetmos_tt27` | NFET, typical-typical, 27 °C (IHP style) |

**Complete example tree (SKY130, two models, one length each, abbreviated):**

```
LUTs_SKY130/
├── n_01v8/
│   ├── LUT_N_150/
│   │   ├── nfetff-25.csv
│   │   ├── nfetff27.csv
│   │   ├── nfetff75.csv
│   │   ├── nfetss-25.csv
│   │   ├── nfetss27.csv
│   │   ├── nfetss75.csv
│   │   ├── nfettt-25.csv
│   │   ├── nfettt27.csv
│   │   └── nfettt75.csv
│   ├── LUT_N_200/
│   │   └── ...
│   └── ...
├── p_01v8/
│   ├── LUT_P_150/
│   │   ├── pfetff-25.csv
│   │   ├── pfetff27.csv
│   │   └── ...
│   └── ...
├── n_01v8_lvt/
│   └── ...
└── p_01v8_lvt/
    └── ...
```

---

## 2  CSV File Format

Each CSV file is a standard comma-separated-values file loaded with
`pandas.read_csv()`.  Leading whitespace around column names is stripped
automatically (`skipinitialspace=True`).

### 2.1  Header Row

The **first line** must be a comma-separated list of column names.  Column
names are **case-insensitive** — ROAR normalizes all headers to lowercase on
import.

### 2.2  Required Columns

The following columns **must** be present in every CSV file (shown in
lowercase; original case does not matter):

| Column | Description | Units |
|--------|-------------|-------|
| `gm`   | Transconductance | S (Siemens) |
| `id`   | Drain current (alias: `ids`) | A |
| `cgg`  | Total gate capacitance | F |
| `cgs`  | Gate-source capacitance | F |
| `cgd`  | Gate-drain capacitance | F |
| `cds`  | Drain-source capacitance | F |
| `css`  | Source-source capacitance | F |
| `cdd`  | Drain-drain capacitance | F |
| `gds`  | Output conductance | S |
| `vth`  | Threshold voltage | V |
| `vdsat`| Saturation voltage | V |
| `vgs`  | Gate-source voltage | V |
| `vds`  | Drain-source voltage | V |
| `w`    | Channel width | see note below |
| `l`    | Channel length | see note below |
| `pdk`  | PDK identifier string | — |

**Also required — one of the following pairs** (ROAR auto-aliases them):

| Column | Alias | Description |
|--------|-------|-------------|
| `kgm`  | `gm_id` | gm/Id ratio (V⁻¹) |

If you provide `gm_id`, ROAR will create a `kgm` column automatically
(and vice versa).  Similarly, if you provide `id`, ROAR creates an `ids`
alias.

### 2.3  Optional Columns

These columns are **computed automatically** by ROAR if missing, so you do not
need to include them:

| Column | Derivation |
|--------|------------|
| `ft`   | `gm / (2π · cgg)` |
| `rds`  | `1 / gds` |
| `wt`   | `gm / cgg` |
| `kcdd` | `cdd / ids` |
| `kcgg` | `cgg / ids` |
| `kcgd` | `\|cgd\| / ids` |
| `kcgs` | `\|cgs\| / ids` |
| `kcds` | `\|cds\| / ids` |
| `gmro` | `gm / gds` (also aliased as `gm/gds`) |
| `gds/gm` | `gds / gm` |
| `kgds` | `gds / ids` |
| `iden` | `ids / W` (current density) |
| `kgmft`| `kgm · ft` (also aliased as `gmidft`) |

### 2.4  Sweep / Index Columns

The characterization scripts produce interleaved `isweep` / `i_<param>` columns
(e.g., `isweep`, `i_id`, `i_cgg`, …).  These are the DC sweep current values
at which each parameter was measured.  They are preserved in the DataFrame but
are **not used directly** by the graphing engine — ROAR plots parameter-vs-
parameter from the named columns.  You may include or omit these columns
freely.

### 2.5  Width and Length Encoding

The `W` and `L` columns must contain a **single constant value** per file
(every row has the same W and L).  The values are read from the first data row.

* **SKY130 convention:** `W` is in µm as a bare number (e.g., `0.840`); `L` is
  in µm as a bare number (e.g., `0.150`).  ROAR internally multiplies W by 1e-6
  when `pdk == "sky130"` to compute current density (`iden`).
* **IHP convention:** `W` is a bare number (e.g., `1.00`); `L` is a string with
  unit suffix (e.g., `.130u`).

Choose whichever convention your characterization script produces.  The `L`
value for each file **must match** the length implied by its parent directory
name.

### 2.6  PDK Column

The `pdk` column must contain a **single constant string** identifying the PDK.
This string is stored in the corner object and can be used by downstream logic.

Examples: `sky130`, `ihp-sg13g2`, `my_custom_pdk`.

### 2.7  Example: Minimal CSV

```csv
gm,id,cgg,cgs,cgd,cds,css,cdd,gds,vth,vdsat,vgs,vds,kgm,w,l,pdk
2.749e-08,9.996e-10,3.227e-16,-6.308e-17,3.866e-19,3.829e-17,5.732e-17,-1.857e-19,1.623e-09,7.648e-01,4.324e-02,3.987e-01,3.987e-01,2.750e+01,0.840,0.150,my_pdk
3.431e-08,1.250e-09,3.252e-16,-6.691e-17,4.036e-19,4.044e-17,6.053e-17,-1.942e-19,2.002e-09,7.648e-01,4.324e-02,4.064e-01,4.064e-01,2.744e+01,0.840,0.150,my_pdk
```

### 2.8  Example: Full CSV (With Sweep Columns)

This is the format produced by the shipped ngspice characterization scripts:

```csv
isweep,gm,i_id,id,i_cgg,cgg,i_cgs,cgs,i_cgd,cgd,i_cds,cds,i_css,css,i_cdd,cdd,i_gds,gds,i_vth,vth,i_vdsat,vdsat,i_vgs,vgs,i_vds,vds,i_rds,rds,i_wt,wt,i_ft,ft,i_kgm,kgm,W,L,pdk
1.000e-09,2.749e-08,1.000e-09,9.996e-10,1.000e-09,3.227e-16,...,2.750e+01,0.840,0.150,sky130
```

---

## 3  Characterization

ROAR does **not** mandate a specific simulator.  Any tool that can sweep drain
current and extract the required MOSFET small-signal parameters can produce
valid LUTs.

### 3.1  General Procedure

1. **Build a diode-connected MOSFET test bench.**  Connect gate to drain so the
   device is biased at `VGS = VDS`.  Apply a swept DC current source from drain
   to source.

2. **Sweep the drain current** logarithmically from a small value (e.g., 1 nA)
   to a large value (e.g., 1 mA).  Typical resolution is 20 points per decade.

3. **Extract small-signal parameters** at each bias point: `gm`, `gds`, `cgg`,
   `cgs`, `cgd`, `cds`, `css`, `cdd`, `vth`, `vdsat`, `vgs`, `vds`.

4. **Compute derived quantities** (or let ROAR compute them):
   - `kgm = gm / id`
   - `ft = gm / (2π · cgg)`
   - `rds = 1 / gds`

5. **Append metadata columns** (`W`, `L`, `pdk`) as constant values to every
   row.

6. **Write the CSV** with a header row and one data row per sweep point.

7. **Repeat** for every combination of:
   - Device model (NMOS, PMOS, LVT, HVT, …)
   - Channel length
   - Process corner (TT, SS, FF, …)
   - Temperature (−25 °C, 27 °C, 75 °C, …)

### 3.2  Reference Scripts

The `characterization/` directory contains working examples:

| Script | PDK | Simulator |
|--------|-----|-----------|
| `create_lookup_tables_ngspice_sky130.py` | SKY130 | ngspice |
| `create_lookup_tables_ngspice_ihp-sg13g2.py` | IHP SG13G2 | ngspice |

These scripts use a SPICE template (`char_template.cir` or variant) with
placeholder tokens `_LENGTH`, `_CORNER`, and `_TEMPERATURE` that are substituted
at runtime.  You can adapt the same approach for any PDK by modifying the
`.lib` include path and device instance names.

### 3.3  Using a Different Simulator

If you use Spectre, HSPICE, Xyce, or another simulator:

1. Create an equivalent test bench in your simulator's format.
2. Extract the same set of small-signal parameters.
3. Write the results to CSV with the column names listed in Section 2.2.
4. Place the files in the directory structure described in Section 1.

---

## 4  Data Conventions

### 4.1  Sign Conventions

All parameter values should use the **simulator's native sign convention**.
Capacitances may be negative (e.g., `cgs` is typically negative for MOSFETs in
many simulators).  ROAR takes absolute values where needed (e.g., when
computing `kcgs`, `kcgd`, `kcds`).

### 4.2  Sweep Order

Rows must be ordered by **increasing drain current**.  The characterization
scripts sweep current logarithmically from low to high, which naturally
produces this order.

### 4.3  Units

All electrical quantities should be in **SI base units** (Amperes, Volts,
Siemens, Farads).  Width and length are in **micrometers** as bare numbers
(e.g., `0.150` for 150 nm) or with a unit suffix string (e.g., `.130u`).

---

## 5  Registering LUTs with ROAR

### 5.1  `tech_list.txt`

ROAR loads LUTs at startup from the file `${ROAR_HOME}/tech_list.txt`.  Each
non-empty, non-comment line has the format:

```
<PDK_NAME>  <LUT_ROOT_PATH>
```

| Field | Description |
|-------|-------------|
| `<PDK_NAME>` | Display name shown in the Tech Browser (e.g., `MY-PDK`). |
| `<LUT_ROOT_PATH>` | Absolute or `${ROAR_HOME}`-relative path to the LUT root directory. |

**Environment variables** are supported in the path via `${VAR}` or `$VAR`
syntax.  The `~` home-directory shorthand is also expanded.

**Example `tech_list.txt`:**

```
SKY130A      ${ROAR_HOME}/characterization/sky130/LUTs_SKY130
IHP-SG13G2   ${ROAR_HOME}/characterization/ihp130/LUTs_IHP130
MY-CUSTOM    /home/user/my_pdk/LUTs
WORK-PDK     ${PDK_ROOT}/luts/characterized
```

Lines starting with `#` are treated as comments.

### 5.2  Adding LUTs at Runtime

LUTs can also be added interactively via the ROAR Tech Browser's **"Add LUT"**
button, which prompts for a directory and PDK name.

---

## 6  Complete Walkthrough: Adding a New PDK

This section walks through adding a fictional PDK called **ACME45** with two
device flavors (nfet, pfet), two channel lengths (45 nm and 90 nm), and three
PVT corners (TT @ 27 °C, SS @ −40 °C, FF @ 125 °C).

### Step 1: Create the directory structure

```
mkdir -p LUTs_ACME45/nfet_core/LUT_N_45n
mkdir -p LUTs_ACME45/nfet_core/LUT_N_90n
mkdir -p LUTs_ACME45/pfet_core/LUT_P_45n
mkdir -p LUTs_ACME45/pfet_core/LUT_P_90n
```

### Step 2: Run characterization and produce CSVs

For each combination of (model, length, corner, temperature), run your
simulator and write a CSV.  Place the files:

```
LUTs_ACME45/
├── nfet_core/
│   ├── LUT_N_45n/
│   │   ├── nfettt27.csv
│   │   ├── nfetss-40.csv
│   │   └── nfetff125.csv
│   └── LUT_N_90n/
│       ├── nfettt27.csv
│       ├── nfetss-40.csv
│       └── nfetff125.csv
└── pfet_core/
    ├── LUT_P_45n/
    │   ├── pfettt27.csv
    │   ├── pfetss-40.csv
    │   └── pfetff125.csv
    └── LUT_P_90n/
        ├── pfettt27.csv
        ├── pfetss-40.csv
        └── pfetff125.csv
```

Each CSV must contain at minimum:

```csv
gm,id,cgg,cgs,cgd,cds,css,cdd,gds,vth,vdsat,vgs,vds,kgm,w,l,pdk
<data rows...>
```

### Step 3: Register in tech_list.txt

Add one line to `${ROAR_HOME}/tech_list.txt`:

```
ACME45  /path/to/LUTs_ACME45
```

### Step 4: Launch ROAR

The Tech Browser will show:

```
PDK
└── ACME45
    ├── nfet_core
    │   ├── 45n
    │   │   ├── nfettt27
    │   │   ├── nfetss-40
    │   │   └── nfetff125
    │   └── 90n
    │       ├── nfettt27
    │       ├── nfetss-40
    │       └── nfetff125
    └── pfet_core
        ├── 45n
        │   └── ...
        └── 90n
            └── ...
```

---

## 7  Troubleshooting

| Symptom | Likely Cause |
|---------|--------------|
| PDK does not appear in Tech Browser | Path in `tech_list.txt` is wrong or directory does not exist. Check the terminal for `Warning: tech dir not found` messages. |
| Model directory is empty in browser | Length sub-directories are missing or do not contain `.csv` files. |
| `KeyError: 'l'` on import | CSV is missing the `l` (channel length) column. |
| `KeyError: 'pdk'` on import | CSV is missing the `pdk` column. |
| `KeyError: 'id'` / `KeyError: 'ids'` | CSV must have either an `id` or `ids` column. |
| `KeyError: 'kgm'` | CSV must have either a `kgm` or `gm_id` column. |
| Graphs look wrong or empty | Check that values are in SI units and that the sweep current range covers the region of interest. |
| `iden` (current density) is wrong | For `sky130`, W is auto-scaled by 1e-6.  For other PDKs, ensure W is in the correct unit so that `ids / W` gives A/µm or A/m as desired. |

---

## 8  Quick Reference: Column Name Summary

**Bold** = must be present in the CSV.  *Italic* = auto-computed if absent.

| Column | Required | Description |
|--------|----------|-------------|
| **`gm`** | ✅ | Transconductance |
| **`id`** (or `ids`) | ✅ | Drain current |
| **`cgg`** | ✅ | Total gate capacitance |
| **`cgs`** | ✅ | Gate-source capacitance |
| **`cgd`** | ✅ | Gate-drain capacitance |
| **`cds`** | ✅ | Drain-source capacitance |
| **`css`** | ✅ | Source-source capacitance |
| **`cdd`** | ✅ | Drain-drain capacitance |
| **`gds`** | ✅ | Output conductance |
| **`vth`** | ✅ | Threshold voltage |
| **`vdsat`** | ✅ | Saturation voltage |
| **`vgs`** | ✅ | Gate-source voltage |
| **`vds`** | ✅ | Drain-source voltage |
| **`kgm`** (or `gm_id`) | ✅ | gm/Id ratio |
| **`w`** | ✅ | Channel width |
| **`l`** | ✅ | Channel length |
| **`pdk`** | ✅ | PDK identifier string |
| *`ft`* | — | Transit frequency |
| *`rds`* | — | Drain-source resistance |
| *`kcdd`* | — | Cdd / Id |
| *`kcgg`* | — | Cgg / Id |
| *`kcgd`* | — | |Cgd| / Id |
| *`kcgs`* | — | |Cgs| / Id |
| *`kcds`* | — | |Cds| / Id |
| *`gmro`* | — | gm · ro = gm / gds |
| *`kgds`* | — | gds / Id |
| *`iden`* | — | Id / W (current density) |
| *`kgmft`* | — | kgm · ft |


# ROAR - Robust Optimal Analog Reuse

**Version:** 2.0  
**Date:** January 2026  
**Author:** Alec S. Adair

---

## Overview

ROAR (Robust Optimal Analog Reuse) is a powerful analog circuit design and optimization tool that enables engineers to explore device characteristics, visualize lookup tables (LUTs), and optimize analog designs across multiple process corners.

### Key Features

- **Interactive Device Characterization Viewer** - Visualize transistor performance metrics across multiple corners
- **Design Equation Solver** - Define and solve complex design equations with multi-dimensional parameter sweeps
- **3D Surface Plotting** - Visualize relationships between three or more parameters
- **Multi-Corner Analysis** - Compare device behavior across process, voltage, and temperature (PVT) corners
- **Custom Technology Support** - Import your own device characterization data
- **Locked Window Synchronization** - Synchronize multiple plots for comparative analysis
- **Interactive Markers** - Place and manipulate measurement markers on plots

---

## Quick Start

### Installation

1. **Set Environment Variables** (required):
   ```tcsh
   setenv ROAR_HOME /path/to/roar
   setenv ROAR_CHARACTERIZATION ${ROAR_HOME}/characterization
   setenv ROAR_DESIGN ${ROAR_HOME}/design
   setenv ROAR_SRC ${ROAR_HOME}/src
   ```

2. **Install Dependencies**:
   ```bash
   cd ${ROAR_SRC}/gui
   pip install -r requirements.txt
   ```

3. **Configure Technologies**:
   Create or edit `${ROAR_HOME}/tech_list.txt`:
   ```
   SKY130A ${ROAR_CHARACTERIZATION}/sky130/LUTs_SKY130
   IHP-SG13G2 ${ROAR_CHARACTERIZATION}/ihp130/LUTs_IHP130
   ```

4. **Launch ROAR**:
   ```bash
   cd ${ROAR_SRC}/gui
   python3 roar_gui.py
   ```

---

## Application Structure

### Main Components

1. **ROARHeader** - Application banner with quick-access buttons
2. **ROAREditorWindow** - Design equation editor and device instance table
3. **ROARGraphGrid** - 2×2 grid of lookup windows for visualization
4. **ROARLookupWindow** - Individual plotting window with tech browser

### Workflow Modes

#### Device Parameters Mode
- **Purpose**: Explore raw device characterization data
- **Use Case**: Understand transistor behavior, find optimal operating points
- **X/Y Axes**: Direct device parameters (gm, ids, vgs, etc.)

#### Design Equations Mode  
- **Purpose**: Design circuits using equations that reference device parameters
- **Use Case**: Size transistors, optimize performance metrics
- **X/Y/Z Axes**: User-defined equations combining device parameters

---

## Key Capabilities

### 1. Interactive Plotting

#### 2D Plots
- **Linear/Log Scales** - Toggle X and Y axes independently
- **Dual-Axis Plotting** - Plot two different Y parameters with different units
- **Auto-Fit** - Automatically scale view to data
- **Pan and Zoom** - Navigate plots with mouse controls

#### 3D Plots
- **Surface Plots** - Visualize three-parameter relationships
- **Contour Plots** - 2D projection with contour lines
- **Interactive Rotation** - Click and drag to rotate view
- **Navigation Toolbar** - Pan, zoom, and reset controls
- **Color Mapping** - Per-corner color schemes

### 2. Markers and Measurements

#### Vertical Markers (V key)
- Display X and Y values at cursor position
- Show values for all plotted curves

#### Horizontal Markers (H key)
- Display Y value across all curves
- Useful for finding X values at target Y

#### Marker Operations
- **Select**: Click on marker line
- **Move**: Drag selected marker
- **Delete**: Select marker(s), press Delete
- **Unselect All**: Press Escape
- **Show Difference**: Select two markers, press D

### 3. Window Synchronization

#### Locking Windows
1. Check the attachment checkbox for another window
2. Windows are now "locked"
3. Markers move together
4. Log scale changes propagate
5. Can be bidirectional

#### Copy/Paste Windows
1. Click "Copy" on source window
2. Click "Paste" on destination window  
3. All settings, colors, and markers are copied

### 4. Design Equation Solver

#### Equation Syntax
```
# Simple assignments
kgm1 = kgm:M1          # Lookup from device M1
ids_total = ids1 + ids2 # Arithmetic

# Functions
sqrt(x)
log(x), log10(x)
sin(x), cos(x), tan(x)
arcsin(x), arccos(x), arctan(x)
abs(x)

# 3D Equations (two independent variables)
kgm1 = kgm:M1          # Independent 1
kgm2 = kgm:M2          # Independent 2  
product = kgm1 * kgm2  # Dependent (for 3D)
```

#### Device Lookup Syntax
```
parameter:device_instance
```
Examples:
- `gm:M1` - Transconductance of M1
- `ids:M2` - Drain current of M2
- `vgs:M3` - Gate-source voltage of M3

#### Multi-Device 3D Plotting
1. Add device instances in the Instance Table
2. Assign corners to each device (click "Corners" cell)
3. Use lookups like `kgm:M1`, `kgm:M2` in equations
4. Enable "3-D" checkbox
5. Each device uses its own corner LUT

---

## User Interface Guide

### Menu Bar

#### File Menu
- **New Design** - Clear all equations and start fresh
- **Open Design** - Load design from JSON file
- **Save Design** - Save current design
- **Save Design As** - Save with new filename
- **Export Plot** - Save current plot as image

#### View Menu
- **New Graph Tab** - Create additional graph grid
- **Toggle Dark Mode** - Switch UI theme
- **Show/Hide Design Editor** - Undock editor to separate window

#### Tools Menu
- **Reload Technologies** - Refresh LUT data
- **Clear All Markers** - Remove markers from all windows
- **Reset Window Layout** - Restore default sizes

### Tech Browser

The Tech Browser shows available technologies in a tree structure:

```
PDK_NAME
└── Device Type (nfet, pfet, etc.)
    └── Length (e.g., 130n)
        └── Corners (tt, ff, ss, etc.)
```

#### Checkbox States
- **Unchecked** - Corner not plotted
- **Checked** - Corner plotted with assigned color
- **Indeterminate** - Some child items checked

#### Color Assignment
- Right-click corner → "Set Color"
- Each corner has unique color
- Colors persist during session

### Control Panel

Located in each ROARLookupWindow:

#### Mode Selection
- **Radio Buttons**: Switch between Device Params and Design Eqs modes

#### Axis Configuration
- **X, Y, Z Combo Boxes**: Select parameters to plot
- **Spinboxes**: Display current cursor values
- **Splitters**: Adjust control widths

#### Plot Options
- **LogX, LogY, LogZ**: Toggle logarithmic scales
- **3-D**: Enable three-dimensional plotting (Design Eqs mode only)
- **Contour**: Show contour plot instead of surface
- **Black BG**: Switch to black background for 3D plots

#### Window Management
- **Copy**: Copy window configuration
- **Attachment Checkboxes**: Lock windows together
- **Color Indicators**: Show attached window status

### Design Editor

#### Equation Panel
- Left side: Expression names
- Right side: Expression definitions
- **+** button: Add new equation
- **×** button: Remove equation
- **Validation**: Real-time syntax checking

#### Instance Table
- **Instance**: Device reference name (M1, M2, etc.)
- **W**: Device width (μm)
- **L**: Device length (μm)
- **kgm**: Normalized gm (read-only, from LUT)
- **Corners**: Assigned corner for this device (click to change)

Columns are resizable by dragging headers.

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **V** | Add vertical marker |
| **H** | Add horizontal marker |
| **D** | Show difference between two selected markers |
| **Delete** | Delete selected markers |
| **Escape** | Unselect all markers |
| **Ctrl+N** | New design |
| **Ctrl+O** | Open design |
| **Ctrl+S** | Save design |
| **F** | Auto-fit plot to data |

---

## Custom Technology Characterization

### CSV File Format Specification

ROAR reads device characterization data from CSV files. Each file represents one process corner for one device type at one channel length.

#### Required Directory Structure

```
${ROAR_CHARACTERIZATION}/
└── your_technology/
    └── LUTs_YOUR_TECH/
        └── device_type/
            └── length/
                └── corners/
                    ├── corner1.csv
                    ├── corner2.csv
                    └── corner3.csv
```

Example:
```
characterization/
└── sky130/
    └── LUTs_SKY130/
        ├── nfet/
        │   ├── 130n/
        │   │   └── corners/
        │   │       ├── nfettt27.csv
        │   │       ├── nfetff75.csv
        │   │       └── nfetss27.csv
        │   └── 500n/
        │       └── corners/
        │           └── ...
        └── pfet/
            └── ...
```

#### Required CSV Columns

##### Mandatory Columns (case-insensitive)

| Column | Units | Description | Range |
|--------|-------|-------------|-------|
| `pdk` | - | PDK name (e.g., "SKY130A") | String |
| `l` or `L` | m | Channel length | > 0 |
| `w` | m | Channel width | > 0 |
| `gm` | S | Transconductance | ≥ 0 |
| `id` or `ids` | A | Drain current | ≥ 0 |
| `gds` | S | Output conductance | ≥ 0 |
| `vgs` | V | Gate-source voltage | Any |
| `vds` | V | Drain-source voltage | ≥ 0 |
| `vth` | V | Threshold voltage | Any |
| `cgg` | F | Gate capacitance | ≥ 0 |
| `cgs` | F | Gate-source capacitance | ≥ 0 |
| `cgd` | F | Gate-drain capacitance | ≥ 0 |
| `cds` | F | Drain-source capacitance | ≥ 0 |
| `cdd` | F | Drain capacitance | ≥ 0 |
| `css` | F | Source capacitance | ≥ 0 |

##### Optional Columns (auto-calculated if missing)

| Column | Formula | Description |
|--------|---------|-------------|
| `gm_id` or `kgm` | gm / id | Normalized transconductance |
| `ft` | gm / (2π × cgg) | Transit frequency |
| `gmro` | gm / gds | Intrinsic gain |
| `kcgg` | cgg / id | Normalized gate cap |
| `kcgs` | cgs / id | Normalized gate-source cap |
| `kcgd` | cgd / id | Normalized gate-drain cap |
| `kcds` | cds / id | Normalized drain-source cap |
| `kcdd` | cdd / id | Normalized drain cap |
| `kgds` | gds / id | Normalized output conductance |

##### Additional Optional Columns

| Column | Description |
|--------|-------------|
| `vdsat` | Saturation voltage |
| `rds` | Output resistance (1/gds) |
| `isweep` | Sweep index |
| `wt` | Unity gain frequency |
| `gmidft` | gm/id × ft product |
| `kgmft` | kgm × ft product |

#### CSV Format Requirements

1. **Header Row**: First row must contain column names
2. **Delimiter**: Comma-separated (`,`)
3. **Whitespace**: Leading/trailing spaces are automatically stripped
4. **Numeric Format**: Standard float notation (e.g., `1.23e-9`)
5. **Missing Values**: Not allowed for required columns
6. **Column Order**: Any order is acceptable
7. **Case**: Column names are case-insensitive (converted to lowercase)

#### Example CSV File

```csv
pdk,l,w,isweep,gm,id,gds,vgs,vds,vth,vdsat,cgg,cgs,cgd,cds,css,cdd,gm_id
SKY130A,1.3e-7,1e-6,0,1.23e-6,1.00e-9,8.45e-9,0.45,0.9,0.42,0.18,3.21e-15,2.10e-15,0.98e-15,0.13e-15,2.23e-15,1.08e-15,1230
SKY130A,1.3e-7,1e-6,1,2.45e-6,2.00e-9,1.67e-8,0.50,0.9,0.42,0.19,6.34e-15,4.15e-15,1.92e-15,0.26e-15,4.41e-15,2.14e-15,1225
SKY130A,1.3e-7,1e-6,2,3.67e-6,3.00e-9,2.48e-8,0.53,0.9,0.42,0.20,9.45e-15,6.18e-15,2.85e-15,0.39e-15,6.57e-15,3.18e-15,1223
...
```

### Creating Characterization Data

#### Method 1: SPICE Simulations

Use your SPICE simulator to sweep gm/id and extract parameters:

1. **Setup**: Create netlist with device under test
2. **Sweep**: Vary Vgs to sweep gm/id from ~3 to ~30
3. **Extract**: Save DC operating point and AC parameters
4. **Export**: Format as CSV with required columns

Example SPICE testbench:
```spice
* Device characterization testbench
.param W=1u L=130n
.param VGS=0.5 VDS=0.9

M1 d g 0 0 nfet w={W} l={L}
Vgs g 0 {VGS}
Vds d 0 {VDS}

.dc VGS 0.3 1.2 0.01
.print dc i(Vds) @M1[gm] @M1[gds] @M1[vth] @M1[vdsat]
.ac dec 10 1 1e12
.print ac @M1[cgg] @M1[cgs] @M1[cgd] @M1[cds]
```

#### Method 2: Measurement Data

If using silicon measurements:

1. **Measure**: DC and AC characteristics
2. **De-embed**: Remove parasitics
3. **Format**: Match CSV column requirements
4. **Validate**: Check for monotonicity and physical validity

#### Data Quality Guidelines

- **Points**: 50-200 points per LUT (balance accuracy vs. file size)
- **gm/id Range**: 3-30 for most technologies
- **Smoothness**: Ensure monotonic relationships where expected
- **Corner Coverage**: Minimum tt, ff, ss; ideal: 5-9 corners
- **Lengths**: Provide min, typical, and max lengths used in designs

### Registering New Technology

1. **Organize Files**: Place LUTs in proper directory structure

2. **Update tech_list.txt**:
   ```
   YOUR_PDK ${ROAR_CHARACTERIZATION}/your_technology/LUTs_YOUR_TECH
   ```

3. **Restart ROAR**: New technology appears in Tech Browser

4. **Verify**: Check that all corners load without errors

### Troubleshooting Characterization Issues

#### "File does not exist"
- Check `tech_list.txt` paths
- Verify `${ROAR_CHARACTERIZATION}` environment variable
- Ensure CSV files have `.csv` extension

#### "Column 'X' not found"
- Verify CSV has all required columns
- Check column name spelling
- Ensure header row is present

#### "Invalid data in column 'X'"
- Check for non-numeric values
- Look for NaN or Inf values
- Verify units are correct (not mA when A expected)

#### Plots look wrong
- Verify data is in SI units (A, V, S, F, m)
- Check gm/id range (typical: 3-30)
- Ensure VDS > VDSAT for saturation region data

---

## Advanced Features

### Equation Solver Architecture

The equation solver processes expressions in this order:

1. **Parse**: Validate syntax and extract symbols
2. **Dependency**: Build dependency graph
3. **Lookup**: Extract base parameter data from LUTs
4. **Evaluate**: Compute expressions in dependency order
5. **3D Mesh** (if enabled): Create parameter grid and evaluate Z

### Performance Optimization

#### 3D Plotting Performance
- **Grid Resolution**: Adjustable (default 40×40 points)
- **Downsampling**: Automatic for large datasets
- **Caching**: LUT data cached after first load
- **Lazy Evaluation**: Equations evaluated only when needed

#### Large Dataset Handling
- Pandas DataFrames for efficient operations
- NumPy vectorization for calculations
- Incremental plot updates
- Memory-efficient storage

### Extending ROAR

#### Adding New Parameters

To add custom derived parameters:

1. Edit `cid.py` → `CIDCorner.import_lut()`
2. Add calculation after existing derived parameters
3. Follow pattern: check if exists, compute array, assign to dataframe

Example:
```python
if not self.check_if_param_exists("my_param"):
    my_param_array = []
    param_a = self.df["param_a"]
    param_b = self.df["param_b"]
    for i in range(len(param_a)):
        result = param_a[i] / param_b[i]
        my_param_array.append(result)
    self.df["my_param"] = my_param_array
```

#### Adding New Functions

To add equation solver functions:

1. Edit `equation_solver.py` → `ROAREquationSolver`
2. Add to allowed functions in `_safe_eval()`
3. Import from `numpy` or `math` modules

Example:
```python
safe_dict = {
    '__builtins__': {},
    'sqrt': np.sqrt,
    'log': np.log,
    'sinh': np.sinh,  # Add new function
    # ... existing functions
}
```

---

## Troubleshooting

### Application Won't Start

**Symptom**: ImportError or ModuleNotFoundError  
**Solution**:
```bash
pip install -r ${ROAR_SRC}/gui/requirements.txt
```

**Symptom**: "ROAR_HOME not set"  
**Solution**: Export environment variables (see Installation)

### Plots Not Appearing

**Check 1**: Is checkbox in Tech Browser checked?  
**Check 2**: Are X and Y axes different?  
**Check 3**: Does data exist in selected range?

### 3D Plot Issues

**Slow Rotation**: Reduce grid resolution in code  
**Flat Surface**: Check if Z varies with X and Y  
**Black Screen**: Verify data contains valid values

### Equation Errors

**"Symbol not found"**: Check device instance exists in table  
**"Syntax error"**: Verify equation uses supported operators  
**"Circular dependency"**: Reorder equations or break cycle

### Memory Issues

**Large LUT Files**: Use smaller point spacing  
**Multiple Corners**: Close unused technologies  
**Many Tabs**: Limit to 4-5 graph tabs

---

## Tips and Best Practices

### Design Workflow

1. **Start Simple**: Begin with single-transistor analysis
2. **Verify LUTs**: Plot basic relationships (ids vs. vgs)
3. **Build Gradually**: Add equations one at a time
4. **Use Markers**: Identify optimal operating points
5. **Compare Corners**: Use locked windows for PVT analysis

### Plotting Efficiency

- **Lock Windows**: Synchronize exploration across corners
- **Use Markers**: More accurate than visual estimation
- **Log Scales**: Better for wide dynamic range
- **Dual Y-axes**: Compare parameters with different units
- **3D for Two Inputs**: Visualize trade-offs clearly

### Design Equation Strategy

- **Name Clearly**: Use descriptive equation names
- **Document**: Add comments in design JSON files
- **Reuse**: Save common equation sets as templates
- **Verify**: Check intermediate values make physical sense
- **Sanity Check**: Compare with hand calculations

---

## File Formats

### Design File (.json)

```json
{
  "expressions": {
    "kgm1": "kgm:M1",
    "ids1": "ids:M1",
    "gain": "gm1 / gds1"
  },
  "constraints": {
    "power_max": "ids1 * 1.8 < 0.001"
  },
  "device_instances": [
    {
      "instance": "M1",
      "W": 1.0,
      "L": 0.13,
      "corners": ["nfettt27", "nfetff75"]
    }
  ],
  "defaults": {
    "VDD": 1.8,
    "temp": 27
  }
}
```

### Technology List (tech_list.txt)

```
# Format: PDK_NAME  DIRECTORY_PATH
# Supports environment variables: ${VAR} or $VAR

SKY130A ${ROAR_CHARACTERIZATION}/sky130/LUTs_SKY130
IHP-SG13G2 ${ROAR_CHARACTERIZATION}/ihp130/LUTs_IHP130

# Custom technology
MY_PDK /home/user/my_tech/LUTs_MY_PDK
```

---

## Support and Resources

### Getting Help

- **GitHub Issues**: Report bugs and request features
- **Documentation**: This README and inline code comments
- **Examples**: See `${ROAR_DESIGN}` directory for sample designs

### Citing ROAR

If you use ROAR in research or publications, please cite:

```
Adair, A. S. (2026). ROAR: Robust Optimal Analog Reuse.
Analog Circuit Design and Optimization Tool.
```

---

## License

[Specify your license here]

---

## Version History

### Version 2.0 (January 2026)
- Added 3D surface plotting with matplotlib
- Improved marker synchronization in locked windows
- Added multi-device 3D plotting support
- Enhanced rotation controls for 3D plots
- Added navigation toolbar for 3D interaction
- Implemented dual Y-axis plotting
- Added trigonometric functions to equation solver
- Fixed text label following in synchronized markers
- Improved UI responsiveness and layout

### Version 1.0
- Initial release
- Basic 2D plotting functionality
- Tech browser with corner selection
- Design equation editor
- Device parameter mode

---

## Contact

**Author**: Alec S. Adair  
**Project**: ROAR - Robust Optimal Analog Reuse  
**Date**: January 2026

---

*This README was generated to provide comprehensive guidance for ROAR users. For additional information, please refer to the User Manual or contact the development team.*

# ROAR Python API

The public package is `roar` (distribution: `roar-cad`). Python **3.10 or
newer** is required. Its implementation is in [roar/design.py](../roar/design.py),
[roar/evaluation.py](../roar/evaluation.py), and
[roar/session.py](../roar/session.py).

## Installation, imports, and assets

From a checkout, install the headless API with `pip install -e .`. For desktop
Qt plots, use `pip install -e '.[gui]'`. These editable installations do not
require the csh launchers; the existing desktop installation instructions are
in [INSTALLATION_AND_USAGE.md](INSTALLATION_AND_USAGE.md).

```python
from pathlib import Path
import roar

HOME = Path("/path/to/roar")  # Checkout/assets root, not the Python executable.
design = roar.Design("Common source")
```

`import roar`, detached design editing/serialization, and constructing a hidden
`Session` do **not** load Qt, NumPy, pandas, SymPy, or Matplotlib. Importing the
package does not start an application, change `sys.path`, or replace SIGINT's
handler. Numerical imports happen on evaluation; Qt imports happen on live
operations. LUT discovery itself does not load CSVs or the legacy backend.

Pass `home=HOME` to `Technologies`, evaluation, headless graph exports, `Session`,
or `launch` to select the asset root explicitly. Resolution is: explicit `home`,
then `ROAR_HOME`, then a checkout containing [tech_list.txt](../tech_list.txt).
A wheel contains the Python backend but **does not ship LUTs or the full asset
tree**. Supply an external checkout/asset root and its technology mappings.
An explicit home overrides an inherited `ROAR_HOME`.

Evaluation/live operations initialize legacy paths and environment variables
on demand, so their process-neutrality is not the same as a plain import. The
backend preserves SIGINT's handler and removes an inherited inline Matplotlib
backend setting when necessary; do not rely on evaluation leaving `sys.path`
or environment variables unchanged.

## Build and edit a detached design

```python
SKY = "PDK>SKY130A>n_01v8>150>nfettt27"

design.add_instance("M1", corners=None, kgm=12, ID=20e-6, L=150e-9)
design.add_expression("gm_id", "kgm:M1", plot=True)
design.add_expression("load", 5e-12)
design.add_expression("frequency", "200e6")
design.add_expression("current", "2*pi*frequency*load/gm_id")
design.add_constraint("positive", "current > 0")
design.add_expression("alternative", "1", enabled=False)

graph = design.graph().configure(
    mode="design", x="gm_id", y="current", corners=[SKY], log_y=True,
    legend=True,
)
```

Mutators return their owning `Design` or `Graph` for chaining unless noted
otherwise. A new `Design(name="Design")` has one named tab with **four** windows
(indices 0–3), empty editor rows, light theme, and iterative solving disabled.
Each window starts in device mode with `kgm`, `kcgs`, `iden` axes and only its
own window index in `locked_windows`.

### Row CRUD and flags

| Method | Purpose |
| --- | --- |
| `add_expression(symbol, expression, *, enabled=True, plot=False)` | Add a constant, LUT lookup, or equation; numbers become text. |
| `set_expression(symbol, expression)` | Replace an existing expression. |
| `add_constraint(symbol, expression, *, enabled=True, plot=False)` | Add a named boolean constraint. |
| `set_constraint(symbol, expression)` | Replace an existing constraint. |
| `add_instance(name, *, corners=None, enabled=True, **parameters)` | Add an instance with default empty `kgm`, `ID`, `W`, `L` columns. |
| `set_row_enabled(kind, name, enabled=True)` | Store the inverse `disabled` flag. |
| `set_row_plot(kind, name, plot=True)` | Store the editor's `plot` flag. |
| `move_row(kind, name, index)` | Reorder within one table (zero-based destination). |
| `remove_row(kind, name)` | Delete a named row. |

`kind` is exactly `"expression"`, `"constraint"`, or `"instance"`.
`add_*` rejects duplicate names **within that table**. Missing named rows raise
`KeyError`; invalid indices raise `IndexError`. Expression/constraint symbols
and newly added instance names must be Python identifiers; equation symbols
cannot start with the reserved `__roar_` prefix. Empty expressions are rejected.

`design.expressions` and `design.constraints` return dictionaries of enabled
rows only. `design.instances` includes **all** instance rows, including their
flags and attribute metadata. Disabled rows are retained by every design
serialization format. The headless evaluator excludes disabled expressions
and constraints, but currently `get_device_corners()` still includes disabled
instances; do not use the instance flag as a promise to skip its corner
validation. `plot` preserves editor UI intent; it does not automatically choose
a graph's axes or restrict `Design.evaluate()` outputs.

```python
design.set_expression("load", "4e-12")
design.set_constraint("positive", "current > 1e-6")
design.set_row_enabled("expression", "alternative", False)
design.set_row_plot("expression", "current", True)
design.move_row("expression", "current", 0)
design.remove_row("expression", "alternative")
```

### Global and custom device corners

`corners=None` means the GUI's `[*Global*]` selection. For headless evaluation,
global corners come from an explicit `corners=` argument or the union of saved
graph selections. Custom corners are full Technology Browser leaf paths:

```python
design.set_instance_corners("M1", [SKY])
info = design.get_device_corners()["M1"]
# info: corners=['nfettt27'], corner_paths=[SKY],
#       pdk='SKY130A', model='n_01v8', length='150'
design.set_instance_corners("M1", None)  # Restore global selection.
```

`add_instance` and `set_instance_corners` accept one path, a sequence of paths,
or entries containing a `path` key. The old four-part form without `PDK>` is
canonicalized. Bare corner names are insufficient. Duplicate paths and empty
custom selections are rejected; use `None`, not `[]`, for global selection.
Display names may repeat across PDKs/models/lengths; full paths retain identity.

Custom device lists are paired **by index**, not pooled or expanded as a
Cartesian product. All participating custom/global lists must have equal
counts and each tuple's LUTs must have equal sample counts. Device-qualified
lookups use their instance's path. An unqualified lookup such as `kgm` still
requires a global selection, even if every instance has custom corners.

### Instance attributes and provenance

```python
design.set_instance_attribute(
    "M1", "W", 2e-6, source_label="selected width", reduce="max",
    per_corner={SKY: 2e-6}, as_column=True,
)
design.set_instance_attribute("M1", "annotation", 7, as_column=False)
parameters = design.get_instance_parameters()
design.clear_instance_attribute("M1", "annotation")
```

`set_instance_attribute(instance, attr, value, *, source_label="API",
reduce="literal", per_corner=None, as_column=True)` stores a native pinned
`_attributes` entry with `resolved`, `source_label`, `reduce`, `per_corner`, and
`as_column`. It records the supplied resolved value; detached calls do **not**
compute the reduction or sample a marker. Values/metadata must be JSON
serializable and finite. Structural row keys and underscore-prefixed names
are reserved. Custom attributes may be metadata-only; standard `kgm`, `ID`,
`W`, `L` columns are updated even with `as_column=False`.

`get_instance_parameters()` returns per-instance dictionaries containing
`value` and `source`, with reduction/per-corner metadata for resolved
attributes. Metadata takes precedence over the table's text value. Empty
values and private/structural columns are omitted. Clearing an attribute removes
its metadata and empties an existing column; it does not delete the column.
These assigned values are stored/exported inputs, **not automatic definitions
in the equation solver**: `column:instance` reads a LUT column, not an assigned
instance-table attribute.

### Tabs, window settings, and independent snapshots

```python
design.add_tab("Device curves").rename_tab("Device curves", "Devices")
design.select_tab("Devices")
second_graph = design.graph("Devices", 1)
design.set_window(width=1200, height=800, x=100, y=100,
                  maximized=False, theme="dark", console_visible=True)

snapshot = design.to_state()
independent = roar.Design.from_state(snapshot)
```

`add_tab`, `rename_tab`, `remove_tab`, and `select_tab` operate by name or
zero-based tab index (except `add_tab`, which takes a new name).
Names must be unique/nonempty and cannot be `"+"`. Removing the final tab is
prohibited. Selection follows the retained tab when earlier tabs are removed.
`graph(tab=0, index=0)` returns a mutable view into the owning design, not a
detached snapshot. Changing that graph changes the design.

`to_state()`, `tabs`, `instances`, `iterative_settings`, `Graph.to_state()`,
and the parameter/corner getters return independent copies. Mutate the design
through named methods, or edit a state snapshot and load it with `from_state`.
`expressions` and `constraints` are also fresh dictionaries.

`set_window` defaults to 1200×800 at (100, 100), not maximized, light theme,
console hidden. Width/height must be positive; theme is `light` or `dark`.
Live `Session.apply()` restores geometry without showing/maximizing the window.

## Save, load, and export inputs

| API | Content |
| --- | --- |
| `Design.load(path)` | Load native application JSON or editor-only design JSON. |
| `Design.from_state(state)` | Copy/validate a native state or editor-only dictionary. |
| `design.save(path)` | Full application state: editor, attributes, tabs, graph flags, window settings; adds a `saved_at` timestamp to the file only. |
| `design.export_design(path)` | Editor-only JSON: rows, flags, metadata, iterative settings; no graph tabs/window settings. |
| `design.export_python(path)` | Runnable public-API reconstruction of all inputs and graphs. |
| `design.export_spice(path)` | Instance attributes/table values as SPICE `.param` statements, **not a circuit netlist**. |

File writers return `Path` and create parent directories. Input serialization
does not need LUTs or Qt. Unknown state keys are preserved for compatibility;
missing graph windows receive defaults. Loading checks JSON compatibility,
row/tab name uniqueness, graph indices and selected tab. It is **not** equation
syntax checking or numerical verification; use evaluation for that.

SPICE names are lowercased `instance_attribute` names with punctuation replaced
by underscores and a `p_` prefix when needed for a leading digit. Collisions
after sanitization raise `ValueError`, as do multiline values. Provenance and
per-corner reductions are comments. No populated parameters produces a
header-only file. Stored parameters are exported even for disabled instances.

### Reconstruction scripts versus solver scripts

An API `export_python()` script defines `build_design()` returning a fresh
`roar.Design`. Importing it or using `runpy.run_path` does not save a file or
open a GUI. Executing it accepts:

- `--output PATH`: saved full-state file; default is the script's sibling with
  the `.roar` suffix.
- `--show`: save first, then open a standalone live `Session`.

Each `build_design()` call is independent. No checkout-specific internal import
is embedded, but the package must be installed/importable and GUI display still
needs assets/dependencies. Currently these generated scripts do **not** have an
`--exports` option.

`Session.export_solver_python(path)` is different: it invokes the existing
GUI's **computational solver-script** generator on the live editor's
expressions, constraints and device data. It requires a live session/backend;
it is not the public-API reconstruction format and should not be assumed to
define `build_design()` or support the same CLI arguments. `Session.export_python`
captures the live design and produces the reconstruction format instead.

## Technologies, units, and headless evaluation

```python
technologies = roar.Technologies(home=HOME)
paths = technologies.corners(pdk="SKY130A", model="n_01v8", length="150")
lut = technologies.load(SKY)  # Independent normalized pandas DataFrame.

results = design.evaluate(["gm_id", "current"], corners=[SKY], home=HOME)
result = results[0]
unfiltered = result.to_dataframe()
passing = unfiltered.loc[result.constraint_mask]
```

`Technologies(home=None, paths=None)` reads the technology mappings by default.
`paths={"MyPDK": "/absolute/LUT/root"}` replaces that catalogue for discovery
and `load`; relative roots are resolved against home. Environment variables,
`~`, and `${ROAR_HOME}` are expanded. `Design.evaluate` does not accept a
`Technologies` object or its `paths` mapping; register evaluation LUTs through
the selected asset root. `corners(pdk=None, model=None, length=None)` returns
sorted full leaf paths. Missing mappings/files or malformed paths raise
explicit exceptions rather than generating zeros. `load(path)` caches
normalized data and returns a fresh frame; frame attributes identify the full
corner, registered PDK, model, length token, and CSV source.

### Unit policy

There is no general dimensional-analysis or automatic unit-conversion layer.
`Technologies.load` uses the existing `CIDCorner` normalization, not a new
all-SI schema. Column names become lowercase; aliases/derived quantities such
as `ids`, `kgm`, `ft`, `kcgs`, `kcgd`, `kgds`, and `iden` follow that backend.

- Current is in amperes, capacitance in farads, conductance in siemens, and
  `ft` in hertz. `kgm` is gm/ID in inverse volts; `kcgs` uses `abs(cgs)/ids`.
- Raw `w`/`l` columns retain the CSV units. The checked-in SKY130 CSVs store
  them in **micrometres**. When the CSV's `pdk` is `sky130`, the backend converts
  width to metres for `iden`, so this derived current density is **A/m**, not
  A/µm. The registered name `SKY130A` and CSV `pdk` identity are distinct.
- Length directory tokens (`150`, `500`, IHP's historical `130u`, etc.) are
  labels, **not quantities to convert**. Use the CSV data and its documented
  units for numerical lengths.
- Saved attributes and equation constants have the units supplied by the
  caller. For example, `L=150e-9` is a caller-supplied metre-valued parameter;
  it does not rewrite a LUT's `l` column.
- Marker positions, live axis ranges, evaluation values and CSV samples are
  linear physical values. Log display never means passing `log10(value)`.

See [LUT_SPECIFICATION.md](LUT_SPECIFICATION.md) for the asset layout and CSV
conventions; inspect a custom LUT's units rather than assuming all dimensions
are SI.

### Equations, masks, and strict validation

`design.evaluate(symbols=None, *, corners=None, home=None,
apply_constraints=True)` returns a list of `EvaluationResult`, one per corner
tuple. `symbols` may be a name or sequence; omitted means all enabled
expression names. All enabled expressions are validated/solved, including
those not requested. Undefined symbols, missing instances/columns/corners,
shape mismatches and failed/nonconvergent solves raise; they are not concealed
as valid zero data.

Use normal SymPy-style arithmetic (`**` for powers). A device lookup must be
a standalone expression such as `"kgm:M1"`; introduce it as a named expression
before combining it with arithmetic. Unqualified normalized LUT columns may
appear in arithmetic. Scientific notation and `pi` are supported. The legacy
trigonometric names `sin`, `cos`, `tan` and their inverse forms use **degrees**.
Constraints must evaluate to booleans; combine vector conditions using
parenthesized `&`/`|`, and use `Eq(a, b)` for numerical equality rather than
Python's structural `==`.

**Trust boundary:** equations are trusted SymPy/Python input, just like the
editor. Parsing/evaluation and loading/executing exported Python scripts are
**not a sandbox**. Do not evaluate untrusted designs.

`EvaluationResult` exposes:

- `corner`: full global path, or a custom tuple label containing instance
  names and full paths; `None` for a constant-only solve without corners.
- `values`: requested unfiltered numeric arrays. Scalars are length-one
  arrays, not eagerly repeated sample vectors.
- `constraint_mask`: boolean AND of enabled constraints, retaining all sample
  positions. `apply_constraints=False` avoids parsing/applying constraints.
- `device_corners`: exact instance-to-full-path mapping for that tuple.
- `convergence`: iteration information or `None` for a noniterative solve.
- `to_dataframe()`: broadcast scalars to mask length, retain all rows, and
  attach corner/device/convergence metadata. Apply the mask explicitly if
  using this table directly.

Evaluation does not mutate the design. Nonfinite ordinary numerical samples
can remain in results; graph extraction filters them rather than claiming
every raw result is finite.

### Iterative solving

```python
cycle = roar.Design("Fixed point")
cycle.add_expression("a", ".5*b + 1").add_expression("b", ".5*a + 1")
cycle.set_iterative_solver(
    enabled=True, max_iterations=100, tolerance=1e-8, damping=.75,
    initial_guesses={"a": 1.0, "b": 1.0},
)
solved = cycle.evaluate(home=HOME)[0]
assert solved.convergence["converged"]
```

`set_iterative_solver` defaults to `enabled=False`, `max_iterations=50`,
`tolerance=1e-6`, `damping=1.0`, and empty `initial_guesses`. Iterations must be
a positive integer, tolerance finite/positive, damping finite in `(0, 1]`,
and guesses JSON-compatible/finite. Multi-symbol cycles require iterative
solving. Legacy self-referential cycles are explicitly rejected. Failure to
converge or nonfinite cycle values raises `RuntimeError`. Setting options does
not itself run or verify a design.

## Detached graphs: headless samples and exports

`Graph.configure` takes **friendly names**:

```python
graph.configure(x="gm_id", y="current", z="load", mode="design",
                log_x=False, log_y=True, log_z=False,
                three_d=False, contour=False, legend=True,
                black_background=False, spin_x=12, spin_y=0, spin_z=0,
                locked_windows=[0])
graph.select_corners([SKY], colors={SKY: "#336699"})
graph.set_color(SKY, "#336699")
graph.add_marker(12, vertical=True)
graph.add_marker(20e-6, vertical=False)
graph.remove_marker(1)

samples = graph.evaluate(home=HOME)
graph.export_csv("exports/kgm_current.csv", home=HOME)
graph.export_plot("exports/kgm_current.png", home=HOME)
graph.export_plot("exports/kgm_current.svg", home=HOME)
```

All `configure` arguments default to `None` (leave unchanged). `mode` is
`device` or `design`. `corners` selects graph-global leaf paths; `select_corners([])`
clears that selection. Device mode reads normalized LUT columns directly and
does not apply design constraints. Design mode evaluates the selected enabled
expression names and applies constraints.

`configure_state(**values)` accepts native saved keys, for example
`combo_x_text`, `is_device_params_mode`, `checked_paths`, `checkbox_logx`,
`checkbox_3d`, `checkbox_contour`, `checkbox_legend`, `checkbox_black_bg`,
`spin_x_value`, `locked_windows`, `color_map`, and `markers`. Inspect
`to_state()` for all keys. Unknown keys and changing a window's index are
rejected. Detached axis selection is stored immediately; LUT existence and
axis availability are checked when evaluating or applying to a live graph.

`evaluate(home=None)` returns one pandas frame per corner tuple with `x`, `y`
and, in 3-D mode, `z` columns. Samples are filtered for enabled design
constraints, finite active axes and positive values on logarithmic axes,
without log-transforming the output. Markers/spin boxes do not resample,
interpolate, or change the evaluated samples. `clear_markers()` removes all
saved markers. Nonfinite positions and nonpositive positions on log axes are
rejected.

`export_csv(path, *, home=None)` writes `corner,x,y[,z]` with one row per
filtered sample; an empty graph still writes column headers.
`export_plot(path, *, home=None)` supports PNG, SVG, and PDF with a Matplotlib
Agg canvas, without a display or Qt application. It draws 2-D lines and saved
markers, or **3-D sample scatter**, not the legacy GUI mesh. Log scales,
axis labels, per-path colors and legends are supported. `contour`,
`black_background`, locks and spin controls are preserved GUI state, not a
promise of equivalent headless rendering. In particular, a saved 3-D contour
flag does **not** create a headless contour surface.

## Live GUI sessions

### Standalone script

```python
# Assume design has been built or loaded above.
session = roar.Session(design, home=HOME)
session.run()  # Creates/shows the GUI and runs its owned Qt event loop.
```

`Session(design=None, *, home=None, show=False, app=None)` is lazy while
hidden, unless attaching with `app=`. Accessing `session.app`, applying a
design, obtaining a live graph, or showing it initializes/reuses Qt on the
**main thread**. `run()` is for a session that created the `QApplication`; it
raises if an embedded host owns/runs the event loop. Do not nest Qt event loops.

### Notebooks and existing ROAR applications

Enable IPython's `%gui qt` in a notebook cell **before** showing the window:

```python
session = roar.launch(design, home=HOME)  # Keep this reference alive.
# Notebook/embedded host owns the event loop; do not call session.run().
```

`launch(design=None, *, home=None, run=False)` also accepts a saved-state path;
it shows a session and returns it. `run=True` is for an appropriate standalone
host, not a notebook. For an already running ROAR window:

```python
# existing_roar_app must be the real ROARApp, not just QApplication.
attached = roar.Session.from_app(existing_roar_app)
snapshot = attached.capture()
```

`from_app` attaches without constructing/restoring another design. The existing
ROAR app and its `QApplication` must belong to the current thread. Passing both
`app=` and a `design` to the constructor explicitly applies that design.

### Session operations

| Method/property | Effect |
| --- | --- |
| `app` | Access the live ROARApp; initializes a lazy session. |
| `apply(design)` | Restore rows, attributes, iterative settings, graph tabs/flags without file/progress dialogs or showing/maximizing. |
| `capture()` | Return an independent detached `Design` from the current widgets. |
| `graph(tab=0, index=0)` | Return `LiveGraph` for a real tab and window 0–3 (not the GUI's `+` tab). |
| `refresh(tab=None)` | Publish current editor symbols and refresh all windows, or one tab. |
| `show()` / `run()` | Show under a host loop / run an owned standalone loop. |
| `save`, `export_design`, `export_python`, `export_spice` | Capture the live state and delegate to the detached writers. |
| `export_solver_python(path)` | Write the legacy computational solver script, not a reconstruction. |
| `close()` | Close the window and invalidate the session; an attached window is also closed. |

`Session` is a context manager; exiting calls `close()`. Keep sessions alive
while using their widgets. Live operations must occur on the GUI thread.
Live export methods do not all create parent directories (in particular live
plot/solver-script exports); create an export directory before using them.

### LiveGraph configuration, markers, and exports

Unlike detached `Graph.configure`, **`LiveGraph.configure` accepts native saved
state keys**, not `x=`, `mode=`, or other friendly aliases:

```python
live = session.graph(0, 0)
live.apply(design.graph(0, 0))  # Apply friendly-configured detached graph.
live.configure(checkbox_logy=True, checkbox_legend=True, locked_windows=[0])
live.refresh()
marker_index = live.add_marker(12, vertical=True)
readouts = live.marker_values(marker_index)
assignment = live.assign("M1", "selected_current", marker=marker_index,
                         reduce="max", as_column=True)
live.set_range(x=(5, 20), y=(1e-6, 1e-3)).autofit()
```

- `widget` exposes the underlying legacy lookup window; `to_state()` returns a
  deep-copy configuration. `apply(graph)` maps a detached graph to this window.
  `configure(**kwargs)` validates known keys, axes and exact corner leaf paths.
- `add_marker(pos, vertical=True)` returns the new marker's index.
  `clear_markers()` removes all. `marker_values(index=0)` returns independent
  dictionaries with `curve_idx`, `corner_path`, `corner_name`, `x`, `y`.
  Values are linear **nearest-sample readouts**, not interpolation.
- `assign(instance, attr, value=None, marker=0, reduce="mean",
  source_label=None, as_column=True)` returns the saved pinned attribute spec.
  With no literal value, vertical markers supply Y and horizontal markers
  supply X. Reductions are `mean`, `min`, `max`, or `corner:<name/path>`; that
  selector must identify exactly one curve. Per-corner keys retain full paths.
  A supplied finite literal uses `reduce="literal"` instead.
- `set_range(x=None, y=None, z=None)` uses finite increasing **linear** bounds
  and converts positive log bounds internally. Legacy GL 3-D ranges are not
  supported. `autofit()`, `reset()`, `expand()`, and `contract()` expose those
  live window operations.
- `export_csv(path)` writes original 2-D linear curve samples before log
  transformation/downsampling, with columns
  `curve_idx,curve_name,corner_path,x,y`. This differs from detached graph CSV.
- `export_png(path)` captures the live plot. A 3-D capture needs a shown,
  rendered OpenGL widget on a real display, not offscreen/minimal Qt.
  `export_svg(path)` is 2-D only. Marker readouts/assignment and CSV export
  are also 2-D operations.

The GUI's 3-D/contour visualization uses the legacy mesh/surface implementation;
headless sample extraction and scatter exports are not a reproduction of that
mesh. Do not promise a live 3-D PNG in CI without a working display/OpenGL setup.

## Common-source 200 MHz builder

[design/create_common_source_200MHz.py](../design/create_common_source_200MHz.py)
uses `import roar` and explicit API calls. `build_design()` constructs 33
expressions, two constraints, the global-corner M1 instance, four tabs and
sixteen plots with their axes, active trace colors, locks and markers.
It does not read or copy the original saved design.

- `--output PATH`: default sibling common-source application-state file.
- `--show`: optionally open the constructed design in the GUI.
- `--exports DIRECTORY`: also write common-source editor JSON, a reconstruction
  Python script, SPICE parameters, and `kgm_current` CSV/PNG/SVG exports. It
  evaluates the checked-in LUT and prints the constraint-passing sample count.

The original equations are intentionally preserved. The 200 MHz value is
`fu`, the unity-gain target; the loaded bandwidth is approximately 40 MHz.
`kcs1` retains its bare `kcgs` reference and `cgg1` retains the original
division by current (which does not give physical capacitance with F/A LUT
units). The example is reconstruction, not circuit certification. Portable
window geometry replaces the original off-screen position; unused color-cache
entries for unchecked corners are omitted. M1 dimensions remain unassigned,
so its initial SPICE export contains only a header.

The existing saved example is
[common_source_200MHz.roar](../design/common_source_200MHz.roar).

## Tests

[test_roar_api.py](../tests/test_roar_api.py) uses `unittest`, the real detached
model, fresh subprocesses, and checked-in SKY130 data for serialization, CRUD,
flags, metadata, SPICE collision handling, reconstruction scripts, import
isolation, evaluation masks/units, and headless CSV/PNG/SVG export. It requires
the headless dependencies and checkout LUT assets, not pytest or Qt.
The separate [evaluation tests](../tests/test_roar_evaluation.py) cover strict
solver behavior; [GUI API tests](../tests/test_roar_gui_api.py) cover real
offscreen Qt widgets and live exports with the GUI extra installed.

## Additional live graph controls

These methods belong to `LiveGraph`, require the GUI thread, and do not add
saved-state keys or friendly aliases to `configure`.

| Method | Behavior |
| --- | --- |
| `copy_to(other, *, copy_attachments=False)` | Apply this graph's saved configuration through the destination's `configure`, retaining its index and, by default, its exact locks. Pass `copy_attachments=True` to copy source lock indices verbatim. Returns the destination. Copies selected corners, colors and 2-D line markers without attachment-driven duplication; does not change either graph's browser role or instance-specific corners. |
| `set_browser_mode("global" / "local" / "follower")` | Use the GUI's role setters. A global master replaces any other master in the same grid; local browsers ignore global updates; followers receive them. Setting a role alone does not synthesize a corner-change event. Roles are live-only, not added to capture/save state. |
| `select_corners(paths, colors=None)` | Replace the exact checked leaf selection; a single full GUI path is accepted, and `[]` clears it. Optional colors are a path-to-valid-CSS/Qt-color-string mapping. Unspecified cached colors are retained. Duplicate, missing and non-leaf paths are rejected before mutation. |
| `set_color(path, color)` | Update a known leaf's color without selecting it or discarding other cached colors. |
| `lock(indices)` | Replace exact, unique integer attachment indices in 0–3, without copying markers to attached windows. `[]` removes all locks. |

Corner/color wrappers on a global master publish through the existing GUI
follower synchronization. Local windows and explicit instance corner records
remain independent, including the GUI's all-custom Design Eqs exception.
Full GUI corner paths are required; shortened path aliases are not accepted.
All mutators above except `copy_to` return the source `LiveGraph` for chaining.

### Live 3-D sample picking and camera

- `add_point_marker(x, y, z, corner=None)` returns a point-marker index. Supply
  finite **linear physical** coordinates (positive on active log axes). It
  selects the nearest finite sample already registered by the GUI render pass,
  using Euclidean distance in linear XYZ space without unit rescaling or
  interpolation. `corner` matches a rendered **surface label**, not a full
  technology path. A repeated pick of the same sample/label reuses its index.
- `point_marker_values(index=0)` returns an independent dictionary with
  `x`, `y`, `z`, and `label`. It uses the GL widget's `_display_orig` conversion
  so Log Z readouts are physical linear values, not stored log values or
  normalized drawing coordinates. Indices refer to the GL point-marker list,
  separately from 2-D line-marker indices.
- `set_camera(distance=None, elevation=None, azimuth=None, center=None)` changes
  only supplied GL camera options and returns the graph. Distance must be
  positive; all supplied numbers must be finite. Elevation/azimuth are degrees;
  center is a three-coordinate sequence in the GUI's **normalized GL space**,
  not physical axis units. This is not a replacement for physical 3-D ranges.

These 3-D methods reject 2-D mode, missing GL widgets, and offscreen/minimal Qt.
Point picking also reports absent/empty rendered samples clearly: show the
3-D graph and let the GUI render it before picking. Camera settings and 3-D
point markers are live-only, not serialized or copied by `copy_to`; there is
no headless equivalent promised here. `clear_markers()` clears GL markers too.

The offscreen tests exercise numeric selection, Log Z conversion and camera
options on a **real GL widget with injected sample arrays**. Display-platform
guards and marker drawing are patched for those tests. Actual mesh rendering,
marker visuals and real-display OpenGL capture are **not verified** by them.
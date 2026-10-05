"""Headless LUT discovery, strict equation evaluation, and graph samples.

Designs are consumed through their public data API, not imported here. Expressions
are trusted SymPy/Python input, just as in the editor; this is not a sandbox.
Numerical and legacy backend imports are deferred until they are needed.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from io import StringIO
import os
from pathlib import Path
import re
import shlex
from types import SimpleNamespace
import tokenize
from typing import Any

from ._backend import load_backend, resolve_home

__all__ = ["Technologies", "EvaluationResult", "evaluate_design", "graph_data"]


def _path(path: str) -> str:
    """Canonical GUI leaf path; accept the old form without the PDK prefix."""
    if not isinstance(path, str):
        raise TypeError("Corner paths must be strings")
    parts = [part.strip() for part in path.split(">")]
    if len(parts) == 4:
        parts.insert(0, "PDK")
    if (len(parts) != 5 or parts[0] != "PDK" or
            any(not part or part in (".", "..") or "/" in part or "\\" in part
                for part in parts[1:])):
        raise ValueError(f"Expected a full PDK>technology>model>length>corner path: {path!r}")
    return ">".join(parts)


class Technologies:
    """Lazy catalogue of LUT roots keyed by their registered PDK identity.

    ``paths`` optionally replaces the technology-list mapping with a mapping of
    PDK names to LUT roots. Relative roots are relative to ``home``. CSV loading
    uses CIDCorner's normalization and is cached; callers receive independent
    frames so evaluation cannot corrupt the cache. Lengths are directory tokens,
    not converted units (notably IHP's historical ``130u`` names).
    """

    def __init__(self, home=None, paths: Mapping | None = None):
        self.home = resolve_home(home)
        if paths is None:
            paths = {}
            source = self.home / "tech_list.txt"
            with source.open(encoding="utf-8") as stream:
                for lineno, line in enumerate(stream, 1):
                    parts = shlex.split(line, comments=True)
                    if not parts:
                        continue
                    if len(parts) < 2:
                        raise ValueError(f"Invalid technology mapping at {source}:{lineno}")
                    paths[parts[0]] = " ".join(parts[1:])
        if not isinstance(paths, Mapping):
            raise TypeError("paths must map PDK names to LUT roots")
        self.paths = {}
        for pdk, root in paths.items():
            if not isinstance(pdk, str) or not pdk or any(c in pdk for c in ">/\\"):
                raise ValueError(f"Invalid PDK name: {pdk!r}")
            text = re.sub(r"\$\{ROAR_HOME\}|\$ROAR_HOME\b", lambda _: str(self.home), os.fspath(root))
            root_path = Path(os.path.expanduser(os.path.expandvars(text)))
            self.paths[pdk] = (root_path if root_path.is_absolute() else self.home / root_path).resolve()
        self._cache: dict[str, Any] = {}

    def _discover(self, pdk=None, model=None, length=None):
        if pdk is not None and pdk not in self.paths:
            raise ValueError(f"Unknown PDK: {pdk!r}")
        files = {}
        for name, root in self.paths.items():
            if pdk is not None and name != pdk:
                continue
            if not root.is_dir():
                raise FileNotFoundError(f"LUT root for {name} does not exist: {root}")
            for device in sorted(root.iterdir()):
                if not device.is_dir() or (model is not None and device.name != str(model)):
                    continue
                for directory in sorted(device.glob("LUT_*_*")):
                    token = directory.name.rsplit("_", 1)[-1]
                    if not directory.is_dir() or (length is not None and token != str(length)):
                        continue
                    for csv in sorted(directory.glob("*.csv")):
                        key = _path(f"PDK>{name}>{device.name}>{token}>{csv.stem}")
                        if key in files:
                            raise ValueError(f"Ambiguous LUT corner: {key}")
                        files[key] = csv
        return files

    def corners(self, pdk=None, model=None, length=None) -> list[str]:
        """Return sorted full leaf paths, without importing a backend or CSV."""
        return sorted(self._discover(pdk, model, length))

    def load(self, path: str):
        """Return a normalized pandas DataFrame; absent files never become zeros."""
        key = _path(path)
        _, pdk, model, length, corner = key.split(">")
        files = self._discover(pdk, model, length)
        if key not in files:
            raise FileNotFoundError(f"LUT file for corner {key} does not exist under {self.paths[pdk]}")
        if key not in self._cache:
            backend = load_backend("cid", self.home)
            try:
                frame = backend.CIDCorner(corner_name=corner, lut_csv=str(files[key]), pdk=pdk).df
            except KeyError as exc:
                raise ValueError(f"Missing LUT column {exc.args[0]!r} while normalizing {key}") from exc
            if frame is None:
                raise RuntimeError(f"CIDCorner failed to load {files[key]}")
            frame.attrs.update(corner=key, pdk=pdk, model=model, length=length, csv=str(files[key]))
            self._cache[key] = frame
        return self._cache[key].copy(deep=True)


def _vector(value, name):
    import numpy as np
    array = np.asarray(value)
    if array.ndim == 2 and array.shape[1] == 1:
        array = array[:, 0]
    if array.ndim > 1 or array.dtype.kind not in "biufc":
        raise ValueError(f"Evaluation of {name!r} did not produce a numeric sample vector")
    return np.atleast_1d(array).copy()


def _broadcast(value, size, name):
    import numpy as np
    array = _vector(value, name)
    try:
        return np.broadcast_to(array, (size,)).copy()
    except ValueError as exc:
        raise ValueError(f"Sample shape mismatch for {name!r}: {array.shape}, expected ({size},)") from exc


@dataclass
class EvaluationResult:
    """Unfiltered values and an AND-combined mask for one corner tuple.

    Scalar values are length-one arrays; ``to_dataframe`` broadcasts them to the
    mask length. No samples are discarded until graph extraction. A custom tuple
    label includes instance names and full paths; ``device_corners`` retains its
    exact mapping. A constant-only evaluation without corners has label ``None``.
    """

    corner: str | None
    values: dict[str, Any]
    constraint_mask: Any
    convergence: dict | None = None
    device_corners: dict[str, str] = field(default_factory=dict)

    def to_dataframe(self):
        import numpy as np
        import pandas as pd
        mask = _vector(self.constraint_mask, "constraint_mask")
        if mask.dtype != np.dtype(bool):
            raise ValueError("constraint_mask must be boolean")
        frame = pd.DataFrame({name: _broadcast(value, len(mask), name)
                              for name, value in self.values.items()}, index=range(len(mask)))
        frame.attrs.update(corner=self.corner, convergence=self.convergence,
                           device_corners=dict(self.device_corners))
        return frame


def _global_paths(design):
    state = design.to_state()
    paths = []
    for tab in state.get("graph_tabs", {}).get("tabs", []):
        for window in tab.get("windows", []):
            for path in window.get("checked_paths", []):
                canonical = _path(path)
                if canonical not in paths:
                    paths.append(canonical)
    return paths


def _paths(paths):
    if isinstance(paths, str):
        paths = [paths]
    return [_path(path) for path in paths]


def _corner_tuples(design, corners, device_info):
    global_paths = _global_paths(design) if corners is None else _paths(corners)
    custom = {}
    for name, info in device_info.items():
        if info.get("corners") is None:
            continue
        paths = info.get("corner_paths")
        if not paths:
            names = info["corners"]
            if all(isinstance(corner, str) and ">" in corner for corner in names):
                paths = names
            elif all(info.get(key) is not None for key in ("pdk", "model", "length")):
                paths = [f"PDK>{info['pdk']}>{info['model']}>{info['length']}>{corner}" for corner in names]
            else:
                raise ValueError(f"Instance {name!r} needs full corner paths with PDK/model/length")
        custom[name] = _paths(paths)
        if not custom[name]:
            raise ValueError(f"Instance {name!r} has an empty custom corner selection")
        if len(custom[name]) != len(info["corners"]):
            raise ValueError(f"Corner names/paths count mismatch for instance {name!r}")
    counts = {len(paths) for paths in custom.values()}
    if global_paths:
        counts.add(len(global_paths))
    if len(counts) > 1:
        raise ValueError("Corner count mismatch: global and custom selections must be index-matched")
    count = next(iter(counts), 1)
    for index in range(count):
        global_path = global_paths[index] if global_paths else None
        mapping = {name: paths[index] for name, paths in custom.items()}
        for name in device_info:
            if name not in custom and global_path is not None:
                mapping[name] = global_path
        if custom:
            labels = ([f"global={global_path}"] if global_path is not None else [])
            labels.extend(f"{name}={path}" for name, path in mapping.items())
            label = " | ".join(labels)
        else:
            label = global_path
        yield label, global_path, mapping


def _parse(expressions, backend):
    import sympy as sp

    def degree(function):
        # SymPy's unevaluated parser passes evaluate=False to function calls;
        # the legacy degree wrappers accept only the angle argument.
        def call(angle, **_):
            return function(angle)
        return call

    namespace = {name: getattr(sp, name) for name in dir(sp) if not name.startswith("_")}
    namespace.update(sin=degree(backend.sind), cos=degree(backend.cosd), tan=degree(backend.tand),
                     asin=degree(backend.asind), acos=degree(backend.acosd), atan=degree(backend.atand),
                     arcsin=degree(backend.asind), arccos=degree(backend.acosd), arctan=degree(backend.atand),
                     sind=degree(backend.sind), cosd=degree(backend.cosd), tand=degree(backend.tand),
                     asind=degree(backend.asind), acosd=degree(backend.acosd), atand=degree(backend.atand),
                     abs=sp.Abs, min=sp.Min, max=sp.Max, e=sp.E)
    namespace.update({name: sp.Symbol(name) for name in expressions})
    parsed = {}
    for name, text in expressions.items():
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Empty or non-string expression for {name!r}")
        if ":" in text:
            match = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)\s*", text)
            if match is None:
                raise ValueError(f"Invalid lookup for {name!r}; expected standalone 'column:instance'")
            parsed[name] = (match[1], match[2])
            continue
        try:
            local = dict(namespace)
            for tok in tokenize.generate_tokens(StringIO(text).readline):
                if tok.type == tokenize.NAME and tok.string not in local:
                    local[tok.string] = sp.Symbol(tok.string)
            # Retain references such as typo-typo or 0*typo for strict undefined
            # symbol validation instead of simplifying them away before binding.
            value = sp.sympify(text, locals=local, evaluate=False)
            parsed[name] = sp.sympify(value) if isinstance(value, bool) else value
            if not isinstance(parsed[name], sp.Basic):
                raise TypeError("Expected a SymPy expression")
        except (sp.SympifyError, SyntaxError, TypeError, ValueError, tokenize.TokenError) as exc:
            raise ValueError(f"Invalid expression {name!r}: {exc}") from exc
    return parsed


def _strict_solver(backend, app):
    """Keep legacy scheduling/iteration, but never swallow numerical errors.

    Include constant nodes and self-edges explicitly: the legacy dependency
    builder omits both. Its iterative SCC finder still excludes self-cycles;
    those are rejected rather than falsely reported as converged.
    """
    import numpy as np
    import sympy as sp

    class StrictSolver(backend.ROAREquationSolver):
        def build_dependency_graph(self):
            graph = defaultdict(set)
            for name, expression in self.equations.items():
                graph[name] = {str(symbol) for symbol in expression.free_symbols}
                for dependency in graph[name]:
                    graph.setdefault(dependency, set())
            return graph

        def topological_sort(self, graph):
            # The iterative backend reconstructs a graph without copying empty
            # lookup leaf nodes, then indexes those absent nodes' indegrees.
            complete = defaultdict(set, {name: set(deps) for name, deps in graph.items()})
            for deps in graph.values():
                for dependency in deps:
                    complete.setdefault(dependency, set())
            return super().topological_sort(complete)

        def evaluate_equation(self, expression, results, corner_dfs=None):
            symbols = sorted(expression.free_symbols, key=str)
            args = []
            for symbol in symbols:
                name = str(symbol)
                if name not in results:
                    raise ValueError(f"Unresolved symbol {name!r} while evaluating {expression}")
                # Legacy lookups are (n, 1), iterative seeds become (n,).
                # Flatten individual vectors BEFORE broadcasting; otherwise
                # NumPy silently creates an erroneous (n, n) Cartesian product.
                args.append(_vector(results[name], name))
            if args:
                args = np.broadcast_arrays(*args)
            function = sp.lambdify(symbols, expression, modules="numpy")
            try:
                return function(*args)
            except (TypeError, ValueError, NameError, AttributeError, ZeroDivisionError) as exc:
                raise ValueError(f"Failed to evaluate {expression}: {exc}") from exc

    return StrictSolver(top_level_app=app)


def evaluate_design(design, symbols=None, *, corners=None, home=None,
                    apply_constraints=True) -> list[EvaluationResult]:
    """Solve every enabled expression once per selected corner tuple.

    Requested symbols must be enabled expression names. Omitted ``corners`` uses
    the union of saved graph selections. Custom device corners are paired by
    index and must have equal counts; LUT sample counts must also match. Global
    lookups require an explicit/saved global selection, even in custom mode.
    Iterative failures/non-convergence raise; successful iteration info is kept.
    """
    import numpy as np
    import pandas as pd
    import sympy as sp

    expressions = dict(design.expressions)
    constraints = dict(design.constraints) if apply_constraints else {}
    requested = list(expressions) if symbols is None else ([symbols] if isinstance(symbols, str) else list(symbols))
    for name in requested:
        if name not in expressions:
            raise ValueError(f"Unknown requested symbol: {name!r}")
    backend = load_backend("equation_solver", home)
    info = design.get_device_corners()
    settings = dict(design.iterative_settings)
    if settings.get("enabled", False):
        iterations = settings.get("max_iterations", 50)
        tolerance = settings.get("tolerance", 1e-6)
        damping = settings.get("damping", 1.0)
        if type(iterations) is not int or iterations < 1:
            raise ValueError("Iterative max_iterations must be a positive integer")
        if not np.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("Iterative tolerance must be finite and positive")
        if not np.isfinite(damping) or not 0 < damping <= 1:
            raise ValueError("Iterative damping must be finite and in (0, 1]")
    editor = SimpleNamespace(get_expressions_and_constraints=lambda: (expressions, constraints),
                             get_device_corners=lambda: info,
                             get_iterative_settings=lambda: settings)
    app = SimpleNamespace(editor_window=editor)
    # Constraint names are labels, not definitions that can shadow expressions.
    equations = dict(expressions)
    constraint_keys = {}
    for index, (name, text) in enumerate(constraints.items()):
        key = f"__roar_constraint_{index}"
        while key in equations:
            key += "_"
        equations[key] = text
        constraint_keys[key] = name
    parsed = _parse(equations, backend)
    lookup_names = set(backend.ROAREquationSolver(app).lookup_vals)
    technologies = None
    output = []
    for label, global_path, mapping in _corner_tuples(design, corners, info):
        frames = {}
        paths = list(dict.fromkeys(([global_path] if global_path else []) + list(mapping.values())))
        if paths:
            if technologies is None:
                technologies = Technologies(home)
            frames = {path: technologies.load(path) for path in paths}
        sizes = {len(frame) for frame in frames.values()}
        if len(sizes) > 1:
            raise ValueError(f"LUT sample count mismatch in corner tuple {label}")
        size = next(iter(sizes), 1)
        bindings = {}
        solver = _strict_solver(backend, app)

        def bind(column, device=None):
            if device is not None and device not in info:
                raise ValueError(f"Unknown instance {device!r} in lookup {column}:{device}")
            path = mapping.get(device) if device is not None else global_path
            if path is None:
                raise ValueError(f"Missing global corner selection for lookup {column}" +
                                 (f":{device}" if device is not None else ""))
            frame = frames[path]
            if column not in frame.columns:
                raise ValueError(f"Missing LUT column {column!r} in {path}")
            key = f"__roar_lookup_{len(bindings)}"
            while key in equations or key in bindings:
                key += "_"
            bindings[key] = _broadcast(frame[column].to_numpy(), size, column)
            return sp.Symbol(key)

        for name, expression in parsed.items():
            if isinstance(expression, tuple):
                solver.equations[name] = bind(*expression)
            else:
                replacements = {}
                for symbol in expression.free_symbols:
                    dependency = str(symbol)
                    if dependency in expressions:
                        continue
                    if dependency not in lookup_names:
                        # Also permit actual normalized LUT columns not listed
                        # in the legacy tuple (e.g. kcgg, kcdd, w and l).
                        if global_path is None or dependency not in frames[global_path].columns:
                            raise ValueError(f"Undefined symbol {dependency!r} in expression {name!r}")
                    replacements[symbol] = bind(dependency)
                solver.equations[name] = expression.xreplace(replacements)
        solver.lookup_vals = tuple(bindings)
        data = [pd.DataFrame(bindings, index=range(size))]
        graph = solver.build_dependency_graph()
        if settings.get("enabled", False):
            if any(name in dependencies for name, dependencies in graph.items()):
                raise RuntimeError("The legacy iterative solver does not support self-referential cycles")
            values, convergence = solver.evaluate_equations_iterative(
                [], data, initial_guesses=settings.get("initial_guesses", {}),
                max_iterations=settings.get("max_iterations", 50),
                tolerance=settings.get("tolerance", 1e-6), damping=settings.get("damping", 1.0))
            if values is None or not convergence.get("converged", False):
                raise RuntimeError(f"Iterative evaluation failed to converge: {convergence}")
            # Legacy max(0, nan) can incorrectly declare a NaN cycle converged.
            for name in convergence.get("cycle_variables", ()):
                if name not in values or not np.isfinite(_vector(values[name], name)).all():
                    raise RuntimeError(f"Iterative evaluation produced non-finite cycle variable {name!r}")
        else:
            if solver.has_cycle(graph):
                raise ValueError("Cyclic expressions require the iterative solver")
            values = solver.evaluate_equations([], data)
            convergence = None
        if values is None:
            raise RuntimeError(f"Equation solver failed for corner {label}")
        # Validate ALL expressions, not just selected outputs; do not conceal
        # unresolved symbolic results in an unrequested expression.
        arrays = {name: _vector(values[name], name) for name in expressions}
        for name, array in arrays.items():
            _broadcast(array, size, name)
        mask = np.ones(size, dtype=bool)
        for key, name in constraint_keys.items():
            constraint = _broadcast(values[key], size, name)
            if constraint.dtype != np.dtype(bool):
                raise ValueError(f"Constraint {name!r} must evaluate to booleans")
            mask &= constraint
        output.append(EvaluationResult(label, {name: arrays[name] for name in requested},
                                       mask, convergence, dict(mapping)))
    return output


def graph_data(design, graph, home=None):
    """Extract finite, constraint-filtered linear x/y[/z] samples per tuple.

    ``graph`` is GUI state or an object with ``to_state()``. Log flags discard
    non-positive samples but do not log-transform physical values. Spin boxes,
    markers and presentation options do not change the evaluated samples.
    """
    import numpy as np
    import pandas as pd
    config = graph.to_state() if hasattr(graph, "to_state") else dict(graph)
    axes = "xyz" if config.get("checkbox_3d", False) else "xy"
    symbols = {axis: config.get(f"combo_{axis}_text", "") for axis in axes}
    if any(not symbol for symbol in symbols.values()):
        raise ValueError("Graph requires a symbol for each active axis")
    paths = config.get("checked_paths", [])
    frames = []
    if config.get("is_device_params_mode", True):
        technologies = Technologies(home)
        for path in _paths(paths):
            source = technologies.load(path)
            for symbol in symbols.values():
                if symbol not in source.columns:
                    raise ValueError(f"Unknown graph lookup/LUT column {symbol!r} in {path}")
            frame = pd.DataFrame({axis: source[symbol].to_numpy() for axis, symbol in symbols.items()})
            frame.attrs.update(source.attrs)
            frames.append((frame, np.ones(len(frame), dtype=bool)))
    else:
        for result in evaluate_design(design, list(dict.fromkeys(symbols.values())),
                                      corners=paths, home=home,
                                      apply_constraints=config.get("apply_constraints", True)):
            source = result.to_dataframe()
            frame = pd.DataFrame({axis: source[symbol].to_numpy() for axis, symbol in symbols.items()})
            frame.attrs.update(source.attrs)
            frames.append((frame, result.constraint_mask.copy()))
    output = []
    for frame, mask in frames:
        for axis in axes:
            values = frame[axis].to_numpy()
            mask &= np.isfinite(values)
            if config.get(f"checkbox_log{axis}", False):
                mask &= values > 0
        output.append(frame.loc[mask].reset_index(drop=True))
    return output
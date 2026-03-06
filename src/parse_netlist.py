#!/usr/bin/env python3
"""
parse_netlist.py

Reads and parses a SPICE netlist file (specifically the xschem/sky130-style
netlist used in the ROAR project).  The parser handles:

  * Comment lines   (** and *)
  * Continuation lines (+ at the start of a line)
  * .subckt / .ends directives
  * .iopin directives
  * MOSFET instance lines  (X… or M… prefixes)
  * Passive / source instance lines (R, C, L, V, I prefixes)
  * .end directive
  * Key=value and key='expression' parameter extraction

Usage
-----
    python parse_netlist.py                          # defaults to cm_ota.spice
    python parse_netlist.py path/to/other.spice
"""

import os
import re
import sys
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MOSFETInstance:
    """Represents a single MOSFET instance line."""
    name: str                          # e.g. "XM1"
    drain: str = ""
    gate: str = ""
    source: str = ""
    body: str = ""
    model: str = ""                    # e.g. "sky130_fd_pr__nfet_01v8"
    parameters: Dict[str, str] = field(default_factory=dict)  # L, W, nf, …

    def device_type(self) -> str:
        """Return 'nmos' or 'pmos' based on the model name."""
        model_lower = self.model.lower()
        if "nfet" in model_lower or "nmos" in model_lower:
            return "nmos"
        elif "pfet" in model_lower or "pmos" in model_lower:
            return "pmos"
        return "unknown"


@dataclass
class GenericInstance:
    """Represents a non-MOSFET instance (R, C, L, V, I, or subcircuit X)."""
    name: str
    nodes: List[str] = field(default_factory=list)
    model: str = ""
    parameters: Dict[str, str] = field(default_factory=dict)


@dataclass
class Subcircuit:
    """Represents a .subckt … .ends block."""
    name: str
    ports: List[str] = field(default_factory=list)
    instances: list = field(default_factory=list)   # MOSFETInstance | GenericInstance


@dataclass
class SpiceNetlist:
    """Top-level container for a parsed SPICE netlist."""
    filepath: str = ""
    title: str = ""
    comments: List[str] = field(default_factory=list)
    iopins: List[str] = field(default_factory=list)
    subcircuits: List[Subcircuit] = field(default_factory=list)
    top_instances: list = field(default_factory=list)  # instances outside .subckt
    directives: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_QUOTED_PARAM_RE = re.compile(
    r"(\w+)\s*=\s*'([^']*)'",
)
_SIMPLE_PARAM_RE = re.compile(
    r"(\w+)\s*=\s*(\S+)",
)


def _parse_parameters(token_string: str) -> Dict[str, str]:
    """Extract key=value pairs from a parameter string.

    Handles both plain values  (L=0.500)  and quoted expressions
    (ad='int((nf+1)/2) * W/nf * 0.29').
    """
    params: Dict[str, str] = {}

    # First pull out quoted params so they don't confuse the simple regex
    for m in _QUOTED_PARAM_RE.finditer(token_string):
        params[m.group(1)] = m.group(2)

    # Remove quoted params from the string, then grab simple ones
    remaining = _QUOTED_PARAM_RE.sub("", token_string)
    for m in _SIMPLE_PARAM_RE.finditer(remaining):
        key = m.group(1)
        if key not in params:
            params[key] = m.group(2)

    return params


def _split_tokens(line: str) -> List[str]:
    """Split a line into whitespace-delimited tokens, but keep quoted
    expressions (single-quoted) together."""
    tokens = []
    buf = ""
    in_quote = False
    for ch in line:
        if ch == "'" and not in_quote:
            in_quote = True
            buf += ch
        elif ch == "'" and in_quote:
            in_quote = False
            buf += ch
        elif ch in (" ", "\t") and not in_quote:
            if buf:
                tokens.append(buf)
                buf = ""
        else:
            buf += ch
    if buf:
        tokens.append(buf)
    return tokens


def _is_mosfet_instance(first_token: str) -> bool:
    """Return True if the line looks like a MOSFET instance (X or M prefix
    followed by a name)."""
    upper = first_token[0].upper()
    return upper in ("X", "M")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_spice_netlist(filepath: str) -> SpiceNetlist:
    """Read *filepath* and return a populated :class:`SpiceNetlist`."""

    netlist = SpiceNetlist(filepath=filepath)

    with open(filepath, "r") as fh:
        raw_lines = fh.readlines()

    # ------ 1. Join continuation lines (lines starting with '+') ----------
    joined_lines: List[str] = []
    for raw in raw_lines:
        stripped = raw.rstrip("\n").rstrip()
        if stripped.startswith("+"):
            if joined_lines:
                joined_lines[-1] += " " + stripped[1:].lstrip()
            else:
                joined_lines.append(stripped)
        else:
            joined_lines.append(stripped)

    # ------ 2. Walk through joined lines ----------------------------------
    current_subckt: Optional[Subcircuit] = None

    for line in joined_lines:
        stripped = line.strip()

        # blank line
        if not stripped:
            continue

        # Lines starting with * or ** (comments, commented-out directives)
        if stripped.startswith("*"):
            # Check for schematic path comment
            if "sch_path:" in stripped:
                netlist.title = stripped.split("sch_path:")[-1].strip()
                netlist.comments.append(stripped)
                continue
            # *.iopin <pin>
            m = re.match(r"^\*+\.iopin\s+(\S+)", stripped)
            if m:
                netlist.iopins.append(m.group(1))
                continue
            # **.subckt  (commented-out subckt header)
            m = re.match(r"^\*+\.subckt\s+(\S+)\s*(.*)", stripped)
            if m:
                name = m.group(1)
                ports = m.group(2).split() if m.group(2).strip() else []
                current_subckt = Subcircuit(name=name, ports=ports)
                continue
            # **.ends
            if re.match(r"^\*+\.ends", stripped):
                if current_subckt is not None:
                    netlist.subcircuits.append(current_subckt)
                    current_subckt = None
                continue
            # other comment
            netlist.comments.append(stripped)
            continue

        # ---- SPICE directives --------------------------------------------
        lower = stripped.lower()

        # .subckt
        if lower.startswith(".subckt"):
            tokens = stripped.split()
            name = tokens[1] if len(tokens) > 1 else "unknown"
            ports = tokens[2:] if len(tokens) > 2 else []
            current_subckt = Subcircuit(name=name, ports=ports)
            continue

        # .ends
        if lower.startswith(".ends"):
            if current_subckt is not None:
                netlist.subcircuits.append(current_subckt)
                current_subckt = None
            continue

        # .end
        if lower == ".end":
            netlist.directives.append(stripped)
            continue

        # other directives (.tran, .ac, .param, .include, …)
        if stripped.startswith("."):
            netlist.directives.append(stripped)
            continue

        # ---- Instance lines  (X, M, R, C, L, V, I) ----------------------
        tokens = _split_tokens(stripped)
        if not tokens:
            continue

        first = tokens[0]
        first_upper = first[0].upper()

        if _is_mosfet_instance(first):
            inst = _parse_mosfet_line(tokens, stripped)
            if current_subckt is not None:
                current_subckt.instances.append(inst)
            else:
                netlist.top_instances.append(inst)
        elif first_upper in ("R", "C", "L", "V", "I"):
            inst = _parse_generic_line(tokens, stripped)
            if current_subckt is not None:
                current_subckt.instances.append(inst)
            else:
                netlist.top_instances.append(inst)
        else:
            # Unknown line – store as directive / comment
            netlist.directives.append(stripped)

    # If a subcircuit was still open (missing .ends), store it anyway
    if current_subckt is not None:
        netlist.subcircuits.append(current_subckt)

    return netlist


def _parse_mosfet_line(tokens: List[str], full_line: str) -> MOSFETInstance:
    """Parse a MOSFET instance line into a :class:`MOSFETInstance`.

    Expected format (sky130 / xschem style):
        XM1 drain gate source body model_name key=val …
    """
    inst = MOSFETInstance(name=tokens[0])

    # Find the first token containing '=' – everything before it (after
    # the instance name) is positional:  drain gate source body model
    param_start = None
    for i, tok in enumerate(tokens[1:], start=1):
        if "=" in tok:
            param_start = i
            break

    if param_start is None:
        # No parameters found – best-effort positional parse
        positional = tokens[1:]
    else:
        positional = tokens[1:param_start]

    # Assign positional fields
    if len(positional) >= 1:
        inst.drain = positional[0]
    if len(positional) >= 2:
        inst.gate = positional[1]
    if len(positional) >= 3:
        inst.source = positional[2]
    if len(positional) >= 4:
        inst.body = positional[3]
    if len(positional) >= 5:
        inst.model = positional[4]

    # Parse key=value parameters from the full line (after the model name)
    # Using the full line preserves quoted expressions that may contain spaces.
    if inst.model:
        param_section = full_line.split(inst.model, 1)[-1]
    elif param_start is not None:
        param_section = " ".join(tokens[param_start:])
    else:
        param_section = ""

    inst.parameters = _parse_parameters(param_section)

    return inst


def _parse_generic_line(tokens: List[str], full_line: str) -> GenericInstance:
    """Parse a generic (non-MOSFET) instance line."""
    inst = GenericInstance(name=tokens[0])
    for tok in tokens[1:]:
        if "=" in tok:
            break
        inst.nodes.append(tok)

    # Last node might be a model name if there are params after it
    inst.parameters = _parse_parameters(full_line)
    return inst


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------

def print_netlist_summary(netlist: SpiceNetlist) -> None:
    """Print a human-readable summary of the parsed netlist."""
    print("=" * 65)
    print(f"  SPICE Netlist: {netlist.filepath}")
    if netlist.title:
        print(f"  Schematic:     {netlist.title}")
    print("=" * 65)

    if netlist.iopins:
        print(f"\n  I/O Pins ({len(netlist.iopins)}): {', '.join(netlist.iopins)}")

    if netlist.subcircuits:
        for sc in netlist.subcircuits:
            print(f"\n  Subcircuit: {sc.name}")
            print(f"    Ports: {', '.join(sc.ports)}")
            _print_instances(sc.instances, indent=4)

    if netlist.top_instances:
        print("\n  Top-level instances:")
        _print_instances(netlist.top_instances, indent=4)

    if netlist.directives:
        print(f"\n  Directives ({len(netlist.directives)}):")
        for d in netlist.directives:
            print(f"    {d}")

    # Collect unique nets
    all_nets = set()
    for inst in netlist.top_instances:
        if isinstance(inst, MOSFETInstance):
            all_nets.update([inst.drain, inst.gate, inst.source, inst.body])
        elif isinstance(inst, GenericInstance):
            all_nets.update(inst.nodes)
    for sc in netlist.subcircuits:
        for inst in sc.instances:
            if isinstance(inst, MOSFETInstance):
                all_nets.update([inst.drain, inst.gate, inst.source, inst.body])
            elif isinstance(inst, GenericInstance):
                all_nets.update(inst.nodes)
    all_nets.discard("")
    if all_nets:
        print(f"\n  Unique nets ({len(all_nets)}): {', '.join(sorted(all_nets))}")

    print()


def _print_instances(instances, indent=4):
    pad = " " * indent
    nmos_count = 0
    pmos_count = 0
    for inst in instances:
        if isinstance(inst, MOSFETInstance):
            dtype = inst.device_type()
            if dtype == "nmos":
                nmos_count += 1
            elif dtype == "pmos":
                pmos_count += 1
            print(f"{pad}[{dtype.upper():5s}] {inst.name:6s}  "
                  f"D={inst.drain:10s} G={inst.gate:10s} "
                  f"S={inst.source:10s} B={inst.body:10s}  "
                  f"model={inst.model}")
            if inst.parameters:
                param_str = "  ".join(f"{k}={v}" for k, v in inst.parameters.items())
                print(f"{pad}        params: {param_str}")
        elif isinstance(inst, GenericInstance):
            print(f"{pad}[ELEM ] {inst.name:6s}  "
                  f"nodes={', '.join(inst.nodes)}")
            if inst.parameters:
                param_str = "  ".join(f"{k}={v}" for k, v in inst.parameters.items())
                print(f"{pad}        params: {param_str}")
    if nmos_count or pmos_count:
        print(f"{pad}--- NMOS: {nmos_count}  PMOS: {pmos_count}  "
              f"Total: {nmos_count + pmos_count} ---")


def netlist_to_dict(netlist: SpiceNetlist) -> dict:
    """Convert the parsed netlist to a JSON-serialisable dictionary."""
    result = {
        "filepath": netlist.filepath,
        "title": netlist.title,
        "iopins": netlist.iopins,
        "comments": netlist.comments,
        "directives": netlist.directives,
        "subcircuits": [],
        "top_instances": [],
    }
    for sc in netlist.subcircuits:
        sc_dict = {"name": sc.name, "ports": sc.ports, "instances": []}
        for inst in sc.instances:
            sc_dict["instances"].append(_instance_to_dict(inst))
        result["subcircuits"].append(sc_dict)
    for inst in netlist.top_instances:
        result["top_instances"].append(_instance_to_dict(inst))
    return result


def _instance_to_dict(inst) -> dict:
    if isinstance(inst, MOSFETInstance):
        return {
            "type": "mosfet",
            "name": inst.name,
            "drain": inst.drain,
            "gate": inst.gate,
            "source": inst.source,
            "body": inst.body,
            "model": inst.model,
            "device_type": inst.device_type(),
            "parameters": inst.parameters,
        }
    elif isinstance(inst, GenericInstance):
        return {
            "type": "generic",
            "name": inst.name,
            "nodes": inst.nodes,
            "model": inst.model,
            "parameters": inst.parameters,
        }
    return {}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    default_path = os.path.join(os.path.dirname(__file__), "cm_ota.spice")
    filepath = sys.argv[1] if len(sys.argv) > 1 else default_path

    if not os.path.isfile(filepath):
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    netlist = parse_spice_netlist(filepath)
    print_netlist_summary(netlist)

    # Optionally dump JSON with --json flag
    if "--json" in sys.argv:
        print(json.dumps(netlist_to_dict(netlist), indent=2))

    # Optionally run topology identification with --topology flag
    if "--topology" in sys.argv:
        from topology import identify_topology, print_topology_report
        result = identify_topology(netlist)
        print_topology_report(result)


if __name__ == "__main__":
    main()


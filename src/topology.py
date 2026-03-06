#!/usr/bin/env python3
"""
topology.py

Identifies analog circuit topology from a parsed SPICE netlist.

Detection proceeds bottom-up:
  1. Diode-connected transistors  (gate == drain)
  2. Current mirrors              (shared gate, same type, one diode-connected)
  3. Differential pairs            (shared source, gates are input pins)
  4. Tail current sources          (drain feeds diff-pair source, source on supply)
  5. Active loads                  (opposite-type device on diff-pair drain nets)
  6. Overall topology classification

Usage
-----
    python topology.py                          # defaults to cm_ota.spice
    python topology.py path/to/other.spice
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional

from parse_netlist import (
    MOSFETInstance,
    SpiceNetlist,
    parse_spice_netlist,
    print_netlist_summary,
)


# ---------------------------------------------------------------------------
# Helper – supply net detection
# ---------------------------------------------------------------------------

_DEFAULT_SUPPLY_NAMES = {"vdd", "vss", "gnd", "avdd", "avss", "dvdd", "dvss"}


def _net(name: str) -> str:
    """Normalise a net name for comparison (lowercase)."""
    return name.strip().lower()


def infer_supply_nets(mosfets: List[MOSFETInstance]) -> Tuple[Set[str], Set[str]]:
    """Infer positive and negative supply nets from MOSFET body connections.

    A body net is only considered a supply if it is shared by a majority of
    transistors of that type (e.g. vdd is the body of most PMOS devices).
    This avoids false positives like a diff-pair source net used as bulk in
    4-terminal MOSFET instances.

    Returns (positive_supplies, negative_supplies).
    """
    from collections import Counter
    pos: Set[str] = set()
    neg: Set[str] = set()

    # Count body-net occurrences per device type
    pmos_bodies: Counter = Counter()
    nmos_bodies: Counter = Counter()
    n_pmos = 0
    n_nmos = 0
    for m in mosfets:
        body = _net(m.body)
        if not body:
            continue
        if m.device_type() == "pmos":
            pmos_bodies[body] += 1
            n_pmos += 1
        elif m.device_type() == "nmos":
            nmos_bodies[body] += 1
            n_nmos += 1

    # A body net is a supply if it is used by more than half of that type
    threshold_p = max(n_pmos / 2, 1)
    threshold_n = max(n_nmos / 2, 1)
    for net, count in pmos_bodies.items():
        if count >= threshold_p:
            pos.add(net)
    for net, count in nmos_bodies.items():
        if count >= threshold_n:
            neg.add(net)

    # Also include well-known names
    for s in _DEFAULT_SUPPLY_NAMES:
        if s in ("vdd", "avdd", "dvdd"):
            pos.add(s)
        else:
            neg.add(s)
    return pos, neg


def is_supply(net: str, pos: Set[str], neg: Set[str]) -> bool:
    return _net(net) in pos or _net(net) in neg


# ---------------------------------------------------------------------------
# Sub-block dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DiodeConnected:
    """A transistor with gate tied to drain."""
    instance: MOSFETInstance


@dataclass
class CurrentMirror:
    """A current mirror: one diode-connected reference + one or more outputs."""
    reference: MOSFETInstance               # diode-connected device
    outputs: List[MOSFETInstance]            # mirror copies
    gate_net: str                            # shared gate net
    device_type: str                         # "nmos" or "pmos"


@dataclass
class DifferentialPair:
    """A differential pair sharing a source node."""
    m_pos: MOSFETInstance                    # gate on positive input
    m_neg: MOSFETInstance                    # gate on negative input
    source_net: str                          # shared source net
    device_type: str                         # "nmos" or "pmos"


@dataclass
class TailCurrentSource:
    """Transistor biasing a differential pair."""
    instance: MOSFETInstance
    diff_pair_source_net: str


@dataclass
class ActiveLoad:
    """Transistor(s) loading a diff-pair drain."""
    instances: List[MOSFETInstance]
    load_net: str                            # the diff-pair drain net they share
    device_type: str                         # "nmos" or "pmos"
    is_mirror: bool = False                  # True if part of a current mirror


@dataclass
class TopologyResult:
    """Complete topology analysis result."""
    mosfets: List[MOSFETInstance] = field(default_factory=list)
    diode_connected: List[DiodeConnected] = field(default_factory=list)
    current_mirrors: List[CurrentMirror] = field(default_factory=list)
    diff_pairs: List[DifferentialPair] = field(default_factory=list)
    tail_sources: List[TailCurrentSource] = field(default_factory=list)
    active_loads: List[ActiveLoad] = field(default_factory=list)
    classification: str = "Unknown"
    classification_notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 1. Diode-connected detection
# ---------------------------------------------------------------------------

def find_diode_connected(
    mosfets: List[MOSFETInstance],
    pos_supply: Set[str],
    neg_supply: Set[str],
) -> Dict[str, DiodeConnected]:
    """Return dict keyed by instance name for every diode-connected MOSFET."""
    result: Dict[str, DiodeConnected] = {}
    for m in mosfets:
        g = _net(m.gate)
        d = _net(m.drain)
        # gate == drain and the net is not a supply rail
        if g and d and g == d and not is_supply(g, pos_supply, neg_supply):
            result[m.name] = DiodeConnected(instance=m)
    return result


# ---------------------------------------------------------------------------
# 2. Current mirror detection
# ---------------------------------------------------------------------------

def find_current_mirrors(
    mosfets: List[MOSFETInstance],
    diode_set: Dict[str, DiodeConnected],
    pos_supply: Set[str],
    neg_supply: Set[str],
) -> List[CurrentMirror]:
    """Group same-type MOSFETs sharing a gate net; require ≥1 diode-connected."""
    # Group by (device_type, gate_net)
    groups: Dict[Tuple[str, str], List[MOSFETInstance]] = {}
    for m in mosfets:
        key = (m.device_type(), _net(m.gate))
        groups.setdefault(key, []).append(m)

    mirrors: List[CurrentMirror] = []
    for (dtype, gate), members in groups.items():
        if len(members) < 2:
            continue
        # Skip if gate is a supply net (e.g. both bodies tied to vdd)
        if is_supply(gate, pos_supply, neg_supply):
            continue
        # Find the diode-connected reference(s)
        refs = [m for m in members if m.name in diode_set]
        outs = [m for m in members if m.name not in diode_set]
        if not refs:
            continue
        # Use first diode-connected as the reference
        mirrors.append(CurrentMirror(
            reference=refs[0],
            outputs=outs + refs[1:],   # extra diode-connected treated as outputs
            gate_net=gate,
            device_type=dtype,
        ))
    return mirrors


# ---------------------------------------------------------------------------
# 3. Differential pair detection
# ---------------------------------------------------------------------------

def find_differential_pairs(
    mosfets: List[MOSFETInstance],
    iopins: List[str],
    pos_supply: Set[str],
    neg_supply: Set[str],
) -> List[DifferentialPair]:
    """Find pairs of same-type MOSFETs sharing a source net with gates on I/O pins."""
    iopin_set = {_net(p) for p in iopins}

    # Group by (device_type, source_net), excluding supply source nets
    groups: Dict[Tuple[str, str], List[MOSFETInstance]] = {}
    for m in mosfets:
        s = _net(m.source)
        if is_supply(s, pos_supply, neg_supply):
            continue
        key = (m.device_type(), s)
        groups.setdefault(key, []).append(m)

    pairs: List[DifferentialPair] = []
    for (dtype, src_net), members in groups.items():
        if len(members) < 2:
            continue
        # Find members whose gates are I/O pins
        input_members = [m for m in members if _net(m.gate) in iopin_set]
        if len(input_members) < 2:
            continue
        # Take the first two as the diff pair
        m_a, m_b = input_members[0], input_members[1]
        # Heuristic: label the one with "inp" / "+" as positive
        ga = _net(m_a.gate)
        gb = _net(m_b.gate)
        if "inp" in ga or "+" in ga or "p" == ga[-1:]:
            m_pos, m_neg = m_a, m_b
        elif "inp" in gb or "+" in gb or "p" == gb[-1:]:
            m_pos, m_neg = m_b, m_a
        else:
            m_pos, m_neg = m_a, m_b  # arbitrary
        pairs.append(DifferentialPair(
            m_pos=m_pos, m_neg=m_neg,
            source_net=src_net, device_type=dtype,
        ))
    return pairs


# ---------------------------------------------------------------------------
# 4. Tail current source detection
# ---------------------------------------------------------------------------

def find_tail_current_sources(
    mosfets: List[MOSFETInstance],
    diff_pairs: List[DifferentialPair],
    pos_supply: Set[str],
    neg_supply: Set[str],
) -> List[TailCurrentSource]:
    """Find transistors whose drain feeds a diff-pair source net."""
    dp_source_nets = {dp.source_net for dp in diff_pairs}
    results: List[TailCurrentSource] = []
    seen: Set[str] = set()
    for m in mosfets:
        d = _net(m.drain)
        s = _net(m.source)
        if d in dp_source_nets and is_supply(s, pos_supply, neg_supply):
            if m.name not in seen:
                results.append(TailCurrentSource(instance=m, diff_pair_source_net=d))
                seen.add(m.name)
    return results


# ---------------------------------------------------------------------------
# 5. Active load detection
# ---------------------------------------------------------------------------

def find_active_loads(
    mosfets: List[MOSFETInstance],
    diff_pairs: List[DifferentialPair],
    mirrors: List[CurrentMirror],
) -> List[ActiveLoad]:
    """Find opposite-type devices connected to diff-pair drain nets."""
    # Build set of mirror instance names for quick lookup
    mirror_names: Set[str] = set()
    for cm in mirrors:
        mirror_names.add(cm.reference.name)
        for o in cm.outputs:
            mirror_names.add(o.name)

    # Diff-pair member names (skip these)
    dp_names: Set[str] = set()
    for dp in diff_pairs:
        dp_names.add(dp.m_pos.name)
        dp_names.add(dp.m_neg.name)

    results: List[ActiveLoad] = []
    for dp in diff_pairs:
        dp_type = dp.device_type
        for dp_drain in (_net(dp.m_pos.drain), _net(dp.m_neg.drain)):
            load_fets = []
            for m in mosfets:
                if m.name in dp_names:
                    continue
                if m.device_type() == dp_type:
                    continue  # same type as diff pair → not a load
                if _net(m.drain) == dp_drain:
                    load_fets.append(m)
            if load_fets:
                any_mirror = any(m.name in mirror_names for m in load_fets)
                results.append(ActiveLoad(
                    instances=load_fets,
                    load_net=dp_drain,
                    device_type=load_fets[0].device_type(),
                    is_mirror=any_mirror,
                ))
    return results


# ---------------------------------------------------------------------------
# 6. Output stage detection helpers
# ---------------------------------------------------------------------------

def _find_output_net(iopins: List[str], pos_supply: Set[str], neg_supply: Set[str]) -> Optional[str]:
    """Heuristic: find the output pin among I/O pins."""
    for p in iopins:
        pn = _net(p)
        if pn in ("out", "vout", "output", "outp", "outn"):
            return pn
    # Fallback: pick first pin that isn't supply or obvious input
    input_like = {"inp", "inn", "in+", "in-", "in", "vinp", "vinn",
                  "itail", "ibias", "vbias"}
    for p in iopins:
        pn = _net(p)
        if pn not in pos_supply and pn not in neg_supply and pn not in input_like:
            return pn
    return None


def _find_output_stage_mirrors(
    mirrors: List[CurrentMirror],
    diff_pairs: List[DifferentialPair],
    output_net: Optional[str],
) -> List[CurrentMirror]:
    """Find mirrors that drive the output net but are NOT active loads of the diff pair."""
    if output_net is None:
        return []
    dp_drain_nets: Set[str] = set()
    for dp in diff_pairs:
        dp_drain_nets.add(_net(dp.m_pos.drain))
        dp_drain_nets.add(_net(dp.m_neg.drain))

    output_mirrors: List[CurrentMirror] = []
    for cm in mirrors:
        drives_output = False
        for out_m in cm.outputs:
            if _net(out_m.drain) == output_net:
                drives_output = True
                break
        if not drives_output and _net(cm.reference.drain) == output_net:
            drives_output = True
        # Mirror gate net should NOT be a diff-pair drain (those are loads, not output stage)
        # Actually it CAN be — the load mirrors *re-mirror* to the output.  Check if any
        # mirror *output* device drain is the output net.
        if drives_output:
            output_mirrors.append(cm)
    return output_mirrors


# ---------------------------------------------------------------------------
# 7. Overall classification
# ---------------------------------------------------------------------------

def classify_topology(result: TopologyResult, iopins: List[str],
                      pos_supply: Set[str], neg_supply: Set[str]) -> None:
    """Set result.classification and result.classification_notes."""
    n_fets = len(result.mosfets)
    n_dp = len(result.diff_pairs)
    n_mirrors = len(result.current_mirrors)
    n_tail = len(result.tail_sources)
    n_loads = len(result.active_loads)

    notes = result.classification_notes
    output_net = _find_output_net(iopins, pos_supply, neg_supply)
    notes.append(f"Total MOSFETs: {n_fets}")
    notes.append(f"Differential pairs: {n_dp}")
    notes.append(f"Current mirrors: {n_mirrors}")
    notes.append(f"Tail current sources: {n_tail}")
    notes.append(f"Active loads: {n_loads}")
    if output_net:
        notes.append(f"Output net: {output_net}")

    # ---- No diff pair → not a recognisable OTA --------------------------
    if n_dp == 0:
        result.classification = "Unknown (no differential pair found)"
        return

    dp = result.diff_pairs[0]
    dp_type = dp.device_type  # e.g. "nmos"
    opp_type = "pmos" if dp_type == "nmos" else "nmos"

    # Collect diff-pair drain nets
    dp_drain_nets = {_net(dp.m_pos.drain), _net(dp.m_neg.drain)}

    # ---- Five-transistor OTA (simplest) ----------------------------------
    if n_fets == 5 and n_dp == 1 and n_mirrors >= 1 and n_tail >= 1:
        result.classification = "Five-Transistor OTA"
        notes.append("Classic 5T OTA: 1 diff pair + 1 mirror load + 1 tail source")
        return

    # ---- Identify output-stage mirrors -----------------------------------
    output_mirrors = _find_output_stage_mirrors(
        result.current_mirrors, result.diff_pairs, output_net)

    # Mirrors whose gate net is a diff-pair drain net → load mirrors
    load_mirrors = [cm for cm in result.current_mirrors
                    if cm.gate_net in dp_drain_nets]
    # Mirrors that are NOT load mirrors and NOT tail mirrors
    tail_gate_nets = {_net(ts.instance.gate) for ts in result.tail_sources}
    non_load_mirrors = [cm for cm in result.current_mirrors
                        if cm.gate_net not in dp_drain_nets
                        and cm.gate_net not in tail_gate_nets]

    # ---- Two-stage OTA ---------------------------------------------------
    # Second stage: a common-source transistor whose gate is driven by the
    # first-stage output and whose drain is the final output.
    second_stage_fets = []
    if output_net:
        # First-stage output candidates: diff-pair drain nets
        for m in result.mosfets:
            if m.name == dp.m_pos.name or m.name == dp.m_neg.name:
                continue
            if _net(m.gate) in dp_drain_nets and _net(m.drain) == output_net:
                # Ensure it's not part of a load mirror
                is_load = any(_net(m.gate) == cm.gate_net for cm in load_mirrors)
                if not is_load:
                    second_stage_fets.append(m)

    if second_stage_fets:
        result.classification = "Two-Stage OTA"
        names = ", ".join(m.name for m in second_stage_fets)
        notes.append(f"Second gain stage transistor(s): {names}")
        return

    # ---- Current-mirror OTA ----------------------------------------------
    # Diff pair has diode-connected active loads of opposite type whose
    # mirror copies (or additional mirrors) drive the output net.
    if load_mirrors and output_mirrors:
        result.classification = "Current-Mirror OTA"
        load_names = ", ".join(f"{cm.reference.name}→" +
                               ",".join(o.name for o in cm.outputs)
                               for cm in load_mirrors)
        out_names = ", ".join(f"{cm.reference.name}→" +
                              ",".join(o.name for o in cm.outputs)
                              for cm in output_mirrors)
        notes.append(f"Load mirrors: {load_names}")
        notes.append(f"Output mirrors: {out_names}")
        return

    # ---- Folded-cascode OTA ----------------------------------------------
    # Key signature: transistors of the SAME type as the diff pair (but not
    # the diff pair itself) whose sources are on supply and whose drains
    # connect to diff-pair drain nets — current "folds" from the diff pair
    # into these same-type transistors.
    same_type_on_dp_drains = [m for m in result.mosfets
                              if m.device_type() == dp_type
                              and m.name != dp.m_pos.name
                              and m.name != dp.m_neg.name
                              and _net(m.drain) in dp_drain_nets
                              and is_supply(_net(m.source), pos_supply, neg_supply)]
    # Also look for same-type transistors whose SOURCE connects to a
    # diff-pair drain net (cascode configuration)
    same_type_cascode = [m for m in result.mosfets
                         if m.device_type() == dp_type
                         and m.name != dp.m_pos.name
                         and m.name != dp.m_neg.name
                         and _net(m.source) in dp_drain_nets]
    folding_fets = same_type_on_dp_drains + same_type_cascode
    if folding_fets and n_loads > 0:
        result.classification = "Folded-Cascode OTA"
        names = ", ".join(m.name for m in folding_fets)
        notes.append(f"Folding transistors: {names}")
        return

    # ---- Telescopic OTA --------------------------------------------------
    # All load/cascode transistors are opposite type, stacked between diff-pair
    # drains and supply, with NO current folding.
    cascode_candidates = [m for m in result.mosfets
                          if m.device_type() == opp_type
                          and _net(m.source) in dp_drain_nets
                          and not is_supply(_net(m.drain), pos_supply, neg_supply)]
    if cascode_candidates and not folding_fets:
        result.classification = "Telescopic OTA"
        names = ", ".join(m.name for m in cascode_candidates)
        notes.append(f"Cascode transistors: {names}")
        return

    # ---- Simple OTA with mirror load (no output stage mirror) ------------
    if load_mirrors and not output_mirrors:
        result.classification = "Simple Mirror-Loaded OTA"
        return

    # ---- Fallback --------------------------------------------------------
    result.classification = "Unknown"
    notes.append("Could not match a known OTA topology pattern.")


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def identify_topology(netlist: SpiceNetlist) -> TopologyResult:
    """Run the full topology identification pipeline on *netlist*."""

    # Gather all MOSFET instances (from subcircuits first, then top-level)
    mosfets: List[MOSFETInstance] = []
    for sc in netlist.subcircuits:
        for inst in sc.instances:
            if isinstance(inst, MOSFETInstance):
                mosfets.append(inst)
    for inst in netlist.top_instances:
        if isinstance(inst, MOSFETInstance):
            mosfets.append(inst)

    if not mosfets:
        return TopologyResult(classification="No MOSFETs found")

    # Infer supply nets
    pos_supply, neg_supply = infer_supply_nets(mosfets)

    # Collect I/O pins from both netlist.iopins and subcircuit ports
    all_iopins: List[str] = list(netlist.iopins)
    for sc in netlist.subcircuits:
        for p in sc.ports:
            if _net(p) not in {_net(x) for x in all_iopins}:
                all_iopins.append(p)

    # 1. Diode-connected
    diode_map = find_diode_connected(mosfets, pos_supply, neg_supply)

    # 2. Current mirrors
    mirrors = find_current_mirrors(mosfets, diode_map, pos_supply, neg_supply)

    # 3. Differential pairs
    diff_pairs = find_differential_pairs(mosfets, all_iopins, pos_supply, neg_supply)

    # 4. Tail current sources
    tail_sources = find_tail_current_sources(mosfets, diff_pairs, pos_supply, neg_supply)

    # 5. Active loads
    active_loads = find_active_loads(mosfets, diff_pairs, mirrors)

    # Assemble result
    result = TopologyResult(
        mosfets=mosfets,
        diode_connected=list(diode_map.values()),
        current_mirrors=mirrors,
        diff_pairs=diff_pairs,
        tail_sources=tail_sources,
        active_loads=active_loads,
    )

    # 6. Classify
    classify_topology(result, all_iopins, pos_supply, neg_supply)

    return result


# ---------------------------------------------------------------------------
# Pretty-print
# ---------------------------------------------------------------------------

def print_topology_report(result: TopologyResult) -> None:
    """Print a human-readable topology analysis report."""
    print()
    print("=" * 65)
    print("  TOPOLOGY ANALYSIS REPORT")
    print("=" * 65)

    # Diode-connected
    print(f"\n  Diode-connected transistors ({len(result.diode_connected)}):")
    for dc in result.diode_connected:
        m = dc.instance
        print(f"    {m.name:6s} [{m.device_type().upper():5s}]  "
              f"gate=drain={_net(m.drain)}")

    # Current mirrors
    print(f"\n  Current mirrors ({len(result.current_mirrors)}):")
    for cm in result.current_mirrors:
        out_names = ", ".join(m.name for m in cm.outputs)
        print(f"    [{cm.device_type.upper():5s}] gate_net={cm.gate_net:12s}  "
              f"ref={cm.reference.name:6s} → outputs=[{out_names}]")

    # Differential pairs
    print(f"\n  Differential pairs ({len(result.diff_pairs)}):")
    for dp in result.diff_pairs:
        print(f"    [{dp.device_type.upper():5s}] "
              f"{dp.m_pos.name} (G={dp.m_pos.gate}) / "
              f"{dp.m_neg.name} (G={dp.m_neg.gate})  "
              f"shared source={dp.source_net}")

    # Tail current sources
    print(f"\n  Tail current sources ({len(result.tail_sources)}):")
    for ts in result.tail_sources:
        m = ts.instance
        print(f"    {m.name:6s} [{m.device_type().upper():5s}]  "
              f"drain→{ts.diff_pair_source_net}  gate={m.gate}")

    # Active loads
    print(f"\n  Active loads ({len(result.active_loads)}):")
    for al in result.active_loads:
        names = ", ".join(m.name for m in al.instances)
        mirror_tag = " (mirror)" if al.is_mirror else ""
        print(f"    [{al.device_type.upper():5s}] on net={al.load_net:12s}  "
              f"devices=[{names}]{mirror_tag}")

    # Classification
    print(f"\n  {'─' * 61}")
    print(f"  CLASSIFICATION:  {result.classification}")
    if result.classification_notes:
        print(f"  {'─' * 61}")
        for note in result.classification_notes:
            print(f"    • {note}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cm_ota.spice")
    filepath = sys.argv[1] if len(sys.argv) > 1 else default_path

    if not os.path.isfile(filepath):
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    netlist = parse_spice_netlist(filepath)
    print_netlist_summary(netlist)

    result = identify_topology(netlist)
    print_topology_report(result)


if __name__ == "__main__":
    main()


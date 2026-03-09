"""
GUI/results.py

ResultsCache — holds the solved FrameAnalysis instance and pre-computed
per-member force envelopes so the viewport and property panel can query
results without re-running the solver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np

if TYPE_CHECKING:
    from mech_core.analysis.fea import FrameAnalysis
    from .document import StructuralDocument


@dataclass
class MemberResults:
    """Pre-sampled forces for a single member."""
    member_id: str
    positions: List[float]            # x positions along member (m)
    axial:     List[float]            # Fx  (kN)
    shear_y:   List[float]            # Vy  (kN)
    shear_z:   List[float]            # Vz  (kN)
    moment_y:  List[float]            # My  (kN·m)  weak axis
    moment_z:  List[float]            # Mz  (kN·m)  strong axis
    torsion:   List[float]            # Tx  (kN·m)
    # Envelope values
    max_shear_y: float  = 0.0
    min_shear_y: float  = 0.0
    max_moment_z: float = 0.0
    min_moment_z: float = 0.0


@dataclass
class NodeDisplacement:
    node_id: str
    dx: float   # m
    dy: float   # m
    dz: float   # m
    rx: float   # rad
    ry: float   # rad
    rz: float   # rad


class ResultsCache:
    """
    Stores a solved FrameAnalysis instance and derived display data.

    Keeps the FrameAnalysis object alive so the viewport can query
    deflections and forces on demand.
    """

    def __init__(
        self,
        fea: "FrameAnalysis",
        node_displacements: Dict[str, NodeDisplacement],
        member_results:     Dict[str, MemberResults],
        scale_factor:       float = 100.0,
        load_case:          str   = "Case 1",
    ):
        self.fea                  = fea
        self.node_displacements   = node_displacements
        self.member_results       = member_results
        self.scale_factor         = scale_factor
        self.load_case            = load_case

    # ---- Factory ------------------------------------------------------------

    @classmethod
    def from_fea(
        cls,
        fea: "FrameAnalysis",
        doc: "StructuralDocument",
        n_sample: int    = 30,
        load_case: str   = "Case 1",
    ) -> "ResultsCache":
        """Build a ResultsCache from a solved FrameAnalysis."""

        node_displacements: Dict[str, NodeDisplacement] = {}
        member_results:     Dict[str, MemberResults]    = {}

        # ---- Node displacements --------------------------------------------
        for nd in doc.nodes.values():
            try:
                pn_node = fea.model.nodes[nd.id]
                node_displacements[nd.id] = NodeDisplacement(
                    node_id = nd.id,
                    dx = getattr(pn_node, "DX", {}).get(load_case, 0.0),
                    dy = getattr(pn_node, "DY", {}).get(load_case, 0.0),
                    dz = getattr(pn_node, "DZ", {}).get(load_case, 0.0),
                    rx = getattr(pn_node, "RX", {}).get(load_case, 0.0),
                    ry = getattr(pn_node, "RY", {}).get(load_case, 0.0),
                    rz = getattr(pn_node, "RZ", {}).get(load_case, 0.0),
                )
            except (KeyError, AttributeError):
                node_displacements[nd.id] = NodeDisplacement(nd.id, 0, 0, 0, 0, 0, 0)

        # ---- Member force diagrams -----------------------------------------
        for mb in doc.members.values():
            try:
                pn_member = fea.model.members[mb.id]
                L = pn_member.L()
                positions = list(np.linspace(0, L, n_sample))

                axial    = [pn_member.axial(x, combo_name=load_case) / 1e3   for x in positions]
                shear_y  = [pn_member.shear('Fy', x, combo_name=load_case) / 1e3 for x in positions]
                shear_z  = [pn_member.shear('Fz', x, combo_name=load_case) / 1e3 for x in positions]
                moment_y = [pn_member.moment('My', x, combo_name=load_case) / 1e3 for x in positions]
                moment_z = [pn_member.moment('Mz', x, combo_name=load_case) / 1e3 for x in positions]

                # Torsion (Tx) — safe fallback
                try:
                    torsion = [pn_member.torque(x, combo_name=load_case) / 1e3 for x in positions]
                except Exception:
                    torsion = [0.0] * len(positions)

                mr = MemberResults(
                    member_id    = mb.id,
                    positions    = positions,
                    axial        = axial,
                    shear_y      = shear_y,
                    shear_z      = shear_z,
                    moment_y     = moment_y,
                    moment_z     = moment_z,
                    torsion      = torsion,
                    max_shear_y  = max(shear_y),
                    min_shear_y  = min(shear_y),
                    max_moment_z = max(moment_z),
                    min_moment_z = min(moment_z),
                )
                member_results[mb.id] = mr

            except Exception:
                # If a member fails to sample, skip gracefully
                pass

        return cls(
            fea                = fea,
            node_displacements = node_displacements,
            member_results     = member_results,
            load_case          = load_case,
        )

    # ---- Convenience accessors ----------------------------------------------

    def deformed_node_pos(
        self, node_id: str,
        orig_x: float, orig_y: float, orig_z: float,
        scale: float,
    ) -> Tuple[float, float, float]:
        """Return deformed position of a node at given display scale."""
        disp = self.node_displacements.get(node_id)
        if disp is None:
            return orig_x, orig_y, orig_z
        return (
            orig_x + disp.dx * scale,
            orig_y + disp.dy * scale,
            orig_z + disp.dz * scale,
        )

    def diagram_data(
        self, member_id: str, diagram_type: str
    ) -> Tuple[List[float], List[float]]:
        """
        Return (positions, values) for a force diagram.

        diagram_type: "axial" | "shear_y" | "shear_z" |
                      "moment_y" | "moment_z" | "torsion"
        """
        mr = self.member_results.get(member_id)
        if mr is None:
            return [], []
        data = getattr(mr, diagram_type, [])
        return mr.positions, data

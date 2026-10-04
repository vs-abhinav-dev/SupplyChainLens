from typing import List
from ..graph.backend import GraphBackend
from .base import GraphAnalyzer
from .models import CycleItem, CyclesResult


class CyclesAnalyzer(GraphAnalyzer):
    """
    Detects circular dependencies and multi-package cycles in the graph.
    Cycles create build and resolution deadlocks and elevate supply chain risk.
    """

    @property
    def name(self) -> str:
        return "cycles"

    @property
    def description(self) -> str:
        return "Detects circular dependency loops and strongly connected dependency components."

    @property
    def category(self) -> str:
        return "cycles"

    def analyze(self, graph: GraphBackend, max_cycles: int = 50, **kwargs) -> CyclesResult:
        # Non-trivial SCCs (size >= 2) indicate circular dependencies
        sccs = graph.strongly_connected_components()
        non_trivial_sccs = [scc for scc in sccs if len(scc) > 1]

        detected_cycles: List[CycleItem] = []
        cycle_idx = 1

        for scc in non_trivial_sccs:
            subgraph = graph.get_subgraph(scc)
            sorted_scc = sorted(list(scc))
            start_node = sorted_scc[0]

            # Find a closed directed cycle path starting from start_node within the SCC
            # Path search from start_node to its predecessors within SCC
            pred_within_scc = [
                p.node_id for p in subgraph.predecessors(start_node) if p.node_id in scc
            ]
            cycle_path = []
            for pred in pred_within_scc:
                path = subgraph.shortest_path(start_node, pred)
                if path:
                    cycle_path = path + [start_node]
                    break

            if not cycle_path:
                cycle_path = sorted_scc

            detected_cycles.append(CycleItem(
                cycle_id=cycle_idx,
                length=len(scc),
                cycle=cycle_path,
            ))
            cycle_idx += 1
            if cycle_idx > max_cycles:
                break

        # Check for self-loops (node depending on its own version)
        for node in graph.nodes():
            if graph.has_edge(node.node_id, node.node_id):
                detected_cycles.append(CycleItem(
                    cycle_id=cycle_idx,
                    length=1,
                    cycle=[node.node_id, node.node_id],
                ))
                cycle_idx += 1
                if cycle_idx > max_cycles:
                    break

        return CyclesResult(
            total_cycles=len(detected_cycles),
            has_cycles=len(detected_cycles) > 0,
            cycles=detected_cycles,
        )

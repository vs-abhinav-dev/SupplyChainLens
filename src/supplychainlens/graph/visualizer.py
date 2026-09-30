from typing import Set
from .graph import VersionGraph


def _clean_node_label(node_id: str) -> str:
    """Format node_id cleanly (e.g. 'npm:express@4.18.0' -> 'express@4.18.0')."""
    if node_id.startswith("npm:"):
        return node_id[4:]
    return node_id


def render_ascii_subgraph(
    graph: VersionGraph,
    root_node_id: str,
    max_depth: int = 2,
    direction: str = "outgoing",
) -> str:
    """
    Renders a small ASCII tree representation of a subgraph starting from root_node_id.

    Parameters
    ----------
    graph : VersionGraph
        The graph containing nodes and edges.
    root_node_id : str
        The starting node_id (e.g. 'npm:express@5.1.0').
    max_depth : int, default=2
        Maximum tree depth traversal.
    direction : str, default="outgoing"
        'outgoing' to show dependencies (A depends on B), or 'incoming' to show dependents (B depends on A).

    Returns
    -------
    str
        ASCII formatted multiline string representing the subgraph tree.
    """
    if not graph.has_node(root_node_id):
        return f"Node '{root_node_id}' not found in graph."

    lines = []
    lines.append(_clean_node_label(root_node_id))

    def _build_tree(node_id: str, current_depth: int, prefix: str, visited: Set[str]):
        if current_depth >= max_depth:
            return

        if direction == "outgoing":
            edges = graph.get_outgoing_edges(node_id)
            adjacent_ids = [e.target_node_id for e in edges]
        else:
            edges = graph.get_incoming_edges(node_id)
            adjacent_ids = [e.source_node_id for e in edges]

        count = len(adjacent_ids)
        for idx, target_id in enumerate(adjacent_ids):
            is_last = (idx == count - 1)
            connector = " └── " if is_last else " ├── "
            child_prefix = "     " if is_last else " │   "

            edge = graph.get_edge(node_id, target_id) if direction == "outgoing" else graph.get_edge(target_id, node_id)
            constraint_str = f" [{edge.version_constraint}]" if edge and edge.version_constraint else ""

            label = _clean_node_label(target_id)
            lines.append(f"{prefix}{connector}{label}{constraint_str}")

            if target_id not in visited:
                visited.add(target_id)
                _build_tree(target_id, current_depth + 1, prefix + child_prefix, visited)

    visited_nodes = {root_node_id}
    _build_tree(root_node_id, 0, "", visited_nodes)

    return "\n".join(lines)

from typing import List, Dict, Any
try:
    import networkx as nx
except Exception:
    nx = None


def build_graph(rels: List[Dict[str, str]]):
    """Builds a directed graph from relationship list.

    rels: [{'parent':..., 'child':..., 'type':...}, ...]
    Returns networkx.DiGraph or None if networkx not installed.
    """
    if nx is None:
        return None
    G = nx.DiGraph()
    for r in rels:
        p = r.get('parent')
        c = r.get('child')
        t = r.get('type', 'contains')
        G.add_node(p)
        G.add_node(c)
        G.add_edge(p, c, relation=t)
    return G


def graph_to_json(G):
    if G is None:
        return {"error": "networkx not installed"}
    nodes = [{'id': n} for n in G.nodes()]
    edges = [{'source': u, 'target': v, **(d or {})} for u, v, d in G.edges(data=True)]
    return {'nodes': nodes, 'edges': edges}


def build_graph_json(rels: List[Dict[str, str]]):
    G = build_graph(rels)
    return graph_to_json(G)

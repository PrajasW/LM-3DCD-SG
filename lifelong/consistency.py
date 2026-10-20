"""Step 2: pairwise distance consistency between candidate matches and maximum-clique search (PCM / TEASER style)."""
import igraph as ig
import numpy as np


def _pairwise(x):
    return np.linalg.norm(x[:, None, :] - x[None, :, :], axis=-1)


def compatibility_matrix(map_graph, new_graph, cands, cfg):
    """A[a, b] is True when candidate matches a and b can both be correct for a rigid, unchanged pair of objects."""
    m = len(cands)
    if m == 0:
        return np.zeros((0, 0), dtype=bool)
    mo = [map_graph.objects[c.map_id] for c in cands]
    no = [new_graph.objects[c.new_id] for c in cands]
    cm = np.stack([o.centroid for o in mo])
    cn = np.stack([o.centroid for o in no])
    # Allow the centroid of a large object to shift when only part of it is seen.
    r = np.array([max(a.radius, b.radius) for a, b in zip(mo, no)])
    tol = cfg["dist_eps"] + cfg["radius_beta"] * (r[:, None] + r[None, :])

    A = np.abs(_pairwise(cm) - _pairwise(cn)) <= tol

    # Both visits share the floor, so height differences must agree too (rejects mirrored configurations).
    hm = np.array([o.height_center for o in mo])
    hn = np.array([o.height_center for o in no])
    if np.all(np.isfinite(hm)) and np.all(np.isfinite(hn)):
        A &= np.abs((hm[:, None] - hm[None, :]) - (hn[:, None] - hn[None, :])) <= tol

    map_ids = np.array([c.map_id for c in cands])
    new_ids = np.array([c.new_id for c in cands])
    A &= map_ids[:, None] != map_ids[None, :]   # one-to-one
    A &= new_ids[:, None] != new_ids[None, :]
    np.fill_diagonal(A, False)
    return A


def max_clique(A, costs=None, subset=None):
    """Indices of the largest clique of A (restricted to `subset`); ties broken by lowest summed cost."""
    idx = np.arange(len(A)) if subset is None else np.asarray(subset)
    if len(idx) == 0:
        return []
    sub = A[np.ix_(idx, idx)]
    rows, cols = np.nonzero(np.triu(sub, 1))
    g = ig.Graph(n=len(idx), edges=list(zip(rows.tolist(), cols.tolist())))
    cliques = g.largest_cliques()
    if costs is not None and len(cliques) > 1:
        cliques.sort(key=lambda q: sum(costs[idx[i]] for i in q))
    return sorted(int(idx[i]) for i in cliques[0])


def consistent_groups(A, cands, min_size=2):
    """Greedy sequence of maximum cliques: the first is the static set, later ones are objects that moved together."""
    costs = np.array([c.cost for c in cands])
    remaining = list(range(len(cands)))
    groups = []
    while remaining:
        q = max_clique(A, costs, remaining)
        if len(q) < (1 if not groups else min_size):
            break
        groups.append(q)
        used_map = {cands[i].map_id for i in q}
        used_new = {cands[i].new_id for i in q}
        remaining = [i for i in remaining
                     if cands[i].map_id not in used_map and cands[i].new_id not in used_new]
    return groups

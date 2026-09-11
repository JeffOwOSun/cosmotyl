"""Keep only the largest connected component of an STL (drop CSG slivers)."""
import sys
from collections import defaultdict

from stl_components import read_stl


def clean(path, out=None):
    tris = read_stl(path)
    vid, parent = {}, []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    tri_ids = []
    for tri in tris:
        ids = []
        for v in tri:
            if v not in vid:
                vid[v] = len(parent)
                parent.append(len(parent))
            ids.append(vid[v])
        union(ids[0], ids[1])
        union(ids[0], ids[2])
        tri_ids.append(ids[0])

    comps = defaultdict(list)
    for i, t in enumerate(tri_ids):
        comps[find(t)].append(i)
    keep = max(comps.values(), key=len)
    dropped = len(tris) - len(keep)
    with open(out or path, 'w') as f:
        f.write('solid clean\n')
        for i in keep:
            a, b, c = tris[i]
            f.write(' facet normal 0 0 0\n  outer loop\n')
            for v in (a, b, c):
                f.write(f'   vertex {v[0]} {v[1]} {v[2]}\n')
            f.write('  endloop\n endfacet\n')
        f.write('endsolid clean\n')
    return len(comps), dropped


if __name__ == '__main__':
    n, d = clean(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f'{n} components; dropped {d} sliver tris')

"""Find disconnected components in a binary STL (union-find on shared vertices)."""
import struct
from pathlib import Path
import sys
from collections import defaultdict


def read_stl(path):
    data = Path(path).read_bytes()
    if data[:5] == b'solid' and b'facet' in data[:200]:
        tris, cur = [], []
        for line in data.decode('ascii', 'ignore').splitlines():
            parts = line.split()
            if parts[:1] == ['vertex']:
                cur.append(tuple(round(float(p), 4) for p in parts[1:4]))
                if len(cur) == 3:
                    tris.append(cur)
                    cur = []
        return tris
    n = struct.unpack('<I', data[80:84])[0]
    tris = []
    off = 84
    for _ in range(n):
        vals = struct.unpack_from('<9f', data, off + 12)
        tris.append([tuple(round(v, 4) for v in vals[i:i + 3]) for i in (0, 3, 6)])
        off += 50
    return tris


def main(path):
    tris = read_stl(path)
    vid = {}
    parent = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    tri_root = []
    for tri in tris:
        ids = []
        for v in tri:
            if v not in vid:
                vid[v] = len(parent)
                parent.append(len(parent))
            ids.append(vid[v])
        union(ids[0], ids[1])
        union(ids[0], ids[2])
        tri_root.append(ids[0])

    comps = defaultdict(list)
    for i, t in enumerate(tri_root):
        comps[find(t)].append(i)
    print(f'{len(comps)} connected component(s)')
    for root, idxs in sorted(comps.items(), key=lambda kv: -len(kv[1])):
        xs, ys, zs = [], [], []
        for i in idxs:
            for v in tris[i]:
                xs.append(v[0]); ys.append(v[1]); zs.append(v[2])
        print(f'  tris={len(idxs):6d} bbox x[{min(xs):7.1f},{max(xs):7.1f}] '
              f'y[{min(ys):7.1f},{max(ys):7.1f}] z[{min(zs):6.1f},{max(zs):6.1f}]')


if __name__ == '__main__':
    main(sys.argv[1])

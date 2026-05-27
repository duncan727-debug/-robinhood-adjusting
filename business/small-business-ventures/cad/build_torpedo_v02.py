"""
Glidodyne torpedo v0.2 — properly hydrodynamic.
Longer body (8:1 fineness ratio), full ogive nose, swept-back fins.
Reference: Series 58 / Albacore-style body of revolution.
"""
import math
import os
import numpy as np
import trimesh

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# v0.2 — slimmer, longer, sleeker
TOTAL_LEN = 175.0
BODY_DIA = 20.0
NOSE_FRAC = 0.30   # 30% of length is the ogive nose
TAIL_FRAC = 0.25   # 25% tapers down to a smaller boat-tail
TAIL_END_DIA = 12.0
FIN_LEN = 32.0
FIN_HEIGHT = 9.0
FIN_THICK = 1.6
FIN_SWEEP_DEG = 35.0
SEG = 72


def build_body():
    """Single mesh: ogive nose + parallel midbody + boat-tail."""
    nose_len = TOTAL_LEN * NOSE_FRAC
    tail_len = TOTAL_LEN * TAIL_FRAC
    mid_len = TOTAL_LEN - nose_len - tail_len

    n_nose = 28
    n_mid = 4
    n_tail = 18
    rings = []  # list of (z, radius)

    # nose: ogive (tangent ogive curve)
    R_body = BODY_DIA / 2
    for i in range(n_nose + 1):
        t = i / n_nose
        # tangent ogive: r = R * sqrt(1 - ((1 - t))^2) — produces a clean rounded nose
        r = R_body * math.sqrt(max(0.0, 1.0 - (1.0 - t) ** 2))
        rings.append((t * nose_len, r))

    # mid: parallel
    for i in range(1, n_mid + 1):
        z = nose_len + (i / n_mid) * mid_len
        rings.append((z, R_body))

    # tail: cosine taper from R_body down to R_tail
    R_tail = TAIL_END_DIA / 2
    for i in range(1, n_tail + 1):
        t = i / n_tail
        # smooth cosine taper
        r = R_tail + (R_body - R_tail) * (math.cos(math.pi * t) + 1) / 2
        z = nose_len + mid_len + t * tail_len
        rings.append((z, r))

    verts = []
    for z, r in rings:
        for j in range(SEG):
            a = 2 * math.pi * j / SEG
            verts.append([r * math.cos(a), r * math.sin(a), z])

    faces = []
    n_rings = len(rings)
    for i in range(n_rings - 1):
        for j in range(SEG):
            a = i * SEG + j
            b = i * SEG + (j + 1) % SEG
            c = (i + 1) * SEG + j
            d = (i + 1) * SEG + (j + 1) % SEG
            faces.append([a, c, b])
            faces.append([b, c, d])

    # cap the rear with a small disk
    rear_center = len(verts)
    verts.append([0, 0, TOTAL_LEN])
    last_ring_start = (n_rings - 1) * SEG
    for j in range(SEG):
        a = last_ring_start + j
        b = last_ring_start + (j + 1) % SEG
        faces.append([a, b, rear_center])

    # cap the nose tip
    nose_tip = len(verts)
    verts.append([0, 0, 0])
    for j in range(SEG):
        a = j
        b = (j + 1) % SEG
        faces.append([nose_tip, a, b])

    return trimesh.Trimesh(vertices=verts, faces=faces, process=True)


def build_fin():
    """Swept-back fin: a thin tapered quadrilateral extrusion."""
    # base shape in XZ plane (we'll align later)
    # leading edge at z=0, trailing edge at z=FIN_LEN
    # root chord (at body) full FIN_LEN, tip chord shorter; sweep tilts tip back
    sweep_off = FIN_LEN * math.tan(math.radians(FIN_SWEEP_DEG)) * 0.35
    tip_chord = FIN_LEN * 0.55
    root_y = 0.0
    tip_y = FIN_HEIGHT

    # 4 vertices of fin in YZ plane, extruded in X
    outline = [
        [root_y, 0],
        [root_y, FIN_LEN],
        [tip_y, sweep_off + tip_chord],
        [tip_y, sweep_off],
    ]
    # extrude along X
    verts = []
    faces = []
    for x in (-FIN_THICK / 2, FIN_THICK / 2):
        for y, z in outline:
            verts.append([x, y, z])
    # two quads each split into triangles
    # bottom (x = -t/2): 0,1,2,3 ; top (x = +t/2): 4,5,6,7
    quads = [
        (0, 1, 2, 3),       # bottom face
        (7, 6, 5, 4),       # top face
        (0, 4, 5, 1),       # side
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    for a, b, c, d in quads:
        faces.append([a, b, c])
        faces.append([a, c, d])
    return trimesh.Trimesh(vertices=verts, faces=faces, process=True)


def torpedo():
    body = build_body()
    parts = [body]

    R_body = BODY_DIA / 2
    fin_z_start = TOTAL_LEN - FIN_LEN - 4
    for k in range(4):
        fin = build_fin()
        # position fin so its root is on body surface, fin extends outward in +Y
        fin.apply_translation([0, R_body - 0.5, fin_z_start])
        ang = k * math.pi / 2
        fin.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 0, 1]))
        parts.append(fin)

    m = trimesh.util.concatenate(parts)
    m.merge_vertices()
    return m


def main():
    m = torpedo()
    stl = os.path.join(OUT_DIR, "glidodyne-torpedo-v0.2.stl")
    m.export(stl)
    print(f"torpedo v0.2: faces={len(m.faces)}, bbox={m.bounding_box.extents.round(1).tolist()}")
    print(f"wrote {stl}")


if __name__ == "__main__":
    main()

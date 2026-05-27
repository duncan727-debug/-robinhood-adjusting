"""
Glidodyne torpedo projectile — foam dart sized for Concept C launcher.
~140mm long, 22mm dia body, ogive nose, 4 tail fins.
"""
import math
import os
import numpy as np
import trimesh

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

BODY_LEN = 110.0
BODY_DIA = 22.0
NOSE_LEN = 22.0
TAIL_LEN = 18.0
FIN_LEN = 26.0
FIN_HEIGHT = 10.0
FIN_THICK = 2.2
SEG = 64


def ogive_nose():
    """Tapered nose: a cone-like cylinder built by stacking discs."""
    n = 24
    verts = []
    faces = []
    for i in range(n + 1):
        t = i / n
        z = t * NOSE_LEN
        r = (BODY_DIA / 2.0) * math.sqrt(max(0.0, 1.0 - (1 - t) ** 2))
        for j in range(SEG):
            a = 2 * math.pi * j / SEG
            verts.append([r * math.cos(a), r * math.sin(a), z])
    verts.append([0, 0, NOSE_LEN])
    tip_idx = len(verts) - 1
    for i in range(n):
        for j in range(SEG):
            a = i * SEG + j
            b = i * SEG + (j + 1) % SEG
            c = (i + 1) * SEG + j
            d = (i + 1) * SEG + (j + 1) % SEG
            faces.append([a, c, b])
            faces.append([b, c, d])
    for j in range(SEG):
        a = n * SEG + j
        b = n * SEG + (j + 1) % SEG
        faces.append([a, b, tip_idx])
    m = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
    return m


def torpedo():
    body = trimesh.creation.cylinder(radius=BODY_DIA / 2, height=BODY_LEN, sections=SEG)
    body.apply_translation([0, 0, BODY_LEN / 2])

    nose = ogive_nose()
    nose.apply_translation([0, 0, BODY_LEN])

    tail = trimesh.creation.cylinder(
        radius=BODY_DIA / 2 * 0.85, height=TAIL_LEN, sections=SEG
    )
    tail.apply_translation([0, 0, -TAIL_LEN / 2])

    parts = [body, nose, tail]

    for k in range(4):
        fin = trimesh.creation.box(extents=[FIN_THICK, FIN_HEIGHT, FIN_LEN])
        fin.apply_translation([0, BODY_DIA / 2 + FIN_HEIGHT / 2 - 1, -TAIL_LEN + FIN_LEN / 2])
        ang = k * math.pi / 2
        fin.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 0, 1]))
        parts.append(fin)

    m = trimesh.util.concatenate(parts)
    m.merge_vertices()
    return m


def main():
    m = torpedo()
    stl = os.path.join(OUT_DIR, "glidodyne-torpedo-v0.1.stl")
    m.export(stl)
    print(f"torpedo: faces={len(m.faces)}, bbox={m.bounding_box.extents.round(1).tolist()}")
    print(f"wrote {stl}")


if __name__ == "__main__":
    main()

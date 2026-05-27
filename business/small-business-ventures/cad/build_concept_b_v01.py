"""
Glidodyne Concept B v0.1 — pistol-grip rifle form (preserved variant).
NOTE: This was the first interpretation; the sketch-faithful T1000 form
lives in build_concept_b_v02.py. Both are kept for reference.
"""
import math
import os
import sys
import trimesh

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

BARREL_LEN       = 320.0
BARREL_OUTER_DIA = 36.0
BARREL_INNER_DIA = 24.0
WALL             = (BARREL_OUTER_DIA - BARREL_INNER_DIA) / 2

GRIP_LEN         = 90.0
GRIP_DIA         = 26.0
GRIP_SPACING     = 130.0
GRIP_OFFSET_FROM_REAR = 70.0

REAR_CAP_LEN     = 22.0
REAR_CAP_DIA     = 40.0
MUZZLE_RING_LEN  = 14.0
MUZZLE_RING_DIA  = 42.0

SIGHT_LEN        = 18.0
SIGHT_HEIGHT     = 8.0
SIGHT_WIDTH      = 6.0

MARK_DIAMETER    = 12.0
MARK_DEPTH       = 0.6

SEG              = 96


def barrel():
    outer = trimesh.creation.cylinder(radius=BARREL_OUTER_DIA / 2, height=BARREL_LEN, sections=SEG)
    inner = trimesh.creation.cylinder(radius=BARREL_INNER_DIA / 2, height=BARREL_LEN + 2, sections=SEG)
    return outer.difference(inner)


def muzzle_ring():
    outer = trimesh.creation.cylinder(radius=MUZZLE_RING_DIA / 2, height=MUZZLE_RING_LEN, sections=SEG)
    inner = trimesh.creation.cylinder(radius=BARREL_INNER_DIA / 2, height=MUZZLE_RING_LEN + 2, sections=SEG)
    ring = outer.difference(inner)
    ring.apply_translation([0, 0, BARREL_LEN / 2 - MUZZLE_RING_LEN / 2])
    return ring


def rear_cap():
    cap = trimesh.creation.cylinder(radius=REAR_CAP_DIA / 2, height=REAR_CAP_LEN, sections=SEG)
    cap.apply_translation([0, 0, -BARREL_LEN / 2 + REAR_CAP_LEN / 2])
    mark = trimesh.creation.cylinder(radius=MARK_DIAMETER / 2, height=MARK_DEPTH * 2 + 0.5, sections=64)
    mark.apply_translation([0, 0, -BARREL_LEN / 2 - 0.1])
    return cap.difference(mark)


def grip_at(z_position):
    g = trimesh.creation.cylinder(radius=GRIP_DIA / 2, height=GRIP_LEN, sections=SEG)
    g.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    y_center = -(BARREL_OUTER_DIA / 2 + GRIP_LEN / 2 - 6)
    g.apply_translation([0, y_center, z_position])
    cap = trimesh.creation.icosphere(subdivisions=3, radius=GRIP_DIA / 2)
    cap.apply_translation([0, y_center - GRIP_LEN / 2 + 2, z_position])
    g = g.union(cap)
    block = trimesh.creation.box(extents=[GRIP_DIA, 14, GRIP_DIA * 0.95])
    block.apply_translation([0, -BARREL_OUTER_DIA / 2 + 2, z_position])
    return g.union(block)


def sight():
    s = trimesh.creation.box(extents=[SIGHT_WIDTH, SIGHT_HEIGHT, SIGHT_LEN * 6])
    s.apply_translation([0, BARREL_OUTER_DIA / 2 + SIGHT_HEIGHT / 2 - 1, 0])
    return s


def trigger_pod():
    body = trimesh.creation.box(extents=[18, 26, 36])
    z = -BARREL_LEN / 2 + GRIP_OFFSET_FROM_REAR
    y = -(BARREL_OUTER_DIA / 2 + 12)
    body.apply_translation([0, y, z + 12])
    return body


def build():
    z_rear_grip = -BARREL_LEN / 2 + GRIP_OFFSET_FROM_REAR
    z_front_grip = z_rear_grip + GRIP_SPACING
    parts = [barrel(), muzzle_ring(), rear_cap(),
             grip_at(z_rear_grip), grip_at(z_front_grip),
             sight(), trigger_pod()]
    mesh = parts[0]
    for i, p in enumerate(parts[1:], 1):
        mesh = mesh.union(p)
        print(f"  union {i}/{len(parts)-1} ok  (faces={len(mesh.faces)})", file=sys.stderr)
    return mesh


def main():
    m = build()
    m.fix_normals(); m.merge_vertices(); m.update_faces(m.unique_faces())
    stl = os.path.join(OUT_DIR, "glidodyne-concept-b-v0.1.stl")
    m.export(stl)
    print(f"wrote {stl}")


if __name__ == "__main__":
    main()

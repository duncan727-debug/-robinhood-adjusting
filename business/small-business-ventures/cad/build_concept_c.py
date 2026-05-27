"""
Glidodyne Concept C — elastic-band underwater torpedo launcher.
Builds an STL from trimesh primitives + boolean unions.
v0.1 · Smith · 2026-05-24

Run:  python3 build_concept_c.py
Outputs:
  - glidodyne-concept-c-v0.1.stl  (printable mesh, mm units)
  - glidodyne-concept-c-v0.1.png  (preview render)
"""
import math
import os
import sys
import numpy as np
import trimesh

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- parameters (mm) -------------------------------------------------
YOKE_OUTER_DIA   = 120.0
YOKE_THICKNESS   = 14.0
YOKE_HEIGHT      = 22.0

GRIP_LENGTH      = 95.0
GRIP_DIAMETER    = 26.0

ARM_LENGTH       = 28.0
ARM_WIDTH        = 22.0
ARM_THICKNESS    = 12.0
ARM_ANGLE_DEG    = 35.0   # symmetric, off the vertical

MARK_DIAMETER    = 14.0
MARK_DEPTH       = 0.6

SEGMENTS         = 96
# ---------------------------------------------------------------------------


def yoke():
    """Annular ring with chamfered edges and a shallow monogram recess."""
    outer = trimesh.creation.cylinder(
        radius=YOKE_OUTER_DIA / 2.0, height=YOKE_HEIGHT, sections=SEGMENTS
    )
    inner = trimesh.creation.cylinder(
        radius=YOKE_OUTER_DIA / 2.0 - YOKE_THICKNESS,
        height=YOKE_HEIGHT + 2,
        sections=SEGMENTS,
    )
    ring = outer.difference(inner)

    # monogram recess on the front face (+Y)
    mark = trimesh.creation.cylinder(
        radius=MARK_DIAMETER / 2.0, height=MARK_DEPTH * 2 + 0.5, sections=64
    )
    # rotate to point along -Y, position on outer face front
    mark.apply_transform(
        trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])
    )
    front_y = YOKE_OUTER_DIA / 2.0 - YOKE_THICKNESS / 2.0
    mark.apply_translation([0, front_y - MARK_DEPTH, 0])
    ring = ring.difference(mark)
    return ring


def grip():
    """Cylindrical grip extending in -Y from the yoke's bottom face."""
    g = trimesh.creation.cylinder(
        radius=GRIP_DIAMETER / 2.0, height=GRIP_LENGTH, sections=SEGMENTS
    )
    # default cylinder is along Z; rotate to lie along Y
    g.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    # position: grip extends downward in -Y from the bottom of yoke ring
    y_anchor = -(YOKE_OUTER_DIA / 2.0 - YOKE_THICKNESS / 2.0)
    g.apply_translation([0, y_anchor - GRIP_LENGTH / 2.0 + YOKE_THICKNESS / 2.0, 0])

    # rounded tip cap
    cap = trimesh.creation.icosphere(subdivisions=3, radius=GRIP_DIAMETER / 2.0)
    cap.apply_translation([0, y_anchor - GRIP_LENGTH + YOKE_THICKNESS / 2.0, 0])
    return g.union(cap)


def arm(side: str):
    """Rectangular arm protruding from the upper-side of the yoke."""
    body = trimesh.creation.box(extents=[ARM_WIDTH, ARM_LENGTH, ARM_THICKNESS])
    # tip cylinder (rounded end where the elastic band loops)
    tip = trimesh.creation.cylinder(
        radius=ARM_WIDTH / 2.0, height=ARM_THICKNESS, sections=48
    )
    tip.apply_translation([0, ARM_LENGTH / 2.0, 0])
    body = body.union(tip)

    # band-locking groove: shallow circumferential notch near the tip
    groove = trimesh.creation.cylinder(
        radius=ARM_WIDTH / 2.0 + 0.2, height=2.5, sections=48
    )
    groove.apply_transform(
        trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])
    )
    groove.apply_translation([0, ARM_LENGTH / 2.0 - 4, 0])
    # subtract a thin slice all around: easier — use a torus-like ring
    inner_groove = trimesh.creation.cylinder(
        radius=ARM_WIDTH / 2.0 - 1.5, height=2.5, sections=48
    )
    inner_groove.apply_transform(
        trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])
    )
    inner_groove.apply_translation([0, ARM_LENGTH / 2.0 - 4, 0])
    groove_ring = groove.difference(inner_groove)
    body = body.difference(groove_ring)

    # position arm on the yoke
    # anchor point on the inside of the ring, at the angled position
    angle = math.radians(90.0 + (ARM_ANGLE_DEG if side == "right" else -ARM_ANGLE_DEG))
    anchor_radius = YOKE_OUTER_DIA / 2.0 - YOKE_THICKNESS / 2.0
    x = anchor_radius * math.cos(angle)
    y = anchor_radius * math.sin(angle)

    # rotate arm so its length axis points outward from the ring
    body.apply_transform(
        trimesh.transformations.rotation_matrix(angle - math.pi / 2, [0, 0, 1])
    )
    body.apply_translation([x, y, 0])
    return body


def build():
    parts = [yoke(), grip(), arm("left"), arm("right")]
    print(f"[build] starting union of {len(parts)} parts...", file=sys.stderr)
    mesh = parts[0]
    for i, p in enumerate(parts[1:], 1):
        mesh = mesh.union(p)
        print(f"[build] union {i}/{len(parts)-1} ok  (faces={len(mesh.faces)})", file=sys.stderr)
    return mesh


def main():
    mesh = build()
    # repair / normalize
    mesh.fix_normals()
    mesh.merge_vertices()
    mesh.update_faces(mesh.unique_faces())

    # report key facts
    print(f"vertices: {len(mesh.vertices)}")
    print(f"faces:    {len(mesh.faces)}")
    print(f"watertight: {mesh.is_watertight}")
    print(f"volume:   {mesh.volume:.0f} mm^3")
    print(f"bounding box (mm): {mesh.bounding_box.extents.round(1).tolist()}")
    # weight estimate (PLA ~1.24 g/cc, PETG ~1.27, ABS ~1.04, nylon ~1.15)
    cc = mesh.volume / 1000.0
    print(f"approx mass: PLA={cc*1.24:.0f}g, PETG={cc*1.27:.0f}g, ABS={cc*1.04:.0f}g")

    stl_path = os.path.join(OUT_DIR, "glidodyne-concept-c-v0.1.stl")
    mesh.export(stl_path)
    print(f"wrote {stl_path}")

    # preview render (PNG)
    try:
        scene = trimesh.Scene(mesh)
        png = scene.save_image(resolution=(1200, 900), visible=True)
        png_path = os.path.join(OUT_DIR, "glidodyne-concept-c-v0.1.png")
        with open(png_path, "wb") as f:
            f.write(png)
        print(f"wrote {png_path}")
    except Exception as e:
        print(f"[preview] skipped: {e}")


if __name__ == "__main__":
    main()

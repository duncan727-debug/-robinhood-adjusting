"""
Glidodyne Concept B — two-hand tube launcher (v0.2, matches original sketch).
Braun T1000 / flashlight form factor:
  - long horizontal charcoal cylinder
  - top-mounted pump handle (slides up/down to cock the internal bands)
  - palm 'FIRE' trigger at the rear cap (large round orange button)
  - amber pressure-status window on the side
  - two-hand operation: one hand grips body, other operates pump then trigger
"""
import math
import os
import sys
import trimesh

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# main tube
BARREL_LEN       = 340.0
BARREL_OUTER_DIA = 48.0
BARREL_INNER_DIA = 26.0   # accepts Ø20mm torpedo
SEG              = 96

# muzzle ring (front face, slight flare)
MUZZLE_RING_LEN  = 12.0
MUZZLE_RING_DIA  = 54.0

# rear cap — slightly larger disc that holds the palm trigger
REAR_CAP_LEN     = 24.0
REAR_CAP_DIA     = 56.0

# palm fire trigger button (recessed into rear cap)
TRIGGER_DIA      = 28.0
TRIGGER_DEPTH    = 4.0    # sits flush; cosmetic only — modeled as raised disc
TRIGGER_PROUD    = 2.5    # how much it stands proud of the rear face

# top pump handle (slides along upper rail)
PUMP_LEN         = 110.0
PUMP_WIDTH       = 34.0
PUMP_HEIGHT      = 14.0
PUMP_RAIL_LEN    = 180.0
PUMP_RAIL_WIDTH  = 22.0
PUMP_RAIL_HEIGHT = 6.0
PUMP_CONNECTOR_DIA = 12.0
PUMP_CONNECTOR_LEN = 16.0

# pressure window (side strip, amber)
WINDOW_LEN       = 60.0
WINDOW_HEIGHT    = 10.0
WINDOW_DEPTH     = 1.2   # recess depth for color-fill / printed insert
WINDOW_OFFSET_FROM_REAR = 95.0  # distance from rear cap

# brand monogram recess (single etched G on side, opposite from window)
MARK_DIAMETER    = 10.0
MARK_DEPTH       = 0.5
MARK_OFFSET_FROM_FRONT = 80.0


def barrel():
    outer = trimesh.creation.cylinder(radius=BARREL_OUTER_DIA / 2, height=BARREL_LEN, sections=SEG)
    inner = trimesh.creation.cylinder(radius=BARREL_INNER_DIA / 2, height=BARREL_LEN + 2, sections=SEG)
    tube = outer.difference(inner)
    return tube  # along Z, centered at origin


def muzzle_ring():
    outer = trimesh.creation.cylinder(radius=MUZZLE_RING_DIA / 2, height=MUZZLE_RING_LEN, sections=SEG)
    inner = trimesh.creation.cylinder(radius=BARREL_INNER_DIA / 2, height=MUZZLE_RING_LEN + 2, sections=SEG)
    ring = outer.difference(inner)
    ring.apply_translation([0, 0, BARREL_LEN / 2 + MUZZLE_RING_LEN / 2 - 2])
    return ring


def rear_cap_with_trigger():
    """Solid disc at rear face with a raised palm-trigger button in the center."""
    cap = trimesh.creation.cylinder(radius=REAR_CAP_DIA / 2, height=REAR_CAP_LEN, sections=SEG)
    cap.apply_translation([0, 0, -BARREL_LEN / 2 - REAR_CAP_LEN / 2 + 2])

    # palm trigger: a raised disc proud of the rear face
    trigger = trimesh.creation.cylinder(radius=TRIGGER_DIA / 2, height=TRIGGER_PROUD + 4, sections=64)
    trigger_z = -BARREL_LEN / 2 - REAR_CAP_LEN - TRIGGER_PROUD / 2
    trigger.apply_translation([0, 0, trigger_z])
    cap = cap.union(trigger)
    return cap


def pump_rail():
    """Low rail block on top of barrel that the pump handle slides along."""
    rail = trimesh.creation.box(extents=[PUMP_RAIL_WIDTH, PUMP_RAIL_HEIGHT, PUMP_RAIL_LEN])
    # position on top of barrel (+Y), centered along barrel
    rail.apply_translation([0, BARREL_OUTER_DIA / 2 + PUMP_RAIL_HEIGHT / 2 - 0.5, 0])
    return rail


def pump_handle():
    """The actual pump grip on top, with a connector post going into the rail."""
    handle = trimesh.creation.box(extents=[PUMP_WIDTH, PUMP_HEIGHT, PUMP_LEN])
    # ride above the rail
    y = BARREL_OUTER_DIA / 2 + PUMP_RAIL_HEIGHT + PUMP_CONNECTOR_LEN + PUMP_HEIGHT / 2 - 0.5
    handle.apply_translation([0, y, 0])
    # round the ends with cylinders
    for z_off in (-PUMP_LEN / 2, PUMP_LEN / 2):
        cap = trimesh.creation.cylinder(
            radius=PUMP_HEIGHT / 2, height=PUMP_WIDTH, sections=48
        )
        cap.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        cap.apply_translation([0, y, z_off])
        handle = handle.union(cap)

    # connector post(s) — two short cylinders linking handle to rail
    for z_off in (-PUMP_LEN / 3, PUMP_LEN / 3):
        post = trimesh.creation.cylinder(
            radius=PUMP_CONNECTOR_DIA / 2, height=PUMP_CONNECTOR_LEN + 4, sections=24
        )
        post_y = BARREL_OUTER_DIA / 2 + PUMP_RAIL_HEIGHT + PUMP_CONNECTOR_LEN / 2
        post.apply_translation([0, post_y, z_off])
        handle = handle.union(post)
    return handle


def pressure_window_recess():
    """Shallow rectangular recess on the side of the barrel for the amber strip."""
    box = trimesh.creation.box(extents=[WINDOW_DEPTH * 2 + 1, WINDOW_HEIGHT, WINDOW_LEN])
    # position on +X side of barrel, centered Z = rear-ish
    x = BARREL_OUTER_DIA / 2 - WINDOW_DEPTH / 2
    z = -BARREL_LEN / 2 + WINDOW_OFFSET_FROM_REAR + WINDOW_LEN / 2
    box.apply_translation([x, 0, z])
    return box


def monogram_recess():
    """Shallow round recess for the laser-etched G."""
    cyl = trimesh.creation.cylinder(radius=MARK_DIAMETER / 2, height=MARK_DEPTH * 2 + 1, sections=64)
    cyl.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    x = -BARREL_OUTER_DIA / 2 + MARK_DEPTH / 2
    z = BARREL_LEN / 2 - MARK_OFFSET_FROM_FRONT
    cyl.apply_translation([x, 0, z])
    return cyl


def build():
    print("[build B v0.2] additive parts...", file=sys.stderr)
    mesh = barrel()
    for p in (muzzle_ring(), rear_cap_with_trigger(), pump_rail(), pump_handle()):
        mesh = mesh.union(p)
        print(f"  union ok  (faces={len(mesh.faces)})", file=sys.stderr)

    print("[build B v0.2] subtractive details...", file=sys.stderr)
    for r in (pressure_window_recess(), monogram_recess()):
        mesh = mesh.difference(r)
        print(f"  diff ok  (faces={len(mesh.faces)})", file=sys.stderr)
    return mesh


def main():
    m = build()
    m.fix_normals()
    m.merge_vertices()
    m.update_faces(m.unique_faces())

    print(f"vertices: {len(m.vertices)}")
    print(f"faces:    {len(m.faces)}")
    print(f"watertight: {m.is_watertight}")
    print(f"volume:   {m.volume:.0f} mm^3")
    print(f"bounding box: {m.bounding_box.extents.round(1).tolist()}")
    cc = m.volume / 1000.0
    print(f"approx mass: PLA={cc*1.24:.0f}g, PETG={cc*1.27:.0f}g, ABS={cc*1.04:.0f}g")

    stl = os.path.join(OUT_DIR, "glidodyne-concept-b-v0.2.stl")
    m.export(stl)
    print(f"wrote {stl}")


if __name__ == "__main__":
    main()

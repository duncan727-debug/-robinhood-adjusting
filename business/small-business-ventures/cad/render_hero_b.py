"""Hero render: Glidodyne Concept B v0.2 (T1000-style tube) + torpedoes v0.2.

Colors faces by centroid region to match the original sketch:
  - barrel + rear cap            charcoal
  - muzzle ring + pump handle    warm white
  - palm trigger (rear button)   signal orange
  - pressure-window recess       amber
"""
import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

OUT = os.path.dirname(os.path.abspath(__file__))
LAUNCHER_STL = os.path.join(OUT, "glidodyne-concept-b-v0.2.stl")
TORPEDO_STL = os.path.join(OUT, "glidodyne-torpedo-v0.2.stl")

WARM_WHITE = np.array([245, 243, 239]) / 255
INK = np.array([29, 29, 31]) / 255
ORANGE = np.array([255, 122, 48]) / 255
CHARCOAL = np.array([58, 58, 60]) / 255
AMBER = np.array([232, 168, 56]) / 255

LIGHT = np.array([0.35, 0.55, 0.85]); LIGHT /= np.linalg.norm(LIGHT)

# launcher geometry constants (match build_concept_b.py v0.2)
BARREL_LEN = 340.0
BARREL_OUTER_DIA = 48.0
WINDOW_LEN = 60.0
WINDOW_HEIGHT = 10.0
WINDOW_OFFSET_FROM_REAR = 95.0

# z extents to classify
Z_MUZZLE_FACE   = BARREL_LEN / 2 - 2     # muzzle ring starts here
Z_REAR_FACE     = -BARREL_LEN / 2        # rear cap starts here
Z_TRIGGER_FACE  = -BARREL_LEN / 2 - 26   # palm trigger sits past rear cap
Y_PUMP_BOTTOM   = BARREL_OUTER_DIA / 2 + 5  # anything above is pump rail/handle
WINDOW_Z_LO = -BARREL_LEN / 2 + WINDOW_OFFSET_FROM_REAR
WINDOW_Z_HI = WINDOW_Z_LO + WINDOW_LEN


def classify_faces(m):
    """Return per-face color array based on face centroid position."""
    fv = m.vertices[m.faces]
    centroids = fv.mean(axis=1)
    x = centroids[:, 0]; y = centroids[:, 1]; z = centroids[:, 2]

    colors = np.tile(CHARCOAL, (len(m.faces), 1))

    # pump rail + pump handle: anything above Y_PUMP_BOTTOM
    pump_mask = y > Y_PUMP_BOTTOM
    colors[pump_mask] = WARM_WHITE

    # muzzle ring: anything z > Z_MUZZLE_FACE
    muzzle_mask = z > Z_MUZZLE_FACE
    colors[muzzle_mask] = WARM_WHITE

    # palm trigger: z < Z_TRIGGER_FACE (past rear cap)
    trigger_mask = z < Z_TRIGGER_FACE
    colors[trigger_mask] = ORANGE

    # pressure window recess: side face (x > 0) within window z-range
    win_mask = (x > BARREL_OUTER_DIA / 2 - 3) & (z > WINDOW_Z_LO) & (z < WINDOW_Z_HI) & (np.abs(y) < WINDOW_HEIGHT)
    colors[win_mask] = AMBER

    return colors


def shaded(mesh, face_colors=None, fallback=WARM_WHITE, edge_alpha=0.08):
    fv = mesh.vertices[mesh.faces]
    n = np.cross(fv[:, 1] - fv[:, 0], fv[:, 2] - fv[:, 0])
    nn = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.where(nn > 0, nn, 1)
    sh = np.clip(n @ LIGHT, 0.30, 1.0)
    if face_colors is None:
        face_colors = np.tile(fallback, (len(mesh.faces), 1))
    colors = face_colors * sh[:, None]
    colors = np.clip(colors, 0, 1)
    return Poly3DCollection(
        fv, facecolors=colors,
        edgecolors=(0.05, 0.05, 0.05, edge_alpha), linewidths=0.12,
    )


NOSE_LEN = 175.0 * 0.30
def split_nose(m):
    fv_z = m.vertices[m.faces][:, :, 2]
    is_tip = fv_z.max(axis=1) <= NOSE_LEN + 0.1
    return (
        trimesh.Trimesh(vertices=m.vertices.copy(), faces=m.faces[~is_tip], process=False),
        trimesh.Trimesh(vertices=m.vertices.copy(), faces=m.faces[is_tip], process=False),
    )


def torpedo_at(x, y, z, nose_forward_z=True):
    base = trimesh.load(TORPEDO_STL)
    body, nose = split_nose(base)
    for part in (body, nose):
        # flip 180° around Y so nose ends up at high z (pointing +Z = forward)
        part.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [0, 1, 0]))
        part.apply_translation([0, 0, 175.0])
        part.apply_translation([x, y, z])
    return body, nose


def main():
    launcher = trimesh.load(LAUNCHER_STL)
    launcher_colors = classify_faces(launcher)

    # three torpedoes: one in-flight just past muzzle, two staged below
    t1 = torpedo_at(0, 0, 200)     # in-flight from muzzle
    t2 = torpedo_at(0, -75, -50)   # staged below
    t3 = torpedo_at(0, -110, 80)   # staged below-front

    torpedoes = [t1, t2, t3]

    fig = plt.figure(figsize=(16, 10), facecolor=WARM_WHITE)
    fig.suptitle(
        "Glidodyne · Concept B · v0.2   |   T1000-form tube · top pump · palm-trigger · hydrodynamic torpedo",
        fontsize=13, color=INK, y=0.96, weight="medium",
    )

    def view(ax, elev, azim, title):
        ax.set_facecolor(WARM_WHITE)
        ax.add_collection3d(shaded(launcher, face_colors=launcher_colors, edge_alpha=0.10))
        for body, nose in torpedoes:
            body_colors = np.tile(CHARCOAL, (len(body.faces), 1))
            nose_colors = np.tile(ORANGE, (len(nose.faces), 1))
            ax.add_collection3d(shaded(body, face_colors=body_colors, edge_alpha=0.12))
            ax.add_collection3d(shaded(nose, face_colors=nose_colors, edge_alpha=0.04))

        pts = [launcher.vertices]
        for b, n in torpedoes:
            pts.append(b.vertices); pts.append(n.vertices)
        pts = np.vstack(pts)
        mn, mx = pts.min(axis=0), pts.max(axis=0)
        ctr = (mn + mx) / 2
        half = (mx - mn).max() / 2 * 1.05
        ax.set_xlim(ctr[0] - half, ctr[0] + half)
        ax.set_ylim(ctr[1] - half, ctr[1] + half)
        ax.set_zlim(ctr[2] - half, ctr[2] + half)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(title, fontsize=11, color=INK, pad=4)
        ax.set_axis_off()
        for p in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
            p.set_facecolor(WARM_WHITE); p.set_edgecolor(WARM_WHITE)

    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    view(ax1, 18, -70, "hero · firing line")

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    view(ax2, 12, 75, "opposite side · window visible")

    fig.text(
        0.5, 0.04,
        "Launcher: 378 × 87 × 56 mm  ·  charcoal body / warm-white pump + muzzle / orange palm-trigger     |     "
        "Torpedo v0.2: Ø20 × 175 mm  ·  8.75:1 fineness  ·  tangent ogive · swept fins",
        ha="center", fontsize=9.5, color="#6e6e73", family="monospace",
    )
    fig.text(
        0.5, 0.015,
        "concept B  ·  T1000-form  ·  side-pump action  ·  rear palm trigger  ·  amber pressure window  ·  Glidodyne / Magadu LLC  ·  2026",
        ha="center", fontsize=8, color="#a1a1a6",
    )

    out = os.path.join(OUT, "glidodyne-concept-b-hero-v0.2.png")
    fig.savefig(out, dpi=160, facecolor=WARM_WHITE, bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

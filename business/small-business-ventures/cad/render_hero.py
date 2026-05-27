"""Hero render: Glidodyne Concept C + 3 torpedoes in brand palette."""
import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

OUT = os.path.dirname(os.path.abspath(__file__))
LAUNCHER_STL = os.path.join(OUT, "glidodyne-concept-c-v0.1.stl")
TORPEDO_STL = os.path.join(OUT, "glidodyne-torpedo-v0.1.stl")

# brand palette
WARM_WHITE = np.array([245, 243, 239]) / 255
INK = np.array([29, 29, 31]) / 255
ORANGE = np.array([255, 122, 48]) / 255
CHARCOAL = np.array([58, 58, 60]) / 255

LIGHT = np.array([0.35, -0.4, 0.85])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def shaded_collection(mesh, base_color, edge_alpha=0.10):
    fv = mesh.vertices[mesh.faces]
    n = np.cross(fv[:, 1] - fv[:, 0], fv[:, 2] - fv[:, 0])
    nn = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.where(nn > 0, nn, 1)
    sh = np.clip(n @ LIGHT, 0.30, 1.0)
    colors = np.outer(sh, base_color)
    colors = np.clip(colors, 0, 1)
    return Poly3DCollection(
        fv,
        facecolors=colors,
        edgecolors=(0.1, 0.1, 0.1, edge_alpha),
        linewidths=0.15,
    )


def load_launcher():
    m = trimesh.load(LAUNCHER_STL)
    # center on origin
    c = (m.bounds[0] + m.bounds[1]) / 2
    m.apply_translation(-c)
    return m


def load_torpedo():
    m = trimesh.load(TORPEDO_STL)
    return m


def torpedo_with_orange_tip(position, rot_z_deg=0):
    """Return (body_mesh, tip_mesh) — tip will be rendered in orange."""
    m = load_torpedo()
    # split: nose vs body — flag faces with all vertices z > BODY_LEN
    BODY_LEN = 110.0
    fv_z = m.vertices[m.faces][:, :, 2]
    is_tip = (fv_z.min(axis=1) >= BODY_LEN - 0.1)
    tip_faces = m.faces[is_tip]
    body_faces = m.faces[~is_tip]

    body = trimesh.Trimesh(vertices=m.vertices.copy(), faces=body_faces, process=False)
    tip = trimesh.Trimesh(vertices=m.vertices.copy(), faces=tip_faces, process=False)

    for part in (body, tip):
        if rot_z_deg:
            part.apply_transform(
                trimesh.transformations.rotation_matrix(
                    math.radians(rot_z_deg), [0, 0, 1]
                )
            )
        part.apply_translation(position)
    return body, tip


def render_view(ax, launcher, torpedoes, elev, azim, title):
    ax.set_facecolor(WARM_WHITE)
    ax.add_collection3d(shaded_collection(launcher, WARM_WHITE))
    for body, tip in torpedoes:
        ax.add_collection3d(shaded_collection(body, CHARCOAL, edge_alpha=0.18))
        ax.add_collection3d(shaded_collection(tip, ORANGE, edge_alpha=0.05))

    # combined bounds
    all_pts = [launcher.vertices]
    for body, tip in torpedoes:
        all_pts.append(body.vertices)
        all_pts.append(tip.vertices)
    pts = np.vstack(all_pts)
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
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor(WARM_WHITE)
        pane.set_edgecolor(WARM_WHITE)


def main():
    launcher = load_launcher()

    # launcher is in XY plane in its native frame after centering.
    # arrange three torpedoes: one loaded in the yoke + two beside.
    # torpedo native: long axis along Z. We want them lying in the launcher's plane.
    # rotate torpedo so its long axis is along Y, sitting in launcher plane.

    def laid_torpedo(offset_x=0, offset_y=0, offset_z=0):
        m = load_torpedo()
        # rotate -90 deg around X so its +Z (nose) points +Y
        m.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
        # split tip vs body in new frame: nose now at +Y
        fv_y = m.vertices[m.faces][:, :, 1]
        is_tip = (fv_y.min(axis=1) >= 110.0 - 0.1)
        body = trimesh.Trimesh(vertices=m.vertices.copy(), faces=m.faces[~is_tip], process=False)
        tip = trimesh.Trimesh(vertices=m.vertices.copy(), faces=m.faces[is_tip], process=False)
        for part in (body, tip):
            part.apply_translation([offset_x, offset_y, offset_z])
        return body, tip

    # one loaded through the yoke (centered on launcher's ring center)
    # launcher center post-translate: ring center is roughly at y = +75 (yoke offset)
    # Easier: just place torpedoes relative to launcher bounds
    lb = launcher.bounds
    ring_cx = 0
    ring_cy = (lb[0][1] + lb[1][1]) / 2 + 60  # roughly the ring center
    z_mid = 0

    loaded = laid_torpedo(offset_x=ring_cx, offset_y=ring_cy - 55, offset_z=z_mid)
    side1 = laid_torpedo(offset_x=ring_cx - 90, offset_y=ring_cy - 55, offset_z=z_mid - 30)
    side2 = laid_torpedo(offset_x=ring_cx + 90, offset_y=ring_cy - 55, offset_z=z_mid - 30)

    torpedoes = [loaded, side1, side2]

    fig = plt.figure(figsize=(15, 10), facecolor=WARM_WHITE)
    fig.suptitle(
        "Glidodyne · The Launcher · v0.1   |   prototype + projectile system",
        fontsize=15, color=INK, y=0.96, weight="medium",
    )

    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    render_view(ax1, launcher, torpedoes, elev=28, azim=42, title="hero")

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    render_view(ax2, launcher, torpedoes, elev=82, azim=-90, title="top")

    fig.text(
        0.5, 0.04,
        "Launcher: 120 × 220 × 26 mm  ·  PLA ~200 g     |     "
        "Torpedo: Ø22 × 150 mm  ·  closed-cell foam, replaceable",
        ha="center", fontsize=10, color="#6e6e73", family="monospace",
    )
    fig.text(
        0.5, 0.015,
        "concept C  ·  elastic-band launcher  ·  Glidodyne / Magadu LLC  ·  2026",
        ha="center", fontsize=8.5, color="#a1a1a6",
    )

    out = os.path.join(OUT, "glidodyne-hero-v0.1.png")
    fig.savefig(out, dpi=160, facecolor=WARM_WHITE, bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

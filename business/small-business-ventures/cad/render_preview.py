"""Headless preview render of the Concept C STL using matplotlib.
Produces 4 views: ISO, top, side, front."""
import os
import sys
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

OUT = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(OUT, "glidodyne-concept-c-v0.1.stl")

mesh = trimesh.load(STL)
print(f"loaded {STL}: {len(mesh.faces)} faces")

# four views: (elev, azim, label)
views = [
    (25, 35, "isometric"),
    (90, -90, "top"),
    (0, -90, "front"),
    (0, 0, "side"),
]

fig = plt.figure(figsize=(14, 12), facecolor="#f5f3ef")
fig.suptitle(
    "Glidodyne · Concept C · v0.1   |   elastic-band underwater torpedo launcher",
    fontsize=14,
    color="#1d1d1f",
    y=0.97,
)

verts = mesh.vertices
faces = mesh.faces

# compute face normals to vary shading
face_verts = verts[faces]
v0 = face_verts[:, 1] - face_verts[:, 0]
v1 = face_verts[:, 2] - face_verts[:, 0]
normals = np.cross(v0, v1)
norms = np.linalg.norm(normals, axis=1, keepdims=True)
normals = normals / np.where(norms > 0, norms, 1)
light_dir = np.array([0.4, -0.4, 0.8])
light_dir = light_dir / np.linalg.norm(light_dir)
shading = np.clip(normals @ light_dir, 0.25, 1.0)

# build face color array (warm white modulated by shading)
base = np.array([245 / 255, 243 / 255, 239 / 255])  # warm white
face_colors = np.outer(shading, base) + 0.0
face_colors = np.clip(face_colors, 0, 1)

# bounds
mn = verts.min(axis=0)
mx = verts.max(axis=0)
span = mx - mn
ctr = (mn + mx) / 2.0
half = span.max() / 2 * 1.05

for i, (elev, azim, label) in enumerate(views):
    ax = fig.add_subplot(2, 2, i + 1, projection="3d")
    ax.set_facecolor("#f5f3ef")
    coll = Poly3DCollection(
        verts[faces],
        facecolors=face_colors,
        edgecolors=(0.1, 0.1, 0.1, 0.15),
        linewidths=0.2,
    )
    ax.add_collection3d(coll)
    ax.set_xlim(ctr[0] - half, ctr[0] + half)
    ax.set_ylim(ctr[1] - half, ctr[1] + half)
    ax.set_zlim(ctr[2] - half, ctr[2] + half)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(label, fontsize=11, color="#1d1d1f", pad=4)
    ax.set_xlabel("X (mm)", fontsize=8, color="#6e6e73")
    ax.set_ylabel("Y (mm)", fontsize=8, color="#6e6e73")
    ax.set_zlabel("Z (mm)", fontsize=8, color="#6e6e73")
    ax.tick_params(labelsize=7, colors="#6e6e73")
    ax.grid(True, alpha=0.15)
    # tighter pane backgrounds
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor("#fafafa")
        pane.set_edgecolor("#d0d0d0")

# specs block
specs = (
    f"Volume: {mesh.volume/1000:.1f} cc   |   "
    f"Bounding box: {span[0]:.0f} × {span[1]:.0f} × {span[2]:.0f} mm   |   "
    f"Approx mass (PLA): {mesh.volume/1000*1.24:.0f} g   |   "
    f"Faces: {len(mesh.faces)}   |   "
    f"Watertight: {mesh.is_watertight}"
)
fig.text(0.5, 0.02, specs, ha="center", fontsize=9, color="#6e6e73", family="monospace")

png = os.path.join(OUT, "glidodyne-concept-c-v0.1.png")
fig.savefig(png, dpi=140, facecolor="#f5f3ef", bbox_inches="tight")
print(f"wrote {png}")

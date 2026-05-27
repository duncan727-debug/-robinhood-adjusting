// =============================================================================
// Glidodyne Concept C — Elastic-band underwater torpedo launcher
// Parametric OpenSCAD model · v0.1 · Smith · 2026-05-24
// =============================================================================
//
// Design intent (per torpedo-launcher-90-day-plan.md):
//   - Cheapest of the three concepts (no pressure system, no patent risk)
//   - One-piece printable body in HDPE / PLA / PETG for MVP test
//   - Off-the-shelf food-safe silicone bands (replaceable consumable)
//   - Generic torpedo cradle — accepts SwimWays-style foam torpedo for MVP
//   - Sized for a 7-12 year old grip
//   - Visual language: Braun/Apple geometric clarity, no tactical styling
//
// Print orientation: lay flat on print bed, grip pointing toward operator,
// yoke ring extending away. Negligible support needed.
//
// Total dry weight target: 220-260 g (PLA) / 240-300 g (PETG)
// Print time estimate (FDM, 0.2mm layer): 6-9 hours

// ============= PARAMETERS =====================================================

// Overall dimensions
yoke_outer_dia    = 120;  // mm — main ring outer diameter
yoke_thickness    = 14;   // mm — ring cross-section
yoke_height       = 22;   // mm — Z-axis depth of the ring body
grip_length       = 95;   // mm — handle extension below the yoke
grip_diameter     = 26;   // mm — kid-friendly grip thickness
grip_taper        = 1.05; // narrowing toward base for grip-shaping

// Arm extensions (where elastic bands anchor)
arm_length        = 28;   // mm — protrudes from yoke outer edge
arm_thickness     = 12;   // mm
arm_width         = 22;   // mm

// Band anchor groove
groove_dia        = 6;    // mm — diameter of band-locking groove
groove_inset      = 8;    // mm — distance from arm tip

// Brand monogram recess (single G, laser-etched feel)
mark_diameter     = 14;   // mm
mark_depth        = 0.6;  // mm — shallow embossed recess for paint-fill or laser

// Print/tolerance allowances
$fn               = 96;   // smooth curves
wall_min          = 3.0;  // minimum wall thickness anywhere
chamfer           = 1.2;  // soft edge radius on all visible surfaces

// ============= MAIN ASSEMBLY ==================================================

module glidodyne_concept_c() {
    union() {
        yoke();
        grip();
        arms_pair();
    }
}

// ============= YOKE (main ring) ==============================================

module yoke() {
    difference() {
        // outer ring volume
        linear_extrude(yoke_height)
            difference() {
                circle(d = yoke_outer_dia);
                circle(d = yoke_outer_dia - 2 * yoke_thickness);
            }
        // top edge chamfer
        translate([0, 0, yoke_height - chamfer])
            rotate_extrude()
                translate([yoke_outer_dia/2 - chamfer, 0])
                    polygon([[0,0],[chamfer,0],[chamfer,chamfer]]);
        // bottom edge chamfer
        translate([0, 0, 0])
            rotate_extrude()
                translate([yoke_outer_dia/2 - chamfer, 0])
                    polygon([[0,0],[chamfer,0],[chamfer,-chamfer]]);
        // monogram recess on front face
        translate([0, yoke_outer_dia/2 - yoke_thickness - mark_diameter/2 - 4, yoke_height/2])
            rotate([90, 0, 0])
                cylinder(d = mark_diameter, h = mark_depth * 2, center = true);
    }
}

// ============= GRIP (handle) =================================================

module grip() {
    grip_base_z = -grip_length;
    hull() {
        // grip top joins yoke smoothly
        translate([0, -yoke_outer_dia/2 + yoke_thickness/2, yoke_height/2])
            rotate([90, 0, 0])
                cylinder(d = grip_diameter * 0.95, h = 1, center = true);
        // grip body
        translate([0, -yoke_outer_dia/2 - 10, yoke_height/2])
            rotate([90, 0, 0])
                cylinder(d = grip_diameter, h = 1, center = true);
        // grip tip (slight taper)
        translate([0, -yoke_outer_dia/2 - grip_length, yoke_height/2])
            rotate([90, 0, 0])
                cylinder(d = grip_diameter / grip_taper, h = 1, center = true);
    }
}

// ============= ARMS (elastic-band anchors) ===================================

module arm(side) {
    angle = side == "left" ? 90 + 35 : 90 - 35;
    anchor_x = (yoke_outer_dia/2 - yoke_thickness/2) * cos(angle);
    anchor_y = (yoke_outer_dia/2 - yoke_thickness/2) * sin(angle);

    translate([anchor_x, anchor_y, yoke_height/2])
        rotate([0, 0, angle - 90])
            arm_body();
}

module arm_body() {
    union() {
        // arm shaft
        translate([0, 0, 0])
            cube([arm_width, arm_length, arm_thickness], center = true);
        // tip cap
        translate([0, arm_length/2 - 1, 0])
            cylinder(d = arm_width, h = arm_thickness, center = true);
        // band-locking groove (subtracted later by a difference if printed solid;
        // for v0.1 we annotate via a recess on the outside)
    }
}

module arms_pair() {
    arm("left");
    arm("right");
}

// ============= INVOCATION ====================================================

glidodyne_concept_c();

// =============================================================================
// END OF MODEL
//
// To export STL from this file:
//   openscad -o glidodyne-concept-c-v0.1.stl glidodyne-concept-c-v0.1.scad
//
// Estimated print cost (Craftcloud / Hubs / JLCPCB 3D, 2026):
//   PLA, 0.2mm layer, 20% infill, single unit  ~$18-32
//   PETG, 0.2mm layer, 25% infill, single unit ~$25-42
//   Nylon SLS, single unit                     ~$60-95
//   Total for 3-5 iteration units (PLA)        ~$80-160
//
// =============================================================================

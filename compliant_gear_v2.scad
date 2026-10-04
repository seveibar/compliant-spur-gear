// Zero-backlash compliant spur gear — v2 (print-friendly finger cap)
// -------------------------------------------------------------------
// Same mechanism as v1 (compliant_gear.scad): every tooth is hollow, its two
// flanks are full-width cantilever walls, the tooth is cut oversize by
// `preload` per flank, and the tip is closed by interleaved fingers that
// slide past each other until a finger reaches the opposite wall.
//
// v1 stacked flat finger layers, so the underside of every finger was a 90°
// overhang. In v2 each finger is a wedge whose faces are at
// `overhang_angle` from vertical, and the L and R wedges interleave as a
// zig-zag. Printed flat (Z up), every downward-facing surface of the cap is
// self-supporting.
//
// In a planar section through the cap (normal to the tooth axis) the L and
// R wedges form two interleaved rows of 45° triangles, one row rooted in
// each wall, with clearance on every face.
//
// Closing travel is still `cap_clearance`: tips reach the opposite wall
// before the sloped faces meet (the slope gap is >= cap_clearance).

/* [Gear] */
module_m       = 3;     // module [mm]
teeth          = 20;
face_width     = 12;    // [mm]
pressure_angle = 20;    // [deg]
bore_d         = 8;

/* [Compliance] */
preload        = 0.10;  // extra flank thickness at pitch circle, per side [mm]
hollow_frac    = 0.55;  // slot width as a fraction of tooth width
slot_depth     = 2.0;   // how far the slot goes below the root circle [mm]
cap_height     = 1.8;   // radial height of the finger cap, down from the tip [mm]
cap_clearance  = 1.0;   // finger tip to opposite wall at rest = closing travel [mm]
overhang_angle = 45;    // wedge face angle from vertical; 45 prints unsupported [deg]
root_fillet    = 0.6;

/* [Mating pinion (for assembly preview)] */
pinion_teeth   = 16;
show           = "assembly"; // [gear, pinion, assembly, tooth_sections, tooth_closeup]

$fn = 96;
STEPS = 24;

// ---------- involute math (radians) ----------
function deg(a) = a * 180 / PI;
function rad(a) = a * PI / 180;
function inv(a_rad) = tan(deg(a_rad)) - a_rad;

function rp(N)  = module_m * N / 2;
function rb(N)  = rp(N) * cos(pressure_angle);
function ra(N)  = rp(N) + module_m;
function rf(N)  = rp(N) - 1.25 * module_m;

// half angular tooth thickness at radius r [rad]
function psi(N, r, pl) =
    let(rr = max(r, rb(N)),
        a_r = acos(rb(N) / rr))
    PI / (2 * N) + pl / rp(N) + inv(rad(pressure_angle)) - inv(rad(a_r));

function polar(r, a_rad) = [r * cos(deg(a_rad)), r * sin(deg(a_rad))];

function radii(r0, r1) = [for (i = [0:STEPS]) r0 + (r1 - r0) * i / STEPS];

// slot half angle at radius r
function slot_a(N, r) = hollow_frac * psi(N, min(r, ra(N)), preload);
function slot_hw(N) = rf(N) * slot_a(N, rf(N));

// ---------- 2D primitives ----------
module tooth2d(N, pl) {
    r0 = rf(N) - 0.5;
    rs = radii(r0, ra(N));
    right = [for (r = rs) polar(r, -psi(N, r, pl))];
    left  = [for (i = [len(rs) - 1:-1:0]) polar(rs[i], psi(N, rs[i], pl))];
    polygon(concat(right, left));
}

module gear2d(N, pl) {
    offset(r = -root_fillet) offset(delta = root_fillet)
    union() {
        circle(r = rf(N));
        for (i = [0:N - 1]) rotate(i * 360 / N) tooth2d(N, pl);
    }
}

// slot (hollow) inside the tooth at angle 0, open at the tip
module slot2d(N) {
    rs = radii(rf(N), ra(N) + 1);
    hw = slot_hw(N);
    right = [for (r = rs) polar(r, -slot_a(N, r))];
    left  = [for (i = [len(rs) - 1:-1:0]) polar(rs[i], slot_a(N, rs[i]))];
    union() {
        polygon(concat(right, left));
        // extension into the rim for a longer, softer cantilever
        translate([rf(N) - slot_depth, -hw]) square([slot_depth + 0.05, 2 * hw]);
        translate([rf(N) - slot_depth, 0]) circle(r = hw, $fn = 32);
    }
}

// ---------- finger wedges ----------
function rcap(N) = ra(N) - cap_height;
// widest slot half width in the cap sets the zig-zag period
function s_max(N) = rcap(N) * slot_a(N, rcap(N));
// slope gap = P/2*tan + 2c - 2s >= c  =>  P >= 2(2s - c)/tan
function period_min(N) = 2 * (2 * s_max(N) - cap_clearance) / tan(overhang_angle);
function n_periods(N) = max(1, floor(face_width / period_min(N)));
function period(N) = face_width / n_periods(N);

// one wedge-shaped finger from wall `side` (+1 = L, CCW), apex at height z.
// In each radial slice it is a triangle in (tangential, z): apex at the tip,
// cap_clearance short of the other wall; base inside its own wall.
module wedge(N, side, z) {
    rs = radii(rcap(N), ra(N));
    n = len(rs);
    pts = [for (r = rs) let(
                aw = side * (slot_a(N, r) + 0.01),
                at = -side * (slot_a(N, r) - cap_clearance / r),
                h  = r * abs(aw - at) / tan(overhang_angle))
            each [[r * cos(deg(at)), r * sin(deg(at)), z],
                  [r * cos(deg(aw)), r * sin(deg(aw)), z - h],
                  [r * cos(deg(aw)), r * sin(deg(aw)), z + h]]];
    sides = [for (i = [0:n - 2]) let(a = 3 * i, b = 3 * i + 3)
                each [[a, b, b + 1], [a, b + 1, a + 1],
                      [a + 1, b + 1, b + 2], [a + 1, b + 2, a + 2],
                      [a + 2, b + 2, b], [a + 2, b, a]]];
    caps = [[0, 1, 2], [3 * n - 3, 3 * n - 1, 3 * n - 2]];
    polyhedron(points = pts, faces = concat(caps, sides), convexity = 4);
}

module fingers3d(N) {
    P = period(N);
    intersection() {
        union()
            for (k = [-1:n_periods(N)]) {
                wedge(N,  1, (k + 0.25) * P);
                wedge(N, -1, (k + 0.75) * P);
            }
        translate([0, 0, face_width / 2])
            cube([4 * ra(N), 4 * ra(N), face_width], center = true);
    }
}

echo(str("v2 finger period ", period(teeth), " mm, ", n_periods(teeth),
         " L + ", n_periods(teeth), " R wedges; slope gap at cap root ",
         period(teeth) / 2 * tan(overhang_angle) + 2 * cap_clearance - 2 * s_max(teeth), " mm"));

module compliant_gear(N = teeth) {
    F = face_width;
    union() {
        difference() {
            linear_extrude(F) gear2d(N, preload);
            translate([0, 0, -1]) cylinder(d = bore_d, h = F + 2);
            for (i = [0:N - 1]) rotate(i * 360 / N)
                translate([0, 0, -1]) linear_extrude(F + 2) slot2d(N);
        }
        for (i = [0:N - 1]) rotate(i * 360 / N) fingers3d(N);
    }
}

module pinion(N = pinion_teeth) {
    difference() {
        linear_extrude(face_width) gear2d(N, 0);
        translate([0, 0, -1]) cylinder(d = bore_d, h = face_width + 2);
    }
}

module assembly() {
    color("orange") compliant_gear();
    a = rp(teeth) + rp(pinion_teeth);   // nominal center distance
    color("steelblue", 0.85)
        translate([a, 0, 0]) rotate(180 + 180 / pinion_teeth) pinion();
}

// cross sections through an L-finger apex and an R-finger apex
module tooth_sections() {
    zs = [0.25 * period(teeth) + period(teeth), 0.75 * period(teeth) + period(teeth)];
    for (i = [0:1])
        translate([i * 18, 0, 0])
        translate([-rp(teeth), 0, 0])
        projection(cut = true) translate([0, 0, -zs[i]])
            intersection() {
                compliant_gear();
                translate([rp(teeth) - 6, -6, -1]) cube([12, 12, face_width + 2]);
            }
}

if (show == "gear")           compliant_gear();
else if (show == "pinion")    pinion();
else if (show == "assembly")  assembly();
else if (show == "tooth_sections") tooth_sections();
else if (show == "tooth_closeup")
    intersection() {
        compliant_gear();
        translate([rp(teeth) - 4, -5, -1]) cube([8, 10, face_width + 2]);
    }

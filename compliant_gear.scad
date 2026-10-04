// Zero-backlash compliant spur gear
// ---------------------------------
// Alternative to a spring-loaded split gear. Every tooth is hollow: its two
// flanks are thin cantilever walls rooted in the rim, each running the full
// face width. The tooth is cut oversize by `preload` per flank, so when it
// meshes at nominal center distance the mating gear squeezes both walls
// toward the tooth center.
//
// The hollow is closed at the tip by interleaved fingers. Along Z the tip is
// split into `cap_layers` layers; in each layer one wall sends a finger
// across the slot, stopping `cap_clearance` short of the opposite wall:
//
//    developed section through the cap (looking radially):
//
//      z=F  |R wall|<==== R finger ====|  gap  |L wall|
//           |R wall|  gap  |==== L finger ====>|L wall|
//           |R wall|<==== R finger ====|  gap  |L wall|
//      z=0  |R wall|  gap  |==== L finger ====>|L wall|
//
// Pushed inward, the fingers slide past each other in their own layers. There
// is no dedicated stop: the walls stop when a finger runs into the inside of
// the opposite wall, after `cap_clearance` of closing travel at the cap.

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
cap_layers     = 4;     // number of interleaved finger layers along Z
cap_clearance  = 1.0;   // finger end to opposite wall at rest = closing travel [mm]
layer_gap      = 0.3;   // Z clearance between fingers so they slide, not fuse [mm]
root_fillet    = 0.6;

/* [Mating pinion (for assembly preview)] */
pinion_teeth   = 16;
show           = "assembly"; // [gear, pinion, assembly, tooth_sections]

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

// finger from one wall (side = +1 left / +CCW wall, -1 right wall) across
// the slot in the cap zone, ending `cap_clearance` short of the other wall
module finger2d(N, side) {
    rs = radii(ra(N) - cap_height, ra(N));
    root = [for (r = rs) polar(r, side * (slot_a(N, r) + 0.01))];  // inside own wall
    tip  = [for (i = [len(rs) - 1:-1:0])
                polar(rs[i], -side * (slot_a(N, rs[i]) - cap_clearance / rs[i]))];
    polygon(concat(root, tip));
}

// ---------- 3D ----------
function layer_z0(i) = i * face_width / cap_layers + (i > 0 ? layer_gap / 2 : 0);
function layer_z1(i) = (i + 1) * face_width / cap_layers
                       - (i < cap_layers - 1 ? layer_gap / 2 : 0);

module fingers3d(N) {
    for (i = [0:cap_layers - 1])
        translate([0, 0, layer_z0(i)])
            linear_extrude(layer_z1(i) - layer_z0(i))
                finger2d(N, i % 2 == 0 ? 1 : -1);
}

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

// cross sections through the first two finger layers
module tooth_sections() {
    zs = [(layer_z0(0) + layer_z1(0)) / 2, (layer_z0(1) + layer_z1(1)) / 2];
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

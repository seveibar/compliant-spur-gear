// Backlash test stand for two compliant_gear.scad (v1) gears
// ----------------------------------------------------------
// A base plate with two pillars. Each pillar is a wide shoulder that the
// gear's hub sits on (so the teeth and spring walls never touch the plate)
// and a pin that runs through the gear's bore with a small clearance.
//
// The two compliant gears preload each other, which pushes them apart, so
// each gear rides against the outer side of its pin. The pins are therefore
// placed 2 x pin_clearance closer than the nominal center distance: once the
// preload takes up the clearance, the gears mesh at exactly the nominal
// distance. Set `extra_center_distance` > 0 to open the mesh up and watch
// backlash appear.

/* [Gears being tested] */
module_m       = 3;
teeth          = 20;     // both gears
gear_bore_d    = 8;
gear_width     = 12;

/* [Pillars] */
pin_clearance  = 0.15;   // radial clearance between pin and bore [mm]
shoulder_d     = 16;     // must stay inside the slot bottoms (~Ø46)
shoulder_h     = 2.0;    // gap between gear and plate
pin_extra      = 3.0;    // pin length above the gear's top face
pin_chamfer    = 0.8;
extra_center_distance = 0;  // >0 opens the mesh to show backlash

/* [Base] */
plate_t        = 4;
plate_margin   = 8;      // beyond the gear tips
corner_r       = 6;

/* [Preview] */
show           = "stand"; // [stand, assembly]

$fn = 96;

use <compliant_gear.scad>   // modules only; used for the assembly preview

center_nominal = module_m * teeth;          // 2 x pitch radius
pin_spacing    = center_nominal - 2 * pin_clearance + extra_center_distance;
pin_d          = gear_bore_d - 2 * pin_clearance;
tip_r          = module_m * teeth / 2 + module_m;

module pillar() {
    // shoulder with a small fillet-like flare into the plate
    cylinder(d1 = shoulder_d + 2, d2 = shoulder_d, h = 1);
    cylinder(d = shoulder_d, h = shoulder_h);
    // pin, chamfered at the top for easy insertion
    pin_h = shoulder_h + gear_width + pin_extra;
    cylinder(d = pin_d, h = pin_h - pin_chamfer);
    translate([0, 0, pin_h - pin_chamfer])
        cylinder(d1 = pin_d, d2 = pin_d - 2 * pin_chamfer, h = pin_chamfer);
}

module plate() {
    L = pin_spacing + 2 * (tip_r + plate_margin);
    Wd = 2 * (tip_r + plate_margin);
    translate([-(tip_r + plate_margin), -Wd / 2, -plate_t])
        linear_extrude(plate_t)
            offset(r = corner_r) offset(delta = -corner_r) square([L, Wd]);
}

module stand() {
    plate();
    pillar();
    translate([pin_spacing, 0, 0]) pillar();
}

if (show == "stand") stand();
else if (show == "assembly") {
    color("gray") stand();
    // gears pushed apart by their preload: each against the outer side of its pin
    color("orange")
        translate([-pin_clearance, 0, shoulder_h]) compliant_gear();
    color("gold")
        translate([pin_spacing + pin_clearance, 0, shoulder_h])
            rotate(180 + 180 / teeth) compliant_gear();
}

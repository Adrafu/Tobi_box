// Tobi Box, Ladesockel Rev. 4: Druckmuster der Führung (T1, T2, T3, T8)
// Alle Maße in mm. Werte mit (R) sind Richtwerte aus design_draft.md.
// Auswahl: teil = "sockel" | "boxboden" | "halter" | "kragenprobe" | "alle"
// Koordinaten: x = Richtung der Rippen, y = vorne (-) nach hinten (+), z = oben.
// Hinten (+y) laufen Kabelkanal im Sockel und Kabelrinne im Boxboden.

teil = "alle";

// ---------- Allgemein ----------
spiel        = 0.4;   // Passung Kragen/Tasche, je Seite (Druck-Toleranz)
fn_fein      = 48;    // $fn für runde Teile
$fn          = fn_fein;

// ---------- Mulde (Sockel) ----------
mulde_boden  = 124;   // Mulde innen, Boden quadratisch
mulde_h      = 20;    // Höhe der Mulde
mulde_winkel = 60;    // Wandwinkel gegen die Waagrechte
unterteil_h  = 15;    // Höhe Unterteil (Gewicht, Kabel); Mulden-Boden beginnt vorne hier
gefaelle     = 2;     // Gefälle Mulden-Boden nach vorne (-y) in Grad
sockel_aussen= 156;   // Außenmaß Sockel quadratisch
sockel_ecke  = 8;     // Eckenradius außen
rinne_b      = 6;     // Rinne vorne, Breite
rinne_t      = 5;     // Rinne, Tiefe unter dem Boden
abl_d        = 4;     // Ablaufbohrung
abl_x        = [-45, -18, 18, 45]; // 4 Ablaufbohrungen
freistich_b  = 22;    // Freistich für TPU-Ecken der Box, Kantenlänge
freistich_t  = 3;     // Freistich, Tiefe unter dem Boden
box_b        = 120;   // Box (und Boxboden) quadratisch
ecke_unter   = 2;     // TPU-Ecken ragen so weit unter den Boxboden (R)
sitz_h       = 3.5;   // Boxboden-Unterseite über Mulden-Boden Mitte, wenn gesteckt
boden_luft   = 0.8;   // Mindestabstand Boxboden zum schrägen Mulden-Boden

// ---------- Gewichtsraum und Kabel (Sockel) ----------
hohl_x_innen = 16;    // Gewichtsraum links/rechts: innere Kante (Mittelsteg für Kabel)
hohl_x_aussen= 62;    // äußere Kante
hohl_y       = 100;   // Länge in y
hohl_u       = 2;     // Boden des Gewichtsraums
hohl_h       = 9;     // Höhe; Stahlscheiben-Stapel höchstens hohl_h - 0.4
kabel_d      = 4.0;   // Kabeldurchmesser des Netzteil-Kabels (messen!)
bohr_d       = 7;     // Kabelbohrung unter der Halter-Aufnahme
rille_t      = 5;     // Kabelkanal an der Unterseite, Tiefe (offen nach unten)
klemm_ueber  = 0.5;   // Klemmzone: Kanal um so viel schmaler als das Kabel
klemm_y0     = 14;    // Klemmzone beginnt bei y
klemm_y1     = 30;    // Klemmzone endet bei y
zip_y        = 22;    // Kabelbinder-Schlitz, Lage in y
zip_b        = 3.6;   // Schlitz Breite (Kabelbinder bis 3,5 mm)
zip_d        = 1.8;   // Schlitz Dicke

// ---------- Rippen und Nuten ----------
rippe_y      = 38;    // Rippe vorne/hinten bei y = -/+ rippe_y
rippe_b      = 8;     // Rippenbreite
rippe_l      = 76;    // Rippenlänge (in x)
rippe_fase   = 2;     // Fase oben als Einlauf
rippe_oben   = 27;    // Rippenoberkante über Mulden-Boden Mitte (siehe assert)
rippe_frei   = 2;     // Soll: Steckerspitze mindestens so weit frei bei 90°
nut_spiel    = 1.0;   // Nut-Breite = Rippenbreite + 2 * nut_spiel
nut_fase     = 2;     // Fase am Nuteingang
nut_luft     = 1.0;   // Nut-Tiefe über Rippenhöhe
wand         = 2.4;   // Wandstärke im Boxboden

// ---------- Kragen und Tasche ----------
kragen_h     = 16;    // Kragenhöhe über Mulden-Boden Mitte
kragen_wand_u= 3;     // Wand unten (Kragen-Fuß)
kragen_wand_o= 2.5;   // Wand oben
einsteck     = 6.5;   // Einstecktiefe des Steckers in die Buchse
tasche_dach  = 1.2;   // Dach der Tasche (Boxboden), Buchse sitzt darauf
einlauf      = 3;     // Einlauf-Fase am Tascheneingang (fängt ca. +/-3 mm)
min_eingriff = 5;     // Kragen greift mindestens so tief, bevor der Stecker berührt (R)

// ---------- Stecker und schwimmender Halter (TPU 95A) ----------
stecker_b    = 12.5;  // Umspritzkörper Breite (messen!)
stecker_d    = 6.5;   // Umspritzkörper Dicke (messen!)
stecker_l    = 20;    // Umspritzkörper Länge (messen!)
stecker_schale= 6.7;  // Metallschale ragt aus dem Körper (messen!)
halter_wand  = 2.5;   // Wand der Klemmhülse
halter_boden = 2;     // Bodenplatte = Flansch (Dicke)
halter_h     = 14;    // Gesamthöhe Halter ab Unterkante Flansch
presssitz    = 0.4;   // Hülse innen um so viel kleiner als der Stecker (TPU dehnt)
flansch_ueber= 2.25;  // Flansch steht je Seite über die Hülse
halter_spiel = 1.0;   // Spiel seitlich im Kragen (+/- 1 mm)
halter_hub   = 1.0;   // Spiel nach oben/unten (+/- 1 mm)
halter_bohr  = 6;     // Kabelloch im Flansch

// ---------- Boxboden ----------
box_boden    = 3;     // Bodenstärke
box_wand_h   = 25;    // Wandhöhe über dem Boden
kabelrinne_b = 12;    // Kabelrinne (gewinkelter Stecker), Breite
kabelrinne_t = 9;     // Kabelrinne, Tiefe ab Unterseite
ecke_b       = 18;    // Aussparung für TPU-Ecke, Kantenlänge
schraube     = "M2";  // "M2" oder "M2.5" für das Breakout
rec_b        = 8.94;  // USB-C-Buchse Breite
rec_d        = 3.26;  // USB-C-Buchse Dicke
rec_l        = 7.35;  // USB-C-Buchse Länge (Tiefe)
pcb_b        = 15;    // Breakout-Platine Breite (messen!)
pcb_h        = 12;    // Platine Höhe (steht senkrecht)
pcb_t        = 1.6;   // Platinendicke
loch_dx      = 5.5;   // Schraublöcher bei x = +/- loch_dx
loch_z       = 7;     // Schraubloch-Höhe über Buchsen-Öffnung

// ================= Abgeleitete Werte =================
zc          = unterteil_h + (mulde_boden/2)*tan(gefaelle); // Mulden-Boden Mitte (abs.)
box_h       = box_boden + box_wand_h;
tasche_t    = kragen_h - sitz_h;                // Tiefe der Tasche bis Dach-Unterseite
z_open      = tasche_t + tasche_dach;           // Buchsen-Öffnung im Boxboden
tip_nom     = kragen_h + tasche_dach + einsteck;// Steckerspitze über Mulden-Boden, gesteckt
tip_max     = tip_nom + halter_hub;             // Halter ganz oben
body_unten  = tip_nom - stecker_schale - stecker_l;
halter_unten= body_unten - halter_boden;
ledge_rel   = halter_unten - halter_hub;        // Auflage des Flansches (relativ zu zc)
pocket_h    = halter_boden + 2*halter_hub;
pocket_top  = ledge_rel + pocket_h;

hs_x = stecker_b + 2*halter_wand;  hs_y = stecker_d + 2*halter_wand;   // Hülse außen
hf_x = hs_x + 2*flansch_ueber;     hf_y = hs_y + 2*flansch_ueber;      // Flansch
th_x = hs_x + 2*halter_spiel;      th_y = hs_y + 2*halter_spiel;       // Hals im Kragen
pk_x = hf_x + 2*halter_spiel;      pk_y = hf_y + 2*halter_spiel;       // Tasche des Flansches
kx_u = pk_x + 2*kragen_wand_u;     ky_u = pk_y + 2*kragen_wand_u;      // Kragen außen unten
kx_o = th_x + 2*kragen_wand_o;     ky_o = th_y + 2*kragen_wand_o;      // Kragen außen oben
kragen_kegel = atan((kx_u-kx_o)/2 / kragen_h);
nut_b       = rippe_b + 2*nut_spiel;
nut_t       = rippe_oben - sitz_h + nut_luft;

// ================= Nachrechnen =================
assert(rippe_oben - tip_max >= rippe_frei,
  "Rippen zu niedrig: Steckerspitze bei 90 Grad nicht mindestens rippe_frei frei");
assert(tasche_t - einsteck >= min_eingriff,
  "Kragen greift zu kurz, bevor der Stecker die Buchse berührt");
assert(sitz_h - tan(gefaelle)*box_b/2 >= boden_luft,
  "Boxboden streift am schrägen Mulden-Boden");
assert(kragen_kegel > 5 && kragen_kegel < 30, "Kegelwinkel des Kragens unplausibel");
assert(halter_h - halter_boden < stecker_l - 2, "Hülse zu hoch: Stecker ragt nicht genug heraus");
assert(halter_h + halter_hub < kragen_h, "Halter stößt oben an den Kragen");
assert(zc + ledge_rel >= rille_t + 2, "Halter-Auflage zu tief: zu wenig Material über dem Kabelkanal");
assert(pk_x/2 + 2 <= hohl_x_innen, "Halter-Aufnahme ragt in den Gewichtsraum");
assert(bohr_d > kabel_d + 1 && halter_bohr > kabel_d + 1, "Kabelloch zu klein");
assert(nut_t + wand <= box_h, "Nut-Tunnel höher als der Boxboden");
assert(z_open + pcb_h <= box_h + 1, "Platine ragt weit über den Boxrand");
assert(rippe_l/2 + 2 <= (mulde_boden/2 - freistich_b) , "Rippen reichen in die Freistiche");
echo(str("Mulden-Boden Mitte z = ", zc, " | Steckerspitze max = ", tip_max,
         " | Rippe oben = ", rippe_oben, " | Nuttiefe = ", nut_t,
         " | Eingriff = ", tasche_t - einsteck, " | Kegel = ", kragen_kegel));

// ================= Hilfsmodule =================
module rrect(b, r, h) {
  linear_extrude(h) offset(r) square(b - 2*r, center = true);
}

// ---------- Sockel ----------
module mulde_schnitt() {
  t  = (mulde_h + 1) / tan(mulde_winkel);
  intersection() {
    translate([0, 0, unterteil_h])
      linear_extrude(height = mulde_h + 1,
                     scale = (mulde_boden + 2*t) / mulde_boden)
        square(mulde_boden, center = true);
    // nur oberhalb der um gefaelle geneigten Boden-Ebene
    translate([0, -mulde_boden/2, unterteil_h]) rotate([gefaelle, 0, 0])
      translate([-200, -200, 0]) cube([400, 400, 200]);
  }
}

module rippen() {
  zu = unterteil_h - 3;
  for (s = [-1, 1])
    translate([0, s*rippe_y, 0])
      rotate([90, 0, 90]) linear_extrude(height = rippe_l, center = true)
        polygon([[-rippe_b/2, zu], [rippe_b/2, zu],
                 [rippe_b/2, zc + rippe_oben - rippe_fase],
                 [rippe_b/2 - rippe_fase, zc + rippe_oben],
                 [-rippe_b/2 + rippe_fase, zc + rippe_oben],
                 [-rippe_b/2, zc + rippe_oben - rippe_fase]]);
}

module kragen_aussen() {   // Ursprung = Mulden-Boden Mitte
  translate([0, 0, -3]) linear_extrude(3.01) square([kx_u, ky_u], center = true);
  linear_extrude(height = kragen_h, scale = [kx_o/kx_u, ky_o/ky_u])
    square([kx_u, ky_u], center = true);
}

module kragen_innen() {    // Tasche für den Flansch + Hals für die Hülse
  translate([-pk_x/2, -pk_y/2, ledge_rel]) cube([pk_x, pk_y, pocket_h]);
  translate([-th_x/2, -th_y/2, pocket_top - 0.01])
    cube([th_x, th_y, kragen_h - pocket_top + 1]);
}

module streifen(y, w) { translate([-w/2, y]) square([w, 0.01]); }

module rille2d() {   // Kabelkanal von oben gesehen, mit Klemmzone
  rb = kabel_d + 2;  kb = kabel_d - klemm_ueber;  ra = kabel_d + 0.6;
  yend = sockel_aussen/2 + 1;
  hull() { circle(d = rb); streifen(klemm_y0 - 3, rb); }
  hull() { streifen(klemm_y0 - 3, rb); streifen(klemm_y0 + 1, kb); }
  hull() { streifen(klemm_y0 + 1, kb); streifen(klemm_y1 - 1, kb); }
  hull() { streifen(klemm_y1 - 1, kb); streifen(klemm_y1 + 3, ra); }
  hull() { streifen(klemm_y1 + 3, ra); streifen(yend, ra); }
}

module kabelweg() {
  translate([0, 0, -1]) cylinder(d = bohr_d, h = zc + ledge_rel + 1.1);
  translate([0, 0, -1]) linear_extrude(rille_t + 1) rille2d();
  // Kabelbinder-Schlitze: zwei senkrechte Schlitze und ein Tunnel darüber
  xs = (kabel_d - klemm_ueber)/2 + zip_b/2 + 0.8;
  for (s = [-1, 1])
    translate([s*xs - zip_b/2, zip_y - zip_d/2, -1]) cube([zip_b, zip_d, rille_t + 4.5]);
  translate([-xs, zip_y - zip_d/2, rille_t + 1.5]) cube([2*xs, zip_d, zip_b - 1]);
}

module gewichtsraeume() {
  for (s = [-1, 1])
    translate([s*(hohl_x_innen + hohl_x_aussen)/2 - (hohl_x_aussen - hohl_x_innen)/2,
               -hohl_y/2, hohl_u])
      cube([hohl_x_aussen - hohl_x_innen, hohl_y, hohl_h]);
}

module rinne_und_ablauf() {
  translate([0, -mulde_boden/2, unterteil_h]) rotate([gefaelle, 0, 0])
    translate([-box_b/2, -0.5, -rinne_t]) cube([box_b, rinne_b + 0.5, rinne_t + 4]);
  for (x = abl_x)
    translate([x, -mulde_boden/2 + rinne_b/2, -1]) cylinder(d = abl_d, h = unterteil_h + 3, $fn = 24);
}

module freistiche() {
  translate([0, -mulde_boden/2, unterteil_h]) rotate([gefaelle, 0, 0])
    for (sx = [-1, 1], sy = [-1, 1])
      translate([sx*(mulde_boden/2 - freistich_b/2),
                 mulde_boden/2 + sy*(mulde_boden/2 - freistich_b/2) - freistich_b/2,
                 -freistich_t])
        translate([-freistich_b/2, 0, 0]) cube([freistich_b, freistich_b, freistich_t + 4]);
}

module sockel() {
  difference() {
    union() {
      difference() {
        rrect(sockel_aussen, sockel_ecke, unterteil_h + mulde_h);
        mulde_schnitt();
      }
      rippen();
      translate([0, 0, zc]) kragen_aussen();
    }
    translate([0, 0, zc]) kragen_innen();
    kabelweg();
    gewichtsraeume();
    rinne_und_ablauf();
    freistiche();
  }
}

// ---------- Halter (TPU 95A), Druck: Flansch unten, Hülse nach oben ----------
module halter() {
  difference() {
    union() {
      translate([-hf_x/2, -hf_y/2, 0]) cube([hf_x, hf_y, halter_boden]);
      translate([-hs_x/2, -hs_y/2, 0]) cube([hs_x, hs_y, halter_h]);
    }
    // Klemmraum für den Umspritzkörper (etwas zu klein: presst)
    translate([-(stecker_b - presssitz)/2, -(stecker_d - presssitz)/2, halter_boden])
      cube([stecker_b - presssitz, stecker_d - presssitz, halter_h]);
    // Kabelloch
    translate([0, 0, -1]) cylinder(d = halter_bohr, h = halter_boden + 2);
  }
}

// ---------- Boxboden ----------
function tx(z) = kx_u - (kx_u - kx_o) * (z + sitz_h) / kragen_h;  // Kragen-Breite in Boxhöhe z
function ty(z) = ky_u - (ky_u - ky_o) * (z + sitz_h) / kragen_h;

module slab(x, y, z) { translate([-x/2, -y/2, z]) cube([x, y, 0.01]); }

module tasche_cut() {
  s = spiel;
  linear_extrude(height = tasche_t,
                 scale = [(tx(tasche_t) + 2*s)/(tx(0) + 2*s), (ty(tasche_t) + 2*s)/(ty(0) + 2*s)])
    square([tx(0) + 2*s, ty(0) + 2*s], center = true);
  hull() {
    slab(tx(0) + 2*s + 2*(einlauf + 0.5), ty(0) + 2*s + 2*(einlauf + 0.5), -0.5);
    slab(tx(einlauf) + 2*s, ty(einlauf) + 2*s, einlauf);
  }
}

module tasche_huelle(top) {   // Vollkörper um die Tasche, verjüngt
  w0 = tx(0) + 2*spiel + 2*einlauf + 2*wand;
  d0 = ty(0) + 2*spiel + 2*einlauf + 2*wand;
  w1 = tx(top) + 2*spiel + 2*wand;
  d1 = ty(top) + 2*spiel + 2*wand;
  hull() { slab(w0, d0, 0); slab(w1, d1, top); }
}

module nut_profil(b, t, f) {
  polygon([[-(b/2 + f), -1], [b/2 + f, -1], [b/2 + f, 0], [b/2, f], [b/2, t],
           [-b/2, t], [-b/2, f], [-(b/2 + f), 0]]);
}

module nut_cut_x(b, t, f) {   // Nut entlang x, durch beide Seitenwände
  rotate([90, 0, 90]) linear_extrude(height = box_b + 10, center = true) nut_profil(b, t, f);
}
module nut_huelle_x(b, t, f) {
  rotate([90, 0, 90]) linear_extrude(height = box_b, center = true)
    translate([-(b/2 + f + wand), 0]) square([b + 2*f + 2*wand, t + wand]);
}

module rinne_cut_y() {   // vom Kragen nach hinten (+y) bis zur Rückkante
  translate([0, box_b/2 + 5, 0]) rotate([90, 0, 0]) linear_extrude(height = box_b/2 + 5)
    nut_profil(kabelrinne_b, kabelrinne_t, nut_fase);
}
module rinne_huelle_y() {
  translate([0, box_b/2, 0]) rotate([90, 0, 0]) linear_extrude(height = box_b/2)
    translate([-(kabelrinne_b/2 + nut_fase + wand), 0])
      square([kabelrinne_b + 2*nut_fase + 2*wand, kabelrinne_t + wand]);
}

module platinenraum() {
  yb = -(rec_d/2 + pcb_t + 0.3);
  // Loch im Dach für den Steckerschaft
  translate([-(rec_b/2 + 0.3), -(rec_d/2 + 0.3), tasche_t - 0.01])
    cube([rec_b + 0.6, rec_d + 0.6, tasche_dach + 0.02]);
  // Buchsenkörper, umfasst von Stützwand
  translate([-(rec_b/2 + 0.3), -(rec_d/2 + 0.3), z_open]) cube([rec_b + 0.6, rec_d + 0.6, 40]);
  // Platine steht senkrecht, Ebene xz, Buchse auf der +y-Seite
  translate([-(pcb_b/2 + 0.3), yb, z_open]) cube([pcb_b + 0.6, pcb_t + 0.3 + 0.2, 40]);
  // Schrauben-Vorbohrung (M2: 1.7, M2.5: 2.1), waagrecht in die Stützwand
  pilot = (schraube == "M2") ? 1.7 : 2.1;
  for (s = [-1, 1])
    translate([s*loch_dx, yb + 0.01, z_open + loch_z]) rotate([90, 0, 0])
      cylinder(d = pilot, h = 7, $fn = 20);
}

module ecken_aussparung() {
  for (sx = [-1, 1], sy = [-1, 1])
    translate([sx*(box_b/2 - ecke_b/2) - ecke_b/2, sy*(box_b/2 - ecke_b/2) - ecke_b/2, -1])
      cube([ecke_b, ecke_b, ecke_unter + 1]);
}

module boxboden() {
  stuetz_top = min(z_open + pcb_h + 1, box_h);
  difference() {
    union() {
      difference() {
        rrect(box_b, 4, box_h);
        translate([0, 0, box_boden]) rrect(box_b - 2*wand, 2, box_h);
      }
      intersection() {
        rrect(box_b, 4, box_h);
        union() {
          for (s = [-1, 1]) translate([0, s*rippe_y, 0]) nut_huelle_x(nut_b, nut_t, nut_fase);
          rinne_huelle_y();
          tasche_huelle(stuetz_top);
        }
      }
    }
    for (s = [-1, 1]) translate([0, s*rippe_y, 0]) nut_cut_x(nut_b, nut_t, nut_fase);
    rinne_cut_y();
    tasche_cut();
    platinenraum();
    ecken_aussparung();
  }
}

// ---------- Kragenprobe: Kragen-Stück + Taschen-Stück ----------
module kragenprobe() {
  h = -ledge_rel + 2;
  // Kragen mit Aufnahme auf einem Sockelstumpf
  translate([-32, 0, 0]) difference() {
    union() {
      translate([-kx_u/2 - 4, -ky_u/2 - 4, 0]) cube([kx_u + 8, ky_u + 8, h]);
      translate([0, 0, h]) kragen_aussen();
    }
    translate([0, 0, h]) kragen_innen();
    translate([0, 0, -1]) cylinder(d = bohr_d, h = h + 1.1);
  }
  // Taschen-Stück
  translate([32, 0, 0]) difference() {
    tasche_huelle(z_open + 2);
    tasche_cut();
    translate([-(rec_b/2 + 0.3), -(rec_d/2 + 0.3), tasche_t - 0.01])
      cube([rec_b + 0.6, rec_d + 0.6, 30]);
  }
}

// ---------- Auswahl ----------
if (teil == "sockel") sockel();
else if (teil == "boxboden") boxboden();
else if (teil == "halter") halter();
else if (teil == "kragenprobe") kragenprobe();
else if (teil == "alle") {
  color("lightsteelblue") sockel();
  color("khaki") translate([155, 0, 0]) boxboden();
  color("tomato") translate([240, 0, 0]) halter();
  color("palegreen") translate([240, -80, 0]) kragenprobe();
} else assert(false, "teil muss sockel, boxboden, halter, kragenprobe oder alle sein");

// Tobi Box, Ladesockel Variante 4a "hoher Kragen": Druckmuster der Führung
// Alle Maße in mm. Werte mit (R) sind Richtwerte, mit (messen!) vor dem Druck prüfen.
// Auswahl: teil = "sockel" | "boxboden" | "halter" | "kragenprobe" | "alle"
//          Hilfsteile zum Ansehen: "baugruppe0" | "baugruppe90" (Schnitt in y = 0;
//          baugruppe90 zeigt die Box gekippt, so wie sie bei 90 Grad liegt)
//          Pruefteil: "kippcheck" = Schnittmenge Sockel/gekippte Box (muss leer sein)
// Koordinaten: x = lange Seite des Kragens, y = vorne (-) nach hinten (+), z = oben.
// Höhen im Kragen-Bereich zählen ab der Bezugsebene z0 = Boxboden, wenn die Box
// bei 0 Grad gesteckt ist. z0 liegt sitz_h über dem Mulden-Boden in der Mitte
// (wegen des Gefälles, siehe assert "Boxboden streift").
// Im Boxboden zählen Höhen ab der Boxbodenfläche (Unterseite) = 0.

teil = "alle";

// ---------- Allgemein ----------
spiel        = 0.5;   // Passung Kragen/Tasche, je Seite (Druck-Toleranz)
fn_fein      = 48;    // $fn für runde Teile
$fn          = fn_fein;
befestigung  = false; // true: zwei Schraubenlöcher im Sockel für Möbel-Befestigung

// ---------- Mulde (Sockel) ----------
mulde_boden  = 124;   // Mulde innen, Boden quadratisch
mulde_h      = 20;    // Höhe der Mulde
mulde_winkel = 60;    // Wandwinkel gegen die Waagrechte
unterteil_h  = 22;    // Höhe Unterteil (Gewicht, Kabel, Halter-Schulter); Mulden-Boden vorne
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
sitz_h       = 3;     // Boxboden-Unterseite (gesteckt) über Mulden-Boden Mitte
boden_luft   = 0.8;   // Mindestabstand Boxboden zum schrägen Mulden-Boden

// ---------- Gewichtsraum und Kabel (Sockel) ----------
hohl_x_innen = 16;    // Gewichtsraum links/rechts: innere Kante (Mittelsteg für Kabel)
hohl_x_aussen= 66;    // äußere Kante
hohl_y       = 100;   // Länge in y
hohl_u       = 2;     // Boden des Gewichtsraums
hohl_h       = 16;    // Höhe; Stahlscheiben-Stapel höchstens hohl_h - 0.4
gewicht_soll = 1000;  // Soll: so viel Stahl (g) muss hineinpassen
stahl_dichte = 7.85;  // g/cm³
fuellgrad    = 0.85;  // Scheiben füllen den Raum nur zu diesem Anteil
kabel_d      = 4.0;   // Kabeldurchmesser des Netzteil-Kabels (messen!)
bohr_d       = 7;     // Kabelbohrung unter der Halter-Aufnahme
rille_t      = 5;     // Kabelkanal an der Unterseite, Tiefe (offen nach unten)
klemm_ueber  = 0.5;   // Klemmzone: Kanal um so viel schmaler als das Kabel
klemm_y0     = 14;    // Klemmzone beginnt bei y
klemm_y1     = 30;    // Klemmzone endet bei y
zip_y        = 22;    // Kabelbinder-Schlitz, Lage in y
zip_b        = 3.6;   // Schlitz Breite (Kabelbinder bis 3,5 mm)
zip_d        = 1.8;   // Schlitz Dicke

// ---------- Befestigung (nur bei befestigung = true) ----------
bef_x        = 32;    // Schraubenlöcher bei x = +/- bef_x
bef_y        = 56;    // und y = bef_y (hinten im Muldenboden, unter der Box)
bef_d        = 4.5;   // Schaft (Schraube bis M4)
bef_kopf     = 9.5;   // Senkung für den Kopf, Durchmesser
bef_kopf_t   = 3;     // Senkung, Tiefe unter dem Muldenboden

// ---------- Kragen (Sockel, fest mit der Mulde gedruckt) ----------
kragen_h     = 14;    // Kragenhöhe über z0
kragen_b_u   = 38;    // unten, lange Seite (x)
kragen_d_u   = 20;    // unten, kurze Seite (y)
kragen_b_o   = 32;    // oben, lange Seite
kragen_d_o   = 14;    // oben, kurze Seite
schacht_b    = 14;    // Schacht oben, x (Zapfen 13 + 2 x 0,5)
schacht_d    = 8;     // Schacht oben, y (Zapfen 7 + 2 x 0,5)
schacht_fase = 1;     // Einlauf-Fase am Schacht
spitze_unter = 2;     // Metallspitze liegt so weit unter der Kragenoberkante

// ---------- Tasche und Zapfen (Boxboden) ----------
zapfen_b     = 13;    // Buchsen-Zapfen, x (Feinführung: 0,5 je Seite im Schacht)
zapfen_d     = 7;     // Buchsen-Zapfen, y
zapfen_fase  = 0.6;   // Fase an der Zapfen-Unterkante
buchse_h     = 5.5;   // Buchsen-Öffnung (Zapfen-Unterseite) über der Boxbodenfläche
wand         = 2.4;   // Wandstärke im Boxboden
min_eingriff = 6;     // Kragen führt die Tasche mindestens so tief, bevor die Spitze berührt
min_abstand90= 5;     // bei 90 Grad flach: Zapfen-Unterseite mindestens so weit über der Spitze
min_abstand_kipp = 3; // bei 90 Grad, maximal gekippt: Zapfen mindestens so weit über der Spitze
min_fuehrung = 6;     // bei 0/180 Grad: Führungsfläche der Tasche neben der Rinne mindestens (x je Seite)
min_band     = 4;     // bei 0/180 Grad: durchgehendes Wandband über der Rinne mindestens (z)

// ---------- Stecker und Halter (TPU 95A) ----------
stecker_b    = 12.5;  // Umspritzkörper Breite (messen!)
stecker_d    = 6.5;   // Umspritzkörper Dicke (messen!)
stecker_l    = 20;    // Umspritzkörper Länge (messen!)
stecker_schale= 6.7;  // Metallschale ragt aus dem Körper (messen!)
schale_b     = 8.4;   // Metallschale Breite (nur für die Ansicht)
schale_d     = 2.6;   // Metallschale Dicke (nur für die Ansicht)
halter_wand  = 2.5;   // Wand der Klemmhülse
halter_boden = 2;     // Bodenplatte = Flansch (Dicke)
halter_h     = 14;    // Gesamthöhe Halter ab Unterkante Flansch
presssitz    = 0.4;   // Hülse innen um so viel kleiner als der Stecker (TPU dehnt)
flansch_ueber= 2.25;  // Flansch steht je Seite über die Hülse
halter_spiel = 0.5;   // Spiel seitlich (+/- 0,5), Halter ist axial NICHT beweglich
flansch_luft = 0.3;   // Luft über dem Flansch (Flansch liegt auf fester Schulter)
halter_bohr  = 6;     // Kabelloch im Flansch
steckkraft   = 20;    // N, Steckkraft; wird von der Schulter aufgenommen, nicht vom TPU

// ---------- Boxboden ----------
box_boden    = 3;     // Bodenstärke
box_wand_h   = 25;    // Wandhöhe über dem Boden
box_r        = 4;     // Eckenradius außen
dach_h       = 4;     // Taschendach (Material über der Tasche, trägt Zapfen und Litzenführung)
kabelrinne_b = 18;    // Kabelrinne nach hinten (+y), Breite. Mindestens so breit, dass der
                      // Kragen bei 90 Grad (Box gekippt) hineintaucht, ohne an den Rinnenkanten
                      // anzuliegen (Prüfung: assert "Rinne zu schmal fuer den Kragen")
kabelrinne_t = 8;     // Kabelrinne, Tiefe ab Unterseite
rinne_fase   = 1;     // Fase am Rinnenrand
winkel_b     = 12;    // Winkelstecker: Körper quer zum Kabel
winkel_h     = 6;     // Winkelstecker: Körperhöhe unter der Buchsen-Öffnung
winkel_l     = 20;    // Winkelstecker: Körperlänge in Kabelrichtung
ecke_b       = 18;    // Aussparung für TPU-Ecke, Kantenlänge

// ---------- Buchseneinsatz im Zapfen (austauschbares Modul, erst die gekaufte Buchse messen!) ----------
buchse_b     = 9.0;   // Buchse samt Platine/Gehäuse, Breite (x)         (R, messen!)
buchse_t     = 3.3;   // Buchse, Dicke (y)                                (R, messen!)
buchse_l     = 7.4;   // Buchse, Länge (Einbautiefe, z)                   (R, messen!)
buchse_spiel = 0.15;  // Spiel je Seite im Buchsenraum
buchse_befest= "kleben"; // "kleben" | "schrauben" (2 x M2)
zapfen_wand_min = 1.2; // Mindestwand des Zapfens um den Buchsenraum, je Seite
litze_d      = 4;     // Litzenführung (Bohrung vom Buchsenraum nach oben ins Box-Innere)
schr_dx      = 3;     // Schrauben M2: Bohrungen bei x = +/- schr_dx
schr_z       = 4;     // Schrauben M2: Höhe über der Buchsen-Öffnung
schr_d       = 1.7;   // Schrauben M2: Bohrung für selbstschneidende Schraube
schr_wand_min= 1.5;   // Schrauben M2: Wand, in die geschraubt wird, mindestens

// ================= Abgeleitete Werte =================
zc          = unterteil_h + (mulde_boden/2)*tan(gefaelle); // Mulden-Boden Mitte (abs.)
z0          = zc + sitz_h;                      // Boxboden gesteckt (abs.), Bezugsebene
box_h       = box_boden + box_wand_h;
kx_u = kragen_b_u;  ky_u = kragen_d_u;  kx_o = kragen_b_o;  ky_o = kragen_d_o;
kragen_kegel = atan((kx_u-kx_o)/2 / kragen_h);
tasche_t    = kragen_h;                         // Tiefe der Tasche = Höhe des Kragens
z_open      = buchse_h;                         // Buchsen-Öffnung über Boxbodenfläche
tip         = kragen_h - spitze_unter;          // Steckerspitze über z0 (= 12)
einsteck    = tip - z_open;                     // Stecklänge bei 0 Grad (= 6,5)
body_top    = tip - stecker_schale;             // Oberkante Umspritzkörper
body_unten  = body_top - stecker_l;
halter_unten= body_unten - halter_boden;
ledge_rel   = halter_unten;                     // feste Schulter, trägt den Flansch
pocket_h    = halter_boden + flansch_luft;
pocket_top  = ledge_rel + pocket_h;
hals_top    = halter_unten + halter_h + 1;      // Hals-Raum der Hülse endet hier
kanal_top   = body_top + 0.3;                   // Körper-Kanal endet hier, darüber der Schacht

hs_x = stecker_b + 2*halter_wand;  hs_y = stecker_d + 2*halter_wand;   // Hülse außen
hf_x = hs_x + 2*flansch_ueber;     hf_y = hs_y + 2*flansch_ueber;      // Flansch
th_x = hs_x + 2*halter_spiel;      th_y = hs_y + 2*halter_spiel;       // Hals im Kragen
pk_x = hf_x + 2*halter_spiel;      pk_y = hf_y + 2*halter_spiel;       // Tasche des Flansches
kn_x = stecker_b + 2*(halter_spiel + 0.3);  kn_y = stecker_d + 2*(halter_spiel + 0.3);

tasche_oeff_x = kx_u + 2*spiel;   tasche_oeff_y = ky_u + 2*spiel;      // an der Bodenfläche
tasche_oben_x = kx_o + 2*spiel;   tasche_oben_y = ky_o + 2*spiel;      // am Taschendach

// Lage bei 90 Grad flach (ohne Kippen), nur als Bezug
zapfen_abst90 = (kragen_h + z_open) - tip;      // Zapfen-Unterseite über Steckerspitze (flach)
eingriff      = kragen_h - einsteck;            // Kragen-Führung, wenn Spitze die Buchse erreicht
zapfen_im_schacht = kragen_h - tip;             // Zapfen taucht schon so tief ein (Spitze berührt)
winkel_unten  = z_open - winkel_h;              // Unterkante Winkelstecker über Bodenfläche
gewicht_kap   = 2*(hohl_x_aussen-hohl_x_innen)*hohl_y*(hohl_h-0.4)/1000 * stahl_dichte * fuellgrad;

// Buchsenraum im Zapfen
bc_b          = buchse_b + 2*buchse_spiel;      // Buchsenraum, x
bc_t          = buchse_t + 2*buchse_spiel;      // Buchsenraum, y
bc_top        = z_open + buchse_l + 0.3;        // Decke des Buchsenraums (ab Boxbodenfläche)
schr_wand     = (zapfen_d - bc_t)/2;            // Wand, in die die Schrauben greifen
dach_top      = tasche_t + dach_h;              // Oberkante Taschendach / Stütze

// Bei 90 Grad gekippt (Rinne zeigt nach -x, Box wird um y gedreht).
// Die Rinne frisst die eine Kragen-Auflage. Die Box liegt mit dem Tasche-Rand (+x) auf der
// Kragen-Oberkante (Drehpunkt P) und kippt zur Rinnenseite, bis die Aussenkante der Bodenflaeche
// den Mulden-Boden beruehrt. Zwei Kandidaten, der kleinere Winkel gilt:
//  A: gerade Boxkante (ohne TPU-Ecke) an der hoechsten Stelle ausserhalb des Freistichs
//     (der Boden steigt nach hinten, +y, mit dem Gefaelle);
//  B: TPU-Ecke (ragt ecke_unter unter die Bodenflaeche) im Freistich, hinten an der geraden Kante.
// Ebene (x = Sockel-x, z ab z0): P = (kipp_px, kragen_h); Bodenflaeche dreht um P mit Winkel w.
kipp_px       = tasche_oeff_y/2;                       // Drehpunkt, Sockel-x
kipp_s        = kipp_px + box_b/2;                     // von P bis zur Aussenkante, entlang der Bodenflaeche
function mulden_z(y) = unterteil_h + (y + mulde_boden/2)*tan(gefaelle) - z0;   // Mulden-Boden ab z0
kipp_yA       = min(box_b/2 - ecke_b, mulde_boden/2 - freistich_b);   // A: letzte Stelle der Kante vor Ecke/Freistich
kipp_yB       = box_b/2 - box_r;                       // B: gerade Kante der TPU-Ecke endet vor dem Radius
kipp_wA       = asin((kragen_h - mulden_z(kipp_yA))/kipp_s);
kipp_cB       = kragen_h - (mulden_z(kipp_yB) - freistich_t);          // = s*sin(w) + ecke_unter*cos(w)
kipp_R        = sqrt(kipp_s*kipp_s + ecke_unter*ecke_unter);
kipp_phi      = atan2(ecke_unter, kipp_s);
kipp_wB       = asin(kipp_cB/kipp_R) - kipp_phi;
kipp_w        = min(kipp_wA, kipp_wB);                 // Kippwinkel in Grad
kipp_ecke_x   = kipp_px - kipp_s*cos(kipp_w) + ecke_unter*sin(kipp_w);   // Sockel-x der Aussenkante (Ecke)
kipp_ecke_z   = kragen_h - kipp_s*sin(kipp_w) - ecke_unter*cos(kipp_w);  // Sockel-z der Ecke ab z0
// Unterseite des Zapfens (Abstand z_open von der Bodenflaeche) an seiner tiefsten Kante (Sockel-x = -zapfen_d/2)
kipp_zapfen_z = kragen_h + z_open*cos(kipp_w) + tan(kipp_w)*(-zapfen_d/2 - kipp_px + z_open*sin(kipp_w));
kipp_abstand  = kipp_zapfen_z - tip;                   // Rest-Abstand Zapfen ueber Steckerspitze
// Kragen taucht auf der Rinnenseite in die Rinne ein: Tiefe senkrecht zur Bodenflaeche und Breite
kipp_tiefe    = (kragen_b_o/2 + kipp_px)*sin(kipp_w);  // Kragen-Oberkante ragt so weit in die Rinne
kipp_kr_halb  = ky_o/2 + (ky_u - ky_o)/2 * (kipp_tiefe/cos(kipp_w))/kragen_h; // halbe Kragenbreite auf Hoehe der Bodenflaeche

// Bei 0/180 Grad: Rinne laeuft ab y = rinne_y0 nach hinten und schneidet die Hinterwand der Tasche an
rinne_y0      = zapfen_d/2 + 0.5;
fuehr_rest    = (tasche_oeff_x - (tasche_oeff_x - tasche_oben_x)*kabelrinne_t/tasche_t)/2
                - kabelrinne_b/2;                               // Rest der Hinterwand je Seite (oben an der Rinne)
fuehr_rest_u  = tasche_oeff_x/2 - kabelrinne_b/2 - rinne_fase;  // Rest an der Bodenflaeche (Fase)
fuehr_band    = tasche_t - kabelrinne_t;                        // durchgehendes Wandband ueber der Rinne

// ================= Nachrechnen =================
// (a) 0 und 180 Grad: Die Rinne kreuzt keine Fuehrungsflaeche, die zum Stecken noetig ist
assert(rinne_y0 >= zapfen_d/2 + 0.25 && rinne_y0 >= schacht_d/2 - 0.01,
  "Rinne beginnt zu nah am Zapfen/Schacht (Feinfuehrung)");
assert(min(fuehr_rest, fuehr_rest_u) >= min_fuehrung,
  "Rinne schneidet die Hinterwand der Tasche zu breit auf (Fuehrungsflaeche zu klein)");
assert(fuehr_band >= min_band, "Rinne zu tief: kein durchgehendes Wandband ueber der Rinne");
// (b) 90 Grad, maximal gekippt: Zapfen bleibt min_abstand_kipp ueber der Steckerspitze
assert(kipp_cB/kipp_R < 1 && (kragen_h - mulden_z(kipp_yA))/kipp_s < 1, "Kippwinkel: Box erreicht den Mulden-Boden nicht (Rechnung ungueltig)");
assert(kipp_ecke_x >= -mulde_boden/2, "Bodenecke trifft bei Kippung die Muldenwand, Rechnung anpassen");
assert(kipp_abstand >= min_abstand_kipp,
  "Zapfen bei 90 Grad und maximaler Kippung zu nah an der Steckerspitze: kragen_h erhoehen oder spitze_unter senken");
// Voraussetzung der Kipp-Rechnung: der Kragen taucht frei in die Rinne ein (sonst stuetzt die Rinnenkante)
assert(kipp_tiefe + 1 <= kabelrinne_t, "Rinne zu flach fuer den Kragen bei maximaler Kippung");
assert(kabelrinne_b/2 >= kipp_kr_halb + 0.3, "Rinne zu schmal fuer den Kragen bei maximaler Kippung");
assert(zapfen_abst90 >= min_abstand90,
  "Zapfen bei 90 Grad zu nah an der Steckerspitze");
assert(eingriff >= min_eingriff,
  "Kragen fuehrt die Tasche zu kurz, bevor die Steckerspitze die Buchse beruehrt");
assert(zapfen_im_schacht >= 1, "Zapfen taucht bei Kontakt noch nicht in den Schacht ein");
assert(einsteck <= stecker_schale && einsteck <= buchse_l, "Stecklaenge passt nicht zu Schale/Buchse");
assert(z_open >= 1, "Zapfen ragt ueber die Bodenflaeche hinaus");
assert(winkel_unten >= -ecke_unter,
  "Winkelstecker ragt weiter unter die Bodenflaeche als die TPU-Ecken");
assert(winkel_b + 0.4 <= kabelrinne_b && z_open <= kabelrinne_t,
  "Winkelstecker passt nicht in die Kabelrinne");
assert(zapfen_b < schacht_b && zapfen_d < schacht_d && schacht_b - zapfen_b <= 1.01 && schacht_d - zapfen_d <= 1.01,
  "Zapfen/Schacht: Feinfuehrung nicht +/- 0,5");
assert((zapfen_b - bc_b)/2 >= zapfen_wand_min && (zapfen_d - bc_t)/2 >= zapfen_wand_min,
  "Zapfen-Wand um die Buchse zu duenn");
assert(bc_top + 0.5 <= tasche_t + dach_h && litze_d < zapfen_d - 2*zapfen_wand_min + 1 && litze_d >= 3,
  "Buchsenraum/Litzenfuehrung passt nicht ins Taschendach");
assert(buchse_befest == "kleben" || buchse_befest == "schrauben", "buchse_befest: kleben oder schrauben");
assert(buchse_befest != "schrauben" || (schr_wand >= schr_wand_min && schr_dx + 1 <= bc_b/2),
  "Schrauben M2: Wand zu duenn oder Bohrung ausserhalb des Buchsenraums");
assert(sitz_h - tan(gefaelle)*box_b/2 >= boden_luft,
  "Boxboden streift am schraegen Mulden-Boden");
assert(kragen_kegel > 5 && kragen_kegel < 30, "Kegelwinkel des Kragens unplausibel");
assert(halter_h - halter_boden < stecker_l - 2, "Huelse zu hoch: Stecker ragt nicht genug heraus");
assert(hals_top < body_top && kanal_top < tip, "Schacht/Kanal-Hoehen passen nicht zur Steckerlage");
assert(z0 + ledge_rel >= rille_t + 2, "Halter-Schulter zu tief: zu wenig Material ueber dem Kabelkanal");
assert(pk_x/2 + 2 <= hohl_x_innen, "Halter-Aufnahme ragt in den Gewichtsraum");
assert(kn_y/2 + 2 <= ky_o/2 + 3, "Kragen-Wand um den Kanal zu duenn");
assert(ky_o/2 - schacht_d/2 >= 2, "Kragen-Wand oben um den Schacht zu duenn");
assert(bohr_d > kabel_d + 1 && halter_bohr > kabel_d + 1, "Kabelloch zu klein");
assert(gewicht_kap >= gewicht_soll, "Gewichtsraum fasst nicht gewicht_soll Stahl");
assert(unterteil_h - (hohl_u + hohl_h) >= 3, "Decke ueber dem Gewichtsraum zu duenn");
assert(dach_top + 1 <= box_h, "Taschendach ragt ueber den Boxrand");
assert(!befestigung || (bef_x + bef_kopf/2 <= mulde_boden/2 - freistich_b && bef_y - bef_kopf/2 > hohl_y/2),
  "Befestigungsloch liegt im Freistich");
echo(str("KIPPEN 90 Grad: Winkel = ", kipp_w, " Grad (A Kante ", kipp_wA, ", B Ecke ", kipp_wB, ") | Rest-Abstand Zapfen ueber Spitze = ", kipp_abstand,
         " | Zapfen-Unterkante z = ", kipp_zapfen_z, " | Ecke x = ", kipp_ecke_x, ", z = ", kipp_ecke_z,
         " | Kragen taucht in Rinne = ", kipp_tiefe, ", halbe Breite dort = ", kipp_kr_halb,
         " | Rinne-Rest 0/180 Grad: ", fuehr_rest, " / ", fuehr_rest_u, ", Band ", fuehr_band));
echo(str("z0 = ", z0, " | Spitze = ", tip, " | Stecklaenge = ", einsteck,
         " | Zapfen-Unterseite 90 Grad flach ueber Spitze = ", zapfen_abst90,
         " | Eingriff = ", eingriff, " | Zapfen im Schacht bei Kontakt = ", zapfen_im_schacht,
         " | Winkelstecker-Unterkante = ", winkel_unten, " | Kegel = ", kragen_kegel,
         " | Gewichtsraum fasst ca. ", gewicht_kap, " g Stahl"));

// ================= Hilfsmodule =================
module rrect(b, r, h) {
  linear_extrude(h) offset(r) square(b - 2*r, center = true);
}
module slab(x, y, z) { translate([-x/2, -y/2, z]) cube([x, y, 0.01]); }

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

module kragen_aussen() {   // Ursprung = z0
  translate([0, 0, -(sitz_h + 3)]) linear_extrude(sitz_h + 3.01) square([kx_u, ky_u], center = true);
  linear_extrude(height = kragen_h, scale = [kx_o/kx_u, ky_o/ky_u])
    square([kx_u, ky_u], center = true);
}

module kragen_innen() {    // Ursprung = z0: Schulter-Tasche, Hals, Körper-Kanal, Schacht
  // Tasche für den Flansch: Boden = feste Schulter, +/- halter_spiel seitlich
  translate([-pk_x/2, -pk_y/2, ledge_rel]) cube([pk_x, pk_y, pocket_h]);
  // Hals für die Hülse
  translate([-th_x/2, -th_y/2, pocket_top - 0.01])
    cube([th_x, th_y, hals_top - pocket_top + 0.01]);
  // Kanal für den Umspritzkörper
  translate([-kn_x/2, -kn_y/2, hals_top - 0.01])
    cube([kn_x, kn_y, kanal_top - hals_top + 0.01]);
  // Schacht 12 x 7 für Metallschale und Zapfen
  translate([-schacht_b/2, -schacht_d/2, kanal_top - 0.01])
    cube([schacht_b, schacht_d, kragen_h - kanal_top + 1]);
  // Einlauf-Fase oben
  hull() {
    slab(schacht_b, schacht_d, kragen_h - schacht_fase);
    slab(schacht_b + 2*schacht_fase + 1, schacht_d + 2*schacht_fase + 1, kragen_h + 0.5);
  }
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
  translate([0, 0, -1]) cylinder(d = bohr_d, h = z0 + ledge_rel + 1.1);
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

module befestigungslocher() {   // zwei Löcher mit Senkung im Muldenboden (unter der Box)
  fz = unterteil_h + (bef_y + mulde_boden/2) * tan(gefaelle);
  for (s = [-1, 1]) {
    translate([s*bef_x, bef_y, -1]) cylinder(d = bef_d, h = fz + 3, $fn = 32);
    translate([s*bef_x, bef_y, fz - bef_kopf_t]) cylinder(d = bef_kopf, h = 10, $fn = 32);
  }
}

module sockel() {
  difference() {
    union() {
      difference() {
        rrect(sockel_aussen, sockel_ecke, unterteil_h + mulde_h);
        mulde_schnitt();
      }
      translate([0, 0, z0]) kragen_aussen();
    }
    translate([0, 0, z0]) kragen_innen();
    kabelweg();
    gewichtsraeume();
    rinne_und_ablauf();
    freistiche();
    if (befestigung) befestigungslocher();
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
function tx(z) = tasche_oeff_x - (tasche_oeff_x - tasche_oben_x) * z / tasche_t;
function ty(z) = tasche_oeff_y - (tasche_oeff_y - tasche_oben_y) * z / tasche_t;

module tasche_cut() {   // konisch, passend zum Kragen mit Spiel; kein Einlauf (sonst Auflage weg)
  translate([0, 0, -0.5]) linear_extrude(height = tasche_t + 0.5,
      scale = [tasche_oben_x/(tx(-0.5)), tasche_oben_y/(ty(-0.5))])
    square([tx(-0.5), ty(-0.5)], center = true);
}

module tasche_huelle(top) {   // Vollkörper um die Tasche, verjüngt
  hull() {
    slab(tx(0) + 2*wand, ty(0) + 2*wand, 0);
    slab(tx(tasche_t) + 2*wand, ty(tasche_t) + 2*wand, top);
  }
}

module zapfen() {   // hängt vom Taschendach nach unten, Unterseite = Buchsen-Öffnung
  hull() {
    slab(zapfen_b - 2*zapfen_fase, zapfen_d - 2*zapfen_fase, z_open);
    slab(zapfen_b, zapfen_d, z_open + zapfen_fase);
    slab(zapfen_b, zapfen_d, tasche_t + 0.5);
  }
}

module rinne_profil(b, t, f) {
  polygon([[-(b/2 + f), -1], [b/2 + f, -1], [b/2 + f, 0], [b/2, f], [b/2, t],
           [-b/2, t], [-b/2, f], [-(b/2 + f), 0]]);
}
module rinne_strang(b, t, f, laenge) {   // vom Zapfen weg nach hinten (+y) bis über die Kante hinaus
  translate([0, rinne_y0 + laenge, 0]) rotate([90, 0, 0])
    linear_extrude(height = laenge) rinne_profil(b, t, f);
}
module rinne_cut() { rinne_strang(kabelrinne_b, kabelrinne_t, rinne_fase, box_b/2 + 5); }
module rinne_huelle() {   // Wandmaterial um die Rinne, damit sie ein Tunnel bleibt
  intersection() {
    rrect(box_b, box_r, box_h);
    rinne_strang(kabelrinne_b + 2*wand, kabelrinne_t + wand, 0, box_b/2 + 5);
  }
}

// Buchseneinsatz: austauschbares Modul. Buchsenraum von unten (offen), Litzenführung nach oben,
// bei buchse_befest = "schrauben" zwei Bohrungen M2 quer durch die +y-Wand in den Buchsenraum.
module buchseneinsatz() {
  translate([-bc_b/2, -bc_t/2, z_open - 0.01]) cube([bc_b, bc_t, bc_top - z_open + 0.01]);
  translate([0, 0, bc_top - 0.01]) cylinder(d = litze_d, h = dach_top - bc_top + 1);
  if (buchse_befest == "schrauben")
    for (s = [-1, 1])
      translate([s*schr_dx, bc_t/2 - 0.01, z_open + schr_z]) rotate([-90, 0, 0])
        cylinder(d = schr_d, h = schr_wand + 1, $fn = 20);
}

module ecken_aussparung() {
  for (sx = [-1, 1], sy = [-1, 1])
    translate([sx*(box_b/2 - ecke_b/2) - ecke_b/2, sy*(box_b/2 - ecke_b/2) - ecke_b/2, -1])
      cube([ecke_b, ecke_b, ecke_unter + 1]);
}

module boxboden() {
  stuetz_top = dach_top;
  difference() {
    union() {
      difference() {
        union() {
          difference() {
            rrect(box_b, box_r, box_h);
            translate([0, 0, box_boden]) rrect(box_b - 2*wand, 2, box_h);
          }
          intersection() {
            rrect(box_b, box_r, box_h);
            union() { rinne_huelle(); tasche_huelle(stuetz_top); }
          }
        }
        rinne_cut();
        tasche_cut();
        ecken_aussparung();
      }
      zapfen();
    }
    buchseneinsatz();
  }
}

// ---------- Kragenprobe: Kragen mit Halter-Aufnahme + Gegenstück mit Tasche und Zapfen ----------
module kragenprobe() {
  h = -ledge_rel + 2;   // Sockelstumpf unter z0
  // Kragen mit Aufnahme auf einem Stumpf (Stumpf-Oberkante = z0 - sitz_h - 3 wie im Sockel)
  translate([-36, 0, 0]) difference() {
    union() {
      translate([-kx_u/2 - 4, -ky_u/2 - 4, 0]) cube([kx_u + 8, ky_u + 8, h]);
      translate([0, 0, h]) kragen_aussen();
    }
    translate([0, 0, h]) kragen_innen();
    translate([0, 0, -1]) cylinder(d = bohr_d, h = h + 1.1);
  }
  // Gegenstück, zum Druck gedreht (Taschendach unten, Zapfen nach oben, keine Stützen)
  translate([36, 0, dach_top]) rotate([180, 0, 0]) difference() {
    union() {
      difference() {
        tasche_huelle(dach_top);
        tasche_cut();
      }
      zapfen();
    }
    buchseneinsatz();
  }
}

// ---------- Ansicht: Baugruppe im Schnitt (y = 0), nur zum Ansehen ----------
module stecker_modell() {
  translate([0, 0, z0 + halter_unten]) color("tomato") halter();
  color("silver") {
    translate([-stecker_b/2, -stecker_d/2, z0 + body_unten]) cube([stecker_b, stecker_d, stecker_l]);
    translate([-schale_b/2, -schale_d/2, z0 + body_top]) cube([schale_b, schale_d, stecker_schale]);
  }
}
module tpu_ecken() {   // TPU-Ecken: sitzen in der Aussparung, ragen ecke_unter unter die Bodenflaeche
  for (sx = [-1, 1], sy = [-1, 1])
    translate([sx*(box_b/2 - ecke_b/2) - ecke_b/2, sy*(box_b/2 - ecke_b/2) - ecke_b/2, -ecke_unter])
      cube([ecke_b, ecke_b, 2*ecke_unter]);
}
module box_komplett() { boxboden(); tpu_ecken(); }
module box_gekippt() {   // Box bei 90 Grad: Drehpunkt P (Tasche-Rand auf der Kragen-Oberkante), Rinne zeigt nach -x
  translate([kipp_px, 0, z0 + kragen_h]) rotate([0, -kipp_w, 0]) translate([-kipp_px, 0, 0])
    rotate([0, 0, 90]) box_komplett();
}
module baugruppe(grad) {
  difference() {
    union() {
      color("lightsteelblue") sockel();
      if (grad == 0) color("khaki") translate([0, 0, z0]) box_komplett();
      else color("khaki") box_gekippt();
      stecker_modell();
    }
    translate([-300, -300, -1]) cube([600, 300, 300]);   // hintere Hälfte (y >= 0) bleibt, Blick von -y auf die Schnittfläche
  }
}
module kippcheck() {   // Schnittmenge Sockel / gekippte Box inkl. TPU-Ecken: muss leer sein
  intersection() { sockel(); box_gekippt(); }
}

// ---------- Auswahl ----------
if (teil == "sockel") sockel();
else if (teil == "boxboden") boxboden();
else if (teil == "halter") halter();
else if (teil == "kragenprobe") kragenprobe();
else if (teil == "baugruppe0") baugruppe(0);
else if (teil == "baugruppe90") baugruppe(90);
else if (teil == "kippcheck") kippcheck();
else if (teil == "alle") {
  color("lightsteelblue") sockel();
  color("khaki") translate([155, 0, 0]) boxboden();
  color("tomato") translate([240, 0, 0]) halter();
  color("palegreen") translate([240, -80, 0]) kragenprobe();
} else assert(false, "teil muss sockel, boxboden, halter, kragenprobe, baugruppe0, baugruppe90, kippcheck oder alle sein");

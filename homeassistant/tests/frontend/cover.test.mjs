/* Tests von „Cover ändern“ (AP A8f, Design 5.5, 6.1, 6.3, 14). Aufruf: node --test homeassistant/tests/frontend
 *
 * jsdom hat kein Canvas, kein `createImageBitmap` und kein `toBlob`: hier nachgebaut. Der Canvas-Mock merkt sich jede Zeichnung
 * (`drawImage`-Argumente) und jede Kodierung (`toBlob`: Breite, Typ, Qualität) und liefert eine Größe, die von der Qualität abhängt.
 * Das Backend ist der Mock aus mock-hass.mjs (`fetchWithAuth` mit POST und DELETE für das Cover, `coverAufrufe`).
 * Geprüft: Menüpunkt (Fähigkeit `cover`, Serie und Einzeltitel), Zuschneiden (Pfeilknöpfe, Pfeiltasten, Ziehen, Regler, Grenzen),
 * Ausgabe 1024 × 1024 JPEG mit Qualität 0,85 und weniger bei großem Ergebnis, Fehlertexte, „Zurück zum automatischen Cover“.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, MIT_DOM } from './dom-helfer.mjs';

const { ausschnitt, sendeCover, kodiereQuadrat, coverFehlerText, ladeBild, KANTE, QUALITAETEN } = await import('../../custom_components/tobibox/frontend/seiten/cover.js');
const { COVER, FEHLER, SERIE } = await import('../../custom_components/tobibox/frontend/texte.js');

const MIB = 1024 * 1024;

const folge = (name, anzeige) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * MIB, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [] });

function beispiele(m) {
  const b = m.backend.serien;
  b.lied = { id: 'lied', name: 'Wiegenlied', typ: 'normal', ordner: 'Wiegenlied', pruefen: false, hinweise: [], art: 'musik', einzeln: true, dauer_s: 66, cover_stand: null, folgen: [folge('wiegenlied.mp3', 'Wiegenlied')] };
  b.s1.cover_stand = 'ab12cd34';
  b.s2.cover_stand = '99887766';
  b.s2.cover_quelle = 'eigen'; // s2 hat ein eigenes Foto, s1 nur das automatische Cover
  b.s2.cover_auto = 'aa00bb11';
}

/* Canvas, Bild und Kodierung nachbauen. `groesse(q)` = Größe des JPEG in Bytes bei Qualität q. */
function werkzeuge({ breite = 4000, hoehe = 3000, groesse = () => 200 * 1024 } = {}) {
  const proto = window.HTMLCanvasElement.prototype;
  const alt = { getContext: proto.getContext, toBlob: proto.toBlob, cib: globalThis.createImageBitmap };
  const W = { zeichnungen: [], kodierungen: [], bitmaps: [], optionen: [], geschlossen: 0 };
  proto.getContext = function getContext() {
    const c = this;
    return { fillStyle: '', imageSmoothingQuality: '', fillRect() {}, drawImage: (...a) => W.zeichnungen.push({ breite: c.width, hoehe: c.height, a }) };
  };
  proto.toBlob = function toBlob(cb, typ, q) {
    W.kodierungen.push({ breite: this.width, hoehe: this.height, typ, q });
    cb(new Blob([new Uint8Array(groesse(q))], { type: typ }));
  };
  globalThis.createImageBitmap = async (datei, opt) => {
    W.optionen.push(opt);
    if (datei.rauscht) throw new Error('kein Bild');
    const bmp = { width: breite, height: hoehe, close: () => { W.geschlossen += 1; } };
    W.bitmaps.push(bmp);
    return bmp;
  };
  W.zurueck = () => { proto.getContext = alt.getContext; proto.toBlob = alt.toBlob; if (alt.cib) globalThis.createImageBitmap = alt.cib; else delete globalThis.createImageBitmap; };
  return W;
}

function datei(name = 'foto.jpg', typ = 'image/jpeg', bytes = 1000) {
  return new window.File([new Uint8Array(bytes)], name, { type: typ });
}

async function oeffne(id = 's1', opts = {}) {
  const s = await seite({ hash: '', ...opts });
  beispiele(s.m);
  await geheZu(s, `#serie-${id}`);
  await s.flush(10);
  return s;
}

const blatt = (s) => s.q('dialog.blatt[open]');
const titelBlatt = (s) => s.q('dialog.blatt[open] #blatt-t')?.textContent.trim();
const klick = async (s, el) => { assert.ok(el, 'Element zum Klicken fehlt'); el.click(); await s.flush(10); };
const oeffneCover = async (s) => { await klick(s, s.q('[data-menue-serie]')); await klick(s, s.q('dialog.blatt[open] [data-menue="cover"]')); };
const fehlerMeldungen = (s) => s.qa('.toast.err .tmsg').map((x) => x.textContent);
const meldungen = (s) => s.qa('.toast:not(.err) .tmsg').map((x) => x.textContent);
const leisteKnopf = (s, text) => s.qa('dialog.blatt[open] .knoepfe button').find((b) => b.textContent.trim() === text);
const vorschau = (s) => s.q('canvas[data-cover-vorschau]');
const mitteVon = (s) => vorschau(s).dataset.mitte.split(',').map(Number);

/* Foto „wählen“: das Eingabefeld bekommt die Datei, das change-Ereignis löst das Laden aus. */
async function waehle(s, f) {
  const eingabe = s.q('input[data-cover-datei]');
  assert.ok(eingabe, 'Feld zur Fotowahl fehlt');
  Object.defineProperty(eingabe, 'files', { value: [f], configurable: true });
  eingabe.dispatchEvent(new window.Event('change', { bubbles: true }));
  await s.flush(12);
  await warte(5); // das Zeichnen der Vorschau läuft einen Takt später
  await s.flush(4);
}

function zeiger(ziel, art, x, y) {
  const e = new window.Event(art, { bubbles: true, cancelable: true });
  Object.assign(e, { clientX: x, clientY: y, button: 0, pointerId: 1 });
  ziel.dispatchEvent(e);
}

/* ------------------------------------------------------------------ reine Funktionen */

test('ausschnitt: Regler 0 ist das ganze Quadrat der kurzen Seite, 100 ein Viertel davon; das Quadrat bleibt im Foto', () => {
  const a = ausschnitt(4000, 3000, 0);
  assert.deepEqual([a.seite, a.cx, a.cy, a.sx, a.sy], [3000, 2000, 1500, 500, 0]);
  const k = ausschnitt(4000, 3000, 100);
  assert.equal(k.seite, 750);
  const rand = ausschnitt(4000, 3000, 100, { x: -500, y: 99999 });
  assert.deepEqual([rand.sx, rand.sy], [0, 2250], 'links oben begrenzt, unten begrenzt');
  const hoch = ausschnitt(1000, 3000, 50, { x: 500, y: 100 });
  assert.equal(hoch.seite, 1000 / 2.5);
  assert.equal(hoch.sy, 0);
  assert.equal(ausschnitt(1000, 1000, 'x').seite, 1000, 'Unsinn gilt als 0');
  assert.equal(ausschnitt(1000, 1000, 500).seite, 250, 'über 100 gilt 100');
});

test('coverFehlerText: Netzfehler und Größe haben eigene Texte, alles andere kommt aus texte.js', () => {
  const ctx = { fehlerText: (c) => `T:${c}` };
  assert.equal(coverFehlerText(ctx, 'verbindung'), COVER.netz);
  assert.equal(coverFehlerText(ctx, 'datei_zu_gross'), COVER.bild_zu_gross, 'nicht der Text für Dateien mit 2 GB');
  assert.equal(coverFehlerText(ctx, 'zu_viele_aenderungen'), 'T:zu_viele_aenderungen');
  assert.ok(!/GB|Eingang/.test(COVER.bild_zu_gross));
});

test('sendeCover: POST mit image/jpeg, DELETE mit quelle=eigen; Fehlercodes aus der Antwort, sonst aus dem HTTP-Status', async () => {
  const aufrufe = [];
  const antwort = (status, obj, json = true) => ({ ok: status < 300, status, json: async () => { if (!json) throw new Error('kein JSON'); return obj; } });
  let naechste;
  const hass = { fetchWithAuth: async (p, o) => { aufrufe.push([p, o]); if (naechste instanceof Error) throw naechste; return naechste; } };
  naechste = antwort(200, { v: 1, serie_id: 'a b', cover_stand: 'ab12cd34', cover_quelle: 'eigen' });
  const blob = new Blob(['x']);
  assert.deepEqual(await sendeCover(hass, 'a b', blob), { v: 1, serie_id: 'a b', cover_stand: 'ab12cd34', cover_quelle: 'eigen' });
  assert.equal(aufrufe[0][0], '/api/tobibox/cover/a%20b');
  assert.equal(aufrufe[0][1].method, 'POST');
  assert.equal(aufrufe[0][1].headers['Content-Type'], 'image/jpeg');
  assert.equal(aufrufe[0][1].body, blob);
  await sendeCover(hass, 'x');
  assert.equal(aufrufe[1][0], '/api/tobibox/cover/x?quelle=eigen');
  assert.equal(aufrufe[1][1].method, 'DELETE');
  assert.equal(aufrufe[1][1].body, undefined);
  const code = async (n) => { naechste = n; try { await sendeCover(hass, 'x', blob); } catch (e) { return e.code; } return 'kein Fehler'; };
  assert.equal(await code(antwort(400, { fehler: { code: 'cover_ungueltig', text: 'x' } })), 'cover_ungueltig');
  assert.equal(await code(antwort(413, null, false)), 'datei_zu_gross', 'HA selbst antwortet bei sehr großem Rumpf ohne JSON');
  assert.equal(await code(antwort(429, null, false)), 'zu_viele_aenderungen');
  assert.equal(await code(antwort(403, null, false)), 'unauthorized');
  assert.equal(await code(antwort(500, null, false)), 'unknown_error');
  assert.equal(await code(antwort(200, { v: 1 })), 'unknown_error', '200 ohne cover_stand ist keine gültige Antwort');
  assert.equal(await code(new TypeError('Failed to fetch')), 'verbindung');
});

test('kodiereQuadrat: 1024 × 1024, JPEG, Qualität 0,85; über 1,5 MiB Stufe für Stufe weniger; über 3 MiB trotz kleinster Stufe: Fehler', MIT_DOM, async () => {
  const s = await seite({ hash: '' });
  let W = werkzeuge({ groesse: () => 100 * 1024 });
  try {
    const foto = { bild: { width: 4000, height: 3000 }, b: 4000, h: 3000 };
    const a = ausschnitt(4000, 3000, 0);
    const r = await kodiereQuadrat(foto, a);
    assert.equal(r.qualitaet, 0.85);
    assert.deepEqual(W.zeichnungen.at(-1).a.slice(1), [a.sx, a.sy, a.seite, a.seite, 0, 0, KANTE, KANTE]);
    assert.deepEqual(W.kodierungen, [{ breite: 1024, hoehe: 1024, typ: 'image/jpeg', q: 0.85 }]);
    W.zurueck();
    W = werkzeuge({ groesse: (q) => (q > 0.6 ? 2 * MIB : 1 * MIB) });
    const r2 = await kodiereQuadrat(foto, a);
    assert.deepEqual(W.kodierungen.map((k) => k.q), [0.85, 0.75, 0.65, 0.55]);
    assert.equal(r2.blob.size, 1 * MIB);
    W.zurueck();
    W = werkzeuge({ groesse: () => 4 * MIB });
    await assert.rejects(kodiereQuadrat(foto, a), { code: 'cover_zu_gross' });
    assert.equal(W.kodierungen.length, QUALITAETEN.length, 'alle Stufen versucht');
    W.zurueck();
    W = werkzeuge({ groesse: () => 2 * MIB });
    assert.equal((await kodiereQuadrat(foto, a)).qualitaet, QUALITAETEN.at(-1), 'bis 3 MiB erlaubt: die letzte Stufe gilt');
  } finally { W.zurueck(); weg(); }
  assert.ok(s);
});

test('ladeBild: Ausrichtung nach EXIF angefordert; ohne die Option ein zweiter Versuch; unlesbar gibt null', MIT_DOM, async () => {
  await seite({ hash: '' });
  const W = werkzeuge();
  try {
    const r = await ladeBild(datei());
    assert.deepEqual(W.optionen, [{ imageOrientation: 'from-image' }]);
    assert.deepEqual([r.b, r.h], [4000, 3000]);
    const alt = globalThis.createImageBitmap;
    let n = 0;
    globalThis.createImageBitmap = async (d, opt) => { n += 1; if (opt) throw new TypeError('Option unbekannt'); return { width: 10, height: 20 }; };
    assert.deepEqual([(await ladeBild(datei())).b, n], [10, 2], 'alter Browser ohne Option');
    globalThis.createImageBitmap = async () => { throw new Error('kein Bild'); };
    assert.equal(await ladeBild(datei()), null);
    globalThis.createImageBitmap = alt;
  } finally { W.zurueck(); weg(); }
});

/* ------------------------------------------------------------------ Menü und Blatt */

test('Menü: „Cover ändern“ für Serie und Einzeltitel nach „Name ändern“; ohne die Fähigkeit „cover“ gibt es den Punkt nicht', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await klick(s, s.q('[data-menue-serie]'));
  const ids = s.qa('dialog.blatt[open] [data-menue]').map((x) => x.dataset.menue);
  assert.equal(ids.indexOf('cover'), ids.indexOf('name') + 1);
  assert.equal(s.q('dialog.blatt[open] [data-menue="cover"]').textContent.trim(), SERIE.menue.cover);
  await geheZu(s, '#serie-lied');
  await s.flush(8);
  await klick(s, s.q('[data-menue-serie]'));
  assert.ok(s.q('dialog.blatt[open] [data-menue="cover"]'), 'Einzeltitel auch');
  weg();
  const o = await oeffne('s1', { faehigkeiten: ['medien', 'bibliothek', 'korrektur', 'serie_loeschen'] });
  await klick(o, o.q('[data-menue-serie]'));
  assert.ok(o.q('dialog.blatt[open] [data-menue="name"]'));
  assert.equal(o.q('dialog.blatt[open] [data-menue="cover"]'), null, 'ohne Fähigkeit kein Menüpunkt');
  weg();
});

test('Blatt „Cover für „Name““: „Foto wählen“ mit <input type=file accept=image/*>; ohne eigenes Foto kein „Zurück“; Fokus auf „Foto wählen“', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await oeffneCover(s);
  assert.equal(titelBlatt(s), 'Cover für „Die drei ???“');
  const eingabe = s.q('dialog.blatt[open] input[type="file"]');
  assert.equal(eingabe.getAttribute('accept'), 'image/*');
  const knopf = s.q('[data-cover-waehlen]');
  assert.equal(knopf.textContent.trim(), 'Foto wählen');
  assert.equal(s.q('[data-cover-zurueck]'), null, 'nur mit eigenem Foto');
  assert.equal(s.q('[data-cover-vorschau]'), null, 'noch kein Foto: keine Vorschau');
  assert.equal(s.el.shadowRoot.activeElement, knopf, 'der Fokus liegt auf dem Knopf, nicht auf dem versteckten Feld');
  let geklickt = 0;
  eingabe.click = () => { geklickt += 1; };
  await klick(s, knopf);
  assert.equal(geklickt, 1, 'der Knopf öffnet die Dateiwahl');
  assert.deepEqual(leisteKnopf(s, SERIE.abbrechen) && 'da', 'da');
  assert.equal(leisteKnopf(s, COVER.speichern), undefined, '„Speichern“ erst mit einem Foto');
  weg();
});

/* ------------------------------------------------------------------ Zuschneiden */

test('Zuschneiden: Vorschau, vier Pfeilknöpfe (44 px und mehr, mit Namen), Regler; die Pfeile verschieben den Ausschnitt in Schritten und bleiben im Foto', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    await waehle(s, datei());
    assert.deepEqual(W.optionen, [{ imageOrientation: 'from-image' }]);
    const c = vorschau(s);
    assert.ok(c, 'Vorschau da');
    assert.equal(c.width, 560, 'doppelt aufgelöst für scharfe Bildschirme');
    assert.ok(leisteKnopf(s, COVER.speichern), '„Speichern“ erscheint mit dem Foto');
    assert.deepEqual(mitteVon(s), [2000, 1500]);
    const letzte = W.zeichnungen.at(-1);
    assert.deepEqual(letzte.a.slice(1), [500, 0, 3000, 3000, 0, 0, 560, 560], 'ganzes Quadrat der kurzen Seite, mittig');
    const namen = s.qa('[data-cover-pfeil]').map((b) => b.getAttribute('aria-label'));
    assert.deepEqual(namen, [COVER.pfeil.links, COVER.pfeil.hoch, COVER.pfeil.runter, COVER.pfeil.rechts]);
    const pfeil = (r) => s.q(`[data-cover-pfeil="${r}"]`);
    // Regler auf 100: Ausschnitt 750, Pfeile in Schritten von 75
    const regler = s.q('input[data-cover-regler]');
    assert.equal(regler.getAttribute('type'), 'range');
    assert.equal(s.q('label[for="cv-regler"]').textContent, 'Ausschnitt größer oder kleiner');
    regler.value = '100';
    regler.dispatchEvent(new window.Event('input', { bubbles: true }));
    assert.equal(c.dataset.regler, '100');
    assert.equal(W.zeichnungen.at(-1).a[3], 750, 'der Ausschnitt wird kleiner');
    await klick(s, pfeil('links')); // das Foto wandert nach links: der Ausschnitt nach rechts
    assert.deepEqual(mitteVon(s), [2075, 1500]);
    await klick(s, pfeil('rechts'));
    await klick(s, pfeil('rechts'));
    assert.deepEqual(mitteVon(s), [1925, 1500]);
    await klick(s, pfeil('hoch'));
    assert.deepEqual(mitteVon(s), [1925, 1575]);
    await klick(s, pfeil('runter'));
    await klick(s, pfeil('runter'));
    assert.deepEqual(mitteVon(s), [1925, 1425]);
    for (let i = 0; i < 40; i += 1) pfeil('runter').click();
    for (let i = 0; i < 60; i += 1) pfeil('rechts').click();
    assert.deepEqual(mitteVon(s), [375, 375], 'am Rand (Foto nach unten und nach rechts) bleibt das Quadrat im Foto: Mitte höchstens bis halbe Seite vom Rand');
    // größer machen holt den Ausschnitt zurück ins Foto, ohne die Mitte zu verlieren
    regler.value = '0';
    regler.dispatchEvent(new window.Event('input', { bubbles: true }));
    assert.deepEqual(mitteVon(s), [1500, 1500]);
    weg();
  } finally { W.zurueck(); }
});

test('Zuschneiden: Pfeiltasten auf der Vorschau verschieben wie die Knöpfe; andere Tasten und Tasten mit Strg bleiben unberührt', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    await waehle(s, datei());
    const c = vorschau(s);
    const taste = (key, extra = {}) => { const e = new window.KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...extra }); c.dispatchEvent(e); return e; };
    // Regler 100 → Schritt 75
    const regler = s.q('input[data-cover-regler]');
    regler.value = '100'; regler.dispatchEvent(new window.Event('input', { bubbles: true }));
    assert.equal(taste('ArrowLeft').defaultPrevented, true);
    assert.deepEqual(mitteVon(s), [2075, 1500]);
    taste('ArrowDown');
    assert.deepEqual(mitteVon(s), [2075, 1425]);
    taste('ArrowUp'); taste('ArrowRight');
    assert.deepEqual(mitteVon(s), [2000, 1500]);
    assert.equal(taste('a').defaultPrevented, false);
    assert.equal(taste('ArrowLeft', { ctrlKey: true }).defaultPrevented, false);
    assert.deepEqual(mitteVon(s), [2000, 1500]);
    assert.equal(c.tabIndex, 0, 'mit der Tastatur erreichbar');
    assert.ok(c.getAttribute('aria-label').includes('Pfeiltasten'));
    weg();
  } finally { W.zurueck(); }
});

test('Zuschneiden: Ziehen mit Finger oder Maus; das Foto folgt dem Zeiger (Mitte läuft entgegen), Loslassen beendet das Ziehen', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    await waehle(s, datei());
    const c = vorschau(s);
    const regler = s.q('input[data-cover-regler]');
    regler.value = '100'; regler.dispatchEvent(new window.Event('input', { bubbles: true })); // Ausschnitt 750 px auf 280 px Vorschau
    zeiger(c, 'pointerdown', 100, 100);
    zeiger(c, 'pointermove', 128, 100); // 28 px nach rechts = 75 Bildpunkte
    assert.deepEqual(mitteVon(s), [1925, 1500]);
    zeiger(c, 'pointermove', 128, 128);
    assert.deepEqual(mitteVon(s), [1925, 1425]);
    zeiger(c, 'pointerup', 128, 128);
    zeiger(c, 'pointermove', 0, 0);
    assert.deepEqual(mitteVon(s), [1925, 1425], 'nach dem Loslassen bewegt sich nichts mehr');
    zeiger(c, 'pointermove', 500, 500); // ohne vorheriges Drücken
    assert.deepEqual(mitteVon(s), [1925, 1425]);
    weg();
  } finally { W.zurueck(); }
});

test('Zuschneiden: „Anderes Foto wählen“ nimmt ein neues Foto, der Regler beginnt wieder bei „ganz“; das alte Bild wird freigegeben', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    await waehle(s, datei());
    const regler = s.q('input[data-cover-regler]');
    regler.value = '60'; regler.dispatchEvent(new window.Event('input', { bubbles: true }));
    await waehle(s, datei('zweites.jpg'));
    assert.equal(W.bitmaps.length, 2);
    assert.equal(W.geschlossen, 1, 'das erste Bild ist freigegeben');
    assert.equal(s.q('input[data-cover-regler]').value, '0');
    assert.deepEqual(mitteVon(s), [2000, 1500]);
    s.q('dialog.blatt[open] .blatt-x').click();
    await s.flush(8);
    assert.equal(W.geschlossen, 2, 'mit dem Blatt ist auch das zweite frei');
    weg();
  } finally { W.zurueck(); }
});

/* ------------------------------------------------------------------ Speichern */

test('Speichern: ein JPEG-Quadrat 1024 × 1024 (Qualität 0,85) als POST /api/tobibox/cover/<id>; Meldung, Blatt zu, das neue Cover erscheint ohne Neuladen', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('s1');
    const serieGetVorher = s.m.aufrufe('tobibox/serie/get').length;
    await oeffneCover(s);
    await waehle(s, datei());
    s.q('input[data-cover-regler]').value = '50';
    s.q('input[data-cover-regler]').dispatchEvent(new window.Event('input', { bubbles: true }));
    await klick(s, leisteKnopf(s, COVER.speichern));
    await s.flush(10);
    assert.equal(s.m.coverAufrufe.length, 1);
    const a = s.m.coverAufrufe[0];
    assert.deepEqual([a.methode, a.pfad, a.typ], ['POST', '/api/tobibox/cover/s1', 'image/jpeg']);
    assert.equal(a.groesse, 200 * 1024);
    const k = W.kodierungen.at(-1);
    assert.deepEqual([k.breite, k.hoehe, k.typ, k.q], [1024, 1024, 'image/jpeg', 0.85]);
    const z = W.zeichnungen.at(-1);
    assert.equal(z.breite, 1024);
    assert.deepEqual(z.a.slice(5), [0, 0, 1024, 1024], 'auf das ganze Quadrat gezeichnet');
    assert.equal(z.a[3], 3000 / 2.5, 'mit dem Ausschnitt des Reglers');
    assert.ok(meldungen(s).includes(COVER.gespeichert), `Meldungen: ${meldungen(s)}`);
    assert.equal(blatt(s), null, 'das Blatt schließt');
    assert.deepEqual(fehlerMeldungen(s), []);
    // Neuer Stand ohne Neuladen: kein weiteres serie/get, das große Cover fragt den neuen Stand ab
    const stand = s.m.backend.serien.s1.cover_stand;
    assert.notEqual(stand, 'ab12cd34');
    assert.equal(s.m.aufrufe('tobibox/serie/get').length, serieGetVorher, 'kein Neuladen der Serie');
    assert.equal(s.q('.cover.se-xl').dataset.stand, stand);
    assert.ok(s.m.covers.includes(`/api/tobibox/cover/s1?groesse=gross&v=${stand}`), `Anfragen: ${s.m.covers.slice(-3)}`);
    assert.equal(s.m.covers.filter((p) => p.includes('v=ab12cd34')).length, 1, 'das alte Bild wurde nicht noch einmal geholt');
    assert.equal(s.el._covers.stand('s1'), stand, 'Cover-Speicher kennt den Stand');
    // Das Blatt beim nächsten Öffnen bietet jetzt „Zurück …“ an
    await oeffneCover(s);
    assert.ok(s.q('[data-cover-zurueck]'));
    weg();
  } finally { W.zurueck(); }
});

test('Speichern: bei mehr als 1,5 MiB sinkt die Qualität, bis es passt; gesendet wird das kleinere Ergebnis', MIT_DOM, async () => {
  const W = werkzeuge({ groesse: (q) => (q >= 0.75 ? 2.2 * MIB : 1.3 * MIB) });
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    await waehle(s, datei());
    await klick(s, leisteKnopf(s, COVER.speichern));
    await s.flush(10);
    assert.deepEqual(W.kodierungen.map((k) => k.q), [0.85, 0.75, 0.65]);
    assert.equal(s.m.coverAufrufe.length, 1);
    assert.equal(s.m.coverAufrufe[0].groesse, Math.floor(1.3 * MIB));
    assert.equal(blatt(s), null);
    weg();
  } finally { W.zurueck(); }
});

test('Speichern: ein Ergebnis über 3 MiB wird nicht gesendet; Fehlermeldung bleibt, das Blatt bleibt offen', MIT_DOM, async () => {
  const W = werkzeuge({ groesse: () => 3.5 * MIB });
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    await waehle(s, datei());
    await klick(s, leisteKnopf(s, COVER.speichern));
    await s.flush(10);
    assert.equal(s.m.coverAufrufe.length, 0, 'nichts gesendet');
    assert.deepEqual(fehlerMeldungen(s), [COVER.nach_verkleinern_zu_gross]);
    assert.ok(blatt(s), 'das Blatt bleibt');
    weg();
  } finally { W.zurueck(); }
});

test('Fehler bei der Wahl: Foto über 20 MB und Datei ohne Bild; die Meldung bleibt stehen (mit „OK“), das Blatt bleibt bei „Foto wählen“', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    const gross = datei('riesig.jpg', 'image/jpeg', 10);
    Object.defineProperty(gross, 'size', { value: 21 * MIB });
    await waehle(s, gross);
    assert.deepEqual(fehlerMeldungen(s), ['Das Foto ist zu groß (mehr als 20 MB). Nimm ein kleineres.']);
    assert.equal(W.bitmaps.length, 0, 'zu große Fotos werden nicht erst decodiert');
    assert.equal(s.q('[data-cover-vorschau]'), null);
    assert.ok(s.q('[data-cover-waehlen]'), 'weiter bei „Foto wählen“');
    // genau 20 MB sind noch erlaubt
    const grenze = datei('grenze.jpg', 'image/jpeg', 10);
    Object.defineProperty(grenze, 'size', { value: 20 * MIB });
    await waehle(s, grenze);
    assert.ok(s.q('[data-cover-vorschau]'), '20 MB gehen');
    weg();
  } finally { W.zurueck(); }
  const W2 = werkzeuge();
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    await waehle(s, datei('brief.pdf', 'application/pdf'));
    assert.deepEqual(fehlerMeldungen(s), ['Das ist kein Bild. Bitte ein Foto wählen.']);
    assert.equal(W2.bitmaps.length, 0, 'ein PDF wird nicht als Bild versucht');
    s.qa('.toast.err .tok')[0].click();
    await s.flush(4);
    assert.deepEqual(fehlerMeldungen(s), [], '„OK“ räumt die Meldung weg');
    const kaputt = datei('kaputt.jpg', 'image/jpeg');
    kaputt.rauscht = true; // der Mock-Decoder wirft
    await waehle(s, kaputt);
    assert.deepEqual(fehlerMeldungen(s), ['Das ist kein Bild. Bitte ein Foto wählen.'], 'Typ stimmt, Decoder lehnt ab');
    assert.equal(s.q('[data-cover-vorschau]'), null);
    // die Meldung steht im Blatt (Top-Layer), nicht darunter
    assert.ok(s.q('dialog.blatt[open] .toast.err'), 'Meldung im offenen Blatt');
    weg();
  } finally { W2.zurueck(); }
});

test('Fehler vom Backend beim Speichern: Größe, Bild, zu viele Änderungen, NAS, Netz; die Meldung bleibt, das Blatt bleibt, ein zweiter Versuch geht', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    await waehle(s, datei());
    const faelle = [
      [{ code: 'datei_zu_gross', status: 413 }, COVER.bild_zu_gross],
      [{ code: 'cover_ungueltig', status: 400 }, FEHLER.cover_ungueltig],
      [{ code: 'zu_viele_aenderungen', status: 429 }, FEHLER.zu_viele_aenderungen],
      [{ code: 'unauthorized', status: 403 }, FEHLER.unauthorized.replace(/\{[a-z_]+\}/g, '')],
      ['netz', COVER.netz],
    ];
    let n = 0;
    for (const [fehler, text] of faelle) {
      if (fehler === 'netz') s.m.opts.coverNetz = true; else s.m.opts.coverFehler = [fehler];
      await klick(s, leisteKnopf(s, COVER.speichern));
      await s.flush(10);
      n += 1;
      assert.equal(s.m.coverAufrufe.length, n, 'ein Aufruf je Versuch');
      const m = fehlerMeldungen(s);
      assert.equal(m.length, n, `Fehler bleiben stehen und stapeln sich: ${m}`);
      assert.ok(m.at(-1).startsWith(text.split(' ').slice(0, 4).join(' ')) || m.at(-1) === text, `Text zu ${fehler.code ?? fehler}: ${m.at(-1)}`);
      assert.ok(blatt(s), 'das Blatt bleibt offen');
      assert.ok(s.q('[data-cover-vorschau]'), 'der Zuschnitt bleibt');
      assert.equal(s.q('.cover.se-xl').dataset.stand, 'ab12cd34', 'das Cover ändert sich nicht');
    }
    assert.equal(fehlerMeldungen(s)[4], COVER.netz);
    assert.ok(!fehlerMeldungen(s).some((t) => t.includes('2 GB')), 'nie der Text für Dateien mit 2 GB');
    await klick(s, leisteKnopf(s, COVER.speichern)); // nun klappt es
    await s.flush(10);
    assert.equal(blatt(s), null);
    assert.ok(meldungen(s).includes(COVER.gespeichert));
    assert.equal(fehlerMeldungen(s).length, 5, 'ein Erfolg entfernt keinen Fehler (6.3)');
    weg();
  } finally { W.zurueck(); }
});

test('Fehler „Das gibt es nicht mehr“ beim Speichern: Meldung, das Blatt schließt, die Seite lädt neu', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('s1');
    await oeffneCover(s);
    await waehle(s, datei());
    s.m.opts.coverFehler = [{ code: 'serie_nicht_gefunden', status: 404 }];
    const vorher = s.m.aufrufe('tobibox/serie/get').length;
    await klick(s, leisteKnopf(s, COVER.speichern));
    await s.flush(12);
    assert.deepEqual(fehlerMeldungen(s), [FEHLER.serie_nicht_gefunden]);
    assert.equal(blatt(s), null);
    assert.ok(s.m.aufrufe('tobibox/serie/get').length > vorher, 'neu geladen');
    weg();
  } finally { W.zurueck(); }
});

test('Zurück zum automatischen Cover: nur mit eigenem Foto; DELETE ?quelle=eigen, Meldung, das Blatt schließt, das automatische Cover erscheint ohne Neuladen', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('s2');
    assert.equal(s.q('.cover.se-xl').dataset.stand, '99887766');
    await oeffneCover(s);
    const knopf = s.q('[data-cover-zurueck]');
    assert.ok(knopf, 'eigenes Foto: der Knopf ist da');
    assert.equal(knopf.textContent.trim(), 'Zurück zum automatischen Cover');
    assert.ok(knopf.closest('.se-apart'), 'abgesetzt');
    assert.ok(knopf.classList.contains('link'), 'Textknopf');
    const serieGet = s.m.aufrufe('tobibox/serie/get').length;
    await klick(s, knopf);
    await s.flush(8);
    assert.equal(s.m.coverAufrufe.length, 1);
    assert.deepEqual([s.m.coverAufrufe[0].methode, s.m.coverAufrufe[0].pfad], ['DELETE', '/api/tobibox/cover/s2?quelle=eigen']);
    assert.ok(meldungen(s).includes(COVER.zurueck_fertig));
    assert.equal(blatt(s), null);
    assert.equal(s.q('.cover.se-xl').dataset.stand, 'aa00bb11', 'das automatische Cover kommt zurück');
    assert.equal(s.m.aufrufe('tobibox/serie/get').length, serieGet, 'ohne Neuladen');
    await oeffneCover(s);
    assert.equal(s.q('[data-cover-zurueck]'), null, 'jetzt gibt es kein eigenes Foto mehr');
    weg();
  } finally { W.zurueck(); }
});

test('Zurück zum automatischen Cover: ein Fehler (zu viele Änderungen) bleibt als Meldung, das Blatt bleibt offen', MIT_DOM, async () => {
  const s = await oeffne('s2');
  s.m.opts.coverFehler = [{ code: 'zu_viele_aenderungen', status: 429 }];
  await oeffneCover(s);
  await klick(s, s.q('[data-cover-zurueck]'));
  await s.flush(6);
  assert.deepEqual(fehlerMeldungen(s), [FEHLER.zu_viele_aenderungen]);
  assert.ok(blatt(s), 'das Blatt bleibt');
  assert.ok(s.q('[data-cover-zurueck]'), 'zweiter Versuch möglich');
  await klick(s, s.q('[data-cover-zurueck]'));
  await s.flush(8);
  assert.equal(s.m.coverAufrufe.length, 2);
  assert.equal(blatt(s), null);
  weg();
});

test('Einzeltitel: dasselbe Blatt und derselbe POST mit der Kennung des Einzeltitels', MIT_DOM, async () => {
  const W = werkzeuge();
  try {
    const s = await oeffne('lied');
    await oeffneCover(s);
    assert.equal(titelBlatt(s), 'Cover für „Wiegenlied“');
    await waehle(s, datei());
    await klick(s, leisteKnopf(s, COVER.speichern));
    await s.flush(10);
    assert.equal(s.m.coverAufrufe[0].pfad, '/api/tobibox/cover/lied');
    assert.ok(s.q('.cover.se-xl').dataset.stand, 'das Cover ist da (vorher keins)');
    assert.equal(s.q('.cover.se-xl').dataset.bild, '1');
    weg();
  } finally { W.zurueck(); }
});

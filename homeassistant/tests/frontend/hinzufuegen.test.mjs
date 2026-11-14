/* Tests von „Hinzufügen“ (Paket A11a, Design 5.6, 5.6a, 6.1, 6.3, 7.3, 14; Entscheidungen X5, X11, X12, G2, G26a bis G26d, N15, N26, R17-4).
 * Aufruf: node --test homeassistant/tests/frontend
 *
 * Geprüft: Seite (Knöpfe nach Zeiger, Ziehfläche, sonst nichts), „+“ am Handy, Blatt „Was lädst du hoch?“ (Zeile, vier Kacheln, „Abbrechen“ oben
 * rechts), Vorschau und Sätze je Weg (a, b, c, e), „Wohin soll es?“, „Ändern“ behält die Eingaben, Prüfungen vor „Hochladen“, die Felder des Uploads
 * (`gruppe`, `gruppe_anzahl`, …), „Datei 2 von 3“, der Satz „Bildschirm anlassen …“ nur während des Hochladens, Wake Lock (auch ohne `navigator.wakeLock`),
 * Warten, Abbrechen, Unterbrechung, Fehlercodes (Format, zu groß vorab und als 413, kein Speicher), Ergebnis aus dem Eingang, Menü „Dateien in diesen Eintrag“.
 * A11b Teil 2 (ganz unten): die Liste „Zuletzt hinzugefügt“ aus `eingang/list` (NAS, anderes Gerät, 24 Stunden), eine Liste ohne Doppelungen, Band und Punkt zählen die
 * eigenen Uploads, Wiederaufnahme nach dem Neuladen, „Das ist richtig“ bei einem Eintrag aus dem Eingang, „Erledigte ausblenden“ nur auf diesem Gerät.
 * Backend und XMLHttpRequest sind der Mock aus mock-hass.mjs (Modus `xhr: 'manuell'`: der Test lässt Fortschritt und Antwort kommen).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, tippe, jsdom, domBereit, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN, eingangEintrag } from './mock-hass.mjs';
import * as dh from './dom-helfer.mjs';

if (jsdom) await domBereit(); // `File` und `window` für die Tests der reinen Funktionen
const FRONT = '../../custom_components/tobibox/frontend';
const H = await import(`${FRONT}/seiten/hinzufuegen.js`);
const U = await import(`${FRONT}/seiten/upload.js`);
const { HINZU, KACHELN, FEHLER, HINWEISE, GRUENDE, SERIE, fuellen } = await import(`${FRONT}/texte.js`);

const MIB = 1024 * 1024;
const GIB = 1024 * MIB;
const ALLE = [...FAEHIGKEITEN, 'einsortier_wunsch', 'eingang'];
const folge = (name, anzeige, extra = {}) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * MIB, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });

/* ------------------------------------------------------------------ Hilfen */

/* `File` von Node: `FormData` ist in den Tests das von Node und nimmt nur dessen Dateien (im Browser ist es dasselbe Paar). */
function datei(name, bytes = 1000, typ = 'audio/mpeg') { return new File([new Uint8Array(bytes)], name, { type: typ }); }
function riesig(name, groesse = 3 * GIB) { const f = datei(name, 10); Object.defineProperty(f, 'size', { value: groesse }); return f; }
const HAFEN = () => [datei('01 Der Hafen.mp3'), datei('02 Die Karte.mp3'), datei('03 Der Sturm.mp3')];

function beispiele(m) {
  const b = m.backend.serien;
  b.s1.art = 'hoerspiel'; b.s1.cover_stand = 'ab12cd34'; b.s1.angelegt_am = '2026-11-01T10:00:00Z';
  b.lang = { id: 'lang', name: 'Lange Serie', typ: 'normal', ordner: 'Lange', pruefen: false, hinweise: [], art: 'hoerspiel', cover_stand: null, angelegt_am: '2026-11-09T10:00:00Z',
    folgen: Array.from({ length: 12 }, (_, i) => folge(`f${i + 1}.mp3`, `Folge ${i + 1}`, { nummer: i + 1 })) };
  b.buch = { id: 'buch', name: 'Das große Buch', typ: 'normal', ordner: 'Buch', pruefen: false, hinweise: [], art: 'hoerbuch', cover_stand: null, angelegt_am: '2026-11-07T10:00:00Z', folgen: [folge('buch', 'Das große Buch', { art: 'ordner', tracks: 14 })] };
  b.album = { id: 'album', name: 'Sommerlieder', typ: 'normal', ordner: 'Sommer', pruefen: false, hinweise: [], art: 'musik', cover_stand: null, angelegt_am: '2026-11-06T10:00:00Z', folgen: [folge('a1.mp3', 'Lied 1'), folge('a2.mp3', 'Lied 2'), folge('a3.mp3', 'Lied 3'), folge('a4.mp3', 'Lied 4')] };
  b.lied = { id: 'lied', name: 'Wiegenlied', typ: 'normal', ordner: 'Wiegenlied', pruefen: false, hinweise: [], art: 'musik', einzeln: true, cover_stand: null, angelegt_am: '2026-11-05T10:00:00Z', folgen: [folge('wiegenlied.mp3', 'Wiegenlied')] };
}

/* Zeiger (Handy: coarse, Computer: fine) für `matchMedia`; jsdom kennt keins. */
function zeiger(art) {
  window.matchMedia = (q) => ({ matches: q === `(pointer: ${art})`, media: q, addEventListener() {}, removeEventListener() {} });
}

async function start({ hash = '#hinzufuegen', extra = [], grenzen = {}, faehigkeiten = null, ...opts } = {}) {
  const s = await seite({ faehigkeiten: faehigkeiten ?? [...ALLE, ...extra], hash: '', xhr: 'manuell', ...opts });
  s.el.xhrFactory = s.m.xhrFactory;
  Object.assign(s.el.store.s.grenzen, grenzen);
  const mo = H.modell(s.el.ctx);
  mo.lader.drosselMs = 0; mo.lader.wiederholenMs = 5; mo.lader.rueckkehrMs = 25; mo.abfrageMs = [15, 15];
  beispiele(s.m);
  if (hash) { await geheZu(s, hash); await s.flush(10); }
  return { ...s, mo };
}

const klick = async (s, el) => { assert.ok(el, 'Element zum Klicken fehlt'); el.click(); await warte(15); await s.flush(10); };
const blatt = (s) => s.q('dialog.blatt[open]');
const blattText = (s) => blatt(s)?.textContent.replace(/\s+/g, ' ').trim() ?? '';
const satz = (s) => s.q('dialog.blatt[open] [data-satz]')?.textContent.trim();
const kachel = (s, ziel) => s.q(`dialog.blatt[open] [data-ziel="${ziel}"]`);
const knopf = (s, label) => s.qa('dialog.blatt[open] .knoepfe button').find((b) => b.textContent.trim() === label);
const fehler = (s) => s.qa('.toast.err .tmsg').map((x) => x.textContent);
const karten = (s) => s.qa('[data-liste="zuletzt"] [data-eintrag]');
const karte = (s, i = 0) => karten(s)[i];
const kText = (el) => el?.textContent.replace(/\s+/g, ' ').trim() ?? '';
const bis = async (fn, ms = 1500) => { const t0 = Date.now(); for (;;) { const r = fn(); if (r) return r; if (Date.now() - t0 > ms) throw new Error('Zeitüberschreitung'); await warte(10); } };

/* Dateien „wählen“: die Seite hängt eine unsichtbare Eingabe in ihre Wurzel; der Test setzt die Dateien und meldet `change`. */
async function waehle(s, dateien, art = 'dateien') {
  const eingabe = s.q(`input[data-hinz-eingabe="${art}"]`);
  assert.ok(eingabe, `Eingabe ${art} fehlt`);
  Object.defineProperty(eingabe, 'files', { value: dateien, configurable: true });
  eingabe.dispatchEvent(new window.Event('change', { bubbles: true }));
  await warte(15); await s.flush(12);
}
async function dateienWaehlen(s, dateien) { await klick(s, s.q('[data-dateien-waehlen]')); await waehle(s, dateien); }

/* Zum Hochladen: Weg wählen und die Vorschau bestätigen. */
async function hochladen(s, dateien, ziel, vorher = async () => {}) {
  await dateienWaehlen(s, dateien);
  await klick(s, kachel(s, ziel));
  await vorher();
  await klick(s, knopf(s, HINZU.blatt.hochladen));
}

/* Eine Anfrage beenden (alle Bytes, dann Antwort). */
async function fertig(s, i = 0, antwort) {
  const x = await bis(() => s.m.xhrs[i]);
  const g = x.body.get('datei').size;
  x.fortschritt(g, g);
  if (antwort === undefined) x.antwort(200, x.erfolg()); else x.antwort(antwort.status, antwort.body);
  await warte(15); await s.flush(10);
  return x;
}
const felder = (x) => [...x.body.keys()];
const feld = (x, k) => x.body.get(k);

/* ------------------------------------------------------------------ reine Funktionen */

test('grenzeText: 2 GiB sind „2 GB“, 500 MiB „500 MB“, ungültig fällt auf 2 GB zurück', { ...MIT_DOM }, () => {
  assert.equal(U.grenzeText(2 * GIB), '2 GB');
  assert.equal(U.grenzeText(500 * MIB), '500 MB');
  assert.equal(U.grenzeText(1.5 * GIB), '1,5 GB');
  assert.equal(U.grenzeText(undefined), '2 GB');
});

test('pruefeDateien: zu groß und falsches Format vorab, Bilder im Ordner still übergangen', { ...MIT_DOM }, () => {
  const grenzen = { upload_max_bytes: 2 * GIB, endungen: ['mp3', 'm4a', '.M4B'] };
  const r = U.pruefeDateien([datei('a.mp3'), riesig('b.m4b'), datei('c.wma'), datei('d'), datei('.versteckt.mp3'), datei('cover.jpg')], grenzen);
  assert.deepEqual(r.gut.map((d) => d.name), ['a.mp3']);
  assert.deepEqual(r.fehler.map((f) => [f.name, f.code]), [['b.m4b', 'datei_zu_gross'], ['c.wma', 'format_nicht_erlaubt'], ['d', 'format_nicht_erlaubt'], ['cover.jpg', 'format_nicht_erlaubt']]);
  const ordner = U.pruefeDateien([datei('a.mp3'), datei('cover.jpg'), datei('liste.txt'), datei('b.wma')], grenzen, { ordner: true });
  assert.deepEqual(ordner.gut.map((d) => d.name), ['a.mp3']);
  assert.deepEqual(ordner.fehler.map((f) => f.name), ['b.wma']);
  assert.equal(ordner.uebergangen, 2);
  const ohneListe = U.pruefeDateien([datei('x.wma')], { upload_max_bytes: 2 * GIB });
  assert.equal(ohneListe.gut.length, 1, 'ohne Liste entscheidet das Backend (415)');
});

test('Vorschläge: Titel ohne Nummer, Name aus Album oder gemeinsamem Anfang, Art aus Endung und Genre', { ...MIT_DOM }, () => {
  assert.equal(U.titelAusDateiname('01 Der Hafen.mp3'), 'Der Hafen');
  assert.equal(U.titelAusDateiname('Track 07 - Die Karte.mp3'), 'Die Karte');
  assert.equal(U.titelAusDateiname('Der_Mond_und_der_Fuchs.mp3'), 'Der Mond und der Fuchs');
  assert.equal(U.titelAusDateiname('01.mp3'), '01');
  assert.equal(U.nameVorschlag(HAFEN(), [{ album: 'Kapitän Knopf' }]), 'Kapitän Knopf');
  assert.equal(U.nameVorschlag([datei('Kapitän Knopf 01.mp3'), datei('Kapitän Knopf 02.mp3')]), 'Kapitän Knopf');
  assert.equal(U.nameVorschlag([datei('Der Mond und der Fuchs.mp3')]), 'Der Mond und der Fuchs');
  assert.equal(U.artVorschlag([datei('a.m4b')]), 'hoerbuch');
  assert.equal(U.artVorschlag([datei('a.mp3')], [{ genre: 'Hörspiel' }]), 'hoerspiel');
  assert.equal(U.artVorschlag([datei('a.mp3')], [{ genre: 'Pop' }]), 'musik');
  assert.equal(U.artVorschlag([datei('a.mp3')], [{ genre: 'Audiobook' }]), 'hoerbuch');
  assert.equal(U.artVorschlag([datei('a.mp3')]), 'hoerspiel');
});

test('liesAngaben: Album, Titel und Genre aus ID3v2.3; andere Dateien und Unsinn geben null', { ...MIT_DOM }, async () => {
  const text = (id, t) => { const b = new TextEncoder().encode(`\u0003${t}`); const kopf = new Uint8Array(10); kopf.set(new TextEncoder().encode(id)); kopf[7] = b.length; return [...kopf, ...b]; };
  const frames = [...text('TALB', 'Kapitän Knopf'), ...text('TIT2', 'Der Hafen'), ...text('TCON', '(12)Hörbuch')];
  const kopf = [0x49, 0x44, 0x33, 3, 0, 0, 0, 0, 0, frames.length];
  const blob = new Blob([new Uint8Array([...kopf, ...frames, 0, 0, 0, 0])]);
  const f = { name: 'x.mp3', slice: (a, b) => blob.slice(a, b) };
  assert.deepEqual(await U.liesAngaben(f), { album: 'Kapitän Knopf', titel: 'Der Hafen', interpret: '', genre: 'Hörbuch' });
  assert.equal(await U.liesAngaben({ name: 'x.flac', slice: () => blob }), null);
  assert.equal(await U.liesAngaben({ name: 'x.mp3', slice: () => new Blob([new Uint8Array(20)]) }), null);
  assert.equal(await U.liesAngaben({ name: 'x.mp3', slice: () => { throw new Error('kaputt'); } }), null);
});

const wahl = (extra = {}, n = 3) => ({
  schritt: 'vorschau', ziel: null, dateien: Array.from({ length: n }, (_, i) => datei(`${i + 1}.mp3`)), abgelehnt: [], angaben: [], titelRoh: Array.from({ length: n }, (_, i) => `Titel ${i + 1}`),
  artNeu: 'hoerspiel', artEinzeln: 'musik', artVorschlag: 'hoerspiel', hatAlbum: false, nameVorschlag: '', name: '', titel: ['A', 'B', 'C'], serie: null, ...extra,
});

test('Sätze der Vorschau (a): neues Hörbuch, Album, Hörspiel, Geschichten, eine Datei', { ...MIT_DOM }, () => {
  assert.equal(H.satzFuer(wahl({ ziel: 'neu', artNeu: 'hoerbuch', name: 'Kapitän Knopf' })), '3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.');
  assert.equal(H.satzFuer(wahl({ ziel: 'neu', artNeu: 'musik', name: 'Sommerlieder' }, 4)), '4 Dateien → neues Album „Sommerlieder“, Lied 1–4.');
  assert.equal(H.satzFuer(wahl({ ziel: 'neu', artNeu: 'hoerspiel', name: 'Die Wolkenreise' }, 8)), '8 Dateien → neues Hörspiel „Die Wolkenreise“, Folge 1–8.');
  assert.equal(H.satzFuer(wahl({ ziel: 'neu', artNeu: 'hoerbuch', name: 'Das Buch' }, 1)), '1 Datei → neues Hörbuch „Das Buch“ (ein Kapitel).');
  assert.equal(H.satzFuer(wahl({ ziel: 'neu', artNeu: 'geschichte', name: 'Märchen' })), '3 Dateien → neue Geschichten „Märchen“, Geschichte 1–3.');
  assert.equal(H.satzFuer(wahl({ ziel: 'neu', artNeu: 'hoerspiel', name: '  ' })), '3 Dateien → neues Hörspiel „…“, Folge 1–3.');
});

test('Sätze der Vorschau (b): neue Folgen, Teile und Lieder in einem vorhandenen Eintrag; ohne Wahl der Hinweis', { ...MIT_DOM }, () => {
  const lang = { id: 'lang', name: 'Lange Serie', art: 'hoerspiel', anzahl_folgen: 12 };
  assert.equal(H.satzFuer(wahl({ ziel: 'ergaenzen', serie: lang })), '3 Dateien → 3 neue Folgen in „Lange Serie“ (Folge 13–15).');
  assert.equal(H.satzFuer(wahl({ ziel: 'ergaenzen', serie: { ...lang, anzahl_folgen: 20 } }, 2)), '2 Dateien → 2 neue Folgen in „Lange Serie“ (Folge 21–22).');
  assert.equal(H.satzFuer(wahl({ ziel: 'ergaenzen', serie: lang }, 1)), '1 Datei → 1 neue Folge in „Lange Serie“ (Folge 13).');
  assert.equal(H.satzFuer(wahl({ ziel: 'ergaenzen', serie: { ...lang, art: 'hoerbuch', anzahl_folgen: 1 } }, 2)), '2 Dateien → 2 neue Teile in „Lange Serie“ (Teil 2–3).');
  assert.equal(H.satzFuer(wahl({ ziel: 'ergaenzen', serie: { ...lang, art: 'musik', anzahl_folgen: 4 } })), '3 Dateien → 3 neue Lieder in „Lange Serie“ (Lied 5–7).');
  assert.equal(H.satzFuer(wahl({ ziel: 'ergaenzen', serie: null })), '3 Dateien → noch nichts gewählt. Wähle ein Hörspiel, Buch oder Album.');
});

test('Sätze der Vorschau (c, e): einzelne Lieder mit Namen bis drei Dateien, „Sortier du“ mit Vermutung', { ...MIT_DOM }, () => {
  assert.equal(H.satzFuer(wahl({ ziel: 'einzeln', titel: ['Der Mond und der Fuchs'] }, 1)), '1 Datei → 1 einzelnes Lied: „Der Mond und der Fuchs“.');
  assert.equal(H.satzFuer(wahl({ ziel: 'einzeln', titel: ['A', 'B', ''] })), '3 Dateien → 3 einzelne Lieder: „A“, „B“, „…“.');
  assert.equal(H.satzFuer(wahl({ ziel: 'einzeln' }, 5)), '5 Dateien → 5 einzelne Lieder.');
  assert.equal(H.satzFuer(wahl({ ziel: 'einzeln', artEinzeln: 'hoerspiel', titel: ['X'] }, 1)), '1 Datei → 1 einzelne Folge: „X“.');
  assert.equal(H.satzFuer(wahl({ ziel: 'auto', hatAlbum: false, artVorschlag: 'musik', titelRoh: ['Der Mond und der Fuchs'] }, 1)),
    '1 Datei → ich sortiere nach den Angaben in den Dateien ein. Meine Vermutung: ein einzelnes Lied „Der Mond und der Fuchs“.');
  assert.equal(H.satzFuer(wahl({ ziel: 'auto', hatAlbum: true, nameVorschlag: 'Kapitän Knopf', artVorschlag: 'hoerbuch' })),
    '3 Dateien → ich sortiere nach den Angaben in den Dateien ein. Meine Vermutung: neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.');
});

test('vorschauZeilen: höchstens vier, „… und N weitere“, Nummern nach den vorhandenen Folgen', { ...MIT_DOM }, () => {
  const z = H.vorschauZeilen(wahl({ ziel: 'neu', artNeu: 'hoerbuch' }, 6));
  assert.deepEqual(z, { zeilen: ['Kapitel 1 · Titel 1', 'Kapitel 2 · Titel 2', 'Kapitel 3 · Titel 3', 'Kapitel 4 · Titel 4'], weitere: 2 });
  const b = H.vorschauZeilen(wahl({ ziel: 'ergaenzen', serie: { art: 'hoerspiel', anzahl_folgen: 12, name: 'x' } }));
  assert.deepEqual(b.zeilen, ['Folge 13 · Titel 1', 'Folge 14 · Titel 2', 'Folge 15 · Titel 3']);
  assert.equal(H.vorschauZeilen(wahl({ ziel: 'einzeln' })).zeilen.length, 0);
});

test('wunschFuer: Felder je Weg; gruppe_anzahl nur bei mehreren Dateien, Einzeln ohne Gruppe', { ...MIT_DOM }, () => {
  const lang = { id: 'lang', name: 'Lange Serie', art: 'hoerspiel', anzahl_folgen: 12 };
  assert.deepEqual(H.wunschFuer(wahl({ ziel: 'neu', artNeu: 'hoerbuch', name: ' Kapitän Knopf ' }), 'g-1'), { ziel: 'neu', art: 'hoerbuch', name: 'Kapitän Knopf', gruppe: 'g-1', gruppe_anzahl: 3 });
  assert.deepEqual(H.wunschFuer(wahl({ ziel: 'neu', artNeu: 'hoerbuch', name: 'X' }, 1), 'g-1'), { ziel: 'neu', art: 'hoerbuch', name: 'X', gruppe: 'g-1' });
  assert.deepEqual(H.wunschFuer(wahl({ ziel: 'ergaenzen', serie: lang }), 'g-2'), { ziel: 'ergaenzen', serie_id: 'lang', gruppe: 'g-2', gruppe_anzahl: 3 });
  assert.deepEqual(H.wunschFuer(wahl({ ziel: 'einzeln', artEinzeln: 'geschichte' }), 'g-3'), { ziel: 'einzeln', art: 'geschichte' });
  assert.deepEqual(H.wunschFuer(wahl({ ziel: 'auto' }), 'g-4'), { ziel: 'auto', gruppe: 'g-4' });
  assert.deepEqual(H.wunschFuer(wahl({ ziel: 'auto' }, 1), 'g-4'), { ziel: 'auto' });
});

test('Fortschritt und Phase: Anteil über alle Dateien, aktuelle Datei, Phasen des Hochladens', { ...MIT_DOM }, () => {
  const a = { dateien: [{ groesse: 100, gesendet: 100, zustand: 'fertig' }, { groesse: 100, gesendet: 37, zustand: 'sendet' }, { groesse: 200, gesendet: 0, zustand: 'wartet' }] };
  assert.equal(U.gesamtProzent(a), 34);
  assert.deepEqual([U.aktuelleDatei(a).nr, U.aktuelleDatei(a).anzahl, U.dateiProzent(a.dateien[1])], [2, 3, 37]);
  a.gestartet = true;
  assert.equal(U.phaseVon(a), 'hochladen');
  assert.equal(U.phaseVon({ dateien: [{ zustand: 'wartet' }] }), 'wartet');
  assert.equal(U.phaseVon({ dateien: [{ zustand: 'fertig' }, { zustand: 'fertig' }] }), 'sortieren');
  assert.equal(U.phaseVon({ dateien: [{ zustand: 'fertig' }, { zustand: 'fehler' }] }), 'fehler');
  assert.equal(U.phaseVon({ dateien: [{ zustand: 'fertig' }, { zustand: 'unterbrochen' }] }), 'fehlt');
  assert.equal(U.phaseVon({ abgebrochen: true, dateien: [{ zustand: 'fertig' }, { zustand: 'abgebrochen' }] }), 'abgebrochen');
  assert.equal(U.gesamtProzent({ dateien: [] }), 0);
});

test('eingangFuer und Texte: Gruppen-Ordner „Upload <8 Zeichen>“, fertig, bitte ansehen, geht nicht, fehlt; Gründe als Texte', { ...MIT_DOM }, () => {
  const a = { wunsch: { gruppe: 'abcdef12-0000' }, dateien: [{ eingangName: 'x.mp3' }] };
  assert.deepEqual(H.eingangsNamen(a), { ordner: 'Upload abcdef12', dateien: ['x.mp3'] });
  const e = (extra) => ({ name: 'Upload abcdef12', status: 'erledigt', fertig_am: '2026-11-13T10:00:00Z', dateien: 3, ergebnis: [], hinweise: [], pruefen: false, ...extra });
  assert.equal(H.eingangFuer(a, []), null);
  assert.equal(H.eingangFuer(a, [e({ fertig_am: null, status: 'wartet' })]), null, 'noch nicht einsortiert');
  assert.equal(H.eingangFuer(a, [e({ ergebnis: [{ serie_id: 's', serie_name: 'S', serie_neu: true, pruefen: false }] })]).art, 'fertig');
  const p = H.eingangFuer(a, [e({ pruefen: true, ergebnis: [{ serie_id: 's', serie_name: 'S', pruefen: true, pruefen_gruende: ['tags_fehlen', 'tags_fehlen'] }] })]);
  assert.equal(p.art, 'pruefen');
  assert.deepEqual(H.gruende(p), [GRUENDE.tags_fehlen]);
  const f = H.eingangFuer(a, [e({ status: 'blockiert', fertig_am: null, hinweise: [{ code: 'kopierschutz', datei: 'x.mp3', text: 'x' }] })]);
  assert.equal(f.art, 'fehler');
  assert.deepEqual(H.nichtGruende(f), [HINWEISE.kopierschutz]);
  assert.equal(H.eingangFuer(a, [e({ status: 'teilweise', hinweise: [{ code: 'gruppe_unvollstaendig', datei: null, text: '' }] })]).art, 'fehlt');
  // einzelne Dateien ohne Gruppe: alle müssen da sein
  const b = { wunsch: { ziel: 'einzeln' }, dateien: [{ eingangName: 'a.mp3' }, { eingangName: 'b.mp3' }] };
  assert.equal(H.eingangFuer(b, [e({ name: 'a.mp3' })]), null);
  assert.ok(H.eingangFuer(b, [e({ name: 'a.mp3' }), e({ name: 'b.mp3' })]));
});

test('ergebnisText: Hörbuch mit Kapiteln, ergänzte Folgen, einzelnes Lied, mehrere einzelne', { ...MIT_DOM }, () => {
  const erg = (x) => ({ serie_id: 'x', serie_name: 'Kapitän Knopf', serie_neu: true, folge: 'f', tracks: 1, pruefen: false, ...x });
  const a = (ergebnis, details, wunsch = {}) => ({ wunsch, eingang: { ergebnis }, details });
  assert.equal(H.ergebnisText(a([erg({ tracks: 3 })], { x: { art: 'hoerbuch', folgen: [] } })), 'Hörbuch „Kapitän Knopf“ · 3 Kapitel');
  assert.equal(H.ergebnisText(a([erg({ tracks: 1 })], { x: { art: 'hoerbuch', folgen: [] } })), 'Hörbuch „Kapitän Knopf“ · ein Kapitel');
  assert.equal(H.ergebnisText(a([erg({}), erg({ folge: 'g' })], { x: { art: 'musik', folgen: [] } })), 'Album „Kapitän Knopf“ · 2 Lieder');
  const folgen = Array.from({ length: 15 }, (_, i) => ({ name: `f${i + 1}`, nummer: i + 1 }));
  assert.equal(H.ergebnisText(a([erg({ serie_neu: false, serie_name: 'Lange Serie', folge: 'f13' }), erg({ serie_neu: false, serie_name: 'Lange Serie', folge: 'f14' }), erg({ serie_neu: false, serie_name: 'Lange Serie', folge: 'f15' })], { x: { art: 'hoerspiel', folgen } })),
    '„Lange Serie“ · Folge 13–15');
  assert.equal(H.ergebnisText(a([erg({ serie_name: 'Der Mond und der Fuchs' })], { x: { art: 'musik', einzeln: true } })), '„Der Mond und der Fuchs“ · einzelnes Lied');
  assert.equal(H.ergebnisText(a([erg({ serie_id: 'a' }), erg({ serie_id: 'b' })], { a: { art: 'musik', einzeln: true }, b: { art: 'musik', einzeln: true } })), '2 einzelne Lieder (jedes steht für sich)');
  assert.equal(H.ergebnisText(a([erg({})], null)), '„Kapitän Knopf“', 'ohne Einzelheiten steht nur der Name');
  assert.equal(H.artHinweis(a([erg({})], { x: { art: 'musik' } }, { ziel: 'auto' })), 'Art: Musik (aus den Tags vorgeschlagen). Stimmt nicht? Im Eintrag „Art ändern“.');
  assert.equal(H.artHinweis(a([erg({})], { x: { art: 'musik' } }, { ziel: 'neu' })), null, 'nur bei „Weiß nicht“');
});

test('Texte: Titel und Text von „Es fehlt noch eine Datei“ ergeben den Text des Designs (6.1); kein Text ist leer', { ...MIT_DOM }, () => {
  assert.equal(`${HINZU.fehlt.titel} ${HINZU.fehlt.text}`, HINWEISE.gruppe_unvollstaendig);
  assert.equal(HINZU.bildschirm, 'Bildschirm anlassen, bis es fertig ist.');
  const alle = (o) => (typeof o === 'string' ? [o] : Object.values(o).flatMap(alle));
  for (const t of alle(HINZU)) assert.ok(t.trim().length > 0);
  assert.equal(KACHELN.neu.titel, 'Neu anlegen');
});

/* ------------------------------------------------------------------ Seite */

test('Seite am Computer: „‹ Bibliothek“, „Dateien wählen“, „Ordner vom Computer wählen“, Ziehfläche, sonst nichts (X11)', { ...MIT_DOM }, async () => {
  zeiger('fine');
  const s = await start();
  try {
    assert.equal(s.q('main .back').textContent.trim(), '‹ Bibliothek');
    assert.equal(s.q('main h2').textContent.trim(), 'Hinzufügen');
    assert.equal(s.q('[data-dateien-waehlen]').textContent.trim(), 'Dateien wählen');
    assert.equal(s.q('[data-ordner-waehlen]').textContent.trim(), 'Ordner vom Computer wählen');
    assert.equal(s.q('[data-ziehflaeche]').textContent.trim(), 'Dateien oder Ordner hierher ziehen');
    assert.equal(s.qa('main .note, main p').length, 0, 'keine Formatzeile, kein Hinweis auf Größe oder Kopierschutz, keine Karte zum NAS');
    assert.ok(!s.q('[data-liste="zuletzt"]'), 'ohne Hochladen keine Liste');
    assert.ok(!/Bildschirm/.test(s.q('main').textContent), 'kein vorsorgliches „Bildschirm anlassen“');
  } finally { weg(); }
});

test('Seite am Handy: keine Ordnerwahl und keine Ziehfläche', { ...MIT_DOM }, async () => {
  zeiger('coarse');
  const s = await start();
  try {
    assert.ok(s.q('[data-dateien-waehlen]'));
    assert.ok(!s.q('[data-ordner-waehlen]'));
    assert.ok(!s.q('[data-ziehflaeche]'));
  } finally { weg(); }
});

test('„+“ in der Bibliothek: am Handy gleich die Dateiauswahl (kein Seitenwechsel), am Computer der Link zur Seite (N26)', { ...MIT_DOM }, async () => {
  const klicks = [];
  const proto = window.HTMLInputElement.prototype;
  const alt = proto.click;
  proto.click = function click() { klicks.push(this.getAttribute('data-hinz-eingabe')); };
  try {
    zeiger('coarse');
    let s = await start({ hash: '#bibliothek' });
    const plus = s.q('a.kact.primaer');
    assert.equal(plus.getAttribute('href'), '#hinzufuegen');
    const ev = new window.MouseEvent('click', { bubbles: true, cancelable: true });
    plus.dispatchEvent(ev);
    await s.flush(8);
    assert.deepEqual(klicks, ['dateien'], 'input.click() im Tap');
    assert.equal(ev.defaultPrevented, true);
    assert.notEqual(window.location.hash, '#hinzufuegen');
    await waehle(s, HAFEN());
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Was lädst du hoch?', 'das Blatt öffnet über der Bibliothek');
    weg();
    zeiger('fine');
    s = await start({ hash: '#bibliothek' });
    klicks.length = 0;
    const ev2 = new window.MouseEvent('click', { bubbles: true, cancelable: true });
    s.q('a.kact.primaer').dispatchEvent(ev2);
    assert.equal(ev2.defaultPrevented, false, 'am Computer bleibt es ein Link');
    assert.deepEqual(klicks, []);
  } finally { proto.click = alt; weg(); }
});

/* ------------------------------------------------------------------ Blatt „Was lädst du hoch?“ */

test('Blatt: Zeile mit Dateien, vier Kacheln (Titel, eine Zeile, Satz für Screenreader), „Abbrechen“ oben rechts, kein „×“', { ...MIT_DOM }, async () => {
  zeiger('fine');
  const s = await start();
  try {
    await dateienWaehlen(s, HAFEN());
    assert.ok(blatt(s), 'das Blatt ist offen');
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Was lädst du hoch?');
    assert.equal(s.q('dialog.blatt[open] [data-gewaehlt]').textContent.trim(), '3 Dateien gewählt (01 Der Hafen.mp3 …). Was ist das?');
    const ks = s.qa('dialog.blatt[open] [data-kacheln] button');
    assert.deepEqual(ks.map((k) => k.dataset.ziel), ['neu', 'ergaenzen', 'einzeln', 'auto']);
    assert.deepEqual(ks.map((k) => k.querySelector('.hz-t').textContent), ['Neu anlegen', 'Zu Vorhandenem', 'Einzeln', 'Sortier du']);
    assert.deepEqual(ks.map((k) => k.querySelector('.hz-z').textContent), ['Hörspiel, Buch, Album', 'Neue Folgen dazu', 'Lied oder Folge für sich', 'Ich lese die Angaben']);
    for (const k of ks) { assert.ok(k.querySelector('.hz-sym svg[aria-hidden="true"]'), 'Symbol ist aria-hidden'); assert.ok(k.querySelector('.sr').textContent.length > 20, 'ausführlicher Satz für Screenreader'); }
    assert.match(ks[3].querySelector('.sr').textContent, /Wenn ich unsicher bin, steht danach „Bitte ansehen“ da/);
    const oben = s.q('dialog.blatt[open] [data-blatt-oben]');
    assert.equal(oben.textContent.trim(), 'Abbrechen');
    assert.ok(!s.q('dialog.blatt[open] .blatt-x'), 'kein „×“');
    assert.ok(!blattText(s).includes('Playlist'), 'keine fünfte Kachel');
    assert.equal(s.el.shadowRoot.activeElement?.id, 'blatt-t', 'der Fokus steht auf der Überschrift, nicht auf einer Kachel');
  } finally { weg(); }
});

test('Blatt: eine Datei heißt „1 Datei gewählt (Name). …“; „Abbrechen“ oben rechts, Esc und Wischen schließen ohne Folgen', { ...MIT_DOM }, async () => {
  zeiger('fine');
  const s = await start();
  try {
    await dateienWaehlen(s, [datei('Der Mond und der Fuchs.mp3')]);
    assert.equal(s.q('[data-gewaehlt]').textContent.trim(), '1 Datei gewählt (Der Mond und der Fuchs.mp3). Was ist das?');
    await klick(s, s.q('[data-blatt-oben]'));
    assert.ok(!blatt(s), 'Abbrechen schließt');
    assert.equal(s.mo.eintraege.length, 0);
    assert.equal(s.m.xhrs.length, 0, 'es wurde nichts gesendet');
    await dateienWaehlen(s, HAFEN());
    s.q('dialog.blatt').dispatchEvent(new window.Event('cancel', { cancelable: true }));
    await warte(15); await s.flush(8);
    assert.ok(!blatt(s), 'Esc schließt');
    assert.equal(s.mo.eintraege.length, 0);
  } finally { weg(); }
});

test('Zu viele Dateien: Fehlermeldung bleibt, kein Blatt', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, Array.from({ length: 201 }, (_, i) => datei(`${i}.mp3`)));
    assert.ok(!blatt(s));
    assert.deepEqual(fehler(s), ['Das sind zu viele Dateien auf einmal. Wähle höchstens 200 Dateien.']);
  } finally { weg(); }
});

/* ------------------------------------------------------------------ Vorschau je Weg */

test('Vorschau a): Name und „Welche Art?“, Satz mit role=status, ändert sich sofort beim Tippen und beim Wechsel der Art', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, HAFEN());
    await klick(s, kachel(s, 'neu'));
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Das passiert gleich');
    assert.equal(s.el.shadowRoot.activeElement?.id, 'blatt-t', 'Fokus auf der Überschrift, nicht im Namensfeld');
    const st = s.q('dialog.blatt[open] [data-satz]');
    assert.equal(st.getAttribute('role'), 'status');
    assert.equal(st.getAttribute('aria-live'), 'polite');
    const name = s.q('#hz-name');
    assert.equal(name.getAttribute('maxlength'), '100');
    assert.ok(s.q('label[for="hz-name"]'));
    assert.match(st.textContent, /^3 Dateien → neues Hörspiel „Der Hafen“, Folge 1–3\.$/);
    tippe(name, 'Kapitän Knopf');
    await s.flush(6);
    assert.equal(s.q('dialog.blatt[open] [data-satz]'), st, 'derselbe Knoten, damit die Ansage greift');
    assert.equal(st.textContent, '3 Dateien → neues Hörspiel „Kapitän Knopf“, Folge 1–3.');
    assert.equal(s.qa('[data-art-wahl]').map((b) => b.textContent).join('|'), 'Hörspiel|Hörbuch|Album|Geschichten');
    assert.match(s.q('#hz-l-art').textContent, /Welche Art\?/);
    await klick(s, s.q('[data-art-wahl="hoerbuch"]'));
    assert.equal(st.textContent, '3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.');
    assert.equal(s.q('[data-art-wahl="hoerbuch"]').getAttribute('aria-pressed'), 'true');
    assert.equal(s.q('[data-art-wahl="musik"]').getAttribute('aria-pressed'), 'false');
    await klick(s, s.q('[data-art-wahl="musik"]'));
    assert.equal(st.textContent, '3 Dateien → neues Album „Kapitän Knopf“, Lied 1–3.');
    assert.deepEqual(s.qa('[data-vorschau-liste] div').map((d) => d.textContent), ['Lied 1 · Der Hafen', 'Lied 2 · Die Karte', 'Lied 3 · Der Sturm']);
    assert.equal(s.q('[data-zusammen]').textContent.trim(), 'Die Dateien bleiben zusammen. Einsortiert wird, wenn alle 3 da sind.');
    assert.deepEqual(s.qa('dialog.blatt[open] .knoepfe button').map((b) => b.textContent.trim()), ['Abbrechen', 'Ändern', 'Hochladen']);
  } finally { weg(); }
});

test('Vorschau a) bei vielen Dateien: vier Zeilen und „… und 4 weitere“', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, Array.from({ length: 8 }, (_, i) => datei(`${String(i + 1).padStart(2, '0')} Folge.mp3`)));
    await klick(s, kachel(s, 'neu'));
    assert.equal(s.qa('[data-vorschau-liste] > div').length, 5);
    assert.equal(s.qa('[data-vorschau-liste] > div').at(-1).textContent, '… und 4 weitere');
  } finally { weg(); }
});

test('Vorschau b): „Wohin soll es?“ mit Suche, Covern und Art-Knöpfen nur für Hörspiele, Bücher, Alben; danach Satz mit Nummern und Eintrag mit Cover', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, HAFEN());
    await klick(s, kachel(s, 'ergaenzen'));
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Wohin soll es?');
    await bis(() => s.q('[data-hz-wahl] [data-wahl]'));
    assert.ok(s.q('[data-hz-wahl] input[type="search"]'), 'Suchfeld');
    assert.equal(s.qa('[data-hz-wahl] [data-art]').length, 5, 'Art-Knöpfe');
    const ids = s.qa('[data-hz-wahl] [data-wahl]').map((b) => b.dataset.wahl);
    assert.ok(ids.includes('serie:lang') && ids.includes('serie:buch') && ids.includes('serie:album'));
    assert.ok(!ids.includes('serie:lied'), 'ohne Einzeltitel');
    assert.ok(!ids.includes('aktion') && !s.q('[data-hz-wahl] [data-wahl="aktion"]'), 'ohne „Gute Nacht“');
    assert.ok(!s.q('[data-hz-wahl] .seg2'), 'ohne den Umschalter Serie | Folge');
    assert.ok(s.q('[data-hz-wahl] .cover'), 'Cover');
    await klick(s, s.q('[data-hz-wahl] [data-wahl="serie:lang"]'));
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Das passiert gleich');
    assert.equal(satz(s), '3 Dateien → 3 neue Folgen in „Lange Serie“ (Folge 13–15).');
    assert.match(s.q('[data-wohin]').textContent, /Lange Serie.*Hörspiel · 12 Folgen.*Ändern/s);
    assert.ok(s.q('[data-wohin] .cover'), 'der Eintrag mit Cover');
    assert.deepEqual(s.qa('[data-vorschau-liste] > div').map((d) => d.textContent), ['Folge 13 · Der Hafen', 'Folge 14 · Die Karte', 'Folge 15 · Der Sturm']);
    // „Ändern“ beim Eintrag wählt neu
    await klick(s, s.q('[data-wohin]'));
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Wohin soll es?');
    await bis(() => s.q('[data-hz-wahl] [data-wahl="serie:album"]'));
    await klick(s, s.q('[data-hz-wahl] [data-wahl="serie:album"]'));
    assert.equal(satz(s), '3 Dateien → 3 neue Lieder in „Sommerlieder“ (Lied 5–7).');
  } finally { weg(); }
});

test('Vorschau b): Suche im Blatt filtert die Auswahl', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, HAFEN());
    await klick(s, kachel(s, 'ergaenzen'));
    await bis(() => s.q('[data-hz-wahl] [data-wahl]'));
    tippe(s.q('[data-hz-wahl] input[type="search"]'), 'Sommer');
    await warte(320); await s.flush(10);
    const ids = s.qa('[data-hz-wahl] [data-wahl]').map((b) => b.dataset.wahl);
    assert.deepEqual(ids, ['serie:album']);
  } finally { weg(); }
});

test('Vorschau c): Art (Vorgabe Lied) und ein Name je Datei bis drei, danach der Satz „Die übrigen 2 Dateien …“', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, Array.from({ length: 5 }, (_, i) => datei(`0${i + 1} Lied ${i + 1}.mp3`)));
    await klick(s, kachel(s, 'einzeln'));
    assert.equal(s.qa('[data-art-wahl]').map((b) => b.textContent).join('|'), 'Lied|Geschichte|Folge|Hörbuch');
    assert.equal(s.q('[data-art-wahl="musik"]').getAttribute('aria-pressed'), 'true', 'Vorgabe Lied');
    assert.equal(satz(s), '5 Dateien → 5 einzelne Lieder.');
    const felder = s.qa('[data-titel]');
    assert.equal(felder.length, 3);
    assert.deepEqual(s.qa('label.hz-label[for^="hz-t"]').map((l) => l.textContent), ['Name von Datei 1', 'Name von Datei 2', 'Name von Datei 3']);
    assert.equal(s.q('[data-uebrige]').textContent.trim(), 'Die übrigen 2 Dateien heißen wie in ihren Angaben.');
    assert.ok(!s.q('[data-zusammen]'), 'Einzeln bleibt nicht zusammen');
    assert.equal(felder[0].value, 'Lied 1');
    tippe(felder[1], 'Der Mond');
    await s.flush(5);
    assert.equal(satz(s), '5 Dateien → 5 einzelne Lieder.');
    await klick(s, s.q('[data-art-wahl="hoerspiel"]'));
    assert.equal(satz(s), '5 Dateien → 5 einzelne Folgen.');
  } finally { weg(); }
});

test('Vorschau c) mit einer Datei: ein Name, Satz mit dem Namen; bei drei Dateien stehen die Namen im Satz', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, [datei('Der Mond und der Fuchs.mp3')]);
    await klick(s, kachel(s, 'einzeln'));
    assert.equal(satz(s), '1 Datei → 1 einzelnes Lied: „Der Mond und der Fuchs“.');
    assert.equal(s.q('label[for="hz-t0"]').textContent, 'Name');
    tippe(s.q('#hz-t0'), 'Mondlied');
    await s.flush(5);
    assert.equal(satz(s), '1 Datei → 1 einzelnes Lied: „Mondlied“.');
    assert.ok(!s.q('[data-uebrige]'));
  } finally { weg(); }
});

test('Vorschau e): ein Absatz erklärt das Einsortieren, der Satz nennt die Vermutung; keine weiteren Eingaben', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, [datei('Der Mond und der Fuchs.m4b')]);
    await klick(s, kachel(s, 'auto'));
    assert.equal(s.q('[data-sortier-du]').textContent.trim(), HINZU.blatt.sortier_du);
    assert.match(satz(s), /^1 Datei → ich sortiere nach den Angaben in den Dateien ein\. Meine Vermutung: ein einzelnes Hörbuch „Der Mond und der Fuchs“\.$/);
    assert.equal(s.qa('dialog.blatt[open] input').length, 0);
  } finally { weg(); }
});

test('Die Vermutung nutzt die Angaben der Datei (ID3: Album, Titel, Genre), sobald sie gelesen sind', { ...MIT_DOM }, async () => {
  const text = (id, t) => { const b = new TextEncoder().encode(`\u0003${t}`); const kopf = new Uint8Array(10); kopf.set(new TextEncoder().encode(id)); kopf[7] = b.length; return [...kopf, ...b]; };
  const frames = [...text('TALB', 'Kapitän Knopf'), ...text('TIT2', 'Der Hafen'), ...text('TCON', 'Audiobook')];
  const bytes = new Uint8Array([0x49, 0x44, 0x33, 3, 0, 0, 0, 0, 0, frames.length, ...frames, 0, 0, 0, 0]);
  const dateien = [new File([bytes], '01 Der Hafen.mp3'), datei('02 Die Karte.mp3'), datei('03 Der Sturm.mp3')];
  const s = await start();
  try {
    await dateienWaehlen(s, dateien);
    await warte(60); await s.flush(8);
    await klick(s, kachel(s, 'neu'));
    assert.equal(s.q('#hz-name').value, 'Kapitän Knopf', 'Name aus dem Album');
    assert.equal(s.q('[data-art-wahl="hoerbuch"]').getAttribute('aria-pressed'), 'true', 'Art aus dem Genre');
    assert.equal(satz(s), '3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.');
    assert.equal(s.qa('[data-vorschau-liste] > div')[0].textContent, 'Kapitel 1 · Der Hafen');
  } finally { weg(); }
});

test('„Ändern“ führt zu den Kacheln zurück, die Eingaben bleiben erhalten', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, HAFEN());
    await klick(s, kachel(s, 'neu'));
    tippe(s.q('#hz-name'), 'Kapitän Knopf');
    await klick(s, s.q('[data-art-wahl="hoerbuch"]'));
    await klick(s, knopf(s, 'Ändern'));
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Was lädst du hoch?');
    assert.equal(s.el.shadowRoot.activeElement?.id, 'blatt-t');
    await klick(s, kachel(s, 'einzeln'));
    tippe(s.q('#hz-t1'), 'Mein zweites Lied');
    await klick(s, knopf(s, 'Ändern'));
    await klick(s, kachel(s, 'neu'));
    assert.equal(s.q('#hz-name').value, 'Kapitän Knopf', 'der Name ist noch da');
    assert.equal(satz(s), '3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.');
    await klick(s, knopf(s, 'Ändern'));
    await klick(s, kachel(s, 'einzeln'));
    assert.equal(s.q('#hz-t1').value, 'Mein zweites Lied');
  } finally { weg(); }
});

test('Prüfungen vor „Hochladen“: Name fehlt → Meldung bleibt, das Blatt bleibt; Wahl fehlt → Meldung', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, HAFEN());
    await klick(s, kachel(s, 'neu'));
    tippe(s.q('#hz-name'), '   ');
    await s.flush(4);
    await klick(s, knopf(s, 'Hochladen'));
    assert.deepEqual(fehler(s), ['Bitte einen Namen eingeben.']);
    assert.equal(s.q('.toast.err').getAttribute('role'), 'alert');
    assert.ok(s.q('dialog.blatt[open] .toast.err .tok'), 'die Meldung steht im offenen Blatt, mit „OK“');
    assert.ok(blatt(s), 'das Blatt bleibt offen');
    assert.equal(s.m.xhrs.length, 0);
    // „Wohin“ fehlt: nur über das Modell zu erreichen (die Oberfläche lässt „Hochladen“ ohne Wahl nicht zu)
    s.mo.w.ziel = 'ergaenzen'; s.mo.w.serie = null;
    const r = s.mo.hochladen();
    assert.equal(r, false);
    assert.ok(fehler(s).includes('Bitte zuerst wählen, wohin es soll.'));
    // die Meldung bleibt, bis „OK“ getippt wird
    await klick(s, s.q('.toast.err .tok'));
    assert.equal(fehler(s).length, 1);
  } finally { weg(); }
});

/* ------------------------------------------------------------------ Hochladen */

test('Hochladen (Hörbuch aus 3 Dateien): Felder in der Reihenfolge des Vertrags, gleiche gruppe und gruppe_anzahl, Dateien nacheinander', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, HAFEN(), 'neu', async () => { tippe(s.q('#hz-name'), 'Kapitän Knopf'); await klick(s, s.q('[data-art-wahl="hoerbuch"]')); });
    assert.ok(!blatt(s), 'das Blatt ist zu');
    assert.equal(window.location.hash, '#hinzufuegen');
    await bis(() => s.m.xhrs.length === 1);
    await warte(30);
    assert.equal(s.m.xhrs.length, 1, 'die Dateien gehen nacheinander');
    const x1 = s.m.xhrs[0];
    assert.equal(x1.method, 'POST');
    assert.equal(x1.url, '/api/tobibox/upload');
    assert.equal(x1.headers.Authorization, 'Bearer token-123');
    assert.deepEqual(felder(x1).slice(0, 2), ['upload_id', 'gruppe']);
    assert.equal(felder(x1).at(-1), 'datei', '`datei` kommt zuletzt');
    assert.deepEqual(new Set(felder(x1)), new Set(['upload_id', 'gruppe', 'ziel', 'art', 'name', 'gruppe_anzahl', 'datei']));
    assert.equal(feld(x1, 'ziel'), 'neu');
    assert.equal(feld(x1, 'art'), 'hoerbuch');
    assert.equal(feld(x1, 'name'), 'Kapitän Knopf');
    assert.equal(feld(x1, 'gruppe_anzahl'), '3');
    assert.equal(feld(x1, 'datei').name, '01 Der Hafen.mp3');
    assert.match(feld(x1, 'upload_id'), /^[0-9A-Za-z-]{8,64}$/);
    assert.match(feld(x1, 'gruppe'), /^[0-9A-Za-z-]{8,64}$/);
    await fertig(s, 0);
    const x2 = await bis(() => s.m.xhrs[1]);
    assert.equal(feld(x2, 'gruppe'), feld(x1, 'gruppe'));
    assert.equal(feld(x2, 'gruppe_anzahl'), '3');
    assert.notEqual(feld(x2, 'upload_id'), feld(x1, 'upload_id'));
    assert.equal(feld(x2, 'datei').name, '02 Die Karte.mp3');
    await fertig(s, 1);
    const x3 = await bis(() => s.m.xhrs[2]);
    assert.equal(feld(x3, 'datei').name, '03 Der Sturm.mp3');
    assert.equal(feld(x3, 'gruppe'), feld(x1, 'gruppe'));
  } finally { weg(); }
});

test('Weitere Wege: Zu Vorhandenem, Einzeln (je Datei eigener Upload mit eigenem Namen, ohne Gruppe) und Sortier du', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, HAFEN(), 'ergaenzen', async () => { await bis(() => s.q('[data-hz-wahl] [data-wahl="serie:lang"]')); await klick(s, s.q('[data-hz-wahl] [data-wahl="serie:lang"]')); });
    const a = await bis(() => s.m.xhrs[0]);
    assert.deepEqual([feld(a, 'ziel'), feld(a, 'serie_id'), feld(a, 'gruppe_anzahl'), feld(a, 'art'), feld(a, 'name')], ['ergaenzen', 'lang', '3', null, null]);
    for (let i = 0; i < 3; i += 1) await fertig(s, i);
    weg();
    const s2 = await start();
    await hochladen(s2, [datei('a.mp3'), datei('b.mp3')], 'einzeln', async () => { tippe(s2.q('#hz-t0'), 'Erstes'); tippe(s2.q('#hz-t1'), 'Zweites'); await s2.flush(4); });
    const e1 = await bis(() => s2.m.xhrs[0]);
    assert.deepEqual([feld(e1, 'ziel'), feld(e1, 'art'), feld(e1, 'name'), feld(e1, 'gruppe'), feld(e1, 'gruppe_anzahl')], ['einzeln', 'musik', 'Erstes', null, null]);
    await fertig(s2, 0);
    const e2 = await bis(() => s2.m.xhrs[1]);
    assert.equal(feld(e2, 'name'), 'Zweites');
    weg();
    const s3 = await start();
    await hochladen(s3, [datei('x.mp3'), datei('y.mp3')], 'auto');
    const f1 = await bis(() => s3.m.xhrs[0]);
    assert.equal(feld(f1, 'ziel'), 'auto');
    assert.ok(feld(f1, 'gruppe'), 'mehrere Dateien bleiben zusammen');
    assert.equal(feld(f1, 'gruppe_anzahl'), null, 'gruppe_anzahl gilt nur für neu und ergaenzen');
    assert.equal(feld(f1, 'name'), null);
  } finally { weg(); }
});

test('Aus dem Eintrag („Dateien in diesen Eintrag“): gleich die Vorschau von „Zu Vorhandenem“, Felder mit serie_id', { ...MIT_DOM }, async () => {
  zeiger('fine');
  const s = await start({ hash: '#serie-lang' });
  try {
    await bis(() => s.q('[data-menue-serie]'));
    await klick(s, s.q('[data-menue-serie]'));
    const punkt = s.q('dialog.blatt[open] [data-menue="dateien"]');
    assert.equal(punkt.textContent.trim(), 'Dateien in diesen Eintrag');
    await klick(s, punkt);
    await waehle(s, HAFEN());
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Das passiert gleich', 'die Kacheln werden übersprungen');
    assert.equal(satz(s), '3 Dateien → 3 neue Folgen in „Lange Serie“ (Folge 13–15).');
    await klick(s, knopf(s, 'Hochladen'));
    const x = await bis(() => s.m.xhrs[0]);
    assert.deepEqual([feld(x, 'ziel'), feld(x, 'serie_id'), feld(x, 'gruppe_anzahl')], ['ergaenzen', 'lang', '3']);
    assert.equal(window.location.hash, '#hinzufuegen');
  } finally { weg(); }
});

test('Menü des Eintrags: „Dateien in diesen Eintrag“ nur mit der Fähigkeit `einsortier_wunsch` und nicht bei Einzeltiteln', { ...MIT_DOM }, async () => {
  let s = await start({ hash: '#serie-lied' });
  try {
    await bis(() => s.q('[data-menue-serie]'));
    await klick(s, s.q('[data-menue-serie]'));
    assert.ok(!s.q('dialog.blatt[open] [data-menue="dateien"]'), 'nicht bei Einzeltiteln');
    weg();
    s = await start({ hash: '#serie-lang', faehigkeiten: [...FAEHIGKEITEN] });
    await bis(() => s.q('[data-menue-serie]'));
    await klick(s, s.q('[data-menue-serie]'));
    assert.ok(!s.q('dialog.blatt[open] [data-menue="dateien"]'), 'ohne die Fähigkeit nicht');
  } finally { weg(); }
});

test('Ohne die Fähigkeit `einsortier_wunsch` gibt es keine Wahl: die Dateien gehen gleich hoch, mit gruppe, ohne Wunschfelder', { ...MIT_DOM }, async () => {
  const s = await start({ faehigkeiten: [...FAEHIGKEITEN] });
  try {
    await dateienWaehlen(s, HAFEN());
    assert.ok(!blatt(s));
    const x = await bis(() => s.m.xhrs[0]);
    assert.deepEqual(new Set(felder(x)), new Set(['upload_id', 'gruppe', 'datei']));
  } finally { weg(); }
});

test('Fortschritt: „Datei 2 von 3 wird hochgeladen … 37 %“, Balken über alle Dateien, dreiteilige Leiste, „Einsortiert wird erst, wenn alle 3 Dateien da sind.“', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, [datei('01 A.mp3', 1000), datei('02 B.mp3', 1000), datei('03 C.mp3', 1000)], 'neu', async () => { tippe(s.q('#hz-name'), 'Buch'); await s.flush(3); });
    assert.equal(s.q('[data-titel-eintrag]').textContent.trim(), '3 Dateien: 01 A.mp3, 02 B.mp3 …');
    assert.equal(s.q('[data-status]').textContent.trim(), 'Datei 1 von 3 wird hochgeladen … 0 %');
    await fertig(s, 0);
    const x = await bis(() => s.m.xhrs[1]);
    x.fortschritt(370, 1000);
    await s.flush(6);
    assert.equal(s.q('[data-status]').textContent.trim(), 'Datei 2 von 3 wird hochgeladen … 37 %');
    assert.equal(s.q('[data-zusammen]').textContent.trim(), 'Einsortiert wird erst, wenn alle 3 Dateien da sind.');
    const b = s.q('[data-balken]');
    assert.equal(b.getAttribute('role'), 'progressbar');
    assert.equal(b.getAttribute('aria-valuenow'), String(Math.floor((1000 + 370) / 3000 * 100)));
    assert.equal(b.getAttribute('aria-valuemin'), '0');
    assert.equal(b.getAttribute('aria-valuemax'), '100');
    assert.ok(b.getAttribute('aria-label'));
    assert.deepEqual(s.qa('[data-schritte] li').map((l) => l.textContent.trim()), ['Hochladen', 'Einsortieren', 'Fertig']);
    assert.equal(s.q('[data-schritte] li[aria-current="step"]').textContent.trim(), 'Hochladen');
    assert.ok(s.q('[data-abbrechen]'));
  } finally { weg(); }
});

test('Fortschritt bei einer Datei: „Wird hochgeladen … 37 %“, ohne den Satz zum Warten auf andere Dateien', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, [datei('Lied.mp3', 1000)], 'einzeln');
    const x = await bis(() => s.m.xhrs[0]);
    x.fortschritt(370, 1000);
    await s.flush(6);
    assert.equal(s.q('[data-status]').textContent.trim(), 'Wird hochgeladen … 37 %');
    assert.ok(!s.q('[data-zusammen]'));
    x.fortschritt(1000, 1000);
    x.upload.onload();
    await s.flush(6);
    assert.equal(s.q('[data-status]').textContent.trim(), 'Wird geprüft …');
  } finally { weg(); }
});

test('Der Satz „Bildschirm anlassen, bis es fertig ist.“ steht nur während des Hochladens (R17-4, N15)', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    assert.ok(!/Bildschirm/.test(s.q('main').textContent), 'vorher nicht');
    await hochladen(s, [datei('Lied.mp3')], 'einzeln');
    await bis(() => s.q('[data-bildschirm]'));
    assert.equal(s.q('[data-bildschirm]').textContent.trim(), 'Bildschirm anlassen, bis es fertig ist.');
    await fertig(s, 0);
    assert.ok(!/Bildschirm/.test(s.q('main').textContent), 'danach nicht mehr');
    assert.equal(s.q('[data-status]').textContent.trim(), 'Wird einsortiert …');
  } finally { weg(); }
});

/* ------------------------------------------------------------------ Wake Lock */

function wakeLock(modus) {
  const W = { angefordert: [], freigegeben: 0 };
  const nav = window.navigator;
  const alt = Object.getOwnPropertyDescriptor(nav, 'wakeLock');
  if (modus === 'fehlt') Object.defineProperty(nav, 'wakeLock', { value: undefined, configurable: true });
  else Object.defineProperty(nav, 'wakeLock', { configurable: true, value: {
    request: async (typ) => {
      W.angefordert.push(typ);
      if (modus === 'abgelehnt') throw Object.assign(new Error('nicht erlaubt'), { name: 'NotAllowedError' });
      return { release: async () => { W.freigegeben += 1; }, addEventListener() {} };
    } } });
  W.zurueck = () => { if (alt) Object.defineProperty(nav, 'wakeLock', alt); else delete nav.wakeLock; };
  return W;
}

test('Wake Lock: `request(\'screen\')` beim Start, Freigabe, wenn alles durch ist', { ...MIT_DOM }, async () => {
  const W = wakeLock('ok');
  const s = await start();
  try {
    await hochladen(s, [datei('Lied.mp3')], 'einzeln');
    await bis(() => W.angefordert.length);
    assert.deepEqual(W.angefordert, ['screen']);
    assert.equal(W.freigegeben, 0, 'solange es läuft, gehalten');
    await fertig(s, 0);
    await bis(() => W.freigegeben === 1);
  } finally { W.zurueck(); weg(); }
});

test('Wake Lock in `try`: ohne `navigator.wakeLock` und bei Ablehnung läuft das Hochladen trotzdem', { ...MIT_DOM }, async () => {
  for (const modus of ['fehlt', 'abgelehnt']) {
    const W = wakeLock(modus);
    const s = await start();
    try {
      await hochladen(s, [datei('Lied.mp3')], 'einzeln');
      await fertig(s, 0);
      assert.equal(s.q('[data-status]').textContent.trim(), 'Wird einsortiert …', modus);
      assert.deepEqual(fehler(s), [], modus);
    } finally { W.zurueck(); weg(); }
  }
});

/* ------------------------------------------------------------------ Warten, Abbrechen, Unterbrechung */

test('Zwei Uploads gleichzeitig: der weitere wartet („wartet“), kein 429 sichtbar, danach geht es nacheinander weiter', { ...MIT_DOM }, async () => {
  const s = await start({ grenzen: { upload_parallel: 1 } });
  try {
    await hochladen(s, [datei('Eins.mp3')], 'einzeln');
    await bis(() => s.m.xhrs[0]);
    await hochladen(s, [datei('Zwei.mp3')], 'einzeln');
    await warte(30);
    assert.equal(s.m.xhrs.length, 1, 'der zweite Auftrag sendet noch nicht');
    const zwei = karte(s, 0);
    assert.equal(zwei.querySelector('[data-marke]').textContent.trim(), 'wartet');
    assert.match(kText(zwei), /Bildschirm anlassen/);
    assert.match(kText(karte(s, 1)), /Wird hochgeladen/);
    await fertig(s, 0);
    const x = await bis(() => s.m.xhrs[1]);
    assert.equal(feld(x, 'datei').name, 'Zwei.mp3');
  } finally { weg(); }
});

test('Mit `upload_parallel` 2 laufen zwei Aufträge zugleich, der dritte wartet', { ...MIT_DOM }, async () => {
  const s = await start({ grenzen: { upload_parallel: 2 } });
  try {
    for (const n of ['A', 'B', 'C']) await hochladen(s, [datei(`${n}.mp3`)], 'einzeln');
    await warte(30);
    assert.equal(s.m.xhrs.length, 2);
    assert.equal(karte(s, 0).querySelector('[data-marke]')?.textContent.trim(), 'wartet');
  } finally { weg(); }
});

test('Ein 429 `zu_viele_uploads` ist kein Fehler: die Datei wartet und wird noch einmal gesendet', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, [datei('Lied.mp3')], 'einzeln');
    await fertig(s, 0, { status: 429, body: { v: 1, fehler: { code: 'zu_viele_uploads', text: 'x' } } });
    assert.deepEqual(fehler(s), []);
    assert.ok(!/Geht leider nicht/.test(s.q('main').textContent));
    const x = await bis(() => s.m.xhrs[1]);
    assert.equal(feld(x, 'datei').name, 'Lied.mp3');
    await fertig(s, 1);
    assert.equal(s.q('[data-status]').textContent.trim(), 'Wird einsortiert …');
  } finally { weg(); }
});

test('Abbrechen: der laufende Upload wird abgebrochen, die übrigen Dateien werden nicht gesendet; „Abgebrochen“ mit Zahl der angekommenen Dateien', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, HAFEN(), 'neu', async () => { tippe(s.q('#hz-name'), 'Buch'); await s.flush(3); });
    await fertig(s, 0);
    const x = await bis(() => s.m.xhrs[1]);
    x.fortschritt(5, 1000);
    await klick(s, s.q('[data-abbrechen]'));
    assert.equal(x.abgebrochen, true, 'xhr.abort()');
    await warte(30);
    assert.equal(s.m.xhrs.length, 2, 'die dritte Datei wird nicht gesendet');
    const k = karte(s);
    assert.equal(k.dataset.phase, 'abgebrochen');
    assert.match(kText(k), /Abgebrochen\. 1 von 3 Dateien waren schon angekommen/);
    assert.ok(!/Bildschirm/.test(kText(k)));
  } finally { weg(); }
});

test('Abbrechen eines wartenden Auftrags: nichts wird gesendet', { ...MIT_DOM }, async () => {
  const s = await start({ grenzen: { upload_parallel: 1 } });
  try {
    await hochladen(s, [datei('Eins.mp3')], 'einzeln');
    await bis(() => s.m.xhrs[0]);
    await hochladen(s, [datei('Zwei.mp3')], 'einzeln');
    await klick(s, karte(s, 0).querySelector('[data-abbrechen]'));
    assert.equal(karte(s, 0).dataset.phase, 'abgebrochen');
    assert.match(kText(karte(s, 0)), /Abgebrochen\. Es wurde nichts einsortiert\./);
    await fertig(s, 0);
    await warte(30);
    assert.equal(s.m.xhrs.length, 1);
  } finally { weg(); }
});

test('Unterbrechung: nach der Rückkehr ohne Fortschritt „Unterbrochen. Wähle die Datei noch einmal.“; „Fehlende Datei wählen“ sendet mit derselben gruppe', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, HAFEN(), 'neu', async () => { tippe(s.q('#hz-name'), 'Buch'); await s.flush(3); });
    await fertig(s, 0);
    const x = await bis(() => s.m.xhrs[1]);
    x.fortschritt(500, 1000);
    await warte(5);
    document.dispatchEvent(new window.Event('visibilitychange')); // der Bildschirm war gesperrt, die Seite kommt zurück
    await bis(() => x.abgebrochen);
    await bis(() => karte(s)?.dataset.phase === 'hochladen' && s.m.xhrs.length === 3);
    // die dritte Datei geht weiter, die zweite ist unterbrochen
    await fertig(s, 2);
    const k = await bis(() => (karte(s)?.dataset.phase === 'fehlt' ? karte(s) : null));
    assert.match(kText(k), /Es fehlt noch eine Datei\. 2 von 3 Dateien sind angekommen\. Wähle die fehlende Datei noch einmal\./);
    assert.equal(k.querySelector('[data-dateifehler]').textContent, 'Unterbrochen. Wähle die Datei noch einmal.');
    assert.equal(k.querySelector('.hz-dateien .nm').textContent, '02 Die Karte.mp3');
    assert.equal(k.querySelector('[data-fehlende]').textContent.trim(), 'Fehlende Datei wählen');
    const gruppe = feld(s.m.xhrs[0], 'gruppe');
    await klick(s, k.querySelector('[data-fehlende]'));
    await waehle(s, [datei('02 Die Karte.mp3')], 'fehlende');
    const neu = await bis(() => s.m.xhrs[3]);
    assert.equal(feld(neu, 'gruppe'), gruppe);
    assert.equal(feld(neu, 'gruppe_anzahl'), '3');
    assert.equal(feld(neu, 'datei').name, '02 Die Karte.mp3');
    assert.notEqual(feld(neu, 'upload_id'), feld(x, 'upload_id'));
    await fertig(s, 3);
    assert.equal(karte(s).dataset.phase, 'sortieren');
  } finally { weg(); }
});

test('Ein Netzfehler beim Senden: „Die Verbindung ist abgebrochen …“ und „Fehlende Datei wählen“', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, [datei('Lied.mp3')], 'einzeln');
    const x = await bis(() => s.m.xhrs[0]);
    x.netzfehler();
    const k = await bis(() => (karte(s)?.dataset.phase === 'fehlt' ? karte(s) : null));
    assert.equal(k.querySelector('[data-dateifehler]').textContent, FEHLER.verbindung_abgebrochen);
    assert.ok(k.querySelector('[data-fehlende]'));
  } finally { weg(); }
});

/* ------------------------------------------------------------------ Fehlercodes */

test('413 (Proxy oder Backend) → `datei_zu_gross` mit der Zahl aus `hello.grenzen`; die Karte „Geht leider nicht.“ bleibt', { ...MIT_DOM }, async () => {
  const s = await start({ grenzen: { upload_max_bytes: 2 * GIB } });
  try {
    await hochladen(s, [datei('Gross.m4b')], 'einzeln');
    await fertig(s, 0, { status: 413, body: 'zu groß' });
    const k = await bis(() => (karte(s)?.dataset.phase === 'fehler' ? karte(s) : null));
    assert.match(kText(k), /Geht leider nicht\./);
    assert.equal(k.querySelector('[data-dateifehler]').textContent, 'Die Datei ist zu groß (mehr als 2 GB). Kopiere sie am Computer in den Eingang-Ordner auf dem NAS. Frag den Administrator nach dem Ordner.');
    assert.equal(k.classList.contains('err'), true);
    await warte(50);
    assert.ok(karte(s), 'die Karte bleibt');
  } finally { weg(); }
});

test('415 `format_nicht_erlaubt` und 507 `kein_speicher` kommen mit dem Text des Designs', { ...MIT_DOM }, async () => {
  const s = await start({ grenzen: { endungen: undefined } });
  try {
    await hochladen(s, [datei('Lied.wma')], 'einzeln');
    await fertig(s, 0, { status: 415, body: { v: 1, fehler: { code: 'format_nicht_erlaubt', text: 'x' } } });
    let k = await bis(() => (karte(s)?.dataset.phase === 'fehler' ? karte(s) : null));
    assert.equal(k.querySelector('[data-dateifehler]').textContent, 'Dieses Dateiformat spielt die Box nicht. Erlaubt sind MP3, M4A, M4B, AAC, FLAC, OGG, Opus und WAV.');
    await hochladen(s, [datei('Lied2.mp3')], 'einzeln');
    await fertig(s, 1, { status: 507, body: { v: 1, fehler: { code: 'kein_speicher', text: 'x' } } });
    k = await bis(() => (karte(s, 0)?.dataset.phase === 'fehler' ? karte(s, 0) : null));
    assert.equal(k.querySelector('[data-dateifehler]').textContent, 'Auf dem NAS ist kein Platz mehr. Bitte dem Administrator Bescheid sagen.');
  } finally { weg(); }
});

test('Nicht erlaubte Zeichen und unbekannte Antwort: Standardtext, nie ein Code für Eltern', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, [datei('Lied.mp3')], 'einzeln');
    await fertig(s, 0, { status: 500, body: '<html>kaputt</html>' });
    const k = await bis(() => (karte(s)?.dataset.phase === 'fehler' ? karte(s) : null));
    assert.match(k.querySelector('[data-dateifehler]').textContent, /^Das hat nicht geklappt\./);
  } finally { weg(); }
});

test('Zu große Datei vorab: Warnung im Blatt, die Datei wird nicht gesendet, die übrigen gehen hoch; die Karte nennt sie mit dem Text', { ...MIT_DOM }, async () => {
  const s = await start({ grenzen: { upload_max_bytes: 2 * GIB } });
  try {
    await dateienWaehlen(s, [datei('01 Das Boot.mp3'), datei('02 Der Nebel.mp3'), riesig('03 Der See komplett.m4b')]);
    assert.equal(s.q('[data-gewaehlt]').textContent.trim(), '2 Dateien gewählt (01 Das Boot.mp3 …). Was ist das?', 'gezählt werden die Dateien, die hochgeladen werden');
    const w = s.q('dialog.blatt[open] [data-abgelehnt="datei_zu_gross"]');
    assert.ok(w, 'Warnung im Blatt');
    assert.match(w.textContent, /„03 Der See komplett\.m4b“ wird nicht hochgeladen\. Die Datei ist zu groß \(mehr als 2 GB\)\. Kopiere sie am Computer in den Eingang-Ordner auf dem NAS\. Frag den Administrator nach dem Ordner\./);
    await klick(s, kachel(s, 'neu'));
    assert.ok(s.q('dialog.blatt[open] [data-abgelehnt]'), 'auch in der Vorschau');
    tippe(s.q('#hz-name'), 'Der Zauberer vom See');
    await s.flush(3);
    await klick(s, knopf(s, 'Hochladen'));
    const x = await bis(() => s.m.xhrs[0]);
    assert.equal(feld(x, 'gruppe_anzahl'), '2');
    const k = karte(s);
    assert.match(kText(k), /03 Der See komplett\.m4b.*zu groß \(mehr als 2 GB\)/);
    await fertig(s, 0); await fertig(s, 1);
    assert.equal(s.m.xhrs.length, 2, 'die große Datei wurde nie gesendet');
  } finally { weg(); }
});

test('Nur zu große oder unerlaubte Dateien: kein Blatt, kein Senden, die Karte zeigt jeden Fehler und bleibt', { ...MIT_DOM }, async () => {
  const s = await start({ grenzen: { upload_max_bytes: 2 * GIB, endungen: ['mp3', 'm4a', 'm4b'] } });
  try {
    await dateienWaehlen(s, [riesig('Gross.m4b'), datei('Lied.wma')]);
    assert.ok(!blatt(s));
    assert.equal(s.m.xhrs.length, 0);
    const k = karte(s);
    assert.equal(k.dataset.phase, 'fehler');
    const z = k.querySelectorAll('[data-dateifehler]');
    assert.match(z[0].textContent, /^Die Datei ist zu groß \(mehr als 2 GB\)/);
    assert.match(z[1].textContent, /^Dieses Dateiformat spielt die Box nicht\./);
    assert.deepEqual(fehler(s), []);
  } finally { weg(); }
});

test('Ordner: Bilder und Textdateien werden still übergangen, nur Audiodateien kommen ins Blatt', { ...MIT_DOM }, async () => {
  zeiger('fine');
  const s = await start({ grenzen: { endungen: ['mp3'] } });
  try {
    await klick(s, s.q('[data-ordner-waehlen]'));
    const e = s.q('input[data-hinz-eingabe="ordner"]');
    assert.equal(e.webkitdirectory, true);
    await waehle(s, [datei('01 A.mp3'), datei('02 B.mp3'), datei('cover.jpg'), datei('Liste.txt')], 'ordner');
    assert.equal(s.q('[data-gewaehlt]').textContent.trim(), '2 Dateien gewählt (01 A.mp3 …). Was ist das?');
    assert.ok(!s.q('[data-abgelehnt]'));
  } finally { weg(); }
});

test('Ziehen: eine Datei auf die Ziehfläche öffnet das Blatt wie die Dateiwahl', { ...MIT_DOM }, async () => {
  zeiger('fine');
  const s = await start();
  try {
    const flaeche = s.q('[data-ziehflaeche]');
    const ev = new window.Event('drop', { bubbles: true, cancelable: true });
    ev.dataTransfer = { files: HAFEN(), items: [] };
    flaeche.dispatchEvent(ev);
    await warte(30); await s.flush(10);
    assert.ok(blatt(s));
    assert.equal(s.q('[data-gewaehlt]').textContent.trim(), '3 Dateien gewählt (01 Der Hafen.mp3 …). Was ist das?');
    assert.equal(ev.defaultPrevented, true);
  } finally { weg(); }
});

/* ------------------------------------------------------------------ Ergebnis aus dem Eingang */

function eingangAntwort(s, bauen) {
  s.m.on('tobibox/eingang/list', (msg) => {
    const x = s.m.xhrs[0];
    const gruppe = x ? feld(x, 'gruppe') : null;
    const l = bauen({ gruppe, ordner: gruppe ? `Upload ${gruppe.slice(0, 8)}` : null, x, msg });
    return { eintraege: l, gesamt: l.length, sortierung_laeuft: false, geprueft_am: '2026-11-13T12:00:00Z' };
  });
}
const erledigt = (extra) => ({ id: 'e1', art: 'ordner', dateien: 3, ignoriert: 0, groesse_bytes: 3000, status: 'erledigt', hinweise: [], ergebnis: [], fertig_am: '2026-11-13T12:00:00Z', quelle: 'upload', wunsch: null, pruefen: false, ...extra });
const buch = { id: 'neu1', name: 'Kapitän Knopf', typ: 'normal', ordner: 'Kapitän Knopf', pruefen: false, hinweise: [], art: 'hoerbuch', cover_stand: null, folgen: [folge('Kapitän Knopf', 'Kapitän Knopf', { art: 'ordner', tracks: 3 })] };

async function bisSortiert(s) {
  await hochladen(s, HAFEN(), 'neu', async () => { tippe(s.q('#hz-name'), 'Kapitän Knopf'); await klick(s, s.q('[data-art-wahl="hoerbuch"]')); });
  await bis(() => s.q('[data-abbrechen]'));
  s.q('[data-abbrechen]').focus(); // wie ein Tastaturnutzer: der Fokus steht auf der Karte, die gleich ersetzt wird
  for (let i = 0; i < 3; i += 1) await fertig(s, i);
}

test('Ergebnis: „Wird einsortiert …“, danach fertig mit „Hörbuch „Kapitän Knopf“ · 3 Kapitel“ und „Öffnen“; die Karte erhält den Fokus', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    s.m.backend.serien.neu1 = buch;
    let fertigGestellt = false;
    eingangAntwort(s, ({ ordner }) => (fertigGestellt ? [erledigt({ name: ordner, ergebnis: [{ serie_id: 'neu1', serie_name: 'Kapitän Knopf', serie_neu: true, folge: 'Kapitän Knopf', anzeige: 'Kapitän Knopf', tracks: 3, pruefen: false, pruefen_gruende: [] }] })] : []));
    await bisSortiert(s);
    assert.equal(karte(s).dataset.phase, 'sortieren');
    assert.equal(s.q('[data-status]').textContent.trim(), 'Wird einsortiert …');
    assert.equal(s.qa('[data-schritte] li.done').length, 1);
    assert.equal(s.q('[data-schritte] li[aria-current="step"]').textContent.trim(), 'Einsortieren');
    assert.ok(!/Bildschirm/.test(kText(karte(s))));
    fertigGestellt = true;
    const k = await bis(() => (karte(s)?.dataset.phase === 'fertig' ? karte(s) : null));
    await bis(() => /Kapitel/.test(kText(karte(s))));
    assert.equal(k.querySelector('[data-marke]').dataset.marke, 'ok');
    assert.equal(k.querySelector('[data-marke]').textContent.trim(), 'fertig');
    assert.equal(k.querySelector('[data-ergebnis]').textContent.trim(), 'Hörbuch „Kapitän Knopf“ · 3 Kapitel');
    assert.equal(k.querySelector('[data-oeffnen]').getAttribute('href'), '#serie-neu1');
    assert.equal(k.querySelector('[data-oeffnen]').textContent.trim(), 'Öffnen');
    assert.ok(!k.querySelector('[data-art-hinweis]'), 'nur bei „Weiß nicht“');
    assert.equal(s.el.shadowRoot.activeElement, k, 'die Fertig-Karte erhält den Fokus');
    assert.match(s.q('#live').textContent, /fertig$/);
  } finally { weg(); }
});

test('Ergebnis bei „Sortier du“: dazu der Hinweis zur vorgeschlagenen Art', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    s.m.backend.serien.neu1 = { ...buch, art: 'musik', name: 'Sommerlieder' };
    eingangAntwort(s, ({ ordner }) => [erledigt({ name: ordner, ergebnis: [{ serie_id: 'neu1', serie_name: 'Sommerlieder', serie_neu: true, folge: 'a', tracks: 1, pruefen: false, pruefen_gruende: [] }] })]);
    await hochladen(s, [datei('x.mp3'), datei('y.mp3')], 'auto');
    await fertig(s, 0); await fertig(s, 1);
    const k = await bis(() => (karte(s)?.dataset.phase === 'fertig' ? karte(s) : null));
    await bis(() => k.querySelector('[data-art-hinweis]'));
    assert.equal(k.querySelector('[data-art-hinweis]').textContent.trim(), 'Art: Musik (aus den Tags vorgeschlagen). Stimmt nicht? Im Eintrag „Art ändern“.');
  } finally { weg(); }
});

test('Ergebnis „bitte kurz ansehen“: gelbe Karte mit Grund, „Daraus ist geworden“, „Ansehen“ und „Das ist richtig“ (bestätigt den Eintrag)', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    s.m.backend.serien.neu1 = { ...buch, pruefen: true };
    eingangAntwort(s, ({ ordner }) => [erledigt({ name: ordner, pruefen: true, ergebnis: [{ serie_id: 'neu1', serie_name: 'Kapitän Knopf', serie_neu: true, folge: 'Kapitän Knopf', tracks: 3, pruefen: true, pruefen_gruende: ['tags_fehlen'] }] })]);
    await bisSortiert(s);
    const k = await bis(() => (karte(s)?.dataset.phase === 'pruefen' ? karte(s) : null));
    assert.ok(k.classList.contains('warn'));
    assert.equal(k.querySelector('[data-marke]').textContent.trim(), 'bitte ansehen');
    assert.match(kText(k), /Bitte kurz ansehen\. In der Datei steht kein Albumname\. Name und Hörspiel sind aus dem Dateinamen geraten\./);
    await bis(() => /Daraus ist geworden:/.test(kText(karte(s))));
    assert.match(kText(karte(s)), /Daraus ist geworden: Hörbuch „Kapitän Knopf“ · 3 Kapitel/);
    assert.equal(k.querySelector('[data-ansehen]').getAttribute('href'), '#serie-neu1');
    await klick(s, k.querySelector('[data-richtig]'));
    assert.deepEqual(s.m.aufrufe('tobibox/einsortierung/bestaetigen').map((m) => m.serie_id), ['neu1']);
    assert.equal(karte(s).dataset.phase, 'fertig');
    assert.equal(s.m.backend.serien.neu1.pruefen, false);
  } finally { weg(); }
});

test('Ergebnis „geht nicht“: rote Karte mit dem Grund aus den Hinweisen (Kopierschutz)', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    eingangAntwort(s, ({ ordner }) => [erledigt({ name: ordner, status: 'blockiert', fertig_am: null, hinweise: [{ code: 'kopierschutz', datei: 'a.m4b', text: 'x' }] })]);
    await bisSortiert(s);
    const k = await bis(() => (karte(s)?.dataset.phase === 'fehler' ? karte(s) : null));
    assert.ok(k.classList.contains('err'));
    assert.match(kText(k), /Geht leider nicht\. Diese Datei ist kopiergeschützt \(zum Beispiel von Audible oder Apple Books\)\. Die Box kann sie nicht abspielen\. Nimm eine Datei ohne Kopierschutz\./);
    assert.equal(k.querySelector('[data-marke]').textContent.trim(), 'geht nicht');
  } finally { weg(); }
});

test('Ergebnis „Es fehlt noch eine Datei“ (nach 30 Minuten Ruhe im Eingang): gelbe Karte mit „Fehlende Datei wählen“', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    eingangAntwort(s, ({ ordner }) => [erledigt({ name: ordner, dateien: 2, status: 'teilweise', pruefen: true, hinweise: [{ code: 'gruppe_unvollstaendig', datei: null, text: 'x' }], ergebnis: [{ serie_id: 'neu1', serie_name: 'K', serie_neu: true, folge: 'a', tracks: 2, pruefen: true, pruefen_gruende: [] }] })]);
    await bisSortiert(s);
    const k = await bis(() => (karte(s)?.dataset.phase === 'fehlt' ? karte(s) : null));
    assert.match(kText(k), /Es fehlt noch eine Datei\. 3 von 3 Dateien sind angekommen\./, 'die Seite hat alle gesendet; die Zahl kommt von ihr');
    assert.ok(k.querySelector('[data-fehlende]'));
  } finally { weg(); }
});

test('Ohne Antwort des Eingangs nach langer Zeit: „Das dauert länger als sonst.“ statt endlosem Warten', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    s.mo.langeMs = 30;
    eingangAntwort(s, () => []);
    await bisSortiert(s);
    const k = await bis(() => (karte(s)?.dataset.phase === 'lange' ? karte(s) : null));
    assert.match(kText(k), /Das dauert länger als sonst\./);
  } finally { weg(); }
});

test('Ohne die Fähigkeit `eingang` ist „fertig“ gleich nach dem Hochladen, mit „Hochgeladen. Es wird gleich einsortiert.“', { ...MIT_DOM }, async () => {
  const s = await start({ faehigkeiten: ALLE.filter((f) => f !== 'eingang') });
  try {
    await hochladen(s, [datei('Lied.mp3')], 'einzeln');
    await fertig(s, 0);
    const k = await bis(() => (karte(s)?.dataset.phase === 'fertig' ? karte(s) : null));
    assert.match(kText(k), /Hochgeladen\. Es wird gleich einsortiert\./);
    assert.equal(s.m.aufrufe('tobibox/eingang/list').length, 0);
  } finally { weg(); }
});

test('Mehrere Aufträge: neueste zuerst, jeder mit eigenem Fortschritt; die Liste heißt „Zuletzt hinzugefügt“', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, [datei('Eins.mp3')], 'einzeln');
    await hochladen(s, [datei('Zwei.mp3')], 'einzeln');
    assert.equal(s.q('[data-titel="zuletzt"]').textContent.trim(), 'Zuletzt hinzugefügt');
    assert.deepEqual(karten(s).map((k) => k.querySelector('[data-titel-eintrag]').textContent.trim()), ['1 Datei: Zwei.mp3', '1 Datei: Eins.mp3']);
    assert.deepEqual(s.mo.zeilen().map((z) => z.art), ['upload', 'upload'], 'A11b mischt hier weitere Arten dazu');
    assert.equal(s.mo.laufend.length, 2, 'für das Band und den Punkt am Reiter „Bibliothek“ (A11b)');
    await fertig(s, 0);
    assert.equal(s.mo.laufend.length, 2, 'ein Auftrag, der einsortiert wird, läuft noch');
  } finally { weg(); }
});

test('Der Upload läuft weiter, wenn man die Seite verlässt; zurück ist der Stand da', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, [datei('Lied.mp3')], 'einzeln');
    const x = await bis(() => s.m.xhrs[0]);
    await geheZu(s, '#bibliothek');
    x.fortschritt(500, 1000);
    await s.flush(4);
    await geheZu(s, '#hinzufuegen');
    assert.match(s.q('[data-status]').textContent, /Wird hochgeladen … 50 %/);
  } finally { weg(); }
});

test('Sichtbare Marken: jede Zustandsmarke hat Text (Farbe nie allein) und die Kacheln sind echte Knöpfe', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await dateienWaehlen(s, HAFEN());
    for (const k of s.qa('dialog.blatt[open] [data-kacheln] button')) { assert.equal(k.tagName, 'BUTTON'); assert.equal(k.getAttribute('type'), 'button'); }
    await klick(s, kachel(s, 'neu'));
    await klick(s, knopf(s, 'Hochladen'));
    await bis(() => karte(s));
    assert.match(kText(karte(s)), /Bildschirm anlassen, bis es fertig ist\./);
  } finally { weg(); }
});

/* ================================================================== A11b Teil 2: Liste aus dem Eingang */

const minuten = (min) => new Date(Date.now() - min * 60000).toISOString();
const erg = (teil = {}) => ({ serie_id: 's2', serie_name: 'Bibi Blocksberg', serie_neu: true, folge: 'b-01.mp3', anzeige: 'Hexen gibt es doch', tracks: 1, pruefen: false, pruefen_gruende: [], ...teil });
const nasFertig = (teil = {}) => eingangEintrag({ name: 'Bibi-Ordner', art: 'ordner', dateien: 3, quelle: 'nas', fertig_am: minuten(5), zuerst_gesehen: minuten(8), ergebnis: [erg()], ...teil });
const nasLaeuft = (teil = {}) => eingangEintrag({ name: 'Neuer-Ordner', art: 'ordner', dateien: 6, quelle: 'nas', status: 'laeuft', fertig_am: null, zuerst_gesehen: minuten(1), ...teil });
const karteMit = (s, teil) => karten(s).find((k) => kText(k).includes(teil));
const bandText = (s) => s.q('[data-eingang-band]')?.textContent.replace(/\s+/g, ' ').trim();

test('Liste: Einträge vom NAS erscheinen ohne Upload-Schritt, mit „vom NAS“, „Wird einsortiert …“ und „Daraus ist geworden“', { ...MIT_DOM }, async () => {
  const s = await start({ eingang: [nasLaeuft()], eingangErledigt: [nasFertig()] });
  try {
    assert.equal(karten(s).length, 2);
    const lauf = karteMit(s, 'Neuer-Ordner');
    assert.equal(lauf.dataset.phase, 'sortieren');
    assert.equal(lauf.querySelector('[data-quelle]').textContent.trim(), 'vom NAS');
    assert.equal(lauf.querySelector('[data-status]').textContent.trim(), 'Wird einsortiert …');
    assert.equal(lauf.querySelector('[data-abbrechen]'), null, 'ein Eintrag vom NAS wird nicht hochgeladen, es gibt nichts abzubrechen');
    assert.ok(!/Bildschirm/.test(kText(lauf)));
    assert.equal(lauf.querySelector('[data-schritte]'), null, 'vom NAS: kein Hochladeschritt (Design 7.3 Punkt 10)');
    const fertig = karteMit(s, 'Bibi-Ordner');
    assert.equal(fertig.dataset.phase, 'fertig');
    assert.equal(fertig.querySelector('[data-marke]').textContent.trim(), 'fertig');
    assert.equal(fertig.querySelector('[data-quelle]').textContent.trim(), 'vom NAS');
    assert.equal(fertig.querySelector('[data-daraus]').textContent.trim(), 'Daraus ist geworden: Neuer Eintrag „Bibi Blocksberg“ · 1 Folge');
    assert.equal(fertig.querySelector('[data-oeffnen]').getAttribute('href'), '#serie-s2');
    assert.equal(fertig.querySelector('[data-oeffnen]').textContent.trim(), 'Öffnen');
    assert.match(kText(fertig), /^3 Dateien: Bibi-Ordner/);
    assert.equal(s.q('[data-liste="zuletzt"]').children.length, 2);
  } finally { weg(); }
});

test('Liste: Einträge vom Handy (anderes Gerät) heißen „vom Handy“, der Ordner „Upload ab12cd34“ wird nicht als Name gezeigt; Ältere als 24 Stunden fehlen', { ...MIT_DOM }, async () => {
  const s = await start({
    eingangErledigt: [
      nasFertig({ name: 'Upload ab12cd34', quelle: 'upload', dateien: 3 }),
      nasFertig({ name: 'Zu alt', fertig_am: minuten(25 * 60), zuerst_gesehen: minuten(25 * 60 + 5) }),
      nasFertig({ name: 'Grenze', fertig_am: minuten(23 * 60 + 50), zuerst_gesehen: minuten(24 * 60) }),
    ],
  });
  try {
    assert.equal(karten(s).length, 2);
    const h = karteMit(s, '3 Dateien');
    assert.equal(h.querySelector('[data-quelle]').textContent.trim(), 'vom Handy');
    assert.ok(!/Upload ab12cd34/.test(kText(h)));
    assert.ok(!karteMit(s, 'Zu alt'));
    assert.ok(karteMit(s, 'Grenze'));
    assert.equal(s.q('[data-titel="zuletzt"]').textContent.trim(), 'Zuletzt hinzugefügt');
  } finally { weg(); }
});

test('Liste: ohne Einträge in den letzten 24 Stunden steht keine Liste da', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig({ fertig_am: minuten(30 * 60), zuerst_gesehen: minuten(30 * 60) })] });
  try {
    assert.equal(s.q('[data-liste="zuletzt"]'), null);
    assert.equal(s.q('[data-titel="zuletzt"]'), null);
  } finally { weg(); }
});

test('Liste: „bitte kurz ansehen“ mit Gründen (jeder Code ein Satz, ohne Doppelte), „Daraus ist geworden“, „Ansehen“, „Das ist richtig“ und „Das stimmt nicht“; kein „Anders einsortieren“', { ...MIT_DOM }, async () => {
  const e = nasFertig({ pruefen: true, ergebnis: [erg({ pruefen: true, pruefen_gruende: ['tags_fehlen', 'nummer_doppelt', 'track_doppelt', 'track_teils_leer'] })] });
  const s = await start({ eingangErledigt: [e] });
  try {
    const k = karte(s);
    assert.equal(k.dataset.phase, 'pruefen');
    assert.ok(k.classList.contains('warn'));
    assert.equal(k.querySelector('[data-marke]').textContent.trim(), 'bitte ansehen');
    assert.equal(k.querySelector('[data-quelle]').textContent.trim(), 'vom NAS');
    assert.deepEqual([...k.querySelectorAll('[data-grund]')].map((x) => x.textContent), [GRUENDE.tags_fehlen, GRUENDE.nummer_doppelt, GRUENDE.track_doppelt]);
    assert.match(kText(k), /Bitte kurz ansehen\. In der Datei steht kein Albumname/);
    assert.equal(k.querySelector('[data-daraus]').textContent.trim(), 'Daraus ist geworden: Neuer Eintrag „Bibi Blocksberg“ · 1 Folge');
    assert.deepEqual([...k.querySelectorAll('.btns .btn')].map((b) => b.textContent.trim()), ['Ansehen', 'Das ist richtig', 'Das stimmt nicht']);
    assert.equal(k.querySelector('[data-ansehen]').getAttribute('href'), '#serie-s2');
    assert.equal(k.querySelector('[data-stimmt-nicht]').getAttribute('href'), '#serie-s2');
    assert.ok(!/Anders einsortieren/.test(kText(k)));
    assert.equal(bandText(s) ?? null, null, 'das Band gibt es nur in der Bibliothek');
  } finally { weg(); }
});

test('Liste: ein Grund, den die Seite nicht kennt, wird nie als Code gezeigt, sondern als Rückfallsatz', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig({ pruefen: true, ergebnis: [erg({ pruefen: true, pruefen_gruende: ['gibt_es_nicht'] })] })] });
  try {
    assert.equal(karte(s).querySelector('[data-grund]').textContent, 'Beim Einsortieren war etwas unsicher. Schau kurz, ob Name und Art stimmen.');
    assert.ok(!/gibt_es_nicht/.test(kText(karte(s))));
  } finally { weg(); }
});

test('Liste: „Das ist richtig“ bestätigt die Serie; der Eintrag ist nicht mehr „zu prüfen“ (Band weg), die Karte bleibt als „fertig“ und erhält den Fokus', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig({ pruefen: true, ergebnis: [erg({ pruefen: true, pruefen_gruende: ['tags_fehlen'] })] })] });
  try {
    assert.equal(s.el.ctx.eingang().pruefen.length, 1, 'bei „bitte ansehen“ ist die Serie `s2` im Mock noch zu prüfen');
    await klick(s, karte(s).querySelector('[data-richtig]'));
    await s.flush(12);
    assert.deepEqual(s.m.aufrufe('tobibox/einsortierung/bestaetigen').map((m) => m.serie_id), ['s2']);
    assert.equal(s.el.ctx.eingang().pruefen.length, 0, 'im Eingang nichts mehr zu prüfen');
    const k = karte(s);
    assert.equal(k.dataset.phase, 'fertig');
    assert.equal(k.querySelector('[data-richtig]'), null);
    assert.equal(s.el.shadowRoot.activeElement, k, 'der Knopf ist weg, der Fokus geht auf die Karte');
    assert.deepEqual(s.qa('.toast:not(.err) .tmsg').map((x) => x.textContent), ['Danke, ist erledigt.']);
    await geheZu(s, '#bibliothek');
    assert.ok(!/bitte kurz ansehen/.test(bandText(s) ?? ''), 'kein orange Band mehr');
  } finally { weg(); }
});

test('Liste: Fehler bei „Das ist richtig“ bleibt als Meldung stehen und die Karte bleibt „bitte ansehen“', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig({ pruefen: true, ergebnis: [erg({ pruefen: true, pruefen_gruende: ['tags_fehlen'] })] })] });
  try {
    s.m.on('tobibox/einsortierung/bestaetigen', () => { throw Object.assign(new Error('x'), { code: 'serie_nicht_gefunden' }); });
    await klick(s, karte(s).querySelector('[data-richtig]'));
    assert.equal(karte(s).dataset.phase, 'pruefen');
    assert.equal(fehler(s).length, 1);
  } finally { weg(); }
});

test('Liste: „geht nicht“ mit Grund und nächster Handlung (Kopierschutz); ohne bekannten Grund ein allgemeiner Satz mit nächster Handlung', { ...MIT_DOM }, async () => {
  const s = await start({ eingang: [
    eingangEintrag({ name: 'a.m4b', quelle: 'nas', status: 'blockiert', fertig_am: null, zuerst_gesehen: minuten(10), hinweise: [{ code: 'kopierschutz', datei: 'a.m4b', text: 'x' }] }),
    eingangEintrag({ name: 'b.mp3', quelle: 'nas', status: 'blockiert', fertig_am: null, zuerst_gesehen: minuten(20), hinweise: [] }),
  ] });
  try {
    const k = karteMit(s, 'a.m4b');
    assert.equal(k.dataset.phase, 'fehler');
    assert.ok(k.classList.contains('err'));
    assert.equal(k.querySelector('[data-marke]').textContent.trim(), 'geht nicht');
    assert.match(kText(k), /Geht leider nicht\. Diese Datei ist kopiergeschützt .* Nimm eine Datei ohne Kopierschutz\./);
    assert.match(kText(karteMit(s, 'b.mp3')), /Geht leider nicht\. Das hat nicht geklappt\. Versuche es später noch einmal, sonst frag /);
    assert.equal(k.querySelector('[data-richtig]'), null);
  } finally { weg(); }
});

test('Liste: „geht nicht“ nennt die Dateien je Grund (drei Namen, „und N weitere“, gleicher Name mit Ordner)', { ...MIT_DOM }, async () => {
  const h = (code, datei) => ({ code, datei, text: 'x' });
  const s = await start({ eingang: [eingangEintrag({ name: 'Hafen', quelle: 'nas', art: 'ordner', dateien: 1812, status: 'blockiert', fertig_am: null, zuerst_gesehen: minuten(10), hinweise: [
    h('probedekodierung_fehlgeschlagen', 'Die Haferhorde/26. Kapitel 24_ Volle Mähne.mp3.mp3'), h('probedekodierung_fehlgeschlagen', 'Felix/Briefe.mp3'),
    h('probedekodierung_fehlgeschlagen', 'Anderer/Briefe.mp3'), h('probedekodierung_fehlgeschlagen', 'X/vier.mp3'), h('probedekodierung_fehlgeschlagen', 'X/fuenf.mp3'),
    h('kopierschutz', 'Buch.m4b')] })] });
  try {
    const k = karteMit(s, 'Hafen');
    assert.equal(k.dataset.phase, 'fehler');
    const gr = [...k.querySelectorAll('[data-gruppe]')];
    assert.equal(gr.length, 2);
    assert.deepEqual([...gr[0].querySelectorAll('[data-datei]')].map((x) => kText(x)), ['26. Kapitel 24_ Volle Mähne.mp3.mp3', 'Felix/Briefe.mp3', 'Anderer/Briefe.mp3']);
    assert.equal(kText(gr[0].querySelector('[data-weitere]')), 'und 2 weitere');
    assert.match(kText(gr[0]), /^Die Datei ist kaputt oder unvollständig\. Bitte noch einmal kopieren\./);
    assert.deepEqual([...gr[1].querySelectorAll('[data-datei]')].map((x) => kText(x)), ['Buch.m4b']);
    assert.equal(gr[1].querySelector('[data-weitere]'), null);
    assert.doesNotMatch(kText(k), /Die Haferhorde\//, 'nur der Dateiname, nicht der Pfad');
  } finally { weg(); }
});

test('Liste: „teilweise“ zeigt „Daraus ist geworden“ und darunter „Liegt noch im Eingang“ mit Grund und Dateien, ohne „Das ist richtig“', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig({ name: 'Gemischt', dateien: 4, status: 'teilweise', pruefen: true, wunsch: { ziel: 'neu', art: 'hoerspiel' },
    hinweise: [{ code: 'probedekodierung_fehlgeschlagen', datei: 'Gemischt/Kaputt.mp3', text: 'x' }, { code: 'kopierschutz', datei: 'Gemischt/Zu.m4b', text: 'x' }],
    ergebnis: [erg({ pruefen: true, pruefen_gruende: ['tags_fehlen'] })] })] });
  try {
    const k = karteMit(s, 'Gemischt');
    assert.equal(k.dataset.phase, 'pruefen');
    assert.match(kText(k.querySelector('[data-daraus]')), /^Daraus ist geworden: Hörspiel „Bibi Blocksberg“/);
    const rest = k.querySelector('[data-liegt-noch]');
    assert.match(kText(rest), /^Liegt noch im Eingang:/);
    assert.equal(rest.querySelectorAll('[data-gruppe]').length, 2);
    assert.match(kText(rest), /Kaputt\.mp3/);
    assert.match(kText(rest), /Zu\.m4b/);
    assert.doesNotMatch(kText(rest), /In der Datei steht kein Albumname/, 'der Grund des Einsortierten steht oben, nicht beim Rest');
    assert.match(kText(k), /In der Datei steht kein Albumname/);
    assert.equal(k.querySelector('[data-richtig]'), null);
  } finally { weg(); }
});

test('Liste: „Es fehlt noch eine Datei“ (teilweise, gruppe_unvollstaendig): gelbe Karte mit dem Satz, ohne „Das ist richtig“', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig({ name: 'Upload cd34ef56', quelle: 'upload', dateien: 2, status: 'teilweise', pruefen: true, hinweise: [{ code: 'gruppe_unvollstaendig', datei: null, text: 'x' }], ergebnis: [erg({ pruefen: true })] })] });
  try {
    const k = karte(s);
    assert.equal(k.dataset.phase, 'fehlt');
    assert.equal(k.querySelector('[data-marke]').textContent.trim(), 'fehlt noch etwas');
    assert.match(kText(k), /Es fehlt noch eine Datei\. Wähle die fehlende Datei noch einmal\./);
    assert.equal(k.querySelector('[data-richtig]'), null, 'die fehlende Datei bestätigt man nicht weg');
    assert.ok(k.querySelector('[data-ansehen]'));
  } finally { weg(); }
});

test('Liste: mehrere Einträge, neueste zuerst; Eintrag mit mehreren Serien führt „Ansehen“ zur Bibliothek, mit einer zur Serie', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [
    nasFertig({ name: 'Älter', fertig_am: minuten(50), zuerst_gesehen: minuten(55) }),
    nasFertig({ name: 'Neuer', fertig_am: minuten(2), zuerst_gesehen: minuten(3), pruefen: true, ergebnis: [erg({ pruefen: true }), erg({ serie_id: 's1', serie_name: 'Die drei ???', pruefen: false })] }),
  ] });
  try {
    assert.match(kText(karten(s)[0]), /Neuer/);
    assert.match(kText(karten(s)[1]), /Älter/);
    assert.equal(karten(s)[0].querySelector('[data-ansehen]').getAttribute('href'), '#serie-s2', 'nur eine Serie ist noch zu prüfen');
  } finally { weg(); }
});

test('Ohne die Fähigkeit `eingang` gibt es keine Liste aus dem Eingang und keine Abfrage', { ...MIT_DOM }, async () => {
  const s = await start({ faehigkeiten: ALLE.filter((f) => f !== 'eingang'), eingang: [nasLaeuft()] });
  try {
    assert.equal(karten(s).length, 0);
    assert.equal(s.m.aufrufe('tobibox/eingang/list').length, 0);
  } finally { weg(); }
});

test('Die Seite lädt beim Öffnen `eingang/list` neu (Design 7.3 Punkt 5) und folgt dem Ereignis `geaendert`', { ...MIT_DOM }, async () => {
  const s = await start({ hash: '#bibliothek' });
  try {
    const n0 = s.m.aufrufe('tobibox/eingang/list').length;
    s.m.backend.eingang = [nasLaeuft()];
    await geheZu(s, '#hinzufuegen');
    await bis(() => karten(s).length === 1);
    assert.ok(s.m.aufrufe('tobibox/eingang/list').length > n0, 'beim Öffnen neu geholt');
    s.m.backend.eingang = [nasLaeuft(), nasLaeuft({ name: 'Zweiter' })];
    s.m.emit('eingang', 'geaendert', {});
    await bis(() => karten(s).length === 2);
  } finally { weg(); }
});

/* ---- eine Liste, keine Doppelungen */

/* Der Eingang meldet den Eintrag des laufenden Uploads (Gruppen-Ordner), solange `zustand` es sagt. */
function eingangMeldet(s, wie) {
  s.m.on('tobibox/eingang/list', () => {
    const x = s.m.xhrs[0];
    const gruppe = x ? feld(x, 'gruppe') : null;
    const l = wie.zustand === 'leer' || !gruppe ? [] : [eingangEintrag({
      name: `Upload ${gruppe.slice(0, 8)}`, art: 'ordner', dateien: 3, quelle: 'upload', wunsch: { ziel: 'neu', art: 'hoerbuch' },
      ...(wie.zustand === 'laeuft' ? { status: 'laeuft', fertig_am: null, zuerst_gesehen: minuten(0) } : { ergebnis: [erg({ serie_id: 'neu1', serie_name: 'Kapitän Knopf' })], fertig_am: minuten(0) }),
    })];
    return { eintraege: l, gesamt: l.length, sortierung_laeuft: false, geprueft_am: new Date().toISOString() };
  });
}

test('Keine Doppelung: der eigene Upload und sein Eintrag im Eingang sind eine Zeile, beim Einsortieren und danach; das Band zählt ihn einmal', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    s.m.backend.serien.neu1 = { ...buch };
    const wie = { zustand: 'leer' };
    eingangMeldet(s, wie);
    await bisSortiert(s);
    assert.equal(karten(s).length, 1);
    assert.equal(s.el.store.s.lokaleUploads, 1, 'die Seite meldet einen laufenden Upload');
    wie.zustand = 'laeuft';
    s.m.emit('eingang', 'geaendert', {});
    await bis(() => s.el.ctx.eingang().laeuft.length === 1);
    await s.flush(8);
    assert.equal(karten(s).length, 1, 'der Eintrag aus dem Eingang ist derselbe wie der Upload');
    assert.equal(karten(s)[0].dataset.phase, 'sortieren');
    await geheZu(s, '#bibliothek');
    assert.equal(bandText(s), '1 Eintrag wird gerade hinzugefügt.', 'nicht 2');
    assert.equal(s.qa('[data-punkt="eingang"]').length, 1);
    await geheZu(s, '#hinzufuegen');
    wie.zustand = 'fertig';
    s.m.emit('eingang', 'geaendert', {});
    await bis(() => karte(s)?.dataset.phase === 'fertig');
    await s.flush(8);
    assert.equal(karten(s).length, 1);
    assert.equal(karte(s).querySelector('[data-quelle]'), null, 'der eigene Auftrag zeigt keine Quelle');
    assert.equal(s.el.store.s.lokaleUploads, 0);
  } finally { weg(); }
});

test('Band und Punkt zählen den eigenen Upload schon beim Hochladen, bevor der Eingang ihn kennt (und verschwinden, wenn alles einsortiert ist)', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    s.m.backend.serien.neu1 = { ...buch };
    eingangMeldet(s, { zustand: 'leer' });
    await hochladen(s, HAFEN(), 'neu', async () => { tippe(s.q('#hz-name'), 'Kapitän Knopf'); });
    await bis(() => s.m.xhrs[0]);
    assert.equal(s.el.store.s.lokaleUploads, 1);
    await geheZu(s, '#bibliothek');
    assert.equal(bandText(s), '1 Eintrag wird gerade hinzugefügt.');
    assert.ok(s.q('nav.tabs a[href="#bibliothek"] .dot'), 'ruhiger Punkt am Reiter');
    await geheZu(s, '#hinzufuegen');
    await klick(s, s.q('[data-abbrechen]'));
    assert.equal(s.el.store.s.lokaleUploads, 0, 'abgebrochen: zählt nicht mehr');
    await geheZu(s, '#bibliothek');
    assert.ok(!/gerade hinzugefügt/.test(bandText(s) ?? ''));
  } finally { weg(); }
});

test('Nach dem Upload holt die Seite `eingang/list` neu und das Band in der Bibliothek zeigt „bitte kurz ansehen“ (ohne Ereignis)', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    s.m.backend.serien.neu1 = { ...buch, pruefen: true };
    eingangAntwort(s, ({ ordner }) => [eingangEintrag({ name: ordner, art: 'ordner', dateien: 3, quelle: 'upload', pruefen: true, fertig_am: minuten(0), ergebnis: [erg({ serie_id: 'neu1', serie_name: 'Kapitän Knopf', pruefen: true, pruefen_gruende: ['tags_fehlen'] })] })]);
    await bisSortiert(s);
    await bis(() => karte(s)?.dataset.phase === 'pruefen');
    await bis(() => s.el.ctx.eingang().pruefen.length === 1);
    await geheZu(s, '#bibliothek');
    assert.equal(bandText(s), '1 neuer Eintrag bitte kurz ansehen.');
    await geheZu(s, '#hinzufuegen');
    assert.equal(karten(s).length, 1, 'eine Karte, nicht zwei');
    await klick(s, karte(s).querySelector('[data-richtig]'));
    await s.flush(10);
    assert.equal(s.el.ctx.eingang().pruefen.length, 0, 'der Auftrag meldet „Das ist richtig“ auch dem Band');
  } finally { weg(); }
});

/* ---- Neuladen: Wiederaufnahme */

/* „Neuladen der Seite“: ein neues Element gegen dasselbe Backend; der Speicher im Seitenobjekt geht verloren, `localStorage` bleibt. */
async function neuLaden(s, ziel = '#hinzufuegen') {
  s.el.remove();
  const el = new dh.App();
  el.xhrFactory = s.m.xhrFactory;
  document.body.appendChild(el);
  dh.FakeRO.melde(390);
  window.history.replaceState(null, '', `/tobibox${ziel}`);
  el.hass = s.m.hass;
  const flush = async (n = 10) => { for (let i = 0; i < n; i += 1) { await warte(0); await el.updateComplete; } };
  await flush();
  const t = { el, m: s.m, q: (sel) => el.shadowRoot.querySelector(sel), qa: (sel) => [...el.shadowRoot.querySelectorAll(sel)], flush };
  t.mo = H.modell(el.ctx);
  t.mo.lader.drosselMs = 0; t.mo.lader.wiederholenMs = 5; t.mo.abfrageMs = [15, 15];
  await flush(10);
  return t;
}

test('Neuladen mitten im Hochladen: die Seite zeigt „Unterbrochen. Wähle die Datei noch einmal.“ für die Dateien, die nicht angekommen sind; die angekommene bleibt angekommen', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, HAFEN(), 'neu', async () => { tippe(s.q('#hz-name'), 'Kapitän Knopf'); await klick(s, s.q('[data-art-wahl="hoerbuch"]')); });
    await bis(() => s.m.xhrs[0]);
    const gruppe = feld(s.m.xhrs[0], 'gruppe');
    await fertig(s, 0); // Datei 1 ist da, Datei 2 ist unterwegs
    await bis(() => s.m.xhrs[1]);
    const t = await neuLaden(s);
    assert.equal(karten(t).length, 1);
    const k = karte(t);
    assert.equal(k.dataset.phase, 'fehlt');
    assert.match(kText(k), /Es fehlt noch eine Datei\. 1 von 3 Dateien sind angekommen\./);
    assert.deepEqual([...k.querySelectorAll('[data-dateifehler]')].map((x) => x.textContent), ['Unterbrochen. Wähle die Datei noch einmal.', 'Unterbrochen. Wähle die Datei noch einmal.']);
    assert.match(kText(k), /3 Dateien: 01 Der Hafen\.mp3, 02 Die Karte\.mp3 …/);
    assert.equal(t.el.store.s.lokaleUploads, 0, 'nichts läuft, das Band zählt nichts');
    // die Datei noch einmal wählen: dieselbe Gruppe und dieselbe Zahl, damit der Eingang sie zusammen einsortiert
    await klick(t, k.querySelector('[data-fehlende]'));
    await waehle(t, [datei('02 Die Karte.mp3')], 'fehlende');
    const x = await bis(() => t.m.xhrs.find((y) => feld(y, 'gruppe') === gruppe && y !== s.m.xhrs[0]));
    assert.equal(feld(x, 'gruppe_anzahl'), '3');
    assert.equal(feld(x, 'ziel'), 'neu');
    assert.equal(feld(x, 'name'), 'Kapitän Knopf');
    assert.equal(feld(x, 'art'), 'hoerbuch');
    assert.equal(karten(t).length, 1, 'der fortgesetzte Auftrag bleibt eine sichtbare Zeile');
    assert.equal(t.el.store.s.lokaleUploads, 1, 'und zählt wieder im Band');
  } finally { weg(); }
});

test('Neuladen: ein Upload, der schon ganz angekommen war, erscheint nur noch als Eintrag aus dem Eingang (nichts Unterbrochenes, nichts doppelt)', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    eingangAntwort(s, () => []);
    await bisSortiert(s);
    const gruppe = feld(s.m.xhrs[0], 'gruppe');
    assert.equal(karte(s).dataset.phase, 'sortieren');
    s.m.on('tobibox/eingang/list', () => ({ eintraege: [eingangEintrag({ name: `Upload ${gruppe.slice(0, 8)}`, art: 'ordner', dateien: 3, quelle: 'upload', status: 'laeuft', fertig_am: null, zuerst_gesehen: minuten(0) })], gesamt: 1, sortierung_laeuft: true, geprueft_am: new Date().toISOString() }));
    const t = await neuLaden(s);
    assert.equal(karten(t).length, 1);
    assert.equal(karte(t).dataset.phase, 'sortieren');
    assert.equal(karte(t).querySelector('[data-quelle]').textContent.trim(), 'vom Handy');
    assert.equal(karte(t).querySelector('[data-dateifehler]'), null);
  } finally { weg(); }
});

test('Neuladen: ist der Eingang mit der unvollständigen Gruppe schon fertig (nach 30 Minuten), steht nur der Eintrag da, nicht auch noch „Unterbrochen“', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, HAFEN(), 'neu', async () => { tippe(s.q('#hz-name'), 'Kapitän Knopf'); });
    await bis(() => s.m.xhrs[0]);
    const gruppe = feld(s.m.xhrs[0], 'gruppe');
    await fertig(s, 0);
    await bis(() => s.m.xhrs[1]);
    s.m.on('tobibox/eingang/list', () => ({ eintraege: [eingangEintrag({ name: `Upload ${gruppe.slice(0, 8)}`, art: 'ordner', dateien: 1, quelle: 'upload', status: 'teilweise', pruefen: true, hinweise: [{ code: 'gruppe_unvollstaendig', datei: null, text: 'x' }], ergebnis: [erg({ pruefen: true })] })], gesamt: 1, sortierung_laeuft: false, geprueft_am: new Date().toISOString() }));
    const t = await neuLaden(s);
    assert.equal(karten(t).length, 1);
    assert.equal(karte(t).querySelector('[data-quelle]')?.textContent.trim(), 'vom Handy');
    assert.equal(karte(t).querySelector('[data-dateifehler]'), null);
  } finally { weg(); }
});

test('Ein abgebrochener oder fertiger Upload wird nach dem Neuladen nicht „unterbrochen“ (es wird nur gemerkt, was mitten im Hochladen steht)', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    await hochladen(s, [datei('Lied.mp3')], 'einzeln');
    await bis(() => s.m.xhrs[0]);
    await klick(s, s.q('[data-abbrechen]'));
    await s.flush(6);
    assert.equal(window.localStorage.getItem('tobibox.hinzufuegen.offen'), null);
    const t = await neuLaden(s);
    assert.equal(karten(t).length, 0);
  } finally { weg(); }
});

test('Ohne Speicher (localStorage wirft) läuft die Seite weiter, nur ohne Merken', { ...MIT_DOM }, async () => {
  const P = window.Storage.prototype;
  const { getItem, setItem, removeItem } = P;
  P.getItem = () => { throw new Error('gesperrt'); }; P.setItem = () => { throw new Error('gesperrt'); }; P.removeItem = () => { throw new Error('gesperrt'); };
  try {
    const s = await start({ eingangErledigt: [nasFertig()] });
    assert.equal(karten(s).length, 1);
    await hochladen(s, [datei('Lied.mp3')], 'einzeln');
    await fertig(s, 0);
    await klick(s, s.q('[data-erledigte-aus]'));
    assert.equal(s.mo.erledigteAus, true, 'gilt, solange die Seite offen ist');
  } finally { Object.assign(P, { getItem, setItem, removeItem }); weg(); }
});

/* ---- „Erledigte ausblenden“ */

test('„Erledigte ausblenden“ blendet fertige Einträge aus und sagt ehrlich, dass das nur dieses Gerät betrifft; es bleibt nach dem Neuladen', { ...MIT_DOM }, async () => {
  const s = await start({ eingang: [nasLaeuft()], eingangErledigt: [nasFertig(), nasFertig({ name: 'Zweiter', fertig_am: minuten(9), zuerst_gesehen: minuten(10) }), nasFertig({ name: 'Dritter', pruefen: true, fertig_am: minuten(11), ergebnis: [erg({ pruefen: true })] })] });
  try {
    assert.equal(karten(s).length, 4);
    const knopfAus = s.q('[data-erledigte-aus]');
    assert.equal(knopfAus.textContent.trim(), 'Erledigte ausblenden');
    assert.equal(knopfAus.getAttribute('aria-pressed'), 'false');
    assert.equal(s.q('[data-erledigte-hinweis]').textContent.trim(), 'Das gilt nur auf diesem Gerät.');
    await klick(s, knopfAus);
    assert.equal(karten(s).length, 2, 'es bleiben „wird einsortiert“ und „bitte ansehen“');
    assert.ok(karteMit(s, 'Neuer-Ordner') && karteMit(s, 'Dritter'));
    assert.equal(s.q('[data-erledigte-aus]').textContent.trim(), 'Erledigte zeigen');
    assert.equal(s.q('[data-erledigte-aus]').getAttribute('aria-pressed'), 'true');
    assert.equal(s.q('[data-erledigte-hinweis]').textContent.trim(), '2 erledigte Einträge sind ausgeblendet. Das gilt nur auf diesem Gerät.');
    assert.equal(window.localStorage.getItem('tobibox.hinzufuegen.erledigte_aus'), '1');
    assert.equal(s.m.aufrufe('tobibox/einstellungen/set').length, 0, 'nichts geht an den Server');
    const t = await neuLaden(s);
    assert.equal(karten(t).length, 2, 'das Gerät merkt es');
    await klick(t, t.q('[data-erledigte-aus]'));
    assert.equal(karten(t).length, 4);
    assert.equal(window.localStorage.getItem('tobibox.hinzufuegen.erledigte_aus'), null);
  } finally { weg(); }
});

test('„Erledigte ausblenden“ gibt es nur, wenn es etwas Erledigtes gibt; sind alle ausgeblendet, bleibt der Schalter zum Zurückholen', { ...MIT_DOM }, async () => {
  const s = await start({ eingang: [nasLaeuft()] });
  try {
    assert.equal(s.q('[data-erledigte-aus]'), null);
  } finally { weg(); }
  const t = await start({ eingangErledigt: [nasFertig()] });
  try {
    await klick(t, t.q('[data-erledigte-aus]'));
    assert.equal(karten(t).length, 0);
    assert.equal(t.q('[data-liste="zuletzt"]'), null);
    assert.equal(t.q('[data-erledigte-hinweis]').textContent.trim(), '1 erledigter Eintrag ist ausgeblendet. Das gilt nur auf diesem Gerät.');
    await klick(t, t.q('[data-erledigte-aus]'));
    assert.equal(karten(t).length, 1);
  } finally { weg(); }
});

test('Eigene fertige Aufträge gehören zu den Erledigten', { ...MIT_DOM }, async () => {
  const s = await start();
  try {
    s.m.backend.serien.neu1 = { ...buch };
    eingangAntwort(s, ({ ordner }) => [erledigt({ name: ordner, fertig_am: minuten(0), ergebnis: [{ serie_id: 'neu1', serie_name: 'Kapitän Knopf', serie_neu: true, folge: 'Kapitän Knopf', tracks: 3, pruefen: false, pruefen_gruende: [] }] })]);
    await bisSortiert(s);
    await bis(() => karte(s)?.dataset.phase === 'fertig');
    await klick(s, s.q('[data-erledigte-aus]'));
    assert.equal(karten(s).length, 0);
  } finally { weg(); }
});

test('Jetzt prüfen: die Seite „Hinzufügen“ sendet `eingang/sortieren` nicht (Design 5.6: „Sonst nichts“; der Knopf gehört nach Technik)', { ...MIT_DOM }, async () => {
  const s = await start({ eingang: [nasLaeuft()] });
  try {
    assert.ok(!/Jetzt prüfen/.test(s.q('main').textContent));
    assert.equal(s.m.aufrufe('tobibox/eingang/sortieren').length, 0);
  } finally { weg(); }
});

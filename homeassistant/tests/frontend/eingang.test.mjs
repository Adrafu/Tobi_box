/* Tests der Eingang-Anbindung (Paket A11b, Teil 1; Design 5.2 Punkt 2a, 5.3, 6, 7.3 Punkt 3 bis 6 und 10; Vertrag W Nr. 28 und 29, 3.9, 4.5).
 * Aufruf: node --test homeassistant/tests/frontend
 *
 * Geprüft: die Sätze für jeden Grund aus beiden Tabellen des Designs und der Rückfall für unbekannte Codes; die Ableitung „läuft / bitte kurz
 * ansehen / geht nicht / fertig“ aus `eingang/list` (24 Stunden, Doppelte, „Das ist richtig“ wirkt nur auf die Serie); das Band in der Bibliothek in
 * allen Zuständen; der ruhige Punkt am Reiter „Bibliothek“; Ereignisse des Themas `eingang`; die gelbe Karte auf der Serienseite mit „Daraus ist
 * geworden“, „Das ist richtig“ und „Das stimmt nicht“; Band und Karte nach einem Neuladen der Seite (der Zustand kommt aus `eingang/list`).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { seite, geheZu, weg, warte, MIT_DOM, FakeRO } from './dom-helfer.mjs';
import * as dh from './dom-helfer.mjs';
import { eingangEintrag } from './mock-hass.mjs';

const E = await import('../../custom_components/tobibox/frontend/eingang.js');
const { EINGANG, GRUENDE, HINWEISE, SERIE, fuellen } = await import('../../custom_components/tobibox/frontend/texte.js');

const HIER = fileURLToPath(new URL('.', import.meta.url));
const design = readFileSync(join(HIER, '../../../docs/designs/ha-oberflaeche.md'), 'utf8');

const JETZT = Date.parse('2026-11-13T12:00:00Z');
const vor = (min, ref = JETZT) => new Date(ref - min * 60000).toISOString();
const ergebnis = (teil = {}) => ({ serie_id: 's2', serie_name: 'Bibi Blocksberg', serie_neu: true, folge: 'b-01.mp3', anzeige: 'Hexen gibt es doch', tracks: 1, pruefen: false, pruefen_gruende: [], ...teil });

/* ------------------------------------------------------------------ Gründe-Texte (7.3 Punkt 6, beide Tabellen) */

/* Abschnitt 7.3 Punkt 6 des Designs: Tabelle „bitte kurz ansehen“ (Code → Text) und Absatz „geht nicht“. */
function designGruende() {
  const abs = design.slice(design.indexOf('### 7.3 '), design.indexOf('### 7.4 '));
  const tab = abs.slice(abs.indexOf('| Code | Text für Eltern |'), abs.indexOf('**Gründe „geht nicht“**'));
  const ansehen = [];
  for (const zeile of tab.split('\n')) {
    const m = zeile.match(/^\s*\|\s*((?:`[a-z_]+`(?:,\s*)?)+)(?:\s*\([^)]*\))?\s*\|\s*„(.*)“\s*\|\s*$/);
    if (m) for (const c of m[1].matchAll(/`([a-z_]+)`/g)) ansehen.push([c[1], m[2]]);
  }
  const rest = abs.slice(abs.indexOf('**Gründe „geht nicht“**'), abs.indexOf('7. **Zwei Uploads'));
  const geht = [];
  for (const m of rest.matchAll(/((?:`[a-z_]+`(?:,\s*)?)+):\s*„([^“]*)“/g)) for (const c of m[1].matchAll(/`([a-z_]+)`/g)) geht.push([c[1], m[2]]);
  return { ansehen, geht };
}

test('Gründe „bitte kurz ansehen“: jeder Code der Tabelle in 7.3 Punkt 6 gibt genau den Satz des Designs', () => {
  const { ansehen } = designGruende();
  assert.ok(ansehen.length >= 14, `gefunden: ${ansehen.length}`);
  for (const [code, text] of ansehen) {
    assert.equal(E.grundSatz(code), text, code);
    assert.ok(Object.hasOwn(GRUENDE, code), `${code} steht in GRUENDE`);
  }
});

test('Gründe „geht nicht“: jeder Code des Absatzes in 7.3 Punkt 6 gibt genau den Satz des Designs', () => {
  const { geht } = designGruende();
  assert.deepEqual(geht.map(([c]) => c).sort(), ['doppelt', 'ffprobe_fehlt', 'keine_audiodateien', 'kopierschutz', 'nicht_lesbar', 'probedekodierung_fehlgeschlagen', 'verschieben_fehlgeschlagen']);
  for (const [code, text] of geht) {
    assert.equal(E.grundSatz(code), text, code);
    assert.ok(Object.hasOwn(HINWEISE, code), `${code} steht in HINWEISE`);
  }
});

test('Gründe: unbekannter Code (und Prototyp-Namen wie constructor) bekommen den Rückfallsatz, nie den Code', () => {
  for (const c of ['gibt_es_nicht', 'constructor', '', undefined]) assert.equal(E.grundSatz(c), EINGANG.grund_sonst, String(c));
  assert.doesNotMatch(E.grundSatz('gibt_es_nicht'), /gibt_es_nicht/);
  assert.deepEqual(E.gruendeSaetze(['gibt_es_nicht']), [EINGANG.grund_sonst]);
  assert.deepEqual(E.gruendeSaetze([]), [EINGANG.grund_sonst]);
  assert.deepEqual(E.gruendeSaetze(['tags_fehlen', 'gibt_es_nicht', 'tags_fehlen', 'track_doppelt', 'track_teils_leer']), [GRUENDE.tags_fehlen, GRUENDE.track_doppelt], 'unbekannte fallen weg, gleiche Sätze nur einmal');
});

test('Gründe: „Es fehlt noch eine Datei“ nennt keine erfundenen Zahlen; mit Zahlen den Satz aus 6.1', () => {
  assert.doesNotMatch(E.grundSatz('gruppe_unvollstaendig'), /\d von \d/);
  assert.equal(E.grundSatz('gruppe_unvollstaendig'), EINGANG.gruppe_ohne_zahl);
  assert.match(E.grundSatz('gruppe_unvollstaendig', { angekommen: 2, anzahl: 3 }), /^Es fehlt noch eine Datei\. 2 von 3 Dateien sind angekommen\./);
});

test('eintragGruende: Hinweise und Gründe der einsortierten Teile, ohne Doppelte; ohne Codes leer', () => {
  const e = eingangEintrag({ hinweise: [{ code: 'doppelt', datei: 'a.mp3', text: 'x' }], ergebnis: [ergebnis({ pruefen: true, pruefen_gruende: ['tags_fehlen'] }), ergebnis({ pruefen: true, pruefen_gruende: ['tags_fehlen'] })] });
  assert.deepEqual(E.eintragGruende(e), [HINWEISE.doppelt, GRUENDE.tags_fehlen]);
  assert.deepEqual(E.eintragGruende(eingangEintrag()), []);
  assert.deepEqual(E.eintragGruende(eingangEintrag({ hinweise: [{ code: 'neu_und_unbekannt', datei: null, text: 'x' }] })), [EINGANG.grund_sonst]);
});

test('Alle Sätze des Eingangs lassen sich ohne offene Platzhalter lesen', () => {
  const texte = [];
  const sammle = (o) => { if (typeof o === 'string') texte.push(o); else if (o && typeof o === 'object') Object.values(o).forEach(sammle); };
  sammle(EINGANG);
  for (const t of texte) {
    assert.ok(t.trim().length > 0);
    assert.doesNotMatch(fuellen(t, { anzahl: 2, name: 'X', art: 'Hörspiel', einheit: '2 Folgen', text: 'T' }), /\{[a-z_]+\}/, t);
    assert.doesNotMatch(t, /\bUID\b|Revision|Listen-ID/i);
  }
});

/* ------------------------------------------------------------------ Ableitung */

test('eintragZustand: wartet, bereit, laeuft = läuft; blockiert = geht nicht; teilweise = ansehen; erledigt mit pruefen = ansehen', () => {
  for (const st of ['wartet', 'bereit', 'laeuft']) assert.equal(E.eintragZustand({ status: st }), 'laeuft', st);
  assert.equal(E.eintragZustand({ status: 'blockiert' }), 'fehler');
  assert.equal(E.eintragZustand({ status: 'teilweise' }), 'pruefen');
  assert.equal(E.eintragZustand({ status: 'erledigt', pruefen: true }), 'pruefen');
  assert.equal(E.eintragZustand({ status: 'erledigt', pruefen: false }), 'fertig');
  assert.equal(E.eintragZustand({ status: 'erledigt' }), 'fertig');
  assert.equal(E.eintragZustand(null), 'fertig');
});

test('eingangAbleiten: nur die letzten 24 Stunden, neueste zuerst, Doppelte (gleiche id) nur einmal, kaputte Zeit fällt weg', () => {
  const a = eingangEintrag({ id: 'a', status: 'laeuft', fertig_am: null, zuerst_gesehen: vor(5) });
  const b = eingangEintrag({ id: 'b', fertig_am: vor(30) });
  const alt = eingangEintrag({ id: 'alt', fertig_am: vor(24 * 60 + 1) });
  const grenze = eingangEintrag({ id: 'grenze', fertig_am: vor(24 * 60) });
  const doppelt = eingangEintrag({ id: 'b', fertig_am: vor(1) });
  const kaputt = eingangEintrag({ id: 'kaputt', fertig_am: 'kaputt', zuerst_gesehen: null, geaendert_am: null });
  const abl = E.eingangAbleiten([b, alt, a, grenze, doppelt, kaputt, null], { jetzt: JETZT });
  assert.deepEqual(abl.liste.map((x) => x.eintrag.id), ['a', 'b', 'grenze']);
  assert.deepEqual(abl.laeuft.map((x) => x.eintrag.id), ['a']);
  assert.deepEqual(abl.fertig.map((x) => x.eintrag.id), ['b', 'grenze']);
  assert.deepEqual(E.eingangAbleiten(null, { jetzt: JETZT }).liste, []);
});

test('eingangAbleiten: „Das ist richtig“ wirkt nur auf die Serie, darum zählt der Eintrag nur mit einer Serie, die noch geprüft werden muss', () => {
  const e = eingangEintrag({ id: 'x', fertig_am: vor(10), pruefen: true, ergebnis: [ergebnis({ pruefen: true, pruefen_gruende: ['tags_fehlen'] })] });
  assert.equal(E.eingangAbleiten([e], { jetzt: JETZT }).pruefen.length, 1, 'ohne Auskunft über die Serien gilt `pruefen` des Eintrags');
  assert.equal(E.eingangAbleiten([e], { jetzt: JETZT, offeneSerien: new Set(['s2']) }).pruefen.length, 1);
  const bestaetigt = E.eingangAbleiten([e], { jetzt: JETZT, offeneSerien: new Set(['s9']) });
  assert.equal(bestaetigt.pruefen.length, 0);
  assert.equal(bestaetigt.fertig.length, 1);
  const teil = eingangEintrag({ id: 'y', status: 'teilweise', fertig_am: vor(10), pruefen: false });
  assert.equal(E.eingangAbleiten([teil], { jetzt: JETZT, offeneSerien: new Set() }).pruefen.length, 1, '„teilweise“ bleibt, bis der Rest geklärt ist');
});

test('bandZustand: Vorrang läuft, bitte kurz ansehen, geht nicht, „Alles hinzugefügt.“; ohne Einträge kein Band', () => {
  const abl = (liste) => E.eingangAbleiten(liste, { jetzt: JETZT });
  const lauf = (id) => eingangEintrag({ id, status: 'laeuft', fertig_am: null, zuerst_gesehen: vor(1) });
  const pruef = (id) => eingangEintrag({ id, fertig_am: vor(20), pruefen: true, ergebnis: [ergebnis({ pruefen: true })] });
  const kaputt = (id) => eingangEintrag({ id, status: 'blockiert', fertig_am: null, zuerst_gesehen: vor(20), hinweise: [{ code: 'kopierschutz', datei: 'a.m4b', text: 'x' }] });
  const fertig = (id, min = 5) => eingangEintrag({ id, fertig_am: vor(min) });
  assert.equal(E.bandZustand(abl([]), { jetzt: JETZT }), null);
  assert.equal(E.bandZustand(null, { jetzt: JETZT }), null);
  assert.deepEqual(E.bandZustand(abl([lauf('a')]), { jetzt: JETZT }), { art: 'laeuft', anzahl: 1, text: '1 Eintrag wird gerade hinzugefügt.' });
  assert.equal(E.bandZustand(abl([lauf('a'), lauf('b')]), { jetzt: JETZT }).text, '2 Einträge werden gerade hinzugefügt.');
  assert.equal(E.bandZustand(abl([pruef('a')]), { jetzt: JETZT }).text, '1 neuer Eintrag bitte kurz ansehen.');
  assert.equal(E.bandZustand(abl([pruef('a'), pruef('b')]), { jetzt: JETZT }).text, '2 neue Einträge bitte kurz ansehen.');
  assert.equal(E.bandZustand(abl([kaputt('a')]), { jetzt: JETZT }).art, 'fehler');
  assert.equal(E.bandZustand(abl([kaputt('a'), kaputt('b')]), { jetzt: JETZT }).text, '2 Einträge gehen nicht.');
  assert.deepEqual(E.bandZustand(abl([fertig('a')]), { jetzt: JETZT }), { art: 'fertig', anzahl: 1, text: 'Alles hinzugefügt.' });
  assert.equal(E.bandZustand(abl([fertig('a', 16)]), { jetzt: JETZT }), null, 'nach 15 Minuten verschwindet es');
  assert.equal(E.bandZustand(abl([lauf('a'), pruef('b'), kaputt('c')]), { jetzt: JETZT }).art, 'laeuft', 'Laufendes zuerst');
  assert.equal(E.bandZustand(abl([pruef('b'), kaputt('c'), fertig('d')]), { jetzt: JETZT }).art, 'pruefen');
  assert.equal(E.bandZustand(abl([kaputt('c'), fertig('d')]), { jetzt: JETZT }).art, 'fehler');
  assert.deepEqual(E.bandZustand(abl([]), { jetzt: JETZT, lokal: 2 }), { art: 'laeuft', anzahl: 2, text: '2 Einträge werden gerade hinzugefügt.' }, 'Uploads dieser Seite zählen mit');
  assert.equal(E.bandZustand(abl([lauf('a')]), { jetzt: JETZT, lokal: 1 }).anzahl, 2);
});

test('eintragFuerSerie: der neueste Eintrag, aus dem etwas in die Serie kam', () => {
  const a = eingangEintrag({ id: 'a', fertig_am: vor(50), ergebnis: [ergebnis({ serie_id: 's2' })] });
  const b = eingangEintrag({ id: 'b', fertig_am: vor(10), ergebnis: [ergebnis({ serie_id: 's2' }), ergebnis({ serie_id: 's3' })] });
  const abl = E.eingangAbleiten([a, b], { jetzt: JETZT });
  assert.equal(E.eintragFuerSerie(abl, 's2').id, 'b');
  assert.equal(E.eintragFuerSerie(abl, 's3').id, 'b');
  assert.equal(E.eintragFuerSerie(abl, 's9'), null);
  assert.equal(E.eintragFuerSerie(null, 's2'), null);
});

test('naechsteAenderung: wann fällt etwas heraus (24 Stunden, „Alles hinzugefügt.“); ohne Einträge nichts', () => {
  assert.equal(E.naechsteAenderung([], { jetzt: JETZT }), null);
  assert.equal(E.naechsteAenderung(null, { jetzt: JETZT }), null);
  assert.equal(E.naechsteAenderung([eingangEintrag({ fertig_am: vor(5) })], { jetzt: JETZT }), 10 * 60000, 'in 10 Minuten läuft „Alles hinzugefügt.“ ab');
  assert.equal(E.naechsteAenderung([eingangEintrag({ fertig_am: vor(20) })], { jetzt: JETZT }), 24 * 3600000 - 20 * 60000);
  assert.equal(E.naechsteAenderung([eingangEintrag({ fertig_am: vor(24 * 60 + 5) })], { jetzt: JETZT }), null, 'schon draußen');
  assert.ok(E.naechsteAenderung([eingangEintrag({ fertig_am: vor(14.99999) })], { jetzt: JETZT }) >= 1000, 'nie unter einer Sekunde');
});

/* ------------------------------------------------------------------ „Daraus ist geworden: …“ */

test('daraus: neu angelegt (Hörbuch mit Kapiteln, Hörspiel mit Folgen, Album), dazugekommen, einzeln; so wie in 7.3 Punkt 4 (Schritt 3a)', () => {
  const buch = eingangEintrag({ wunsch: { ziel: 'neu', art: 'hoerbuch' }, ergebnis: [ergebnis({ serie_name: 'Kapitän Knopf', tracks: 3 })] });
  assert.equal(E.daraus(buch), 'Daraus ist geworden: Hörbuch „Kapitän Knopf“ · 3 Kapitel');
  const spiel = eingangEintrag({ wunsch: { ziel: 'neu', art: 'hoerspiel' }, ergebnis: Array.from({ length: 8 }, (_, i) => ergebnis({ serie_name: 'Die Wolkenreise', folge: `f${i}.mp3` })) });
  assert.equal(E.daraus(spiel), 'Daraus ist geworden: Hörspiel „Die Wolkenreise“ · 8 Folgen');
  const album = eingangEintrag({ wunsch: { ziel: 'neu', art: 'musik' }, ergebnis: Array.from({ length: 4 }, (_, i) => ergebnis({ serie_name: 'Sommerlieder', folge: `l${i}.mp3` })) });
  assert.equal(E.daraus(album), 'Daraus ist geworden: Album „Sommerlieder“ · 4 Lieder');
  const dazu = eingangEintrag({ wunsch: { ziel: 'ergaenzen', art: 'hoerspiel' }, ergebnis: [1, 2, 3].map((i) => ergebnis({ serie_name: 'Lange Serie', serie_neu: false, folge: `f${i}.mp3` })) });
  assert.equal(E.daraus(dazu), 'Daraus ist geworden: „Lange Serie“ · 3 neue Folgen');
  assert.equal(E.daraus(eingangEintrag({ ergebnis: [ergebnis({ serie_name: 'Lange Serie', serie_neu: false })] })), 'Daraus ist geworden: „Lange Serie“ · 1 neue Folge');
  const lied = eingangEintrag({ wunsch: { ziel: 'einzeln', art: 'musik' }, ergebnis: [ergebnis({ serie_name: 'Der Mond und der Fuchs' })] });
  assert.equal(E.daraus(lied), 'Daraus ist geworden: „Der Mond und der Fuchs“ · einzelnes Lied');
});

test('daraus: NAS-Eintrag ohne Wunsch nimmt die Art der Serie; ohne Art „Neuer Eintrag“; mehrere Serien mit „und 2 weitere“; ohne Ergebnis leer', () => {
  const nas = eingangEintrag({ quelle: 'nas', wunsch: null, ergebnis: [ergebnis({ serie_name: 'Wolken', tracks: 2 }), ergebnis({ serie_name: 'Wolken', folge: 'b.mp3' })] });
  assert.equal(E.daraus(nas), 'Daraus ist geworden: Neuer Eintrag „Wolken“ · 2 Folgen');
  assert.equal(E.daraus(nas, { serien: { s2: { art: 'geschichte', einzeln: false } } }), 'Daraus ist geworden: Geschichten „Wolken“ · 2 Geschichten');
  assert.equal(E.daraus(nas, { serien: (id) => (id === 's2' ? { art: 'musik', einzeln: true } : null) }), 'Daraus ist geworden: „Wolken“ · einzelnes Lied');
  const viele = eingangEintrag({ ergebnis: ['s1', 's2', 's3', 's4', 's5'].map((id) => ergebnis({ serie_id: id, serie_name: `Serie ${id}` })) });
  assert.match(E.daraus(viele), /^Daraus ist geworden: .*Serie s1.*; .*Serie s3.* und 2 weitere$/);
  assert.equal(E.daraus(viele, { serieId: 's4' }), 'Daraus ist geworden: Neuer Eintrag „Serie s4“ · 1 Folge');
  assert.equal(E.daraus(eingangEintrag({ ergebnis: [] })), '');
  assert.equal(E.daraus(null), '');
});

/* ------------------------------------------------------------------ Seite: Band, Punkt, Karte */

const hash = () => window.location.hash;
const klick = async (s, el) => { assert.ok(el, 'Element zum Klicken fehlt'); el.click(); await warte(20); await s.flush(10); };
const band = (s) => s.q('[data-eingang-band]');
const punktLib = (s) => s.q('nav.tabs a[href="#bibliothek"] .dot');
const bandText = (s) => band(s)?.textContent.replace(/\s+/g, ' ').trim();
const toasts = (s) => s.qa('.toast .tmsg').map((x) => x.textContent);

const laeuft = (teil = {}) => eingangEintrag({ status: 'laeuft', fertig_am: null, zuerst_gesehen: new Date().toISOString(), ...teil });
const ansehen = (teil = {}) => eingangEintrag({ pruefen: true, wunsch: { ziel: 'neu', art: 'hoerspiel' }, ergebnis: [ergebnis({ pruefen: true, pruefen_gruende: ['tags_fehlen'] })], ...teil });

async function bibliothek(opts = {}) {
  const s = await seite({ hash: '', ...opts });
  await geheZu(s, '#bibliothek');
  await s.flush(10);
  return s;
}

/* „Neuladen der Seite“: ein neues Element gegen dasselbe Backend; das alte verschwindet. Der Speicher der alten Seite geht verloren. */
async function neuLaden(s, ziel) {
  s.el.remove();
  const el = new dh.App();
  document.body.appendChild(el);
  FakeRO.melde(390);
  window.history.replaceState(null, '', `/tobibox${ziel}`);
  el.hass = s.m.hass;
  const flush = async (n = 10) => { for (let i = 0; i < n; i += 1) { await warte(0); await el.updateComplete; } };
  await flush();
  return { el, m: s.m, q: (sel) => el.shadowRoot.querySelector(sel), qa: (sel) => [...el.shadowRoot.querySelectorAll(sel)], flush };
}

test('Band: ohne Einträge im Eingang gibt es kein Band und keinen Punkt (der Grundbestand ist älter als 24 Stunden)', MIT_DOM, async () => {
  const s = await bibliothek();
  assert.equal(band(s), null);
  assert.equal(punktLib(s), null);
  assert.equal(s.m.letzter('tobibox/eingang/list').filter, 'alle');
  weg();
});

test('Band: „2 Einträge werden gerade hinzugefügt.“ über der Liste, role=status, Link auf #hinzufuegen, tonal (ohne orange und rot)', MIT_DOM, async () => {
  const s = await bibliothek({ eingang: [laeuft(), laeuft({ status: 'wartet' })] });
  const b = band(s);
  assert.equal(b.dataset.eingangBand, 'laeuft');
  assert.equal(b.getAttribute('role'), 'status');
  assert.equal(bandText(s), '2 Einträge werden gerade hinzugefügt.');
  assert.equal(b.querySelector('a').getAttribute('href'), '#hinzufuegen');
  assert.ok(b.classList.contains('eband') && !b.classList.contains('pruefen') && !b.classList.contains('fehler'));
  const lage = (a, c) => a.compareDocumentPosition(c) & window.Node.DOCUMENT_POSITION_FOLLOWING;
  assert.ok(lage(b, s.q('.artrow')), 'das Band steht über der Arten-Zeile');
  assert.ok(lage(b, s.q('[data-liste="bibliothek"]')), '… und über der Liste');
  weg();
});

test('Band: Tipp auf das Band führt zur Seite „Hinzufügen“ (nur verlinkt, die Seite baut A11a)', MIT_DOM, async () => {
  const s = await bibliothek({ eingang: [laeuft()] });
  await klick(s, band(s).querySelector('a'));
  assert.equal(hash(), '#hinzufuegen');
  assert.equal(s.el._route.name, 'hinzufuegen');
  weg();
});

test('Band: alle Zustände aus eingang/list (läuft eins, bitte ansehen eins und mehr, geht nicht, fertig)', MIT_DOM, async () => {
  const fall = [
    ['laeuft', [laeuft()], '1 Eintrag wird gerade hinzugefügt.'],
    ['pruefen', [ansehen()], '1 neuer Eintrag bitte kurz ansehen.'],
    ['pruefen', [ansehen(), ansehen()], '2 neue Einträge bitte kurz ansehen.'],
    ['fehler', [eingangEintrag({ status: 'blockiert', fertig_am: null, hinweise: [{ code: 'kopierschutz', datei: 'a.m4b', text: 'x' }] })], '1 Eintrag geht nicht.'],
    ['fertig', [eingangEintrag({ fertig_am: new Date(Date.now() - 2 * 60000).toISOString() })], 'Alles hinzugefügt.'],
  ];
  for (const [art, liste, text] of fall) {
    const s = await bibliothek(art === 'laeuft' || art === 'fehler' ? { eingang: liste } : { eingangErledigt: liste });
    assert.equal(band(s)?.dataset.eingangBand, art, text);
    assert.equal(bandText(s), text);
    assert.equal(band(s).classList.contains('pruefen'), art === 'pruefen', 'orange nur bei „bitte kurz ansehen“');
    weg();
  }
});

test('Band: „Alles hinzugefügt.“ fehlt, wenn der Eintrag schon lange fertig ist; Einträge über 24 Stunden zählen nicht', MIT_DOM, async () => {
  const s = await bibliothek({ eingangErledigt: [eingangEintrag({ fertig_am: new Date(Date.now() - 3 * 3600000).toISOString() }), ansehen({ fertig_am: new Date(Date.now() - 25 * 3600000).toISOString() })] });
  assert.equal(band(s), null);
  weg();
});

test('Band: das Band steht nur in der Bibliothek, nicht auf dem Start', MIT_DOM, async () => {
  const s = await bibliothek({ eingang: [laeuft()] });
  assert.ok(band(s));
  await geheZu(s, '#start');
  assert.equal(band(s), null);
  await geheZu(s, '#bibliothek');
  assert.ok(band(s));
  weg();
});

test('Punkt am Reiter „Bibliothek“: ruhig, ohne Zahl, nur solange etwas läuft; Satz für Screenreader; der Punkt an „Geräte“ bleibt davon getrennt', MIT_DOM, async () => {
  const s = await bibliothek({ eingang: [laeuft(), laeuft()] });
  const p = punktLib(s);
  assert.ok(p, 'Punkt da');
  assert.ok(p.classList.contains('ruhig'));
  assert.equal(p.textContent.trim(), '', 'ohne Zahl');
  assert.equal(p.getAttribute('aria-hidden'), 'true');
  assert.equal(s.q('nav.tabs a[href="#bibliothek"] .sr').textContent, EINGANG.punkt);
  assert.ok(punktLib(s) && !s.q('nav.tabs a[href="#start"] .dot') && !s.q('nav.tabs a[href="#tobies"] .dot'));
  assert.equal(s.q('nav.tabs a[href="#geraete"] .dot').textContent, '1', 'der rote Punkt mit Zahl gehört den neuen Tobies');
  await geheZu(s, '#geraete');
  assert.ok(punktLib(s), 'der Punkt steht auf jedem Reiter');
  weg();
});

test('Punkt am Reiter: bei „bitte kurz ansehen“, „geht nicht“ und „fertig“ steht kein Punkt (nur ein laufender Upload)', MIT_DOM, async () => {
  for (const opts of [{ eingangErledigt: [ansehen()] }, { eingang: [eingangEintrag({ status: 'blockiert', fertig_am: null })] }, { eingangErledigt: [eingangEintrag()] }]) {
    const s = await bibliothek(opts);
    assert.ok(band(s), 'Band da');
    assert.equal(punktLib(s), null);
    weg();
  }
});

test('Uploads dieser Seite (A11a meldet sie über ctx.lokaleUploads) zählen im Band und am Punkt mit', MIT_DOM, async () => {
  const s = await bibliothek();
  assert.equal(band(s), null);
  s.el.ctx.lokaleUploads(2);
  await s.flush(6);
  assert.equal(bandText(s), '2 Einträge werden gerade hinzugefügt.');
  assert.ok(punktLib(s));
  s.el.ctx.lokaleUploads(0);
  await s.flush(6);
  assert.equal(band(s), null);
  assert.equal(punktLib(s), null);
  weg();
});

test('Ereignisse des Themas eingang: „geaendert“ lädt die Liste neu; Band und Punkt folgen (läuft → bitte kurz ansehen → weg)', MIT_DOM, async () => {
  const s = await bibliothek();
  const abo = s.m.calls.find((c) => c.abo);
  assert.ok(abo.msg.themen.includes('eingang'));
  const zahl = () => s.m.aufrufe('tobibox/eingang/list').length;
  const n0 = zahl();
  s.m.backend.eingang = [laeuft({ id: 'aaaaaaaaaaaa' })];
  s.m.emit('eingang', 'geaendert', {});
  await warte(20); await s.flush(8);
  assert.equal(zahl(), n0 + 1);
  assert.equal(bandText(s), '1 Eintrag wird gerade hinzugefügt.');
  assert.ok(punktLib(s));
  // fertig einsortiert: der Eintrag wechselt vom Eingang ins Protokoll, mit „bitte kurz ansehen“
  s.m.backend.eingang = [];
  s.m.backend.eingangErledigt = [ansehen({ id: 'aaaaaaaaaaaa' })];
  s.m.emit('eingang', 'neu_einsortiert', { eintrag_id: 'aaaaaaaaaaaa', eintrag_name: 'x', ergebnis: [], hinweise: [], zaehler: {} });
  await warte(20); await s.flush(8);
  assert.equal(bandText(s), '1 neuer Eintrag bitte kurz ansehen.');
  assert.ok(band(s).classList.contains('pruefen'));
  assert.equal(punktLib(s), null);
  s.m.backend.eingangErledigt = [];
  s.m.emit('eingang', 'durchlauf_fertig', { geprueft_am: 'x', zaehler: {} });
  await warte(20); await s.flush(8);
  assert.equal(band(s), null);
  const n1 = zahl();
  s.m.emit('eingang', 'snapshot', { offen: 0, blockiert: 0, sortierung_laeuft: false, geprueft_am: null });
  await warte(20); await s.flush(4);
  assert.equal(zahl(), n1, 'der Snapshot bringt nur Zahlen, die Liste wird nicht neu geholt');
  weg();
});

test('Eingang: `eingang/list` meldet einen Fehler (noch nie geprüft): die Seite startet trotzdem, ohne Band', MIT_DOM, async () => {
  const s = await seite({ hash: '#bibliothek' });
  s.m.failNext('tobibox/eingang/list', 'medien_nicht_erreichbar');
  s.m.emit('eingang', 'geaendert', {});
  await warte(20); await s.flush(6);
  assert.equal(s.el.store.s.phase, 'bereit');
  assert.equal(band(s), null);
  weg();
});

test('Eingang: ohne die Fähigkeit `eingang` fragt die Seite nichts und abonniert nichts', MIT_DOM, async () => {
  const s = await seite({ hash: '#bibliothek', faehigkeiten: ['medien', 'upload', 'zuordnung', 'neue_tobies', 'boxen', 'bibliothek'] });
  assert.equal(s.m.aufrufe('tobibox/eingang/list').length, 0);
  assert.ok(!s.m.calls.find((c) => c.abo).msg.themen.includes('eingang'));
  assert.equal(band(s), null);
  weg();
});

/* ---- Serienseite: gelbe Karte „Bitte kurz ansehen“ */

const bibi = (teil = {}) => ansehen({ name: 'Bibi-Ordner', quelle: 'nas', wunsch: null, ergebnis: [ergebnis({ pruefen: true, pruefen_gruende: ['tags_fehlen'] })], ...teil });
const serieSeite = async (id = 's2', opts = {}) => {
  const s = await seite({ hash: '', ...opts });
  await geheZu(s, `#serie-${id}`);
  await s.flush(10);
  return s;
};

test('Serienseite: gelbe Karte mit Grund, „Daraus ist geworden: …“ aus dem Eintrag, „Das ist richtig“ und „Das stimmt nicht“', MIT_DOM, async () => {
  const s = await serieSeite('s2', { eingangErledigt: [bibi()] });
  const karte = s.q('[data-karte="ansehen"]');
  assert.ok(karte.classList.contains('warn'));
  assert.equal(karte.querySelector('strong').textContent, 'Bitte kurz ansehen.');
  assert.equal(karte.querySelector('.se-grund').textContent, GRUENDE.tags_fehlen);
  assert.equal(karte.querySelector('[data-daraus]').textContent, 'Daraus ist geworden: Hörspiel „Bibi Blocksberg“ · 1 Folge');
  assert.deepEqual([...karte.querySelectorAll('button')].map((b) => b.textContent.trim()), ['Das ist richtig', 'Das stimmt nicht']);
  weg();
});

test('Serienseite: ohne Eintrag in den letzten 24 Stunden steht die Karte ohne „Daraus ist geworden“', MIT_DOM, async () => {
  const s = await serieSeite('s2', { eingangErledigt: [bibi({ fertig_am: new Date(Date.now() - 30 * 3600000).toISOString() })] });
  assert.ok(s.q('[data-karte="ansehen"]'));
  assert.equal(s.q('[data-daraus]'), null);
  weg();
});

test('Serienseite: „Das ist richtig“ sendet einsortierung/bestaetigen, die Karte verschwindet, und das Band in der Bibliothek ist weg (der Eintrag bleibt „pruefen“ im Protokoll)', MIT_DOM, async () => {
  const s = await serieSeite('s2', { eingangErledigt: [bibi()] });
  await geheZu(s, '#bibliothek');
  assert.equal(bandText(s), '1 neuer Eintrag bitte kurz ansehen.');
  await geheZu(s, '#serie-s2');
  await klick(s, s.q('[data-richtig]'));
  assert.deepEqual(s.m.aufrufe('tobibox/einsortierung/bestaetigen').map(({ id, type, ...r }) => r), [{ serie_id: 's2' }]);
  assert.equal(s.q('[data-karte="ansehen"]'), null);
  assert.deepEqual(toasts(s), ['Danke, ist erledigt.']);
  assert.equal(s.m.backend.eingangErledigt[0].pruefen, true, 'das Backend löscht das Kennzeichen am Eintrag nicht');
  await s.flush(10);
  await geheZu(s, '#bibliothek');
  assert.equal(band(s)?.dataset.eingangBand, 'fertig', 'bestätigt heißt: nichts mehr anzusehen, kurz „Alles hinzugefügt.“');
  assert.ok(!band(s).classList.contains('pruefen'));
  weg();
});

test('Serienseite: „Das stimmt nicht“ bietet Name, Art und abgesetzt Papierkorb; „Anders einsortieren …“ gibt es noch nicht (A-3)', MIT_DOM, async () => {
  const s = await serieSeite('s2', { eingangErledigt: [bibi()], nichtAdmin: true });
  await klick(s, s.q('[data-stimmt-nicht]'));
  const punkte = s.qa('dialog.blatt[open] [data-menue]').map((x) => x.dataset.menue);
  assert.deepEqual(punkte, ['art', 'name', 'papierkorb']);
  assert.ok(!s.q('dialog.blatt[open]').textContent.includes('Anders einsortieren'));
  assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), SERIE.stimmt_nicht.titel);
  // der Weg „In den Papierkorb …“ geht über die vorhandene Rückfrage
  await klick(s, s.q('dialog.blatt[open] [data-menue="papierkorb"]'));
  assert.match(s.q('dialog.blatt[open]').textContent, /Papierkorb/);
  weg();
});

test('Serienseite: Umbenennen löscht das Kennzeichen der Serie; das Band holt sich den Stand neu', MIT_DOM, async () => {
  const s = await serieSeite('s2', { eingangErledigt: [bibi()], nichtAdmin: true });
  s.m.backend.serien.s2.folgen.forEach((f) => { f.pruefen = false; }); // „Name ändern“ löscht die Kennzeichen der Serie und der Folge
  s.m.backend.serien.s2.pruefen = false;
  const n = s.m.aufrufe('tobibox/eingang/list').length;
  s.el._seiteObj.laden(true);
  await warte(20); await s.flush(10);
  assert.equal(s.q('[data-karte="ansehen"]'), null);
  assert.equal(s.m.aufrufe('tobibox/eingang/list').length, n + 1);
  weg();
});

/* ---- Neuladen der Seite: der Zustand kommt aus eingang/list, nicht aus dem Speicher der Seite */

test('Wiederaufnahme: Band, Punkt und gelbe Karte stimmen nach einem Neuladen der Seite wieder', MIT_DOM, async () => {
  const s = await bibliothek({ eingang: [laeuft(), laeuft()], eingangErledigt: [bibi()] });
  assert.equal(bandText(s), '2 Einträge werden gerade hinzugefügt.');
  assert.ok(punktLib(s));
  const vorher = { text: bandText(s), art: band(s).dataset.eingangBand };
  const s2 = await neuLaden(s, '#bibliothek');
  assert.notEqual(s2.el, s.el);
  assert.deepEqual({ text: s2.q('[data-eingang-band]').textContent.replace(/\s+/g, ' ').trim(), art: s2.q('[data-eingang-band]').dataset.eingangBand }, vorher);
  assert.ok(s2.q('nav.tabs a[href="#bibliothek"] .dot.ruhig'));
  // der Upload ist inzwischen fertig; beim Neuladen steht „bitte kurz ansehen“ da
  s.m.backend.eingang = [];
  const s3 = await neuLaden(s2, '#bibliothek');
  assert.equal(s3.q('[data-eingang-band]').dataset.eingangBand, 'pruefen');
  assert.equal(s3.q('nav.tabs a[href="#bibliothek"] .dot'), null);
  // und die Karte auf der Serienseite
  const s4 = await neuLaden(s3, '#serie-s2');
  assert.ok(s4.q('[data-karte="ansehen"]'));
  assert.equal(s4.q('[data-daraus]').textContent, 'Daraus ist geworden: Hörspiel „Bibi Blocksberg“ · 1 Folge');
  // „Das ist richtig“ ist auf dem Server gemerkt: nach einem weiteren Neuladen gibt es keine Karte und kein „bitte kurz ansehen“ mehr
  s4.q('[data-richtig]').click();
  await warte(20); await s4.flush(10);
  const s5 = await neuLaden(s4, '#bibliothek');
  assert.notEqual(s5.q('[data-eingang-band]')?.dataset.eingangBand, 'pruefen');
  const s6 = await neuLaden(s5, '#serie-s2');
  assert.equal(s6.q('[data-karte="ansehen"]'), null);
  s6.el.remove();
  weg();
});

test('Zeitgeber: „Alles hinzugefügt.“ verschwindet von selbst, wenn die 15 Minuten um sind', MIT_DOM, async () => {
  const s = await bibliothek({ eingangErledigt: [eingangEintrag({ fertig_am: new Date(Date.now() - 14 * 60000 - 59500).toISOString() })] });
  assert.equal(bandText(s), 'Alles hinzugefügt.');
  assert.ok(s.el.store._eingangTimer, 'ein Zeitgeber ist geplant');
  weg();
});

/* ------------------------------------------------------------------ betroffene Dateien (Befund aus dem echten HA) */

test('hinweisGruppen: nur Dateinamen, je Grund eine Gruppe, höchstens drei Namen und „und N weitere“, bei gleichem Namen der Ordner davor', () => {
  const h = (code, datei) => ({ code, datei, text: 'x' });
  const g = E.hinweisGruppen([
    h('probedekodierung_fehlgeschlagen', 'Die Haferhorde - Volle Mähne!/26. Kapitel 24_ Volle Mähne.mp3.mp3'),
    h('probedekodierung_fehlgeschlagen', 'Felix - Briefe von Felix/Briefe von Felix.mp3'),
    h('nicht_lesbar', 'Anderer/Briefe von Felix.mp3'),
    h('probedekodierung_fehlgeschlagen', 'A/vier.mp3'),
    h('probedekodierung_fehlgeschlagen', 'A/fuenf.mp3'),
    h('kopierschutz', 'x/y/Buch.m4b'),
    h('gruppe_unvollstaendig', null),
  ]);
  assert.equal(g.length, 2, 'probedekodierung und nicht_lesbar haben denselben Satz; gruppe_unvollstaendig fehlt');
  assert.equal(g[0].satz, HINWEISE.probedekodierung_fehlgeschlagen);
  assert.deepEqual(g[0].namen, ['26. Kapitel 24_ Volle Mähne.mp3.mp3', 'Felix - Briefe von Felix/Briefe von Felix.mp3', 'Anderer/Briefe von Felix.mp3']);
  assert.equal(g[0].weitere, 2);
  assert.deepEqual(g[1].namen, ['Buch.m4b']);
  assert.equal(g[1].weitere, 0);
  assert.deepEqual(E.hinweisGruppen([{ code: 'neu_unbekannt', datei: 'a\\b\\c.mp3' }]), [{ satz: EINGANG.grund_sonst, namen: ['c.mp3'], weitere: 0 }]);
  assert.deepEqual(E.hinweisGruppen([]), []);
});

test('ergebnisGruende: nur die Gründe der einsortierten Teile; bei „teilweise“ bleibt das Band „bitte kurz ansehen“', () => {
  const e = eingangEintrag({ id: 't', status: 'teilweise', fertig_am: vor(5), ergebnis: [ergebnis({ pruefen: true, pruefen_gruende: ['tags_fehlen'] })], hinweise: [{ code: 'kopierschutz', datei: 'a.m4b', text: 'x' }] });
  assert.deepEqual(E.ergebnisGruende(e), [GRUENDE.tags_fehlen]);
  const abl = E.eingangAbleiten([e], { jetzt: JETZT });
  assert.equal(E.bandZustand(abl, { jetzt: JETZT }).art, 'pruefen');
});

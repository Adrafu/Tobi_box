/* Tests der Seite (AP 3.2). Aufruf: node --test homeassistant/tests/frontend
 *
 * Die Logik (TobiboxStore) läuft ohne DOM gegen den Mock (mock-hass.mjs).
 * Die Darstellungstests brauchen jsdom und werden übersprungen, wenn es fehlt
 * (jsdom aus npm oder aus dem Ordner in TOBIBOX_JSDOM_DIR, der ein node_modules enthält).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createMockHass, SCHEMA, pruefeEingabe } from './mock-hass.mjs';

const HIER = fileURLToPath(new URL('.', import.meta.url));
const FRONTEND = join(HIER, '../../custom_components/tobibox/frontend');
const panel = await import('../../custom_components/tobibox/frontend/tobibox-panel.js');
const { TobiboxStore, FEHLERTEXTE, fehlerText } = panel;

const mocks = [];

/* Store mit Mock; `antworten` steuert die Rückfragen und merkt sie in `dialoge`. */
async function neu(opts = {}, antworten = {}) {
  const mock = createMockHass(opts);
  mocks.push(mock);
  const store = new TobiboxStore({ xhrFactory: mock.xhrFactory });
  const dialoge = [];
  const wert = (k, o, standard) => { dialoge.push({ k, ...o }); const a = antworten[k]; return typeof a === 'function' ? a(o) : (a === undefined ? standard : a); };
  store.ui = {
    confirm: async (o) => wert('confirm', o, true),
    prompt: async (o) => wert('prompt', o, null),
    waehleSerie: async (o) => wert('serie', o, null),
    waehleZiel: async (o) => wert('ziel', o, null),
  };
  await store.attach(mock.hass);
  await mock.tick();
  return { mock, store, dialoge, s: store.s };
}
const lade = async (store, id = 's1') => { store.s.view = 'serie'; store.s.serieId = id; await store.ladeSerie(id); };

/* ------------------------------------------------------------------ Modul */

test('Das Modul lädt, auch ohne DOM, und trägt die feste Lit-Version im Kopf', () => {
  assert.equal(typeof TobiboxStore, 'function');
  assert.equal(panel.VERTRAG_V, 1);
  assert.equal(panel.UPLOAD_URL, '/api/tobibox/upload');
  const lit = readFileSync(join(FRONTEND, 'lit-all.min.js'), 'utf8');
  assert.match(lit.split('\n').slice(0, 6).join('\n'), /lit@3\.\d+\.\d+/);
  assert.doesNotMatch(lit, /from\s*["']https?:/, 'Lit darf nichts aus dem Netz laden');
  const pj = readFileSync(join(FRONTEND, 'tobibox-panel.js'), 'utf8');
  assert.doesNotMatch(pj, /unsafeHTML|innerHTML|https?:\/\/(?!www\.w3)/, 'kein HTML aus Namen, keine Netz-Adressen');
});

// Vertrag W, Änderung 12.11.: Texte kommen mit der neuen Seite (Design ha-oberflaeche, Paket A5)
const NEU_FUER_NEUE_SEITE = [
  'zu_viele_aenderungen',
  'cover_ungueltig',
  'cover_nicht_gefunden',
  'wunsch_ungueltig',
  'neu_einsortieren_nicht_moeglich',
  'hoerkopie_warteschlange_voll',
  'zu_viele_streams',
  'hoerkopie_wartet',
  'warteschlange_voll', // 13.11. (A0-Q): Texte kommen mit der neuen Seite, die alte Seite kennt die Warteschlange nicht
  'warteschlange_doppelt',
];

test('Alle Fehlercodes des Vertrags (Abschnitt 7) haben einen deutschen Text', () => {
  const doc = readFileSync(join(HIER, '../../../docs/protocol/ha-websocket-v1.md'), 'utf8');
  const tabelle = doc.slice(doc.indexOf('## 7. Gemeinsame Fehlercodes'), doc.indexOf('## 8. Grenzen'));
  const codes = [...tabelle.matchAll(/^\| `([a-z_]+)` \|/gm)].map((m) => m[1]);
  assert.ok(codes.length >= 30, `gefunden: ${codes.length}`);
  for (const c of NEU_FUER_NEUE_SEITE) assert.ok(codes.includes(c), `${c} steht nicht mehr in Abschnitt 7 – Liste NEU_FUER_NEUE_SEITE aktualisieren`);
  for (const c of codes) {
    if (NEU_FUER_NEUE_SEITE.includes(c)) continue;
    assert.ok(FEHLERTEXTE[c], `Text für ${c} fehlt`);
  }
  assert.equal(fehlerText('neuer_code_x', 'Klartext vom Backend'), 'Klartext vom Backend');
  assert.equal(fehlerText('neuer_code_x'), FEHLERTEXTE.unknown_error);
});

test('Der Mock ist streng: unbekannte Felder, fehlende Pflichtfelder, bestaetigt', () => {
  assert.throws(() => pruefeEingabe({ type: 'tobibox/hello', v: 1, extra: 1 }), (e) => e.code === 'invalid_format');
  assert.throws(() => pruefeEingabe({ type: 'tobibox/serie/get' }), (e) => e.code === 'invalid_format');
  assert.throws(() => pruefeEingabe({ type: 'tobibox/papierkorb/empty', bestaetigt: false }), (e) => e.code === 'invalid_format');
  assert.throws(() => pruefeEingabe({ type: 'tobibox/folgen/order', serie_id: 'a', folgen: [] }), (e) => e.code === 'invalid_format');
});

/* ------------------------------------------------------------------ Start */

test('Start: hello mit v=1, Abo, Listen laden, Prüfung und Einsortieren anstoßen', async () => {
  const { mock, s } = await neu();
  assert.deepEqual(mock.aufrufe('tobibox/hello')[0], { id: mock.aufrufe('tobibox/hello')[0].id, type: 'tobibox/hello', v: 1 });
  assert.equal(mock.calls.filter((c) => c.abo).length, 1);
  assert.equal(mock.calls.find((c) => c.abo).type, 'tobibox/subscribe');
  for (const t of ['serien/list', 'boxen/list', 'neue_tobies/list', 'zuordnung/list', 'eingang/list', 'papierkorb/list', 'medien/pruefen', 'eingang/sortieren']) {
    assert.ok(mock.aufrufe(`tobibox/${t}`).length >= 1, `${t} wurde nicht aufgerufen`);
  }
  assert.equal(s.bereit, true);
  assert.equal(s.darf, true);
  assert.equal(s.serien.length, 3);
  assert.equal(s.konfig.zustand, 'ok');
});

test('Start ohne Schreibrecht: keine schreibenden Aufrufe', async () => {
  const { mock, s } = await neu({ darf: false });
  assert.equal(s.darf, false);
  assert.equal(mock.aufrufe('tobibox/medien/pruefen').length, 0);
  assert.equal(mock.aufrufe('tobibox/eingang/sortieren').length, 0);
  assert.equal(s.serien.length, 3);
});

test('Fähigkeiten: nur was hello zusagt wird geladen', async () => {
  const { mock } = await neu({ faehigkeiten: ['medien', 'zuordnung'] });
  assert.equal(mock.aufrufe('tobibox/eingang/list').length, 0);
  assert.equal(mock.aufrufe('tobibox/papierkorb/list').length, 0);
});

test('Backend kennt hello nicht: Hinweis „Seite neu laden“', async () => {
  const mock = createMockHass();
  mock.on('tobibox/hello', () => { throw { code: 'unknown_command', message: 'x' }; });
  const store = new TobiboxStore();
  await store.attach(mock.hass);
  assert.equal(store.s.reloadNoetig, true);
  assert.equal(mock.aufrufe('tobibox/serien/list').length, 0);
});

test('Backend mit kleinerem v: Hinweis „Seite neu laden“, nichts weiter', async () => {
  const mock = createMockHass();
  mock.on('tobibox/hello', () => ({ v: 0, version: '0', darf_schreiben: true, faehigkeiten: [], boxen: [], konfig: {}, grenzen: {} }));
  const store = new TobiboxStore();
  await store.attach(mock.hass);
  assert.equal(store.s.reloadNoetig, true);
});

/* ------------------------------------------------------------------ Serien und Folgen */

test('serie/create mit anfrage_id; Überraschungs-Serie mit typ', async () => {
  const { mock, store } = await neu({}, { prompt: 'Neue Reihe' });
  await store.serieAnlegen();
  const m = mock.letzter('tobibox/serie/create');
  assert.equal(m.name, 'Neue Reihe');
  assert.match(m.anfrage_id, /^[0-9A-Za-z-]{8,64}$/);
  assert.equal('typ' in m, false);
  await store.serieAnlegen('ueberraschung');
  assert.equal(mock.letzter('tobibox/serie/create').typ, 'ueberraschung');
});

test('serie/rename und folge/rename (mit stand)', async () => {
  const { mock, store, s } = await neu({}, { prompt: 'Neuer Name' });
  await store.serieUmbenennen('s1', 'Die drei ???');
  assert.deepEqual({ ...mock.letzter('tobibox/serie/rename'), id: 0 }, { id: 0, type: 'tobibox/serie/rename', serie_id: 's1', name: 'Neuer Name' });
  await lade(store);
  const standVorher = s.serie.stand;
  await store.folgeUmbenennen('s1', s.serie.folgen[0]);
  const m = mock.letzter('tobibox/folge/rename');
  assert.equal(m.folge, 'folge-01.mp3'); assert.equal(m.name, 'Neuer Name'); assert.equal(m.stand, standVorher);
  assert.equal(s.serie.folgen[0].anzeige, 'Neuer Name');
});

test('Abbruch im Namensfeld sendet nichts', async () => {
  const { mock, store } = await neu();
  assert.equal(await store.serieUmbenennen('s1', 'x'), false);
  assert.equal(mock.aufrufe('tobibox/serie/rename').length, 0);
});

test('folgen/order: Tipp hoch/runter und Ziehen schicken die ganze Liste mit stand', async () => {
  const { mock, store, s } = await neu();
  await lade(store);
  const stand0 = s.serie.stand;
  await store.folgeBewegen('s1', 'folge-03.mp3', -1);
  let m = mock.letzter('tobibox/folgen/order');
  assert.deepEqual(m.folgen, ['folge-01.mp3', 'folge-03.mp3', 'folge-02.mp3']);
  assert.equal(m.stand, stand0); assert.equal(m.serie_id, 's1');
  assert.deepEqual(s.serie.folgen.map((f) => f.name), m.folgen);
  await store.folgeZiehen('s1', 'folge-01.mp3', 'folge-02.mp3');
  m = mock.letzter('tobibox/folgen/order');
  assert.deepEqual(m.folgen, ['folge-03.mp3', 'folge-02.mp3', 'folge-01.mp3']);
  assert.match(m.stand, /^[0-9a-f]{16}$/);
  assert.equal(await store.folgeBewegen('s1', 'folge-03.mp3', -1), false, 'ganz oben: nichts senden');
  assert.equal(mock.aufrufe('tobibox/folgen/order').length, 2);
});

test('folgen/order mit altem stand: stand_veraltet wird angezeigt und die Serie neu geladen', async () => {
  const { mock, store, s } = await neu();
  await lade(store);
  mock.backend.serien.s1.name = 'Von außen geändert'; // ändert den Fingerabdruck
  const vorher = mock.aufrufe('tobibox/serie/get').length;
  assert.equal(await store.folgeBewegen('s1', 'folge-02.mp3', 1), false);
  assert.equal(s.fehler.code, 'stand_veraltet');
  assert.match(s.fehler.text, /neu geladen/);
  assert.ok(mock.aufrufe('tobibox/serie/get').length > vorher);
  assert.equal(s.serie.name, 'Von außen geändert');
});

test('Folge löschen ohne Tobies: Rückfrage, kein tobies_bestaetigt', async () => {
  const { mock, store, dialoge } = await neu();
  await lade(store);
  await store.folgeLoeschen('s1', 'folge-03.mp3');
  assert.equal(dialoge.at(-1).k, 'confirm');
  const m = mock.letzter('tobibox/folge/delete');
  assert.equal(m.folge, 'folge-03.mp3'); assert.ok(m.stand); assert.equal('tobies_bestaetigt' in m, false);
});

test('Folge löschen mit Tobies: Rückfrage nennt Anzahl und Namen, dann tobies_bestaetigt=true', async () => {
  const { mock, store, dialoge, s } = await neu();
  await lade(store);
  await store.folgeLoeschen('s1', 'folge-02.mp3');
  const d = dialoge.at(-1);
  assert.match(d.text, /1 Tobie zeigt/);
  assert.deepEqual(d.liste, ['04FF…BBAA']);
  assert.equal(mock.letzter('tobibox/folge/delete').tobies_bestaetigt, true);
  assert.match(s.hinweis.text, /1 Tobie spielt/);
});

test('Löschen abgelehnt: nichts wird gesendet', async () => {
  const { mock, store } = await neu({}, { confirm: false });
  await store.folgeLoeschen('s1', 'folge-02.mp3');
  await store.serieLoeschen('s1');
  assert.equal(mock.aufrufe('tobibox/folge/delete').length, 0);
  assert.equal(mock.aufrufe('tobibox/serie/delete').length, 0);
});

test('Serie löschen: zählt Serien- und Folgen-Tobies (2), sendet stand und tobies_bestaetigt', async () => {
  const { mock, store, dialoge } = await neu();
  await store.serieLoeschen('s1');
  assert.match(dialoge.at(-1).text, /2 Tobies zeigen/);
  assert.deepEqual(dialoge.at(-1).liste.sort(), ['04FF…BBAA', 'Anna']);
  const m = mock.letzter('tobibox/serie/delete');
  assert.equal(m.serie_id, 's1'); assert.equal(m.tobies_bestaetigt, true); assert.match(m.stand, /^[0-9a-f]{16}$/);
});

test('Serie ohne Tobies löschen: ohne tobies_bestaetigt', async () => {
  const { mock, store } = await neu();
  await store.serieLoeschen('s2');
  assert.equal('tobies_betroffen' in mock.letzter('tobibox/serie/delete'), false);
  assert.equal('tobies_bestaetigt' in mock.letzter('tobibox/serie/delete'), false);
});

test('Folge verschieben: Serie wählen, Rückfrage mit Anzahl und „von vorn“, stand der Quelle', async () => {
  const { mock, store, dialoge, s } = await neu({}, { serie: 's2' });
  await lade(store);
  await store.folgeVerschieben('s1', s.serie.folgen[1]);
  assert.deepEqual(dialoge.find((d) => d.k === 'serie').ausser, ['s1']);
  assert.match(dialoge.at(-1).text, /1 Tobie zeigt.*von vorn/);
  const m = mock.letzter('tobibox/folge/verschieben');
  assert.deepEqual({ serie_id: m.serie_id, folge: m.folge, ziel_serie_id: m.ziel_serie_id, tobies_bestaetigt: m.tobies_bestaetigt }, { serie_id: 's1', folge: 'folge-02.mp3', ziel_serie_id: 's2', tobies_bestaetigt: true });
  assert.match(m.stand, /^[0-9a-f]{16}$/);
});

test('Folge verschieben ohne Tobies: trotzdem Rückfrage, kein tobies_bestaetigt', async () => {
  const { mock, store, dialoge, s } = await neu({}, { serie: 's2' });
  await lade(store);
  await store.folgeVerschieben('s1', s.serie.folgen[0]);
  assert.equal(dialoge.at(-1).k, 'confirm');
  assert.equal('tobies_bestaetigt' in mock.letzter('tobibox/folge/verschieben'), false);
});

test('Serien zusammenführen: beide stand, Anzahl der Tobies in der Rückfrage', async () => {
  const { mock, store, dialoge, s } = await neu({}, { serie: 's2' });
  await store.serienZusammenfuehren('s1');
  assert.equal(dialoge.find((d) => d.k === 'serie').nurNormal, true);
  assert.match(dialoge.at(-1).text, /3 Folgen aus „Die drei \?\?\?“.*2 Tobies zeigen/);
  const m = mock.letzter('tobibox/serien/zusammenfuehren');
  assert.equal(m.quelle_id, 's1'); assert.equal(m.ziel_id, 's2'); assert.equal(m.tobies_bestaetigt, true);
  assert.match(m.stand_quelle, /^[0-9a-f]{16}$/); assert.match(m.stand_ziel, /^[0-9a-f]{16}$/);
  assert.equal(s.serieId, 's2');
});

test('einsortierung/bestaetigen: ganze Serie oder einzelne Folgen', async () => {
  const { mock, store } = await neu();
  await store.einsortierungBestaetigen('s2');
  assert.equal('folgen' in mock.letzter('tobibox/einsortierung/bestaetigen'), false);
  await store.einsortierungBestaetigen('s2', ['b-01.mp3']);
  assert.deepEqual(mock.letzter('tobibox/einsortierung/bestaetigen').folgen, ['b-01.mp3']);
  assert.equal(mock.backend.serien.s2.folgen[0].pruefen, false);
});

/* ------------------------------------------------------------------ Eingang, Papierkorb */

test('Eingang: Filter, Sortieren, sofort', async () => {
  const { mock, store, s } = await neu();
  await store.setEingangFilter('erledigt');
  assert.equal(mock.letzter('tobibox/eingang/list').filter, 'erledigt');
  assert.equal(s.eingang.filter, 'erledigt');
  await store.eingangSortieren();
  assert.deepEqual(Object.keys(mock.letzter('tobibox/eingang/sortieren')).sort(), ['id', 'type']);
  await store.eingangSortieren(true);
  assert.equal(mock.letzter('tobibox/eingang/sortieren').sofort, true);
});

test('Papierkorb: wiederherstellen, leeren mit bestaetigt=true und Anzahl in der Rückfrage', async () => {
  const { mock, store, dialoge, s } = await neu();
  assert.equal(s.papierkorb.gesamt, 1);
  await store.papierkorbLeeren();
  assert.match(dialoge.at(-1).text, /1 Eintrag \(/);
  assert.equal(mock.letzter('tobibox/papierkorb/empty').bestaetigt, true);
  assert.equal(s.papierkorb.gesamt, 0);
  const { mock: m2, store: st2, s: s2 } = await neu();
  await st2.papierkorbWiederherstellen(s2.papierkorb.eintraege[0]);
  assert.equal(m2.letzter('tobibox/papierkorb/restore').eintrag_id, 'aabbccddeeff');
  const { mock: m3, store: st3 } = await neu({}, { confirm: false });
  await st3.papierkorbLeeren();
  assert.equal(m3.aufrufe('tobibox/papierkorb/empty').length, 0);
});

/* ------------------------------------------------------------------ Tobies */

test('Neuer Tobie zuordnen: zuordnung/set mit erwartet_ziel=null und Name', async () => {
  const w = { ziel: { typ: 'folge', serie: 's1', folge: 'folge-01.mp3' }, name: 'Ben', box: null };
  const { mock, store, s } = await neu({}, { ziel: w });
  await store.zuordnen('0499887766554433', null);
  const m = mock.letzter('tobibox/zuordnung/set');
  assert.deepEqual({ uid: m.uid, ziel: m.ziel, name: m.name, erwartet_ziel: m.erwartet_ziel }, { uid: '0499887766554433', ziel: w.ziel, name: 'Ben', erwartet_ziel: null });
  assert.equal('ueberschreiben' in m, false);
  assert.equal(s.neueTobies.gesamt, 0);
  assert.equal(s.zuordnungen.gesamt, 3);
});

test('Zuordnen ohne Namen sendet kein name; Aktionskarte (Status, Gute Nacht)', async () => {
  for (const aktion of ['status', 'gute_nacht']) {
    const { mock, store } = await neu({}, { ziel: { ziel: { typ: 'aktion', aktion }, name: null } });
    await store.zuordnen('0499887766554433', null);
    const m = mock.letzter('tobibox/zuordnung/set');
    assert.equal('name' in m, false);
    assert.deepEqual(m.ziel, { typ: 'aktion', aktion });
  }
});

test('Ziel ändern: erwartet_ziel = bisheriges Ziel und Rückfrage beim Überschreiben', async () => {
  const bisher = { typ: 'serie', serie: 's1' };
  const { mock, store, dialoge } = await neu({}, { ziel: { ziel: { typ: 'serie', serie: 's2' }, name: null } });
  await store.zuordnen('04A1B2C3D4E5F6', bisher, 'Anna');
  assert.equal(dialoge.filter((d) => d.k === 'confirm').length, 1);
  const m = mock.letzter('tobibox/zuordnung/set');
  assert.deepEqual(m.erwartet_ziel, bisher);
  assert.equal(m.name, null, 'leerer Name bei vorhandenem Namen löscht ihn (null)');
});

test('Überschreiben abgelehnt: keine Zuordnung gesendet', async () => {
  const { mock, store } = await neu({}, { ziel: { ziel: { typ: 'serie', serie: 's2' }, name: null }, confirm: false });
  await store.zuordnen('04A1B2C3D4E5F6', { typ: 'serie', serie: 's1' });
  assert.equal(mock.aufrufe('tobibox/zuordnung/set').length, 0);
});

test('Tobie umbenennen (Name) und lösen mit erwartet_ziel; Namen leeren sendet null', async () => {
  const { mock, store, s } = await neu({}, { prompt: 'Lena' });
  const z = s.zuordnungen.liste.find((x) => x.name === 'Anna');
  await store.tobieUmbenennen(z);
  let m = mock.letzter('tobibox/zuordnung/set');
  assert.deepEqual({ uid: m.uid, name: m.name, ziel: m.ziel, erwartet_ziel: m.erwartet_ziel }, { uid: z.uid, name: 'Lena', ziel: z.ziel, erwartet_ziel: z.ziel });
  const { mock: m2, store: st2, s: s2 } = await neu({}, { prompt: '' });
  await st2.tobieUmbenennen(s2.zuordnungen.liste[0]);
  assert.equal(m2.letzter('tobibox/zuordnung/set').name, null);
  const { mock: m3, store: st3, s: s3 } = await neu();
  const z0 = s3.zuordnungen.liste[0];
  await st3.zuordnungLoesen(z0);
  m = m3.letzter('tobibox/zuordnung/remove');
  assert.deepEqual({ uid: m.uid, erwartet_ziel: m.erwartet_ziel }, { uid: z0.uid, erwartet_ziel: z0.ziel });
});

test('zuordnung_geaendert: Fehler sichtbar, Zuordnungen und Neue Tobies werden neu geladen', async () => {
  const { mock, store, s } = await neu({}, { ziel: { ziel: { typ: 'serie', serie: 's1' }, name: null } });
  mock.failNext('tobibox/zuordnung/set', 'zuordnung_geaendert');
  const n = mock.aufrufe('tobibox/zuordnung/list').length;
  await store.zuordnen('0499887766554433', null);
  assert.equal(s.fehler.code, 'zuordnung_geaendert');
  assert.equal(mock.aufrufe('tobibox/zuordnung/list').length, n + 1);
});

test('Neue Tobies verwerfen; Kennung von Hand', async () => {
  const { mock, store, s } = await neu({}, { prompt: '04AABBCCDDEEFF', ziel: { ziel: { typ: 'serie', serie: 's1' }, name: null } });
  await store.neueTobiesVerwerfen('0499887766554433');
  assert.deepEqual(mock.letzter('tobibox/neue_tobies/verwerfen').uid, '0499887766554433');
  assert.equal(s.neueTobies.gesamt, 0);
  await store.kennungVonHand();
  assert.equal(mock.letzter('tobibox/zuordnung/set').uid, '04AABBCCDDEEFF');
});

/* ------------------------------------------------------------------ Lernmodus */

test('Lernmodus: start mit box, ziel, name, anfrage_id; Rückfrage per Ereignis; Antwort; Abbruch', async () => {
  const w = { ziel: { typ: 'serie', serie: 's1' }, name: 'Zoe', box: 'kueche' };
  const { mock, store, s } = await neu({}, { ziel: w });
  await store.lernStart();
  const m = mock.letzter('tobibox/lernmodus/start');
  assert.deepEqual({ box: m.box, ziel: m.ziel, name: m.name }, { box: 'kueche', ziel: w.ziel, name: 'Zoe' });
  assert.match(m.anfrage_id, /^[0-9A-Za-z-]{8,64}$/);
  assert.equal(s.lern.kueche.zustand, 'wartet');
  const id = s.lern.kueche.befehl_id;
  assert.equal(store.offeneRueckfrage(), null);
  mock.emit('lernmodus', 'rueckfrage', { box: 'kueche', befehl_id: id, zustand: 'rueckfrage', ziel: w.ziel, uid: '04A1B2C3D4E5F6', bisher: { typ: 'folge', serie: 's1', folge: 'folge-02.mp3' }, rueckfrage_bis: '2026-11-09T10:01:00Z' });
  assert.equal(store.offeneRueckfrage().uid, '04A1B2C3D4E5F6');
  await store.lernAntwort(id, true);
  assert.deepEqual(Object.keys(mock.letzter('tobibox/lernmodus/antwort')).sort(), ['befehl_id', 'id', 'type', 'ueberschreiben']);
  assert.equal(mock.letzter('tobibox/lernmodus/antwort').ueberschreiben, true);
  assert.equal(store.offeneRueckfrage(), null);
  assert.equal(s.lern.kueche.zustand, 'zugeordnet');
  await store.lernStart();
  await store.lernAbbrechen('kueche');
  assert.deepEqual(mock.letzter('tobibox/lernmodus/abbrechen').box, 'kueche');
  assert.equal(s.lern.kueche.zustand, 'abgebrochen');
});

test('Lernmodus: Antwort „Behalten“ sendet ueberschreiben=false; Aktion ist im Lernmodus nicht wählbar', async () => {
  const { mock, store, s, dialoge } = await neu({}, { ziel: { ziel: { typ: 'folge', serie: 's1', folge: 'folge-01.mp3' }, name: null, box: 'kueche' } });
  await store.lernStart();
  assert.equal(dialoge.at(-1).aktion, false);
  assert.equal(dialoge.at(-1).mitBox, true);
  assert.equal('name' in mock.letzter('tobibox/lernmodus/start'), false);
  await store.lernAntwort(s.lern.kueche.befehl_id, false);
  assert.equal(mock.letzter('tobibox/lernmodus/antwort').ueberschreiben, false);
});

test('Lernmodus: Ereignisse beenden den Vorgang; lernmodus_laeuft wird angezeigt', async () => {
  const w = { ziel: { typ: 'serie', serie: 's1' }, name: null, box: 'kueche' };
  const { mock, store, s } = await neu({}, { ziel: w });
  mock.emit('lernmodus', 'abgelaufen', { box: 'kueche', befehl_id: 'b1', zustand: 'abgelaufen', grund: 'frist', ziel: w.ziel });
  assert.equal(s.lern.kueche.ende, true);
  mock.failNext('tobibox/lernmodus/start', 'lernmodus_laeuft');
  await store.lernStart();
  assert.equal(s.fehler.code, 'lernmodus_laeuft');
});

test('Lernmodus gesperrt, wenn die Konfiguration nicht ok ist (kein Aufruf)', async () => {
  const { mock, store, s } = await neu({}, { ziel: { ziel: { typ: 'serie', serie: 's1' }, name: null, box: 'kueche' } });
  mock.backend.konfig = { ...s.konfig, zustand: 'leer_neu', revision: null, liste_id: null };
  mock.emit('konfig', 'geaendert', { konfig: mock.backend.konfig });
  assert.equal(await store.lernStart(), false);
  assert.equal(mock.aufrufe('tobibox/lernmodus/start').length, 0);
  assert.equal(s.fehler.code, 'konfig_nicht_bereit');
});

/* ------------------------------------------------------------------ Boxen, Liste, Export */

test('Boxen: Status, Sync mit anfrage_id; Sync einer Offline-Box zeigt box_offline', async () => {
  const { mock, store, s } = await neu();
  assert.equal(s.boxen[0].status.speicher_frei_mb, 5120);
  assert.equal(s.boxen[1].konfig_stand, 'veraltet');
  await store.boxSync('kueche');
  const m = mock.letzter('tobibox/box/sync');
  assert.equal(m.box, 'kueche'); assert.match(m.anfrage_id, /^[0-9A-Za-z-]{8,64}$/);
  await store.boxSync('kinderzimmer');
  assert.equal(s.fehler.code, 'box_offline');
});

test('Liste neu ausrollen: bestaetigt=true, anfrage_id; bei leer_neu Warnung vor Verlust', async () => {
  const { mock, store, dialoge, s } = await neu();
  await store.listeNeuAusrollen();
  const m = mock.letzter('tobibox/liste/neu_ausrollen');
  assert.equal(m.bestaetigt, true); assert.match(m.anfrage_id, /^[0-9A-Za-z-]{8,64}$/);
  assert.equal(s.konfig.revision, 1);
  mock.backend.konfig = { ...s.konfig, zustand: 'leer_neu', revision: null, liste_id: null };
  mock.emit('konfig', 'geaendert', { konfig: mock.backend.konfig });
  await store.listeNeuAusrollen();
  assert.match(dialoge.at(-1).text, /verlieren ihre Zuordnung/);
  assert.equal(s.konfig.zustand, 'ok');
});

test('Wiederherstellung: export_lesen, Rückfrage mit Revision, dann aus_export; export_neuer', async () => {
  const { mock, store, dialoge, s } = await neu();
  mock.backend.konfig = { ...s.konfig, zustand: 'export_neuer' };
  mock.emit('konfig', 'geaendert', { konfig: mock.backend.konfig });
  await store.konfigAusExport();
  assert.equal(mock.aufrufe('tobibox/konfig/export_lesen').length, 1);
  assert.match(dialoge.at(-1).text, /Revision 9.*4 Zuordnungen/);
  const m = mock.letzter('tobibox/konfig/aus_export');
  assert.equal(m.bestaetigt, true); assert.match(m.anfrage_id, /^[0-9A-Za-z-]{8,64}$/);
  assert.equal(s.konfig.zustand, 'ok');
  assert.match(s.hinweis.text, /4 Zuordnungen/);
});

test('Wiederherstellung ohne Exportdatei: export_nicht_gefunden, kein aus_export', async () => {
  const { mock, store, s } = await neu();
  mock.backend.exportDatei = { vorhanden: false, liste_id: null, revision: null, exportiert_am: null, anzahl_zuordnungen: null, anzahl_fenster: null, neuer_als_ha: false };
  await store.konfigAusExport();
  assert.equal(s.fehler.code, 'export_nicht_gefunden');
  assert.equal(mock.aufrufe('tobibox/konfig/aus_export').length, 0);
});

test('export_lesen („Export ansehen“) legt exportInfo ab', async () => {
  const { store, s } = await neu();
  await store.exportLesen();
  assert.equal(s.exportInfo.revision, 9);
});

/* ------------------------------------------------------------------ Hochladen */

test('Upload: Felder in Vertragsreihenfolge, Bearer-Token, Fortschritt, Ergebnis', async () => {
  const { mock, store, s } = await neu();
  const datei = new File([new Uint8Array(2048)], 'Folge 4 - Der Rabe.mp3', { type: 'audio/mpeg' });
  const stufen = [];
  store.onChange(() => stufen.push(s.uploads[0]?.zustand));
  await store.hochladen([datei], { serieId: 's1' });
  const x = mock.xhrs[0];
  assert.equal(x.method, 'POST'); assert.equal(x.url, '/api/tobibox/upload');
  assert.equal(x.headers.Authorization, 'Bearer token-123');
  const felder = [...x.body.keys()];
  assert.deepEqual(felder, ['upload_id', 'serie_id', 'datei']);
  assert.match(x.body.get('upload_id'), /^[0-9A-Za-z-]{8,64}$/);
  assert.equal(x.body.get('serie_id'), 's1');
  assert.equal(x.body.get('datei').name, 'Folge 4 - Der Rabe.mp3');
  assert.equal(s.uploads[0].zustand, 'fertig');
  assert.equal(s.uploads[0].gesendet, 2048);
  assert.ok(stufen.includes('sendet'));
  assert.ok(mock.aufrufe('tobibox/eingang/list').length >= 2, 'Eingang wird nach dem Upload neu geladen');
});

test('Upload mehrerer Dateien als eine Folge: gemeinsame gruppe, nacheinander', async () => {
  const { mock, store } = await neu({ xhr: 'manuell' });
  const f = (n) => new File([new Uint8Array(10)], n);
  const p = store.hochladen([f('a.mp3'), f('b.mp3')], { einGruppe: true });
  await mock.tick();
  assert.equal(mock.xhrs.length, 1, 'zweite Datei erst nach der ersten');
  mock.xhrs[0].fortschritt(5, 10);
  assert.equal(store.s.uploads[0].gesendet, 5);
  mock.xhrs[0].antwort(200, mock.xhrs[0].erfolg());
  await mock.tick();
  mock.xhrs[1].antwort(200, mock.xhrs[1].erfolg());
  await p;
  const g = mock.xhrs.map((x) => x.body.get('gruppe'));
  assert.ok(g[0] && g[0] === g[1]); assert.match(g[0], /^[0-9A-Za-z-]{8,64}$/);
  assert.deepEqual([...mock.xhrs[0].body.keys()], ['upload_id', 'gruppe', 'datei']);
});

test('Upload: Fehlercodes aus dem Körper, Warnung, Netzfehler, zu große Datei, erneuertes Token', async () => {
  const { mock, store, s } = await neu({ xhr: 'manuell' });
  const f = (n, g = 10) => new File([new Uint8Array(g)], n);
  let p = store.hochladen([f('x.txt')]);
  await mock.tick();
  mock.xhrs[0].antwort(415, { v: 1, fehler: { code: 'format_nicht_erlaubt', text: 'Dieses Dateiformat spielt die Box nicht.' } });
  await p;
  assert.equal(s.uploads[0].code, 'format_nicht_erlaubt'); assert.equal(s.uploads[0].zustand, 'fehler');
  p = store.hochladen([f('y.mp3')]);
  await mock.tick();
  mock.xhrs[1].antwort(507, 'kein json');
  await p;
  assert.equal(s.uploads[1].code, 'kein_speicher');
  p = store.hochladen([f('z.mp3')]);
  await mock.tick();
  mock.xhrs[2].antwort(200, { ...mock.xhrs[2].erfolg(), pruefung: 'warnung', hinweis: 'kopierschutz' });
  await p;
  assert.equal(s.uploads[2].zustand, 'fertig'); assert.equal(s.uploads[2].pruefung, 'warnung');
  const n = mock.aufrufe('tobibox/eingang/list').length;
  p = store.hochladen([f('w.mp3')]);
  await mock.tick();
  mock.xhrs[3].netzfehler();
  await p;
  assert.equal(s.uploads[3].zustand, 'unklar');
  assert.ok(mock.aufrufe('tobibox/eingang/list').length > n, 'nach Verbindungsfehler im Eingang nachsehen');
  s.grenzen.upload_max_bytes = 5;
  await store.hochladen([f('gross.mp3', 6)]);
  assert.equal(s.uploads[4].code, 'datei_zu_gross');
  assert.equal(mock.xhrs.length, 4, 'zu große Datei wird gar nicht gesendet');
  mock.hass.auth.expired = true;
  s.grenzen.upload_max_bytes = 1000;
  p = store.hochladen([f('t.mp3')]);
  await mock.tick(); await mock.tick();
  assert.equal(mock.xhrs[4].headers.Authorization, 'Bearer token-neu');
  mock.xhrs[4].antwort(200, mock.xhrs[4].erfolg());
  await p;
});

test('Upload-Ereignis (Thema upload) setzt Prüfphase und Fehler je upload_id', async () => {
  const { mock, store, s } = await neu({ xhr: 'manuell' });
  const p = store.hochladen([new File([new Uint8Array(4)], 'a.mp3')]);
  await mock.tick();
  const id = s.uploads[0].id;
  mock.emit('upload', 'fortschritt', { upload_id: 'fremd', zustand: 'fehler', bytes: 1, code: 'datei_zu_gross' });
  assert.equal(s.uploads[0].zustand, 'sendet');
  mock.emit('upload', 'fortschritt', { upload_id: id, zustand: 'pruefe', bytes: 4, code: null });
  assert.equal(s.uploads[0].zustand, 'pruefe');
  mock.xhrs[0].antwort(200, mock.xhrs[0].erfolg());
  await p;
  assert.equal(s.uploads[0].zustand, 'fertig');
});

/* ------------------------------------------------------------------ Fehlerantworten */

const FEHLER_FALLE = [
  ['tobibox/serie/rename', (st) => st.serieUmbenennen('s1', 'x'), 'name_ungueltig', { prompt: 'Neu' }],
  ['tobibox/serie/create', (st) => st.serieAnlegen('ueberraschung'), 'ueberraschung_existiert', { prompt: 'Ü' }],
  ['tobibox/folge/rename', async (st) => { await lade(st); return st.folgeUmbenennen('s1', st.s.serie.folgen[0]); }, 'medien_schreibfehler', { prompt: 'Neu' }],
  ['tobibox/serie/delete', (st) => st.serieLoeschen('s2'), 'medien_nicht_erreichbar', {}],
  ['tobibox/papierkorb/restore', (st) => st.papierkorbWiederherstellen({ id: 'aabbccddeeff' }), 'datei_existiert', {}],
  ['tobibox/papierkorb/empty', (st) => st.papierkorbLeeren(), 'medien_schreibfehler', {}],
  ['tobibox/liste/neu_ausrollen', (st) => st.listeNeuAusrollen(), 'anfrage_id_konflikt', {}],
  ['tobibox/box/sync', (st) => st.boxSync('kueche'), 'mqtt_nicht_verbunden', {}],
  ['tobibox/lernmodus/abbrechen', (st) => st.lernAbbrechen('kueche'), 'box_unbekannt', {}],
  ['tobibox/lernmodus/antwort', (st) => st.lernAntwort('x', true), 'rueckfrage_abgelaufen', {}],
  ['tobibox/zuordnung/remove', (st) => st.zuordnungLoesen(st.s.zuordnungen.liste[0]), 'unauthorized', {}],
  ['tobibox/neue_tobies/verwerfen', (st) => st.neueTobiesVerwerfen('x'), 'kennung_ungueltig', {}],
  ['tobibox/eingang/sortieren', (st) => st.eingangSortieren(), 'eintrag_nicht_gefunden', {}],
  ['tobibox/einsortierung/bestaetigen', (st) => st.einsortierungBestaetigen('s2'), 'serie_nicht_gefunden', {}],
  ['tobibox/zuordnung/set', (st) => st.zuordnen('0499887766554433', null), 'konfig_zu_gross', { ziel: { ziel: { typ: 'serie', serie: 's1' }, name: null } }],
  ['tobibox/zuordnung/set', (st) => st.zuordnen('0499887766554433', null), 'ziel_ungueltig', { ziel: { ziel: { typ: 'serie', serie: 's1' }, name: null } }],
  ['tobibox/konfig/export_lesen', (st) => st.exportLesen(), 'export_ungueltig', {}],
  ['tobibox/medien/pruefen', (st) => st.pruefen(), 'unknown_error', {}],
];

for (const [befehl, tu, code, antw] of FEHLER_FALLE) {
  test(`Fehlerantwort ${code} bei ${befehl.replace('tobibox/', '')} wird mit Text angezeigt`, async () => {
    const { mock, store, s } = await neu({}, antw);
    mock.failNext(befehl, code);
    await tu(store);
    assert.equal(s.fehler?.code, code);
    assert.equal(s.fehler.text, FEHLERTEXTE[code]);
  });
}

test('Unbekannter Code: die message des Backends wird angezeigt; nur der code zählt', async () => {
  const { mock, store, s } = await neu();
  mock.failNext('tobibox/box/sync', { code: 'zukunft_code', message: 'Neuer Fehler aus einer neueren Version' });
  await store.boxSync('kueche');
  assert.equal(s.fehler.text, 'Neuer Fehler aus einer neueren Version');
  mock.failNext('tobibox/box/sync', { code: 'box_offline', message: 'ANDERER TEXT DER IGNORIERT WIRD' });
  await store.boxSync('kueche');
  assert.equal(s.fehler.text, FEHLERTEXTE.box_offline);
});

test('Fehler beim Laden der Listen werden angezeigt', async () => {
  const mock = createMockHass();
  mock.failNext('tobibox/serien/list', 'medien_nicht_erreichbar');
  const store = new TobiboxStore();
  await store.attach(mock.hass);
  assert.equal(store.s.fehler.code, 'medien_nicht_erreichbar');
});

test('tobies_betroffen trotz Rückfrage (Wettlauf): neu lesen und noch einmal fragen', async () => {
  const { mock, store, dialoge } = await neu();
  await lade(store);
  mock.failNext('tobibox/folge/delete', 'tobies_betroffen');
  await store.folgeLoeschen('s1', 'folge-03.mp3');
  assert.equal(dialoge.filter((d) => d.k === 'confirm').length, 2);
  assert.equal(mock.aufrufe('tobibox/folge/delete').length, 2);
});

test('konfig_nicht_bereit: Konfiguration wird neu gelesen (hello)', async () => {
  const { mock, store, s } = await neu({}, { ziel: { ziel: { typ: 'serie', serie: 's1' }, name: null } });
  mock.failNext('tobibox/zuordnung/set', 'konfig_nicht_bereit');
  const n = mock.aufrufe('tobibox/hello').length;
  await store.zuordnen('0499887766554433', null);
  assert.equal(s.fehler.code, 'konfig_nicht_bereit');
  assert.equal(mock.aufrufe('tobibox/hello').length, n + 1);
});

/* ------------------------------------------------------------------ Abos aktualisieren die Ansicht */

test('Snapshots nach dem Abonnieren laden die Listen (Boxen, Neue Tobies)', async () => {
  const { mock } = await neu();
  assert.ok(mock.aufrufe('tobibox/boxen/list').length >= 2);
});

test('Ereignis boxen: geaendert ersetzt die Box und behält die Meldungen; ereignis hängt vorn an', async () => {
  const { mock, store, s } = await neu();
  const k = s.boxen.find((x) => x.box === 'kueche');
  mock.emit('boxen', 'geaendert', { ...k, ereignisse: undefined, online: false, konfig_stand: 'voraus' });
  const neuK = s.boxen.find((x) => x.box === 'kueche');
  assert.equal(neuK.online, false); assert.equal(neuK.konfig_stand, 'voraus'); assert.equal(neuK.ereignisse.length, 1);
  mock.emit('boxen', 'ereignis', { box: 'kueche', ereignis: { id: 'e2', ts: 't', art: 'fehler', daten: {}, text: 'Neu' } });
  assert.equal(s.boxen.find((x) => x.box === 'kueche').ereignisse[0].text, 'Neu');
  assert.equal(store.s.boxen.length, 2);
});

test('Ereignis neue_tobies: neu, aktualisiert, entfernt', async () => {
  const { mock, s } = await neu();
  const e = (uid, anzahl) => ({ uid, zuerst: 'a', zuletzt: 'b', anzahl, boxen: {} });
  mock.emit('neue_tobies', 'neu', { eintrag: e('0411', 1) });
  assert.equal(s.neueTobies.gesamt, 2); assert.equal(s.neueTobies.eintraege[0].uid, '0411');
  mock.emit('neue_tobies', 'aktualisiert', { eintrag: e('0411', 5) });
  assert.equal(s.neueTobies.gesamt, 2); assert.equal(s.neueTobies.eintraege[0].anzahl, 5);
  mock.emit('neue_tobies', 'entfernt', { uid: '0411', grund: 'verworfen' });
  assert.equal(s.neueTobies.gesamt, 1);
});

test('Ereignis medien: serien_geaendert lädt Liste und die offene Serie neu; Papierkorb', async () => {
  const { mock, store, s } = await neu();
  await lade(store);
  mock.backend.serien.s1.name = 'Umbenannt von außen';
  mock.emit('medien', 'serien_geaendert', { serie_ids: ['s1'] });
  await mock.tick(); await mock.tick();
  assert.equal(s.serie.name, 'Umbenannt von außen');
  assert.equal(s.serien.find((x) => x.id === 's1').name, 'Umbenannt von außen');
  mock.backend.papierkorb = [];
  mock.emit('medien', 'papierkorb_geaendert', {});
  await mock.tick(); await mock.tick();
  assert.equal(s.papierkorb.gesamt, 0);
  mock.emit('medien', 'pruefung_fertig', { geprueft_am: '2026-11-09T12:00:00Z', neue_serien: 0, neue_folgen: 0, entfernte_folgen: 0, hinweise: 0 });
  assert.equal(s.geprueftAm, '2026-11-09T12:00:00Z');
});

test('Ereignis eingang: neu_einsortiert wird gezeigt, geaendert lädt neu, durchlauf_fertig', async () => {
  const { mock, s } = await neu();
  mock.emit('eingang', 'neu_einsortiert', { eintrag_id: '1', eintrag_name: 'Hörbuch Neu', ergebnis: [{ serie_id: 's2', serie_name: 'Bibi', serie_neu: false, folge: 'b-02.mp3', anzeige: 'Folge 2', tracks: 1, pruefen: true, pruefen_gruende: ['tags_fehlen'] }], hinweise: [], zaehler: { folgen: 1, serien_neu: 0, pruefen: 1, doppelt: 0, blockiert: 0 } });
  assert.equal(s.neuEinsortiert[0].eintrag_name, 'Hörbuch Neu');
  mock.backend.eingang = [];
  mock.emit('eingang', 'geaendert', {});
  await mock.tick(); await mock.tick();
  assert.equal(s.eingang.eintraege.length, 0);
  s.eingang.sortierungLaeuft = true;
  mock.emit('eingang', 'durchlauf_fertig', { geprueft_am: 'x', zaehler: { eintraege: 1, folgen: 1, serien_neu: 0, pruefen: 0, doppelt: 0, blockiert: 0 } });
  assert.equal(s.eingang.sortierungLaeuft, false);
});

test('Ereignis konfig: geaendert, abweichung, export_fehler, export_ok', async () => {
  const { mock, s } = await neu();
  mock.backend.zuordnungen = {};
  mock.emit('konfig', 'geaendert', { konfig: { ...s.konfig, revision: 8 } });
  assert.equal(s.konfig.revision, 8);
  await mock.tick(); await mock.tick();
  assert.equal(s.zuordnungen.gesamt, 0);
  mock.emit('konfig', 'abweichung', { box: 'kueche', grund: 'voraus', box_liste_id: 'l', box_revision: 9, ha_revision: 8 });
  assert.equal(s.abweichung.box, 'kueche');
  mock.emit('konfig', 'export_fehler', { seit: 't', text: 'NAS schläft' });
  assert.equal(s.konfig.export_ok, false); assert.equal(s.exportFehler.text, 'NAS schläft');
  mock.emit('konfig', 'export_ok', { export_geschrieben_am: '2026-11-09T13:00:00Z' });
  assert.equal(s.konfig.export_ok, true); assert.equal(s.exportFehler, null);
});

test('Ereignisse ändern den Zustand und melden sich bei Zuhörern (Ansicht)', async () => {
  const { mock, store } = await neu();
  let n = 0;
  store.onChange(() => { n += 1; });
  mock.backend.konfig = { revision: 99, liste_id: 'x', zustand: 'export_neuer', export_ok: true, export_geschrieben_am: null };
  mock.emit('konfig', 'geaendert', { konfig: mock.backend.konfig });
  await mock.tick();
  assert.ok(n >= 1);
  assert.equal(store.hatKonfig, false);
});

/* ------------------------------------------------------------------ Abdeckung */

test('Jeder Befehl aus Vertrag W wurde mit seinen Feldern gegen den Mock gesendet', async () => {
  const { mock, store, s } = await neu({}, { prompt: 'Name', serie: 's2', ziel: { ziel: { typ: 'serie', serie: 's1' }, name: null, box: 'kueche' } });
  // Befehle, die in den Tests oben nicht jede Variante hatten, hier noch einmal kurz
  await store.zuordnen('0499887766554433', null);
  await store.lernStart(); await store.lernAbbrechen('kueche');
  await store.lernStart(); await store.lernAntwort(s.lern.kueche.befehl_id, true);
  await store.hochladen([new File([new Uint8Array(1)], 'a.mp3')]);
  const gesehen = new Set(mocks.flatMap((m) => m.calls.map((c) => c.type)));
  const fehlt = Object.keys(SCHEMA).filter((t) => !gesehen.has(t));
  assert.deepEqual(fehlt, []);
  assert.ok(mock.calls.length > 0);
});

/* ------------------------------------------------------------------ Darstellung (jsdom) */

async function ladeJsdom() {
  try { return await import('jsdom'); } catch { /* weiter */ }
  if (process.env.TOBIBOX_JSDOM_DIR) {
    try { return createRequire(join(process.env.TOBIBOX_JSDOM_DIR, 'x.js'))('jsdom'); } catch { /* weiter */ }
  }
  return null;
}
const jsdom = await ladeJsdom();
const MIT_DOM = { skip: jsdom ? false : 'jsdom nicht verfügbar (TOBIBOX_JSDOM_DIR setzen oder npm i jsdom)' };
let Element = null;

async function domBereit() {
  if (Element) return;
  const dom = new jsdom.JSDOM('<!doctype html><body></body>', { pretendToBeVisual: true });
  for (const k of ['window', 'document', 'HTMLElement', 'customElements', 'Node', 'NodeFilter', 'Document', 'ShadowRoot', 'CSSStyleSheet', 'Element', 'Event', 'CustomEvent', 'DocumentFragment', 'Comment', 'Text', 'HTMLTemplateElement', 'MutationObserver']) {
    globalThis[k] = dom.window[k];
  }
  await import('../../custom_components/tobibox/frontend/tobibox-panel.js?dom');
  Element = dom.window.customElements.get('tobibox-panel');
  assert.ok(Element, 'tobibox-panel ist als Custom Element registriert');
}

async function seite(opts = {}) {
  await domBereit();
  const mock = createMockHass(opts);
  const el = new Element();
  document.body.appendChild(el);
  el.store.xhrFactory = mock.xhrFactory;
  el.hass = mock.hass;
  for (let i = 0; i < 6; i++) { await mock.tick(); await el.updateComplete; }
  return { el, mock, q: (sel) => el.shadowRoot.querySelector(sel), qa: (sel) => [...el.shadowRoot.querySelectorAll(sel)], flush: async () => { await mock.tick(); await mock.tick(); await el.updateComplete; } };
}

test('Darstellung: <tobibox-panel> zeigt die Serienliste, deutsch, mit Tippflächen', MIT_DOM, async () => {
  const { el, qa, q } = await seite();
  const text = el.shadowRoot.textContent;
  assert.match(text, /Tobi Box/); assert.match(text, /Die drei \?\?\?/); assert.match(text, /3 Folgen · 2 Tobies/);
  assert.equal(qa('button.karte.zeile').length, 3);
  assert.ok(q('nav'));
});

test('Darstellung: Namen werden nur als Text dargestellt, nie als HTML', MIT_DOM, async () => {
  const { el, mock, qa, flush } = await seite();
  mock.backend.serien.s1.name = '<img src=x onerror="window.boese=1"><b>fett</b>';
  mock.backend.serien.s1.folgen[0].anzeige = '<script>window.boese=2</script>';
  el.store.neuLaden(); await flush(); await flush();
  assert.equal(el.shadowRoot.querySelector('img'), null);
  assert.equal(el.shadowRoot.querySelector('b'), null);
  assert.ok(el.shadowRoot.textContent.includes('<img src=x onerror="window.boese=1"><b>fett</b>'));
  qa('button.karte.zeile').find((b) => b.textContent.includes('<img')).click(); await flush(); await flush();
  assert.equal(el.shadowRoot.querySelector('script'), null);
  assert.ok(el.shadowRoot.textContent.includes('<script>window.boese=2</script>'));
  assert.equal(globalThis.boese, undefined);
});

test('Darstellung: Fehlerantworten erscheinen als Hinweis mit role=alert', MIT_DOM, async () => {
  const { el, mock, q, flush } = await seite();
  mock.failNext('tobibox/box/sync', 'box_offline');
  await el.store.boxSync('kueche'); await flush();
  const b = q('.banner.err');
  assert.ok(b); assert.equal(b.getAttribute('role'), 'alert');
  assert.match(b.textContent, /Die Box ist nicht erreichbar/);
  b.querySelector('button').click(); await flush();
  assert.equal(q('.banner.err'), null);
});

test('Darstellung: Abos aktualisieren die Ansicht (Neue Tobies, Box, Warnung)', MIT_DOM, async () => {
  const { el, mock, q, qa, flush } = await seite();
  el.store.zeige('tobies'); await flush();
  assert.equal(qa('.karte .titel').filter((t) => t.textContent.includes('0411')).length, 0);
  mock.emit('neue_tobies', 'neu', { eintrag: { uid: '041122334455', zuerst: 'a', zuletzt: '2026-11-09T10:00:00Z', anzahl: 1, boxen: { kueche: {} } } });
  await flush();
  assert.ok(qa('.karte .titel').some((t) => t.textContent.includes('0411…4455')));
  assert.match(q('nav').textContent, /Tobies\s*2/);
  mock.backend.konfig = { revision: null, liste_id: null, zustand: 'leer_neu', export_ok: true, export_geschrieben_am: null };
  mock.emit('konfig', 'geaendert', { konfig: mock.backend.konfig });
  await flush();
  assert.match(q('.banner.warn').textContent, /Die Liste der Tobies ist leer/);
  assert.match(q('.banner.warn').textContent, /Aus dem Export holen/);
  assert.match(q('.banner.warn').textContent, /Mit leerer Liste neu beginnen/);
  assert.ok(qa('button').filter((b) => b.textContent.trim() === 'Zuordnen').every((b) => b.disabled), 'Zuordnen ist gesperrt');
  el.store.zeige('boxen'); await flush();
  mock.emit('boxen', 'geaendert', { box: 'kueche', anzeigename: 'Küche', online: true, status: { speicher_frei_mb: 77 }, status_empfangen_am: 't', konfig_stand: 'voraus', lernmodus: null });
  await flush();
  assert.match(el.shadowRoot.textContent, /77 MB/);
  assert.match(el.shadowRoot.textContent, /Box hat neueren Stand/);
});

test('Darstellung: Box-Status mit freiem Speicher und Konfig-Stand', MIT_DOM, async () => {
  const { el, flush } = await seite();
  el.store.zeige('boxen'); await flush();
  const t = el.shadowRoot.textContent;
  assert.match(t, /Freier Speicher: 5120 MB/); assert.match(t, /Liste aktuell/); assert.match(t, /Liste veraltet/);
  assert.match(t, /Liste neu ausrollen/);
});

test('Darstellung: Folgen mit Hoch/Runter, Rückfrage beim Löschen zeigt die Anzahl der Tobies', MIT_DOM, async () => {
  const { el, mock, q, qa, flush } = await seite();
  qa('button.karte.zeile')[0].click(); await flush(); await flush();
  assert.equal(qa('.folge').length, 3);
  qa('.folge')[1].querySelector('button[aria-label="Runter"]').click(); await flush(); await flush();
  assert.deepEqual(mock.letzter('tobibox/folgen/order').folgen, ['folge-01.mp3', 'folge-03.mp3', 'folge-02.mp3']);
  const zeile = qa('.folge').find((f) => f.textContent.includes('Das Gespensterschloss'));
  [...zeile.querySelectorAll('button')].find((b) => b.textContent.trim() === 'Löschen').click();
  await flush(); await flush();
  const d = q('.dialog');
  assert.ok(d); assert.match(d.textContent, /1 Tobie zeigt darauf/);
  [...d.querySelectorAll('button')].find((b) => b.textContent.includes('Abbrechen')).click(); await flush();
  assert.equal(q('.dialog'), null);
  assert.equal(mock.aufrufe('tobibox/folge/delete').length, 0);
});

test('Darstellung: Rückfrage des Lernmodus beim Überschreiben', MIT_DOM, async () => {
  const { el, mock, q, flush } = await seite();
  el.store.s.lern = { kueche: { box: 'kueche', befehl_id: 'b-1', zustand: 'wartet', ziel: { typ: 'serie', serie: 's2' } } };
  mock.emit('lernmodus', 'rueckfrage', { box: 'kueche', befehl_id: 'b-1', zustand: 'rueckfrage', ziel: { typ: 'serie', serie: 's2' }, uid: '04A1B2C3D4E5F6', bisher: { typ: 'serie', serie: 's1' }, rueckfrage_bis: '2026-11-09T10:01:00Z' });
  await flush();
  const d = q('[role=alertdialog]');
  assert.ok(d); assert.match(d.textContent, /Zuordnung überschreiben/); assert.match(d.textContent, /Die drei \?\?\?/);
  assert.match(d.textContent, /Bibi Blocksberg/);
});

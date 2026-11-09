/* Tests der Seite zu AP 4.7 (Einstellungen: Leise-Zeiten, Gute Nacht, Lesezeichen) und zu den Erweiterungen v1.1
 * des Vertrags W (Abschnitt 10). Aufruf: node --test homeassistant/tests/frontend (über index.js).
 *
 * Die Logik (TobiboxStore) läuft ohne DOM gegen den Mock (mock-hass.mjs); die Darstellungstests brauchen jsdom
 * (TOBIBOX_JSDOM_DIR) und werden sonst übersprungen. Der Mock simuliert ein Backend mit und ohne die neuen
 * Fähigkeiten: Die Seite darf neue Befehle und Felder nur senden, wenn hello sie zusagt.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createMockHass, pruefeEingabe, FAEHIGKEITEN, FAEHIGKEITEN_V11, SCHEMA_V11 } from './mock-hass.mjs';

const HIER = fileURLToPath(new URL('.', import.meta.url));
const panel = await import('../../custom_components/tobibox/frontend/tobibox-panel.js');
const {
  TobiboxStore, FEHLERTEXTE, fehlerText, stelleText, pruefeLeiseZeiten, pruefeGuteNacht, pruefeLesezeichenTage,
  leiseZeitenFuerBackend, zuZahl, zeitzoneBekannt, EINSTELLUNG_GRENZEN, neueFensterId,
} = panel;

const NEU = [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11];
const mocks = [];

/* Store mit Mock; `antworten` steuert die Rückfragen. Ohne Angabe sagt das Backend alle neuen Fähigkeiten zu. */
async function neu(opts = {}, antworten = {}) {
  const mock = createMockHass({ faehigkeiten: NEU, ...opts });
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
const alt = (opts = {}, antworten = {}) => neu({ faehigkeiten: FAEHIGKEITEN, ...opts }, antworten); // Backend von vor AP 4.7

const sendet = (mock, typ) => mock.aufrufe(typ).map(({ id, type, ...felder }) => felder); // eslint-disable-line no-unused-vars

/* ------------------------------------------------------------------ Grenzen */

test('Grenzen der Seite = Grenzen im Datenmodell (docs/data-model.md, Abschnitt 2) und auf der Box', () => {
  const doc = readFileSync(join(HIER, '../../../docs/data-model.md'), 'utf8');
  assert.match(doc, /`gute_nacht\.timer_min` \| int 1–240/);
  assert.match(doc, /`gute_nacht\.ausblenden_s` \| int 5–600/);
  assert.match(doc, /`lesezeichen_tage` \| int 0–365/);
  assert.match(doc, /`fenster\[\]\.grenze` \| int 0–100/);
  assert.match(doc, /beliebig viele, höchstens 32/);
  assert.deepEqual(EINSTELLUNG_GRENZEN, { fensterMax: 32, grenze: [0, 100], timerMin: [1, 240], ausblendenS: [5, 600], lesezeichenTage: [0, 365] });
});

const FENSTER = { id: 'abend', tage: [1, 2, 3, 4, 5, 6, 7], von: '19:30', bis: '21:00', wirkung: 'leiser', grenze: 25 };
const lz = (f = {}, zone = 'Europe/Berlin') => ({ zeitzone: zone, fenster: [{ ...FENSTER, ...f }] });

test('Prüfung der Leise-Zeiten: gültig, und jede Grenze an beiden Seiten', () => {
  assert.equal(pruefeLeiseZeiten({ zeitzone: 'Europe/Berlin', fenster: [] }), null);
  assert.equal(pruefeLeiseZeiten(lz()), null);
  assert.equal(pruefeLeiseZeiten(lz({ grenze: 0 })), null);
  assert.equal(pruefeLeiseZeiten(lz({ grenze: 100 })), null);
  assert.equal(pruefeLeiseZeiten(lz({ von: '23:59', bis: '00:00' })), null); // über Mitternacht
  assert.equal(pruefeLeiseZeiten(lz({ wirkung: 'stumm', grenze: undefined })), null);
  const viele = (n) => ({ zeitzone: 'UTC', fenster: Array.from({ length: n }, (_, i) => ({ ...FENSTER, id: `f${i}` })) });
  assert.equal(pruefeLeiseZeiten(viele(32)), null);
  assert.match(pruefeLeiseZeiten(viele(33)), /höchstens 32/);
  for (const [f, muster] of [
    [{ grenze: -1 }, /Grenze/], [{ grenze: 101 }, /Grenze/], [{ grenze: 25.5 }, /Grenze/], [{ grenze: '25' }, /Grenze/], [{ grenze: undefined }, /Grenze/],
    [{ tage: [] }, /Wochentag/], [{ tage: [0] }, /Wochentag/], [{ tage: [8] }, /Wochentag/], [{ tage: [1, 1] }, /Wochentag/],
    [{ von: '24:00' }, /„von“/], [{ von: '7:30' }, /„von“/], [{ von: '' }, /„von“/], [{ bis: '19:60' }, /„bis“/],
    [{ bis: '19:30' }, /nicht gleich/],
    [{ wirkung: 'laut' }, /leiser/], [{ id: '' }, /Name/], [{ id: 'Gross' }, /Name/], [{ id: 'a'.repeat(33) }, /Name/],
  ]) {
    assert.match(pruefeLeiseZeiten(lz(f)) || 'kein Fehler', muster, JSON.stringify(f));
  }
  assert.match(pruefeLeiseZeiten({ zeitzone: 'Europe/Berlin', fenster: [FENSTER, { ...FENSTER }] }), /doppelt/);
  assert.match(pruefeLeiseZeiten(lz({}, 'Nirgendwo/Stadt')), /Zeitzone/);
  assert.match(pruefeLeiseZeiten(lz({}, '')), /Zeitzone/);
  assert.match(pruefeLeiseZeiten(null), /fehlen/);
  assert.equal(zeitzoneBekannt('Europe/Berlin'), true);
  assert.equal(zeitzoneBekannt('UTC'), true);
  assert.equal(zeitzoneBekannt('Mars/Olympus'), false);
});

test('Prüfung von Gute Nacht und Lesezeichen: ganze Zahlen in den Grenzen', () => {
  const gn = (timer_min, ausblenden_s) => ({ timer_min, ausblenden_s });
  for (const [t, a] of [[1, 5], [240, 600], [30, 60]]) assert.equal(pruefeGuteNacht(gn(t, a)), null);
  for (const [t, a] of [[0, 60], [241, 60], [30, 4], [30, 601], [30.5, 60], ['30', 60], [30, NaN], [undefined, 60], [true, 60]]) {
    assert.ok(pruefeGuteNacht(gn(t, a)), `${t}/${a}`);
  }
  assert.match(pruefeGuteNacht(gn(0, 60)), /Timer/);
  assert.match(pruefeGuteNacht(gn(30, 4)), /Ausblenden/);
  for (const t of [0, 1, 14, 365]) assert.equal(pruefeLesezeichenTage(t), null);
  for (const t of [-1, 366, 14.5, '14', null, undefined, NaN, true]) assert.ok(pruefeLesezeichenTage(t), String(t));
});

test('zuZahl: Zahlen aus Eingabefeldern; alles andere bleibt Text und fällt in der Prüfung durch', () => {
  assert.equal(zuZahl('45'), 45); assert.equal(zuZahl(' 7 '), 7); assert.equal(zuZahl('0'), 0); assert.equal(zuZahl(12), 12);
  for (const x of ['', 'abc', '4.5', '1e2', '--3']) assert.equal(zuZahl(x), x);
});

test('Was die Seite sendet: Tage sortiert, bei „stumm“ ohne Grenze, Zusatzfelder fallen weg', () => {
  const out = leiseZeitenFuerBackend({ zeitzone: ' Europe/Berlin ', fenster: [
    { id: 'a', tage: [3, 1, 2], von: '21:00', bis: '06:30', wirkung: 'stumm', grenze: 40, extra: 1 },
    { id: 'b', tage: [7], von: '19:00', bis: '20:00', wirkung: 'leiser', grenze: '30' }] });
  assert.deepEqual(out, { zeitzone: 'Europe/Berlin', fenster: [
    { id: 'a', tage: [1, 2, 3], von: '21:00', bis: '06:30', wirkung: 'stumm' },
    { id: 'b', tage: [7], von: '19:00', bis: '20:00', wirkung: 'leiser', grenze: 30 }] });
  assert.equal(neueFensterId([]), 'fenster-1');
  assert.equal(neueFensterId([{ id: 'fenster-1' }, { id: 'fenster-3' }]), 'fenster-2');
});

test('Texte: einstellung_ungueltig und sortierung_laeuft sind erklärt; die Stelle steht in Worten', () => {
  const doc = readFileSync(join(HIER, '../../../docs/protocol/ha-websocket-v1.md'), 'utf8');
  const tabelle = doc.slice(doc.indexOf('## 7. Gemeinsame Fehlercodes'), doc.indexOf('## 8. Grenzen'));
  for (const c of ['einstellung_ungueltig', 'sortierung_laeuft']) {
    assert.match(tabelle, new RegExp(`^\\| \`${c}\` \\|`, 'm'), `${c} steht im Vertrag, Abschnitt 7`);
    assert.ok(FEHLERTEXTE[c]);
  }
  assert.equal(stelleText('fenster[0].von'), 'Fenster 1, von');
  assert.equal(stelleText('fenster[11].grenze'), 'Fenster 12, Grenze');
  assert.equal(stelleText('fenster[2]'), 'Fenster 3');
  assert.equal(stelleText("leise_zeiten.zeitzone 'x'"), 'Zeitzone');
  assert.equal(stelleText('leise_zeiten.fenster'), 'Leise-Zeiten');
  assert.equal(stelleText('gute_nacht.timer_min'), 'Timer');
  assert.equal(stelleText('gute_nacht.ausblenden_s'), 'Ausblenden');
  assert.equal(stelleText('lesezeichen_tage'), 'Lesezeichen-Ablauf');
  assert.match(fehlerText('einstellung_ungueltig', 'Diese Einstellung ist ungültig: fenster[1].bis. Es wurde nichts geändert.'), /Stelle: Fenster 2, bis\./);
  assert.equal(fehlerText('einstellung_ungueltig', 'unbekanntes Format'), FEHLERTEXTE.einstellung_ungueltig);
});

test('Der Mock bildet ältere Backends ab: neue Befehle und Felder nur mit der Fähigkeit', () => {
  assert.throws(() => pruefeEingabe({ type: 'tobibox/einstellungen/get' }, FAEHIGKEITEN), (e) => e.code === 'unknown_command');
  assert.throws(() => pruefeEingabe({ type: 'tobibox/zuordnung/list', uid: 'a' }, FAEHIGKEITEN), (e) => e.code === 'invalid_format');
  assert.doesNotThrow(() => pruefeEingabe({ type: 'tobibox/zuordnung/list', uid: 'a' }, NEU));
  assert.doesNotThrow(() => pruefeEingabe({ type: 'tobibox/einstellungen/set', lesezeichen_tage: 3 }, NEU));
  assert.throws(() => pruefeEingabe({ type: 'tobibox/einstellungen/set', hinweis_pegel: 3 }, NEU), (e) => e.code === 'invalid_format');
  assert.throws(() => pruefeEingabe({ type: 'tobibox/eingang/entfernen', eintrag_id: 'x' }, NEU), (e) => e.code === 'invalid_format');
});

/* ------------------------------------------------------------------ Einstellungen: Laden */

test('Start mit Fähigkeit „einstellungen“: einstellungen/get wird gelesen', async () => {
  const { mock, s } = await neu();
  assert.equal(mock.aufrufe('tobibox/einstellungen/get').length, 1);
  assert.deepEqual(mock.letzter('tobibox/einstellungen/get'), { id: mock.letzter('tobibox/einstellungen/get').id, type: 'tobibox/einstellungen/get' });
  assert.equal(s.einstellungen.geladen, true);
  assert.deepEqual(s.einstellungen.leise_zeiten, { zeitzone: 'Europe/Berlin', fenster: [] });
  assert.deepEqual(s.einstellungen.gute_nacht, { timer_min: 30, ausblenden_s: 60 });
  assert.equal(s.einstellungen.lesezeichen_tage, 14);
});

test('Ohne die Fähigkeit: kein einstellungen-Aufruf, auch nicht beim Öffnen oder Speichern', async () => {
  const { mock, store, s } = await alt();
  assert.equal(s.einstellungen.geladen, false);
  await store.zeige('einstellungen');
  assert.equal(await store.lesezeichenSpeichern(), true); // kein Entwurf: nichts zu tun
  store.lesezeichenSetzen('5');
  assert.equal(await store.lesezeichenSpeichern(), false);
  assert.equal(mock.aufrufe('tobibox/einstellungen/get').length + mock.aufrufe('tobibox/einstellungen/set').length, 0);
});

test('Ansicht „Einstellungen“ öffnen liest neu', async () => {
  const { mock, store, s } = await neu();
  mock.backend.einstellungen.lesezeichen_tage = 30; // jemand anders hat es geändert
  await store.zeige('einstellungen');
  assert.equal(s.view, 'einstellungen');
  assert.equal(s.einstellungen.lesezeichen_tage, 30);
  assert.equal(mock.aufrufe('tobibox/einstellungen/get').length, 2);
});

/* ------------------------------------------------------------------ Leise-Zeiten */

test('Leise-Zeiten: neues Fenster „stumm“ wird mit den richtigen Feldern gesendet, Revision steigt', async () => {
  const { mock, store, s } = await neu();
  const rev = s.konfig.revision;
  store.fensterNeu();
  assert.equal(store.einstellungenGeaendert.leise, true);
  assert.equal(mock.aufrufe('tobibox/einstellungen/set').length, 0); // erst Speichern sendet
  assert.equal(await store.leiseSpeichern(), true);
  assert.deepEqual(sendet(mock, 'tobibox/einstellungen/set'), [{ leise_zeiten: { zeitzone: 'Europe/Berlin', fenster: [
    { id: 'fenster-1', tage: [1, 2, 3, 4, 5, 6, 7], von: '21:00', bis: '06:30', wirkung: 'stumm' }] } }]);
  assert.equal(s.konfig.revision, rev + 1); // die Änderung erscheint als neue Revision (tobibox/config)
  assert.equal(s.entwurf.leise, null);
  assert.equal(s.einstellungen.leise_zeiten.fenster.length, 1);
  assert.match(s.hinweis.text, /Gespeichert/);
  assert.equal(s.fehler, null);
});

test('Leise-Zeiten: „leiser“ mit Grenze, Wechsel zurück auf „stumm“ entfernt die Grenze', async () => {
  const { mock, store, s } = await neu();
  store.fensterNeu();
  store.fensterAendern(0, { wirkung: 'leiser' });
  assert.equal(store.leiseAnzeige.fenster[0].grenze, 25); // Vorgabe
  store.fensterAendern(0, { grenze: 40, von: '19:30', bis: '21:00' });
  store.tageSetzen(0, [1, 2, 3, 4, 5]);
  store.zeitzoneSetzen('Europe/London');
  await store.leiseSpeichern();
  assert.deepEqual(mock.letzter('tobibox/einstellungen/set').leise_zeiten, { zeitzone: 'Europe/London', fenster: [
    { id: 'fenster-1', tage: [1, 2, 3, 4, 5], von: '19:30', bis: '21:00', wirkung: 'leiser', grenze: 40 }] });
  store.fensterAendern(0, { wirkung: 'stumm' });
  assert.equal('grenze' in store.leiseAnzeige.fenster[0], false);
  await store.leiseSpeichern();
  assert.equal('grenze' in mock.letzter('tobibox/einstellungen/set').leise_zeiten.fenster[0], false);
  assert.equal(s.einstellungen.leise_zeiten.zeitzone, 'Europe/London');
});

test('Leise-Zeiten: Wochentage umschalten bleiben sortiert; Fenster löschen; mehrere Fenster', async () => {
  const { mock, store } = await neu();
  store.fensterNeu(); store.fensterNeu();
  assert.deepEqual(store.leiseAnzeige.fenster.map((f) => f.id), ['fenster-1', 'fenster-2']);
  store.tagUmschalten(0, 3); store.tagUmschalten(0, 3); store.tagUmschalten(0, 7);
  assert.deepEqual(store.leiseAnzeige.fenster[0].tage, [1, 2, 3, 4, 5, 6]);
  store.tagUmschalten(0, 7);
  assert.deepEqual(store.leiseAnzeige.fenster[0].tage, [1, 2, 3, 4, 5, 6, 7]);
  store.fensterLoeschen(0);
  assert.deepEqual(store.leiseAnzeige.fenster.map((f) => f.id), ['fenster-2']);
  store.fensterNeu(); // fenster-1 ist wieder frei
  assert.deepEqual(store.leiseAnzeige.fenster.map((f) => f.id), ['fenster-2', 'fenster-1']);
  await store.leiseSpeichern();
  assert.equal(mock.letzter('tobibox/einstellungen/set').leise_zeiten.fenster.length, 2);
});

test('Leise-Zeiten: Verwerfen löscht den Entwurf, nichts wird gesendet', async () => {
  const { mock, store, s } = await neu();
  store.fensterNeu();
  store.entwurfVerwerfen('leise');
  assert.equal(s.entwurf.leise, null);
  assert.equal(store.leiseAnzeige.fenster.length, 0);
  assert.equal(await store.leiseSpeichern(), true);
  assert.equal(mock.aufrufe('tobibox/einstellungen/set').length, 0);
});

test('Leise-Zeiten: höchstens 32 Fenster; das 33. wird nicht angelegt', async () => {
  const { store, s } = await neu();
  for (let i = 0; i < 33; i++) store.fensterNeu();
  assert.equal(store.leiseAnzeige.fenster.length, 32);
  assert.match(s.hinweis.text, /höchstens 32/);
});

const UNGUELTIG = [
  ['kein Wochentag', (st) => { st.fensterNeu(); st.tageSetzen(0, []); }, /Wochentag/],
  ['von = bis', (st) => { st.fensterNeu(); st.fensterAendern(0, { von: '20:00', bis: '20:00' }); }, /nicht gleich/],
  ['Uhrzeit leer', (st) => { st.fensterNeu(); st.fensterAendern(0, { von: '' }); }, /„von“/],
  ['Grenze über 100', (st) => { st.fensterNeu(); st.fensterAendern(0, { wirkung: 'leiser', grenze: 101 }); }, /Grenze/],
  ['Grenze mit Komma', (st) => { st.fensterNeu(); st.fensterAendern(0, { wirkung: 'leiser', grenze: 12.5 }); }, /Grenze/],
  ['Zeitzone unbekannt', (st) => { st.fensterNeu(); st.zeitzoneSetzen('Mars/Olympus'); }, /Zeitzone/],
];
for (const [name, bereite, muster] of UNGUELTIG) {
  test(`Leise-Zeiten ungültig (${name}): Text in Worten, nichts wird gesendet, der Entwurf bleibt`, async () => {
    const { mock, store, s } = await neu();
    bereite(store);
    assert.equal(await store.leiseSpeichern(), false);
    assert.equal(mock.aufrufe('tobibox/einstellungen/set').length, 0);
    assert.equal(s.fehler.code, 'einstellung_ungueltig');
    assert.match(s.fehler.text, muster);
    assert.ok(s.entwurf.leise, 'der Entwurf bleibt, damit Tobias ihn verbessern kann');
  });
}

test('Leise-Zeiten: das Backend lehnt ab (einstellung_ungueltig): Stelle in Worten, Entwurf und Stand bleiben', async () => {
  const { mock, store, s } = await neu();
  store.fensterNeu();
  mock.failNext('tobibox/einstellungen/set', { code: 'einstellung_ungueltig', message: 'Diese Einstellung ist ungültig: fenster[0].von. Es wurde nichts geändert.' });
  assert.equal(await store.leiseSpeichern(), false);
  assert.equal(s.fehler.code, 'einstellung_ungueltig');
  assert.match(s.fehler.text, /Stelle: Fenster 1, von\./);
  assert.ok(s.entwurf.leise);
  assert.equal(s.einstellungen.leise_zeiten.fenster.length, 0);
});

test('Leise-Zeiten: der Mock-Server lehnt auch ab, was die Seite durchlassen würde (Gegenprobe der Prüfung)', async () => {
  const { mock } = await neu();
  for (const bad of [lz({ von: '25:00' }), lz({ grenze: 101 }), lz({ tage: [] })]) {
    await assert.rejects(mock.hass.connection.sendMessagePromise({ type: 'tobibox/einstellungen/set', leise_zeiten: bad }), (e) => e.code === 'einstellung_ungueltig');
  }
  for (const gut of [lz(), lz({ wirkung: 'stumm', grenze: undefined })]) {
    assert.equal(pruefeLeiseZeiten(gut), null);
    await mock.hass.connection.sendMessagePromise({ type: 'tobibox/einstellungen/set', leise_zeiten: JSON.parse(JSON.stringify(gut)) });
  }
});

test('Gesperrte Konfiguration (leer_neu): kein Speichern, Warnung statt Aufruf', async () => {
  const { mock, store, s } = await neu();
  store.fensterNeu();
  s.konfig = { ...s.konfig, zustand: 'leer_neu' };
  assert.equal(await store.leiseSpeichern(), false);
  assert.equal(s.fehler.code, 'konfig_nicht_bereit');
  assert.equal(mock.aufrufe('tobibox/einstellungen/set').length, 0);
});

test('Kein Schreibrecht des Backends: unauthorized wird angezeigt, Entwurf bleibt', async () => {
  const { mock, store, s } = await neu({ darf: false });
  store.lesezeichenSetzen('3');
  assert.equal(await store.lesezeichenSpeichern(), false);
  assert.equal(s.fehler.code, 'unauthorized');
  assert.equal(s.entwurf.lesezeichen, '3');
  assert.equal(mock.aufrufe('tobibox/einstellungen/get').length, 1); // Lesen geht
});

/* ------------------------------------------------------------------ Gute Nacht und Lesezeichen */

test('Gute Nacht: Zahlen aus den Feldern werden ganze Zahlen; nur gute_nacht wird gesendet', async () => {
  const { mock, store, s } = await neu();
  const rev = s.konfig.revision;
  store.guteNachtSetzen('timer_min', '45');
  assert.equal(store.guteAnzeige.ausblenden_s, 60); // der andere Wert bleibt aus dem gespeicherten Stand
  await store.guteNachtSpeichern();
  assert.deepEqual(sendet(mock, 'tobibox/einstellungen/set'), [{ gute_nacht: { timer_min: 45, ausblenden_s: 60 } }]);
  assert.equal(s.konfig.revision, rev + 1);
  assert.deepEqual(s.einstellungen.gute_nacht, { timer_min: 45, ausblenden_s: 60 });
  store.guteNachtSetzen('ausblenden_s', '120');
  await store.guteNachtSpeichern();
  assert.deepEqual(mock.letzter('tobibox/einstellungen/set').gute_nacht, { timer_min: 45, ausblenden_s: 120 });
  assert.equal(Number.isInteger(mock.letzter('tobibox/einstellungen/set').gute_nacht.timer_min), true);
});

test('Gute Nacht ungültig: nichts wird gesendet', async () => {
  const { mock, store, s } = await neu();
  for (const [feld, wert, muster] of [['timer_min', '0', /Timer/], ['timer_min', '241', /Timer/], ['timer_min', '', /Timer/], ['timer_min', '4.5', /Timer/],
    ['ausblenden_s', '4', /Ausblenden/], ['ausblenden_s', '601', /Ausblenden/], ['ausblenden_s', 'abc', /Ausblenden/]]) {
    store.entwurfVerwerfen('gute');
    store.guteNachtSetzen(feld, wert);
    assert.equal(await store.guteNachtSpeichern(), false, `${feld}=${wert}`);
    assert.match(s.fehler.text, muster);
  }
  assert.equal(mock.aufrufe('tobibox/einstellungen/set').length, 0);
});

test('Gute Nacht: Grenzwerte 1/5 und 240/600 gehen durch', async () => {
  const { mock, store } = await neu();
  store.guteNachtSetzen('timer_min', '1'); store.guteNachtSetzen('ausblenden_s', '5');
  assert.equal(await store.guteNachtSpeichern(), true);
  store.guteNachtSetzen('timer_min', '240'); store.guteNachtSetzen('ausblenden_s', '600');
  assert.equal(await store.guteNachtSpeichern(), true);
  assert.deepEqual(mock.letzter('tobibox/einstellungen/set').gute_nacht, { timer_min: 240, ausblenden_s: 600 });
});

test('Lesezeichen: 0 = nie wird gesendet (nicht weggelassen); Grenzen 0 und 365', async () => {
  const { mock, store, s } = await neu();
  store.lesezeichenSetzen('0');
  assert.equal(await store.lesezeichenSpeichern(), true);
  assert.deepEqual(sendet(mock, 'tobibox/einstellungen/set'), [{ lesezeichen_tage: 0 }]);
  assert.equal(s.einstellungen.lesezeichen_tage, 0);
  assert.equal(s.entwurf.lesezeichen, null);
  assert.equal(store.lesezeichenAnzeige, 0);
  store.lesezeichenSetzen('365');
  assert.equal(await store.lesezeichenSpeichern(), true);
  assert.equal(mock.letzter('tobibox/einstellungen/set').lesezeichen_tage, 365);
});

test('Lesezeichen ungültig: nichts wird gesendet', async () => {
  const { mock, store, s } = await neu();
  for (const wert of ['366', '-1', '', 'x', '14.5']) {
    store.lesezeichenSetzen(wert);
    assert.equal(await store.lesezeichenSpeichern(), false, wert);
    assert.match(s.fehler.text, /0 bis 365/);
  }
  assert.equal(mock.aufrufe('tobibox/einstellungen/set').length, 0);
});

test('Gleicher Wert wie gespeichert: das Backend meldet „schon so“, die Revision bleibt', async () => {
  const { mock, store, s } = await neu();
  const rev = s.konfig.revision;
  store.lesezeichenSetzen('14');
  await store.lesezeichenSpeichern();
  assert.equal(mock.letzter('tobibox/einstellungen/set').lesezeichen_tage, 14);
  assert.equal(s.konfig.revision, rev);
  assert.match(s.hinweis.text, /schon so/);
});

test('Nicht veröffentlicht (Broker weg): Hinweis, dass die Boxen es später bekommen', async () => {
  const { mock, store, s } = await neu();
  mock.on('tobibox/einstellungen/set', () => ({ geaendert: true, konfig: { ...mock.backend.konfig, revision: 9 }, veroeffentlicht: false,
    leise_zeiten: mock.backend.einstellungen.leise_zeiten, gute_nacht: mock.backend.einstellungen.gute_nacht, lesezeichen_tage: 3 }));
  store.lesezeichenSetzen('3');
  await store.lesezeichenSpeichern();
  assert.match(s.hinweis.text, /sobald der Broker wieder erreichbar ist/);
  assert.equal(s.konfig.revision, 9);
});

/* ------------------------------------------------------------------ Ereignisse */

test('Ereignis konfig/geaendert lädt die Einstellungen neu und lässt einen Entwurf stehen', async () => {
  const { mock, store, s } = await neu();
  store.lesezeichenSetzen('99');
  mock.backend.einstellungen.gute_nacht = { timer_min: 20, ausblenden_s: 30 }; // anderes Fenster hat geändert
  const n = mock.aufrufe('tobibox/einstellungen/get').length;
  mock.emit('konfig', 'geaendert', { konfig: mock.backend.konfig });
  await mock.tick(); await mock.tick();
  assert.equal(mock.aufrufe('tobibox/einstellungen/get').length, n + 1);
  assert.deepEqual(s.einstellungen.gute_nacht, { timer_min: 20, ausblenden_s: 30 });
  assert.equal(s.entwurf.lesezeichen, '99');
});

test('Ein Entwurf, der dem gespeicherten Stand entspricht, verschwindet beim Neuladen', async () => {
  const { mock, store, s } = await neu();
  store.lesezeichenSetzen(21);
  mock.backend.einstellungen.lesezeichen_tage = 21;
  await store.ladeEinstellungen();
  assert.equal(s.entwurf.lesezeichen, null);
  assert.equal(store.einstellungenGeaendert.lesezeichen, false);
});

/* ------------------------------------------------------------------ Erweiterung v1.1: eingang/entfernen */

test('eingang/entfernen: Rückfrage, dann eintrag_id und bestaetigt=true; Listen werden neu geladen', async () => {
  const { mock, store, dialoge, s } = await neu();
  const e = s.eingang.eintraege[0];
  assert.equal(await store.eingangEntfernen(e), true);
  assert.match(dialoge.at(-1).text, /Hoerbuch Neu/);
  assert.equal(dialoge.at(-1).gefahr, true);
  assert.deepEqual(sendet(mock, 'tobibox/eingang/entfernen'), [{ eintrag_id: '111111111111', bestaetigt: true }]);
  assert.equal(s.eingang.eintraege.length, 0);
});

test('eingang/entfernen: Abbruch der Rückfrage sendet nichts; ohne Fähigkeit gibt es den Befehl nicht', async () => {
  const { mock, store, s } = await neu({}, { confirm: false });
  assert.equal(await store.eingangEntfernen(s.eingang.eintraege[0]), false);
  assert.equal(mock.aufrufe('tobibox/eingang/entfernen').length, 0);
  const a = await alt();
  assert.equal(await a.store.eingangEntfernen(a.s.eingang.eintraege[0]), false);
  assert.equal(a.mock.aufrufe('tobibox/eingang/entfernen').length, 0);
});

test('eingang/entfernen: Fehler werden angezeigt (sortierung_laeuft, eintrag_nicht_gefunden)', async () => {
  const { mock, store, s } = await neu();
  mock.failNext('tobibox/eingang/entfernen', 'sortierung_laeuft');
  await store.eingangEntfernen(s.eingang.eintraege[0]);
  assert.equal(s.fehler.code, 'sortierung_laeuft');
  assert.equal(s.fehler.text, FEHLERTEXTE.sortierung_laeuft);
  mock.failNext('tobibox/eingang/entfernen', 'eintrag_nicht_gefunden');
  await store.eingangEntfernen(s.eingang.eintraege[0]);
  assert.equal(s.fehler.code, 'eintrag_nicht_gefunden');
});

/* ------------------------------------------------------------------ Erweiterung v1.1: zuordnung/list mit uid, konfig/get */

test('zuordnung/list mit uid: nach Umbenennen und Lösen wird nur diese Zuordnung neu gelesen', async () => {
  const { mock, store, s } = await neu({}, { prompt: 'Neuer Name' });
  const z = s.zuordnungen.liste.find((x) => x.uid === '04A1B2C3D4E5F6');
  mock.reset();
  await store.tobieUmbenennen(z);
  assert.deepEqual(sendet(mock, 'tobibox/zuordnung/list'), [{ uid: '04A1B2C3D4E5F6', limit: 1 }]);
  assert.equal(s.zuordnungen.liste.find((x) => x.uid === z.uid).name, 'Neuer Name');
  assert.equal(s.zuordnungen.liste.length, 2);
  assert.equal(s.zuordnungen.gesamt, 2);
  assert.deepEqual(s.zuordnungen.liste.map((x) => x.uid), ['04A1B2C3D4E5F6', '04FFEEDDCCBBAA']); // Reihenfolge nach uid bleibt
  mock.reset();
  await store.zuordnungLoesen(s.zuordnungen.liste[0]);
  assert.deepEqual(sendet(mock, 'tobibox/zuordnung/list'), [{ uid: '04A1B2C3D4E5F6', limit: 1 }]);
  assert.deepEqual(s.zuordnungen.liste.map((x) => x.uid), ['04FFEEDDCCBBAA']);
  assert.equal(s.zuordnungen.gesamt, 1);
});

test('zuordnung/list mit uid: eine neue Zuordnung kommt an der richtigen Stelle dazu', async () => {
  const { mock, store, s } = await neu({}, { ziel: { ziel: { typ: 'serie', serie: 's1' }, name: 'Neu' } });
  mock.reset();
  await store.zuordnen('0499887766554433', null);
  assert.deepEqual(sendet(mock, 'tobibox/zuordnung/list'), [{ uid: '0499887766554433', limit: 1 }]);
  assert.deepEqual(s.zuordnungen.liste.map((x) => x.uid), ['04A1B2C3D4E5F6', '04FFEEDDCCBBAA', '0499887766554433'].sort());
  assert.equal(s.zuordnungen.gesamt, 3);
});

test('Ältere Backends ohne „zuordnung_uid“: die ganze Liste wird gelesen, kein Feld uid', async () => {
  const { mock, store, s } = await alt({}, { prompt: 'Neuer Name' });
  mock.reset();
  await store.tobieUmbenennen(s.zuordnungen.liste[0]);
  const list = sendet(mock, 'tobibox/zuordnung/list');
  assert.equal(list.length, 1);
  assert.equal('uid' in list[0], false);
  assert.equal(list[0].limit, 100);
});

test('konfig/get ersetzt hello beim Nachladen des Konfig-Stands, wenn das Backend es zusagt', async () => {
  const { mock, store, s } = await neu({}, { ziel: { ziel: { typ: 'serie', serie: 's1' }, name: null } });
  mock.failNext('tobibox/zuordnung/set', 'konfig_nicht_bereit');
  const hellos = mock.aufrufe('tobibox/hello').length;
  mock.backend.konfig = { ...mock.backend.konfig, zustand: 'export_neuer' };
  await store.zuordnen('0499887766554433', null);
  assert.equal(s.fehler.code, 'konfig_nicht_bereit');
  assert.equal(mock.aufrufe('tobibox/konfig/get').length, 1);
  assert.equal(mock.aufrufe('tobibox/hello').length, hellos);
  assert.equal(s.konfig.zustand, 'export_neuer');
});

test('Ohne „konfig_lesen“ bleibt es bei hello', async () => {
  const { mock, store, s } = await alt({}, { ziel: { ziel: { typ: 'serie', serie: 's1' }, name: null } });
  mock.failNext('tobibox/zuordnung/set', 'konfig_nicht_bereit');
  const hellos = mock.aufrufe('tobibox/hello').length;
  await store.zuordnen('0499887766554433', null);
  assert.equal(mock.aufrufe('tobibox/konfig/get').length, 0);
  assert.equal(mock.aufrufe('tobibox/hello').length, hellos + 1);
  assert.equal(s.fehler.code, 'konfig_nicht_bereit');
});

/* ------------------------------------------------------------------ Erweiterung v1.1: Upload fertig */

test('Ereignis „Upload fertig“ mit datei und pruefung rettet einen Upload, dessen Verbindung abbrach', async () => {
  const { mock, store, s } = await neu({ xhr: 'manuell' });
  const p = store.hochladen([new File([new Uint8Array(4)], 'a.mp3')]);
  await mock.tick();
  const id = s.uploads[0].id;
  mock.xhrs[0].netzfehler(); await p;
  assert.equal(s.uploads[0].zustand, 'unklar');
  mock.emit('upload', 'fortschritt', { upload_id: id, zustand: 'fertig', bytes: 4, code: null, datei: 'a (2).mp3', pruefung: 'warnung' });
  assert.equal(s.uploads[0].zustand, 'fertig');
  assert.equal(s.uploads[0].eingangName, 'a (2).mp3');
  assert.equal(s.uploads[0].pruefung, 'warnung');
  assert.equal(s.uploads[0].text, null);
  mock.emit('upload', 'fortschritt', { upload_id: 'fremd', zustand: 'fertig', bytes: 1, code: null, datei: 'x.mp3', pruefung: 'ok' }); // fremder Upload
  assert.equal(s.uploads.length, 1);
});

test('Ereignis „Upload fertig“ ohne die Fähigkeit wird für den Zustand nicht benutzt', async () => {
  const { mock, store, s } = await alt({ xhr: 'manuell' });
  const p = store.hochladen([new File([new Uint8Array(4)], 'a.mp3')]);
  await mock.tick();
  const id = s.uploads[0].id;
  mock.xhrs[0].netzfehler(); await p;
  mock.emit('upload', 'fortschritt', { upload_id: id, zustand: 'fertig', bytes: 4, code: null, datei: 'a.mp3', pruefung: 'ok' });
  assert.equal(s.uploads[0].zustand, 'unklar');
});

test('Ereignis „Upload fertig“ ändert einen schon fertigen Upload nicht', async () => {
  const { mock, store, s } = await neu({ xhr: 'manuell' });
  const p = store.hochladen([new File([new Uint8Array(4)], 'a.mp3')]);
  await mock.tick();
  mock.xhrs[0].antwort(200, { ...mock.xhrs[0].erfolg(), pruefung: 'warnung', hinweis: 'kopierschutz', eingang_name: 'a.mp3' });
  await p;
  mock.emit('upload', 'fortschritt', { upload_id: s.uploads[0].id, zustand: 'fertig', bytes: 4, code: null, datei: 'anders.mp3', pruefung: 'ok' });
  assert.equal(s.uploads[0].eingangName, 'a.mp3');
  assert.equal(s.uploads[0].pruefung, 'warnung');
});

/* ------------------------------------------------------------------ Erweiterung v1.1: papierkorb/restore mit serie_id */

const korbEintrag = (extra = {}) => ({ id: 'aabbccddeeff', typ: 'folge', serie_id: 'weg', serie_name: 'Alte Serie', folge: 'x.mp3', anzeige: 'Alte Folge', ...extra });

test('Wiederherstellen einer Folge, deren Serie es nicht mehr gibt: Serie wählen, dann serie_id mitsenden', async () => {
  const { mock, store, dialoge } = await neu({}, { serie: 's2' });
  assert.equal(await store.papierkorbWiederherstellen(korbEintrag()), true);
  assert.equal(dialoge.filter((d) => d.k === 'serie').length, 1);
  assert.equal(dialoge.at(-1).nurNormal, true);
  assert.match(dialoge.at(-1).titel, /Alte Folge/);
  assert.deepEqual(sendet(mock, 'tobibox/papierkorb/restore'), [{ eintrag_id: 'aabbccddeeff', serie_id: 's2' }]);
});

test('Wiederherstellen: Abbruch der Serienwahl sendet nichts', async () => {
  const { mock, store } = await neu({}, { serie: null });
  assert.equal(await store.papierkorbWiederherstellen(korbEintrag()), false);
  assert.equal(mock.aufrufe('tobibox/papierkorb/restore').length, 0);
});

test('Wiederherstellen in die alte Serie: keine Frage, kein serie_id', async () => {
  const { mock, store, dialoge } = await neu();
  await store.papierkorbWiederherstellen(korbEintrag({ serie_id: 's1' }));
  assert.equal(dialoge.filter((d) => d.k === 'serie').length, 0);
  assert.deepEqual(sendet(mock, 'tobibox/papierkorb/restore'), [{ eintrag_id: 'aabbccddeeff' }]);
});

test('Wiederherstellen „in andere Serie“ fragt auch dann, wenn die alte Serie noch da ist', async () => {
  const { mock, store, dialoge } = await neu({}, { serie: 's2' });
  await store.papierkorbWiederherstellen(korbEintrag({ serie_id: 's1' }), { andere: true });
  assert.equal(dialoge.filter((d) => d.k === 'serie').length, 1);
  assert.deepEqual(sendet(mock, 'tobibox/papierkorb/restore'), [{ eintrag_id: 'aabbccddeeff', serie_id: 's2' }]);
});

test('Wiederherstellen: meldet das Backend serie_nicht_gefunden, fragt die Seite nach einer Serie und sendet noch einmal', async () => {
  const { mock, store, s, dialoge } = await neu({}, { serie: 's2' });
  s.serien = [...s.serien, { id: 'weg', name: 'Alte Serie', typ: 'normal' }]; // die Seite kennt die Serie noch, das Backend nicht mehr
  mock.backend.papierkorb[0].serie_id = 'weg'; // im Backend ist die Serie weg
  assert.equal(await store.papierkorbWiederherstellen(korbEintrag()), true);
  assert.equal(dialoge.filter((d) => d.k === 'serie').length, 1);
  assert.deepEqual(sendet(mock, 'tobibox/papierkorb/restore'), [{ eintrag_id: 'aabbccddeeff' }, { eintrag_id: 'aabbccddeeff', serie_id: 's2' }]);
  assert.equal(s.fehler, null);
});

test('Wiederherstellen einer Serie oder eines Eingangs-Eintrags fragt nie nach einer Serie', async () => {
  const { mock, store, dialoge } = await neu({}, { serie: 's2' });
  await store.papierkorbWiederherstellen({ id: 'aabbccddeeff', typ: 'serie', serie_id: 'weg', anzeige: 'S' });
  await store.papierkorbWiederherstellen({ id: 'aabbccddeeff', typ: 'eingang', serie_id: null, anzeige: 'E' });
  assert.equal(dialoge.filter((d) => d.k === 'serie').length, 0);
  assert.ok(sendet(mock, 'tobibox/papierkorb/restore').every((m) => !('serie_id' in m)));
});

/* ------------------------------------------------------------------ Abdeckung */

test('Jeder neue Befehl (AP 4.7, v1.1) wurde mit seinen Feldern gegen den Mock gesendet', async () => {
  const gesehen = new Set(mocks.flatMap((m) => m.calls.map((c) => c.type)));
  assert.deepEqual(Object.keys(SCHEMA_V11).filter((t) => !gesehen.has(t)), []);
  assert.ok(mocks.some((m) => m.calls.some((c) => c.type === 'tobibox/zuordnung/list' && 'uid' in c.msg)));
  assert.ok(mocks.some((m) => m.calls.some((c) => c.type === 'tobibox/papierkorb/restore' && 'serie_id' in c.msg)));
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

/* panel.test.mjs richtet das DOM im selben Prozess evtl. schon ein; dann wird es mitbenutzt. */
async function domBereit() {
  if (Element) return;
  if (globalThis.customElements?.get('tobibox-panel')) { Element = globalThis.customElements.get('tobibox-panel'); return; }
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
  const mock = createMockHass({ faehigkeiten: NEU, ...opts });
  const el = new Element();
  document.body.appendChild(el);
  el.store.xhrFactory = mock.xhrFactory;
  el.hass = mock.hass;
  for (let i = 0; i < 6; i++) { await mock.tick(); await el.updateComplete; }
  const flush = async () => { await mock.tick(); await mock.tick(); await el.updateComplete; };
  const tippe = async (feld, wert) => { feld.value = wert; feld.dispatchEvent(new window.Event('input', { bubbles: true })); await flush(); };
  return { el, mock, q: (sel) => el.shadowRoot.querySelector(sel), qa: (sel) => [...el.shadowRoot.querySelectorAll(sel)], flush, tippe };
}

test('Darstellung: Zahnrad für „Einstellungen“ nur mit Fähigkeit; es öffnet den Bereich', MIT_DOM, async () => {
  const mit = await seite();
  const rad = mit.q('header button[aria-label="Einstellungen"]');
  assert.ok(rad, 'Zahnrad in der Kopfzeile');
  rad.click(); await mit.flush(); await mit.flush();
  assert.equal(mit.el.store.s.view, 'einstellungen');
  const t = mit.el.shadowRoot.textContent;
  for (const wort of ['Einstellungen', 'Leise-Zeiten', 'Gute Nacht', 'Lesezeichen', 'Zeitzone', 'Fenster hinzufügen']) assert.match(t, new RegExp(wort), wort);
  assert.equal(mit.q('#zeitzone').value, 'Europe/Berlin');
  assert.equal(mit.q('#timer-min').value, '30');
  assert.equal(mit.q('#ausblenden-s').value, '60');
  assert.equal(mit.q('#lesezeichen-tage').value, '14');
  assert.equal(mit.q('#timer-min').getAttribute('inputmode'), 'numeric'); // Zahlentastatur am Handy
  const ohne = await seite({ faehigkeiten: FAEHIGKEITEN });
  assert.equal(ohne.q('header button[aria-label="Einstellungen"]'), null);
});

test('Darstellung: Speichern ist aus, bis etwas geändert ist; Lesezeichen speichern sendet lesezeichen_tage', MIT_DOM, async () => {
  const { el, mock, q, tippe, flush } = await seite();
  el.store.zeige('einstellungen'); await flush(); await flush();
  assert.equal(q('#lesezeichen-speichern').disabled, true);
  await tippe(q('#lesezeichen-tage'), '0');
  assert.equal(q('#lesezeichen-speichern').disabled, false);
  q('#lesezeichen-speichern').click(); await flush(); await flush();
  assert.deepEqual(sendet(mock, 'tobibox/einstellungen/set'), [{ lesezeichen_tage: 0 }]);
  assert.equal(q('#lesezeichen-speichern').disabled, true);
  assert.match(el.shadowRoot.textContent, /Gespeichert/);
});

test('Darstellung: Gute Nacht eingeben und speichern; ungültiger Wert zeigt Text und sendet nichts', MIT_DOM, async () => {
  const { el, mock, q, tippe, flush } = await seite();
  el.store.zeige('einstellungen'); await flush(); await flush();
  await tippe(q('#timer-min'), '999');
  q('#gute-speichern').click(); await flush();
  assert.equal(mock.aufrufe('tobibox/einstellungen/set').length, 0);
  assert.match(q('.banner.err').textContent, /Timer muss eine ganze Zahl von 1 bis 240/);
  assert.equal(q('.banner.err').getAttribute('role'), 'alert');
  await tippe(q('#timer-min'), '45');
  await tippe(q('#ausblenden-s'), '90');
  q('#gute-speichern').click(); await flush(); await flush();
  assert.deepEqual(sendet(mock, 'tobibox/einstellungen/set'), [{ gute_nacht: { timer_min: 45, ausblenden_s: 90 } }]);
});

test('Darstellung: Leise-Zeiten bauen: Fenster, Wochentage, Zeiten, Wirkung, Grenze, Speichern', MIT_DOM, async () => {
  const { el, mock, q, qa, tippe, flush } = await seite();
  el.store.zeige('einstellungen'); await flush(); await flush();
  assert.equal(qa('.fenster').length, 0);
  assert.match(el.shadowRoot.textContent, /Keine Leise-Zeiten/);
  q('#fenster-neu').click(); await flush();
  assert.equal(qa('.fenster').length, 1);
  const f = q('.fenster');
  assert.equal(f.querySelectorAll('.tag').length, 7);
  assert.deepEqual([...f.querySelectorAll('.tag')].map((b) => b.textContent.trim()), ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']);
  assert.ok([...f.querySelectorAll('.tag')].every((b) => b.getAttribute('aria-pressed') === 'true' && b.getAttribute('aria-label')));
  f.querySelector('[data-tag="7"]').click(); await flush();
  f.querySelector('[data-tag="6"]').click(); await flush();
  assert.equal(q('.fenster [data-tag="7"]').getAttribute('aria-pressed'), 'false');
  assert.match(el.shadowRoot.textContent, /Reicht über Mitternacht/); // 21:00 bis 06:30
  await tippe(q('.fenster .von'), '19:30');
  await tippe(q('.fenster .bis'), '21:00');
  assert.doesNotMatch(el.shadowRoot.textContent, /Reicht über Mitternacht/);
  q('.fenster .wirkung-leiser').click(); await flush();
  assert.equal(q('.fenster .grenze').value, '25');
  await tippe(q('.fenster .grenze'), '35');
  assert.match(el.shadowRoot.textContent, /Höchste Lautstärke: 35 %/);
  await tippe(q('#zeitzone'), 'Europe/Vienna');
  q('#leise-speichern').click(); await flush(); await flush();
  assert.deepEqual(sendet(mock, 'tobibox/einstellungen/set'), [{ leise_zeiten: { zeitzone: 'Europe/Vienna', fenster: [
    { id: 'fenster-1', tage: [1, 2, 3, 4, 5], von: '19:30', bis: '21:00', wirkung: 'leiser', grenze: 35 }] } }]);
  assert.equal(qa('.fenster').length, 1);
  q('.fenster .gefahr').click(); await flush();
  assert.equal(qa('.fenster').length, 0);
  assert.equal(mock.backend.einstellungen.leise_zeiten.fenster.length, 1); // gelöscht ist erst nach „Speichern“
});

test('Darstellung: Wochentage ganz abwählen zeigt „mindestens einen Wochentag“', MIT_DOM, async () => {
  const { el, q, qa, flush } = await seite();
  el.store.zeige('einstellungen'); await flush(); await flush();
  q('#fenster-neu').click(); await flush();
  for (const b of qa('.fenster .tag')) { b.click(); await flush(); }
  q('#leise-speichern').click(); await flush();
  assert.match(q('.banner.err').textContent, /mindestens einen Wochentag/);
});

test('Darstellung: Kurzwahl „Mo–Fr“ und „Sa, So“', MIT_DOM, async () => {
  const { el, q, qa, flush } = await seite();
  el.store.zeige('einstellungen'); await flush(); await flush();
  q('#fenster-neu').click(); await flush();
  const knopf = (text) => qa('.fenster .schnell button').find((b) => b.textContent.trim() === text);
  knopf('Mo–Fr').click(); await flush();
  assert.deepEqual(el.store.leiseAnzeige.fenster[0].tage, [1, 2, 3, 4, 5]);
  knopf('Sa, So').click(); await flush();
  assert.deepEqual(el.store.leiseAnzeige.fenster[0].tage, [6, 7]);
  knopf('Alle').click(); await flush();
  assert.equal(el.store.leiseAnzeige.fenster[0].tage.length, 7);
});

test('Darstellung: für das Handy gebaut – große Tippflächen, Zahlen- und Zeitfelder, kein festes Breitenmaß', MIT_DOM, async () => {
  const { el } = await seite();
  const css = readFileSync(join(HIER, '../../custom_components/tobibox/frontend/tobibox-panel.js'), 'utf8');
  assert.match(css, /input\[type=text\], input\[type=number\], input\[type=time\], select \{ width: 100%; min-height: 48px/);
  assert.match(css, /button \{ min-height: 48px; min-width: 48px/);
  assert.match(css, /\.tage \{ display: flex; gap: 4px/);
  assert.match(css, /\.zeiten \{ display: flex; gap: 12px; \}/);
  assert.doesNotMatch(css.slice(css.indexOf('.fenster {'), css.indexOf('input[type=range]')), /width: \d{3,}px/);
  el.store.zeige('einstellungen');
});

test('Darstellung: gesperrte Konfiguration sperrt die Eingaben und zeigt den Grund', MIT_DOM, async () => {
  const { el, mock, q, qa, flush } = await seite();
  el.store.zeige('einstellungen'); await flush(); await flush();
  mock.backend.konfig = { revision: 7, liste_id: 'x', zustand: 'export_neuer', export_ok: true, export_geschrieben_am: null };
  mock.emit('konfig', 'geaendert', { konfig: mock.backend.konfig });
  await flush(); await flush();
  assert.match(el.shadowRoot.textContent, /Änderungen sind gesperrt/);
  assert.ok(q('#lesezeichen-tage').disabled && q('#timer-min').disabled && q('#fenster-neu').disabled);
  assert.ok(qa('.karte button').filter((b) => b.textContent.trim() === 'Speichern').every((b) => b.disabled));
});

test('Darstellung: Namen im Eingang – „Entfernen“ nur bei Blockiertem und nur mit Fähigkeit', MIT_DOM, async () => {
  const mit = await seite();
  mit.el.store.zeige('eingang'); await mit.flush(); await mit.flush();
  const entf = mit.qa('.karte button.gefahr').filter((b) => b.textContent.trim() === 'Entfernen');
  assert.equal(entf.length, 1);
  const ohne = await seite({ faehigkeiten: FAEHIGKEITEN });
  ohne.el.store.zeige('eingang'); await ohne.flush(); await ohne.flush();
  assert.equal(ohne.qa('.karte button.gefahr').filter((b) => b.textContent.trim() === 'Entfernen').length, 0);
});

test('Darstellung: Papierkorb zeigt bei Folgen „In andere Serie …“', MIT_DOM, async () => {
  const { el, qa, flush } = await seite();
  el.store.zeige('papierkorb'); await flush(); await flush();
  assert.ok(qa('.karte button').some((b) => b.textContent.trim() === 'In andere Serie …'));
  assert.ok(qa('.karte button').some((b) => b.textContent.trim() === 'Wiederherstellen'));
});

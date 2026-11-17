/* Tests der Technik-Karten der Stufe B (Paket B4, Design docs/designs/gehoert.md Abschnitt 7): „Verlauf“ auf der Box-Seite und „Hördaten“ in „Speicher und Netz“.
 * Aufruf: node --test homeassistant/tests/frontend
 *
 * Verlauf: Akku-Kurve aus `recorder/statistics_during_period` mit `akku_entitaet`, Beschreibung und Tabelle, 7 und 30 Tage, Ladevorgänge, Laufzeit je Ladung, verworfene
 * Hördaten, Box ohne Sensor, Fehler. Hördaten: „Als Tabelle sichern“ (signierter Pfad), Löschen mit Anzahl und dem Wort, Rechte, ältere HA ohne die Fähigkeit.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, domBereit, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN, FAEHIGKEITEN_V11, FAEHIGKEITEN_B } from './mock-hass.mjs';

if (MIT_DOM.skip === false) await domBereit(); // die alte Komponente definiert ihr Element nur, wenn das DOM vor dem Laden da ist
const T = await import('../../custom_components/tobibox/frontend/seiten/technik_gehoert.js');
const { TECHNIK } = await import('../../custom_components/tobibox/frontend/texte.js');

const ALLE = [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11, ...FAEHIGKEITEN_B, 'konfig_lesen', 'konfig_staende', 'hoerkopie', 'reinhoeren'];
const OHNE_B = ALLE.filter((f) => !FAEHIGKEITEN_B.includes(f));
const text = (el) => el.textContent.replace(/\s+/g, ' ').trim();
const klick = async (s, el) => { assert.ok(el, 'Element zum Klicken fehlt'); el.click(); await warte(20); await s.flush(12); };
const toasts = (s) => s.qa('.toast .tmsg').map(text);
const z = (wer, serie, folge, tag, stunde, sekunden) => ({ wer, serie, folge, tag, stunde, sekunden, mal: 1, fertig: 0 });

async function technik(hash, opts = {}) {
  const s = await seite({ hash: '#start', faehigkeiten: ALLE, ...opts });
  s.m.backend.akkuEntitaeten = ['sensor.kueche_akku'];
  s.m.backend.boxen[0].akku_entitaet = 'sensor.kueche_akku';
  s.m.backend.boxen[1].akku_entitaet = null;
  s.m.backend.gehoert.zeilen = [z('box:kueche', 's1', 'folge-01.mp3', '2026-11-12', 10, 600), z('box:kinderzimmer', 's1', 'folge-02.mp3', '2026-11-12', 11, 300), z('benutzer:u1', 's2', 'b-01.mp3', '2026-11-11', 8, 900)];
  await geheZu(s, hash);
  await s.flush(14);
  return s;
}

/* ------------------------------------------------------------------ reine Funktionen */

test('datumInZone() und addTage(): Datum JJJJ-MM-TT in der Zeitzone, Tage über Monatsgrenzen', () => {
  assert.equal(T.datumInZone(new Date('2026-11-13T23:30:00Z'), 'Europe/Berlin'), '2026-11-14');
  assert.equal(T.datumInZone(new Date('2026-11-13T23:30:00Z'), 'UTC'), '2026-11-13');
  assert.match(T.datumInZone(new Date(), 'gibt/es-nicht'), /^\d{4}-\d\d-\d\d$/, 'unbekannte Zone: Ortszeit');
  assert.equal(T.addTage('2026-11-13', -6), '2026-11-07');
  assert.equal(T.addTage('2026-03-01', -1), '2026-02-28');
  assert.equal(T.addTage('2026-12-30', 3), '2027-01-02');
  assert.equal(T.tagKurz('2026-11-03'), '3.11.');
  assert.equal(T.tagLang('2026-11-03'), '03.11.2026');
});

test('akkuPunkte(): Zeitstempel in Millisekunden oder ISO, Wert aus mean, sonst max, sonst state; Unbrauchbares fällt weg, aufsteigend, 0 bis 100', () => {
  const l = T.akkuPunkte({ 'sensor.x': [
    { start: 3000, mean: 50 }, { start: '1970-01-01T00:00:01Z', max: 20 }, { start: 2000, state: 120 }, { start: 4000 }, { start: 'kaputt', mean: 5 }, { start: 5000, mean: null, max: -4 },
  ] }, 'sensor.x');
  assert.deepEqual(l, [{ t: 1000, v: 20 }, { t: 2000, v: 100 }, { t: 3000, v: 50 }, { t: 5000, v: 0 }]);
  assert.deepEqual(T.akkuPunkte({}, 'sensor.x'), []);
  assert.deepEqual(T.akkuPunkte(null, 'sensor.x'), []);
});

test('akkuTage(): je Tag niedrigster und höchster Stand', () => {
  const t = (iso, v) => ({ t: Date.parse(iso), v });
  assert.deepEqual(T.akkuTage([t('2026-11-12T08:00:00Z', 90), t('2026-11-12T20:00:00Z', 12), t('2026-11-13T01:00:00Z', 40)], 'UTC'), [{ tag: '2026-11-12', min: 12, max: 90 }, { tag: '2026-11-13', min: 40, max: 40 }]);
});

/* ------------------------------------------------------------------ Karte „Verlauf“ */

test('Verlauf: die Box-Seite hat die Karte mit Akku-Kurve (role="img" mit Beschreibung), Tabelle, Ladevorgängen, Laufzeit und verworfenen Hördaten', MIT_DOM, async () => {
  const s = await technik('#technik-box-kueche');
  const k = s.q('[data-karte="verlauf"]');
  assert.ok(k);
  assert.equal(text(k.querySelector('h3')), 'Verlauf');
  const bild = k.querySelector('[data-diagramm="akku"] svg');
  assert.equal(bild.getAttribute('role'), 'img');
  assert.match(bild.getAttribute('aria-label'), /^Akku der letzten 7 Tage: zwischen \d+ und \d+ Prozent, zuletzt \d+ Prozent\.$/);
  assert.ok(bild.querySelector('polyline.tv-linie').getAttribute('points').split(' ').length > 100, 'eine Stunde je Punkt');
  assert.ok(bild.querySelectorAll('.tv-laden').length >= 1, 'Ladezeiten hinterlegt');
  assert.deepEqual([...k.querySelectorAll('[data-tabelle="akku"] thead th')].map(text), ['Tag', 'niedrigster Stand', 'höchster Stand']);
  assert.ok(k.querySelectorAll('[data-tabelle="akku"] tbody tr').length >= 7);
  assert.deepEqual([...k.querySelectorAll('[data-liste="laden"] thead th')].map(text), ['Beginn', 'Ende', 'Dauer']);
  assert.ok(text(k.querySelector('[data-liste="laden"] tbody tr')).includes('läuft noch'), 'die jüngste Ladung läuft noch');
  assert.deepEqual([...k.querySelectorAll('[data-liste="lauf"] thead th')].map(text), ['Von', 'Bis', 'Dauer']);
  assert.equal(text(k.querySelector('[data-verworfen]')), '3 Einträge der Hördaten gingen auf der Box verloren, weil der Speicher voll war.');
  weg();
});

test('Verlauf: Abfragen: technik/verlauf mit box, von und bis (7 Tage einschließlich heute) und die Statistik der Entität stündlich', MIT_DOM, async () => {
  const s = await technik('#technik-box-kueche');
  const v = s.m.aufrufe('tobibox/technik/verlauf').at(-1);
  assert.equal(v.box, 'kueche');
  assert.match(v.von, /^\d{4}-\d\d-\d\d$/);
  assert.equal((Date.parse(v.bis) - Date.parse(v.von)) / 86400000, 6, 'sieben Tage einschließlich heute');
  const r = s.m.aufrufe('recorder/statistics_during_period').at(-1);
  assert.deepEqual(r.statistic_ids, ['sensor.kueche_akku']);
  assert.equal(r.period, 'hour');
  assert.deepEqual(r.types, ['mean', 'min', 'max']);
  assert.ok(Math.abs(Date.parse(r.end_time) - Date.parse(r.start_time) - 7 * 86400000) < 1000);
  weg();
});

test('Verlauf: „30 Tage“ holt Verlauf und Statistik neu; Ladevorgänge zuerst acht Zeilen, „Alle zeigen“ den Rest', MIT_DOM, async () => {
  const s = await technik('#technik-box-kueche');
  assert.equal(s.qa('[data-liste="laden"] tbody tr').length, 7);
  assert.equal(s.q('[data-liste-mehr="laden"]'), null);
  await klick(s, s.q('[data-karte="verlauf"] [data-wert="30"]'));
  assert.equal(s.q('[data-karte="verlauf"] [data-wert="30"]').getAttribute('aria-pressed'), 'true');
  const v = s.m.aufrufe('tobibox/technik/verlauf').at(-1);
  assert.equal((Date.parse(v.bis) - Date.parse(v.von)) / 86400000, 29);
  assert.match(s.q('[data-diagramm="akku"] svg').getAttribute('aria-label'), /^Akku der letzten 30 Tage/);
  assert.equal(s.qa('[data-liste="laden"] tbody tr').length, 8);
  await klick(s, s.q('[data-liste-mehr="laden"]'));
  assert.equal(s.qa('[data-liste="laden"] tbody tr').length, 30);
  assert.equal(text(s.q('[data-liste-mehr="laden"]')), TECHNIK.verlauf.weniger);
  weg();
});

test('Verlauf: eine Box ohne Akku-Sensor zeigt einen Satz statt der Kurve und fragt die Statistik nicht ab', MIT_DOM, async () => {
  const s = await technik('#technik-box-kinderzimmer');
  assert.equal(text(s.q('[data-akku-keine]')), TECHNIK.verlauf.akku_keine);
  assert.equal(s.q('[data-diagramm="akku"]'), null);
  assert.equal(s.m.aufrufe('recorder/statistics_during_period').length, 0);
  assert.ok(s.q('[data-liste="laden"]'), 'der Rest der Karte bleibt');
  weg();
});

test('Verlauf: schließt der Recorder den Sensor aus (keine Werte) oder scheitert die Abfrage, fehlt nur die Kurve, es gibt keine Fehlerkarte', MIT_DOM, async () => {
  const leer = await technik('#technik-box-kueche', { });
  leer.m.backend.akkuEntitaeten = [];
  leer.el._seiten.technik.verlauf.laden(leer.m.backend.boxen[0]);
  await warte(30); await leer.flush(12);
  assert.equal(text(leer.q('[data-akku-leer]')), TECHNIK.verlauf.akku_leer);
  assert.equal(leer.q('[data-karte="verlauf"] .note.err'), null);
  weg();
  const fehl = await technik('#technik-box-kueche');
  fehl.m.failNext('recorder/statistics_during_period', 'unknown_error');
  fehl.el._seiten.technik.verlauf.laden(fehl.m.backend.boxen[0]);
  await warte(30); await fehl.flush(12);
  assert.ok(fehl.q('[data-akku-leer]'));
  assert.equal(fehl.q('[data-karte="verlauf"] .note.err'), null);
  weg();
});

test('Verlauf: scheitert technik/verlauf, steht die Fehlerkarte in der Karte', MIT_DOM, async () => {
  const s = await seite({ hash: '#start', faehigkeiten: ALLE });
  s.m.failNext('tobibox/technik/verlauf', 'unknown_error');
  await geheZu(s, '#technik-box-kueche');
  await s.flush(14);
  assert.ok(s.q('[data-karte="verlauf"] .note.err'));
  weg();
});

test('Verlauf: kein Ladevorgang im Zeitraum: „Keine im Zeitraum.“; keine verworfenen Hördaten: eigener Satz', MIT_DOM, async () => {
  const s = await seite({ hash: '#start', faehigkeiten: ALLE });
  s.m.backend.technikVerlauf = { kueche: { ladevorgaenge: [], laufzeiten: [], verbindung: [], syncs: [], fehler: [], verworfen: [], weitere: true } };
  s.m.backend.boxen[0].akku_entitaet = null;
  await geheZu(s, '#technik-box-kueche');
  await s.flush(14);
  const k = s.q('[data-karte="verlauf"]');
  assert.equal(k.querySelectorAll('.muted').length >= 3, true);
  assert.ok(text(k).includes('Keine im Zeitraum.'));
  assert.equal(text(k.querySelector('[data-verworfen]')), TECHNIK.verlauf.verworfen_keine);
  assert.equal(text(k.querySelector('[data-weitere]')), TECHNIK.verlauf.weitere);
  weg();
});

test('Verlauf: ohne die Fähigkeit gehoert (ältere HA) gibt es die Karte nicht und keine Abfrage; Nicht-Administratoren sehen Technik gar nicht', MIT_DOM, async () => {
  const alt = await seite({ hash: '#technik-box-kueche', faehigkeiten: OHNE_B });
  await alt.flush(14);
  assert.equal(alt.q('[data-karte="verlauf"]'), null);
  assert.equal(alt.m.aufrufe('tobibox/technik/verlauf').length, 0);
  weg();
  const user = await seite({ hash: '#technik-box-kueche', faehigkeiten: ALLE, istAdmin: false });
  await user.flush(14);
  assert.ok(user.q('[data-zustand="nur-admin"]'));
  assert.equal(user.q('[data-karte="verlauf"]'), null);
  assert.equal(user.m.aufrufe('tobibox/technik/verlauf').length, 0);
  weg();
});

/* ------------------------------------------------------------------ Karte „Hördaten“ */

test('Hördaten: die Karte steht in „Speicher und Netz“ mit der Auswahl Alle, Boxen, Reinhören, je Box, je Person; ohne die Fähigkeit fehlt sie', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  const k = s.q('[data-karte="hoerdaten"]');
  assert.ok(k);
  assert.equal(text(k.querySelector('h3')), 'Hördaten');
  const opt = [...k.querySelectorAll('[data-quelle] option')].map((o) => [o.value, text(o)]);
  assert.deepEqual(opt, [['alle', 'Alle Hördaten'], ['boxen', 'Alle Boxen'], ['reinhoeren', 'Reinhören am Handy und Computer'], ['box:kueche', 'Box: Küche'], ['box:kinderzimmer', 'Box: Kinderzimmer'], ['benutzer:u1', 'Person: Person A']]);
  assert.equal(text(k.querySelector('label')), 'Welche Daten?');
  assert.deepEqual([...k.querySelectorAll('button')].map(text), ['Als Tabelle sichern', 'Löschen …']);
  weg();
  const alt = await technik('#technik-speicher', { faehigkeiten: OHNE_B });
  assert.equal(alt.q('[data-karte="hoerdaten"]'), null);
  weg();
});

test('Hördaten: „Als Tabelle sichern“ ruft Befehl 53 mit der Quelle und lädt den signierten Pfad', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  const geladen = [];
  s.el._seiten.technik.hoerdaten.download = (u) => geladen.push(u);
  const sel = s.q('[data-quelle]');
  sel.value = 'box:kueche';
  sel.dispatchEvent(new window.Event('change', { bubbles: true }));
  await s.flush(6);
  await klick(s, s.q('[data-aktion="hoerdaten_sichern"]'));
  assert.deepEqual(s.m.aufrufe('tobibox/gehoert/exportieren').map(({ id, type, ...r }) => r), [{ quelle: 'box:kueche' }]);
  assert.equal(geladen.length, 1);
  assert.match(geladen[0], /^\/api\/tobibox\/export\/.*authSig=/);
  assert.deepEqual(toasts(s), ['Die Tabelle wird geladen.']);
  weg();
});

test('Hördaten: Löschen fragt erst mit trocken nach der Anzahl, zeigt „nicht rückgängig“, verlangt das Wort LÖSCHEN und löscht dann', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  const sel = s.q('[data-quelle]');
  sel.value = 'boxen';
  sel.dispatchEvent(new window.Event('change', { bubbles: true }));
  await s.flush(6);
  await klick(s, s.q('[data-aktion="hoerdaten_loeschen"]'));
  assert.deepEqual(s.m.aufrufe('tobibox/gehoert/loeschen').map(({ id, type, ...r }) => r), [{ quelle: 'boxen', trocken: true }], 'erst nur zählen');
  assert.equal(s.m.backend.gehoert.zeilen.length, 3, 'noch nichts gelöscht');
  const blatt = s.q('dialog.blatt[open]');
  assert.equal(blatt.getAttribute('role'), 'alertdialog');
  assert.equal(text(blatt.querySelector('#blatt-t')), 'Hördaten löschen?');
  assert.equal(text(blatt.querySelector('[data-loeschen-zahl]')), 'Es werden 2 Einträge gelöscht: Alle Boxen. Das lässt sich nicht rückgängig machen.');
  assert.ok(text(blatt).includes('LÖSCHEN'));
  const ja = () => [...s.qa('dialog.blatt[open] .knoepfe button')].find((b) => b.textContent.trim() === 'Endgültig löschen');
  assert.equal(ja().disabled, true);
  const feld = s.q('#tv-wort');
  feld.value = 'loeschn'; feld.dispatchEvent(new window.Event('input', { bubbles: true }));
  await s.flush(6);
  assert.equal(ja().disabled, true, 'ein falsches Wort schaltet nicht frei');
  feld.value = 'löschen'; feld.dispatchEvent(new window.Event('input', { bubbles: true }));
  await s.flush(6);
  assert.equal(ja().disabled, false, 'Groß- und Kleinschreibung ist egal');
  await klick(s, ja());
  assert.deepEqual(s.m.aufrufe('tobibox/gehoert/loeschen').slice(1).map(({ id, type, ...r }) => r), [{ quelle: 'boxen', bestaetigung: 'LÖSCHEN' }]);
  assert.equal(s.m.backend.gehoert.zeilen.length, 1, 'nur die Person bleibt');
  assert.equal(s.q('dialog.blatt[open]'), null);
  assert.deepEqual(toasts(s), ['2 Einträge gelöscht.']);
  weg();
});

test('Hördaten: „Abbrechen“ löscht nichts; ohne Einträge steht „Da ist nichts zu löschen.“ ohne Blatt', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  await klick(s, s.q('[data-aktion="hoerdaten_loeschen"]'));
  await klick(s, [...s.qa('dialog.blatt[open] .knoepfe button')].find((b) => b.textContent.trim() === 'Abbrechen'));
  assert.equal(s.m.aufrufe('tobibox/gehoert/loeschen').length, 1, 'nur die Zählung');
  assert.equal(s.m.backend.gehoert.zeilen.length, 3);
  s.m.backend.gehoert.zeilen = [];
  await klick(s, s.q('[data-aktion="hoerdaten_loeschen"]'));
  assert.equal(s.q('dialog.blatt[open]'), null);
  assert.deepEqual(toasts(s), ['Da ist nichts zu löschen.']);
  weg();
});

test('Hördaten: eine Quelle, die es nicht mehr gibt (wer_ungueltig), zeigt den Text aus texte.js', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  s.m.failNext('tobibox/gehoert/loeschen', 'wer_ungueltig');
  await klick(s, s.q('[data-aktion="hoerdaten_loeschen"]'));
  assert.ok(s.qa('.toast.err .tmsg').some((t) => text(t) === 'Diese Auswahl gibt es nicht mehr. Die Ansicht ist neu geladen.'));
  assert.equal(s.q('dialog.blatt[open]'), null);
  weg();
});

test('verworfenImZeitraum(): Summe der Zuwächse, Rücksetzer auf 0 zählt den neuen Wert, der erste Eintrag mindestens 1, ohne Einträge 0', () => {
  const l = (...v) => v.map((gesamt) => ({ gesamt }));
  assert.equal(T.verworfenImZeitraum([]), 0);
  assert.equal(T.verworfenImZeitraum(undefined), 0);
  assert.equal(T.verworfenImZeitraum(l(40)), 1);
  assert.equal(T.verworfenImZeitraum(l(2, 5, 9)), 7);
  assert.equal(T.verworfenImZeitraum(l(10, 14, 3, 5)), 4 + 3 + 2, 'nach dem Rücksetzer zählt 3 als Zuwachs');
  assert.equal(T.verworfenImZeitraum(l(10, 0, 2)), 0 + 2 === 2 ? 2 : 0, 'Rücksetzer auf 0');
});

test('Verlauf: die Achsenbeschriftung der Kurve steht in der Zeitzone von HA, wie Tabelle und akkuTage', MIT_DOM, async () => {
  const s = await seite({ hash: '#start', faehigkeiten: ALLE });
  s.m.hass.config = { time_zone: 'Pacific/Auckland' };
  s.m.backend.akkuEntitaeten = ['sensor.kueche_akku'];
  s.m.backend.boxen[0].akku_entitaet = 'sensor.kueche_akku';
  await geheZu(s, '#technik-box-kueche');
  await s.flush(14);
  const r = s.m.aufrufe('recorder/statistics_during_period').at(-1);
  const t0 = Math.floor(Date.parse(r.start_time) / 3600000) * 3600000;
  const erste = [...s.qa('[data-diagramm="akku"] text.tv-ax:not(.tv-ay)')].map(text).slice(1);
  assert.equal(erste[0], T.tagKurz(T.datumInZone(new Date(t0), 'Pacific/Auckland')));
  weg();
});

test('Hördaten: wer_ungueltig lädt die Quellenliste neu und setzt die Auswahl auf „Alle“', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  const sel = s.q('[data-quelle]');
  sel.value = 'box:kueche';
  sel.dispatchEvent(new window.Event('change', { bubbles: true }));
  await s.flush(6);
  const n = s.m.aufrufe('tobibox/gehoert/zusammenfassung').length;
  s.m.failNext('tobibox/gehoert/loeschen', 'wer_ungueltig');
  await klick(s, s.q('[data-aktion="hoerdaten_loeschen"]'));
  assert.equal(s.q('[data-quelle]').value, 'alle');
  assert.equal(s.m.aufrufe('tobibox/gehoert/zusammenfassung').length, n + 1, 'Quellenliste neu geladen');
  weg();
});

test('Technik: verlässt man die Box-Seite, bevor die Boxen da sind, startet kein Verlauf mehr', MIT_DOM, async () => {
  const s = await seite({ hash: '#start', faehigkeiten: ALLE });
  const alt = s.m.hass.connection.sendMessagePromise;
  s.m.hass.connection.sendMessagePromise = async (m) => { if (m.type === 'tobibox/boxen/list') await warte(80); return alt(m); };
  await geheZu(s, '#technik-box-kueche');
  await geheZu(s, '#start');
  await warte(200); await s.flush(10);
  assert.equal(s.m.aufrufe('tobibox/technik/verlauf').length, 0);
  assert.equal(s.m.aufrufe('recorder/statistics_during_period').length, 0);
  weg();
});

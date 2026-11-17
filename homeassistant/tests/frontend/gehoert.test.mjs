/* Tests der Unterseite „Gehört“ und der Zeile auf „Geräte“ (Stufe B, Paket B4, Design docs/designs/gehoert.md Abschnitt 7). Aufruf: node --test homeassistant/tests/frontend
 *
 * Reine Funktionen (Hörzeit, Raster, Achse, Sätze), Weg von „Geräte“, Umleitung ohne Fähigkeit, Auswahl „Wer?“, Zeitraum, Rangliste, Aufteilung nach Folgen,
 * Diagramme mit Beschreibung und Tabelle, leere Zustände, Fehler und das Ereignis `gehoert`. Backend: mock-hass.mjs mit Hördaten (`backend.gehoert.zeilen`).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN, FAEHIGKEITEN_V11, FAEHIGKEITEN_B } from './mock-hass.mjs';

const G = await import('../../custom_components/tobibox/frontend/seiten/gehoert.js');
const { GEHOERT, SEITE, fehlerText } = await import('../../custom_components/tobibox/frontend/texte.js');
const { parseRoute } = await import('../../custom_components/tobibox/frontend/tobibox-app.js');

const ALLE = [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11, ...FAEHIGKEITEN_B, 'reinhoeren'];
const z = (wer, serie, folge, tag, stunde, sekunden, mal = 1, fertig = 0) => ({ wer, serie, folge, tag, stunde, sekunden, mal, fertig });
/* „Heute“ im Mock ist der 13.11.2026 (Freitag). Woche = 07. bis 13.11. */
const DATEN = [
  z('box:kueche', 's1', 'folge-01.mp3', '2026-11-13', 19, 1800, 1, 1),
  z('box:kueche', 's1', 'folge-02.mp3', '2026-11-12', 19, 600),
  z('box:kueche', 's2', 'b-01.mp3', '2026-11-11', 8, 900),
  z('box:kinderzimmer', 's1', 'folge-01.mp3', '2026-11-13', 8, 300),
  z('benutzer:u1', 's1', 'folge-03.mp3', '2026-11-10', 15, 1200, 1, 1),
  z('box:kueche', 'weg', 'x.mp3', '2026-11-09', 9, 100),
  z('box:kueche', 's2', 'b-01.mp3', '2026-09-20', 18, 5400), // nur in „Monat“ nicht, in „Jahr“ und „Alles“ ja
];

async function gehoert({ zeilen = DATEN, hash = '#gehoert', ...opts } = {}) {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start', ...opts });
  s.m.backend.gehoert.zeilen = structuredClone(zeilen);
  s.m.backend.boxen[0].anzeige = 'Box 1'; s.m.backend.boxen[1].anzeige = 'Box 2';
  await geheZu(s, hash);
  await s.flush(12);
  s.seite = s.el._seiten.gehoert;
  return s;
}
const klick = async (s, el) => { el.click(); await warte(20); await s.flush(12); };
const text = (el) => el.textContent.replace(/\s+/g, ' ').trim();
const abfragen = (s) => s.m.aufrufe('tobibox/gehoert/zusammenfassung').map(({ id, type, ...r }) => r);

/* ------------------------------------------------------------------ reine Funktionen */

test('hoerzeit(): Sekunden, Minuten und „9:48 Std.“, Rundung ohne „60 Min.“', () => {
  assert.equal(G.hoerzeit(0), '0 Min.');
  assert.equal(G.hoerzeit(45), '45 Sek.');
  assert.equal(G.hoerzeit(59.6), '1 Min.');
  assert.equal(G.hoerzeit(26 * 60), '26 Min.');
  assert.equal(G.hoerzeit(3600 - 20), '1:00 Std.');
  assert.equal(G.hoerzeit(9 * 3600 + 48 * 60), '9:48 Std.');
  assert.equal(G.hoerzeit(10 * 3600 + 5 * 60 + 29), '10:05 Std.');
  assert.equal(G.hoerzeit(undefined), '0 Min.');
  assert.equal(G.hoerzeitSatz(9 * 3600 + 53 * 60), '9 Std. 53 Min.');
});

test('rasterBeschriftung(): Wochentag und Datum, Kalenderwoche, Monat, Uhrzeit', () => {
  assert.deepEqual(G.rasterBeschriftung('tag', '2026-11-13'), { a: 'Fr', b: '13.11.', lang: 'Fr, 13.11.2026' });
  assert.deepEqual(G.rasterBeschriftung('tag', '2026-11-09'), { a: 'Mo', b: '9.11.', lang: 'Mo, 09.11.2026' });
  assert.deepEqual(G.rasterBeschriftung('woche', '2026-W46'), { a: 'KW 46', b: '', lang: 'KW 46 2026' });
  assert.deepEqual(G.rasterBeschriftung('monat', '2026-03'), { a: 'März', b: '26', lang: 'März 2026' });
  assert.equal(G.rasterBeschriftung('stunde', 19).lang, '19 Uhr');
});

test('achse(): höchstens vier Teilstriche mit runden Schritten, nie unter dem größten Wert', () => {
  assert.deepEqual(G.achse(0), { schritt: 5, max: 5 });
  assert.deepEqual(G.achse(74), { schritt: 20, max: 80 });
  assert.deepEqual(G.achse(90), { schritt: 30, max: 90 });
  assert.deepEqual(G.achse(180), { schritt: 60, max: 180 });
  assert.deepEqual(G.achse(7000), { schritt: 1800, max: 7200 });
  for (const m of [0, 1, 7, 33, 61, 119, 241, 500, 1700]) assert.ok(G.achse(m).max >= m && G.achse(m).max / G.achse(m).schritt <= 4, `Achse für ${m}`);
});

test('beschriftete(): bei sieben alle, sonst immer die letzte und zurück im gleichen Abstand; Stunden ab 0', () => {
  assert.deepEqual([...G.beschriftete(7)].sort((a, b) => a - b), [0, 1, 2, 3, 4, 5, 6]);
  assert.deepEqual([...G.beschriftete(30)].sort((a, b) => a - b), [4, 9, 14, 19, 24, 29]);
  assert.ok(G.beschriftete(53).has(52));
  assert.deepEqual([...G.beschriftete(24, 3, true)], [0, 3, 6, 9, 12, 15, 18, 21]);
});

test('summenJeQuelle(), reiheAufRaster(), tagSatz(): „In den letzten 7 Tagen: 9 Std. 53 Min. (Box 1 …, Box 2 …, …)“', () => {
  const auswahl = [{ wer: 'box:a', name: 'Box 1' }, { wer: 'box:b', name: 'Box 2' }, { wer: 'benutzer:u1', name: 'Person A' }, { wer: 'benutzer:u2', name: 'Person B' }];
  const zeilen = [
    { tag: 'd1', wer: 'box:a', sekunden: 3600 }, { tag: 'd1', wer: 'box:b', sekunden: 0 }, { tag: 'd1', wer: 'benutzer:u1', sekunden: 600 },
    { tag: 'd2', wer: 'box:a', sekunden: 1800 }, { tag: 'd2', wer: 'box:b', sekunden: 900 }, { tag: 'd2', wer: 'benutzer:u2', sekunden: 60 },
  ];
  const je = G.summenJeQuelle(zeilen, auswahl);
  assert.deepEqual(je.map((x) => [x.name, x.sekunden]), [['Box 1', 5400], ['Box 2', 900], ['Person A', 600], ['Person B', 60]]);
  const r = G.reiheAufRaster(zeilen, 'tag');
  assert.deepEqual(r.map((x) => [x.wert, x.sekunden]), [['d1', 4200], ['d2', 2760]]);
  assert.equal(r[0].je.get('box:a'), 3600);
  assert.equal(G.tagSatz('woche', 6960, je.slice(0, 2)), 'In den letzten 7 Tagen: 1 Std. 56 Min. (Box 1 1 Std. 30 Min., Box 2 15 Min.).');
  assert.equal(G.tagSatz('woche', 6960, je), 'In den letzten 7 Tagen: 1 Std. 56 Min. (Box 1 1 Std. 30 Min., Box 2 15 Min., Person A 10 Min., …).');
  assert.equal(G.tagSatz('monat', 600), 'In den letzten 30 Tagen: 10 Min.');
  assert.equal(G.tagSatz('jahr', 600), 'Im letzten Jahr: 10 Min.');
  assert.equal(G.tagSatz('alles', 600), 'Insgesamt: 10 Min.');
  assert.equal(G.stundenSatz([{ stunde: 7, sekunden: 60 }, { stunde: 19, sekunden: 600 }, { stunde: 20, sekunden: 100 }]), 'Am meisten um 19 Uhr.');
  assert.equal(G.stundenSatz([{ stunde: 7, sekunden: 0 }]), GEHOERT.stunde.satz_keine);
});

test('aufteilungZeilen(): alle heutigen Folgen in der Reihenfolge der Serie, nicht gehörte mit 0, gehörte Folgen, die es nicht mehr gibt, am Ende', () => {
  const serie = { folgen: [{ name: 'a.mp3', anzeige: 'Eins' }, { name: 'b.mp3', anzeige: 'Zwei' }, { name: 'c.mp3' }] };
  const l = G.aufteilungZeilen([{ folge: 'b.mp3', sekunden: 120, mal: 2, fertig: 1 }, { folge: 'alt.mp3', sekunden: 60, mal: 1, fertig: 0 }], serie);
  assert.deepEqual(l.map((x) => [x.anzeige, x.sekunden, x.mal, x.fertig, x.gehoert]), [['Eins', 0, 0, 0, false], ['Zwei', 120, 2, 1, true], ['c.mp3', 0, 0, 0, false], ['alt.mp3', 60, 1, 0, true]]);
  assert.deepEqual(G.aufteilungZeilen([{ folge: 'x', sekunden: 5, mal: 1, fertig: 0 }], null).map((x) => x.name), ['x'], 'ohne serie/get nur die gehörten');
});

/* ------------------------------------------------------------------ Weg zur Seite, Fähigkeit */

test('Route: #gehoert gilt mit der Fähigkeit und führt ohne sie auf „Geräte“ (ältere HA)', () => {
  assert.equal(parseRoute('#gehoert', { faehigkeiten: ['gehoert'] }).seite, 'gehoert');
  assert.equal(parseRoute('#gehoert', { faehigkeiten: ['gehoert'] }).zurueck, 'geraete');
  assert.equal(parseRoute('#gehoert', { faehigkeiten: ['bibliothek'] }).umleitung, 'geraete');
});

test('Geräte: die Zeile „Wer hat was gehört?“ steht ganz unten, nur mit der Fähigkeit, und öffnet #gehoert', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#geraete' });
  await s.flush(10);
  const zeile = s.q('[data-gehoert-link]');
  assert.ok(zeile);
  assert.equal(text(zeile), 'Wer hat was gehört?');
  assert.equal(zeile.getAttribute('href'), '#gehoert');
  const nachZeile = [...s.q('main').children].slice(-1)[0];
  assert.equal(nachZeile, zeile, 'die Zeile ist das letzte Element der Seite');
  await klick(s, zeile);
  assert.equal(window.location.hash, '#gehoert');
  weg();
  const alt = await seite({ faehigkeiten: [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11], hash: '#geraete' });
  await alt.flush(10);
  assert.equal(alt.q('[data-gehoert-link]'), null, 'ohne gehoert keine Zeile');
  weg();
});

test('Ältere HA: #gehoert öffnet nicht, die Adresse wird auf #geraete umgeschrieben', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11], hash: '#gehoert' });
  await s.flush(12);
  assert.equal(window.location.hash, '#geraete');
  assert.equal(s.q('[data-gehoert]'), null);
  weg();
});

/* ------------------------------------------------------------------ die Seite */

test('Gehört: drei Abfragen (Rangliste, Zeitreihe mit Quellen, Stunden) für „Alle“ und „Woche“; Überschrift und Weg zurück', MIT_DOM, async () => {
  const s = await gehoert();
  assert.equal(text(s.q('main h2')), 'Gehört');
  assert.equal(s.q('a.back').getAttribute('href'), '#geraete');
  assert.equal(text(s.q('a.back')), SEITE.zurueck.geraete);
  assert.deepEqual(abfragen(s), [
    { wer: 'alle', zeitraum: 'woche', nach: ['serie'], limit: 50 },
    { wer: 'alle', zeitraum: 'woche', nach: ['tag', 'wer'] },
    { wer: 'alle', zeitraum: 'woche', nach: ['stunde'] },
  ]);
  weg();
});

test('Gehört: Auswahl „Wer?“ als Knopfgruppe: Alle, Alle Boxen, je Box, je Person; aria-pressed, sichtbare Beschriftung', MIT_DOM, async () => {
  const s = await gehoert();
  const gruppe = s.q('[data-wer]');
  assert.equal(gruppe.getAttribute('role'), 'group');
  assert.equal(s.q(`#${gruppe.getAttribute('aria-labelledby')}`).textContent, 'Wer?');
  const knoepfe = s.qa('[data-wer-knopf]');
  assert.deepEqual(knoepfe.map((b) => [b.dataset.werKnopf, text(b), b.getAttribute('aria-pressed')]), [
    ['alle', 'Alle', 'true'], ['alle_boxen', 'Alle Boxen', 'false'], ['box:kueche', 'Box 1', 'false'], ['box:kinderzimmer', 'Box 2', 'false'], ['benutzer:u1', 'Person A', 'false'],
  ]);
  await klick(s, s.q('[data-wer-knopf="box:kueche"]'));
  assert.equal(s.q('[data-wer-knopf="box:kueche"]').getAttribute('aria-pressed'), 'true');
  assert.equal(s.q('[data-wer-knopf="alle"]').getAttribute('aria-pressed'), 'false');
  assert.deepEqual(abfragen(s).slice(-3).map((a) => [a.wer, a.nach]), [['box:kueche', ['serie']], ['box:kueche', ['tag']], ['box:kueche', ['stunde']]], 'ohne „Alle“ keine Aufteilung nach Quellen');
  await klick(s, s.q('[data-wer-knopf="alle_boxen"]'));
  assert.equal(abfragen(s).at(-1).wer, 'alle_boxen');
  weg();
});

test('Gehört: Zeitraum Woche · Monat · Jahr · Alles wählt das Raster (Tage, Tage, Wochen, Monate) und die Überschrift', MIT_DOM, async () => {
  const s = await gehoert();
  const fall = [['monat', 'tag', 'Hörzeit pro Tag', 'In den letzten 30 Tagen'], ['jahr', 'woche', 'Hörzeit pro Woche', 'Im letzten Jahr'], ['alles', 'monat', 'Hörzeit pro Monat', 'Insgesamt'], ['woche', 'tag', 'Hörzeit pro Tag', 'In den letzten 7 Tagen']];
  for (const [zr, art, titel, satz] of fall) {
    await klick(s, s.q(`[data-zeitraum] [data-wert="${zr}"]`));
    assert.equal(s.q(`[data-zeitraum] [data-wert="${zr}"]`).getAttribute('aria-pressed'), 'true');
    assert.deepEqual(abfragen(s).slice(-3).map((a) => [a.zeitraum, a.nach]), [[zr, ['serie']], [zr, [art, 'wer']], [zr, ['stunde']]]);
    assert.equal(text(s.q('#gh-tag-t')), titel);
    assert.ok(text(s.q('[data-karte="zeitreihe"] [data-satz]')).startsWith(satz), `${zr}: ${text(s.q('[data-karte="zeitreihe"] [data-satz]'))}`);
  }
  weg();
});

test('Gehört: Rangliste mit Hörzeit · Mal · fertig, nach Hörzeit, gelöschte Einträge als eine Zeile ohne Knopf, volle Namen in der Beschriftung', MIT_DOM, async () => {
  const s = await gehoert();
  const kopf = s.qa('[data-rangliste] thead th').map(text);
  assert.deepEqual(kopf, ['Titel', 'Hörzeit', 'Mal', 'fertig']);
  const zeilen = s.qa('[data-rangliste] tbody tr').map((r) => [...r.children].map(text));
  assert.deepEqual(zeilen, [['Die drei ???', '1:05 Std.', '4', '2/3'], ['Bibi Blocksberg', '15 Min.', '1', '0/1'], ['Gelöscht', '2 Min.', '1', '–']]);
  const knopf = s.q('[data-serie-zeile="s1"]');
  assert.equal(knopf.getAttribute('aria-label'), 'Die drei ???: Hörzeit 1 Std. 5 Min., 4 Mal, fertig 2 von 3. Aufteilung nach Folgen ansehen.');
  assert.equal(s.qa('[data-rangliste] button').length, 2, 'die Sammelzeile „Gelöscht“ ist kein Knopf');
  assert.ok(s.q('[data-zeile-weg]'));
  weg();
});

test('Gehört: die Rangliste zeigt zuerst 10 Zeilen, „Alle … zeigen“ den Rest; „weitere“ bei abgeschnittener Liste', MIT_DOM, async () => {
  const viele = [];
  for (let i = 1; i <= 14; i += 1) viele.push(z('box:kueche', `v${i}`, 'f.mp3', '2026-11-12', 10, 100 + i));
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  for (let i = 1; i <= 14; i += 1) s.m.backend.serien[`v${i}`] = { id: `v${i}`, name: `Hörspiel ${i}`, typ: 'normal', ordner: `v${i}`, pruefen: false, hinweise: [], folgen: [{ name: 'f.mp3', anzeige: 'F', pruefen: false, pruefen_gruende: [], tobies: [], tracks: 1, art: 'datei', groesse_bytes: 1 }] };
  s.m.backend.gehoert.zeilen = viele;
  await geheZu(s, '#gehoert');
  await s.flush(12);
  assert.equal(s.qa('[data-rangliste] tbody tr').length, 10);
  const mehr = s.q('[data-rang-mehr]');
  assert.equal(text(mehr), 'Alle 14 zeigen');
  await klick(s, mehr);
  assert.equal(s.qa('[data-rangliste] tbody tr').length, 14);
  assert.equal(text(s.q('[data-rang-mehr]')), 'Nur die ersten 10 zeigen');
  weg();
});

test('Gehört: ein Tipp auf eine Zeile zeigt die Aufteilung nach Folgen (auch nicht gehörte), Summe, Fokus; „‹ Rangliste“ bringt den Fokus zurück', MIT_DOM, async () => {
  const s = await gehoert();
  await klick(s, s.q('[data-serie-zeile="s1"]'));
  await s.flush(10);
  const letzte = s.m.aufrufe('tobibox/gehoert/zusammenfassung').at(-1);
  assert.deepEqual({ wer: letzte.wer, zeitraum: letzte.zeitraum, serie_id: letzte.serie_id, nach: letzte.nach, limit: letzte.limit }, { wer: 'alle', zeitraum: 'woche', serie_id: 's1', nach: ['folge'], limit: 200 });
  assert.equal(s.m.aufrufe('tobibox/serie/get').at(-1).serie_id, 's1');
  assert.equal(s.q('[data-rangliste]'), null);
  assert.equal(text(s.q('[data-aufteilung-titel]')), 'Aufteilung nach FolgenDie drei ???');
  const zeilen = s.qa('[data-aufteilung] tbody tr').map((r) => [...r.children].map(text));
  assert.deepEqual(zeilen, [['Der Rabe', '35 Min.', '2', '1×'], ['Das Gespensterschloss', '10 Min.', '1', '–'], ['Der Super-Papagei', '20 Min.', '1', '1×']]);
  assert.deepEqual([...s.q('[data-summe]').children].map(text), ['Summe', '1:05 Std.', '4', '2×']);
  assert.equal(s.qa('[data-aufteilung] tr.gh-nie').length, 0);
  assert.equal(s.el.shadowRoot.activeElement?.hasAttribute('data-aufteilung-titel'), true, 'der Fokus steht auf der Überschrift');
  await klick(s, s.q('[data-aufteilung-zurueck]'));
  assert.ok(s.q('[data-rangliste]'));
  assert.equal(s.q('[data-aufteilung]'), null);
  assert.equal(s.el.shadowRoot.activeElement?.dataset.serieZeile, 's1', 'der Fokus ist wieder auf der Zeile');
  weg();
});

test('Gehört: Aufteilung mit einer Folge, die nie gehört wurde: grau (gh-nie) mit 0 · 0 · –', MIT_DOM, async () => {
  const s = await gehoert({ zeilen: [z('box:kueche', 's1', 'folge-02.mp3', '2026-11-12', 10, 300)] });
  await klick(s, s.q('[data-serie-zeile="s1"]'));
  await s.flush(10);
  const zeilen = [...s.qa('[data-aufteilung] tbody tr')].map((r) => [r.className, ...[...r.children].map(text)]);
  assert.deepEqual(zeilen, [['gh-nie', 'Der Rabe', '0', '0', '–'], ['', 'Das Gespensterschloss', '5 Min.', '1', '–'], ['gh-nie', 'Der Super-Papagei', '0', '0', '–']]);
  weg();
});

test('Gehört: Diagramme tragen role="img" mit Beschreibung und haben eine Tabelle; Säulen zählen die Minuten; Zahlen nur bei einer Woche', MIT_DOM, async () => {
  const s = await gehoert();
  const bild = s.q('[data-diagramm="zeitreihe"] svg');
  assert.equal(bild.getAttribute('role'), 'img');
  assert.match(bild.getAttribute('aria-label'), /^Säulendiagramm „Hörzeit pro Tag“\. In den letzten 7 Tagen: 1 Std\. 22 Min\. \(Box 1 57 Min\./);
  assert.equal(s.qa('[data-diagramm="zeitreihe"] .gh-saeule').length, 5, 'ein Tag ohne Hörzeit hat keine Säule (der 7. und 8.)');
  assert.equal(s.qa('[data-diagramm="zeitreihe"] .gh-zahl').length, 7, 'eine Zahl über jedem der 7 Tage');
  assert.deepEqual(s.qa('[data-diagramm="zeitreihe"] .gh-ay').map(text), ['0', '10', '20', '30', '40'], 'größter Tag: 35 Minuten, Schritte zu 10');
  const tabelle = s.q('[data-tabelle="zeitreihe"]');
  assert.equal(tabelle.tagName, 'DETAILS');
  assert.equal(text(tabelle.querySelector('summary')), 'Zahlen als Tabelle');
  assert.deepEqual([...tabelle.querySelectorAll('thead th')].map(text), ['Tag', 'Summe', 'Davon']);
  assert.equal(tabelle.querySelectorAll('tbody tr').length, 7);
  assert.deepEqual([...tabelle.querySelector('tbody tr:last-child').children].map(text), ['Fr, 13.11.2026', '35 Min.', 'Box 1 30 Min. Box 2 5 Min.']);
  assert.ok(tabelle.querySelector('caption.sr'), 'die Tabelle hat eine Beschriftung');
  const std = s.q('[data-diagramm="stunden"] svg');
  assert.equal(std.getAttribute('role'), 'img');
  assert.match(std.getAttribute('aria-label'), /^Säulendiagramm „Tageszeiten“\. Am meisten um 19 Uhr\.$/);
  assert.equal(s.qa('[data-diagramm="stunden"] .gh-saeule').length, 4, 'die Stunden 8, 9, 15 und 19');
  assert.deepEqual(s.qa('[data-diagramm="stunden"] text.gh-ax:not(.gh-ay)').map(text).slice(1), ['0', '3', '6', '9', '12', '15', '18', '21']);
  assert.equal(text(s.q('[data-karte="stunden"] [data-satz]')), 'Am meisten um 19 Uhr.');
  assert.equal(s.qa('[data-tabelle="stunden"] tbody tr').length, 24);
  await klick(s, s.q('[data-zeitraum] [data-wert="monat"]'));
  assert.equal(s.qa('[data-diagramm="zeitreihe"] .gh-zahl').length, 0, 'bei 30 Tagen keine Zahlen über den Säulen');
  weg();
});

test('Gehört: bei einer einzelnen Quelle steht in der Tabelle nur eine Spalte „Hörzeit“, im Satz keine Aufteilung', MIT_DOM, async () => {
  const s = await gehoert();
  await klick(s, s.q('[data-wer-knopf="box:kueche"]'));
  assert.deepEqual([...s.qa('[data-tabelle="zeitreihe"] thead th')].map(text), ['Tag', 'Hörzeit']);
  assert.ok(!text(s.q('[data-karte="zeitreihe"] [data-satz]')).includes('('));
  weg();
});

test('Gehört: Alles zählt in Monaten (lückenlos ab dem Monat der ersten Sitzung)', MIT_DOM, async () => {
  const s = await gehoert();
  await klick(s, s.q('[data-zeitraum] [data-wert="alles"]'));
  const monate = s.qa('[data-tabelle="zeitreihe"] tbody th').map(text);
  assert.deepEqual(monate, ['Sept. 2026', 'Okt. 2026', 'Nov. 2026']);
  assert.equal(s.qa('[data-diagramm="zeitreihe"] .gh-zahl').length, 0);
  weg();
});

test('Gehört: „Was wird gezählt?“ nennt Hörzeit, Pausen bis 30 Minuten, Mal, fertig und doppelte Fenster; nichts von „Handy ungefähr“ (Messung B2a)', MIT_DOM, async () => {
  const s = await gehoert();
  const d = s.q('[data-gezaehlt]');
  assert.equal(d.tagName, 'DETAILS');
  assert.equal(text(d.querySelector('summary')), 'Was wird gezählt?');
  const t = text(d);
  for (const w of ['Hörzeit', '30 Minuten', 'Mal', 'fertig', '10 Sekunden', '80 Prozent', 'zählen doppelt']) assert.ok(t.includes(w), `„${w}“ fehlt`);
  assert.ok(!/ungefähr/i.test(t) && !/gesperrt/i.test(t), 'der Punkt „Handy ungefähr“ entfällt');
  weg();
});

/* ------------------------------------------------------------------ leere Zustände, Fehler, Ereignis */

test('Gehört: noch nie etwas gehört (die Boxen stehen trotzdem in der Auswahl): leerer Zustand mit „Zur Bibliothek“', MIT_DOM, async () => {
  const s = await gehoert({ zeilen: [] });
  const leer = s.q('[data-leer="gehoert"]');
  assert.ok(leer);
  assert.equal(text(leer.querySelector('.et')), 'Noch nichts gehört.');
  assert.equal(leer.querySelector('a.btn').getAttribute('href'), '#bibliothek');
  assert.equal(s.q('[data-wer]'), null);
  assert.equal(s.m.aufrufe('tobibox/gehoert/zusammenfassung').filter((a) => a.zeitraum === 'alles' && a.nach[0] === 'wer').length, 1, 'eine Rückfrage über alles entscheidet über den leeren Zustand');
  weg();
});

test('Gehört: in der Woche nichts, früher schon: die Auswahl bleibt, statt der Diagramme steht ein Satz', MIT_DOM, async () => {
  const s = await gehoert({ zeilen: [z('box:kueche', 's1', 'folge-01.mp3', '2026-08-01', 10, 600)] });
  assert.equal(s.q('[data-leer="gehoert"]'), null);
  assert.ok(s.q('[data-wer]') && s.q('[data-zeitraum]'));
  assert.equal(text(s.q('[data-leer-zeitraum]')), 'In diesem Zeitraum wurde nichts gehört.');
  assert.equal(s.q('[data-rangliste]'), null);
  await klick(s, s.q('[data-zeitraum] [data-wert="alles"]'));
  assert.ok(s.q('[data-rangliste]'), 'in „Alles“ steht der Eintrag');
  weg();
});

test('Gehört: Fehler beim Laden zeigt die Fehlerkarte mit „Noch einmal versuchen“', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  s.m.backend.gehoert.zeilen = structuredClone(DATEN);
  s.m.failNext('tobibox/gehoert/zusammenfassung', 'unknown_error', 'unknown_error', 'unknown_error');
  await geheZu(s, '#gehoert');
  await s.flush(12);
  assert.ok(s.q('.note.err'), 'Fehlerkarte');
  assert.equal(s.q('[data-gehoert]'), null);
  await klick(s, s.q('.note.err button'));
  assert.ok(s.q('[data-gehoert]'), 'nach dem zweiten Versuch steht die Seite da');
  weg();
});

test('Gehört: wer_ungueltig (die Quelle gibt es nicht mehr): zurück auf „Alle“, Meldung mit dem Text aus texte.js', MIT_DOM, async () => {
  const s = await gehoert();
  await klick(s, s.q('[data-wer-knopf="box:kueche"]'));
  s.m.failNext('tobibox/gehoert/zusammenfassung', 'wer_ungueltig');
  s.seite.laden(true);
  await warte(30); await s.flush(12);
  assert.equal(s.q('[data-wer-knopf="alle"]').getAttribute('aria-pressed'), 'true');
  assert.ok(s.qa('.toast.err').some((t) => text(t).includes(fehlerText('wer_ungueltig'))), 'Meldung');
  assert.ok(s.q('[data-gehoert]'));
  weg();
});

test('Gehört: zu viele Zeilen (Zeit × Quellen über 400) bei „Alle“: noch einmal ohne die Aufteilung nach Quellen, die Tabelle hat dann nur „Hörzeit“', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  s.m.backend.gehoert.zeilen = structuredClone(DATEN);
  const alt = s.m.hass.connection.sendMessagePromise;
  s.m.hass.connection.sendMessagePromise = (msg) => (msg.type === 'tobibox/gehoert/zusammenfassung' && msg.nach?.length === 2 ? Promise.reject({ code: 'invalid_format', message: 'mehr als 400 Zeilen' }) : alt(msg));
  await geheZu(s, '#gehoert');
  await s.flush(12);
  assert.ok(s.q('[data-gehoert]'), 'keine Fehlerkarte');
  assert.deepEqual([...s.qa('[data-tabelle="zeitreihe"] thead th')].map(text), ['Tag', 'Hörzeit']);
  assert.ok(!text(s.q('[data-karte="zeitreihe"] [data-satz]')).includes('('));
  weg();
});

test('Gehört: das Ereignis `gehoert` lädt die Seite nach etwa einer Sekunde still neu (gebündelt)', MIT_DOM, async () => {
  const s = await gehoert();
  const n = s.m.aufrufe('tobibox/gehoert/zusammenfassung').length;
  s.m.backend.gehoert.zeilen.push(z('box:kueche', 's2', 'b-01.mp3', '2026-11-13', 10, 3600));
  s.m.emit('gehoert', 'geaendert', {});
  s.m.emit('gehoert', 'geaendert', {});
  await warte(1150); await s.flush(12);
  assert.equal(s.m.aufrufe('tobibox/gehoert/zusammenfassung').length, n + 3, 'ein Neuladen mit drei Abfragen für zwei Ereignisse');
  assert.equal(text(s.q('[data-rangliste] tbody tr td')), 'Bibi Blocksberg', 'die neue Hörzeit steht oben');
  assert.equal(s.q('[data-karte="zeitreihe"] .skel'), null, 'ohne Platzhalter beim stillen Neuladen');
  weg();
});

test('Gehört: nach dem Verlassen der Seite lädt ein Ereignis nichts mehr', MIT_DOM, async () => {
  const s = await gehoert();
  await geheZu(s, '#geraete');
  const n = s.m.aufrufe('tobibox/gehoert/zusammenfassung').length;
  s.m.emit('gehoert', 'geaendert', {});
  await warte(1150); await s.flush(6);
  assert.equal(s.m.aufrufe('tobibox/gehoert/zusammenfassung').length, n);
  weg();
});

test('Gehört: der Mock lehnt die Befehle 50 bis 56 und die Felder spieler/spielt ohne die Fähigkeit ab (ältere HA)', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11, 'reinhoeren'], hash: '#start' });
  for (const t of ['tobibox/gehoert/zusammenfassung', 'tobibox/gehoert/zuletzt', 'tobibox/favoriten/list']) {
    await assert.rejects(() => s.m.hass.connection.sendMessagePromise({ type: t, ...(t.endsWith('zusammenfassung') ? { zeitraum: 'woche', nach: ['serie'] } : {}) }), (e) => e.code === 'unknown_command', t);
  }
  await assert.rejects(() => s.m.hass.connection.sendMessagePromise({ type: 'tobibox/hoerstelle/set', serie_id: 's1', folge: 'folge-01.mp3', position_s: 1, dauer_s: 10, spieler: 'abcdefgh12', spielt: true }), (e) => e.code === 'invalid_format');
  weg();
});

test('Gehört: beim Wechsel des Zeitraums bleibt bis zur Antwort die alte Anzeige mit ihrem alten Raster und Satz (kein „KW NaN“, kein falscher Satz)', MIT_DOM, async () => {
  const s = await gehoert();
  const alt = s.m.hass.connection.sendMessagePromise;
  let frei;
  const tor = new Promise((r) => { frei = r; });
  s.m.hass.connection.sendMessagePromise = async (m) => { if (m.type === 'tobibox/gehoert/zusammenfassung' && m.zeitraum === 'jahr') await tor; return alt(m); };
  s.q('[data-zeitraum] [data-wert="jahr"]').click();
  await warte(30); await s.flush(10);
  assert.equal(s.q('[data-zeitraum] [data-wert="jahr"]').getAttribute('aria-pressed'), 'true');
  assert.equal(text(s.q('#gh-tag-t')), 'Hörzeit pro Tag');
  assert.ok(text(s.q('[data-karte="zeitreihe"] [data-satz]')).startsWith('In den letzten 7 Tagen'));
  assert.ok(!text(s.q('[data-gehoert]')).includes('NaN'));
  frei();
  await warte(30); await s.flush(12);
  assert.equal(text(s.q('#gh-tag-t')), 'Hörzeit pro Woche');
  assert.ok(text(s.q('[data-karte="zeitreihe"] [data-satz]')).startsWith('Im letzten Jahr'));
  assert.ok(!text(s.q('[data-gehoert]')).includes('NaN'));
  weg();
});

test('Gehört: ist die Aufteilung abgeschnitten (`weitere`), steht ein Hinweis unter der Tabelle', MIT_DOM, async () => {
  const s = await gehoert();
  const alt = s.m.hass.connection.sendMessagePromise;
  s.m.hass.connection.sendMessagePromise = async (m) => { const r = await alt(m); return m.type === 'tobibox/gehoert/zusammenfassung' && m.nach?.[0] === 'folge' ? { ...r, weitere: true } : r; };
  await klick(s, s.q('[data-serie-zeile="s1"]'));
  await s.flush(10);
  assert.ok(s.q('[data-karte="aufteilung"] [data-auf-weitere]'));
  weg();
});

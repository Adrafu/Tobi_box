/* Tests der Seiten „Bibliothek“ und „Suche“ (AP A7, Design 5.2). Aufruf: node --test homeassistant/tests/frontend
 *
 * Backend aus mock-hass.mjs mit 130 Einträgen (`viele`): Arten, Sortieren und Filter, endloses Nachladen mit `offset`,
 * Suche mit Vorschlägen (Tobies zuerst), leere Zustände, Fehlerzustand, Rechte (Nicht-Administrator sieht dasselbe).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, mitIO, FakeIO, tippe, taste, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN } from './mock-hass.mjs';

const { listenAnfrage, aktiveEinstellungen, STANDARD } = await import('../../custom_components/tobibox/frontend/seiten/bibliothek.js');
const { vorschlaege } = await import('../../custom_components/tobibox/frontend/seiten/suche.js');
const { LEER, fuellen } = await import('../../custom_components/tobibox/frontend/texte.js');

const ids = (s) => s.qa('.lrow').map((a) => a.dataset.serie);
const zeilen = (s) => s.qa('.lrow');
const aufrufe = (s) => s.m.aufrufe('tobibox/serien/list');
const letzte = (s) => { const { id, type, ...rest } = aufrufe(s).at(-1); return rest; };
const knopf = (s, text) => s.qa('dialog button, main button').find((b) => b.textContent.trim().startsWith(text));
const anzahlTobies = (s, id) => Object.values(s.m.backend.zuordnungen).filter((z) => z.ziel.serie === id).length;

async function bibliothek(opts = {}) {
  const s = await seite({ viele: true, hash: '#bibliothek', ...opts });
  await s.flush(10);
  return s;
}

/* ------------------------------------------------------------------ reine Funktionen */

test('listenAnfrage und aktiveEinstellungen: Eingabe für serien/list nach Vertrag 14.2', () => {
  const e = STANDARD();
  assert.deepEqual(listenAnfrage(e), { sortierung: 'name', limit: 60, offset: 0 });
  assert.equal(aktiveEinstellungen(e), 0);
  e.art = 'musik'; e.sortierung = 'neu'; e.typ = 'einzeln'; e.filter.ohne_tobie = true; e.filter.pruefen = true;
  assert.deepEqual(listenAnfrage(e, 120), { art: 'musik', sortierung: 'neu', filter: ['einzeln', 'ohne_tobie', 'pruefen'], limit: 60, offset: 120 });
  assert.equal(aktiveEinstellungen(e), 4, 'Sortierung, Was zeigen und zwei Filter; die Art zählt nicht');
});

test('vorschlaege(): Wortanfang oder Wortbeginn, Tobies zuerst, ohne den Begriff selbst und ohne Doppelte, höchstens fünf', () => {
  const daten = {
    tobies: [{ name: 'Drache' }, { name: null }, { name: 'Drache' }, { name: 'Der Drache' }],
    sammlungen: [{ name: 'Drachenreise' }, { name: 'Kleiner Drache Funk' }, { name: 'Bandwurm' }],
    folgen: [{ anzeige: 'Das Drachenfest' }, { folge: 'drachenei.mp3' }, { anzeige: 'Drachenzahn' }],
  };
  const v = vorschlaege('dra', daten);
  assert.deepEqual(v.map((x) => x.text), ['Drache', 'Der Drache', 'Drachenreise', 'Kleiner Drache Funk', 'Das Drachenfest']);
  assert.deepEqual(v.map((x) => x.art), ['tobie', 'tobie', 'serie', 'serie', 'folge']);
  assert.deepEqual(vorschlaege('Drache', daten).map((x) => x.text).includes('Drache'), false, 'der Begriff selbst ist kein Vorschlag');
  assert.deepEqual(vorschlaege('ache', daten), [], 'mitten im Wort zählt nicht');
  assert.equal(vorschlaege('mud', { sammlungen: [{ name: 'Müde Füchse' }] })[0].text, 'Müde Füchse', 'Umlaute egal');
  assert.equal(vorschlaege('dra', daten, 2).length, 2);
});

/* ------------------------------------------------------------------ Bibliothek: Aufbau */

test('Bibliothek: Zeile „Bibliothek“ mit Lupe und „+“, Arten-Zeile ohne Playlists, keine Reihen, Zählzeile, Platz für das Band', MIT_DOM, async () => {
  const s = await bibliothek();
  assert.equal(s.q('main h2').textContent, 'Bibliothek');
  const lupe = s.q('main a[aria-label="Suchen"]');
  assert.equal(lupe.getAttribute('href'), '#suche');
  const plus = s.q('main a[aria-label="Hinzufügen"]');
  assert.equal(plus.getAttribute('href'), '#hinzufuegen');
  assert.ok(plus.classList.contains('fillp'), 'das „+“ ist gefüllt');
  assert.deepEqual(s.qa('.artrow button').map((b) => b.textContent), ['Alle', 'Hörspiele', 'Hörbücher', 'Musik', 'Geschichten']);
  assert.deepEqual(s.qa('.artrow button').map((b) => b.getAttribute('aria-pressed')), ['true', 'false', 'false', 'false', 'false']);
  assert.ok(!s.q('.artrow').textContent.includes('Playlists'), 'Playlists erst in Stufe C');
  assert.equal(s.qa('.hscroll').length, 0, 'keine Reihen in der Bibliothek');
  assert.ok(!s.q('main').textContent.includes('Neu hinzugefügt'));
  assert.equal(s.q('.count').textContent, '130 Einträge');
  assert.equal(s.q('.count').getAttribute('aria-live'), 'polite');
  assert.equal(s.q('button[data-sortieren]').textContent.trim(), 'Sortieren und Filter');
  assert.equal(s.q('.nbadge'), null);
  // Platz für das Upload-Band: ohne Uploads nichts, A11 hängt sich an ctx.uploadBand
  assert.equal(s.q('.testband'), null);
  s.el.ctx.uploadBand = () => { const d = document.createElement('div'); d.className = 'testband'; return d; };
  s.el.requestUpdate(); await s.flush();
  const band = s.q('.testband');
  assert.ok(band && band.compareDocumentPosition(s.q('.libhead')) & 4, 'das Band steht über der Zeile „Bibliothek“');
  weg();
});

test('Bibliothek: die erste Seite sind 60 Zeilen nach Name; Anfrage mit sortierung, limit und offset', MIT_DOM, async () => {
  const s = await bibliothek();
  assert.equal(zeilen(s).length, 60);
  assert.deepEqual(letzte(s), { sortierung: 'name', limit: 60, offset: 0 });
  const namen = s.qa('.lrow .lt').map((x) => x.textContent);
  assert.deepEqual(namen, [...namen].sort((a, b) => a.localeCompare(b, 'de', { numeric: true })), 'A bis Z');
  weg();
});

test('Bibliothek: Zeile mit Cover, Titel, Untertitel (Art · Anzahl · Dauer), Fortschritt, Marke und Tobie-Symbol aus den Daten', MIT_DOM, async () => {
  const s = await bibliothek();
  const b = s.m.backend.serien;
  let mitDauer = 0; let mitFortschritt = 0; let mitMarke = 0; let mitTobie = 0;
  for (const z of zeilen(s)) {
    const d = b[z.dataset.serie];
    assert.equal(z.getAttribute('href'), `#serie-${d.id}`, 'die ganze Zeile ist ein Link zur Serienseite');
    assert.ok(z.querySelector('.cover.lr'), 'Cover links, 72 px');
    assert.equal(z.querySelector('.lt').textContent, d.name);
    const sub = z.querySelector('.ls').textContent;
    if (d.einzeln) assert.match(sub, /^(Lied|Geschichte) · einzeln( · \d+:\d\d(:\d\d)?)?$/);
    else if (d.art === 'hoerspiel') assert.match(sub, new RegExp(`^Hörspiel · ${d.folgen.length} ${d.folgen.length === 1 ? 'Folge' : 'Folgen'}`));
    else if (d.art === 'hoerbuch') assert.match(sub, new RegExp(`^Hörbuch · ${d.kapitel_anzahl} Kapitel`));
    else if (d.art === 'musik') assert.match(sub, new RegExp(`^Musik · ${d.folgen.length} Lieder`));
    else assert.match(sub, new RegExp(`^${d.folgen.length} Geschichten`));
    assert.equal(/Min\.|Std\./.test(sub), d.dauer_s !== null && !d.einzeln ? true : /Min\.|Std\./.test(sub) && false, 'Dauer nur, wenn das Backend sie kennt');
    if (d.dauer_s !== null) mitDauer += 1;
    const balken = z.querySelector('.pbar');
    assert.equal(!!balken, !!d.hoerstelle, 'Fortschrittsbalken nur bei angehörten Einträgen');
    if (d.hoerstelle) {
      mitFortschritt += 1;
      assert.equal(balken.getAttribute('role'), 'progressbar');
      assert.equal(Number(balken.getAttribute('aria-valuenow')), Math.round(d.hoerstelle.anteil * 100));
      assert.match(z.textContent, d.hoerstelle.anteil >= 0.999 ? /Fertig gehört/ : /noch \d+ (Min\.|Std\.)/);
    }
    assert.equal(!!z.querySelector('.badge'), d.pruefen);
    if (d.pruefen) { mitMarke += 1; assert.equal(z.querySelector('.badge').textContent, 'bitte ansehen'); }
    const n = anzahlTobies(s, d.id);
    const tb = z.querySelector('.tbadge');
    assert.equal(!!tb, n > 0);
    if (n) { mitTobie += 1; assert.equal(tb.textContent.trim(), String(n)); assert.equal(tb.getAttribute('aria-label'), n === 1 ? '1 Tobie' : `${n} Tobies`); }
  }
  assert.ok(mitDauer && mitFortschritt && mitMarke && mitTobie, `Daten decken alle Fälle ab (${mitDauer}/${mitFortschritt}/${mitMarke}/${mitTobie})`);
  weg();
});

test('Bibliothek: Einzeltitel heißen „Lied · einzeln · 1:06“, nie „1 Folge“', MIT_DOM, async () => {
  const s = await bibliothek();
  await geheZu(s, '#bibliothek');
  s.qa('.artrow button')[3].click(); // Musik
  await s.flush(10);
  const einzeln = Object.values(s.m.backend.serien).filter((d) => d.einzeln && d.art === 'musik');
  assert.ok(einzeln.length > 0);
  for (const d of einzeln) {
    const z = zeilen(s).find((x) => x.dataset.serie === d.id);
    if (!z) continue;
    assert.match(z.querySelector('.ls').textContent, /^Lied · einzeln/);
    assert.ok(!/Folge/.test(z.querySelector('.ls').textContent));
  }
  weg();
});

/* ------------------------------------------------------------------ Arten */

test('Arten: Tipp auf „Musik“ fragt art=musik, die Liste zeigt nur Musik; „Alle“ fragt ohne art', MIT_DOM, async () => {
  const s = await bibliothek();
  s.qa('.artrow button')[3].click();
  await s.flush(10);
  assert.equal(letzte(s).art, 'musik');
  assert.deepEqual(s.qa('.artrow button').map((b) => b.getAttribute('aria-pressed')), ['false', 'false', 'false', 'true', 'false']);
  const erwartet = Object.values(s.m.backend.serien).filter((d) => d.art === 'musik').length;
  assert.equal(s.q('.count').textContent, `${erwartet} Einträge`);
  assert.ok(zeilen(s).every((z) => s.m.backend.serien[z.dataset.serie].art === 'musik'));
  s.qa('.artrow button')[1].click(); // Hörspiele
  await s.flush(10);
  assert.equal(letzte(s).art, 'hoerspiel');
  s.qa('.artrow button')[2].click(); // Hörbücher
  await s.flush(10);
  assert.equal(letzte(s).art, 'hoerbuch');
  s.qa('.artrow button')[4].click(); // Geschichten
  await s.flush(10);
  assert.equal(letzte(s).art, 'geschichte');
  s.qa('.artrow button')[0].click();
  await s.flush(10);
  assert.ok(!('art' in letzte(s)));
  assert.equal(s.q('.count').textContent, '130 Einträge');
  weg();
});

test('Arten und Einstellungen bleiben beim Hin- und Herwechseln erhalten', MIT_DOM, async () => {
  const s = await bibliothek();
  s.qa('.artrow button')[3].click();
  await s.flush(10);
  await geheZu(s, '#start');
  await s.flush(10);
  await geheZu(s, '#bibliothek');
  await s.flush(10);
  assert.equal(s.qa('.artrow button')[3].getAttribute('aria-pressed'), 'true');
  assert.equal(letzte(s).art, 'musik');
  weg();
});

/* ------------------------------------------------------------------ Endloses Nachladen */

test('Nachladen: „Mehr laden (60 weitere)“ holt mit offset 60 und 120, ohne Doppelte; danach keine Taste mehr', MIT_DOM, async () => {
  const s = await bibliothek();
  const mehr = () => s.q('button[data-mehr]');
  assert.equal(mehr().textContent, 'Mehr laden (60 weitere)', 'Rückfall für Tastatur und Screenreader bleibt sichtbar');
  mehr().click();
  await s.flush(10);
  assert.equal(letzte(s).offset, 60);
  assert.equal(zeilen(s).length, 120);
  assert.equal(mehr().textContent, 'Mehr laden (10 weitere)');
  assert.equal(s.q('#live').textContent, 'Weitere Einträge geladen.', 'Ansage für Screenreader');
  mehr().click();
  await s.flush(10);
  assert.equal(letzte(s).offset, 120);
  assert.equal(zeilen(s).length, 130);
  assert.equal(new Set(ids(s)).size, 130, 'keine Doppelten');
  assert.equal(mehr(), null);
  assert.equal(s.q('.count').textContent, '130 Einträge');
  assert.deepEqual(aufrufe(s).map((c) => c.offset), [0, 60, 120]);
  weg();
});

test('Nachladen: der Beobachter (200 px Vorlauf) lädt von selbst weiter, solange der Knopf in der Nähe bleibt', MIT_DOM, async () => {
  mitIO(true);
  const s = await bibliothek();
  const knopfEl = s.q('button[data-mehr]');
  assert.ok(FakeIO.beobachtet.includes(knopfEl), 'der Knopf wird beobachtet');
  assert.ok([...FakeIO.alle].some((io) => io.opts?.rootMargin === '200px'));
  assert.equal(aufrufe(s).length, 1, 'solange der Knopf fern ist, wird nichts nachgeladen');
  FakeIO.zeige(knopfEl); // bleibt sichtbar: nach jedem Nachladen meldet der Beobachter erneut
  await s.flush(20);
  assert.deepEqual(aufrufe(s).map((c) => c.offset), [0, 60, 120]);
  assert.equal(zeilen(s).length, 130);
  assert.equal(s.q('button[data-mehr]'), null);
  mitIO(false);
  weg();
});

test('Nachladen: ein Fehler beim Nachladen bleibt als Meldung, die Liste bleibt, der Knopf geht noch', MIT_DOM, async () => {
  const s = await bibliothek();
  s.m.failNext('tobibox/serien/list', 'medien_nicht_erreichbar');
  s.q('button[data-mehr]').click();
  await s.flush(10);
  assert.equal(zeilen(s).length, 60);
  const t = s.q('.toast.err');
  assert.ok(t, 'Fehlermeldung mit „OK“');
  assert.match(t.textContent, /Das NAS antwortet gerade nicht/);
  s.q('button[data-mehr]').click();
  await s.flush(10);
  assert.equal(zeilen(s).length, 120);
  weg();
});

/* ------------------------------------------------------------------ Sortieren und Filter */

test('Blatt „Sortieren und Filter“: Gruppen, Auswahl wirkt sofort, Zahlenpunkt, Zurücksetzen, Fertig', MIT_DOM, async () => {
  const s = await bibliothek();
  s.q('button[data-sortieren]').focus();
  s.q('button[data-sortieren]').click();
  await s.flush();
  const d = s.q('dialog.blatt');
  assert.ok(d && d.hasAttribute('open'), 'natives <dialog>');
  assert.equal(d.querySelector('h2').textContent, 'Sortieren und Filter');
  assert.deepEqual([...d.querySelectorAll('h3')].map((h) => h.textContent), ['Sortieren', 'Was zeigen', 'Nur zeigen']);
  const optionen = () => [...d.querySelectorAll('.optrow')].map((b) => b.textContent.trim());
  assert.deepEqual(optionen(), ['A bis Z', 'Zuletzt hinzugefügt', 'Alles', 'Nur Hörspiele, Bücher, Alben', 'Nur Einzeltitel (einzelne Lieder und Folgen)', 'Ohne Tobie', 'Neu (letzte 14 Tage)', 'Bitte ansehen']);
  assert.ok(!optionen().includes('Zuletzt angehört'), 'ohne Fähigkeit reinhoeren gibt es „Zuletzt angehört“ noch nicht');
  const knoepfe = [...d.querySelectorAll('.knoepfe button')].map((b) => b.textContent);
  assert.deepEqual(knoepfe, ['Zurücksetzen', 'Fertig']);
  const wahl = (text) => [...d.querySelectorAll('.optrow')].find((b) => b.textContent.trim().startsWith(text));

  // Sortieren: Zuletzt hinzugefügt
  wahl('Zuletzt hinzugefügt').click();
  await s.flush(10);
  assert.equal(letzte(s).sortierung, 'neu');
  assert.equal(wahl('Zuletzt hinzugefügt').getAttribute('aria-checked'), 'true', 'das Blatt zeigt die Wahl sofort');
  assert.equal(wahl('A bis Z').getAttribute('aria-checked'), 'false');
  const neueste = Object.values(s.m.backend.serien).sort((a, b) => Date.parse(b.angelegt_am) - Date.parse(a.angelegt_am))[0].id;
  assert.equal(ids(s)[0], neueste, 'die Liste dahinter ändert sich sofort');
  assert.equal(s.q('.nbadge').textContent, '1');

  // Filter: mehrere gleichzeitig
  wahl('Ohne Tobie').click(); await s.flush(10);
  assert.deepEqual(letzte(s).filter, ['ohne_tobie']);
  assert.ok(zeilen(s).every((z) => !z.querySelector('.tbadge')), 'nur Einträge ohne Tobie');
  wahl('Neu (letzte 14 Tage)').click(); await s.flush(10);
  assert.deepEqual(letzte(s).filter, ['neu', 'ohne_tobie'].sort((a, b) => ['ohne_tobie', 'neu', 'pruefen'].indexOf(a) - ['ohne_tobie', 'neu', 'pruefen'].indexOf(b)));
  assert.ok(zeilen(s).every((z) => Date.parse(s.m.backend.serien[z.dataset.serie].angelegt_am) >= Date.parse('2026-10-30T12:00:00Z')));
  wahl('Bitte ansehen').click(); await s.flush(10);
  assert.deepEqual(letzte(s).filter, ['ohne_tobie', 'neu', 'pruefen']);
  assert.equal(wahl('Bitte ansehen').getAttribute('aria-pressed'), 'true');
  assert.equal(s.q('.nbadge').textContent, '4');
  assert.equal(s.q('.nbadge').getAttribute('aria-label'), '4 aktiv');

  // Zurücksetzen hält das Blatt offen und stellt alles zurück
  d.querySelector('.knoepfe button').click();
  await s.flush(10);
  assert.ok(s.q('dialog.blatt'), 'Zurücksetzen schließt nicht');
  assert.deepEqual(letzte(s), { sortierung: 'name', limit: 60, offset: 0 });
  assert.equal(s.q('.nbadge'), null);
  assert.equal(wahl('A bis Z').getAttribute('aria-checked'), 'true');
  assert.equal(s.q('.count').textContent, '130 Einträge');

  // Fertig schließt; der Fokus geht zurück zum Knopf
  wahl('Alles'); // Gruppe vorhanden
  [...s.qa('dialog .knoepfe button')].find((b) => b.textContent === 'Fertig').click();
  await s.flush();
  assert.equal(s.q('dialog.blatt'), null);
  assert.equal(s.el.shadowRoot.activeElement, s.q('button[data-sortieren]'));
  weg();
});

test('Was zeigen: „Nur Einzeltitel“ und „Nur Hörspiele, Bücher, Alben“ gehen als Filter einzeln und sammlung an das Backend', MIT_DOM, async () => {
  const s = await bibliothek();
  s.q('button[data-sortieren]').click();
  await s.flush();
  const wahl = (text) => s.qa('dialog .optrow').find((b) => b.textContent.trim().startsWith(text));
  wahl('Nur Einzeltitel').click(); await s.flush(10);
  assert.deepEqual(letzte(s).filter, ['einzeln']);
  assert.ok(zeilen(s).length > 0 && zeilen(s).every((z) => s.m.backend.serien[z.dataset.serie].einzeln));
  assert.ok(zeilen(s).every((z) => /einzeln/.test(z.querySelector('.ls').textContent)));
  assert.equal(s.q('.nbadge').textContent, '1');
  wahl('Nur Hörspiele, Bücher, Alben').click(); await s.flush(10);
  assert.deepEqual(letzte(s).filter, ['sammlung']);
  assert.ok(zeilen(s).every((z) => !s.m.backend.serien[z.dataset.serie].einzeln));
  wahl('Alles').click(); await s.flush(10);
  assert.ok(!('filter' in letzte(s)));
  weg();
});

test('Sortieren: „Zuletzt angehört“ gibt es nur mit der Fähigkeit reinhoeren und fragt sortierung=angehoert', MIT_DOM, async () => {
  const s = await bibliothek({ faehigkeiten: [...FAEHIGKEITEN, 'reinhoeren'] });
  s.q('button[data-sortieren]').click();
  await s.flush();
  const w = s.qa('dialog .optrow').find((b) => b.textContent.trim() === 'Zuletzt angehört');
  assert.ok(w);
  w.click(); await s.flush(10);
  assert.equal(letzte(s).sortierung, 'angehoert');
  weg();
});

test('Das Blatt schließt per Esc und per Tipp auf den Hintergrund wie jedes Blatt des Gerüsts', MIT_DOM, async () => {
  const s = await bibliothek();
  s.q('button[data-sortieren]').click();
  await s.flush();
  s.q('dialog.blatt').dispatchEvent(new window.Event('cancel', { cancelable: true }));
  await s.flush();
  assert.equal(s.q('dialog.blatt'), null);
  weg();
});

/* ------------------------------------------------------------------ Leere Zustände, Fehler, Rechte */

test('Bibliothek ganz leer: Bild, ein Satz, Knopf „Hinzufügen“; keine Zählzeile', MIT_DOM, async () => {
  const s = await bibliothek({ viele: false, leer: true });
  const l = s.q('[data-leer="bibliothek"]');
  assert.ok(l);
  assert.equal(l.querySelector('.et').textContent, fuellen(LEER.bibliothek.satz));
  assert.equal(l.querySelector('.et').textContent, 'Noch nichts da. Tippe auf „Hinzufügen“.');
  assert.equal(l.querySelector('.bild svg').getAttribute('aria-hidden'), 'true');
  assert.equal(l.querySelector('.btn').textContent, 'Hinzufügen');
  assert.equal(l.querySelector('.btn').getAttribute('href'), '#hinzufuegen');
  assert.equal(s.q('.libbar'), null);
  assert.ok(s.q('main a[aria-label="Hinzufügen"]'), 'das „+“ gibt es trotzdem');
  weg();
});

test('Filter ohne Treffer: „Nichts gefunden. Nimm einen Filter weg.“ mit „Filter zurücksetzen“, das auch die Art zurückstellt', MIT_DOM, async () => {
  const s = await bibliothek();
  s.qa('.artrow button')[2].click(); // Hörbücher
  await s.flush(10);
  s.q('button[data-sortieren]').click();
  await s.flush();
  s.qa('dialog .optrow').find((b) => b.textContent.trim().startsWith('Nur Einzeltitel')).click(); // Hörbücher sind nie einzeln
  await s.flush(10);
  [...s.qa('dialog .knoepfe button')].find((b) => b.textContent === 'Fertig').click();
  await s.flush();
  const l = s.q('[data-leer="filter"]');
  assert.ok(l, 'leerer Zustand „Filter“');
  assert.equal(l.querySelector('.et').textContent, 'Nichts gefunden. Nimm einen Filter weg.');
  assert.equal(l.querySelector('.btn').textContent, 'Filter zurücksetzen');
  assert.equal(s.q('.count').textContent, '0 Einträge');
  assert.ok(s.q('button[data-sortieren]'), 'der Knopf bleibt, damit man den Filter ändern kann');
  l.querySelector('.btn').click();
  await s.flush(10);
  assert.equal(s.q('[data-leer="filter"]'), null);
  assert.deepEqual(letzte(s), { sortierung: 'name', limit: 60, offset: 0 });
  assert.equal(zeilen(s).length, 60);
  assert.equal(s.qa('.artrow button')[0].getAttribute('aria-pressed'), 'true');
  weg();
});

test('Bibliothek: ein Fehler zeigt die Fehlerkarte mit „Noch einmal versuchen“, ohne Antwort nach der Zeitgrenze ebenso', MIT_DOM, async () => {
  const s = await seite({ viele: true });
  await s.flush(10);
  s.m.failNext('tobibox/serien/list', 'medien_nicht_erreichbar');
  await geheZu(s, '#bibliothek');
  await s.flush(10);
  const k = s.q('[data-zustand="fehler"]');
  assert.ok(k);
  assert.equal(k.getAttribute('role'), 'alert');
  assert.match(k.textContent, /Die Seite konnte nichts laden\./);
  assert.ok(s.q('main h2'), 'Kopf und Arten bleiben');
  assert.equal(zeilen(s).length, 0);
  k.querySelector('button').click();
  await s.flush(10);
  assert.equal(s.q('[data-zustand="fehler"]'), null);
  assert.equal(zeilen(s).length, 60);
  // ohne Antwort
  s.m.on('tobibox/serien/list', () => new Promise(() => {}));
  s.el.store.ladeGrenzeMs = 60;
  s.qa('.artrow button')[1].click();
  await s.flush();
  await warte(120);
  await s.flush();
  assert.ok(s.q('[data-zustand="fehler"]'), 'nach der Zeitgrenze der Fehlerzustand');
  weg();
});

test('Rechte: ein Nicht-Administrator sieht dieselbe Bibliothek, dieselben Filter und dieselbe Suche', MIT_DOM, async () => {
  const a = await bibliothek();
  const adminIds = ids(a);
  const adminText = a.q('main').textContent;
  weg();
  const u = await bibliothek({ darf: false });
  assert.deepEqual(ids(u), adminIds);
  assert.equal(u.q('main').textContent, adminText);
  assert.ok(u.q('main a[aria-label="Hinzufügen"]'), 'Hochladen bleibt Alltag für alle');
  assert.equal(u.q('a[aria-label="Technik"]'), null);
  u.q('button[data-sortieren]').click();
  await u.flush();
  u.qa('dialog .optrow').find((b) => b.textContent.trim() === 'Ohne Tobie').click();
  await u.flush(10);
  assert.deepEqual(letzte(u).filter, ['ohne_tobie']);
  assert.equal(u.q('[data-zustand="fehler"]'), null, 'nur Lesen: kein unauthorized');
  weg();
});

test('Tipp auf eine Zeile führt auf #serie-<id> (Serienseite seit A8); „‹ Bibliothek“ führt zurück', MIT_DOM, async () => {
  const s = await bibliothek();
  const z = zeilen(s)[2];
  const id = z.dataset.serie;
  z.click();
  await warte(30);
  await s.flush(10);
  assert.equal(window.location.hash, `#serie-${id}`);
  assert.ok(s.q('.se-hero'), 'die Serienseite ersetzt den Platzhalter (A8)');
  assert.equal(s.q('main .back').getAttribute('href'), '#bibliothek');
  assert.deepEqual(s.qa('nav a[aria-current="page"]').map((a) => a.querySelector('.tn').textContent), ['Bibliothek']);
  weg();
});

/* ------------------------------------------------------------------ Suche */

/* Eigene kleine Daten für die Suche: ein Begriff („drache“), der Tobies, Einträge, Folgen und einen Einzeltitel trifft. */
function drachenDaten(m) {
  const b = m.backend;
  const folge = (name, anzeige) => ({ name, anzeige, nummer: null, groesse_bytes: 5242880, pruefen: false, tobies: [] });
  const serie = (id, name, folgen, extra = {}) => { b.serien[id] = { id, name, typ: 'normal', ordner: name, pruefen: false, hinweise: [], folgen, art: 'hoerspiel', cover_stand: null, angelegt_am: '2026-11-01T10:00:00Z', ...extra }; };
  serie('d1', 'Drachenreise', [folge('a.mp3', 'Das Drachenfest'), folge('b.mp3', 'Die Reise beginnt')]);
  serie('d2', 'Kleiner Drache Funk', [folge('c.mp3', 'Funk fliegt')]);
  for (let i = 1; i <= 10; i += 1) serie(`ds${i}`, `Drachenschule ${i}`, [folge(`s${i}.mp3`, `Drachenlektion ${i}`), folge(`t${i}.mp3`, `Pause ${i}`)]);
  serie('dl', 'Drachenlied', [folge('l.mp3', 'Drachenlied')], { art: 'musik', einzeln: true });
  b.zuordnungen['04D1D1D1D1D1D1'] = { uid: '04D1D1D1D1D1D1', name: 'Drache', ziel: { typ: 'serie', serie: 'd2' }, angelegt_am: '2026-11-12T10:00:00Z' };
  b.zuordnungen['04D2D2D2D2D2D2'] = { uid: '04D2D2D2D2D2D2', name: 'Löwe', ziel: { typ: 'folge', serie: 'd1', folge: 'a.mp3' }, angelegt_am: '2026-11-12T11:00:00Z' };
  b.zuordnungen['04D3D3D3D3D3D3'] = { uid: '04D3D3D3D3D3D3', name: null, ziel: { typ: 'serie', serie: 'd1' }, angelegt_am: '2026-11-12T12:00:00Z' };
}

async function suche(opts = {}, vorbereiten = drachenDaten) {
  const s = await seite({ ...opts });
  vorbereiten?.(s.m);
  await s.flush(8);
  await geheZu(s, '#suche');
  await s.flush();
  const feld = () => s.q('input.suchfeld');
  const sage = async (text, { warten = true } = {}) => { tippe(feld(), text); if (warten) { await warte(300); await s.flush(10); } };
  return { ...s, feld, sage };
}

const gruppen = (s) => s.qa('[data-gruppe]').map((g) => g.dataset.gruppe);
const anrufe = (s, typ) => s.m.aufrufe(typ);

test('Suche: Zurück-Pfeil, Suchfeld mit Fokus, Hinweis „Tippe mindestens 2 Buchstaben.“, erst ab 2 Zeichen', MIT_DOM, async () => {
  const s = await suche();
  assert.equal(s.q('main a[aria-label="Zurück zur Bibliothek"]').getAttribute('href'), '#bibliothek');
  assert.equal(s.feld().getAttribute('placeholder'), 'Hörspiel, Lied, Folge oder Tobie');
  assert.equal(s.feld().getAttribute('type'), 'search');
  assert.equal(s.el.shadowRoot.activeElement, s.feld(), 'der Fokus liegt gleich im Feld');
  assert.equal(s.q('.qres').textContent.trim(), 'Tippe mindestens 2 Buchstaben.');
  await s.sage('d');
  assert.equal(anrufe(s, 'tobibox/folgen/list').length, 0);
  assert.equal(anrufe(s, 'tobibox/zuordnung/list').filter((m) => m.text).length, 0);
  assert.equal(s.q('.qres').textContent.trim(), 'Tippe mindestens 2 Buchstaben.');
  weg();
});

test('Suche: Tobies zuerst, dann Hörspiele/Bücher/Alben, dann Folgen und Lieder; Zählzeile in derselben Reihenfolge', MIT_DOM, async () => {
  const s = await suche();
  await s.sage('drache');
  assert.deepEqual(gruppen(s), ['tobies', 'sammlungen', 'folgen']);
  assert.deepEqual(s.qa('.qres h3').map((h) => h.textContent), ['Tobies', 'Hörspiele, Bücher, Alben', 'Folgen und Lieder']);
  const zu = anrufe(s, 'tobibox/zuordnung/list').find((m) => m.text);
  const se = anrufe(s, 'tobibox/serien/list').find((m) => m.text);
  const fo = anrufe(s, 'tobibox/folgen/list').at(-1);
  assert.deepEqual([zu.text, zu.limit, se.text, se.filter, se.limit, fo.text, fo.limit], ['drache', 8, 'drache', ['sammlung'], 8, 'drache', 10]);
  // Zählzeile aus den Gesamtzahlen des Backends
  assert.equal(s.q('.qres .count').textContent, 'Gefunden: 3 Tobies, 12 Sammlungen, 12 Folgen und Lieder');
  assert.equal(s.q('.qres .count').getAttribute('aria-live'), 'polite');
  assert.equal(s.qa('[data-gruppe="sammlungen"] .lrow').length, 8, 'höchstens 8 Sammlungen');
  assert.equal(s.qa('[data-gruppe="folgen"] .frow').length, 10, 'höchstens 10 Folgen');
  assert.deepEqual(s.qa('.qres .muted').map((m) => m.textContent).filter((t) => t.startsWith('…')),
    ['… und 4 weitere. Genauer suchen hilft.', '… und 2 weitere. Genauer suchen hilft.'], 'Sammlungen (12 − 8) und Folgen (12 − 10)');
  weg();
});

test('Suche: Tobies werden nach Name oder nach dem gefunden, was sie spielen; jede Zeile sagt „spielt …“ und ist ein Link', MIT_DOM, async () => {
  const s = await suche();
  await s.sage('drache');
  const t = s.qa('[data-gruppe="tobies"] .rowbtn');
  assert.equal(t.length, 3);
  const nach = (uid) => t.find((x) => x.getAttribute('href') === `#tobie-${uid}`);
  const drache = nach('04D1D1D1D1D1D1');
  assert.equal(drache.getAttribute('aria-label'), 'Drache bearbeiten');
  assert.match(drache.textContent, /Drache/);
  assert.match(drache.querySelector('.muted').textContent, /^spielt „Kleiner Drache Funk“$/);
  const loewe = nach('04D2D2D2D2D2D2');
  assert.equal(loewe.getAttribute('aria-label'), 'Löwe bearbeiten', 'gefunden über das Ziel, nicht über den Namen');
  assert.equal(loewe.querySelector('.muted').textContent, 'spielt „Das Drachenfest“ aus „Drachenreise“');
  const ohne = nach('04D3D3D3D3D3D3');
  assert.equal(ohne.getAttribute('aria-label'), 'Tobie ohne Namen bearbeiten');
  assert.ok([...t].every((x) => x.querySelector('.chev')), 'Pfeil rechts');
  assert.ok(t.every((x) => x.querySelector('.cover')));
  weg();
});

test('Suche: Treffer sind hervorgehoben, jede Zeile ist ein Link, Einzeltitel stehen nur bei den Folgen und Liedern', MIT_DOM, async () => {
  const s = await suche();
  await s.sage('drache');
  const marks = s.qa('[data-gruppe="sammlungen"] .lt mark').map((m) => m.textContent);
  assert.ok(marks.length > 0 && marks.every((m) => m.toLowerCase() === 'drache'), `Treffer hervorgehoben (${marks})`);
  for (const z of s.qa('[data-gruppe="sammlungen"] .lrow')) assert.match(z.getAttribute('href'), /^#serie-/);
  assert.ok(!s.qa('[data-gruppe="sammlungen"] .lt').some((x) => x.textContent === 'Drachenlied'), 'ohne Einzeltitel');
  await s.sage('drachenlied');
  const f = s.qa('[data-gruppe="folgen"] .frow');
  assert.equal(f.length, 1);
  assert.equal(f[0].querySelector('.muted').textContent, 'Einzeltitel');
  assert.equal(f[0].querySelector('a.slink').getAttribute('href'), '#serie-dl');
  assert.equal(s.qa('[data-gruppe="sammlungen"]').length, 0, 'der Einzeltitel steht nicht bei den Sammlungen');
  await s.sage('lektion 3');
  const g = s.qa('[data-gruppe="folgen"] .frow');
  assert.equal(g.length, 1);
  assert.equal(g[0].querySelector('.muted').textContent, 'Drachenschule 3', 'Folge: „Serie“ als Untertitel');
  assert.equal(g[0].querySelector('a.slink').getAttribute('href'), '#serie-ds3');
  assert.equal(s.qa('.qres .frow button').length, 0, 'Abspielen und ⋯ kommen mit A8b und A9');
  weg();
});

test('Suche: Umlaute und Groß/Klein sind egal', MIT_DOM, async () => {
  const s = await suche({ viele: true }, null);
  await s.sage('MUDE');
  assert.ok(s.qa('[data-gruppe="sammlungen"] .lt').length > 0);
  assert.ok(s.qa('[data-gruppe="sammlungen"] .lt').every((x) => /^Müde /.test(x.textContent)));
  assert.ok(s.qa('[data-gruppe="sammlungen"] .lt mark').every((m) => m.textContent === 'Müde'.slice(0, 4) || m.textContent.toLowerCase() === 'müde'));
  weg();
});

test('Suche: bis zu fünf Vorschläge, Tobies zuerst; Tippen setzt den Begriff ein und sucht gleich', MIT_DOM, async () => {
  const s = await suche();
  await s.sage('dra');
  const v = s.qa('.sug .sugrow');
  assert.ok(v.length >= 3 && v.length <= 5, `${v.length} Vorschläge`);
  assert.equal(v[0].textContent.trim(), 'Drache', 'Tobie-Name zuerst');
  assert.ok(v[0].querySelector('svg'));
  assert.deepEqual(v.map((x) => x.textContent.trim()).slice(0, 3), ['Drache', 'Drachenreise', 'Drachenschule 1']);
  assert.equal(s.q('.sug').getAttribute('aria-label'), 'Vorschläge');
  assert.ok(v.every((x) => x.querySelector('mark')), 'Treffer hervorgehoben');
  v[1].click();
  await s.flush(10);
  assert.equal(s.feld().value, 'Drachenreise');
  assert.ok(anrufe(s, 'tobibox/folgen/list').some((m) => m.text === 'Drachenreise'), 'ohne Verzögerung gesucht');
  assert.ok(!s.qa('.sug .sugrow').some((x) => x.textContent.trim() === 'Drachenreise'), 'der Begriff selbst ist kein Vorschlag');
  assert.equal(s.el.shadowRoot.activeElement, s.feld(), 'Fokus bleibt im Feld');
  weg();
});

test('Suche: nichts gefunden zeigt Bild, „Nichts gefunden zu „xyz“.“ und „Suche löschen“; der Begriff steht als Text', MIT_DOM, async () => {
  const s = await suche();
  await s.sage('<b>xyz</b>');
  const l = s.q('[data-leer="suche"]');
  assert.ok(l);
  assert.equal(l.querySelector('.et').textContent, 'Nichts gefunden zu „<b>xyz</b>“.');
  assert.equal(l.querySelector('.et b'), null, 'nie als HTML');
  assert.equal(l.querySelector('.btn').textContent, 'Suche löschen');
  assert.equal(s.q('.qres .sug'), null);
  l.querySelector('.btn').click();
  await s.flush(10);
  assert.equal(s.feld().value, '');
  assert.equal(s.q('.qres').textContent.trim(), 'Tippe mindestens 2 Buchstaben.');
  assert.equal(s.el.shadowRoot.activeElement, s.feld());
  weg();
});

test('Suche: Verzögerung 250 ms (nur die letzte Eingabe wird gesucht), Enter sucht sofort, Löschen räumt auf', MIT_DOM, async () => {
  const s = await suche();
  tippe(s.feld(), 'dr'); await warte(80);
  tippe(s.feld(), 'dra'); await warte(80);
  tippe(s.feld(), 'drac'); await warte(120);
  assert.equal(anrufe(s, 'tobibox/folgen/list').length, 0, 'noch keine Anfrage');
  await warte(250); await s.flush(10);
  assert.deepEqual(anrufe(s, 'tobibox/folgen/list').map((m) => m.text), ['drac']);
  tippe(s.feld(), 'drach');
  taste(s.feld(), 'Enter');
  await s.flush(10);
  assert.deepEqual(anrufe(s, 'tobibox/folgen/list').map((m) => m.text), ['drac', 'drach'], 'Enter ohne Warten');
  tippe(s.feld(), '');
  await warte(300); await s.flush(10);
  assert.equal(anrufe(s, 'tobibox/folgen/list').length, 2);
  assert.equal(s.q('.qres').textContent.trim(), 'Tippe mindestens 2 Buchstaben.');
  weg();
});

test('Suche: Art und Filter der Bibliothek gelten nicht, die Suche geht über alles', MIT_DOM, async () => {
  const s = await seite({ viele: true, hash: '#bibliothek' });
  await s.flush(10);
  s.qa('.artrow button')[3].click(); // Musik
  await s.flush(10);
  await geheZu(s, '#suche');
  tippe(s.q('input.suchfeld'), 'wilde');
  await warte(300); await s.flush(10);
  const se = s.m.aufrufe('tobibox/serien/list').filter((m) => m.text);
  assert.equal(se.length, 1);
  assert.ok(!('art' in se[0]));
  assert.deepEqual(se[0].filter, ['sammlung'], 'nur der feste Filter der Gruppe');
  assert.ok(s.qa('[data-gruppe="sammlungen"] .lt').length > 0);
  weg();
});

test('Suche: ein Fehler zeigt die Fehlerkarte; „Noch einmal versuchen“ sucht erneut', MIT_DOM, async () => {
  const s = await suche();
  s.m.failNext('tobibox/folgen/list', 'medien_nicht_erreichbar');
  await s.sage('drache');
  const k = s.q('[data-zustand="fehler"]');
  assert.ok(k);
  assert.equal(k.getAttribute('role'), 'alert');
  k.querySelector('button').click();
  await s.flush(10);
  assert.equal(s.q('[data-zustand="fehler"]'), null);
  assert.deepEqual(gruppen(s), ['tobies', 'sammlungen', 'folgen']);
  weg();
});

test('Suche: Rechte — ein Nicht-Administrator sucht und sieht dasselbe', MIT_DOM, async () => {
  const a = await suche();
  await a.sage('drache');
  const admin = a.q('.qres').textContent;
  weg();
  const u = await suche({ darf: false });
  await u.sage('drache');
  assert.equal(u.q('.qres').textContent, admin);
  assert.equal(u.q('[data-zustand="fehler"]'), null);
  weg();
});

test('Suche: der Zurück-Pfeil führt in die Bibliothek, die Lupe der Bibliothek in die Suche', MIT_DOM, async () => {
  const s = await seite({ viele: true, hash: '#bibliothek' });
  await s.flush(10);
  s.q('main a[aria-label="Suchen"]').click();
  await warte(30); await s.flush(10);
  assert.equal(window.location.hash, '#suche');
  assert.deepEqual(s.qa('nav a[aria-current="page"]').map((a) => a.querySelector('.tn').textContent), ['Bibliothek']);
  s.q('main a[aria-label="Zurück zur Bibliothek"]').click();
  await warte(30); await s.flush(10);
  assert.equal(window.location.hash, '#bibliothek');
  assert.equal(zeilen(s).length, 60);
  weg();
});

test('Nach dem Wiederverbinden lädt die aktive Seite still neu (Liste bleibt stehen, keine Platzhalter)', MIT_DOM, async () => {
  const s = await seite({ viele: true, hash: '#bibliothek' });
  await s.flush(10);
  // Der Mock hat keine Verbindungsereignisse; der Store hört auf `ready` der echten Verbindung. Hier von Hand ausgelöst.
  s.el.store.onWiederda();
  const davor = aufrufe(s).length;
  assert.equal(zeilen(s).length, 60, 'die Liste bleibt sichtbar');
  await s.flush(10);
  assert.equal(aufrufe(s).length, davor + 1);
  assert.equal(zeilen(s).length, 60);
  assert.equal(s.q('.laedt'), null);
  weg();
});

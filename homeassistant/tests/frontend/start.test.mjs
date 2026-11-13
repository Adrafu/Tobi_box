/* Tests der Seite „Start“ (AP A7, Design 5.1). Aufruf: node --test homeassistant/tests/frontend
 *
 * Stufe A: Schnellzugriff 2 × 3 aus zuletzt zugeordneten und zuletzt hinzugefügten Einträgen, dazu die Reihe
 * „Neu hinzugefügt“. Reihen ohne Daten fehlen. Backend aus mock-hass.mjs (`viele`: 130 Einträge).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, mitIO, FakeIO, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN } from './mock-hass.mjs';

const { schnellzugriff, REIHEN } = await import('../../custom_components/tobibox/frontend/seiten/start.js');
const { LEER, fuellen, START } = await import('../../custom_components/tobibox/frontend/texte.js');

const ohneNachrichten = (m) => m.calls.filter((c) => !c.abo);
const idsAus = (qa, sel) => qa(sel).map((a) => a.getAttribute('href').replace('#serie-', ''));

test('schnellzugriff(): erst die zugeordneten, dann die neuesten, jeder Eintrag einmal, höchstens sechs', () => {
  const s = (id) => ({ id, name: id });
  assert.deepEqual(schnellzugriff([s('a'), s('b'), s('a')], [s('b'), s('c'), s('d'), s('e'), s('f'), s('g'), s('h')]).map((x) => x.id), ['a', 'b', 'c', 'd', 'e', 'f']);
  assert.deepEqual(schnellzugriff([], [s('x')]).map((x) => x.id), ['x']);
  assert.deepEqual(schnellzugriff([], []), []);
  assert.equal(schnellzugriff([s('a'), s('b'), s('c'), s('d'), s('e'), s('f'), s('g')], []).length, 6);
});

test('REIHEN: nur „Neu hinzugefügt“ hat in Stufe A Daten; die anderen tragen ihre Stufe und fehlen', () => {
  assert.deepEqual(REIHEN.map((r) => [r.id, r.stufe]), [['weiterhoeren', 'A-2'], ['zuletzt_gehoert', 'B'], ['neu', 'A-1'], ['favoriten', 'B']]);
  assert.deepEqual(REIHEN.map((r) => r.eintraege({ neu: [{ id: 'x' }] }).length), [0, 0, 1, 0]);
});

test('Start: Schnellzugriff (2 × 3) und die Reihe „Neu hinzugefügt“, sonst nichts; Reihen ohne Daten fehlen ganz', MIT_DOM, async () => {
  const s = await seite({ viele: true });
  await s.flush(10);
  assert.equal(s.q('[data-start="schnellzugriff"]').getAttribute('class'), 'qgrid');
  assert.equal(s.qa('.qgrid .qt').length, 6);
  assert.equal(s.qa('.hscroll').length, 1, 'genau eine Reihe');
  assert.deepEqual(s.qa('main h3').map((h) => h.textContent), [START.reihen.neu]);
  assert.equal(s.qa('.hscroll .tile').length, 8, 'die acht neuesten');
  for (const verboten of ['weiterhören', 'Zuletzt auf den Boxen gehört', 'Favoriten', 'Ganze Bibliothek', 'Status', 'Hinzufügen']) {
    assert.ok(!s.q('main').textContent.includes(verboten), `${verboten} steht nicht auf dem Start`);
  }
  assert.ok(s.qa('main h2.sr').some((h) => h.textContent === 'Schnellzugriff'));
  weg();
});

test('Start: abgefragt werden nur serien/list (neu, 8) und zuordnung/list (neu), fehlende Ziele einzeln mit serie/get', MIT_DOM, async () => {
  const s = await seite({ viele: true });
  await s.flush(10);
  const c = ohneNachrichten(s.m);
  assert.deepEqual(s.m.aufrufe('tobibox/serien/list'), [{ id: c.find((x) => x.type === 'tobibox/serien/list').msg.id, type: 'tobibox/serien/list', sortierung: 'neu', limit: 8 }]);
  const zu = s.m.letzter('tobibox/zuordnung/list');
  assert.equal(zu.neu, true);
  assert.equal(zu.limit, 12);
  // Zugeordnete Einträge, die nicht unter den acht neuesten stehen, kommen einzeln (nie mehr als sechs)
  const nachgeladen = s.m.aufrufe('tobibox/serie/get');
  assert.ok(nachgeladen.length >= 1 && nachgeladen.length <= 6);
  assert.equal(s.m.aufrufe('tobibox/folgen/list').length, 0);
  weg();
});

test('Start: Schnellzugriff folgt der Zuordnung (zuletzt zugeordnet zuerst), danach die neuesten', MIT_DOM, async () => {
  const s = await seite({ viele: true });
  await s.flush(10);
  const mock = s.m.backend;
  const zuordnungen = Object.values(mock.zuordnungen).filter((z) => z.ziel.typ !== 'aktion').sort((a, b) => Date.parse(b.angelegt_am) - Date.parse(a.angelegt_am));
  const erwartet = [];
  for (const z of zuordnungen) if (!erwartet.includes(z.ziel.serie)) erwartet.push(z.ziel.serie);
  const kacheln = idsAus(s.qa, '.qgrid .qt');
  assert.deepEqual(kacheln.slice(0, Math.min(6, erwartet.length)), erwartet.slice(0, Math.min(6, erwartet.length)));
  assert.equal(new Set(kacheln).size, kacheln.length, 'jeder Eintrag einmal');
  // Jede Kachel ist ein Link auf die Serienseite; Titel in bis zu zwei Zeilen, Cover 56 px links (Stil)
  for (const a of s.qa('.qgrid .qt')) { assert.match(a.getAttribute('href'), /^#serie-[0-9a-f]{12}$/); assert.ok(a.querySelector('.cover')); assert.ok(a.querySelector('.qn').textContent.length > 2); }
  weg();
});

test('Start: „Neu hinzugefügt“ zeigt die acht neuesten in der Reihenfolge des Backends, mit Untertitel ohne Dauer und Marke „bitte ansehen“', MIT_DOM, async () => {
  const s = await seite({ viele: true });
  await s.flush(10);
  const neueste = Object.values(s.m.backend.serien).sort((a, b) => Date.parse(b.angelegt_am) - Date.parse(a.angelegt_am)).slice(0, 8).map((x) => x.id);
  assert.deepEqual(idsAus(s.qa, '.hscroll .tile'), neueste);
  const k = s.qa('.hscroll .tile')[0];
  assert.match(k.querySelector('.tm').textContent, /^(Hörspiel|Hörbuch|Musik|\d+ Geschichten?|Lied|Folge|Geschichte)/);
  assert.ok(!/Min\.|Std\./.test(k.querySelector('.tm').textContent), 'Kacheln zeigen keine Dauer');
  const mitMarke = s.qa('.hscroll .tile').filter((t) => t.querySelector('.badge'));
  for (const t of mitMarke) assert.equal(t.querySelector('.badge').textContent, 'bitte ansehen');
  weg();
});

test('Start ohne Einträge: leerer Zustand mit Knopf „Zur Bibliothek“, keine Reihen, kein Schnellzugriff', MIT_DOM, async () => {
  const s = await seite({ leer: true });
  await s.flush(10);
  const l = s.q('[data-leer="start"]');
  assert.ok(l);
  assert.equal(l.querySelector('.et').textContent, fuellen(LEER.start.satz));
  assert.equal(l.querySelector('.btn').textContent, 'Zur Bibliothek');
  assert.equal(l.querySelector('.btn').getAttribute('href'), '#bibliothek');
  assert.equal(s.q('.qgrid'), null);
  assert.equal(s.q('.hscroll'), null);
  assert.equal(s.qa('main h3').length, 0);
  weg();
});

test('Start mit wenigen Einträgen: weniger als sechs Kacheln, keine Platzhalter', MIT_DOM, async () => {
  const s = await seite(); // Standard-Mock: drei Einträge
  await s.flush(10);
  assert.equal(s.qa('.qgrid .qt').length, 3);
  assert.equal(s.qa('.hscroll .tile').length, 3);
  weg();
});

test('Start: ein Fehler zeigt die Fehlerkarte mit „Noch einmal versuchen“, danach geht es weiter', MIT_DOM, async () => {
  const s = await seite({ viele: true });
  await s.flush(10);
  await geheZu(s, '#bibliothek');
  await s.flush(10);
  s.m.failNext('tobibox/serien/list', 'medien_nicht_erreichbar');
  await geheZu(s, '#start');
  await s.flush(10);
  const k = s.q('[data-zustand="fehler"]');
  assert.ok(k, 'Fehlerkarte');
  assert.equal(k.getAttribute('role'), 'alert');
  assert.match(k.textContent, /Die Seite konnte nichts laden\./);
  assert.match(k.textContent, /Code: medien_nicht_erreichbar/, 'der Administrator sieht den Code');
  assert.equal(s.qa('.qgrid').length, 0);
  k.querySelector('button').click();
  await s.flush(10);
  assert.equal(s.q('[data-zustand="fehler"]'), null);
  assert.equal(s.qa('.qgrid .qt').length, 6);
  weg();
});

test('Start: ohne Antwort wird es nach der Zeitgrenze der Fehlerzustand', MIT_DOM, async () => {
  const s = await seite({ viele: true, ladeGrenzeMs: 60 });
  await s.flush(10);
  s.m.on('tobibox/serien/list', () => new Promise(() => {}));
  await geheZu(s, '#bibliothek');
  await geheZu(s, '#start');
  assert.ok(s.q('.laedt .skel'));
  await warte(120);
  await s.flush();
  assert.ok(s.q('[data-zustand="fehler"]'));
  weg();
});

test('Start: Nicht-Administrator sieht denselben Start (nur Lesen)', MIT_DOM, async () => {
  const a = await seite({ viele: true });
  await a.flush(10);
  const admin = idsAus(a.qa, '.qgrid .qt').concat(idsAus(a.qa, '.hscroll .tile'));
  weg();
  const u = await seite({ viele: true, darf: false });
  await u.flush(10);
  assert.deepEqual(idsAus(u.qa, '.qgrid .qt').concat(idsAus(u.qa, '.hscroll .tile')), admin);
  assert.equal(u.q('a[aria-label="Technik"]'), null);
  assert.ok(u.q('.kopf a[aria-label="Suchen"]'), 'die Lupe im Kopf gibt es für alle');
  weg();
});

test('Start: Kopf mit Begrüßung und Lupe; ab 1100 px steht die Begrüßung als Überschrift auf der Seite', MIT_DOM, async () => {
  const klein = await seite({ viele: true });
  await klein.flush(10);
  assert.ok(klein.q('.kopf h1').textContent.startsWith('Gut'));
  assert.equal(klein.q('.kopf a[aria-label="Suchen"]').getAttribute('href'), '#suche');
  weg();
  const gross = await seite({ viele: true, breite: 1280 });
  await gross.flush(10);
  assert.ok(gross.q('main h2').textContent.startsWith('Gut'));
  weg();
});

test('Start: Cover laden erst, wenn sie sichtbar werden; ohne Bild (cover_stand null) nie', MIT_DOM, async () => {
  mitIO(true);
  const s = await seite({ viele: true });
  await s.flush(10);
  assert.equal(s.m.covers.length, 0, 'noch nichts sichtbar, nichts geladen');
  const mitBild = s.qa('[data-cover]').filter((c) => c.dataset.stand && c.dataset.stand !== '');
  const ohneBild = s.qa('[data-cover]').filter((c) => c.dataset.stand === '');
  assert.ok(mitBild.length > 0);
  FakeIO.zeige(mitBild[0]);
  await s.flush();
  assert.equal(s.m.covers.length, 1);
  assert.match(s.m.covers[0], /^\/api\/tobibox\/cover\/[0-9a-f]{12}\?groesse=klein&v=[0-9a-f]{8}$/);
  assert.match(mitBild[0].style.backgroundImage, /blob:mock-/);
  assert.equal(mitBild[0].dataset.bild, '1');
  for (const c of ohneBild) FakeIO.zeige(c);
  await s.flush();
  assert.equal(s.m.covers.length, 1, 'ohne cover_stand wird nichts angefragt');
  assert.ok(ohneBild.every((c) => !c.style.backgroundImage), 'Platzhalter bleibt');
  assert.ok(ohneBild.every((c) => c.querySelector('.bst').textContent.length === 1), 'Anfangsbuchstabe');
  mitIO(false);
  weg();
});

test('Start: Pflichtfähigkeit „bibliothek“ — ohne sie sagt das Backend invalid_format und die Seite zeigt die Fehlerkarte', MIT_DOM, async () => {
  const s = await seite({ viele: true, faehigkeiten: FAEHIGKEITEN.filter((x) => x !== 'bibliothek') });
  await s.flush(10);
  assert.ok(s.q('[data-zustand="fehler"]'));
  weg();
});

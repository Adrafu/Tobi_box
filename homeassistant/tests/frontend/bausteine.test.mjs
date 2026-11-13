/* Tests der gemeinsamen Bausteine (AP A7, frontend/bausteine.js): reine Funktionen, CoverLader, Segment-Umschalter,
 * leerer Zustand. Aufruf: node --test homeassistant/tests/frontend
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { domBereit, MIT_DOM, tick, taste, warte, mitIO, FakeIO } from './dom-helfer.mjs';

const FRONTEND = join(fileURLToPath(new URL('.', import.meta.url)), '../../custom_components/tobibox/frontend');
const b = await import('../../custom_components/tobibox/frontend/bausteine.js');
const texte = await import('../../custom_components/tobibox/frontend/texte.js');
const { norm, zaehle, dauerText, uhr, untertitel, fortschritt, coverKlasse, teile, ladeMitGrenze, CoverLader } = b;

/* ------------------------------------------------------------------ reine Funktionen (ohne DOM) */

test('Das Modul lädt ohne DOM, nichts aus dem Netz, keine HTML-Einschleusung', () => {
  assert.equal(typeof b.listenZeile, 'function');
  assert.equal(b.html, undefined, 'ohne DOM ist Lit noch nicht da');
  for (const f of ['bausteine.js', 'seiten/start.js', 'seiten/bibliothek.js', 'seiten/suche.js', 'seiten/index.js']) {
    const src = readFileSync(join(FRONTEND, f), 'utf8');
    assert.doesNotMatch(src, /from\s*["']https?:|import\(["']https?:|unsafeHTML|innerHTML\s*=/, f);
  }
});

test('norm: ohne Groß/Klein und ohne Akzente (ä = a)', () => {
  assert.equal(norm('Müde Füchse'), 'mude fuchse');
  assert.equal(norm('ÄÖÜ'), 'aou');
  assert.equal(norm(null), '');
});

test('zaehle: Einzahl bei genau 1, sonst Mehrzahl', () => {
  assert.equal(zaehle(texte.BIB.anzahl, 1), '1 Eintrag');
  assert.equal(zaehle(texte.BIB.anzahl, 0), '0 Einträge');
  assert.equal(zaehle(texte.BIB.anzahl, 60), '60 Einträge');
  assert.equal(zaehle(texte.ZEILE.tobies, 1), '1 Tobie');
  assert.equal(zaehle(texte.ZEILE.tobies, 3), '3 Tobies');
});

test('dauerText und uhr: „26 Min.“, „9 Std. 40 Min.“, „1:06“', () => {
  assert.equal(dauerText(45), '45 Sek.');
  assert.equal(dauerText(26 * 60), '26 Min.');
  assert.equal(dauerText(9 * 3600 + 40 * 60), '9 Std. 40 Min.');
  assert.equal(dauerText(3600), '1 Std.');
  assert.equal(uhr(66), '1:06');
  assert.equal(uhr(3723), '1:02:03');
});

test('untertitel: Hörspiel, Hörbuch, Musik, Geschichten und Einzeltitel nach Design 5.2', () => {
  assert.equal(untertitel({ art: 'hoerspiel', anzahl_folgen: 12, dauer_s: 26 * 60 }), 'Hörspiel · 12 Folgen · 26 Min.');
  assert.equal(untertitel({ art: 'hoerspiel', anzahl_folgen: 1, dauer_s: null }), 'Hörspiel · 1 Folge', 'ohne Dauer fehlt sie');
  assert.equal(untertitel({ art: 'hoerbuch', anzahl_folgen: 1, kapitel_anzahl: 14, dauer_s: 9 * 3600 + 2400 }), 'Hörbuch · 14 Kapitel · 9 Std. 40 Min.');
  assert.equal(untertitel({ art: 'hoerbuch', anzahl_folgen: 1, kapitel_anzahl: 0 }), 'Hörbuch', 'Kapitelzahl erst in A-3');
  assert.equal(untertitel({ art: 'musik', anzahl_folgen: 20, dauer_s: 72 * 60 }), 'Musik · 20 Lieder · 1 Std. 12 Min.');
  assert.equal(untertitel({ art: 'musik', anzahl_folgen: 1 }), 'Musik · 1 Lied');
  assert.equal(untertitel({ art: 'geschichte', anzahl_folgen: 8 }), '8 Geschichten');
  assert.equal(untertitel({ art: 'musik', einzeln: true, anzahl_folgen: 1, dauer_s: 66 }), 'Lied · einzeln · 1:06');
  assert.equal(untertitel({ art: 'geschichte', einzeln: true, anzahl_folgen: 1, dauer_s: 99 }), 'Geschichte · einzeln · 1:39');
  assert.equal(untertitel({ art: 'hoerbuch', einzeln: true, anzahl_folgen: 1 }), 'Hörbuch · einzeln');
  assert.ok(!/Folge/.test(untertitel({ art: 'musik', einzeln: true, anzahl_folgen: 1 })), 'nie „1 Folge“');
  assert.equal(untertitel({ anzahl_folgen: 3 }), 'Hörspiel · 3 Folgen', 'ohne art gilt Hörspiel (Vertrag 14.2)');
  assert.equal(untertitel({ art: 'hoerspiel', anzahl_folgen: 12, dauer_s: 1560 }, { dauer: false }), 'Hörspiel · 12 Folgen');
});

test('fortschritt: „noch 18 Min.“ oder „Fertig gehört“, nur bei angehörten Einträgen', () => {
  assert.equal(fortschritt({}), null);
  assert.deepEqual(fortschritt({ hoerstelle: { anteil: 0.4, rest_s: 18 * 60 } }), { anteil: 0.4, text: 'noch 18 Min.' });
  assert.equal(fortschritt({ hoerstelle: { anteil: 1, rest_s: 0 } }).text, 'Fertig gehört');
  assert.equal(fortschritt({ hoerstelle: { anteil: 7 } }).anteil, 1, 'auf 0 bis 1 begrenzt');
});

test('coverKlasse: stabile von sechs Farben aus der ID', () => {
  assert.equal(coverKlasse('abc'), coverKlasse('abc'));
  const alle = new Set(Array.from({ length: 200 }, (_, i) => coverKlasse(`serie-${i}`)));
  assert.deepEqual([...alle].sort(), ['c1', 'c2', 'c3', 'c4', 'c5', 'c6']);
  assert.match(coverKlasse(''), /^c[1-6]$/);
});

test('teile: Treffer hervorheben ohne Rücksicht auf Groß/Klein und Umlaute; nie HTML', () => {
  assert.deepEqual(teile('Müde Füchse', 'mude'), { vor: '', treffer: 'Müde', nach: ' Füchse' });
  assert.deepEqual(teile('Die Drachenreise', 'DRACHE'), { vor: 'Die ', treffer: 'Drache', nach: 'nreise' });
  assert.deepEqual(teile('abc', 'x'), { vor: 'abc', treffer: null, nach: '' });
  assert.deepEqual(teile('abc', ''), { vor: 'abc', treffer: null, nach: '' });
  assert.equal(teile('<b>x</b>', 'x').treffer, 'x');
});

test('ladeMitGrenze: Antwort oder nach der Zeitgrenze { code: zeitgrenze }', async () => {
  assert.equal(await ladeMitGrenze(Promise.resolve(7), 50), 7);
  await assert.rejects(ladeMitGrenze(new Promise(() => {}), 30), (e) => e.code === 'zeitgrenze');
  await assert.rejects(ladeMitGrenze(Promise.reject({ code: 'x' }), 50), (e) => e.code === 'x');
});

/* ------------------------------------------------------------------ CoverLader */

function fakeHass(antwort = { ok: true }) {
  const urls = [];
  return { urls, fetchWithAuth: async (pfad) => { urls.push(pfad); return { ok: antwort.ok, blob: async () => new Blob(['x']) }; } };
}

test('CoverLader: klein, mit Stand in der Adresse, als blob: zwischengespeichert; 404 bleibt Platzhalter und wird gemerkt', MIT_DOM, async () => {
  await domBereit();
  const hass = fakeHass();
  const l = new CoverLader(() => hass);
  const u1 = await l.blobUrl('s1', 'abcd1234');
  assert.match(u1, /^blob:mock-/);
  assert.equal(await l.blobUrl('s1', 'abcd1234'), u1, 'ein Abruf je Stand');
  assert.deepEqual(hass.urls, ['/api/tobibox/cover/s1?groesse=klein&v=abcd1234']);
  await l.blobUrl('s1', 'neu00000');
  assert.equal(hass.urls.length, 2, 'neuer Stand, neuer Abruf');
  assert.match(await l.blobUrl('s2', '?'), /^blob:mock-/, 'unbekannter Stand wird versucht');
  assert.equal(hass.urls[2], '/api/tobibox/cover/s2?groesse=klein');
  const nein = new CoverLader(() => fakeHass({ ok: false }));
  assert.equal(await nein.blobUrl('s9', '?'), null);
  assert.equal(await new CoverLader(() => null).blobUrl('x', 'y'), null, 'ohne hass kein Fehler');
  l.merke([{ id: 'a', cover_stand: 'ff00ff00' }, { id: 'b', cover_stand: null }, { id: 'c' }]);
  assert.equal(l.stand('a'), 'ff00ff00');
  assert.equal(l.stand('b'), null);
  assert.equal(l.stand('c'), undefined);
});

test('CoverLader: beobachtet nur Cover mit Bild, lädt erst bei Sichtbarkeit und setzt das Bild; ohne Beobachter sofort', MIT_DOM, async () => {
  await domBereit();
  const wurzel = document.createElement('div');
  wurzel.innerHTML = '<div data-cover="a" data-stand="11111111"><span class="bst">A</span></div><div data-cover="b" data-stand=""><span class="bst">B</span></div><div data-cover="c" data-stand="?"><span class="bst">C</span></div>';
  document.body.appendChild(wurzel);
  mitIO(true);
  const hass = fakeHass();
  const l = new CoverLader(() => hass);
  l.beobachte(wurzel);
  await tick();
  assert.equal(hass.urls.length, 0, 'nichts sichtbar, nichts geladen');
  const [a, bb, c] = wurzel.children;
  FakeIO.zeige(a); FakeIO.zeige(c);
  await tick(); await tick();
  assert.deepEqual(hass.urls.sort(), ['/api/tobibox/cover/a?groesse=klein&v=11111111', '/api/tobibox/cover/c?groesse=klein']);
  assert.match(a.style.backgroundImage, /blob:mock-/);
  assert.equal(a.dataset.bild, '1');
  assert.ok(!FakeIO.beobachtet.includes(bb), 'ohne Bild wird nie beobachtet');
  // Ein anderes Cover im selben Element (Lit baut Zeilen um): Bild wird zurückgesetzt und neu geholt
  a.dataset.cover = 'z'; a.dataset.stand = '22222222';
  l.beobachte(wurzel);
  assert.equal(a.style.backgroundImage, '');
  assert.equal(a.dataset.bild, undefined);
  l.abmelden();
  mitIO(false);
  const l2 = new CoverLader(() => hass);
  const n = hass.urls.length;
  wurzel.firstElementChild.dataset.cover = 'q';
  l2.beobachte(wurzel);
  await tick(); await tick();
  assert.ok(hass.urls.length > n, 'ohne IntersectionObserver wird gleich geladen');
  wurzel.remove();
});

/* ------------------------------------------------------------------ Templates */

async function zeichne(vorlage) {
  await domBereit();
  const lit = await import('../../custom_components/tobibox/frontend/lit-all.min.js');
  const name = `bst-test-${Math.random().toString(16).slice(2)}`;
  customElements.define(name, class extends lit.LitElement { render() { return vorlage(); } });
  const el = document.createElement(name);
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

test('Segment-Umschalter: Gruppe mit aria-pressed, Klick wählt, Pfeiltasten wählen den Nachbarn, an den Enden bleibt es', MIT_DOM, async () => {
  const gewaehlt = [];
  let wert = 'a';
  const el = await zeichne(() => b.segment({ label: 'Was?', optionen: [{ wert: 'a', label: 'Eins' }, { wert: 'b', label: 'Zwei' }, { wert: 'c', label: 'Drei' }], wert, onWahl: (w) => { wert = w; gewaehlt.push(w); el.requestUpdate(); } }));
  const g = el.shadowRoot.querySelector('.seg2');
  assert.equal(g.getAttribute('role'), 'group');
  assert.equal(g.getAttribute('aria-label'), 'Was?');
  const knoepfe = () => [...g.querySelectorAll('button')];
  assert.deepEqual(knoepfe().map((k) => k.textContent), ['Eins', 'Zwei', 'Drei']);
  assert.deepEqual(knoepfe().map((k) => k.getAttribute('aria-pressed')), ['true', 'false', 'false']);
  knoepfe()[2].click();
  await el.updateComplete;
  assert.deepEqual(knoepfe().map((k) => k.getAttribute('aria-pressed')), ['false', 'false', 'true']);
  const e = taste(knoepfe()[2], 'ArrowLeft');
  await el.updateComplete;
  assert.ok(e.defaultPrevented);
  assert.equal(wert, 'b');
  assert.equal(el.shadowRoot.activeElement, knoepfe()[1], 'der Fokus springt zum Nachbarn');
  taste(knoepfe()[1], 'ArrowRight'); await el.updateComplete;
  assert.equal(wert, 'c');
  const davor = gewaehlt.length;
  taste(knoepfe()[2], 'ArrowRight'); taste(knoepfe()[0], 'ArrowLeft'); taste(knoepfe()[2], 'a');
  assert.equal(gewaehlt.length, davor, 'am Ende springt nichts, andere Tasten tun nichts');
  el.remove();
});

test('leererZustand: Bild, ein Satz, ein Knopf (Link oder Knopf)', MIT_DOM, async () => {
  let geklickt = 0;
  const el = await zeichne(() => b.html`${b.leererZustand({ art: 'x', bild: b.html`<svg aria-hidden="true"></svg>`, satz: 'Ein Satz.', knopf: { label: 'Weiter', href: '#bibliothek' } })}
    ${b.leererZustand({ art: 'y', bild: b.html`<svg></svg>`, satz: 'Noch einer.', knopf: { label: 'Los', onKlick: () => { geklickt += 1; } } })}`);
  const [l1, l2] = el.shadowRoot.querySelectorAll('.leer');
  assert.equal(l1.dataset.leer, 'x');
  assert.equal(l1.querySelector('.et').textContent, 'Ein Satz.');
  assert.equal(l1.querySelector('a.btn.primary').getAttribute('href'), '#bibliothek');
  l2.querySelector('button.btn.primary').click();
  assert.equal(geklickt, 1);
  assert.equal(l2.querySelectorAll('.btn').length, 1);
  el.remove();
});

test('Kachel, Schnellkachel, Listenzeile: Links auf #serie-<id>, Namen nur als Text', MIT_DOM, async () => {
  const s = { id: 'x1', name: '<i>Böse</i> Serie', art: 'hoerspiel', anzahl_folgen: 3, anzahl_tobies: 2, pruefen: true, cover_stand: null, hoerstelle: { anteil: 0.5, rest_s: 600 } };
  const el = await zeichne(() => b.html`${b.kachel(s)}${b.schnellKachel(s)}${b.listenZeile(s, { term: 'bös' })}`);
  const r = el.shadowRoot;
  for (const sel of ['.tile', '.qt', '.lrow']) assert.equal(r.querySelector(sel).getAttribute('href'), '#serie-x1', sel);
  assert.equal(r.querySelector('.tile .tn').textContent, '<i>Böse</i> Serie');
  assert.equal(r.querySelector('.tn i, .lt i, .qn i'), null, 'kein HTML aus Namen');
  assert.equal(r.querySelector('.lrow mark').textContent, 'Bös', 'Treffer in der Zeile hervorgehoben');
  assert.equal(r.querySelector('.tile .badge').textContent, 'bitte ansehen');
  assert.equal(r.querySelector('.tbadge').getAttribute('aria-label'), '2 Tobies');
  assert.equal(r.querySelector('.cover').dataset.stand, '', 'cover_stand null = kein Bild');
  assert.match(r.querySelector('.cover').getAttribute('class'), /c[1-6]/);
  assert.equal(r.querySelector('.cover .bst').textContent, '<');
  el.remove();
});

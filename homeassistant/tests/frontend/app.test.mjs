/* Tests der neuen Alltagsseite <tobibox-app> (AP A6). Aufruf: node --test homeassistant/tests/frontend
 *
 * Wie panel.test.mjs: jsdom aus npm oder aus TOBIBOX_JSDOM_DIR, Backend aus mock-hass.mjs.
 * jsdom kennt weder ResizeObserver noch <dialog>.showModal(): beides wird hier nachgebaut
 * (ResizeObserver wird von Hand „gemeldet“, das Blatt öffnet über das Attribut `open`).
 */
import test, { mock } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createMockHass, FAEHIGKEITEN } from './mock-hass.mjs';

const HIER = fileURLToPath(new URL('.', import.meta.url));
const FRONTEND = join(HIER, '../../custom_components/tobibox/frontend');
const app = await import('../../custom_components/tobibox/frontend/tobibox-app.js');
const { layoutFuerBreite, begruessung, parseRoute, kontrast, luminanz, berechneTokens, waehleTextfarbe, parseFarbe, AppStore } = app;
const texte = await import('../../custom_components/tobibox/frontend/texte.js');
const { TOBIE, LEER, fuellen } = texte;

/* ------------------------------------------------------------------ Ohne DOM: Breite, Gruß, Routen, Farben */

test('Das Modul lädt ohne DOM, nutzt Lit aus der eingecheckten Datei und nichts aus dem Netz', () => {
  assert.equal(typeof AppStore, 'function');
  assert.equal(app.VERTRAG_V, 1);
  const src = readFileSync(join(FRONTEND, 'tobibox-app.js'), 'utf8');
  assert.match(src, /import\('\.\/lit-all\.min\.js'\)/);
  assert.doesNotMatch(src, /from\s*["']https?:|import\(["']https?:|unsafeHTML/);
  assert.match(src, /import\('\.\/illustrationen\.js'\)/, 'die Illustrationen kommen nur über einen Import');
});

test('Breite des Panels: 699 und 700, 1099 und 1100 px', () => {
  assert.equal(layoutFuerBreite(320), 'unten');
  assert.equal(layoutFuerBreite(699), 'unten');
  assert.equal(layoutFuerBreite(700), 'oben');
  assert.equal(layoutFuerBreite(1099), 'oben');
  assert.equal(layoutFuerBreite(1100), 'seite');
  assert.equal(layoutFuerBreite(1600), 'seite');
});

test('Begrüßung nach Tageszeit, ohne Namen', () => {
  const um = (h) => begruessung(new Date(2026, 10, 13, h, 0));
  assert.equal(um(6), 'Guten Morgen');
  assert.equal(um(10), 'Guten Morgen');
  assert.equal(um(11), 'Guten Tag');
  assert.equal(um(16), 'Guten Tag');
  assert.equal(um(17), 'Guten Abend');
  assert.equal(um(21), 'Guten Abend');
  assert.equal(um(22), 'Gute Nacht');
  assert.equal(um(23), 'Gute Nacht');
  assert.equal(um(3), 'Guten Morgen', 'Design: „Guten Morgen“ gilt bis 11 Uhr, „Gute Nacht“ erst ab 22');
});

test('Routen: Reiter, Unterseiten, Umleitungen', () => {
  assert.deepEqual([parseRoute('').name, parseRoute('#start').tab], ['start', 'start']);
  for (const t of ['bibliothek', 'tobies', 'geraete']) assert.equal(parseRoute(`#${t}`).tab, t);
  assert.equal(parseRoute('#serie-abc').tab, 'bibliothek');
  assert.equal(parseRoute('#serie-abc').id, 'abc');
  assert.equal(parseRoute('#suche').tab, 'bibliothek');
  assert.equal(parseRoute('#tobie-04AA').tab, 'tobies');
  assert.equal(parseRoute('#neu-ziel').tab, 'tobies');
  assert.equal(parseRoute('#box-kueche').tab, 'geraete');
  assert.equal(parseRoute('#technik-box-kueche').sub, 'box-kueche');
  assert.equal(parseRoute('#technik').tab, 'technik');
  assert.equal(parseRoute('#abends').umleitung, 'geraete');
  assert.equal(parseRoute('#mehr').umleitung, 'geraete');
  assert.equal(parseRoute('#gehoert', { faehigkeiten: ['boxen'] }).umleitung, 'geraete');
  assert.equal(parseRoute('#gehoert', { faehigkeiten: ['gehoert'] }).name, 'gehoert');
  assert.equal(parseRoute('#gehoert', { faehigkeiten: null }).name, 'gehoert', 'vor hello keine Umleitung');
  assert.equal(parseRoute('#playlist-x').umleitung, 'bibliothek');
  assert.equal(parseRoute('#unsinn').name, 'start');
});

const THEMEN = {
  hell: { bg: '#fafafa', card: '#ffffff', text: '#212121', text2: '#727272', divider: '#e0e0e0', primary: '#03a9f4', onPrimary: '#ffffff' },
  dunkel: { bg: '#111111', card: '#1c1c1c', text: '#e1e1e1', text2: '#9b9b9b', divider: '#383838', primary: '#ff9800', onPrimary: '#000000' },
  gelb: { bg: '#ffffff', card: '#ffffff', text: '#212121', text2: '#999999', divider: '#e0e0e0', primary: '#ffeb3b', onPrimary: '#ffffff' },
};

test('Kontrastfunktion und Token: Text 4,5:1, Ränder 3:1, in Hell, Dunkel und mit hellem Primärton', () => {
  assert.ok(Math.abs(kontrast('#000000', '#ffffff') - 21) < 0.01);
  assert.ok(luminanz('#ffffff') > luminanz('#808080'));
  assert.deepEqual(parseFarbe('rgb(1, 2, 3)'), [1, 2, 3]);
  assert.equal(parseFarbe('var(--x)'), null);
  for (const [name, eingabe] of Object.entries(THEMEN)) {
    const t = berechneTokens(eingabe);
    const flaechen = [t['--bg'], t['--card'], t['--primary-soft']];
    for (const f of flaechen) {
      assert.ok(kontrast(t['--text'], f) >= 4.5, `${name}: Text auf ${f}`);
      assert.ok(kontrast(t['--text2'], f) >= 4.5, `${name}: Nebentext auf ${f}`);
      assert.ok(kontrast(t['--primary-ink'], f) >= 4.5, `${name}: Primärton als Schrift auf ${f}`);
      assert.ok(kontrast(t['--line'], f) >= 3, `${name}: Rand auf ${f}`);
    }
    assert.ok(kontrast(t['--on-primary'], t['--primary']) >= 4.5, `${name}: Knopfschrift`);
    for (const [fg, bgk] of [['--ok', '--ok-bg'], ['--warn', '--warn-bg'], ['--danger', '--danger-bg']]) {
      for (const f of [t[bgk], t['--bg'], t['--card']]) assert.ok(kontrast(t[fg], f) >= 4.5, `${name}: ${fg} auf ${f}`);
    }
    assert.ok(kontrast(t['--focus'], t['--card']) >= 3, `${name}: Fokusring`);
  }
  // Das helle Gelb: weiße Schrift auf Gelb fällt durch, die Funktion nimmt Schwarz; die Linkfarbe wird dunkel.
  assert.equal(waehleTextfarbe('#ffeb3b', '#ffffff'), '#000000');
  assert.equal(berechneTokens(THEMEN.gelb)['--on-primary'], '#000000');
  assert.notEqual(berechneTokens(THEMEN.gelb)['--primary-ink'], '#ffeb3b');
  assert.equal(berechneTokens(THEMEN.dunkel)['color-scheme'], 'dark');
  assert.equal(berechneTokens({})['color-scheme'], 'light', 'ohne Angaben gelten die Vorgaben');
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
let App = null;
let dom = null;

/* Nachgebauter ResizeObserver: `FakeRO.melde(breite)` löst alle offenen Beobachter aus. */
class FakeRO {
  static alle = new Set();
  constructor(cb) { this.cb = cb; FakeRO.alle.add(this); }
  observe(ziel) { this.ziel = ziel; }
  disconnect() { FakeRO.alle.delete(this); }
  static melde(breite) { for (const r of [...FakeRO.alle]) r.cb([{ contentRect: { width: breite } }]); }
}

async function domBereit() {
  if (App) return;
  dom = new jsdom.JSDOM('<!doctype html><body></body>', { pretendToBeVisual: true, url: 'https://ha.test/tobibox' });
  const w = dom.window;
  for (const k of ['window', 'document', 'HTMLElement', 'customElements', 'Node', 'NodeFilter', 'Document', 'ShadowRoot', 'CSSStyleSheet', 'Element', 'Event', 'CustomEvent', 'DocumentFragment', 'Comment', 'Text', 'HTMLTemplateElement', 'MutationObserver', 'getComputedStyle']) {
    globalThis[k] = w[k];
  }
  globalThis.ResizeObserver = FakeRO;
  // <dialog> kennt jsdom nur als Hülle: showModal setzt `open`, close löscht es und meldet „close“.
  const P = w.HTMLDialogElement.prototype;
  P.showModal = function showModal() { this.setAttribute('open', ''); };
  P.close = function close() { if (this.hasAttribute('open')) { this.removeAttribute('open'); this.dispatchEvent(new w.Event('close')); } };
  await import('../../custom_components/tobibox/frontend/tobibox-app.js?dom');
  App = w.customElements.get('tobibox-app');
  assert.ok(App, 'tobibox-app ist als Custom Element registriert');
}

const tick = () => new Promise((r) => setTimeout(r, 0));
const offene = [];

/* Seite mit Mock-Backend. opts: Mock-Optionen; breite: Panelbreite; hash; narrow. */
async function seite({ breite = 390, hash = '', narrow = false, ...mockOpts } = {}) {
  await domBereit();
  window.history.replaceState(null, '', `/tobibox${hash}`);
  const m = createMockHass({ faehigkeiten: [...FAEHIGKEITEN], ...mockOpts });
  const el = new App();
  el.narrow = narrow;
  document.body.appendChild(el);
  offene.push(el);
  FakeRO.melde(breite);
  el.hass = m.hass;
  const flush = async () => { for (let i = 0; i < 4; i += 1) { await tick(); await el.updateComplete; } };
  await flush();
  const q = (sel) => el.shadowRoot.querySelector(sel);
  const qa = (sel) => [...el.shadowRoot.querySelectorAll(sel)];
  return { el, m, q, qa, flush };
}

function weg() { while (offene.length) offene.pop().remove(); }

/* Eingabe-Ereignis mit Koordinaten (jsdom kennt PointerEvent nur teilweise). */
function zeiger(ziel, art, felder = {}) {
  const e = new window.Event(art, { bubbles: true, cancelable: true });
  for (const [k, v] of Object.entries({ pointerId: 1, button: 0, clientX: 0, clientY: 0, ...felder })) Object.defineProperty(e, k, { value: v });
  ziel.dispatchEvent(e);
  return e;
}

const tabs = (qa) => qa('nav[aria-label="Bereiche"] a').map((a) => a.querySelector('.tn').textContent);
const aktiv = (qa) => qa('nav[aria-label="Bereiche"] a[aria-current="page"]').map((a) => a.querySelector('.tn').textContent);

async function geheZu(s, hash) {
  window.location.hash = hash;
  await new Promise((r) => setTimeout(r, 20));
  await s.flush();
}

test('Reiter: vier, in der Reihenfolge des Designs, mit aria-current am aktiven', MIT_DOM, async () => {
  const s = await seite();
  assert.equal(s.qa('nav[aria-label="Bereiche"]').length, 1);
  assert.deepEqual(tabs(s.qa), ['Start', 'Bibliothek', 'Tobies', 'Geräte']);
  assert.deepEqual(aktiv(s.qa), ['Start']);
  assert.deepEqual(s.qa('nav a').map((a) => a.getAttribute('href')), ['#start', '#bibliothek', '#tobies', '#geraete']);
  await geheZu(s, '#bibliothek');
  assert.deepEqual(aktiv(s.qa), ['Bibliothek']);
  assert.equal(s.q('main h2').textContent, 'Bibliothek');
  await geheZu(s, '#serie-abc');
  assert.deepEqual(aktiv(s.qa), ['Bibliothek'], 'eine Unterseite hält ihren Reiter markiert');
  assert.equal(s.q('main .back').getAttribute('href'), '#bibliothek');
  assert.equal(s.q('main .back').textContent, '‹ Bibliothek');
  await geheZu(s, '#box-kueche');
  assert.deepEqual(aktiv(s.qa), ['Geräte']);
  assert.equal(s.q('main h2').textContent, 'Küche', 'Name der Box');
  weg();
});

test('Routen: #mehr und #abends führen nach #geraete, #gehoert nur mit Fähigkeit', MIT_DOM, async () => {
  const s = await seite();
  await geheZu(s, '#abends');
  assert.equal(window.location.hash, '#geraete');
  assert.deepEqual(aktiv(s.qa), ['Geräte']);
  await geheZu(s, '#mehr');
  assert.equal(window.location.hash, '#geraete');
  await geheZu(s, '#gehoert');
  assert.equal(window.location.hash, '#geraete', 'ohne Fähigkeit gehoert zurück nach Geräte');
  await geheZu(s, '#playlist-x');
  assert.equal(window.location.hash, '#bibliothek');
  weg();
  const mit = await seite({ faehigkeiten: [...FAEHIGKEITEN, 'gehoert'], hash: '#gehoert' });
  assert.equal(window.location.hash, '#gehoert');
  assert.equal(mit.q('main h2').textContent, 'Gehört');
  assert.equal(mit.q('main .back').textContent, '‹ Geräte');
  assert.deepEqual(aktiv(mit.qa), ['Geräte']);
  weg();
});

test('Technik: Administrator hat das Symbol und die Seite, Nicht-Administrator weder noch', MIT_DOM, async () => {
  const admin = await seite({ hash: '#technik' });
  assert.ok(admin.q('.kopf a[aria-label="Technik"]'));
  assert.equal(admin.q('main h2').textContent, 'Technik');
  assert.equal(admin.q('.kopf a[aria-label="Technik"]').getAttribute('aria-current'), 'page');
  assert.equal(admin.qa('nav a[aria-current="page"]').length, 0);
  weg();
  const user = await seite({ darf: false });
  assert.equal(user.q('a[aria-label="Technik"]'), null);
  assert.equal(user.q('[aria-label="Technik"]'), null);
  assert.deepEqual(tabs(user.qa), ['Start', 'Bibliothek', 'Tobies', 'Geräte']);
  await geheZu(user, '#technik');
  assert.equal(user.q('[data-zustand="nur-admin"]').textContent.trim(), 'Dieser Bereich ist nur für Administratoren. Wenn du etwas Technisches brauchst, frag den Administrator.');
  assert.equal(user.q('a[aria-label="Technik"]'), null);
  await geheZu(user, '#technik-boxen');
  assert.ok(user.q('[data-zustand="nur-admin"]'));
  weg();
});

test('Kopf: Begrüßung auf dem Start, sonst der Seitentitel (nie „Tobi Box“ und Seitentitel zugleich), Suchen nur auf Start und Bibliothek, Menüknopf bei narrow', MIT_DOM, async () => {
  const s = await seite({ narrow: true });
  assert.equal(s.q('.kopf h1').textContent, begruessung());
  assert.ok(s.q('.kopf a[aria-label="Suchen"]'));
  assert.ok(s.q('.kopf ha-menu-button'));
  const rund = s.qa('.kopf .rund');
  assert.ok(rund.length >= 2);
  await geheZu(s, '#tobies');
  assert.equal(s.q('.kopf h1').textContent, 'Tobies');
  assert.equal(s.q('.kopf a[aria-label="Suchen"]'), null);
  assert.equal(s.qa('h1, h2').filter((h) => h.textContent.trim() === 'Tobies' && h.closest('main') && !h.hasAttribute('data-doppelt')).length, 0, 'die Überschrift im Inhalt ist nicht noch einmal sichtbar');
  await geheZu(s, '#geraete');
  assert.equal(s.q('.kopf h1').textContent, 'Geräte');
  assert.ok(s.q('main h2[data-doppelt]'), 'Überschrift im Inhalt bleibt für Screenreader, wird aber nicht gezeigt');
  assert.equal(s.qa('.kopf h1').filter((h) => h.textContent.includes('Tobi Box')).length, 0);
  weg();
  const ohne = await seite({ narrow: false });
  assert.equal(ohne.q('ha-menu-button'), null);
  weg();
});

test('Breite des Panels: 699, 700, 1099 und 1100 px schalten Reiter unten, oben, Seitenleiste', MIT_DOM, async () => {
  const s = await seite({ breite: 699 });
  const pos = (n) => n.compareDocumentPosition(s.q('main'));
  assert.equal(s.el.getAttribute('data-layout'), 'unten');
  assert.ok(pos(s.q('nav')) & dom.window.Node.DOCUMENT_POSITION_PRECEDING, 'unten: nach dem Inhalt'); // main liegt vor nav
  assert.ok(s.q('.kopf'));
  FakeRO.melde(700); await s.flush();
  assert.equal(s.el.getAttribute('data-layout'), 'oben');
  assert.ok(pos(s.q('nav')) & dom.window.Node.DOCUMENT_POSITION_FOLLOWING, 'oben: vor dem Inhalt');
  assert.ok(s.q('.kopf'));
  assert.equal(s.qa('nav').length, 1);
  FakeRO.melde(1099); await s.flush();
  assert.equal(s.el.getAttribute('data-layout'), 'oben');
  FakeRO.melde(1100); await s.flush();
  assert.equal(s.el.getAttribute('data-layout'), 'seite');
  assert.ok(s.q('aside.seite nav[aria-label="Bereiche"]'), 'Reiter liegen in der Seitenleiste');
  assert.ok(s.q('.kopf h1'), 'am Computer steht der große Seitentitel im Kopf');
  assert.equal(s.q('aside.seite .marke').textContent, 'Tobi Box');
  assert.equal(s.q('aside.seite a[href="#hinzufuegen"]').textContent.trim(), 'Hinzufügen', 'ruhige Zeile mit Symbol und Text (Design 3.1)');
  assert.equal(s.q('aside.seite a.tech').textContent.trim(), 'Technik');
  assert.equal(s.q('.kopf a.tech'), null, 'Technik steht am Computer nur in der Seitenleiste');
  assert.equal(s.q('aside.seite .rund'), null, 'keine runden Einzelknöpfe in der Seitenleiste');
  assert.equal(s.qa('nav').length, 1);
  assert.deepEqual(tabs(s.qa), ['Start', 'Bibliothek', 'Tobies', 'Geräte']);
  FakeRO.melde(699); await s.flush();
  assert.equal(s.el.getAttribute('data-layout'), 'unten');
  assert.equal(s.q('aside'), null);
  weg();
  const n = await seite({ breite: 1100, darf: false });
  assert.equal(n.q('aside.seite a[aria-label="Technik"]'), null, 'auch in der Seitenleiste kein Technik-Symbol für Nicht-Administratoren');
  weg();
});

test('Platz für den Mini-Player: versteckt, zwischen Inhalt und Leiste, mit --minih', MIT_DOM, async () => {
  const s = await seite({ breite: 390 });
  const mini = s.q('.mini');
  assert.ok(mini && mini.hidden);
  assert.ok(mini.nextElementSibling.matches('nav.tabs'), 'bündig über der Leiste');
  assert.ok(mini.previousElementSibling.matches('.rahmen'), 'unter dem Scrollbereich, nicht darin (immer am unteren Rand)');
  assert.ok(!s.q('.rahmen').contains(mini));
  assert.equal(s.el.miniPlatz, mini);
  s.el.setMini(true);
  assert.equal(mini.hidden, false);
  assert.equal(s.el.style.getPropertyValue('--minih'), '64px');
  s.el.setMini(false);
  assert.equal(mini.hidden, true);
  s.el.setMini(true);
  FakeRO.melde(1280); await s.flush();
  assert.equal(s.q('.mini').hidden, false, 'Zustand überlebt den Wechsel in die Seitenleisten-Ansicht');
  assert.ok(s.q('.spalte').contains(s.q('.mini')));
  s.el.setMini(false);
  assert.equal(s.el.style.getPropertyValue('--minih'), '0px');
  weg();
});

test('Bei offener Tastatur verschwinden Leiste und Mini-Player (visualViewport)', MIT_DOM, async () => {
  await domBereit();
  window.visualViewport = { height: 300, addEventListener() {}, removeEventListener() {} };
  const s = await seite();
  const feld = document.createElement('input');
  s.q('main').appendChild(feld);
  feld.focus();
  feld.dispatchEvent(new window.Event('focusin', { bubbles: true, composed: true }));
  await s.flush();
  assert.ok(s.q('.app').hasAttribute('data-kbd'));
  weg();
  delete window.visualViewport;
});

/* ------------------------------------------------------------------ Abo, Zustände */

test('Start: hello mit v=1, Abo der Themen über hass.connection, Listen laden', MIT_DOM, async () => {
  const s = await seite();
  const hello = s.m.aufrufe('tobibox/hello');
  assert.equal(hello.length, 1);
  assert.equal(hello[0].v, 1);
  const abo = s.m.calls.find((c) => c.abo);
  assert.equal(abo.type, 'tobibox/subscribe');
  assert.deepEqual(abo.msg.themen, ['boxen', 'neue_tobies', 'konfig', 'eingang']); // A11b: `eingang` für Band und Punkt am Reiter „Bibliothek“
  assert.equal(s.m.aufrufe('tobibox/neue_tobies/list').length, 1);
  assert.equal(s.m.aufrufe('tobibox/boxen/list').length, 1);
  assert.equal(s.m.aufrufe('tobibox/medien/pruefen').length, 0, 'das Gerüst stößt nichts an');
  assert.equal(s.el.store.s.phase, 'bereit');
  weg();
  // Trennen: das Abo wird beendet
  const t = await seite();
  const abo2 = t.m.subs.at(-1);
  assert.equal(abo2.aktiv, true);
  t.el.remove();
  assert.equal(abo2.aktiv, false);
  offene.length = 0;
});

test('Lädt: Platzhalter, nach der Zeitgrenze der Fehlerzustand mit „Noch einmal versuchen“', MIT_DOM, async () => {
  await domBereit();
  const m = createMockHass({ faehigkeiten: [...FAEHIGKEITEN] });
  m.on('tobibox/hello', () => new Promise(() => {}));
  const el = new App();
  el.store.ladeGrenzeMs = 40;
  document.body.appendChild(el); offene.push(el);
  FakeRO.melde(390);
  el.hass = m.hass;
  await tick(); await el.updateComplete;
  const sr = el.shadowRoot;
  assert.ok(sr.querySelector('.laedt .skel'), 'graue Platzhalter statt „Lade …“');
  assert.equal(sr.querySelector('.laedt').getAttribute('aria-busy'), 'true');
  assert.equal(sr.querySelector('main').textContent.includes('Lade'), false);
  await new Promise((r) => setTimeout(r, 80)); await el.updateComplete;
  const k = sr.querySelector('[data-zustand="fehler"]');
  assert.ok(k);
  assert.equal(k.getAttribute('role'), 'alert');
  assert.match(k.textContent, /Die Seite konnte nichts laden\./);
  assert.match(k.textContent, /sag dem Administrator Bescheid\./);
  assert.equal(k.querySelector('button').textContent, 'Noch einmal versuchen');
  // Wieder versuchen, dieses Mal antwortet das Backend
  m.on('tobibox/hello', () => ({ v: 1, version: '0.1.0', darf_schreiben: true, faehigkeiten: [...FAEHIGKEITEN], boxen: [], konfig: { zustand: 'ok' }, grenzen: {} }));
  k.querySelector('button').click();
  for (let i = 0; i < 5; i += 1) { await tick(); await el.updateComplete; }
  assert.equal(sr.querySelector('[data-zustand="fehler"]'), null);
  assert.equal(el.store.s.phase, 'bereit');
  weg();
});

test('Fehler beim Laden: Fehlerkarte; „unknown_command“ ist „Seite veraltet“; Administratoren sehen den Code', MIT_DOM, async () => {
    const m = createMockHass({ faehigkeiten: [...FAEHIGKEITEN] });
  m.failNext('tobibox/hello', 'unknown_error');
  const el = new App(); document.body.appendChild(el); offene.push(el); FakeRO.melde(390);
  el.hass = m.hass;
  for (let i = 0; i < 4; i += 1) { await tick(); await el.updateComplete; }
  const f = el.shadowRoot.querySelector('[data-zustand="fehler"]');
  assert.ok(f);
  assert.match(f.textContent, /Code: unknown_error/, 'der Administrator sieht den Code');
  weg();
  const m2 = createMockHass({ faehigkeiten: [...FAEHIGKEITEN], darf: false });
  m2.failNext('tobibox/hello', 'unknown_command');
  const e2 = new App(); document.body.appendChild(e2); offene.push(e2); FakeRO.melde(390);
  e2.hass = m2.hass;
  for (let i = 0; i < 4; i += 1) { await tick(); await e2.updateComplete; }
  const v = e2.shadowRoot.querySelector('[data-zustand="veraltet"]');
  assert.ok(v);
  assert.match(v.textContent, /Die Seite ist veraltet\. Bitte lade sie neu/);
  weg();
});

test('Leere Zustände: Bild aria-hidden, ein Satz, ein Knopf; Geräte nur ohne Boxen', MIT_DOM, async () => {
  const s = await seite({ leer: true }); // A7: Start und Bibliothek zeigen Inhalte, den leeren Zustand nur ohne Einträge
  await new Promise((r) => setTimeout(r, 20)); await s.flush();
  const l = s.q('[data-leer="start"]');
  assert.ok(l);
  assert.equal(l.querySelector('.bild svg').getAttribute('aria-hidden'), 'true');
  assert.equal(l.querySelectorAll('p.et').length, 1);
  assert.equal(l.querySelector('.et').textContent, fuellen(LEER.start.satz));
  assert.equal(l.querySelectorAll('a.btn, button.btn').length, 1);
  assert.equal(l.querySelector('.btn').getAttribute('href'), '#bibliothek');
  await geheZu(s, '#bibliothek');
  assert.equal(s.q('[data-leer="bibliothek"] .btn').textContent, 'Hinzufügen');
  await geheZu(s, '#tobies');
  assert.equal(s.q('[data-leer="tobies"] .et').textContent, 'Noch keine Tobies. Lege einen Tobie auf eine Box, dann erscheint er unter „Geräte“.', 'A9: Design 6.2');
  assert.equal(s.q('[data-leer="tobies"] .btn').getAttribute('href'), '#geraete');
  assert.ok(s.q('[data-regal] a[data-neu]'), 'das Regal zeigt auch ohne Tobies die Kachel „+ Neuer Tobie“');
  await geheZu(s, '#geraete');
  assert.equal(s.q('[data-leer="keine_box"]'), null, 'es gibt Boxen');
  weg();
  const leer = await seite({ hash: '#geraete' });
  leer.m.backend.boxen = [];
  leer.el.store.s.boxen = {}; leer.el.store.s.faehigkeiten = leer.el.store.s.faehigkeiten.filter((x) => x !== 'boxen');
  await leer.el.store._ladeListen(); await leer.flush();
  const kb = leer.q('[data-leer="keine_box"]');
  assert.ok(kb);
  assert.equal(kb.querySelector('.et').textContent, 'Noch keine Box eingerichtet. Bitte dem Administrator Bescheid sagen.');
  assert.equal(kb.querySelector('.btn').textContent, 'Jetzt neu laden');
  weg();
});

test('Band „Keine Verbindung“ und „Änderungen sind gerade gesperrt“', MIT_DOM, async () => {
  await domBereit();
  const m = createMockHass({ faehigkeiten: [...FAEHIGKEITEN], darf: false });
  const ls = {};
  m.hass.connection.addEventListener = (n, f) => { ls[n] = f; };
  m.hass.connection.removeEventListener = () => {};
  const el = new App(); document.body.appendChild(el); offene.push(el); FakeRO.melde(390);
  el.hass = m.hass;
  for (let i = 0; i < 4; i += 1) { await tick(); await el.updateComplete; }
  const sr = el.shadowRoot;
  assert.equal(sr.querySelector('[data-band]'), null);
  ls.disconnected();
  await el.updateComplete;
  const b = sr.querySelector('[data-band="verbindung"]');
  assert.ok(b);
  assert.equal(b.getAttribute('role'), 'alert');
  assert.match(b.textContent, /Keine Verbindung zu Home Assistant\./);
  assert.match(b.textContent, /Jetzt neu laden/);
  ls.ready();
  for (let i = 0; i < 3; i += 1) { await tick(); await el.updateComplete; }
  assert.equal(sr.querySelector('[data-band="verbindung"]'), null);
  m.emit('konfig', 'geaendert', { konfig: { zustand: 'leer_neu' } });
  await el.updateComplete;
  assert.equal(sr.querySelector('[data-band="gesperrt"]').textContent.trim(), 'Änderungen sind gerade gesperrt. Bitte dem Administrator Bescheid sagen.');
  m.emit('konfig', 'geaendert', { konfig: { zustand: 'ok' } });
  await el.updateComplete;
  assert.equal(sr.querySelector('[data-band="gesperrt"]'), null);
  weg();
});

/* ------------------------------------------------------------------ Tokens im Element */

test('Das Element setzt die Token als Eigenschaften (auch ohne HA-Variablen)', MIT_DOM, async () => {
  const s = await seite();
  for (const k of ['--primary-ink', '--on-primary', '--line', '--primary-soft', '--danger']) assert.ok(s.el.style.getPropertyValue(k), k);
  assert.ok(kontrast(s.el.style.getPropertyValue('--text'), s.el.style.getPropertyValue('--card')) >= 4.5);
  weg();
});

/* ------------------------------------------------------------------ Blätter */

async function blattOeffnen(s, opts = {}) {
  const ausloeser = s.q('nav a[href="#bibliothek"]');
  ausloeser.focus();
  assert.equal(s.el.shadowRoot.activeElement, ausloeser);
  const zu = s.el.oeffneBlatt({ titel: 'Probeblatt', inhalt: 'Inhalt', knoepfe: [{ label: 'Abbrechen' }, { label: 'Speichern', kind: 'primary' }], ...opts });
  await s.flush();
  return { zu, ausloeser, d: s.q('dialog.blatt') };
}

test('Blatt: Aufbau mit × oben, Griff, Überschrift, Leiste unten; Fokus beim Öffnen auf der harmlosen Antwort', MIT_DOM, async () => {
  const s = await seite();
  const { d } = await blattOeffnen(s);
  assert.ok(d.hasAttribute('open'));
  assert.equal(d.getAttribute('aria-labelledby'), 'blatt-t');
  assert.equal(d.querySelector('#blatt-t').textContent, 'Probeblatt');
  assert.equal(d.querySelector('.blatt-x').getAttribute('aria-label'), 'Schließen');
  assert.ok(d.querySelector('.griff'));
  assert.deepEqual([...d.querySelectorAll('.knoepfe button')].map((b) => b.textContent), ['Abbrechen', 'Speichern']);
  assert.equal(s.el.shadowRoot.activeElement.textContent, 'Abbrechen');
  s.el.schliesseBlatt();
  await s.flush();
  weg();
});

for (const [weg_, was] of [['x', 'Knopf ×'], ['knopf', 'Knopf in der Leiste'], ['esc', 'Esc'], ['hintergrund', 'Tipp auf den Hintergrund'], ['wischen', 'Wischen nach unten'], ['route', 'Browser-Zurück']]) {
  test(`Blatt schließt per ${was}, danach open === false und der Fokus ist zurück am Auslöser`, MIT_DOM, async () => {
    const s = await seite();
    const { zu, ausloeser, d } = await blattOeffnen(s);
    if (weg_ === 'x') d.querySelector('.blatt-x').click();
    if (weg_ === 'knopf') d.querySelector('.knoepfe button').click();
    if (weg_ === 'esc') d.dispatchEvent(new window.Event('cancel', { cancelable: true }));
    if (weg_ === 'hintergrund') d.click();
    if (weg_ === 'wischen') {
      const griff = d.querySelector('.griff');
      zeiger(griff, 'pointerdown', { clientY: 100, timeStamp: 0 });
      zeiger(griff, 'pointermove', { clientY: 140, timeStamp: 50 });
      zeiger(griff, 'pointermove', { clientY: 300, timeStamp: 100 });
      assert.match(d.style.transform, /translateY\(200px\)/, 'das Blatt folgt dem Finger');
      zeiger(griff, 'pointerup', { clientY: 300, timeStamp: 120 });
    }
    if (weg_ === 'route') { window.location.hash = '#tobies'; await new Promise((r) => setTimeout(r, 20)); }
    const grund = await zu;
    await s.flush();
    assert.equal(grund, weg_);
    assert.equal(d.open, false);
    assert.equal(s.q('dialog.blatt'), null);
    if (weg_ !== 'route') assert.equal(s.el.shadowRoot.activeElement, ausloeser);
    weg();
  });
}

test('Blatt: kurzes Wischen oder Wischen nach oben schließt nicht, das Blatt springt zurück', MIT_DOM, async () => {
  const s = await seite();
  const { d } = await blattOeffnen(s);
  const griff = d.querySelector('.griff');
  Object.defineProperty(d, 'offsetHeight', { value: 400, configurable: true });
  zeiger(griff, 'pointerdown', { clientY: 100, timeStamp: 0 });
  zeiger(griff, 'pointermove', { clientY: 150, timeStamp: 500 });
  zeiger(griff, 'pointerup', { clientY: 150, timeStamp: 1000 });
  assert.ok(s.q('dialog.blatt'), 'unter 25 % und langsam: bleibt offen');
  assert.equal(d.style.transform, '');
  zeiger(griff, 'pointerdown', { clientY: 200, timeStamp: 2000 });
  zeiger(griff, 'pointermove', { clientY: 120, timeStamp: 2100 });
  zeiger(griff, 'pointerup', { clientY: 120, timeStamp: 2200 });
  assert.ok(s.q('dialog.blatt'));
  s.el.schliesseBlatt(); await s.flush();
  weg();
});

test('Blatt: ein Knopf, der false liefert, hält es offen; ein zweites Blatt ersetzt das erste', MIT_DOM, async () => {
  const s = await seite();
  let n = 0;
  const { zu, d } = await blattOeffnen(s, { knoepfe: [{ label: 'Prüfen', fn: () => { n += 1; return false; } }, { label: 'Fertig', fn: () => { n += 10; } }] });
  d.querySelectorAll('.knoepfe button')[0].click();
  await s.flush();
  assert.equal(n, 1);
  assert.ok(s.q('dialog.blatt'));
  const zweites = s.el.oeffneBlatt({ titel: 'Zweites' });
  assert.equal(await zu, 'ersetzt');
  await s.flush();
  assert.equal(s.qa('dialog.blatt').length, 1);
  assert.equal(s.q('#blatt-t').textContent, 'Zweites');
  s.q('.blatt-x').click();
  assert.equal(await zweites, 'x');
  await s.flush();
  weg();
});

test('Blatt: Inhalt aus Namen bleibt Text (kein HTML)', MIT_DOM, async () => {
  const s = await seite();
  s.el.oeffneBlatt({ titel: '<img src=x onerror="window.boese=1">', inhalt: '<b>fett</b>' });
  await s.flush();
  assert.equal(s.q('dialog img'), null);
  assert.equal(s.q('dialog .blatt-b b'), null);
  assert.ok(s.q('dialog .blatt-b').textContent.includes('<b>fett</b>'));
  assert.equal(window.boese, undefined);
  s.el.schliesseBlatt(); await s.flush();
  weg();
});

/* ------------------------------------------------------------------ Meldungen */

const toasts = (s) => [...s.el.shadowRoot.querySelectorAll('.toastbox .toast')];

test('Meldung: Erfolg verschwindet nach 4,5 s, ersetzt die vorige und hat role=status', MIT_DOM, async (t) => {
  const s = await seite();
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    s.el.melde('Gespeichert. Die Boxen bekommen es gleich.');
    assert.equal(toasts(s).length, 1);
    assert.equal(toasts(s)[0].getAttribute('role'), 'status');
    assert.equal(s.el.shadowRoot.querySelector('#live').textContent, 'Gespeichert. Die Boxen bekommen es gleich.');
    t.mock.timers.tick(4499);
    assert.equal(toasts(s).length, 1);
    s.el.melde('Zweite');
    assert.deepEqual(toasts(s).map((x) => x.textContent), ['Zweite'], 'eine neue Erfolgsmeldung ersetzt die alte');
    t.mock.timers.tick(4499);
    assert.equal(toasts(s).length, 1);
    t.mock.timers.tick(1);
    assert.equal(toasts(s).length, 0);
  } finally { t.mock.timers.reset(); }
  weg();
});

test('Meldung mit Aktion bleibt 6 s; „Rückgängig“ ruft die Aktion und sagt es an', MIT_DOM, async (t) => {
  const s = await seite();
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    let n = 0;
    s.el.melde('Löwe spielt jetzt „Abenteuer im Wald“ (vorher „Kommissar Kralle“).', { aktion: { text: TOBIE.rueckgaengig, fn: () => { n += 1; } } });
    const knopf = toasts(s)[0].querySelector('button');
    assert.equal(knopf.textContent, 'Rückgängig');
    t.mock.timers.tick(5999);
    assert.equal(toasts(s).length, 1);
    knopf.click();
    assert.equal(n, 1);
    assert.equal(toasts(s).length, 0);
    assert.equal(s.el.shadowRoot.querySelector('#live').textContent, 'Rückgängig gemacht.');
    s.el.melde('Noch eine', { aktion: { text: 'Name geben', fn() {} } });
    t.mock.timers.tick(6000);
    assert.equal(toasts(s).length, 0);
  } finally { t.mock.timers.reset(); }
  weg();
});

test('Meldung: Fehler bleiben mit „OK“ (44 px hoch im Stil), mehrere stehen übereinander, Erfolg räumt sie nicht ab', MIT_DOM, async (t) => {
  const s = await seite();
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    s.el.meldeFehler('Bitte einen Namen eingeben.');
    s.el.meldeFehler('Das kann dieser Browser nicht abspielen.');
    s.el.melde('Gespeichert.');
    assert.equal(toasts(s).length, 3);
    const fehler = toasts(s).filter((x) => x.classList.contains('err'));
    assert.equal(fehler.length, 2);
    for (const f of fehler) {
      assert.equal(f.getAttribute('role'), 'alert');
      assert.equal(f.querySelector('button').textContent, 'OK');
    }
    t.mock.timers.tick(600000);
    assert.equal(toasts(s).length, 2, 'der Erfolg ist weg, die Fehler bleiben');
    fehler[0].querySelector('button').click();
    assert.equal(toasts(s).length, 1);
    // Wegwischen: über 70 px weg, darunter bleibt sie
    const rest = toasts(s)[0];
    zeiger(rest, 'pointerdown', { clientX: 100 });
    zeiger(rest, 'pointermove', { clientX: 140 });
    zeiger(rest, 'pointerup', { clientX: 140 });
    assert.equal(toasts(s).length, 1);
    zeiger(rest, 'pointerdown', { clientX: 100 });
    zeiger(rest, 'pointermove', { clientX: 20 });
    zeiger(rest, 'pointerup', { clientX: 20 });
    assert.equal(toasts(s).length, 0);
  } finally { t.mock.timers.reset(); }
  weg();
});

test('Meldung: Der Bereich zieht in das offene Blatt und danach zurück; der Fokus wird nicht entführt', MIT_DOM, async () => {
  const s = await seite();
  const { d, ausloeser } = await blattOeffnen(s);
  const vorher = s.el.shadowRoot.activeElement;
  s.el.meldeFehler('Bitte einen Namen eingeben.');
  const box = s.q('.toastbox');
  assert.equal(box.parentNode, d, 'im Blatt');
  assert.ok(box.classList.contains('imblatt'));
  assert.equal(s.el.shadowRoot.activeElement, vorher, 'der Fokus bleibt');
  d.querySelector('.blatt-x').click();
  await s.flush();
  assert.equal(s.q('.toastbox').parentNode, s.q('.app'), 'wieder unten');
  assert.equal(s.q('.toastbox').classList.contains('imblatt'), false);
  assert.equal(toasts(s).length, 1, 'der Fehler bleibt');
  assert.equal(s.el.shadowRoot.activeElement, ausloeser);
  weg();
});

/* ------------------------------------------------------------------ Neuer Tobie, Punkt am Reiter */

const neuerEintrag = (uid, box = 'kueche', zuletzt = '2026-11-13T10:00:00Z') => ({ uid, zuerst: zuletzt, zuletzt, anzahl: 1, boxen: { [box]: { zuerst: zuletzt, zuletzt, anzahl: 1, zeit_ok: true } } });

test('Globale Meldung „Neuer Tobie auf <Box>.“ mit Knopf „Zuordnen“ aus einem Abo-Ereignis, auf jeder Seite', MIT_DOM, async () => {
  const s = await seite({ hash: '#bibliothek' });
  assert.equal(toasts(s).length, 0, 'der Snapshot und die schon wartenden lösen keine Meldung aus');
  s.m.emit('neue_tobies', 'neu', { eintrag: neuerEintrag('04AABBCCDDEEFF', 'kinderzimmer') });
  await s.flush();
  const t = toasts(s);
  assert.equal(t.length, 1);
  assert.equal(t[0].querySelector('.tmsg').textContent, 'Neuer Tobie auf Kinderzimmer.');
  assert.equal(t[0].querySelector('button').textContent, 'Zuordnen');
  assert.equal(t[0].getAttribute('role'), 'status');
  t[0].querySelector('button').click();
  assert.equal(window.location.hash, '#neu-ziel-04AABBCCDDEEFF', 'A10: die Kennung steht in der Adresse');
  await new Promise((r) => setTimeout(r, 20)); await s.flush();
  assert.equal(s.q('main h2').textContent, 'Neuer Tobie erkannt');
  assert.deepEqual(aktiv(s.qa), ['Geräte'], 'A10: der Reiter, von dem man kam (Karte oder Meldung), bleibt markiert');
  weg();
});

test('Neuer-Tobie-Meldung: nur beim ersten Auftauchen, mit dem Namen der Box der letzten Meldung, nicht auf der Warteseite', MIT_DOM, async () => {
  const s = await seite();
  const gemeldet = [];
  s.el.store.onNeuerTobie = (n) => gemeldet.push(n);
  s.m.emit('neue_tobies', 'neu', { eintrag: { uid: '04X1', zuerst: 'a', zuletzt: 'c', anzahl: 2, boxen: { kueche: { zuletzt: 'a' }, kinderzimmer: { zuletzt: 'c' } } } });
  s.m.emit('neue_tobies', 'neu', { eintrag: neuerEintrag('04X1') });
  s.m.emit('neue_tobies', 'aktualisiert', { eintrag: neuerEintrag('04X1') });
  s.m.emit('neue_tobies', 'neu', { eintrag: neuerEintrag('0499887766554433') }); // stand schon beim Start in der Liste
  assert.equal(gemeldet.length, 1);
  assert.deepEqual([gemeldet[0].uid, gemeldet[0].box, gemeldet[0].anzeige], ['04X1', 'kinderzimmer', 'Kinderzimmer']);
  weg();
  const w = await seite({ hash: '#neu-warten' });
  w.m.emit('neue_tobies', 'neu', { eintrag: neuerEintrag('04WARTEN1') });
  await w.flush();
  assert.equal(toasts(w).length, 0, 'auf der Warteseite nimmt die Seite selbst den Tobie');
  weg();
});

test('Punkt am Reiter „Geräte“ mit Zahl und Text für Screenreader', MIT_DOM, async () => {
  const s = await seite();
  const punkt = () => s.qa('nav a').map((a) => [a.querySelector('.tn').textContent, a.querySelector('.dot')?.textContent ?? null, a.querySelector('.sr')?.textContent ?? null]);
  assert.deepEqual(punkt(), [['Start', null, null], ['Bibliothek', null, null], ['Tobies', null, null], ['Geräte', '1', '1 neuer Tobie']], 'eine unbekannte Kennung wartet');
  assert.equal(s.q('nav .dot').getAttribute('aria-hidden'), 'true');
  s.m.emit('neue_tobies', 'neu', { eintrag: neuerEintrag('04ZWEI') });
  await s.flush();
  assert.deepEqual(punkt()[3], ['Geräte', '2', '2 neue Tobies']);
  s.m.emit('neue_tobies', 'entfernt', { uid: '04ZWEI', grund: 'zugeordnet' });
  s.m.emit('neue_tobies', 'entfernt', { uid: '0499887766554433', grund: 'verworfen' });
  await s.flush();
  assert.deepEqual(punkt()[3], ['Geräte', null, null]);
  assert.equal(s.qa('nav .dot').length, 0);
  weg();
});

test('Auch in der Seitenleiste steht der Punkt am Reiter „Geräte“', MIT_DOM, async () => {
  const s = await seite({ breite: 1280 });
  assert.equal(s.q('aside nav a[href="#geraete"] .dot').textContent, '1');
  weg();
});

/* ------------------------------------------------------------------ B1: HA setzt die Adresse mit pushState und meldet `location-changed` */

test('B1: Seitenwechsel auch ohne hashchange (HA: pushState und location-changed), popstate; Fokus nur bei neuer Adresse; Abmelden beim Entfernen', MIT_DOM, async () => {
  const warte = (ms) => new Promise((r) => setTimeout(r, ms));
  const s = await seite({ hash: '#start' });
  assert.ok(s.q('nav a[href="#bibliothek"]'));
  // wie HA: Klick abfangen, pushState, dann location-changed (kein hashchange)
  window.history.pushState(null, '', '/tobibox#bibliothek');
  window.dispatchEvent(new window.CustomEvent('location-changed'));
  await warte(20); await s.flush();
  assert.equal(s.q('main h2').textContent, 'Bibliothek', 'Seite gewechselt');
  assert.equal(s.q('nav a[aria-current="page"]').getAttribute('href'), '#bibliothek');
  window.history.pushState(null, '', '/tobibox#geraete');
  window.dispatchEvent(new window.CustomEvent('location-changed'));
  await warte(20); await s.flush();
  assert.equal(s.q('main h2').textContent, 'Geräte');
  // popstate (Zurück-Taste von Hand ausgelöst)
  window.history.replaceState(null, '', '/tobibox#tobies');
  window.dispatchEvent(new window.Event('popstate'));
  await warte(20); await s.flush();
  assert.equal(s.q('nav a[aria-current="page"]').getAttribute('href'), '#tobies');
  // dieselbe Adresse noch einmal (popstate und hashchange zusammen): Fokus wird nicht erneut gesetzt
  s.q('main').blur?.();
  const zaehl = { n: 0 };
  const alt = s.q('main').focus.bind(s.q('main'));
  s.q('main').focus = (...a) => { zaehl.n += 1; return alt(...a); };
  window.dispatchEvent(new window.Event('popstate'));
  window.dispatchEvent(new window.Event('hashchange'));
  await warte(20); await s.flush();
  assert.equal(zaehl.n, 0, 'Fokus nur, wenn sich die Adresse geändert hat');
  weg();
  // nach dem Entfernen reagiert die App nicht mehr
  window.history.pushState(null, '', '/tobibox#start');
  window.dispatchEvent(new window.CustomEvent('location-changed'));
});

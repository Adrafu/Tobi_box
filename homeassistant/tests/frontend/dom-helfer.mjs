/* Gemeinsame Werkzeuge für die jsdom-Tests der Seiten (A7: start.test.mjs, bibliothek.test.mjs, bausteine.test.mjs).
 *
 * jsdom aus npm oder aus TOBIBOX_JSDOM_DIR. jsdom kennt weder ResizeObserver noch IntersectionObserver noch
 * <dialog>.showModal(): hier nachgebaut (ResizeObserver und IntersectionObserver werden von Hand „gemeldet“,
 * das Blatt öffnet über das Attribut `open`). `URL.createObjectURL` liefert `blob:mock-<n>`.
 * Jede Testdatei läuft in einem eigenen Prozess; die App wird erst nach dem DOM geladen.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { createMockHass, FAEHIGKEITEN } from './mock-hass.mjs';

async function ladeJsdom() {
  try { return await import('jsdom'); } catch { /* weiter */ }
  if (process.env.TOBIBOX_JSDOM_DIR) {
    try { return createRequire(join(process.env.TOBIBOX_JSDOM_DIR, 'x.js'))('jsdom'); } catch { /* weiter */ }
  }
  return null;
}
export const jsdom = await ladeJsdom();
export const MIT_DOM = { skip: jsdom ? false : 'jsdom nicht verfügbar (TOBIBOX_JSDOM_DIR setzen oder npm i jsdom)' };

export class FakeRO {
  static alle = new Set();
  constructor(cb) { this.cb = cb; FakeRO.alle.add(this); }
  observe(ziel) { this.ziel = ziel; }
  disconnect() { FakeRO.alle.delete(this); }
  static melde(breite) { for (const r of [...FakeRO.alle]) r.cb([{ contentRect: { width: breite } }]); }
}

/* IntersectionObserver zum Anfassen: `FakeIO.zeige(ziel)` meldet „sichtbar“. Ein erneutes `observe` meldet den Zustand
 * wie beim echten Beobachter noch einmal, wenn das Ziel schon sichtbar ist (`FakeIO.sichtbar`). */
export class FakeIO {
  static alle = new Set();
  static sichtbar = new Set();
  static beobachtet = [];
  constructor(cb, opts) { this.cb = cb; this.opts = opts; this.ziele = new Set(); FakeIO.alle.add(this); }
  observe(ziel) { FakeIO.alle.add(this); this.ziele.add(ziel); FakeIO.beobachtet.push(ziel); if (FakeIO.sichtbar.has(ziel)) this.cb([{ target: ziel, isIntersecting: true }]); }
  unobserve(ziel) { this.ziele.delete(ziel); }
  disconnect() { this.ziele.clear(); }
  static zeige(ziel) { FakeIO.sichtbar.add(ziel); for (const io of [...FakeIO.alle]) if (io.ziele.has(ziel)) io.cb([{ target: ziel, isIntersecting: true }]); }
  static verberge(ziel) { FakeIO.sichtbar.delete(ziel); }
  static zuruecksetzen() { FakeIO.alle.clear(); FakeIO.sichtbar.clear(); FakeIO.beobachtet = []; }
}

export let dom = null;
export let App = null;
let blobZaehler = 0;

export async function domBereit() {
  if (App) return;
  dom = new jsdom.JSDOM('<!doctype html><body></body>', { pretendToBeVisual: true, url: 'https://ha.test/tobibox' });
  const w = dom.window;
  for (const k of ['window', 'document', 'HTMLElement', 'customElements', 'Node', 'NodeFilter', 'Document', 'ShadowRoot', 'CSSStyleSheet', 'Element', 'Event', 'CustomEvent', 'DocumentFragment', 'Comment', 'Text', 'HTMLTemplateElement', 'MutationObserver', 'getComputedStyle', 'KeyboardEvent']) {
    globalThis[k] = w[k];
  }
  globalThis.ResizeObserver = FakeRO;
  URL.createObjectURL = () => `blob:mock-${++blobZaehler}`;
  const P = w.HTMLDialogElement.prototype;
  P.showModal = function showModal() { this.setAttribute('open', ''); };
  P.close = function close() { if (this.hasAttribute('open')) { this.removeAttribute('open'); this.dispatchEvent(new w.Event('close')); } };
  await import('../../custom_components/tobibox/frontend/tobibox-app.js?dom');
  App = w.customElements.get('tobibox-app');
  assert.ok(App, 'tobibox-app ist als Custom Element registriert');
}

/* Ein-/ausschalten des IntersectionObservers für Seiten, die danach neu angelegt werden. */
export function mitIO(an) {
  if (an) globalThis.IntersectionObserver = FakeIO;
  else delete globalThis.IntersectionObserver;
  FakeIO.zuruecksetzen();
}

export const tick = () => new Promise((r) => setTimeout(r, 0));
export const warte = (ms) => new Promise((r) => setTimeout(r, ms));
const offene = [];
export function weg() { while (offene.length) offene.pop().remove(); }

/* Seite mit Mock-Backend. opts: Mock-Optionen (`viele`, `leer`, `darf`, `faehigkeiten` …); breite: Panelbreite; hash; narrow. */
export async function seite({ breite = 390, hash = '', narrow = false, ...mockOpts } = {}) {
  await domBereit();
  window.history.replaceState(null, '', `/tobibox${hash}`);
  const m = createMockHass({ faehigkeiten: [...FAEHIGKEITEN], ...mockOpts });
  const el = new App();
  el.narrow = narrow;
  if (mockOpts.ladeGrenzeMs) el.store.ladeGrenzeMs = mockOpts.ladeGrenzeMs;
  document.body.appendChild(el);
  offene.push(el);
  FakeRO.melde(breite);
  el.hass = m.hass;
  const flush = async (n = 6) => { for (let i = 0; i < n; i += 1) { await tick(); await el.updateComplete; } };
  await flush();
  const q = (sel) => el.shadowRoot.querySelector(sel);
  const qa = (sel) => [...el.shadowRoot.querySelectorAll(sel)];
  return { el, m, q, qa, flush };
}

export async function geheZu(s, hash) {
  window.location.hash = hash;
  await warte(20);
  await s.flush();
}

/* Tastendruck auf ein Element (jsdom: KeyboardEvent mit key). */
export function taste(ziel, key) {
  const e = new window.KeyboardEvent('keydown', { key, bubbles: true, cancelable: true });
  ziel.dispatchEvent(e);
  return e;
}

/* Text ins Suchfeld schreiben und das Eingabe-Ereignis auslösen. */
export function tippe(feld, text) {
  feld.value = text;
  feld.dispatchEvent(new window.Event('input', { bubbles: true }));
}

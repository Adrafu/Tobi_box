/* Gemeinsame Werkzeuge der Player-Tests (player.test.mjs, player_bewegung.test.mjs; Pakete A8b, A8e, A7c, A8m).
 *
 * jsdom spielt nichts ab: `HTMLMediaElement` wird hier durch einen Zustand je Element ersetzt (`currentTime`, `duration`, `paused`, `ended`,
 * `playbackRate`, `play`, `pause`, `load`). `lade(el, dauer)` meldet `loadedmetadata`, `zeit(el, t)` ein `timeupdate`, `ende(el)` das Ende.
 */
import { seite, geheZu, domBereit } from './dom-helfer.mjs';
import { FAEHIGKEITEN } from './mock-hass.mjs';

export const REIN = [...FAEHIGKEITEN, 'reinhoeren'];

/* Falsches `HTMLMediaElement`; gibt die Liste der Aufrufe zurück (`play`, `pause`, `load` mit dem Element). Mit `zurueck()` wieder wegräumen. */
export async function mockAudio() {
  await domBereit();
  const P = window.HTMLMediaElement.prototype;
  const alt = {};
  const namen = ['currentTime', 'duration', 'paused', 'ended', 'playbackRate', 'defaultPlaybackRate', 'play', 'pause', 'load', 'canPlayType'];
  for (const n of namen) alt[n] = Object.getOwnPropertyDescriptor(P, n);
  const st = new WeakMap();
  const z = (el) => { if (!st.has(el)) st.set(el, { t: 0, d: NaN, paused: true, ended: false, rate: 1 }); return st.get(el); };
  const aufrufe = [];
  const def = (n, d) => Object.defineProperty(P, n, { configurable: true, ...d });
  def('currentTime', { get() { return z(this).t; }, set(v) { z(this).t = v; } });
  def('duration', { get() { return z(this).d; } });
  def('paused', { get() { return z(this).paused; } });
  def('ended', { get() { return z(this).ended; } });
  def('playbackRate', { get() { return z(this).rate; }, set(v) { z(this).rate = v; } });
  def('defaultPlaybackRate', { get() { return z(this).rate; }, set(v) { z(this).rate = v; } });
  def('play', { value() { aufrufe.push({ art: 'play', el: this }); z(this).paused = false; z(this).ended = false; this.dispatchEvent(new window.Event('play')); return Promise.resolve(); } });
  def('pause', { value() { aufrufe.push({ art: 'pause', el: this }); if (!z(this).paused) { z(this).paused = true; this.dispatchEvent(new window.Event('pause')); } } });
  def('load', { value() { aufrufe.push({ art: 'load', el: this }); z(this).t = 0; z(this).d = NaN; z(this).ended = false; z(this).paused = true; } });
  def('canPlayType', { value() { return 'maybe'; } });
  return {
    aufrufe,
    zustand: z,
    zurueck() { for (const n of namen) { if (alt[n]) Object.defineProperty(P, n, alt[n]); else delete P[n]; } },
  };
}

/* Datei fertig geladen: Länge setzen, `loadedmetadata` melden. */
export function lade(el, dauer) { Object.defineProperty(el, 'duration', { configurable: true, get: () => dauer }); el.dispatchEvent(new window.Event('loadedmetadata')); }
/* Die Wiedergabe steht bei t Sekunden (`timeupdate`). */
export function zeit(el, t) { el.currentTime = t; el.dispatchEvent(new window.Event('timeupdate')); }
/* Das Ende der Datei: erst `pause` (wie im Browser), dann `ended`. */
export function ende(el, dauer) {
  el.currentTime = dauer;
  Object.defineProperty(el, 'ended', { configurable: true, get: () => true });
  Object.defineProperty(el, 'paused', { configurable: true, get: () => true });
  el.dispatchEvent(new window.Event('pause'));
  el.dispatchEvent(new window.Event('ended'));
  delete el.ended; delete el.paused;
}

/* Eingabe-Ereignis mit Koordinaten (jsdom kennt PointerEvent nur teilweise). */
export function zeiger(ziel, art, felder = {}) {
  const e = new window.Event(art, { bubbles: true, cancelable: true });
  for (const [k, v] of Object.entries({ pointerId: 1, button: 0, clientX: 0, clientY: 0, timeStamp: 0, ...felder })) Object.defineProperty(e, k, { value: v, configurable: true });
  ziel.dispatchEvent(e);
  return e;
}

/* Die Serie s1 des Mocks mit Dauern, dazu eine Ordner-Folge „buch“ mit drei Tracks und ein Einzeltitel. */
export function beispiele(m) {
  const b = m.backend.serien;
  const folge = (name, anzeige, extra = {}) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * 1048576, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });
  b.s1.cover_stand = 'ab12cd34';
  b.s1.art = 'hoerspiel';
  b.s1.folgen.forEach((f, i) => { f.dauer_s = 120 + i * 10; });
  b.buch = { id: 'buch', name: 'Das große Buch', typ: 'normal', ordner: 'Buch', pruefen: false, hinweise: [], art: 'hoerbuch', dauer_s: 300, cover_stand: null,
    folgen: [folge('buch', 'Das große Buch', { art: 'ordner', tracks: 3, dauer_s: 300, spuren_s: [100, 120, 80] })] };
  b.lied = { id: 'lied', name: 'Wiegenlied', typ: 'normal', ordner: 'Lied', pruefen: false, hinweise: [], art: 'musik', einzeln: true, dauer_s: 66, cover_stand: null,
    folgen: [folge('wiegenlied.mp3', 'Wiegenlied', { dauer_s: 66 })] };
  b['sonder'] = { id: 'sonder', name: 'Sonderzeichen', typ: 'normal', ordner: 'Sonder', pruefen: false, hinweise: [], art: 'hoerspiel', cover_stand: null,
    folgen: [folge('Teil 1 #2 (Ende)?.mp3', 'Teil 1', { dauer_s: 60 }), folge('100% Mond+Sterne&Rest.mp3', 'Teil 2', { dauer_s: 60 })] };
}

/* App mit Reinhören; öffnet optional eine Serienseite. */
export async function spielSeite({ hash = '', ...opts } = {}) {
  const s = await seite({ hash: '', faehigkeiten: REIN, ...opts });
  beispiele(s.m);
  if (hash) { await geheZu(s, hash); await s.flush(10); }
  s.audio = () => s.el.spieler._audio;
  s.sp = s.el.spieler;
  return s;
}

/* Reinhören starten und das Laden der Datei melden; gibt das Audio-Element zurück. */
export async function starteSerie(s, dauer = 120) {
  s.q('[data-reinhoeren]').click();
  await s.flush(12);
  const a = s.audio();
  lade(a, dauer);
  await s.flush(8);
  return a;
}

/* Nur Mikroaufgaben abwarten (für Tests mit nachgebauten Zeitgebern: `dom-helfer.flush` wartet mit setTimeout). */
export async function mikro(s, n = 40) { for (let i = 0; i < n; i += 1) { await Promise.resolve(); await s.el.updateComplete; } }

export const bereitAufrufe = (s) => s.m.aufrufe('tobibox/audio/bereit');
export const setAufrufe = (s) => s.m.aufrufe('tobibox/hoerstelle/set');

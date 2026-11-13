/* Tobi Box: neue Alltagsseite für Home Assistant (Paket A6, Design docs/designs/ha-oberflaeche.md).
 *
 * Panel-Gerüst ohne Bewegung: vier Reiter, Panelbreite per ResizeObserver, Kopf, Hash-Routen, Tokens aus dem
 * HA-Theme mit Kontrastfunktion, Zustände (Lädt, Fehler, Leer), Blätter (<dialog>), Meldungen, Abo der
 * WebSocket-Themen über hass.connection, Platz für den Mini-Player und der Punkt am Reiter „Geräte“.
 * Die Inhalte der Seiten sind eigene Module unter seiten/ (A7: Start, Bibliothek, Suche; weitere folgen in A7b, A8, A12),
 * gemeinsame Bausteine stehen in bausteine.js, das Verzeichnis in seiten/index.js. Bewegung kommt mit A6m.
 *
 * Technik: Lit aus ./lit-all.min.js (fest eingecheckt, dasselbe wie die alte Seite, nichts aus dem Netz).
 * Namen und Texte aus Daten werden nur als Text gesetzt (Lit maskiert selbst). Die Texte stehen in texte.js.
 * Die Illustrationen der leeren Zustände (A6b) kommen aus ./illustrationen.js; fehlt die Datei oder ein Bild,
 * steht ein schlichter Platzhalter da.
 */
import { fuellen, fehlerText, SEITE, TOBIE, LEER, TECHNIK } from './texte.js';
import { SEITEN } from './seiten/index.js';
import { initLit, bausteinStil, CoverLader, leererZustand } from './bausteine.js';

export const VERTRAG_V = 1;
export const REITER_UNTEN_BIS = 700; // Panelbreite unter 700 px: Reiter unten
export const SEITENLEISTE_AB = 1100; // ab 1100 px: eigene Seitenleiste dazwischen: Reiter oben

/* ------------------------------------------------------------------ Farben und Kontrast (Design 4) */

const STANDARD_HELL = { bg: '#fafafa', card: '#ffffff', text: '#212121', text2: '#5f6368', divider: '#dcdfe3', primary: '#03a9f4', onPrimary: '#ffffff' };
const STANDARD_DUNKEL = { bg: '#111315', card: '#1c1e21', text: '#e8eaed', text2: '#aeb4bb', divider: '#3a3f45', primary: '#4fc3f7', onPrimary: '#00212f' };

/* '#rgb', '#rrggbb', 'rgb(…)' und 'rgba(…)' → [r, g, b] oder null. */
export function parseFarbe(f) {
  if (Array.isArray(f)) return f;
  const s = String(f ?? '').trim().toLowerCase();
  let m = /^#([0-9a-f]{3})$/.exec(s);
  if (m) return [...m[1]].map((c) => parseInt(c + c, 16));
  m = /^#([0-9a-f]{6})(?:[0-9a-f]{2})?$/.exec(s);
  if (m) return [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16));
  m = /^rgba?\(\s*(\d+(?:\.\d+)?)[ ,]+(\d+(?:\.\d+)?)[ ,]+(\d+(?:\.\d+)?)/.exec(s);
  if (m) return [m[1], m[2], m[3]].map((x) => Math.round(Number(x)));
  return null;
}

export function zuHex(rgb) {
  return `#${rgb.map((x) => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, '0')).join('')}`;
}

/* Relative Leuchtdichte nach WCAG. */
export function luminanz(f) {
  const [r, g, b] = parseFarbe(f).map((x) => {
    const c = x / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/* Kontrastverhältnis zweier Farben (1 bis 21). */
export function kontrast(a, b) {
  const la = luminanz(a);
  const lb = luminanz(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/* Mischt a mit b; t = 0 ergibt a, t = 1 ergibt b. */
export function mischen(a, b, t) {
  const x = parseFarbe(a);
  const y = parseFarbe(b);
  return zuHex(x.map((v, i) => v * (1 - t) + y[i] * t));
}

/* Gibt `farbe` zurück, wenn sie gegen alle `flaechen` mindestens `min` hält; sonst schrittweise zu `ziel`
 * (Schwarz oder Weiß) gemischt, bis es reicht. Reicht auch das reine Ziel nicht, kommt das Ziel. */
export function sichern(farbe, flaechen, min, ziel) {
  const ok = (c) => flaechen.every((f) => kontrast(c, f) >= min);
  if (ok(farbe)) return zuHex(parseFarbe(farbe));
  for (let i = 1; i <= 50; i += 1) {
    const c = mischen(farbe, ziel, i / 50);
    if (ok(c)) return c;
  }
  return zuHex(parseFarbe(ziel));
}

/* Schriftfarbe auf einer Fläche: die gewünschte, wenn sie 4,5:1 hält, sonst Schwarz oder Weiß, je nachdem was besser ist. */
export function waehleTextfarbe(flaeche, gewuenscht, min = 4.5) {
  if (gewuenscht && parseFarbe(gewuenscht) && kontrast(gewuenscht, flaeche) >= min) return zuHex(parseFarbe(gewuenscht));
  return kontrast('#000000', flaeche) >= kontrast('#ffffff', flaeche) ? '#000000' : '#ffffff';
}

/* Die sechs Platzhalterfarben der Cover (auch als --c1 bis --c6 im Stil der App). */
const COVER_FARBEN = ['#ad1457', '#00695c', '#5e35b1', '#8d4a00', '#1565c0', '#2e7d32'];

/* Alle Farb-Token aus den HA-Farben. Eingabe: bg, card, text, text2, divider, primary, onPrimary (CSS-Farben, auch
 * leer). Ausgabe: Objekt `{ '--bg': '#…', … }`. Text 4,5:1, Ränder und Warnkarten 3:1 gegen Seite, Karte und Primärton-Hinweis. */
export function berechneTokens(e = {}) {
  const hell = STANDARD_HELL;
  const dunkelVorgabe = STANDARD_DUNKEL;
  const nimm = (k, d) => (parseFarbe(e[k]) ? zuHex(parseFarbe(e[k])) : d[k]);
  const card0 = parseFarbe(e.card) ? zuHex(parseFarbe(e.card)) : null;
  const dunkel = (card0 ?? hell.card) && luminanz(card0 ?? hell.card) < 0.179;
  const d = dunkel ? dunkelVorgabe : hell;
  const bg = nimm('bg', d);
  const card = card0 ?? d.card;
  const text = nimm('text', d);
  const primary = nimm('primary', d);
  const ziel = dunkel ? '#ffffff' : '#000000';

  const primarySoft = mischen(card, primary, dunkel ? 0.22 : 0.12);
  // Die Reiterleiste (unten und oben) ist zu 94 % deckend; die sechs Cover-Farben darunter scheinen mit 6 % durch (A14-1a, N28).
  const unterCover = COVER_FARBEN.map((c) => mischen(card, c, 0.06));
  const flaechen = [bg, card, primarySoft];
  const text2 = sichern(nimm('text2', d), [...flaechen, ...unterCover], 4.5, text);
  const primaryInk = sichern(primary, [...flaechen, ...unterCover], 4.5, ziel);
  const onPrimary = waehleTextfarbe(primary, parseFarbe(e.onPrimary) ? e.onPrimary : d.onPrimary);
  const focus = sichern(dunkel ? '#ffb74d' : '#e65100', [bg, card], 3, ziel);

  const status = (basis) => {
    const hintergrund = mischen(card, basis, dunkel ? 0.18 : 0.1);
    return [sichern(basis, [bg, card, hintergrund], 4.5, ziel), hintergrund];
  };
  const [ok, okBg] = status(dunkel ? '#81c784' : '#1b5e20');
  const [warn, warnBg] = status(dunkel ? '#ffcc80' : '#8a4b00');
  const [danger, dangerBg] = status(dunkel ? '#ef9a9a' : '#b71c1c');
  // Rand: 3:1 auch gegen die Hinweisflächen (Knöpfe mit Rand liegen in Hinweiskarten)
  const line = sichern(dunkel ? '#7d848c' : '#7c8187', [...flaechen, okBg, warnBg, dangerBg], 3, ziel);

  return {
    '--bg': bg, '--card': card, '--text': text, '--text2': text2, '--divider': nimm('divider', d),
    '--primary': primary, '--on-primary': onPrimary, '--primary-soft': primarySoft, '--primary-ink': primaryInk,
    '--ok': ok, '--ok-bg': okBg, '--warn': warn, '--warn-bg': warnBg, '--danger': danger, '--danger-bg': dangerBg,
    '--focus': focus, '--line': line,
    '--shine': dunkel ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.2)',
    '--shadow': dunkel ? 'rgba(0, 0, 0, 0.5)' : 'rgba(0, 0, 0, 0.12)',
    '--scrim': dunkel ? 'rgba(0, 0, 0, 0.65)' : 'rgba(0, 0, 0, 0.5)',
    'color-scheme': dunkel ? 'dark' : 'light',
  };
}

/* ------------------------------------------------------------------ Breite, Gruß, Routen */

/* Panelbreite → Lage der Reiter: 'unten' (unter 700), 'oben' (700 bis unter 1100), 'seite' (ab 1100). */
export function layoutFuerBreite(breite) {
  if (breite >= SEITENLEISTE_AB) return 'seite';
  if (breite >= REITER_UNTEN_BIS) return 'oben';
  return 'unten';
}

/* Begrüßung nach Tageszeit (Design 3.1): bis 11 Uhr, bis 17, bis 22, sonst „Gute Nacht“. Kein Name. */
export function begruessung(datum = new Date()) {
  const h = datum.getHours();
  const b = SEITE.begruessung;
  return h < 11 ? b.morgen : h < 17 ? b.tag : h < 22 ? b.abend : b.nacht;
}

export const REITER = ['start', 'bibliothek', 'tobies', 'geraete'];

const TECHNIK_SUB = { boxen: 'technik_boxen', speicher: 'technik_speicher', liste: 'technik_liste', tobies: 'technik_tobies', meldungen: 'technik_meldungen', einstellungen: 'technik_einstellungen' };

/* Adresse (nach `#`) → { name, tab, id, sub, seite (Schlüssel in SEITE.seiten), zurueck, umleitung }.
 * `umleitung` ist die Adresse, auf die die Seite umgeschrieben wird (Design 3.2). `faehigkeiten`: hello.faehigkeiten,
 * oder null, solange hello noch nicht da ist (dann keine Umleitung wegen fehlender Fähigkeit). */
export function parseRoute(hash, { faehigkeiten = null } = {}) {
  const h = String(hash || '').replace(/^#/, '');
  const r = (o) => o;
  if (h === '' || h === 'start') return r({ name: 'start', tab: 'start' });
  if (h.startsWith('serie-')) return r({ name: 'serie', tab: 'bibliothek', id: h.slice(6), seite: 'serie', zurueck: 'bibliothek' });
  if (h.startsWith('tobie-')) return r({ name: 'tobie', tab: 'tobies', id: h.slice(6), seite: 'tobie', zurueck: 'tobies' });
  if (h === 'neu' || h === 'neu-warten' || h === 'neu-queue') return r({ name: h, tab: 'tobies', seite: h.replace('-', '_'), zurueck: 'tobies' });
  if (h === 'neu-ziel') return r({ name: 'neu-ziel', tab: 'tobies', seite: 'neu_ziel', zurueck: 'tobies' });
  if (h.startsWith('geben-')) return r({ name: 'geben', tab: 'bibliothek', id: h.slice(6), seite: 'geben', zurueck: 'bibliothek' });
  if (h.startsWith('box-')) return r({ name: 'box', tab: 'geraete', id: h.slice(4), seite: 'box', zurueck: 'geraete' });
  if (h.startsWith('playlist-')) return r({ name: 'start', tab: 'bibliothek', umleitung: 'bibliothek' }); // Stufe C: noch nicht gebaut
  if (h === 'hinzufuegen' || h === 'anlernen' || h === 'suche') return r({ name: h, tab: 'bibliothek', seite: h, zurueck: 'bibliothek' });
  if (h === 'technik') return r({ name: 'technik', tab: 'technik', seite: 'technik' });
  if (h.startsWith('technik-')) {
    const sub = h.slice(8);
    const box = sub.startsWith('box-') ? sub.slice(4) : null;
    return r({ name: 'technik', tab: 'technik', sub, id: box, seite: box !== null ? 'technik_box' : (TECHNIK_SUB[sub] || 'technik'), zurueck: 'technik' });
  }
  if (h === 'gehoert') {
    if (faehigkeiten && !faehigkeiten.includes('gehoert')) return r({ name: 'geraete', tab: 'geraete', umleitung: 'geraete' });
    return r({ name: 'gehoert', tab: 'geraete', seite: 'gehoert', zurueck: 'geraete' });
  }
  if (h === 'abends' || h === 'mehr') return r({ name: 'geraete', tab: 'geraete', umleitung: 'geraete' });
  if (REITER.includes(h)) return r({ name: h, tab: h });
  return r({ name: 'start', tab: 'start' });
}

/* ------------------------------------------------------------------ Daten: hello, Abo, Listen (ohne DOM) */

const GRENZE_LAEDT_MS = 10000;
const THEMEN = ['boxen', 'neue_tobies', 'konfig'];

export class AppStore {
  constructor({ ladeGrenzeMs = GRENZE_LAEDT_MS } = {}) {
    this.ladeGrenzeMs = ladeGrenzeMs;
    this.s = { phase: 'laedt', fehlerCode: null, faehigkeiten: null, boxen: {}, boxAnzeigen: {}, neue: [], konfigZustand: 'ok', verbindungWeg: false };
    this.hass = null;
    this.onNeuerTobie = null; // ({ uid, box, anzeige }) beim ersten Auftauchen einer unbekannten Kennung nach dem Start
    this.onWiederda = null; // () nach dem Wiederverbinden: die aktive Seite lädt neu
    this._ls = new Set();
    this._lauf = 0;
    this._bekannt = new Set();
  }

  onChange(fn) { this._ls.add(fn); return () => this._ls.delete(fn); }
  _set(teil) { Object.assign(this.s, teil); this._ls.forEach((f) => f()); }
  _api(type, felder = {}) { return this.hass.connection.sendMessagePromise({ type, ...felder }); }

  async attach(hass) {
    this.hass = hass;
    const c = hass.connection;
    if (c && typeof c.addEventListener === 'function') {
      this._weg = () => this._set({ verbindungWeg: true });
      this._da = () => { this._set({ verbindungWeg: false }); this._ladeListen().catch(() => {}); this.onWiederda?.(); };
      c.addEventListener('disconnected', this._weg);
      c.addEventListener('ready', this._da);
    }
    await this.start();
  }

  detach() {
    this._lauf += 1;
    clearTimeout(this._timer);
    try { const u = this._abo; this._abo = null; if (typeof u === 'function') u(); } catch { /* egal */ }
    const c = this.hass?.connection;
    if (c && typeof c.removeEventListener === 'function') {
      if (this._weg) c.removeEventListener('disconnected', this._weg);
      if (this._da) c.removeEventListener('ready', this._da);
    }
    this.hass = null;
  }

  async start() {
    const lauf = ++this._lauf;
    clearTimeout(this._timer);
    try { const u = this._abo; this._abo = null; if (typeof u === 'function') u(); } catch { /* egal */ }
    this._set({ phase: 'laedt', fehlerCode: null });
    this._timer = setTimeout(() => {
      if (lauf === this._lauf && this.s.phase === 'laedt') this._set({ phase: 'fehler', fehlerCode: 'zeitgrenze' });
    }, this.ladeGrenzeMs);
    try {
      const hello = await this._api('tobibox/hello', { v: VERTRAG_V });
      if (lauf !== this._lauf) return;
      if (hello.v > VERTRAG_V) { clearTimeout(this._timer); this._set({ phase: 'veraltet' }); return; }
      const fae = hello.faehigkeiten || [];
      this.s.faehigkeiten = fae;
      this.s.boxAnzeigen = { ...(hello.grenzen?.box_anzeigen || {}), ...(hello.box_anzeigen || {}) };
      this.s.konfigZustand = hello.konfig?.zustand || 'ok';
      this._abo = await this.hass.connection.subscribeMessage((ev) => this._ereignis(ev), { type: 'tobibox/subscribe', themen: THEMEN });
      if (lauf !== this._lauf) return;
      await this._ladeListen();
      if (lauf !== this._lauf) return;
      this._bekannt = new Set(this.s.neue.map((n) => n.uid));
      clearTimeout(this._timer);
      this._set({ phase: 'bereit' });
    } catch (e) {
      if (lauf !== this._lauf) return;
      clearTimeout(this._timer);
      this._set({ phase: e?.code === 'unknown_command' ? 'veraltet' : 'fehler', fehlerCode: e?.code || 'unknown_error' });
    }
  }

  async _ladeListen() {
    const fae = this.s.faehigkeiten || [];
    const neu = {};
    if (fae.includes('boxen')) {
      const r = await this._api('tobibox/boxen/list');
      neu.boxen = Object.fromEntries((r.boxen || []).map((b) => [b.box, b]));
      const anz = { ...this.s.boxAnzeigen };
      for (const b of r.boxen || []) if (!anz[b.box]) anz[b.box] = b.anzeige || b.anzeigename || b.box;
      neu.boxAnzeigen = anz;
    }
    if (fae.includes('neue_tobies')) {
      const r = await this._api('tobibox/neue_tobies/list', { limit: 100 });
      neu.neue = r.eintraege || [];
    }
    this._set(neu);
  }

  anzeige(box) { return this.s.boxAnzeigen[box] || this.s.boxen[box]?.anzeige || this.s.boxen[box]?.anzeigename || box; }

  /* Box, die den Tobie zuletzt gemeldet hat. */
  _meldendeBox(eintrag) {
    const liste = Object.entries(eintrag?.boxen || {});
    if (!liste.length) return null;
    return liste.sort((a, b) => String(b[1].zuletzt || '').localeCompare(String(a[1].zuletzt || '')))[0][0];
  }

  _ereignis(ev) {
    if (!ev || ev.v !== VERTRAG_V) return;
    const d = ev.daten || {};
    if (ev.thema === 'neue_tobies') {
      if (ev.art === 'neu' || ev.art === 'aktualisiert') {
        const e = d.eintrag;
        if (!e || !e.uid) return;
        const rest = this.s.neue.filter((n) => n.uid !== e.uid);
        this._set({ neue: [e, ...rest] });
        if (ev.art === 'neu' && !this._bekannt.has(e.uid)) {
          this._bekannt.add(e.uid);
          const box = this._meldendeBox(e);
          this.onNeuerTobie?.({ uid: e.uid, box, anzeige: box ? this.anzeige(box) : '' });
        }
      } else if (ev.art === 'entfernt') {
        this._set({ neue: this.s.neue.filter((n) => n.uid !== d.uid) });
      }
    } else if (ev.thema === 'boxen') {
      if (ev.art === 'geaendert' && d.box) this._set({ boxen: { ...this.s.boxen, [d.box]: d } });
    } else if (ev.thema === 'konfig') {
      if ((ev.art === 'snapshot' || ev.art === 'geaendert') && d.konfig) this._set({ konfigZustand: d.konfig.zustand || 'ok' });
    }
  }
}

/* ------------------------------------------------------------------ Illustrationen (A6b, eigene Datei) */

let illustrationenGeladen = null;
export function ladeIllustrationen() {
  illustrationenGeladen ??= import('./illustrationen.js').then((m) => m.ILLUSTRATIONEN || m.default || {}).catch(() => ({}));
  return illustrationenGeladen;
}

/* ------------------------------------------------------------------ Element */

const ICON = {
  home: 'M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z',
  lib: 'M4 5v13h17V5H4zm10 2v3.5h-3V7h3zM6 7h3v3.5H6V7zm0 9v-3.5h3V16H6zm5 0v-3.5h3V16h-3zm8 0h-3v-3.5h3V16zm-3-5.5V7h3v3.5h-3z',
  tag: 'M17.63 5.84C17.27 5.33 16.67 5 16 5L5 5.01C3.9 5.01 3 5.9 3 7v10c0 1.1.9 1.99 2 1.99L16 19c.67 0 1.27-.33 1.63-.84L22 12l-4.37-6.16z',
  spk: 'M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02z',
  tool: 'M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z',
  search: 'M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z',
  plus: 'M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z',
  close: 'M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z',
};

const lit = typeof HTMLElement !== 'undefined' && typeof customElements !== 'undefined'
  ? await import('./lit-all.min.js') : null;

if (lit) {
  initLit(lit);
  const { LitElement, html, css, nothing, svg } = lit;
  const ic = (n, gr = 24) => html`<svg viewBox="0 0 24 24" width=${gr} height=${gr} aria-hidden="true" focusable="false"><path d=${ICON[n]}></path></svg>`;

  class TobiboxApp extends LitElement {
    static properties = {
      hass: { attribute: false }, narrow: { type: Boolean }, route: { attribute: false }, panel: { attribute: false },
      _tick: { state: true }, _layout: { state: true }, _hash: { state: true }, _blatt: { state: true }, _kbd: { state: true },
      _bilder: { state: true },
    };

    constructor() {
      super();
      this.store = new AppStore();
      this._tick = 0;
      this._layout = 'unten';
      this._hash = '';
      this._blatt = null;
      this._kbd = false;
      this._bilder = {};
      this._neuUid = null; // Kennung für „Neuer Tobie erkannt“ (#neu-ziel)
      this._neuVon = 'tobies';
      this._themenStand = '';
      this._seiten = {}; // je Seite ein Objekt aus seiten/<name>.js (erzeuge(ctx)), angelegt beim ersten Besuch
      this._seiteObj = null;
      this._seiteKey = null;
      this._covers = new CoverLader(() => this.hass);
      this.ctx = this._baueCtx();
      this.store.onWiederda = () => this._seiteObj?.neuLaden?.();
      this._off = this.store.onChange(() => { this._tick += 1; if (this.store.s.phase === 'bereit') this._leseHash(); });
      this.store.onNeuerTobie = (n) => this._neuerTobie(n);
      this._onHash = () => { this._leseHash(); this._schliesseBlattBeiRoute(); this._fokusMain = true; this._scrollOben = true; };
      this._onResize = () => this._messeBreite();
    }

    /* ---- Lebenslauf */
    connectedCallback() {
      super.connectedCallback();
      this._leseHash();
      window.addEventListener('hashchange', this._onHash);
      this._messeBreite();
      if (typeof ResizeObserver !== 'undefined') {
        this._ro = new ResizeObserver((eintraege) => {
          const e = eintraege[eintraege.length - 1];
          const w = e?.contentRect?.width ?? e?.borderBoxSize?.[0]?.inlineSize;
          this._messeBreite(w);
        });
        this._ro.observe(this);
      } else window.addEventListener('resize', this._onResize);
      this._fokusEin = (e) => this._tastatur(e.target);
      this._fokusAus = () => setTimeout(() => { this._kbd = false; }, 0);
      this.renderRoot.addEventListener('focusin', this._fokusEin);
      this.renderRoot.addEventListener('focusout', this._fokusAus);
      this._vv = window.visualViewport;
      this._vvFn = () => this._tastatur(this.renderRoot.activeElement);
      this._vv?.addEventListener?.('resize', this._vvFn);
      ladeIllustrationen().then((b) => { this._bilder = b; });
    }

    disconnectedCallback() {
      super.disconnectedCallback();
      window.removeEventListener('hashchange', this._onHash);
      window.removeEventListener('resize', this._onResize);
      this._ro?.disconnect(); this._ro = null;
      this._seiteObj?.verlassen?.(); this._seiteObj = null; this._seiteKey = null;
      this._covers.abmelden();
      this.renderRoot.removeEventListener('focusin', this._fokusEin);
      this.renderRoot.removeEventListener('focusout', this._fokusAus);
      this._vv?.removeEventListener?.('resize', this._vvFn);
      this.store.detach();
    }

    willUpdate(ch) {
      if (ch.has('hass') && this.hass) {
        if (!this.store.hass) this.store.attach(this.hass); else this.store.hass = this.hass;
      }
    }

    updated(ch) {
      this.setAttribute('data-layout', this._layout);
      this._wendeTokens();
      this._seitenWechsel();
      if (this._blatt && !this._blatt.offen) this._blattEinrichten();
      if (this._scrollOben) { this._scrollOben = false; const r = this.renderRoot.querySelector('.rahmen'); const sp = this.renderRoot.querySelector('.spalte'); if (r) r.scrollTop = 0; if (sp) sp.scrollTop = 0; }
      if (this._fokusMain) { this._fokusMain = false; this.renderRoot.querySelector('main')?.focus({ preventScroll: true }); }
      if (ch.has('hass')) this._wendeTokens();
      this._covers.beobachte(this.renderRoot);
      this._seiteObj?.nachRender?.(this.renderRoot);
    }

    /* ---- Tokens aus dem HA-Theme (Design 4) */
    _wendeTokens() {
      let v = () => '';
      try { const cs = getComputedStyle(this); v = (n) => cs.getPropertyValue(n).trim(); } catch { /* ohne Stil */ }
      const t = berechneTokens({
        bg: v('--primary-background-color'), card: v('--card-background-color'), text: v('--primary-text-color'),
        text2: v('--secondary-text-color'), divider: v('--divider-color'), primary: v('--primary-color'), onPrimary: v('--text-primary-color'),
      });
      const stand = JSON.stringify(t);
      if (stand === this._themenStand) return;
      this._themenStand = stand;
      for (const [k, w] of Object.entries(t)) this.style.setProperty(k, w);
    }

    /* ---- Breite des Panels */
    _messeBreite(w) {
      let breite = w;
      if (!breite) breite = this.getBoundingClientRect?.().width || window.innerWidth || 0;
      const l = layoutFuerBreite(breite);
      if (l !== this._layout) this._layout = l;
    }

    _tastatur(ziel) {
      const feld = ziel && ziel.matches?.('input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]):not([type=button]):not([type=submit]), textarea');
      const vv = this._vv;
      this._kbd = !!(feld && vv && vv.height < (window.innerHeight || 0) * 0.8);
    }

    /* ---- Routen */
    get _faehigkeiten() { return this.store.s.faehigkeiten; }
    get _route() { return parseRoute(this._hash, { faehigkeiten: this.store.s.phase === 'bereit' ? this._faehigkeiten : null }); }

    _leseHash() {
      let h = window.location.hash || '';
      const r = parseRoute(h, { faehigkeiten: this.store.s.phase === 'bereit' ? this._faehigkeiten : null });
      if (r.umleitung) {
        const ziel = `#${r.umleitung}`;
        try { window.history.replaceState(window.history.state, '', ziel); } catch { window.location.hash = ziel; }
        h = ziel;
      }
      if (h !== this._hash) this._hash = h;
    }

    _schliesseBlattBeiRoute() { if (this._blatt) this.schliesseBlatt('route'); }

    /* ---- Admin */
    get _admin() { return this.hass?.user?.is_admin === true; }

    /* ================================================================== Blätter (<dialog>) */
    /* oeffneBlatt({ titel, inhalt, knoepfe: [{ label, kind, fn }], rolle })
     * Schließen: Knopf ×, Knopf in der Leiste, Esc, Hintergrund, Wischen nach unten. Danach geht der Fokus zurück.
     * `inhalt` darf eine Funktion sein: sie wird bei jedem Zeichnen neu aufgerufen (das Blatt folgt dem Zustand der Seite).
     * Antwort: Promise mit dem Grund ('x', 'knopf', 'esc', 'hintergrund', 'wischen', 'route', 'ersetzt', 'code').
     * A6m ersetzt _blattAn und _blattAus durch Bewegung; _blattAus ruft `fertig` erst nach dem Ende der Bewegung. */
    oeffneBlatt({ titel, inhalt = nothing, knoepfe = [], rolle = null } = {}) {
      if (this._blatt) this._blattEntfernen(this._blatt, 'ersetzt', false);
      const rueck = this.renderRoot.activeElement || (typeof document !== 'undefined' ? document.activeElement : null);
      return new Promise((aufloesen) => {
        this._blatt = { titel, inhalt, knoepfe, rolle, offen: false, schliesst: false, aufloesen, rueck: this._blattRueck ?? rueck };
        this._blattRueck = null;
      });
    }

    schliesseBlatt(grund = 'code') {
      const b = this._blatt;
      if (!b || b.schliesst) return;
      b.schliesst = true;
      const d = this.renderRoot.querySelector('dialog.blatt');
      if (!d) { this._blattEntfernen(b, grund, true); return; }
      this._blattAus(d, () => this._blattEntfernen(b, grund, true));
    }

    _blattEinrichten() {
      const b = this._blatt;
      const d = this.renderRoot.querySelector('dialog.blatt');
      if (!d) return;
      b.offen = true;
      if (typeof d.showModal === 'function') { try { d.showModal(); } catch { d.setAttribute('open', ''); } } else d.setAttribute('open', '');
      this._wischen(d);
      this._blattAn(d);
      this._meldungenPlatz();
      const erst = d.querySelector('[autofocus]') || d.querySelector('.knoepfe button, .blatt-b button, .blatt-b input, .blatt-b select, .blatt-b a') || d.querySelector('h2');
      erst?.focus?.();
    }

    /* Haken für A6m (Bewegung): hier ohne Bewegung. */
    _blattAn() {}
    _blattAus(d, fertig) { fertig(); }

    _blattEntfernen(b, grund, mitFokus) {
      if (this._blatt !== b) return;
      const d = this.renderRoot.querySelector('dialog.blatt');
      this._blattRueck = null;
      if (d) {
        try { if (typeof d.close === 'function') d.close(); else d.removeAttribute('open'); } catch { d.removeAttribute('open'); }
        d.removeAttribute('open');
      }
      this._blatt = null;
      this._meldungenPlatz(true);
      b.aufloesen(grund);
      if (mitFokus) {
        this.updateComplete.then(() => {
          const r = b.rueck;
          if (r && r.isConnected && typeof r.focus === 'function') r.focus();
        });
      }
    }

    /* Wischen nach unten (Griff, Überschrift und Inhalt, solange er oben steht): das Blatt folgt dem Finger. */
    _wischen(d) {
      if (d._wischt) return;
      d._wischt = true;
      let y0 = null; let x0 = 0; let id = null; let cap = false; let dy = 0; let ly = 0; let lt = 0; let vel = 0;
      const ueberspringen = (t) => !t.closest?.('.griff, h2') && (d.scrollTop > 0 || !!t.closest?.('input, select, textarea, canvas, [data-griff]'));
      d.addEventListener('pointerdown', (e) => {
        if ((e.button ?? 0) > 0 || d.dataset.closing || this._blatt?.schliesst || ueberspringen(e.target)) return;
        y0 = e.clientY; x0 = e.clientX; id = e.pointerId; cap = false; dy = 0; ly = y0; lt = e.timeStamp; vel = 0;
      });
      d.addEventListener('pointermove', (e) => {
        if (y0 === null || e.pointerId !== id) return;
        const ddy = e.clientY - y0; const ddx = e.clientX - x0;
        if (!cap) {
          if (ddy > 8 && ddy > Math.abs(ddx)) { cap = true; try { d.setPointerCapture(id); } catch { /* ohne */ } } else return;
        }
        const dt = e.timeStamp - lt; if (dt > 0) vel = (e.clientY - ly) / dt;
        ly = e.clientY; lt = e.timeStamp;
        dy = Math.max(0, ddy);
        d.style.transform = `translateY(${dy}px)`;
      });
      const ende = () => {
        if (y0 === null) return;
        const war = cap; y0 = null; cap = false;
        if (!war) return;
        try { d.releasePointerCapture(id); } catch { /* ohne */ }
        this._gewischtAm = Date.now();
        if (dy > (d.offsetHeight || 0) * 0.25 || (vel > 0.5 && dy > 30)) { d.dataset.wisch = '1'; this.schliesseBlatt('wischen'); } else d.style.transform = '';
      };
      d.addEventListener('pointerup', ende);
      d.addEventListener('pointercancel', ende);
    }

    _blattKlick(e) {
      const d = e.currentTarget;
      if (e.target === d && Date.now() - (this._gewischtAm || 0) > 250) this.schliesseBlatt('hintergrund');
    }

    async _blattKnopf(k) {
      const behalten = await k.fn?.();
      if (behalten !== false) this.schliesseBlatt('knopf');
    }

    _blattHtml() {
      const b = this._blatt;
      if (!b) return nothing;
      return html`<dialog class="blatt" aria-labelledby="blatt-t" role=${b.rolle ?? nothing}
          @cancel=${(e) => { e.preventDefault(); this.schliesseBlatt('esc'); }} @click=${(e) => this._blattKlick(e)}>
        <div class="blatt-in">
          <div class="griff" aria-hidden="true"></div>
          <button type="button" class="rund blatt-x" aria-label=${SEITE.schliessen} @click=${() => this.schliesseBlatt('x')}>${ic('close', 28)}</button>
          <h2 id="blatt-t" tabindex="-1">${b.titel}</h2>
          <div class="blatt-b">${typeof b.inhalt === 'function' ? b.inhalt() : b.inhalt}</div>
          <div class="knoepfe">${b.knoepfe.map((k) => html`<button type="button" class=${`btn ${k.kind || ''}`} @click=${() => this._blattKnopf(k)}>${k.label}</button>`)}</div>
        </div>
      </dialog>`;
    }

    /* ================================================================== Meldungen (Design 6.3) */
    get _tb() { return this.renderRoot.querySelector('.toastbox'); }

    /* Der Meldungsbereich zieht in das oberste offene Blatt um (Top-Layer), sonst zurück nach unten. */
    _meldungenPlatz(ohneBlatt = false) {
      const tb = this._tb; const app = this.renderRoot.querySelector('.app');
      if (!tb || !app) return;
      const offen = ohneBlatt ? [] : [...this.renderRoot.querySelectorAll('dialog[open]')].filter((x) => !x.dataset.closing);
      const d = offen.length ? offen[offen.length - 1] : null;
      if (d) { if (tb.parentNode !== d) d.appendChild(tb); tb.classList.add('imblatt'); } else { if (tb.parentNode !== app) app.appendChild(tb); tb.classList.remove('imblatt'); }
    }

    _meldungWeg(el) { if (el.parentNode) el.parentNode.removeChild(el); }

    /* melde(text, { fehler, aktion: { text, fn } }): Erfolg 4,5 s, mit Aktion 6 s, Fehler bleibt bis „OK“ oder Wegwischen. */
    melde(text, { fehler = false, aktion = null } = {}) {
      const tb = this._tb;
      if (!tb) return null;
      this._meldungenPlatz();
      if (!fehler) tb.querySelectorAll('.toast:not(.err)').forEach((x) => this._meldungWeg(x));
      const doc = tb.ownerDocument;
      const el = doc.createElement('div');
      el.className = `toast${fehler ? ' err' : ''}`;
      el.setAttribute('role', fehler ? 'alert' : 'status');
      const msg = doc.createElement('span'); msg.className = 'tmsg'; msg.textContent = text; el.appendChild(msg);
      let knopf = null;
      if (fehler || aktion) {
        knopf = doc.createElement('button'); knopf.type = 'button'; knopf.className = 'tok';
        knopf.textContent = fehler ? SEITE.ok : aktion.text;
        el.appendChild(knopf);
      }
      tb.appendChild(el);
      // Wegwischen nach links oder rechts (Schwelle 70 px)
      let x0 = null; let dx = 0;
      el.addEventListener('pointerdown', (e) => { if (e.target.closest?.('.tok')) return; x0 = e.clientX; dx = 0; try { el.setPointerCapture(e.pointerId); } catch { /* ohne */ } });
      el.addEventListener('pointermove', (e) => { if (x0 === null) return; dx = e.clientX - x0; el.style.transform = `translateX(${dx}px)`; el.style.opacity = String(Math.max(0.3, 1 - Math.abs(dx) / 300)); });
      const ende = () => {
        if (x0 === null) return; x0 = null;
        if (Math.abs(dx) > 70) this._meldungWeg(el); else { el.style.transform = ''; el.style.opacity = ''; }
      };
      el.addEventListener('pointerup', ende); el.addEventListener('pointercancel', ende);
      if (fehler) { knopf.addEventListener('click', () => this._meldungWeg(el)); return el; }
      this._ansage(text);
      if (aktion) knopf.addEventListener('click', () => { this._meldungWeg(el); aktion.fn?.(); if (aktion.text === TOBIE.rueckgaengig) this._ansage(TOBIE.rueckgaengig_gemacht); });
      setTimeout(() => this._meldungWeg(el), aktion ? 6000 : 4500);
      return el;
    }

    meldeFehler(text) { return this.melde(text, { fehler: true }); }
    _ansage(text) { const l = this.renderRoot.querySelector('#live'); if (l) l.textContent = text; }

    /* Globale Meldung „Neuer Tobie auf <Box> – Zuordnen“ (R17-6). Auf den Seiten, die selbst auf den Tobie warten, bleibt sie aus. */
    _neuerTobie({ uid, anzeige }) {
      const n = this._route.name;
      if (n === 'neu-warten' || (n === 'neu-ziel' && this._neuUid === uid)) return;
      this.melde(fuellen(TOBIE.neuer_tobie_meldung, { box: anzeige || undefined }), {
        aktion: { text: TOBIE.zuordnen, fn: () => { this._neuUid = uid; this._neuVon = 'geraete'; window.location.hash = '#neu-ziel'; } },
      });
    }

    /* ================================================================== Mini-Player-Platz (X31) */
    get miniPlatz() { return this.renderRoot.querySelector('.mini'); }

    /* Zeigt oder versteckt den Platz; die Höhe geht an die Meldungen (--minih). Die Player-Logik kommt mit A8b. */
    setMini(an, hoehe = 64) {
      const m = this.miniPlatz;
      if (!m) return;
      m.hidden = !an;
      this.style.setProperty('--minih', an ? `${hoehe}px` : '0px');
    }

    /* ================================================================== Darstellung */
    _bild(name) {
      const quelle = this._bilder?.[name];
      const doc = this.ownerDocument;
      if (typeof quelle === 'string' && quelle.includes('<svg')) {
        const t = doc.createElement('template'); t.innerHTML = quelle.trim(); // eigene, feste Datei, nie Daten des Backends
        const n = t.content.firstElementChild;
        if (n) { n.setAttribute('aria-hidden', 'true'); n.setAttribute('focusable', 'false'); return n; }
      }
      return svg`<svg class="illu" viewBox="0 0 200 150" aria-hidden="true" focusable="false"><ellipse cx="100" cy="138" rx="76" ry="9" fill="var(--primary-soft)"></ellipse><circle cx="100" cy="68" r="40" fill="var(--card)" stroke="var(--primary-ink)" stroke-width="3"></circle></svg>`;
    }

    /* Leerer Zustand (Design 6.2): Bild, ein Satz, ein Knopf. `werte` setzt Platzhalter im Satz, `knopf` überschreibt den Knopf. */
    _leer(art, bild, { werte = {}, href = null, aktion = null } = {}) {
      const t = LEER[art];
      const knopf = !t.knopf ? null : href ? { label: t.knopf, href } : { label: t.knopf, onKlick: aktion };
      return leererZustand({ art, bild: this._bild(bild), satz: fuellen(t.satz, werte), knopf });
    }

    _laedt() {
      return html`<div class="laedt" aria-busy="true"><span class="sr" role="status">${SEITE.laedt}</span>
        <div class="skel"></div><div class="skel"></div><div class="skel"></div></div>`;
    }

    _fehlerKarte(code = this.store.s.fehlerCode, neu = () => this.store.start()) {
      const t = SEITE.fehler_laden;
      const admin = this._admin;
      return html`<div class="note err" role="alert" data-zustand="fehler"><strong>${t.titel}</strong><br>${fuellen(t.text)}${admin && code ? html` <span class="muted">(Code: ${code})</span>` : nothing}
        <div class="btns"><button type="button" class="btn" @click=${neu}>${t.knopf}</button></div></div>`;
    }

    _veraltetKarte() {
      return html`<div class="note warn" role="alert" data-zustand="veraltet"><strong>${SEITE.veraltet}</strong>
        <div class="btns"><button type="button" class="btn" @click=${() => window.location.reload()}>${SEITE.verbindung_weg.knopf}</button></div></div>`;
    }

    _baender() {
      const s = this.store.s;
      const out = [];
      if (s.verbindungWeg) {
        const t = SEITE.verbindung_weg;
        out.push(html`<div class="note err band" role="alert" data-band="verbindung"><strong>${t.titel}</strong> ${t.text}
          <div class="btns"><button type="button" class="btn" @click=${() => window.location.reload()}>${t.knopf}</button></div></div>`);
      }
      if (s.phase === 'bereit' && s.konfigZustand !== 'ok' && !this._admin) {
        out.push(html`<div class="note warn band" role="status" data-band="gesperrt">${fuellen(SEITE.liste_gesperrt)}</div>`);
      }
      // Warnleiste zur Liste für Administratoren auf jeder Seite (Design 5.9); die Technik-Seite zeigt sie selbst mit den Knöpfen
      if (s.phase === 'bereit' && this._admin && this._route.name !== 'technik'
        && (s.konfigZustand === 'leer_neu' || s.konfigZustand === 'export_neuer' || Object.values(s.boxen).some((b) => b?.konfig_stand === 'voraus'))) {
        const w = TECHNIK.warnband;
        out.push(html`<div class="note warn band" role="alert" data-band="liste"><strong>${w.global}</strong>
          <a class="nl" href="#technik-liste">${w.global_link}</a></div>`);
      }
      return out;
    }

    _zurueck(r) {
      if (!r.zurueck) return nothing;
      let ziel = r.zurueck;
      if (r.name === 'neu-ziel') ziel = this._neuVon === 'geraete' ? 'geraete' : 'tobies';
      return html`<a class="back" href=${`#${ziel}`}>${SEITE.zurueck[ziel]}</a>`;
    }

    _titel(r) {
      if (REITER.includes(r.name)) return r.name === 'start' ? SEITE.reiter.start : SEITE.reiter[r.name];
      if (r.name === 'box' && r.id) return this.store.anzeige(r.id);
      return SEITE.seiten[r.seite] || SEITE.titel;
    }

    /* ---- Seiten aus seiten/ (Vertrag: bausteine.js) */
    _baueCtx() {
      const app = this;
      return {
        api: (type, felder) => app.store._api(type, felder),
        faehig: (name) => (app.store.s.faehigkeiten || []).includes(name),
        get admin() { return app._admin; },
        get layout() { return app._layout; },
        get hass() { return app.hass; }, // für eingebettete Komponenten (Technik: <tobibox-panel .hass=…>)
        get grenzeMs() { return app.store.ladeGrenzeMs; },
        get wurzel() { return app.renderRoot; },
        neuZeichnen: () => app.requestUpdate(),
        laedt: () => app._laedt(),
        fehlerKarte: (code, neu) => app._fehlerKarte(code, neu),
        leer: (art, bild, opts) => app._leer(art, bild, opts),
        oeffneBlatt: (o) => app.oeffneBlatt(o),
        schliesseBlatt: (g) => app.schliesseBlatt(g),
        melde: (text, o) => app.melde(text, o),
        meldeFehler: (text) => app.meldeFehler(text),
        ansage: (text) => app._ansage(text),
        fehlerText: (code) => fehlerText(code, { admin: app._admin }),
        begruessung: () => begruessung(),
        covers: app._covers,
        uploadBand: () => nothing, // A11 ersetzt das durch das Band der laufenden Uploads
        boxen: () => app.store.s.boxen, // live: Box-Name -> Box-Objekt aus `boxen/list` und den Ereignissen (A7b)
        gesperrt: () => app.store.s.konfigZustand !== 'ok' || app.store.s.verbindungWeg, // Liste gesperrt oder keine Verbindung: Knöpfe, die ändern, grau (A7b)
        folgenAktionen: null, // A8b/A9 setzen eine Funktion x => Template (Abspielen und „⋯“ in Folgenzeilen der Suche)
      };
    }

    _seiteFuer(name) {
      if (!SEITEN[name]) return null;
      return (this._seiten[name] ??= SEITEN[name].erzeuge(this.ctx));
    }

    /* Ruft `verlassen` und `betreten`, wenn die sichtbare Seite (oder ihre Adresse, zum Beispiel `#serie-<id>`) wechselt.
     * Solange `hello` nicht da ist, ist keine Seite aktiv. */
    _seitenWechsel() {
      const r = this._route;
      const aktiv = this.store.s.phase === 'bereit' && SEITEN[r.name] && !(r.name === 'technik' && !this._admin);
      const key = aktiv ? `${r.name}|${r.id ?? ''}|${r.sub ?? ''}` : null; // Technik: jede Unterseite betritt neu
      if (key === this._seiteKey) return;
      const alt = this._seiteObj;
      this._seiteKey = key;
      this._seiteObj = key ? this._seiteFuer(r.name) : null;
      alt?.verlassen?.();
      this._seiteObj?.betreten?.(r);
    }

    _seite(r) {
      const s = this.store.s;
      if (r.name === 'technik' && !this._admin) {
        return html`<div class="note warn" data-zustand="nur-admin"><strong>${fuellen(SEITE.technik_nur_admin)}</strong></div>`;
      }
      if (s.phase === 'laedt') return this._laedt();
      if (s.phase === 'fehler') return this._fehlerKarte();
      if (s.phase === 'veraltet') return this._veraltetKarte();
      const seite = this._seiteFuer(r.name);
      if (seite) return seite.render(r);
      const h2 = (extra = '') => html`<h2 class=${extra}>${this._titel(r)}</h2>`;
      switch (r.name) {
        case 'tobies':
          return html`${h2()}${this._leer('tobies', 'keineTobies')}`;
        case 'geraete':
          return html`${h2()}<div class="platz" data-platz="boxen"></div>${Object.keys(s.boxen).length ? nothing : this._leer('keine_box', 'keineBox', { aktion: () => this.store.start() })}`;
        case 'gehoert':
          return html`${this._zurueck(r)}${h2()}${this._leer('gehoert', 'gehoertOhneDaten', { href: '#bibliothek' })}`;
        default:
          return html`${this._zurueck(r)}${h2()}<div class="platz" data-platz=${r.name}></div>`;
      }
    }

    /* ---- Kopf und Reiter */
    _kopfSymbole(r) {
      return html`${r.name === 'start' ? html`<a class="rund" href="#suche" aria-label=${SEITE.suchen}>${ic('search')}</a>` : nothing}
        ${this._admin ? html`<a class="rund tech" href="#technik" aria-label=${SEITE.technik} aria-current=${r.tab === 'technik' ? 'page' : nothing}>${ic('tool')}</a>` : nothing}`;
    }

    _kopf(r) {
      return html`<header class="kopf">
        ${this.narrow ? html`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>` : nothing}
        <h1>${r.name === 'start' ? begruessung() : SEITE.titel}</h1>
        <span class="symbole">${this._kopfSymbole(r)}</span></header>`;
    }

    _nav(r) {
      const n = this.store.s.neue.length;
      const punkt = n ? html`<span class="dot" aria-hidden="true">${n}</span><span class="sr">${n === 1 ? TOBIE.neue_tobies_punkt : fuellen(TOBIE.neue_tobies_punkt_mehr, { anzahl: n })}</span>` : nothing;
      return html`<nav class=${`tabs ${this._layout}`} aria-label=${SEITE.bereiche}><div class="tr">
        ${REITER.map((id) => html`<a href=${`#${id}`} aria-current=${r.tab === id ? 'page' : nothing}><span class="ti">${ic({ start: 'home', bibliothek: 'lib', tobies: 'tag', geraete: 'spk' }[id], 26)}</span><span class="tn">${SEITE.reiter[id]}</span>${id === 'geraete' ? punkt : nothing}</a>`)}
      </div></nav>`;
    }

    _seitenleiste(r) {
      return html`<aside class="seite">
        ${this.narrow ? html`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>` : nothing}
        <div class="marke">${SEITE.titel}</div>
        ${this._nav(r)}
        <div class="werkzeuge"><a class="rund" href="#hinzufuegen" aria-label=${SEITE.hinzufuegen}>${ic('plus')}</a>
          ${this._admin ? html`<a class="rund tech" href="#technik" aria-label=${SEITE.technik} aria-current=${r.tab === 'technik' ? 'page' : nothing}>${ic('tool')}</a>` : nothing}</div>
      </aside>`;
    }

    render() {
      const r = this._route;
      const l = this._layout;
      return html`<div class="app" data-layout=${l} ?data-kbd=${this._kbd}>
        <div class="rahmen">
          ${l === 'seite' ? this._seitenleiste(r) : nothing}
          <div class="spalte">
            ${l === 'seite' ? nothing : this._kopf(r)}
            ${l === 'oben' ? this._nav(r) : nothing}
            ${this._baender()}
            <main id="main" tabindex="-1" aria-label=${this._titel(r)}>${this._seite(r)}</main>
            <div class="mini" hidden part="mini"><slot name="mini"></slot></div>
            ${l === 'unten' ? this._nav(r) : nothing}
          </div>
        </div>
        ${this._blattHtml()}
        <div class="toastbox"></div>
        <div id="live" class="sr" role="status" aria-live="polite"></div>
      </div>`;
    }

    static styles = [css`
      :host {
        display: block; height: 100%; overflow: hidden;
        --bg: #fafafa; --card: #ffffff; --text: #212121; --text2: #5f6368; --divider: #dcdfe3;
        --primary: #01689f; --on-primary: #ffffff; --primary-soft: #e1f2fb; --primary-ink: #01689f;
        --ok: #1b5e20; --ok-bg: #e6f4e7; --warn: #8a4b00; --warn-bg: #fff1d6; --danger: #b71c1c; --danger-bg: #fdeaea;
        --focus: #e65100; --line: #7c8187; --shadow: rgba(0, 0, 0, 0.12); --scrim: rgba(0, 0, 0, 0.5);
        --r-card: 16px; --r-big: 24px;
        --c1: #ad1457; --c2: #00695c; --c3: #5e35b1; --c4: #8d4a00; --c5: #1565c0; --c6: #2e7d32; --on-cover: #ffffff; --shine: rgba(255, 255, 255, 0.2);
        --dauer-kurz: 150ms; --dauer-mittel: 250ms; --dauer-lang: 350ms; --dauer-feder: 500ms;
        --kurve: cubic-bezier(.2, 0, 0, 1); --kurve-aus: cubic-bezier(.4, 0, 1, 1);
        --minih: 0px;
      }
      * { box-sizing: border-box; }
      .app { position: relative; height: 100%; overflow: hidden; background: var(--bg); color: var(--text);
        font-family: Roboto, system-ui, sans-serif; font-size: 16px; line-height: 1.45; --navh: calc(64px + env(safe-area-inset-bottom, 0px)); }
      .app:not([data-layout="unten"]) { --navh: 0px; }
      button, select, input { font: inherit; color: inherit; }
      button { cursor: pointer; }
      a { color: var(--primary-ink); }
      :focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; border-radius: 6px; }
      .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
      .rahmen { height: 100%; overflow-y: auto; overscroll-behavior: contain; }
      .spalte { min-height: 100%; display: flex; flex-direction: column; min-width: 0; }
      main { flex: 1 0 auto; min-width: 0; padding: 4px max(16px, env(safe-area-inset-right, 0px)) 24px max(16px, env(safe-area-inset-left, 0px)); outline: none; }
      main:focus, main:focus-visible { outline: none; }
      h2 { font-size: 20px; font-weight: 500; margin: 16px 0 12px; }
      main > h2:first-child, main > .back + h2 { margin-top: 8px; }

      /* Kopf */
      .kopf { display: flex; align-items: center; gap: 8px; min-height: 56px; padding: 4px max(16px, env(safe-area-inset-right, 0px)) 4px max(16px, env(safe-area-inset-left, 0px)); }
      .kopf h1 { font-size: 24px; margin: 0; font-weight: 500; flex: 1; min-width: 0; overflow-wrap: anywhere; line-height: 1.2; }
      .symbole { display: flex; gap: 8px; flex: none; }
      .rund { width: 48px; height: 48px; border-radius: 24px; border: 0; background: var(--primary-soft); color: var(--primary-ink); display: inline-grid; place-items: center; text-decoration: none; flex: none; }
      .rund svg { fill: currentColor; }
      .rund[aria-current="page"] { outline: 2px solid var(--primary-ink); outline-offset: -2px; }
      ha-menu-button { flex: none; color: var(--text); }

      /* Reiter */
      nav.tabs { z-index: 20; background: var(--card); }
      nav.tabs .tr { display: flex; }
      nav.tabs a { flex: 1 1 0; min-width: 0; min-height: 64px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
        text-decoration: none; color: var(--text2); font-size: 14px; font-weight: 500; position: relative; padding: 4px 2px; border-radius: 8px; text-align: center; overflow-wrap: anywhere; }
      nav.tabs a svg { fill: currentColor; display: block; }
      nav.tabs a[aria-current="page"] { color: var(--primary-ink); }
      nav.tabs .ti { display: grid; place-items: center; width: 56px; height: 32px; border-radius: 16px; }
      nav.tabs a[aria-current="page"] .ti { background: var(--primary-soft); }
      nav.tabs .dot { position: absolute; top: 4px; left: calc(50% + 6px); min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; background: var(--danger); color: var(--card); font-size: 12px; line-height: 18px; text-align: center; font-weight: 700; }
      nav.tabs.unten { position: sticky; bottom: 0; box-shadow: 0 -2px 12px var(--shadow); padding: 0 max(8px, env(safe-area-inset-left, 0px)) env(safe-area-inset-bottom, 0px) max(8px, env(safe-area-inset-right, 0px)); }
      @supports ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) and (background: color-mix(in srgb, red 50%, blue)) {
        nav.tabs.unten, nav.tabs.oben { background: color-mix(in srgb, var(--card) 94%, transparent); -webkit-backdrop-filter: blur(12px) saturate(1.3); backdrop-filter: blur(12px) saturate(1.3); }
      }
      nav.tabs.oben { position: sticky; top: 0; padding: 0 max(16px, env(safe-area-inset-left, 0px)); box-shadow: 0 2px 8px var(--shadow); }
      nav.tabs.oben .tr { max-width: 720px; gap: 4px; }
      nav.tabs.oben a { flex-direction: row; justify-content: center; gap: 8px; min-height: 52px; font-size: 16px; }
      nav.tabs.oben .ti { width: 32px; background: none !important; }
      nav.tabs.oben .dot { position: static; }
      .app[data-kbd] nav.tabs.unten, .app[data-kbd] .mini { display: none; }

      /* Seitenleiste ab 1100 px */
      .app[data-layout="seite"] .rahmen { display: grid; grid-template-columns: 264px minmax(0, 1fr); overflow: hidden; }
      aside.seite { height: 100%; overflow-y: auto; display: flex; flex-direction: column; background: var(--card); box-shadow: 2px 0 12px var(--shadow); padding: 20px 12px 16px; z-index: 20; }
      aside.seite .marke { font-size: 24px; font-weight: 500; padding: 0 12px 16px; }
      aside.seite nav.tabs { background: transparent; }
      aside.seite nav.tabs .tr { flex-direction: column; gap: 4px; }
      aside.seite nav.tabs a { flex: none; flex-direction: row; justify-content: flex-start; gap: 12px; font-size: 16px; padding: 0 16px; min-height: 52px; border-radius: 26px; }
      aside.seite nav.tabs a[aria-current="page"] { background: var(--primary-soft); }
      aside.seite nav.tabs .ti { width: 28px; height: 28px; background: none !important; }
      aside.seite nav.tabs .dot { position: static; }
      aside.seite .werkzeuge { margin-top: auto; display: flex; gap: 8px; flex-wrap: wrap; padding-top: 16px; }
      .app[data-layout="seite"] .spalte { height: 100%; overflow-y: auto; min-height: 0; }
      .app[data-layout="seite"] main { max-width: 1100px; width: 100%; padding: 24px 32px; margin: 0 auto; }

      /* Platz für den Mini-Player: bündig auf der Leiste */
      .mini { position: sticky; bottom: var(--navh); z-index: 19; background: var(--card); border-top: 1px solid var(--divider); box-shadow: 0 -2px 8px var(--shadow); }
      .mini[hidden] { display: none; }

      /* Karten, Knöpfe, Hinweise */
      .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 48px; padding: 0 20px; border-radius: 24px; border: 1px solid transparent;
        background: var(--primary-soft); color: var(--primary-ink); font-weight: 500; text-align: center; text-decoration: none; }
      .btn.primary { background: var(--primary); color: var(--on-primary); border-color: var(--primary-ink); }
      .btn.danger { background: var(--danger-bg); color: var(--danger); }
      .btn.danger.solid { background: var(--danger); color: var(--card); }
      .btn.link { background: none; border: 0; padding: 0 8px; min-height: 44px; }
      .btns { display: flex; flex-wrap: wrap; gap: 12px; }
      .muted { color: var(--text2); font-size: 14px; }
      .back { display: inline-flex; align-items: center; min-height: 44px; font-weight: 500; text-decoration: none; color: var(--primary-ink); }
      .note { border-radius: var(--r-card); padding: 12px 16px; margin: 12px 0 16px; background: var(--primary-soft); border: 1px solid var(--line); }
      .note.warn { background: var(--warn-bg); color: var(--warn); border: 2px solid var(--warn); }
      .note.err { background: var(--danger-bg); color: var(--danger); border: 2px solid var(--danger); }
      .note .btns { margin-top: 8px; }
      .note a.nl { display: inline-flex; align-items: center; min-height: 44px; margin-left: 8px; color: inherit; font-weight: 500; }
      .note.band { margin: 8px max(16px, env(safe-area-inset-right, 0px)) 0 max(16px, env(safe-area-inset-left, 0px)); }
      .note .btn { background: var(--card); border: 1px solid var(--line); color: var(--text); }

      /* Zustände */
      .skel { height: 84px; border-radius: var(--r-card); background: var(--primary-soft); margin: 16px 0; animation: puls 1.4s ease-in-out infinite; }
      @keyframes puls { 50% { opacity: 0.5; } }
      .leer { display: grid; justify-items: center; text-align: center; gap: 8px; padding: 24px 16px 16px; background: var(--card); border-radius: var(--r-big); box-shadow: 0 1px 3px var(--shadow); margin: 8px 0 16px; }
      .leer .bild { width: min(220px, 64%); display: block; }
      .leer .bild svg { width: 100%; height: auto; display: block; }
      .leer .et { font-size: 18px; font-weight: 500; margin: 8px 0 0; max-width: 34ch; line-height: 1.35; overflow-wrap: anywhere; }
      .leer .btns { justify-content: center; margin: 8px 0; }

      /* Blatt */
      dialog.blatt { border: 0; padding: 0; background: var(--card); color: var(--text); width: 100%; max-width: 560px; max-height: 92vh; max-height: 92dvh;
        overscroll-behavior: contain; overflow: auto; border-radius: var(--r-big); box-shadow: 0 8px 32px var(--shadow); touch-action: pan-x pinch-zoom; }
      dialog.blatt::backdrop { background: var(--scrim, rgba(0, 0, 0, 0.5)); }
      .blatt-in { position: relative; padding: 20px max(16px, env(safe-area-inset-right, 0px)) max(20px, env(safe-area-inset-bottom, 0px)) max(16px, env(safe-area-inset-left, 0px)); }
      .blatt h2 { margin: 0 0 8px; padding-right: 56px; touch-action: none; outline: none; }
      .griff { height: 20px; margin: -12px 0 0; touch-action: none; display: grid; place-items: center; }
      .griff::before { content: ""; width: 44px; height: 5px; border-radius: 3px; background: var(--line); }
      .blatt-x { float: right; position: sticky; top: 0; z-index: 3; margin: -8px -8px 0 8px; background: var(--card); border: 0; }
      .knoepfe:not(:empty) { position: sticky; bottom: 0; z-index: 2; background: var(--card); margin-top: 16px; padding: 8px 0; display: flex; flex-wrap: wrap; gap: 12px; justify-content: flex-end; }
      @media (max-width: 699px) { dialog.blatt { margin: auto 0 0; max-width: none; border-radius: var(--r-big) var(--r-big) 0 0; } }

      /* Meldungen */
      .toastbox { position: absolute; left: 50%; transform: translateX(-50%); bottom: calc(var(--navh) + var(--minih) + 16px); z-index: 2000; display: grid; gap: 8px; width: min(92%, 520px); pointer-events: none; }
      .toastbox > * { pointer-events: auto; }
      .toastbox.imblatt { position: fixed; bottom: auto; top: max(12px, env(safe-area-inset-top, 0px)); }
      .toast { display: flex; align-items: center; gap: 12px; background: var(--text); color: var(--bg); padding: 12px 16px; border-radius: var(--r-card); touch-action: pan-y; }
      .toast .tmsg { flex: 1; min-width: 0; overflow-wrap: anywhere; }
      .toast.err { background: var(--danger-bg); color: var(--danger); border: 2px solid var(--danger); }
      .toast .tok { min-width: 56px; min-height: 44px; border-radius: 22px; border: 1px solid currentColor; background: none; color: inherit; font-weight: 700; padding: 0 16px; flex: none; }
      @media (prefers-reduced-motion: reduce) { .skel { animation: none; } }
    `, bausteinStil(), ...Object.values(SEITEN).map((x) => x.stil?.()).filter(Boolean)];
  }

  if (!customElements.get('tobibox-app')) customElements.define('tobibox-app', TobiboxApp);
}

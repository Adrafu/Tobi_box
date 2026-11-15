/* Tobi Box: neue Alltagsseite für Home Assistant (Paket A6, Design docs/designs/ha-oberflaeche.md).
 *
 * Panel-Gerüst: vier Reiter, Panelbreite per ResizeObserver, Kopf, Hash-Routen, Tokens aus dem
 * HA-Theme mit Kontrastfunktion, Zustände (Lädt, Fehler, Leer), Blätter (<dialog>), Meldungen, Abo der
 * WebSocket-Themen über hass.connection, Platz für den Mini-Player und der Punkt am Reiter „Geräte“.
 * Die Inhalte der Seiten sind eigene Module unter seiten/ (A7: Start, Bibliothek, Suche; weitere folgen in A7b, A8, A12),
 * gemeinsame Bausteine stehen in bausteine.js, das Verzeichnis in seiten/index.js. Die Bewegung (A6m: Blätter, iOS-Blatt-Effekt,
 * Meldungen, Seitenwechsel, Pille, Cover-Flug der Serienseite) steht hier und in bewegung.js; die Werte sind Tokens im Stil (`--dauer-*`,
 * `--kurve*`, `--feder*`, `--druck*`, `--hinten-*`). Bindend ist Messung 7 (docs/plan/messungen-ha-testpanel.md): nie `startViewTransition`,
 * FLIP mit Ecken, Blatt-Effekt nur auf dem sichtbaren Inhalt (`.hinten`), das Blatt steckt nicht darin.
 *
 * Technik: Lit aus ./lit-all.min.js (fest eingecheckt, dasselbe wie die alte Seite, nichts aus dem Netz).
 * Namen und Texte aus Daten werden nur als Text gesetzt (Lit maskiert selbst). Die Texte stehen in texte.js.
 * Die Illustrationen der leeren Zustände (A6b) kommen aus ./illustrationen.js; fehlt die Datei oder ein Bild,
 * steht ein schlichter Platzhalter da.
 */
import { fuellen, fehlerText, SEITE, TOBIE, LEER, TECHNIK, SUCHE, EINGANG, PLAYER } from './texte.js';
import { eingangAbleiten, bandZustand, naechsteAenderung } from './eingang.js';
import { SEITEN } from './seiten/index.js';
import { folgenAktion } from './seiten/tobies.js';
import { reduziert, kannAnimieren, tokenMs, kurve, animiere, nachEnde, flipKlon, rechteck } from './bewegung.js';
import { initLit, bausteinStil, CoverLader, coverGrossUrl, leererZustand, kopfAktion, korbNeueFremde, korbNeuesteMs, ic as symbol } from './bausteine.js';
import { Spieler, spielerStil } from './player.js';

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
const STILLE_KOEPFE = ['serie', 'tobie', 'neu', 'neu-warten', 'neu-ziel', 'neu-queue', 'geben']; // Seiten mit eigener großer Überschrift im Inhalt

const TECHNIK_SUB = { boxen: 'technik_boxen', speicher: 'technik_speicher', liste: 'technik_liste', tobies: 'technik_tobies', meldungen: 'technik_meldungen', einstellungen: 'technik_einstellungen' };

/* Adresse (nach `#`) → { name, tab, id, sub, seite (Schlüssel in SEITE.seiten), zurueck, umleitung }.
 * `umleitung` ist die Adresse, auf die die Seite umgeschrieben wird (Design 3.2). `faehigkeiten`: hello.faehigkeiten,
 * oder null, solange hello noch nicht da ist (dann keine Umleitung wegen fehlender Fähigkeit). */
export function parseRoute(hash, { faehigkeiten = null } = {}) {
  const [h, abfrage = ''] = String(hash || '').replace(/^#/, '').split('?'); // `#bibliothek?sortierung=neu` (Link „Alle anzeigen“ vom Start)
  const r = (o) => o;
  // A9/A10: Seiten der Tobies tragen ihr festes Ziel und den Rückweg in der Adresse (`#neu?s=<serie>&f=<folge>`, `#neu-ziel-<kennung>?von=tobies`)
  const q = (o) => (abfrage ? { ...o, abfrage: Object.fromEntries(new URLSearchParams(abfrage)) } : o);
  if (h === '' || h === 'start') return r({ name: 'start', tab: 'start' });
  if (h.startsWith('serie-')) return r({ name: 'serie', tab: 'bibliothek', id: h.slice(6), seite: 'serie', zurueck: 'bibliothek' });
  if (h.startsWith('tobie-')) return r(q({ name: 'tobie', tab: 'tobies', id: h.slice(6), seite: 'tobie', zurueck: 'tobies' }));
  if (h === 'neu' || h === 'neu-warten' || h === 'neu-queue') return r(q({ name: h, tab: 'tobies', seite: h.replace('-', '_'), zurueck: 'tobies' }));
  if (h === 'neu-ziel' || h.startsWith('neu-ziel-')) {
    // `#neu-ziel-<kennung>`: von der Karte oder Meldung auf „Geräte“ (Reiter „Geräte“ bleibt markiert), nach Weg 1 `?von=tobies`
    const id = h.slice(9) || undefined;
    const von = new URLSearchParams(abfrage).get('von');
    return r(q({ name: 'neu-ziel', tab: !id || von === 'tobies' ? 'tobies' : 'geraete', id, seite: 'neu_ziel', zurueck: von === 'tobies' || !id ? 'tobies' : 'geraete' }));
  }
  if (h.startsWith('geben-')) return r(q({ name: 'geben', tab: 'bibliothek', id: h.slice(6), seite: 'geben', zurueck: 'bibliothek' }));
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
  if (h === 'bibliothek') return r({ name: h, tab: h, sortierung: new URLSearchParams(abfrage).get('sortierung') || undefined });
  if (REITER.includes(h)) return r({ name: h, tab: h });
  return r({ name: 'start', tab: 'start' });
}

/* ------------------------------------------------------------------ Daten: hello, Abo, Listen (ohne DOM) */

const GRENZE_LAEDT_MS = 10000;
const KORB_GESEHEN = 'tobibox.korb_gesehen'; // localStorage: Zeitpunkt (ms) des neuesten Papierkorb-Eintrags, den dieses Gerät gesehen hat (AC3)
const THEMEN = ['boxen', 'neue_tobies', 'konfig']; // dazu `eingang` (Band und Punkt, A11b) und `warteschlange`, wenn hello die Fähigkeit zusagt (Vertrag 4.5, 4.8)

export class AppStore {
  constructor({ ladeGrenzeMs = GRENZE_LAEDT_MS } = {}) {
    this.ladeGrenzeMs = ladeGrenzeMs;
    this.s = { phase: 'laedt', fehlerCode: null, faehigkeiten: null, grenzen: {}, boxen: {}, boxAnzeigen: {}, neue: [], warteschlange: [], platz: [], konfigZustand: 'ok', verbindungWeg: false,
      eingang: [], offeneSerien: null, lokaleUploads: 0, lokaleNamen: [], korbNeu: [] }; // korbNeu: neue Papierkorb-Einträge anderer Benutzer, nur für Administratoren (AC3);  Eingang: Einträge aus `eingang/list`; offeneSerien: Serien, die noch „bitte prüfen“ sind (A11b)
    this.hass = null;
    this.onNeuerTobie = null; // ({ uid, box, anzeige }) beim ersten Auftauchen einer unbekannten Kennung nach dem Start
    this.onWiederda = null; // () nach dem Wiederverbinden: die aktive Seite lädt neu
    this.onAbgearbeitet = null; // (daten) ein Tobie hat eine Vormerkung genommen (Thema `warteschlange`, `abgearbeitet`)
    this._ls = new Set();
    this._evLs = new Set(); // Seiten, die auf Ereignisse warten (Weg 1, Wartekarte): `ereignis(fn)`
    this._lauf = 0;
    this._bekannt = new Set();
    this._eingangTimer = null;
    this._korbGesehen = null; // Millisekunden (Serverzeit): was im Papierkorb schon gesehen ist; je Gerät in `localStorage`, ohne Speicher nur bis zum Neuladen
  }

  onChange(fn) { this._ls.add(fn); return () => this._ls.delete(fn); }
  /* Jedes Ereignis des Abos geht danach an `fn(ev)` (nachdem der Speicher es aufgenommen hat). Gibt die Abmeldung zurück. */
  onEreignis(fn) { this._evLs.add(fn); return () => this._evLs.delete(fn); }
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
    clearTimeout(this._eingangTimer);
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
      this.s.grenzen = hello.grenzen || {}; // upload_max_bytes, upload_parallel, endungen … (A11a: Hinzufügen)
      this.s.boxAnzeigen = { ...(hello.grenzen?.box_anzeigen || {}), ...(hello.box_anzeigen || {}) };
      this.s.konfigZustand = hello.konfig?.zustand || 'ok';
      const themen = [...THEMEN, ...(fae.includes('eingang') ? ['eingang'] : []), ...(fae.includes('warteschlange') ? ['warteschlange'] : []), ...(this._korbBeobachten() ? ['medien'] : [])];
      this._abo = await this.hass.connection.subscribeMessage((ev) => this._ereignis(ev), { type: 'tobibox/subscribe', themen });
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
    if (fae.includes('warteschlange')) {
      const r = await this._api('tobibox/warteschlange/list');
      neu.warteschlange = r.eintraege || [];
    }
    this._set(neu);
    await this.ladeEingang();
    this.ladeKorbNeu(); // nicht abwarten: der Punkt am Technik-Symbol darf den Start nicht aufhalten
  }

  /* Papierkorb-Punkt am Technik-Symbol (AC3, nur Administratoren): neue Einträge anderer Benutzer seit dem letzten Besuch von „Technik › Speicher“
   * auf diesem Gerät. Gelesen wird `papierkorb/list` (Vertrag W 3.3: `geloescht_von`, `geloescht_am`); neu geladen wird beim Start, nach dem
   * Wiederverbinden und bei jedem Ereignis `medien`/`papierkorb_geaendert`. Es gibt kein HA-Ereignis und keine HA-Mitteilung. */
  _korbBeobachten() { return this.hass?.user?.is_admin === true && (this.s.faehigkeiten || []).includes('papierkorb'); }

  _korbLiesGesehen() {
    try { const v = Number(window.localStorage?.getItem(KORB_GESEHEN)); return Number.isFinite(v) && v > 0 ? v : null; } catch { return null; }
  }
  _korbMerke(ms) { try { window.localStorage?.setItem(KORB_GESEHEN, String(ms)); } catch { /* ohne Speicher: gilt bis zum Neuladen */ } }

  /* Stand „gesehen“ in Millisekunden oder null, solange er noch nicht feststeht. */
  korbGesehenStand() { return this._korbGesehen; }

  async ladeKorbNeu() {
    if (!this.hass || !this._korbBeobachten()) { if (this.s.korbNeu.length) this._set({ korbNeu: [] }); return; }
    if (this._korbLaedt) { this._korbNochmal = true; return; }
    this._korbLaedt = true;
    const lauf = this._lauf;
    try {
      do {
        this._korbNochmal = false;
        const r = await this._api('tobibox/papierkorb/list', { limit: 100, offset: 0 });
        if (lauf !== this._lauf) return;
        const liste = r.eintraege || [];
        if (this._korbGesehen === null) { // erster Besuch auf diesem Gerät: was jetzt schon drin liegt, ist nicht neu
          this._korbGesehen = this._korbLiesGesehen() ?? Math.max(1, korbNeuesteMs(liste));
          if (this._korbLiesGesehen() === null) this._korbMerke(this._korbGesehen);
        }
        this._set({ korbNeu: korbNeueFremde(liste, this.hass?.user?.id, this._korbGesehen) });
      } while (this._korbNochmal);
    } catch { /* der nächste Anlass (Ereignis, Neuladen) holt es noch einmal */ } finally { this._korbLaedt = false; }
  }

  /* Die Seite „Technik › Speicher“ hat den Papierkorb geladen und angezeigt: alles darin gilt als gesehen, der Punkt verschwindet. */
  korbGesehen(eintraege) {
    const ms = Math.max(1, this._korbGesehen ?? 0, korbNeuesteMs(eintraege)); // mindestens 1: „0“ wäre im Speicher nicht von „nie“ zu unterscheiden
    if (ms !== this._korbGesehen) { this._korbGesehen = ms; this._korbMerke(ms); }
    if (this.s.korbNeu.length) this._set({ korbNeu: [] });
  }

  /* Eingang (A11b): `eingang/list` (Filter `alle`: was noch im Eingang liegt und die letzten einsortierten) und, wenn ein Eintrag „bitte ansehen“
   * trägt, welche Serien das wirklich noch sind (`serien/list` mit Filter `pruefen`): „Das ist richtig“ löscht nur das Kennzeichen der Serie, nicht
   * den Eintrag im Protokoll (Vertrag 3.9, 28). Fehler (zum Beispiel `medien_nicht_erreichbar`, solange nie geprüft wurde) lassen den alten Stand stehen. */
  async ladeEingang() {
    const fae = this.s.faehigkeiten || [];
    if (!this.hass || !fae.includes('eingang')) return;
    if (this._eingangLaedt) { this._eingangNochmal = true; return; }
    this._eingangLaedt = true;
    const lauf = this._lauf;
    try {
      do {
        this._eingangNochmal = false;
        const r = await this._api('tobibox/eingang/list', { filter: 'alle', limit: 100 });
        const eintraege = r.eintraege || [];
        let offen = null;
        if (fae.includes('bibliothek') && eintraege.some((e) => e.pruefen)) {
          const sr = await this._api('tobibox/serien/list', { filter: ['pruefen'], limit: 200 });
          offen = new Set((sr.serien || []).map((x) => x.id));
        }
        if (lauf !== this._lauf) return;
        this._set({ eingang: eintraege, offeneSerien: offen });
        this._planeEingang();
      } while (this._eingangNochmal);
    } catch { /* der nächste Anlass (Ereignis, Neuladen) holt es noch einmal */ } finally { this._eingangLaedt = false; }
  }

  /* Was die Seiten vom Eingang sehen (Ableitung nach eingang.js). */
  eingangAbl() { return eingangAbleiten(this.s.eingang, { offeneSerien: this.s.offeneSerien }); }

  /* Uploads, die diese Seite selbst gerade sendet (A11a meldet sie); sie zählen im Band wie laufende Einträge. `namen` sind die Namen im Eingang, die zu
   * diesen Uploads gehören (Gruppen-Ordner „Upload ab12cd34“, Dateinamen): ein Eintrag mit so einem Namen zählt nicht noch einmal. */
  setLokaleUploads(n, namen = []) {
    const z = Math.max(0, Number(n) || 0);
    const liste = (Array.isArray(namen) ? namen : []).map(String);
    if (z === this.s.lokaleUploads && liste.join('\n') === this.s.lokaleNamen.join('\n')) return;
    this._set({ lokaleUploads: z, lokaleNamen: liste });
  }

  /* Das Band und der Punkt am Reiter: wie `eingangAbl()`, ohne die laufenden Einträge, die zu einem Upload dieser Seite gehören (der zählt als `lokaleUploads`). */
  eingangAblBand() {
    const abl = this.eingangAbl();
    const namen = this.s.lokaleNamen;
    if (!namen.length) return abl;
    return { ...abl, laeuft: abl.laeuft.filter((x) => x.eintrag.quelle === 'nas' || !namen.includes(x.eintrag.name)) };
  }

  /* Ein Zeitgeber, damit „Alles hinzugefügt.“ und Einträge nach 24 Stunden von selbst verschwinden. */
  _planeEingang() {
    clearTimeout(this._eingangTimer);
    const ms = naechsteAenderung(this.s.eingang);
    if (ms === null) return;
    this._eingangTimer = setTimeout(() => { this._set({}); this._planeEingang(); }, Math.min(ms, 3600000));
    this._eingangTimer?.unref?.();
  }

  /* Die Vormerkungen neu holen (nach jedem Ereignis, die `position` der übrigen ändert sich; Vertrag 4.8). */
  async ladeWarteschlange() {
    if (!(this.s.faehigkeiten || []).includes('warteschlange') || !this.hass) return;
    const lauf = this._lauf;
    try {
      const r = await this._api('tobibox/warteschlange/list');
      if (lauf === this._lauf) this._set({ warteschlange: r.eintraege || [] });
    } catch { /* die nächste Meldung holt sie noch einmal */ }
  }

  /* Karte „Ein neuer Tobie hat einen Platz bekommen. Name geben?“ (N11): bleibt, bis er einen Namen hat oder „Später“ gewählt ist. */
  platzEntfernen(uid) {
    if (this.s.platz.some((p) => p.uid === uid)) this._set({ platz: this.s.platz.filter((p) => p.uid !== uid) });
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
    this._aufnehmen(ev);
    for (const f of [...this._evLs]) { try { f(ev); } catch { /* eine Seite darf die anderen nicht stören */ } }
  }

  _aufnehmen(ev) {
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
    } else if (ev.thema === 'eingang') {
      if (ev.art === 'geaendert' || ev.art === 'neu_einsortiert' || ev.art === 'durchlauf_fertig') this.ladeEingang(); // `snapshot` bringt nur Zahlen
    } else if (ev.thema === 'medien') {
      if (ev.art === 'papierkorb_geaendert') this.ladeKorbNeu();
    } else if (ev.thema === 'warteschlange' && ev.art !== 'snapshot') {
      this.ladeWarteschlange();
      if (ev.art === 'abgearbeitet' && d.uid) {
        if (!d.name) this._set({ platz: [{ uid: d.uid, box: d.box ?? null }, ...this.s.platz.filter((p) => p.uid !== d.uid)] });
        this.onAbgearbeitet?.(d);
      }
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
  chev: 'M10 6 8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z',
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
      this._themenStand = '';
      this._flug = null; // vorgemerkter Cover-Flug der Serienseite: { art: 'hin' | 'zurueck', id, rect, radius, zeit }
      this._pillenStand = new Map(); // letzte Stelle der Pillen (Reiter, Segmente), auch wenn die Seite neu gebaut wird
      this._seiten = {}; // je Seite ein Objekt aus seiten/<name>.js (erzeuge(ctx)), angelegt beim ersten Besuch
      this._seiteObj = null;
      this._seiteKey = null;
      this._covers = new CoverLader(() => this.hass);
      this.ctx = this._baueCtx();
      this.spieler = new Spieler(this.ctx); // Player (A8b): `<audio>`, Leiste und Vollansicht; die Seiten erreichen ihn über `ctx.spieler`
      this._spielerMini = false;
      this.store.onWiederda = () => this._seiteObj?.neuLaden?.();
      this._off = this.store.onChange(() => { this._tick += 1; if (this.store.s.phase === 'bereit') this._leseHash(); });
      this.store.onNeuerTobie = (n) => this._neuerTobie(n);
      this.store.onAbgearbeitet = (d) => this._abgearbeitet(d);
      /* Home Assistant fängt Klicks auf Links ab, setzt die Adresse mit `history.pushState` und meldet `location-changed`; ein
       * `hashchange` kommt dann nicht (B1). Darum hören wir auch auf `location-changed` und `popstate`. Fokus und Scrollen nur,
       * wenn sich die Adresse wirklich geändert hat (Zurück-Taste meldet `popstate` und `hashchange` zugleich). */
      this._onHash = () => {
        const vorher = this._route;
        const kopf = vorher.name === 'serie' ? this.renderRoot.querySelector('.cover.se-xl[data-cover-gross]') : null;
        const kopfFlaeche = kopf ? { rect: rechteck(kopf.getBoundingClientRect()), radius: this._radius(kopf) } : null;
        const stand = this._scrollStand(); // Scrollstand der Seite, die wir gerade verlassen (AM6)
        this._leseHash();
        this._flugNachHash(vorher, kopfFlaeche);
        if (this._hash === this._behandelt) return;
        const vorherHash = this._behandelt;
        this._behandelt = this._hash;
        const scrollWieder = this._herkunftNachHash(vorherHash, stand);
        this._schliesseBlattBeiRoute(); this._fokusMain = true; this._scrollOben = scrollWieder === null; this._scrollWieder = scrollWieder; this.requestUpdate();
      };
      this._onResize = () => this._messeBreite();
      this._coverKlick = (e) => this._coverMerken(e);
      this._coverZeiger = (e) => this._grossVorladen(e.target?.closest?.('a[data-serie]')?.querySelector('.cover[data-cover]'));
    }

    /* ---- Lebenslauf */
    connectedCallback() {
      super.connectedCallback();
      this._leseHash();
      this._behandelt = this._hash;
      window.addEventListener('hashchange', this._onHash);
      window.addEventListener('popstate', this._onHash);
      window.addEventListener('location-changed', this._onHash);
      this._messeBreite();
      this._messeRand();
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
      this.renderRoot.addEventListener('click', this._coverKlick, true);
      this.renderRoot.addEventListener('pointerdown', this._coverZeiger, true);
      this._vv = window.visualViewport;
      this._vvFn = () => this._tastatur(this.renderRoot.activeElement);
      this._vv?.addEventListener?.('resize', this._vvFn);
      this.spieler.anmelden();
      ladeIllustrationen().then((b) => { this._bilder = b; });
    }

    disconnectedCallback() {
      super.disconnectedCallback();
      window.removeEventListener('hashchange', this._onHash);
      window.removeEventListener('popstate', this._onHash);
      window.removeEventListener('location-changed', this._onHash);
      window.removeEventListener('resize', this._onResize);
      this._ro?.disconnect(); this._ro = null;
      this._seiteObj?.verlassen?.(); this._seiteObj = null; this._seiteKey = null;
      this._covers.abmelden();
      this.renderRoot.removeEventListener('focusin', this._fokusEin);
      this.renderRoot.removeEventListener('focusout', this._fokusAus);
      this.renderRoot.removeEventListener('click', this._coverKlick, true);
      this.renderRoot.removeEventListener('pointerdown', this._coverZeiger, true);
      clearTimeout(this._hintenTimer);
      this._vv?.removeEventListener?.('resize', this._vvFn);
      this.spieler.abmelden();
      this.store.detach();
    }

    willUpdate(ch) {
      if (ch.has('hass') && this.hass) {
        if (!this.store.hass) this.store.attach(this.hass); else this.store.hass = this.hass;
      }
      this.spieler.vorZeichnen(); // Kreuzblende des Mini-Covers: eine Kopie des alten Covers, solange es noch im DOM steht
    }

    updated(ch) {
      this.setAttribute('data-layout', this._layout);
      this._wendeTokens();
      this._messeRand();
      this._seitenWechsel();
      this._doppelteUeberschrift();
      if (this._blatt && !this._blatt.offen) this._blattEinrichten();
      if (this._scrollWieder != null) this._scrollHalten();
      if (this._scrollOben) { this._scrollOben = false; const r = this.renderRoot.querySelector('.rahmen'); const sp = this.renderRoot.querySelector('.spalte'); if (r) r.scrollTop = 0; if (sp) sp.scrollTop = 0; }
      if (this._fokusMain) { this._fokusMain = false; this.renderRoot.querySelector('main')?.focus({ preventScroll: true }); }
      if (ch.has('hass')) this._wendeTokens();
      this._covers.beobachte(this.renderRoot);
      this._seiteObj?.nachRender?.(this.renderRoot);
      this._pillenSetzen();
      this._coverFlug();
      this._spielerNach();
    }

    /* Player (A8b, A8m): Leiste zeigen oder verstecken, `data-voll` am Host (Vollansicht deckt die Seite: kein iOS-Blatt-Effekt), danach die Vollansicht
     * öffnen und die gemerkte Stelle holen. */
    _spielerNach() {
      const sp = this.spieler;
      const da = !!sp.s;
      const m = this.miniPlatz;
      if (da !== this._spielerMini) {
        this._spielerMini = da;
        this.setMini(da, (da && m?.offsetHeight) || 67);
        if (da) sp.miniEinblenden();
      } else if (da && m && m.offsetHeight && this.style.getPropertyValue('--minih') !== `${m.offsetHeight}px`) this.style.setProperty('--minih', `${m.offsetHeight}px`);
      if (this.hasAttribute('data-voll') !== sp.offen) this.toggleAttribute('data-voll', sp.offen);
      sp.nachRender();
      if (this.store.s.phase === 'bereit') sp.wiederherstellen();
    }

    /* Der Seitenkopf trägt den Titel der Seite (große Überschrift am Computer, Titel neben dem Menüknopf am Handy). Steht dieselbe
     * Überschrift noch einmal im Inhalt, bleibt sie für Screenreader und Tests da, wird aber nicht gezeigt (AB4: nie zwei Titel). */
    _doppelteUeberschrift() {
      const root = this.renderRoot;
      const kopf = root.querySelector('.kopf');
      const h1 = kopf?.querySelector('h1');
      const text = (h1?.textContent || '').trim();
      for (const h of root.querySelectorAll('main h2[data-doppelt]')) h.removeAttribute('data-doppelt');
      kopf?.removeAttribute('data-still');
      if (!text || kopf.classList.contains('still')) return; // die Seite trägt ihren Titel selbst im Inhalt (Serie, Tobie, Neuer Tobie)
      const h2 = root.querySelector('main h2');
      if (!h2 || h2.textContent.trim() !== text) return;
      // Am Computer steht auf Unterseiten „‹ Zurück“ vor dem Titel: dann trägt die Überschrift der Seite den Titel, der Kopf schweigt
      if (this._layout === 'seite' && h2.previousElementSibling?.classList.contains('back')) kopf.setAttribute('data-still', '');
      else h2.setAttribute('data-doppelt', '');
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

    /* HA (ha-panel-custom, Light-DOM, ohne eigene Höhe) setzt um unser Element Innenabstand für die Safe-Area. Wir
     * ziehen ihn von der Höhe ab (--rand-v) und lassen unsere Leiste dann keinen zweiten Abstand unten bauen (--sab). */
    _messeRand() {
      let v = 0; let unten = 0;
      try {
        const p = this.parentElement;
        if (p) { const cs = getComputedStyle(p); unten = parseFloat(cs.paddingBottom) || 0; v = (parseFloat(cs.paddingTop) || 0) + unten; }
      } catch { /* ohne Stil */ }
      const rv = `${v}px`;
      const sab = unten > 0 ? '0px' : 'var(--tb-safe-unten, env(safe-area-inset-bottom, 0px))';
      if (this.style.getPropertyValue('--rand-v') !== rv) this.style.setProperty('--rand-v', rv);
      if (this.style.getPropertyValue('--sab') !== sab) this.style.setProperty('--sab', sab);
    }

    _tastatur(ziel) {
      const feld = ziel && ziel.matches?.('input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]):not([type=button]):not([type=submit]), textarea');
      const vv = this._vv;
      this._kbd = !!(feld && vv && vv.height < (window.innerHeight || 0) * 0.8);
    }

    /* ================================================================== Bewegung der Seiten (A6m) */
    _radius(el) { try { return parseFloat(getComputedStyle(el).borderTopLeftRadius) || 0; } catch { return 0; } }

    /* Seitenwechsel (Reiter, Unterseiten ohne Cover-Übergang): nur kurzes Überblenden, die Seite gleitet nie. */
    _seiteBlenden() {
      const m = this.renderRoot.querySelector('main');
      if (!m || !kannAnimieren(m) || reduziert()) return; // bei „weniger Bewegung“ schaltet die Seite direkt um
      // erst ist der neue Inhalt gezeichnet (wir sind nach dem Zeichnen), dann ein kurzes Überblenden, das nie ganz durchsichtig wird (kein leeres Bild)
      animiere(m, [{ opacity: 0.6 }, { opacity: 1 }], { duration: tokenMs(this, '--dauer-kurz'), easing: kurve(this) });
    }

    /* Tipp auf eine Kachel, Zeile oder einen Treffer mit Cover: die Fläche des Covers merken (Cover-Flug der Serienseite, R17-1). */
    _coverMerken(e) {
      if (e.defaultPrevented || (e.button ?? 0) > 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = e.target?.closest?.('a[data-serie]');
      const c = a?.querySelector('.cover[data-cover]');
      if (!c) return;
      this._grossVorladen(c);
      this._flug = { art: 'hin', id: a.dataset.serie, rect: rechteck(c.getBoundingClientRect()), radius: this._radius(c), zeit: Date.now() };
    }

    /* AM7: das große Cover schon beim Antippen holen (Zeiger runter, bevor die Adresse wechselt); die Serienseite nimmt dasselbe Versprechen aus dem Speicher. */
    _grossVorladen(c) {
      const id = c?.dataset?.cover; const stand = c?.dataset?.stand;
      if (id && stand && stand !== '?') coverGrossUrl(this._covers, id, stand);
    }

    /* Die Adresse hat gewechselt: ein Flug „hin“ gilt nur für seine Serienseite; wer die Serienseite verlässt, merkt sich den großen Kopf für den Rückflug. */
    _flugNachHash(vorher, kopfFlaeche) {
      const r = this._route;
      if (this._flug?.art === 'hin' && !(r.name === 'serie' && r.id === this._flug.id)) this._flug = null;
      if (this._hash === this._behandelt) return;
      if (vorher.name === 'serie' && r.name !== 'serie' && kopfFlaeche) this._flug = { art: 'zurueck', id: vorher.id, ...kopfFlaeche, zeit: Date.now() };
    }

    /* ---- Herkunft der Serienseite (AM6): „‹ Start“, „‹ Bibliothek“ … führt dorthin zurück, woher man kam, mit dem alten Scrollstand. */
    _scrollStand() {
      const w = this.renderRoot;
      if (!w?.querySelector) return 0;
      return Math.max(w.querySelector('.rahmen')?.scrollTop ?? 0, w.querySelector('.spalte')?.scrollTop ?? 0);
    }

    /* Die Adresse hat gewechselt (einmal je Wechsel). Nach einer Serienseite hin: Herkunft merken (Stapel, damit Serie → Serie → zurück → zurück stimmt). Zurück auf die
     * Herkunft (Knopf, Zurück-Taste, Wischen): Eintrag vom Stapel nehmen und den Scrollstand zurückgeben. Jede andere Seite räumt den Stapel. */
    _herkunftNachHash(vorherHash, stand) {
      const st = this._herkunftStapel ?? (this._herkunftStapel = []);
      const nach = parseRoute(this._hash);
      const von = parseRoute(vorherHash);
      const oben = st[st.length - 1];
      const gleich = (a, b) => String(a || '').replace(/^#/, '') === String(b || '').replace(/^#/, '') || (!String(a || '').replace(/^#/, '') && String(b).replace(/^#/, '') === 'start') || (!String(b || '').replace(/^#/, '') && String(a).replace(/^#/, '') === 'start');
      if (oben && gleich(oben.hash, this._hash)) { st.pop(); return nach.name === 'serie' ? null : oben.scroll; }
      if (nach.name === 'serie') {
        if (von.name !== 'serie' || vorherHash !== this._hash) {
          if (SEITE.zurueck[von.name]) st.push({ hash: vorherHash || '#start', name: von.name, scroll: von.name === 'serie' ? 0 : stand });
          else st.length = 0;
        }
        if (st.length > 12) st.shift();
        return null;
      }
      st.length = 0;
      return null;
    }

    /* Rückweg zur Herkunft: den alten Scrollstand setzen und ein halbe Sekunde lang halten, bis die Liste ihre echte Höhe hat (Zeilen, die noch nicht gezeichnet waren,
     * wachsen oder schrumpfen und der Browser schiebt sonst den Stand mit). Eine Eingabe des Fingers oder Rads beendet das Halten sofort. */
    _scrollHalten() {
      const setze = () => {
        const v = this._scrollWieder;
        if (v == null) return false;
        const r = this.renderRoot.querySelector('.rahmen'); const sp = this.renderRoot.querySelector('.spalte');
        if (r && Math.abs(r.scrollTop - v) > 0.5) r.scrollTop = v;
        if (sp && Math.abs(sp.scrollTop - v) > 0.5) sp.scrollTop = v;
        return true;
      };
      setze();
      if (this._scrollSchleife) return;
      this._scrollSchleife = true;
      const bis = Date.now() + 600;
      const stopp = () => { this._scrollWieder = null; };
      this.renderRoot.addEventListener('touchstart', stopp, { once: true, passive: true });
      this.renderRoot.addEventListener('wheel', stopp, { once: true, passive: true });
      const schritt = () => {
        if (this._scrollWieder == null || Date.now() > bis || !this.isConnected || typeof requestAnimationFrame !== 'function') {
          this._scrollWieder = null; this._scrollSchleife = false;
          this.renderRoot.removeEventListener('touchstart', stopp); this.renderRoot.removeEventListener('wheel', stopp);
          return;
        }
        setze();
        requestAnimationFrame(schritt);
      };
      if (typeof requestAnimationFrame === 'function') requestAnimationFrame(schritt); else this._scrollSchleife = false;
    }

    get _herkunft() {
      const o = this._herkunftStapel?.[this._herkunftStapel.length - 1];
      const nach = parseRoute(this._hash);
      if (!o || nach.name !== 'serie') return null;
      return { hash: o.hash, label: SEITE.zurueck[o.name] };
    }

    /* Nach jedem Zeichnen: wartet ein Flug und steht das Cover jetzt da, fliegt es (FLIP mit `element.animate`, nie View Transitions). */
    _coverFlug() {
      const f = this._flug;
      if (!f) return;
      if (Date.now() - f.zeit > (f.art === 'hin' ? 3000 : 2000)) { this._flug = null; return; }
      const r = this._route;
      const wurzel = this.renderRoot;
      let el = null;
      if (f.art === 'hin') {
        if (r.name !== 'serie' || r.id !== f.id) return;
        el = wurzel.querySelector('.cover.se-xl[data-cover-gross]');
        if (!el || el.dataset.coverGross !== f.id) return; // die Serie lädt noch
      } else {
        if (r.name === 'serie') { this._flug = null; return; }
        const alle = [...wurzel.querySelectorAll('a[data-serie] .cover[data-cover]')].filter((c) => c.dataset.cover === f.id);
        const vp = wurzel.querySelector(this._layout === 'seite' ? '.spalte' : '.rahmen')?.getBoundingClientRect();
        // mehrere Kacheln derselben Serie (Start): die erste, die im sichtbaren Teil liegt
        el = (vp && alle.find((c) => { const b = c.getBoundingClientRect(); return b.bottom > vp.top && b.top < vp.bottom && b.right > vp.left && b.left < vp.right; })) ?? alle[0] ?? null;
        if (!el) return; // die neue Seite lädt noch
        const sicht = wurzel.querySelector(this._layout === 'seite' ? '.spalte' : '.rahmen')?.getBoundingClientRect();
        const b = el.getBoundingClientRect();
        if (sicht && (b.bottom <= sicht.top || b.top >= sicht.bottom || b.right <= sicht.left || b.left >= sicht.right)) { this._flug = null; return; } // nicht im sichtbaren Teil: nur Überblenden
      }
      // AM5: Ziel erst messen, wenn es ruhig steht. Zeilen mit `content-visibility: auto` messen im ersten Bild mit der geschätzten Höhe (112 statt 92 px) und rücken im
      // nächsten Bild an ihren Platz; auch Bilder, die Platz bekommen, schieben nach. Darum (Rückflug): gleiches Rechteck in drei Bildern hintereinander, höchstens 8 Bilder. Das große Cover der Serienseite hat das Problem nicht.
      if (f.warte) return; // ein Bild abwarten (mehrere `updated` im selben Bild zählen nicht als zwei Messungen)
      const gemessen = rechteck(el.getBoundingClientRect());
      const gleich = f.letztes && ['left', 'top', 'width', 'height'].every((k) => Math.abs(gemessen[k] - f.letztes[k]) < 0.5);
      f.versuche = (f.versuche ?? 0) + 1;
      f.gleiche = gleich ? (f.gleiche ?? 0) + 1 : 0;
      // Chromium nimmt die Zeilen erst im Bild nach der ersten Messung in die Anzeige und legt sie erst im übernächsten neu aus: zweimal gleich (drei Bilder) zählt als ruhig
      if (f.art === 'zurueck' && f.gleiche < 2 && f.versuche < 8 && typeof requestAnimationFrame === 'function') {
        f.letztes = gemessen;
        f.warte = true;
        requestAnimationFrame(() => { f.warte = false; if (this._flug === f && this.isConnected) this._coverFlug(); });
        return;
      }
      this._flug = null;
      if (reduziert() || !kannAnimieren(el)) return; // kein Flug: die Seite schaltet direkt um
      const nach = gemessen;
      // der Flug läuft mit einem Klon in der obersten Schicht (Befund Tobias 14.11.: in der Liste malten die Nachbarzeilen über das fliegende Cover)
      const dauer = tokenMs(this, '--dauer-feder');
      const an = flipKlon(el, f.rect, nach, { overlay: wurzel.querySelector('.app'), dauer, easing: kurve(this, '--feder'), radiusVon: f.radius, radiusNach: this._radius(el) });
      if (an) nachEnde(an, dauer + 300, () => an.aufraeumen());
      if (an) this._zielFolgen(an, el, nach);
      if (an && f.art === 'hin') this._restBlenden(wurzel.querySelector('main'), el);
    }

    /* Das Ziel kann sich während des Flugs noch bewegen (Zeilen werden gezeichnet, Bilder bekommen Platz): jedes Bild neu messen und das Ende des Flugs nachführen,
     * damit der Klon genau auf dem echten Cover landet (AM5). */
    _zielFolgen(an, el, nach) {
      if (typeof requestAnimationFrame !== 'function' || typeof an.neuesZiel !== 'function') return;
      let aktuell = nach;
      const schritt = () => {
        if (!el.isConnected || an.playState === 'finished' || an.playState === 'idle') return;
        const n = rechteck(el.getBoundingClientRect());
        if (['left', 'top', 'width', 'height'].some((k) => Math.abs(n[k] - aktuell[k]) > 0.5)) { aktuell = n; an.neuesZiel(n, this._radius(el)); }
        requestAnimationFrame(schritt);
      };
      requestAnimationFrame(schritt);
    }

    /* Der Rest der Serienseite blendet über (`--dauer-mittel`); das fliegende Cover bleibt dabei unberührt. */
    _restBlenden(knoten, cover) {
      for (const c of knoten?.children ?? []) {
        if (c === cover) continue;
        if (c.contains(cover)) this._restBlenden(c, cover);
        else animiere(c, [{ opacity: 0.6 }, { opacity: 1 }], { duration: tokenMs(this, '--dauer-mittel'), easing: kurve(this) });
      }
    }

    /* Pille (X33): ein eigenes Element je Segment-Umschalter und für den aktiven Reiter (unten und in der Seitenleiste, nicht in der oberen Leiste).
     * Es gleitet zur neuen Stelle (CSS-Übergang `transform` mit `--feder`, Breite und Höhe mit `--kurve`) und merkt sich die letzte Stelle,
     * auch wenn der Umschalter neu gebaut wird (`_pillenStand`). Ohne Pille (Zeile ohne aktiven Eintrag) bleibt der Knopf selbst gefüllt (`.hp` fehlt). */
    _pillenSetzen() {
      const wurzel = this.renderRoot;
      const nav = wurzel.querySelector('.tr');
      if (nav) {
        const l = this._layout;
        const a = l === 'oben' ? null : nav.querySelector('a[aria-current="page"]');
        this._pille(nav, a && (l === 'seite' ? a : a.querySelector('.ti')), `reiter|${l}`);
      }
      for (const seg of wurzel.querySelectorAll('.seg2')) {
        this._pille(seg, seg.querySelector(':scope > button[aria-pressed="true"]'), `seg|${seg.closest('dialog') ? 'blatt' : 'seite'}|${seg.getAttribute('aria-label') || ''}`);
      }
    }

    _pille(host, ziel, schluessel) {
      let p = host.querySelector(':scope > .pille');
      if (!ziel || !ziel.offsetWidth) { if (p) p.style.display = 'none'; host.classList.remove('hp'); return; }
      let x = 0; let y = 0; let n = ziel;
      while (n && n !== host) { x += n.offsetLeft; y += n.offsetTop; n = n.offsetParent; }
      if (n !== host) return;
      const g = { x, y, w: ziel.offsetWidth, h: ziel.offsetHeight };
      const neu = !p;
      if (!p) { p = host.ownerDocument.createElement('i'); p.className = 'pille'; p.setAttribute('aria-hidden', 'true'); host.insertBefore(p, host.firstChild); }
      p.style.display = '';
      if (host.classList.contains('tr')) { try { p.style.borderRadius = getComputedStyle(ziel).borderRadius; } catch { /* ohne Stil */ } }
      const setze = (q) => { p.style.width = `${q.w}px`; p.style.height = `${q.h}px`; p.style.transform = `translate(${q.x}px, ${q.y}px)`; };
      const alt = this._pillenStand.get(schluessel);
      if (neu) {
        p.style.transition = 'none'; setze(alt ?? g); void p.offsetWidth; p.style.transition = '';
        if (alt) setze(g);
      } else setze(g);
      host.classList.add('hp');
      this._pillenStand.set(schluessel, g);
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
     * `inhalt` darf eine Funktion sein: sie wird bei jedem Zeichnen neu aufgerufen (das Blatt folgt dem Zustand der Seite);
     * `titel` und `knoepfe` dürfen es ebenfalls sein (A11a: das Blatt „Was lädst du hoch?“ wechselt den Inhalt zwischen den Schritten).
     * `kopfKnopf: { label, fn }` ersetzt das „×“ durch einen Textknopf oben rechts (Hochladen, Design 5.6); `fokus: 'titel'` setzt den
     * Fokus beim Öffnen auf die Überschrift statt auf den ersten Knopf.
     * Antwort: Promise mit dem Grund ('x', 'knopf', 'esc', 'hintergrund', 'wischen', 'route', 'ersetzt', 'code').
     * Bewegung (A6m): das Blatt federt herein und gleitet hinaus; `close()` und das Auflösen des Versprechens kommen erst nach dem Ende
     * der Bewegung (`_blattAus` ruft `fertig` erst dann). Am Handy (unter 700 px) tritt die Seite dahinter zurück (iOS-Blatt-Effekt, `.hinten`). */
    oeffneBlatt({ titel, inhalt = nothing, knoepfe = [], rolle = null, kopfKnopf = null, fokus = null } = {}) {
      const nachfolger = !!this._blatt; // Blatt direkt aus einem anderen: der Hintergrund bleibt stehen, nur das neue gleitet herein
      if (this._blatt) this._blattEntfernen(this._blatt, 'ersetzt', false);
      const rueck = this.renderRoot.activeElement || (typeof document !== 'undefined' ? document.activeElement : null);
      return new Promise((aufloesen) => {
        this._blatt = { titel, inhalt, knoepfe, rolle, kopfKnopf, fokus, offen: false, schliesst: false, nachfolger, aufloesen, rueck: this._blattRueck ?? rueck };
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
      /* Das <dialog> bleibt beim Wechsel von Blatt zu Blatt dasselbe Element: Reste der letzten Bewegung wegräumen. */
      try { d.getAnimations?.().forEach((a) => a.cancel()); } catch { /* ohne */ }
      d.style.transform = ''; d.style.removeProperty('--bd');
      d.classList.remove('zu', 'zieht'); delete d.dataset.closing; delete d.dataset.wisch;
      b.offen = true;
      const effekt = this._hintenVorbereiten();
      /* Messung 7 (h4b): das Blatt steht beim `showModal()` schon am Endpunkt; die Bewegung beginnt in derselben Aufgabe direkt danach,
       * der Fokus wird ohne Scrollen gesetzt, und der Dialog schneidet bis zum Ende der Bewegung ab (`overflow: clip`, Klasse `auf`).
       * Sonst scrollt das iPhone zum ×-Knopf, und das Blatt springt. */
      d.classList.add('auf');
      if (typeof d.showModal === 'function') { try { d.showModal(); } catch { d.setAttribute('open', ''); } } else d.setAttribute('open', '');
      this._blattAn(d);
      if (effekt) this._hintenEin();
      this._wischen(d);
      this._meldungenPlatz();
      const erst = (b.fokus === 'titel' ? d.querySelector('h2') : null) || d.querySelector('[autofocus]') || d.querySelector('.knoepfe button, .blatt-b button, .blatt-b input, .blatt-b select, .blatt-b a') || d.querySelector('h2');
      erst?.focus?.({ preventScroll: true });
    }

    get _schmal() { return (window.innerWidth || 0) < REITER_UNTEN_BIS; }

    /* Hereinfedern: am Handy um die eigene Höhe von unten, ab 700 px nur 32 px mit Überblenden; bei „weniger Bewegung“ nur Überblenden. */
    _blattAn(d) {
      const ende = () => d.classList.remove('auf');
      if (!kannAnimieren(d)) { ende(); return; }
      const rot = reduziert();
      const kf = rot ? [{ opacity: 0 }, { opacity: 1 }]
        : this._schmal ? [{ transform: 'translateY(100%)' }, { transform: 'none' }]
          : [{ transform: 'translateY(32px)', opacity: 0 }, { transform: 'none', opacity: 1 }];
      const dauer = tokenMs(this, rot ? '--dauer-kurz' : '--dauer-feder');
      const an = animiere(d, kf, { duration: dauer, easing: kurve(this, rot ? '--kurve' : '--feder') });
      if (!an) { ende(); return; }
      nachEnde(an, dauer + 100, ende);
    }

    /* Hinausgleiten (Tippen: `--dauer-mittel`, `--kurve-aus`; nach dem Wegwischen mit Feder), dann erst `fertig` (= `close()`). */
    _blattAus(d, fertig) {
      d.dataset.closing = '1';
      d.classList.add('zu');
      d.classList.remove('auf');
      this._hintenAus();
      if (!kannAnimieren(d)) { fertig(); return; }
      const rot = reduziert();
      let kf; let name; let kv = '--kurve-aus';
      if (rot) { kf = [{ opacity: 1 }, { opacity: 0 }]; name = '--dauer-kurz'; kv = '--kurve'; } else if (d.dataset.wisch === '1') {
        let dy = 0;
        try { dy = parseFloat(/translateY\((-?[\d.]+)px\)/.exec(d.style.transform)?.[1]) || 0; } catch { /* ohne */ }
        kf = [{ transform: `translateY(${dy}px)` }, { transform: 'translateY(100%)' }]; name = '--dauer-feder'; kv = '--feder';
      } else if (this._schmal) { kf = [{ transform: 'none' }, { transform: 'translateY(100%)' }]; name = '--dauer-mittel'; } else {
        kf = [{ transform: 'none', opacity: 1 }, { transform: 'translateY(32px)', opacity: 0 }]; name = '--dauer-mittel';
      }
      const dauer = tokenMs(this, name);
      const an = animiere(d, kf, { duration: dauer, easing: kurve(this, kv), fill: 'forwards' });
      if (!an) { fertig(); return; }
      nachEnde(an, dauer + 100, fertig);
    }

    /* ---- iOS-Blatt-Effekt (nur am Handy, Messung 7 h4a): `.hinten` (Seite ohne Blatt und Meldungen) wird kleiner, rund und dunkler.
     * Drehpunkt und Ausschnitt gehören zum sichtbaren Teil des Panels (gemessen vor dem Verkleinern). Das Blatt steckt nicht darin. */
    _hintenVorbereiten() {
      if (this._layout !== 'unten' || reduziert() || this.hasAttribute('data-voll')) return false; // Player voll: Seite ist ganz verdeckt, kein Effekt
      const w = this.renderRoot.querySelector('.hinten'); const app = this.renderRoot.querySelector('.app');
      if (!w || !app) return false;
      clearTimeout(this._hintenTimer);
      if (!w.classList.contains('effekt-an')) {
        const rw = w.getBoundingClientRect(); const rp = this.getBoundingClientRect();
        const oben = Math.max(0, rp.top); const unten = Math.min(window.innerHeight || rp.bottom, rp.bottom);
        w.style.setProperty('--oy', `${(oben + unten) / 2 - rw.top}px`);
        w.style.setProperty('--ct', `${Math.max(0, oben - rw.top)}px`);
        w.style.setProperty('--cb', `${Math.max(0, rw.bottom - unten)}px`);
        w.classList.add('effekt-an'); app.classList.add('hinten-an');
      }
      return true;
    }

    _hintenEin() {
      const w = this.renderRoot.querySelector('.hinten');
      if (!w) return;
      void w.offsetWidth; // erst jetzt auf „t = 1“, damit der Übergang von 0 an läuft
      w.classList.add('effekt');
    }

    _hintenAus() {
      const w = this.renderRoot.querySelector('.hinten'); const app = this.renderRoot.querySelector('.app');
      if (!w || !w.classList.contains('effekt-an')) return;
      w.classList.remove('effekt', 'zieht'); w.style.removeProperty('--t');
      clearTimeout(this._hintenTimer);
      this._hintenTimer = setTimeout(() => {
        w.classList.remove('effekt-an'); app?.classList.remove('hinten-an');
        for (const k of ['--oy', '--ct', '--cb']) w.style.removeProperty(k);
      }, tokenMs(this, '--dauer-feder') + 100);
    }

    _blattEntfernen(b, grund, mitFokus) {
      if (this._blatt !== b) return;
      const d = this.renderRoot.querySelector('dialog.blatt');
      this._blattRueck = null;
      if (d) {
        try { if (typeof d.close === 'function') d.close(); else d.removeAttribute('open'); } catch { d.removeAttribute('open'); }
        d.removeAttribute('open');
      }
      this._blatt = null;
      if (grund !== 'ersetzt') this._hintenAus();
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
        this._ziehen(d, dy);
      });
      const ende = () => {
        if (y0 === null) return;
        const war = cap; y0 = null; cap = false;
        if (!war) return;
        try { d.releasePointerCapture(id); } catch { /* ohne */ }
        this._gewischtAm = Date.now();
        if (dy > (d.offsetHeight || 0) * 0.25 || (vel > 0.5 && dy > 30)) { d.dataset.wisch = '1'; this.schliesseBlatt('wischen'); } else this._zurueckFedern(d, dy);
      };
      d.addEventListener('pointerup', ende);
      d.addEventListener('pointercancel', ende);
    }

    /* Beim Ziehen geht der Effekt anteilig zurück (`--t` von 1 bis 0, ohne Übergang) und der Hintergrund wird durchsichtiger. */
    _ziehen(d, dy) {
      const t = Math.max(0, 1 - dy / (d.offsetHeight || 1));
      d.classList.add('zieht'); d.style.setProperty('--bd', String(t));
      const w = this.renderRoot.querySelector('.hinten');
      if (w?.classList.contains('effekt-an')) { w.classList.add('zieht'); w.style.setProperty('--t', String(t)); }
    }

    /* Loslassen unter der Schwelle: das Blatt federt zurück, die Seite dahinter mit. */
    _zurueckFedern(d, dy) {
      d.style.transform = ''; d.style.removeProperty('--bd'); d.classList.remove('zieht');
      const w = this.renderRoot.querySelector('.hinten');
      if (w) { w.classList.remove('zieht'); w.style.removeProperty('--t'); }
      if (!reduziert() && dy > 0) animiere(d, [{ transform: `translateY(${dy}px)` }, { transform: 'none' }], { duration: tokenMs(this, '--dauer-feder'), easing: kurve(this, '--feder') });
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
      return html`<dialog class="blatt" aria-labelledby="blatt-t" role=${b.rolle ?? nothing} ?data-nachfolger=${b.nachfolger}
          @cancel=${(e) => { e.preventDefault(); this.schliesseBlatt('esc'); }} @click=${(e) => this._blattKlick(e)}>
        <div class="blatt-in">
          <div class="griff" aria-hidden="true"></div>
          ${b.kopfKnopf
    ? html`<button type="button" class="btn link blatt-oben" data-blatt-oben @click=${() => this._blattKnopf(b.kopfKnopf)}>${b.kopfKnopf.label}</button>`
    : html`<button type="button" class="rund blatt-x" aria-label=${SEITE.schliessen} @click=${() => this.schliesseBlatt('x')}>${ic('close', 28)}</button>`}
          <h2 id="blatt-t" tabindex="-1">${typeof b.titel === 'function' ? b.titel() : b.titel}</h2>
          <div class="blatt-b">${typeof b.inhalt === 'function' ? b.inhalt() : b.inhalt}</div>
          <div class="knoepfe">${(typeof b.knoepfe === 'function' ? b.knoepfe() : b.knoepfe).map((k) => html`<button type="button" class=${`btn ${k.kind || ''}`} ?disabled=${k.aus === true} @click=${() => this._blattKnopf(k)}>${k.label}</button>`)}</div>
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

    /* Meldung entfernen: sie gleitet hinaus (`--dauer-mittel`, `--kurve-aus`; nach einem Wegwischen in die Richtung des Fingers) und wird dann
     * entfernt. `sofort` ohne Bewegung (eine neue Meldung ersetzt die alte im selben Bild: nichts blinkt). Ohne Web Animations API sofort. */
    _meldungWeg(el, { sofort = false, dx = null } = {}) {
      if (!el.parentNode || el._geht) return;
      const weg = () => { if (el.parentNode) el.parentNode.removeChild(el); };
      if (sofort || !kannAnimieren(el)) { weg(); return; }
      el._geht = true;
      const rot = reduziert();
      const oben = this._tb?.classList.contains('imblatt');
      let kf;
      if (rot) kf = [{ opacity: 1 }, { opacity: 0 }];
      else if (dx !== null) kf = [{ transform: `translateX(${dx}px)`, opacity: 1 }, { transform: `translateX(${dx < 0 ? -1 : 1}${'00%'})`, opacity: 0 }];
      else kf = [{ transform: 'none', opacity: 1 }, { transform: `translateY(${oben ? '-' : ''}24px)`, opacity: 0 }];
      const dauer = tokenMs(this, rot ? '--dauer-kurz' : '--dauer-mittel');
      const an = animiere(el, kf, { duration: dauer, easing: kurve(this, rot ? '--kurve' : '--kurve-aus'), fill: 'forwards' });
      if (!an) { weg(); return; }
      nachEnde(an, dauer + 100, weg);
    }

    /* melde(text, { fehler, aktion: { text, fn } }): Erfolg 4,5 s, mit Aktion 6 s, Fehler bleibt bis „OK“ oder Wegwischen. */
    melde(text, { fehler = false, aktion = null } = {}) {
      const tb = this._tb;
      if (!tb) return null;
      this._meldungenPlatz();
      if (!fehler) tb.querySelectorAll('.toast:not(.err)').forEach((x) => this._meldungWeg(x, { sofort: true }));
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
      // Hereinfedern um 24 px (im Blatt von oben, sonst von unten); bei „weniger Bewegung“ nur einblenden
      const rot = reduziert();
      animiere(el, rot ? [{ opacity: 0 }, { opacity: 1 }] : [{ transform: `translateY(${tb.classList.contains('imblatt') ? '-' : ''}24px)`, opacity: 0 }, { transform: 'none', opacity: 1 }],
        { duration: tokenMs(this, rot ? '--dauer-kurz' : '--dauer-feder'), easing: kurve(this, rot ? '--kurve' : '--feder') });
      // Wegwischen nach links oder rechts (Schwelle 70 px)
      let x0 = null; let dx = 0;
      el.addEventListener('pointerdown', (e) => { if (e.target.closest?.('.tok')) return; x0 = e.clientX; dx = 0; try { el.setPointerCapture(e.pointerId); } catch { /* ohne */ } });
      el.addEventListener('pointermove', (e) => { if (x0 === null) return; dx = e.clientX - x0; el.style.transform = `translateX(${dx}px)`; el.style.opacity = String(Math.max(0.3, 1 - Math.abs(dx) / 300)); });
      const ende = () => {
        if (x0 === null) return; x0 = null;
        if (Math.abs(dx) > 70) { const d0 = dx; el.style.transform = ''; el.style.opacity = ''; this._meldungWeg(el, { dx: d0 }); } else {
          const d0 = dx; el.style.transform = ''; el.style.opacity = '';
          if (!reduziert() && d0) animiere(el, [{ transform: `translateX(${d0}px)` }, { transform: 'none' }], { duration: tokenMs(this, '--dauer-feder'), easing: kurve(this, '--feder') });
        }
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
      const r = this._route;
      if (r.name === 'neu-warten' || (r.name === 'neu-ziel' && r.id === encodeURIComponent(uid))) return;
      this.melde(fuellen(TOBIE.neuer_tobie_meldung, { box: anzeige || undefined }), {
        aktion: { text: TOBIE.zuordnen, fn: () => this.navigiere(`#neu-ziel-${encodeURIComponent(uid)}`) },
      });
    }

    /* Ein neuer Tobie hat eine Vormerkung genommen (5.13): „Box 1: Der neue Tobie spielt jetzt „…“.“ mit „Name geben“ (ohne den Knopf,
     * wenn er schon einen Namen hat). Auf jeder Seite; die Karte „Platz bekommen“ auf „Geräte“ legt der Speicher an. */
    _abgearbeitet(d) {
      const z = d.ziel || {};
      const ziel = z.typ === 'aktion' ? (SUCHE.aktionen[z.aktion] || z.aktion) : z.typ === 'folge' ? (d.folge_anzeige || z.folge) : (d.serie_name || '');
      this.melde(fuellen(TOBIE.aufgelegt_zugeordnet, { box: d.box ? this.store.anzeige(d.box) : undefined, ziel }), d.name ? {} : {
        aktion: { text: TOBIE.name_geben, fn: () => this.navigiere(`#tobie-${encodeURIComponent(d.uid)}?name=1`) },
      });
    }

    /* Seitenwechsel wie in Home Assistant: `history.pushState` (oder `replaceState`) und `location-changed` (B1). */
    navigiere(hash, ersetzen = false) {
      const ziel = String(hash).startsWith('#') ? String(hash) : `#${hash}`;
      try {
        window.history[ersetzen ? 'replaceState' : 'pushState'](window.history.state, '', `${window.location.pathname}${window.location.search}${ziel}`);
      } catch { window.location.hash = ziel; return; }
      window.dispatchEvent(new CustomEvent('location-changed'));
    }

    /* ================================================================== Mini-Player-Platz (X31) */
    get miniPlatz() { return this.renderRoot.querySelector('.mini'); }

    /* Zeigt oder versteckt den Platz; die Höhe geht an die Meldungen (--minih). Die Player-Logik kommt mit A8b. */
    setMini(an, hoehe = 64) {
      const m = this.miniPlatz;
      if (!m) return;
      this._miniAn = !!an;
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

    /* Band über der Zeile „Bibliothek“ (Design 5.2 Punkt 2a): tonal, mindestens 44 px, `role="status"`; Tippen öffnet `#hinzufuegen`.
     * Der Zustand kommt aus `eingang/list` und den Ereignissen (store.s.eingang), nie aus dem Speicher dieser Seite. */
    _eingangBand() {
      if (this.store.s.phase !== 'bereit') return nothing;
      const z = bandZustand(this.store.eingangAblBand(), { lokal: this.store.s.lokaleUploads });
      if (!z) return nothing;
      return html`<div class=${`eband ${z.art}`} role="status" data-eingang-band=${z.art}><a href="#hinzufuegen"><span class="et">${z.text}</span>${ic('chev', 22)}</a></div>`;
    }

    _zurueck(r) {
      if (!r.zurueck) return nothing;
      const ziel = r.zurueck;
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
        herkunft: () => app._herkunft, // { hash, label } der Seite, von der man auf die Serienseite kam, oder null (AM6)
        uploadBand: () => app._eingangBand(), // Band über der Zeile „Bibliothek“ (Design 5.2 Punkt 2a, A11b)
        eingang: () => app.store.eingangAbl(), // Ableitung nach eingang.js: { liste, laeuft, pruefen, fehler, fertig }
        eingangNeuLaden: () => app.store.ladeEingang(), // nach „Das ist richtig“ und nach jedem Upload
        lokaleUploads: (n, namen) => app.store.setLokaleUploads(n, namen), // A11a: Zahl der Uploads dieser Seite (und ihre Namen im Eingang), damit das Band sie einmal mitzählt
        grenzen: () => app.store.s.grenzen || {}, // `hello.grenzen` (upload_max_bytes, upload_parallel, endungen …)
        neuesXhr: () => (app.xhrFactory ? app.xhrFactory() : new XMLHttpRequest()), // Upload mit Fortschritt (A11a); Tests setzen `xhrFactory`
        blattFokus: () => app.updateComplete.then(() => app.renderRoot.querySelector('dialog.blatt #blatt-t')?.focus?.({ preventScroll: true })), // Fokus auf die Überschrift des offenen Blatts
        boxen: () => app.store.s.boxen, // live: Box-Name -> Box-Objekt aus `boxen/list` und den Ereignissen (A7b)
        boxAnzeige: (box) => app.store.anzeige(box), // Anzeigename der Box (A9)
        neue: () => app.store.s.neue, // unbekannte Tobies (`neue_tobies/list` und Ereignisse)
        warteschlange: () => app.store.s.warteschlange, // Vormerkungen (`warteschlange/list` und Ereignisse), leer ohne die Fähigkeit
        warteschlangeNeuLaden: () => app.store.ladeWarteschlange(),
        get nutzerId() { return app.hass?.user?.id; }, // eigene HA-Benutzerkennung (Papierkorb: „von anderen“)
        korbGesehenStand: () => app.store.korbGesehenStand(), // Papierkorb (AC3): bis wann dieses Gerät alles gesehen hat (ms) oder null
        korbGesehen: (eintraege) => app.store.korbGesehen(eintraege), // Papierkorb gezeigt: der Punkt am Technik-Symbol geht
        platz: () => app.store.s.platz, // Tobies, die eine Vormerkung ohne Namen genommen haben (Karte auf „Geräte“)
        platzEntfernen: (uid) => app.store.platzEntfernen(uid),
        ereignis: (fn) => app.store.onEreignis(fn), // `fn(ev)` für jedes Ereignis des Abos; gibt die Abmeldung zurück
        navigiere: (hash, o = {}) => app.navigiere(hash, o.ersetzen === true), // Seitenwechsel im Modell von HA (pushState + `location-changed`)
        gesperrt: () => app.store.s.konfigZustand !== 'ok' || app.store.s.verbindungWeg, // Liste gesperrt oder keine Verbindung: Knöpfe, die ändern, grau (A7b)
        get spieler() { return app.spieler; }, // Player (A8b): `starte`, `schalte`, `spieleId`, `laeuft`, `ist`
        nachZeichnen: () => app.updateComplete,
        meldungenPlatz: (ohneBlatt) => app._meldungenPlatz(ohneBlatt === true),
        folgenAktionen: (x) => html`${app.ctx.faehig('reinhoeren') ? app._spielKnopf(x) : nothing}${folgenAktion(app.ctx, x)}`, // Abspielen und „⋯“ in Folgenzeilen der Suche (A8b, A9)
      };
    }

    /* Abspielknopf in einer Folgenzeile der Suche (48 px, rund, gefüllt): spielt genau diese Folge, bei der laufenden „Pause“. */
    _spielKnopf(x) {
      const titel = x.anzeige || x.folge;
      const spielt = this.spieler.laeuft(x.serie_id, x.folge);
      return html`<button type="button" class="iconbtn fillp se-play" data-abspielen aria-label=${fuellen(spielt ? PLAYER.folge.pausieren : PLAYER.folge.abspielen, { titel })}
        @click=${() => this.spieler.spieleId(x.serie_id, x.folge)}>${symbol(spielt ? 'pause' : 'play', 24)}</button>`;
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
      const warSeite = this._seiteKey !== null;
      // Wechsel auf eine Seite, die erst laden muss (Serienseite): die alte bleibt stehen, bis die neue Daten hat (höchstens 700 ms), statt kurz Platzhalter zu zeigen
      this._vorSeite = alt && warSeite && key && r.name !== this._seiteRoute?.name ? { obj: alt, route: this._seiteRoute, bis: Date.now() + 700 } : null;
      this._seiteRoute = key ? r : null;
      this._seiteKey = key;
      this._seiteObj = key ? this._seiteFuer(r.name) : null;
      alt?.verlassen?.();
      this._seiteObj?.betreten?.(r);
      if (warSeite && key && !(this._flug?.art === 'hin' && this._flug.id === r.id)) this._seiteBlenden();
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
      const vor = this._vorSeite;
      if (seite && vor && Date.now() < vor.bis && typeof seite.laedt === 'function' && seite.laedt(r)) return vor.obj.render(vor.route);
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
    /* Titel im Seitenkopf (Design 3.1, AB4): auf dem Start die Begrüßung, sonst der Name der Seite; nie zusätzlich „Tobi Box“. */
    _kopfTitel(r) {
      if (r.name === 'start') return begruessung();
      return this._titel(r);
    }

    /* Punkt am Technik-Symbol (AC3): nur Administratoren, nur bei neuen Papierkorb-Einträgen anderer Benutzer */
    _korbPunkt() { return this._admin && this.store.s.phase === 'bereit' && this.store.s.korbNeu.length > 0; }

    _kopfSymbole(r) {
      const seite = this.store.s.phase === 'bereit' ? this._seiteFuer(r.name) : null;
      const aktion = typeof seite?.kopfAktionen === 'function' ? seite.kopfAktionen(r)
        : (r.name === 'start' ? kopfAktion({ href: '#suche', label: SEITE.suchen, symbol: 'search' }) : nothing);
      // Technik: am Computer steht sie in der Seitenleiste, sonst als rundes Symbol im Kopf
      const technik = this._admin && this._layout !== 'seite'
        ? html`<a class="rund tech" href="#technik" aria-label=${this._korbPunkt() ? `${SEITE.technik}, ${TECHNIK.korb.punkt}` : SEITE.technik} aria-current=${r.tab === 'technik' ? 'page' : nothing}>${ic('tool')}${this._korbPunkt() ? html`<span class="dot ruhig" data-punkt="papierkorb" aria-hidden="true"></span>` : nothing}</a>` : nothing;
      return html`${aktion}${technik}`;
    }

    _kopf(r) {
      const still = STILLE_KOEPFE.includes(r.name); // diese Seiten zeigen ihren Titel selbst im Inhalt
      return html`<header class=${`kopf${still ? ' still' : ''}`}>
        ${this.narrow ? html`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>` : nothing}
        <h1 class=${still ? 'sr' : ''}>${this._kopfTitel(r)}</h1>
        <span class="symbole">${this._kopfSymbole(r)}</span></header>`;
    }

    _nav(r) {
      const n = this.store.s.neue.length;
      const punkt = n ? html`<span class="dot" aria-hidden="true">${n}</span><span class="sr">${n === 1 ? TOBIE.neue_tobies_punkt : fuellen(TOBIE.neue_tobies_punkt_mehr, { anzahl: n })}</span>` : nothing;
      // Bibliothek: ruhiger Punkt ohne Zahl, solange etwas hinzugefügt wird (Design 5.2 Punkt 2a, N15)
      const laeuft = this.store.s.phase === 'bereit' && (this.store.eingangAblBand().laeuft.length + this.store.s.lokaleUploads) > 0;
      const punktLib = laeuft ? html`<span class="dot ruhig" data-punkt="eingang" aria-hidden="true"></span><span class="sr">${EINGANG.punkt}</span>` : nothing;
      return html`<nav class=${`tabs ${this._layout}`} aria-label=${SEITE.bereiche}><div class="tr">
        ${REITER.map((id) => html`<a href=${`#${id}`} aria-current=${r.tab === id ? 'page' : nothing}><span class="ti">${ic({ start: 'home', bibliothek: 'lib', tobies: 'tag', geraete: 'spk' }[id], 26)}</span><span class="tn">${SEITE.reiter[id]}</span>${id === 'geraete' ? punkt : id === 'bibliothek' ? punktLib : nothing}</a>`)}
      </div></nav>`;
    }

    _seitenleiste(r) {
      const aktiv = r.tab === 'technik' ? 'page' : nothing;
      return html`<aside class="seite">
        ${this.narrow ? html`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>` : nothing}
        <div class="marke"><span class="logo" aria-hidden="true">${ic('spk', 22)}</span>${SEITE.titel}</div>
        ${this._nav(r)}
        <div class="werkzeuge">
          <a class="srow" href="#hinzufuegen">${ic('plus', 24)}<span>${SEITE.hinzufuegen}</span></a>
          ${this._admin ? html`<a class="srow tech" href="#technik" aria-current=${aktiv}>${ic('tool', 24)}<span>${SEITE.technik}</span>${this._korbPunkt() ? html`<span class="dot ruhig" data-punkt="papierkorb" aria-hidden="true"></span><span class="sr">${TECHNIK.korb.punkt}</span>` : nothing}</a>` : nothing}</div>
      </aside>`;
    }

    /* Der Platz liegt außerhalb des Scrollbereichs (unten, oben) bündig auf der Leiste; in der Seitenleisten-Ansicht
     * unten in der Inhaltsspalte. Der Zustand (hidden) überlebt einen Wechsel des Ortes (siehe updated). */
    _miniHtml() { return html`<div class="mini" ?hidden=${!this._miniAn} part="mini">${this.spieler.miniHtml()}<slot name="mini"></slot></div>`; }

    render() {
      const r = this._route;
      const l = this._layout;
      return html`<div class="app" data-layout=${l} ?data-kbd=${this._kbd}>
        <div class="hinten">
        <div class="rahmen">
          ${l === 'seite' ? this._seitenleiste(r) : nothing}
          <div class="spalte">
            ${this._kopf(r)}
            ${l === 'oben' ? this._nav(r) : nothing}
            ${this._baender()}
            <main id="main" tabindex="-1" aria-label=${this._titel(r)}>${this._seite(r)}</main>
            ${l === 'seite' ? this._miniHtml() : nothing}
          </div>
        </div>
        ${l === 'seite' ? nothing : this._miniHtml()}
        ${l === 'unten' ? this._nav(r) : nothing}
        </div>
        ${this.spieler.vollHtml()}
        ${this._blattHtml()}
        <div class="toastbox"></div>
        <div id="live" class="sr" role="status" aria-live="polite"></div>
      </div>`;
    }

    static styles = [css`
      :host {
        display: block; height: 100%; overflow: hidden;
        /* HA gibt dem Panel keine Höhe weiter (ha-panel-custom: Light-DOM, height auto), "100%" greift dann nicht: Fenstergröße minus HA-Rand. */
        height: calc(100vh - var(--rand-v, 0px)); height: calc(100dvh - var(--rand-v, 0px));
        --rand-v: 0px; --sab: var(--tb-safe-unten, env(safe-area-inset-bottom, 0px));
        --bg: #fafafa; --card: #ffffff; --text: #212121; --text2: #5f6368; --divider: #dcdfe3;
        --primary: #01689f; --on-primary: #ffffff; --primary-soft: #e1f2fb; --primary-ink: #01689f;
        --ok: #1b5e20; --ok-bg: #e6f4e7; --warn: #8a4b00; --warn-bg: #fff1d6; --danger: #b71c1c; --danger-bg: #fdeaea;
        --focus: #e65100; --line: #7c8187; --shadow: rgba(0, 0, 0, 0.12); --scrim: rgba(0, 0, 0, 0.5);
        --r-card: 16px; --r-big: 24px;
        --c1: #ad1457; --c2: #00695c; --c3: #5e35b1; --c4: #8d4a00; --c5: #1565c0; --c6: #2e7d32; --on-cover: #ffffff; --shine: rgba(255, 255, 255, 0.2);
        --dauer-kurz: 150ms; --dauer-mittel: 250ms; --dauer-lang: 350ms; --dauer-feder: 500ms;
        --kurve: cubic-bezier(.2, 0, 0, 1); --kurve-aus: cubic-bezier(.4, 0, 1, 1);
        --feder: var(--kurve); --feder-weich: var(--kurve); /* Rückfall ohne linear() */
        --druck: 0.97; --druck-zeile: 0.98; --hinten-skala: 0.94; --hinten-radius: 14px; --hinten-dunkel: 0.8; --hinten-grund: #000;
        --minih: 0px;
      }
      /* Feder (Design 4): Response ca. 0,45 s, Dämpfung ca. 0,8 (schwingt etwa 1,5 Prozent über das Ziel, nach 500 ms ruhig); weich: Response 0,5 s, Dämpfung 0,9 */
      @supports (transition-timing-function: linear(0, 1)) {
        :host { --feder: linear(0, 0.031, 0.108, 0.21, 0.322, 0.435, 0.541, 0.637, 0.72, 0.791, 0.849, 0.896, 0.932, 0.96, 0.98, 0.995, 1.004, 1.01, 1.014, 1.015, 1.015, 1.014, 1.013, 1.011, 1.009, 1.008, 1);
          --feder-weich: linear(0, 0.024, 0.082, 0.161, 0.25, 0.341, 0.431, 0.514, 0.591, 0.659, 0.719, 0.771, 0.815, 0.852, 0.883, 0.909, 0.93, 0.946, 0.96, 0.97, 0.979, 0.985, 0.99, 0.994, 0.996, 0.998, 0.999, 1); }
      }
      /* Reduzierte Bewegung: nur Überblenden. Alle Federn werden zur Kurve, alle Dauern kurz, kein Skalieren, kein Abdunkeln, keine Übergänge von transform. */
      @media (prefers-reduced-motion: reduce) {
        :host { --dauer-mittel: var(--dauer-kurz); --dauer-lang: var(--dauer-kurz); --dauer-feder: var(--dauer-kurz); --feder: var(--kurve); --feder-weich: var(--kurve);
          --druck: 1; --druck-zeile: 1; --hinten-skala: 1; --hinten-radius: 0px; --hinten-dunkel: 1; }
        *, *::before, *::after { transition-property: opacity, background-color, color, border-color, box-shadow !important; }
      }
      * { box-sizing: border-box; }
      /* overflow: clip statt nur hidden: „hidden“ lässt sich per Programm scrollen (scrollIntoView, Fokus); dann rutscht die
         Reiterleiste nach oben (Befund im echten HA, „Name geben“ am Handy). „hidden“ bleibt als Rückfall für alte Browser. */
      .app { position: relative; height: 100%; overflow: hidden; overflow: clip; background: var(--bg); color: var(--text); display: flex; flex-direction: column;
        font-family: Roboto, system-ui, sans-serif; font-size: 16px; line-height: 1.45; --navh: calc(64px + var(--sab)); }
      .app:not([data-layout="unten"]) { --navh: 0px; }
      button, select, input { font: inherit; color: inherit; }
      button { cursor: pointer; }
      a { color: var(--primary-ink); }
      :focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; border-radius: 6px; }
      .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
      /* .hinten = alles hinter dem Blatt (Seite, Mini-Player, Reiterleiste), ohne Blatt und Meldungen. Nur sie wird beim Blatt kleiner (iOS-Effekt, Messung 7). */
      .hinten { flex: 1 1 0; min-height: 0; min-width: 0; display: flex; flex-direction: column; background: var(--bg); }
      .app.hinten-an { background: var(--hinten-grund); }
      .hinten.effekt-an { transform-origin: 50% var(--oy, 50%); transform: scale(calc(1 - (1 - var(--hinten-skala)) * var(--t, 0)));
        clip-path: inset(var(--ct, 0px) 0 var(--cb, 0px) 0 round calc(var(--hinten-radius) * var(--t, 0)));
        filter: brightness(calc(1 - (1 - var(--hinten-dunkel)) * var(--t, 0)));
        transition: transform var(--dauer-feder) var(--feder), clip-path var(--dauer-feder) var(--feder), filter var(--dauer-feder) var(--feder-weich); }
      .hinten.effekt { --t: 1; }
      .hinten.effekt-an.zieht { transition: none; }
      .rahmen { flex: 1 1 0; min-height: 0; overflow-y: auto; overscroll-behavior: contain; }
      .spalte { min-height: 100%; display: flex; flex-direction: column; min-width: 0; }
      main { flex: 1 0 auto; min-width: 0; padding: 4px max(16px, env(safe-area-inset-right, 0px)) 24px max(16px, env(safe-area-inset-left, 0px)); outline: none; }
      main:focus, main:focus-visible { outline: none; }
      h2 { font-size: 20px; font-weight: 500; margin: 16px 0 12px; }
      main > h2:first-child, main > .back + h2 { margin-top: 8px; }

      /* Kopf */
      .kopf { display: flex; align-items: center; gap: 8px; min-height: 56px; padding: 4px max(16px, env(safe-area-inset-right, 0px)) 4px max(16px, env(safe-area-inset-left, 0px)); }
      .kopf h1 { font-size: 24px; margin: 0; font-weight: 500; flex: 1; min-width: 0; overflow-wrap: anywhere; line-height: 1.2; }
      .symbole { display: flex; gap: 8px; flex: none; margin-left: auto; }
      .rund { width: 48px; height: 48px; border-radius: 24px; border: 0; background: var(--primary-soft); color: var(--primary-ink); display: inline-grid; place-items: center; text-decoration: none; flex: none; }
      .rund { position: relative; }
      .rund svg { fill: currentColor; }
      .rund .dot.ruhig, .srow .dot.ruhig { display: inline-block; width: 12px; height: 12px; border-radius: 6px; background: var(--primary-ink); border: 2px solid var(--card); box-sizing: content-box; }
      .rund .dot.ruhig { position: absolute; top: 6px; right: 6px; }
      .srow .dot.ruhig { margin-left: auto; }
      .rund[aria-current="page"] { outline: 2px solid var(--primary-ink); outline-offset: -2px; }
      ha-menu-button { flex: none; color: var(--text); }

      /* Reiter */
      nav.tabs { z-index: 20; background: var(--card); }
      nav.tabs .tr { display: flex; position: relative; }
      /* Pille (X33): ein Element, das zur neuen Stelle gleitet (aktiver Reiter unten und in der Seitenleiste, Segment-Umschalter) */
      .pille { position: absolute; left: 0; top: 0; z-index: 0; pointer-events: none; will-change: transform; transition: transform var(--dauer-feder) var(--feder), width var(--dauer-mittel) var(--kurve), height var(--dauer-mittel) var(--kurve); }
      nav.tabs .tr > .pille { background: var(--primary-soft); }
      nav.tabs .tr.hp a[aria-current="page"], nav.tabs .tr.hp a[aria-current="page"] .ti, aside.seite nav.tabs .tr.hp a[aria-current="page"] { background: none; }
      nav.tabs.oben .pille { display: none; }
      nav.tabs a { flex: 1 1 0; min-width: 0; min-height: 64px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
        text-decoration: none; color: var(--text2); font-size: 14px; font-weight: 500; position: relative; padding: 4px 2px; border-radius: 8px; text-align: center; overflow-wrap: anywhere; }
      nav.tabs a svg { fill: currentColor; display: block; }
      nav.tabs a[aria-current="page"] { color: var(--primary-ink); }
      nav.tabs .ti { display: grid; place-items: center; width: 56px; height: 32px; border-radius: 16px; }
      nav.tabs a[aria-current="page"] .ti { background: var(--primary-soft); }
      nav.tabs .dot.ruhig { display: inline-block; min-width: 0; width: 12px; height: 12px; padding: 0; top: 8px; left: calc(50% + 14px); background: var(--primary-ink); border: 2px solid var(--card); box-sizing: content-box; }
      nav.tabs .dot { position: absolute; top: 4px; left: calc(50% + 6px); min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; background: var(--danger); color: var(--card); font-size: 12px; line-height: 18px; text-align: center; font-weight: 700; }
      nav.tabs.unten { flex: none; box-shadow: 0 -2px 12px var(--shadow); padding: 0 max(8px, env(safe-area-inset-left, 0px)) var(--sab) max(8px, env(safe-area-inset-right, 0px)); }
      @supports ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) and (background: color-mix(in srgb, red 50%, blue)) {
        nav.tabs.unten, nav.tabs.oben { background: color-mix(in srgb, var(--card) 94%, transparent); -webkit-backdrop-filter: blur(12px) saturate(1.3); backdrop-filter: blur(12px) saturate(1.3); }
      }
      nav.tabs.oben { position: sticky; top: 0; padding: 0 max(16px, env(safe-area-inset-left, 0px)); box-shadow: 0 2px 8px var(--shadow); }
      nav.tabs.oben .tr { max-width: 720px; gap: 4px; margin: 0 auto; }
      .app[data-layout="oben"] .kopf, .app[data-layout="oben"] main { width: 100%; max-width: 1000px; margin-inline: auto; }
      nav.tabs.oben a { flex-direction: row; justify-content: center; gap: 8px; min-height: 52px; font-size: 16px; }
      nav.tabs.oben .ti { width: 32px; background: none !important; }
      nav.tabs.oben .dot { position: static; }
      nav.tabs.oben .dot.ruhig { margin-left: -4px; }
      .app[data-kbd] nav.tabs.unten, .app[data-kbd] .mini { display: none; }

      /* Computer (ab 1100 px Panelbreite): Seitenleiste mit eigenem Kopf, Inhalt mit Höchstbreite, großer Seitenkopf (AB3) */
      .app[data-layout="seite"] { --inhalt-max: 1320px; --rand-x: 40px; }
      .app[data-layout="seite"] .rahmen { display: grid; grid-template-columns: 216px minmax(0, 1fr); overflow: hidden; }
      aside.seite { height: 100%; overflow-y: auto; display: flex; flex-direction: column; background: var(--card); border-right: 1px solid var(--divider); padding: 28px 10px 16px; z-index: 20; }
      aside.seite .marke { display: flex; align-items: center; gap: 10px; font-size: 20px; font-weight: 700; letter-spacing: -0.2px; line-height: 1.2; padding: 0 12px 28px; }
      aside.seite .logo { width: 36px; height: 36px; border-radius: 10px; background: var(--primary); color: var(--on-primary); display: grid; place-items: center; flex: none; }
      aside.seite .logo svg { fill: currentColor; }
      aside.seite nav.tabs { background: transparent; }
      aside.seite nav.tabs .tr { flex-direction: column; gap: 2px; }
      aside.seite nav.tabs a { flex: none; flex-direction: row; justify-content: flex-start; gap: 14px; font-size: 16px; padding: 0 12px; min-height: 48px; border-radius: 12px; }
      aside.seite nav.tabs a[aria-current="page"] { background: var(--primary-soft); }
      aside.seite nav.tabs .ti { width: 28px; height: 28px; background: none !important; }
      aside.seite nav.tabs .dot { position: static; margin-left: auto; }
      aside.seite nav.tabs .dot.ruhig { margin-right: 6px; }
      aside.seite .werkzeuge { margin-top: auto; padding-top: 12px; border-top: 1px solid var(--divider); display: grid; gap: 2px; }
      .srow { display: flex; align-items: center; gap: 14px; min-height: 48px; padding: 0 12px; border-radius: 12px; color: var(--text2); text-decoration: none; font-weight: 500; font-size: 16px; }
      .srow svg { fill: currentColor; flex: none; }
      .srow[aria-current="page"] { background: var(--primary-soft); color: var(--primary-ink); }
      @media (hover: hover) {
        aside.seite nav.tabs a:not([aria-current="page"]):hover, .srow:not([aria-current="page"]):hover { background: var(--primary-soft); color: var(--primary-ink); }
      }
      .app[data-layout="seite"] .spalte { height: 100%; overflow-y: auto; min-height: 0; }
      .app[data-layout="seite"] .kopf, .app[data-layout="seite"] main { width: 100%; max-width: var(--inhalt-max); margin-inline: auto; }
      .app[data-layout="seite"] .kopf { min-height: 0; padding: 44px var(--rand-x) 20px; gap: 16px; }
      .app[data-layout="seite"] .kopf h1 { font-size: 36px; font-weight: 700; letter-spacing: -0.6px; line-height: 1.15; }
      .app[data-layout="seite"] .kopf.still, .app[data-layout="seite"] .kopf[data-still] { padding: 0; }
      .kopf[data-still] h1 { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
      .app[data-layout="seite"] main > .back:first-child { margin-top: 36px; }
      .app[data-layout="seite"] main > .back + h2 { font-size: 36px; letter-spacing: -0.6px; margin: 4px 0 20px; }
      .app[data-layout="seite"] .symbole { gap: 12px; align-items: center; }
      .app[data-layout="seite"] main { padding: 8px var(--rand-x) 64px; container-type: inline-size; }
      .app[data-layout="seite"] main h2 { font-size: 22px; font-weight: 700; letter-spacing: -0.2px; margin: 32px 0 14px; }
      .app[data-layout="seite"] main > h2:first-child, .app[data-layout="seite"] main > .back + h2 { margin-top: 8px; }
      .app[data-layout="seite"] .note.band { width: calc(100% - 2 * var(--rand-x)); max-width: calc(var(--inhalt-max) - 2 * var(--rand-x)); margin: 12px auto 0; }
      /* Dieselbe Überschrift steht schon im Seitenkopf: für Screenreader bleiben, nicht doppelt zeigen */
      main h2[data-doppelt] { position: absolute; width: 1px; height: 1px; margin: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

      /* Platz für den Mini-Player: bündig auf der Leiste */
      .mini { flex: none; position: relative; z-index: 19; background: var(--card); border-top: 1px solid var(--divider); box-shadow: 0 -2px 8px var(--shadow); }
      .app[data-layout="seite"] .spalte .mini { position: sticky; bottom: 0; }
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
      /* Band „Hinzufügen läuft“ über der Bibliothek (Design 5.2 Punkt 2a): tonal, mindestens 44 px, orange bei „bitte kurz ansehen“, rot bei „geht nicht“ */
      .eband { margin: 8px 0 4px; }
      .eband a { display: flex; align-items: center; gap: 8px; min-height: 44px; padding: 6px 8px 6px 16px; border-radius: var(--r-card); background: var(--primary-soft); color: var(--primary-ink);
        border: 1px solid var(--line); text-decoration: none; font-weight: 500; font-size: 15px; line-height: 1.3; }
      .eband .et { flex: 1; min-width: 0; overflow-wrap: anywhere; }
      .eband a svg { fill: currentColor; flex: none; }
      .eband.pruefen a { background: var(--warn-bg); color: var(--warn); border: 2px solid var(--warn); padding: 5px 7px 5px 15px; }
      .eband.fehler a { background: var(--danger-bg); color: var(--danger); border: 2px solid var(--danger); padding: 5px 7px 5px 15px; }

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
      dialog.blatt::backdrop { background: var(--scrim, rgba(0, 0, 0, 0.5)); opacity: var(--bd, 1); }
      dialog.blatt[open]::backdrop { animation: bd-ein var(--dauer-mittel) var(--kurve); }
      dialog.blatt[data-nachfolger]::backdrop { animation: none; }
      dialog.blatt.zu::backdrop { opacity: 0; transition: opacity var(--dauer-mittel) var(--kurve-aus); }
      dialog.blatt.zieht::backdrop { transition: none; }
      @keyframes bd-ein { from { opacity: 0; } }
      dialog.blatt.auf { overflow: clip; } /* bis zum Ende des Hereinfederns kann der Dialog nicht scrollen (Messung 7 h4b) */
      .blatt-in { position: relative; padding: 20px max(16px, env(safe-area-inset-right, 0px)) max(20px, env(safe-area-inset-bottom, 0px)) max(16px, env(safe-area-inset-left, 0px)); }
      .blatt h2 { margin: 0 0 8px; padding-right: 56px; touch-action: none; outline: none; }
      .griff { height: 20px; margin: -12px 0 0; touch-action: none; display: grid; place-items: center; }
      .griff::before { content: ""; width: 44px; height: 5px; border-radius: 3px; background: var(--line); }
      .blatt-x { float: right; position: sticky; top: 0; z-index: 3; margin: -8px -8px 0 8px; background: var(--card); border: 0; }
      .blatt-oben { float: right; position: sticky; top: 0; z-index: 3; margin: -12px -8px 0 8px; min-width: 64px; background: var(--card); color: var(--primary-ink); font-weight: 500; }
      .knoepfe:not(:empty) { position: sticky; bottom: 0; z-index: 2; background: var(--card); margin-top: 16px; padding: 8px 0; display: flex; flex-wrap: wrap; gap: 12px; justify-content: flex-end; }
      /* Am Handy füllt eine Fläche in Kartenfarbe unter dem Blatt den Spalt, wenn die Feder leicht über das Ziel schwingt */
      @media (max-width: 699px) { dialog.blatt { margin: auto 0 0; max-width: none; border-radius: var(--r-big) var(--r-big) 0 0; box-shadow: 0 8px 32px var(--shadow), 0 80px 0 0 var(--card); } }

      /* Meldungen */
      .toastbox { position: absolute; left: 50%; transform: translateX(-50%); bottom: calc(var(--navh) + var(--minih) + 16px); z-index: 2000; display: grid; gap: 8px; width: min(92%, 520px); pointer-events: none; }
      .toastbox > * { pointer-events: auto; }
      .toastbox.imblatt { position: fixed; bottom: auto; top: max(12px, env(safe-area-inset-top, 0px)); }
      .toast { display: flex; align-items: center; gap: 12px; background: var(--text); color: var(--bg); padding: 12px 16px; border-radius: var(--r-card); touch-action: pan-y; }
      .toast .tmsg { flex: 1; min-width: 0; overflow-wrap: anywhere; }
      .toast.err { background: var(--danger-bg); color: var(--danger); border: 2px solid var(--danger); }
      .toast .tok { min-width: 56px; min-height: 44px; border-radius: 22px; border: 1px solid currentColor; background: none; color: inherit; font-weight: 700; padding: 0 16px; flex: none; }
      @media (prefers-reduced-motion: reduce) { .skel { animation: none; } }

      /* Druck-Rückmeldung (X34): beim Drücken leicht kleiner, beim Loslassen federt es zurück; Zeilen weniger. Nicht an ausgegrauten Knöpfen. */
      :is(.btn, .iconbtn, .rund, .tile, .qt, .rcard, .back, .hz-kachel, .ttile, .tb-opt, .tb-weg, .rowbtn, .lrow, .slink, .tb-wzeile, .se-wrow, .tzeile, a.gstatus, a.glink) { transition: transform var(--dauer-feder) var(--feder); }
      :is(.btn, .iconbtn, .rund, .tile, .qt, .rcard, .back, .hz-kachel, .ttile, .tb-opt, .tb-weg):active:not(:disabled):not([aria-disabled="true"]) { transform: scale(var(--druck)); transition-duration: var(--dauer-kurz); transition-timing-function: var(--kurve); }
      :is(.rowbtn, .lrow, .slink, .tb-wzeile, .se-wrow, .tzeile, a.gstatus, a.glink):active:not(:disabled):not([aria-disabled="true"]) { transform: scale(var(--druck-zeile)); transition-duration: var(--dauer-kurz); transition-timing-function: var(--kurve); }
      .seg2 { position: relative; }
      .seg2 > .pille { background: var(--primary); border-radius: 24px; box-shadow: inset 0 0 0 2px var(--primary-ink), 0 1px 3px var(--shadow); }
      .seg2 button { position: relative; z-index: 1; }
      .seg2.hp > button[aria-pressed="true"] { background: transparent; box-shadow: none; }
    `, bausteinStil(), spielerStil(), ...Object.values(SEITEN).map((x) => x.stil?.()).filter(Boolean)];
  }

  if (!customElements.get('tobibox-app')) customElements.define('tobibox-app', TobiboxApp);
}

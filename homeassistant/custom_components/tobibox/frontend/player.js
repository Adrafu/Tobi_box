/* Player der Seite (Pakete A8b, A8e, A7c, A8m; Design docs/designs/ha-oberflaeche.md, Abschnitt 5.12 und 4 „Bewegung“).
 *
 * Was hier steht:
 *   - reine Funktionen (ohne DOM, getestet in player.test.mjs): Folgen, Ordner-Folgen über Tracks, Zeitleiste, Beschriftung des Knopfs
 *     „Reinhören / Hier weiterhören / Noch einmal hören“ je Hörstelle;
 *   - `Spieler`: das `<audio>`-Element, `audio/bereit` vor jedem Start, Link erneuern, nächste Folge im Voraus signieren, Hörstelle sammeln
 *     (`hoerstelle/set`), Media-Session, Sperre (A8e), Tempo, Wischen auf und zu;
 *   - die Darstellung: Leiste (Mini-Player) und Vollansicht (`<dialog class="player">`) als Lit-Templates, dazu die Bewegung (A8m):
 *     Cover-Flug nur über FLIP mit `element.animate` (Messung 7, nie `startViewTransition`), Mini-Player federt herein, Kreuzblende des Covers.
 *
 * Die App (tobibox-app.js) legt EIN `Spieler`-Objekt an, ruft `miniHtml()` und `vollHtml()` beim Zeichnen und `nachRender()` danach. Die Seiten
 * erreichen ihn über `ctx.spieler` (`starte({ serie, folge })`, `toggle()`, `laeuft(serieId, folgeName)`).
 *
 * Verträge: Vertrag W Befehle 39 bis 42 (`audio/bereit` mit `folge`, `hoerstelle/get|set|liste`), 14.5 (signierter Pfad, `track` nur bei
 * Ordner-Folgen), 14.6 (Hörstelle: höchstens alle 10 s, sofort bei Pause, Sprung, Wechsel, Ende, Schließen). Der Zustand kommt nie aus dem
 * Fehler des `<audio>`-Elements (der meldet 401, 429, 503 und 404 gleich), sondern aus `audio/bereit`.
 */
import { html, nothing, css, ic, ic30, cover, uhr, coverGrossUrl, abspiel } from './bausteine.js';
import { PLAYER, FEHLER, HOERPROBE, ZEILE, KAPITEL, fuellen } from './texte.js';
import { reduziert, kannAnimieren, tokenMs, kurve, animiere, nachEnde, flipKlon, rechteck } from './bewegung.js';

export const TEMPOS = [1, 1.25, 1.5];
export const SPRUNG_S = 30; // ±30 Sekunden
export const SCHWELLE_AUF = 40; // Wischen nach oben in der Leiste (Design 5.12, X6)
export const SCHWELLE_ZU = 70; // Wischen nach unten in der Vollansicht
export const ENTSPERREN_MS = 2000; // Entsperren durch Halten (X14)
export const SPEICHER_MS = 10000; // Hörstelle: höchstens alle 10 s während der Wiedergabe (14.6)
export const LINK_ERNEUERN_MS = 20 * 3600 * 1000; // der Link gilt 24 Stunden; nach 20 Stunden holt die Seite einen neuen (14.5)
export const VORBEREITET_NEU_MS = 15000; // `wird_vorbereitet`: nach 15 s fragt die Seite erneut (5.12)
export const VORAB_S = 45; // so viele Sekunden vor dem Ende wird die nächste Datei signiert (Messung 2: Lücke 822 ms)
export const NEU_VERSUCHE = 2; // so oft fragt die Seite nach einem Fehler des `<audio>`-Elements neu, bevor sie aufgibt
const TEMPO_KEY = 'tobibox.tempo';

/* ------------------------------------------------------------------ reine Funktionen */

export const zahl = (x) => typeof x === 'number' && Number.isFinite(x);
export const folgeName = (f) => f?.anzeige || f?.name || '';

/* Anzahl Tracks: nur Ordner-Folgen haben mehr als einen (Vertrag 14.5, `track` ist 0-basiert). */
export function trackAnzahl(f) {
  const n = f?.art === 'ordner' ? Number(f.tracks) : 1;
  return Number.isInteger(n) && n > 1 ? n : 1;
}

/* Track-Längen einer Ordner-Folge (`spuren_s`), nur wenn sie vollständig und brauchbar sind; sonst null. */
export function spurenVon(f) {
  const s = f?.spuren_s;
  const n = trackAnzahl(f);
  return n > 1 && Array.isArray(s) && s.length === n && s.every((x) => zahl(x) && x > 0) ? s : null;
}

/* Länge der ganzen Folge: Summe der Tracks, sonst `dauer_s`; null, solange unbekannt. */
export function gesamtVon(f) {
  const sp = spurenVon(f);
  if (sp) return sp.reduce((a, b) => a + b, 0);
  return zahl(f?.dauer_s) && f.dauer_s > 0 ? f.dauer_s : null;
}

/* Stelle in der ganzen Folge aus Track und Sekunden im Track (ohne bekannte Spuren: Sekunden im Track). */
export function globalPos(f, track, t) {
  const sp = spurenVon(f);
  return sp ? sp.slice(0, track).reduce((a, b) => a + b, 0) + t : t;
}

/* Umkehrung: Stelle in der ganzen Folge → { track, offset }. Ohne bekannte Spuren gibt es nur Track 0. */
export function ortVon(f, pos) {
  const sp = spurenVon(f);
  const p = Math.max(0, pos);
  if (!sp) return { track: 0, offset: p };
  let rest = p;
  for (let i = 0; i < sp.length; i += 1) {
    if (rest < sp[i] || i === sp.length - 1) return { track: i, offset: Math.min(rest, sp[i]) };
    rest -= sp[i];
  }
  return { track: 0, offset: p };
}

/* ------------------------------------------------------------------ Kapitel (A8d, Design 5.3, 5.12, 11.4.8) */

/* Beginnt der Titel selbst mit „Kapitel“ („Kapitel 2.2“, „Kapitel 1 & Kapitel 2.1“), setzt die Seite kein zweites „Kapitel n:“ davor (AM22). */
export const beginntMitKapitel = (titel) => /^\s*kapitel(?![\p{L}])/iu.test(String(titel ?? ''));

/* Titel eines Kapitels: nur aus Zahlen („1“) wird „Kapitel 1“, ohne Titel „Kapitel {nr}“. */
export function kapitelTitel(roh, nr) {
  const t = String(roh ?? '').trim();
  if (!t) return fuellen(KAPITEL.nummer, { nr });
  return /^\d+$/.test(t) ? fuellen(KAPITEL.nummer, { nr: Number(t) }) : t;
}

/* Kapitelliste einer Folge (Folge-Objekt von `serie/get`): [{ nr, titel, start_s, track, laenge_s }]. Weniger als zwei, oder Unbrauchbares: leer (keine Liste). */
export function kapitelVon(f) {
  const roh = Array.isArray(f?.kapitel) ? f.kapitel.filter((k) => k && zahl(k.start_s) && k.start_s >= 0) : [];
  if (roh.length < 2) return [];
  const gesamt = gesamtVon(f);
  return roh.map((k, i) => {
    const bis = i + 1 < roh.length ? roh[i + 1].start_s : gesamt;
    const laenge = zahl(bis) && bis > k.start_s ? bis - k.start_s : null;
    return { nr: i + 1, titel: kapitelTitel(k.titel, i + 1), start_s: k.start_s, track: Number.isInteger(k.track) && k.track >= 0 ? k.track : null, laenge_s: laenge };
  });
}

/* Welches Kapitel gilt an dieser Stelle (Track, Sekunden im Track)? Index oder -1. Ohne bekannte Track-Längen entscheidet bei Ordner-Folgen der Track. */
export function kapitelIndex(kap, f, track, t) {
  if (!kap.length) return -1;
  const nachTrack = trackAnzahl(f) > 1 && !spurenVon(f);
  const g = globalPos(f, track, t);
  let idx = 0;
  kap.forEach((k, i) => { if (nachTrack ? (k.track ?? 0) <= track : k.start_s <= g + 0.01) idx = i; });
  return idx;
}

/* Wohin der Sprung auf ein Kapitel führt: { track, offset (Sekunden im Track) }. Ordner-Folgen: der Track des Kapitels, die Zeit im Track. */
export function kapitelZiel(f, k) {
  if (trackAnzahl(f) <= 1) return { track: 0, offset: k.start_s };
  const sp = spurenVon(f);
  if (k.track === null) return ortVon(f, k.start_s);
  const davor = sp ? sp.slice(0, k.track).reduce((a, b) => a + b, 0) : 0;
  return { track: k.track, offset: Math.max(0, k.start_s - davor) };
}

/* Stelle der gemerkten Hörstelle einer Folge in der ganzen Folge (Sekunden), oder null. */
export function hoerstelleGlobal(f) {
  const h = f?.hoerstelle;
  if (!h || !zahl(h.position_s)) return null;
  return typeof h.track === 'number' ? globalPos(f, h.track, h.position_s) : h.position_s;
}

/* Zeilen für Serienseite und Blatt: die Kapitel mit Zustand. `index`: das markierte Kapitel (oder -1), `fertig`: alles gehört.
 * Gehört sind die Kapitel vor dem markierten (bei „fertig“ alle). */
export function kapitelZeilen(kap, { index = -1, fertig = false } = {}) {
  return kap.map((k, i) => ({ ...k, i, aktuell: i === index, gehoert: fertig || (index >= 0 && i < index) }));
}

/* „ab 2:49 · 0:19“ (ohne bekannte Länge nur „ab 2:49“). */
export const kapitelAb = (z) => (z.laenge_s ? fuellen(KAPITEL.ab, { start: uhr(z.start_s), laenge: uhr(z.laenge_s) }) : fuellen(KAPITEL.ab_start, { start: uhr(z.start_s) }));

/* Wort zum Zustand einer Zeile (Farbe nie allein): „läuft“ / „hier weiter“ am markierten, „gehört“ an den schon gehörten. */
export const kapitelZustandText = (z, spielt) => (z.aktuell ? (spielt ? KAPITEL.laeuft : KAPITEL.hier_weiter) : (z.gehoert ? KAPITEL.gehoert : ''));
export const kapitelZustandHtml = (z, spielt) => { const t = kapitelZustandText(z, spielt); return t ? html`<span class="kap-zu">${t}</span>` : nothing; };

/* Name der Zeile für Screenreader: „Kapitel 4: Der Sturm, ab 1:12, aktuelles Kapitel, abspielen“ (`zusatz` ersetzt „abspielen“, zum Beispiel „Player öffnen“). */
export const kapitelAria = (z, spielt, zusatz = KAPITEL.aria_abspielen) => `${beginntMitKapitel(z.titel) ? fuellen(KAPITEL.aria_eigen, { titel: z.titel, start: uhr(z.start_s) }) : fuellen(KAPITEL.aria, { nr: z.nr, titel: z.titel, start: uhr(z.start_s) })}${z.aktuell ? KAPITEL.aria_aktuell : ''}${z.gehoert && !z.aktuell ? `, ${KAPITEL.gehoert}` : ''}${zusatz}`;

/* Hat irgendeine Folge der Serie eine Kapitelliste? Dann reserviert der Player den Platz für Zeile und Knopf (AM15: nichts springt). */
export const serieHatKapitel = (serie) => (serie?.folgen || []).some((f) => kapitelVon(f).length > 0);

/* Braucht diese Folge noch eine Hörkopie, bevor sie spielt? Dann reservieren Serienseite und Player den Platz für die Karte (AM15). */
export const wartetAufKopie = (f) => ['nicht_angelegt', 'wartet'].includes(f?.hoerkopie?.zustand);

/* Wohin „Reinhören“ führt (Design 5.3): { art: 'rein' | 'weiter' | 'nochmal', index, folge, zeit } oder null (keine Folgen).
 * Grundlage sind `hoerstelle` je Folge (`position_s`, `fertig`) und `hoerstelle.folge` der Serie (zuletzt gehörte Folge). */
export function hoerziel(serie) {
  const folgen = serie?.folgen || [];
  if (!folgen.length) return null;
  if (!folgen.some((f) => f.hoerstelle) && !serie.hoerstelle) return { art: 'rein', index: 0, folge: folgen[0], zeit: 0 };
  if (folgen.every((f) => f.hoerstelle?.fertig)) return { art: 'nochmal', index: 0, folge: folgen[0], zeit: 0 };
  let i = folgen.findIndex((f) => f.name === serie.hoerstelle?.folge);
  if (i < 0) for (let k = folgen.length - 1; k >= 0; k -= 1) if (folgen[k].hoerstelle) { i = k; break; }
  if (i < 0 || folgen[i].hoerstelle?.fertig) { // zuletzt gehörte Folge ist fertig: die nächste ungehörte, sonst die erste ungehörte
    let j = i < 0 ? -1 : folgen.findIndex((f, k) => k > i && !f.hoerstelle?.fertig);
    if (j < 0) j = folgen.findIndex((f) => !f.hoerstelle?.fertig);
    i = j;
  }
  const h = folgen[i].hoerstelle;
  return { art: 'weiter', index: i, folge: folgen[i], zeit: h && !h.fertig && zahl(h.position_s) ? h.position_s : 0 };
}

/* Beschriftung des Hauptknopfs der Serienseite: { art, label, zusatz }. `spielt`: diese Serie läuft gerade; `aktuell`: die Folge, die läuft (sonst die, an der man steht).
 * AM15: die Zeile darunter steht immer (Play und Pause ändern keine Höhe): beim Abspielen „{Folge} · läuft“, sonst „{Folge} · ab 0:24“, bei „Reinhören“ und „Noch einmal hören“ nur der Name. */
export function knopfText(serie, { spielt = false, aktuell = null } = {}) {
  const z = hoerziel(serie);
  if (!z) return null;
  const ziel = (f) => (serie.folgen.length > 1 ? folgeName(f) : serie.name);
  if (spielt) return { art: 'pause', label: PLAYER.knopf.pause, zusatz: fuellen(PLAYER.knopf.laeuft, { ziel: ziel(aktuell || z.folge) }) };
  const label = PLAYER.knopf[z.art];
  const zusatz = z.art === 'weiter' && z.zeit >= 5 ? fuellen(PLAYER.knopf.zusatz, { ziel: ziel(z.folge), zeit: uhr(z.zeit) }) : ziel(z.folge);
  return { art: z.art, label, zusatz };
}

/* Einträge der Reihe „Am Handy weiterhören“ (Start): `hoerstelle/liste` (zuletzt angehört zuerst) mit der Kurzform der Serie (für das Cover).
 * Eine Serie, die es nicht mehr gibt, fällt weg. */
export function weiterReihe(eintraege, kurzformen) {
  const karte = new Map((kurzformen || []).map((s) => [s.id, s]));
  return (eintraege || []).map((e) => {
    const s = karte.get(e.serie_id);
    return { ...(s || { id: e.serie_id, name: e.name, cover_stand: undefined }), id: e.serie_id, name: s?.name ?? e.name, weiter: e };
  }).filter((x) => x.id);
}

const MIME = { mp3: 'audio/mpeg', m4a: 'audio/mp4', m4b: 'audio/mp4', aac: 'audio/aac', flac: 'audio/flac', ogg: 'audio/ogg', opus: 'audio/ogg; codecs=opus', wav: 'audio/wav' };
/* Spielt dieser Browser die Datei? Ohne `canPlayType` oder ohne bekannte Endung: ja (der Server entscheidet dann über die Hörkopie). */
export function formatErlaubt(audio, dateiname) {
  const ende = /\.([A-Za-z0-9]+)$/.exec(String(dateiname ?? ''))?.[1]?.toLowerCase();
  const mime = ende && MIME[ende];
  if (!mime || !audio || typeof audio.canPlayType !== 'function') return true;
  return audio.canPlayType(mime) !== '';
}

/* ------------------------------------------------------------------ Speicher des Geräts (nur Bequemlichkeit) */

function ladeTempo() {
  try { const v = Number(window.localStorage?.getItem(TEMPO_KEY)); return TEMPOS.includes(v) ? v : 1; } catch { return 1; }
}

const radiusVon = (el) => { try { return parseFloat(getComputedStyle(el).borderTopLeftRadius) || 0; } catch { return 0; } };

/* Kennung dieser Player-Instanz für `hoerstelle/set` (Vertrag 41: 8 bis 64 Zeichen aus [A-Za-z0-9_-]). Nicht der Benutzer, nichts Dauerhaftes. */
export function neueSpielerId() {
  try { const u = globalThis.crypto?.randomUUID?.(); if (u) return u; } catch { /* weiter */ }
  let t = '';
  const z = '0123456789abcdefghijklmnopqrstuvwxyz';
  for (let i = 0; i < 24; i += 1) t += z[Math.floor(Math.random() * z.length)];
  return t;
}

/* ------------------------------------------------------------------ Spieler */

export class Spieler {
  /* ctx: api, faehig, neuZeichnen, melde, meldeFehler, ansage, fehlerText, oeffneBlatt, schliesseBlatt, covers, wurzel (Shadow-Root), hass,
   * meldungenPlatz, admin. Alles aus der App (tobibox-app.js `_baueCtx`). */
  constructor(ctx) {
    this.ctx = ctx;
    this.vorbereitetNeuMs = VORBEREITET_NEU_MS; // (Tests dürfen es kürzen)
    this.s = null; // { serie (serie/get), i (Folge), track, pos (Sekunden im Track), dauer (Länge der Datei) }
    this.zustand = 'leer'; // leer | laedt | pause | spielt | vorbereitet
    this.tempo = ladeTempo();
    this.offen = false; // Vollansicht gezeigt (oder am Schließen)
    this.schliesst = false;
    this.gesperrt = false; // Sperre gegen Kinderfinger (X14): nur im Browser, wird nicht gemerkt
    this._audio = null;
    this._lauf = 0; // zählt Starts: eine späte Antwort eines älteren Starts wird verworfen
    this._geladen = false; // loadedmetadata ist da
    this._quelle = false;
    this._wartePos = 0;
    this._wartePlay = false;
    this._linkZeit = 0;
    this._stellen = {}; // Folge → { position_s, fertig, track } der eigenen Hörstelle (gemerkt, damit „Nächste Folge“ weiterhört)
    this._letzteSpeicherung = 0;
    this._vorab = null; // { key, erg, zeit }: die nächste Datei, schon signiert
    this._vorabFrage = null; // Schlüssel, für den schon gefragt wurde
    this._versuche = 0;
    this._wiederhergestellt = false;
    this._gewischtAm = 0;
    this._zieht = false; // Zeitleiste wird gezogen
    this._sessionStand = 0;
    this._sessionKey = '';
    this._miniKey = null;
    this._miniAltKlon = null;
    this._hold = null;
    this._offene = null;
    this._spielerId = neueSpielerId(); // Stufe B: eine zufällige Kennung je Player-Instanz; mit `gehoert` sendet jede Hörstelle sie mit (HA zählt je Instanz eine Sitzung)
    this._onSicht = () => { if (typeof document !== 'undefined' && document.hidden) this._speichere(true); };
    this._onHide = () => this._speichere(true);
  }

  /* ---- Lebenslauf (die App ruft das beim Einhängen und Aushängen) */
  anmelden() {
    window.addEventListener('pagehide', this._onHide);
    document.addEventListener('visibilitychange', this._onSicht);
  }

  abmelden() {
    window.removeEventListener('pagehide', this._onHide);
    document.removeEventListener('visibilitychange', this._onSicht);
    this._speichere(true);
    clearTimeout(this._vorbTimer);
    clearTimeout(this._hold?.timer);
    try { this._audio?.pause?.(); } catch { /* ohne Wiedergabe */ }
  }

  get audio() {
    if (this._audio) return this._audio;
    const a = document.createElement('audio');
    a.preload = 'none';
    a.setAttribute('playsinline', '');
    a.style.display = 'none';
    this._audio = a;
    const wurzel = this.ctx.wurzel;
    try { (wurzel?.appendChild ? wurzel : null)?.appendChild(a); } catch { /* ein losgelöstes Element spielt auch */ }
    a.addEventListener('timeupdate', () => this._aufZeit());
    a.addEventListener('loadedmetadata', () => this._aufMeta());
    a.addEventListener('durationchange', () => this._aufDauer());
    a.addEventListener('play', () => this._aufPlay());
    a.addEventListener('playing', () => { this._versuche = 0; });
    a.addEventListener('pause', () => this._aufPause());
    a.addEventListener('ended', () => this._aufEnde());
    a.addEventListener('error', () => this._aufFehler());
    return a;
  }

  /* ---- Zustand */
  get folge() { return this.s?.serie?.folgen?.[this.s.i] ?? null; }
  get spielt() { return this.zustand === 'spielt'; }
  get gesamt() {
    const f = this.folge;
    return (f && gesamtVon(f)) || (this.s?.dauer > 0 ? this.s.dauer : 0);
  }
  get gpos() { return this.s ? globalPos(this.folge, this.s.track, this.s.pos) : 0; }
  get kapitel() { return this.folge ? kapitelVon(this.folge) : []; }
  /* Index des Kapitels an der aktuellen Stelle (-1 ohne Kapitel). */
  get kapitelNr() { return this.s && this.folge ? kapitelIndex(this.kapitel, this.folge, this.s.track, this.s.pos) : -1; }

  /* Läuft genau diese Serie (und Folge) gerade? Für Knöpfe und Anzeigen der Seiten. */
  laeuft(serieId, name = null) { return !!this.s && this.s.serie.id === serieId && (name === null || this.folge?.name === name) && this.spielt; }
  ist(serieId, name = null) { return !!this.s && this.s.serie.id === serieId && (name === null || this.folge?.name === name); }

  _stand() {
    abspiel.serie = this.s?.serie?.id ?? null;
    abspiel.folge = this.folge?.name ?? null;
    abspiel.spielt = this.spielt;
    this._session();
    this.ctx.neuZeichnen();
  }

  _dauerDerDatei() {
    const f = this.folge;
    const sp = f && spurenVon(f);
    if (sp && sp[this.s.track]) return sp[this.s.track];
    if (f && trackAnzahl(f) === 1 && zahl(f.dauer_s) && f.dauer_s > 0) return f.dauer_s;
    return 0;
  }

  /* ================================================================== Starten, Wechseln */

  /* Startet eine Folge einer Serie (`serie` = Antwort von `serie/get`). `ziel` ({ track, offset }) überstimmt die gemerkte Stelle (Kapitelsprung). Ohne `folge`: dort, wo die eigene Hörstelle steht („Hier weiterhören“),
   * bei einer neuen Serie die erste Folge. Mit `folge` (Name): diese Folge, bei der gemerkten Stelle. Fragt zuerst `hoerstelle/get`. */
  async starte({ serie, folge = null, ziel = null } = {}) {
    const folgen = serie?.folgen || [];
    if (!folgen.length) return;
    let stand = null;
    if (this.ctx.faehig('reinhoeren')) {
      try { stand = await this.ctx.api('tobibox/hoerstelle/get', { serie_id: serie.id }); } catch { /* ohne gemerkte Stelle weiter */ }
    }
    const mit = { ...serie, hoerstelle: stand?.weiter ? { ...(serie.hoerstelle || {}), folge: stand.weiter.folge } : serie.hoerstelle,
      folgen: folgen.map((f) => (stand?.folgen?.[f.name] ? { ...f, hoerstelle: stand.folgen[f.name] } : f)) };
    this._stellen = {};
    for (const [n, e] of Object.entries(stand?.folgen || {})) this._stellen[n] = { position_s: e.position_s, fertig: e.fertig, track: e.track ?? (stand.weiter?.folge === n ? stand.weiter.track ?? 0 : 0) };
    let i;
    let pos = 0;
    let track = 0;
    if (folge === null) {
      const z = hoerziel(mit);
      i = z.index; pos = z.art === 'weiter' ? z.zeit : 0;
    } else {
      i = folgen.findIndex((f) => f.name === folge);
      if (i < 0) return;
      const e = this._stellen[folge];
      if (e && !e.fertig && e.position_s > 1 && (trackAnzahl(folgen[i]) === 1 || stand?.weiter?.folge === folge)) pos = e.position_s;
    }
    if (trackAnzahl(folgen[i]) > 1 && pos > 0) track = this._stellen[folgen[i].name]?.track ?? 0;
    if (ziel) { track = ziel.track; pos = ziel.offset; } // A8d: Sprung auf ein Kapitel
    this._versuche = 0;
    return this._laden(serie, i, track, pos, { auto: true });
  }

  /* Tipp auf Abspielen/Pause einer Serie oder Folge der Seiten: läuft sie schon, schaltet es um. */
  async schalte({ serie, folge = null }) {
    if (this.ist(serie.id, folge) && this._quelle) { this.toggle(); return; }
    return this.starte({ serie, folge });
  }

  /* Wie `schalte`, aber nur mit der Kennung (Suche, Start): holt die Serie bei Bedarf selbst. */
  async spieleId(serieId, folge = null) {
    if (this.ist(serieId, folge) && this._quelle) { this.toggle(); return; }
    let serie;
    try { serie = await this.ctx.api('tobibox/serie/get', { serie_id: serieId }); } catch (e) { this.ctx.meldeFehler(this.ctx.fehlerText(e?.code || 'unknown_error')); return; }
    return this.starte({ serie, folge });
  }

  /* Die gemerkte Stelle holen und die Leiste zeigen, ohne Ton (nach dem Neuladen der Seite, 5.12). Ton startet nur nach einem Tipp. */
  async wiederherstellen() {
    if (this._wiederhergestellt || this.s || !this.ctx.faehig('reinhoeren')) return;
    this._wiederhergestellt = true;
    try {
      const r = await this.ctx.api('tobibox/hoerstelle/liste', { limit: 1 });
      const e = r?.eintraege?.[0];
      if (!e || this.s) return;
      const serie = await this.ctx.api('tobibox/serie/get', { serie_id: e.serie_id });
      if (this.s) return;
      const i = (serie.folgen || []).findIndex((f) => f.name === e.folge);
      if (i < 0) return;
      this.s = { serie, i, track: e.track ?? 0, pos: e.position_s ?? 0, dauer: 0 };
      this.s.dauer = this._dauerDerDatei();
      this._stellen = { [e.folge]: { position_s: e.position_s, fertig: false, track: e.track ?? 0 } };
      this.zustand = 'pause';
      this._stand();
    } catch { /* keine gemerkte Stelle: keine Leiste */ }
  }

  /* Eine Datei laden: erst `audio/bereit`, dann `src`. `auto`: nach dem Laden spielen. */
  async _laden(serie, i, track, pos, { auto = true, vorbereiten = true, retry = false } = {}) {
    const lauf = ++this._lauf;
    clearTimeout(this._vorbTimer);
    this._speichere(true);
    const vorher = this.s ? { s: this.s, zustand: this.zustand } : null;
    const folge = serie.folgen[i];
    this.s = { serie, i, track, pos, dauer: 0 };
    this.s.dauer = this._dauerDerDatei();
    this._geladen = false;
    this._wartePos = pos;
    this._wartePlay = auto;
    this.zustand = 'laedt';
    if (!retry) this._versuche = 0;
    this._vorabFrage = null;
    this._stand();
    const zurueck = () => { if (vorher && lauf === this._lauf) { this.s = vorher.s; this.zustand = vorher.zustand === 'spielt' ? 'pause' : vorher.zustand; this._stand(); } else if (lauf === this._lauf) { this.s = null; this.zustand = 'leer'; this._stand(); } };
    if (!this.ctx.faehig('hoerkopie') && !formatErlaubt(this.audio, folge.name)) {
      this.ctx.meldeFehler(FEHLER.browser_spielt_nicht);
      zurueck();
      return;
    }
    const key = `${i}|${track}`;
    let erg;
    if (this._vorab && this._vorab.key === `${serie.id}|${key}` && this._vorab.erg.zustand === 'bereit' && Date.now() - this._vorab.zeit < LINK_ERNEUERN_MS) {
      erg = this._vorab.erg;
      this._vorab = null;
    } else {
      try {
        erg = await this.ctx.api('tobibox/audio/bereit', { serie_id: serie.id, folge: folge.name, ...(trackAnzahl(folge) > 1 ? { track } : {}), ...(vorbereiten ? {} : { vorbereiten: false }) });
      } catch (e) {
        if (lauf !== this._lauf) return;
        this.ctx.meldeFehler(this.ctx.fehlerText(e?.code || 'unknown_error'));
        zurueck();
        return;
      }
    }
    if (lauf !== this._lauf) return;
    if (erg.zustand === 'wird_vorbereitet') {
      this.zustand = 'vorbereitet';
      if (!retry && vorbereiten) this.ctx.melde(HOERPROBE.vorbereitung);
      this._stand();
      this._vorbTimer = setTimeout(() => { if (lauf === this._lauf) this._laden(serie, i, track, pos, { auto, vorbereiten: false, retry: true }); }, this.vorbereitetNeuMs);
      return;
    }
    if (erg.zustand !== 'bereit') { // `fehlt`
      this.ctx.meldeFehler(erg.grund === 'medien_nicht_erreichbar' ? this.ctx.fehlerText('medien_nicht_erreichbar') : HOERPROBE.keine_datei);
      zurueck();
      return;
    }
    this._quelle = true;
    this._linkZeit = Date.now();
    const a = this.audio;
    const hass = this.ctx.hass;
    a.src = typeof hass?.hassUrl === 'function' ? hass.hassUrl(erg.pfad) : erg.pfad;
    a.preload = 'auto';
    try { a.defaultPlaybackRate = this.tempo; a.playbackRate = this.tempo; } catch { /* ohne */ }
    // kein `load()` hinterher: das Setzen von `src` startet das Laden schon, ein zweiter Start bräche die erste Anfrage ab (doppelte Anfrage)
    this._stand();
  }

  _aufMeta() {
    const a = this.audio;
    if (!this.s || !this._quelle) return;
    this._geladen = true;
    if (zahl(a.duration) && a.duration > 0) this.s.dauer = a.duration;
    this._letzteSpeicherung = Date.now(); // der Start zählt als Speicherung: die nächste folgt frühestens nach 10 Sekunden
    try { if (this._wartePos > 0) a.currentTime = this._wartePos; } catch { /* nicht suchbar */ }
    try { a.playbackRate = this.tempo; } catch { /* ohne */ }
    if (this._wartePlay) this._spielen();
    this._wartePlay = false;
    this._wartePos = 0;
    this._stand();
  }

  _aufDauer() {
    const a = this._audio;
    if (!this.s || !a || !zahl(a.duration) || !(a.duration > 0)) return;
    if (this.s.dauer !== a.duration) { this.s.dauer = a.duration; this._tick(); }
  }

  _spielen() {
    const a = this.audio;
    try {
      const p = a.play();
      if (p && typeof p.catch === 'function') {
        p.catch((e) => {
          if (e?.name === 'AbortError') return; // ein neuer Start hat diesen abgelöst
          this.zustand = 'pause';
          if (e?.name === 'NotAllowedError') this.ctx.melde(HOERPROBE.fertig); // kein Tipp dahinter (zum Beispiel nach dem Warten auf die Hörprobe): ein Tipp startet es
          this._stand();
        });
      }
    } catch { /* ohne Wiedergabe */ }
  }

  _aufPlay() {
    if (!this.s || !this._quelle) return;
    this.zustand = 'spielt';
    this._stand();
  }

  _aufPause() {
    const a = this._audio;
    if (!this.s || !this._quelle || (a && a.ended)) return;
    if (this.zustand === 'laedt' || this.zustand === 'vorbereitet') return;
    this.zustand = 'pause';
    this._speichere(true);
    this._stand();
  }

  _aufZeit() {
    const a = this._audio;
    if (!this.s || !a || !this._geladen) return;
    this.s.pos = a.currentTime;
    if (this.spielt) { this._speichere(false); this._vorabHolen(); }
    this._tick();
    const kn = this.kapitelNr; // ein anderes Kapitel: Zeile im Player und Markierung auf der Seite nachziehen
    if (kn !== this._kapNr) { this._kapNr = kn; this.ctx.neuZeichnen(); }
  }

  _aufEnde() {
    if (!this.s) return;
    const { serie, i, track } = this.s;
    const f = this.folge;
    if (track + 1 < trackAnzahl(f)) { this._laden(serie, i, track + 1, 0, { auto: true }); return; }
    this.s.pos = this.s.dauer || this.s.pos;
    this._stellen[f.name] = { position_s: this.s.pos, fertig: true, track };
    this._speichere(true, { fertig: true });
    this._geladen = false; // das Wechseln speichert nicht noch einmal (sonst wäre die Folge wieder „nicht fertig“)
    if (i + 1 < serie.folgen.length) { this._laden(serie, i + 1, 0, 0, { auto: true }); return; }
    this.zustand = 'pause'; // nach der letzten Folge ist Schluss (5.12)
    this._stand();
  }

  /* Fehler des `<audio>`-Elements: sagt nichts über die Ursache (401, 429, 503, 404 sehen gleich aus). Die Seite fragt neu per `audio/bereit`
   * und macht an der Stelle weiter; bleibt es dabei, spielt dieser Browser die Datei nicht. */
  _aufFehler() {
    const a = this._audio;
    if (!this.s || !this._quelle || !a || !a.getAttribute?.('src')) return;
    const wollte = this.zustand === 'spielt' || this._wartePlay;
    if (this._versuche >= NEU_VERSUCHE) {
      this._versuche = 0;
      this.zustand = 'pause';
      this.ctx.meldeFehler(FEHLER.browser_spielt_nicht);
      this._stand();
      return;
    }
    this._versuche += 1;
    this._quelle = false;
    this._laden(this.s.serie, this.s.i, this.s.track, this._geladen ? this.s.pos : this._wartePos, { auto: wollte, retry: true });
  }

  /* ---- nächste Datei im Voraus signieren (Messung 2: Lücke beim Trackwechsel am gesperrten Handy 822 ms) */
  _naechstes() {
    if (!this.s) return null;
    const { serie, i, track } = this.s;
    const f = this.folge;
    if (track + 1 < trackAnzahl(f)) return { i, track: track + 1, folge: f };
    if (i + 1 < serie.folgen.length) return { i: i + 1, track: 0, folge: serie.folgen[i + 1] };
    return null;
  }

  async _vorabHolen() {
    const n = this._naechstes();
    const dauer = this.s?.dauer;
    if (!n || !(dauer > 0) || dauer - this.s.pos > VORAB_S) return;
    const key = `${this.s.serie.id}|${n.i}|${n.track}`;
    if (this._vorabFrage === key) return;
    this._vorabFrage = key;
    const lauf = this._lauf;
    try {
      const erg = await this.ctx.api('tobibox/audio/bereit', { serie_id: this.s.serie.id, folge: n.folge.name, ...(trackAnzahl(n.folge) > 1 ? { track: n.track } : {}), vorbereiten: false });
      if (lauf === this._lauf && erg?.zustand === 'bereit') this._vorab = { key, erg, zeit: Date.now() };
    } catch { /* beim Wechsel fragt die Seite dann selbst */ }
  }

  /* ================================================================== Bedienung */

  toggle() {
    if (!this.s) return;
    const a = this._audio;
    if (this.zustand === 'laedt') return;
    if (this.zustand === 'vorbereitet') { clearTimeout(this._vorbTimer); this._lauf += 1; this.zustand = 'pause'; this._stand(); return; }
    if (!this._quelle || !this._geladen || !a || !a.getAttribute?.('src')) {
      this._versuche = 0;
      this._laden(this.s.serie, this.s.i, this.s.track, this.s.pos, { auto: true });
      return;
    }
    if (a.paused || a.ended) {
      if (Date.now() - this._linkZeit > LINK_ERNEUERN_MS) { // der Link läuft bald ab: neuen holen, an derselben Stelle weiter
        this._quelle = false;
        this._laden(this.s.serie, this.s.i, this.s.track, a.currentTime, { auto: true });
        return;
      }
      if (a.ended) { try { a.currentTime = 0; } catch { /* ohne */ } }
      this._spielen();
    } else a.pause();
  }

  /* Springt an eine Stelle der ganzen Folge (bei Ordner-Folgen über Tracks hinweg). */
  seek(sek) {
    if (!this.s) return;
    const f = this.folge;
    const g = this.gesamt;
    const ziel = Math.max(0, g > 0 ? Math.min(sek, g) : sek);
    const { track, offset } = ortVon(f, ziel);
    const a = this._audio;
    if (track !== this.s.track) {
      this._laden(this.s.serie, this.s.i, track, offset, { auto: this.spielt || this.zustand === 'laedt' });
      return;
    }
    this.s.pos = offset;
    if (a && this._geladen) { try { a.currentTime = offset; } catch { /* nicht suchbar */ } }
    this._speichere(true);
    this._tick();
    this._session(true);
  }

  sprung(delta) { this.seek(this.gpos + delta); }

  /* ---- Kapitel (A8d, Design 11.4.8): eingebettete Kapitel setzen die Zeit, bei Ordner-Folgen wechselt der Track (neuer Link, `?track=n`) und dann die Zeit im Track.
   * Die Hörstelle speichert wie bisher `track` und `position_s`. Nach dem Sprung läuft der Ton weiter (auch aus der Pause). */
  springeKapitel(index) {
    const k = this.kapitel[index];
    if (!this.s || !k) return;
    const { track, offset } = kapitelZiel(this.folge, k);
    const a = this._audio;
    const frisch = Date.now() - this._linkZeit <= LINK_ERNEUERN_MS;
    if (track !== this.s.track || !this._quelle || !this._geladen || !a || !frisch) {
      this._laden(this.s.serie, this.s.i, track, offset, { auto: true });
      return;
    }
    this.s.pos = offset;
    try { a.currentTime = offset; } catch { /* nicht suchbar */ }
    this._speichere(true);
    this._tick();
    this._session(true);
    if (!this.spielt) this._spielen();
    this.ctx.neuZeichnen();
  }

  /* Tipp auf eine Kapitelzeile der Serienseite (AM13): ist es das geladene Kapitel (läuft oder pausiert), öffnet die Vollansicht und der Ton bleibt;
   * sonst springt der Player dorthin und spielt (aus einer anderen Folge oder ohne Player: Start an dieser Stelle). */
  async spieleKapitel({ serie, folge, index }) {
    const f = (serie?.folgen || []).find((x) => x.name === folge);
    const k = f && kapitelVon(f)[index];
    if (!k) return;
    if (this.ist(serie.id, folge) && this._quelle) {
      if (this.kapitelNr === index) { this.oeffnen(); return; }
      this.springeKapitel(index);
      return;
    }
    return this.starte({ serie, folge, ziel: kapitelZiel(f, k) });
  }

  /* „Vorige Folge“ springt bei mehr als 5 Sekunden zuerst an den Anfang der Folge. */
  vorige() {
    if (!this.s) return;
    if (this.gpos > 5 || this.s.i === 0) { this.seek(0); return; }
    this._wechsle(this.s.i - 1, false);
  }

  naechste() {
    if (!this.s || this.s.i + 1 >= this.s.serie.folgen.length) return;
    this._wechsle(this.s.i + 1, true);
  }

  _wechsle(j, vor) {
    const { serie } = this.s;
    const f = serie.folgen[j];
    const e = vor ? this._stellen[f.name] : null; // vorwärts: an der gemerkten Stelle, rückwärts von vorn
    const pos = e && !e.fertig && e.position_s > 1 ? e.position_s : 0;
    this._laden(serie, j, pos > 0 && trackAnzahl(f) > 1 ? (e.track ?? 0) : 0, pos, { auto: true });
  }

  setzeTempo(v) {
    if (!TEMPOS.includes(v)) return;
    this.tempo = v;
    try { window.localStorage?.setItem(TEMPO_KEY, String(v)); } catch { /* ohne Speicher */ }
    const a = this._audio;
    if (a) { try { a.playbackRate = v; a.defaultPlaybackRate = v; } catch { /* ohne */ } }
    this._stand();
  }

  /* ---- Sperre gegen Kinderfinger (A8e, X14) */
  sperren() {
    if (!this.s) return;
    this.gesperrt = true;
    this.ctx.ansage(PLAYER.voll.ansage_gesperrt);
    this._stand();
    this._fokus('dialog.player [data-p="unlock"]');
  }

  /* Fokus nach dem nächsten Zeichnen (das Ziel steht vorher noch nicht im DOM). */
  _fokus(sel) {
    Promise.resolve(this.ctx.nachZeichnen?.()).then(() => this.ctx.wurzel?.querySelector?.(sel)?.focus?.({ preventScroll: true }));
  }

  holeStart(knopf) {
    this.holeStopp();
    knopf?.classList?.add('holding');
    this._hold = { knopf, timer: setTimeout(() => this._entsperren(), ENTSPERREN_MS) };
  }

  holeStopp() {
    if (!this._hold) return;
    clearTimeout(this._hold.timer);
    this._hold.knopf?.classList?.remove('holding');
    this._hold = null;
  }

  _entsperren() {
    this.holeStopp();
    this.gesperrt = false;
    this.ctx.ansage(PLAYER.voll.ansage_entsperrt);
    this._stand();
    this._fokus('dialog.player [data-p="play"]');
  }

  /* ================================================================== Hörstelle sammeln (Vertrag 14.6) */

  _speichere(sofort = false, { fertig = false } = {}) {
    if (!this.s || !this.ctx.faehig('reinhoeren') || (!this._geladen && !fertig)) return;
    const jetzt = Date.now();
    if (!sofort && jetzt - this._letzteSpeicherung < SPEICHER_MS) return;
    const a = this._audio;
    const f = this.folge;
    let dauer = a && zahl(a.duration) && a.duration > 0 ? a.duration : this.s.dauer;
    if (!(dauer > 0)) return;
    let pos = a && this._geladen ? a.currentTime : this.s.pos;
    if (!zahl(pos)) pos = this.s.pos;
    if (fertig) pos = dauer;
    pos = Math.max(0, Math.min(pos, dauer));
    const msg = { serie_id: this.s.serie.id, folge: f.name, position_s: Math.round(pos * 10) / 10, dauer_s: Math.max(1, Math.round(dauer * 10) / 10) };
    if (trackAnzahl(f) > 1) msg.track = this.s.track;
    if (fertig) msg.fertig = true;
    if (this.ctx.faehig('gehoert')) { msg.spieler = this._spielerId; msg.spielt = this.spielt && !fertig; } // Stufe B (Vertrag 41): nur mit der Fähigkeit; `spielt` = der Ton läuft gerade
    this._letzteSpeicherung = jetzt;
    this._stellen[f.name] = { position_s: msg.position_s, fertig, track: this.s.track };
    Promise.resolve(this.ctx.api('tobibox/hoerstelle/set', msg)).catch(() => { /* zu_viele_aenderungen und Netzfehler: der nächste Anlass speichert wieder */ });
  }

  /* ================================================================== Media-Session (Sperrbildschirm) */

  _session(nurPosition = false) {
    const nav = typeof window !== 'undefined' ? window.navigator : null;
    const ms = nav?.mediaSession;
    if (!ms || !this.s) return;
    try {
      if (!this._handler) {
        this._handler = true;
        const setze = (n, fn) => { try { ms.setActionHandler(n, fn); } catch { /* Aktion unbekannt */ } };
        setze('play', () => { if (!this.spielt) this.toggle(); });
        setze('pause', () => { if (this.spielt) this.toggle(); });
        setze('seekbackward', (d) => this.sprung(-(d?.seekOffset || SPRUNG_S)));
        setze('seekforward', (d) => this.sprung(d?.seekOffset || SPRUNG_S));
        setze('previoustrack', () => this.vorige());
        setze('nexttrack', () => this.naechste());
        setze('seekto', (d) => { if (d && zahl(d.seekTime)) this.seek(d.seekTime); });
      }
      const f = this.folge;
      const s = this.s.serie;
      const key = `${s.id}|${this.s.i}`;
      if (key !== this._sessionKey && typeof window.MediaMetadata === 'function') {
        this._sessionKey = key;
        const art = ZEILE.art[s.art] || '';
        ms.metadata = new window.MediaMetadata({ title: folgeName(f), artist: s.name, album: art });
        if (s.cover_stand && this.ctx.covers?.blobUrl) {
          this.ctx.covers.blobUrl(s.id, s.cover_stand).then((url) => {
            if (url && key === this._sessionKey) ms.metadata = new window.MediaMetadata({ title: folgeName(f), artist: s.name, album: art, artwork: [{ src: url, sizes: '192x192', type: 'image/jpeg' }] });
          }).catch(() => {});
        }
      }
      if (!nurPosition) ms.playbackState = this.spielt ? 'playing' : 'paused';
      const g = this.gesamt;
      if (typeof ms.setPositionState === 'function' && g > 0 && (nurPosition || Date.now() - this._sessionStand > 4000)) {
        this._sessionStand = Date.now();
        ms.setPositionState({ duration: g, playbackRate: this.tempo, position: Math.min(this.gpos, g) });
      }
    } catch { /* Sperrbildschirm geht nicht: kein Fehler für die Wiedergabe */ }
  }

  /* ================================================================== Darstellung */

  /* Zeit und Balken ohne neues Zeichnen: Lit überschreibt sie nicht (sie stehen nicht in den Bindungen). */
  _tick() {
    const w = this.ctx.wurzel;
    if (!w || !this.s) return;
    const g = this.gesamt;
    const p = g > 0 ? Math.min(this.gpos, g) : this.gpos;
    const bar = w.querySelector('.mini .mbar i');
    if (bar) bar.style.width = `${g > 0 ? Math.round(Math.min(100, (p / g) * 100) * 100) / 100 : 0}%`;
    const d = w.querySelector('dialog.player');
    if (d) {
      const sl = d.querySelector('.pslider');
      const gezeigt = this._zieht && sl ? Number(sl.value) : p;
      if (sl && !this._zieht) sl.value = String(Math.round(p));
      const t = d.querySelector('[data-ptime]');
      const r = d.querySelector('[data-prest]');
      if (t) t.textContent = uhr(gezeigt);
      if (r) r.textContent = `−${uhr(Math.max(0, g - gezeigt))}`;
      if (sl) sl.setAttribute('aria-valuetext', fuellen(PLAYER.voll.zeit_von, { zeit: uhr(gezeigt), gesamt: uhr(g) }));
    }
    this._session(false);
  }

  _miniCover() { return this.ctx.wurzel?.querySelector?.('.mini .mopen .cover') ?? null; }

  /* Leiste (Mini-Player). Antippen oder Wischen nach oben öffnet die Vollansicht, der runde Knopf schaltet Play/Pause. */
  miniHtml() {
    if (!this.s) return nothing;
    const { serie } = this.s;
    const f = this.folge;
    const titel = folgeName(f);
    const sub = this._untertitel();
    return html`<div class="mini-in" @pointerdown=${(e) => this._miniDown(e)} @pointermove=${(e) => this._miniMove(e)} @pointerup=${(e) => this._miniEnde(e)} @pointercancel=${(e) => this._miniEnde(e)}>
      <div class="mbar" aria-hidden="true"><i></i></div>
      <div class="mrow">
        <button type="button" class="mopen" data-p="open" aria-label=${fuellen(PLAYER.mini.oeffnen, { titel, serie: serie.name })} title=${PLAYER.mini.tipp} @click=${() => this._miniKlick('open')}>
          ${cover(serie, 'sm')}<span class="grow"><span class="mt">${titel}</span><span class="ms">${sub}</span></span></button>
        <button type="button" class="mplay" data-p="toggle" aria-label=${this.spielt ? PLAYER.mini.pause : PLAYER.mini.abspielen} @click=${() => this._miniKlick('toggle')}>${ic(this.spielt ? 'pause' : 'play', 28)}</button>
      </div></div>`;
  }

  _untertitel() {
    const { serie } = this.s;
    return serie.einzeln || this.folge?.name === serie.name ? (ZEILE.art[serie.art] ?? serie.name) : serie.name;
  }

  _miniKlick(was) {
    if (Date.now() - this._gewischtAm < 250) return;
    if (was === 'open') this.oeffnen(); else this.toggle();
  }

  /* Wischen nach oben in der Leiste (mindestens 40 px, deutlich mehr senkrecht als waagerecht) öffnet die Vollansicht (Design 5.12, X6). */
  _miniDown(e) { if ((e.button ?? 0) > 0) return; this._swY = e.clientY; this._swX = e.clientX; this._swCap = false; }

  _miniEnde(e) {
    this._swY = null;
    if (this._swCap) { try { e.currentTarget.releasePointerCapture(e.pointerId); } catch { /* ohne */ } }
    this._swCap = false;
  }

  _miniMove(e) {
    if (this._swY == null) return;
    const dy = this._swY - e.clientY;
    const dx = e.clientX - this._swX;
    // mit der Maus bleibt das Ziehen sonst an der Leiste kleben, sobald der Zeiger sie nach oben verlässt (Touch hat das von selbst)
    if (!this._swCap && dy > 8 && dy > Math.abs(dx)) { this._swCap = true; try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* ohne */ } }
    if (dy > SCHWELLE_AUF && dy > Math.abs(dx) * 1.5) {
      this._swY = null;
      this._gewischtAm = Date.now();
      this.oeffnen();
    }
  }

  /* Vollansicht. Steht nur im DOM, solange `offen` gilt (auch während des Schließens). */
  vollHtml() {
    if (!this.offen || !this.s) return nothing;
    const { serie, i } = this.s;
    const f = this.folge;
    const L = this.gesperrt;
    const n = serie.folgen.length;
    const g = this.gesamt;
    const sub = n > 1 ? fuellen(PLAYER.voll.folge_von, { eintrag: this._untertitel(), nr: i + 1, anzahl: n }) : this._untertitel();
    // A8d, AM15: Zeile „Kapitel …“ und Knopf stehen, sobald irgendeine Folge der Serie Kapitel hat (feste Höhe); ohne Kapitel in der Serie gibt es beides nicht
    const kap = this.kapitel;
    const hatKap = serieHatKapitel(serie);
    const kn = kap.length ? this.kapitelNr : -1;
    const kapZeile = kn >= 0 ? this._kapitelZeile(kap[kn], kap.length) : '';
    const wartet = this.zustand === 'vorbereitet';
    const knopf = (was, label, symbol, aus = false, klasse = '') => html`<button type="button" class=${`pbtn ${klasse}`.trim()} data-p=${was} aria-label=${label} ?disabled=${aus || L} @click=${() => this._klick(was)}>${symbol}</button>`;
    return html`<dialog class="player" aria-labelledby="p-ansicht pt-t" ?data-gesperrt=${L}
        @cancel=${(e) => { e.preventDefault(); if (!L) this.schliessen('esc'); }} @close=${() => this._dialogClose()}
        @pointerdown=${(e) => this._ziehDown(e)} @pointermove=${(e) => this._ziehMove(e)} @pointerup=${(e) => this._ziehEnde(e)} @pointercancel=${(e) => this._ziehEnde(e)}
        @contextmenu=${(e) => { if (L) e.preventDefault(); }}>
      <div class="p-wrap"><div class="p-flaeche" aria-hidden="true"></div>
      <div class="pin">
        <div class="grip" aria-hidden="true"></div>
        <div class="phead">
          <button type="button" class="iconbtn plain" data-p="close" aria-label=${PLAYER.voll.schliessen} ?disabled=${L} @click=${() => this._klick('close')}>${ic('down', 28)}</button>
          <span class="muted" id="p-ansicht">${L ? PLAYER.voll.gesperrt : PLAYER.voll.laeuft}</span>
          <button type="button" class="iconbtn plain" data-p="more" aria-haspopup="dialog" aria-label=${PLAYER.voll.mehr} ?disabled=${L} @click=${() => this._klick('more')}>${ic('more', 28)}</button>
        </div>
        ${cover(serie, 'pxl')}
        <div class="ptitle"><h2 id="pt-t" tabindex="-1">${folgeName(f)}</h2><div class="muted" data-psub>${sub}</div>${hatKap ? html`<div class="muted pkap" data-pkap aria-live="off">${kapZeile}</div>` : nothing}</div>
        <input class="pslider" type="range" min="0" max=${Math.max(1, Math.round(g))} step="1" aria-label=${PLAYER.voll.position} ?disabled=${L}
          @input=${() => { this._zieht = true; this._tick(); }} @change=${(e) => { this._zieht = false; this.seek(Number(e.target.value)); }}>
        <div class="ptimes"><span data-ptime>0:00</span><span data-prest>−0:00</span></div>
        <div class="pctl">
          ${knopf('prev', PLAYER.voll.vorige, ic('prev', 32), i === 0)}${knopf('back', PLAYER.voll.zurueck30, ic30(false))}
          ${knopf('play', this.spielt ? PLAYER.mini.pause : PLAYER.mini.abspielen, ic(this.spielt ? 'pause' : 'play', 40), false, 'main')}
          ${knopf('fwd', PLAYER.voll.vor30, ic30(true))}${knopf('next', PLAYER.voll.naechste, ic('next', 32), i >= n - 1)}
        </div>
        <div class=${hatKap ? 'speed mitkap' : 'speed'}>${hatKap ? html`<button type="button" class="btn" data-p="kapitel" aria-haspopup="dialog" ?disabled=${L || !kap.length} @click=${() => this._klick('kapitel')}>${ic('list', 20)}${PLAYER.voll.kapitel}</button>` : nothing}${L
    ? html`<button type="button" class="btn primary unlock" data-p="unlock" aria-label=${PLAYER.voll.entsperren_aria}
            @pointerdown=${(e) => { if ((e.button ?? 0) === 0) this.holeStart(e.currentTarget); }} @pointerup=${() => this.holeStopp()} @pointercancel=${() => this.holeStopp()} @pointerleave=${() => this.holeStopp()}
            @keydown=${(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); if (!e.repeat) this.holeStart(e.currentTarget); } }} @keyup=${() => this.holeStopp()}
            @click=${() => { if (Date.now() - this._gewischtAm >= 250) this.ctx.melde(PLAYER.voll.entsperren_hinweis); }}><span class="ring"></span>${ic('lock', 24)}${PLAYER.voll.gedrueckt_halten}</button>`
    : html`<button type="button" class="btn" data-p="lock" @click=${() => this.sperren()}>${ic('lock', 20)}${PLAYER.voll.sperren}</button>`}</div>
        ${wartet || wartetAufKopie(f) ? html`<p class="muted pnote" data-pnote ?data-vorbereitet=${wartet} role="status">${wartet ? PLAYER.voll.vorbereitet : ''}</p>` : nothing}
      </div></div></dialog>`;
  }

  _klick(was) {
    if (Date.now() - this._gewischtAm < 250 || this.gesperrt) return;
    if (was === 'close') this.schliessen('knopf');
    else if (was === 'play') this.toggle();
    else if (was === 'back') this.sprung(-SPRUNG_S);
    else if (was === 'fwd') this.sprung(SPRUNG_S);
    else if (was === 'prev') this.vorige();
    else if (was === 'next') this.naechste();
    else if (was === 'more') this.tempoBlatt();
    else if (was === 'kapitel') this.kapitelBlatt();
  }

  /* Zeile unter dem Titel: „Kapitel 8: Das Echo (8 von 12)“ (ein Titel „Kapitel 8“ steht nicht doppelt). */
  _kapitelZeile(k, anzahl) {
    const titel = beginntMitKapitel(k.titel) ? k.titel : fuellen(KAPITEL.nummer_titel, { nr: k.nr, titel: k.titel });
    return fuellen(PLAYER.voll.kapitel_zeile, { titel, nr: k.nr, anzahl });
  }

  /* Blatt „Kapitel“ (Design 5.12): Titel, „ab 2:49 · 0:19“, schon gehörte mit Häkchen, das aktuelle markiert und beim Öffnen sichtbar. Tipp = dorthin springen und weiterspielen, das Blatt schließt. */
  kapitelBlatt() {
    if (!this.s || !this.kapitel.length) return;
    const zeile = (z) => html`<button type="button" class="kap-zeile" data-kapitel=${z.i} aria-current=${z.aktuell ? 'true' : nothing} aria-label=${kapitelAria(z, this.spielt)}
        @click=${() => { this.springeKapitel(z.i); this.ctx.schliesseBlatt('knopf'); }}>
        <span class="kap-nr">${z.gehoert ? ic('check', 20) : html`<span aria-hidden="true">${z.nr}</span>`}</span>
        <span class="kap-txt"><span class="kap-t">${z.titel}</span><span class="muted kap-ab">${kapitelAb(z)}</span></span>
        ${kapitelZustandHtml(z, this.spielt)}</button>`;
    this.ctx.oeffneBlatt({
      titel: KAPITEL.abschnitt,
      inhalt: () => html`<div class="kap-liste" data-kapitel-liste>${kapitelZeilen(this.kapitel, { index: this.kapitelNr }).map(zeile)}</div>`,
      knoepfe: [{ label: KAPITEL.schliessen }],
    });
    Promise.resolve(this.ctx.nachZeichnen?.()).then(() => setTimeout(() => {
      const el = this.ctx.wurzel?.querySelector?.('dialog.blatt [aria-current="true"]');
      if (!el) return;
      try { el.scrollIntoView?.({ block: 'center' }); } catch { /* ohne */ }
      el.focus?.({ preventScroll: true });
    }, 0));
  }

  /* Blatt „Wiedergabe“ mit der Geschwindigkeit (gilt für alle Folgen, wird gemerkt; X14). */
  tempoBlatt() {
    const T = PLAYER.tempo;
    this.ctx.oeffneBlatt({
      titel: T.titel,
      inhalt: () => html`<h3 class="p-h3">${T.abschnitt}</h3><div class="p-stack" role="radiogroup" aria-label=${T.label}>${TEMPOS.map((v) => html`<button type="button" class="p-opt" role="radio" data-tempo=${v}
        aria-checked=${this.tempo === v ? 'true' : 'false'} @click=${() => { this.setzeTempo(v); this.ctx.schliesseBlatt('knopf'); }}><span>${T.werte[v]}</span>${this.tempo === v ? ic('check', 22) : nothing}</button>`)}</div>`,
      knoepfe: [{ label: T.schliessen }],
    });
  }

  /* ================================================================== Vollansicht öffnen und schließen (A8m) */

  oeffnen() {
    if (!this.s || this.offen) return;
    const mc = this._miniCover();
    this._flugVon = mc ? { rect: rechteck(mc.getBoundingClientRect()), radius: radiusVon(mc) } : null;
    this.offen = true;
    this.schliesst = false;
    this.ctx.neuZeichnen();
  }

  schliessen(grund = 'knopf', { dy = 0 } = {}) {
    if (!this.offen || this.schliesst || this.gesperrt) return;
    const d = this.ctx.wurzel?.querySelector?.('dialog.player');
    if (!d) { this.offen = false; this.ctx.neuZeichnen(); return; }
    this.schliesst = true;
    this._dialogZu(d, dy);
  }

  _teile(d) {
    return { flaeche: d.querySelector('.p-flaeche'), gross: d.querySelector('.pin > .cover'), rest: [...d.querySelectorAll('.pin > :not(.cover)')] };
  }

  /* Wird nach jedem Zeichnen gerufen (tobibox-app.js `updated`): öffnet die neue Vollansicht, setzt Bilder und Fokus. */
  nachRender() {
    const w = this.ctx.wurzel;
    if (!w) return;
    const d = w.querySelector('dialog.player');
    if (d) this._grossesCover(d); // AM14: zuerst das Bild setzen, erst danach klont `_dialogEin` das große Cover für den Flug
    if (d && !d.dataset.offen) { d.dataset.offen = '1'; this._dialogEin(d); }
    this._miniWechsel();
    this._tick();
    const sl = d?.querySelector('.pslider');
    if (sl && !this._zieht) { const g = this.gesamt; sl.value = String(Math.round(Math.min(this.gpos, g || this.gpos))); }
  }

  /* Das große Cover bekommt zuerst das kleine Bild (vom Mini-Cover oder aus dem Cover-Lader) und dann die große Fassung (AM14, wie AM7 auf der Serienseite).
   * So trägt auch der Klon im Flug (Öffnen und Schließen) schon ein Bild und nicht die Ersatzkachel. Die große Fassung wird erst dekodiert und blendet dann über. */
  _grossesCover(d) {
    const big = d.querySelector('.pin > .cover');
    const mini = this._miniCover();
    const { serie } = this.s;
    if (!big || big.dataset.pxl === serie.id + (serie.cover_stand ?? '')) return;
    const key = serie.id + (serie.cover_stand ?? '');
    big.dataset.pxl = key;
    delete big.dataset.gross;
    let klein = mini?.style.backgroundImage || '';
    if (!klein && serie.cover_stand) { const u = this.ctx.covers?.kleinSofort?.(serie.id, serie.cover_stand); if (u) klein = `url("${u}")`; }
    if (klein) { big.style.backgroundImage = klein; big.dataset.bild = '1'; }
    if (!serie.cover_stand) return;
    coverGrossUrl(this.ctx.covers, serie.id, serie.cover_stand).then(async (url) => {
      if (!url || !big.isConnected || big.dataset.pxl !== key) return;
      if (klein && typeof Image === 'function') { // erst dekodieren, dann überblenden: kein Sprung, kein Aufblitzen
        try { const img = new Image(); img.src = url; if (typeof img.decode === 'function') await img.decode(); } catch { /* ohne Dekodieren weiter */ }
        if (!big.isConnected || big.dataset.pxl !== key) return;
      }
      this._grossSetzen(big, url, klein);
    });
  }

  /* Die große Fassung an die Stelle des kleinen Bildes: eine Schicht blendet darüber ein, dann wird sie zum Hintergrund. Das kleine Bild bleibt darunter, bis die Schicht fertig ist. */
  _grossSetzen(el, url, klein) {
    const fertig = () => { el.style.backgroundImage = `url("${url}")`; el.dataset.bild = '1'; el.dataset.gross = '1'; };
    if (!klein || reduziert() || !kannAnimieren(el)) { fertig(); return; }
    const o = el.ownerDocument.createElement('i');
    o.setAttribute('aria-hidden', 'true');
    o.setAttribute('data-gross-schicht', '1');
    Object.assign(o.style, { position: 'absolute', inset: '0', borderRadius: 'inherit', backgroundImage: `url("${url}")`, backgroundSize: 'cover', backgroundPosition: 'center', pointerEvents: 'none', opacity: '0' });
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    el.appendChild(o);
    const an = animiere(o, [{ opacity: 0 }, { opacity: 1 }], { duration: 220, easing: 'ease-out', fill: 'forwards' });
    const ende = () => { fertig(); o.remove(); };
    if (!an) { ende(); return; }
    if (an.finished && typeof an.finished.then === 'function') an.finished.then(ende, ende); else { an.onfinish = ende; an.oncancel = ende; }
  }

  _mini() { return this.ctx.wurzel?.querySelector?.('.mini') ?? null; }

  _dialogEin(d) {
    const mini = this._mini();
    d.classList.add('fliegt');
    if (typeof d.showModal === 'function') { try { d.showModal(); } catch { d.setAttribute('open', ''); } } else d.setAttribute('open', '');
    mini?.classList.add('hebt');
    this.ctx.meldungenPlatz?.();
    (d.querySelector('[data-p="play"]') || d.querySelector('h2'))?.focus?.({ preventScroll: true });
    const ende = () => d.classList.remove('fliegt');
    const { flaeche, gross, rest } = this._teile(d);
    if (!kannAnimieren(d)) { ende(); return; }
    const rot = reduziert();
    const lang = tokenMs(d, '--dauer-feder');
    const dauer = tokenMs(d, rot ? '--dauer-kurz' : '--dauer-feder');
    const laufende = [];
    if (rot) { // nur Überblenden, kein Flug
      laufende.push(animiere(d, [{ opacity: 0 }, { opacity: 1 }], { duration: dauer, easing: kurve(d, '--kurve') }));
    } else {
      const schmal = (window.innerWidth || 0) < 700;
      // die Vollansicht gleitet unter dem Cover herauf (am Handy um die ganze Höhe, am Computer nur 32 px mit Überblenden)
      laufende.push(animiere(flaeche, schmal ? [{ transform: 'translateY(100%)' }, { transform: 'none' }] : [{ transform: 'translateY(32px)', opacity: 0 }, { transform: 'none', opacity: 1 }],
        { duration: lang, easing: kurve(d, '--feder') }));
      // Titel und Steuerung blenden mit 140 ms Verzögerung ein (14 px Weg)
      for (const x of rest) laufende.push(animiere(x, [{ opacity: 0, transform: 'translateY(14px)' }, { opacity: 1, transform: 'none' }], { duration: tokenMs(d, '--dauer-lang'), delay: 140, fill: 'backwards', easing: kurve(d, '--kurve') }));
      // das Cover wandert vom Mini-Player an seinen Platz (FLIP, Ecken laufen mit)
      const von = this._flugVon;
      if (gross && von) {
        const nach = rechteck(gross.getBoundingClientRect());
        laufende.push(flipKlon(gross, von.rect, nach, { overlay: d, dauer: lang, easing: kurve(d, '--feder'), radiusVon: von.radius, radiusNach: radiusVon(gross) }));
      }
    }
    const echte = laufende.filter(Boolean);
    if (!echte.length) { ende(); return; }
    nachEnde(echte[0], Math.max(lang, dauer) + 350 + 100, ende);
  }

  /* Schließen: das große Cover fliegt zur Fläche des Mini-Covers, die Vollansicht gleitet hinunter (nach dem Wischen von der Stelle des Fingers aus). */
  _dialogZu(d, dy = 0) {
    d.dataset.closing = '1';
    d.classList.add('fliegt', 'zu');
    const mc = this._miniCover();
    const { flaeche, gross, rest } = this._teile(d);
    const fertig = () => this._dialogFertig(d);
    if (!kannAnimieren(d)) { fertig(); return; }
    const rot = reduziert();
    const lang = tokenMs(d, '--dauer-feder');
    const kurz = tokenMs(d, rot ? '--dauer-kurz' : '--dauer-mittel');
    const laufende = [];
    if (rot) {
      laufende.push(animiere(d, [{ opacity: 1 }, { opacity: 0 }], { duration: kurz, easing: kurve(d, '--kurve'), fill: 'forwards' }));
    } else {
      const h = d.offsetHeight || window.innerHeight || 600;
      const schmal = (window.innerWidth || 0) < 700;
      d.style.setProperty('--dy', '0px');
      const ab = dy > 0 ? `translateY(${dy}px)` : 'none';
      laufende.push(animiere(flaeche, schmal ? [{ transform: ab }, { transform: `translateY(${h}px)` }] : [{ transform: ab, opacity: 1 }, { transform: 'translateY(32px)', opacity: 0 }],
        { duration: dy > 0 ? lang : kurz, easing: kurve(d, dy > 0 ? '--feder' : '--kurve-aus'), fill: 'forwards' }));
      for (const x of rest) laufende.push(animiere(x, [{ opacity: 1, transform: ab }, { opacity: 0, transform: dy > 0 ? `translateY(${h}px)` : 'translateY(14px)' }], { duration: dy > 0 ? lang : kurz, easing: kurve(d, dy > 0 ? '--feder' : '--kurve-aus'), fill: 'forwards' }));
      if (gross && mc) {
        const nach = rechteck(mc.getBoundingClientRect());
        const jetzt = rechteck(gross.getBoundingClientRect()); // nach dem Wischen: dort, wo der Finger das Cover gerade hingezogen hat
        // der Klon liegt in der Vollansicht (oberste Schicht) und bleibt bis `_dialogFertig` stehen: erst dann ist das Mini-Cover wieder da
        const an = flipKlon(gross, jetzt, nach, { overlay: d, auto: false, dauer: lang, easing: kurve(d, '--feder'), radiusVon: radiusVon(gross), radiusNach: radiusVon(mc) });
        laufende.push(an);
        this._flugAn = an;
      }
    }
    const echte = laufende.filter(Boolean);
    if (!echte.length) { fertig(); return; }
    nachEnde(this._flugAn && !rot ? this._flugAn : echte[0], lang + 100, fertig);
  }

  _dialogFertig(d) {
    if (!this.offen) return;
    const flug = this._flugAn;
    this._flugAn = null;
    this._mini()?.classList.remove('hebt'); // das Mini-Cover ist da, im selben Bild verschwindet der Klon
    try { flug?.aufraeumen?.(); } catch { /* schon weg */ }
    try { flug?.cancel?.(); } catch { /* schon beendet */ }
    for (const x of d.querySelectorAll('.pin > *, .p-flaeche')) { try { x.getAnimations?.().forEach((a) => a.cancel()); } catch { /* ohne */ } }
    this._schliessend = true;
    try { if (typeof d.close === 'function') d.close(); else d.removeAttribute('open'); } catch { d.removeAttribute('open'); }
    d.removeAttribute('open');
    this._schliessend = false;
    this.offen = false;
    this.schliesst = false;
    this._mini()?.classList.remove('hebt');
    this.ctx.meldungenPlatz?.(true);
    this.ctx.neuZeichnen();
    this._fokus('.mini .mopen');
  }

  /* Der Browser hat den Dialog von selbst geschlossen (nicht über uns): sauber aufräumen. */
  _dialogClose() {
    if (this._schliessend || !this.offen) return;
    this.offen = false;
    this.schliesst = false;
    this._mini()?.classList.remove('hebt');
    this.ctx.meldungenPlatz?.(true);
    this.ctx.neuZeichnen();
  }

  /* ---- Wischen nach unten: die Vollansicht folgt dem Finger, bei mehr als 25 % der Höhe oder schneller Bewegung schließt sie (von dort aus),
   *      sonst federt sie zurück. Mindestens 70 px (5.12). Nicht vom Zeitregler und nicht vom Entsperr-Knopf. */
  _ziehDown(e) {
    if ((e.button ?? 0) > 0 || this.gesperrt || this.schliesst) return;
    if (e.target?.closest?.('input[type="range"], [data-p="unlock"]')) return;
    this._zy = { y: e.clientY, x: e.clientX, id: e.pointerId, cap: false, dy: 0, ly: e.clientY, lt: e.timeStamp, v: 0 };
  }

  _ziehMove(e) {
    const z = this._zy;
    if (!z || e.pointerId !== z.id) return;
    const d = e.currentTarget;
    const ddy = e.clientY - z.y;
    const ddx = e.clientX - z.x;
    if (!z.cap) {
      if (ddy > 8 && ddy > Math.abs(ddx)) { z.cap = true; try { d.setPointerCapture(z.id); } catch { /* ohne */ } } else return;
    }
    const dt = e.timeStamp - z.lt;
    if (dt > 0) z.v = (e.clientY - z.ly) / dt;
    z.ly = e.clientY; z.lt = e.timeStamp;
    z.dy = Math.max(0, ddy);
    d.classList.add('zieht');
    d.style.setProperty('--dy', `${z.dy}px`);
    d.style.setProperty('--bd', String(Math.max(0, 1 - z.dy / (d.offsetHeight || 1))));
  }

  _ziehEnde(e) {
    const z = this._zy;
    if (!z || e.pointerId !== z.id) return;
    this._zy = null;
    if (!z.cap) return;
    const d = e.currentTarget;
    try { d.releasePointerCapture(z.id); } catch { /* ohne */ }
    this._gewischtAm = Date.now();
    d.classList.remove('zieht');
    const h = d.offsetHeight || 1;
    if (z.dy >= SCHWELLE_ZU && (z.dy > h * 0.25 || z.v > 0.3)) { d.style.removeProperty('--bd'); this.schliessen('wischen', { dy: z.dy }); return; }
    this._zurueckFedern(d, z.dy);
  }

  _zurueckFedern(d, dy) {
    const { flaeche, gross, rest } = this._teile(d);
    d.style.removeProperty('--dy');
    d.style.removeProperty('--bd');
    if (reduziert() || dy <= 0) return;
    const o = { duration: tokenMs(d, '--dauer-feder'), easing: kurve(d, '--feder') };
    for (const x of [flaeche, ...rest]) animiere(x, [{ transform: `translateY(${dy}px)` }, { transform: 'none' }], o);
    animiere(gross, [{ translate: `0 ${dy}px` }, { translate: '0 0' }], o);
  }

  /* ---- Mini-Player: federt von unten herein, wenn zum ersten Mal etwas spielt; das Cover wechselt mit Kreuzblende */
  miniEinblenden() {
    const m = this._mini();
    if (!m) return;
    const rot = reduziert();
    animiere(m, rot ? [{ opacity: 0 }, { opacity: 1 }] : [{ transform: 'translateY(100%)', opacity: 0 }, { transform: 'none', opacity: 1 }],
      { duration: tokenMs(m, rot ? '--dauer-kurz' : '--dauer-feder'), easing: kurve(m, rot ? '--kurve' : '--feder') });
  }

  /* Vor dem Zeichnen: wechselt der Titel der Leiste, merkt sich die Seite eine Kopie des alten Covers (Kreuzblende, nichts blinkt). */
  vorZeichnen() {
    const key = this.s ? `${this.s.serie.id}|${this.s.i}` : null;
    if (key === this._miniKey) return;
    const alt = this._miniCover();
    this._miniAltKlon = alt && this._miniKey !== null && key !== null ? { klon: alt.cloneNode(true) } : null;
  }

  _miniWechsel() {
    const key = this.s ? `${this.s.serie.id}|${this.s.i}` : null;
    if (key === this._miniKey) return;
    const alt = this._miniAltKlon;
    this._miniKey = key;
    this._miniAltKlon = null;
    const nc = this._miniCover();
    const tx = this.ctx.wurzel?.querySelector?.('.mini .mopen .grow');
    if (!alt || !nc || !kannAnimieren(nc)) return;
    const rot = reduziert();
    const host = nc.parentElement;
    try {
      const k = alt.klon;
      const r = nc.getBoundingClientRect();
      Object.assign(k.style, { position: 'absolute', margin: '0', zIndex: '3', pointerEvents: 'none', left: `${nc.offsetLeft}px`, top: `${nc.offsetTop}px`, width: `${r.width || nc.offsetWidth}px`, height: `${r.height || nc.offsetHeight}px` });
      host.style.position = host.style.position || 'relative';
      host.appendChild(k);
      const an = animiere(k, [{ opacity: 1 }, { opacity: 0 }], { duration: tokenMs(nc, '--dauer-mittel'), easing: 'ease-out' });
      nachEnde(an, tokenMs(nc, '--dauer-mittel') + 100, () => k.remove());
      if (!an) k.remove();
      if (!rot) {
        animiere(nc, [{ transform: 'scale(0.9)' }, { transform: 'none' }], { duration: tokenMs(nc, '--dauer-feder'), easing: kurve(nc, '--feder') });
        if (tx) animiere(tx, [{ opacity: 0, transform: 'translateY(6px)' }, { opacity: 1, transform: 'none' }], { duration: tokenMs(nc, '--dauer-lang'), easing: kurve(nc, '--kurve') });
      } else if (tx) animiere(tx, [{ opacity: 0 }, { opacity: 1 }], { duration: tokenMs(nc, '--dauer-kurz') });
    } catch { /* ohne Kreuzblende */ }
  }
}

/* ------------------------------------------------------------------ Stil */

export const spielerStil = () => css`
  /* Leiste (Mini-Player, Prototyp .mbar/.mrow/.mopen/.mplay); der Platz selbst (.mini) steht in tobibox-app.js */
  .mini { touch-action: pan-x; user-select: none; -webkit-user-select: none; }
  .mini.hebt .cover { visibility: hidden; }
  .mbar { height: 3px; background: var(--divider); }
  .mbar i { display: block; height: 100%; width: 0; background: var(--primary-ink); }
  .mrow { display: flex; align-items: center; gap: 8px; padding: 4px max(16px, env(safe-area-inset-right, 0px)) 4px max(16px, env(safe-area-inset-left, 0px)); max-width: 1180px; margin: 0 auto; }
  .mopen { flex: 1; min-width: 0; display: flex; align-items: center; gap: 12px; border: 0; background: none; text-align: left; min-height: 56px; padding: 0; color: inherit; }
  .mopen .cover { position: relative; }
  .mopen .grow { min-width: 0; display: grid; }
  .mopen .mt { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mopen .ms { font-size: 14px; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mplay { width: 48px; height: 48px; border-radius: 24px; border: 1px solid var(--primary-ink); background: var(--primary); color: var(--on-primary); display: grid; place-items: center; flex: none; padding: 0; }
  .mplay svg { width: 28px; height: 28px; fill: currentColor; }

  /* Vollansicht: am Handy ganze Fläche, ab 700 px ein Blatt. Der Dialog selbst bleibt unbewegt; Fläche, Cover, Titel und Steuerung bewegen sich einzeln (FLIP). */
  dialog.player { padding: 0; border: 0; width: 100%; max-width: 480px; max-height: 96dvh; background: transparent; color: var(--text); border-radius: var(--r-big); overflow: auto; overscroll-behavior: contain; }
  dialog.player.fliegt { overflow: visible; }
  dialog.player::backdrop { background: var(--scrim, rgba(0, 0, 0, 0.5)); opacity: var(--bd, 1); }
  dialog.player[open]::backdrop { animation: bd-ein var(--dauer-mittel) var(--kurve); }
  dialog.player.zu::backdrop { opacity: 0; transition: opacity var(--dauer-mittel) var(--kurve-aus); }
  dialog.player.zieht::backdrop { transition: none; }
  @media (max-width: 699px) { dialog.player { max-width: none; height: 100dvh; max-height: 100dvh; margin: 0; border-radius: 0; } }
  .p-wrap { position: relative; border-radius: inherit; }
  .p-flaeche { position: absolute; inset: 0; background: var(--card); border-radius: inherit; box-shadow: 0 8px 32px var(--shadow); transform: translateY(var(--dy, 0px)); }
  @media (max-width: 699px) { .p-flaeche { box-shadow: 0 8px 32px var(--shadow), 0 96px 0 0 var(--card); } }
  .pin { position: relative; padding: 8px max(16px, env(safe-area-inset-right, 0px)) max(16px, env(safe-area-inset-bottom, 0px)) max(16px, env(safe-area-inset-left, 0px)); display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; justify-items: center; touch-action: pan-x; }
  @media (max-width: 699px) { .pin { min-height: 100dvh; align-content: center; } }
  @media (max-height: 560px) { .pin { touch-action: auto; } }
  .pin > :not(.cover) { transform: translateY(var(--dy, 0px)); }
  .pin > .cover { translate: 0 var(--dy, 0px); }
  .phead { width: 100%; display: flex; align-items: center; justify-content: space-between; }
  .iconbtn.plain { border: 0; background: none; color: var(--text); }
  .iconbtn.plain:disabled, .pslider:disabled { opacity: 0.35; }
  dialog.player .cover.pxl { width: min(62vw, 280px, 36dvh); font-size: 96px; border-radius: var(--r-card); }
  .ptitle { text-align: center; width: 100%; }
  .ptitle h2 { margin: 4px 0 2px; font-size: 22px; overflow-wrap: anywhere; outline: none; }
  .pslider { width: 100%; min-height: 44px; accent-color: var(--primary); margin: 0; }
  .ptimes { width: 100%; display: flex; justify-content: space-between; font-size: 14px; color: var(--text2); margin-top: -8px; font-variant-numeric: tabular-nums; }
  .pctl { display: flex; align-items: center; justify-content: center; gap: 4px; width: 100%; }
  .pbtn { width: 52px; height: 52px; border-radius: 26px; border: 0; background: none; display: grid; place-items: center; color: var(--text); padding: 0; }
  .pbtn svg { width: 32px; height: 32px; fill: currentColor; }
  .pbtn.main { width: 72px; height: 72px; border-radius: 36px; background: var(--primary); color: var(--on-primary); border: 1px solid var(--primary-ink); }
  .pbtn.main svg { width: 40px; height: 40px; }
  .pbtn:disabled { opacity: 0.35; }
  .speed { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; width: 100%; }
  .pnote { margin: 0; font-size: 13px; text-align: center; min-height: 18px; line-height: 18px; } /* AM15: der Platz steht, auch wenn der Satz noch fehlt */
  .pkap { height: 20px; line-height: 20px; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } /* A8d, AM15: immer eine Zeile fester Höhe */
  .speed.mitkap { flex-wrap: nowrap; }
  .speed.mitkap .btn { flex: 0 0 auto; }
  .speed.mitkap .unlock { flex: 1 1 0; min-width: 0; }
  /* Blatt „Kapitel“ (A8d): Zeilen als Knöpfe, mindestens 56 px; die markierte ist getönt */
  .kap-liste { display: grid; gap: 0; }
  .kap-zeile { width: 100%; min-height: 56px; display: flex; align-items: center; gap: 12px; padding: 8px 4px; border: 0; border-top: 1px solid var(--divider); background: none; color: inherit; text-align: left; font: inherit; }
  .kap-zeile:first-child { border-top: 0; }
  .kap-zeile[aria-current="true"] { background: var(--primary-soft); border-radius: 12px; }
  .kap-nr { width: 28px; flex: none; display: grid; place-items: center; color: var(--text2); font-weight: 500; }
  .kap-nr svg { fill: var(--ok); }
  .kap-txt { flex: 1; min-width: 0; display: grid; gap: 1px; }
  .kap-t { overflow-wrap: anywhere; }
  .kap-ab { font-size: 14px; font-variant-numeric: tabular-nums; }
  .kap-zu { flex: none; font-size: 14px; color: var(--text2); }
  .kap-zeile[aria-current="true"] .kap-zu { color: var(--primary-ink); font-weight: 500; }
  .grip { width: 44px; height: 5px; border-radius: 3px; background: var(--line); margin: 0 auto 4px; }
  /* Sperre (X14): Entsperren nur durch Halten, der Füllbalken zeigt den Fortschritt */
  .unlock { position: relative; overflow: hidden; min-height: 64px; flex: 1 1 100%; max-width: 360px; user-select: none; -webkit-user-select: none; -webkit-touch-callout: none; touch-action: none; }
  .unlock > :not(.ring) { position: relative; }
  .unlock svg { fill: currentColor; }
  .unlock .ring { position: absolute; left: 0; top: 0; bottom: 0; width: 0; background: var(--on-primary); opacity: 0.22; pointer-events: none; }
  .unlock.holding .ring { width: 100%; transition: width 2s linear; }
  .speed .btn svg { fill: currentColor; }
  /* Blatt „Wiedergabe“ */
  .p-h3 { font-size: 17px; font-weight: 500; margin: 8px 0; }
  .p-stack { display: grid; gap: 8px; }
  .p-opt { width: 100%; min-height: 48px; border: 1px solid var(--line); border-radius: var(--r-card); background: var(--card); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; text-align: left; }
  .p-opt[aria-checked="true"] { background: var(--primary-soft); border-color: var(--primary-ink); }
  .p-opt svg { width: 22px; height: 22px; fill: var(--primary-ink); }
  /* Reihe „Am Handy weiterhören“ (Start, A7c): Kachel mit Balken und Abspielknopf auf dem Cover */
  .reihenfeld .wh { flex: 0 0 var(--kw); position: relative; scroll-snap-align: start; min-width: 0; }
  .wh .tile { width: 100%; }
  .wh .tile .pbar { margin: 0; }
  .playov { position: absolute; right: 10px; top: calc(var(--kw, 120px) - 54px); width: 44px; height: 44px; border-radius: 22px; border: 1px solid var(--primary-ink); background: var(--primary); color: var(--on-primary); display: grid; place-items: center; box-shadow: 0 1px 4px var(--shadow); padding: 0; }
  .playov svg { width: 24px; height: 24px; fill: currentColor; }
  /* Knopf „Reinhören“ auf der Serienseite (Design 5.3): Hauptknopf 56 px */
  .btn.xl { min-height: 56px; font-size: 17px; border-radius: 28px; }
  .btn.xl svg { width: 24px; height: 24px; fill: currentColor; }
  @media (prefers-reduced-motion: reduce) { .unlock.holding .ring { transition: none; } }
`;

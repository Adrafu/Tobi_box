/* Hochladen: reine Funktionen und die Warteschlange (Design 5.6, 5.6a, 7.3; Vertrag W 5 und 14.4; Paket A11a).
 *
 * Dieses Modul kennt kein DOM-Template. Die Seite (seiten/hinzufuegen.js) hält je Hochladen einen „Auftrag“ (so heißt hier der Eintrag unter
 * „Zuletzt hinzugefügt“) und gibt ihn der Warteschlange `Hochlader`:
 *
 *   auftrag = { id, wunsch, dateien: [datei], abgebrochen, gestartet, … }
 *   datei   = { id (= upload_id), datei (File), name, groesse, wunschName, zustand, gesendet, code, hinweis, eingangName, … }
 *   zustand = 'wartet' | 'sendet' | 'pruefe' | 'fertig' | 'fehler' | 'verbindung' | 'unterbrochen' | 'abgebrochen'
 *   wunsch  = { ziel, art, name, serie_id, gruppe, gruppe_anzahl } oder null (ohne Wunsch: nur upload_id, serie_id, gruppe)
 *
 * Senden: `POST /api/tobibox/upload`, `multipart/form-data`, eine Datei je Anfrage, Felder vor `datei` in der Reihenfolge des Vertrags.
 * Fortschritt: `XMLHttpRequest` (`upload.onprogress`), denn `fetch` meldet beim Hochladen keinen Fortschritt und `hass.fetchWithAuth`
 * baut auf `fetch`. Die Anmeldung wie im alten Panel und im Vertrag 5.1: Header `Authorization: Bearer <Zugriffstoken>` aus `hass.auth`,
 * vorher mit `hass.auth.refreshAccessToken()` erneuert, wenn es abgelaufen ist (ein laufender Upload bricht danach nicht ab).
 *
 * Reihenfolge: ein Auftrag sendet seine Dateien nacheinander („Datei 2 von 3“); mehrere Aufträge laufen höchstens `upload_parallel` zugleich
 * (aus `hello.grenzen`, Vorgabe 2), die übrigen „warten“. Ein 429 `zu_viele_uploads` ist kein Fehler: die Datei wartet und wird wieder gesendet.
 * Solange etwas läuft oder wartet, hält die Seite einen Wake Lock (`navigator.wakeLock.request('screen')`, immer in `try`).
 */
import { fehlerText } from '../texte.js';

export const MIB = 1048576;
export const GIB = 1073741824;
export const GRUPPE_MAX = 200; // `gruppe_anzahl`: 2 bis 200 (Vertrag 14.4, `GRUPPE_ANZAHL_MAX`)
export const UPLOAD_URL = '/api/tobibox/upload';
const HTTP_CODE = { 401: 'unauthorized', 403: 'unauthorized', 413: 'datei_zu_gross', 415: 'format_nicht_erlaubt', 429: 'zu_viele_uploads', 503: 'medien_nicht_erreichbar', 507: 'kein_speicher' };
export const ZUSTAENDE_LAUFEN = ['wartet', 'sendet', 'pruefe'];
export const ZUSTAENDE_NEU_WAEHLEN = ['verbindung', 'unterbrochen', 'abgebrochen']; // diese Datei kann man noch einmal wählen
// Dateien, die in einem Ordner liegen und keine Audiodateien sind: sie werden still übergangen (Design 5.6: „nichts erklären“)
const UEBERGEHEN = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic', 'txt', 'nfo', 'cue', 'log', 'pdf', 'm3u', 'm3u8', 'url', 'ini', 'db', 'xml', 'json', 'md', 'sfv', 'md5', 'accurip']);

/* ------------------------------------------------------------------ reine Funktionen */

export function neueId() {
  const c = globalThis.crypto;
  if (c?.randomUUID) return c.randomUUID();
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}${Math.random().toString(16).slice(2, 10)}`;
}

export const endung = (name) => { const m = /\.([^./\\]+)$/.exec(String(name ?? '')); return m ? m[1].toLowerCase() : ''; };
export const ohneEndung = (name) => String(name ?? '').replace(/\.[^./\\]+$/, '');

/* „2 GB“, „500 MB“, „1,5 GB“: die Zahl für den Text von `datei_zu_gross` (aus `hello.grenzen.upload_max_bytes`; das Design sagt GB für 2 GiB). */
export function grenzeText(bytes) {
  const n = Number(bytes);
  if (!Number.isFinite(n) || n <= 0) return '2 GB';
  const zahl = (x) => String(Math.round(x * 10) / 10).replace('.', ',');
  return n >= GIB ? `${zahl(n / GIB)} GB` : `${zahl(Math.max(1, n / MIB))} MB`;
}

/* Natürliche Reihenfolge nach Dateiname („2 …“ vor „10 …“); die Auswahl des Systems bleibt sonst, wie sie ist. */
export function sortiereNatuerlich(dateien) {
  const vgl = new Intl.Collator('de', { numeric: true, sensitivity: 'base' });
  return [...dateien].sort((a, b) => vgl.compare(a.name, b.name));
}

/* Prüft die Auswahl vor dem Hochladen:
 *   gut      Dateien, die hochgeladen werden
 *   fehler   [{ name, groesse, code }] mit `datei_zu_gross` (mehr als `upload_max_bytes`) oder `format_nicht_erlaubt` (Endung nicht in
 *            `hello.grenzen.endungen`; fehlt die Liste, entscheidet das Backend mit 415)
 *   uebergangen  Anzahl der still übergangenen Dateien (nur bei `ordner`: Bilder, Textdateien, versteckte Dateien)
 * Eine Gruppe soll vollständig ankommen: darum wird eine Datei, die nicht geht, schon vorab gemeldet, nicht erst nach 30 Minuten. */
export function pruefeDateien(dateien, grenzen = {}, { ordner = false } = {}) {
  const max = Number(grenzen.upload_max_bytes) > 0 ? Number(grenzen.upload_max_bytes) : null;
  const erlaubt = Array.isArray(grenzen.endungen) && grenzen.endungen.length ? new Set(grenzen.endungen.map((x) => String(x).replace(/^\./, '').toLowerCase())) : null;
  const aus = { gut: [], fehler: [], uebergangen: 0 };
  for (const d of dateien) {
    const e = endung(d.name);
    if (String(d.name).startsWith('.') || (ordner && UEBERGEHEN.has(e))) { aus.uebergangen += 1; continue; }
    if (erlaubt && !erlaubt.has(e)) { aus.fehler.push({ name: d.name, groesse: d.size, code: 'format_nicht_erlaubt' }); continue; }
    if (max && d.size > max) { aus.fehler.push({ name: d.name, groesse: d.size, code: 'datei_zu_gross' }); continue; }
    aus.gut.push(d);
  }
  return aus;
}

/* Name einer Datei ohne Endung, ohne führende Nummer: „01 Der Hafen.mp3“ → „Der Hafen“ (nie leer). */
export function titelAusDateiname(name) {
  const roh = ohneEndung(name).replace(/_/g, ' ').trim();
  const t = roh.replace(/^\s*(?:(?:track|titel|kapitel|folge|teil|lied)\s*)?\d+\s*(?:[-–.)\]:]\s*|\s+)/i, '').trim();
  return t || roh || String(name ?? '');
}

/* Vorschlag für den Namen eines neuen Eintrags (Design 7.3 Karte a): Album der ersten Datei, sonst gemeinsamer Anfang der Dateinamen,
 * sonst der Name der ersten Datei. */
export function nameVorschlag(dateien, angaben = []) {
  const album = (angaben[0]?.album || '').trim();
  if (album) return album;
  const namen = dateien.map((d) => ohneEndung(d.name).replace(/_/g, ' ').trim());
  if (namen.length > 1) {
    let p = namen[0];
    for (const n of namen.slice(1)) { let i = 0; while (i < p.length && i < n.length && p[i].toLowerCase() === n[i].toLowerCase()) i += 1; p = p.slice(0, i); }
    p = p.replace(/[\s\-–._,(\[:]*\d*[\s\-–._,(\[:]*$/, '').trim();
    if (p.length >= 3) return p;
  }
  return dateien[0] ? titelAusDateiname(dateien[0].name) : '';
}

/* Art-Vorschlag aus den Angaben (Genre) und der Endung: `m4b` ist ein Hörbuch. Sonst Hörspiel. */
export function artVorschlag(dateien, angaben = []) {
  const genre = angaben.map((a) => a?.genre || '').join(' ');
  if (dateien.some((d) => endung(d.name) === 'm4b') || /h(ö|oe)rbuch|audio ?book|spoken/i.test(genre)) return 'hoerbuch';
  if (/h(ö|oe)rspiel|radio ?play/i.test(genre)) return 'hoerspiel';
  if (/geschichte|story|stories|märchen/i.test(genre)) return 'geschichte';
  if (genre.trim()) return 'musik';
  return 'hoerspiel';
}

/* ---- Angaben in der Datei lesen (ID3v2 am Anfang einer MP3; andere Formate: nichts, der Name kommt aus dem Dateinamen) */

const alsPuffer = (blob) => (typeof blob.arrayBuffer === 'function' ? blob.arrayBuffer() : new Promise((ok, nein) => {
  const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = () => nein(r.error); r.readAsArrayBuffer(blob);
}));

function id3Text(b) {
  if (!b.length) return '';
  const k = b[0]; const rest = b.subarray(1);
  const dek = (label, x) => { try { return new TextDecoder(label).decode(x); } catch { return ''; } };
  let t;
  if (k === 1) t = rest[0] === 0xff && rest[1] === 0xfe ? dek('utf-16le', rest.subarray(2)) : rest[0] === 0xfe && rest[1] === 0xff ? dek('utf-16be', rest.subarray(2)) : dek('utf-16le', rest);
  else if (k === 2) t = dek('utf-16be', rest);
  else if (k === 3) t = dek('utf-8', rest);
  else t = dek('iso-8859-1', rest);
  return t.replace(/\u0000.*$/s, '').trim();
}

/* Liefert { album, titel, interpret, genre } oder null. Liest höchstens die ersten 128 KiB; nie ein Fehler nach außen. */
export async function liesAngaben(datei) {
  try {
    if (endung(datei.name) !== 'mp3') return null;
    const b = new Uint8Array(await alsPuffer(datei.slice(0, 131072)));
    if (b.length < 10 || b[0] !== 0x49 || b[1] !== 0x44 || b[2] !== 0x33) return null;
    const ver = b[3];
    const sync = (o) => (b[o] << 21) | (b[o + 1] << 14) | (b[o + 2] << 7) | b[o + 3];
    const ende = Math.min(b.length, 10 + sync(6));
    const a = { album: '', titel: '', interpret: '', genre: '' };
    const feld = { TALB: 'album', TAL: 'album', TIT2: 'titel', TT2: 'titel', TPE1: 'interpret', TP1: 'interpret', TCON: 'genre', TCO: 'genre' };
    const kopf = ver === 2 ? 6 : 10;
    for (let o = 10; o + kopf < ende;) {
      const id = String.fromCharCode(...b.subarray(o, o + (ver === 2 ? 3 : 4)));
      if (!/^[A-Z0-9]{3,4}$/.test(id)) break;
      const n = ver === 2 ? (b[o + 3] << 16) | (b[o + 4] << 8) | b[o + 5] : ver === 4 ? sync(o + 4) : ((b[o + 4] << 24) | (b[o + 5] << 16) | (b[o + 6] << 8) | b[o + 7]) >>> 0;
      if (n <= 0 || o + kopf + n > b.length) break;
      if (feld[id] && !a[feld[id]]) a[feld[id]] = id3Text(b.subarray(o + kopf, o + kopf + n)).replace(/^\((\d+)\)/, '');
      o += kopf + n;
    }
    return a.album || a.titel || a.interpret || a.genre ? a : null;
  } catch { return null; }
}

/* ---- Drag and drop: Dateien und Ordner (Chrome, Safari: `webkitGetAsEntry`), sonst die Dateiliste */
export async function dateienAusDrop(dt) {
  if (!dt) return [];
  const eintraege = Array.from(dt.items || []).map((i) => (typeof i.webkitGetAsEntry === 'function' ? i.webkitGetAsEntry() : null));
  if (!eintraege.length || eintraege.some((x) => !x)) return Array.from(dt.files || []);
  const aus = [];
  const lies = (leser) => new Promise((ok, nein) => leser.readEntries(ok, nein));
  const gehe = async (e) => {
    if (e.isFile) { const f = await new Promise((ok, nein) => e.file(ok, nein)); aus.push(f); return; }
    if (!e.isDirectory) return;
    const leser = e.createReader();
    for (;;) { const teil = await lies(leser); if (!teil.length) break; for (const k of teil) await gehe(k); }
  };
  try { for (const e of eintraege) await gehe(e); } catch { return Array.from(dt.files || []); }
  return aus;
}

/* ---- Fortschritt */

/* Anteil 0 bis 100 über alle Dateien (fertige zählen voll). */
export function gesamtProzent(a) {
  let summe = 0; let gesendet = 0;
  for (const d of a.dateien) {
    const g = Math.max(0, d.groesse || 0);
    summe += g;
    gesendet += d.zustand === 'fertig' || d.zustand === 'pruefe' ? g : Math.min(g, Math.max(0, d.gesendet || 0));
  }
  if (!summe) return a.dateien.length && a.dateien.every((d) => d.zustand === 'fertig') ? 100 : 0;
  return Math.max(0, Math.min(100, Math.floor((gesendet / summe) * 100)));
}

export const dateiProzent = (d) => (d.zustand === 'fertig' || d.zustand === 'pruefe' ? 100 : d.groesse > 0 ? Math.max(0, Math.min(100, Math.floor(((d.gesendet || 0) / d.groesse) * 100))) : 0);

/* Die Datei, die gerade dran ist: { nr (ab 1), anzahl, datei }. */
export function aktuelleDatei(a) {
  const i = a.dateien.findIndex((d) => d.zustand === 'sendet' || d.zustand === 'pruefe');
  const j = i >= 0 ? i : Math.max(0, a.dateien.findIndex((d) => d.zustand === 'wartet'));
  return { nr: j + 1, anzahl: a.dateien.length, datei: a.dateien[j] };
}

/* Wo steht ein Auftrag? 'wartet' (noch nicht dran) | 'hochladen' | 'abgebrochen' | 'sortieren' (alles hochgeladen; `a.eingang` sagt mehr) |
 * 'fehler' (mindestens eine Datei geht nicht) | 'fehlt' (eine Datei muss noch einmal gewählt werden). */
export function phaseVon(a) {
  const z = a.dateien.map((d) => d.zustand);
  if (z.some((x) => ZUSTAENDE_LAUFEN.includes(x))) return a.gestartet ? 'hochladen' : 'wartet';
  if (a.abgebrochen) return 'abgebrochen';
  if (!z.length) return a.abgelehnt?.length ? 'fehler' : 'sortieren';
  if (z.every((x) => x === 'fertig')) return 'sortieren';
  if (z.some((x) => x === 'fehler')) return 'fehler';
  return 'fehlt';
}

/* Text zu einem Fehler einer Datei (Vertrag 7 und Design 6.1). */
export function dateiFehlerText(d, { grenzen = {}, admin = false } = {}) {
  if (d.zustand === 'unterbrochen') return null; // steht in HINZU.unterbrochen
  const code = d.zustand === 'verbindung' ? 'verbindung_abgebrochen' : d.code || 'unknown_error';
  return fehlerText(code, { grenze: grenzeText(grenzen.upload_max_bytes), admin });
}

/* ------------------------------------------------------------------ Warteschlange */

const bei = (ms) => new Promise((r) => setTimeout(r, ms));

export class Hochlader {
  /* ctx: hass, grenzen(), neuesXhr(); `aenderung()` meldet jede Änderung (gedrosselt), `fertig(auftrag)` einen Auftrag, dessen Dateien alle durch sind. */
  constructor(ctx, { aenderung = () => {}, fertig = () => {}, drosselMs = 200, wiederholenMs = 3000, rueckkehrMs = 4000 } = {}) {
    this.ctx = ctx;
    this.aenderung = aenderung;
    this.fertig = fertig;
    this.drosselMs = drosselMs;
    this.wiederholenMs = wiederholenMs; // Pause vor dem nächsten Versuch nach 429 (`zu_viele_uploads`)
    this.rueckkehrMs = rueckkehrMs; // so lange darf nach dem Zurückkehren ein Upload ohne Fortschritt bleiben, dann „Unterbrochen“
    this.auftraege = [];
    this._laeufe = 0;
    this._wl = null;
    this._sichtbar = () => this._beiSichtbar();
  }

  get parallel() { const n = Number(this.ctx.grenzen?.().upload_parallel); return n >= 1 ? Math.floor(n) : 2; }
  get aktiv() { return this.auftraege.some((a) => !a.erledigt); }

  /* ---- Auftrag einreihen, abbrechen, Datei noch einmal wählen */
  einreihen(auftrag) {
    auftrag.erledigt = false; auftrag.laeuft = false; auftrag.gestartet = false; auftrag.abgebrochen = false;
    this.auftraege.push(auftrag);
    this._sperren();
    this._pumpe();
    this._melde(true);
  }

  abbrechen(auftrag) {
    if (auftrag.abgebrochen || auftrag.erledigt) return;
    auftrag.abgebrochen = true;
    for (const d of auftrag.dateien) {
      if (d.zustand === 'wartet') d.zustand = 'abgebrochen';
      else if (d.zustand === 'sendet' || d.zustand === 'pruefe') { d.vomBenutzer = true; try { d.xhr?.abort(); } catch { /* egal */ } }
    }
    if (!auftrag.laeuft) this._ende(auftrag);
    this._melde(true);
  }

  /* Eine Datei noch einmal wählen („Fehlende Datei wählen“): ersetzt die Datei, die fehlt (gleicher Name zuerst), sonst kommt sie dazu. Gleiche
   * `gruppe` und `gruppe_anzahl` wie vorher. */
  nochEinmal(auftrag, datei) {
    const frei = auftrag.dateien.filter((d) => ZUSTAENDE_NEU_WAEHLEN.includes(d.zustand) || d.zustand === 'fehler');
    const slot = frei.find((d) => d.name === datei.name) || frei[0];
    const neu = { id: neueId(), datei, name: datei.name, groesse: datei.size, wunschName: slot?.wunschName ?? null, zustand: 'wartet', gesendet: 0, code: null, hinweis: null, eingangName: null };
    if (slot) auftrag.dateien[auftrag.dateien.indexOf(slot)] = neu; else auftrag.dateien.push(neu);
    auftrag.abgebrochen = false; auftrag.eingang = null;
    if (auftrag.erledigt) { auftrag.erledigt = false; this.auftraege.includes(auftrag) || this.auftraege.push(auftrag); }
    this._sperren();
    this._pumpe();
    this._melde(true);
  }

  /* ---- Ablauf */
  _pumpe() {
    for (const a of this.auftraege) {
      if (this._laeufe >= this.parallel) break;
      if (a.erledigt || a.laeuft || a.abgebrochen) continue;
      if (!a.dateien.some((d) => d.zustand === 'wartet')) continue;
      this._lauf(a);
    }
  }

  async _lauf(a) {
    a.laeuft = true; a.gestartet = true; this._laeufe += 1;
    try {
      for (const d of a.dateien) {
        if (d.zustand !== 'wartet') continue;
        if (a.abgebrochen) { d.zustand = 'abgebrochen'; continue; }
        await this._sende(a, d);
      }
    } finally {
      a.laeuft = false; this._laeufe -= 1;
      if (a.dateien.some((d) => d.zustand === 'wartet') && !a.abgebrochen) this._pumpe(); // eine Datei kam während des Laufs dazu
      else this._ende(a);
      this._pumpe();
    }
  }

  _ende(a) {
    if (a.erledigt) return;
    a.erledigt = true;
    for (const d of a.dateien) if (d.zustand === 'wartet') d.zustand = 'abgebrochen';
    if (!this.aktiv) this._entsperren();
    this._melde(true);
    try { this.fertig(a); } catch { /* die Seite darf die Warteschlange nicht stören */ }
  }

  async _token() {
    const au = this.ctx.hass?.auth;
    try { if (au?.expired && au.refreshAccessToken) await au.refreshAccessToken(); } catch { /* weiter mit dem alten Token */ }
    return au?.accessToken || au?.data?.access_token || '';
  }

  _formular(a, d) {
    const w = a.wunsch || {};
    const fd = new FormData();
    fd.append('upload_id', d.id);
    if (w.serie_id) fd.append('serie_id', w.serie_id);
    if (w.gruppe) fd.append('gruppe', w.gruppe);
    if (w.ziel) fd.append('ziel', w.ziel);
    if (w.art) fd.append('art', w.art);
    const name = d.wunschName || w.name;
    if (name) fd.append('name', name);
    if (w.gruppe_anzahl) fd.append('gruppe_anzahl', String(w.gruppe_anzahl));
    fd.append('datei', d.datei, d.name);
    return fd;
  }

  /* Eine Datei senden, bis sie durch ist, einen Fehler hat oder abgebrochen wurde. */
  async _sende(a, d) {
    let erneuert = false;
    for (let versuch = 0; versuch < 60; versuch += 1) {
      if (a.abgebrochen) { d.zustand = 'abgebrochen'; return; }
      d.zustand = 'sendet'; d.gesendet = 0; d.code = null; d.vomBenutzer = false; d.unterbrochen = false;
      this._melde(true);
      const r = await this._eine(a, d);
      if (r.abbruch) { d.zustand = d.unterbrochen ? 'unterbrochen' : 'abgebrochen'; this._melde(true); return; }
      if (r.netz) { d.zustand = d.unterbrochen ? 'unterbrochen' : 'verbindung'; this._melde(true); return; }
      const ok = r.status >= 200 && r.status < 300 && r.body && !r.body.fehler;
      if (ok) {
        Object.assign(d, { zustand: 'fertig', gesendet: d.groesse, eingangName: r.body.eingang_name ?? null, pruefung: r.body.pruefung ?? null, hinweis: r.body.hinweis ?? null, xhr: null, datei: null }); // die Datei wird nicht mehr gebraucht
        this._melde(true); return;
      }
      const code = r.body?.fehler?.code || HTTP_CODE[r.status] || 'unknown_error';
      if (code === 'unauthorized' && r.status === 401 && !erneuert) { erneuert = true; try { await this.ctx.hass?.auth?.refreshAccessToken?.(); } catch { /* weiter */ } continue; }
      if (code === 'zu_viele_uploads') { d.zustand = 'wartet'; this._melde(true); await bei(this.wiederholenMs); continue; } // kein Fehler: warten und noch einmal
      Object.assign(d, { zustand: 'fehler', code, xhr: null });
      this._melde(true); return;
    }
    Object.assign(d, { zustand: 'fehler', code: 'zu_viele_uploads', xhr: null });
    this._melde(true);
  }

  async _eine(a, d) {
    const token = await this._token();
    return new Promise((ok) => {
      const xhr = this.ctx.neuesXhr();
      d.xhr = xhr; d.letzterFortschritt = Date.now();
      xhr.open('POST', UPLOAD_URL);
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.upload.onprogress = (ev) => {
        const anteil = ev.lengthComputable && ev.total > 0 ? ev.loaded / ev.total : (d.groesse > 0 ? ev.loaded / d.groesse : 0);
        d.gesendet = Math.max(d.gesendet || 0, Math.min(d.groesse, Math.round(anteil * d.groesse)));
        d.letzterFortschritt = Date.now();
        this._melde(false);
      };
      xhr.upload.onload = () => { if (d.zustand === 'sendet') { d.zustand = 'pruefe'; d.gesendet = d.groesse; this._melde(true); } };
      xhr.onload = () => {
        let body = null;
        try { body = JSON.parse(xhr.responseText); } catch { /* keine Antwort im JSON-Format */ }
        ok({ status: xhr.status, body });
      };
      xhr.onerror = () => ok({ netz: true });
      xhr.ontimeout = () => ok({ netz: true });
      xhr.onabort = () => ok({ abbruch: true });
      try { xhr.send(this._formular(a, d)); } catch { ok({ netz: true }); }
    });
  }

  /* ---- Rückmeldung an die Seite (Fortschritt gedrosselt, Zustandswechsel sofort) */
  _melde(sofort) {
    if (sofort || !this.drosselMs) { clearTimeout(this._t); this._t = null; this.aenderung(); return; }
    if (this._t) return;
    this._t = setTimeout(() => { this._t = null; this.aenderung(); }, this.drosselMs);
  }

  /* ---- Bildschirm anlassen (Wake Lock) und Rückkehr in die Seite */
  async _sperren() {
    try { document.addEventListener('visibilitychange', this._sichtbar); } catch { /* ohne */ }
    if (this._wl || this._wlBittet) return;
    this._wlBittet = true;
    try {
      this._wl = await window.navigator.wakeLock.request('screen');
      this._wl?.addEventListener?.('release', () => { this._wl = null; });
      if (!this.aktiv) this._entsperren(); // es war inzwischen alles fertig
    } catch { this._wl = null; } finally { this._wlBittet = false; }
  }

  _entsperren() {
    try { document.removeEventListener('visibilitychange', this._sichtbar); } catch { /* ohne */ }
    const w = this._wl; this._wl = null;
    try { Promise.resolve(w?.release?.()).catch(() => {}); } catch { /* ohne */ }
  }

  /* Beim Zurückkehren (Bildschirm war gesperrt): Wake Lock neu holen; Dateien, die bei „wird hochgeladen“ stehen geblieben sind, werden
   * „Unterbrochen. Wähle die Datei noch einmal.“ (Design 7.3 Punkt 8). */
  _beiSichtbar() {
    if (document.visibilityState && document.visibilityState !== 'visible') return;
    if (this.aktiv) this._sperren();
    const seit = Date.now();
    setTimeout(() => {
      for (const a of this.auftraege) {
        for (const d of a.dateien) {
          if (d.zustand === 'sendet' && (d.letzterFortschritt || 0) <= seit) { d.unterbrochen = true; try { d.xhr?.abort(); } catch { /* egal */ } }
        }
      }
    }, this.rueckkehrMs);
  }
}

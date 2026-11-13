/* Tobi Box: Seite für Home Assistant (AP 3.2).
 *
 * Spricht ausschließlich nach Vertrag W (docs/protocol/ha-websocket-v1.md, Version 1):
 * Befehle über hass.connection.sendMessagePromise, Ereignisse über subscribeMessage,
 * Hochladen über POST /api/tobibox/upload (XMLHttpRequest, damit es Fortschritt gibt).
 * Die Seite wertet nur `code` aus; `message` dient bei unbekanntem Code als Text.
 * Namen werden nur als Text dargestellt (Lit maskiert selbst; es gibt kein rohes HTML).
 *
 * Seit AP 4.7 (09.11.): Bereich „Einstellungen“ (Leise-Zeiten, Gute Nacht, Lesezeichen-Ablauf) und die
 * Erweiterungen v1.1 (Eingangseintrag entfernen, Filter `uid`, `konfig/get`, Details im Ereignis „Upload fertig“).
 * Neue Befehle und Felder nutzt die Seite nur, wenn `hello.faehigkeiten` sie zusagt.
 *
 * Aufbau: TobiboxStore hält Zustand und Logik (ohne DOM, einzeln testbar),
 * <tobibox-panel> ist nur die Darstellung. Lit kommt aus ./lit-all.min.js (fest eingecheckt).
 */

export const VERTRAG_V = 1;
export const UPLOAD_URL = '/api/tobibox/upload';

/* ------------------------------------------------------------------ Texte */

export const FEHLERTEXTE = {
  invalid_format: 'Die Eingabe passt nicht. Bitte prüfen.',
  unauthorized: 'Dafür sind Administratorrechte nötig.',
  unknown_command: 'Die Seite ist neuer als die Integration. Bitte die Seite neu laden (Strg+F5).',
  unknown_error: 'Das hat nicht geklappt.',
  anfrage_id_konflikt: 'Dieser Vorgang wurde schon mit anderen Angaben gesendet. Bitte noch einmal versuchen.',
  medien_nicht_erreichbar: 'Die Medien-Freigabe (NAS) ist gerade nicht erreichbar.',
  medien_schreibfehler: 'Schreiben auf die Medien-Freigabe ist fehlgeschlagen.',
  kein_speicher: 'Auf der Freigabe ist nicht genug Platz.',
  mqtt_nicht_verbunden: 'Der MQTT-Broker ist nicht erreichbar. Der Befehl wurde nicht gesendet.',
  serie_nicht_gefunden: 'Diese Serie gibt es nicht (mehr).',
  folge_nicht_gefunden: 'Diese Folge gibt es nicht (mehr).',
  eintrag_nicht_gefunden: 'Diesen Eintrag gibt es nicht (mehr).',
  export_nicht_gefunden: 'Es gibt keine Exportdatei auf dem NAS.',
  export_ungueltig: 'Die Exportdatei ist nicht lesbar oder ungültig. Es wurde nichts übernommen.',
  box_unbekannt: 'Diese Box ist nicht eingerichtet.',
  box_offline: 'Die Box ist nicht erreichbar.',
  kennung_ungueltig: 'Diese Kennung ist ungültig.',
  ziel_ungueltig: 'Dieses Ziel ist nicht erlaubt (zum Beispiel die Überraschungs-Serie oder dieselbe Serie).',
  zuordnung_existiert: 'Dieser Tobie hat schon ein anderes Ziel.',
  zuordnung_geaendert: 'Die Zuordnung wurde inzwischen woanders geändert. Die Ansicht wurde neu geladen.',
  konfig_zu_gross: 'Die Liste der Zuordnungen wäre zu groß.',
  konfig_nicht_bereit: 'Die Liste ist gesperrt, bis die Warnung oben geklärt ist.',
  name_ungueltig: 'Dieser Name ist leer oder zu lang.',
  reihenfolge_ungueltig: 'Die Reihenfolge passt nicht zu den Folgen.',
  stand_veraltet: 'Die Serie wurde inzwischen geändert. Die Ansicht wurde neu geladen, bitte noch einmal versuchen.',
  tobies_betroffen: 'Es zeigen Tobies darauf. Bitte bestätigen.',
  ueberraschung_existiert: 'Es gibt schon eine Überraschungs-Serie.',
  lernmodus_laeuft: 'Für diese Box läuft schon ein Lernmodus mit anderem Ziel. Bitte erst abbrechen.',
  kein_lernmodus: 'Der Lernmodus läuft nicht mehr.',
  rueckfrage_abgelaufen: 'Die Zeit für die Rückfrage ist abgelaufen. Der Tobie wurde nicht umgeschrieben.',
  datei_existiert: 'In der Serie liegt schon eine Folge mit diesem Namen.',
  serie_existiert: 'Diese Serie ist schon vorhanden.',
  upload_laeuft: 'Dieser Upload läuft schon.',
  zu_viele_uploads: 'Es laufen schon zwei Uploads. Bitte kurz warten.',
  datei_zu_gross: 'Die Datei ist zu groß.',
  format_nicht_erlaubt: 'Dieses Dateiformat spielt die Box nicht.',
  einstellung_ungueltig: 'Diese Einstellung ist ungültig. Es wurde nichts geändert.',
  sortierung_laeuft: 'Das Einsortieren läuft gerade. Bitte gleich noch einmal versuchen.',
};

const HTTP_CODE = { 401: 'unauthorized', 403: 'unauthorized', 413: 'datei_zu_gross', 415: 'format_nicht_erlaubt',
  429: 'zu_viele_uploads', 507: 'kein_speicher', 503: 'medien_nicht_erreichbar' };

/* Stelle in einer Meldung `einstellung_ungueltig` („…ungültig: fenster[0].von. Es wurde nichts geändert.“) in Worten. */
const FELD_NAMEN = { id: 'Name', tage: 'Wochentage', von: 'von', bis: 'bis', wirkung: 'Wirkung', grenze: 'Grenze' };
export function stelleText(pfad) {
  const f = /^fenster\[(\d+)\](?:\.(\w+))?/.exec(pfad || '');
  if (f) return `Fenster ${Number(f[1]) + 1}${f[2] ? `, ${FELD_NAMEN[f[2]] || f[2]}` : ''}`;
  if (/^leise_zeiten\.zeitzone/.test(pfad || '')) return 'Zeitzone';
  if (/^leise_zeiten/.test(pfad || '')) return 'Leise-Zeiten';
  if (/^gute_nacht\.timer_min/.test(pfad || '')) return 'Timer';
  if (/^gute_nacht\.ausblenden_s/.test(pfad || '')) return 'Ausblenden';
  if (/^gute_nacht/.test(pfad || '')) return 'Gute Nacht';
  if (/^lesezeichen_tage/.test(pfad || '')) return 'Lesezeichen-Ablauf';
  return '';
}

export function fehlerText(code, message) {
  if (code === 'einstellung_ungueltig') {
    const stelle = stelleText(/ungültig: (.+?)\. Es wurde/.exec(message || '')?.[1]);
    return stelle ? `${FEHLERTEXTE[code]} Stelle: ${stelle}.` : FEHLERTEXTE[code];
  }
  if (code && FEHLERTEXTE[code]) return FEHLERTEXTE[code];
  return message || FEHLERTEXTE.unknown_error;
}

/* ------------------------------------------------------------------ Einstellungen (AP 4.7) */

/* Dieselben Regeln und Grenzen wie auf der Box (store.py, parse_konfig) und in HA (store.py, pruefe_*).
 * Das Backend prüft noch einmal und bleibt maßgeblich; die Seite spart nur den Weg und zeigt es in Worten. */
export const EINSTELLUNG_GRENZEN = {
  fensterMax: 32, grenze: [0, 100], timerMin: [1, 240], ausblendenS: [5, 600], lesezeichenTage: [0, 365],
};
export const LESEZEICHEN_VORGABE = 14;
export const WOCHENTAGE = [[1, 'Mo', 'Montag'], [2, 'Di', 'Dienstag'], [3, 'Mi', 'Mittwoch'], [4, 'Do', 'Donnerstag'], [5, 'Fr', 'Freitag'], [6, 'Sa', 'Samstag'], [7, 'So', 'Sonntag']];
const ZEIT_RE = /^([01]\d|2[0-3]):[0-5]\d$/;
const FENSTER_ID_RE = /^[a-z0-9_-]{1,32}$/;
const ganz = (x) => typeof x === 'number' && Number.isInteger(x);
const imBereich = (x, [lo, hi]) => ganz(x) && x >= lo && x <= hi;

/* Eine Zahl aus einem Eingabefeld: Zahl bleibt Zahl, „45“ wird 45, alles andere bleibt Text und fällt in der Prüfung durch. */
export function zuZahl(v) {
  if (typeof v === 'number') return v;
  if (typeof v === 'string' && /^\s*-?\d+\s*$/.test(v)) return parseInt(v, 10);
  return v;
}

export function zeitzoneBekannt(zone) {
  if (typeof zone !== 'string' || !zone) return false;
  try { new Intl.DateTimeFormat('de-DE', { timeZone: zone }); return true; } catch { return false; }
}

/* Gibt den Text des ersten Fehlers zurück, sonst null. */
export function pruefeLeiseZeiten(lz) {
  if (!lz || typeof lz !== 'object') return 'Die Leise-Zeiten fehlen.';
  if (!zeitzoneBekannt(lz.zeitzone)) return 'Die Zeitzone ist unbekannt. Ein Beispiel: Europe/Berlin.';
  if (!Array.isArray(lz.fenster)) return 'Die Fenster fehlen.';
  if (lz.fenster.length > EINSTELLUNG_GRENZEN.fensterMax) return `Es sind höchstens ${EINSTELLUNG_GRENZEN.fensterMax} Fenster möglich.`;
  const ids = new Set();
  for (const [i, f] of lz.fenster.entries()) {
    const w = `Fenster ${i + 1}`;
    if (!f || typeof f !== 'object') return `${w}: ungültig.`;
    if (typeof f.id !== 'string' || !FENSTER_ID_RE.test(f.id) || ids.has(f.id)) return `${w}: Der Name ist ungültig oder doppelt.`;
    ids.add(f.id);
    if (!Array.isArray(f.tage) || !f.tage.length || !f.tage.every((t) => imBereich(t, [1, 7])) || new Set(f.tage).size !== f.tage.length) {
      return `${w}: Bitte mindestens einen Wochentag wählen.`;
    }
    if (typeof f.von !== 'string' || !ZEIT_RE.test(f.von)) return `${w}: „von“ ist keine Uhrzeit (hh:mm).`;
    if (typeof f.bis !== 'string' || !ZEIT_RE.test(f.bis)) return `${w}: „bis“ ist keine Uhrzeit (hh:mm).`;
    if (f.von === f.bis) return `${w}: „von“ und „bis“ dürfen nicht gleich sein.`;
    if (f.wirkung === 'leiser') {
      if (!imBereich(f.grenze, EINSTELLUNG_GRENZEN.grenze)) return `${w}: Die Grenze muss eine ganze Zahl von 0 bis 100 sein.`;
    } else if (f.wirkung !== 'stumm') return `${w}: Bitte „leiser“ oder „stumm“ wählen.`;
  }
  return null;
}
export function pruefeGuteNacht(gn) {
  if (!gn || typeof gn !== 'object') return 'Die Gute-Nacht-Einstellungen fehlen.';
  if (!imBereich(gn.timer_min, EINSTELLUNG_GRENZEN.timerMin)) return 'Der Timer muss eine ganze Zahl von 1 bis 240 Minuten sein.';
  if (!imBereich(gn.ausblenden_s, EINSTELLUNG_GRENZEN.ausblendenS)) return 'Das Ausblenden muss eine ganze Zahl von 5 bis 600 Sekunden sein.';
  return null;
}
export function pruefeLesezeichenTage(t) {
  return imBereich(t, EINSTELLUNG_GRENZEN.lesezeichenTage) ? null : 'Die Tage müssen eine ganze Zahl von 0 bis 365 sein (0 = nie).';
}

/* Was die Seite sendet: nur bekannte Felder, ganze Zahlen, bei „stumm“ ohne Grenze. */
export function leiseZeitenFuerBackend(lz) {
  return {
    zeitzone: typeof lz.zeitzone === 'string' ? lz.zeitzone.trim() : lz.zeitzone,
    fenster: (lz.fenster || []).map((f) => {
      const o = { id: f.id, tage: [...(f.tage || [])].sort((a, b) => a - b), von: f.von, bis: f.bis, wirkung: f.wirkung };
      if (f.wirkung === 'leiser') o.grenze = zuZahl(f.grenze);
      return o;
    }),
  };
}
export const ueberMitternacht = (f) => typeof f.von === 'string' && typeof f.bis === 'string' && f.bis < f.von;
export function neueFensterId(fenster) {
  const belegt = new Set(fenster.map((f) => f.id));
  for (let n = 1; n < 1000; n++) if (!belegt.has(`fenster-${n}`)) return `fenster-${n}`;
  return `fenster-${Date.now().toString(36)}`;
}
const klon = (x) => JSON.parse(JSON.stringify(x));

const HINWEIS_TEXTE = {
  datei_fehlt: 'Datei fehlt', kopierschutz: 'Kopierschutz', nicht_lesbar: 'Nicht lesbar',
  probedekodierung_fehlgeschlagen: 'Probedekodierung fehlgeschlagen', pruefung_nicht_moeglich: 'Prüfung nicht möglich',
  doppelte_id_korrigiert: 'Doppelte Kennung korrigiert', serie_json_ungueltig_repariert: 'Serien-Datei repariert',
  reservierter_ordner: 'Reservierter Ordner', ffprobe_fehlt: 'ffprobe fehlt', keine_audiodateien: 'Keine Audiodateien',
  verschieben_fehlgeschlagen: 'Verschieben fehlgeschlagen', doppelt: 'Schon vorhanden (verworfen)',
  vorgabe_serie_fehlt: 'Gewählte Serie fehlt',
};
export const hinweisText = (h) => (h && (h.text || HINWEIS_TEXTE[h.code] || h.code)) || '';

export const LERN_ZUSTAND = {
  wartet: 'Bitte jetzt den neuen Tobie auf die Box legen …',
  rueckfrage: 'Der Tobie hat schon ein anderes Ziel.',
  zugeordnet: 'Zugeordnet.',
  abgelehnt: 'Abgelehnt, nichts geändert.',
  abgebrochen: 'Abgebrochen.',
  abgelaufen: 'Abgelaufen, es wurde kein Tobie gemeldet.',
  box_lehnt_ab: 'Die Box hat den Lernmodus abgelehnt.',
};
const LERN_ENDE = new Set(['zugeordnet', 'abgelehnt', 'abgebrochen', 'abgelaufen', 'box_lehnt_ab']);

export const KONFIG_STAND = {
  aktuell: 'Liste aktuell', veraltet: 'Liste veraltet', voraus: 'Box hat neueren Stand', unbekannt: 'Stand unbekannt',
};

export const AKTIONEN = { status: 'Status', gute_nacht: 'Gute Nacht' };

export const plural = (n, eins, mehr) => `${n} ${n === 1 ? eins : mehr}`;
export const kurz = (uid) => (uid && uid.length > 11 ? `${uid.slice(0, 4)}…${uid.slice(-4)}` : uid || '');
export const tobieLabel = (t) => (t && (t.name || kurz(t.uid))) || '';

export function groesse(bytes) {
  if (bytes == null) return '';
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(bytes >= 10485760 ? 0 : 1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function zeitKurz(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

const uuid = () => (globalThis.crypto?.randomUUID
  ? globalThis.crypto.randomUUID()
  : 'x' + Math.random().toString(16).slice(2) + Date.now().toString(16));

const sameZiel = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

/* ------------------------------------------------------------------ Store */

export class TobiboxStore {
  constructor(opts = {}) {
    this.xhrFactory = opts.xhrFactory || (() => new XMLHttpRequest());
    this.hass = null;
    this._unsub = null;
    this._listeners = new Set();
    this._pending = false;
    this._coalesce = new Map();
    /* Hooks der Oberfläche; Tests setzen eigene. Vorgabe: ablehnen. */
    this.ui = {
      confirm: async () => false,
      prompt: async () => null,
      waehleZiel: async () => null,
      waehleSerie: async () => null,
    };
    this.s = {
      bereit: false, reloadNoetig: false, darf: false, faehigkeiten: [], boxenNamen: [], grenzen: {}, version: '',
      konfig: null, view: 'serien', serieId: null, serie: null,
      serien: [], ueberraschung: null, geprueftAm: null, pruefungLaeuft: false,
      eingang: { eintraege: [], gesamt: 0, filter: 'offen', sortierungLaeuft: false, geprueftAm: null },
      neuEinsortiert: [], papierkorb: { eintraege: [], gesamt: 0, gesamtBytes: 0 },
      neueTobies: { eintraege: [], gesamt: 0 }, zuordnungen: { liste: [], gesamt: 0 },
      boxen: [], lern: {}, uploads: [], abweichung: null, exportFehler: null,
      exportInfo: null, fehler: null, hinweis: null, busy: 0,
      einstellungen: { geladen: false, leise_zeiten: null, gute_nacht: null, lesezeichen_tage: null },
      entwurf: { leise: null, gute: null, lesezeichen: null },
    };
  }

  /* -- Grundlagen */
  onChange(fn) { this._listeners.add(fn); return () => this._listeners.delete(fn); }
  _changed() {
    if (this._pending) return;
    this._pending = true;
    queueMicrotask(() => { this._pending = false; this._listeners.forEach((f) => f(this.s)); });
  }
  get hatKonfig() { return !this.s.konfig || this.s.konfig.zustand === 'ok'; }
  has(f) { return this.s.faehigkeiten.includes(f); }

  async _api(type, payload = {}) {
    this.s.busy += 1; this._changed();
    try {
      return await this.hass.connection.sendMessagePromise({ type, ...payload });
    } catch (e) {
      const err = new Error(e?.message || 'Fehler');
      err.code = (e && e.code) || 'unknown_error';
      err.apiMessage = e?.message;
      throw err;
    } finally {
      this.s.busy -= 1; this._changed();
    }
  }

  setFehler(code, message) {
    this.s.fehler = { code, text: fehlerText(code, message), ts: Date.now() };
    this._changed();
  }
  setFehlerText(code, text) { this.s.fehler = { code, text, ts: Date.now() }; this._changed(); }
  clearFehler() { this.s.fehler = null; this._changed(); }
  setHinweis(text) { this.s.hinweis = text ? { text, ts: Date.now() } : null; this._changed(); }

  /* Führt eine Aktion aus, zeigt Fehler an, lädt bei Bedarf neu. Gibt true bei Erfolg. */
  async _tu(fn) {
    try { await fn(); return true; } catch (e) {
      const code = e.code || 'unknown_error';
      this.setFehler(code, e.apiMessage);
      await this._nachFehler(code);
      return false;
    }
  }
  async _nachFehler(code) {
    try {
      if (code === 'stand_veraltet') { await this.ladeSerien(); if (this.s.serieId) await this.ladeSerie(this.s.serieId); }
      else if (code === 'zuordnung_geaendert' || code === 'zuordnung_existiert') { await this.ladeZuordnungen(); await this.ladeNeueTobies(); }
      else if (code === 'konfig_nicht_bereit') { await this.ladeKonfig(); }
      else if (code === 'serie_nicht_gefunden' || code === 'folge_nicht_gefunden') { await this.ladeSerien(); }
      else if (code === 'eintrag_nicht_gefunden') { await this.ladePapierkorb(); await this.ladeEingang(); }
    } catch { /* schon angezeigt */ }
  }

  _einmal(key, fn) { /* fasst gleichzeitige Nachladungen zusammen */
    const st = this._coalesce.get(key);
    if (st) { st.nochmal = true; return st.p; }
    const e = { nochmal: false };
    e.p = (async () => {
      try { await fn(); } finally {
        this._coalesce.delete(key);
        if (e.nochmal) await this._einmal(key, fn);
      }
    })();
    this._coalesce.set(key, e);
    return e.p;
  }

  /* -- Start */
  async attach(hass) {
    this.hass = hass;
    if (this._started) return;
    this._started = true;
    try {
      const h = await this._api('tobibox/hello', { v: VERTRAG_V });
      if (h.v < VERTRAG_V) { this.s.reloadNoetig = true; this._changed(); return; }
      this._uebernehmeHello(h);
    } catch (e) {
      if (e.code === 'unknown_command') this.s.reloadNoetig = true;
      else this.setFehler(e.code, e.apiMessage);
      this._changed();
      return;
    }
    await this._abonnieren();
    this.s.bereit = true; this._changed();
    if (this.s.darf) {
      /* Beim Öffnen: Prüfung und Einsortieren anstoßen (Vertrag, Nr. 30). */
      this._api('tobibox/medien/pruefen').catch(() => {});
      if (this.has('eingang')) this._api('tobibox/eingang/sortieren').catch(() => {});
    }
    await this.ladeAlles();
  }

  detach() {
    if (this._unsub) { try { this._unsub(); } catch { /* egal */ } }
    this._unsub = null; this._started = false;
  }

  _uebernehmeHello(h) {
    Object.assign(this.s, {
      darf: !!h.darf_schreiben, faehigkeiten: h.faehigkeiten || [], boxenNamen: h.boxen || [],
      grenzen: h.grenzen || {}, version: h.version || '', konfig: h.konfig || null,
    });
    this._changed();
  }
  async hello() { this._uebernehmeHello(await this._api('tobibox/hello', { v: VERTRAG_V })); }

  async _abonnieren() {
    this._unsub = await this.hass.connection.subscribeMessage((ev) => this.onEvent(ev), { type: 'tobibox/subscribe' });
  }

  async ladeAlles() {
    const f = [this.ladeSerien(), this.ladeBoxen(), this.ladeNeueTobies(), this.ladeZuordnungen()];
    if (this.has('eingang')) f.push(this.ladeEingang());
    if (this.has('papierkorb')) f.push(this.ladePapierkorb());
    if (this.has('einstellungen')) f.push(this.ladeEinstellungen());
    const r = await Promise.allSettled(f);
    const bad = r.find((x) => x.status === 'rejected');
    if (bad) this.setFehler(bad.reason.code, bad.reason.apiMessage);
  }

  /* -- Laden */
  async ladeSerien() {
    const r = await this._api('tobibox/serien/list');
    Object.assign(this.s, { serien: r.serien, ueberraschung: r.ueberraschung, geprueftAm: r.geprueft_am, pruefungLaeuft: r.pruefung_laeuft });
    this._changed();
  }
  async ladeSerie(id) {
    try { this.s.serie = await this._api('tobibox/serie/get', { serie_id: id }); } catch (e) {
      if (e.code === 'serie_nicht_gefunden') { this.s.serie = null; this.s.serieId = null; this.s.view = 'serien'; }
      this._changed(); throw e;
    }
    this._changed();
    return this.s.serie;
  }
  async ladeBoxen() { this.s.boxen = (await this._api('tobibox/boxen/list')).boxen; this._changed(); }
  async ladeNeueTobies(offset = 0) {
    const r = await this._api('tobibox/neue_tobies/list', { limit: 100, offset });
    this.s.neueTobies = { eintraege: offset ? [...this.s.neueTobies.eintraege, ...r.eintraege] : r.eintraege, gesamt: r.gesamt };
    this._changed();
  }
  async ladeZuordnungen(offset = 0) {
    const r = await this._api('tobibox/zuordnung/list', { limit: 100, offset });
    this.s.zuordnungen = { liste: offset ? [...this.s.zuordnungen.liste, ...r.zuordnungen] : r.zuordnungen, gesamt: r.gesamt };
    if (r.konfig) this.s.konfig = { ...this.s.konfig, ...r.konfig };
    this._changed();
  }
  /* Nur der Konfig-Stand (Erweiterung v1.1: konfig/get); ältere Backends: hello. */
  async ladeKonfig() {
    if (!this.has('konfig_lesen')) { await this.hello(); return; }
    const r = await this._api('tobibox/konfig/get');
    this.s.konfig = r.konfig; this._changed();
  }
  /* Eine Zuordnung neu lesen (Erweiterung v1.1: zuordnung/list mit uid); ältere Backends: die ganze Liste. */
  async ladeZuordnung(uid) {
    if (!this.has('zuordnung_uid')) { await this.ladeZuordnungen(); return; }
    const r = await this._api('tobibox/zuordnung/list', { uid, limit: 1 });
    const alt = this.s.zuordnungen.liste.some((z) => z.uid === uid);
    const rest = this.s.zuordnungen.liste.filter((z) => z.uid !== uid);
    const neu = r.zuordnungen[0];
    const liste = neu ? [...rest, neu].sort((a, b) => (a.uid < b.uid ? -1 : (a.uid > b.uid ? 1 : 0))) : rest;
    this.s.zuordnungen = { liste, gesamt: Math.max(liste.length, this.s.zuordnungen.gesamt + (neu ? 1 : 0) - (alt ? 1 : 0)) };
    if (r.konfig) this.s.konfig = { ...this.s.konfig, ...r.konfig };
    this._changed();
  }
  async ladeEinstellungen() {
    const r = await this._api('tobibox/einstellungen/get');
    this.s.einstellungen = { geladen: true, leise_zeiten: r.leise_zeiten, gute_nacht: r.gute_nacht, lesezeichen_tage: r.lesezeichen_tage };
    if (r.konfig) this.s.konfig = { ...this.s.konfig, ...r.konfig };
    /* ein Entwurf, der dem gespeicherten Stand entspricht, ist keiner mehr */
    const e = this.s.entwurf;
    if (e.leise && JSON.stringify(e.leise) === JSON.stringify(r.leise_zeiten)) e.leise = null;
    if (e.gute && JSON.stringify(e.gute) === JSON.stringify(r.gute_nacht)) e.gute = null;
    if (e.lesezeichen != null && e.lesezeichen === r.lesezeichen_tage) e.lesezeichen = null;
    this._changed();
  }
  async ladeEingang(filter = this.s.eingang.filter, offset = 0) {
    const r = await this._api('tobibox/eingang/list', { filter, limit: 50, offset });
    this.s.eingang = {
      eintraege: offset ? [...this.s.eingang.eintraege, ...r.eintraege] : r.eintraege, gesamt: r.gesamt, filter,
      sortierungLaeuft: r.sortierung_laeuft, geprueftAm: r.geprueft_am,
    };
    this._changed();
  }
  async ladePapierkorb(offset = 0) {
    const r = await this._api('tobibox/papierkorb/list', { limit: 100, offset });
    this.s.papierkorb = { eintraege: offset ? [...this.s.papierkorb.eintraege, ...r.eintraege] : r.eintraege, gesamt: r.gesamt, gesamtBytes: r.gesamt_bytes };
    this._changed();
  }
  weiter(was) {
    return this._tu(async () => {
      if (was === 'zuordnungen') await this.ladeZuordnungen(this.s.zuordnungen.liste.length);
      if (was === 'neueTobies') await this.ladeNeueTobies(this.s.neueTobies.eintraege.length);
      if (was === 'papierkorb') await this.ladePapierkorb(this.s.papierkorb.eintraege.length);
      if (was === 'eingang') await this.ladeEingang(this.s.eingang.filter, this.s.eingang.eintraege.length);
    });
  }
  neuLaden() { return this._tu(async () => { await this.hello(); await this.ladeAlles(); if (this.s.serieId) await this.ladeSerie(this.s.serieId); }); }
  pruefen() {
    return this._tu(async () => {
      await this._api('tobibox/medien/pruefen');
      if (this.has('eingang')) await this._api('tobibox/eingang/sortieren');
    });
  }

  /* -- Navigation */
  zeige(view) {
    this.s.view = view; this.s.serieId = view === 'serie' ? this.s.serieId : null; if (view !== 'serie') this.s.serie = null; this._changed();
    if (view === 'einstellungen' && this.has('einstellungen')) return this._tu(() => this.ladeEinstellungen());
    return undefined;
  }
  oeffneSerie(id) {
    this.s.view = 'serie'; this.s.serieId = id; this.s.serie = null; this._changed();
    return this._tu(() => this.ladeSerie(id));
  }
  setEingangFilter(filter) { return this._tu(() => this.ladeEingang(filter)); }

  /* -- Serien */
  async serieAnlegen(typ = 'normal') {
    const name = await this.ui.prompt({ titel: typ === 'ueberraschung' ? 'Überraschungs-Serie anlegen' : 'Neue Serie', label: 'Name', wert: typ === 'ueberraschung' ? 'Überraschung' : '', max: this.s.grenzen.serie_name_max || 100, ja: 'Anlegen' });
    if (name == null) return false;
    return this._tu(async () => {
      const p = { name, anfrage_id: uuid() };
      if (typ === 'ueberraschung') p.typ = 'ueberraschung';
      await this._api('tobibox/serie/create', p);
      await this.ladeSerien();
    });
  }
  async serieUmbenennen(id, aktuell) {
    const name = await this.ui.prompt({ titel: 'Serie umbenennen', label: 'Anzeigename', wert: aktuell, max: this.s.grenzen.serie_name_max || 100, ja: 'Speichern' });
    if (name == null) return false;
    return this._tu(async () => {
      await this._api('tobibox/serie/rename', { serie_id: id, name });
      await this.ladeSerien(); if (this.s.serieId === id) await this.ladeSerie(id);
    });
  }
  async folgeUmbenennen(serieId, folge) {
    const name = await this.ui.prompt({ titel: 'Folge umbenennen', label: 'Anzeigename', wert: folge.anzeige, max: this.s.grenzen.folge_anzeige_max || 200, ja: 'Speichern' });
    if (name == null) return false;
    return this._tu(async () => {
      const stand = this.s.serie?.id === serieId ? this.s.serie.stand : undefined;
      await this._api('tobibox/folge/rename', { serie_id: serieId, folge: folge.name, name, stand });
      await this.ladeSerie(serieId); await this.ladeSerien();
    });
  }

  _tobiesText(tobies) {
    return tobies.map(tobieLabel).join(', ');
  }
  _tobiesVonSerie(s) {
    const t = [...(s.zuordnungen || [])];
    (s.folgen || []).forEach((f) => t.push(...(f.tobies || [])));
    return t;
  }

  /* Reihenfolge: Die Seite schickt die ganze Liste und `stand`. */
  async folgenSetzen(serieId, namen) {
    const stand = this.s.serie?.stand;
    const alt = this.s.serie;
    if (alt && alt.id === serieId) { /* sofort zeigen */
      const nach = new Map(alt.folgen.map((f) => [f.name, f]));
      this.s.serie = { ...alt, folgen: namen.map((n) => nach.get(n)) }; this._changed();
    }
    const ok = await this._tu(async () => {
      await this._api('tobibox/folgen/order', { serie_id: serieId, folgen: namen, stand });
      await this.ladeSerie(serieId);
    });
    if (!ok && alt) { try { await this.ladeSerie(serieId); } catch { /* angezeigt */ } }
    return ok;
  }
  folgeBewegen(serieId, name, delta) {
    const namen = this.s.serie.folgen.map((f) => f.name);
    const i = namen.indexOf(name); const j = i + delta;
    if (i < 0 || j < 0 || j >= namen.length) return Promise.resolve(false);
    [namen[i], namen[j]] = [namen[j], namen[i]];
    return this.folgenSetzen(serieId, namen);
  }
  folgeZiehen(serieId, von, nach) {
    const namen = this.s.serie.folgen.map((f) => f.name);
    const i = namen.indexOf(von); const j = namen.indexOf(nach);
    if (i < 0 || j < 0 || i === j) return Promise.resolve(false);
    namen.splice(j, 0, namen.splice(i, 1)[0]);
    return this.folgenSetzen(serieId, namen);
  }

  async folgeLoeschen(serieId, folge) {
    return this._tu(async () => {
      const s = await this.ladeSerie(serieId);
      const f = s.folgen.find((x) => x.name === folge) || { tobies: [] };
      for (let runde = 0; runde < 2; runde++) {
        const tobies = f.tobies || [];
        const ja = await this.ui.confirm({
          titel: 'Folge in den Papierkorb?',
          text: tobies.length
            ? `${plural(tobies.length, 'Tobie zeigt', 'Tobies zeigen')} darauf. Trotzdem in den Papierkorb? Die Zuordnung bleibt, die Box spielt bis zur Wiederherstellung die Überraschung.`
            : `„${f.anzeige || folge}“ kommt in den Papierkorb und lässt sich dort wiederherstellen.`,
          liste: tobies.map(tobieLabel), ja: 'In den Papierkorb', gefahr: true,
        });
        if (!ja) return;
        try {
          const p = { serie_id: serieId, folge, stand: this.s.serie.stand };
          if (tobies.length) p.tobies_bestaetigt = true;
          const r = await this._api('tobibox/folge/delete', p);
          if (r.betroffene_tobies?.length) this.setHinweis(`${plural(r.betroffene_tobies.length, 'Tobie spielt', 'Tobies spielen')} jetzt die Überraschung, bis die Folge zurück ist.`);
          await this.ladeSerie(serieId); await this.ladeSerien(); await this._optional(this.ladePapierkorb());
          return;
        } catch (e) {
          if (e.code !== 'tobies_betroffen' || runde) throw e;
          const neu = await this.ladeSerie(serieId); /* jemand hat inzwischen zugeordnet */
          f.tobies = (neu.folgen.find((x) => x.name === folge) || {}).tobies || [];
        }
      }
    });
  }
  async _optional(p) { try { await p; } catch { /* nur Anzeige */ } }

  async serieLoeschen(serieId) {
    return this._tu(async () => {
      const s = await this._api('tobibox/serie/get', { serie_id: serieId });
      const tobies = this._tobiesVonSerie(s);
      const ja = await this.ui.confirm({
        titel: `Serie „${s.name}“ in den Papierkorb?`,
        text: tobies.length
          ? `${plural(tobies.length, 'Tobie zeigt', 'Tobies zeigen')} auf diese Serie oder ihre Folgen. Trotzdem in den Papierkorb? Die Zuordnungen bleiben, die Box spielt bis zur Wiederherstellung die Überraschung.`
          : `Die Serie mit ${plural(s.folgen.length, 'Folge', 'Folgen')} kommt in den Papierkorb und lässt sich dort wiederherstellen.`,
        liste: tobies.map(tobieLabel), ja: 'In den Papierkorb', gefahr: true,
      });
      if (!ja) return;
      const p = { serie_id: serieId, stand: s.stand };
      if (tobies.length) p.tobies_bestaetigt = true;
      await this._api('tobibox/serie/delete', p);
      if (this.s.serieId === serieId) { this.s.serieId = null; this.s.serie = null; this.s.view = 'serien'; }
      await this.ladeSerien(); await this._optional(this.ladePapierkorb());
    });
  }

  async folgeVerschieben(serieId, folge) {
    const ziel = await this.ui.waehleSerie({ titel: `„${folge.anzeige}“ verschieben nach …`, ausser: [serieId] });
    if (!ziel) return false;
    return this._tu(async () => {
      const s = await this._api('tobibox/serie/get', { serie_id: serieId });
      const f = s.folgen.find((x) => x.name === folge.name) || { tobies: [] };
      const zielName = this.s.serien.find((x) => x.id === ziel)?.name || '';
      const n = (f.tobies || []).length;
      const ja = await this.ui.confirm({
        titel: 'Folge verschieben?',
        text: n
          ? `${plural(n, 'Tobie zeigt', 'Tobies zeigen')} auf diese Folge. Sie zeigen danach auf die Folge in „${zielName}“ und beginnen auf den Boxen von vorn.`
          : `„${f.anzeige}“ wechselt in die Serie „${zielName}“.`,
        liste: (f.tobies || []).map(tobieLabel), ja: 'Verschieben',
      });
      if (!ja) return;
      const p = { serie_id: serieId, folge: folge.name, ziel_serie_id: ziel, stand: s.stand };
      if (n) p.tobies_bestaetigt = true;
      await this._api('tobibox/folge/verschieben', p);
      await this.ladeSerie(serieId); await this.ladeSerien();
      if (n) await this._optional(this.ladeZuordnungen());
    });
  }

  async serienZusammenfuehren(quelleId) {
    const ziel = await this.ui.waehleSerie({ titel: 'Mit welcher Serie zusammenführen?', ausser: [quelleId], nurNormal: true });
    if (!ziel) return false;
    return this._tu(async () => {
      const [q, z] = await Promise.all([this._api('tobibox/serie/get', { serie_id: quelleId }), this._api('tobibox/serie/get', { serie_id: ziel })]);
      const tobies = this._tobiesVonSerie(q);
      const ja = await this.ui.confirm({
        titel: 'Serien zusammenführen?',
        text: `${plural(q.folgen.length, 'Folge', 'Folgen')} aus „${q.name}“ wechseln nach „${z.name}“, „${q.name}“ kommt in den Papierkorb.`
          + (tobies.length ? ` ${plural(tobies.length, 'Tobie zeigt', 'Tobies zeigen')} darauf und zeigen danach auf „${z.name}“; Folgen-Tobies beginnen auf den Boxen von vorn.` : ''),
        liste: tobies.map(tobieLabel), ja: 'Zusammenführen', gefahr: true,
      });
      if (!ja) return;
      const p = { quelle_id: quelleId, ziel_id: ziel, stand_quelle: q.stand, stand_ziel: z.stand };
      if (tobies.length) p.tobies_bestaetigt = true;
      const r = await this._api('tobibox/serien/zusammenfuehren', p);
      this.setHinweis(`${plural(r.verschoben, 'Folge', 'Folgen')} verschoben.`);
      this.s.view = 'serie'; this.s.serieId = ziel;
      await this.ladeSerien(); await this.ladeSerie(ziel);
      if (tobies.length) await this._optional(this.ladeZuordnungen());
    });
  }

  einsortierungBestaetigen(serieId, folgen) {
    return this._tu(async () => {
      const p = { serie_id: serieId };
      if (folgen) p.folgen = folgen;
      await this._api('tobibox/einsortierung/bestaetigen', p);
      await this.ladeSerien();
      if (this.s.serieId === serieId) await this.ladeSerie(serieId);
      if (this.has('eingang')) await this._optional(this.ladeEingang());
    });
  }

  /* -- Papierkorb */
  /* Eine Folge kommt in ihre alte Serie zurück. Gibt es die nicht mehr, wählt Tobias eine andere Serie
   * (`serie_id` bei papierkorb/restore, Vertrag W Nr. 11). `andere` fragt immer nach der Serie. */
  async papierkorbWiederherstellen(eintrag, { andere = false } = {}) {
    const serieFehlt = eintrag.typ === 'folge' && !!eintrag.serie_id && this.s.serien.length > 0 && !this.s.serien.some((x) => x.id === eintrag.serie_id);
    let serieId = null;
    if (eintrag.typ === 'folge' && (andere || serieFehlt)) {
      serieId = await this._andereSerieWaehlen(eintrag);
      if (!serieId) return false;
    }
    return this._tu(async () => {
      const p = { eintrag_id: eintrag.id };
      if (serieId) p.serie_id = serieId;
      try {
        await this._api('tobibox/papierkorb/restore', p);
      } catch (e) {
        /* Die alte Serie gibt es nicht mehr: nach einer anderen fragen und noch einmal senden */
        if (e.code !== 'serie_nicht_gefunden' || eintrag.typ !== 'folge' || serieId) throw e;
        await this._optional(this.ladeSerien());
        const neu = await this._andereSerieWaehlen(eintrag);
        if (!neu) return;
        await this._api('tobibox/papierkorb/restore', { eintrag_id: eintrag.id, serie_id: neu });
      }
      await this.ladePapierkorb(); await this.ladeSerien();
    });
  }
  _andereSerieWaehlen(eintrag) {
    return this.ui.waehleSerie({ titel: `„${eintrag.anzeige || eintrag.folge}“ zurückholen in …`, nurNormal: true });
  }
  async papierkorbLeeren() {
    const n = this.s.papierkorb.gesamt;
    const ja = await this.ui.confirm({
      titel: 'Papierkorb leeren?',
      text: `${plural(n, 'Eintrag', 'Einträge')} (${groesse(this.s.papierkorb.gesamtBytes)}) werden endgültig gelöscht. Das lässt sich nicht rückgängig machen.`,
      ja: 'Endgültig löschen', gefahr: true,
    });
    if (!ja) return false;
    return this._tu(async () => {
      const r = await this._api('tobibox/papierkorb/empty', { bestaetigt: true });
      this.setHinweis(`${plural(r.geloescht, 'Eintrag', 'Einträge')} gelöscht.`);
      await this.ladePapierkorb();
    });
  }

  /* -- Eingang */
  eingangSortieren(sofort = false) {
    return this._tu(async () => {
      const p = sofort ? { sofort: true } : {};
      await this._api('tobibox/eingang/sortieren', p);
    });
  }

  /* Erweiterung v1.1 (eingang/entfernen): Blockiertes oder Defektes in den Papierkorb, mit Rückfrage. */
  async eingangEntfernen(eintrag) {
    if (!this.has('eingang_entfernen')) return false;
    const ja = await this.ui.confirm({
      titel: 'Aus dem Eingang entfernen?',
      text: `„${eintrag.name}“ kommt in den Papierkorb und lässt sich dort wiederherstellen.`,
      ja: 'In den Papierkorb', gefahr: true,
    });
    if (!ja) return false;
    return this._tu(async () => {
      await this._api('tobibox/eingang/entfernen', { eintrag_id: eintrag.id, bestaetigt: true });
      await this.ladeEingang(); await this._optional(this.ladePapierkorb());
    });
  }

  /* -- Neue Tobies und Zuordnungen */
  _konfigOk() {
    if (this.hatKonfig) return true;
    this.setFehler('konfig_nicht_bereit');
    return false;
  }
  neueTobiesVerwerfen(uid) {
    return this._tu(async () => { await this._api('tobibox/neue_tobies/verwerfen', { uid }); await this.ladeNeueTobies(); });
  }
  async zuordnen(uid, bisher = null, nameVorgabe = '') {
    if (!this._konfigOk()) return false;
    const w = await this.ui.waehleZiel({ titel: 'Tobie zuordnen', mitName: true, aktion: true, name: nameVorgabe, ziel: bisher });
    if (!w) return false;
    return this._tu(async () => {
      if (bisher && !sameZiel(bisher, w.ziel)) {
        const ja = await this.ui.confirm({ titel: 'Zuordnung ändern?', text: 'Dieser Tobie hat schon ein anderes Ziel. Es wird ersetzt.', ja: 'Ersetzen' });
        if (!ja) return;
      }
      const p = { uid, ziel: w.ziel, erwartet_ziel: bisher };
      if (w.name) p.name = w.name; else if (nameVorgabe) p.name = null;
      const r = await this._api('tobibox/zuordnung/set', p);
      if (r.konfig) this.s.konfig = { ...this.s.konfig, ...r.konfig };
      if (r.veroeffentlicht === false) this.setHinweis('Gespeichert. Die Boxen bekommen die Liste, sobald der Broker wieder erreichbar ist.');
      await this.ladeZuordnung(uid); await this.ladeNeueTobies();
    });
  }
  async tobieUmbenennen(z) {
    if (!this._konfigOk()) return false;
    const name = await this.ui.prompt({ titel: 'Tobie-Name', label: 'Name (leer lassen für keinen Namen)', wert: z.name || '', max: this.s.grenzen.tobie_name_max || 60, ja: 'Speichern', leerErlaubt: true });
    if (name == null) return false;
    return this._tu(async () => {
      await this._api('tobibox/zuordnung/set', { uid: z.uid, ziel: z.ziel, name: name === '' ? null : name, erwartet_ziel: z.ziel });
      await this.ladeZuordnung(z.uid);
    });
  }
  async zuordnungLoesen(z) {
    if (!this._konfigOk()) return false;
    const ja = await this.ui.confirm({ titel: 'Zuordnung lösen?', text: `${tobieLabel(z)} spielt danach die Überraschung und erscheint wieder unter „Neue Tobies“.`, ja: 'Lösen', gefahr: true });
    if (!ja) return false;
    return this._tu(async () => {
      await this._api('tobibox/zuordnung/remove', { uid: z.uid, erwartet_ziel: z.ziel });
      await this.ladeZuordnung(z.uid);
    });
  }
  async kennungVonHand() {
    const uid = await this.ui.prompt({ titel: 'Kennung von Hand', label: 'Kennung des Tobies', wert: '', max: 64, ja: 'Weiter' });
    if (!uid) return false;
    return this.zuordnen(uid.trim(), null);
  }

  /* -- Lernmodus */
  async lernStart() {
    if (!this._konfigOk()) return false;
    const w = await this.ui.waehleZiel({ titel: 'Neuen Tobie lernen', mitBox: true, aktion: false, mitName: true });
    if (!w) return false;
    return this._tu(async () => {
      const p = { box: w.box, ziel: w.ziel, anfrage_id: uuid() };
      if (w.name) p.name = w.name;
      const r = await this._api('tobibox/lernmodus/start', p);
      this.s.lern = { ...this.s.lern, [r.box]: { box: r.box, befehl_id: r.befehl_id, zustand: 'wartet', ziel: r.ziel, beginn: r.beginn, frist_bis: r.frist_bis } };
    });
  }
  lernAntwort(befehlId, ueberschreiben) {
    return this._tu(async () => {
      const r = await this._api('tobibox/lernmodus/antwort', { befehl_id: befehlId, ueberschreiben });
      const box = Object.keys(this.s.lern).find((b) => this.s.lern[b].befehl_id === befehlId);
      if (box) this.s.lern = { ...this.s.lern, [box]: { ...this.s.lern[box], zustand: r.zustand, ende: true } };
      if (r.konfig) this.s.konfig = { ...this.s.konfig, ...r.konfig };
      await this._optional(this.ladeZuordnungen());
    });
  }
  lernAbbrechen(box) {
    return this._tu(async () => {
      await this._api('tobibox/lernmodus/abbrechen', { box });
      this.s.lern = { ...this.s.lern, [box]: { ...(this.s.lern[box] || { box }), zustand: 'abgebrochen', ende: true } };
    });
  }
  lernVergessen(box) { const l = { ...this.s.lern }; delete l[box]; this.s.lern = l; this._changed(); }
  offeneRueckfrage() { return Object.values(this.s.lern).find((v) => v.zustand === 'rueckfrage' && !v.ende) || null; }

  /* -- Boxen, Liste */
  boxSync(box) {
    return this._tu(async () => {
      await this._api('tobibox/box/sync', { box, anfrage_id: uuid() });
      this.setHinweis('Sync angestoßen. Das Ergebnis erscheint im Status der Box.');
    });
  }
  async listeNeuAusrollen() {
    const z = this.s.konfig?.zustand;
    const leer = z === 'leer_neu';
    const ja = await this.ui.confirm({
      titel: leer ? 'Mit leerer Liste neu beginnen?' : 'Liste neu ausrollen?',
      text: leer
        ? 'Alle Tobies verlieren ihre Zuordnung. Die Boxen bekommen eine leere Liste.'
        : 'HA verteilt den eigenen Stand mit neuer Listen-ID an alle Boxen. Boxen mit anderem Stand übernehmen ihn.',
      ja: leer ? 'Leer beginnen' : 'Neu ausrollen', gefahr: true,
    });
    if (!ja) return false;
    return this._tu(async () => {
      const r = await this._api('tobibox/liste/neu_ausrollen', { bestaetigt: true, anfrage_id: uuid() });
      this.s.konfig = { ...this.s.konfig, ...r.konfig }; this.s.abweichung = null;
      if (!r.veroeffentlicht) this.setHinweis('Gespeichert. Die Boxen bekommen die Liste, sobald der Broker wieder erreichbar ist.');
      await this.ladeZuordnungen(); await this._optional(this.ladeBoxen());
    });
  }
  exportLesen() {
    return this._tu(async () => { this.s.exportInfo = await this._api('tobibox/konfig/export_lesen'); this._changed(); });
  }
  async konfigAusExport() {
    let info;
    if (!(await this._tu(async () => { info = await this._api('tobibox/konfig/export_lesen'); this.s.exportInfo = info; }))) return false;
    if (!info.vorhanden) { this.setFehler('export_nicht_gefunden'); return false; }
    const ja = await this.ui.confirm({
      titel: 'Aus dem Export holen?',
      text: `Export: Revision ${info.revision}, ${zeitKurz(info.exportiert_am)}, ${plural(info.anzahl_zuordnungen ?? 0, 'Zuordnung', 'Zuordnungen')}. Die Liste wird mit neuer Listen-ID an alle Boxen verteilt.`,
      ja: 'Aus Export holen', gefahr: true,
    });
    if (!ja) return false;
    return this._tu(async () => {
      const r = await this._api('tobibox/konfig/aus_export', { bestaetigt: true, anfrage_id: uuid() });
      this.s.konfig = { ...this.s.konfig, ...r.konfig }; this.s.abweichung = null;
      this.setHinweis(`${plural(r.uebernommen?.zuordnungen ?? 0, 'Zuordnung', 'Zuordnungen')} aus dem Export übernommen.`);
      await this.ladeZuordnungen(); await this._optional(this.ladeBoxen());
    });
  }

  /* -- Einstellungen (AP 4.7): Leise-Zeiten, Gute Nacht, Lesezeichen-Ablauf.
   * Ein Entwurf (s.entwurf.*) hält, was Tobias gerade eingibt; gespeichert wird je Bereich mit einstellungen/set. */
  get einstellungenGeaendert() {
    const e = this.s.entwurf;
    return { leise: !!e.leise, gute: !!e.gute, lesezeichen: e.lesezeichen != null };
  }
  /* Die Werte, die die Oberfläche zeigt: der Entwurf, sonst der gespeicherte Stand. */
  get leiseAnzeige() { return this.s.entwurf.leise || this.s.einstellungen.leise_zeiten; }
  get guteAnzeige() { return this.s.entwurf.gute || this.s.einstellungen.gute_nacht; }
  get lesezeichenAnzeige() { return this.s.entwurf.lesezeichen ?? this.s.einstellungen.lesezeichen_tage; }

  _leiseEntwurf(fn) {
    const d = this.s.entwurf.leise ? this.s.entwurf.leise : klon(this.s.einstellungen.leise_zeiten);
    if (!d) return false;
    fn(d);
    this.s.entwurf.leise = d; this._changed();
    return true;
  }
  zeitzoneSetzen(zone) { return this._leiseEntwurf((d) => { d.zeitzone = zone; }); }
  fensterNeu() {
    return this._leiseEntwurf((d) => {
      if (d.fenster.length >= EINSTELLUNG_GRENZEN.fensterMax) { this.setHinweis(`Es sind höchstens ${EINSTELLUNG_GRENZEN.fensterMax} Fenster möglich.`); return; }
      d.fenster.push({ id: neueFensterId(d.fenster), tage: [1, 2, 3, 4, 5, 6, 7], von: '21:00', bis: '06:30', wirkung: 'stumm' });
    });
  }
  fensterAendern(i, patch) {
    return this._leiseEntwurf((d) => {
      const f = d.fenster[i]; if (!f) return;
      Object.assign(f, patch);
      if (f.wirkung === 'stumm') delete f.grenze;
      else if (f.wirkung === 'leiser' && f.grenze == null) f.grenze = 25;
    });
  }
  fensterLoeschen(i) { return this._leiseEntwurf((d) => { d.fenster.splice(i, 1); }); }
  tagUmschalten(i, tag) {
    return this._leiseEntwurf((d) => {
      const f = d.fenster[i]; if (!f) return;
      f.tage = f.tage.includes(tag) ? f.tage.filter((t) => t !== tag) : [...f.tage, tag].sort((a, b) => a - b);
    });
  }
  tageSetzen(i, tage) { return this._leiseEntwurf((d) => { if (d.fenster[i]) d.fenster[i].tage = [...tage]; }); }
  guteNachtSetzen(feld, wert) {
    const d = this.s.entwurf.gute ? this.s.entwurf.gute : klon(this.s.einstellungen.gute_nacht);
    if (!d) return false;
    d[feld] = wert; this.s.entwurf.gute = d; this._changed();
    return true;
  }
  lesezeichenSetzen(wert) { this.s.entwurf.lesezeichen = wert; this._changed(); }
  entwurfVerwerfen(was) {
    if (was === 'leise') this.s.entwurf.leise = null;
    if (was === 'gute') this.s.entwurf.gute = null;
    if (was === 'lesezeichen') this.s.entwurf.lesezeichen = null;
    this._changed();
  }

  /* Prüft in der Seite (gleiche Regeln wie Box und HA), sendet erst dann. Gibt true bei Erfolg. */
  async _einstellungSpeichern(was, payload, fehlerText_) {
    if (!this.has('einstellungen')) return false;
    if (!this._konfigOk()) return false;
    if (fehlerText_) { this.setFehlerText('einstellung_ungueltig', fehlerText_); return false; }
    return this._tu(async () => {
      const r = await this._api('tobibox/einstellungen/set', payload);
      this._einstellungUebernehmen(r, was);
    });
  }
  _einstellungUebernehmen(r, was) {
    const e = this.s.einstellungen;
    this.s.einstellungen = {
      geladen: true,
      leise_zeiten: r.leise_zeiten ?? e.leise_zeiten, gute_nacht: r.gute_nacht ?? e.gute_nacht, lesezeichen_tage: r.lesezeichen_tage ?? e.lesezeichen_tage,
    };
    if (was === 'leise') this.s.entwurf.leise = null;
    if (was === 'gute') this.s.entwurf.gute = null;
    if (was === 'lesezeichen') this.s.entwurf.lesezeichen = null;
    if (r.konfig) this.s.konfig = { ...this.s.konfig, ...r.konfig };
    if (r.veroeffentlicht === false) this.setHinweis('Gespeichert. Die Boxen bekommen die Einstellung, sobald der Broker wieder erreichbar ist.');
    else if (r.geaendert === false) this.setHinweis('Das war schon so eingestellt.');
    else this.setHinweis('Gespeichert. Die Boxen übernehmen die Einstellung, sobald sie verbunden sind.');
    this._changed();
  }
  leiseSpeichern() {
    const d = this.s.entwurf.leise;
    if (!d) return Promise.resolve(true);
    const lz = leiseZeitenFuerBackend(d);
    return this._einstellungSpeichern('leise', { leise_zeiten: lz }, pruefeLeiseZeiten(lz));
  }
  guteNachtSpeichern() {
    const d = this.s.entwurf.gute;
    if (!d) return Promise.resolve(true);
    const gn = { timer_min: zuZahl(d.timer_min), ausblenden_s: zuZahl(d.ausblenden_s) };
    return this._einstellungSpeichern('gute', { gute_nacht: gn }, pruefeGuteNacht(gn));
  }
  lesezeichenSpeichern() {
    if (this.s.entwurf.lesezeichen == null) return Promise.resolve(true);
    const t = zuZahl(this.s.entwurf.lesezeichen);
    return this._einstellungSpeichern('lesezeichen', { lesezeichen_tage: t }, pruefeLesezeichenTage(t));
  }

  /* -- Hochladen */
  async _token() {
    const a = this.hass.auth;
    try { if (a?.expired && a.refreshAccessToken) await a.refreshAccessToken(); } catch { /* weiter mit altem Token */ }
    return a?.data?.access_token || '';
  }
  hochladen(dateien, { serieId = null, einGruppe = false } = {}) {
    const liste = Array.from(dateien);
    const gruppe = einGruppe && liste.length > 1 ? uuid() : null;
    const eintraege = liste.map((f) => ({ id: uuid(), name: f.name, size: f.size, gesendet: 0, zustand: 'wartet', code: null, text: null, serieId, datei: f }));
    this.s.uploads = [...this.s.uploads, ...eintraege]; this._changed();
    return (async () => {
      for (const e of eintraege) await this._upload1(e, serieId, gruppe);
    })();
  }
  _upEintrag(e, patch) { Object.assign(e, patch); this._changed(); }
  async _upload1(e, serieId, gruppe) {
    const max = this.s.grenzen.upload_max_bytes;
    if (max && e.size > max) { this._upEintrag(e, { zustand: 'fehler', code: 'datei_zu_gross', text: fehlerText('datei_zu_gross') }); return; }
    this._upEintrag(e, { zustand: 'sendet' });
    const token = await this._token();
    const fd = new FormData();
    fd.append('upload_id', e.id);
    if (serieId) fd.append('serie_id', serieId);
    if (gruppe) fd.append('gruppe', gruppe);
    fd.append('datei', e.datei, e.name);
    const xhr = this.xhrFactory();
    await new Promise((fertig) => {
      xhr.open('POST', UPLOAD_URL);
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.upload.onprogress = (ev) => this._upEintrag(e, { gesendet: ev.loaded, size: ev.lengthComputable ? ev.total : e.size });
      xhr.upload.onload = () => { if (e.zustand === 'sendet') this._upEintrag(e, { zustand: 'pruefe', gesendet: e.size }); };
      xhr.onload = () => {
        let body = null;
        try { body = JSON.parse(xhr.responseText); } catch { /* kein JSON */ }
        if (xhr.status >= 200 && xhr.status < 300 && body && !body.fehler) {
          this._upEintrag(e, { zustand: 'fertig', gesendet: e.size, pruefung: body.pruefung, hinweis: body.hinweis, eingangName: body.eingang_name });
          this._nachUpload();
        } else {
          const code = body?.fehler?.code || HTTP_CODE[xhr.status] || 'unknown_error';
          this._upEintrag(e, { zustand: 'fehler', code, text: fehlerText(code, body?.fehler?.text) });
        }
        fertig();
      };
      const unklar = () => {
        this._upEintrag(e, { zustand: 'unklar', text: 'Die Verbindung ist abgebrochen. Ob die Datei angekommen ist, zeigt der Eingang.' });
        this._nachUpload(); fertig();
      };
      xhr.onerror = unklar; xhr.onabort = unklar; xhr.ontimeout = unklar;
      xhr.send(fd);
    });
  }
  _nachUpload() { if (this.has('eingang')) this._optional(this.ladeEingang()); }
  uploadsAufraeumen() { this.s.uploads = this.s.uploads.filter((u) => ['wartet', 'sendet', 'pruefe'].includes(u.zustand)); this._changed(); }

  /* -- Ereignisse (Abschnitt 4) */
  onEvent(ev) {
    if (!ev || !ev.thema) return;
    const d = ev.daten || {};
    const art = ev.art;
    const bg = (p) => { p.catch?.(() => {}); };
    switch (ev.thema) {
      case 'boxen':
        if (art === 'snapshot') bg(this._einmal('boxen', () => this.ladeBoxen()));
        else if (art === 'geaendert') {
          const alt = this.s.boxen.find((b) => b.box === d.box);
          const neu = { ...d, ereignisse: alt?.ereignisse || [] };
          this.s.boxen = alt ? this.s.boxen.map((b) => (b.box === d.box ? neu : b)) : [...this.s.boxen, neu];
        } else if (art === 'ereignis') {
          this.s.boxen = this.s.boxen.map((b) => (b.box === d.box ? { ...b, ereignisse: [d.ereignis, ...(b.ereignisse || [])].slice(0, 20) } : b));
        }
        break;
      case 'neue_tobies':
        if (art === 'snapshot') bg(this._einmal('neue', () => this.ladeNeueTobies()));
        else if (art === 'neu' || art === 'aktualisiert') {
          const liste = this.s.neueTobies.eintraege;
          const schon = liste.some((x) => x.uid === d.eintrag.uid);
          this.s.neueTobies = { eintraege: [d.eintrag, ...liste.filter((x) => x.uid !== d.eintrag.uid)], gesamt: this.s.neueTobies.gesamt + (schon ? 0 : 1) };
        } else if (art === 'entfernt') {
          const liste = this.s.neueTobies.eintraege;
          const n = liste.filter((x) => x.uid !== d.uid);
          this.s.neueTobies = { eintraege: n, gesamt: Math.max(0, this.s.neueTobies.gesamt - (liste.length - n.length)) };
        }
        break;
      case 'lernmodus':
        if (art === 'snapshot') {
          const l = {}; (d.vorgaenge || []).forEach((v) => { l[v.box] = v; }); this.s.lern = l;
        } else if (d.box) {
          const alt = this.s.lern[d.box] || {};
          const ende = LERN_ENDE.has(d.zustand);
          this.s.lern = { ...this.s.lern, [d.box]: { ...alt, ...d, ende } };
          if (d.zustand === 'zugeordnet') { bg(this._einmal('zuo', () => this.ladeZuordnungen())); bg(this._einmal('neue', () => this.ladeNeueTobies())); }
        }
        break;
      case 'medien':
        if (art === 'snapshot') { this.s.pruefungLaeuft = !!d.pruefung_laeuft; this.s.geprueftAm = d.geprueft_am; }
        else if (art === 'serien_geaendert') {
          bg(this._einmal('serien', () => this.ladeSerien()));
          if (this.s.serieId && (d.serie_ids || []).includes(this.s.serieId)) bg(this._einmal('serie', () => this.ladeSerie(this.s.serieId)));
        } else if (art === 'pruefung_fertig') { this.s.pruefungLaeuft = false; this.s.geprueftAm = d.geprueft_am; bg(this._einmal('serien', () => this.ladeSerien())); }
        else if (art === 'papierkorb_geaendert' && this.has('papierkorb')) bg(this._einmal('korb', () => this.ladePapierkorb()));
        break;
      case 'eingang':
        if (art === 'snapshot') { this.s.eingang = { ...this.s.eingang, sortierungLaeuft: !!d.sortierung_laeuft, geprueftAm: d.geprueft_am }; this.s.eingangZaehler = { offen: d.offen, blockiert: d.blockiert }; }
        else if (art === 'geaendert') bg(this._einmal('eingang', () => this.ladeEingang()));
        else if (art === 'neu_einsortiert') {
          this.s.neuEinsortiert = [{ ...d, ts: Date.now() }, ...this.s.neuEinsortiert].slice(0, 20);
          bg(this._einmal('eingang', () => this.ladeEingang()));
        } else if (art === 'durchlauf_fertig') {
          this.s.eingang = { ...this.s.eingang, sortierungLaeuft: false, geprueftAm: d.geprueft_am };
          bg(this._einmal('eingang', () => this.ladeEingang()));
        }
        break;
      case 'konfig':
        if (art === 'snapshot' || art === 'geaendert') {
          this.s.konfig = d.konfig;
          if (art === 'geaendert') {
            bg(this._einmal('zuo', () => this.ladeZuordnungen()));
            if (this.has('einstellungen')) bg(this._einmal('einst', () => this.ladeEinstellungen()));
          }
        } else if (art === 'abweichung') this.s.abweichung = d;
        else if (art === 'export_fehler') { this.s.exportFehler = d; if (this.s.konfig) this.s.konfig = { ...this.s.konfig, export_ok: false }; }
        else if (art === 'export_ok') { this.s.exportFehler = null; if (this.s.konfig) this.s.konfig = { ...this.s.konfig, export_ok: true, export_geschrieben_am: d.export_geschrieben_am }; }
        break;
      case 'upload':
        if (art === 'fortschritt') {
          const u = this.s.uploads.find((x) => x.id === d.upload_id);
          if (u) {
            if (d.zustand === 'pruefe' && u.zustand !== 'fertig') u.zustand = 'pruefe';
            /* Erweiterung v1.1: „fertig“ trägt Dateiname im Eingang und Ergebnis der Prüfung. Das rettet einen Upload,
             * dessen Verbindung abbrach (Zustand „unklar“), bevor die Antwort kam. */
            if (d.zustand === 'fertig' && this.has('upload_fertig_details') && u.zustand !== 'fertig' && u.zustand !== 'fehler') {
              Object.assign(u, { zustand: 'fertig', gesendet: u.size, text: null, pruefung: d.pruefung ?? u.pruefung, eingangName: d.datei ?? u.eingangName });
              this._nachUpload();
            }
            if (d.zustand === 'fehler' && u.zustand !== 'fehler') { u.zustand = 'fehler'; u.code = d.code; u.text = fehlerText(d.code); }
          }
        }
        break;
      default:
    }
    this._changed();
  }
}

/* ------------------------------------------------------------------ Element */

const lit = typeof HTMLElement !== 'undefined' && typeof customElements !== 'undefined'
  ? await import('./lit-all.min.js') : null;

if (lit) {
  const { LitElement, html, css, nothing, repeat } = lit;

  class TobiboxPanel extends LitElement {
    static properties = {
      hass: { attribute: false }, narrow: { type: Boolean }, route: { attribute: false }, panel: { attribute: false },
      _tick: { state: true }, _dlg: { state: true }, _drag: { state: true },
      /* A12/A13: Einbettung in „Technik“ der neuen Seite (Design 5.9). Ohne `eingebettet` ändert sich nichts. */
      eingebettet: { type: Boolean, reflect: true }, bereich: { type: String }, box: { type: String },
    };

    constructor() {
      super();
      this.store = new TobiboxStore();
      this._tick = 0; this._dlg = null; this._drag = null;
      this.eingebettet = false; this.bereich = 'alle'; this.box = '';
      this._off = this.store.onChange(() => { this._tick += 1; });
      this.store.ui = {
        confirm: (o) => this._frage('confirm', o),
        prompt: (o) => this._frage('prompt', o),
        waehleSerie: (o) => this._frage('serie', o),
        waehleZiel: (o) => this._frage('ziel', o),
      };
    }

    willUpdate(ch) {
      if (ch.has('hass') && this.hass) {
        if (!this.store.hass) this.store.attach(this.hass); else this.store.hass = this.hass;
      }
    }
    disconnectedCallback() { super.disconnectedCallback(); this.store.detach(); }

    /* -- Dialoge */
    _frage(kind, opts) {
      return new Promise((resolve) => {
        const d = { kind, opts, resolve, werte: {} };
        if (kind === 'prompt') d.werte.text = opts.wert ?? '';
        if (kind === 'serie') d.werte.serie = '';
        if (kind === 'ziel') {
          const z = opts.ziel || {};
          d.werte = { typ: z.typ || 'serie', serie: z.serie || '', folge: z.folge || '', aktion: z.aktion || 'status', box: this.store.s.boxenNamen[0] || '', name: opts.name || '', folgen: [] };
          if (d.werte.typ === 'folge' && d.werte.serie) this._ladeFolgen(d);
        }
        this._dlg = d;
      });
    }
    _zu(wert) { const d = this._dlg; this._dlg = null; d?.resolve(wert); }
    async _ladeFolgen(d) {
      d.werte.folgen = []; this.requestUpdate();
      if (!d.werte.serie) return;
      try { const s = await this.store._api('tobibox/serie/get', { serie_id: d.werte.serie }); d.werte.folgen = s.folgen; if (!d.werte.folge || !s.folgen.some((f) => f.name === d.werte.folge)) d.werte.folge = s.folgen[0]?.name || ''; } catch (e) { this.store.setFehler(e.code, e.apiMessage); }
      this.requestUpdate();
    }

    /* -- Hilfen */
    _serienName(id) { return this.store.s.serien.find((s) => s.id === id)?.name || ''; }
    _zielText(z, mit = {}) {
      if (!z) return '';
      if (z.typ === 'aktion') return `Aktion: ${AKTIONEN[z.aktion] || z.aktion}`;
      const sn = mit.serie_name ?? this._serienName(z.serie);
      if (z.typ === 'serie') return `Serie: ${sn || '(fehlt)'}`;
      return `Folge: ${mit.folge_anzeige || z.folge} · ${sn || '(Serie fehlt)'}`;
    }
    get _s() { return this.store.s; }
    get _kannSchreiben() { return this._s.darf; }
    get _gesperrt() { return !this.store.hatKonfig; }

    /* -- Darstellung */
    render() {
      if (this.eingebettet) return this._renderEingebettet();
      const s = this._s;
      return html`
        <div class="app">
          <header>
            <h1>Tobi Box</h1>
            <span class="grow"></span>
            ${s.busy > 0 ? html`<span class="spin" aria-label="Lädt"></span>` : nothing}
            ${this.store.has('einstellungen') ? html`<button class="icon ${s.view === 'einstellungen' ? 'aktiv' : ''}" @click=${() => this.store.zeige('einstellungen')} aria-label="Einstellungen">⚙</button>` : nothing}
            <button class="icon" @click=${() => this.store.neuLaden()} aria-label="Neu laden">↻</button>
          </header>
          <main>
            ${s.reloadNoetig ? html`<div class="banner err" role="alert">Bitte die Seite neu laden (Strg+F5).</div>` : nothing}
            ${this._bannerFehler()}${this._bannerHinweis()}${this._bannerKonfig()}
            ${!s.bereit && !s.reloadNoetig ? html`<p class="leer">Lade …</p>` : this._ansicht()}
          </main>
          ${this._nav()}
          ${this._dialog()}${this._rueckfrageLern()}
        </div>`;
    }

    _bannerFehler() {
      const f = this._s.fehler;
      if (!f) return nothing;
      return html`<div class="banner err" role="alert"><span class="grow">${f.text}</span>
        <button class="klein" @click=${() => this.store.clearFehler()}>OK</button></div>`;
    }
    _bannerHinweis() {
      const h = this._s.hinweis;
      if (!h) return nothing;
      return html`<div class="banner info" role="status"><span class="grow">${h.text}</span>
        <button class="klein" @click=${() => this.store.setHinweis(null)}>OK</button></div>`;
    }
    _bannerKonfig() {
      const s = this._s; const k = s.konfig;
      const out = [];
      if (k?.zustand === 'leer_neu') {
        out.push(html`<div class="banner warn" role="alert"><b>Die Liste der Tobies ist leer.</b>
          Der Speicher in HA ist leer, obwohl es schon einmal eine Liste gab. Bis du entscheidest, ändert sich nichts an den Boxen.
          <div class="reihe">${this._kannSchreiben ? html`
            <button @click=${() => this.store.konfigAusExport()}>Aus dem Export holen</button>
            <button class="gefahr" @click=${() => this.store.listeNeuAusrollen()}>Mit leerer Liste neu beginnen</button>` : nothing}</div></div>`);
      } else if (k?.zustand === 'export_neuer') {
        out.push(html`<div class="banner warn" role="alert"><b>Der Export auf dem NAS ist neuer als der Stand in HA.</b>
          HA wurde wohl aus einer Sicherung zurückgespielt. Bis du entscheidest, ändert sich nichts an den Boxen.
          <div class="reihe">${this._kannSchreiben ? html`
            <button @click=${() => this.store.konfigAusExport()}>Aus dem Export holen</button>
            <button class="gefahr" @click=${() => this.store.listeNeuAusrollen()}>Stand von HA behalten</button>` : nothing}</div></div>`);
      }
      if (k && k.export_ok === false && k.zustand === 'ok') {
        out.push(html`<div class="banner warn" role="alert">Die Sicherung auf dem NAS fehlt: Der Export konnte nicht geschrieben werden.${s.exportFehler?.text ? html` ${s.exportFehler.text}` : nothing}</div>`);
      }
      if (s.abweichung) {
        out.push(html`<div class="banner warn" role="alert">Die Box ${s.abweichung.box} hat einen neueren Stand als HA. Bitte „Liste neu ausrollen“ (oder aus dem Export holen).
          <div class="reihe">${this._kannSchreiben ? html`<button @click=${() => this.store.listeNeuAusrollen()}>Liste neu ausrollen</button>
            <button @click=${() => this.store.konfigAusExport()}>Aus dem Export holen</button>` : nothing}</div></div>`);
      }
      return out;
    }

    _nav() {
      const s = this._s;
      const tab = (id, text, badge) => html`<button class="tab ${s.view === id || (id === 'serien' && s.view === 'serie') ? 'aktiv' : ''}" @click=${() => this.store.zeige(id)}>
        <span>${text}</span>${badge ? html`<span class="badge">${badge}</span>` : nothing}</button>`;
      const offen = s.eingang.filter === 'offen' ? s.eingang.gesamt : (s.eingangZaehler?.offen || 0);
      return html`<nav>
        ${tab('serien', 'Serien', '')}
        ${this.store.has('eingang') ? tab('eingang', 'Eingang', offen || '') : nothing}
        ${tab('tobies', 'Tobies', s.neueTobies.gesamt || '')}
        ${tab('boxen', 'Boxen', '')}
        ${this.store.has('papierkorb') ? tab('papierkorb', 'Korb', '') : nothing}
      </nav>`;
    }

    _ansicht() {
      switch (this._s.view) {
        case 'serie': return this._viewSerie();
        case 'eingang': return this._viewEingang();
        case 'tobies': return this._viewTobies();
        case 'boxen': return this._viewBoxen();
        case 'papierkorb': return this._viewKorb();
        case 'einstellungen': return this._viewEinstellungen();
        default: return this._viewSerien();
      }
    }

    /* -- Serienliste und Hochladen */
    _viewSerien() {
      const s = this._s; const w = this._kannSchreiben;
      return html`
        ${w && this.store.has('upload') ? this._uploadKarte() : nothing}
        ${w && s.ueberraschung === 'fehlt' ? html`<div class="karte"><p>Es gibt noch keine Überraschungs-Serie. Die Box spielt sonst bei unbekannten Tobies einen Fehlerton.</p>
          <button @click=${() => this.store.serieAnlegen('ueberraschung')}>Überraschungs-Serie anlegen</button></div>` : nothing}
        ${s.ueberraschung === 'mehrere' ? html`<div class="banner warn">Es gibt mehr als eine Überraschungs-Serie.</div>` : nothing}
        ${s.ueberraschung === 'leer' ? html`<div class="banner info">Die Überraschungs-Serie ist noch leer.</div>` : nothing}
        <div class="reihe">
          ${w ? html`<button @click=${() => this.store.serieAnlegen()}>Neue Serie</button>
          <button class="zweit" @click=${() => this.store.pruefen()}>Freigabe prüfen</button>` : nothing}
        </div>
        <p class="klein-text">${s.pruefungLaeuft ? 'Prüfung läuft …' : (s.geprueftAm ? `Zuletzt geprüft: ${zeitKurz(s.geprueftAm)}` : '')}</p>
        ${s.serien.length ? s.serien.map((x) => html`
          <button class="karte zeile" @click=${() => this.store.oeffneSerie(x.id)}>
            <span class="titel">${x.name}${x.typ === 'ueberraschung' ? html` <span class="marke">Überraschung</span>` : nothing}</span>
            <span class="meta">${plural(x.anzahl_folgen, 'Folge', 'Folgen')} · ${plural(x.anzahl_tobies, 'Tobie', 'Tobies')}</span>
            ${x.pruefen || x.anzahl_pruefen ? html`<span class="marke warnm">bitte prüfen${x.anzahl_pruefen ? ` (${x.anzahl_pruefen})` : ''}</span>` : nothing}
            ${x.hinweise?.length ? html`<span class="marke warnm">${plural(x.hinweise.length, 'Hinweis', 'Hinweise')}</span>` : nothing}
          </button>`) : html`<p class="leer">Noch keine Serien.</p>`}`;
    }

    _uploadKarte() {
      const s = this._s;
      return html`<div class="karte">
        <h2>Hochladen</h2>
        <label>In diese Serie einsortieren (Vorgabe)
          <select id="up-serie">
            <option value="">Nach den Tags entscheiden</option>
            ${s.serien.map((x) => html`<option value=${x.id}>${x.name}</option>`)}
          </select></label>
        <label class="check"><input type="checkbox" id="up-gruppe"> Die Dateien gehören zu einer Folge (ein Hörbuch)</label>
        <label class="datei">Dateien wählen
          <input type="file" id="up-dateien" multiple accept="audio/*,.m4b,.m4a,.mp3,.flac,.ogg,.opus,.wav,.aac"
            @change=${(e) => this._hochladen(e)}></label>
        ${s.uploads.map((u) => this._uploadZeile(u))}
        ${s.uploads.some((u) => ['fertig', 'fehler', 'unklar'].includes(u.zustand)) ? html`<button class="zweit" @click=${() => this.store.uploadsAufraeumen()}>Liste leeren</button>` : nothing}
      </div>`;
    }
    _hochladen(e) {
      const root = this.renderRoot;
      const dateien = Array.from(e.target.files || []);
      if (!dateien.length) return;
      this.store.hochladen(dateien, { serieId: root.querySelector('#up-serie')?.value || null, einGruppe: !!root.querySelector('#up-gruppe')?.checked });
      e.target.value = '';
    }
    _uploadZeile(u) {
      const pct = u.size ? Math.min(100, Math.round((u.gesendet / u.size) * 100)) : 0;
      const text = {
        wartet: 'wartet', sendet: `${pct} %`, pruefe: 'wird geprüft …',
        fertig: u.pruefung === 'warnung' ? `Warnung${u.hinweis ? `: ${u.hinweis}` : ''}. Die Datei bleibt im Eingang.` : 'angekommen',
        fehler: u.text, unklar: u.text,
      }[u.zustand];
      return html`<div class="upload ${u.zustand}">
        <div class="zeile2"><span class="titel">${u.name}</span><span class="meta">${groesse(u.size)}</span></div>
        <progress max="100" value=${u.zustand === 'fertig' || u.zustand === 'pruefe' ? 100 : pct}></progress>
        <div class="meta">${text}</div></div>`;
    }

    /* -- Serie */
    _viewSerie() {
      const s = this._s; const ser = s.serie; const w = this._kannSchreiben;
      if (!ser) return html`<button class="zweit" @click=${() => this.store.zeige('serien')}>‹ Serien</button><p class="leer">Lade …</p>`;
      return html`
        <button class="zweit" @click=${() => this.store.zeige('serien')}>‹ Serien</button>
        <div class="karte">
          <h2>${ser.name}</h2>
          <div class="meta">${plural(ser.folgen.length, 'Folge', 'Folgen')} · ${plural(ser.anzahl_tobies, 'Tobie', 'Tobies')}</div>
          ${ser.hinweise?.map((h) => html`<div class="marke warnm blockm">${hinweisText(h)}${h.folge ? html` (${h.folge})` : nothing}</div>`)}
          ${ser.zuordnungen?.length ? html`<div class="meta">Tobies auf die ganze Serie: ${ser.zuordnungen.map(tobieLabel).join(', ')}</div>` : nothing}
          ${w ? html`<div class="reihe">
            <button @click=${() => this.store.serieUmbenennen(ser.id, ser.name)}>Umbenennen</button>
            ${ser.pruefen || ser.anzahl_pruefen ? html`<button @click=${() => this.store.einsortierungBestaetigen(ser.id)}>Alles geprüft</button>` : nothing}
            ${ser.typ === 'normal' ? html`<button class="zweit" @click=${() => this.store.serienZusammenfuehren(ser.id)}>Zusammenführen …</button>` : nothing}
            ${this.store.has('serie_loeschen') ? html`<button class="gefahr" @click=${() => this.store.serieLoeschen(ser.id)}>Serie löschen</button>` : nothing}
          </div>` : nothing}
        </div>
        ${w && this.store.has('upload') ? this._uploadKarteSerie(ser) : nothing}
        ${ser.folgen.length ? repeat(ser.folgen, (f) => f.name, (f, i) => this._folge(ser, f, i)) : html`<p class="leer">Noch keine Folgen.</p>`}`;
    }
    _uploadKarteSerie(ser) {
      return html`<div class="karte"><label class="datei">Dateien in diese Serie hochladen
        <input type="file" multiple accept="audio/*,.m4b,.m4a,.mp3,.flac,.ogg,.opus,.wav,.aac" @change=${(e) => {
          const d = Array.from(e.target.files || []); if (!d.length) return;
          this.store.hochladen(d, { serieId: ser.id }); e.target.value = '';
        }}></label>
        ${this._s.uploads.map((u) => this._uploadZeile(u))}</div>`;
    }
    _folge(ser, f, i) {
      const w = this._kannSchreiben; const n = ser.folgen.length;
      return html`<div class="karte folge ${this._drag === f.name ? 'zieht' : ''}" draggable=${w ? 'true' : 'false'}
          @dragstart=${(e) => { this._drag = f.name; e.dataTransfer?.setData('text/plain', f.name); }}
          @dragover=${(e) => e.preventDefault()}
          @drop=${(e) => { e.preventDefault(); const von = this._drag; this._drag = null; if (von) this.store.folgeZiehen(ser.id, von, f.name); }}
          @dragend=${() => { this._drag = null; }}>
        <div class="zeile2"><span class="nr">${i + 1}</span>
          <span class="titel">${f.anzeige}</span></div>
        <div class="meta">${f.art === 'ordner' ? plural(f.tracks, 'Track', 'Tracks') + ' · ' : ''}${groesse(f.groesse_bytes)}${f.nummer != null ? ` · Nr. ${f.nummer}` : ''}${f.tobies?.length ? ` · Tobies: ${f.tobies.map(tobieLabel).join(', ')}` : ''}</div>
        <div>
          ${f.pruefen ? html`<span class="marke warnm">bitte prüfen</span>` : nothing}
          ${f.pruefung === 'warnung' ? html`<span class="marke warnm">Warnung${f.hinweis ? `: ${HINWEIS_TEXTE[f.hinweis] || f.hinweis}` : ''}</span>` : nothing}
        </div>
        ${w ? html`<div class="reihe">
          <button class="zweit" ?disabled=${i === 0} aria-label="Hoch" @click=${() => this.store.folgeBewegen(ser.id, f.name, -1)}>▲ Hoch</button>
          <button class="zweit" ?disabled=${i === n - 1} aria-label="Runter" @click=${() => this.store.folgeBewegen(ser.id, f.name, 1)}>▼ Runter</button>
          <button class="zweit" @click=${() => this.store.folgeUmbenennen(ser.id, f)}>Umbenennen</button>
          <button class="zweit" @click=${() => this.store.folgeVerschieben(ser.id, f)}>Verschieben</button>
          ${f.pruefen ? html`<button class="zweit" @click=${() => this.store.einsortierungBestaetigen(ser.id, [f.name])}>Geprüft</button>` : nothing}
          <button class="gefahr" @click=${() => this.store.folgeLoeschen(ser.id, f.name)}>Löschen</button>
        </div>` : nothing}
      </div>`;
    }

    /* -- Eingang */
    _viewEingang() {
      const s = this._s; const e = s.eingang; const w = this._kannSchreiben;
      return html`
        <div class="reihe">
          ${['offen', 'erledigt'].map((fl) => html`<button class="${e.filter === fl ? '' : 'zweit'}" @click=${() => this.store.setEingangFilter(fl)}>${fl === 'offen' ? 'Im Eingang' : 'Einsortiert'}</button>`)}
        </div>
        ${w ? html`<div class="reihe">
          <button @click=${() => this.store.eingangSortieren()}>Erneut einsortieren</button>
          <button class="zweit" @click=${() => this.store.eingangSortieren(true)}>Sofort, ohne Wartezeit</button></div>` : nothing}
        <p class="klein-text">${e.sortierungLaeuft ? 'Einsortieren läuft …' : (e.geprueftAm ? `Zuletzt: ${zeitKurz(e.geprueftAm)}` : '')}</p>
        ${s.neuEinsortiert.length ? html`<h2>Neu einsortiert</h2>${s.neuEinsortiert.map((n) => html`<div class="karte">
          <div class="titel">${n.eintrag_name}</div>
          ${(n.ergebnis || []).map((r) => this._ergebnis(r))}
          ${(n.hinweise || []).map((h) => html`<div class="marke warnm blockm">${hinweisText(h)}</div>`)}</div>`)}` : nothing}
        <h2>${e.filter === 'offen' ? 'Liegt im Eingang' : 'Zuletzt einsortiert'}</h2>
        ${e.eintraege.length ? e.eintraege.map((x) => html`<div class="karte">
          <div class="titel">${x.name}</div>
          <div class="meta">${plural(x.dateien, 'Datei', 'Dateien')} · ${groesse(x.groesse_bytes)} · ${({ wartet: 'wartet', bereit: 'bereit', laeuft: 'läuft', blockiert: 'blockiert', teilweise: 'teilweise einsortiert', erledigt: 'einsortiert' })[x.status] || x.status}</div>
          ${(x.hinweise || []).map((h) => html`<div class="marke warnm blockm">${hinweisText(h)}${h.datei ? html` (${h.datei})` : nothing}</div>`)}
          ${(x.ergebnis || []).map((r) => this._ergebnis(r))}
          ${w && this.store.has('eingang_entfernen') && e.filter === 'offen' && ['blockiert', 'teilweise'].includes(x.status)
            ? html`<div class="reihe"><button class="gefahr" @click=${() => this.store.eingangEntfernen(x)}>Entfernen</button></div>` : nothing}</div>`) : html`<p class="leer">Nichts im Eingang.</p>`}
        ${e.eintraege.length < e.gesamt ? html`<button class="zweit" @click=${() => this.store.weiter('eingang')}>Mehr laden</button>` : nothing}`;
    }
    _ergebnis(r) {
      const w = this._kannSchreiben;
      return html`<div class="ergebnis">
        <span>${r.anzeige}</span> <span class="meta">in „${r.serie_name}“${r.serie_neu ? ' (neue Serie)' : ''}</span>
        ${r.pruefen ? html`<span class="marke warnm">bitte prüfen</span>` : nothing}
        <div class="reihe">
          <button class="zweit" @click=${() => this.store.oeffneSerie(r.serie_id)}>Serie öffnen</button>
          ${w && r.pruefen ? html`<button class="zweit" @click=${() => this.store.einsortierungBestaetigen(r.serie_id, [r.folge])}>Geprüft</button>` : nothing}
        </div></div>`;
    }

    /* -- Tobies */
    _viewTobies() {
      const s = this._s; const w = this._kannSchreiben; const gesperrt = this._gesperrt;
      return html`
        ${gesperrt ? html`<div class="banner info">Änderungen an den Zuordnungen sind gesperrt, bis die Warnung oben geklärt ist.</div>` : nothing}
        <h2>Neue Tobies</h2>
        ${s.neueTobies.eintraege.length ? s.neueTobies.eintraege.map((n) => html`<div class="karte">
          <div class="titel">${kurz(n.uid)}</div>
          <div class="meta">${n.anzahl}× gemeldet · zuletzt ${zeitKurz(n.zuletzt)} · ${Object.keys(n.boxen || {}).join(', ')}</div>
          ${w ? html`<div class="reihe">
            <button ?disabled=${gesperrt} @click=${() => this.store.zuordnen(n.uid, null)}>Zuordnen</button>
            <button class="zweit" @click=${() => this.store.neueTobiesVerwerfen(n.uid)}>Verwerfen</button></div>` : nothing}</div>`)
          : html`<p class="leer">Keine neuen Tobies. Lege einen unbekannten Tobie auf eine Box, dann erscheint er hier.</p>`}
        ${s.neueTobies.eintraege.length < s.neueTobies.gesamt ? html`<button class="zweit" @click=${() => this.store.weiter('neueTobies')}>Mehr laden</button>` : nothing}
        ${w && this.store.has('lernmodus') ? this._lernKarte() : nothing}
        ${w ? html`<button class="zweit" ?disabled=${gesperrt} @click=${() => this.store.kennungVonHand()}>Kennung von Hand eingeben</button>` : nothing}
        <h2>Zugeordnete Tobies</h2>
        ${s.zuordnungen.liste.length ? s.zuordnungen.liste.map((z) => html`<div class="karte">
          <div class="titel">${z.name || kurz(z.uid)}</div>
          <div class="meta">${z.name ? kurz(z.uid) + ' · ' : ''}${this._zielText(z.ziel, z)}</div>
          ${z.folge_vorhanden === false ? html`<span class="marke warnm">Folge fehlt</span>` : nothing}
          ${z.ziel.typ !== 'aktion' && z.serie_name == null ? html`<span class="marke warnm">Serie fehlt</span>` : nothing}
          ${w ? html`<div class="reihe">
            <button class="zweit" ?disabled=${gesperrt} @click=${() => this.store.tobieUmbenennen(z)}>Name</button>
            <button class="zweit" ?disabled=${gesperrt} @click=${() => this.store.zuordnen(z.uid, z.ziel, z.name || '')}>Ziel ändern</button>
            <button class="gefahr" ?disabled=${gesperrt} @click=${() => this.store.zuordnungLoesen(z)}>Lösen</button></div>` : nothing}</div>`)
          : html`<p class="leer">Noch keine Zuordnungen.</p>`}
        ${s.zuordnungen.liste.length < s.zuordnungen.gesamt ? html`<button class="zweit" @click=${() => this.store.weiter('zuordnungen')}>Mehr laden</button>` : nothing}`;
    }
    _lernKarte() {
      const s = this._s;
      return html`<h2>Lernmodus</h2><div class="karte">
        <p>Die Box lernt den nächsten aufgelegten Tobie und ordnet ihn dem gewählten Ziel zu.</p>
        <button ?disabled=${this._gesperrt} @click=${() => this.store.lernStart()}>Neuen Tobie lernen</button>
        ${Object.values(s.lern).map((v) => html`<div class="lern ${v.zustand}">
          <b>${v.box}</b>: ${LERN_ZUSTAND[v.zustand] || v.zustand}
          ${v.text ? html`<div class="meta">${v.text}</div>` : nothing}
          <div class="meta">${this._zielText(v.ziel)}</div>
          <div class="reihe">${v.ende ? html`<button class="zweit" @click=${() => this.store.lernVergessen(v.box)}>Schließen</button>`
            : html`<button class="gefahr" @click=${() => this.store.lernAbbrechen(v.box)}>Abbrechen</button>`}</div></div>`)}
      </div>`;
    }
    _rueckfrageLern() {
      const v = this.store.offeneRueckfrage();
      if (!v) return nothing;
      return html`<div class="schleier"><div class="dialog" role="alertdialog" aria-modal="true">
        <h2>Zuordnung überschreiben?</h2>
        <p>Dieser Tobie (${kurz(v.uid)}) hat schon ein Ziel: ${this._zielText(v.bisher)}.</p>
        <p>Neu wäre: ${this._zielText(v.ziel)}.</p>
        <p class="meta">Antworte bis ${zeitKurz(v.rueckfrage_bis)}.</p>
        <div class="reihe">
          <button class="gefahr" @click=${() => this.store.lernAntwort(v.befehl_id, true)}>Überschreiben</button>
          <button class="zweit" @click=${() => this.store.lernAntwort(v.befehl_id, false)}>Behalten</button></div></div></div>`;
    }

    /* -- Boxen */
    _viewBoxen() {
      const s = this._s;
      return html`
        ${s.boxen.map((b) => this._boxKarte(b))}
        ${this._listeKarte()}
        <p class="klein-text">Integration ${s.version}</p>`;
    }
    _boxKarte(b) {
      const w = this._kannSchreiben;
      return html`<div class="karte">
          <div class="titel"><span class="punkt ${b.online ? 'on' : (b.online === false ? 'off' : 'unb')}"></span> ${b.anzeigename || b.box}</div>
          <div class="meta">${b.online ? 'online' : (b.online === false ? 'offline' : 'unbekannt')} · <span class="stand ${b.konfig_stand}">${KONFIG_STAND[b.konfig_stand] || b.konfig_stand}</span></div>
          ${b.status ? html`<div class="meta">Freier Speicher: ${b.status.speicher_frei_mb != null ? `${b.status.speicher_frei_mb} MB` : '–'}
            ${b.status.netz != null ? html` · Netz: ${typeof b.status.netz === 'object' ? (b.status.netz.klasse || b.status.netz.name || '') : b.status.netz}` : nothing}
            ${b.status.akku_prozent != null ? html` · Akku: ${b.status.akku_prozent} %` : nothing}
            ${b.status.version ? html` · Version ${b.status.version}` : nothing}</div>
            ${b.status.sync ? html`<div class="meta">Sync: ${b.status.sync.ergebnis || b.status.sync.zustand || ''}${b.status.sync.grund ? ` (${b.status.sync.grund})` : ''}</div>` : nothing}
            ${b.status.letzter_fehler ? html`<div class="marke warnm blockm">${typeof b.status.letzter_fehler === 'string' ? b.status.letzter_fehler : (b.status.letzter_fehler.text || b.status.letzter_fehler.code || '')}</div>` : nothing}` : nothing}
          ${b.konfig_stand === 'voraus' ? html`<div class="marke warnm blockm">Diese Box hat einen neueren Stand als HA. Bitte „Liste neu ausrollen“.</div>` : nothing}
          ${b.ereignisse?.length ? html`<details><summary>Letzte Meldungen (${b.ereignisse.length})</summary>
            ${b.ereignisse.map((e) => html`<div class="meta">${zeitKurz(e.ts)} · ${e.text || e.art}</div>`)}</details>` : nothing}
          ${w ? html`<div class="reihe"><button ?disabled=${b.online !== true} @click=${() => this.store.boxSync(b.box)}>Sync jetzt</button></div>` : nothing}
        </div>`;
    }
    _listeKarte() {
      const s = this._s; const w = this._kannSchreiben; const k = s.konfig;
      return k ? html`<div class="karte"><h2>Liste der Tobies</h2>
          <div class="meta">Revision ${k.revision ?? '–'} · Export ${k.export_ok ? `ok (${zeitKurz(k.export_geschrieben_am)})` : 'fehlt'}</div>
          ${w ? html`<div class="reihe"><button class="gefahr" @click=${() => this.store.listeNeuAusrollen()}>Liste neu ausrollen</button>
            <button class="zweit" @click=${() => this.store.exportLesen()}>Export ansehen</button></div>` : nothing}
          ${s.exportInfo ? html`<div class="meta">${s.exportInfo.vorhanden ? `Export: Revision ${s.exportInfo.revision}, ${zeitKurz(s.exportInfo.exportiert_am)}, ${plural(s.exportInfo.anzahl_zuordnungen ?? 0, 'Zuordnung', 'Zuordnungen')}${s.exportInfo.neuer_als_ha ? ' (neuer als HA)' : ''}` : 'Kein Export vorhanden.'}</div>` : nothing}
        </div>` : nothing;
    }

    /* -- Papierkorb */
    _viewKorb() {
      const p = this._s.papierkorb; const w = this._kannSchreiben;
      return html`
        ${w && p.gesamt ? html`<button class="gefahr" @click=${() => this.store.papierkorbLeeren()}>Papierkorb leeren (${p.gesamt})</button>` : nothing}
        ${p.eintraege.length ? p.eintraege.map((e) => html`<div class="karte">
          <div class="titel">${e.anzeige}</div>
          <div class="meta">${({ folge: 'Folge', serie: 'Serie', eingang: 'Eingang' })[e.typ] || e.typ}${e.serie_name ? ` aus „${e.serie_name}“` : ''} · ${plural(e.tracks, 'Datei', 'Dateien')} · ${groesse(e.groesse_bytes)} · ${zeitKurz(e.geloescht_am)}</div>
          ${w ? html`<div class="reihe"><button @click=${() => this.store.papierkorbWiederherstellen(e)}>Wiederherstellen</button>
            ${e.typ === 'folge' ? html`<button class="zweit" @click=${() => this.store.papierkorbWiederherstellen(e, { andere: true })}>In andere Serie …</button>` : nothing}</div>` : nothing}</div>`)
          : html`<p class="leer">Der Papierkorb ist leer.</p>`}
        ${p.eintraege.length < p.gesamt ? html`<button class="zweit" @click=${() => this.store.weiter('papierkorb')}>Mehr laden</button>` : nothing}`;
    }

    /* -- Einstellungen (AP 4.7) */
    _viewEinstellungen() {
      const st = this.store; const s = this._s; const w = this._kannSchreiben; const gesperrt = this._gesperrt || !w;
      const zurueck = this.eingebettet ? nothing : html`<button class="zweit" @click=${() => st.zeige('serien')}>‹ Zurück</button>`;
      const titel = this.eingebettet ? nothing : html`<h2>Einstellungen</h2>`;
      if (!s.einstellungen.geladen) return html`${zurueck}${titel}<p class="leer">Lade …</p>`;
      const lz = st.leiseAnzeige; const gn = st.guteAnzeige; const tage = st.lesezeichenAnzeige;
      const gea = st.einstellungenGeaendert;
      return html`
        ${zurueck}
        ${titel}
        ${this._gesperrt ? html`<div class="banner info">Änderungen sind gesperrt, bis die Warnung oben geklärt ist.</div>` : nothing}

        <div class="karte" id="leise">
          <h2>Leise-Zeiten</h2>
          <p class="meta">In diesen Zeiten spielt die Box leiser oder gar nicht. Ein Fenster gehört zu dem Tag, an dem es beginnt.</p>
          <label>Zeitzone
            <input type="text" id="zeitzone" .value=${lz.zeitzone} ?disabled=${gesperrt} autocapitalize="off" autocomplete="off" spellcheck="false"
              @input=${(e) => st.zeitzoneSetzen(e.target.value)}></label>
          ${lz.fenster.length ? lz.fenster.map((f, i) => this._fenster(f, i, gesperrt)) : html`<p class="leer">Keine Leise-Zeiten. Die Box spielt immer in der normalen Lautstärke.</p>`}
          <div class="reihe">
            <button class="zweit" id="fenster-neu" ?disabled=${gesperrt || lz.fenster.length >= EINSTELLUNG_GRENZEN.fensterMax} @click=${() => st.fensterNeu()}>Fenster hinzufügen</button>
          </div>
          ${this._speichern(gea.leise, gesperrt, () => st.leiseSpeichern(), () => st.entwurfVerwerfen('leise'), 'leise-speichern')}
        </div>

        <div class="karte" id="gute-nacht">
          <h2>Gute Nacht</h2>
          <p class="meta">Mit der Gute-Nacht-Karte läuft ein Timer. Danach wird die Box leiser und hört auf.</p>
          <label>Timer in Minuten (1 bis 240)
            <input type="number" inputmode="numeric" id="timer-min" min="1" max="240" step="1" .value=${String(gn.timer_min)} ?disabled=${gesperrt}
              @input=${(e) => st.guteNachtSetzen('timer_min', e.target.value)}></label>
          <label>Ausblenden in Sekunden (5 bis 600)
            <input type="number" inputmode="numeric" id="ausblenden-s" min="5" max="600" step="1" .value=${String(gn.ausblenden_s)} ?disabled=${gesperrt}
              @input=${(e) => st.guteNachtSetzen('ausblenden_s', e.target.value)}></label>
          ${this._speichern(gea.gute, gesperrt, () => st.guteNachtSpeichern(), () => st.entwurfVerwerfen('gute'), 'gute-speichern')}
        </div>

        <div class="karte" id="lesezeichen">
          <h2>Lesezeichen</h2>
          <p class="meta">Wurde ein Tobie so viele Tage nicht gespielt, beginnt er die Folge wieder von vorn. 0 heißt: nie.</p>
          <label>Tage (0 bis 365)
            <input type="number" inputmode="numeric" id="lesezeichen-tage" min="0" max="365" step="1" .value=${String(tage)} ?disabled=${gesperrt}
              @input=${(e) => st.lesezeichenSetzen(e.target.value)}></label>
          ${this._speichern(gea.lesezeichen, gesperrt, () => st.lesezeichenSpeichern(), () => st.entwurfVerwerfen('lesezeichen'), 'lesezeichen-speichern')}
        </div>`;
    }
    _speichern(geaendert, gesperrt, speichern, verwerfen, id) {
      return html`<div class="reihe">
        <button id=${id} ?disabled=${gesperrt || !geaendert} @click=${speichern}>Speichern</button>
        ${geaendert ? html`<button class="zweit" @click=${verwerfen}>Verwerfen</button>` : nothing}
      </div>`;
    }
    _fenster(f, i, gesperrt) {
      const st = this.store; const leiser = f.wirkung === 'leiser';
      const alle = [1, 2, 3, 4, 5, 6, 7]; const wochentags = [1, 2, 3, 4, 5]; const wochenende = [6, 7];
      const gleich = (a, b) => a.length === b.length && a.every((t, k) => t === b[k]);
      return html`<div class="fenster" data-fenster=${i}>
        <div class="zeile2"><b class="grow">Fenster ${i + 1}</b>
          <button class="gefahr klein" ?disabled=${gesperrt} aria-label="Fenster ${i + 1} löschen" @click=${() => st.fensterLoeschen(i)}>Löschen</button></div>
        <div class="tage" role="group" aria-label="Wochentage">
          ${WOCHENTAGE.map(([n, kurzName, lang]) => html`<button class="tag ${f.tage.includes(n) ? 'an' : ''}" aria-pressed=${f.tage.includes(n) ? 'true' : 'false'}
            aria-label=${lang} data-tag=${n} ?disabled=${gesperrt} @click=${() => st.tagUmschalten(i, n)}>${kurzName}</button>`)}
        </div>
        <div class="reihe schnell">
          <button class="zweit klein ${gleich(f.tage, alle) ? 'aktiv' : ''}" ?disabled=${gesperrt} @click=${() => st.tageSetzen(i, alle)}>Alle</button>
          <button class="zweit klein ${gleich(f.tage, wochentags) ? 'aktiv' : ''}" ?disabled=${gesperrt} @click=${() => st.tageSetzen(i, wochentags)}>Mo–Fr</button>
          <button class="zweit klein ${gleich(f.tage, wochenende) ? 'aktiv' : ''}" ?disabled=${gesperrt} @click=${() => st.tageSetzen(i, wochenende)}>Sa, So</button>
        </div>
        <div class="zeiten">
          <label>von<input type="time" class="von" step="60" .value=${f.von} ?disabled=${gesperrt} @input=${(e) => st.fensterAendern(i, { von: e.target.value })}></label>
          <label>bis<input type="time" class="bis" step="60" .value=${f.bis} ?disabled=${gesperrt} @input=${(e) => st.fensterAendern(i, { bis: e.target.value })}></label>
        </div>
        ${ueberMitternacht(f) ? html`<p class="meta">Reicht über Mitternacht bis zum nächsten Tag.</p>` : nothing}
        <div class="reihe" role="group" aria-label="Wirkung">
          <button class="wirkung-leiser ${leiser ? '' : 'zweit'}" aria-pressed=${leiser ? 'true' : 'false'} ?disabled=${gesperrt} @click=${() => st.fensterAendern(i, { wirkung: 'leiser' })}>Leiser</button>
          <button class="wirkung-stumm ${leiser ? 'zweit' : ''}" aria-pressed=${leiser ? 'false' : 'true'} ?disabled=${gesperrt} @click=${() => st.fensterAendern(i, { wirkung: 'stumm' })}>Stumm</button>
        </div>
        ${leiser ? html`<label>Höchste Lautstärke: ${f.grenze} %
          <input type="range" class="grenze" min="0" max="100" step="1" .value=${String(f.grenze)} ?disabled=${gesperrt}
            @input=${(e) => st.fensterAendern(i, { grenze: Number(e.target.value) })}></label>`
          : html`<p class="meta">Die Box spielt nicht. Ein leiser Ton zeigt, dass der Tobie erkannt wurde.</p>`}
      </div>`;
    }

    /* -- Eingebettet in „Technik“ (A12/A13, Design 5.9): ohne Kopf und Reiterleiste, nur der Bereich aus `bereich`.
     * `bereich`: boxen (Karten der Boxen; mit `box` nur diese Box), liste (Stand der Liste, Export), aufraeumen (neue Serie,
     * Überraschungs-Serie), eingang, papierkorb, tobies (Kennung von Hand, Lernmodus, Zuordnungen), einstellungen, meldungen
     * (Protokoll der Boxen mit Codes) oder alle (Vorgabe: alle nacheinander mit Überschrift). Die Warnleisten zur Liste zeigt
     * dann die Technik-Seite selbst. */
    static BEREICHE = {
      boxen: 'Boxen', liste: 'Liste der Tobies', aufraeumen: 'Bibliothek aufräumen', eingang: 'Eingang', papierkorb: 'Papierkorb',
      tobies: 'Tobies', einstellungen: 'Einstellungen', meldungen: 'Meldungen',
    };
    _renderEingebettet() {
      const s = this._s;
      const namen = TobiboxPanel.BEREICHE;
      const einzeln = namen[this.bereich] ? this.bereich : null;
      return html`
        <div class="app eingebettet" data-bereich=${einzeln || 'alle'}>
          <main>
            ${s.reloadNoetig ? html`<div class="banner err" role="alert">Bitte die Seite neu laden (Strg+F5).</div>` : nothing}
            ${this._bannerFehler()}${this._bannerHinweis()}
            ${!s.bereit && !s.reloadNoetig ? html`<p class="leer">Lade …</p>`
              : (einzeln ? this._bereich(einzeln) : Object.keys(namen).map((k) => html`<section data-bereich-teil=${k}><h2>${namen[k]}</h2>${this._bereich(k)}</section>`))}
          </main>
          ${this._dialog()}${this._rueckfrageLern()}
        </div>`;
    }
    _bereich(b) {
      const s = this._s;
      switch (b) {
        case 'boxen': return html`${s.boxen.filter((x) => !this.box || x.box === this.box).map((x) => this._boxKarte(x))}
          ${s.boxen.length ? nothing : html`<p class="leer">Keine Boxen eingerichtet.</p>`}`;
        case 'liste': return html`${this._listeKarte()}<p class="klein-text">Integration ${s.version}</p>`;
        case 'aufraeumen': return this._viewAufraeumen();
        case 'eingang': return this._viewEingang();
        case 'papierkorb': return this._viewKorb();
        case 'tobies': return this._viewTobies();
        case 'einstellungen': return this._viewEinstellungen();
        default: return this._viewMeldungen();
      }
    }
    _viewAufraeumen() {
      const s = this._s; const w = this._kannSchreiben;
      return html`
        ${w && s.ueberraschung === 'fehlt' ? html`<div class="karte"><p>Es gibt noch keine Überraschungs-Serie. Die Box spielt sonst bei unbekannten Tobies einen Fehlerton.</p>
          <button @click=${() => this.store.serieAnlegen('ueberraschung')}>Überraschungs-Serie anlegen</button></div>` : nothing}
        ${s.ueberraschung === 'mehrere' ? html`<div class="banner warn">Es gibt mehr als eine Überraschungs-Serie.</div>` : nothing}
        ${s.ueberraschung === 'leer' ? html`<div class="banner info">Die Überraschungs-Serie ist noch leer.</div>` : nothing}
        ${w ? html`<div class="reihe"><button class="zweit" @click=${() => this.store.serieAnlegen()}>Neues leeres Hörspiel</button></div>` : nothing}`;
    }
    _viewMeldungen() {
      const s = this._s;
      const mit = s.boxen.filter((b) => b.ereignisse?.length);
      return html`${mit.length ? mit.map((b) => html`<div class="karte" data-meldungen=${b.box}>
          <div class="titel">${b.anzeigename || b.box}</div>
          ${b.ereignisse.map((e) => html`<div class="meta">${zeitKurz(e.ts)} · <span class="marke">${e.art}</span> ${e.text || ''}</div>`)}</div>`)
        : html`<p class="leer">Keine Meldungen von den Boxen.</p>`}`;
    }

    /* -- Dialoge */
    _dialog() {
      const d = this._dlg;
      if (!d) return nothing;
      const o = d.opts;
      const abbruch = html`<button class="zweit" @click=${() => this._zu(d.kind === 'confirm' ? false : null)}>Abbrechen</button>`;
      if (d.kind === 'confirm') {
        return html`<div class="schleier"><div class="dialog" role="alertdialog" aria-modal="true">
          <h2>${o.titel}</h2><p>${o.text}</p>
          ${o.liste?.length ? html`<ul>${o.liste.map((x) => html`<li>${x}</li>`)}</ul>` : nothing}
          <div class="reihe"><button class="${o.gefahr ? 'gefahr' : ''}" @click=${() => this._zu(true)}>${o.ja || 'Ja'}</button>${abbruch}</div></div></div>`;
      }
      if (d.kind === 'prompt') {
        return html`<div class="schleier"><form class="dialog" @submit=${(e) => { e.preventDefault(); const t = d.werte.text.trim(); if (t || o.leerErlaubt) this._zu(t); }}>
          <h2>${o.titel}</h2>
          <label>${o.label}<input type="text" .value=${d.werte.text} maxlength=${o.max || 100} autofocus
            @input=${(e) => { d.werte.text = e.target.value; }}></label>
          <div class="reihe"><button type="submit">${o.ja || 'OK'}</button>${abbruch}</div></form></div>`;
      }
      if (d.kind === 'serie') {
        const serien = this._s.serien.filter((x) => !(o.ausser || []).includes(x.id) && (!o.nurNormal || x.typ === 'normal'));
        return html`<div class="schleier"><div class="dialog">
          <h2>${o.titel}</h2>
          <label>Serie<select @change=${(e) => { d.werte.serie = e.target.value; this.requestUpdate(); }}>
            <option value="">Bitte wählen</option>
            ${serien.map((x) => html`<option value=${x.id} ?selected=${d.werte.serie === x.id}>${x.name}</option>`)}</select></label>
          <div class="reihe"><button ?disabled=${!d.werte.serie} @click=${() => this._zu(d.werte.serie)}>Weiter</button>${abbruch}</div></div></div>`;
      }
      return this._zielDialog(d, abbruch);
    }
    _zielDialog(d, abbruch) {
      const o = d.opts; const v = d.werte; const s = this._s;
      const serien = s.serien.filter((x) => x.typ === 'normal');
      const set = (k, val, laden) => { v[k] = val; if (laden) this._ladeFolgen(d); this.requestUpdate(); };
      const okZiel = v.typ === 'aktion' || (v.typ === 'serie' && v.serie) || (v.typ === 'folge' && v.serie && v.folge);
      const fertig = () => {
        const ziel = v.typ === 'aktion' ? { typ: 'aktion', aktion: v.aktion }
          : v.typ === 'serie' ? { typ: 'serie', serie: v.serie } : { typ: 'folge', serie: v.serie, folge: v.folge };
        this._zu({ ziel, name: v.name.trim() || null, box: v.box });
      };
      return html`<div class="schleier"><div class="dialog">
        <h2>${o.titel}</h2>
        ${o.mitBox ? html`<label>Box<select @change=${(e) => set('box', e.target.value)}>
          ${s.boxenNamen.map((b) => html`<option value=${b} ?selected=${v.box === b}>${b}</option>`)}</select></label>` : nothing}
        <div class="reihe">
          ${[['serie', 'Serie'], ['folge', 'Einzelne Folge'], ...(o.aktion ? [['aktion', 'Aktion']] : [])].map(([t, n]) => html`
            <button class="${v.typ === t ? '' : 'zweit'}" @click=${() => set('typ', t, t === 'folge')}>${n}</button>`)}
        </div>
        ${v.typ === 'aktion' ? html`<label>Aktion<select @change=${(e) => set('aktion', e.target.value)}>
            ${Object.entries(AKTIONEN).map(([k, n]) => html`<option value=${k} ?selected=${v.aktion === k}>${n}</option>`)}</select></label>`
          : html`<label>Serie<select @change=${(e) => set('serie', e.target.value, v.typ === 'folge')}>
            <option value="">Bitte wählen</option>
            ${serien.map((x) => html`<option value=${x.id} ?selected=${v.serie === x.id}>${x.name}</option>`)}</select></label>
          ${v.typ === 'folge' ? html`<label>Folge<select @change=${(e) => set('folge', e.target.value)}>
            ${v.folgen.map((f) => html`<option value=${f.name} ?selected=${v.folge === f.name}>${f.anzeige}</option>`)}</select></label>` : nothing}`}
        ${o.mitName ? html`<label>Name des Tobies (freiwillig)<input type="text" .value=${v.name} maxlength=${s.grenzen.tobie_name_max || 60}
            @input=${(e) => { v.name = e.target.value; }}></label>` : nothing}
        <div class="reihe"><button ?disabled=${!okZiel} @click=${fertig}>Weiter</button>${abbruch}</div></div></div>`;
    }

    static styles = css`
      :host { display: block; background: var(--primary-background-color, #fafafa); color: var(--primary-text-color, #212121);
        min-height: 100vh; font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); font-size: 16px; }
      * { box-sizing: border-box; }
      .app { max-width: 720px; margin: 0 auto; padding-bottom: 88px; }
      header { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: var(--app-header-background-color, var(--primary-color, #03a9f4));
        color: var(--app-header-text-color, #fff); position: sticky; top: 0; z-index: 5; }
      h1 { font-size: 20px; margin: 0; font-weight: 500; }
      h2 { font-size: 17px; margin: 16px 0 8px; font-weight: 500; }
      main { padding: 8px 16px; }
      .grow { flex: 1; }
      .karte { background: var(--card-background-color, #fff); border: 1px solid var(--divider-color, #e0e0e0); border-radius: 12px;
        padding: 12px 14px; margin: 10px 0; display: block; width: 100%; text-align: left; color: inherit; font: inherit; }
      .karte h2 { margin-top: 0; }
      button.karte.zeile { cursor: pointer; display: flex; flex-direction: column; gap: 4px; min-height: 64px; }
      .titel { font-weight: 500; overflow-wrap: anywhere; }
      .meta, .klein-text { color: var(--secondary-text-color, #727272); font-size: 14px; overflow-wrap: anywhere; }
      .leer { color: var(--secondary-text-color, #727272); text-align: center; padding: 24px 0; }
      .reihe { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 2px; }
      button { min-height: 48px; min-width: 48px; padding: 0 16px; border-radius: 10px; border: 0; cursor: pointer; font: inherit; font-weight: 500;
        background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); flex: 1 1 auto; }
      button.zweit { background: transparent; color: var(--primary-color, #03a9f4); border: 1px solid var(--primary-color, #03a9f4); }
      button.gefahr { background: var(--error-color, #db4437); color: #fff; border: 0; }
      button.klein { min-height: 36px; flex: 0 0 auto; }
      button.icon { flex: 0 0 auto; background: transparent; color: inherit; font-size: 22px; }
      button:disabled { opacity: .45; cursor: default; }
      .banner { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 12px 14px; border-radius: 10px; margin: 10px 0; }
      .banner > .reihe { width: 100%; }
      .banner.err { background: var(--error-color, #db4437); color: #fff; }
      .banner.warn { background: var(--warning-color, #ffa600); color: #212121; }
      .banner.info { background: var(--info-color, var(--secondary-background-color, #e8f0fe)); color: var(--primary-text-color, #212121); }
      .marke { display: inline-block; font-size: 12px; padding: 2px 8px; border-radius: 10px; background: var(--secondary-background-color, #eee); margin: 2px 4px 2px 0; }
      .marke.warnm { background: var(--warning-color, #ffa600); color: #212121; }
      .marke.blockm { display: block; border-radius: 6px; padding: 6px 8px; }
      label { display: block; margin: 10px 0; font-size: 14px; color: var(--secondary-text-color, #727272); }
      label.check { display: flex; gap: 8px; align-items: center; color: var(--primary-text-color, #212121); font-size: 15px; min-height: 44px; }
      input[type=text], input[type=number], input[type=time], select { width: 100%; min-height: 48px; margin-top: 4px; font: inherit; padding: 0 10px; border-radius: 8px;
        border: 1px solid var(--divider-color, #bbb); background: var(--card-background-color, #fff); color: var(--primary-text-color, #212121); }
      label.datei input { display: block; margin-top: 8px; width: 100%; }
      progress { width: 100%; height: 10px; }
      .upload { margin: 8px 0; } .upload.fehler .meta, .upload.unklar .meta { color: var(--error-color, #db4437); }
      .zeile2 { display: flex; gap: 10px; align-items: baseline; }
      .nr { color: var(--secondary-text-color, #727272); min-width: 1.6em; }
      .folge.zieht { opacity: .5; }
      .ergebnis { margin: 8px 0; padding-top: 8px; border-top: 1px solid var(--divider-color, #e0e0e0); }
      .lern { margin-top: 12px; padding-top: 8px; border-top: 1px solid var(--divider-color, #e0e0e0); }
      .punkt { display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--disabled-text-color, #999); }
      .punkt.on { background: var(--success-color, #43a047); } .punkt.off { background: var(--error-color, #db4437); }
      .stand.veraltet, .stand.voraus { color: var(--warning-color, #ffa600); font-weight: 500; }
      nav { position: fixed; left: 0; right: 0; bottom: 0; display: flex; background: var(--card-background-color, #fff);
        border-top: 1px solid var(--divider-color, #e0e0e0); padding-bottom: env(safe-area-inset-bottom); z-index: 6; }
      nav .tab { flex: 1; min-height: 56px; border-radius: 0; background: transparent; color: var(--secondary-text-color, #727272); padding: 0 4px; font-size: 14px; }
      nav .tab.aktiv { color: var(--primary-color, #03a9f4); border-top: 3px solid var(--primary-color, #03a9f4); }
      .badge { margin-left: 4px; background: var(--error-color, #db4437); color: #fff; border-radius: 10px; padding: 0 6px; font-size: 12px; }
      .schleier { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: flex-end; justify-content: center; z-index: 20; }
      .dialog { background: var(--card-background-color, #fff); color: var(--primary-text-color, #212121); width: 100%; max-width: 560px;
        border-radius: 16px 16px 0 0; padding: 16px; max-height: 90vh; overflow: auto; }
      @media (min-width: 600px) { .schleier { align-items: center; } .dialog { border-radius: 16px; } }
      .spin { width: 18px; height: 18px; border: 3px solid rgba(255,255,255,.4); border-top-color: #fff; border-radius: 50%; animation: dreh 1s linear infinite; }
      @keyframes dreh { to { transform: rotate(360deg); } }
      ul { margin: 6px 0; padding-left: 20px; }
      button.icon.aktiv { background: rgba(255,255,255,.25); }
      .fenster { border-top: 1px solid var(--divider-color, #e0e0e0); margin-top: 12px; padding-top: 8px; }
      .tage { display: flex; gap: 4px; margin: 8px 0; }
      .tage .tag { flex: 1 1 0; min-width: 0; padding: 0; background: transparent; color: var(--primary-text-color, #212121); border: 1px solid var(--divider-color, #bbb); }
      .tage .tag.an { background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); border-color: var(--primary-color, #03a9f4); }
      .reihe.schnell { margin-top: 0; }
      .fenster button.klein { min-height: 44px; }
      button.klein.aktiv { background: var(--secondary-background-color, #eee); }
      .zeiten { display: flex; gap: 12px; } .zeiten label { flex: 1 1 0; min-width: 0; }
      input[type=range] { width: 100%; min-height: 48px; margin-top: 4px; }
      :host([eingebettet]) { min-height: 0; background: transparent; }
      :host([eingebettet]) .app { padding-bottom: 0; max-width: none; }
      :host([eingebettet]) main { padding: 0; }
      :host([eingebettet]) .app > .schleier, :host([eingebettet]) .schleier { z-index: 30; }
      :host([eingebettet]) summary { min-height: 44px; display: flex; align-items: center; cursor: pointer; }
    `;
  }

  if (!customElements.get('tobibox-panel')) customElements.define('tobibox-panel', TobiboxPanel);
}

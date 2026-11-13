/* Seite „Geräte“ (Design 3.4, 5.1.1, 5.8, Paket A7b): Status-Karten der Boxen und der Abschnitt „Abends“.
 *
 * Von oben nach unten: Karten der Boxen (ein Satz je Box, ganze Karte ist ein Link auf `#box-<id>`), ein Platz für die
 * Karten „Neuer Tobie aufgelegt“ und die Warteschlange (A9/A10), dann „Abends“ mit der Karte „Gute Nacht“ (Schnellwahl,
 * „Anderer Wert“, Speichern) und der Karte „Leise-Zeiten“ (Wochenansicht, Satz „Jetzt: …“, „+ Leise-Zeit“, Blatt zum Anlegen,
 * Ändern und Löschen). Die Zeile „Wer hat was gehört?“ ist Stufe B (Fähigkeit `gehoert`, Paket B5) und fehlt hier.
 *
 * Daten: Boxen kommen live aus dem Speicher der App (`ctx.boxen()`, Vertrag `boxen/list` und Ereignisse), die Namen der
 * spielenden Serie und Folge holt die Seite einmal je Serie mit `serie/get`. Einstellungen: `einstellungen/get` und
 * `einstellungen/set` (Vertrag 3.11). Jede Änderung sendet `erwartet_revision` (Fähigkeit `bibliothek`); ein Nicht-Administrator
 * sendet die Zeitzone nicht (das Backend ignoriert sie), ein Administrator schickt den gespeicherten Wert unverändert zurück, damit
 * sie nicht auf `Europe/Berlin` zurückfällt. Schnittstelle zur App: siehe bausteine.js.
 */
import { html, nothing, css, ic, cover, segment, ladeMitGrenze } from '../bausteine.js';
import { GERAETE, GERAETE_SEITE, ABENDS, LEISE, SEITE, statusSatz, fuellen } from '../texte.js';

export const TAGE = [1, 2, 3, 4, 5, 6, 7]; // ISO: 1 Montag bis 7 Sonntag
export const MAX_FENSTER = 32;
export const SCHNELLWAHL_MIN = [15, 30, 45, 60, 90];
export const ANDERE_MIN = [5, 10, 20, 120, 180, 240]; // „Anderer Wert …“, Design 5.8: 5 bis 240 Minuten
export const ABWEICHUNG_MS = 5 * 60 * 1000; // U23d: Satz zu neuen Zuordnungen erst nach 5 Minuten Abweichung

/* ------------------------------------------------------------------ reine Funktionen */

const zwei = (n) => String(n).padStart(2, '0');

/* „06:30“ → „6:30“, „19:30“ → „19:30“ (Design 5.8: „leiser bis 7:00“). */
export function uhrzeit(hhmm) {
  const [h, m] = String(hhmm).split(':');
  return `${Number(h)}:${m}`;
}

/* „HH:MM“ → Minuten seit Mitternacht. */
export function minuten(hhmm) {
  const [h, m] = String(hhmm).split(':').map(Number);
  return h * 60 + m;
}

/* Wochentag (1 bis 7) und Minuten seit Mitternacht in der Zeitzone der Leise-Zeiten (so rechnet auch die Box). */
export function jetztInZone(zone, datum = new Date()) {
  let teile = null;
  try {
    teile = new Intl.DateTimeFormat('en-US', { timeZone: zone, weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(datum);
  } catch { /* unbekannte Zone: Ortszeit */ }
  if (!teile) return { tag: ((datum.getDay() + 6) % 7) + 1, min: datum.getHours() * 60 + datum.getMinutes() };
  const wert = (t) => teile.find((p) => p.type === t)?.value;
  const tag = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 7 }[wert('weekday')] ?? 1;
  return { tag, min: (Number(wert('hour')) % 24) * 60 + Number(wert('minute')) };
}

/* Abschnitte der Wochenansicht je Wochentag. Ein Fenster gehört zu dem Tag, an dem es beginnt; reicht es über Mitternacht
 * (`bis` < `von`), läuft es am nächsten Tag von 0 Uhr bis `bis` weiter (`fortsetzung`, `vontag`). Minuten 0 bis 1440. */
export function leiseAbschnitte(fenster) {
  const tage = Object.fromEntries(TAGE.map((d) => [d, []]));
  for (const w of fenster || []) {
    const a = minuten(w.von);
    const b = minuten(w.bis);
    for (const d of w.tage) {
      if (!tage[d]) continue;
      if (b > a) tage[d].push({ w, a, b, fortsetzung: false });
      else {
        tage[d].push({ w, a, b: 1440, fortsetzung: false, ueberMitternacht: true });
        tage[(d % 7) + 1].push({ w, a: 0, b, fortsetzung: true, vontag: d });
      }
    }
  }
  return tage;
}

/* Satz zum Jetzt (Design 5.8): { text, art: 'still' | 'leiser' | 'normal' }. „Still“ geht vor „Leiser“. */
export function jetztSatz(abschnitte, jetzt) {
  const heute = abschnitte[jetzt.tag] || [];
  let beste = null;
  for (const g of heute) if (jetzt.min >= g.a && jetzt.min < g.b && (!beste || (g.w.wirkung === 'stumm' && beste.w.wirkung !== 'stumm'))) beste = g;
  if (beste) {
    let ende = beste.b;
    if (ende === 1440) {
      const weiter = (abschnitte[(jetzt.tag % 7) + 1] || []).find((x) => x.fortsetzung && x.w === beste.w);
      if (weiter) ende = weiter.b;
    }
    const bis = uhrzeit(`${zwei(Math.floor((ende % 1440) / 60))}:${zwei(ende % 60)}`);
    return beste.w.wirkung === 'stumm'
      ? { text: fuellen(ABENDS.leise.jetzt_still, { bis }), art: 'still' }
      : { text: fuellen(ABENDS.leise.jetzt_leiser, { bis }), art: 'leiser' };
  }
  const naechste = heute.filter((g) => g.a > jetzt.min).sort((x, y) => x.a - y.a)[0];
  return naechste
    ? { text: fuellen(ABENDS.leise.jetzt_normal, { von: uhrzeit(naechste.w.von) }), art: 'normal' }
    : { text: ABENDS.leise.jetzt_normal_ohne, art: 'normal' };
}

/* „Mo, Di, Mi, Do, So“ (Reihenfolge Mo bis So), für den Satz „Gilt für …“. */
export function tageListe(tage) {
  return TAGE.filter((d) => tage.includes(d)).map((d) => ABENDS.leise.tage[d]).join(', ');
}

/* Kurzform mit Bereichen für die Rückfrage beim Löschen: „Jeden Tag“, „Mo–Do, So“, „Fr, Sa“. */
export function tageKurz(tage) {
  const t = TAGE.filter((d) => tage.includes(d));
  if (t.length === 7) return ABENDS.leise.jeden_tag;
  const teile = [];
  for (let i = 0; i < t.length;) {
    let j = i;
    while (j + 1 < t.length && t[j + 1] === t[j] + 1) j += 1;
    teile.push(j - i >= 2 ? `${ABENDS.leise.tage[t[i]]}–${ABENDS.leise.tage[t[j]]}` : t.slice(i, j + 1).map((d) => ABENDS.leise.tage[d]).join(', '));
    i = j + 1;
  }
  return teile.join(', ');
}

/* Wert, den die Box im Fenster wirklich bekommt: `grenze` nur bei „leiser“ (Vertrag 3.11), Tage aufsteigend. */
export function fensterSenden(w) {
  const out = { id: w.id, tage: [...w.tage].sort((x, y) => x - y), von: w.von, bis: w.bis, wirkung: w.wirkung };
  if (w.wirkung === 'leiser') out.grenze = w.grenze ?? 25;
  return out;
}

/* Neue ID: 1 bis 32 Zeichen aus [a-z0-9_-], noch nicht vergeben. */
export function neueFensterId(vorhandene) {
  const belegt = new Set((vorhandene || []).map((w) => w.id));
  for (;;) {
    const id = `w${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
    if (!belegt.has(id)) return id;
  }
}

export const standardFenster = (vorhandene) => ({ id: neueFensterId(vorhandene), tage: [7, 1, 2, 3, 4], von: '19:30', bis: '06:30', wirkung: 'stumm', grenze: 25 });

/* „heute um 18:40“, „gestern um 8:05“, „am 08.11. um 20:00“ (Ortszeit des Geräts). */
export function zuletztText(iso, jetzt = new Date()) {
  const t = new Date(iso);
  if (!iso || Number.isNaN(t.getTime())) return '';
  const tag = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((tag(jetzt) - tag(t)) / 86400000);
  const uhr = `${t.getHours()}:${zwei(t.getMinutes())}`;
  const z = GERAETE_SEITE.zeit;
  if (diff === 0) return fuellen(z.heute, { uhr });
  if (diff === 1) return fuellen(z.gestern, { uhr });
  return fuellen(z.sonst, { datum: `${zwei(t.getDate())}.${zwei(t.getMonth() + 1)}.`, uhr });
}

/* ------------------------------------------------------------------ Status der Boxen (auch für die Detailseite) */

const dateiOhneEndung = (n) => String(n ?? '').replace(/\.[^./]+$/, '');

/* Hält je Seite, was zu den Karten gehört: Namen der spielenden Serie und Folge (einmal je Serie mit `serie/get`, Design 5.1.1)
 * und seit wann eine Box eine veraltete Liste hat (Satz „Neue Zuordnungen kommen …“ erst nach 5 Minuten, U23d). */
export class BoxStatus {
  constructor(ctx) {
    this.ctx = ctx;
    this.serien = new Map(); // id -> { phase, name, cover_stand, folgen: Map(name -> { anzeige, nummer }) }
    this.veraltetSeit = new Map(); // Box -> Zeit in ms
    this.jetzt = () => new Date();
    this._lauf = 0;
    this._timer = null;
  }

  zuruecksetzen() { this._lauf += 1; this.serien = new Map(); this.veraltetSeit = new Map(); this.stoppen(); }
  stoppen() { clearTimeout(this._timer); this._timer = null; }

  /* Wird nach jedem Zeichnen gerufen: lädt fehlende Namen, merkt Abweichungen, plant das nächste Zeichnen. */
  beobachte(boxen) {
    const jetztMs = this.jetzt().getTime();
    let wartet = Infinity;
    for (const box of boxen) {
      const sid = box.status?.serie?.id;
      if (box.online === true && sid && ['spielt', 'pausiert'].includes(box.status?.zustand) && !this.serien.has(sid)) this._hole(sid);
      if (box.online === true && box.konfig_stand === 'veraltet') {
        if (!this.veraltetSeit.has(box.box)) this.veraltetSeit.set(box.box, jetztMs);
        const rest = ABWEICHUNG_MS - (jetztMs - this.veraltetSeit.get(box.box));
        if (rest > 0) wartet = Math.min(wartet, rest);
      } else this.veraltetSeit.delete(box.box);
    }
    if (wartet !== Infinity && !this._timer) {
      this._timer = setTimeout(() => { this._timer = null; this.ctx.neuZeichnen(); }, wartet + 500);
      this._timer.unref?.();
    }
  }

  async _hole(sid) {
    const lauf = this._lauf;
    this.serien.set(sid, { phase: 'laedt', name: '', cover_stand: undefined, folgen: new Map() });
    try {
      const s = await ladeMitGrenze(this.ctx.api('tobibox/serie/get', { serie_id: sid }), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.ctx.covers?.merke?.([s]);
      this.serien.set(sid, {
        phase: 'bereit', name: s.name, cover_stand: s.cover_stand,
        folgen: new Map((s.folgen || []).map((f) => [f.name, { anzeige: f.anzeige, nummer: f.nummer ?? null }])),
      });
    } catch {
      if (lauf !== this._lauf) return;
      this.serien.set(sid, { phase: 'fehler', name: '', cover_stand: undefined, folgen: new Map() }); // Rückfall: Namen aus dem Status
    }
    this.ctx.neuZeichnen();
  }

  /* Alles, was die Karte und die Detailseite zeigen. */
  daten(box) {
    const st = box.status || null;
    const anzeige = box.anzeige || box.anzeigename || box.box;
    const sid = st?.serie?.id ?? null;
    const info = sid ? this.serien.get(sid) : null;
    const folgeName = st?.folge?.name ?? null;
    const fi = info?.folgen?.get(folgeName);
    const serieName = info?.name || st?.serie?.name || '';
    const folge = fi?.anzeige ?? dateiOhneEndung(folgeName);
    const seit = this.veraltetSeit.get(box.box);
    const jetzt = this.jetzt();
    const s = statusSatz({
      anzeige, online: box.online, zustand: st?.zustand, serie: serieName, folge, folge_nummer: fi?.nummer ?? null,
      akku_prozent: st?.akku_prozent, lader: st?.lader, zeit_letzte_meldung: zuletztText(box.status_empfangen_am, jetzt),
      konfig_stand: box.konfig_stand === 'veraltet' ? 'veraltet' : 'aktuell', // „voraus“ und „unbekannt“ sind kein Grund für den Satz
      abweichung_min: seit ? (jetzt.getTime() - seit) / 60000 : 0,
    });
    const spielt = box.online === true && sid && ['spielt', 'pausiert'].includes(st?.zustand);
    return {
      id: box.box, anzeige, online: box.online, lage: s.lage, satz: s.satz, nebentext: s.nebentext, warnung: s.warnung,
      cover: spielt ? { id: sid, name: serieName, cover_stand: info?.phase === 'bereit' ? info.cover_stand : this.ctx.covers?.stand?.(sid) } : null,
      serieName: spielt ? serieName : '', folge: spielt ? folge : '', nummer: spielt ? (fi?.nummer ?? null) : null,
      akku: typeof st?.akku_prozent === 'number' ? st.akku_prozent : null, lader: st?.lader === true,
      zuletzt: zuletztText(box.status_empfangen_am, jetzt),
    };
  }
}

const LAUTSPRECHER = 'M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z';

/* Karte der Box (Design 5.1.1): Cover oder Lautsprecher, ein Satz, Nebentext. `link`: die ganze Karte ist ein Link. */
export function boxKarte(d, { link = true } = {}) {
  const bild = d.cover ? cover(d.cover, 'md') : html`<div class="cover md ph" aria-hidden="true"><svg viewBox="0 0 24 24" width="30" height="30" focusable="false"><path d=${LAUTSPRECHER}></path></svg></div>`;
  const klasse = `gkarte gstatus${d.online === true ? '' : ' off'}`;
  const inhalt = html`${bild}<div class="txt"><div class="sent"><span class="dotx" aria-hidden="true"></span>${d.satz}</div>
      ${d.nebentext ? html`<div class=${`muted${d.warnung ? ' warnl' : ''}`} data-nebentext>${d.nebentext}</div>` : nothing}</div>
    ${link ? html`<span class="chev" aria-hidden="true">${ic('chev', 24)}</span>` : nothing}`;
  return link
    ? html`<a class=${klasse} href=${`#box-${d.id}`} data-box=${d.id} data-lage=${d.lage}>${inhalt}</a>`
    : html`<div class=${klasse} data-box=${d.id} data-lage=${d.lage}>${inhalt}</div>`;
}

/* ------------------------------------------------------------------ Seite */

class GeraeteSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.status = new BoxStatus(ctx);
    this.z = { phase: 'laedt', fehlerCode: null }; // Zustand des Abschnitts „Abends“ (die Karten der Boxen brauchen keinen)
    this.e = { leise_zeiten: { zeitzone: 'Europe/Berlin', fenster: [] }, revision: null };
    this.gn = { timer: 30, gespeichert: 30, ausblenden: 60, hatTobie: null };
    this.b = null; // Blatt „Leise-Zeit“
    this.jetzt = () => new Date(); // Uhr der Wochenansicht (in Tests ersetzbar)
    this._lauf = 0;
    this._speichert = false;
    this._uhr = null;
  }

  betreten() {
    this.status.zuruecksetzen();
    this._uhr = setInterval(() => this.ctx.neuZeichnen(), 60000); // die Marke „jetzt“ wandert
    this._uhr.unref?.();
    this.laden();
  }

  neuLaden() { this.laden(true); }

  verlassen() {
    this._lauf += 1;
    clearInterval(this._uhr);
    this._uhr = null;
    this.status.stoppen();
  }

  nachRender() { this.status.beobachte(Object.values(this.ctx.boxen())); }

  /* ---- Daten */
  async laden(still = false) {
    const lauf = ++this._lauf;
    if (!this.ctx.faehig('einstellungen')) { this.z = { phase: 'ohne', fehlerCode: null }; this.ctx.neuZeichnen(); return; }
    if (!still || this.z.phase !== 'bereit') this.z = { phase: 'laedt', fehlerCode: null };
    this.ctx.neuZeichnen();
    try {
      const [r, hat] = await ladeMitGrenze(Promise.all([this.ctx.api('tobibox/einstellungen/get'), this._hatGuteNachtTobie()]), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this._uebernehme(r);
      this.gn.hatTobie = hat;
      this.z = { phase: 'bereit', fehlerCode: null };
    } catch (err) {
      if (lauf !== this._lauf) return;
      this.z = { phase: 'fehler', fehlerCode: err?.code || 'unknown_error' };
    }
    this.ctx.neuZeichnen();
  }

  /* Gibt es einen Tobie mit der Aktion „Gute Nacht“? Ein Fehler hier ist kein Grund, den Abschnitt zu sperren (null: unbekannt). */
  async _hatGuteNachtTobie() {
    if (!this.ctx.faehig('zuordnung')) return null;
    try {
      for (let offset = 0; offset < 1000; offset += 100) {
        const r = await this.ctx.api('tobibox/zuordnung/list', { limit: 100, offset });
        if ((r.zuordnungen || []).some((x) => x.ziel?.typ === 'aktion' && x.ziel.aktion === 'gute_nacht')) return true;
        if (offset + 100 >= (r.gesamt ?? 0)) return false;
      }
      return false;
    } catch { return null; }
  }

  /* Stand aus `einstellungen/get` oder der Antwort von `einstellungen/set` (gleiche Felder). */
  _uebernehme(r) {
    if (r.leise_zeiten) this.e.leise_zeiten = { zeitzone: r.leise_zeiten.zeitzone || 'Europe/Berlin', fenster: (r.leise_zeiten.fenster || []).map((w) => ({ ...w })) };
    if (r.gute_nacht) {
      const dirty = this.gn.timer !== this.gn.gespeichert;
      this.gn.gespeichert = r.gute_nacht.timer_min;
      this.gn.ausblenden = r.gute_nacht.ausblenden_s;
      if (!dirty) this.gn.timer = r.gute_nacht.timer_min;
    }
    if (r.konfig && typeof r.konfig.revision === 'number') this.e.revision = r.konfig.revision;
  }

  get gesperrt() { return this.ctx.gesperrt(); }

  _senden(teil) {
    const rev = this.ctx.faehig('bibliothek') && this.e.revision !== null ? { erwartet_revision: this.e.revision } : {};
    return this.ctx.api('tobibox/einstellungen/set', { ...teil, ...rev });
  }

  /* Fehler beim Speichern: Meldung am Ort der Handlung (bleibt, bis „OK“). `stand_veraltet`: Ansicht neu laden, das Blatt schließt.
   * Gibt zurück, ob das Blatt offen bleiben soll. */
  _fehler(err) {
    const code = err?.code || 'unknown_error';
    this.ctx.meldeFehler(this.ctx.fehlerText(code));
    if (code === 'stand_veraltet' || code === 'zuordnung_geaendert') { this.laden(true); return false; }
    return true;
  }

  /* ---- Gute Nacht */
  waehleTimer(min) { this.gn.timer = min; this.ctx.neuZeichnen(); }

  async speichereGuteNacht() {
    if (this._speichert || this.gesperrt || this.gn.timer === this.gn.gespeichert) return;
    this._speichert = true;
    this.ctx.neuZeichnen();
    try {
      const r = await this._senden({ gute_nacht: { timer_min: this.gn.timer, ausblenden_s: this.gn.ausblenden } });
      this._uebernehme(r);
      this.gn.timer = this.gn.gespeichert;
      this.ctx.melde(ABENDS.meldung.gespeichert);
    } catch (err) { this._fehler(err); }
    this._speichert = false;
    this.ctx.neuZeichnen();
  }

  oeffneAnleitung() {
    this.ctx.oeffneBlatt({
      titel: ABENDS.gute_nacht.anlegen_titel,
      inhalt: () => html`<p>${ABENDS.gute_nacht.anlegen_text}</p>`,
      knoepfe: [{ label: SEITE.schliessen, kind: 'primary' }],
    });
  }

  /* ---- Leise-Zeiten: Blatt */
  oeffneFenster(id) {
    const vorhanden = id ? this.e.leise_zeiten.fenster.find((w) => w.id === id) : null;
    if (id && !vorhanden) return;
    if (!id && this.e.leise_zeiten.fenster.length >= MAX_FENSTER) { this.ctx.meldeFehler(ABENDS.meldung.zu_viele); return; }
    const w = vorhanden ? { ...vorhanden, tage: [...vorhanden.tage], grenze: vorhanden.grenze ?? 25 } : standardFenster(this.e.leise_zeiten.fenster);
    const b = { neu: !vorhanden, ...w };
    this.b = b;
    this.ctx.oeffneBlatt({
      titel: vorhanden ? ABENDS.blatt.titel_aendern : ABENDS.blatt.titel_neu,
      inhalt: () => this._blattInhalt(),
      knoepfe: [
        { label: ABENDS.blatt.abbrechen },
        { label: ABENDS.blatt.speichern, kind: 'primary', fn: () => this.speichereFenster() },
      ],
    }).then(() => { if (this.b === b) this.b = null; });
  }

  _aendere(teil) { Object.assign(this.b, teil); this.ctx.neuZeichnen(); }

  _schalteTag(d) {
    const tage = this.b.tage.includes(d) ? this.b.tage.filter((x) => x !== d) : [...this.b.tage, d];
    this._aendere({ tage });
  }

  _blattInhalt() {
    const b = this.b;
    if (!b) return nothing;
    const T = ABENDS.blatt;
    const gleich = (liste) => b.tage.length === liste.length && liste.every((d) => b.tage.includes(d));
    const schnell = [
      { id: 'alle', label: ABENDS.leise.jeden_tag, tage: TAGE }, { id: 'so-do', label: T.so_do, tage: [7, 1, 2, 3, 4] }, { id: 'fr-sa', label: T.fr_sa, tage: [5, 6] },
    ];
    const zeit = (feld, id, label) => html`<div class="gfeld"><label for=${id}>${label}</label>
      <input class="zeitfeld" type="time" id=${id} step="300" data-feld=${feld} .value=${b[feld]}
        @input=${(e) => { if (e.target.value) this._aendere({ [feld]: e.target.value }); }} @change=${(e) => { if (e.target.value) this._aendere({ [feld]: e.target.value }); }}></div>`;
    return html`
      ${b.tage.length ? html`<p class="gilt" data-gilt>${fuellen(LEISE.gilt_fuer, { tage: tageListe(b.tage) })}</p>` : html`<p class="gilt warnl" data-gilt>${T.kein_tag_hinweis}</p>`}
      <div class="gfeld"><span class="lbl" id="lz-tage">${T.tage}</span>
        <div class="gchips" role="group" aria-labelledby="lz-tage">${TAGE.map((d) => html`<button type="button" class="gchip" data-tag=${d} aria-pressed=${b.tage.includes(d) ? 'true' : 'false'} @click=${() => this._schalteTag(d)}>${ABENDS.leise.tage[d]}</button>`)}</div>
        <div class="gchips" role="group" aria-label=${T.schnell_label}>${schnell.map((q) => html`<button type="button" class="gchip" data-schnell=${q.id} aria-pressed=${gleich(q.tage) ? 'true' : 'false'} @click=${() => this._aendere({ tage: [...q.tage] })}>${q.label}</button>`)}</div></div>
      ${zeit('von', 'lz-von', T.von)}
      <div class="gfeld">${zeit('bis', 'lz-bis', T.bis)}<div class="muted" data-mitternacht>${minuten(b.bis) < minuten(b.von) ? T.ueber_mitternacht : ''}</div></div>
      <div class="gfeld"><span class="lbl" id="lz-wirkung">${T.was}</span>
        ${segment({ label: T.was, optionen: [{ label: ABENDS.leise.still, wert: 'stumm' }, { label: ABENDS.leise.leiser, wert: 'leiser' }], wert: b.wirkung, onWahl: (w) => this._aendere({ wirkung: w }) })}</div>
      ${b.wirkung === 'leiser'
        ? html`<div class="gfeld"><label for="lz-grenze">${fuellen(T.grenze, { prozent: b.grenze })}</label>
            <input type="range" class="regler" id="lz-grenze" min="0" max="100" step="5" .value=${String(b.grenze)} @input=${(e) => this._aendere({ grenze: Number(e.target.value) })}></div>`
        : html`<p class="muted">${T.still_hinweis}</p>`}
      ${b.neu ? nothing : html`<div class="apart"><button type="button" class="btn link danger" data-loeschen @click=${() => this.frageLoeschen()}>${T.loeschen}</button></div>`}`;
  }

  /* Speichern im Blatt. Gibt `false` zurück, wenn das Blatt offen bleiben soll (Fehler an der Eingabe oder beim Senden). */
  async speichereFenster() {
    const b = this.b;
    if (!b || this._speichert) return false;
    if (this.gesperrt) { this.ctx.meldeFehler(this.ctx.fehlerText('konfig_nicht_bereit')); return false; }
    if (!b.tage.length) { this.ctx.meldeFehler(ABENDS.meldung.kein_tag); return false; }
    if (b.von === b.bis) { this.ctx.meldeFehler(ABENDS.meldung.von_gleich); return false; }
    const neu = fensterSenden(b);
    const liste = this.e.leise_zeiten.fenster.map((w) => (w.id === b.id ? neu : fensterSenden(w)));
    if (b.neu) liste.push(neu);
    return this._sendeFenster(liste, ABENDS.meldung.gespeichert);
  }

  async _sendeFenster(liste, meldung) {
    this._speichert = true;
    try {
      // Zeitzone: nur ein Administrator darf sie setzen; er schickt den gespeicherten Wert zurück (sonst gälte Europe/Berlin).
      const lz = { ...(this.ctx.admin ? { zeitzone: this.e.leise_zeiten.zeitzone } : {}), fenster: liste };
      const r = await this._senden({ leise_zeiten: lz });
      this._uebernehme(r);
      this.ctx.melde(meldung);
      return undefined;
    } catch (err) {
      return this._fehler(err) ? false : undefined;
    } finally {
      this._speichert = false;
      this.ctx.neuZeichnen();
    }
  }

  frageLoeschen() {
    const b = this.b;
    if (!b || b.neu) return;
    const T = ABENDS.blatt;
    this.ctx.oeffneBlatt({
      titel: T.loeschen_titel,
      inhalt: () => html`<p>${fuellen(T.loeschen_text, { tage: tageKurz(b.tage), von: uhrzeit(b.von), bis: uhrzeit(b.bis) })}</p>`,
      knoepfe: [
        { label: T.abbrechen },
        { label: T.loeschen_knopf, kind: 'danger solid', fn: () => this._sendeFenster(this.e.leise_zeiten.fenster.filter((w) => w.id !== b.id).map(fensterSenden), ABENDS.meldung.geloescht) },
      ],
    });
  }

  /* ---- Darstellung */
  render() {
    const { ctx } = this;
    const boxen = Object.values(ctx.boxen());
    return html`<h2>${GERAETE.titel}</h2>
      ${boxen.length
        ? html`<div class="gboxen" data-geraete="boxen" role="list" aria-label=${GERAETE_SEITE.boxen_label}>${boxen.map((b) => html`<div role="listitem">${boxKarte(this.status.daten(b))}</div>`)}</div>`
        : ctx.leer('keine_box', 'keineBox', { aktion: () => window.location.reload() })}
      <div class="platz" data-platz="neue-tobies"></div>
      ${this._abends()}`;
  }

  _abends() {
    const { ctx, z } = this;
    if (z.phase === 'ohne') return nothing;
    const kopf = html`<h2 class="abends" data-abschnitt="abends">${ABENDS.titel}</h2>`;
    if (z.phase === 'laedt') return html`${kopf}${ctx.laedt()}`;
    if (z.phase === 'fehler') return html`${kopf}${ctx.fehlerKarte(z.fehlerCode, () => this.laden())}`;
    return html`${kopf}${this._guteNacht()}${this._leiseZeiten()}`;
  }

  _guteNacht() {
    const T = ABENDS.gute_nacht;
    const { gn } = this;
    const aus = gn.timer !== gn.gespeichert;
    const andere = ANDERE_MIN.includes(gn.timer) ? ANDERE_MIN : [...ANDERE_MIN, ...(SCHNELLWAHL_MIN.includes(gn.timer) ? [] : [gn.timer])].sort((x, y) => x - y);
    return html`<div class="gkarte" data-karte="gute-nacht"><h3>${T.titel}</h3><div class="muted">${T.text}</div>
      <div class="gfeld"><span class="lbl" id="gn-timer">${T.timer}</span>
        <div class="gchips wrap" role="group" aria-labelledby="gn-timer">${SCHNELLWAHL_MIN.map((m) => html`<button type="button" class="gchip" data-minuten=${m} aria-pressed=${gn.timer === m ? 'true' : 'false'} @click=${() => this.waehleTimer(m)}>${fuellen(T.minuten, { minuten: m })}</button>`)}</div>
        <div class="selw"><label class="sr" for="gn-andere">${T.anderer_label}</label>
          <select id="gn-andere" class="auswahl" @change=${(e) => { if (e.target.value) this.waehleTimer(Number(e.target.value)); }}>
            <option value="" .selected=${SCHNELLWAHL_MIN.includes(gn.timer)}>${T.anderer}</option>
            ${andere.map((m) => html`<option value=${m} .selected=${gn.timer === m}>${fuellen(T.anderer_minuten, { minuten: m })}</option>`)}
          </select></div></div>
      <button type="button" class="btn primary" data-gn-speichern ?disabled=${!aus || this.gesperrt || this._speichert} @click=${() => this.speichereGuteNacht()}>${aus ? T.speichern : T.gespeichert}</button>
      ${gn.hatTobie === null ? nothing : html`<div class="muted gnhinweis">${gn.hatTobie ? T.hat_tobie : T.kein_tobie} <button type="button" class="btn link" data-gn-anleitung @click=${() => this.oeffneAnleitung()}>${T.anlegen}</button></div>`}</div>`;
  }

  _leiseZeiten() {
    const T = ABENDS.leise;
    return html`<div class="gkarte" data-karte="leise-zeiten"><h3>${T.titel}</h3>${this._wochenansicht()}
      <div class="btns lzneu"><button type="button" class="btn primary" data-leise-neu ?disabled=${this.gesperrt} @click=${() => this.oeffneFenster(null)}>${ic('plus', 20)}${T.neu}</button></div></div>`;
  }

  _wochenansicht() {
    const T = ABENDS.leise;
    const { zeitzone, fenster } = this.e.leise_zeiten;
    const abschn = leiseAbschnitte(fenster);
    const jetzt = jetztInZone(zeitzone, this.jetzt());
    const satz = jetztSatz(abschn, jetzt);
    const label = (d, g) => {
      const wirkung = g.w.wirkung === 'stumm' ? T.wirkung_still : fuellen(T.wirkung_leiser, { grenze: g.w.grenze });
      return g.fortsetzung
        ? fuellen(T.fortsetzung, { tag: T.tage[d], vontag: T.tage[g.vontag], bis: uhrzeit(g.w.bis), wirkung })
        : fuellen(T.abschnitt, { tag: T.tage[d], von: uhrzeit(g.w.von), bis: uhrzeit(g.w.bis), wirkung });
    };
    return html`<div class="wk" data-wochenansicht>
      <div class="jetzt" role="status" data-jetzt=${satz.art}>${satz.text}</div>
      <div class="wg" role="group" aria-label=${T.wochenansicht} style=${`--n:${(jetzt.min / 1440).toFixed(4)}`}>
        <span class="nowtag" aria-hidden="true">${T.marke_jetzt}</span>
        <div class="ax" aria-hidden="true">${[0, 6, 12, 18, 24].map((h) => html`<span style=${`--k:${h / 24}`}>${h}</span>`)}</div>
        ${TAGE.map((d) => html`<div class=${`dr${d === jetzt.tag ? ' heute' : ''}`} data-tag=${d}>
          <span class="dl">${T.tage[d]}${d === jetzt.tag ? html`<span class="sr">${T.heute}</span>` : nothing}</span>
          <div class="trk">${abschn[d].map((g) => {
            const start = (g.a / 14.4).toFixed(2);
            const breite = ((g.b - g.a) / 14.4).toFixed(2);
            const still = g.w.wirkung === 'stumm';
            return html`<span class=${`seg ${still ? 's' : 'l'}`} style=${`left:${start}%;width:${breite}%`} aria-hidden="true"></span>
              <button type="button" class="hit" data-fenster=${g.w.id} data-tag=${d} data-fortsetzung=${g.fortsetzung ? '1' : nothing} style=${`--s:${start};--w:${breite}`}
                aria-label=${label(d, g)} @click=${() => this.oeffneFenster(g.w.id)}></button>`;
          })}</div></div>`)}
        <span class="nowl" aria-hidden="true"></span>
      </div>
      <div class="lg" aria-hidden="true"><span><i class="s"></i>${T.still}</span><span><i class="l"></i>${T.leiser}</span></div>
      ${fenster.length ? nothing : html`<div class="muted lzleer" data-leer="leise-zeiten">${T.leer}</div>`}</div>`;
  }
}

export const erzeuge = (ctx) => new GeraeteSeite(ctx);

export const stil = () => css`
  /* Karten (eigene Namen, damit sie die Karten anderer Seiten nicht berühren) */
  .gkarte { display: block; background: var(--card); border-radius: var(--r-card); box-shadow: 0 1px 3px var(--shadow); padding: 16px; margin: 0 0 16px; min-width: 0; color: inherit; text-decoration: none; }
  .gkarte h3 { font-size: 17px; font-weight: 500; margin: 0 0 4px; }
  .gboxen { display: grid; grid-template-columns: 1fr; gap: 0 16px; }
  .app:not([data-layout="unten"]) .gboxen { grid-template-columns: 1fr 1fr; }
  .gboxen > div { min-width: 0; }
  main h2.abends { margin-top: 24px; }
  .gstatus { display: flex; gap: 12px; align-items: center; }
  a.gstatus:active { background: var(--primary-soft); }
  .gstatus .txt { min-width: 0; flex: 1; }
  .gstatus .sent { font-weight: 500; font-size: 17px; overflow-wrap: anywhere; }
  .gstatus .dotx { display: inline-block; width: 10px; height: 10px; border-radius: 5px; margin-right: 6px; background: var(--ok); }
  .gstatus.off .dotx { background: var(--text2); }
  .gstatus.off .cover:not(.ph) { opacity: 0.45; } /* der Platzhalter bleibt unverblasst: sein Symbol braucht 3:1 gegen die Fläche */
  .gstatus .chev { flex: none; color: var(--text2); }
  .gstatus .chev svg { width: 24px; height: 24px; fill: currentColor; display: block; }
  .gstatus .cover.ph { background: var(--primary-soft); color: var(--text2); border-radius: 12px; }
  .gstatus .cover.ph svg { fill: currentColor; }
  .warnl { color: var(--warn); font-weight: 500; }
  .platz:empty { display: none; }

  /* Formularteile (Gute Nacht, Blatt) */
  .gfeld { display: grid; gap: 4px; margin: 12px 0; }
  .gfeld label, .gfeld .lbl { font-size: 14px; color: var(--text2); }
  .gchips { display: flex; gap: 6px; flex-wrap: wrap; }
  .gchips + .gchips { margin-top: 8px; }
  .gchips.wrap { gap: 8px; }
  .gchip { min-width: 44px; min-height: 44px; border-radius: 22px; border: 1px solid var(--line); background: var(--card); color: var(--text); font-weight: 500; padding: 0 12px; }
  .gchip[aria-pressed="true"] { background: var(--primary); color: var(--on-primary); border-color: var(--primary-ink); }
  .selw { margin-top: 8px; }
  .auswahl, .zeitfeld { min-height: 48px; border-radius: 10px; border: 1px solid var(--line); background: var(--card); color: var(--text); padding: 0 12px; font-size: 16px; max-width: 100%; }
  .zeitfeld { width: 100%; max-width: 220px; }
  .regler { width: 100%; min-height: 44px; accent-color: var(--primary); }
  .gilt { margin: 4px 0 0; font-weight: 500; }
  .apart { margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--divider); }
  .apart .btn.link { min-height: 44px; }
  .gnhinweis { margin-top: 12px; }
  .gnhinweis .btn.link { min-height: 44px; padding: 0 8px; }
  .lzneu { margin-top: 12px; }
  .gkarte .btn[disabled] { background: var(--card); color: var(--text2); border-color: var(--line); cursor: default; }
  .lzleer { margin-top: 8px; }

  /* Wochenansicht der Leise-Zeiten (Design 5.8): Leiste 0 bis 24 Uhr je Tag; Still = ausgefüllt, Leiser = schräg gestreift */
  .wk { margin-top: 12px; }
  .wk .jetzt { font-weight: 500; font-size: 17px; margin-bottom: 12px; }
  .wk .wg { position: relative; padding-left: 36px; }
  .wk .nowtag { position: absolute; top: 0; left: calc(36px + (100% - 36px) * var(--n)); transform: translateX(-50%); font-size: 12px; font-weight: 700; line-height: 18px; padding: 0 6px; border-radius: 6px; background: var(--text); color: var(--card); z-index: 3; }
  .wk .ax { position: relative; height: 38px; }
  .wk .ax span { position: absolute; bottom: 2px; left: calc(100% * var(--k)); transform: translateX(-50%); font-size: 13px; color: var(--text2); }
  .wk .dr { display: flex; align-items: center; gap: 4px; height: 44px; margin-left: -36px; }
  .wk .dl { width: 32px; flex: none; font-size: 14px; font-weight: 500; color: var(--text); }
  .wk .dr.heute .dl { color: var(--primary-ink); font-weight: 700; }
  .wk .trk { position: relative; flex: 1; height: 28px; border: 1px solid var(--line); border-radius: 8px; background-color: var(--card); background-image: linear-gradient(to right, var(--divider) 1px, transparent 1px); background-size: 25% 100%; }
  .wk .seg { position: absolute; top: 2px; bottom: 2px; min-width: 4px; border-radius: 5px; pointer-events: none; }
  .wk .seg.s { background: var(--primary-ink); }
  .wk .seg.l { background: repeating-linear-gradient(135deg, var(--primary-ink) 0 3px, var(--primary-soft) 3px 7px); border: 2px solid var(--primary-ink); }
  .wk .hit { position: absolute; top: -9px; height: 44px; padding: 0; border: 0; background: none; border-radius: 8px;
    left: clamp(0px, calc(var(--s) * 1% + var(--w) * 0.5% - max(var(--w) * 1%, 44px) / 2), calc(100% - max(var(--w) * 1%, 44px))); width: max(calc(var(--w) * 1%), 44px); }
  .wk .hit:active { background: var(--primary-soft); opacity: 0.4; }
  .wk .hit:focus-visible { outline: 3px solid var(--focus); outline-offset: -3px; }
  .wk .nowl { position: absolute; top: 20px; bottom: 0; width: 2px; margin-left: -1px; left: calc(36px + (100% - 36px) * var(--n)); background: var(--text); pointer-events: none; z-index: 2; }
  .wk .lg { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 8px; font-size: 14px; color: var(--text); }
  .wk .lg span { display: inline-flex; align-items: center; gap: 8px; }
  .wk .lg i { display: inline-block; width: 28px; height: 16px; border-radius: 5px; }
  .wk .lg i.s { background: var(--primary-ink); }
  .wk .lg i.l { background: repeating-linear-gradient(135deg, var(--primary-ink) 0 3px, var(--primary-soft) 3px 7px); border: 2px solid var(--primary-ink); }

  /* Box-Detailseite (seiten/box.js) */
  .gdetail { display: grid; gap: 0; padding: 4px 16px; }
  .gdetail .gz { display: flex; gap: 12px; padding: 10px 0; border-top: 1px solid var(--divider); font-size: 16px; }
  .gdetail .gz:first-child { border-top: 0; }
  .gdetail .gz .k { color: var(--text2); flex: 0 0 40%; font-size: 14px; padding-top: 2px; }
  .gdetail .gz .v { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  a.glink { display: flex; align-items: center; gap: 12px; min-height: 56px; padding: 0 16px; color: var(--text); text-decoration: none; font-weight: 500; }
  a.glink:active { background: var(--primary-soft); }
  a.glink .chev { margin-left: auto; color: var(--text2); }
  a.glink .chev svg { width: 24px; height: 24px; fill: currentColor; display: block; }
  a.glink.gkarte { padding: 0 16px; }
  main h2.technik { margin-top: 24px; }
`;

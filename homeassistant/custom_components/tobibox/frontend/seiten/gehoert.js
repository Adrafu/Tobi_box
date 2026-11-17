/* Unterseite „Gehört“ `#gehoert` (Stufe B, Paket B4; Design docs/designs/gehoert.md Abschnitt 7 und docs/designs/ha-oberflaeche.md 5.10, 5.10.1).
 *
 * Nur mit der Fähigkeit `gehoert` (ohne sie leitet die App auf „Geräte“ um). Aufbau von oben nach unten: „‹ Geräte“, Überschrift, die Auswahl „Wer?“
 * (Alle · Alle Boxen · je Box · je Person), der Zeitraum (Woche · Monat · Jahr · Alles), die Rangliste „Wer hat was gehört?“ mit den Spalten
 * Hörzeit · Mal · fertig (ein Tipp auf eine Zeile zeigt die Aufteilung nach Folgen), das Diagramm „Hörzeit pro Tag“ (Jahr: pro Woche, Alles: pro Monat),
 * die „Tageszeiten“ und die aufklappbare Erklärung „Was wird gezählt?“.
 *
 * Daten: ausschließlich Befehl 50 `gehoert/zusammenfassung` (Vertrag 3.14), je Ansicht drei Abfragen: Rangliste (`nach = ["serie"]`), Zeitreihe
 * (`["tag"]`, `["woche"]` oder `["monat"]`, bei „Alle“ mit `"wer"` für die Tabelle) und Tageszeiten (`["stunde"]`). Die Liste der Quellen kommt als `wer_auswahl`
 * aus der Antwort. Das Ereignis `gehoert` (`geaendert`, gebündelt) lädt still neu.
 * Diagramme ohne Bibliothek (SVG): `role="img"` mit Beschreibung, dazu je eine Tabelle („Zahlen als Tabelle“). Farben sind Tokens (`--chart1`, `--chart2`, `--grid`).
 * Schnittstelle zur App: siehe bausteine.js.
 */
import { html, nothing, css, svg, segment, ladeMitGrenze, dauerText } from '../bausteine.js';
import { GEHOERT, SEITE, fuellen } from '../texte.js';

export const RANG_ANZAHL = 10; // so viele Zeilen zeigt die Rangliste zuerst (Design 5.10)
export const RANG_LIMIT = 50; // so viele holt die Abfrage
export const ZEITRAEUME = ['woche', 'monat', 'jahr', 'alles'];
export const REIHEN_ART = { woche: 'tag', monat: 'tag', jahr: 'woche', alles: 'monat' }; // Raster der Zeitreihe je Zeitraum (Design 7)
const NEU_LADEN_MS = 1000; // das Ereignis `gehoert` kommt höchstens alle 5 s; eine Sekunde sammeln reicht

/* ------------------------------------------------------------------ reine Funktionen */

const zwei = (n) => String(n).padStart(2, '0');
const WOCHENTAGE = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
const MONATE = ['Jan.', 'Feb.', 'März', 'Apr.', 'Mai', 'Juni', 'Juli', 'Aug.', 'Sept.', 'Okt.', 'Nov.', 'Dez.'];

/* „9:48 Std.“, „26 Min.“, „45 Sek.“, „0 Min.“: kurze Form für Tabellen und Zeilen (Design 5.10). */
export function hoerzeit(sek) {
  const s = Math.max(0, Math.round(Number(sek) || 0));
  const E = GEHOERT.einheit;
  if (s === 0) return `0 ${E.min}`;
  if (s < 60) return `${s} ${E.sek}`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m} ${E.min}`;
  return `${Math.floor(m / 60)}:${zwei(m % 60)} ${E.std}`;
}

/* Gesprochene und Satzform: „9 Std. 53 Min.“ (wie überall in der Seite). */
export const hoerzeitSatz = (sek) => dauerText(Math.max(0, Number(sek) || 0));

const minuten = (sek) => Math.round((Number(sek) || 0) / 60);

/* Beschriftungen eines Rasterwerts: { a, b (zweite Zeile oder ''), lang (für die Tabelle und das Beschreiben) }. `art`: tag, woche, monat, stunde. */
export function rasterBeschriftung(art, wert) {
  if (art === 'tag') {
    const [j, m, t] = String(wert).split('-').map(Number);
    const wt = WOCHENTAGE[new Date(Date.UTC(j, m - 1, t)).getUTCDay()];
    return { a: wt, b: `${t}.${m}.`, lang: `${wt}, ${zwei(t)}.${zwei(m)}.${j}` };
  }
  if (art === 'woche') {
    const [j, w] = String(wert).split('-W');
    const kw = fuellen(GEHOERT.tag.woche_kurz, { nr: Number(w) });
    return { a: kw, b: '', lang: `${kw} ${j}` };
  }
  if (art === 'monat') {
    const [j, m] = String(wert).split('-').map(Number);
    return { a: MONATE[m - 1], b: String(j).slice(2), lang: `${MONATE[m - 1]} ${j}` };
  }
  return { a: String(wert), b: '', lang: fuellen(GEHOERT.stunde.uhr, { stunde: wert }) };
}

/* Obergrenze der Achse in Minuten: höchstens vier Teilstriche, runde Schritte. Gibt { max, schritt }. */
export function achse(maxMin) {
  const schritte = [5, 10, 15, 20, 30, 60, 90, 120, 180, 240, 300, 480, 600, 900, 1200, 1800, 3600];
  const schritt = schritte.find((s) => Math.ceil(maxMin / s) <= 4) ?? 3600;
  return { schritt, max: schritt * Math.max(1, Math.ceil(maxMin / schritt)) };
}

/* Welche Beschriftungen unter den Säulen stehen: immer die letzte, dann zurück im gleichen Abstand (höchstens etwa sechs); `vomAnfang`: ab der ersten (Stunden 0, 3, 6 …). */
export function beschriftete(n, abstand = null, vomAnfang = false) {
  const k = abstand ?? (n <= 7 ? 1 : Math.ceil(n / 6));
  const aus = new Set();
  if (vomAnfang) for (let i = 0; i < n; i += k) aus.add(i);
  else for (let i = n - 1; i >= 0; i -= k) aus.add(i);
  return aus;
}

/* Summen je Quelle aus den Zeilen mit `wer` (bei „Alle“): [{ wer, name, sekunden }] absteigend, ohne Nullen. */
export function summenJeQuelle(zeilen, auswahl) {
  const m = new Map();
  for (const z of zeilen || []) if (z.wer) m.set(z.wer, (m.get(z.wer) || 0) + (z.sekunden || 0));
  const name = (w) => auswahl.find((x) => x.wer === w)?.name ?? w;
  return [...m.entries()].filter(([, s]) => s > 0).sort((x, y) => y[1] - x[1]).map(([wer, sekunden]) => ({ wer, name: name(wer), sekunden }));
}

/* Zeilen einer Zeitreihe zu einer Zeile je Rasterwert: [{ wert, sekunden, je: Map(wer → sekunden) }], Reihenfolge wie geliefert (lückenlos aufsteigend). */
export function reiheAufRaster(zeilen, art) {
  const m = new Map();
  for (const z of zeilen || []) {
    const e = m.get(z[art]) ?? { wert: z[art], sekunden: 0, je: new Map() };
    e.sekunden += z.sekunden || 0;
    if (z.wer) e.je.set(z.wer, (e.je.get(z.wer) || 0) + (z.sekunden || 0));
    m.set(z[art], e);
  }
  return [...m.values()];
}

/* Der Satz über dem Diagramm: „In den letzten 7 Tagen: 9 Std. 53 Min. (Box 1 5 Std. 58 Min., Box 2 3 Std. 55 Min., …)“. `quellen`: Summen je Quelle (nur bei „Alle“). */
export function tagSatz(zeitraum, sekunden, quellen = []) {
  const T = GEHOERT.tag;
  let satz = fuellen(T.satz[zeitraum] ?? T.satz.alles, { summe: hoerzeitSatz(sekunden) });
  if (quellen.length > 1) {
    const teile = quellen.slice(0, 3).map((q) => `${q.name} ${hoerzeitSatz(q.sekunden)}`);
    if (quellen.length > 3) teile.push('…');
    satz += ` ${fuellen(T.aufteilung, { teile: teile.join(', ') })}`;
  }
  return /[.…]$/.test(satz) ? satz : `${satz}.`; // „… 53 Min.“ endet schon mit einem Punkt
}

/* Satz zu den Tageszeiten: die Stunde mit der größten Hörzeit. */
export function stundenSatz(zeilen) {
  let beste = null;
  for (const z of zeilen || []) if (z.sekunden > 0 && (!beste || z.sekunden > beste.sekunden)) beste = z;
  return beste ? fuellen(GEHOERT.stunde.satz, { stunde: beste.stunde }) : GEHOERT.stunde.satz_keine;
}

/* Zeilen der Aufteilung nach Folgen: alle heutigen Folgen der Serie (aus `serie/get`, in deren Reihenfolge), dazu gehörte Folgen, die dort nicht mehr stehen.
 * Nicht gehörte Folgen tragen 0 / 0 / 0 (`gehoert: false`). `folgen`: Antwort von Befehl 50 (`nach = ["folge"]`), `serie`: Antwort von `serie/get` oder null. */
export function aufteilungZeilen(folgen, serie) {
  const je = new Map((folgen || []).map((z) => [z.folge, z]));
  const aus = [];
  const gesehen = new Set();
  for (const f of serie?.folgen || []) {
    const z = je.get(f.name);
    gesehen.add(f.name);
    aus.push({ name: f.name, anzeige: f.anzeige || f.name, sekunden: z?.sekunden ?? 0, mal: z?.mal ?? 0, fertig: z?.fertig ?? 0, gehoert: !!z && z.sekunden > 0 });
  }
  for (const z of folgen || []) if (!gesehen.has(z.folge)) aus.push({ name: z.folge, anzeige: z.folge, sekunden: z.sekunden, mal: z.mal, fertig: z.fertig, gehoert: z.sekunden > 0 });
  return aus;
}

const malText = (n) => fuellen(n === 1 ? GEHOERT.rangliste.mal.eins : GEHOERT.rangliste.mal.mehr, { anzahl: n });
const fertigText = (z) => (z.folgen_gesamt > 0 ? `${z.folgen_fertig ?? 0}/${z.folgen_gesamt}` : GEHOERT.aufteilung.nie);

/* ------------------------------------------------------------------ Diagramm (SVG, ohne Bibliothek) */

const B = 360; const H = 210; const L = 34; const R = 8; const O = 22; const U = 36; // Zeichenfläche in Einheiten; die Breite folgt dem Behälter (viewBox)

/* Säulendiagramm. `werte`: [{ sek, a, b }] (Beschriftung a und b unter der Säule); `zahlen`: Minuten über jeder Säule; `abstand`: nur jede n-te Beschriftung (vom Ende). */
function saeulen({ werte, zahlen = false, beschreibung, abstand = null, vomAnfang = false }) {
  const n = werte.length;
  const maxMin = Math.max(0, ...werte.map((w) => minuten(w.sek)));
  const { schritt, max } = achse(maxMin);
  const pw = B - L - R; const ph = H - O - U;
  const slot = pw / Math.max(1, n);
  const bw = Math.min(slot * 0.66, 30);
  const y = (min) => O + ph - (min / max) * ph;
  const striche = [];
  for (let m = 0; m <= max; m += schritt) striche.push(m);
  const zeigen = beschriftete(n, abstand, vomAnfang);
  return html`<svg class="gh-bild" viewBox="0 0 ${B} ${H}" role="img" aria-label=${beschreibung} focusable="false">
    <text class="gh-ax" x="0" y="11">${GEHOERT.tag.achse}</text>
    ${striche.map((m) => svg`<line class="gh-gitter" x1=${L} x2=${B - R} y1=${y(m)} y2=${y(m)}></line><text class="gh-ax gh-ay" x=${L - 5} y=${y(m) + 4} text-anchor="end">${m}</text>`)}
    ${werte.map((w, i) => {
    const min = minuten(w.sek);
    const h = (min / max) * ph;
    const x = L + slot * i + (slot - bw) / 2;
    return svg`<g>${h > 0 ? svg`<rect class="gh-saeule" x=${x} y=${y(min)} width=${bw} height=${h} rx="3"></rect>` : nothing}
        ${zahlen ? svg`<text class="gh-zahl" x=${x + bw / 2} y=${y(min) - 4} text-anchor="middle">${min}</text>` : nothing}
        ${zeigen.has(i) ? svg`<text class="gh-ax" x=${x + bw / 2} y=${O + ph + 14} text-anchor="middle">${w.a}</text>${w.b ? svg`<text class="gh-ax" x=${x + bw / 2} y=${O + ph + 27} text-anchor="middle">${w.b}</text>` : nothing}` : nothing}</g>`;
  })}</svg>`;
}

/* ------------------------------------------------------------------ Seite */

class GehoertSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.e = { wer: 'alle', zeitraum: 'woche', serie: null }; // `serie`: Aufteilung nach Folgen offen (Serien-ID)
    this.z = { phase: 'laedt', fehlerCode: null, auswahl: [], rang: null, reihe: null, stunden: null, nie: false };
    this.auf = null; // { phase, serie, name, zeilen, summe, fehlerCode }
    this.alleRang = false; // alle geladenen Zeilen der Rangliste zeigen
    this.merkeSerie = null; // Zeile der Rangliste, die nach „‹ Rangliste“ den Fokus bekommt
    this._fokus = null;
    this._lauf = 0;
    this._aufLauf = 0;
    this._timer = null;
    this._abmelden = null;
  }

  betreten() {
    this._abmelden?.();
    this._abmelden = this.ctx.ereignis?.((ev) => { if (ev?.thema === 'gehoert' && ev.art === 'geaendert') this._planeLaden(); }) ?? null;
    this.laden(this.z.phase === 'bereit');
  }

  neuLaden() { this.laden(true); }

  verlassen() {
    this._lauf += 1;
    this._aufLauf += 1;
    clearTimeout(this._timer);
    this._abmelden?.();
    this._abmelden = null;
  }

  _planeLaden() {
    clearTimeout(this._timer);
    this._timer = setTimeout(() => { this.laden(true); }, NEU_LADEN_MS);
    this._timer.unref?.();
  }

  /* ---- Daten */
  _frage(extra) {
    const wer = this.e.wer;
    return this.ctx.api('tobibox/gehoert/zusammenfassung', { wer, zeitraum: this.e.zeitraum, ...extra });
  }

  async _holeAlles() {
    const { zeitraum, wer } = this.e;
    const art = REIHEN_ART[zeitraum];
    const mitWer = wer === 'alle';
    const rang = this._frage({ nach: ['serie'], limit: RANG_LIMIT });
    // Zu viele Zeilen (Zeit × Quellen über 400): ohne die Aufteilung nach Quellen noch einmal
    const reihe = this._frage({ nach: mitWer ? [art, 'wer'] : [art] }).catch((e) => (mitWer && e?.code === 'invalid_format' ? this._frage({ nach: [art] }) : Promise.reject(e)));
    const stunden = this._frage({ nach: ['stunde'] });
    const [r, t, s] = await Promise.all([rang, reihe, stunden]);
    // B4-OFFEN: Ob noch nie etwas gehört wurde, sagt die Antwort nicht: `wer_auswahl` nennt die eingerichteten Boxen auch ohne Daten (Backend, gehoert_abfrage.py). Darum fragt die Seite bei
    // leerer Anzeige einmal über „Alles“ nach (eine vierte Abfrage). Ein Feld wie `summe_alles` in Befehl 50 würde sie sparen.
    let nie = false; // noch nie etwas gehört (leerer Zustand): die Boxen stehen in `wer_auswahl`, auch wenn es keine Daten gibt, darum zählt die Summe über alles
    if ((r.summe?.sekunden ?? 0) === 0 && (t.summe?.sekunden ?? 0) === 0) {
      nie = this.e.zeitraum === 'alles' && this.e.wer === 'alle';
      if (!nie) nie = ((await this.ctx.api('tobibox/gehoert/zusammenfassung', { wer: 'alle', zeitraum: 'alles', nach: ['wer'], limit: 1 })).summe?.sekunden ?? 0) === 0;
    }
    return { rang: r, reihe: t, stunden: s, auswahl: r.wer_auswahl || [], nie, zeitraum, wer }; // zeitraum und wer gehören zur Antwort (Raster, Satz und Tabelle richten sich danach, nicht nach dem schon gewechselten Knopf)
  }

  async laden(still = false) {
    const lauf = ++this._lauf;
    if (!still || this.z.phase !== 'bereit') this.z = { ...this.z, phase: 'laedt', fehlerCode: null };
    this.ctx.neuZeichnen();
    try {
      const d = await ladeMitGrenze(this._holeAlles(), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.z = { phase: 'bereit', fehlerCode: null, ...d };
      if (this.e.wer !== 'alle' && this.e.wer !== 'alle_boxen' && !d.auswahl.some((x) => x.wer === this.e.wer)) { this.e.wer = 'alle'; this.e.serie = null; this.auf = null; return this.laden(true); }
    } catch (err) {
      if (lauf !== this._lauf) return undefined;
      if (err?.code === 'wer_ungueltig' && this.e.wer !== 'alle') { // die Quelle gibt es nicht mehr: auf „Alle“ zurück und neu laden
        this.e = { ...this.e, wer: 'alle', serie: null };
        this.auf = null;
        this.ctx.meldeFehler(this.ctx.fehlerText('wer_ungueltig'));
        return this.laden(true);
      }
      this.z = { ...this.z, phase: 'fehler', fehlerCode: err?.code || 'unknown_error' };
    }
    if (this.e.serie && this.z.phase === 'bereit') this.ladeAufteilung(this.e.serie, { still: true });
    this.ctx.neuZeichnen();
    return undefined;
  }

  async ladeAufteilung(serieId, { still = false, name = null } = {}) {
    const lauf = ++this._aufLauf;
    if (!still || !this.auf) this.auf = { phase: 'laedt', serie: serieId, name: name ?? this._serieName(serieId), zeilen: [], summe: null, fehlerCode: null };
    this.ctx.neuZeichnen();
    try {
      const [r, s] = await ladeMitGrenze(Promise.all([
        this._frage({ serie_id: serieId, nach: ['folge'], limit: 200 }),
        this.ctx.api('tobibox/serie/get', { serie_id: serieId }).catch(() => null), // ohne die Liste der Folgen zeigt die Aufteilung nur die gehörten
      ]), this.ctx.grenzeMs);
      if (lauf !== this._aufLauf) return;
      this.auf = { phase: 'bereit', serie: serieId, name: s?.name ?? this.auf?.name ?? name ?? this._serieName(serieId), zeilen: aufteilungZeilen(r.zeilen, s), summe: r.summe, weitere: !!r.weitere, fehlerCode: null };
    } catch (err) {
      if (lauf !== this._aufLauf) return;
      if (err?.code === 'serie_nicht_gefunden') { this.schliesseAufteilung(false); this.ctx.meldeFehler(this.ctx.fehlerText(err.code)); this.laden(true); return; }
      this.auf = { ...(this.auf || {}), phase: 'fehler', serie: serieId, fehlerCode: err?.code || 'unknown_error' };
    }
    if (this._aufFokus) { this._aufFokus = false; this._fokus = '[data-aufteilung-titel]'; }
    this.ctx.neuZeichnen();
  }

  _serieName(id) { return this.z.rang?.zeilen?.find((x) => x.serie === id)?.name ?? ''; }

  /* ---- Bedienung */
  waehleWer(wer) {
    if (this.e.wer === wer) return;
    this.e = { ...this.e, wer, serie: null };
    this.auf = null;
    this.alleRang = false;
    this.laden(true);
  }

  waehleZeitraum(zeitraum) {
    if (this.e.zeitraum === zeitraum) return;
    this.e = { ...this.e, zeitraum, serie: null };
    this.auf = null;
    this.alleRang = false;
    this.laden(true);
  }

  oeffneAufteilung(z) {
    if (!z.serie) return;
    this.e = { ...this.e, serie: z.serie };
    this.merkeSerie = z.serie;
    this._fokus = '[data-aufteilung-titel]';
    this._aufFokus = true; // der Fokus muss auch nach dem Laden auf der Überschrift stehen (die Karte wird dabei neu gebaut)
    this.ladeAufteilung(z.serie, { name: z.name });
  }

  schliesseAufteilung(fokus = true) {
    this._aufLauf += 1;
    this.e = { ...this.e, serie: null };
    this.auf = null;
    if (fokus) this._fokus = this.merkeSerie ? `[data-serie-zeile="${this.merkeSerie}"]` : '[data-rangliste-titel]';
    this.ctx.neuZeichnen();
  }

  nachRender(wurzel) {
    const f = this._fokus;
    if (!f) return;
    const ziel = wurzel.querySelector(f);
    if (ziel) { this._fokus = null; ziel.focus?.({ preventScroll: false }); }
  }

  /* ---- Darstellung */
  render() {
    const { ctx, z } = this;
    const kopf = html`<a class="back" href="#geraete">${SEITE.zurueck.geraete}</a><h2>${GEHOERT.titel}</h2>`;
    if (z.phase === 'laedt') return html`${kopf}${ctx.laedt()}`;
    if (z.phase === 'fehler') return html`${kopf}${ctx.fehlerKarte(z.fehlerCode, () => this.laden())}`;
    if (z.nie || !z.auswahl.length) return html`${kopf}${ctx.leer('gehoert', 'gehoertOhneDaten', { href: '#bibliothek' })}`;
    const keine = (z.rang?.summe?.sekunden ?? 0) === 0 && (z.reihe?.summe?.sekunden ?? 0) === 0;
    return html`${kopf}<div class="gh" data-gehoert>
      ${this._wer()}${this._zeitraum()}
      ${keine ? html`<div class="gh-karte" data-leer-zeitraum><p class="muted gh-leerzeile">${GEHOERT.leer_zeitraum}</p></div>`
    : html`${this._rangliste()}${this._zeitreihe()}${this._stunden()}`}
      ${this._gezaehlt()}</div>`;
  }

  _wer() {
    const { z, e } = this;
    const boxen = z.auswahl.filter((x) => x.art === 'box');
    const personen = z.auswahl.filter((x) => x.art === 'person');
    const knoepfe = [{ wer: 'alle', name: GEHOERT.alle }, ...(boxen.length ? [{ wer: 'alle_boxen', name: GEHOERT.alle_boxen }] : []), ...boxen, ...personen];
    return html`<div class="gh-feld"><span class="gh-lbl" id="gh-wer">${GEHOERT.wer}</span>
      <div class="gh-chips" role="group" aria-labelledby="gh-wer" data-wer>${knoepfe.map((k) => html`<button type="button" class="gh-chip" data-wer-knopf=${k.wer}
        aria-pressed=${e.wer === k.wer ? 'true' : 'false'} @click=${() => this.waehleWer(k.wer)}>${k.name}</button>`)}</div></div>`;
  }

  _zeitraum() {
    const Z = GEHOERT.zeitraum;
    return html`<div class="gh-feld" data-zeitraum>${segment({ label: Z.label, optionen: ZEITRAEUME.map((w) => ({ label: Z[w], wert: w })), wert: this.e.zeitraum, onWahl: (w) => this.waehleZeitraum(w) })}</div>`;
  }

  /* Rangliste „Wer hat was gehört?“ oder, nach einem Tipp, die Aufteilung nach Folgen. */
  _rangliste() {
    if (this.e.serie) return this._aufteilung();
    const R2 = GEHOERT.rangliste;
    const { rang } = this.z;
    const alle = rang?.zeilen || [];
    const sichtbar = this.alleRang ? alle : alle.slice(0, RANG_ANZAHL);
    return html`<section class="gh-karte" data-karte="rangliste" aria-labelledby="gh-rang-t"><h3 id="gh-rang-t" tabindex="-1" data-rangliste-titel>${R2.titel}</h3>
      <div class="gh-tw"><table class="gh-tabelle gh-rang" data-rangliste><thead><tr>
        <th scope="col" class="gh-t">${R2.spalten.titel}</th><th scope="col" class="gh-z">${R2.spalten.hoerzeit}</th><th scope="col" class="gh-z">${R2.spalten.mal}</th><th scope="col" class="gh-z">${R2.spalten.fertig}</th></tr></thead>
        <tbody>${sichtbar.map((z) => this._rangZeile(z))}</tbody></table></div>
      ${alle.length > RANG_ANZAHL ? html`<div class="btns gh-mehr"><button type="button" class="btn" data-rang-mehr aria-expanded=${this.alleRang ? 'true' : 'false'} @click=${() => { this.alleRang = !this.alleRang; this.ctx.neuZeichnen(); }}>${this.alleRang ? R2.weniger : fuellen(R2.mehr, { anzahl: alle.length })}</button></div>` : nothing}
      ${rang?.weitere ? html`<p class="muted gh-hinweis" data-rang-weitere>${R2.weitere}</p>` : nothing}</section>`;
  }

  _rangZeile(z) {
    const R2 = GEHOERT.rangliste;
    const werte = { name: z.name, hoerzeit: hoerzeitSatz(z.sekunden), mal: malText(z.mal), fertig: z.folgen_gesamt > 0 ? fuellen(R2.fertig_von, { fertig: z.folgen_fertig ?? 0, gesamt: z.folgen_gesamt }) : '' };
    const aria = fuellen(z.folgen_gesamt > 0 ? R2.zeile : R2.zeile_ohne_fertig, werte);
    const zellen = html`<td class="gh-z">${hoerzeit(z.sekunden)}</td><td class="gh-z">${z.mal}</td><td class="gh-z">${fertigText(z)}</td>`;
    if (!z.serie) return html`<tr data-zeile-weg><td class="gh-t"><span class="gh-name gh-weg">${z.name}</span></td>${zellen}</tr>`; // alle gelöschten Einträge: eine Zeile ohne Ziel
    return html`<tr data-serie=${z.serie}><td class="gh-t"><button type="button" class="gh-name gh-knopf" data-serie-zeile=${z.serie} aria-label=${aria} @click=${() => this.oeffneAufteilung(z)}>${z.name}</button></td>${zellen}</tr>`;
  }

  _aufteilung() {
    const A = GEHOERT.aufteilung;
    const a = this.auf;
    const kopf = html`<button type="button" class="gh-zurueck" data-aufteilung-zurueck @click=${() => this.schliesseAufteilung()}>${A.zurueck}</button>
      <h3 id="gh-auf-t" tabindex="-1" data-aufteilung-titel>${A.titel}${a?.name ? html`<span class="gh-sub">${a.name}</span>` : nothing}</h3>`;
    if (!a || a.phase === 'laedt') return html`<section class="gh-karte" data-karte="aufteilung" aria-labelledby="gh-auf-t">${kopf}${this.ctx.laedt()}</section>`;
    if (a.phase === 'fehler') return html`<section class="gh-karte" data-karte="aufteilung" aria-labelledby="gh-auf-t">${kopf}${this.ctx.fehlerKarte(a.fehlerCode, () => this.ladeAufteilung(a.serie))}</section>`;
    const s = a.summe || { sekunden: 0, mal: 0, fertig: 0 };
    return html`<section class="gh-karte" data-karte="aufteilung" aria-labelledby="gh-auf-t">${kopf}
      <div class="gh-tw"><table class="gh-tabelle gh-rang" data-aufteilung><thead><tr>
        <th scope="col" class="gh-t">${A.spalten.folge}</th><th scope="col" class="gh-z">${A.spalten.hoerzeit}</th><th scope="col" class="gh-z">${A.spalten.mal}</th><th scope="col" class="gh-z">${A.spalten.fertig}</th></tr></thead>
        <tbody>${a.zeilen.map((z) => this._folgenZeile(z))}</tbody>
        <tfoot><tr data-summe><th scope="row" class="gh-t">${A.summe}</th><td class="gh-z">${hoerzeit(s.sekunden)}</td><td class="gh-z">${s.mal}</td><td class="gh-z">${s.fertig ? fuellen(A.fertig_mal, { anzahl: s.fertig }) : A.nie}</td></tr></tfoot></table></div>
      ${a.weitere ? html`<p class="muted gh-hinweis" data-auf-weitere>${GEHOERT.rangliste.weitere}</p>` : nothing}</section>`;
  }

  _folgenZeile(z) {
    const A = GEHOERT.aufteilung;
    return html`<tr class=${z.gehoert ? '' : 'gh-nie'} data-folge=${z.name}><td class="gh-t"><span class="gh-name">${z.anzeige}</span></td>
      <td class="gh-z">${z.gehoert ? hoerzeit(z.sekunden) : '0'}</td><td class="gh-z">${z.mal}</td><td class="gh-z">${z.fertig ? fuellen(A.fertig_mal, { anzahl: z.fertig }) : A.nie}</td></tr>`;
  }

  /* Hörzeit pro Tag, Woche oder Monat: Säulen, Satz darüber, Tabelle darunter. */
  _zeitreihe() {
    const { z } = this;
    const T = GEHOERT.tag;
    const zeitraum = z.zeitraum ?? this.e.zeitraum; // die Parameter der geladenen Antwort
    const wer = z.wer ?? this.e.wer;
    const art = REIHEN_ART[zeitraum];
    const raster = reiheAufRaster(z.reihe?.zeilen, art);
    const jeQuelle = wer === 'alle' ? summenJeQuelle(z.reihe?.zeilen, z.auswahl) : [];
    const satz = tagSatz(zeitraum, z.reihe?.summe?.sekunden ?? 0, jeQuelle);
    const titel = T.titel[art];
    const werte = raster.map((r) => ({ sek: r.sekunden, ...rasterBeschriftung(art, r.wert) }));
    const bild = fuellen(T.bild, { titel, satz });
    const mitQuellen = wer === 'alle' && raster.some((r) => r.je.size > 0);
    const namen = (r) => z.auswahl.filter((x) => (r.je.get(x.wer) ?? 0) > 0).map((x) => ({ name: x.name, sekunden: r.je.get(x.wer) }));
    const spalte = T.spalten[art];
    // Bei „Alle“ steht je Zeile die Summe und daneben, was davon auf welche Quelle fällt (eine schmale Spalte statt einer Spalte je Quelle: passt auch auf 390 px)
    return html`<section class="gh-karte" data-karte="zeitreihe" aria-labelledby="gh-tag-t"><h3 id="gh-tag-t">${titel}</h3>
      <p class="gh-satz" data-satz>${satz}</p>
      <div class="gh-diagramm" data-diagramm="zeitreihe">${saeulen({ werte, zahlen: art === 'tag' && raster.length <= 7, beschreibung: bild })}</div>
      <details class="gh-details" data-tabelle="zeitreihe"><summary>${GEHOERT.tabelle}</summary>
        <div class="gh-tw"><table class="gh-tabelle"><caption class="sr">${titel}</caption><thead><tr><th scope="col" class="gh-t">${spalte}</th>
          <th scope="col" class="gh-z">${mitQuellen ? T.spalten.summe : T.spalten.hoerzeit}</th>${mitQuellen ? html`<th scope="col" class="gh-d">${T.spalten.davon}</th>` : nothing}</tr></thead>
          <tbody>${raster.map((r, i) => html`<tr><th scope="row" class="gh-t">${werte[i].lang}</th><td class="gh-z">${hoerzeit(r.sekunden)}</td>
            ${mitQuellen ? html`<td class="gh-d">${namen(r).map((q) => html`<span class="gh-q">${q.name} ${hoerzeit(q.sekunden)}</span> `)}</td>` : nothing}</tr>`)}</tbody></table></div></details></section>`;
  }

  /* Tageszeiten: 24 Säulen (Stunde 0 bis 23). */
  _stunden() {
    const S = GEHOERT.stunde;
    const zeilen = this.z.stunden?.zeilen || [];
    const satz = stundenSatz(zeilen);
    const werte = zeilen.map((r) => ({ sek: r.sekunden, a: String(r.stunde), b: '' }));
    const bild = fuellen(S.bild, { satz });
    return html`<section class="gh-karte" data-karte="stunden" aria-labelledby="gh-std-t"><h3 id="gh-std-t">${S.titel}</h3>
      <p class="gh-satz" data-satz>${satz}</p>
      <div class="gh-diagramm" data-diagramm="stunden">${saeulen({ werte, beschreibung: bild, abstand: 3, vomAnfang: true })}</div>
      <details class="gh-details" data-tabelle="stunden"><summary>${GEHOERT.tabelle}</summary>
        <div class="gh-tw"><table class="gh-tabelle"><caption class="sr">${S.titel}</caption><thead><tr><th scope="col" class="gh-t">${S.spalten.stunde}</th><th scope="col" class="gh-z">${S.spalten.hoerzeit}</th></tr></thead>
          <tbody>${zeilen.map((r) => html`<tr><th scope="row" class="gh-t">${fuellen(S.uhr, { stunde: r.stunde })}</th><td class="gh-z">${hoerzeit(r.sekunden)}</td></tr>`)}</tbody></table></div></details></section>`;
  }

  _gezaehlt() {
    const G = GEHOERT.gezaehlt;
    return html`<details class="gh-details gh-karte" data-gezaehlt><summary>${G.titel}</summary>
      <dl class="gh-dl">${G.zeilen.map((x) => html`<dt>${x.k}</dt><dd>${x.t}</dd>`)}</dl></details>`;
  }
}

export const erzeuge = (ctx) => new GehoertSeite(ctx);

export const stil = () => css`
  .gh { --chart1: var(--primary-ink); --chart2: var(--text2); --grid: var(--divider); display: grid; gap: 0; max-width: 760px; min-width: 0; }
  .gh-karte { background: var(--card); border-radius: var(--r-card); box-shadow: 0 1px 3px var(--shadow); padding: 12px 16px 16px; margin: 0 0 16px; min-width: 0; }
  .app[data-layout="seite"] .gh-karte { border-radius: 20px; padding: 16px 24px 24px; box-shadow: 0 1px 4px var(--shadow); }
  .gh-karte h3 { font-size: 17px; font-weight: 500; margin: 4px 0 8px; outline: none; }
  .gh-karte h3 .gh-sub { display: block; font-size: 15px; font-weight: 400; color: var(--text2); overflow-wrap: anywhere; }
  .gh-feld { display: grid; gap: 6px; margin: 4px 0 12px; min-width: 0; }
  .gh-lbl { font-size: 14px; color: var(--text2); }
  .gh-chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .gh-chip { min-width: 44px; min-height: 44px; border-radius: 22px; border: 1px solid var(--line); background: var(--card); color: var(--text); font-weight: 500; padding: 0 16px; overflow-wrap: anywhere; }
  .gh-chip[aria-pressed="true"] { background: var(--primary); color: var(--on-primary); border-color: var(--primary-ink); font-weight: 700; box-shadow: inset 0 0 0 1px var(--primary-ink); }
  .gh-leerzeile { margin: 8px 0; }
  .gh-tw { overflow-x: auto; max-width: 100%; }
  .gh-tabelle { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  .gh-tabelle th, .gh-tabelle td { padding: 0; text-align: left; font-weight: 400; border-top: 1px solid var(--divider); vertical-align: middle; }
  .gh-tabelle thead th { font-size: 13px; font-weight: 500; color: var(--text2); border-top: 0; padding: 4px 0 6px; }
  .gh-tabelle tfoot th, .gh-tabelle tfoot td { font-weight: 700; border-top: 2px solid var(--divider); padding: 12px 0; }
  .gh-tabelle .gh-t { padding-right: 8px; overflow-wrap: anywhere; }
  .gh-tabelle .gh-z { text-align: right; white-space: nowrap; padding-left: 8px; }
  .gh-rang .gh-z { width: 1%; }
  .gh-tabelle .gh-d { padding-left: 12px; }
  .gh-tabelle td.gh-d { color: var(--text2); font-size: 14px; }
  .gh-q { display: block; }
  .gh-tabelle tbody tr:first-child td, .gh-tabelle tbody tr:first-child th { border-top: 0; }
  .gh-tabelle td.gh-t, .gh-tabelle th.gh-t { min-width: 0; }
  .gh-tabelle tbody th.gh-t, .gh-tabelle tbody td.gh-z { padding-top: 8px; padding-bottom: 8px; }
  .gh-name { display: block; font-weight: 500; line-height: 1.3; }
  .gh-knopf { width: 100%; min-height: 44px; padding: 8px 0; border: 0; background: none; color: var(--text); text-align: left; font: inherit; font-weight: 500; overflow-wrap: anywhere; border-radius: 8px; cursor: pointer; }
  .gh-knopf:focus-visible { outline: 3px solid var(--focus); outline-offset: -3px; }
  @media (hover: hover) { .gh-rang tr[data-serie]:hover { background: var(--primary-soft); } }
  .gh-weg { color: var(--text2); padding: 8px 0; font-weight: 400; }
  .gh-nie td, .gh-nie .gh-name { color: var(--text2); font-weight: 400; }
  .gh-zurueck { min-height: 44px; margin: 0 0 4px -8px; padding: 0 12px; border: 0; background: none; color: var(--primary-ink); font-weight: 500; font-size: 16px; border-radius: 22px; }
  .gh-zurueck:focus-visible { outline: 3px solid var(--focus); }
  .gh-mehr { justify-content: center; margin: 12px 0 0; }
  .gh-hinweis { margin: 8px 0 0; font-size: 14px; }
  .gh-satz { margin: 0 0 8px; overflow-wrap: anywhere; }
  .gh-diagramm { margin: 4px 0 8px; }
  svg.gh-bild { display: block; width: 100%; max-width: 640px; height: auto; fill: var(--text2); overflow: visible; }
  .gh-bild text { font-family: inherit; fill: var(--text2); font-size: 11px; }
  .gh-bild .gh-ay { font-size: 10px; }
  .gh-bild .gh-zahl { fill: var(--text); font-weight: 500; font-size: 11px; }
  .gh-bild .gh-gitter { stroke: var(--grid); stroke-width: 1; }
  .gh-bild .gh-saeule { fill: var(--chart1); }
  .gh-details > summary { display: flex; align-items: center; min-height: 44px; font-weight: 500; color: var(--primary-ink); cursor: pointer; border-radius: 8px; }
  .gh-details > summary:focus-visible { outline: 3px solid var(--focus); outline-offset: -3px; }
  .gh-details .gh-tw { margin-top: 4px; }
  details.gh-karte { padding: 4px 16px 4px; }
  .gh-dl { margin: 0 0 8px; display: grid; gap: 4px; }
  .gh-dl dt { font-weight: 700; margin-top: 8px; }
  .gh-dl dd { margin: 0; overflow-wrap: anywhere; }
`;

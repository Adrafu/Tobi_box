/* Technik, Stufe B (Paket B4, Design docs/designs/gehoert.md Abschnitt 7): zwei Karten, nur mit der Fähigkeit `gehoert`, nur für Administratoren.
 *
 *   VerlaufKarte      „Verlauf“ auf der Box-Seite (`#technik-box-<id>`): Akku-Kurve der letzten 7 oder 30 Tage (HA-Befehl `recorder/statistics_during_period`
 *                     mit `akku_entitaet` aus `boxen/list`; ohne Sensor keine Kurve), Ladevorgänge, Laufzeit je Ladung und verworfene Hördaten
 *                     (Befehl 52 `technik/verlauf`). Die Kurve hat `role="img"` mit Beschreibung und eine Tabelle.
 *   HoerdatenKarte    „Hördaten“ in „Speicher und Netz“: „Als Tabelle sichern“ (Befehl 53, signierter Pfad) und „Löschen …“ (Befehl 54: erst `trocken` mit der
 *                     Zahl, dann die Bestätigung mit dem Wort LÖSCHEN) für Alle, die Boxen, das Reinhören, eine Box oder eine Person.
 */
import { html, nothing, svg, segment, ladeMitGrenze, zaehle } from '../bausteine.js';
import { TECHNIK, fuellen } from '../texte.js';
import { zeitKurz } from '../tobibox-panel.js';
import { hoerzeitSatz } from './gehoert.js';

const zwei = (n) => String(n).padStart(2, '0');
export const VERLAUF_TAGE = [7, 30];
const ZEILEN_ZUERST = 8; // Ladevorgänge und Laufzeiten: so viele Zeilen zuerst

/* ------------------------------------------------------------------ reine Funktionen */

/* „JJJJ-MM-TT“ eines Zeitpunkts in einer Zeitzone (Vorgabe: die des Geräts). */
export function datumInZone(datum, zone) {
  try {
    const t = new Intl.DateTimeFormat('en-CA', { timeZone: zone || undefined, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(datum);
    const w = (a) => t.find((p) => p.type === a)?.value;
    if (w('year') && w('month') && w('day')) return `${w('year')}-${w('month')}-${w('day')}`;
  } catch { /* unbekannte Zone: Ortszeit */ }
  return `${datum.getFullYear()}-${zwei(datum.getMonth() + 1)}-${zwei(datum.getDate())}`;
}

export function addTage(tag, n) {
  const t = new Date(Date.parse(`${tag}T00:00:00Z`) + n * 86400000);
  return t.toISOString().slice(0, 10);
}

/* Antwort von `recorder/statistics_during_period` für eine Entität → [{ t (ms), v (Prozent) }], aufsteigend; ohne Zahlen fällt der Eintrag weg.
 * `start` ist je nach HA-Version ein Zeitstempel in Millisekunden oder eine ISO-Zeit; Wert: `mean`, sonst `max`, sonst `state`. */
export function akkuPunkte(antwort, id) {
  const l = Array.isArray(antwort?.[id]) ? antwort[id] : [];
  const aus = [];
  for (const x of l) {
    const t = typeof x?.start === 'number' ? x.start : Date.parse(x?.start);
    const v = [x?.mean, x?.max, x?.state].find((y) => typeof y === 'number' && Number.isFinite(y));
    if (Number.isFinite(t) && v !== undefined) aus.push({ t, v: Math.max(0, Math.min(100, v)) });
  }
  return aus.sort((a, b) => a.t - b.t);
}

/* Je Tag der niedrigste und der höchste Stand (Tag in der Zeitzone): [{ tag, min, max }]. */
export function akkuTage(punkte, zone) {
  const m = new Map();
  for (const p of punkte) {
    const tag = datumInZone(new Date(p.t), zone);
    const e = m.get(tag) ?? { tag, min: p.v, max: p.v };
    e.min = Math.min(e.min, p.v); e.max = Math.max(e.max, p.v);
    m.set(tag, e);
  }
  return [...m.values()];
}

export const tagKurz = (tag) => { const [, m, t] = String(tag).split('-').map(Number); return `${t}.${m}.`; };
export const tagLang = (tag) => { const [j, m, t] = String(tag).split('-').map(Number); return `${zwei(t)}.${zwei(m)}.${j}`; };

/* Kurze Dauer: „5 Std. 20 Min.“ */
export const dauerKurz = (sek) => hoerzeitSatz(sek);

/* Verworfene Hördaten im Zeitraum: `gesamt` ist die Gesamtzahl der Box und kann auf 0 zurückfallen (Neustart, Tausch). Gezählt wird die Summe der Zuwächse zwischen
 * aufeinanderfolgenden Werten; fällt der Wert zurück, zählt der neue Wert als Zuwachs. Der erste Eintrag hat keinen Vorgänger im Zeitraum: er zeigt nur, dass es einen Anstieg gab
 * (mindestens 1). Ohne Einträge 0. */
export function verworfenImZeitraum(liste) {
  const l = (Array.isArray(liste) ? liste : []).map((x) => Number(x?.gesamt)).filter((v) => Number.isFinite(v) && v >= 0);
  if (!l.length) return 0;
  let summe = 0;
  for (let i = 1; i < l.length; i += 1) summe += l[i] >= l[i - 1] ? l[i] - l[i - 1] : l[i];
  return Math.max(1, summe);
}

/* Prozentwert gerundet für Sätze. */
const prozent = (v) => Math.round(v);

/* ------------------------------------------------------------------ Kurve (SVG, ohne Bibliothek) */

const B = 360; const H = 190; const L = 34; const R = 8; const O = 14; const U = 28;

function kurve({ punkte, laden, beschreibung, zone }) {
  const t0 = punkte[0].t; const t1 = punkte.at(-1).t;
  const pw = B - L - R; const ph = H - O - U;
  const x = (t) => L + ((t - t0) / Math.max(1, t1 - t0)) * pw;
  const y = (v) => O + ph - (v / 100) * ph;
  const linie = punkte.map((p) => `${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
  const baender = (laden || []).map((l) => ({ a: Math.max(t0, Date.parse(l.beginn)), b: Math.min(t1, l.ende ? Date.parse(l.ende) : t1) })).filter((q) => Number.isFinite(q.a) && Number.isFinite(q.b) && q.b > q.a);
  const marken = [0, 0.5, 1].map((f) => ({ f, t: t0 + (t1 - t0) * f }));
  const ankerX = (f) => (f === 0 ? 'start' : f === 1 ? 'end' : 'middle');
  return html`<svg class="tv-bild" viewBox="0 0 ${B} ${H}" role="img" aria-label=${beschreibung} focusable="false">
    <text class="tv-ax" x="0" y="9">${TECHNIK.verlauf.achse}</text>
    ${baender.map((q) => svg`<rect class="tv-laden" x=${x(q.a)} y=${O} width=${Math.max(1, x(q.b) - x(q.a))} height=${ph}></rect>`)}
    ${[0, 50, 100].map((v) => svg`<line class="tv-gitter" x1=${L} x2=${B - R} y1=${y(v)} y2=${y(v)}></line><text class="tv-ax tv-ay" x=${L - 5} y=${y(v) + 4} text-anchor="end">${v}</text>`)}
    <polyline class="tv-linie" points=${linie}></polyline>
    ${marken.map((m) => svg`<text class="tv-ax" x=${x(m.t)} y=${O + ph + 16} text-anchor=${ankerX(m.f)}>${tagKurz(datumInZone(new Date(m.t), zone))}</text>`)}</svg>`;
}

/* ------------------------------------------------------------------ Karte „Verlauf“ */

export class VerlaufKarte {
  constructor(ctx) {
    this.ctx = ctx;
    this.tage = 7;
    this.z = { phase: 'laedt', fehlerCode: null, daten: null, akku: null }; // akku: null (kein Sensor), [] (keine Werte) oder Punkte
    this.alleLaden = false;
    this.alleLauf = false;
    this._lauf = 0;
    this._box = null;
  }

  zone() { return this.ctx.hass?.config?.time_zone || undefined; }

  async laden(box, { still = false } = {}) {
    const lauf = ++this._lauf;
    this._box = box;
    if (!still || this.z.phase !== 'bereit') this.z = { ...this.z, phase: 'laedt', fehlerCode: null };
    this.ctx.neuZeichnen();
    const jetzt = new Date();
    const bis = datumInZone(jetzt, this.zone());
    const von = addTage(bis, -(this.tage - 1));
    const id = box.akku_entitaet || null;
    const verlauf = this.ctx.api('tobibox/technik/verlauf', { box: box.box, von, bis });
    // Die Kurve darf fehlen (kein Sensor, Recorder schließt ihn aus): dann steht nur ein Satz da, nie ein Fehler
    const akku = id
      ? this.ctx.api('recorder/statistics_during_period', { start_time: new Date(jetzt.getTime() - this.tage * 86400000).toISOString(), end_time: jetzt.toISOString(), statistic_ids: [id], period: 'hour', types: ['mean', 'min', 'max'] })
        .then((r) => akkuPunkte(r, id)).catch(() => [])
      : Promise.resolve(null);
    try {
      const [d, a] = await ladeMitGrenze(Promise.all([verlauf, akku]), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.z = { phase: 'bereit', fehlerCode: null, daten: d, akku: a };
    } catch (err) {
      if (lauf !== this._lauf) return;
      this.z = { ...this.z, phase: 'fehler', fehlerCode: err?.code || 'unknown_error' };
    }
    this.ctx.neuZeichnen();
  }

  verlassen() { this._lauf += 1; }

  waehleTage(n) {
    if (this.tage === n || !this._box) return;
    this.tage = n;
    this.laden(this._box, { still: true });
  }

  _tabelle({ titel, spalten, zeilen, zusatz = '' }) {
    return html`<details class="tv-details" data-tabelle=${zusatz || nothing}><summary>${TECHNIK.verlauf.tabelle}</summary>
      <div class="tv-tw"><table class="tv-tabelle"><caption class="sr">${titel}</caption><thead><tr>${spalten.map((s, i) => html`<th scope="col" class=${i ? 'tv-z' : ''}>${s}</th>`)}</tr></thead>
        <tbody>${zeilen.map((z) => html`<tr>${z.map((c, i) => (i ? html`<td class="tv-z">${c}</td>` : html`<th scope="row">${c}</th>`))}</tr>`)}</tbody></table></div></details>`;
  }

  _akku() {
    const T = TECHNIK.verlauf;
    const a = this.z.akku;
    const kopf = html`<h4 class="tv-h">${T.akku}</h4>`;
    if (a === null) return html`${kopf}<p class="muted" data-akku-keine>${T.akku_keine}</p>`;
    if (a.length < 2) return html`${kopf}<p class="muted" data-akku-leer>${T.akku_leer}</p>`;
    const vs = a.map((p) => p.v);
    const min = prozent(Math.min(...vs)); const max = prozent(Math.max(...vs)); const zuletzt = prozent(a.at(-1).v);
    const beschreibung = fuellen(T.akku_kurve, { tage: this.tage, min, max, zuletzt });
    const tage = akkuTage(a, this.zone());
    return html`${kopf}<div class="tv-diagramm" data-diagramm="akku">${kurve({ punkte: a, laden: this.z.daten?.ladevorgaenge, beschreibung, zone: this.zone() })}</div>
      <p class="muted tv-legende" data-akku-satz>${beschreibung}</p>
      ${this._tabelle({ titel: T.akku, spalten: [T.spalte.tag, T.spalte.niedrigster, T.spalte.hoechster], zeilen: tage.map((t) => [tagLang(t.tag), `${prozent(t.min)} %`, `${prozent(t.max)} %`]), zusatz: 'akku' })}`;
  }

  _liste({ id, titel, spalten, zeilen, aria }) {
    const T = TECHNIK.verlauf;
    const alle = this[id === 'laden' ? 'alleLaden' : 'alleLauf'];
    const sichtbar = alle ? zeilen : zeilen.slice(0, ZEILEN_ZUERST);
    return html`<h4 class="tv-h">${titel}</h4>
      ${zeilen.length ? html`<div class="tv-tw"><table class="tv-tabelle" data-liste=${id} aria-label=${aria}><thead><tr>${spalten.map((s, i) => html`<th scope="col" class=${i ? 'tv-z' : ''}>${s}</th>`)}</tr></thead>
        <tbody>${sichtbar.map((z) => html`<tr>${z.map((c, i) => (i ? html`<td class="tv-z">${c}</td>` : html`<th scope="row">${c}</th>`))}</tr>`)}</tbody></table></div>
        ${zeilen.length > ZEILEN_ZUERST ? html`<div class="btns"><button type="button" class="btn" data-liste-mehr=${id} aria-expanded=${alle ? 'true' : 'false'} @click=${() => { if (id === 'laden') this.alleLaden = !this.alleLaden; else this.alleLauf = !this.alleLauf; this.ctx.neuZeichnen(); }}>${alle ? T.weniger : T.mehr}</button></div>` : nothing}`
        : html`<p class="muted">${T.keine}</p>`}`;
  }

  render() {
    const { ctx, z } = this;
    const T = TECHNIK.verlauf;
    const kopf = html`<h3 id="t-verlauf">${T.titel}</h3>`;
    if (z.phase === 'laedt') return html`<section class="tkarte" data-karte="verlauf" aria-labelledby="t-verlauf">${kopf}${ctx.laedt()}</section>`;
    if (z.phase === 'fehler') return html`<section class="tkarte" data-karte="verlauf" aria-labelledby="t-verlauf">${kopf}${ctx.fehlerKarte(z.fehlerCode, () => this._box && this.laden(this._box))}</section>`;
    const d = z.daten || {};
    const laden = [...(d.ladevorgaenge || [])].reverse();
    const lauf = [...(d.laufzeiten || [])].reverse();
    const verworfen = verworfenImZeitraum(d.verworfen);
    return html`<section class="tkarte tv" data-karte="verlauf" aria-labelledby="t-verlauf">${kopf}
      <div class="tv-wahl">${segment({ label: T.zeitraum, optionen: VERLAUF_TAGE.map((n) => ({ label: T.tage[n], wert: n })), wert: this.tage, onWahl: (n) => this.waehleTage(n) })}</div>
      ${this._akku()}
      ${this._liste({ id: 'laden', titel: T.ladevorgaenge, aria: T.ladevorgaenge, spalten: [T.spalte.beginn, T.spalte.ende, T.spalte.dauer],
    zeilen: laden.map((x) => [zeitKurz(x.beginn), x.ende ? zeitKurz(x.ende) : T.laedt_noch, x.dauer_s != null ? dauerKurz(x.dauer_s) : '–']) })}
      ${this._liste({ id: 'lauf', titel: T.laufzeit, aria: T.laufzeit, spalten: [T.spalte.von, T.spalte.bis, T.spalte.dauer],
    zeilen: lauf.map((x) => [zeitKurz(x.von), x.bis ? zeitKurz(x.bis) : '–', x.dauer_s != null ? dauerKurz(x.dauer_s) : '–']) })}
      <h4 class="tv-h">${T.verworfen}</h4>
      <p class="${verworfen ? '' : 'muted'}" data-verworfen>${verworfen ? zaehle(T.verworfen_satz, verworfen) : T.verworfen_keine}</p>
      ${d.weitere ? html`<p class="muted" data-weitere>${T.weitere}</p>` : nothing}</section>`;
  }
}

/* ------------------------------------------------------------------ Karte „Hördaten“ */

/* Standardweg zum Speichern: ein Link mit `download` (der signierte Pfad gilt für den Aufrufer, 10 Minuten). Tests ersetzen `download`.
 * B4-OFFEN: Wie die HA-App am iPhone und der Browser die CSV-Datei behandeln (Laden oder Öffnen), ist nicht geprüft; in B6 am echten Gerät ansehen. */
export function ladeHerunter(url) {
  const a = document.createElement('a');
  a.href = url;
  a.rel = 'noopener';
  a.setAttribute('download', '');
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export class HoerdatenKarte {
  /* `technik`: die Seite (`tu`, `beschaeftigt`, `b.boxen`). */
  constructor(ctx, technik) {
    this.ctx = ctx;
    this.technik = technik;
    this.wahl = 'alle';
    this.quellen = null; // wer_auswahl aus Befehl 50 oder null (nur die festen Punkte)
    this.download = (url) => ladeHerunter(url);
    this._lauf = 0;
  }

  async laden() {
    const lauf = ++this._lauf;
    try {
      const r = await ladeMitGrenze(this.ctx.api('tobibox/gehoert/zusammenfassung', { wer: 'alle', zeitraum: 'alles', nach: ['wer'], limit: 1 }), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.quellen = r.wer_auswahl || [];
      if (this.wahl !== 'alle' && !this.optionen().some((o) => o.wert === this.wahl)) this.wahl = 'alle';
    } catch { if (lauf === this._lauf) this.quellen = null; } // ohne die Liste: nur die festen Punkte
    this.ctx.neuZeichnen();
  }

  verlassen() { this._lauf += 1; }

  optionen() {
    const H = TECHNIK.hoerdaten;
    const boxen = this.technik.b.boxen || [];
    const name = (id) => { const b = boxen.find((x) => x.box === id); return b ? (b.anzeige || b.anzeigename || b.box) : id; };
    const aus = [{ wert: 'alle', label: H.quelle.alle }, { wert: 'boxen', label: H.quelle.boxen }, { wert: 'reinhoeren', label: H.quelle.reinhoeren }];
    for (const q of this.quellen || []) {
      if (q.art === 'box') aus.push({ wert: q.wer, label: fuellen(H.box, { name: q.name || name(q.wer.slice(4)) }) });
      else aus.push({ wert: q.wer, label: fuellen(H.person, { name: q.name }) });
    }
    return aus;
  }

  /* Befehl 53 oder 54; bei `wer_ungueltig` (Quelle gibt es nicht mehr) wird die Liste neu geladen und die Auswahl steht wieder auf „Alle“ (der Text sagt „neu geladen“). */
  async _befehl(type, felder) {
    try { return await this.ctx.api(type, felder); } catch (err) {
      if (err?.code === 'wer_ungueltig') { this.wahl = 'alle'; this.laden(); }
      throw err;
    }
  }

  label() { return this.optionen().find((o) => o.wert === this.wahl)?.label ?? this.wahl; }

  async sichern() {
    const H = TECHNIK.hoerdaten;
    let r;
    if (!await this.technik.tu('hoerdaten_sichern', async () => { r = await this._befehl('tobibox/gehoert/exportieren', { quelle: this.wahl }); })) return;
    if (!r?.pfad) return;
    const hass = this.ctx.hass;
    this.download(typeof hass?.hassUrl === 'function' ? hass.hassUrl(r.pfad) : r.pfad);
    this.ctx.melde(H.sichern_gemacht);
  }

  async loeschen() {
    const { ctx } = this;
    const H = TECHNIK.hoerdaten;
    const quelle = this.wahl;
    let z;
    if (!await this.technik.tu('hoerdaten_zaehlen', async () => { z = await this._befehl('tobibox/gehoert/loeschen', { quelle, trocken: true }); })) return;
    const anzahl = z?.anzahl ?? 0;
    if (!anzahl) { ctx.melde(H.loeschen_nichts); return; }
    let wort = '';
    const passt = () => ['LÖSCHEN', 'LOESCHEN'].includes(wort.trim().toUpperCase());
    const was = this.label();
    const ja = await new Promise((fertig) => {
      let gewaehlt = false;
      ctx.oeffneBlatt({
        titel: H.loeschen_titel,
        rolle: 'alertdialog',
        inhalt: () => html`<p data-loeschen-zahl>${fuellen(anzahl === 1 ? H.loeschen_text.eins : H.loeschen_text.mehr, { anzahl, was })}</p>
          <div class="tv-feld"><label for="tv-wort">${H.loeschen_wort}</label>
            <input id="tv-wort" type="text" autocomplete="off" autocapitalize="characters" spellcheck="false" aria-label=${H.loeschen_label} .value=${wort}
              @input=${(e) => { wort = e.target.value; ctx.neuZeichnen(); }}></div>`,
        knoepfe: () => [
          { label: TECHNIK.abbrechen },
          { label: H.loeschen_ja, kind: 'danger solid', aus: !passt(), fn: () => { if (!passt()) return false; gewaehlt = true; return undefined; } },
        ],
      }).then(() => fertig(gewaehlt));
    });
    if (!ja) return;
    let r;
    if (!await this.technik.tu('hoerdaten_loeschen', async () => { r = await this._befehl('tobibox/gehoert/loeschen', { quelle, bestaetigung: H.wort }); })) return;
    ctx.melde(zaehle(H.geloescht, r?.anzahl ?? 0));
    this.laden();
  }

  render() {
    const H = TECHNIK.hoerdaten;
    const zu = !!this.technik.beschaeftigt;
    return html`<section class="tkarte tv" data-karte="hoerdaten" aria-labelledby="t-hoerdaten"><h3 id="t-hoerdaten">${H.titel}</h3>
      <div class="tv-feld"><label for="tv-quelle">${H.welche}</label>
        <select id="tv-quelle" class="auswahl" data-quelle @change=${(e) => { this.wahl = e.target.value; this.ctx.neuZeichnen(); }}>${this.optionen().map((o) => html`<option value=${o.wert} ?selected=${o.wert === this.wahl}>${o.label}</option>`)}</select></div>
      <div class="btns tknoepfe"><button type="button" class="btn" data-aktion="hoerdaten_sichern" ?disabled=${zu} @click=${() => this.sichern()}>${H.sichern}</button>
        <button type="button" class="btn danger" data-aktion="hoerdaten_loeschen" ?disabled=${zu} @click=${() => this.loeschen()}>${H.loeschen}</button></div></section>`;
  }
}

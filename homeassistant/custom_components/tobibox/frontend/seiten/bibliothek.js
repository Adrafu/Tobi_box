/* Seite „Bibliothek“ (Design 5.2, Paket A7): wie eine Hörbuch-App, ohne Reihen.
 *
 * Aufbau: Platz für das Upload-Band (A11), Zeile „Bibliothek“ mit Lupe und „+“, Arten-Zeile, Zählzeile mit dem Knopf
 * „Sortieren und Filter“, Liste (Päckchen von 60, endlos nachladend, mit „Mehr laden“ als Rückfall).
 * Die Arten-Zeile mit „Playlists“ kommt erst mit Stufe C und fehlt hier. Das Backend sucht, filtert, sortiert und blättert
 * (`serien/list`: art, filter, sortierung, limit, offset). Schnittstelle zur App: siehe bausteine.js.
 */
import { html, nothing, css, ic, listenZeile, rasterKachel, kopfAktion, segment, ladeMitGrenze, zaehle } from '../bausteine.js';
import { BIB, SEITE, fuellen } from '../texte.js';
import { plusKlick } from './hinzufuegen.js';

export const SEITE_GROESSE = 60; // Päckchen (Design 5.2 Punkt 5, X23)
export const ARTEN = ['alle', 'hoerspiel', 'hoerbuch', 'musik', 'geschichte'];
const FILTER = ['ohne_tobie', 'neu', 'pruefen'];

export const STANDARD = () => ({ art: 'alle', sortierung: 'name', typ: 'alle', filter: { ohne_tobie: false, neu: false, pruefen: false } });

/* Zahl der eingestellten Dinge am Knopf „Sortieren und Filter“ (Art zählt nicht, sie hat eigene Reiter). */
export function aktiveEinstellungen(e) {
  return (e.sortierung !== 'name' ? 1 : 0) + (e.typ !== 'alle' ? 1 : 0) + FILTER.filter((f) => e.filter[f]).length;
}

/* Eingabe für `serien/list` aus den Einstellungen (Vertrag 14.2). */
export function listenAnfrage(e, offset = 0) {
  const filter = [...(e.typ !== 'alle' ? [e.typ] : []), ...FILTER.filter((f) => e.filter[f])];
  return {
    ...(e.art !== 'alle' ? { art: e.art } : {}),
    sortierung: e.sortierung,
    ...(filter.length ? { filter } : {}),
    limit: SEITE_GROESSE,
    offset,
  };
}

/* Ansicht am Computer (ab 1100 px): Cover-Raster oder Liste; die Wahl gilt je Gerät (`localStorage`, ohne Speicher: Raster). */
export const ANSICHT_SCHLUESSEL = 'tobibox.bibliothek.ansicht';
export function leseAnsicht() {
  try { const v = window.localStorage.getItem(ANSICHT_SCHLUESSEL); return v === 'liste' ? 'liste' : 'raster'; } catch { return 'raster'; }
}
export function speichereAnsicht(v) {
  try { window.localStorage.setItem(ANSICHT_SCHLUESSEL, v); } catch { /* ohne Speicher: gilt nur bis zum Neuladen */ }
}

class BibliothekSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.ansicht = leseAnsicht();
    this.e = STANDARD();
    this.z = { phase: 'laedt', fehlerCode: null, eintraege: [], gesamt: 0, weitere: false, ladeMehr: false };
    this._lauf = 0;
    this._io = null;
    this._neuBeobachten = false;
  }

  betreten(route) {
    const w = route?.sortierung;
    if (['name', 'neu', 'angehoert'].includes(w) && w !== this.e.sortierung) { this.e = { ...this.e, sortierung: w }; this.laden(false); return; }
    this.laden(this.z.phase === 'bereit');
  } // schon Daten da: still auffrischen, ohne Platzhalter
  neuLaden() { this.laden(true); }
  verlassen() { this._lauf += 1; this._io?.disconnect(); this._io = null; }

  /* ---- Daten */
  async laden(still = false) {
    const lauf = ++this._lauf;
    if (!still || this.z.phase !== 'bereit') this.z = { ...this.z, phase: 'laedt', fehlerCode: null, ladeMehr: false };
    this.ctx.neuZeichnen();
    try {
      const r = await ladeMitGrenze(this.ctx.api('tobibox/serien/list', listenAnfrage(this.e)), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.ctx.covers.merke(r.serien);
      this.z = { phase: 'bereit', fehlerCode: null, eintraege: r.serien || [], gesamt: r.gesamt ?? (r.serien || []).length, weitere: !!r.weitere, ladeMehr: false };
    } catch (err) {
      if (lauf !== this._lauf) return;
      this.z = { ...this.z, phase: 'fehler', fehlerCode: err?.code || 'unknown_error', ladeMehr: false };
    }
    this.ctx.neuZeichnen();
  }

  async mehrLaden() {
    const z = this.z;
    if (z.phase !== 'bereit' || !z.weitere || z.ladeMehr) return;
    const lauf = this._lauf;
    this.z = { ...z, ladeMehr: true };
    this.ctx.neuZeichnen();
    try {
      const r = await ladeMitGrenze(this.ctx.api('tobibox/serien/list', listenAnfrage(this.e, z.eintraege.length)), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.ctx.covers.merke(r.serien);
      const schon = new Set(z.eintraege.map((s) => s.id));
      const neu = (r.serien || []).filter((s) => !schon.has(s.id));
      this.z = { ...this.z, eintraege: [...z.eintraege, ...neu], gesamt: r.gesamt ?? this.z.gesamt, weitere: !!r.weitere, ladeMehr: false };
      this.ctx.ansage(BIB.weitere_geladen); // der Fokus bleibt, wo er ist
    } catch (err) {
      if (lauf !== this._lauf) return;
      this.z = { ...this.z, ladeMehr: false };
      this.ctx.meldeFehler(this.ctx.fehlerText(err?.code || 'unknown_error'));
    }
    this._neuBeobachten = true;
    this.ctx.neuZeichnen();
  }

  /* ---- Einstellungen */
  setzeArt(art) {
    if (this.e.art === art) return;
    this.e = { ...this.e, art };
    this.laden(true);
  }

  aendere(teil) {
    this.e = { ...this.e, ...teil, filter: { ...this.e.filter, ...(teil.filter || {}) } };
    this.laden(true);
  }

  zuruecksetzen({ mitArt = false } = {}) {
    this.e = { ...STANDARD(), art: mitArt ? 'alle' : this.e.art };
    this.laden(true);
  }

  /* ---- Blatt „Sortieren und Filter“ */
  oeffneBlatt() {
    const b = BIB.blatt;
    const sortierungen = this.ctx.faehig('reinhoeren') ? ['name', 'neu', 'angehoert'] : ['name', 'neu'];
    const wahl = (name, werte, texte, aktuell, setze) => html`<div class="stack" role="radiogroup" aria-label=${name}>${werte.map((w) => html`
      <button type="button" class="optrow" role="radio" aria-checked=${aktuell === w ? 'true' : 'false'} @click=${() => setze(w)}><span>${texte[w]}</span>${aktuell === w ? ic('check', 22) : nothing}</button>`)}</div>`;
    const inhalt = () => html`
      <h3 class="blatt-h">${b.sortieren}</h3>${wahl(b.sortieren, sortierungen, b.sortierung, this.e.sortierung, (w) => this.aendere({ sortierung: w }))}
      <h3 class="blatt-h">${b.was}</h3>${wahl(b.was, ['alle', 'sammlung', 'einzeln'], b.was_wahl, this.e.typ, (w) => this.aendere({ typ: w }))}
      <h3 class="blatt-h">${b.nur}</h3><div class="stack">${FILTER.map((f) => html`
        <button type="button" class="optrow" aria-pressed=${this.e.filter[f] ? 'true' : 'false'} @click=${() => this.aendere({ filter: { [f]: !this.e.filter[f] } })}><span>${b.nur_wahl[f]}</span>${this.e.filter[f] ? ic('check', 22) : nothing}</button>`)}</div>`;
    return this.ctx.oeffneBlatt({
      titel: b.titel,
      inhalt,
      knoepfe: [
        { label: b.zuruecksetzen, fn: () => { this.zuruecksetzen(); return false; } },
        { label: b.fertig, kind: 'primary' },
      ],
    });
  }

  /* ---- Beobachter für endloses Nachladen (200 px Vorlauf); der Knopf „Mehr laden“ bleibt als Rückfall */
  nachRender(wurzel) {
    const knopf = wurzel.querySelector('button[data-mehr]');
    if (!knopf || typeof IntersectionObserver !== 'function') return;
    if (!this._io) {
      this._io = new IntersectionObserver((eintraege) => { if (eintraege.some((x) => x.isIntersecting)) this.mehrLaden(); }, { rootMargin: '200px' });
      this._beobachtet = null;
    }
    if (this._beobachtet !== knopf || this._neuBeobachten) {
      this._io.disconnect(); // erneutes Beobachten meldet den Zustand noch einmal: bleibt der Knopf nah, lädt es weiter
      this._io.observe(knopf);
      this._beobachtet = knopf;
      this._neuBeobachten = false;
    }
  }

  /* ---- Darstellung */
  get _raster() { return this.ctx.layout === 'seite' && this.ansicht === 'raster'; }

  setzeAnsicht(v) {
    if (this.ansicht === v) return;
    this.ansicht = v;
    speichereAnsicht(v);
    this.ctx.neuZeichnen();
  }

  /* Aktionen im Seitenkopf: am Computer der Umschalter Raster | Liste, Lupe und „+“ (X29: Hinzufügen gehört in die Bibliothek). */
  kopfAktionen() {
    const A = BIB.ansicht;
    return html`${this.ctx.layout === 'seite' ? html`<span class="ansicht">${segment({ label: A.label, optionen: [
      { label: html`${ic('grid', 18)}${A.raster}`, wert: 'raster' }, { label: html`${ic('list', 18)}${A.liste}`, wert: 'liste' }], wert: this.ansicht, onWahl: (v) => this.setzeAnsicht(v) })}</span>` : nothing}
      ${kopfAktion({ href: '#suche', label: BIB.lupe, symbol: 'search' })}${kopfAktion({ href: '#hinzufuegen', label: SEITE.hinzufuegen, symbol: 'plus', primaer: true, onKlick: (e) => plusKlick(this.ctx, e) })}`;
  }

  _kopf() {
    return html`${this.ctx.uploadBand()}<h2 class="sr">${SEITE.reiter.bibliothek}</h2>
      <div class="artrow" role="group" aria-label=${BIB.arten_label}>${ARTEN.map((a) => html`
        <button type="button" class="arttab" aria-pressed=${this.e.art === a ? 'true' : 'false'} @click=${() => this.setzeArt(a)}>${BIB.arten[a]}</button>`)}</div>`;
  }

  render() {
    const { ctx, z, e } = this;
    const kopf = this._kopf();
    if (z.phase === 'laedt') return html`${kopf}${ctx.laedt()}`;
    if (z.phase === 'fehler') return html`${kopf}${ctx.fehlerKarte(z.fehlerCode, () => this.laden())}`;
    const aktiv = aktiveEinstellungen(e);
    if (!z.eintraege.length) {
      if (e.art === 'alle' && aktiv === 0) return html`${kopf}${ctx.leer('bibliothek', 'bibliothekLeer', { href: '#hinzufuegen' })}`;
      return html`${kopf}${this._leiste(aktiv)}${ctx.leer('filter', 'filterOhneTreffer', { aktion: () => this.zuruecksetzen({ mitArt: true }) })}`;
    }
    const rest = z.gesamt - z.eintraege.length;
    return html`${kopf}${this._leiste(aktiv)}
      <div class=${this._raster ? 'rgrid' : 'liste'} data-liste="bibliothek" data-ansicht=${this._raster ? 'raster' : 'liste'} aria-busy=${z.ladeMehr ? 'true' : 'false'}>${z.eintraege.map((s) => (this._raster ? rasterKachel(s) : listenZeile(s)))}</div>
      ${z.weitere ? html`<div class="btns mehr"><button type="button" class="btn" data-mehr ?disabled=${z.ladeMehr} @click=${() => this.mehrLaden()}>${fuellen(BIB.mehr_laden, { anzahl: Math.max(1, Math.min(SEITE_GROESSE, rest)) })}</button></div>` : nothing}`;
  }

  _leiste(aktiv) {
    return html`<div class="libbar"><span class="count" aria-live="polite">${zaehle(BIB.anzahl, this.z.gesamt)}</span>
      <button type="button" class="btn" data-sortieren aria-haspopup="dialog" @click=${() => this.oeffneBlatt()}>${ic('tune', 20)}${BIB.sortieren_filter}${aktiv ? html`<span class="nbadge" aria-label=${fuellen(BIB.aktiv, { anzahl: aktiv })}>${aktiv}</span>` : nothing}</button></div>`;
  }
}

export const erzeuge = (ctx) => new BibliothekSeite(ctx);

export const stil = () => css`
  .ansicht { display: contents; }
  .ansicht .seg2 { width: 220px; }
  .ansicht .seg2 button { gap: 6px; font-size: 15px; }
  .ansicht .seg2 svg { fill: currentColor; flex: none; }
  .artrow { display: flex; gap: 2px; overflow-x: auto; scrollbar-width: none; border-bottom: 1px solid var(--divider); margin: 0 0 12px; }
  .artrow::-webkit-scrollbar { display: none; }
  .app[data-layout="seite"] .artrow { margin-top: 4px; }
  .arttab { flex: none; min-height: 44px; padding: 0 12px; border: 0; background: none; font-weight: 500; color: var(--text2); border-bottom: 3px solid transparent; border-radius: 0; }
  .arttab[aria-pressed="true"] { color: var(--primary-ink); border-bottom-color: var(--primary-ink); }
  .libbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 12px 0 4px; }
  .libbar .count { margin: 0; }
  .libbar .btn { min-height: 44px; padding: 0 14px; }
  .libbar .btn svg { width: 20px; height: 20px; fill: currentColor; }
  .nbadge { min-width: 20px; height: 20px; padding: 0 6px; border-radius: 10px; background: var(--primary); color: var(--on-primary); border: 1px solid var(--primary-ink);
    font-size: 12px; line-height: 18px; text-align: center; font-weight: 700; }
  .liste { display: block; }
  .mehr { justify-content: center; margin-top: 16px; }
  .stack { display: grid; gap: 8px; }
  .blatt-h { font-size: 16px; font-weight: 500; margin: 16px 0 8px; }
  .optrow { width: 100%; min-height: 48px; border: 1px solid var(--line); border-radius: var(--r-card); background: var(--card); display: flex; align-items: center;
    justify-content: space-between; padding: 0 16px; text-align: left; }
  .optrow[aria-pressed="true"], .optrow[aria-checked="true"] { background: var(--primary-soft); border-color: var(--primary-ink); }
  .optrow svg { width: 22px; height: 22px; fill: var(--primary-ink); }
`;

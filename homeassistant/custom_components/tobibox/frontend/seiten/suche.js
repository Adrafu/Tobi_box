/* Seite „Suche“ (`#suche`, Design 5.2, Runde 13 X16 „Tobies zuerst“, Paket A7).
 *
 * Ab 2 Zeichen (Verzögerung 250 ms, Umlaute und Groß/Klein egal) fragt die Seite drei Befehle zugleich:
 * `zuordnung/list` (Tobies, nach Name oder nach dem, was sie spielen), `serien/list` mit Filter `sammlung` (Hörspiele,
 * Bücher, Alben) und `folgen/list` (Folgen und Lieder, auch Einzeltitel). Oben bis zu fünf Vorschläge. Art und Filter der
 * Bibliothek gelten hier nicht. Jede Zeile ist ein Link; Abspielen und „⋯“ der Folgenzeile kommen mit A8b und A9
 * (Haken `ctx.folgenAktionen(x)`). Schnittstelle zur App: siehe bausteine.js.
 */
import { html, nothing, css, ic, cover, coverAktion, listenZeile, folgenZeile, markiert, norm, zaehle, ladeMitGrenze } from '../bausteine.js';
import { SUCHE, TOBIE, fuellen } from '../texte.js';

export const MIN_ZEICHEN = 2;
export const VERZOEGERUNG_MS = 250;
export const MAX_SAMMLUNGEN = 8;
export const MAX_FOLGEN = 10;
export const MAX_TOBIES = 8;
export const MAX_VORSCHLAEGE = 5;

/* Vorschläge (X16): Wortanfang oder Wortbeginn, Tobies zuerst, dann Einträge, dann Folgen und Lieder; ohne den Begriff selbst
 * und ohne Doppelte. Quelle sind die Treffer, die schon geladen sind. Liefert { text, art: 'tobie' | 'serie' | 'folge' }. */
export function vorschlaege(term, { tobies = [], sammlungen = [], folgen = [] }, max = MAX_VORSCHLAEGE) {
  const t = norm(term).trim();
  const out = [];
  const gesehen = new Set();
  const nimm = (text, art) => {
    if (!text || out.length >= max) return;
    const n = norm(text);
    if (n === t || gesehen.has(n)) return;
    if (n.startsWith(t) || n.includes(` ${t}`)) { gesehen.add(n); out.push({ text, art }); }
  };
  tobies.forEach((x) => nimm(x.name, 'tobie'));
  sammlungen.forEach((s) => nimm(s.name, 'serie'));
  folgen.forEach((f) => nimm(f.anzeige || f.folge, 'folge'));
  return out;
}

class SucheSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.eingabe = '';
    this.z = { phase: 'leer', term: '', fehlerCode: null, tobies: { liste: [], gesamt: 0 }, sammlungen: { liste: [], gesamt: 0 }, folgen: { liste: [], gesamt: 0 } };
    this._lauf = 0;
    this._timer = null;
    this._fokus = false;
  }

  betreten() { this._fokus = true; this.ctx.neuZeichnen(); }
  verlassen() { this._lauf += 1; clearTimeout(this._timer); }
  neuLaden() { if (this.z.term) this.suche(this.z.term); }

  nachRender(wurzel) {
    if (!this._fokus) return;
    const feld = wurzel.querySelector('input.suchfeld');
    if (feld) { this._fokus = false; feld.focus({ preventScroll: true }); }
  }

  /* Eingabe im Feld: nach 250 ms suchen. `sofort`: ohne Verzögerung (Vorschlag, „Suche löschen“). */
  tippe(wert, { sofort = false } = {}) {
    this.eingabe = wert;
    clearTimeout(this._timer);
    const term = wert.trim();
    if (term.length < MIN_ZEICHEN) {
      this._lauf += 1;
      this.z = { ...this.z, phase: 'leer', term: '', fehlerCode: null };
      this.ctx.neuZeichnen();
      return;
    }
    if (sofort) this.suche(term); else this._timer = setTimeout(() => this.suche(term), VERZOEGERUNG_MS);
  }

  async suche(term) {
    const lauf = ++this._lauf;
    const { ctx } = this;
    this.z = { ...this.z, phase: this.z.phase === 'bereit' ? 'bereit' : 'laedt', term, fehlerCode: null };
    ctx.neuZeichnen();
    try {
      const [zu, se, fo] = await ladeMitGrenze(Promise.all([
        ctx.api('tobibox/zuordnung/list', { text: term, limit: MAX_TOBIES }),
        ctx.api('tobibox/serien/list', { text: term, filter: ['sammlung'], limit: MAX_SAMMLUNGEN }),
        ctx.api('tobibox/folgen/list', { text: term, limit: MAX_FOLGEN }),
      ]), ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      ctx.covers.merke(se.serien);
      this.z = {
        phase: 'bereit', term, fehlerCode: null,
        tobies: { liste: zu.zuordnungen || [], gesamt: zu.gesamt ?? (zu.zuordnungen || []).length },
        sammlungen: { liste: se.serien || [], gesamt: se.gesamt ?? (se.serien || []).length },
        folgen: { liste: fo.folgen || [], gesamt: fo.gesamt ?? (fo.folgen || []).length },
      };
    } catch (e) {
      if (lauf !== this._lauf) return;
      this.z = { ...this.z, phase: 'fehler', fehlerCode: e?.code || 'unknown_error' };
    }
    ctx.neuZeichnen();
  }

  loesche() {
    this.tippe('', { sofort: true });
    this._fokus = true;
    this.ctx.neuZeichnen();
  }

  /* ---- Darstellung */
  _tobieZeile(x, term) {
    const { ctx } = this;
    const ziel = x.ziel || {};
    const name = x.name || TOBIE.ohne_name;
    let spielt;
    let bild;
    if (ziel.typ === 'aktion') {
      spielt = fuellen(SUCHE.spielt, { ziel: SUCHE.aktionen[ziel.aktion] || ziel.aktion });
      bild = coverAktion('sm');
    } else {
      const titel = ziel.typ === 'folge' ? (x.folge_anzeige || ziel.folge) : x.serie_name;
      spielt = ziel.typ === 'folge' && x.serie_name
        ? fuellen(SUCHE.spielt_aus, { ziel: titel, serie: x.serie_name })
        : fuellen(SUCHE.spielt, { ziel: titel || '?' });
      bild = cover({ id: ziel.serie, name: x.serie_name, cover_stand: ctx.covers.stand(ziel.serie) }, 'sm');
    }
    return html`<a class="rowbtn" href=${`#tobie-${x.uid}`} aria-label=${fuellen(SUCHE.tobie_bearbeiten, { tobie: name })}>${bild}
      <span class="grow"><strong>${markiert(name, term)}</strong><span class="muted">${spielt}</span></span><span class="chev" aria-hidden="true">${ic('chev', 24)}</span></a>`;
  }

  _weitere(g, gezeigt) {
    const rest = g.gesamt - gezeigt;
    return rest > 0 ? html`<div class="muted">${fuellen(SUCHE.weitere, { anzahl: rest })}</div>` : nothing;
  }

  _ergebnisse() {
    const { ctx, z } = this;
    const term = z.term;
    const gesamt = z.tobies.gesamt + z.sammlungen.gesamt + z.folgen.gesamt;
    if (!gesamt) {
      return ctx.leer('suche', 'sucheOhneTreffer', { werte: { suchwort: term }, aktion: () => this.loesche() });
    }
    const vs = vorschlaege(term, { tobies: z.tobies.liste, sammlungen: z.sammlungen.liste, folgen: z.folgen.liste });
    const zaehlzeile = fuellen(SUCHE.gefunden, {
      tobies: zaehle(SUCHE.tobies, z.tobies.gesamt), sammlungen: zaehle(SUCHE.sammlungen, z.sammlungen.gesamt), folgen: zaehle(SUCHE.folgen, z.folgen.gesamt),
    });
    const aktionen = (x) => (ctx.folgenAktionen ? ctx.folgenAktionen(x) : nothing);
    return html`
      ${vs.length ? html`<div class="sug" role="group" aria-label=${SUCHE.vorschlaege}>${vs.map((v) => html`
        <button type="button" class="sugrow" data-vorschlag @click=${() => this._vorschlag(v.text)}>${ic(v.art === 'tobie' ? 'tag' : 'search', 22)}<span>${markiert(v.text, term)}</span></button>`)}</div>` : nothing}
      <div class="count" aria-live="polite">${zaehlzeile}</div>
      ${z.tobies.liste.length ? html`<h3 class="rowh">${SUCHE.gruppen.tobies}</h3><div class="card"><div class="rows" data-gruppe="tobies">${z.tobies.liste.map((x) => this._tobieZeile(x, term))}</div></div>${this._weitere(z.tobies, z.tobies.liste.length)}` : nothing}
      ${z.sammlungen.liste.length ? html`<h3 class="rowh">${SUCHE.gruppen.sammlungen}</h3><div class="card"><div data-gruppe="sammlungen">${z.sammlungen.liste.map((s) => listenZeile(s, { term }))}</div></div>${this._weitere(z.sammlungen, z.sammlungen.liste.length)}` : nothing}
      ${z.folgen.liste.length ? html`<h3 class="rowh">${SUCHE.gruppen.folgen}</h3><div class="card"><div data-gruppe="folgen">${z.folgen.liste.map((x) => folgenZeile(x, { term, stand: ctx.covers.stand(x.serie_id), aktionen: aktionen(x) }))}</div></div>${this._weitere(z.folgen, z.folgen.liste.length)}` : nothing}`;
  }

  _vorschlag(text) {
    this.tippe(text, { sofort: true });
    this._fokus = true;
    this.ctx.neuZeichnen();
  }

  render() {
    const { ctx, z } = this;
    let inhalt;
    if (z.phase === 'leer') inhalt = html`<div class="muted hinweis">${SUCHE.mindestens}</div>`;
    else if (z.phase === 'laedt') inhalt = ctx.laedt();
    else if (z.phase === 'fehler') inhalt = ctx.fehlerKarte(z.fehlerCode, () => this.suche(z.term));
    else inhalt = this._ergebnisse();
    return html`<div class="shead"><a class="iconbtn" href="#bibliothek" aria-label=${SUCHE.zurueck}>${ic('back', 26)}</a>
      <div class="grow"><label class="sr" for="qsuche">${SUCHE.label}</label>
        <input class="suchfeld" id="qsuche" type="search" placeholder=${SUCHE.feld} .value=${this.eingabe} autocomplete="off" enterkeyhint="search"
          @input=${(e) => this.tippe(e.target.value)} @keydown=${(e) => { if (e.key === 'Enter') { e.preventDefault(); this.tippe(e.target.value, { sofort: true }); } }}></div></div>
      <div class="qres" data-suche=${z.phase}>${inhalt}</div>`;
  }
}

export const erzeuge = (ctx) => new SucheSeite(ctx);

export const stil = () => css`
  .shead { display: flex; align-items: center; gap: 4px; margin: 4px 0 12px; }
  .shead .grow { flex: 1; min-width: 0; }
  .suchfeld { width: 100%; min-height: 48px; border-radius: 24px; border: 1px solid var(--line); background: var(--card); color: var(--text); padding: 0 16px; }
  .hinweis { padding: 8px 4px; }
  .card { background: var(--card); border-radius: var(--r-card); box-shadow: 0 1px 3px var(--shadow); padding: 4px 16px; margin-bottom: 8px; min-width: 0; }
  .sug { display: grid; margin: 0 0 12px; border-radius: var(--r-card); background: var(--card); box-shadow: 0 1px 3px var(--shadow); overflow: hidden; }
  .sugrow { display: flex; align-items: center; gap: 12px; min-height: 48px; padding: 0 16px; border: 0; border-top: 1px solid var(--divider); background: none; color: var(--text); text-align: left; width: 100%; }
  .sugrow:first-child { border-top: 0; }
  .sugrow svg { width: 22px; height: 22px; fill: var(--text2); flex: none; }
  .sugrow span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rowbtn { width: 100%; padding: 10px 0; display: flex; align-items: center; gap: 12px; min-height: 56px; border-top: 1px solid var(--divider); color: inherit; text-decoration: none; }
  .rowbtn:first-child { border-top: 0; }
  .rowbtn:active { background: var(--primary-soft); }
  .rowbtn .grow { flex: 1; min-width: 0; display: grid; overflow-wrap: anywhere; }
  .rowbtn .chev { flex: none; width: 24px; height: 24px; display: grid; place-items: center; color: var(--text2); }
  .rowbtn .chev svg { width: 24px; height: 24px; fill: currentColor; display: block; }
`;

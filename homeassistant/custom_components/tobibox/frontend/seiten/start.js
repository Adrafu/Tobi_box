/* Seite „Start“ (Design 5.1, Paket A7): Schaufenster für Inhalte, nur Stufe A.
 *
 * Schnellzugriff 2 × 3: zuletzt einem Tobie zugeordnete Einträge (`zuordnung/list`, neu zuerst), danach die zuletzt
 * hinzugefügten (`serien/list`, Sortierung `neu`). Darunter die Reihen aus REIHEN; eine Reihe ohne Daten fehlt ganz.
 * Boxen, Uploads und Admin-Blöcke gehören nicht auf den Start (Design 5.1). Schnittstelle: siehe bausteine.js.
 */
import { html, nothing, kachel, schnellKachel, ladeMitGrenze } from '../bausteine.js';
import { START, SEITE } from '../texte.js';

const SCHNELL_ANZAHL = 6; // Raster 2 × 3
const NEU_ANZAHL = 8; // „die acht neuesten Einträge“

/* Reihen des Starts mit der Stufe, ab der es Daten gibt (Design 5.1 Punkt 4). `eintraege(z)` liefert Kurzformen von
 * Einträgen; ist die Liste leer, fehlt die Reihe. Neue Reihen hier eintragen (A7c: „Am Handy weiterhören“ mit eigener
 * Kachel mit Balken und Abspielknopf, Stufe B: `gehoert/zusammenfassung`). */
export const REIHEN = [
  { id: 'weiterhoeren', stufe: 'A-2', titel: START.reihen.weiterhoeren, eintraege: () => [] },
  { id: 'zuletzt_gehoert', stufe: 'B', titel: START.reihen.zuletzt_gehoert, eintraege: () => [] },
  { id: 'neu', stufe: 'A-1', titel: START.reihen.neu, eintraege: (z) => z.neu },
  { id: 'favoriten', stufe: 'B', titel: START.reihen.favoriten, eintraege: () => [] },
];

/* Reihenfolge der sechs Kacheln: erst die zugeordneten (in der Reihenfolge der Zuordnung, jeder Eintrag einmal), dann
 * die neuesten, bis sechs voll sind. `zugeordnet` und `neu` sind Listen von Kurzformen. */
export function schnellzugriff(zugeordnet, neu, max = SCHNELL_ANZAHL) {
  const aus = [];
  const gesehen = new Set();
  for (const s of [...zugeordnet, ...neu]) {
    if (!s || gesehen.has(s.id)) continue;
    gesehen.add(s.id);
    aus.push(s);
    if (aus.length >= max) break;
  }
  return aus;
}

class StartSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.z = { phase: 'laedt', fehlerCode: null, neu: [], schnell: [] };
    this._lauf = 0;
  }

  betreten() { this.laden(); }
  neuLaden() { this.laden(true); }
  verlassen() { this._lauf += 1; }

  async laden(still = false) {
    const lauf = ++this._lauf;
    if (!still || this.z.phase !== 'bereit') this.z = { ...this.z, phase: 'laedt', fehlerCode: null };
    this.ctx.neuZeichnen();
    try {
      const daten = await ladeMitGrenze(this._hole(), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.z = { phase: 'bereit', fehlerCode: null, ...daten };
    } catch (e) {
      if (lauf !== this._lauf) return;
      this.z = { ...this.z, phase: 'fehler', fehlerCode: e?.code || 'unknown_error' };
    }
    this.ctx.neuZeichnen();
  }

  async _hole() {
    const { ctx } = this;
    const [serien, zu] = await Promise.all([
      ctx.api('tobibox/serien/list', { sortierung: 'neu', limit: NEU_ANZAHL }),
      ctx.api('tobibox/zuordnung/list', { neu: true, limit: 12 }),
    ]);
    const neu = serien.serien || [];
    const bekannt = new Map(neu.map((s) => [s.id, s]));
    // Ziele der zuletzt zugeordneten Tobies; ein Eintrag fehlt in „neu“ → einzeln nachladen (höchstens sechs)
    const ids = [];
    for (const x of zu.zuordnungen || []) {
      const id = x.ziel?.typ === 'aktion' ? null : x.ziel?.serie;
      if (id && x.serie_name !== null && !ids.includes(id)) ids.push(id);
      if (ids.length >= SCHNELL_ANZAHL) break;
    }
    const fehlen = ids.filter((id) => !bekannt.has(id));
    const nachgeladen = await Promise.allSettled(fehlen.map((id) => ctx.api('tobibox/serie/get', { serie_id: id })));
    nachgeladen.forEach((r, i) => { if (r.status === 'fulfilled' && r.value?.id) bekannt.set(fehlen[i], r.value); });
    const zugeordnet = ids.map((id) => bekannt.get(id)).filter(Boolean);
    ctx.covers.merke([...bekannt.values()]);
    return { neu, schnell: schnellzugriff(zugeordnet, neu) };
  }

  render() {
    const { ctx, z } = this;
    const kopf = ctx.layout === 'seite' ? html`<h2>${ctx.begruessung()}</h2>` : html`<h2 class="sr">${SEITE.reiter.start}</h2>`;
    if (z.phase === 'laedt') return html`${kopf}${ctx.laedt()}`;
    if (z.phase === 'fehler') return html`${kopf}${ctx.fehlerKarte(z.fehlerCode, () => this.laden())}`;
    if (!z.schnell.length && !z.neu.length) return html`${kopf}${ctx.leer('start', 'bibliothekLeer', { href: '#bibliothek' })}`;
    return html`${kopf}
      ${z.schnell.length ? html`<h2 class="sr">${START.schnellzugriff}</h2><div class="qgrid" data-start="schnellzugriff">${z.schnell.map((s) => schnellKachel(s))}</div>` : nothing}
      ${REIHEN.map((r) => {
        const e = r.eintraege(z);
        return e.length ? html`<h3 class="rowh">${r.titel}</h3><div class="hscroll" data-reihe=${r.id}>${e.map((s) => kachel(s))}</div>` : nothing;
      })}`;
  }
}

export const erzeuge = (ctx) => new StartSeite(ctx);
export const stil = null; // die Bausteine (Kachel, Schnellzugriff, Reihe) bringen ihren Stil in bausteine.js mit

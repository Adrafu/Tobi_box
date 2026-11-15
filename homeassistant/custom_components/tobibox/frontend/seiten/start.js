/* Seite „Start“ (Design 5.1, Paket A7): Schaufenster für Inhalte, nur Stufe A.
 *
 * Schnellzugriff 2 × 3: zuletzt einem Tobie zugeordnete Einträge (`zuordnung/list`, neu zuerst), danach die zuletzt
 * hinzugefügten (`serien/list`, Sortierung `neu`). Darunter die Reihen aus REIHEN; eine Reihe ohne Daten fehlt ganz.
 * Boxen, Uploads und Admin-Blöcke gehören nicht auf den Start (Design 5.1). Schnittstelle: siehe bausteine.js.
 */
import { html, nothing, ic, cover, eq, laeuftAn, abspiel, kachel, schnellKachel, kopfAktion, ladeMitGrenze, dauerText } from '../bausteine.js';
import { START, SEITE, ZEILE, PLAYER, fuellen } from '../texte.js';
import { weiterReihe } from '../player.js';

const SCHNELL_ANZAHL = 6; // Raster 2 × 3
const NEU_ANZAHL = 8; // „die acht neuesten Einträge“
const WEITER_ANZAHL = 8; // Reihe „Am Handy weiterhören“

/* Reihen des Starts mit der Stufe, ab der es Daten gibt (Design 5.1 Punkt 4). `eintraege(z)` liefert Kurzformen von
 * Einträgen; ist die Liste leer, fehlt die Reihe. Neue Reihen hier eintragen (A7c: „Am Handy weiterhören“ mit eigener
 * Kachel mit Balken und Abspielknopf, Stufe B: `gehoert/zusammenfassung`). */
export const REIHEN = [
  { id: 'weiterhoeren', stufe: 'A-2', titel: START.reihen.weiterhoeren, eintraege: (z) => z.weiter || [], kachel: weiterKachel },
  { id: 'zuletzt_gehoert', stufe: 'B', titel: START.reihen.zuletzt_gehoert, eintraege: () => [] },
  { id: 'neu', stufe: 'A-1', titel: START.reihen.neu, eintraege: (z) => z.neu, alle: '#bibliothek?sortierung=neu' },
  { id: 'favoriten', stufe: 'B', titel: START.reihen.favoriten, eintraege: () => [] },
];

/* Kachel der Reihe „Am Handy weiterhören“ (A7c, Design 5.2 Punkt 4): Cover mit Balken, „noch 21 Min.“ und der runde Abspielknopf auf dem Cover.
 * `s.weiter` ist der Eintrag aus `hoerstelle/liste`; der Knopf spielt dort weiter (Folge und Stelle holt der Player selbst). */
export function weiterKachel(s, ctx) {
  const w = s.weiter || {};
  const p = Math.round(Math.max(0, Math.min(1, w.anteil ?? 0)) * 100);
  const spielt = ctx.spieler?.laeuft(s.id);
  return html`<div class="wh" data-weiter=${s.id}><a class="tile" href=${`#serie-${s.id}`} data-serie=${s.id}><span class="pos">${cover(s)}${laeuftAn(s.id) ? eq(abspiel.spielt) : nothing}</span>
      <span class="pbar" role="progressbar" aria-label=${ZEILE.fortschritt} aria-valuemin="0" aria-valuemax="100" aria-valuenow=${p}><i style=${`width:${p}%`}></i></span>
      <span class="tn">${s.name}</span><span class="tm">${fuellen(ZEILE.rest, { dauer: dauerText(w.rest_s ?? 0) })}</span></a>
    <button type="button" class="playov" data-weiter-spielen aria-label=${fuellen(PLAYER.reihe.weiterhoeren, { name: s.name })} @click=${() => ctx.spieler.spieleId(s.id, w.folge ?? null)}>${ic(spielt ? 'pause' : 'play', 24)}</button></div>`;
}

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
    this.z = { phase: 'laedt', fehlerCode: null, neu: [], schnell: [], weiter: [] };
    this._lauf = 0;
  }

  betreten() { this.laden(this.z.phase === 'bereit'); } // schon Daten da: still auffrischen, kein Platzhalter-Blitz beim Reiterwechsel
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
    const rein = ctx.faehig('reinhoeren');
    const [serien, zu, liste, angehoert] = await Promise.all([
      ctx.api('tobibox/serien/list', { sortierung: 'neu', limit: NEU_ANZAHL }),
      ctx.api('tobibox/zuordnung/list', { neu: true, limit: 12 }),
      // Reihe „Am Handy weiterhören“ (A7c): die eigene Hörstelle; ein Fehler dort lässt nur diese Reihe weg, nie den Start
      rein ? ctx.api('tobibox/hoerstelle/liste', { limit: WEITER_ANZAHL }).catch(() => null) : null,
      rein ? ctx.api('tobibox/serien/list', { sortierung: 'angehoert', limit: 24 }).catch(() => null) : null,
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
    ctx.covers.merke([...bekannt.values(), ...(angehoert?.serien || [])]);
    return { neu, schnell: schnellzugriff(zugeordnet, neu), weiter: weiterReihe(liste?.eintraege, angehoert?.serien) };
  }

  /* Aktionen im Seitenkopf: die Lupe (am Computer als Pille „Suchen“). */
  kopfAktionen() { return kopfAktion({ href: '#suche', label: SEITE.suchen, symbol: 'search' }); }

  /* Pfeile der Reihen (nur bei Maus-Hover am Computer sichtbar, AB5): blättern um die sichtbare Breite minus eine Kachel. */
  _blaettern(e, richtung) {
    const reihe = e.currentTarget.closest('.reihe')?.querySelector('.hscroll');
    if (!reihe) return;
    const kachel = (reihe.querySelector('.tile')?.offsetWidth || 0) + 12;
    const schritt = Math.max(120, reihe.clientWidth - kachel) * richtung;
    let ruhig = false;
    try { ruhig = window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch { /* ohne matchMedia: mit Bewegung */ }
    try { reihe.scrollBy({ left: schritt, behavior: ruhig ? 'auto' : 'smooth' }); } catch { reihe.scrollLeft += schritt; }
  }

  /* Stand der Reihe: Pfeile grau/weg am Anfang und Ende, Verlauf links erst nach dem Scrollen, rechts solange es weitergeht. */
  nachRender(wurzel) {
    for (const reihe of wurzel.querySelectorAll('.reihe')) {
      const sc = reihe.querySelector('.hscroll');
      if (!sc) continue;
      const stand = () => {
        const [zu, vor] = reihe.querySelectorAll('.pfeil');
        const links = sc.scrollLeft > 1;
        const rechts = sc.scrollLeft + sc.clientWidth < sc.scrollWidth - 1;
        if (zu) zu.disabled = !links;
        if (vor) vor.disabled = !rechts;
        reihe.toggleAttribute('data-links', links);
        reihe.toggleAttribute('data-rechts', rechts);
      };
      if (!sc._pfeile) { sc._pfeile = true; sc.addEventListener('scroll', stand, { passive: true }); }
      stand();
    }
  }

  render() {
    const { ctx, z } = this;
    const kopf = html`<h2 class="sr">${ctx.layout === 'seite' ? ctx.begruessung() : SEITE.reiter.start}</h2>`;
    if (z.phase === 'laedt') return html`${kopf}${ctx.laedt()}`;
    if (z.phase === 'fehler') return html`${kopf}${ctx.fehlerKarte(z.fehlerCode, () => this.laden())}`;
    if (!z.schnell.length && !z.neu.length && !z.weiter.length) return html`${kopf}${ctx.leer('start', 'bibliothekLeer', { href: '#bibliothek' })}`;
    return html`${kopf}
      ${z.schnell.length ? html`<h2 class="sr">${START.schnellzugriff}</h2><div class="qgrid" data-start="schnellzugriff">${z.schnell.map((s) => schnellKachel(s))}</div>` : nothing}
      ${REIHEN.map((r) => {
        const e = r.eintraege(z);
        return e.length ? html`<section class="reihe"><div class="reihenkopf"><h3 class="rowh">${r.titel}</h3>
          ${r.alle ? html`<a class="alle" href=${r.alle}>${START.alle}</a>` : nothing}</div>
          <div class="reihenfeld">
            <button type="button" class="pfeil zu" aria-label=${START.pfeil.zurueck} @click=${(ev) => this._blaettern(ev, -1)}>${ic('chev', 24)}</button>
            <div class="hscroll" data-reihe=${r.id}>${e.map((s) => (r.kachel ?? kachel)(s, ctx))}</div>
            <button type="button" class="pfeil vor" aria-label=${START.pfeil.vor} @click=${(ev) => this._blaettern(ev, 1)}>${ic('chev', 24)}</button></div></section>` : nothing;
      })}`;
  }
}

export const erzeuge = (ctx) => new StartSeite(ctx);
export const stil = null; // die Bausteine (Kachel, Schnellzugriff, Reihe) bringen ihren Stil in bausteine.js mit

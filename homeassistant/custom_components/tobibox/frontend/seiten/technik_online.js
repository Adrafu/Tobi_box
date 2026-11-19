/* Technik › „Online-Suche“ (Design docs/designs/online-suche.md Abschnitt 5.3, 6.4 und 10, Paket OS4): Zustand der Quellen (Apple, Tonies, Tonies-Shop, Claude, Tonie-Liste),
 * „Bibliothek durchsuchen“ / „Anhalten“ mit Fortschritt, die letzten Läufe mit Zahlen und Zustand und „Alle zurücknehmen“ je Lauf.
 *
 * Nur für Administratoren mit der Fähigkeit `online_suche` (das Gerüst und technik.js halten alle anderen fern). Daten: Befehl 63 `online/status` beim Betreten,
 * danach das Ereignis `online` (Vertrag 4.11: `snapshot`, `stand`, `fertig`, `quelle`; die App abonniert es nur für Administratoren). Der Lauf braucht die Seite nicht;
 * ein Lauf, der ohne `grund` abgebrochen ist (Fehler außerhalb einer Serie), steht als „Abgebrochen.“ ohne Grund da. Befehle: Nr. 62 `online/lauf` (start, stop),
 * Nr. 60 `online/zuruecknehmen` mit `lauf_id` (läuft im Hintergrund, das Ergebnis kommt als Ereignis `fertig` mit `vorgang = zuruecknahme`).
 *
 * T11 (Fähigkeit `online_lauf_liste`): je Lauf mit Änderungen eine aufklappbare „Liste der Änderungen“ (Nr. 65 `online/lauf_aenderungen`, beim Aufklappen frisch geholt):
 * je Eintrag Name (Link auf die Serie), Felder in Klartext, Status und bei `fertig` ein eigenes „Zurücknehmen“ (Nr. 60 mit `serie_id` + `aenderung_id`, sofort, mit der
 * Antwort). Ohne die Fähigkeit bleibt es bei den Zahlen und „Alle zurücknehmen“.
 */
import { html, nothing, css, ladeMitGrenze, zaehle } from '../bausteine.js';
import { ONLINE, TECHNIK, fuellen } from '../texte.js';
import { zeitKurz } from '../tobibox-panel.js';
import { uhrzeit, quellenName, feldListe } from './online.js';

const QUELLEN = ['itunes', 'tonies', 'tonies_shop'];
const AKTIV = ['laeuft', 'pausiert', 'wird_angehalten'];
export const LISTE_MAX = 500; // Vertrag Nr. 65: höchstens so viele Einträge, dann `weitere`

/* ------------------------------------------------------------------ reine Funktionen */

/* Zeile zu einer Quelle aus Nr. 63: erreichbar, Pause bis … oder „antwortet gerade nicht“. */
export function quellenZustand(q, zone) {
  if (!q || q.erreichbar === true) return ONLINE.technik.quelle_ok;
  const uhr = uhrzeit(q.pause_bis, zone);
  return uhr ? fuellen(ONLINE.technik.quelle_pause, { uhr_bis: uhr }) : ONLINE.technik.quelle_aus;
}

/* Claude: nicht eingerichtet, bereit oder antwortet nicht. */
export function claudeZustand(c) {
  if (!c || c.eingerichtet !== true) return ONLINE.technik.claude_aus;
  return c.erreichbar === true ? ONLINE.technik.claude_ok : ONLINE.technik.claude_nein;
}

const zahlenWerte = (z) => ({ erledigt: z?.erledigt ?? 0, gesamt: z?.gesamt ?? 0, geaendert: z?.geaendert ?? 0, vorschlaege: z?.vorschlaege ?? 0, keiner: z?.keiner ?? 0 });

/* „Fertig: 120 Einträge geändert, 38 Vorschläge, 12 ohne Treffer.“ bzw. der Zustand eines beendeten Laufs (`abgebrochen` darf ohne `grund` kommen). */
export function laufEndeText(l) {
  const T = ONLINE.technik;
  if (l.zustand === 'fertig') return fuellen(T.fertig, zahlenWerte(l.zahlen));
  if (l.zustand === 'angehalten') return T.angehalten;
  if (l.zustand === 'abgebrochen') return (l.grund && T.abgebrochen_grund[l.grund]) || T.abgebrochen;
  return T.abgebrochen;
}

/* Satz zum laufenden Lauf: Pause (mit der bremsenden Quelle, wenn bekannt), „Hält nach dieser Serie an.“ oder der Fortschritt. */
export function laufText(lauf, quellen, zone) {
  const T = ONLINE.technik;
  if (!lauf) return T.kein_lauf;
  if (lauf.zustand === 'wird_angehalten') return T.wird_angehalten;
  if (lauf.zustand === 'pausiert') {
    const uhr = uhrzeit(lauf.pause_bis, zone);
    const q = QUELLEN.find((n) => quellen?.[n]?.pause_bis && quellen[n].pause_bis === lauf.pause_bis) ?? QUELLEN.find((n) => quellen?.[n]?.pause_bis);
    return q ? fuellen(T.pause, { uhr_bis: uhr, quelle: quellenName(q) }) : fuellen(T.pause_ohne, { uhr_bis: uhr });
  }
  return fuellen(T.laeuft, zahlenWerte(lauf));
}

/* ------------------------------------------------------------------ Seite */

export class OnlineSeite {
  /* `technik`: die Seite (für `tu`, `beschaeftigt`). */
  constructor(ctx, technik) {
    this.ctx = ctx;
    this.technik = technik;
    this.z = { phase: 'laedt', fehlerCode: null, status: null };
    this.rueck = null; // laufende Rücknahme eines Laufs: { lauf_id, erledigt, gesamt } oder null
    this._lauf = 0;
    this._abmelden = null;
    this._fertigeRueck = new Set(); // `lauf_id` der Rücknahmen, deren Ereignis `fertig` schon da war (es kann vor der Antwort auf Nr. 60 kommen)
    this.listen = new Map(); // aufgeklappte Listen der Änderungen: lauf_id → { phase: 'laedt'|'bereit'|'fehler', eintraege, weitere, fehlerCode, n }
  }

  hatListe() { return this.ctx.faehig('online_lauf_liste'); }

  zone() { return this.ctx.hass?.config?.time_zone || undefined; }

  betreten() {
    this.rueck = null; // die Wahrheit liefert Nr. 63; ein verpasstes `fertig` darf „Wird zurückgenommen“ nicht festhalten (GO4-1)
    this._fertigeRueck = new Set();
    this.listen = new Map(); // die Listen sind beim Wiederkommen zu (und frisch, wenn sie aufgehen)
    this._beobachten();
    this.laden({ still: this.z.phase === 'bereit' });
  }

  verlassen() {
    this._lauf += 1;
    try { this._abmelden?.(); } catch { /* egal */ }
    this._abmelden = null;
  }

  async laden({ still = false } = {}) {
    const lauf = ++this._lauf;
    if (!still || this.z.phase !== 'bereit') this.z = { ...this.z, phase: 'laedt', fehlerCode: null };
    this.ctx.neuZeichnen();
    try {
      const r = await ladeMitGrenze(this.ctx.api('tobibox/online/status'), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.z = { phase: 'bereit', fehlerCode: null, status: r };
    } catch (err) {
      if (lauf !== this._lauf) return;
      this.z = { ...this.z, phase: 'fehler', fehlerCode: err?.code || 'unknown_error' };
    }
    this.ctx.neuZeichnen();
  }

  /* Ereignisse des Themas `online`: `snapshot` ersetzt den Stand, `stand` und `fertig` führen den Lauf nach (die Rücknahme getrennt), `quelle` setzt eine Quelle. */
  _beobachten() {
    if (this._abmelden) return;
    this._abmelden = this.ctx.ereignis?.((ev) => { if (ev?.thema === 'online') this._ereignis(ev); }) ?? null;
  }

  _ereignis(ev) {
    const d = ev.daten || {};
    const st = this.z.status;
    if (ev.art === 'snapshot') { this.rueck = null; this.z = { phase: 'bereit', fehlerCode: null, status: d }; this.ctx.neuZeichnen(); return; }
    if (!st) return;
    if (ev.art === 'quelle' && d.quelle) {
      const q = { erreichbar: d.erreichbar === true, ...(d.pause_bis ? { pause_bis: d.pause_bis } : {}) };
      this.z = { ...this.z, status: { ...st, quellen: { ...st.quellen, [d.quelle]: q } } };
    } else if (ev.art === 'stand' && d.vorgang === 'zuruecknahme') {
      if (!this._fertigeRueck.has(d.lauf_id)) this.rueck = { lauf_id: d.lauf_id, erledigt: d.erledigt ?? 0, gesamt: d.gesamt ?? 0 };
    } else if (ev.art === 'stand') {
      const { vorgang, ...rest } = d; // eslint-disable-line no-unused-vars
      this.z = { ...this.z, status: { ...st, lauf: { ...(st.lauf || {}), ...rest } } };
    } else if (ev.art === 'fertig' && d.vorgang === 'zuruecknahme') {
      this.rueck = null;
      this._fertigeRueck.add(d.lauf_id);
      const n = d.uebersprungen_anzahl ?? 0;
      this.ctx.melde(n > 0 ? zaehle(ONLINE.zuruecknehmen.uebersprungen, n) : ONLINE.zuruecknehmen.fertig);
      this.laden({ still: true });
      if (this.listen.has(d.lauf_id)) this.ladeListe(d.lauf_id, { still: true }); // die Stati der offenen Liste sind jetzt andere
    } else if (ev.art === 'fertig') {
      const { vorgang, lauf_id, zustand, grund, ...zahlen } = d; // eslint-disable-line no-unused-vars
      const neu = { lauf_id, zustand, ...(grund ? { grund } : {}), ende: new Date().toISOString(), zahlen: zahlenWerte(zahlen) }; // vorläufig, bis Nr. 63 die Liste liefert: sonst steht kurz das Ende des vorigen Laufs da
      const alt = (st.letzte_laeufe || []).filter((x) => x.lauf_id !== lauf_id);
      this.z = { ...this.z, status: { ...st, lauf: null, letzte_laeufe: [neu, ...alt] } };
      this.laden({ still: true }); // `letzte_laeufe` kommt nur mit Nr. 63
    }
    this.ctx.neuZeichnen();
  }

  /* ---- Aktionen */
  async starten() {
    const ok = await this.technik.tu('online_lauf', async () => {
      const r = await this.ctx.api('tobibox/online/lauf', { aktion: 'start' });
      this.z = { ...this.z, status: { ...(this.z.status || {}), lauf: r?.lauf ?? null } };
    });
    if (ok) this.ctx.melde(ONLINE.technik.gestartet);
    else this.laden({ still: true }); // `lauf_laeuft_schon`: der Stand der Seite war alt
  }

  async anhalten() {
    await this.technik.tu('online_lauf', async () => {
      const r = await this.ctx.api('tobibox/online/lauf', { aktion: 'stop' });
      this.z = { ...this.z, status: { ...(this.z.status || {}), lauf: r?.lauf ?? null } };
    });
  }

  alleZuruecknehmen(l) {
    const { ctx } = this;
    const T = ONLINE.technik;
    const anzahl = l.zahlen?.geaendert ?? 0;
    return new Promise((fertig) => {
      let ja = false;
      ctx.oeffneBlatt({
        titel: T.alle_zurueck_titel,
        rolle: 'alertdialog',
        inhalt: html`<p data-alle-zurueck-text>${zaehle(T.alle_zurueck_text, anzahl)}</p>`,
        knoepfe: [{ label: TECHNIK.abbrechen }, { label: T.alle_zurueck, kind: 'primary', fn: () => { ja = true; } }],
      }).then(() => fertig(ja));
    }).then(async (ja) => {
      if (!ja) return;
      const ok = await this.technik.tu('online_zurueck', async () => {
        await ctx.api('tobibox/online/zuruecknehmen', { lauf_id: l.lauf_id });
        if (!this._fertigeRueck.has(l.lauf_id) && this.rueck?.lauf_id !== l.lauf_id) this.rueck = { lauf_id: l.lauf_id, erledigt: 0, gesamt: anzahl }; // das Ereignis `stand`/`fertig` führt es nach
      });
      if (!ok) this.laden({ still: true }); // `lauf_nicht_gefunden`: die Liste der Läufe war alt
      ctx.neuZeichnen();
    });
  }

  /* ---- Liste der Änderungen (T11) */
  listeUmschalten(laufId) {
    if (this.listen.has(laufId)) { this.listen.delete(laufId); this.ctx.neuZeichnen(); return; }
    this.ladeListe(laufId);
  }

  async ladeListe(laufId, { still = false } = {}) {
    const alt = this.listen.get(laufId);
    const n = (this._listeN = (this._listeN ?? 0) + 1); // ein Zähler je Seite: eine späte Antwort einer zugeklappten Liste zählt nie
    if (!still || !alt || alt.phase !== 'bereit') this.listen.set(laufId, { phase: 'laedt', eintraege: [], weitere: false, fehlerCode: null, n });
    else this.listen.set(laufId, { ...alt, n });
    this.ctx.neuZeichnen();
    try {
      const r = await ladeMitGrenze(this.ctx.api('tobibox/online/lauf_aenderungen', { lauf_id: laufId }), this.ctx.grenzeMs);
      if (this.listen.get(laufId)?.n !== n) return; // zugeklappt oder neuer geholt
      this.listen.set(laufId, { phase: 'bereit', eintraege: Array.isArray(r?.eintraege) ? r.eintraege : [], weitere: r?.weitere === true, fehlerCode: null, n });
    } catch (err) {
      if (this.listen.get(laufId)?.n !== n) return;
      const code = err?.code || 'unknown_error';
      if (code === 'lauf_nicht_gefunden') { // der Lauf ist nicht mehr unter den letzten 5: die Liste der Läufe war alt
        this.listen.delete(laufId);
        this.ctx.meldeFehler(this.ctx.fehlerText(code));
        this.laden({ still: true });
      } else this.listen.set(laufId, { phase: 'fehler', eintraege: [], weitere: false, fehlerCode: code, n });
    }
    this.ctx.neuZeichnen();
  }

  /* „Zurücknehmen“ eines Eintrags: Nr. 60 mit `serie_id` + `aenderung_id`; `tu` lässt keinen zweiten Tipp durch, solange eines läuft. */
  async eintragZuruecknehmen(laufId, e) {
    let code = null;
    let r = null;
    const ok = await this.technik.tu('online_zurueck_eintrag', async () => {
      try { r = await this.ctx.api('tobibox/online/zuruecknehmen', { serie_id: e.serie_id, aenderung_id: e.aenderung_id }); } catch (err) { code = err?.code || null; throw err; }
    });
    const L = this.listen.get(laufId);
    if (ok) {
      const n = r?.uebersprungen_anzahl ?? (r?.uebersprungen || []).length;
      this.ctx.melde(n > 0 ? zaehle(ONLINE.zuruecknehmen.uebersprungen, n) : ONLINE.zuruecknehmen.fertig);
      if (L && (r?.zurueckgenommen ?? 0) > 0) this.listen.set(laufId, { ...L, eintraege: L.eintraege.map((x) => (x.aenderung_id === e.aenderung_id ? { ...x, status: 'zurueckgenommen' } : x)) }); // ganz übersprungen: bleibt „Geändert“
    }
    if (this.listen.has(laufId)) this.ladeListe(laufId, { still: true }); // die Wahrheit holen (auch nach einem Fehler: `aenderung_nicht_gefunden` heißt, die Liste war alt)
    if (code === 'aenderung_nicht_gefunden' || code === 'lauf_nicht_gefunden') this.laden({ still: true });
    this.ctx.neuZeichnen();
  }

  _liste(l) {
    const T = ONLINE.technik;
    const L = this.listen.get(l.lauf_id);
    if (!L) return nothing;
    const zu = !!this.technik.beschaeftigt || !!this.rueck;
    let inhalt;
    if (L.phase === 'laedt') inhalt = html`<p class="muted" data-liste-laedt role="status">${T.liste_laedt}</p>`;
    else if (L.phase === 'fehler') inhalt = this.ctx.fehlerKarte(L.fehlerCode, () => this.ladeListe(l.lauf_id));
    else {
      inhalt = L.eintraege.length ? html`<ul class="to-eintraege" data-liste-eintraege=${l.lauf_id}>${L.eintraege.map((e) => {
        const felder = feldListe(e.felder);
        const zurueck = e.status === 'zurueckgenommen';
        return html`<li class="to-eintrag" data-eintrag=${e.aenderung_id} data-status=${e.status}>
          <span class="to-etext"><a class="to-ename" href=${`#serie-${encodeURIComponent(e.serie_id)}`} data-eintrag-serie=${e.serie_id}>${e.name}</a>
            <span class="muted" data-eintrag-felder>${felder}</span>
            <span class=${zurueck ? 'muted to-status' : 'to-status'} data-eintrag-status>${T.liste_status[e.status] ?? ''}</span></span>
          ${zurueck ? nothing : html`<button type="button" class="btn" data-eintrag-zurueck=${e.aenderung_id} aria-label=${fuellen(T.eintrag_zurueck_aria, { name: e.name, felder })} ?disabled=${zu} @click=${() => this.eintragZuruecknehmen(l.lauf_id, e)}>${T.eintrag_zurueck}</button>`}</li>`;
      })}</ul>` : html`<p class="muted" data-liste-leer>${T.liste_leer}</p>`;
      if (L.weitere) inhalt = html`${inhalt}<p class="muted" data-liste-weitere role="status">${fuellen(T.liste_weitere, { max: LISTE_MAX })}</p>`;
    }
    return html`<div class="to-liste-aend" id=${`to-liste-${l.lauf_id}`} data-liste-aenderungen=${l.lauf_id}>${inhalt}</div>`;
  }

  /* ---- Darstellung */
  _quellen(st) {
    const T = ONLINE.technik;
    const zeile = (name, text, daten) => html`<li data-quelle=${daten}><span class="to-name">${name}</span> <span class="muted to-wert" data-quelle-zustand>${text}</span></li>`;
    const l = st.tonie_liste;
    const listeText = l ? fuellen(T.liste_stand, { stand: zeitKurz(l.stand) || '–', anzahl: zaehle(T.liste_eintraege, l.anzahl ?? 0) }) : T.liste_keine;
    return html`<section class="tkarte" data-karte="online-quellen" aria-labelledby="to-quellen"><h3 id="to-quellen">${T.quellen}</h3>
      <ul class="to-liste">${QUELLEN.map((q) => zeile(quellenName(q), quellenZustand(st.quellen?.[q], this.zone()), q))}
        ${zeile(quellenName('claude'), claudeZustand(st.quellen?.claude), 'claude')}
        ${zeile(T.liste, listeText, 'tonie_liste')}</ul></section>`;
  }

  _lauf_(st) {
    const T = ONLINE.technik;
    const l = st.lauf;
    const aktiv = !!l && AKTIV.includes(l.zustand);
    const zu = !!this.technik.beschaeftigt;
    const ende = !aktiv ? (st.letzte_laeufe || [])[0] : null;
    const p = aktiv && l.gesamt > 0 ? Math.round(Math.min(1, (l.erledigt ?? 0) / l.gesamt) * 100) : 0;
    return html`<section class="tkarte" data-karte="online-lauf" aria-labelledby="to-lauf"><h3 id="to-lauf">${T.lauf}</h3>
      <p data-lauf-zustand=${aktiv ? l.zustand : 'kein'} role="status">${aktiv ? laufText(l, st.quellen, this.zone()) : T.kein_lauf}</p>
      ${aktiv ? html`<span class="pbar" role="progressbar" aria-label=${T.fortschritt} aria-valuemin="0" aria-valuemax="100" aria-valuenow=${p}><i style=${`width:${p}%`}></i></span>
        <p class="muted" data-lauf-zahlen>${fuellen(T.zahlen, zahlenWerte(l))}</p>` : nothing}
      ${this.rueck ? html`<p class="muted" data-rueck-laeuft role="status">${fuellen(T.rueck_laeuft, zahlenWerte(this.rueck))}</p>` : nothing}
      <div class="btns tknoepfe">${aktiv
    ? html`<button type="button" class="btn" data-aktion="online_anhalten" ?disabled=${zu || l.zustand === 'wird_angehalten'} @click=${() => this.anhalten()}>${T.anhalten}</button>`
    : html`<button type="button" class="btn primary" data-aktion="online_starten" ?disabled=${zu} @click=${() => this.starten()}>${T.starten}</button>`}</div>
      ${ende && !aktiv ? html`<p class="muted" data-lauf-ende>${laufEndeText(ende)}</p>` : nothing}</section>`;
  }

  _letzte(st) {
    const T = ONLINE.technik;
    const liste = st.letzte_laeufe || [];
    const zu = !!this.technik.beschaeftigt || !!this.rueck;
    return html`<section class="tkarte" data-karte="online-laeufe" aria-labelledby="to-letzte"><h3 id="to-letzte">${T.letzte}</h3>
      ${liste.length ? html`<ul class="to-laeufe" data-liste="laeufe">${liste.map((l) => {
    const zeit = zeitKurz(l.ende || l.beginn) || '–';
    const geaendert = l.zahlen?.geaendert ?? 0;
    return html`<li class="to-lauf" data-lauf=${l.lauf_id} data-zustand=${l.zustand}><span class="to-name">${fuellen(T.lauf_vom, { zeit })}</span>
          <span data-lauf-text>${laufEndeText(l)}</span>
          ${l.zustand !== 'fertig' ? html`<span class="muted" data-lauf-zahlen>${fuellen(T.zahlen, zahlenWerte(l.zahlen))}</span>` : nothing}
          ${geaendert > 0 ? html`<div class="btns">${this.hatListe() ? html`<button type="button" class="btn" data-liste-auf=${l.lauf_id} aria-expanded=${this.listen.has(l.lauf_id) ? 'true' : 'false'} aria-controls=${this.listen.has(l.lauf_id) ? `to-liste-${l.lauf_id}` : nothing} aria-label=${fuellen(T.aenderungen_aria, { zeit })} @click=${() => this.listeUmschalten(l.lauf_id)}>${T.aenderungen}</button>` : nothing}
            <button type="button" class="btn" data-alle-zurueck=${l.lauf_id} aria-label=${fuellen(T.alle_zurueck_aria, { zeit })} ?disabled=${zu} @click=${() => this.alleZuruecknehmen(l)}>${T.alle_zurueck}</button></div>` : nothing}
          ${geaendert > 0 && this.hatListe() ? this._liste(l) : nothing}</li>`;
  })}</ul>` : html`<p class="muted" data-keine-laeufe>${T.keine_laeufe}</p>`}</section>`;
  }

  render() {
    const { ctx, z } = this;
    if (z.phase === 'laedt') return ctx.laedt();
    if (z.phase === 'fehler') return ctx.fehlerKarte(z.fehlerCode, () => this.laden());
    const st = z.status || {};
    return html`<div data-online-seite>${this._lauf_(st)}${this._quellen(st)}${this._letzte(st)}</div>`;
  }
}

export function onlineStil() {
  return css`
  .to-liste, .to-laeufe { list-style: none; margin: 4px 0 8px; padding: 0; display: grid; gap: 0; }
  .to-liste li { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 2px 12px; padding: 10px 0; border-top: 1px solid var(--divider); }
  .to-liste li:first-child { border-top: 0; }
  .to-name { font-weight: 500; }
  .to-wert { text-align: right; overflow-wrap: anywhere; }
  .to-lauf { display: grid; gap: 2px; padding: 12px 0; border-top: 1px solid var(--divider); }
  .to-lauf:first-child { border-top: 0; }
  .to-lauf .btns { margin-top: 6px; }
  .to-eintraege { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 0; }
  .to-eintrag { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 4px 12px; padding: 10px 0; border-top: 1px solid var(--divider); }
  .to-eintrag:first-child { border-top: 0; }
  .to-etext { display: grid; gap: 2px; min-width: 0; flex: 1 1 200px; overflow-wrap: anywhere; justify-items: start; }
  .to-ename { font-weight: 500; display: inline-flex; align-items: center; min-height: 44px; color: var(--primary-ink); text-decoration: none; border-radius: 8px; }
  .to-ename:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
  .to-status { font-size: 14px; }
  `;
}

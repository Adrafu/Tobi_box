/* Gemeinsame Bausteine der Seiten (Paket A7, Design docs/designs/ha-oberflaeche.md, Abschnitte 4, 5.2, 6.2).
 *
 * Wer eine Seite baut (seiten/start.js, bibliothek.js, suche.js; später geraete.js, serie.js, technik.js),
 * nimmt hier die Bausteine und trägt sich in seiten/index.js ein. Dieses Modul lädt auch ohne DOM
 * (Tests der reinen Funktionen); `html` und die anderen Lit-Teile sind dann `undefined`.
 *
 * ---------------------------------------------------------------------------------------- Seiten-Vertrag
 * seiten/index.js: `SEITEN = { <Routenname>: { erzeuge(ctx), stil } }`. Der Routenname ist `parseRoute(hash).name`
 * (start, bibliothek, suche, serie, tobie, box, technik …). `stil` ist ein Lit-`css`-Ergebnis (oder `null`).
 * `erzeuge(ctx)` gibt EIN Objekt zurück, das die App je Seite einmal anlegt und behält (Zustand wie Art oder
 * Sortierung bleibt beim Hin- und Herwechseln erhalten):
 *
 *   betreten(route)      Die Seite wird sichtbar (auch bei neuer Adresse derselben Seite, zum Beispiel #serie-<id>).
 *                        Hier Daten laden; solange sie fehlen, rendert die Seite `ctx.laedt()`.
 *   render(route)        Gibt ein Lit-Template zurück. Rein lesend, ruft nie selbst `api`.
 *   nachRender(wurzel)   (optional) nach jedem Zeichnen: Fokus setzen, Beobachter anhängen. `wurzel` = Shadow-Root.
 *   verlassen()          (optional) Aufräumen: Zeitgeber löschen, laufende Antworten verwerfen (Zähler erhöhen).
 *   neuLaden()           (optional) Verbindung ist wieder da: Daten frisch holen.
 *
 * ---------------------------------------------------------------------------------------------- `ctx`
 *   api(type, felder)           Promise auf `hass.connection.sendMessagePromise`; Fehler sind { code, message }.
 *   faehig(name)                gibt `true`, wenn `hello.faehigkeiten` den Namen nennt (Vertrag 9).
 *   admin, layout               Administrator? ; 'unten' | 'oben' | 'seite'.
 *   neuZeichnen()               fordert ein neues Zeichnen der App an (nach jeder Änderung des Zustands).
 *   laedt()                     graue Platzhalter-Karten (Design 6, „Lädt“).
 *   fehlerKarte(code, neu)      rote Karte mit „Noch einmal versuchen“ (ruft `neu`).
 *   leer(art, bild, opts)       leerer Zustand (Design 6.2): `art` = Schlüssel in LEER, `bild` = Name der
 *                               Illustration, opts = { werte, href, aktion }.
 *   oeffneBlatt(opts), schliesseBlatt(grund)   Blätter. `inhalt` darf eine Funktion sein (wird bei jedem Zeichnen
 *                               neu aufgerufen, so ändert sich das Blatt mit dem Zustand).
 *   melde(text, opts), meldeFehler(text), ansage(text)   Meldungen und Ansage für Screenreader.
 *   covers                      CoverLader (unten): `merke(serien)` nach jeder Antwort mit Kurzformen.
 *   grenzeMs                    Zeitgrenze fürs Laden (Design 6: 10 s), für `ladeMitGrenze`.
 *   uploadBand()                Platz für das Band der laufenden Uploads (A11 füllt es, bis dahin `nothing`).
 *   navigiere(hash, { ersetzen })   Seitenwechsel wie in Home Assistant (`history.pushState` und `location-changed`, Befund B1).
 *   ereignis(fn)                `fn(ev)` für jedes Ereignis des Abos; gibt die Abmeldung zurück (A9/A10: Weg 1, Wartekarte).
 *   boxAnzeige(box), neue(), warteschlange(), warteschlangeNeuLaden(), platz(), platzEntfernen(uid)   Boxnamen, unbekannte Tobies,
 *                               Vormerkungen und Tobies, die eine Vormerkung ohne Namen genommen haben (A9/A10, seiten/tobies.js).
 *
 * ---------------------------------------------------------------------------------------- Bausteine
 *   ic(name, größe)             Symbol (SVG). Namen: ICON.
 *   cover(s, größe)             Cover mit Platzhalter (Buchstabe, eine von sechs Farben aus der ID); das Bild lädt
 *                               der CoverLader erst, wenn es sichtbar wird. `s` = { id, name, cover_stand }.
 *   coverAktion(größe, symbol)  Cover für Aktionen (Gute Nacht).
 *   listenZeile(s, { term })    Zeile der Bibliothek (72-px-Cover, Titel, Untertitel, Fortschritt, Tobie-Symbol).
 *   kachel(s)                   Kachel für Reihen (120 px). schnellKachel(s): flache Kachel für 2 × 3.
 *   folgenZeile(x, opts)        Zeile „Folge oder Lied“ der Suche; `opts.aktionen` nimmt Abspielen und „⋯“ (A8b, A9).
 *   segment({ label, optionen, wert, onWahl })   Segment-Umschalter (Design 4); Pfeiltasten wählen den Nachbarn.
 *   leererZustand({ art, bild, satz, knopf })    Bild, ein Satz, ein Knopf (Design 6.2).
 *   bausteinStil()              das CSS dazu; die App hängt es vor die Stile der Seiten.
 *   Reine Funktionen: norm, zaehle, dauerText, uhr, untertitel, fortschritt, coverKlasse, teile, ladeMitGrenze.
 */
import { fuellen, ZEILE } from './texte.js';

/* Lit steckt in lebenden Bindungen: Ohne DOM sind sie `undefined`. Wer das Modul ohne DOM lädt (Tests der reinen Funktionen),
 * bekommt sie mit `initLit(lit)` nachgereicht; tobibox-app.js ruft das, sobald es Lit geladen hat. Stile sind darum Funktionen. */
export let html;
export let nothing;
export let repeat;
export let classMap;
export let css;
export function initLit(l) {
  if (!l) return;
  ({ html, nothing, repeat, classMap, css } = l);
}
if (typeof HTMLElement !== 'undefined' && typeof customElements !== 'undefined') initLit(await import('./lit-all.min.js'));

/* ------------------------------------------------------------------ reine Funktionen */

/* Kleinschreibung ohne Akzente und Umlaute (ä = a), für Suche und Hervorhebung. */
export function norm(s) {
  return String(s ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

/* Zählwort: `paar` = { eins, mehr } aus texte.js. */
export function zaehle(paar, n) {
  return fuellen(n === 1 ? paar.eins : paar.mehr, { anzahl: n });
}

const zwei = (n) => String(n).padStart(2, '0');

/* „26 Min.“, „9 Std. 40 Min.“, „45 Sek.“ */
export function dauerText(sek) {
  const d = ZEILE.dauer;
  if (sek < 60) return `${Math.round(sek)} ${d.sek}`;
  const m = Math.round(sek / 60);
  if (m >= 60) return `${Math.floor(m / 60)} ${d.std}${m % 60 ? ` ${m % 60} ${d.min}` : ''}`;
  return `${m} ${d.min}`;
}

/* „1:06“, „1:02:03“ (für Einzeltitel). */
export function uhr(sek) {
  const s = Math.max(0, Math.round(sek));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h ? `${h}:${zwei(m)}:${zwei(s % 60)}` : `${m}:${zwei(s % 60)}`;
}

const gueltigeDauer = (x) => (typeof x === 'number' && Number.isFinite(x) && x > 0 ? x : null);

/* Untertitel eines Eintrags (Design 5.2 Punkt 5): „Hörspiel · 12 Folgen · 26 Min.“, „Hörbuch · 14 Kapitel · 9 Std. 40 Min.“,
 * „Musik · 20 Lieder“, „Lied · einzeln · 1:06“. Zahlen aus `anzahl_folgen`, `kapitel_anzahl`, `dauer_s`; ohne Dauer fehlt sie
 * (in A-1 liefert das Backend noch keine). `dauer: false` lässt sie auch weg (Kacheln). */
export function untertitel(s, { dauer = true } = {}) {
  const art = ZEILE.art[s.art] ? s.art : 'hoerspiel';
  const sek = dauer ? gueltigeDauer(s.dauer_s) : null;
  const n = s.anzahl_folgen ?? 0;
  const teile = [];
  if (s.einzeln) {
    teile.push(ZEILE.einzeln_art[art], ZEILE.einzeln);
    if (sek) teile.push(uhr(sek));
    return teile.join(' · ');
  }
  if (art === 'geschichte') teile.push(zaehle(ZEILE.geschichten, n));
  else {
    teile.push(ZEILE.art[art]);
    if (art === 'hoerbuch') {
      if (s.kapitel_anzahl > 0) teile.push(zaehle(ZEILE.kapitel, s.kapitel_anzahl));
      else if (n > 1) teile.push(zaehle(ZEILE.folgen, n));
    } else teile.push(zaehle(art === 'musik' ? ZEILE.lieder : ZEILE.folgen, n));
  }
  if (sek) teile.push(dauerText(sek));
  return teile.join(' · ');
}

/* Fortschritt aus `hoerstelle` ({ anteil, rest_s }) oder null: { anteil (0..1), text }. */
export function fortschritt(s) {
  const h = s.hoerstelle;
  if (!h || typeof h.anteil !== 'number') return null;
  const anteil = Math.max(0, Math.min(1, h.anteil));
  const text = anteil >= 0.999 ? ZEILE.fertig : fuellen(ZEILE.rest, { dauer: dauerText(h.rest_s ?? 0) });
  return { anteil, text };
}

/* Eine von sechs Platzhalterfarben aus der ID (stabil): 'c1' bis 'c6'. */
export function coverKlasse(id) {
  let h = 2166136261;
  for (const c of String(id ?? '')) { h ^= c.codePointAt(0); h = Math.imul(h, 16777619); }
  return `c${((h >>> 0) % 6) + 1}`;
}

/* Text in { vor, treffer, nach }; `treffer` ist null ohne Fund. Ohne Rücksicht auf Groß/Klein und Umlaute. */
export function teile(text, term) {
  const t = String(text ?? '');
  const n = norm(t);
  const w = norm(term).trim();
  if (!w || n.length !== t.length) return { vor: t, treffer: null, nach: '' };
  const i = n.indexOf(w);
  if (i < 0) return { vor: t, treffer: null, nach: '' };
  return { vor: t.slice(0, i), treffer: t.slice(i, i + w.length), nach: t.slice(i + w.length) };
}

/* Wartet auf `p`; nach `ms` Millisekunden kommt der Fehler { code: 'zeitgrenze' } (Design 6: nach 10 s Fehlerzustand). */
export function ladeMitGrenze(p, ms = 10000) {
  let timer;
  const grenze = new Promise((_, nein) => { timer = setTimeout(() => nein({ code: 'zeitgrenze', message: 'zeitgrenze' }), ms); });
  return Promise.race([p, grenze]).finally(() => clearTimeout(timer));
}

/* ------------------------------------------------------------------ Cover laden (Design 5.2 Leistung, Vertrag 14.3) */

/* Lädt Cover erst, wenn sie sichtbar werden (IntersectionObserver mit 200 px Vorlauf), in 192 px
 * (`?groesse=klein`) mit `hass.fetchWithAuth`, hält sie als `blob:` nach `cover_stand`. Ein Cover ohne Bild (`cover_stand`
 * ist `null`) wird nie angefragt; ist der Stand unbekannt (Antworten von `folgen/list` und `zuordnung/list` tragen keinen),
 * wird es versucht, und ein 404 bleibt der Platzhalter (wird gemerkt). */
export class CoverLader {
  constructor(holeHass) {
    this.holeHass = holeHass;
    this.bilder = new Map(); // `${id}:${stand}` -> Promise<blob-URL oder null>
    this.staende = new Map(); // id -> cover_stand (string oder null)
    this.io = null;
  }

  /* Merkt sich die Stände aus Kurzformen (`serien/list`, `serie/get`). */
  merke(serien) {
    for (const s of serien || []) if (s && s.id && 'cover_stand' in s) this.staende.set(s.id, s.cover_stand);
  }

  stand(id) { return this.staende.has(id) ? this.staende.get(id) : undefined; }

  async blobUrl(id, stand) {
    const key = `${id}:${stand}`;
    if (!this.bilder.has(key)) {
      this.bilder.set(key, (async () => {
        try {
          const hass = this.holeHass();
          if (!hass || typeof hass.fetchWithAuth !== 'function' || typeof URL.createObjectURL !== 'function') return null;
          const pfad = `/api/tobibox/cover/${encodeURIComponent(id)}?groesse=klein${stand && stand !== '?' ? `&v=${encodeURIComponent(stand)}` : ''}`;
          const r = await hass.fetchWithAuth(pfad);
          if (!r || !r.ok) return null;
          return URL.createObjectURL(await r.blob());
        } catch { return null; }
      })());
    }
    return this.bilder.get(key);
  }

  async _setze(el) {
    const key = el._coverKey;
    const url = await this.blobUrl(el.dataset.cover, el.dataset.stand);
    if (url && el._coverKey === key && el.isConnected) {
      el.style.backgroundImage = `url("${url}")`;
      el.dataset.bild = '1';
    }
  }

  /* Geht alle `[data-cover]` unter `wurzel` durch (nach jedem Zeichnen). */
  beobachte(wurzel) {
    if (!wurzel) return;
    if (!this.io && typeof IntersectionObserver === 'function') {
      this.io = new IntersectionObserver((eintraege) => {
        for (const e of eintraege) if (e.isIntersecting) { this.io.unobserve(e.target); this._setze(e.target); }
      }, { rootMargin: '200px' });
    }
    for (const el of wurzel.querySelectorAll('[data-cover]')) {
      const key = `${el.dataset.cover}:${el.dataset.stand}`;
      if (el._coverKey === key) continue;
      el._coverKey = key;
      el.style.backgroundImage = '';
      delete el.dataset.bild;
      if (el.dataset.stand === '' || !el.dataset.cover) continue; // kein Cover vorhanden
      if (this.io) this.io.observe(el); else this._setze(el);
    }
  }

  abmelden() { this.io?.disconnect(); this.io = null; }
}

/* ------------------------------------------------------------------ Symbole */

export const ICON = {
  tag: 'M17.63 5.84C17.27 5.33 16.67 5 16 5L5 5.01C3.9 5.01 3 5.9 3 7v10c0 1.1.9 1.99 2 1.99L16 19c.67 0 1.27-.33 1.63-.84L22 12l-4.37-6.16z',
  search: 'M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z',
  plus: 'M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z',
  chev: 'M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z',
  back: 'M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z',
  check: 'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
  tune: 'M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z',
  more: 'M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z',
  grid: 'M3 3v8h8V3H3zm6 6H5V5h4v4zm-6 4v8h8v-8H3zm6 6H5v-4h4v4zm4-16v8h8V3h-8zm6 6h-4V5h4v4zm-6 4v8h8v-8h-8zm6 6h-4v-4h4v4z',
  list: 'M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z',
  moon: 'M9 2c-1.05 0-2.05.16-3 .46 4.06 1.27 7 5.06 7 9.54 0 4.48-2.94 8.27-7 9.54.95.3 1.95.46 3 .46 5.52 0 10-4.48 10-10S14.52 2 9 2z',
  clock: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z',
  down: 'M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z',
};

export const ic = (n, gr = 24) => html`<svg viewBox="0 0 24 24" width=${gr} height=${gr} aria-hidden="true" focusable="false"><path d=${ICON[n]}></path></svg>`;

/* ------------------------------------------------------------------ Templates */

const anfang = (name) => String(name ?? '').trim().charAt(0).toUpperCase();

export function cover(s, groesse = '') {
  const id = s?.id ?? '';
  const stand = s?.cover_stand === null ? '' : (s?.cover_stand ?? '?'); // '' = kein Bild; '?' = unbekannt, versuchen
  return html`<div class=${`cover ${coverKlasse(id)} ${groesse}`.trim()} data-cover=${id} data-stand=${stand} aria-hidden="true"><span class="bst">${anfang(s?.name) || '?'}</span></div>`;
}

export function coverAktion(groesse = '', symbol = 'moon') {
  return html`<div class=${`cover act ${groesse}`.trim()} aria-hidden="true">${ic(symbol, groesse === 'xs' ? 18 : 24)}</div>`;
}

export function markiert(text, term) {
  const t = teile(text, term);
  return t.treffer === null ? t.vor : html`${t.vor}<mark>${t.treffer}</mark>${t.nach}`;
}

const marke = (s) => (s.pruefen ? html`<span class="badge">${ZEILE.bitte_ansehen}</span>` : nothing);

export function listenZeile(s, { term = '' } = {}) {
  const f = fortschritt(s);
  const tobies = s.anzahl_tobies ?? 0;
  return html`<a class="lrow" href=${`#serie-${s.id}`} data-serie=${s.id}>${cover(s, 'lr')}<span class="grow">
      <span class="lt">${markiert(s.name, term)}</span><span class="ls">${untertitel(s)}</span>
      ${f ? html`<span class="pbar" role="progressbar" aria-label=${ZEILE.fortschritt} aria-valuemin="0" aria-valuemax="100" aria-valuenow=${Math.round(f.anteil * 100)}><i style=${`width:${Math.round(f.anteil * 100)}%`}></i></span><span class="ls">${f.text}</span>` : nothing}
      ${marke(s)}</span>
    ${tobies ? html`<span class="tbadge" role="img" aria-label=${zaehle(ZEILE.tobies, tobies)}>${ic('tag', 16)}${tobies}</span>` : nothing}</a>`;
}

export function kachel(s) {
  return html`<a class="tile" href=${`#serie-${s.id}`} data-serie=${s.id}><span class="pos">${cover(s)}${marke(s)}</span>
    <span class="tn">${s.name}</span><span class="tm">${untertitel(s, { dauer: false })}</span></a>`;
}

export function schnellKachel(s) {
  return html`<a class="qt" href=${`#serie-${s.id}`} data-serie=${s.id}>${cover(s)}<span class="qn">${s.name}</span></a>`;
}

/* Karte im Cover-Raster der Bibliothek (Computer, AB3): Cover, darunter Titel und Untertitel; auf dem Cover das Tobie-Symbol mit
 * der Zahl und, wenn nötig, die Marke „bitte ansehen“. Fortschritt als dünner Balken unter dem Cover. */
export function rasterKachel(s, { term = '' } = {}) {
  const f = fortschritt(s);
  const tobies = s.anzahl_tobies ?? 0;
  return html`<a class="rcard" href=${`#serie-${s.id}`} data-serie=${s.id}><span class="rpos">${cover(s)}${marke(s)}
      ${tobies ? html`<span class="tbadge on" role="img" aria-label=${zaehle(ZEILE.tobies, tobies)}>${ic('tag', 16)}${tobies}</span>` : nothing}</span>
    <span class="rt">${markiert(s.name, term)}</span><span class="rs">${untertitel(s, { dauer: false })}</span>
    ${f ? html`<span class="pbar" role="progressbar" aria-label=${ZEILE.fortschritt} aria-valuemin="0" aria-valuemax="100" aria-valuenow=${Math.round(f.anteil * 100)}><i style=${`width:${Math.round(f.anteil * 100)}%`}></i></span>` : nothing}</a>`;
}

/* Aktion im Seitenkopf: am Handy und im mittleren Bereich ein runder Symbolknopf (48 px), ab 1100 px eine Pille mit Text
 * (das Gerüst schaltet das über `data-layout`). `primaer`: gefüllt (Hauptaktion), sonst tonal. */
export function kopfAktion({ href, label, symbol, primaer = false }) {
  return html`<a class=${`rund kact${primaer ? ' primaer' : ''}`} href=${href} aria-label=${label}>${ic(symbol, 24)}<span class="kt" aria-hidden="true">${label}</span></a>`;
}

/* x = Zeile von `folgen/list`; opts: term, stand (cover_stand der Serie, falls bekannt), aktionen (Template). */
export function folgenZeile(x, { term = '', stand, aktionen = nothing } = {}) {
  const titel = x.anzeige || x.folge;
  return html`<div class="frow"><a class="slink" href=${`#serie-${x.serie_id}`} data-serie=${x.serie_id}>${cover({ id: x.serie_id, name: x.serie_name, cover_stand: stand }, 'sm')}
      <span class="grow"><span class="nm">${markiert(titel, term)}</span><span class="muted">${x.serie_einzeln ? 'Einzeltitel' : x.serie_name}</span></span></a>${aktionen}</div>`;
}

/* Segment-Umschalter: 2 bis 4 gleich breite Wahlmöglichkeiten, `aria-pressed`, Pfeiltasten springen und wählen. */
export function segment({ label, optionen, wert, onWahl, aus = false }) {
  const taste = (e, i) => {
    const hin = { ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1 }[e.key];
    if (!hin) return;
    const j = i + hin;
    if (j < 0 || j >= optionen.length) return;
    e.preventDefault();
    e.currentTarget.parentElement.querySelectorAll('button')[j]?.focus();
    onWahl(optionen[j].wert);
  };
  return html`<div class=${`seg2${optionen.length > 4 ? ' viele' : ''}`} role="group" aria-label=${label}>${optionen.map((o, i) => html`<button type="button" data-wert=${o.wert} aria-label=${o.aria ?? nothing} aria-pressed=${o.wert === wert ? 'true' : 'false'} ?disabled=${aus}
      @click=${() => onWahl(o.wert)} @keydown=${(e) => taste(e, i)}>${o.label}</button>`)}</div>`;
}

/* knopf: { label, href } (Link) oder { label, onKlick } (Knopf). `bild` ist ein Knoten oder Template. */
export function leererZustand({ art, bild, satz, knopf = null }) {
  const k = !knopf ? nothing
    : knopf.href
      ? html`<div class="btns"><a class="btn primary" href=${knopf.href}>${knopf.label}</a></div>`
      : html`<div class="btns"><button type="button" class="btn primary" @click=${knopf.onKlick}>${knopf.label}</button></div>`;
  return html`<div class="leer" data-leer=${art}><span class="bild">${bild}</span><p class="et">${satz}</p>${k}</div>`;
}

/* ------------------------------------------------------------------ Stil */

export const bausteinStil = () => css`
  /* Cover: Platzhalter mit Buchstabe, das Bild kommt später als Hintergrund (data-bild) */
  .cover { aspect-ratio: 1; width: 100%; border-radius: 12px; display: grid; place-items: center; color: var(--on-cover); font-weight: 700; font-size: 44px;
    background-size: cover; background-position: center; background-image: linear-gradient(135deg, var(--shine), transparent 60%); }
  .cover[data-bild] .bst { visibility: hidden; }
  .cover.c1 { background-color: var(--c1); } .cover.c2 { background-color: var(--c2); } .cover.c3 { background-color: var(--c3); }
  .cover.c4 { background-color: var(--c4); } .cover.c5 { background-color: var(--c5); } .cover.c6 { background-color: var(--c6); }
  .cover.act { background-color: var(--primary); color: var(--on-primary); background-image: none; }
  .cover.act svg { fill: currentColor; }
  .cover.xs { width: 32px; font-size: 15px; border-radius: 8px; flex: none; }
  .cover.sm { width: 48px; font-size: 22px; border-radius: 10px; flex: none; }
  .cover.md { width: 64px; font-size: 28px; flex: none; }
  .cover.lr { width: 72px; font-size: 32px; flex: none; }
  .cover.lg { width: 120px; font-size: 52px; flex: none; }

  mark { background: var(--primary-soft); color: var(--text); border-radius: 3px; padding: 0 1px; }
  .badge { display: inline-block; font-size: 13px; font-weight: 500; padding: 2px 10px; border-radius: 12px; background: var(--warn-bg); color: var(--warn); }
  .count { font-size: 14px; color: var(--text2); margin: 4px 0 12px; }
  .rowh { font-size: 17px; font-weight: 500; margin: 16px 0 6px; }

  /* Symbolknöpfe (Lupe 44 px, „+“ 48 px) */
  .iconbtn { min-width: 48px; min-height: 48px; border-radius: 24px; border: 0; background: none; color: var(--text); display: inline-grid; place-items: center; text-decoration: none; flex: none; }
  .iconbtn svg { fill: currentColor; }
  .iconbtn.lupe { min-width: 44px; min-height: 44px; }
  .iconbtn.fillp { background: var(--primary); color: var(--on-primary); border: 1px solid var(--primary-ink); }

  /* Reihen und Kacheln (Start) */
  .hscroll { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 4px; }
  .tile { flex: 0 0 120px; border: 0; background: none; padding: 4px; text-align: left; display: grid; gap: 6px; align-content: start; border-radius: var(--r-card);
    min-width: 0; color: inherit; text-decoration: none; }
  .tile:active { background: var(--primary-soft); }
  .tile .tn { font-weight: 500; font-size: 15px; line-height: 1.25; overflow-wrap: anywhere; }
  .tile .tm { font-size: 13px; color: var(--text2); }
  .tile .pos { position: relative; }
  .tile .pos .badge { position: absolute; left: 6px; bottom: 6px; font-size: 12px; padding: 1px 8px; }
  .qgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0 0 8px; }
  .qt { display: flex; align-items: center; gap: 10px; min-height: 56px; padding: 0 8px 0 0; border: 0; border-radius: 12px; background: var(--card);
    box-shadow: 0 1px 3px var(--shadow); color: var(--text); text-align: left; min-width: 0; overflow: hidden; text-decoration: none; }
  .qt:active { background: var(--primary-soft); }
  .qt .cover { width: 56px; border-radius: 0; flex: none; font-size: 24px; }
  .qt .qn { font-size: 14px; font-weight: 500; line-height: 1.25; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow-wrap: anywhere; min-width: 0; }

  /* Listenzeilen (Bibliothek, Suche) */
  .lrow { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-top: 1px solid var(--divider); text-decoration: none; color: inherit; min-height: 84px;
    content-visibility: auto; contain-intrinsic-size: auto 92px; }
  .lrow:first-child { border-top: 0; }
  .lrow:active, .slink:active { background: var(--primary-soft); }
  .lrow .grow { flex: 1; min-width: 0; display: grid; gap: 1px; }
  .lt { display: block; font-weight: 500; line-height: 1.3; overflow-wrap: anywhere; }
  .ls { display: block; font-size: 14px; color: var(--text2); }
  .pbar { display: block; height: 4px; background: var(--divider); border-radius: 2px; overflow: hidden; margin: 5px 0 1px; width: 100%; }
  .pbar i { display: block; height: 100%; background: var(--primary-ink); }
  .tbadge { display: inline-flex; align-items: center; gap: 3px; font-size: 14px; color: var(--text2); flex: none; }
  .tbadge svg { width: 16px; height: 16px; fill: currentColor; }
  .lrow .badge { justify-self: start; margin-top: 2px; }
  .frow { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-top: 1px solid var(--divider); content-visibility: auto; contain-intrinsic-size: auto 64px; }
  .frow:first-child { border-top: 0; }
  .frow .grow { flex: 1; min-width: 0; overflow-wrap: anywhere; display: grid; }
  .frow .nm { font-weight: 500; }
  .slink { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; min-height: 56px; color: inherit; text-decoration: none; }

  /* Segment-Umschalter (Design 4, X32): Spur ohne Rahmen, gleich breite Segmente, gewählt = gefüllte Pille */
  .seg2 { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: 0; padding: 4px; border: 0; border-radius: 28px; background: var(--primary-soft); width: 100%; max-width: 420px; }
  .seg2 button { min-height: 44px; padding: 0 12px; border: 0; border-radius: 24px; background: transparent; color: var(--text); font-weight: 500; font-size: 14px; line-height: 1.2;
    text-align: center; display: flex; align-items: center; justify-content: center; }
  .seg2 button[aria-pressed="true"] { background: var(--primary); color: var(--on-primary); font-weight: 700; box-shadow: inset 0 0 0 2px var(--primary-ink), 0 1px 3px var(--shadow); }
  .seg2 button:disabled { opacity: 0.5; cursor: default; }
  .seg2 button:focus-visible { outline-offset: 0; border-radius: 24px; }
  .seg2.viele button { padding: 0 2px; }
  .seg2 .einheit { white-space: pre; }
  @media (max-width: 359px) { .seg2.viele .einheit { display: none; } }

  /* Seitenkopf-Aktionen: rund (Handy), Pille mit Text (ab 1100 px) */
  .kact .kt { display: none; }
  .rund.kact.primaer { background: var(--primary); color: var(--on-primary); box-shadow: inset 0 0 0 2px var(--primary-ink); }
  .app[data-layout="seite"] .rund.kact { width: auto; min-height: 44px; height: 44px; padding: 0 18px 0 14px; border-radius: 22px; display: inline-flex; align-items: center; gap: 8px; font-weight: 500; font-size: 15px; }
  .app[data-layout="seite"] .kact .kt { display: inline; }

  /* Karte im Cover-Raster (Computer) */
  .rgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); gap: 28px 20px; margin: 12px 0 0; }
  .rcard { display: grid; gap: 4px; align-content: start; min-width: 0; color: inherit; text-decoration: none; border-radius: 14px; }
  .rcard .rpos { position: relative; display: block; }
  .rcard .cover { border-radius: 14px; font-size: 56px; box-shadow: 0 1px 4px var(--shadow); transition: transform var(--dauer-mittel) var(--kurve), box-shadow var(--dauer-mittel) var(--kurve); }
  .rcard .rt { margin-top: 6px; font-weight: 500; font-size: 15px; line-height: 1.3; overflow-wrap: anywhere; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .rcard .rs { font-size: 13px; color: var(--text2); }
  .rcard .pbar { margin: 4px 0 0; }
  .rcard .rpos .badge { position: absolute; left: 8px; bottom: 8px; font-size: 12px; padding: 1px 8px; box-shadow: 0 1px 3px var(--shadow); }
  .tbadge.on { position: absolute; right: 8px; bottom: 8px; padding: 2px 8px 2px 6px; border-radius: 12px; background: var(--card); color: var(--text); font-size: 13px; font-weight: 500; box-shadow: 0 1px 3px var(--shadow); }
  @media (hover: hover) {
    .rcard:hover .cover { transform: translateY(-3px); box-shadow: 0 10px 22px var(--shadow); }
    .tile:hover .cover { transform: translateY(-2px); box-shadow: 0 8px 18px var(--shadow); }
    .qt:hover { background: var(--primary-soft); }
    .lrow:hover { background: var(--primary-soft); }
  }
  .rcard:active { transform: scale(0.98); }

  /* Reihen (Start, AB5): die letzte Kachel ist angeschnitten, Verlauf an den Rändern, am Computer Pfeile bei Maus-Hover */
  .reihe { margin: 0 0 8px; container-type: inline-size; }
  .reihenkopf { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .reihenkopf .rowh { margin: 16px 0 6px; }
  .alle { display: inline-flex; align-items: center; min-height: 44px; padding: 0 8px; margin: 10px -8px 0 0; font-weight: 500; font-size: 15px; color: var(--primary-ink); text-decoration: none; border-radius: 22px; }
  .alle:hover { background: var(--primary-soft); }
  .reihenfeld { position: relative; --g: 12px; --n: 2; --kw: calc((100cqw - var(--n) * var(--g)) / (var(--n) + 0.45)); }
  @container (min-width: 500px) { .reihenfeld { --n: 3; } }
  @container (min-width: 720px) { .reihenfeld { --n: 4; --g: 16px; } }
  @container (min-width: 1000px) { .reihenfeld { --n: 5; --g: 20px; } }
  @container (min-width: 1240px) { .reihenfeld { --n: 6; } }
  .reihenfeld .hscroll { gap: var(--g); scroll-snap-type: x proximity; scrollbar-width: none; }
  .reihenfeld .hscroll::-webkit-scrollbar { display: none; }
  .reihenfeld .tile { flex: 0 0 var(--kw); scroll-snap-align: start; }
  .reihenfeld::before, .reihenfeld::after { content: ""; position: absolute; top: 0; bottom: 4px; width: 56px; z-index: 2; pointer-events: none; opacity: 0; transition: opacity var(--dauer-mittel) var(--kurve); }
  .reihenfeld::before { left: 0; background: linear-gradient(to right, var(--bg), transparent); }
  .reihenfeld::after { right: 0; background: linear-gradient(to left, var(--bg), transparent); }
  .reihe[data-links] .reihenfeld::before, .reihe[data-rechts] .reihenfeld::after { opacity: 1; }
  .pfeil { display: none; }
  @media (hover: hover) and (pointer: fine) {
    .pfeil { display: inline-grid; position: absolute; top: calc(var(--kw) / 2); transform: translateY(-50%); z-index: 3; width: 48px; height: 48px; border-radius: 24px; border: 0; padding: 0; place-items: center;
      background: var(--card); color: var(--text); box-shadow: 0 2px 10px var(--shadow), 0 0 0 1px var(--divider); opacity: 0; pointer-events: none; transition: opacity var(--dauer-kurz) var(--kurve); }
    .pfeil svg { fill: currentColor; }
    .pfeil.vor { right: 4px; }
    .pfeil.zu { left: 4px; }
    .pfeil.zu svg { transform: scaleX(-1); }
    .reihe:hover .pfeil:not(:disabled), .pfeil:focus-visible { opacity: 1; pointer-events: auto; }
    .pfeil:disabled { display: none; }
    .pfeil:hover { background: var(--primary-soft); color: var(--primary-ink); }
  }

  /* Computer (ab 1100 px Panelbreite): Cover-Kacheln, Schnellzugriff in drei Spalten */
  .app[data-layout="seite"] .hscroll { padding: 4px 0 8px; }
  .app[data-layout="seite"] .tile { gap: 8px; }
  .app[data-layout="seite"] .tile .cover { border-radius: 14px; font-size: 64px; box-shadow: 0 1px 4px var(--shadow); transition: transform var(--dauer-mittel) var(--kurve), box-shadow var(--dauer-mittel) var(--kurve); }
  .app[data-layout="seite"] .tile .tn { font-size: 16px; margin-top: 2px; }
  .app[data-layout="seite"] .tile .tm { font-size: 14px; }
  .app[data-layout="seite"] .tile .pos .badge { left: 8px; bottom: 8px; box-shadow: 0 1px 3px var(--shadow); }
  .app[data-layout="seite"] .qgrid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 12px; }
  .app[data-layout="seite"] .qt { min-height: 72px; gap: 16px; border-radius: 14px; box-shadow: 0 1px 4px var(--shadow); padding-right: 12px; }
  .app[data-layout="seite"] .qt .cover { width: 72px; font-size: 30px; }
  .app[data-layout="seite"] .qt .qn { font-size: 16px; }
  .app[data-layout="seite"] .rowh { font-size: 22px; font-weight: 700; letter-spacing: -0.2px; margin-top: 24px; }
  .app[data-layout="seite"] .lrow { padding: 10px 12px; margin: 0 -12px; }
`;

/* ------------------------------------------------------------------ Großes Cover (A8, Vertrag 14.3: `?groesse=gross`) */

/* Lädt das große Cover der Serienseite (`/api/tobibox/cover/<id>?groesse=gross`) mit `hass.fetchWithAuth` und liefert eine
 * `blob:`-Adresse oder `null` (kein Bild, 404, Fehler). Nutzt den Speicher des CoverLaders (`covers.bilder`), eigener Schlüssel
 * je Stand. `stand` = `cover_stand` der Serie; `null` oder '' heißt: kein Cover, es wird nichts angefragt. */
export function coverGrossUrl(covers, id, stand) {
  if (!covers || !id || !stand) return Promise.resolve(null);
  const key = `${id}:${stand}:gross`;
  if (!covers.bilder.has(key)) {
    covers.bilder.set(key, (async () => {
      try {
        const hass = covers.holeHass();
        if (!hass || typeof hass.fetchWithAuth !== 'function' || typeof URL.createObjectURL !== 'function') return null;
        const r = await hass.fetchWithAuth(`/api/tobibox/cover/${encodeURIComponent(id)}?groesse=gross&v=${encodeURIComponent(stand)}`);
        if (!r || !r.ok) return null;
        return URL.createObjectURL(await r.blob());
      } catch { return null; }
    })());
  }
  return covers.bilder.get(key);
}

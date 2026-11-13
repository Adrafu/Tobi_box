/* Seiten rund um die Tobies (Pakete A9 und A10; Design 5.3, 5.4, 5.7, 5.13, 6.3, 7.1, 7.2, 8, 10.2).
 *
 * Eine Datei, sieben Routen (seiten/index.js trägt sie ein), ein gemeinsames Modell je App (`modell(ctx)`):
 *   #tobies             Regal: „+ Neuer Tobie“, Kacheln (zuletzt zugeordnet zuerst), Suche ab 9 Tobies, wartende Einträge
 *   #tobie-<kennung>    „Was soll … spielen?“: Zielwahl, Zeile „Vorher“ (24 Stunden), Namen ändern, vergessen
 *   #neu                Neuer Tobie: Weg 1 „Leg ihn jetzt auf eine Box“, Weg 2 „Später auflegen“ (optional `?s=<serie>&f=<folge>` = festes Ziel)
 *   #neu-warten         Weg 1: wartet auf ein Ereignis, das NACH dem Start eintrifft (`neue_tobies` neu oder aktualisiert)
 *   #neu-ziel-<kennung> „Neuer Tobie erkannt“: Name, Zielwahl, „Das war ein Versehen“ (`?von=tobies|geraete` bestimmt „‹ …“)
 *   #neu-queue          Weg 2: Box, Name, Ziel, dann die Wartekarte (Warteschlange, Vertrag 3.13)
 *   #geben-<ziel>       „Welcher Tobie soll das spielen?“ (<serie> oder <serie>~<Folge, URL-kodiert>)
 * Dazu die Teile für andere Seiten: Karten auf „Geräte“ (`geraeteKarten`), „Gespielt von“ und Chips auf der Serienseite
 * (`gespieltVonKarte`, `tobieChips`), das Menü „Einem Tobie geben …“ (`gebenLink`). Rechte: alles Alltag (Design 10.2);
 * jeder Aufruf von `zuordnung/set` und `zuordnung/remove` sendet `erwartet_ziel`. Der Lernmodus ist nur in „Technik“ (Administratoren).
 * Schnittstelle zur App: siehe bausteine.js (Seiten-Vertrag).
 */
import { html, nothing, css, repeat, ic, cover, coverAktion, segment, ladeMitGrenze, norm, markiert, untertitel } from '../bausteine.js';
import { TOBIE, TOBIES, GERAETE, VOR, SEITE, SUCHE, ZEILE, fuellen } from '../texte.js';

export const SUCHE_AB = 9; // Suchfeld im Regal ab so vielen Tobies (Design 5.7)
export const VORHER_MS = 24 * 3600 * 1000; // Zeile „Vorher“ bleibt 24 Stunden (Design 5.4)
const PAECKCHEN = 30; // Zielwahl: Listen laden in Päckchen zu 30 (Design 5.4)
const NEU_REIHE = 8; // „Neu hinzugefügt“: die acht neuesten Einträge (Design 5.4)
const ARTEN = ['alle', 'hoerspiel', 'hoerbuch', 'musik', 'geschichte'];

/* ------------------------------------------------------------------ reine Funktionen */

export const tName = (t) => t?.name || TOBIE.ohne_name;
const gleich = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
const kodiere = encodeURIComponent;

/* Name des Ziels aus einer Zuordnung oder Vormerkung (`serie_name`, `folge_anzeige`, bei Aktionen der Name der Aktion). */
export function zielTitel(x) {
  const z = x?.ziel || {};
  if (z.typ === 'aktion') return SUCHE.aktionen[z.aktion] || z.aktion || '';
  if (z.typ === 'folge') return x.folge_anzeige || (x.folge_vorhanden === false ? TOBIES.art.weg : z.folge) || '';
  return x?.serie_name || TOBIES.art.weg;
}

/* „vor 2 Minuten“ (Ortszeit egal, nur die Differenz). Ungültige Zeit: ''. */
export function vorZeit(iso, jetzt = new Date()) {
  const t = Date.parse(iso);
  if (!iso || Number.isNaN(t)) return '';
  const min = Math.floor(Math.max(0, jetzt.getTime() - t) / 60000);
  const f = (paar, n) => fuellen(n === 1 ? paar.eins : paar.mehr, { anzahl: n });
  if (min < 1) return VOR.jetzt;
  if (min < 60) return f(VOR.minuten, min);
  if (min < 24 * 60) return f(VOR.stunden, Math.floor(min / 60));
  return f(VOR.tage, Math.floor(min / (24 * 60)));
}

/* Box, die den neuen Tobie zuletzt gemeldet hat (Eintrag von `neue_tobies/list`). */
export function meldendeBox(eintrag) {
  const liste = Object.entries(eintrag?.boxen || {});
  if (!liste.length) return null;
  return liste.sort((a, b) => String(b[1].zuletzt || '').localeCompare(String(a[1].zuletzt || '')))[0][0];
}

/* Ist die Zeile „Vorher“ noch zu sehen? `vorher` = { ziel, am } oder null; 24 Stunden ab `am`. */
export function vorherAktiv(vorher, jetzt = new Date()) {
  if (!vorher?.ziel) return false;
  const t = Date.parse(vorher.am);
  return Number.isNaN(t) ? true : jetzt.getTime() - t < VORHER_MS;
}

/* Tobies ohne Doppelte (nach Kennung). */
function einmalig(liste) {
  const gesehen = new Set();
  return liste.filter((t) => t && !gesehen.has(t.uid) && gesehen.add(t.uid));
}

/* Alle Tobies, die diese Serie oder eine ihrer Folgen spielen (Antwort von `serie/get`). */
export function tobiesDerSerie(s) {
  return einmalig([...(s?.zuordnungen || []), ...(s?.folgen || []).flatMap((f) => f.tobies || [])]);
}

/* Ziel „Einem Tobie geben …“ aus der Adresse (`geben-<serie>` oder `geben-<serie>~<Folge>`) oder aus `?s=…&f=…`. */
export function zielAusId(id) {
  const roh = String(id ?? '');
  const dekodiere = (t) => { try { return decodeURIComponent(t); } catch { return t; } };
  const i = roh.indexOf('~');
  if (i < 0) return roh ? { typ: 'serie', serie: dekodiere(roh) } : null;
  return { typ: 'folge', serie: dekodiere(roh.slice(0, i)), folge: dekodiere(roh.slice(i + 1)) };
}
export const idAusZiel = (z) => (z.typ === 'folge' ? `${z.serie}~${kodiere(z.folge)}` : z.serie);
export function zielAusAbfrage(q) {
  if (!q?.s) return null;
  return q.f ? { typ: 'folge', serie: q.s, folge: q.f } : { typ: 'serie', serie: q.s };
}
export function abfrageFuerZiel(z) {
  if (!z) return '';
  const p = new URLSearchParams({ s: z.serie, ...(z.typ === 'folge' ? { f: z.folge } : {}) });
  return `?${p.toString()}`;
}

/* Link „Einem Tobie geben …“ für einen Eintrag (Serie) oder eine einzelne Folge. Ein Einzeltitel gibt es nur als Folge (Design 5.4). */
export const gebenLink = (serieId, folge = null) => `#geben-${kodiere(serieId)}${folge === null ? '' : `~${kodiere(folge)}`}`;

/* Neue Tobies (Liste von `neue_tobies/list`), die eine passende Vormerkung hätte nehmen müssen, aber nicht genommen hat
 * (Design 5.13, N20): Die Vormerkung war schon da, als der Tobie gemeldet wurde, und die Uhr der Box stimmt (`zeit_ok`). Liefert die Kennungen. */
export function nichtZugeordnet(neue, vormerkungen) {
  const aus = new Set();
  for (const e of neue || []) {
    const box = meldendeBox(e);
    const m = box ? e.boxen[box] : null;
    if (!m || m.zeit_ok !== true) continue;
    const gemeldet = Date.parse(m.zuletzt);
    if (Number.isNaN(gemeldet)) continue;
    if ((vormerkungen || []).some((v) => (v.box === null || v.box === box) && Date.parse(v.angelegt_am) < gemeldet)) aus.add(e.uid);
  }
  return aus;
}

/* ------------------------------------------------------------------ Modell (je App einmal): Liste der Tobies, Aktionen */

const MODELLE = new WeakMap();
export function modell(ctx) {
  if (!MODELLE.has(ctx)) MODELLE.set(ctx, new TobieModell(ctx));
  return MODELLE.get(ctx);
}

class TobieModell {
  constructor(ctx) {
    this.ctx = ctx;
    this.l = { phase: 'laedt', fehlerCode: null, eintraege: [] }; // Zuordnungen (`zuordnung/list`)
    this.serien = new Map(); // id -> { phase: 'laedt' | 'bereit' | 'fehler', s, fehlerCode }
    this.jetzt = () => new Date(); // Uhr (in Tests ersetzbar)
    this._lauf = 0;
  }

  tobie(uid) { return this.l.eintraege.find((x) => x.uid === uid) ?? null; }

  /* ---- Daten */
  async _holeAlle() {
    const { ctx } = this;
    const alle = [];
    let gesamt = Infinity;
    for (let offset = 0; offset < 1000 && alle.length < gesamt; offset += 100) {
      const r = await ctx.api('tobibox/zuordnung/list', { ...(ctx.faehig('bibliothek') ? { neu: true } : {}), limit: 100, offset });
      alle.push(...(r.zuordnungen || []));
      gesamt = r.gesamt ?? alle.length;
      if (!(r.zuordnungen || []).length) break;
    }
    // zuletzt zugeordnet zuerst (U4); `angelegt_am` fehlt bei alten Einträgen und steht dann hinten
    return alle.map((x, i) => [x, i]).sort((a, b) => (Date.parse(b[0].angelegt_am) || 0) - (Date.parse(a[0].angelegt_am) || 0) || a[1] - b[1]).map((x) => x[0]);
  }

  async laden(still = false) {
    const { ctx } = this;
    const lauf = ++this._lauf;
    if (!still || this.l.phase !== 'bereit') { this.l = { ...this.l, phase: 'laedt', fehlerCode: null }; ctx.neuZeichnen(); }
    try {
      const eintraege = await ladeMitGrenze(this._holeAlle(), ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      for (const x of eintraege) if (x.ziel?.serie && x.cover_stand !== undefined) ctx.covers.merke([{ id: x.ziel.serie, cover_stand: x.cover_stand }]);
      this.l = { phase: 'bereit', fehlerCode: null, eintraege };
    } catch (err) {
      if (lauf !== this._lauf) return;
      this.l = { ...this.l, phase: 'fehler', fehlerCode: err?.code || 'unknown_error' };
    }
    ctx.neuZeichnen();
  }

  /* Eine Serie mit ihren Folgen (`serie/get`), einmal je Serie; Name, Art und Cover für Karten und Zeilen. */
  serie(id) { return this.serien.get(id) ?? null; }

  holeSerie(id, versuch = 1) {
    if (!id || (versuch === 1 && this.serien.has(id))) return;
    const { ctx } = this;
    this.serien.set(id, { phase: 'laedt', s: null });
    ctx.api('tobibox/serie/get', { serie_id: id }).then((s) => {
      ctx.covers.merke([s]);
      this.serien.set(id, { phase: 'bereit', s });
      ctx.neuZeichnen();
    }, (err) => {
      const code = err?.code || 'unknown_error';
      // ein zweiter Versuch bei einem vorübergehenden Fehler (sonst bliebe die Art bis zum nächsten Öffnen falsch)
      if (versuch < 2 && code !== 'serie_nicht_gefunden') { this.holeSerie(id, versuch + 1); return; }
      this.serien.set(id, { phase: 'fehler', s: null, fehlerCode: code });
      ctx.neuZeichnen();
    });
  }

  /* Titel eines Ziels, das nicht aus einer Zuordnung kommt (zum Beispiel das alte Ziel in `vorher`). Leer, solange es lädt oder fehlt. */
  zielTitelAusSerie(z) {
    if (z?.typ === 'aktion') return SUCHE.aktionen[z.aktion] || z.aktion;
    const i = this.serie(z?.serie);
    if (i?.phase !== 'bereit') return '';
    if (z.typ === 'folge') {
      const f = i.s.folgen?.find((x) => x.name === z.folge);
      return f ? (f.anzeige || f.name) : '';
    }
    return i.s.name;
  }

  /* „Spielt jetzt“: Art des Ziels (Design 5.4). */
  zielArt(x) {
    const z = x.ziel || {};
    if (z.typ === 'aktion') return TOBIES.art.aktion;
    const i = this.serie(z.serie);
    if (z.serie && (!i || i.phase === 'laedt')) return ''; // Art noch unbekannt: keine Vermutung zeigen („Ganze Serie“ wäre oft falsch)
    const s = i?.phase === 'bereit' ? i.s : null;
    if (z.typ === 'folge') {
      if (s?.einzeln) return TOBIES.art.einzeltitel;
      const einheit = ZEILE.einzeln_art[s?.art] || ZEILE.einzeln_art.hoerspiel;
      return fuellen(TOBIES.art.folge, { serie: x.serie_name || s?.name || TOBIES.art.serie_ohne, einheit });
    }
    return (s && TOBIES.art.serie[s.art]) || TOBIES.art.serie_ohne;
  }

  coverFuer(x, groesse = 'xs') {
    const z = x.ziel || {};
    if (z.typ === 'aktion') return coverAktion(groesse);
    const stand = x.cover_stand !== undefined ? x.cover_stand : this.ctx.covers.stand(z.serie);
    return cover({ id: z.serie, name: x.serie_name ?? '', cover_stand: stand }, groesse);
  }

  /* ---- Aktionen */
  /* Fehler einer Änderung als Meldung. `zuordnung_geaendert`: Liste neu laden (Text sagt es). Gibt den Code zurück. */
  _fehler(err, { neu = false } = {}) {
    const code = err?.code || 'unknown_error';
    const { ctx } = this;
    if (code === 'zuordnung_geaendert' && neu) ctx.meldeFehler(TOBIES.erkannt.woanders);
    else ctx.meldeFehler(ctx.fehlerText(code));
    if (code === 'zuordnung_geaendert' || code === 'konfig_nicht_bereit') this.laden(true);
    return code;
  }

  /* Ordnet einen Tobie einem Ziel zu (Tap auf ein Ergebnis, ohne Rückfrage, Design 5.4). `alt` = seine bisherige Zuordnung oder null
   * (neuer Tobie). Meldung mit „Rückgängig“ (R17-3): bei Umhängen mit altem und neuem Ziel, bei einem neuen Tobie `zuordnung/remove`
   * mit `als_neu`. Antwort: { ok: true } oder { ok: false, code }. */
  async setze({ uid, ziel, alt = null, name, box = null, text }) {
    const { ctx } = this;
    const felder = { uid, ziel, erwartet_ziel: alt ? alt.ziel : null, ...(name ? { name } : {}) };
    let r;
    try { r = await ctx.api('tobibox/zuordnung/set', felder); } catch (err) { return { ok: false, code: this._fehler(err, { neu: !alt }) }; }
    this.laden(true);
    if (name) ctx.platzEntfernen?.(uid);
    const wer = tName({ name: name || alt?.name });
    if (alt && r.geaendert === false) { ctx.melde(fuellen(TOBIE.zugeordnet_neu, { tobie: wer, ziel: text })); return { ok: true }; }
    if (alt) {
      const vorher = zielTitel(alt);
      ctx.melde(fuellen(TOBIE.zugeordnet_umgehaengt, { tobie: wer, ziel: text, vorher }), { aktion: { text: TOBIE.rueckgaengig, fn: () => this.stelleZurueck({ uid, ziel: alt.ziel, erwartet: ziel, text: vorher, tobie: wer }) } });
    } else {
      ctx.melde(fuellen(TOBIE.zugeordnet_neu, { tobie: wer, ziel: text }), { aktion: { text: TOBIE.rueckgaengig, fn: () => this.nimmNeuZurueck({ uid, erwartet: ziel, box }) } });
    }
    return { ok: true };
  }

  /* „Rückgängig“ und „Zurückstellen“ nach dem Umhängen: das alte Ziel wieder setzen (`erwartet_ziel` schützt vor Überschreiben). */
  async stelleZurueck({ uid, ziel, erwartet, text, tobie, still = false }) {
    const { ctx } = this;
    try { await ctx.api('tobibox/zuordnung/set', { uid, ziel, erwartet_ziel: erwartet }); } catch (err) { this._fehler(err); return false; }
    await this.laden(true);
    if (still) ctx.melde(fuellen(TOBIE.zurueckgestellt, { tobie: tobie ?? TOBIE.ohne_name, ziel: text }));
    else ctx.melde(TOBIE.rueckgaengig_gemacht);
    return true;
  }

  /* „Rückgängig“ bei einem neuen Tobie: er liegt danach wieder als „unbekannt, zuletzt gesehen“ in `neue_tobies` (Vertrag 3.5). */
  async nimmNeuZurueck({ uid, erwartet, box }) {
    const { ctx } = this;
    const felder = { uid, erwartet_ziel: erwartet, ...(box && ctx.faehig('zuordnung_rueckgaengig') ? { als_neu: { box } } : {}) };
    try { await ctx.api('tobibox/zuordnung/remove', felder); } catch (err) { this._fehler(err); return false; }
    await this.laden(true);
    ctx.melde(TOBIE.rueckgaengig_gemacht);
    return true;
  }

  /* „Das war ein Versehen, nicht merken“: Rückfrage, dann `neue_tobies/verwerfen`. `danach` läuft nach dem Verwerfen. */
  frageVerwerfen(uid, ausloeser, danach) {
    const { ctx } = this;
    const T = TOBIES.erkannt;
    ctx.oeffneBlatt({
      titel: T.frage_titel, rolle: 'alertdialog',
      inhalt: html`<p>${T.frage_satz}</p>`,
      knoepfe: [{ label: T.frage_nein }, { label: T.frage_ja, kind: 'primary', fn: async () => {
        try { await ctx.api('tobibox/neue_tobies/verwerfen', { uid }); } catch (err) { ctx.meldeFehler(ctx.fehlerText(err?.code || 'unknown_error')); return false; }
        ctx.melde(T.verworfen);
        danach?.();
        return undefined;
      } }],
    }).then((grund) => { if (grund !== 'ersetzt' && grund !== 'route' && ausloeser?.isConnected) setTimeout(() => ausloeser.focus?.({ preventScroll: true }), 0); });
  }

  /* „Abbrechen“ einer Vormerkung (jeder darf, auch fremde, Design 5.13). */
  async bricheAb(eintrag) {
    const { ctx } = this;
    try { await ctx.api('tobibox/warteschlange/abbrechen', { eintrag_id: eintrag.id }); } catch (err) { ctx.meldeFehler(ctx.fehlerText(err?.code || 'unknown_error')); return false; }
    ctx.warteschlangeNeuLaden?.();
    ctx.melde(TOBIES.wartet.abgebrochen);
    return true;
  }

  /* ---- Texte zur Vormerkung */
  boxText(box) { return box === null || box === undefined ? TOBIES.box_egal : this.ctx.boxAnzeige(box); }
  wartetTitel(e) { return fuellen(TOBIES.wartet.titel, { box: this.boxText(e.box), ziel: zielTitel(e) }); }
}

/* ------------------------------------------------------------------ Zielwahl (Design 5.4): eine Seite für Tobie, Weg 1 und Weg 2 */

class Zielwahl {
  constructor(ctx, onWahl, { neuReihe = false } = {}) {
    this.ctx = ctx;
    this.onWahl = onWahl;
    this.neuReihe = neuReihe;
    this.zuruecksetzen();
  }

  zuruecksetzen() {
    clearTimeout(this._timer);
    this.modus = 'serie';
    this.art = 'alle';
    this.eingabe = '';
    this.term = '';
    this.offen = null;
    this.l = {}; // Liste -> { phase, eintraege, weitere, mehr, fehlerCode }
    this.folgen = new Map(); // serie -> { phase, folgen, fehlerCode }
    this._z = {};
  }

  start() { this.zuruecksetzen(); this.lade(); }

  /* Lädt, was zu Modus, Art und Suchbegriff gehört. Die Reihe „Neu hinzugefügt“ nur einmal. */
  lade() {
    const text = this.term.length >= 2 ? this.term : null;
    const art = this.art === 'alle' ? {} : { art: this.art };
    const basis = { sortierung: 'neu', limit: PAECKCHEN, ...art, ...(text ? { text } : {}) };
    if (this.neuReihe && !this.l.neu) this._hole('neu', { sortierung: 'neu', limit: NEU_REIHE });
    if (this.modus === 'serie') this._hole('serie', { ...basis, filter: ['sammlung'] });
    else if (text) this._hole('treffer', { ...basis, sortierung: 'titel' });
    else { this._hole('serie', { ...basis, filter: ['sammlung'] }); this._hole('einzel', { ...basis, filter: ['einzeln'] }); }
  }

  /* Ohne die Fähigkeit `bibliothek` (altes Backend) gibt es nur die ganze Liste: Filter, Sortierung und Päckchen macht die Seite. */
  async _anfrage(key, felder, offset) {
    const { ctx } = this;
    if (key === 'treffer') return ctx.api('tobibox/folgen/list', { ...felder, offset });
    if (ctx.faehig('bibliothek')) return ctx.api('tobibox/serien/list', { ...felder, offset });
    const r = await ctx.api('tobibox/serien/list', {});
    const f = felder.filter || [];
    let l = (r.serien || []).filter((s) => (!felder.art || (s.art ?? 'hoerspiel') === felder.art)
      && (!f.includes('sammlung') || !s.einzeln) && (!f.includes('einzeln') || s.einzeln) && (!felder.text || norm(s.name).includes(norm(felder.text))));
    l = l.sort((a, b) => (Date.parse(b.angelegt_am) || 0) - (Date.parse(a.angelegt_am) || 0));
    const seite = l.slice(offset, offset + felder.limit);
    return { serien: seite, weitere: offset + seite.length < l.length };
  }

  async _hole(key, felder, offset = 0) {
    const { ctx } = this;
    const mein = (this._z[key] = (this._z[key] || 0) + 1);
    if (offset === 0) this.l[key] = { phase: 'laedt', eintraege: [], weitere: false, mehr: false };
    else this.l[key] = { ...this.l[key], mehr: true };
    ctx.neuZeichnen();
    try {
      const r = await ladeMitGrenze(this._anfrage(key, felder, offset), ctx.grenzeMs);
      if (mein !== this._z[key]) return;
      let neu = key === 'treffer' ? (r.folgen || []) : (r.serien || []).filter((s) => s.typ !== 'ueberraschung');
      if (key !== 'treffer') ctx.covers.merke(r.serien);
      if (offset > 0) {
        const schon = new Set(this.l[key].eintraege.map((x) => x.id ?? `${x.serie_id}/${x.folge}`));
        neu = [...this.l[key].eintraege, ...neu.filter((x) => !schon.has(x.id ?? `${x.serie_id}/${x.folge}`))];
      }
      this.l[key] = { phase: 'bereit', eintraege: neu, weitere: !!r.weitere, mehr: false };
    } catch (err) {
      if (mein !== this._z[key]) return;
      if (offset === 0) this.l[key] = { phase: 'fehler', eintraege: [], weitere: false, mehr: false, fehlerCode: err?.code || 'unknown_error' };
      else { this.l[key] = { ...this.l[key], mehr: false }; ctx.meldeFehler(ctx.fehlerText(err?.code || 'unknown_error')); }
    }
    ctx.neuZeichnen();
  }

  /* ---- Eingaben */
  setzeModus(m) { if (m === this.modus) return; this.modus = m; this.offen = null; this.lade(); }
  setzeArt(a) { if (a === this.art) return; this.art = a; this.lade(); }
  tippe(wert) {
    this.eingabe = wert;
    clearTimeout(this._timer);
    this._timer = setTimeout(() => { this.term = wert.trim(); this.offen = null; this.lade(); }, 250);
    this.ctx.neuZeichnen();
  }
  loescheSuche() { clearTimeout(this._timer); this.eingabe = ''; this.term = ''; this.lade(); this.ctx.neuZeichnen(); }

  /* Auswahl einer Serie, Folge, Aktion. Ein Einzeltitel wird als Folge der eigenen Serie zugeordnet (Design 5.4). */
  waehleSerie(s) {
    if (s.einzeln) return this.waehleEinzeltitel(s);
    return this.onWahl({ typ: 'serie', serie: s.id }, { text: s.name });
  }

  async waehleEinzeltitel(s) {
    const { ctx } = this;
    try {
      const g = await ctx.api('tobibox/serie/get', { serie_id: s.id });
      const f = g.folgen?.[0];
      if (!f) { ctx.meldeFehler(ctx.fehlerText('ziel_ungueltig')); return undefined; }
      return this.onWahl({ typ: 'folge', serie: s.id, folge: f.name }, { text: s.name });
    } catch (err) { ctx.meldeFehler(ctx.fehlerText(err?.code || 'unknown_error')); return undefined; }
  }

  waehleFolge(serieId, f) { return this.onWahl({ typ: 'folge', serie: serieId, folge: f.name }, { text: f.anzeige || f.name }); }
  waehleAktion() { return this.onWahl({ typ: 'aktion', aktion: 'gute_nacht' }, { text: SUCHE.aktionen.gute_nacht }); }

  async klappe(serie) {
    const { ctx } = this;
    if (this.offen === serie.id) { this.offen = null; ctx.neuZeichnen(); return; }
    this.offen = serie.id;
    if (!this.folgen.has(serie.id)) {
      this.folgen.set(serie.id, { phase: 'laedt', folgen: [] });
      ctx.neuZeichnen();
      try {
        const g = await ctx.api('tobibox/serie/get', { serie_id: serie.id });
        this.folgen.set(serie.id, { phase: 'bereit', folgen: g.folgen || [] });
      } catch (err) { this.folgen.set(serie.id, { phase: 'fehler', folgen: [], fehlerCode: err?.code || 'unknown_error' }); }
    }
    ctx.neuZeichnen();
  }

  /* ---- Darstellung */
  _kachel(s) {
    return html`<button type="button" class="tile" data-wahl=${`serie:${s.id}`} aria-label=${fuellen(TOBIES.wahl.waehlen, { name: s.name })} @click=${() => this.waehleSerie(s)}>
      <span class="pos">${cover(s)}</span><span class="tn">${s.name}</span><span class="tm">${untertitel(s, { dauer: false })}</span></button>`;
  }

  _zeile(s, term = '') {
    return html`<button type="button" class="rowbtn" data-wahl=${`serie:${s.id}`} aria-label=${fuellen(TOBIES.wahl.waehlen, { name: s.name })} @click=${() => this.waehleSerie(s)}>${cover(s, 'sm')}
      <span class="grow"><span class="nm">${markiert(s.name, term)}</span><span class="muted">${untertitel(s, { dauer: false })}</span></span><span class="chev" aria-hidden="true">${ic('chev', 24)}</span></button>`;
  }

  _mehr(key, felder) {
    const g = this.l[key];
    if (!g?.weitere) return nothing;
    return html`<div class="btns tb-mehr"><button type="button" class="btn" data-mehr=${key} ?disabled=${g.mehr} @click=${() => this._hole(key, felder(), g.eintraege.length)}>${TOBIES.wahl.mehr}</button></div>`;
  }

  _basis() {
    const text = this.term.length >= 2 ? this.term : null;
    return { sortierung: 'neu', limit: PAECKCHEN, ...(this.art === 'alle' ? {} : { art: this.art }), ...(text ? { text } : {}) };
  }

  _liste(key, inhalt, felder) {
    const g = this.l[key];
    if (!g || g.phase === 'laedt') return html`<p class="muted tb-laedt" role="status">${TOBIES.wahl.laedt}</p>`;
    if (g.phase === 'fehler') return this.ctx.fehlerKarte(g.fehlerCode, () => this._hole(key, felder()));
    return html`${inhalt(g.eintraege)}${this._mehr(key, felder)}`;
  }

  _leer() {
    const T = TOBIES.wahl;
    if (!this.term) return html`<p class="muted tb-leerzeile" data-wahl-leer>${T.leer}</p>`;
    return html`<div class="card muted tb-leerzeile" data-wahl-leer>${fuellen(T.nichts, { suchwort: this.term })}
      <div class="btns"><button type="button" class="btn link" data-suche-loeschen @click=${() => this.loescheSuche()}>${T.suche_loeschen}</button></div></div>`;
  }

  _ergebnis() {
    const T = TOBIES.wahl;
    const term = this.term.length >= 2 ? this.term : '';
    const felder = (extra) => () => ({ ...this._basis(), ...extra });
    if (this.modus === 'serie') {
      return this._liste('serie', (l) => (!l.length ? this._leer()
        : term ? html`<div class="card"><div class="rows" data-ergebnis="serie">${l.map((s) => this._zeile(s, term))}</div></div>`
          : html`<div class="tb-kacheln" data-ergebnis="serie">${l.map((s) => this._kachel(s))}</div>`), felder({ filter: ['sammlung'] }));
    }
    if (term) {
      return this._liste('treffer', (l) => (!l.length ? this._leer() : html`<div class="card"><div class="rows" data-ergebnis="treffer">${l.map((x) => html`
        <button type="button" class="rowbtn" data-wahl=${`folge:${x.serie_id}:${x.folge}`} aria-label=${fuellen(T.waehlen, { name: x.anzeige || x.folge })}
          @click=${() => this.waehleFolge(x.serie_id, { name: x.folge, anzeige: x.anzeige })}>${cover({ id: x.serie_id, name: x.serie_name, cover_stand: x.cover_stand }, 'sm')}
          <span class="grow"><span class="nm">${markiert(x.anzeige || x.folge, term)}</span><span class="muted">${x.serie_einzeln ? T.einzeltitel : x.serie_name}</span></span></button>`)}</div></div>`),
      felder({ sortierung: 'titel' }));
    }
    const serien = this._liste('serie', (l) => (!l.length ? nothing : html`<div class="card"><div class="rows" data-ergebnis="folge">${l.map((s) => this._aufklapp(s))}</div></div>`), felder({ filter: ['sammlung'] }));
    const einzel = this._liste('einzel', (l) => (!l.length ? nothing : html`<h3 class="tb-h3">${T.einzeltitel}</h3><div class="card"><div class="rows" data-ergebnis="einzel">${l.map((s) => this._zeile(s))}</div></div>`), felder({ filter: ['einzeln'] }));
    return html`${serien}${einzel}`;
  }

  _aufklapp(s) {
    const T = TOBIES.wahl;
    const offen = this.offen === s.id;
    const f = this.folgen.get(s.id);
    return html`<div class="tb-auf"><button type="button" class=${`rowbtn${offen ? ' open' : ''}`} data-serie=${s.id} aria-expanded=${offen ? 'true' : 'false'} @click=${() => this.klappe(s)}>${cover(s, 'sm')}
        <span class="grow"><span class="nm">${s.name}</span><span class="muted">${untertitel(s, { dauer: false })}</span></span><span class="chev" aria-hidden="true">${ic('down', 24)}</span></button>
      ${offen ? html`<div class="tb-sub" role="group" aria-label=${fuellen(T.folgen_von, { name: s.name })}>${!f || f.phase === 'laedt' ? html`<p class="muted tb-laedt" role="status">${T.laedt}</p>`
        : f.phase === 'fehler' ? this.ctx.fehlerKarte(f.fehlerCode, () => { this.folgen.delete(s.id); this.offen = null; this.klappe(s); })
          : f.folgen.map((x, i) => html`<button type="button" class="rowbtn" data-wahl=${`folge:${s.id}:${x.name}`} aria-label=${fuellen(T.waehlen, { name: x.anzeige || x.name })} @click=${() => this.waehleFolge(s.id, x)}>
            <span class="muted tb-nr" aria-hidden="true">${x.nummer ?? i + 1}</span><span class="grow"><span class="nm">${x.anzeige || x.name}</span></span></button>`)}</div>` : nothing}</div>`;
  }

  render() {
    const T = TOBIES.wahl;
    const neuReihe = this.neuReihe && !this.term && this.l.neu?.phase === 'bereit' && this.l.neu.eintraege.length
      ? html`<h3 class="tb-h3" data-titel="neu">${T.neu_reihe}</h3><div class="tb-reihe" data-reihe="neu">${this.l.neu.eintraege.map((s) => html`
        <button type="button" class="tile" data-wahl=${`${s.einzeln ? 'einzel' : 'serie'}:${s.id}`} aria-label=${fuellen(T.waehlen, { name: s.name })} @click=${() => this.waehleSerie(s)}>
          <span class="pos">${cover(s)}</span><span class="tn">${s.name}</span><span class="tm">${untertitel(s, { dauer: false })}</span></button>`)}</div>` : nothing;
    return html`<div class="tb-wahl" data-zielwahl>
      ${segment({ label: T.gruppe, optionen: [{ label: T.serie, wert: 'serie' }, { label: T.folge, wert: 'folge' }], wert: this.modus, onWahl: (w) => this.setzeModus(w) })}
      <label class="sr" for="tb-zw-suche">${T.suchen_label}</label>
      <input id="tb-zw-suche" class="tb-suche" type="search" placeholder=${T.suchen_label} autocomplete="off" .value=${this.eingabe}
        @input=${(e) => this.tippe(e.target.value)} @keydown=${(e) => { if (e.key === 'Enter') { e.preventDefault(); clearTimeout(this._timer); this.term = this.eingabe.trim(); this.lade(); } }}>
      <div class="artrow" role="group" aria-label=${T.art_label}>${ARTEN.map((a) => html`<button type="button" class="arttab" data-art=${a} aria-pressed=${this.art === a ? 'true' : 'false'} @click=${() => this.setzeArt(a)}>${T.arten[a]}</button>`)}</div>
      ${neuReihe}
      <div class="tb-ergebnis" aria-live="polite">${this._ergebnis()}</div>
      <button type="button" class="tb-opt" data-wahl="aktion" @click=${() => this.waehleAktion()}>${ic('moon', 24)}<span class="grow"><strong>${T.gute_nacht}</strong><br><span class="muted">${T.gute_nacht_zeile}</span></span></button>
    </div>`;
  }
}

/* ------------------------------------------------------------------ Bausteine */

/* Zeile „Er soll spielen: …“ / „Spielt jetzt“ (Karte mit Cover, Beschriftung, Titel, Art). */
function zielKarte({ bild, label, titel, art, klasse = '' }) {
  return html`<div class=${`tb-cur ${klasse}`.trim()}>${bild}<div class="grow"><span class="lab">${label}</span><span class="lt">${titel}</span>${art ? html`<span class="lab">${art}</span>` : nothing}</div></div>`;
}

/* Name „Wie soll er heißen?“: überspringbar, auf Touch-Geräten kein Autofokus (Design 7.1). */
function namenKarte(wert, onEingabe, id = 'tb-neuname') {
  return html`<div class="tb-karte tb-name" data-karte="name"><h3>${TOBIE.name_frage}</h3><div class="muted">${TOBIE.name_hinweis}</div>
    <div class="tb-namefeld"><label class="sr" for=${id}>${TOBIES.name.label}</label>
      <input id=${id} type="text" maxlength="60" autocomplete="off" placeholder=${TOBIE.name_platzhalter} .value=${wert} @input=${(e) => onEingabe(e.target.value)}></div></div>`;
}

/* Chips „Gespielt von“: Name des Tobies, Tipp öffnet seine Seite (44 px hoch). */
export function tobieChips(tobies) {
  return html`${tobies.map((t) => html`<a class="tb-chip" href=${`#tobie-${kodiere(t.uid)}`} data-chip=${t.uid}>${ic('tag', 20)}${tName(t)}</a>`)}`;
}

/* Karte „Gespielt von“ der Serienseite (Design 5.3): Chips und „+ Tobie“, oder „Noch kein Tobie · Einem Tobie geben …“. */
export function gespieltVonKarte(s) {
  const tobies = tobiesDerSerie(s);
  const einzeln = s.einzeln && s.folgen?.[0];
  const href = gebenLink(s.id, einzeln ? s.folgen[0].name : null);
  if (!tobies.length) {
    return html`<div class="tb-gespielt" data-karte="gespielt-von"><div class="tb-glabel">${TOBIES.gespielt.von_leer}</div>
      <div class="tb-chips"><span class="tb-keiner">${TOBIE.noch_kein_tobie}</span><a class="btn link" href=${href} data-geben>${TOBIE.einem_tobie_geben}</a></div></div>`;
  }
  return html`<div class="tb-gespielt" data-karte="gespielt-von"><div class="tb-glabel">${TOBIES.gespielt.von}</div>
    <div class="tb-chips" role="group" aria-label=${TOBIES.gespielt.tobies}>${tobieChips(tobies)}<a class="tb-chip plus" href=${href} data-plus aria-label=${TOBIE.weiteren_tobie}>${TOBIE.plus_tobie}</a></div></div>`;
}

/* Zeile einer Folge: Chips der Tobies, die genau diese Folge spielen, und „+ Tobie“ (Design 5.3). */
export function folgenChips(serieId, x) {
  const tobies = x.tobies || [];
  if (!tobies.length) return nothing;
  return html`<div class="tb-chips klein" role="group" aria-label=${TOBIES.gespielt.tobies}>${tobieChips(tobies)}<a class="tb-chip plus" href=${gebenLink(serieId, x.name)} data-plus aria-label=${TOBIE.weiteren_tobie}>${TOBIE.plus_tobie}</a></div>`;
}

/* „⋯“ in Folgenzeilen der Suche: ein Blatt mit „Einem Tobie geben …“ (Design 5.3, X20e). */
export function folgenAktion(ctx, x) {
  const titel = x.anzeige || x.folge;
  return html`<button type="button" class="iconbtn se-more" data-menue-folge aria-haspopup="dialog" aria-label=${fuellen('Mehr zu {titel}', { titel })}
    @click=${() => ctx.oeffneBlatt({
    titel,
    inhalt: html`<div class="se-stack"><button type="button" class="btn" data-menue="geben" @click=${() => ctx.navigiere(gebenLink(x.serie_id, x.folge))}>${TOBIE.einem_tobie_geben}</button></div>`,
    knoepfe: [{ label: SEITE.schliessen }],
  })}>${ic('more', 22)}</button>`;
}

/* Rückweg und Zielkarte für ein festes Ziel (`?s=…`), gemeinsam für `#neu`, `#neu-warten`, `#neu-ziel`, `#neu-queue`. */
function festesZielKarte(m, ziel, label) {
  if (!ziel) return nothing;
  m.holeSerie(ziel.serie);
  const i = m.serie(ziel.serie);
  const s = i?.phase === 'bereit' ? i.s : null;
  const f = ziel.typ === 'folge' ? s?.folgen?.find((x) => x.name === ziel.folge) : null;
  const titel = ziel.typ === 'folge' ? (f ? (f.anzeige || f.name) : ziel.folge) : (s?.name ?? '…');
  return zielKarte({ bild: s ? cover(s, 'sm') : html`<div class="cover sm c1" aria-hidden="true"></div>`, label, titel, klasse: 'fest' });
}

/* ------------------------------------------------------------------ Seiten */

/* ---- #tobies: das Regal */
class TobiesSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.m = modell(ctx);
    this.term = '';
    this._aus = null;
  }

  betreten() {
    this.m.laden(this.m.l.phase === 'bereit');
    this._aus?.();
    this._aus = this.ctx.ereignis((ev) => { if (ev.thema === 'konfig' && ev.art === 'geaendert') this.m.laden(true); });
  }

  neuLaden() { this.m.laden(true); }
  verlassen() { this._aus?.(); this._aus = null; }

  _wartend() {
    const { ctx, m } = this;
    const liste = ctx.warteschlange();
    return liste.map((e) => html`<div class="tb-karte tb-wartet" data-eintrag=${e.id}><span class="fig" aria-hidden="true">${ic('clock', 28)}</span>
      <div class="grow"><strong>${m.wartetTitel(e)}</strong><div class="muted">${TOBIES.wartet.zeile}</div></div>
      <button type="button" class="btn" data-abbrechen @click=${() => m.bricheAb(e)}>${TOBIES.wartet.abbrechen}</button></div>`);
  }

  _kachel(x) {
    const { m } = this;
    const name = tName(x);
    const ziel = zielTitel(x);
    const z = x.ziel || {};
    const i = m.serie(z.serie);
    const einzeln = z.typ === 'folge' && (i?.s?.einzeln || norm(x.serie_name) === norm(x.folge_anzeige)); // ein Einzeltitel gehört zu keiner Serie
    const zusatz = z.typ === 'folge' && x.serie_name && !einzeln ? html`<span class="zusatz">${x.serie_name}</span>` : nothing;
    return html`<a class="ttile" href=${`#tobie-${kodiere(x.uid)}`} data-tobie=${x.uid} aria-label=${fuellen(TOBIES.kachel_aria, { tobie: name, ziel })}>
      <span class="fig" aria-hidden="true">${ic('tag', 28)}</span><span class="tn">${name}</span>
      <span class="spielt">${m.coverFuer(x)}<span class="st">${ziel}${zusatz}</span></span></a>`;
  }

  render() {
    const { ctx, m } = this;
    const h2 = html`<h2>${SEITE.reiter.tobies}</h2>`;
    const l = m.l;
    if (l.phase === 'laedt') return html`${h2}${ctx.laedt()}`;
    if (l.phase === 'fehler' && !l.eintraege.length) return html`${h2}${ctx.fehlerKarte(l.fehlerCode, () => m.laden())}`;
    const alle = l.eintraege;
    const keineBox = !Object.keys(ctx.boxen()).length;
    if (!alle.length && keineBox) return html`${h2}${ctx.leer('tobies', 'keineTobies', { href: '#geraete' })}`;
    const leerKarte = !alle.length && !ctx.warteschlange().length ? ctx.leer('tobies', 'keineTobies', { href: '#geraete' }) : nothing; // Design 6.2: Satz und Knopf unter der Kachel
    const term = norm(this.term.trim());
    const treffer = !term ? alle : alle.filter((x) => norm(`${tName(x)} ${zielTitel(x)} ${x.serie_name ?? ''}`).includes(term));
    const suche = alle.length >= SUCHE_AB;
    return html`${h2}${this._wartend()}
      ${suche ? html`<label class="sr" for="tb-suche">${TOBIES.suche.label}</label><input id="tb-suche" class="tb-suche" type="search" placeholder=${TOBIES.suche.platzhalter} autocomplete="off" .value=${this.term}
        @input=${(e) => { this.term = e.target.value; ctx.neuZeichnen(); }}>` : nothing}
      ${term && !treffer.length
    ? html`<div class="leer tb-keiner-leer" data-leer="tobie-suche"><p class="et">${fuellen(TOBIES.suche.keiner, { suchwort: this.term.trim() })}</p>
          <div class="btns"><button type="button" class="btn primary" data-suche-loeschen @click=${() => { this.term = ''; ctx.neuZeichnen(); }}>${TOBIES.suche.loeschen}</button></div></div>`
    : html`<div class="tb-regal" data-regal role="list" aria-label=${TOBIES.regal_label}>
          ${term ? nothing : html`<div role="listitem"><a class="ttile neu" href="#neu" data-neu><span class="fig" aria-hidden="true">${ic('plus', 28)}</span><span class="tn">${TOBIES.neuer}</span></a></div>`}
          ${repeat(treffer, (x) => x.uid, (x) => html`<div role="listitem">${this._kachel(x)}</div>`)}</div>${leerKarte}`}`;
  }
}

/* ---- #tobie-<kennung>: „Was soll … spielen?“ */
class TobieSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.m = modell(ctx);
    this.uid = null;
    this.zw = new Zielwahl(ctx, (ziel, info) => this.waehle(ziel, info));
    this.nameWert = '';
    this.nameFuer = null;
    this.fokusName = false;
    this.busy = false;
    this._aus = null;
  }

  betreten(route) {
    let uid = route?.id ?? null;
    try { uid = decodeURIComponent(uid); } catch { /* roh */ }
    this.uid = uid;
    this.nameFuer = null;
    this.fokusName = route?.abfrage?.name === '1';
    this.busy = false;
    this.m.serien.clear();
    this.m.laden(false);
    this.zw.start();
    this._aus?.();
    this._aus = this.ctx.ereignis((ev) => { if (ev.thema === 'konfig' && ev.art === 'geaendert') this.m.laden(true); });
  }

  neuLaden() { this.m.laden(true); }
  verlassen() { this._aus?.(); this._aus = null; this.zw.zuruecksetzen(); }

  get eintrag() { return this.m.tobie(this.uid); }

  nachRender(wurzel) {
    // Erst fokussieren, wenn die Liste frisch geladen ist: Der erste Zug nach `betreten` zeigt noch die alte Liste, der nächste ersetzt sie
    // und nähme dem Feld den Fokus wieder weg.
    if (this.fokusName && this.m.l.phase === 'bereit') {
      const feld = wurzel.querySelector('#tb-name');
      if (feld) { this.fokusName = false; feld.focus({ preventScroll: true }); feld.scrollIntoView?.({ block: 'center' }); }
    }
  }

  async waehle(ziel, info) {
    const x = this.eintrag;
    if (!x || this.busy) return;
    this.busy = true;
    this.ctx.neuZeichnen();
    const r = await this.m.setze({ uid: x.uid, ziel, alt: x, text: info.text });
    this.busy = false;
    if (r.ok) this.ctx.navigiere('#tobies');
    else this.ctx.neuZeichnen();
  }

  async speichereName() {
    const x = this.eintrag;
    const { ctx } = this;
    const v = this.nameWert.trim();
    if (!x || this.busy) return;
    if (!v) { ctx.meldeFehler(TOBIES.name.leer); return; }
    this.busy = true;
    try {
      await ctx.api('tobibox/zuordnung/set', { uid: x.uid, ziel: x.ziel, name: v, erwartet_ziel: x.ziel });
      ctx.platzEntfernen?.(x.uid);
      ctx.melde(TOBIES.name.gespeichert);
    } catch (err) {
      const code = err?.code || 'unknown_error';
      ctx.meldeFehler(ctx.fehlerText(code));
      if (code === 'zuordnung_geaendert') this.nameFuer = null;
    }
    this.busy = false;
    await this.m.laden(true);
  }

  stelleZurueck(x) {
    const v = x.vorher;
    const text = this.m.zielTitelAusSerie(v.ziel);
    return this.m.stelleZurueck({ uid: x.uid, ziel: v.ziel, erwartet: x.ziel, text, tobie: tName(x), still: true });
  }

  frageVergessen(ausloeser) {
    const x = this.eintrag;
    const { ctx } = this;
    if (!x) return;
    const T = TOBIES.vergessen;
    ctx.oeffneBlatt({
      titel: T.titel, rolle: 'alertdialog',
      inhalt: html`<p>${fuellen(T.satz, { tobie: tName(x) })}</p>`,
      knoepfe: [{ label: T.nein }, { label: T.ja, kind: 'danger solid', fn: async () => {
        try { await ctx.api('tobibox/zuordnung/remove', { uid: x.uid, erwartet_ziel: x.ziel }); } catch (err) {
          const code = this.m._fehler(err);
          return code === 'zuordnung_geaendert' ? undefined : false;
        }
        ctx.melde(T.fertig);
        this.m.laden(true);
        ctx.navigiere('#tobies');
        return undefined;
      } }],
    }).then((grund) => { if (grund !== 'ersetzt' && grund !== 'route' && ausloeser?.isConnected) setTimeout(() => ausloeser.focus?.({ preventScroll: true }), 0); });
  }

  render() {
    const { ctx, m } = this;
    const zurueck = html`<a class="back" href="#tobies" data-zurueck>${SEITE.zurueck.tobies}</a>`;
    const l = m.l;
    if (l.phase === 'laedt') return html`${zurueck}${ctx.laedt()}`;
    if (l.phase === 'fehler' && !l.eintraege.length) return html`${zurueck}${ctx.fehlerKarte(l.fehlerCode, () => m.laden())}`;
    const x = this.eintrag;
    if (!x) {
      return html`${zurueck}<div class="note warn" role="alert" data-zustand="weg">${TOBIES.seite.weg.satz} <a class="nl" href="#tobies">${TOBIES.seite.weg.link}</a></div>`;
    }
    if (this.nameFuer !== x.uid) { this.nameFuer = x.uid; this.nameWert = x.name ?? ''; }
    const z = x.ziel || {};
    m.holeSerie(z.serie);
    if (x.vorher?.ziel?.serie) m.holeSerie(x.vorher.ziel.serie);
    const vorherText = vorherAktiv(x.vorher, m.jetzt()) ? m.zielTitelAusSerie(x.vorher.ziel) : '';
    const name = x.name || TOBIES.seite.dieser;
    return html`${zurueck}
      <h2 class="tb-titel" tabindex="-1">${fuellen(TOBIES.seite.frage, { tobie: name })}</h2>
      ${vorherText ? html`<div class="tb-vorher" data-vorher><span>${fuellen(TOBIE.vorher, { vorher: vorherText })}</span><span class="punkt" aria-hidden="true">·</span>
        <button type="button" class="btn link" data-zurueckstellen ?disabled=${this.busy} @click=${() => this.stelleZurueck(x)}>${TOBIE.zurueckstellen}</button></div>` : nothing}
      ${zielKarte({ bild: m.coverFuer(x, 'sm'), label: TOBIES.seite.spielt_jetzt, titel: zielTitel(x), art: m.zielArt(x), klasse: 'jetzt' })}
      <div class=${this.busy ? 'tb-busy' : ''} ?inert=${this.busy}>${this.zw.render()}</div>
      <div class="tb-manage" data-abschnitt="verwalten"><h3>${TOBIES.name.titel}</h3>
        <form class="tb-namefeld" @submit=${(e) => { e.preventDefault(); this.speichereName(); }}><label class="sr" for="tb-name">${TOBIES.name.label}</label>
          <input id="tb-name" type="text" maxlength="60" autocomplete="off" placeholder=${TOBIE.name_platzhalter} .value=${this.nameWert} @input=${(e) => { this.nameWert = e.target.value; }}>
          <button type="submit" class="btn" data-name-speichern ?disabled=${this.busy}>${TOBIES.name.speichern}</button></form>
        <button type="button" class="btn link danger" data-vergessen @click=${(e) => this.frageVergessen(e.currentTarget)}>${TOBIES.vergessen.knopf}</button></div>`;
  }
}

/* Gemeinsam für die Seiten von „Neuer Tobie“: festes Ziel aus `?s=…` und Rückweg. */
function neuKontext(m, route) {
  const q = route?.abfrage || {};
  const fest = zielAusAbfrage(q);
  const abfrage = abfrageFuerZiel(fest);
  const zurueck = fest ? `#serie-${kodiere(fest.serie)}` : '#tobies';
  let label = SEITE.zurueck.tobies;
  if (fest) {
    const i = m.serie(fest.serie);
    label = `‹ ${i?.phase === 'bereit' ? i.s.name : SEITE.zurueck.bibliothek.replace('‹ ', '')}`;
  }
  return { fest, abfrage, zurueck, label, q };
}

/* ---- #neu: zwei Wege */
class NeuSeite {
  constructor(ctx) { this.ctx = ctx; this.m = modell(ctx); }

  betreten() { this.m.serien.clear(); }

  render(route) {
    const { ctx, m } = this;
    const k = neuKontext(m, route);
    if (k.fest) m.holeSerie(k.fest.serie);
    const T = TOBIES.neu;
    const zeile = (href, symbol, w, id, an = true) => html`<a class=${`tb-weg${an ? '' : ' aus'}`} href=${an ? href : nothing} data-weg=${id} aria-disabled=${an ? nothing : 'true'}><span class="wc-i">${ic(symbol, 26)}</span>
      <span class="grow"><span class="wc-t">${w.titel}</span><span class="muted">${w.zeile}</span></span><span class="chev" aria-hidden="true">${ic('chev', 24)}</span></a>`;
    return html`<a class="back" href=${k.zurueck} data-zurueck>${k.label}</a>
      <h2 class="tb-titel" tabindex="-1">${SEITE.seiten.neu}</h2>
      ${festesZielKarte(m, k.fest, T.er_soll)}
      ${!Object.keys(ctx.boxen()).length ? html`<div class="note warn" role="status" data-zustand="keine-box">${fuellen(T.ohne_box)}</div>` : nothing}
      ${ctx.faehig('neue_tobies') ? zeile(`#neu-warten${k.abfrage}`, 'tag', T.weg1, 'jetzt') : nothing}
      ${ctx.faehig('warteschlange') ? zeile(`#neu-queue${k.abfrage}`, 'clock', T.weg2, 'spaeter') : nothing}`;
  }
}

/* ---- #neu-warten: Weg 1, Schritt 1 */
class NeuWartenSeite {
  constructor(ctx) { this.ctx = ctx; this.m = modell(ctx); this._aus = null; this.route = null; }

  betreten(route) {
    this.route = route;
    this._aus?.();
    // Nur Ereignisse, die NACH dem Start eintreffen: die Liste beim Start (und was schon wartet) zählt nicht (Design 7.1, N12)
    this._aus = this.ctx.ereignis((ev) => {
      if (ev.thema !== 'neue_tobies' || !['neu', 'aktualisiert'].includes(ev.art)) return;
      const uid = ev.daten?.eintrag?.uid;
      if (!uid) return;
      const k = neuKontext(this.m, this.route);
      this.ctx.navigiere(`#neu-ziel-${kodiere(uid)}${k.abfrage ? `${k.abfrage}&` : '?'}von=tobies`, { ersetzen: true });
    });
  }

  verlassen() { this._aus?.(); this._aus = null; }

  render(route) {
    this.route = route ?? this.route;
    const { ctx, m } = this;
    const k = neuKontext(m, route);
    const namen = Object.keys(ctx.boxen()).map((b) => ctx.boxAnzeige(b));
    const T = TOBIES.warten;
    const titel = namen.length === 1 ? fuellen(T.eine, { box: namen[0] }) : namen.length === 2 ? fuellen(T.zwei, { box: namen[0], box_zwei: namen[1] }) : T.viele;
    return html`<a class="back" href=${`#neu${k.abfrage}`} data-zurueck>${SEITE.zurueck.tobies}</a>
      <div class="tb-warte" data-zustand="warten"><div class="ring" aria-hidden="true">${ic('tag', 48)}</div>
        <h2 class="tb-titel" tabindex="-1">${titel}</h2><div class="muted">${T.satz}</div>
        <div class="btns"><a class="btn" href=${`#neu${k.abfrage}`} data-abbrechen>${T.abbrechen}</a></div></div>`;
  }
}

/* ---- #neu-ziel-<kennung>: „Neuer Tobie erkannt“ */
class NeuZielSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.m = modell(ctx);
    this.uid = null;
    this.route = null;
    this.name = '';
    this.busy = false;
    this.zw = new Zielwahl(ctx, (ziel, info) => this.waehle(ziel, info), { neuReihe: true });
  }

  betreten(route) {
    let uid = route?.id ?? null;
    try { uid = decodeURIComponent(uid); } catch { /* roh */ }
    this.uid = uid;
    this.route = route;
    this.name = '';
    this.busy = false;
    this.m.serien.clear();
    this.zw.start();
  }

  verlassen() { this.zw.zuruecksetzen(); }

  get eintrag() { return this.ctx.neue().find((e) => e.uid === this.uid) ?? null; }

  async waehle(ziel, info) {
    const e = this.eintrag;
    if (!e || this.busy) return;
    const k = neuKontext(this.m, this.route);
    this.busy = true;
    this.ctx.neuZeichnen();
    const r = await this.m.setze({ uid: e.uid, ziel, alt: null, name: this.name.trim() || undefined, box: meldendeBox(e), text: info.text });
    this.busy = false;
    if (r.ok) this.ctx.navigiere(k.fest ? k.zurueck : '#tobies');
    else if (r.code === 'zuordnung_geaendert') this.ctx.navigiere('#tobies');
    else this.ctx.neuZeichnen();
  }

  render(route) {
    this.route = route ?? this.route;
    const { ctx, m } = this;
    const k = neuKontext(m, this.route);
    if (k.fest) m.holeSerie(k.fest.serie);
    const vonTobies = k.q.von === 'tobies';
    const zurueck = html`<a class="back" href=${vonTobies ? '#tobies' : '#geraete'} data-zurueck>${vonTobies ? SEITE.zurueck.tobies : SEITE.zurueck.geraete}</a>`;
    const e = this.eintrag;
    if (!e) {
      return html`<div class="tb-leiste">${zurueck}</div><h2 class="tb-titel" tabindex="-1">${SEITE.seiten.neu_ziel}</h2>
        <div class="note warn" role="status" data-zustand="weg">${TOBIES.erkannt.weg}<div class="btns"><a class="btn" href="#tobies">${TOBIES.erkannt.zu_den_tobies}</a></div></div>`;
    }
    const box = meldendeBox(e);
    const T = TOBIES.erkannt;
    return html`<div class="tb-leiste">${zurueck}
        <button type="button" class="btn link tb-versehen" data-versehen @click=${(ev) => m.frageVerwerfen(e.uid, ev.currentTarget, () => ctx.navigiere(vonTobies ? '#tobies' : '#geraete'))}>${T.versehen}</button></div>
      <h2 class="sr" tabindex="-1">${SEITE.seiten.neu_ziel}</h2>
      <div class="note ok" role="status" data-karte="erkannt"><strong>${T.titel}</strong> ${box ? fuellen(T.auf, { box: ctx.boxAnzeige(box) }) : ''}</div>
      ${namenKarte(this.name, (v) => { this.name = v; })}
      ${k.fest
    ? html`${festesZielKarte(m, k.fest, TOBIES.neu.er_spielt)}<div class="btns"><button type="button" class="btn primary" data-fertig ?disabled=${this.busy}
          @click=${() => this.waehle(k.fest, { text: m.zielTitelAusSerie(k.fest) || '…' })}>${TOBIES.neu.fertig}</button></div>`
    : html`<h3 class="tb-h3 gross">${TOBIES.wahl.frage}</h3><div class=${this.busy ? 'tb-busy' : ''} ?inert=${this.busy}>${this.zw.render()}</div>`}`;
  }
}

/* ---- #neu-queue: Weg 2 „Später auflegen“ */
class NeuQueueSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.m = modell(ctx);
    this.route = null;
    this.box = 'egal';
    this.name = '';
    this.queued = null;
    this.busy = false;
    this._aus = null;
    this.zw = new Zielwahl(ctx, (ziel, info) => this.vormerken(ziel, info), { neuReihe: true });
  }

  betreten(route) {
    this.route = route;
    this.box = 'egal';
    this.name = '';
    this.queued = null;
    this.busy = false;
    this.m.serien.clear();
    this.zw.start();
    this._aus?.();
    this._aus = this.ctx.ereignis((ev) => {
      if (ev.thema !== 'warteschlange' || !this.queued || ev.daten?.id !== this.queued) return;
      if (ev.art === 'abgearbeitet') { this.queued = null; this.ctx.navigiere('#tobies'); } // „geht sie zum Regal“ (Design 5.13)
      else if (ev.art === 'abgebrochen') { this.queued = null; this.ctx.neuZeichnen(); }
    });
  }

  verlassen() { this._aus?.(); this._aus = null; this.zw.zuruecksetzen(); }

  async vormerken(ziel, info) {
    const { ctx } = this;
    if (this.busy) return;
    this.busy = true;
    ctx.neuZeichnen();
    const felder = { box: this.box === 'egal' ? null : this.box, ziel, ...(this.name.trim() ? { name: this.name.trim() } : {}) };
    try {
      const r = await ctx.api('tobibox/warteschlange/set', felder);
      this.queued = r.eintrag?.id ?? null;
      ctx.warteschlangeNeuLaden?.();
      this.text = info.text;
    } catch (err) { this.m._fehler(err); }
    this.busy = false;
    ctx.neuZeichnen();
  }

  async abbrechen(e) {
    if (await this.m.bricheAb(e)) { this.queued = null; this.ctx.navigiere('#tobies'); }
  }

  render(route) {
    this.route = route ?? this.route;
    const { ctx, m } = this;
    const k = neuKontext(m, this.route);
    const T = TOBIES.queue;
    const zurueck = html`<a class="back" href=${`#neu${k.abfrage}`} data-zurueck>${SEITE.zurueck.tobies}</a>`;
    const e = this.queued ? ctx.warteschlange().find((x) => x.id === this.queued) : null;
    if (e) {
      return html`${zurueck}<div class="tb-warte" data-zustand="wartet"><div class="ring" aria-hidden="true">${ic('clock', 48)}</div>
        <h2 class="tb-titel" tabindex="-1">${fuellen(T.warte_titel, { box: m.boxText(e.box), ziel: zielTitel(e) })}</h2><div class="muted">${T.warte_satz}</div>
        <div class="btns"><button type="button" class="btn" data-abbrechen @click=${() => this.abbrechen(e)}>${T.abbrechen}</button>
          <a class="btn primary" href=${k.zurueck} data-fertig>${T.fertig}</a></div></div>`;
    }
    if (k.fest) m.holeSerie(k.fest.serie);
    const boxen = Object.keys(ctx.boxen());
    const optionen = [...boxen.map((b) => ({ label: ctx.boxAnzeige(b), wert: b })), { label: T.egal, wert: 'egal' }];
    return html`${zurueck}<h2 class="tb-titel" tabindex="-1">${TOBIES.neu.weg2.titel}</h2>
      <div class="tb-boxwahl" data-karte="box"><div class="tb-glabel">${T.box_frage}</div>
        ${segment({ label: T.box_label, optionen, wert: this.box, onWahl: (w) => { this.box = w; ctx.neuZeichnen(); } })}</div>
      ${namenKarte(this.name, (v) => { this.name = v; }, 'tb-queue-name')}
      ${k.fest
    ? html`${festesZielKarte(m, k.fest, TOBIES.neu.er_soll)}<div class="btns"><button type="button" class="btn primary" data-vormerken ?disabled=${this.busy}
          @click=${() => this.vormerken(k.fest, { text: m.zielTitelAusSerie(k.fest) || '…' })}>${TOBIES.neu.vormerken}</button></div>`
    : html`<h3 class="tb-h3 gross">${TOBIES.wahl.frage}</h3><div class=${this.busy ? 'tb-busy' : ''} ?inert=${this.busy}>${this.zw.render()}</div>`}`;
  }
}

/* ---- #geben-<ziel>: „Welcher Tobie soll das spielen?“ */
class GebenSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.m = modell(ctx);
    this.ziel = null;
    this.busy = false;
  }

  betreten(route) {
    this.ziel = zielAusId(route?.id);
    this.busy = false;
    this.m.serien.clear();
    if (this.ziel) this.m.holeSerie(this.ziel.serie);
    this.m.laden(this.m.l.phase === 'bereit');
  }

  neuLaden() { this.m.laden(true); }

  async waehle(x, text) {
    if (this.busy || !this.ziel) return;
    this.busy = true;
    this.ctx.neuZeichnen();
    const r = await this.m.setze({ uid: x.uid, ziel: this.ziel, alt: x, text });
    this.busy = false;
    if (r.ok) this.ctx.navigiere(`#serie-${kodiere(this.ziel.serie)}`);
    else this.ctx.neuZeichnen();
  }

  render(route) {
    const { ctx, m } = this;
    const ziel = this.ziel ?? zielAusId(route?.id);
    if (!ziel) return html`<a class="back" href="#bibliothek">${SEITE.zurueck.bibliothek}</a>${ctx.laedt()}`;
    const i = m.serie(ziel.serie);
    if (i?.phase === 'fehler') {
      return html`<a class="back" href="#bibliothek">${SEITE.zurueck.bibliothek}</a><div class="note err" role="alert" data-zustand="weg">${TOBIES.geben.ziel_weg} <a class="nl" href="#bibliothek">${SEITE.zurueck.bibliothek.replace('‹ ', '')}</a></div>`;
    }
    const s = i?.phase === 'bereit' ? i.s : null;
    const f = ziel.typ === 'folge' ? s?.folgen?.find((x) => x.name === ziel.folge) : null;
    const titel = ziel.typ === 'folge' ? (f ? (f.anzeige || f.name) : ziel.folge) : (s?.name ?? '…');
    const l = m.l;
    const text = titel;
    return html`<a class="back" href=${`#serie-${kodiere(ziel.serie)}`} data-zurueck>${s ? `‹ ${s.name}` : SEITE.zurueck.bibliothek}</a>
      <h2 class="tb-titel" tabindex="-1">${SEITE.seiten.geben}</h2>
      ${zielKarte({ bild: s ? cover(s, 'sm') : html`<div class="cover sm c1" aria-hidden="true"></div>`, label: s ? (s.einzeln ? TOBIES.art.einzeltitel : ziel.typ === 'folge' ? fuellen(TOBIES.art.folge, { serie: s.name, einheit: ZEILE.einzeln_art[s.art] || ZEILE.einzeln_art.hoerspiel }) : (TOBIES.art.serie[s.art] || TOBIES.art.serie_ohne)) : '', titel, klasse: 'fest' })}
      ${l.phase === 'laedt' ? ctx.laedt() : html`<div class="tb-regal" data-regal role="list" aria-label=${TOBIES.regal_label}>
        <div role="listitem"><a class="ttile neu" href=${`#neu${abfrageFuerZiel(ziel)}`} data-neu><span class="fig" aria-hidden="true">${ic('plus', 28)}</span><span class="tn">${TOBIES.neuer}</span></a></div>
        ${repeat(l.eintraege, (x) => x.uid, (x) => html`<div role="listitem"><button type="button" class="ttile" data-tobie=${x.uid} ?disabled=${this.busy}
          aria-label=${fuellen(TOBIES.kachel_aria, { tobie: tName(x), ziel: zielTitel(x) })} @click=${() => this.waehle(x, text)}>
          <span class="fig" aria-hidden="true">${ic('tag', 28)}</span><span class="tn">${tName(x)}</span><span class="spielt">${m.coverFuer(x)}<span class="st">${zielTitel(x)}</span></span></button></div>`)}</div>`}`;
  }
}

/* ------------------------------------------------------------------ Karten auf „Geräte“ (Design 5.13, 7.1) */

/* Gibt die Karten für den Platz `[data-platz="neue-tobies"]` zurück. */
export function geraeteKarten(ctx) {
  const m = modell(ctx);
  const neue = ctx.neue();
  const queue = ctx.warteschlange();
  const jetzt = m.jetzt();
  const nz = nichtZugeordnet(neue, queue);
  const karten = [];
  const grund = ctx.gesperrt() ? GERAETE.grund_gesperrt : GERAETE.grund_sonst;
  for (const e of neue.filter((x) => nz.has(x.uid))) {
    const box = meldendeBox(e);
    karten.push(html`<div class="tb-karte warn" role="group" data-karte="nicht-zugeordnet" data-uid=${e.uid}><h3>${GERAETE.nicht_zugeordnet.titel}</h3>
      <div class="muted">${grund}</div><div class="btns"><a class="btn" href=${`#neu-ziel-${kodiere(e.uid)}`} data-jetzt-zuordnen>${GERAETE.nicht_zugeordnet.jetzt_zuordnen}</a>
        <button type="button" class="btn link" data-versehen @click=${(ev) => m.frageVerwerfen(e.uid, ev.currentTarget)}>${GERAETE.versehen}</button></div>
      <span class="sr">${box ? ctx.boxAnzeige(box) : ''}</span></div>`);
  }
  // Neue Tobies je Box: einer = ganze Karte ist ein Link; mehrere = Karte mit Zeilen (N12)
  const rest = neue.filter((x) => !nz.has(x.uid));
  const jeBox = new Map();
  for (const e of rest) {
    const b = meldendeBox(e) ?? '';
    if (!jeBox.has(b)) jeBox.set(b, []);
    jeBox.get(b).push(e);
  }
  // `mitUhr`: in der Karte mit mehreren Tobies steht die Uhrzeit dabei, sonst sähen die Zeilen gleich aus (Abnahme A-1b)
  const zeitText = (e, mitUhr = false) => {
    const b = meldendeBox(e);
    const mm = b ? e.boxen[b] : null;
    const iso = mm ? mm.zuletzt || e.zuletzt : null;
    const z = mm && mm.zeit_ok !== false ? vorZeit(iso, jetzt) : '';
    if (!z) return GERAETE.neuer_tobie.zeile_ohne;
    if (mitUhr) {
      const d = new Date(iso);
      const uhr = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
      return fuellen(GERAETE.neuer_tobie.zeile_uhr, { uhr, zeit: z });
    }
    return fuellen(GERAETE.neuer_tobie.zeile, { zeit: z });
  };
  for (const [b, liste] of jeBox) {
    const boxName = b ? ctx.boxAnzeige(b) : undefined;
    if (liste.length === 1) {
      const e = liste[0];
      karten.push(html`<div class="tb-karte warn tb-neu-karte" data-karte="neuer-tobie" data-uid=${e.uid}>
        <a class="tb-karte-link" href=${`#neu-ziel-${kodiere(e.uid)}`}><strong>${fuellen(GERAETE.neuer_tobie.titel, { box: boxName })}</strong><span class="zeit">${zeitText(e)}</span></a>
        <button type="button" class="btn link" data-versehen @click=${(ev) => m.frageVerwerfen(e.uid, ev.currentTarget)}>${GERAETE.versehen}</button></div>`);
    } else {
      karten.push(html`<div class="tb-karte warn" role="group" data-karte="neue-tobies" data-box=${b}><h3>${fuellen(GERAETE.neue_tobies.titel, { anzahl: liste.length, box: boxName })}</h3>
        ${liste.map((e) => html`<div class="tb-zeile" data-uid=${e.uid}><a class="tb-zeilenlink" href=${`#neu-ziel-${kodiere(e.uid)}`} aria-label=${`${GERAETE.neue_zeile}: ${zeitText(e, true)}`}><span class="grow">${zeitText(e, true)}</span><span class="chev" aria-hidden="true">${ic('chev', 24)}</span></a>
          <button type="button" class="btn link" data-versehen @click=${(ev) => m.frageVerwerfen(e.uid, ev.currentTarget)}>${GERAETE.versehen}</button></div>`)}</div>`);
    }
  }
  // „Ein neuer Tobie hat einen Platz bekommen. Name geben?“ bleibt, bis er einen Namen hat oder „Später“ gewählt ist (N11)
  for (const p of ctx.platz()) {
    karten.push(html`<div class="tb-karte" role="group" data-karte="platz-bekommen" data-uid=${p.uid}><h3>${GERAETE.platz_bekommen.titel}</h3><div class="muted">${GERAETE.platz_bekommen.frage}</div>
      <div class="btns"><a class="btn primary" href=${`#tobie-${kodiere(p.uid)}?name=1`} data-name-geben>${GERAETE.platz_bekommen.name_geben}</a>
        <button type="button" class="btn" data-spaeter @click=${() => ctx.platzEntfernen(p.uid)}>${GERAETE.platz_bekommen.spaeter}</button></div></div>`);
  }
  // Wartet auf einen neuen Tobie: Zeilen, Tipp öffnet ein Blatt mit „Nicht mehr warten“
  if (queue.length) {
    karten.push(html`<div class="tb-karte" role="group" data-karte="wartet"><h3>${GERAETE.wartet.titel}</h3>
      ${queue.map((e, i) => html`<button type="button" class="rowbtn tb-wzeile" data-eintrag=${e.id} aria-haspopup="dialog" @click=${(ev) => zeigeEintrag(ctx, m, e, ev.currentTarget)}>
        <span class="grow"><span class="nm">${fuellen(GERAETE.wartet.zeile1, { box: m.boxText(e.box) })}</span>
          <span class="muted">${fuellen(GERAETE.wartet.zeile2, { serie: zielTitel(e), nr: e.position ?? i + 1, gesamt: queue.length })}</span></span>
        <span class="chev" aria-hidden="true">${ic('chev', 24)}</span></button>`)}</div>`);
  }
  return html`${karten}`;
}

function zeigeEintrag(ctx, m, e, ausloeser) {
  const queue = ctx.warteschlange();
  ctx.oeffneBlatt({
    titel: fuellen(GERAETE.wartet.zeile1, { box: m.boxText(e.box) }),
    inhalt: html`<p>${fuellen(GERAETE.wartet.zeile2, { serie: zielTitel(e), nr: e.position ?? queue.indexOf(e) + 1, gesamt: queue.length })}</p>`,
    knoepfe: [{ label: GERAETE.wartet_blatt.schliessen }, { label: GERAETE.wartet.abbrechen, kind: 'danger solid', fn: async () => ((await m.bricheAb(e)) ? undefined : false) }],
  }).then((grund) => { if (grund !== 'ersetzt' && grund !== 'route' && ausloeser?.isConnected) setTimeout(() => ausloeser.focus?.({ preventScroll: true }), 0); });
}

/* Beim Öffnen von „Geräte“: Karten „Platz bekommen“ prüfen (Tobie schon benannt oder vergessen: Karte weg). */
export async function pruefePlatz(ctx) {
  const liste = ctx.platz();
  if (!liste.length || !ctx.faehig('zuordnung')) return;
  try {
    const r = await ctx.api('tobibox/zuordnung/list', { limit: 100 });
    const da = new Map((r.zuordnungen || []).map((x) => [x.uid, x]));
    for (const p of liste) if (!da.get(p.uid) || da.get(p.uid).name) ctx.platzEntfernen(p.uid);
  } catch { /* die Karte bleibt */ }
}

/* ------------------------------------------------------------------ Verzeichnis und Stil */

const seite = (Klasse, stil = null) => ({ erzeuge: (ctx) => new Klasse(ctx), stil });

export const tobies = seite(TobiesSeite, () => css`
  /* Regal (Design 5.7, Vorlage x20_tobie_zuerst.html): Kacheln mindestens 150 px breit und 148 px hoch */
  .tb-regal { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); margin: 4px 0 16px; padding: 0; }
  .tb-regal > div { min-width: 0; display: grid; }
  .ttile { border: 0; background: var(--card); box-shadow: 0 1px 3px var(--shadow); border-radius: var(--r-card); padding: 14px 12px 12px; min-height: 148px; text-align: left; display: grid;
    gap: 10px; align-content: start; color: var(--text); min-width: 0; text-decoration: none; width: 100%; }
  .ttile:active { background: var(--primary-soft); }
  .ttile:disabled { opacity: 0.6; }
  .fig { width: 52px; height: 52px; border-radius: 26px; background: var(--primary-soft); color: var(--primary-ink); display: grid; place-items: center; flex: none; }
  .fig svg { fill: currentColor; }
  .ttile .tn { font-weight: 500; font-size: 17px; line-height: 1.25; overflow-wrap: anywhere; }
  .ttile .spielt { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .ttile .spielt .cover { flex: none; }
  .ttile .st { font-size: 13px; line-height: 1.25; color: var(--text2); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
  .ttile .zusatz { display: block; font-size: 12px; margin-top: 2px; }
  .ttile.neu { border: 2px dashed var(--primary-ink); background: none; box-shadow: none; align-content: center; justify-items: start; color: var(--primary-ink); }
  .ttile.neu .fig { background: var(--primary); color: var(--on-primary); }
  .ttile.neu .tn { color: var(--primary-ink); }
  @media (hover: hover) { .ttile:hover:not(:disabled) { background: var(--primary-soft); } .ttile.neu:hover { background: var(--primary-soft); } }

  /* Computer: Regal als Cover-Raster – das Cover des Ziels groß, der Tobie als Marke darauf */
  .app[data-layout="seite"] .tb-regal { grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 24px 20px; margin-top: 12px; }
  .app[data-layout="seite"] .ttile { position: relative; padding: 12px 12px 14px; min-height: 0; gap: 10px; border-radius: 18px; box-shadow: 0 1px 4px var(--shadow); transition: transform var(--dauer-mittel) var(--kurve), box-shadow var(--dauer-mittel) var(--kurve); }
  .app[data-layout="seite"] .ttile .spielt { display: contents; }
  .app[data-layout="seite"] .ttile .spielt .cover { order: -2; width: 100%; font-size: 64px; border-radius: 12px; }
  .app[data-layout="seite"] .ttile .fig { position: absolute; top: 20px; left: 20px; width: 40px; height: 40px; border-radius: 20px; z-index: 1; box-shadow: 0 1px 3px var(--shadow); background: var(--card); }
  .app[data-layout="seite"] .ttile .fig svg { width: 22px; height: 22px; }
  .app[data-layout="seite"] .ttile:not(.neu) .tn { order: -1; margin-top: 2px; font-size: 17px; }
  .app[data-layout="seite"] .ttile .spielt .cover.act svg { width: 44%; height: 44%; }
  .app[data-layout="seite"] .ttile .st { font-size: 14px; -webkit-line-clamp: 2; }
  .app[data-layout="seite"] .ttile.neu { min-height: 100%; border-radius: 18px; padding: 24px 16px; align-content: center; }
  .app[data-layout="seite"] .ttile.neu .fig { position: static; width: 52px; height: 52px; border-radius: 26px; background: var(--primary); box-shadow: none; }
  .app[data-layout="seite"] .ttile.neu .fig svg { width: 28px; height: 28px; }
  @media (hover: hover) { .app[data-layout="seite"] a.ttile:hover:not(.neu), .app[data-layout="seite"] button.ttile:hover:not(:disabled) { transform: translateY(-3px); box-shadow: 0 10px 22px var(--shadow); background: var(--card); } }

  .tb-suche { width: 100%; min-height: 48px; border-radius: 24px; border: 1px solid var(--line); background: var(--card); color: var(--text); padding: 0 16px; margin: 4px 0 12px; }
  .app[data-layout="seite"] .tb-suche { max-width: 480px; }
  .tb-keiner-leer .btns { justify-content: center; }
  .tb-h3 { font-size: 17px; font-weight: 500; margin: 20px 0 8px; }
  .app[data-layout="seite"] .tb-h3 { font-size: 20px; font-weight: 700; margin-top: 28px; }

  /* Karten (wartende Einträge, Namen, Geräte) */
  .tb-karte { display: block; background: var(--card); border-radius: var(--r-card); box-shadow: 0 1px 3px var(--shadow); padding: 16px; margin: 0 0 16px; min-width: 0; color: inherit; }
  .tb-karte h3 { font-size: 17px; font-weight: 500; margin: 0 0 4px; }
  .tb-karte .btns { margin-top: 12px; }
  .tb-karte.warn { background: var(--warn-bg); color: var(--warn); border: 2px solid var(--warn); }
  .tb-karte.warn .muted { color: var(--warn); }
  .tb-karte.warn .btn { background: var(--card); color: var(--text); border-color: var(--line); }
  .tb-karte.warn .btn.link { background: none; border: 0; color: var(--warn); font-weight: 500; }
  .tb-wartet { display: flex; align-items: center; gap: 12px; }
  .tb-wartet .grow { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  .app[data-layout="seite"] .tb-karte { border-radius: 20px; padding: 20px 24px; box-shadow: 0 1px 4px var(--shadow); }
  .tb-neu-karte { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .tb-karte-link { flex: 1 1 240px; min-width: 0; display: grid; gap: 2px; min-height: 56px; align-content: center; color: inherit; text-decoration: none; overflow-wrap: anywhere; }
  .tb-karte-link .zeit { font-size: 14px; }
  .tb-zeile { display: grid; gap: 0; border-top: 1px solid currentColor; padding: 2px 0 4px; }
  .tb-zeile:first-of-type { border-top: 0; }
  .tb-zeile .btn.link { justify-self: start; padding-left: 0; }
  .tb-zeilenlink { min-width: 0; display: flex; align-items: center; gap: 8px; min-height: 52px; color: inherit; text-decoration: none; }
  .tb-zeilenlink .chev { color: inherit; }
  .tb-zeilenlink .chev svg, .tb-wzeile .chev svg { width: 24px; height: 24px; fill: currentColor; display: block; }
  .tb-wzeile { width: 100%; display: flex; align-items: center; gap: 12px; min-height: 56px; padding: 8px 0; border: 0; border-top: 1px solid var(--divider); background: none; color: inherit; font: inherit; text-align: left; }
  .tb-wzeile:first-of-type { border-top: 0; }
  .tb-wzeile .grow { flex: 1; min-width: 0; display: grid; gap: 2px; overflow-wrap: anywhere; }
  .tb-wzeile .nm { font-weight: 500; }
  .tb-wzeile .chev { flex: none; color: var(--text2); display: grid; place-items: center; }
  .tb-wzeile:active { background: var(--primary-soft); }
  .tb-karte .btn.link { padding-left: 0; }

  /* Seite „Was soll … spielen?“ und die Seiten von „Neuer Tobie“ */
  .tb-titel { font-size: 24px; font-weight: 500; line-height: 1.25; margin: 4px 0 12px; overflow-wrap: anywhere; outline: none; }
  .app[data-layout="seite"] .tb-titel { font-size: 36px; font-weight: 700; letter-spacing: -0.6px; line-height: 1.15; margin: 4px 0 20px; }
  .tb-leiste { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
  .tb-leiste { flex-wrap: nowrap; align-items: center; }
  .tb-leiste .back { flex: none; }
  .tb-versehen { margin-left: auto; text-align: right; min-width: 0; flex: 0 1 auto; line-height: 1.25; padding: 6px 8px; }
  .tb-cur { display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: var(--r-card); background: var(--primary-soft); margin: 0 0 16px; }
  .tb-cur .grow { min-width: 0; display: grid; overflow-wrap: anywhere; }
  .tb-cur .lab { font-size: 13px; color: var(--text2); }
  .tb-cur .lt { font-size: 16px; font-weight: 500; }
  .tb-cur .cover { flex: none; }
  .tb-vorher { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; margin: 0 0 12px; color: var(--text2); font-size: 15px; }
  .tb-vorher .btn.link { font-weight: 500; }
  .tb-busy { opacity: 0.6; }
  .tb-wahl { display: grid; gap: 0; margin-top: 4px; min-width: 0; }
  .tb-wahl .seg2 { margin-bottom: 12px; }
  .tb-wahl .artrow { margin-top: 0; }
  .tb-kacheln { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); margin: 4px 0 12px; }
  .app[data-layout="seite"] .tb-kacheln { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 20px 16px; }
  .tb-kacheln .tile, .tb-reihe .tile { flex: none; width: 100%; font: inherit; cursor: pointer; }
  .tb-reihe { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 4px; scrollbar-width: none; }
  .tb-reihe::-webkit-scrollbar { display: none; }
  .tb-reihe .tile { flex: 0 0 120px; width: 120px; }
  .tb-wahl .card { margin: 0 0 12px; }
  .tb-wahl .rows { display: grid; }
  .tb-wahl .rowbtn { width: 100%; border: 0; border-top: 1px solid var(--divider); border-radius: 0; background: none; color: inherit; text-align: left; padding: 10px 4px; display: flex; align-items: center; gap: 12px; min-height: 56px; text-decoration: none; }
  .tb-wahl .rows > .rowbtn:first-child, .tb-wahl .tb-auf:first-child > .rowbtn:first-child { border-top: 0; }
  .tb-wahl .rowbtn .grow { flex: 1; min-width: 0; overflow-wrap: anywhere; display: grid; }
  .tb-wahl .rowbtn .nm { font-weight: 500; }
  .tb-wahl .rowbtn .chev { flex: none; width: 24px; height: 24px; display: grid; place-items: center; color: var(--text2); }
  .tb-wahl .rowbtn .chev svg { width: 24px; height: 24px; fill: currentColor; display: block; }
  .tb-wahl .rowbtn[aria-expanded="true"] .chev { transform: rotate(180deg); }
  .tb-wahl .rowbtn:active { background: var(--primary-soft); }
  .tb-sub { padding-left: 16px; border-left: 3px solid var(--primary-soft); margin: 0 0 8px 12px; }
  .tb-sub .rowbtn { min-height: 48px; }
  .tb-nr { width: 24px; text-align: center; flex: none; }
  .tb-mehr { justify-content: center; margin: 4px 0 12px; }
  .tb-laedt, .tb-leerzeile { padding: 12px 4px; }
  .tb-opt { margin-top: 12px; width: 100%; min-height: 56px; border: 1px solid var(--line); border-radius: var(--r-card); background: var(--card); display: flex; align-items: center; gap: 12px; padding: 0 16px; text-align: left; color: inherit; }
  .tb-opt .grow { flex: 1; min-width: 0; }
  .tb-opt svg { fill: var(--primary-ink); flex: none; }
  .tb-opt:active { background: var(--primary-soft); }
  .tb-manage { margin-top: 28px; padding-top: 8px; border-top: 1px solid var(--divider); }
  .tb-manage h3 { font-size: 17px; font-weight: 500; margin: 12px 0 0; }
  .tb-namefeld { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 8px 0 16px; }
  .tb-namefeld input { flex: 1 1 200px; min-height: 48px; border-radius: 10px; border: 1px solid var(--line); background: var(--card); color: var(--text); padding: 0 12px; min-width: 0; }
  .tb-manage .btn.link.danger { background: none; border: 0; color: var(--danger); }
  .tb-name .tb-namefeld { margin-bottom: 0; }
  .tb-boxwahl { margin: 0 0 16px; }
  .tb-glabel { font-size: 14px; color: var(--text2); margin: 0 0 4px; }
  .note.ok { background: var(--ok-bg); color: var(--ok); border: 2px solid var(--ok); }

  /* Weg 1 und 2: zwei große Zeilen, Warteseite mit Ring */
  .tb-weg { width: 100%; display: flex; align-items: center; gap: 14px; min-height: 80px; padding: 12px 16px; background: var(--card); border: 1px solid var(--line); border-radius: var(--r-card); text-align: left; margin: 0 0 12px; color: var(--text); text-decoration: none; }
  .tb-weg .wc-i { width: 44px; height: 44px; border-radius: 22px; background: var(--primary-soft); color: var(--primary-ink); display: grid; place-items: center; flex: none; }
  .tb-weg .wc-i svg { fill: currentColor; }
  .tb-weg .grow { flex: 1; min-width: 0; display: grid; gap: 2px; }
  .tb-weg .wc-t { font-weight: 500; font-size: 17px; line-height: 1.3; }
  .tb-weg .chev { color: var(--text2); display: grid; place-items: center; }
  .tb-weg .chev svg { fill: currentColor; display: block; }
  .tb-weg:active { background: var(--primary-soft); }
  @media (hover: hover) { .tb-weg:hover { background: var(--primary-soft); } }
  .tb-warte { text-align: center; padding: 24px 8px; display: grid; justify-items: center; gap: 4px; }
  .tb-warte .tb-titel { margin: 0 0 4px; }
  .tb-warte .btns { justify-content: center; margin-top: 16px; }
  .ring { width: 120px; height: 120px; margin: 8px auto 16px; border-radius: 60px; border: 4px solid var(--primary-ink); display: grid; place-items: center; animation: tb-ring 1.6s ease-in-out infinite; }
  .ring svg { fill: var(--primary-ink); }
  @keyframes tb-ring { 50% { transform: scale(1.08); box-shadow: 0 0 0 12px var(--primary-soft); } }
  @media (prefers-reduced-motion: reduce) {
    .ring { animation: none; }
    .ttile, .app[data-layout="seite"] .ttile { transition: none; }
    .app[data-layout="seite"] a.ttile:hover:not(.neu), .app[data-layout="seite"] button.ttile:hover:not(:disabled) { transform: none; }
  }

  /* „Gespielt von“ und Chips (Serienseite) */
  .tb-gespielt { background: var(--card); border-radius: var(--r-card); box-shadow: 0 1px 3px var(--shadow); padding: 12px 16px 14px; margin: 0 0 16px; min-width: 0; }
  .tb-chips { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .tb-keiner { color: var(--text); }
  .tb-chip { display: inline-flex; align-items: center; gap: 6px; min-height: 44px; padding: 0 14px 0 10px; border-radius: 22px; background: var(--primary-soft); color: var(--primary-ink); font-weight: 500; text-decoration: none; border: 1px solid var(--line); overflow-wrap: anywhere; }
  .tb-chip svg { fill: currentColor; flex: none; }
  .tb-chip.plus { padding: 0 16px; background: none; }
  .tb-chips.klein { margin-top: 4px; }
  .tb-gespielt .btn.link { background: none; border: 0; }
  .app[data-layout="seite"] .tb-gespielt { border-radius: 20px; padding: 16px 24px 18px; box-shadow: 0 1px 4px var(--shadow); }
`);

export const tobie = seite(TobieSeite);
export const neu = seite(NeuSeite);
export const neuWarten = seite(NeuWartenSeite);
export const neuZiel = seite(NeuZielSeite);
export const neuQueue = seite(NeuQueueSeite);
export const geben = seite(GebenSeite);
export { Zielwahl, TobieModell };

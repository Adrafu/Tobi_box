/* Seite „Serie“ (Design 5.3, 5.9 Menüs, 10 Rechte; Paket A8): Kopf, Folgenliste, Einzeltitel, Menüs, „Das ist richtig“.
 *
 * Route `#serie-<id>`. Daten: `serie/get` (Kurzform der Serie, `folgen` mit `tobies`, `zuordnungen`, `stand`). Jede Änderung sendet
 * den `stand` mit und lädt danach frisch (`stand_veraltet` → Meldung und neu laden). Rechte (Design 10): Name ändern, Art ändern,
 * Verschieben, Papierkorb (mit Rückfrage, nennt die Tobies) und „Das ist richtig“ sind Alltag; „Reihenfolge ändern“
 * (`folgen/order`) und „Mit anderem zusammenführen …“ (`serien/zusammenfuehren`) gibt es nur für Administratoren und sind für
 * andere nicht da (nicht nur gesperrt).
 *
 * „Gespielt von“ mit Chips, „+ Tobie“ und „Einem Tobie geben …“ (Karte und „⋯“ der Folge) kommen aus seiten/tobies.js (A9).
 * Noch nicht hier: Player und „Reinhören“ (A8b), „Cover ändern“ (A8f),
 * Kapitelzeile (A8d), „Anders einsortieren“ (A-3), Playlists (Stufe C), Cover-Flug (A6m/A8m). Schnittstelle zur App: bausteine.js.
 */
import { html, nothing, css, repeat, ic, cover, coverKlasse, coverGrossUrl, ladeMitGrenze, untertitel, uhr, dauerText, norm } from '../bausteine.js';
import { SERIE, ZEILE, GRUENDE, TOBIE, SEITE, fuellen } from '../texte.js';
import { gespieltVonKarte, folgenChips, gebenLink } from './tobies.js';

export const SICHTBAR = 20; // Folgen, die zuerst gezeigt werden; ab mehr als 20 gibt es das Suchfeld (Design 5.3)
const WAHL_GROESSE = 30; // Päckchen der Zielwahl
const ARTEN = ['hoerspiel', 'hoerbuch', 'musik', 'geschichte'];
const ENDE_FEHLER = ['stand_veraltet', 'serie_nicht_gefunden', 'folge_nicht_gefunden']; // Blatt schließen, neu laden

/* ------------------------------------------------------------------ reine Funktionen */

const tName = (t) => t?.name || TOBIE.ohne_name;

/* Tobies ohne Doppelte (nach Kennung). */
function einmalig(tobies) {
  const aus = [];
  const gesehen = new Set();
  for (const t of tobies) {
    if (!t || gesehen.has(t.uid)) continue;
    gesehen.add(t.uid);
    aus.push(t);
  }
  return aus;
}

/* Tobies, die auf die ganze Serie oder auf eine ihrer Folgen zeigen (Rückfrage beim Löschen, Vertrag 24). */
export function tobiesDerSerie(s) {
  return einmalig([...(s?.zuordnungen || []), ...(s?.folgen || []).flatMap((f) => f.tobies || [])]);
}

/* Satz mit Zahl und Namen aus einem Paar { eins, mehr }; `werte` ergänzt weitere Platzhalter. Leere Liste: ''. */
export function tobiesSatz(paar, tobies, werte = {}) {
  if (!tobies.length) return '';
  return fuellen(tobies.length === 1 ? paar.eins : paar.mehr, { ...werte, anzahl: tobies.length, namen: tobies.map(tName).join(', ') });
}

/* Gründe für „Bitte kurz ansehen“ (Design 7.3, GRUENDE): ohne Doppelte, unbekannte Codes fallen weg; ohne Text der Rückfall. */
export function gruendeTexte(s) {
  const codes = [...(s?.pruefen_gruende || []), ...(s?.folgen || []).flatMap((f) => f.pruefen_gruende || [])];
  const aus = [...new Set(codes)].filter((c) => GRUENDE[c]).map((c) => GRUENDE[c]);
  return aus.length ? aus : [SERIE.ansehen.grund_sonst];
}

export const brauchtPruefung = (s) => !!(s?.pruefen || (s?.folgen || []).some((f) => f.pruefen));

/* Dauer und Kapitelzahl einer Folge getrennt (die Spalten am Computer brauchen beides einzeln). */
export function folgenMetaTeile(x) {
  const dauer = typeof x.dauer_s === 'number' && x.dauer_s > 0 ? uhr(x.dauer_s) : '';
  const kap = Array.isArray(x.kapitel) && x.kapitel.length ? x.kapitel.length : (x.art === 'ordner' && x.tracks > 1 ? x.tracks : 0);
  return { dauer, kapitel: kap ? fuellen(SERIE.kapitel, { anzahl: kap }) : '' };
}

/* Zeile unter dem Titel einer Folge: „2:19“ und bei Ordner-Folgen „· 14 Kapitel“; fehlt beides, nichts (Daten kommen erst später). */
export function folgenMeta(x) {
  const t = folgenMetaTeile(x);
  return [t.dauer, t.kapitel].filter(Boolean).join(' · ');
}

/* „Schon 18 % gehört · noch 21 Min.“ aus `hoerstelle` der Serie, sonst null. */
export function serienFortschritt(s) {
  const h = s?.hoerstelle;
  if (!h || typeof h.anteil !== 'number' || h.anteil <= 0) return null;
  if (h.anteil >= 0.999) return ZEILE.fertig;
  return fuellen(SERIE.schon_gehoert, { prozent: Math.round(h.anteil * 100), dauer: dauerText(h.rest_s ?? 0) });
}

const anfang = (name) => String(name ?? '').trim().charAt(0).toUpperCase() || '?';

/* ------------------------------------------------------------------ Seite */

class SerieSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.id = null;
    this.z = { phase: 'laedt', fehlerCode: null, serie: null };
    this.sterm = '';
    this.gezeigt = SICHTBAR;
    this.ordnen = false;
    this._lauf = 0;
    this._kette = Promise.resolve(); // Reihenfolge: Änderungen laufen nacheinander (jede mit dem neuesten `stand`)
    this._busy = false;
    this._fokus = null;
  }

  betreten(route) {
    const id = route?.id ?? null;
    if (id !== this.id) {
      this.id = id;
      this.z = { phase: 'laedt', fehlerCode: null, serie: null };
      this.sterm = '';
      this.gezeigt = SICHTBAR;
      this.ordnen = false;
      this._kette = Promise.resolve();
    }
    this.laden(this.z.phase === 'bereit'); // schon Daten da: still auffrischen
  }

  neuLaden() { return this.laden(true); }

  verlassen() { this._lauf += 1; this.ordnen = false; }

  /* ---- Daten */
  async laden(still = false) {
    const lauf = ++this._lauf;
    const id = this.id;
    if (!still || this.z.phase !== 'bereit') this.z = { ...this.z, phase: 'laedt', fehlerCode: null };
    this.ctx.neuZeichnen();
    try {
      const r = await ladeMitGrenze(this.ctx.api('tobibox/serie/get', { serie_id: id }), this.ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.ctx.covers.merke([r]);
      this.z = { phase: 'bereit', fehlerCode: null, serie: r };
    } catch (err) {
      if (lauf !== this._lauf) return;
      const code = err?.code || 'unknown_error';
      this.z = code === 'serie_nicht_gefunden' ? { phase: 'weg', fehlerCode: code, serie: null } : { ...this.z, phase: 'fehler', fehlerCode: code };
    }
    this.ctx.neuZeichnen();
  }

  /* Fehler einer Änderung: Meldung; bei „veraltet“ und „gibt es nicht mehr“ neu laden und das Blatt schließen ('zu'),
   * sonst bleibt das Blatt offen ('offen'), damit man es noch einmal versuchen kann. */
  _fehler(err) {
    const code = err?.code || 'unknown_error';
    this.ctx.meldeFehler(this.ctx.fehlerText(code));
    if (ENDE_FEHLER.includes(code)) { this.laden(true); return 'zu'; }
    return 'offen';
  }

  /* ---- Blätter */
  /* Öffnet ein Blatt; nach dem Schließen (nicht beim Ersetzen durch das nächste Blatt, nicht bei Seitenwechsel) geht der Fokus
   * zurück zum Auslöser, oder zur Überschrift, wenn es ihn nicht mehr gibt (zum Beispiel nach dem Löschen einer Folge). */
  _blatt(opts, ausloeser) {
    const p = this.ctx.oeffneBlatt(opts);
    p.then((grund) => { if (grund !== 'ersetzt' && grund !== 'route') this._fokusZurueck(ausloeser); });
    return p;
  }

  _fokusZurueck(el) {
    setTimeout(() => {
      const ziel = el && el.isConnected ? el : this.ctx.wurzel?.querySelector('main h2');
      ziel?.focus?.({ preventScroll: true });
    }, 0);
  }

  /* Rückfrage mit Sätzen und zwei Knöpfen; `fn` liefert `false`, wenn das Blatt offen bleiben soll. */
  _frage({ titel, saetze, knopf, gefahr = false, fn }, ausloeser) {
    return this._blatt({
      titel,
      rolle: 'alertdialog',
      inhalt: html`${saetze.filter(Boolean).map((t) => html`<p>${t}</p>`)}`,
      knoepfe: [{ label: SERIE.abbrechen }, { label: knopf, kind: gefahr ? 'danger solid' : 'primary', fn }],
    }, ausloeser);
  }

  /* Blatt mit einem Namensfeld. `speichern(wert)` wirft { code } bei Fehlern. */
  _nameBlatt({ wert, max, ausloeser, speichern }) {
    let eingabe = wert;
    let fehler = '';
    let laeuft = false;
    const ok = async () => {
      if (laeuft) return false;
      const v = eingabe.trim();
      if (!v) { fehler = SERIE.name.leer; this.ctx.neuZeichnen(); return false; }
      if (v === wert.trim()) return undefined; // nichts geändert: einfach schließen
      laeuft = true;
      try {
        await speichern(v);
        this.ctx.melde(SERIE.name.gespeichert);
        return undefined;
      } catch (err) {
        if (err?.code === 'name_ungueltig') { fehler = this.ctx.fehlerText('name_ungueltig'); this.ctx.neuZeichnen(); return false; }
        return this._fehler(err) === 'zu' ? undefined : false;
      } finally { laeuft = false; }
    };
    const inhalt = () => html`<div class="se-feld"><label for="se-name">${SERIE.name.label}</label>
      <input id="se-name" type="text" maxlength=${max} autocomplete="off" autofocus .value=${eingabe} aria-invalid=${fehler ? 'true' : 'false'} aria-describedby=${fehler ? 'se-name-f' : nothing}
        @input=${(e) => { eingabe = e.target.value; if (fehler) { fehler = ''; this.ctx.neuZeichnen(); } }}
        @keydown=${async (e) => { if (e.key !== 'Enter') return; e.preventDefault(); if ((await ok()) !== false) this.ctx.schliesseBlatt('knopf'); }}>
      ${fehler ? html`<p class="se-fehl" id="se-name-f" role="alert">${fehler}</p>` : nothing}</div>`;
    return this._blatt({ titel: SERIE.name.titel, inhalt, knoepfe: [{ label: SERIE.abbrechen }, { label: SERIE.name.speichern, kind: 'primary', fn: ok }] }, ausloeser);
  }

  /* Zielwahl (Verschieben, Zusammenführen): Suchfeld und Liste der Einträge aus `serien/list`, Päckchen von 30.
   * `nurNormal`: nur normale Serien (Zusammenführen, Vertrag 27). Ausgeschlossen sind immer diese Serie, Einzeltitel (Vertrag 14.4)
   * und für Nicht-Administratoren die Überraschungs-Serie (Vertrag 26). */
  _waehle({ titel, nurNormal = false, ausloeser, onWahl }) {
    const P = { term: '', phase: 'laedt', fehlerCode: null, eintraege: [], weitere: false, ladeMehr: false };
    const eigene = this.z.serie.id;
    const admin = this.ctx.admin;
    const neu = this.ctx.faehig('bibliothek');
    let lauf = 0;
    let timer = null;
    const passt = (s) => s.id !== eigene && !s.einzeln && (nurNormal ? s.typ === 'normal' : (admin || s.typ !== 'ueberraschung'))
      && (neu || !P.term.trim() || norm(s.name).includes(norm(P.term.trim())));
    const hole = async (offset = 0) => {
      const mein = ++lauf;
      const text = P.term.trim();
      if (offset === 0) { P.phase = 'laedt'; P.fehlerCode = null; } else P.ladeMehr = true;
      this.ctx.neuZeichnen();
      try {
        const felder = neu ? { sortierung: 'name', filter: ['sammlung'], limit: WAHL_GROESSE, offset, ...(text.length >= 2 ? { text } : {}) } : {};
        const r = await ladeMitGrenze(this.ctx.api('tobibox/serien/list', felder), this.ctx.grenzeMs);
        if (mein !== lauf) return;
        this.ctx.covers.merke(r.serien);
        const dazu = (r.serien || []).filter(passt);
        const schon = new Set(P.eintraege.map((x) => x.id));
        P.eintraege = offset === 0 ? dazu : [...P.eintraege, ...dazu.filter((x) => !schon.has(x.id))];
        P.weitere = !!r.weitere;
        P.phase = 'bereit';
      } catch (err) {
        if (mein !== lauf) return;
        if (offset === 0) { P.phase = 'fehler'; P.fehlerCode = err?.code || 'unknown_error'; } else this.ctx.meldeFehler(this.ctx.fehlerText(err?.code || 'unknown_error'));
      }
      P.ladeMehr = false;
      this.ctx.neuZeichnen();
    };
    const zeile = (x) => html`<button type="button" class="se-wrow" data-wahl=${x.id} aria-label=${fuellen(SERIE.wahl.wahlname, { name: x.name })} @click=${() => onWahl(x)}>
      ${cover(x, 'sm')}<span class="grow"><span class="nm">${x.name}</span><span class="muted">${untertitel(x, { dauer: false })}</span></span>
      <span class="se-chev" aria-hidden="true">${ic('chev', 24)}</span></button>`;
    const inhalt = () => html`<label class="sr" for="se-wahl-s">${SERIE.wahl.suchen}</label>
      <input id="se-wahl-s" class="se-sfeld" type="search" autocomplete="off" placeholder=${SERIE.wahl.platzhalter} .value=${P.term}
        @input=${(e) => { P.term = e.target.value; clearTimeout(timer); timer = setTimeout(() => hole(0), 250); }}>
      ${P.phase === 'laedt' ? html`<p class="muted se-wlaedt" role="status">${SEITE.laedt}</p>`
        : P.phase === 'fehler' ? this.ctx.fehlerKarte(P.fehlerCode, () => hole(0))
          : P.eintraege.length ? html`<div class="se-wahl" data-wahl-liste>${P.eintraege.map(zeile)}</div>
            ${P.weitere ? html`<div class="btns se-mehr"><button type="button" class="btn" data-wahl-mehr ?disabled=${P.ladeMehr} @click=${() => hole(P.eintraege.length)}>${fuellen(SERIE.mehr_laden, { anzahl: WAHL_GROESSE })}</button></div>` : nothing}`
            : html`<p class="muted se-wleer" data-wahl-leer>${SERIE.wahl.nichts}</p>`}`;
    hole(0);
    return this._blatt({ titel, inhalt, knoepfe: [{ label: SERIE.abbrechen }] }, ausloeser).then((g) => { clearTimeout(timer); lauf += 1; return g; });
  }

  /* ---- Menü des Eintrags („⋯“ oben rechts) */
  serieMenue(ausloeser) {
    const s = this.z.serie;
    const admin = this.ctx.admin;
    const art = this.ctx.faehig('bibliothek') && s.typ !== 'ueberraschung';
    const punkte = [
      { id: 'name', label: SERIE.menue.name, fn: () => this.serieUmbenennen(ausloeser) },
      ...(art ? [{ id: 'art', label: SERIE.menue.art, fn: () => this.artAendern(ausloeser) }] : []),
      ...(admin && !s.einzeln && s.folgen.length > 1 ? [{ id: 'reihenfolge', label: SERIE.menue.reihenfolge, fn: () => this.reihenfolgeStart(ausloeser) }] : []),
      ...(admin && s.typ === 'normal' && this.ctx.faehig('korrektur') ? [{ id: 'zusammen', label: SERIE.menue.zusammen, fn: () => this.zusammenfuehren(ausloeser) }] : []),
    ];
    this._menue(s.name, punkte, this._papierkorbPunkt(ausloeser), ausloeser);
  }

  /* Menü einer Folge („⋯“ in der Zeile): Name ändern, In anderes verschieben …, abgesetzt Papierkorb … */
  folgeMenue(x, ausloeser) {
    const titel = x.anzeige || x.name;
    this._menue(titel, [
      { id: 'geben', label: TOBIE.einem_tobie_geben, fn: () => this.ctx.navigiere(gebenLink(this.z.serie.id, x.name)) },
      { id: 'name', label: SERIE.menue.name, fn: () => this.folgeUmbenennen(x, ausloeser) },
      ...(this.ctx.faehig('korrektur') ? [{ id: 'verschieben', label: SERIE.menue.verschieben, fn: () => this.folgeVerschieben(x, ausloeser) }] : []),
    ], { id: 'papierkorb', label: SERIE.menue.folge_papierkorb, fn: () => this.folgeLoeschen(x, ausloeser) }, ausloeser);
  }

  /* „In den Papierkorb …“ des Eintrags; ohne die Fähigkeit `serie_loeschen` gibt es den Punkt nicht (wie im alten Panel). */
  _papierkorbPunkt(ausloeser) {
    return this.ctx.faehig('serie_loeschen') ? { id: 'papierkorb', label: SERIE.menue.papierkorb, fn: () => this.serieLoeschen(ausloeser) } : null;
  }

  _menue(titel, punkte, abgesetzt, ausloeser, davor = nothing) {
    const knopf = (p, extra = '') => html`<button type="button" class=${`btn ${extra}`.trim()} data-menue=${p.id} @click=${() => p.fn()}>${p.label}</button>`;
    return this._blatt({
      titel,
      inhalt: html`${davor}<div class="se-stack">${punkte.map((p) => knopf(p))}</div>
        ${abgesetzt ? html`<div class="se-apart">${knopf(abgesetzt, 'link danger')}</div>` : nothing}`,
      knoepfe: [{ label: SERIE.schliessen }],
    }, ausloeser);
  }

  /* ---- „Das ist richtig“ und „Das stimmt nicht“ (Design 5.3, U11) */
  async richtig() {
    if (this._busy) return;
    this._busy = true;
    try {
      await this.ctx.api('tobibox/einsortierung/bestaetigen', { serie_id: this.id });
      this._fokus = 'main h2'; // die Karte verschwindet, der Knopf mit ihr
      this.ctx.melde(SERIE.ansehen.danke);
      await this.laden(true);
    } catch (err) { this._fehler(err); } finally { this._busy = false; }
  }

  /* „Das stimmt nicht“ öffnet nur das passende Menü: Name, Art, (Administrator) Zusammenführen, abgesetzt Papierkorb.
   * „Anders einsortieren …“ kommt mit A-3. */
  stimmtNicht(ausloeser) {
    const s = this.z.serie;
    const admin = this.ctx.admin;
    const art = this.ctx.faehig('bibliothek') && s.typ !== 'ueberraschung';
    const punkte = [
      ...(art ? [{ id: 'art', label: SERIE.menue.art, fn: () => this.artAendern(ausloeser) }] : []),
      { id: 'name', label: SERIE.menue.name, fn: () => this.serieUmbenennen(ausloeser) },
      ...(admin && s.typ === 'normal' && this.ctx.faehig('korrektur') ? [{ id: 'zusammen', label: SERIE.menue.zusammen, fn: () => this.zusammenfuehren(ausloeser) }] : []),
    ];
    const davor = html`<p class="muted">${fuellen(SERIE.stimmt_nicht.satz, { name: s.name })}</p>${!s.einzeln && s.folgen.length ? html`<p class="muted">${SERIE.stimmt_nicht.folge}</p>` : nothing}`;
    this._menue(SERIE.stimmt_nicht.titel, punkte, this._papierkorbPunkt(ausloeser), ausloeser, davor);
  }

  /* ---- Umbenennen */
  serieUmbenennen(ausloeser) {
    const s = this.z.serie;
    return this._nameBlatt({
      wert: s.name, max: 100, ausloeser,
      speichern: async (name) => { await this.ctx.api('tobibox/serie/rename', { serie_id: s.id, name }); await this.laden(true); },
    });
  }

  folgeUmbenennen(x, ausloeser) {
    const s = this.z.serie;
    return this._nameBlatt({
      wert: x.anzeige || x.name, max: 200, ausloeser,
      speichern: async (name) => { await this.ctx.api('tobibox/folge/rename', { serie_id: s.id, folge: x.name, name, stand: s.stand }); await this.laden(true); },
    });
  }

  /* ---- Art ändern (Blatt „Was ist das?“) */
  artAendern(ausloeser) {
    const s = this.z.serie;
    const aktuell = ARTEN.includes(s.art) ? s.art : 'hoerspiel';
    let wahl = aktuell;
    let laeuft = false;
    const inhalt = () => html`<p class="muted">${SERIE.art.satz}</p>
      <div class="se-stack" role="radiogroup" aria-label=${SERIE.art.label}>${ARTEN.map((a) => html`
        <button type="button" class="se-opt" role="radio" data-art=${a} aria-checked=${wahl === a ? 'true' : 'false'} @click=${() => { wahl = a; this.ctx.neuZeichnen(); }}><span>${ZEILE.art[a]}</span>${wahl === a ? ic('check', 22) : nothing}</button>`)}</div>`;
    const speichern = async () => {
      if (laeuft) return false;
      if (wahl === aktuell) return undefined;
      laeuft = true;
      try {
        await this.ctx.api('tobibox/serie/art_setzen', { serie_id: s.id, art: wahl });
        this.ctx.melde(fuellen(SERIE.art.gespeichert, { art: ZEILE.art[wahl] }));
        await this.laden(true);
        return undefined;
      } catch (err) { return this._fehler(err) === 'zu' ? undefined : false; } finally { laeuft = false; }
    };
    return this._blatt({ titel: SERIE.art.titel, inhalt, knoepfe: [{ label: SERIE.abbrechen }, { label: SERIE.name.speichern, kind: 'primary', fn: speichern }] }, ausloeser);
  }

  /* ---- Verschieben (Folge in eine andere Serie) */
  folgeVerschieben(x, ausloeser) {
    return this._waehle({ titel: SERIE.wahl.verschieben, ausloeser, onWahl: (ziel) => this._frageVerschieben(x, ziel, ausloeser) });
  }

  _frageVerschieben(x, ziel, ausloeser) {
    const titel = x.anzeige || x.name;
    const tobies = x.tobies || [];
    return this._frage({
      titel: fuellen(SERIE.verschieben.titel, { titel, ziel: ziel.name }),
      saetze: [SERIE.verschieben.satz, tobiesSatz(SERIE.verschieben.tobies, tobies)],
      knopf: SERIE.verschieben.knopf,
      fn: async () => {
        if (this._busy) return false;
        this._busy = true;
        const s = this.z.serie;
        try {
          await this.ctx.api('tobibox/folge/verschieben', { serie_id: s.id, folge: x.name, ziel_serie_id: ziel.id, stand: s.stand, ...(tobies.length ? { tobies_bestaetigt: true } : {}) });
          this.ctx.melde(fuellen(SERIE.verschieben.fertig, { titel, ziel: ziel.name }));
          await this.laden(true);
          return undefined;
        } catch (err) {
          if (err?.code === 'tobies_betroffen') return this._nochmalFragen(x, ziel, ausloeser, (neu) => this._frageVerschieben(neu, ziel, ausloeser));
          return this._fehler(err) === 'zu' ? undefined : false;
        } finally { this._busy = false; }
      },
    }, ausloeser);
  }

  /* Das Backend sagt „es hängen Tobies daran“, obwohl die Seite keine kannte: neu laden und mit dem frischen Stand noch einmal fragen. */
  async _nochmalFragen(x, ziel, ausloeser, frage) {
    await this.laden(true);
    const neu = this.z.serie?.folgen?.find((f) => f.name === x.name);
    if (neu) frage(neu);
    return false; // das nächste Blatt hat das alte ersetzt
  }

  /* ---- Zusammenführen (Administrator) */
  zusammenfuehren(ausloeser) {
    return this._waehle({ titel: SERIE.wahl.zusammen, nurNormal: true, ausloeser, onWahl: (ziel) => this._frageZusammen(ziel, ausloeser) });
  }

  _frageZusammen(ziel, ausloeser) {
    const s = this.z.serie;
    const tobies = tobiesDerSerie(s);
    const w = { name: s.name, ziel: ziel.name };
    return this._frage({
      titel: fuellen(SERIE.zusammen.titel, w),
      saetze: [fuellen(SERIE.zusammen.satz, w), tobiesSatz(SERIE.zusammen.tobies, tobies, w)],
      knopf: SERIE.zusammen.knopf,
      fn: async () => {
        if (this._busy) return false;
        this._busy = true;
        const q = this.z.serie;
        try {
          const r = await this.ctx.api('tobibox/serien/zusammenfuehren', { quelle_id: q.id, ziel_id: ziel.id, stand_quelle: q.stand, stand_ziel: ziel.stand, ...(tobies.length ? { tobies_bestaetigt: true } : {}) });
          this._lauf += 1;
          window.location.hash = `#serie-${r.ziel?.id ?? ziel.id}`;
          this.ctx.melde(fuellen(SERIE.zusammen.fertig, w));
          return undefined;
        } catch (err) {
          if (err?.code === 'tobies_betroffen') { await this.laden(true); if (this.z.serie) this._frageZusammen(ziel, ausloeser); return false; }
          return this._fehler(err) === 'zu' ? undefined : false;
        } finally { this._busy = false; }
      },
    }, ausloeser);
  }

  /* ---- Papierkorb mit Rückfrage (nennt die Tobies, die dann nichts mehr spielen) */
  _papierkorbSatz(art, tobies) {
    return [SERIE.papierkorb[art], tobiesSatz(SERIE.papierkorb.tobies, tobies), SERIE.papierkorb.admin].filter(Boolean).join(' ');
  }

  serieLoeschen(ausloeser) {
    const s = this.z.serie;
    const tobies = tobiesDerSerie(s);
    return this._frage({
      titel: fuellen(SERIE.papierkorb.titel, { titel: s.name }),
      saetze: [this._papierkorbSatz('serie', tobies)],
      knopf: SERIE.papierkorb.knopf,
      gefahr: true,
      fn: async () => {
        if (this._busy) return false;
        this._busy = true;
        const q = this.z.serie;
        try {
          await this.ctx.api('tobibox/serie/delete', { serie_id: q.id, stand: q.stand, ...(tobies.length ? { tobies_bestaetigt: true } : {}) });
          this._lauf += 1;
          window.location.hash = '#bibliothek';
          this.ctx.melde(fuellen(SERIE.papierkorb.fertig, { titel: q.name }));
          return undefined;
        } catch (err) {
          if (err?.code === 'tobies_betroffen') { await this.laden(true); if (this.z.serie) this.serieLoeschen(ausloeser); return false; }
          return this._fehler(err) === 'zu' ? undefined : false;
        } finally { this._busy = false; }
      },
    }, ausloeser);
  }

  folgeLoeschen(x, ausloeser) {
    const titel = x.anzeige || x.name;
    const tobies = x.tobies || [];
    return this._frage({
      titel: fuellen(SERIE.papierkorb.titel, { titel }),
      saetze: [this._papierkorbSatz('folge', tobies)],
      knopf: SERIE.papierkorb.knopf,
      gefahr: true,
      fn: async () => {
        if (this._busy) return false;
        this._busy = true;
        const s = this.z.serie;
        try {
          await this.ctx.api('tobibox/folge/delete', { serie_id: s.id, folge: x.name, stand: s.stand, ...(tobies.length ? { tobies_bestaetigt: true } : {}) });
          this.ctx.melde(fuellen(SERIE.papierkorb.fertig, { titel }));
          await this.laden(true);
          return undefined;
        } catch (err) {
          if (err?.code === 'tobies_betroffen') return this._nochmalFragen(x, null, ausloeser, (neu) => this.folgeLoeschen(neu, ausloeser));
          return this._fehler(err) === 'zu' ? undefined : false;
        } finally { this._busy = false; }
      },
    }, ausloeser);
  }

  /* ---- Reihenfolge ändern (Administrator, ▲/▼ je Zeile, kein Ziehen) */
  reihenfolgeStart() {
    this.ordnen = true;
    this.sterm = '';
    this.ctx.schliesseBlatt('ersetzt'); // der Fokus geht erst zurück zum Auslöser, dann (unten) auf „Fertig“
    this.ctx.neuZeichnen();
    setTimeout(() => this.ctx.wurzel?.querySelector('[data-fertig]')?.focus?.({ preventScroll: true }), 0);
  }

  reihenfolgeEnde() {
    this.ordnen = false;
    this._fokus = 'main h2';
    this.ctx.neuZeichnen();
  }

  /* Tausch in der Liste sofort sichtbar; `folgen/order` sendet die ganze Liste mit dem neuesten `stand` (nacheinander). */
  bewege(i, richtung) {
    const s = this.z.serie;
    const j = i + richtung;
    if (!s || j < 0 || j >= s.folgen.length) return;
    const folgen = [...s.folgen];
    [folgen[i], folgen[j]] = [folgen[j], folgen[i]];
    const name = folgen[j].name;
    this.z = { ...this.z, serie: { ...s, folgen } };
    this._fokus = { folge: name, knopf: richtung < 0 ? 'auf' : 'ab' };
    this.ctx.neuZeichnen();
    this._kette = this._kette.then(async () => {
      const aktuell = this.z.serie;
      try {
        const r = await this.ctx.api('tobibox/folgen/order', { serie_id: aktuell.id, folgen: aktuell.folgen.map((f) => f.name), stand: aktuell.stand });
        this.z = { ...this.z, serie: { ...this.z.serie, stand: r.serie?.stand ?? this.z.serie.stand } };
      } catch (err) { this._fehler(err); this.laden(true); }
    });
  }

  /* ---- Darstellung */
  nachRender(wurzel) {
    for (const el of wurzel.querySelectorAll('[data-cover-gross]')) {
      const key = `${el.dataset.coverGross}:${el.dataset.stand}`;
      if (el._grossKey === key) continue;
      el._grossKey = key;
      el.style.backgroundImage = '';
      delete el.dataset.bild;
      if (!el.dataset.stand) continue; // kein Cover vorhanden
      coverGrossUrl(this.ctx.covers, el.dataset.coverGross, el.dataset.stand).then((url) => {
        if (url && el._grossKey === key && el.isConnected) { el.style.backgroundImage = `url("${url}")`; el.dataset.bild = '1'; }
      });
    }
    const f = this._fokus;
    if (f) {
      let ziel = null;
      if (typeof f === 'string') ziel = wurzel.querySelector(f);
      else {
        const zeile = [...wurzel.querySelectorAll('[data-folge]')].find((r) => r.dataset.folge === f.folge);
        ziel = zeile?.querySelector(`[data-${f.knopf}]:not([disabled])`) ?? zeile?.querySelector('[data-auf]:not([disabled]), [data-ab]:not([disabled])') ?? wurzel.querySelector('[data-fertig]');
      }
      if (ziel) { this._fokus = null; ziel.focus?.({ preventScroll: true }); }
    }
  }

  /* Am Computer sitzt das Menü des Eintrags im großen Kopf (neben dem Titel), sonst oben rechts neben „‹ Bibliothek“. */
  _leiste(s) {
    const gross = this.ctx.layout === 'seite';
    return html`<div class="se-leiste"><a class="back" href="#bibliothek" data-zurueck>${SERIE.zurueck}</a>
      ${s && !gross ? html`<button type="button" class="iconbtn se-mehr-knopf" data-menue-serie aria-haspopup="dialog" aria-label=${fuellen(SERIE.mehr_zu, { titel: s.name })}
        @click=${(e) => this.serieMenue(e.currentTarget)}>${ic('more', 24)}</button>` : nothing}</div>`;
  }

  render(route) {
    const { ctx, z } = this;
    if (route?.id !== this.id || z.phase === 'laedt') return html`${this._leiste(null)}${ctx.laedt()}`;
    if (z.phase === 'fehler') return html`${this._leiste(null)}${ctx.fehlerKarte(z.fehlerCode, () => this.laden())}`;
    if (z.phase === 'weg') return html`${this._leiste(null)}<div class="note err" role="alert" data-zustand="weg">${SERIE.weg.satz} <a href="#bibliothek">${SERIE.weg.link}</a></div>`;
    const s = z.serie;
    return html`${this._leiste(s)}${this._kopf(s)}${gespieltVonKarte(s)}${this._ansehen(s)}${s.einzeln ? this._einzeln(s) : this._folgen(s)}`;
  }

  _kopf(s) {
    const fort = serienFortschritt(s);
    const gross = this.ctx.layout === 'seite';
    return html`<div class="se-hero">
      <div class=${`cover se-xl ${coverKlasse(s.id)}`} data-cover-gross=${s.id} data-stand=${s.cover_stand ?? ''} aria-hidden="true"><span class="bst">${anfang(s.name)}</span></div>
      <div class="se-htxt"><h2 tabindex="-1">${s.name}</h2><div class="muted" data-untertitel>${untertitel(s)}</div>
        ${fort ? html`<div class="muted" data-fortschritt>${fort}</div>` : nothing}
        ${gross ? html`<div class="btns se-aktionen"><button type="button" class="btn se-mehr-knopf" data-menue-serie aria-haspopup="dialog" aria-label=${fuellen(SERIE.mehr_zu, { titel: s.name })}
          @click=${(e) => this.serieMenue(e.currentTarget)}>${ic('more', 24)}${SERIE.mehr}</button></div>` : nothing}</div></div>`;
  }

  _ansehen(s) {
    if (!brauchtPruefung(s)) return nothing;
    const a = SERIE.ansehen;
    return html`<div class="note warn" data-karte="ansehen" role="group" aria-label=${a.titel}><strong>${a.titel}</strong>
      ${gruendeTexte(s).map((g) => html`<span class="se-grund">${g}</span>`)}
      <div class="btns"><button type="button" class="btn" data-richtig @click=${() => this.richtig()}>${a.richtig}</button>
        <button type="button" class="btn" data-stimmt-nicht aria-haspopup="dialog" @click=${(e) => this.stimmtNicht(e.currentTarget)}>${a.stimmt_nicht}</button></div></div>`;
  }

  _einzeln(s) {
    const art = SERIE.einzeln[s.art] ? s.art : 'hoerspiel';
    return html`<p class="se-einzeln" data-einzeln>${SERIE.einzeln[art]} ${SERIE.einzeln.schluss}</p>`;
  }

  _folgen(s) {
    const { ctx } = this;
    const alle = s.folgen || [];
    const art = SERIE.abschnitt[s.art] ? s.art : 'hoerspiel';
    if (!alle.length) {
      return html`<div class="leer se-leer" data-leer="serie"><p class="et">${fuellen(SERIE.leer.satz, { name: s.name })}</p>
        <div class="btns"><a class="btn primary" href="#hinzufuegen">${SERIE.leer.knopf}</a></div></div>`;
    }
    const ordnen = this.ordnen && ctx.admin && alle.length > 1;
    const term = ordnen ? '' : this.sterm.trim();
    const treffer = alle.map((x, i) => ({ x, i })).filter(({ x }) => !term || norm(x.anzeige || x.name).includes(norm(term)));
    const rest = treffer.length - this.gezeigt;
    return html`<div class="se-kopfzeile"><h3 class="se-abschnitt">${SERIE.abschnitt[art]}</h3>
        ${ordnen ? html`<button type="button" class="btn" data-fertig @click=${() => this.reihenfolgeEnde()}>${SERIE.reihenfolge.fertig}</button>` : nothing}</div>
      ${alle.length > SICHTBAR && !ordnen ? html`<label class="sr" for="se-suche">${SERIE.suchen.label}</label>
        <input id="se-suche" class="se-sfeld" type="search" autocomplete="off" placeholder=${SERIE.suchen.platzhalter} .value=${this.sterm}
          @input=${(e) => { this.sterm = e.target.value; this.gezeigt = SICHTBAR; ctx.neuZeichnen(); }}>` : nothing}
      ${treffer.length ? html`<div class="se-karte" data-liste="folgen">${ctx.layout === 'seite' && !ordnen ? html`<div class="se-spalten" aria-hidden="true"><span class="c-nr">${SERIE.spalten.nr}</span><span>${SERIE.spalten.titel}</span><span class="c-dauer">${SERIE.spalten.dauer}</span><span></span></div>` : nothing}${repeat(treffer.slice(0, this.gezeigt), ({ x }) => x.name, ({ x, i }) => this._zeile(x, i, alle.length, ordnen))}</div>
          ${rest > 0 ? html`<div class="btns se-mehr"><button type="button" class="btn" data-mehr @click=${() => { this.gezeigt += SICHTBAR; ctx.neuZeichnen(); }}>${fuellen(SERIE.mehr_laden, { anzahl: Math.min(rest, SICHTBAR) })}</button></div>` : nothing}`
        : ctx.leer('suche', 'sucheOhneTreffer', { werte: { suchwort: term }, aktion: () => { this.sterm = ''; ctx.neuZeichnen(); } })}`;
  }

  _zeile(x, i, n, ordnen) {
    const titel = x.anzeige || x.name;
    const meta = folgenMeta(x);
    const teile = folgenMetaTeile(x);
    const h = x.hoerstelle;
    let fort = nothing;
    if (h?.fertig) fort = html`<span class="ls se-ok">${ic('check', 16)} ${ZEILE.fertig}</span>`;
    else if (h && typeof h.position_s === 'number' && h.position_s > 1 && x.dauer_s > 0) {
      const p = Math.round(Math.min(1, h.position_s / x.dauer_s) * 100);
      fort = html`<span class="pbar" role="progressbar" aria-label=${ZEILE.fortschritt} aria-valuemin="0" aria-valuemax="100" aria-valuenow=${p}><i style=${`width:${p}%`}></i></span>
        <span class="ls">${fuellen(ZEILE.rest, { dauer: uhr(Math.max(0, x.dauer_s - h.position_s)) })}</span>`;
    }
    return html`<div class="frow se-zeile" data-folge=${x.name}>
      <span class="se-num" aria-hidden="true">${x.nummer ?? i + 1}</span>
      <div class="grow"><span class="nm">${titel}</span>${meta ? html`<span class="muted se-meta-voll">${meta}</span>` : nothing}${teile.kapitel ? html`<span class="muted se-meta-kap">${teile.kapitel}</span>` : nothing}${fort}${folgenChips(this.id, x)}</div>
      <span class="se-dauer" aria-hidden="true">${teile.dauer}</span>
      ${ordnen
        ? html`<button type="button" class="iconbtn se-ord" data-auf ?disabled=${i === 0} aria-label=${fuellen(SERIE.reihenfolge.hoch, { titel })} @click=${() => this.bewege(i, -1)}>▲</button>
          <button type="button" class="iconbtn se-ord" data-ab ?disabled=${i === n - 1} aria-label=${fuellen(SERIE.reihenfolge.runter, { titel })} @click=${() => this.bewege(i, 1)}>▼</button>`
        : html`<button type="button" class="iconbtn se-more" data-menue-folge aria-haspopup="dialog" aria-label=${fuellen(SERIE.mehr_zu, { titel })} @click=${(e) => this.folgeMenue(x, e.currentTarget)}>${ic('more', 22)}</button>`}</div>`;
  }
}

export const erzeuge = (ctx) => new SerieSeite(ctx);

export const stil = () => css`
  .se-leiste { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 48px; }
  .se-mehr-knopf { margin-right: -8px; } /* ohne Fläche wie im Prototyp (Kopf), die Zeilen haben die getönte Fläche (X25) */
  .se-more { min-width: 44px; min-height: 44px; width: 44px; height: 44px; border-radius: 12px; border: 0; background: var(--primary-soft); color: var(--primary-ink); flex: none; margin-left: 8px; }
  .se-more svg, .se-mehr-knopf svg { fill: currentColor; }
  .se-hero { display: grid; justify-items: center; text-align: center; gap: 8px; margin: 4px 0 16px; }
  .se-htxt { display: grid; gap: 2px; justify-items: center; min-width: 0; max-width: 100%; }
  .se-htxt h2 { margin: 4px 0 2px; font-size: 24px; line-height: 1.25; overflow-wrap: anywhere; outline: none; }
  .cover.se-xl { width: min(46vw, 190px); font-size: 80px; border-radius: var(--r-card); }
  .app:not([data-layout="unten"]) .se-hero { grid-template-columns: 220px minmax(0, 1fr); justify-items: start; text-align: left; gap: 8px 28px; align-items: center; }
  .app:not([data-layout="unten"]) .se-htxt { justify-items: start; }
  .app:not([data-layout="unten"]) .cover.se-xl { width: 220px; }
  .se-meta-kap, .se-dauer, .se-spalten { display: none; }

  /* Computer (ab 1100 px): großer Kopf wie ein Album bei Apple Music, Folgenliste mit Spalten Nr., Titel, Dauer, „⋯“ */
  .app[data-layout="seite"] .se-leiste { min-height: 44px; margin-top: -4px; }
  .app[data-layout="seite"] .se-hero { grid-template-columns: 248px minmax(0, 1fr); gap: 8px 40px; align-items: end; margin: 8px 0 28px; padding: 32px; border-radius: 28px; background: var(--card); }
  @supports (background: color-mix(in srgb, red 10%, blue)) {
    .app[data-layout="seite"] .se-hero { background: linear-gradient(180deg, color-mix(in srgb, var(--primary) 14%, var(--card)), var(--card) 85%); }
  }
  .app[data-layout="seite"] .cover.se-xl { width: 248px; font-size: 96px; border-radius: 18px; box-shadow: 0 8px 28px var(--shadow); }
  .app[data-layout="seite"] .se-htxt { gap: 6px; align-self: end; }
  .app[data-layout="seite"] .se-htxt h2 { font-size: 40px; font-weight: 700; letter-spacing: -0.8px; line-height: 1.12; margin: 0 0 4px; }
  .app[data-layout="seite"] .se-htxt .muted { font-size: 16px; }
  .se-aktionen { margin-top: 14px; }
  .se-aktionen .btn svg { fill: currentColor; }
  .app[data-layout="seite"] .se-kopfzeile { margin-top: 12px; }
  .app[data-layout="seite"] .se-abschnitt { font-size: 22px; font-weight: 700; letter-spacing: -0.2px; }
  .app[data-layout="seite"] .se-karte { padding: 0; overflow: hidden; border-radius: 20px; box-shadow: 0 1px 4px var(--shadow); }
  .app[data-layout="seite"] .se-spalten, .app[data-layout="seite"] .se-zeile { display: grid; grid-template-columns: 56px minmax(0, 1fr) 96px 44px; column-gap: 12px; align-items: center; padding-inline: 20px; }
  .app[data-layout="seite"] .se-spalten { min-height: 48px; font-size: 13px; font-weight: 500; letter-spacing: 0.4px; text-transform: uppercase; color: var(--text2); border-bottom: 1px solid var(--divider); }
  .app[data-layout="seite"] .se-spalten .c-nr { text-align: center; }
  .app[data-layout="seite"] .se-spalten .c-dauer, .app[data-layout="seite"] .se-dauer { text-align: right; }
  .app[data-layout="seite"] .se-zeile { min-height: 64px; }
  .app[data-layout="seite"] .se-spalten + .se-zeile { border-top: 0; }
  .app[data-layout="seite"] .se-zeile:hover { background: var(--primary-soft); }
  .app[data-layout="seite"] .se-zeile .se-num { width: auto; font-size: 15px; font-variant-numeric: tabular-nums; }
  .app[data-layout="seite"] .se-dauer { display: block; color: var(--text2); font-size: 15px; font-variant-numeric: tabular-nums; }
  .app[data-layout="seite"] .se-meta-voll { display: none; }
  .app[data-layout="seite"] .se-meta-kap { display: block; }
  .app[data-layout="seite"] .se-zeile .se-more { margin-left: 0; }
  .app[data-layout="seite"] .se-zeile:hover .se-more { background: var(--card); }
  .se-grund { display: block; margin-top: 2px; }
  .note .se-grund:first-of-type { margin-top: 4px; }
  .se-einzeln { background: var(--card); border-radius: var(--r-card); box-shadow: 0 1px 3px var(--shadow); padding: 16px; margin: 8px 0 16px; }
  .se-kopfzeile { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 8px 0 4px; }
  .se-abschnitt { font-size: 20px; font-weight: 500; margin: 8px 0; }
  .se-karte { background: var(--card); border-radius: var(--r-card); box-shadow: 0 1px 3px var(--shadow); padding: 4px 16px; margin: 4px 0 8px; min-width: 0; }
  .se-sfeld { width: 100%; min-height: 48px; border-radius: 24px; border: 1px solid var(--line); background: var(--card); color: var(--text); padding: 0 16px; margin: 4px 0 8px; }
  .se-zeile { padding: 8px 0; min-height: 64px; }
  .se-zeile .grow { gap: 1px; }
  .se-num { width: 28px; text-align: center; color: var(--text2); font-weight: 500; flex: none; }
  .se-ok { color: var(--ok); display: flex; align-items: center; gap: 4px; }
  .se-ok svg { fill: currentColor; flex: none; }
  .se-ord { min-width: 44px; min-height: 44px; width: 44px; height: 44px; border-radius: 12px; border: 0; background: var(--primary-soft); color: var(--primary-ink); font-size: 16px; flex: none; }
  .se-ord:disabled { opacity: 0.4; cursor: default; }
  .se-mehr { justify-content: center; margin: 12px 0; }
  .se-leer .btns { justify-content: center; }
  .se-stack { display: grid; gap: 8px; }
  .se-apart { margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--divider); }
  .se-apart .btn.link { background: none; border: 0; padding: 0 8px; min-height: 44px; color: var(--danger); }
  .se-opt { width: 100%; min-height: 48px; border: 1px solid var(--line); border-radius: var(--r-card); background: var(--card); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; text-align: left; }
  .se-opt[aria-checked="true"] { background: var(--primary-soft); border-color: var(--primary-ink); }
  .se-opt svg { width: 22px; height: 22px; fill: var(--primary-ink); }
  .se-feld { display: grid; gap: 6px; margin: 8px 0; }
  .se-feld label { font-weight: 500; }
  .se-feld input { min-height: 48px; border-radius: 12px; border: 1px solid var(--line); background: var(--card); color: var(--text); padding: 0 14px; width: 100%; }
  .se-fehl { margin: 0; color: var(--danger); font-weight: 500; }
  .se-wahl { display: grid; margin-top: 4px; }
  .se-wrow { width: 100%; min-height: 64px; display: flex; align-items: center; gap: 12px; padding: 8px 0; border: 0; border-top: 1px solid var(--divider); background: none; text-align: left; color: inherit; }
  .se-wrow:first-child { border-top: 0; }
  .se-wrow:active { background: var(--primary-soft); }
  .se-wrow .grow { flex: 1; min-width: 0; display: grid; overflow-wrap: anywhere; }
  .se-wrow .nm { font-weight: 500; }
  .se-chev { flex: none; width: 24px; height: 24px; display: grid; place-items: center; color: var(--text2); }
  .se-chev svg { width: 24px; height: 24px; fill: currentColor; display: block; }
  .se-wlaedt, .se-wleer { padding: 12px 4px; }
`;

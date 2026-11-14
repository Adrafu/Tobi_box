/* Hinzufügen (Design 5.6, 5.6a, 7.3; Paket A11a): Seite `#hinzufuegen`, Blatt „Was lädst du hoch?“, Vorschau, Hochladen mit Fortschritt.
 *
 * Aufbau
 *   - `HinzModell` (je App einmal, `modell(ctx)`) hält die Auswahl (`w`), die Aufträge (`eintraege`, so heißen sie unter „Zuletzt hinzugefügt“) und
 *     die Warteschlange `Hochlader` (seiten/upload.js). Es lebt über Seitenwechsel hinweg: der Upload läuft weiter, wenn man in der Bibliothek stöbert.
 *   - `HinzSeite` ist die Seite: „‹ Bibliothek“, „Dateien wählen“, am Computer „Ordner vom Computer wählen“ und die Ziehfläche, darunter „Zuletzt hinzugefügt“.
 *   - Das Blatt (natives `<dialog>` der App, `ctx.oeffneBlatt`) hat drei Schritte: Kacheln → Vorschau (a, b, c, e) und, bei „Zu Vorhandenem“, davor
 *     „Wohin soll es?“. „Abbrechen“ steht oben rechts (`kopfKnopf`), kein „×“. Der Fokus geht beim Wechsel auf die Überschrift.
 *   - Einstiege: Seite (Knöpfe, Ziehen), „+“ der Bibliothek am Handy (`plusKlick`: gleich die Dateiauswahl, N26), Menü „Dateien in diesen Eintrag“
 *     der Serienseite (`dateienInEintrag`: gleich die Vorschau b).
 *
 * A11b (Eingang-Anbindung): „Zuletzt hinzugefügt“ ist **eine** Liste (`HinzSeite.zeilen()`, neueste zuerst): die Aufträge dieses Geräts (`modell.zeilen()`,
 * `art: 'upload'`) und alle Einträge der letzten 24 Stunden aus `eingang/list` (`art: 'eingang'`; auch vom NAS und von anderen Geräten, `ctx.eingang()`).
 * Ein Auftrag und der Eintrag, den er im Eingang angelegt hat, sind **eine** Zeile: der Auftrag „besitzt“ den Eintrag (`gehoertZu`: Gruppen-Ordner
 * „Upload <8 Zeichen>“ oder Dateiname), der Eintrag wird dann nicht noch einmal gezeigt. Nach einem Neuladen gibt es nur noch die Einträge aus `eingang/list`;
 * Uploads, die mitten im Hochladen stehen geblieben sind, merkt sich das Gerät (`localStorage`, nur Namen und Wunsch) und zeigt sie als
 * „Unterbrochen. Wähle die Datei noch einmal.“ (Design 7.3 Punkt 8). Band und Punkt am Reiter zählen die Aufträge über `ctx.lokaleUploads(n, namen)`.
 * Das Ergebnis des eigenen Hochladens kommt aus `eingang/list` (Abfrage alle paar Sekunden, nur solange etwas einsortiert wird): `a.eingang` =
 * `{ art: 'fertig' | 'pruefen' | 'fehler' | 'fehlt' | 'lange', eintraege, ergebnis, hinweise }`; die Texte dazu baut `ergebnisText`, die Gründe
 * `gruende`. Ohne Fähigkeit `einsortier_wunsch` gibt es keine Wahl: die Dateien gehen gleich hoch (alte Felder `serie_id`, `gruppe`).
 */
import { html, nothing, css, ic, cover, untertitel } from '../bausteine.js';
import { HINZU, KACHELN, SEITE, SERIE, TOBIES, GRUENDE, HINWEISE, FEHLER, ZEILE, EINGANG, fuellen, fehlerText } from '../texte.js';
import { Zielwahl } from './tobies.js';
import { FENSTER_MS, eintragGruende, ergebnisGruende, hinweisGruppen, daraus as eingangDaraus } from '../eingang.js';
import {
  Hochlader, GRUPPE_MAX, ZUSTAENDE_NEU_WAEHLEN, neueId, pruefeDateien, sortiereNatuerlich, nameVorschlag, artVorschlag, liesAngaben, titelAusDateiname,
  dateienAusDrop, gesamtProzent, dateiProzent, aktuelleDatei, phaseVon, dateiFehlerText, grenzeText,
} from './upload.js';

export { phaseVon, gesamtProzent };

const ARTEN_WAHL = ['alle', 'hoerspiel', 'hoerbuch', 'musik', 'geschichte'];
const ABFRAGE_MS = [2000, 3000]; // erste Abfrage nach 2 s, danach alle 3 s; nach 20 Abfragen alle 10 s
const LANGE_MS = 30 * 60 * 1000; // so lange wartet der Eingang auf eine Gruppe (Vertrag 14.4); danach „Das dauert länger als sonst“
const ANZEIGE_NAMEN = 2; // „3 Dateien: 01 Der Hafen.mp3, 02 Die Karte.mp3 …“

/* ------------------------------------------------------------------ Symbole (Design 5.6: Bücherregal, Regal mit Plus, Note, Zauberstab) */

const SYMBOLE = {
  neu: 'M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z',
  zu_vorhandenem: 'M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9h-4v4h-2v-4H9V9h4V5h2v4h4v2z',
  einzeln: 'M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z',
  sortier_du: 'M7.5 5.6L10 7 8.6 4.5 10 2 7.5 3.4 5 2l1.4 2.5L5 7zm12 9.8L17 14l1.4 2.5L17 19l2.5-1.4L22 19l-1.4-2.5L22 14zM22 2l-2.5 1.4L17 2l1.4 2.5L17 7l2.5-1.4L22 7l-1.4-2.5zm-7.63 5.29a.9959.9959 0 0 0-1.41 0L1.29 18.96c-.39.39-.39 1.02 0 1.41l2.34 2.34c.39.39 1.02.39 1.41 0L16.7 11.05c.39-.39.39-1.02 0-1.41l-2.33-2.35zm-1.03 5.49l-2.12-2.12 2.44-2.44 2.12 2.12-2.44 2.44z',
  datei: 'M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z',
  ordner: 'M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z',
  haken: 'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
};
const sym = (n, gr = 24) => html`<svg viewBox="0 0 24 24" width=${gr} height=${gr} aria-hidden="true" focusable="false"><path d=${SYMBOLE[n]}></path></svg>`;

/* ------------------------------------------------------------------ Umgebung */

const medien = (abfrage) => { try { return !!window.matchMedia?.(abfrage).matches; } catch { return false; } };
/* Zeiger: am Handy grob (`coarse`), am Computer fein (`fine`). Ohne `matchMedia` (Tests) gilt: kein Zeiger bekannt, die Seite zeigt nur „Dateien wählen“. */
export const zeigerGrob = () => medien('(pointer: coarse)');
export const zeigerFein = () => medien('(pointer: fine)');

/* ------------------------------------------------------------------ reine Funktionen: Sätze der Vorschau (Design 7.3) */

const dateienText = (n) => fuellen(n === 1 ? HINZU.dateien.eins : HINZU.dateien.mehr, { anzahl: n });
const bereich = (wort, ab, n) => (n === 1 ? `${wort} ${ab}` : `${wort} ${ab}–${ab + n - 1}`);
const artOk = (art) => (HINZU.satz.nummer[art] ? art : 'hoerspiel');

/* „neues Hörbuch „Kapitän Knopf“, Kapitel 1–3“ (ein Kapitel: „… (ein Kapitel)“). */
export function neuTeil(art, name, n) {
  const a = artOk(art);
  const T = HINZU.satz;
  return a === 'hoerbuch' && n === 1 ? fuellen(T.neu.hoerbuch_eins, { name }) : fuellen(T.neu[a], { name, nummern: bereich(T.nummer[a], 1, n) });
}

/* Was „Sortier du“ vermutet: ohne Album und bei einer Datei ein einzelner Titel, sonst etwas Neues. */
export function vermutung(w) {
  const n = w.dateien.length;
  const art = artOk(w.artVorschlag);
  if (!w.hatAlbum && n === 1) return fuellen(HINZU.satz.vermutung_einzeln[art], { name: w.titelRoh[0] || '…' });
  return neuTeil(art, (w.nameVorschlag || '').trim() || '…', n);
}

/* Der Satz der Vorschau je Weg (a, b, c, e) und Stand der Eingaben `w`. */
export function satzFuer(w) {
  const n = w.dateien.length;
  const d = dateienText(n);
  const T = HINZU.satz;
  if (w.ziel === 'neu') return fuellen(T.neu_satz, { dateien: d, neu: neuTeil(w.artNeu, (w.name || '').trim() || '…', n) });
  if (w.ziel === 'ergaenzen') {
    if (!w.serie) return fuellen(T.dazu_offen, { dateien: d });
    const art = artOk(w.serie.art);
    const wort = T.dazu_wort[art];
    const ab = (w.serie.anzahl_folgen ?? 0) + 1;
    return fuellen(n === 1 ? T.dazu_eins : T.dazu, { dateien: d, anzahl: n, wort: n === 1 ? wort.eins : wort.mehr, name: w.serie.name, nummern: bereich(wort.eins, ab, n) });
  }
  if (w.ziel === 'einzeln') {
    const wort = T.einzeln_wort[artOk(w.artEinzeln)];
    const namen = n <= 3 ? `: ${w.titel.slice(0, n).map((x) => `„${(x || '').trim() || '…'}“`).join(', ')}` : '';
    return fuellen(T.einzeln, { dateien: d, anzahl: n, wort: n === 1 ? wort.eins : wort.mehr, namen });
  }
  if (w.ziel === 'auto') return fuellen(T.sortieren, { dateien: d, vermutung: vermutung(w) });
  return '';
}

/* Zeilen „Kapitel 1 · Der Hafen“ unter dem Satz (höchstens vier) und „… und 4 weitere“. */
export function vorschauZeilen(w) {
  const n = w.dateien.length;
  let wort; let ab = 1;
  if (w.ziel === 'neu') wort = HINZU.satz.nummer[artOk(w.artNeu)];
  else if (w.ziel === 'ergaenzen' && w.serie) { wort = HINZU.satz.dazu_wort[artOk(w.serie.art)].eins; ab = (w.serie.anzahl_folgen ?? 0) + 1; } else return { zeilen: [], weitere: 0 };
  const zeilen = w.titelRoh.slice(0, Math.min(4, n)).map((t, i) => `${wort} ${ab + i} · ${t}`);
  return { zeilen, weitere: Math.max(0, n - 4) };
}

const eindeutig = (liste) => [...new Set(liste)];

/* Die Marke einer Karte („fertig“, „bitte ansehen“, „geht nicht“ …): Farbe und Wort, nie nur die Farbe. */
const marke = (art, text) => html`<span class=${`hz-marke ${art}`} data-marke=${art}>${art === 'ok' ? sym('haken', 18) : nothing}${text}</span>`;

/* Wie das Hochladen im Backend ankommt (Design 7.3 Punkt 3, Vertrag 14.4). */
export function wunschFuer(w, gruppe = neueId()) {
  const n = w.dateien.length;
  const mehr = n > 1 ? { gruppe_anzahl: n } : {};
  if (w.ziel === 'neu') return { ziel: 'neu', art: w.artNeu, name: (w.name || '').trim(), gruppe, ...mehr };
  if (w.ziel === 'ergaenzen') return { ziel: 'ergaenzen', serie_id: w.serie.id, gruppe, ...mehr };
  if (w.ziel === 'einzeln') return { ziel: 'einzeln', art: w.artEinzeln };
  return { ziel: 'auto', ...(n > 1 ? { gruppe } : {}) };
}

/* ------------------------------------------------------------------ Ergebnis aus dem Eingang (für den eigenen Hochladen) */

const nameDesEintrags = (a) => {
  const ersten = (a.dateien.length ? a.dateien : a.abgelehnt || []).map((d) => d.name); // gezählt werden die Dateien, die hochgeladen werden
  const n = ersten.length;
  return fuellen(HINZU.titel_dateien, { dateien: dateienText(n), namen: ersten.slice(0, ANZEIGE_NAMEN).join(', ') + (n > ANZEIGE_NAMEN ? ' …' : '') });
};

/* Namen im Eingang, an denen ein Auftrag zu erkennen ist: der Gruppen-Ordner „Upload <8 Zeichen>“ und die Namen der einzelnen Dateien. */
export function eingangsNamen(a) {
  return { ordner: a.wunsch?.gruppe ? `Upload ${a.wunsch.gruppe.slice(0, 8)}` : null, dateien: a.dateien.map((d) => d.eingangName).filter(Boolean) };
}

const fertigEintrag = (e) => !!e.fertig_am || ['blockiert', 'teilweise', 'erledigt'].includes(e.status);

/* Gehört dieser Eintrag aus `eingang/list` zu diesem Auftrag? (Dann zeigt die Seite nur den Auftrag.) Nur Einträge, die über den Upload kamen:
 * ein Eintrag vom NAS mit zufällig demselben Dateinamen ist ein anderer. */
export function gehoertZu(a, e) {
  if (!e || e.quelle === 'nas') return false;
  const n = eingangsNamen(a);
  return (!!n.ordner && e.name === n.ordner) || n.dateien.includes(e.name);
}

/* Was sich das Gerät merkt (`localStorage`; jeder Zugriff in `try`, ohne Speicher geht alles weiter, nur ohne Merken). */
const SPEICHER_OFFEN = 'tobibox.hinzufuegen.offen'; // Aufträge, die beim Neuladen mitten im Hochladen waren
const SPEICHER_AUS = 'tobibox.hinzufuegen.erledigte_aus'; // „Erledigte ausblenden“ (Design 7.3 Punkt 5: nur dieses Gerät)
const speicherLies = (k) => { try { return window.localStorage?.getItem(k) ?? null; } catch { return null; } };
const speicherSchreibe = (k, v) => { try { if (v === null) window.localStorage?.removeItem(k); else window.localStorage?.setItem(k, v); } catch { /* ohne Speicher */ } };

/* Ordnet die Antwort von `eingang/list` einem Auftrag zu. Liefert `null`, solange der Eintrag fehlt oder noch einsortiert wird, sonst
 * { art, eintraege, ergebnis, hinweise }. */
export function eingangFuer(a, eintraege) {
  const n = eingangsNamen(a);
  const ordner = n.ordner ? eintraege.find((e) => e.name === n.ordner) : null;
  const einzeln = n.dateien.map((x) => eintraege.find((e) => e.name === x)).filter(Boolean);
  const treffer = ordner ? [ordner] : einzeln.length && einzeln.length === n.dateien.length ? einzeln : [];
  if (!treffer.length || !treffer.every(fertigEintrag)) return null;
  const ergebnis = treffer.flatMap((e) => e.ergebnis || []);
  const hinweise = treffer.flatMap((e) => e.hinweise || []);
  const angekommen = treffer.reduce((s, e) => s + (e.dateien || 0), 0);
  let art = 'fertig';
  if (hinweise.some((h) => h.code === 'gruppe_unvollstaendig')) art = 'fehlt';
  else if (!ergebnis.length && treffer.every((e) => e.status === 'blockiert')) art = 'fehler';
  else if (treffer.some((e) => e.pruefen || e.status === 'teilweise') || ergebnis.some((x) => x.pruefen)) art = 'pruefen';
  return { art, eintraege: treffer, ergebnis, hinweise, angekommen };
}

/* Gründe als Texte für Eltern (eindeutig). */
export function gruende(eingang) {
  const codes = eindeutig([...eingang.ergebnis.flatMap((x) => x.pruefen_gruende || []), ...eingang.hinweise.filter((h) => h.code !== 'gruppe_unvollstaendig').map((h) => h.code)]);
  const texte = codes.map((c) => (GRUENDE[c] ? GRUENDE[c] : HINWEISE[c] ? fuellen(HINWEISE[c]) : null)).filter(Boolean);
  return eindeutig(texte);
}

/* Gründe für „geht nicht“ (Hinweise des Eintrags, Design 7.3 Punkt 6). */
export function nichtGruende(eingang) {
  const texte = eingang.hinweise.map((h) => (HINWEISE[h.code] ? fuellen(HINWEISE[h.code]) : h.text)).filter(Boolean);
  return eindeutig(texte);
}

/* Was daraus geworden ist (Design 7.3 Punkt 4, 3a): „Hörbuch „Kapitän Knopf“ · 3 Kapitel“, „„Lange Serie“ · Folge 13–15“, „„Der Mond …“ · einzelnes Lied“.
 * `details` = Antworten von `serie/get` je `serie_id` (fehlt eine, steht nur der Name). */
export function ergebnisText(a) {
  const erg = a.eingang?.ergebnis || [];
  if (!erg.length) return '';
  const E = HINZU.ergebnis;
  const T = HINZU.satz;
  const ids = eindeutig(erg.map((x) => x.serie_id));
  const det = (id) => a.details?.[id] || null;
  if (ids.length === 1) {
    const s = det(ids[0]);
    const name = erg[0].serie_name || s?.name || '';
    const art = artOk(s?.art ?? a.wunsch?.art);
    if (!s) return fuellen(E.nur_name, { name });
    if (s.einzeln) return fuellen(E.einzeln, { name, wort: T.einzeln_wort[art].eins });
    if (erg.some((x) => x.serie_neu)) {
      const tracks = erg.reduce((sum, x) => sum + Math.max(1, x.tracks || 1), 0);
      const zahl = art === 'hoerbuch' ? tracks : erg.length;
      const paar = { hoerbuch: E.kapitel, musik: E.lieder, hoerspiel: E.folgen, geschichte: E.geschichten }[art];
      return fuellen(E[art], { name, anzahl: fuellen(zahl === 1 ? paar.eins : paar.mehr, { anzahl: zahl }) });
    }
    const k = erg.length;
    const wort = T.dazu_wort[art].eins;
    const folgen = s.folgen || [];
    const nummern = erg.map((x) => folgen.find((f) => f.name === x.folge)?.nummer);
    const ab = nummern.every((x) => Number.isInteger(x)) ? Math.min(...nummern) : Math.max(1, folgen.length - k + 1);
    return fuellen(E.dazu, { name, nummern: bereich(wort, ab, k) });
  }
  const alleEinzeln = ids.every((id) => det(id)?.einzeln);
  if (alleEinzeln) {
    const art = artOk(det(ids[0]).art);
    return fuellen(E.einzeln_mehr, { anzahl: ids.length, wort: T.einzeln_wort[art].mehr });
  }
  return fuellen(E.mehrere, { anzahl: ids.length, name: erg[0].serie_name || '' });
}

/* Die Art, die „Sortier du“ vorgeschlagen hat, als Hinweis (Design 7.3 3a; nur bei „Weiß nicht“). */
export function artHinweis(a) {
  if (a.wunsch && a.wunsch.ziel !== 'auto') return null;
  const erg = a.eingang?.ergebnis || [];
  const neu = erg.find((x) => x.serie_neu);
  const s = neu ? a.details?.[neu.serie_id] : null;
  return s?.art && ZEILE.art[s.art] ? fuellen(HINZU.art_vorgeschlagen, { art: ZEILE.art[s.art] }) : null;
}

/* ------------------------------------------------------------------ Auswahl „Wohin soll es?“ (die Zielwahl der Tobies, ohne Einzeltitel und Gute Nacht) */

class WohinWahl extends Zielwahl {
  constructor(ctx, onSerie) { super(ctx, () => {}); this.onSerie = onSerie; }

  lade() {
    const text = this.term.length >= 2 ? this.term : null;
    this._hole('serie', { sortierung: 'neu', limit: 30, ...(this.art === 'alle' ? {} : { art: this.art }), ...(text ? { text } : {}), filter: ['sammlung'] });
  }

  waehleSerie(s) { return this.onSerie(s); }

  render() {
    const T = TOBIES.wahl;
    return html`<div class="tb-wahl hz-wohin" data-zielwahl data-hz-wahl>
      <label class="sr" for="hz-suche">${HINZU.blatt.wohin_suchen}</label>
      <input id="hz-suche" class="tb-suche" type="search" placeholder=${HINZU.blatt.wohin_suchen} autocomplete="off" .value=${this.eingabe}
        @input=${(e) => this.tippe(e.target.value)} @keydown=${(e) => { if (e.key === 'Enter') { e.preventDefault(); clearTimeout(this._timer); this.term = this.eingabe.trim(); this.lade(); } }}>
      <div class="artrow" role="group" aria-label=${T.art_label}>${ARTEN_WAHL.map((a) => html`<button type="button" class="arttab" data-art=${a} aria-pressed=${this.art === a ? 'true' : 'false'} @click=${() => this.setzeArt(a)}>${T.arten[a]}</button>`)}</div>
      <div class="tb-ergebnis" aria-live="polite">${this._ergebnis()}</div>
    </div>`;
  }
}

/* ------------------------------------------------------------------ Modell */

const MODELLE = new WeakMap();
export function modell(ctx) {
  if (!MODELLE.has(ctx)) MODELLE.set(ctx, new HinzModell(ctx));
  return MODELLE.get(ctx);
}

class HinzModell {
  constructor(ctx) {
    this.ctx = ctx;
    this.eintraege = []; // Aufträge dieses Geräts, neueste zuerst
    this.w = null; // die Auswahl im offenen Blatt
    this.ueber = false; // etwas wird über die Ziehfläche gezogen
    this.abfrageMs = ABFRAGE_MS; // Tests setzen kürzere Zeiten
    this.langeMs = LANGE_MS;
    this.erledigteAus = speicherLies(SPEICHER_AUS) === '1'; // „Erledigte ausblenden“ gilt nur auf diesem Gerät
    this.bestaetigt = new Set(); // Einträge, bei denen jemand hier „Das ist richtig“ getippt hat (für Backends ohne Bibliothek, die `pruefen` nicht löschen)
    this.fokusId = null; // Eintrag, dessen Karte nach dem nächsten Zeichnen den Fokus bekommt
    this.lader = new Hochlader(ctx, {
      aenderung: () => { this._lokale(); ctx.neuZeichnen(); },
      fertig: (a) => this._nachUpload(a),
    });
    this._wiederherstellen();
  }

  /* ---- Merken über das Neuladen hinweg: Aufträge, die bei „wird hochgeladen“ oder „es fehlt eine Datei“ stehen, mit Namen und Wunsch (keine Dateien).
   * Nach dem Neuladen stehen die nicht fertigen Dateien auf „Unterbrochen. Wähle die Datei noch einmal.“ (Design 7.3 Punkt 8); die schon angekommenen
   * bleiben angekommen, ein Auftrag mit Gruppe sendet beim erneuten Wählen mit derselben `gruppe` weiter. Älter als 24 Stunden: vergessen. */
  _wiederherstellen() {
    let roh = [];
    try { roh = JSON.parse(speicherLies(SPEICHER_OFFEN) || '[]'); } catch { roh = []; }
    if (!Array.isArray(roh)) return;
    const jetzt = Date.now();
    for (const r of roh) {
      if (!r || !Array.isArray(r.dateien) || !(jetzt - Number(r.angelegt) <= FENSTER_MS)) continue;
      const dateien = r.dateien.map((d) => ({
        id: d.id || neueId(), datei: null, name: String(d.name ?? ''), groesse: Number(d.groesse) || 0, wunschName: d.wunschName ?? null,
        zustand: d.fertig ? 'fertig' : 'unterbrochen', gesendet: d.fertig ? Number(d.groesse) || 0 : 0, code: null, hinweis: null, eingangName: d.eingangName ?? null,
      }));
      if (!dateien.some((d) => d.zustand !== 'fertig')) continue;
      this.eintraege.push({
        id: r.id || neueId(), art: 'upload', wunsch: r.wunsch ?? null, abgelehnt: Array.isArray(r.abgelehnt) ? r.abgelehnt : [], angelegt: Number(r.angelegt), eingang: null, details: null, polls: 0,
        dateien, erledigt: true, laeuft: false, gestartet: true, abgebrochen: false, wiederhergestellt: true,
      });
    }
    this.eintraege.sort((x, y) => y.angelegt - x.angelegt);
  }

  _merkeOffene() {
    const offen = this.eintraege.filter((a) => a.dateien.length && ['wartet', 'hochladen', 'fehlt'].includes(phaseVon(a)));
    speicherSchreibe(SPEICHER_OFFEN, offen.length ? JSON.stringify(offen.map((a) => ({
      id: a.id, wunsch: a.wunsch, angelegt: a.angelegt, abgelehnt: (a.abgelehnt || []).map((x) => ({ name: x.name, code: x.code, groesse: x.groesse })),
      dateien: a.dateien.map((d) => ({ id: d.id, name: d.name, groesse: d.groesse, wunschName: d.wunschName, fertig: d.zustand === 'fertig', eingangName: d.eingangName })),
    }))) : null);
  }

  /* Band und Punkt am Reiter „Bibliothek“ zählen die Aufträge mit (`ctx.lokaleUploads`); die Namen sagen, welche Einträge im Eingang schon zu ihnen gehören,
   * damit nichts doppelt zählt. */
  _lokale() {
    const l = this.laufend;
    const namen = l.flatMap((a) => { const n = eingangsNamen(a); return [n.ordner, ...n.dateien].filter(Boolean); });
    try { this.ctx.lokaleUploads?.(l.length, namen); } catch { /* die Seite darf daran nicht scheitern */ }
    this._merkeOffene();
  }

  setzeErledigteAus(an) {
    this.erledigteAus = !!an;
    speicherSchreibe(SPEICHER_AUS, an ? '1' : null);
    this.ctx.neuZeichnen();
  }

  zeilen() { return this.eintraege.map((a) => ({ art: 'upload', id: a.id, auftrag: a })); }
  /* Aufträge, die noch laufen oder einsortiert werden (A11b: Band und Punkt am Reiter „Bibliothek“). */
  get laufend() { return this.eintraege.filter((a) => ['wartet', 'hochladen', 'sortieren'].includes(this.anzeigePhase(a))); }
  get wunschFaehig() { return this.ctx.faehig('einsortier_wunsch'); }

  /* ---- Dateiwahl: eine unsichtbare Eingabe, die die Seite kurz in ihre Wurzel hängt (der Klick muss im Tippen des Benutzers laufen, N26) */
  waehle({ ordner = false, mehrere = true, serie = null, fuerAuftrag = null } = {}) {
    const wurzel = this.ctx.wurzel;
    if (!wurzel || typeof document === 'undefined') return;
    this._eingabe?.remove();
    const eingabe = document.createElement('input');
    eingabe.type = 'file';
    eingabe.multiple = mehrere;
    if (ordner) { eingabe.setAttribute('webkitdirectory', ''); eingabe.webkitdirectory = true; }
    eingabe.setAttribute('data-hinz-eingabe', fuerAuftrag ? 'fehlende' : ordner ? 'ordner' : 'dateien');
    eingabe.setAttribute('aria-hidden', 'true');
    eingabe.tabIndex = -1;
    eingabe.style.cssText = 'position:fixed;left:-9999px;top:0;width:1px;height:1px;opacity:0;pointer-events:none';
    eingabe.addEventListener('change', () => {
      const dateien = Array.from(eingabe.files || []);
      eingabe.remove();
      if (this._eingabe === eingabe) this._eingabe = null;
      if (!dateien.length) return;
      if (fuerAuftrag) this.fehlendeDatei(fuerAuftrag, dateien[0]); else this.auswahl(dateien, { ordner, serie });
    });
    wurzel.appendChild(eingabe);
    this._eingabe = eingabe;
    eingabe.click();
  }

  /* Die Auswahl ist da (Dateiwahl oder Ziehen): prüfen, dann das Blatt öffnen (oder bei „Dateien in diesen Eintrag“ gleich die Vorschau b). */
  auswahl(dateien, { ordner = false, serie = null } = {}) {
    const ctx = this.ctx;
    const g = pruefeDateien(dateien, ctx.grenzen?.() || {}, { ordner });
    const gut = sortiereNatuerlich(g.gut);
    if (!gut.length && !g.fehler.length) return;
    if (gut.length > GRUPPE_MAX) { ctx.meldeFehler(fuellen(HINZU.blatt.zu_viele, { max: GRUPPE_MAX })); return; }
    if (!gut.length) { this._eintragNurFehler(g.fehler); return; }
    if (!this.wunschFaehig) { this.starte({ dateien: gut, abgelehnt: g.fehler, wunsch: gut.length > 1 || serie ? { ...(gut.length > 1 ? { gruppe: neueId() } : {}), ...(serie ? { serie_id: serie.id } : {}) } : null }); return; }
    const w = {
      schritt: 'kacheln', ziel: null, dateien: gut, abgelehnt: g.fehler, angaben: [], titelRoh: gut.map((d) => titelAusDateiname(d.name)),
      artNeu: 'hoerspiel', artEinzeln: 'musik', artVorschlag: 'hoerspiel', hatAlbum: false, nameVorschlag: nameVorschlag(gut), name: nameVorschlag(gut), nameManuell: false,
      artNeuManuell: false, artEinzelnManuell: false, titel: gut.slice(0, 3).map((d) => titelAusDateiname(d.name)), serie: null, vonSerie: false, wahl: null,
    };
    w.artNeu = artVorschlag(gut); w.artVorschlag = w.artNeu;
    if (serie) { w.ziel = 'ergaenzen'; w.serie = serie; w.vonSerie = true; w.schritt = 'vorschau'; }
    this.w = w;
    this._zeigeBlatt();
    this._angaben(w);
  }

  /* Angaben in den ersten Dateien (ID3 bei MP3) lesen und Vorschläge nachziehen, soweit der Benutzer noch nichts selbst eingegeben hat. */
  async _angaben(w) {
    const lesen = w.dateien.slice(0, 4).map((d) => liesAngaben(d));
    const angaben = await Promise.all(lesen);
    if (this.w !== w || !angaben.some(Boolean)) return;
    w.angaben = angaben;
    w.hatAlbum = !!(angaben[0]?.album || '').trim();
    w.titelRoh = w.titelRoh.map((t, i) => (angaben[i]?.titel || '').trim() || t);
    w.titel = w.titel.map((t, i) => (w.titelGeaendert?.[i] ? t : w.titelRoh[i]));
    w.nameVorschlag = nameVorschlag(w.dateien, angaben);
    w.artVorschlag = artVorschlag(w.dateien, angaben);
    if (!w.nameManuell) w.name = w.nameVorschlag;
    if (!w.artNeuManuell) w.artNeu = w.artVorschlag;
    if (!w.artEinzelnManuell && ['musik', 'geschichte'].includes(w.artVorschlag)) w.artEinzeln = w.artVorschlag;
    this.ctx.neuZeichnen();
  }

  _eintragNurFehler(fehler) {
    const a = { id: neueId(), art: 'upload', wunsch: null, dateien: [], abgelehnt: fehler, angelegt: Date.now(), erledigt: true, fokus: true };
    this.eintraege.unshift(a);
    this.ctx.navigiere('#hinzufuegen');
    this.ctx.neuZeichnen();
  }

  /* ---- Blatt */
  _zeigeBlatt() {
    const ctx = this.ctx;
    const w = this.w;
    const p = ctx.oeffneBlatt({
      titel: () => (w.schritt === 'kacheln' ? HINZU.blatt.titel : w.schritt === 'wohin' ? HINZU.blatt.wohin_titel : HINZU.blatt.vorschau_titel),
      inhalt: () => this._blattInhalt(w),
      knoepfe: () => this._blattKnoepfe(w),
      kopfKnopf: { label: HINZU.blatt.abbrechen },
      fokus: 'titel',
    });
    p.then((grund) => {
      if (this.w === w) { w.wahl?.zuruecksetzen?.(); this.w = null; }
      if (grund !== 'ersetzt' && grund !== 'route') setTimeout(() => ctx.wurzel?.querySelector('[data-dateien-waehlen]')?.focus?.({ preventScroll: true }), 0);
    });
  }

  schritt(w, schritt) {
    if (this.w !== w) return;
    w.schritt = schritt;
    this.ctx.neuZeichnen();
    this.ctx.blattFokus?.();
  }

  waehleZiel(z) {
    const w = this.w;
    if (!w) return;
    w.ziel = z;
    if (z === 'ergaenzen' && !w.serie) { this.zeigeWahl(); return; }
    this.schritt(w, 'vorschau');
  }

  zeigeWahl() {
    const w = this.w;
    if (!w) return;
    w.wahl = new WohinWahl(this.ctx, (s) => this.waehleSerie(s));
    w.wahl.start();
    this.schritt(w, 'wohin');
  }

  waehleSerie(s) {
    const w = this.w;
    if (!w) return;
    w.serie = { id: s.id, name: s.name, art: s.art ?? 'hoerspiel', anzahl_folgen: s.anzahl_folgen ?? 0, cover_stand: s.cover_stand ?? null, einzeln: !!s.einzeln };
    w.ziel = 'ergaenzen';
    this.schritt(w, 'vorschau');
  }

  aendern() {
    const w = this.w;
    if (w) this.schritt(w, 'kacheln'); // die Eingaben bleiben erhalten
  }

  /* „Hochladen“: Prüfungen (Design 7.3 Punkt 3), dann starten. Liefert `false`, wenn das Blatt offen bleiben soll. */
  hochladen() {
    const w = this.w;
    if (!w || w.schritt !== 'vorschau') return false;
    if (w.ziel === 'ergaenzen' && !w.serie) { this.ctx.meldeFehler(HINZU.blatt.kein_ziel); return false; }
    if (w.ziel === 'neu' && !(w.name || '').trim()) { this.ctx.meldeFehler(HINZU.blatt.kein_name); return false; }
    const wunsch = wunschFuer(w);
    const namen = w.ziel === 'einzeln' ? w.dateien.map((_, i) => (i < 3 ? (w.titel[i] || '').trim() || null : null)) : [];
    this.starte({ dateien: w.dateien, abgelehnt: w.abgelehnt, wunsch, namen });
    return undefined;
  }

  /* Einen Auftrag anlegen und einreihen; danach zeigt die Seite „Hinzufügen“ den Fortschritt. */
  starte({ dateien, abgelehnt = [], wunsch = null, namen = [] }) {
    const a = {
      id: neueId(), art: 'upload', wunsch, abgelehnt, angelegt: Date.now(), eingang: null, details: null, polls: 0,
      dateien: dateien.map((f, i) => ({ id: neueId(), datei: f, name: f.name, groesse: f.size, wunschName: namen[i] ?? null, zustand: 'wartet', gesendet: 0, code: null, hinweis: null, eingangName: null })),
    };
    this.eintraege.unshift(a);
    this.lader.einreihen(a);
    this._lokale();
    this.ctx.schliesseBlatt?.('knopf');
    if (!/^#hinzufuegen\b/.test(window.location.hash || '')) this.ctx.navigiere('#hinzufuegen');
    this.ctx.neuZeichnen();
    return a;
  }

  /* ---- Fehlende Datei noch einmal wählen */
  fehlendeDatei(a, datei) {
    const g = pruefeDateien([datei], this.ctx.grenzen?.() || {});
    if (g.fehler.length) { this.ctx.meldeFehler(fehlerText(g.fehler[0].code, { grenze: grenzeText(this.ctx.grenzen?.().upload_max_bytes), admin: this.ctx.admin })); return; }
    if (!g.gut.length) return;
    a.fokus = false;
    a.fortgesetzt = true;
    this.lader.nochEinmal(a, g.gut[0]);
  }

  abbrechen(a) { this.lader.abbrechen(a); }

  /* ---- Nach dem Hochladen: Ergebnis aus dem Eingang */
  _nachUpload(a) {
    this.ctx.eingangNeuLaden?.(); // der Eingang kennt die Datei jetzt: Band und Liste holen sich den neuen Stand
    if (phaseVon(a) !== 'sortieren') { this._merke(a); return; }
    a.fertigAm = Date.now();
    if (!this.ctx.faehig('eingang')) { a.eingang = { art: 'fertig', eintraege: [], ergebnis: [], hinweise: [], angekommen: a.dateien.length, ohne: true }; this._merke(a); return; }
    this._planeAbfrage(this.abfrageMs[0]);
  }

  _merke(a) { a.fokus = true; this._lokale(); this.ctx.ansage(this._ansageText(a)); this.ctx.neuZeichnen(); }

  _ansageText(a) {
    const p = this.anzeigePhase(a);
    const t = nameDesEintrags(a);
    return `${t}: ${HINZU.marke[p === 'fertig' ? 'fertig' : p === 'pruefen' ? 'ansehen' : p === 'abgebrochen' ? 'abgebrochen' : p === 'fehlt' ? 'fehlt' : 'geht_nicht']}`;
  }

  /* Phase für die Karte: Phase des Hochladens, danach die Antwort des Eingangs. */
  anzeigePhase(a) {
    const p = phaseVon(a);
    return p === 'sortieren' && a.eingang ? a.eingang.art : p;
  }

  _planeAbfrage(ms) {
    clearTimeout(this._abfrageT);
    this._abfrageT = setTimeout(() => this._abfrage(), ms);
  }

  async _abfrage() {
    this._abfrageT = null;
    if (this.ctx.wurzel?.host && this.ctx.wurzel.host.isConnected === false) return; // die App ist weg: nicht weiterfragen
    const offen = this.eintraege.filter((a) => phaseVon(a) === 'sortieren' && !a.eingang);
    if (!offen.length) return;
    let antwort = null;
    try { antwort = await this.ctx.api('tobibox/eingang/list', { filter: 'alle', limit: 100 }); } catch { /* die nächste Abfrage versucht es noch einmal */ }
    const liste = antwort?.eintraege || [];
    for (const a of offen) {
      a.polls += 1;
      const e = antwort ? eingangFuer(a, liste) : null;
      if (e) { a.eingang = e; this._ladeDetails(a); this._merke(a); this.ctx.eingangNeuLaden?.(); } else if (Date.now() - (a.fertigAm || 0) > this.langeMs) {
        a.eingang = { art: 'lange', eintraege: [], ergebnis: [], hinweise: [], angekommen: 0 };
        this._merke(a);
      }
    }
    if (this.eintraege.some((a) => phaseVon(a) === 'sortieren' && !a.eingang)) this._planeAbfrage(Math.max(...offen.map((a) => a.polls)) >= 20 ? 10000 : this.abfrageMs[1]);
    this._lokale();
    this.ctx.neuZeichnen();
  }

  /* Art und Zahl der Folgen der neuen Einträge, damit „Daraus ist geworden“ ein Satz wird. Fehler sind egal: dann steht nur der Name da. */
  async _ladeDetails(a) {
    const ids = eindeutig((a.eingang?.ergebnis || []).map((x) => x.serie_id)).slice(0, 3);
    a.details = a.details || {};
    await Promise.all(ids.map(async (id) => {
      try { const r = await this.ctx.api('tobibox/serie/get', { serie_id: id }); a.details[id] = r?.serie ?? r ?? null; } catch { /* nur der Name */ }
    }));
    this.ctx.neuZeichnen();
  }

  async richtig(a) {
    const ids = eindeutig((a.eingang?.ergebnis || []).filter((x) => x.pruefen).map((x) => x.serie_id));
    try {
      for (const id of ids) await this.ctx.api('tobibox/einsortierung/bestaetigen', { serie_id: id });
      a.eingang = { ...a.eingang, art: 'fertig', ergebnis: a.eingang.ergebnis.map((x) => ({ ...x, pruefen: false })) };
      a.fokus = true;
      this.ctx.melde(SERIE.ansehen.danke);
      this.ctx.eingangNeuLaden?.(); // das Band in der Bibliothek zählt den Eintrag nicht mehr als „bitte kurz ansehen“
    } catch (err) { this.ctx.meldeFehler(this.ctx.fehlerText(err?.code || 'unknown_error')); }
    this.ctx.neuZeichnen();
  }

  /* „Das ist richtig“ bei einem Eintrag aus dem Eingang (NAS, anderes Gerät, nach dem Neuladen): bestätigt die betroffenen Serien (Vertrag 28). */
  async richtigEintrag(e) {
    const ids = eindeutig((e.ergebnis || []).filter((x) => x.pruefen && x.serie_id).map((x) => x.serie_id));
    try {
      for (const id of ids) await this.ctx.api('tobibox/einsortierung/bestaetigen', { serie_id: id });
      this.bestaetigt.add(e.id);
      this.fokusId = e.id;
      this.ctx.melde(SERIE.ansehen.danke);
      this.ctx.eingangNeuLaden?.();
    } catch (err) { this.ctx.meldeFehler(this.ctx.fehlerText(err?.code || 'unknown_error')); }
    this.ctx.neuZeichnen();
  }

  /* ---- Blatt: Inhalt und Knöpfe je Schritt */
  _blattKnoepfe(w) {
    if (w.schritt === 'vorschau') {
      return [
        { label: HINZU.blatt.abbrechen, kind: 'link' },
        { label: HINZU.blatt.aendern, fn: () => { this.aendern(); return false; } },
        { label: HINZU.blatt.hochladen, kind: 'primary', fn: () => this.hochladen() },
      ];
    }
    if (w.schritt === 'wohin') return [{ label: HINZU.blatt.zurueck, fn: () => { this.schritt(w, 'kacheln'); return false; } }];
    return [];
  }

  _blattInhalt(w) {
    if (w.schritt === 'kacheln') return this._kacheln(w);
    if (w.schritt === 'wohin') return w.wahl ? w.wahl.render() : nothing;
    return this._vorschau(w);
  }

  _zuGross(w) {
    if (!w.abgelehnt.length) return nothing;
    const grenze = grenzeText(this.ctx.grenzen?.().upload_max_bytes);
    return html`${w.abgelehnt.map((x) => html`<div class="note warn" data-abgelehnt=${x.code}><strong>${fuellen(HINZU.blatt.nicht_hochgeladen, { datei: x.name })}</strong> ${fehlerText(x.code, { grenze, admin: this.ctx.admin })}</div>`)}`;
  }

  _kacheln(w) {
    const n = w.dateien.length;
    const zeile = fuellen(n === 1 ? HINZU.blatt.gewaehlt_eins : HINZU.blatt.gewaehlt_mehr, { anzahl: n, name: w.dateien[0].name });
    const karten = [['neu', 'neu'], ['zu_vorhandenem', 'ergaenzen'], ['einzeln', 'einzeln'], ['sortier_du', 'auto']];
    return html`<p class="hz-zeile muted" data-gewaehlt>${zeile}</p>${this._zuGross(w)}
      <div class="hz-kacheln" role="group" aria-label=${HINZU.blatt.titel} data-kacheln>
        ${karten.map(([k, ziel]) => html`<button type="button" class="hz-kachel" data-ziel=${ziel} data-kachel=${k} aria-pressed=${w.ziel === ziel ? 'true' : nothing} @click=${() => this.waehleZiel(ziel)}>
          <span class="hz-sym" aria-hidden="true">${sym(k, 32)}</span><span class="hz-t">${KACHELN[k].titel}</span><span class="hz-z">${KACHELN[k].zeile}</span><span class="sr">. ${KACHELN[k].satz}</span></button>`)}
      </div>`;
  }

  _artWahl(optionen, wert, onWahl, id) {
    return html`<div class="hz-feld"><span class="hz-label" id=${id}>${HINZU.blatt.welche_art}</span>
      <div class="hz-art" role="group" aria-labelledby=${id}>${optionen.map(([a, label]) => html`<button type="button" data-art-wahl=${a} aria-pressed=${wert === a ? 'true' : 'false'} @click=${() => onWahl(a)}>${label}</button>`)}</div></div>`;
  }

  _vorschau(w) {
    const n = w.dateien.length;
    const { zeilen, weitere } = vorschauZeilen(w);
    const liste = zeilen.length ? html`<div class="hz-vorliste" role="group" aria-label=${HINZU.blatt.was_wird} data-vorschau-liste>${zeilen.map((z) => html`<div>${z}</div>`)}${weitere ? html`<div class="muted">${fuellen(HINZU.blatt.weitere, { anzahl: weitere })}</div>` : nothing}</div>` : nothing;
    const zusammen = n > 1 && (w.ziel === 'neu' || w.ziel === 'ergaenzen') ? html`<p class="muted" data-zusammen>${fuellen(HINZU.blatt.zusammen, { anzahl: n })}</p>` : nothing;
    let eingaben = nothing;
    if (w.ziel === 'neu') {
      eingaben = html`<div class="hz-feld"><label class="hz-label" for="hz-name">${HINZU.blatt.name}</label>
          <input id="hz-name" type="text" maxlength="100" autocomplete="off" .value=${w.name} @input=${(e) => { w.name = e.target.value; w.nameManuell = true; this.ctx.neuZeichnen(); }}></div>
        ${this._artWahl(['hoerspiel', 'hoerbuch', 'musik', 'geschichte'].map((a) => [a, HINZU.art_neu[a]]), w.artNeu, (a) => { w.artNeu = a; w.artNeuManuell = true; this.ctx.neuZeichnen(); }, 'hz-l-art')}
        ${liste}`;
    } else if (w.ziel === 'ergaenzen') {
      const s = w.serie;
      eingaben = html`<div class="hz-feld"><span class="hz-label" id="hz-l-wohin">${HINZU.blatt.wohin_titel}</span>
          <button type="button" class="hz-wohin-knopf" data-wohin aria-labelledby="hz-l-wohin hz-wohin-text" @click=${() => this.zeigeWahl()}>
            ${s ? cover({ id: s.id, name: s.name, cover_stand: s.cover_stand }, 'sm') : nothing}
            <span class="hz-wohin-text" id="hz-wohin-text">${s ? html`<span class="nm">${s.name}</span><span class="muted">${untertitel({ ...s, einzeln: false }, { dauer: false })}</span>` : HINZU.blatt.wohin_waehlen}</span>
            <span class="muted hz-aendern" aria-hidden="true">${HINZU.blatt.aendern}</span></button></div>
        ${s ? liste : nothing}`;
    } else if (w.ziel === 'einzeln') {
      eingaben = html`${this._artWahl(['musik', 'geschichte', 'hoerspiel', 'hoerbuch'].map((a) => [a, HINZU.art_einzeln[a]]), w.artEinzeln, (a) => { w.artEinzeln = a; w.artEinzelnManuell = true; this.ctx.neuZeichnen(); }, 'hz-l-art')}
        ${w.dateien.slice(0, 3).map((_, i) => html`<div class="hz-feld"><label class="hz-label" for=${`hz-t${i}`}>${n > 1 ? fuellen(HINZU.blatt.name_von, { nr: i + 1 }) : HINZU.blatt.name}</label>
          <input id=${`hz-t${i}`} type="text" maxlength="100" autocomplete="off" data-titel=${i} .value=${w.titel[i] ?? ''}
            @input=${(e) => { w.titel[i] = e.target.value; (w.titelGeaendert ??= {})[i] = true; this.ctx.neuZeichnen(); }}></div>`)}
        ${n > 3 ? html`<p class="muted" data-uebrige>${fuellen(HINZU.blatt.uebrige, { anzahl: n - 3 })}</p>` : nothing}`;
    } else if (w.ziel === 'auto') {
      eingaben = html`<p data-sortier-du>${HINZU.blatt.sortier_du}</p>`;
    }
    return html`<div class="hz-satz" role="status" aria-live="polite" data-satz>${satzFuer(w)}</div>${this._zuGross(w)}${zusammen}${eingaben}`;
  }

  /* ---- Drag and drop auf der Seite */
  async ziehen(e) {
    e.preventDefault();
    this.ueber = false;
    this.ctx.neuZeichnen();
    const dateien = await dateienAusDrop(e.dataTransfer);
    if (dateien.length) this.auswahl(dateien, { ordner: dateien.some((d) => d.webkitRelativePath || (d.name && /\//.test(d.name))) });
  }
}

/* ------------------------------------------------------------------ Einstiege von anderen Seiten */

/* „+“ in der Bibliothek: am Handy (`pointer: coarse`) gleich die Dateiauswahl (N26). Liefert `true`, wenn der Tap hier erledigt ist. */
export function plusKlick(ctx, ereignis) {
  if (!zeigerGrob()) return false;
  ereignis?.preventDefault?.();
  modell(ctx).waehle();
  return true;
}

/* „Dateien in diesen Eintrag“ auf der Serienseite: Dateiauswahl, danach gleich die Vorschau von „Zu Vorhandenem“. `serie` = { id, name, art, anzahl_folgen, cover_stand }. */
export function dateienInEintrag(ctx, serie) {
  modell(ctx).waehle({ serie: { id: serie.id, name: serie.name, art: serie.art ?? 'hoerspiel', anzahl_folgen: serie.anzahl_folgen ?? serie.folgen?.length ?? 0, cover_stand: serie.cover_stand ?? null, einzeln: false } });
}

/* ------------------------------------------------------------------ Seite */

class HinzSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.m = modell(ctx);
  }

  /* Die Seite lädt beim Öffnen `eingang/list` neu (Design 7.3 Punkt 5); danach halten die Ereignisse des Themas `eingang` die Liste aktuell. */
  betreten() { this.ctx.eingangNeuLaden?.(); }

  nachRender(wurzel) {
    if (this.m.fokusId) { // nach „Das ist richtig“ bei einem Eintrag aus dem Eingang: die Karte, die den Knopf ersetzt hat
      const k = wurzel.querySelector(`[data-eintrag="${this.m.fokusId}"]`);
      if (k) { this.m.fokusId = null; k.focus({ preventScroll: true }); }
    }
    // Die Fertig-Karte erhält den Fokus, wenn sie die Fortschrittskarte ersetzt (Design 14; `aria-live` allein genügt Tastaturnutzern nicht)
    for (const a of this.m.eintraege) {
      if (!a.fokus) continue;
      const k = wurzel.querySelector(`[data-eintrag="${a.id}"]`);
      if (!k) continue;
      a.fokus = false;
      const aktiv = wurzel.activeElement;
      if (!aktiv || aktiv === wurzel.querySelector('main') || k.contains(aktiv) || !aktiv.closest?.('main')) k.focus({ preventScroll: true });
    }
  }

  /* ---- Seite */
  render() {
    const m = this.m;
    const fein = zeigerFein();
    const alle = this.zeilen();
    const erledigt = alle.filter((z) => this._erledigt(z)).length;
    const zeilen = m.erledigteAus ? alle.filter((z) => !this._erledigt(z)) : alle;
    return html`<a class="back" href="#bibliothek" data-zurueck>${SEITE.zurueck.bibliothek}</a><h2>${SEITE.seiten.hinzufuegen}</h2>
      <div class="hz-wahl" data-hinzufuegen>
        <button type="button" class="btn primary hz-gross" data-dateien-waehlen @click=${() => m.waehle()}>${sym('datei', 28)}${HINZU.dateien_waehlen}</button>
        ${fein ? html`<button type="button" class="btn hz-gross" data-ordner-waehlen @click=${() => m.waehle({ ordner: true })}>${sym('ordner', 28)}${HINZU.ordner_waehlen}</button>` : nothing}
      </div>
      ${fein ? html`<div class=${`hz-zieh${m.ueber ? ' ueber' : ''}`} data-ziehflaeche @dragenter=${(e) => { e.preventDefault(); m.ueber = true; this.ctx.neuZeichnen(); }}
        @dragover=${(e) => { e.preventDefault(); }} @dragleave=${(e) => { if (e.currentTarget === e.target) { m.ueber = false; this.ctx.neuZeichnen(); } }} @drop=${(e) => m.ziehen(e)}>
        ${sym('datei', 32)}<span>${m.ueber ? HINZU.ziehen_los : HINZU.ziehen}</span></div>` : nothing}
      ${alle.length ? html`<h3 class="hz-h" data-titel="zuletzt">${HINZU.zuletzt}</h3>
        ${erledigt || m.erledigteAus ? this._ausblenden(erledigt) : nothing}
        ${zeilen.length ? html`<div class="hz-liste" data-liste="zuletzt">${zeilen.map((z) => this.karte(z))}</div>` : nothing}` : nothing}`;
  }

  /* „Erledigte ausblenden“: ein Schalter, der sich nur dieses Gerät merkt (Design 7.3 Punkt 5; ehrlich gesagt). */
  _ausblenden(erledigt) {
    const m = this.m;
    const T = HINZU.erledigte;
    return html`<div class="hz-aus" data-erledigte>
      <button type="button" class="btn" data-erledigte-aus aria-pressed=${m.erledigteAus ? 'true' : 'false'} @click=${() => m.setzeErledigteAus(!m.erledigteAus)}>${m.erledigteAus ? T.zeigen : T.aus}</button>
      <span class="muted" data-erledigte-hinweis>${m.erledigteAus && erledigt ? `${fuellen(erledigt === 1 ? T.versteckt.eins : T.versteckt.mehr, { anzahl: erledigt })} ` : ''}${T.geraet}</span></div>`;
  }

  /* Die Zeilen von „Zuletzt hinzugefügt“, neueste zuerst: die Aufträge dieses Geräts und die Einträge der letzten 24 Stunden aus `eingang/list`, die zu
   * keinem Auftrag gehören (NAS, andere Geräte, nach dem Neuladen). Ein Auftrag und sein Eintrag im Eingang sind eine Zeile. */
  zeilen() {
    const m = this.m;
    const abl = this.ctx.eingang?.() ?? null;
    const liste = abl?.liste || [];
    const lokal = m.zeilen().filter((z) => {
      const a = z.auftrag;
      if (!a.wiederhergestellt || a.fortgesetzt) return true; // nach „Datei noch einmal wählen“ läuft der Auftrag wieder: er bleibt sichtbar
      const e = liste.map((x) => x.eintrag).filter((x) => gehoertZu(a, x));
      return !e.some(fertigEintrag); // der Eingang hat die Gruppe inzwischen selbst einsortiert (30 Minuten Ruhe): dann steht dort der Eintrag
    }).map((z) => ({ ...z, zeit: z.auftrag.angelegt }));
    const frei = liste.filter((x) => !lokal.some((z) => gehoertZu(z.auftrag, x.eintrag)))
      .map((x) => ({ art: 'eingang', id: x.eintrag.id, eintrag: x.eintrag, zustand: x.zustand === 'pruefen' && m.bestaetigt.has(x.eintrag.id) && x.eintrag.status !== 'teilweise' ? 'fertig' : x.zustand, zeit: x.zeit }));
    return [...lokal, ...frei].sort((x, y) => y.zeit - x.zeit);
  }

  /* Grund und betroffene Dateien: ein Satz je Grund, darunter die Namen („und N weitere“ ab der vierten Datei). */
  _gruppen(hinweise) {
    return hinweisGruppen(hinweise).map((g) => html`<div class="hz-gruppe" data-gruppe><span class="hz-grund" data-grund>${g.satz}</span>
      ${g.namen.length ? html`<ul class="hz-dateien" data-dateien>${g.namen.map((n) => html`<li data-datei>${n}</li>`)}${g.weitere ? html`<li data-weitere>${fuellen(EINGANG.daraus_weitere, { anzahl: g.weitere })}</li>` : nothing}</ul>` : nothing}</div>`);
  }

  _erledigt(z) { return z.art === 'upload' ? this.m.anzeigePhase(z.auftrag) === 'fertig' : z.zustand === 'fertig'; }

  /* Eine Zeile unter „Zuletzt hinzugefügt“: ein Auftrag dieses Geräts (`upload`) oder ein Eintrag aus dem Eingang (`eingang`). */
  karte(z) {
    if (z.art === 'eingang') return this._eingangKarte(z);
    if (z.art !== 'upload') return nothing;
    const a = z.auftrag;
    const p = this.m.anzeigePhase(a);
    const titel = nameDesEintrags(a);
    const kopf = html`<div class="hz-titel" data-titel-eintrag>${titel}</div>${a.dateien.length ? this._abgelehnt(a) : nothing}`;
    const marke = (art, text) => html`<span class=${`hz-marke ${art}`} data-marke=${art}>${art === 'ok' ? sym('haken', 18) : nothing}${text}</span>`;
    const rahmen = (klasse, inhalt, status = null) => html`<div class=${`hz-karte ${klasse}`} data-eintrag=${a.id} data-phase=${p} tabindex="-1" role=${status ?? nothing}>${kopf}${inhalt}</div>`;
    if (p === 'wartet') {
      return rahmen('', html`<div class="hz-zeile2">${marke('neutral', HINZU.wartet)}</div>
        <div class="hz-bleib" data-bildschirm>${HINZU.bildschirm}</div>
        <div class="btns"><button type="button" class="btn" data-abbrechen @click=${() => this.m.abbrechen(a)}>${HINZU.abbrechen}</button></div>`);
    }
    if (p === 'hochladen') return rahmen('', this._fortschritt(a));
    if (p === 'sortieren') return rahmen('', html`${this._schritte(a, 1)}<div class="hz-status" role="status" data-status>${HINZU.einsortiert}</div>`);
    if (p === 'lange') return rahmen('', html`${this._schritte(a, 1)}<div class="hz-status" role="status" data-status>${HINZU.einsortiert_lange}</div>`);
    if (p === 'abgebrochen') {
      const k = a.dateien.filter((d) => d.zustand === 'fertig').length;
      const text = k ? fuellen(HINZU.abgebrochen_teil, { angekommen: k, anzahl: a.dateien.length }) : HINZU.abgebrochen;
      return rahmen('', html`<div class="hz-zeile2">${marke('neutral', HINZU.marke.abgebrochen)}</div><div class="hz-text" data-status>${text}</div>`);
    }
    if (p === 'fertig') {
      const e = a.eingang;
      const erg = ergebnisText(a);
      const hinweis = artHinweis(a);
      const ids = eindeutig((e.ergebnis || []).map((x) => x.serie_id));
      const ziel = ids.length === 1 ? `#serie-${encodeURIComponent(ids[0])}` : '#bibliothek?sortierung=neu';
      return rahmen('fertig', html`<div class="hz-zeile2">${marke('ok', HINZU.marke.fertig)}</div>
        ${erg ? html`<div class="hz-text" data-ergebnis>${erg}</div>` : e.ohne ? html`<div class="hz-text" data-ergebnis>${HINZU.hochgeladen_ohne_eingang}</div>` : nothing}
        ${hinweis ? html`<div class="muted" data-art-hinweis>${hinweis}</div>` : nothing}
        ${ids.length || e.ohne ? html`<div class="btns"><a class="btn" href=${e.ohne ? '#bibliothek?sortierung=neu' : ziel} data-oeffnen>${HINZU.oeffnen}</a></div>` : nothing}`);
    }
    if (p === 'pruefen') {
      const e = a.eingang;
      const gr = gruende(e);
      const erg = ergebnisText(a);
      const ids = eindeutig(e.ergebnis.map((x) => x.serie_id));
      return html`<div class="hz-karte note warn" data-eintrag=${a.id} data-phase=${p} tabindex="-1">${kopf}
        <div class="hz-zeile2">${marke('warn', HINZU.marke.ansehen)}</div>
        <div><strong>${HINZU.ansehen_titel}</strong>${gr.length ? html` ${gr.map((t) => html`<span class="hz-grund" data-grund>${t}</span>`)}` : html` <span class="hz-grund" data-grund>${SERIE.ansehen.grund_sonst}</span>`}</div>
        ${erg ? html`<div data-ergebnis><strong>${fuellen(HINZU.daraus, { was: '' }).trim()}</strong> ${erg}</div>` : nothing}
        <div class="btns">${ids.length ? html`<a class="btn" href=${ids.length === 1 ? `#serie-${encodeURIComponent(ids[0])}` : '#bibliothek?sortierung=neu'} data-ansehen>${HINZU.ansehen}</a>` : nothing}
          <button type="button" class="btn" data-richtig @click=${() => this.m.richtig(a)}>${HINZU.richtig}</button></div></div>`;
    }
    if (p === 'fehlt') return this._fehlt(a, kopf, marke);
    return this._fehler(a, kopf, marke);
  }

  /* ---- Einträge aus dem Eingang (NAS: ohne die Leiste „Hochladen“ davor, Design 7.3 Punkt 10; anderes Gerät, nach dem Neuladen): wird einsortiert, fertig, bitte kurz ansehen, geht nicht, es fehlt noch eine Datei.
   * „Anders einsortieren“ gibt es hier nicht (Design 15, A11b: kommt mit A-3); „Das stimmt nicht“ führt zur Serienseite, dort steht die Auswahl (Design 5.3). */
  _eingangKarte(z) {
    const e = z.eintrag;
    const T = HINZU;
    const n = Math.max(1, Number(e.dateien) || 1);
    const generisch = !e.name || /^Upload [0-9a-f]{6,}$/i.test(e.name); // der Ordner, den die Seite für eine Gruppe anlegt, heißt nur „Upload ab12cd34“
    const titel = generisch ? dateienText(n) : fuellen(T.titel_dateien, { dateien: dateienText(n), namen: e.name });
    const q = T.quelle[e.quelle] ?? null;
    const kopf = html`<div class="hz-titel" data-titel-eintrag>${titel}</div>`;
    const zeile = (art, text) => html`<div class="hz-zeile2">${art ? marke(art, text) : nothing}${q ? html`<span class="hz-quelle" data-quelle=${e.quelle}>${q}</span>` : nothing}</div>`;
    const ids = eindeutig((e.ergebnis || []).map((x) => x.serie_id).filter(Boolean));
    const offene = eindeutig((e.ergebnis || []).filter((x) => x.pruefen && x.serie_id).map((x) => x.serie_id));
    const ziel = (liste) => (liste.length === 1 ? `#serie-${encodeURIComponent(liste[0])}` : '#bibliothek?sortierung=neu');
    const wasDaraus = eingangDaraus(e) || EINGANG.daraus_nichts;
    const rahmen = (klasse, phase, inhalt) => html`<div class=${`hz-karte ${klasse}`} data-eintrag=${e.id} data-phase=${phase} data-quelle=${e.quelle ?? nothing} tabindex="-1">${kopf}${inhalt}</div>`;
    if (z.zustand === 'laeuft') {
      return rahmen('', 'sortieren', html`${zeile(null)}${e.quelle === 'nas' ? nothing : this._schritte(null, 1)}<div class="hz-status" role="status" data-status>${T.einsortiert}</div>`);
    }
    if (z.zustand === 'fehler') {
      const gr = this._gruppen(e.hinweise);
      return rahmen('note err', 'fehler', html`${zeile('err', T.marke.geht_nicht)}
        <div data-geht-nicht><strong>${T.geht_nicht}</strong> ${gr.length ? gr : html` <span class="hz-grund" data-grund>${fuellen(T.geht_nicht_sonst)}</span>`}</div>`);
    }
    if (z.zustand === 'pruefen') {
      const fehlt = (e.hinweise || []).some((h) => h.code === 'gruppe_unvollstaendig');
      const teilweise = e.status === 'teilweise' && !fehlt;
      const saetze = teilweise ? ergebnisGruende(e) : eintragGruende(e);
      const rest = teilweise ? this._gruppen(e.hinweise) : [];
      const richtig = e.status !== 'teilweise' && offene.length > 0;
      const wohin = offene.length ? offene : ids;
      return rahmen('note warn', fehlt ? 'fehlt' : 'pruefen', html`${zeile('warn', fehlt ? T.marke.fehlt : T.marke.ansehen)}
        <div><strong>${T.ansehen_titel}</strong> ${(saetze.length || teilweise ? saetze : [EINGANG.grund_sonst]).map((t) => html` <span class="hz-grund" data-grund>${t}</span>`)}</div>
        <div data-daraus>${wasDaraus}</div>
        ${rest.length ? html`<div data-liegt-noch><strong>${T.liegt_noch}</strong> ${rest}</div>` : nothing}
        ${wohin.length || richtig ? html`<div class="btns">
          ${wohin.length ? html`<a class="btn" href=${ziel(wohin)} data-ansehen>${T.ansehen}</a>` : nothing}
          ${richtig ? html`<button type="button" class="btn" data-richtig @click=${() => this.m.richtigEintrag(e)}>${T.richtig}</button>` : nothing}
          ${wohin.length ? html`<a class="btn" href=${ziel(wohin)} data-stimmt-nicht>${SERIE.ansehen.stimmt_nicht}</a>` : nothing}</div>` : nothing}`);
    }
    return rahmen('fertig', 'fertig', html`${zeile('ok', T.marke.fertig)}
      <div class="hz-text" data-daraus>${wasDaraus}</div>
      ${ids.length ? html`<div class="btns"><a class="btn" href=${ziel(ids)} data-oeffnen>${T.oeffnen}</a></div>` : nothing}`);
  }

  /* Dateien, die nicht hochgeladen werden (zu groß, falsches Format), neben denen, die hochgeladen werden: die Warnung steht an der Karte (Design 5.6). */
  _abgelehnt(a) {
    const grenze = grenzeText(this.ctx.grenzen?.().upload_max_bytes);
    return html`${(a.abgelehnt || []).map((x) => html`<div class="hz-abgelehnt" data-abgelehnt=${x.code}><strong>${fuellen(HINZU.blatt.nicht_hochgeladen, { datei: x.name })}</strong> ${fehlerText(x.code, { grenze, admin: this.ctx.admin })}</div>`)}`;
  }

  _fortschritt(a) {
    const { nr, anzahl, datei } = aktuelleDatei(a);
    const gesamt = gesamtProzent(a);
    const prozent = datei ? dateiProzent(datei) : 0;
    const geprueft = datei?.zustand === 'pruefe' && anzahl === 1;
    const satz = geprueft ? HINZU.geprueft : anzahl > 1 ? fuellen(HINZU.hochladen_mehr, { nr, anzahl, prozent }) : fuellen(HINZU.hochladen_eins, { prozent });
    const gruppe = !!a.wunsch?.gruppe_anzahl;
    return html`<div class="hz-status" role="status" data-status>${satz}</div>
      ${anzahl > 1 && gruppe ? html`<div class="muted" data-zusammen>${fuellen(HINZU.warten_auf_alle, { anzahl })}</div>` : nothing}
      <div class="hz-balken" role="progressbar" aria-label=${fuellen(HINZU.fortschritt, { prozent: gesamt })} aria-valuemin="0" aria-valuemax="100" aria-valuenow=${gesamt} data-balken><i style=${`width:${gesamt}%`}></i></div>
      ${this._schritte(a, 0)}
      <div class="hz-bleib" data-bildschirm>${HINZU.bildschirm}</div>
      <div class="btns"><button type="button" class="btn" data-abbrechen @click=${() => this.m.abbrechen(a)}>${HINZU.abbrechen}</button></div>`;
  }

  /* Dreiteilige Leiste: Hochladen · Einsortieren · Fertig (`aktuell` = 0, 1 oder 2). */
  _schritte(a, aktuell) {
    const S = HINZU.schritte;
    return html`<ol class="hz-schritte" aria-label=${S.name} data-schritte>${[S.hochladen, S.einsortieren, S.fertig].map((t, i) => html`<li class=${i < aktuell ? 'done' : i === aktuell ? 'now' : ''} aria-current=${i === aktuell ? 'step' : nothing}><span>${t}</span></li>`)}</ol>`;
  }

  _dateiZeilen(a) {
    const grenzen = this.ctx.grenzen?.() || {};
    const admin = this.ctx.admin;
    const zeilen = [
      ...a.dateien.filter((d) => ['fehler', 'verbindung', 'unterbrochen', 'abgebrochen'].includes(d.zustand)).map((d) => ({ name: d.name, text: d.zustand === 'unterbrochen' ? HINZU.unterbrochen : dateiFehlerText(d, { grenzen, admin }) })),
      ...(a.dateien.length ? [] : (a.abgelehnt || []).map((x) => ({ name: x.name, text: fehlerText(x.code, { grenze: grenzeText(grenzen.upload_max_bytes), admin }) }))),
    ];
    const nurEine = zeilen.length === 1 && a.dateien.length + (a.abgelehnt || []).length === 1; // der Name steht schon im Titel der Karte
    return html`<ul class="hz-dateien" data-dateizeilen>${zeilen.map((z) => html`<li>${nurEine ? nothing : html`<span class="nm">${z.name}</span>`}<span data-dateifehler>${z.text}</span></li>`)}</ul>`;
  }

  _fehlt(a, kopf, marke) {
    const angekommen = a.dateien.filter((d) => d.zustand === 'fertig').length;
    const anzahl = a.wunsch?.gruppe_anzahl || a.dateien.length;
    const gruppe = !!a.wunsch?.gruppe_anzahl;
    return html`<div class="hz-karte note warn" data-eintrag=${a.id} data-phase="fehlt" tabindex="-1">${kopf}
      <div class="hz-zeile2">${marke('warn', HINZU.marke.fehlt)}</div>
      ${gruppe ? html`<div data-fehlt><strong>${HINZU.fehlt.titel}</strong> ${fuellen(HINZU.fehlt.text, { angekommen, anzahl })}</div>` : nothing}
      ${this._dateiZeilen(a)}
      <div class="btns"><button type="button" class="btn" data-fehlende @click=${() => this.m.waehle({ mehrere: false, fuerAuftrag: a })}>${HINZU.fehlt.knopf}</button></div></div>`;
  }

  _fehler(a, kopf, marke) {
    const e = a.eingang;
    const angekommen = a.dateien.filter((d) => d.zustand === 'fertig').length;
    const gr = e ? this._gruppen(e.hinweise) : [];
    const gruende = e && !gr.length ? nichtGruende(e) : [];
    return html`<div class="hz-karte note err" data-eintrag=${a.id} data-phase="fehler" tabindex="-1">${kopf}
      <div class="hz-zeile2">${marke('err', HINZU.marke.geht_nicht)}</div>
      <div data-geht-nicht><strong>${HINZU.geht_nicht}</strong> ${gr}${gruende.map((t) => html` <span class="hz-grund">${t}</span>`)}</div>
      ${e ? nothing : this._dateiZeilen(a)}
      ${!e && angekommen ? html`<div data-angekommen>${fuellen(HINZU.andere_angekommen, { angekommen })}</div>` : nothing}
      ${!e && a.dateien.some((d) => ZUSTAENDE_NEU_WAEHLEN.includes(d.zustand)) ? html`<div class="btns"><button type="button" class="btn" data-fehlende @click=${() => this.m.waehle({ mehrere: false, fuerAuftrag: a })}>${HINZU.fehlt.knopf}</button></div>` : nothing}</div>`;
  }
}

export const erzeuge = (ctx) => new HinzSeite(ctx);

export const stil = () => css`
  .hz-wahl { display: grid; gap: 12px; max-width: 560px; margin: 8px 0 16px; }
  .btn.hz-gross { min-height: 64px; width: 100%; font-size: 18px; border-radius: var(--r-big); gap: 12px; justify-content: flex-start; padding: 0 24px; }
  .btn.hz-gross svg { fill: currentColor; flex: none; }
  .hz-zieh { display: grid; justify-items: center; align-content: center; gap: 8px; min-height: 140px; max-width: 560px; margin: 0 0 24px; padding: 24px; text-align: center; color: var(--text2);
    border: 2px dashed var(--line); border-radius: var(--r-big); background: transparent; }
  .hz-zieh svg { fill: currentColor; }
  .hz-zieh.ueber { background: var(--primary-soft); border-color: var(--primary-ink); color: var(--primary-ink); }
  .hz-h { font-size: 18px; font-weight: 500; margin: 16px 0 8px; }
  .hz-liste { display: grid; gap: 12px; max-width: 760px; }
  .hz-karte { background: var(--card); border-radius: var(--r-card); box-shadow: 0 1px 3px var(--shadow); padding: 14px 16px; display: grid; gap: 8px; min-width: 0; outline-offset: 2px; }
  .hz-karte.note { margin: 0; box-shadow: none; }
  .hz-karte.fertig { border: 1px solid var(--line); }
  .hz-titel { font-weight: 500; overflow-wrap: anywhere; }
  .hz-quelle { font-size: 14px; color: var(--text); }
  .hz-aus { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; margin: 0 0 8px; }
  .hz-aus .muted { font-size: 14px; }
  .hz-zeile2 { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .hz-marke { display: inline-flex; align-items: center; gap: 4px; min-height: 24px; padding: 0 10px; border-radius: 12px; font-size: 13px; font-weight: 700; border: 1px solid var(--line); background: var(--card); color: var(--text); }
  .hz-marke svg { fill: currentColor; }
  .hz-marke.ok { background: var(--ok-bg); color: var(--ok); border-color: var(--ok); }
  .hz-marke.warn { background: var(--card); color: var(--warn); border-color: var(--warn); }
  .hz-marke.err { background: var(--card); color: var(--danger); border-color: var(--danger); }
  .hz-status { font-size: 16px; }
  .hz-text { overflow-wrap: anywhere; }
  .hz-grund { display: inline; overflow-wrap: anywhere; }
  .hz-gruppe { display: grid; gap: 4px; margin-top: 4px; min-width: 0; overflow-wrap: anywhere; }
  .hz-gruppe .hz-dateien { padding-left: 8px; }
  [data-liegt-noch] { display: grid; gap: 2px; min-width: 0; }
  .hz-abgelehnt { font-size: 15px; padding: 8px 12px; border-radius: 12px; background: var(--warn-bg); color: var(--warn); border: 1px solid var(--warn); overflow-wrap: anywhere; }
  .hz-bleib { font-weight: 500; }
  .hz-balken { height: 8px; background: var(--divider); border-radius: 4px; overflow: hidden; }
  .hz-balken i { display: block; height: 100%; background: var(--primary-ink); transition: width var(--dauer-mittel) linear; }
  .hz-schritte { display: flex; gap: 6px; list-style: none; margin: 0; padding: 0; }
  .hz-schritte li { flex: 1; min-width: 0; }
  .hz-schritte li::before { content: ""; display: block; height: 6px; border-radius: 3px; background: var(--divider); margin-bottom: 4px; }
  .hz-schritte li.done::before { background: var(--ok); }
  .hz-schritte li.now::before { background: var(--primary-ink); }
  .hz-schritte li span { font-size: 13px; color: var(--text2); }
  .hz-schritte li.now span { color: var(--text); font-weight: 700; }
  .hz-dateien { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  .hz-dateien li { display: grid; gap: 2px; overflow-wrap: anywhere; }
  .hz-dateien .nm { font-weight: 500; }
  @media (prefers-reduced-motion: reduce) { .hz-balken i { transition: none; } }

  /* Blatt „Was lädst du hoch?“ */
  .hz-zeile { margin: 0 0 8px; font-size: 15px; overflow-wrap: anywhere; }
  .hz-kacheln { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 8px; }
  .hz-kachel { display: grid; justify-items: center; align-content: center; gap: 6px; min-height: 132px; padding: 12px 6px; text-align: center; border: 1px solid var(--line); border-radius: var(--r-big); background: var(--card); color: var(--text); min-width: 0; }
  .hz-kachel:active { background: var(--primary-soft); }
  .hz-kachel .hz-sym { width: 56px; height: 56px; border-radius: 28px; background: var(--primary-soft); color: var(--primary-ink); display: grid; place-items: center; }
  .hz-kachel .hz-sym svg { fill: currentColor; }
  .hz-kachel .hz-t { font-weight: 500; font-size: 17px; line-height: 1.25; overflow-wrap: anywhere; }
  .hz-kachel .hz-z { font-size: 13px; color: var(--text2); line-height: 1.3; }
  @media (hover: hover) and (pointer: fine) { .hz-kachel:hover { background: var(--primary-soft); } }
  .hz-satz { background: var(--primary-soft); border-radius: var(--r-card); padding: 14px 16px; font-size: 18px; font-weight: 500; line-height: 1.4; margin: 4px 0 12px; overflow-wrap: anywhere; }
  .hz-feld { display: grid; gap: 6px; margin: 12px 0; }
  .hz-label { font-weight: 500; }
  .hz-feld input[type="text"] { min-height: 48px; border-radius: 12px; border: 1px solid var(--line); background: var(--card); color: var(--text); padding: 0 14px; width: 100%; }
  .hz-art { display: flex; flex-wrap: wrap; gap: 8px; }
  .hz-art button { min-height: 44px; padding: 0 16px; border-radius: 22px; border: 1px solid var(--line); background: var(--card); color: var(--text); font-weight: 500; }
  .hz-art button[aria-pressed="true"] { background: var(--primary); color: var(--on-primary); border-color: var(--primary-ink); font-weight: 700; box-shadow: inset 0 0 0 1px var(--primary-ink); }
  .hz-vorliste { display: grid; gap: 2px; font-size: 15px; margin: 12px 0 4px; padding: 10px 14px; background: var(--bg); border-radius: 10px; }
  .hz-vorliste > div { overflow-wrap: anywhere; }
  .hz-wohin-knopf { width: 100%; display: flex; align-items: center; gap: 12px; min-height: 64px; padding: 8px 14px; border: 1px solid var(--line); border-radius: 14px; background: var(--card); color: var(--text); text-align: left; }
  .hz-wohin-text { flex: 1; min-width: 0; display: grid; overflow-wrap: anywhere; }
  .hz-wohin-text .nm { font-weight: 500; }
  .hz-aendern { flex: none; }
  .hz-wohin .tb-ergebnis { min-height: 120px; }
`;

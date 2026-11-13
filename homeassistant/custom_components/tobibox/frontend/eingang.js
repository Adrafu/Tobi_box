/* Eingang: was gerade hinzugefügt wird und was „bitte kurz ansehen“ ist (Design 5.2 Punkt 2a, 6, 7.3 Punkt 3 bis 6 und 10; Paket A11b).
 *
 * Reine Funktionen ohne DOM und ohne Lit, damit das Band in der Bibliothek, der Punkt am Reiter, die Serienseite (A11b) und die Liste
 * „Zuletzt hinzugefügt“ auf der Seite „Hinzufügen“ (A11a, Teil 2 von A11b) dieselbe Ableitung benutzen. Der Zustand kommt immer aus
 * `eingang/list` (Vertrag W Nr. 29) und den Ereignissen des Themas `eingang` (Vertrag 4.5), nie aus dem Speicher einer Seite:
 * nach einem Neuladen der Seite stimmt alles wieder.
 *
 * Exportiert:
 *   FENSTER_MS, FERTIG_BAND_MS         24 Stunden („Zuletzt hinzugefügt“, Design 7.3 Punkt 5) und die Zeit, in der „Alles hinzugefügt.“ steht
 *   eintragZeit(e)                     Zeitpunkt eines Eintrags in ms (`fertig_am`, sonst `zuerst_gesehen`, sonst `geaendert_am`) oder null
 *   eintragZustand(e)                  'laeuft' | 'pruefen' | 'fehler' | 'fertig' (aus `status` und `pruefen`, Vertrag 3.9)
 *   eingangAbleiten(eintraege, opt)    { liste, laeuft, pruefen, fehler, fertig }: die Einträge der letzten 24 Stunden, nach Zustand sortiert
 *   bandZustand(abl, opt)              { art, anzahl, text } für das Band, oder null (kein Band)
 *   eintragFuerSerie(abl, serieId)     der neueste Eintrag, aus dem etwas in diese Serie kam, oder null
 *   grundSatz(code, werte)             Code → Satz für Eltern („bitte kurz ansehen“ und „geht nicht“), mit Rückfall für unbekannte Codes
 *   gruendeSaetze(codes)               mehrere Codes → Sätze ohne Doppelte; ohne bekannten Code der Rückfall
 *   eintragGruende(e)                  alle Sätze eines Eingangs-Eintrags (`hinweise` und `ergebnis[].pruefen_gruende`)
 *   daraus(e, opt)                     „Daraus ist geworden: …“ als Satz, oder '' ohne Ergebnis
 *   naechsteAenderung(eintraege, opt)  ms bis sich Band oder Liste durch bloßen Zeitablauf ändern (für einen Zeitgeber), oder null
 */
import { EINGANG, GRUENDE, HINWEISE, fuellen } from './texte.js';

export const FENSTER_MS = 24 * 3600 * 1000;
export const FERTIG_BAND_MS = 15 * 60 * 1000;
const LAUFEND = new Set(['wartet', 'bereit', 'laeuft']);

const alsMs = (t) => { const x = Date.parse(t); return Number.isFinite(x) ? x : null; };

/* Zeitpunkt, ab dem die 24 Stunden zählen. */
export function eintragZeit(e) {
  return alsMs(e?.fertig_am) ?? alsMs(e?.zuerst_gesehen) ?? alsMs(e?.geaendert_am);
}

/* Zustand eines Eintrags (Vertrag 3.9): `wartet`, `bereit`, `laeuft` = läuft; `blockiert` = geht nicht; `teilweise` = ein Teil blieb liegen
 * (bitte ansehen); sonst einsortiert, mit `pruefen` = bitte kurz ansehen. */
export function eintragZustand(e) {
  const st = e?.status;
  if (LAUFEND.has(st)) return 'laeuft';
  if (st === 'blockiert') return 'fehler';
  if (st === 'teilweise') return 'pruefen';
  return e?.pruefen ? 'pruefen' : 'fertig';
}

/* Die Einträge der letzten 24 Stunden (neueste zuerst, ohne Doppelte), je Zustand eine Liste.
 * opt.jetzt: Zeit in ms (Vorgabe jetzt). opt.offeneSerien: Menge von Serien-IDs, die noch „bitte prüfen“ sind (aus `serien/list` mit Filter
 * `pruefen`). Der Vertrag löscht `pruefen` am Eingangs-Eintrag nicht, wenn jemand „Das ist richtig“ tippt (`einsortierung/bestaetigen` wirkt nur auf
 * die Serie); darum zählt ein Eintrag nur dann als „bitte kurz ansehen“, wenn mindestens eine der betroffenen Serien noch geprüft werden muss.
 * Ohne `offeneSerien` (Backend ohne Bibliothek) gilt `pruefen` des Eintrags. */
export function eingangAbleiten(eintraege, { jetzt = Date.now(), offeneSerien = null } = {}) {
  const gesehen = new Set();
  const liste = [];
  for (const e of Array.isArray(eintraege) ? eintraege : []) {
    if (!e || gesehen.has(e.id)) continue;
    gesehen.add(e.id);
    const t = eintragZeit(e);
    if (t === null || jetzt - t > FENSTER_MS) continue;
    let zustand = eintragZustand(e);
    if (zustand === 'pruefen' && e.status !== 'teilweise' && offeneSerien) {
      const betroffen = (e.ergebnis || []).filter((r) => r.pruefen && r.serie_id);
      if (betroffen.length && !betroffen.some((r) => offeneSerien.has(r.serie_id))) zustand = 'fertig';
    }
    liste.push({ eintrag: e, zustand, zeit: t });
  }
  liste.sort((a, b) => b.zeit - a.zeit);
  const je = (z) => liste.filter((x) => x.zustand === z);
  return { liste, laeuft: je('laeuft'), pruefen: je('pruefen'), fehler: je('fehler'), fertig: je('fertig') };
}

/* Band über der Zeile „Bibliothek“ (Design 5.2 Punkt 2a). Vorrang: es läuft etwas → bitte kurz ansehen (orange) → geht nicht →
 * „Alles hinzugefügt.“ (nur kurz nach dem Fertigwerden, opt.fertigMs). opt.lokal: Uploads, die diese Seite gerade selbst sendet (A11a).
 * Rückgabe { art: 'laeuft' | 'pruefen' | 'fehler' | 'fertig', anzahl, text } oder null. */
export function bandZustand(abl, { jetzt = Date.now(), lokal = 0, fertigMs = FERTIG_BAND_MS } = {}) {
  const wort = (paar, n) => fuellen(n === 1 ? paar.eins : paar.mehr, { anzahl: n });
  const laeuft = (abl?.laeuft?.length || 0) + Math.max(0, lokal);
  if (laeuft > 0) return { art: 'laeuft', anzahl: laeuft, text: wort(EINGANG.band.laeuft, laeuft) };
  const n = abl?.pruefen?.length || 0;
  if (n > 0) return { art: 'pruefen', anzahl: n, text: wort(EINGANG.band.pruefen, n) };
  const f = abl?.fehler?.length || 0;
  if (f > 0) return { art: 'fehler', anzahl: f, text: wort(EINGANG.band.fehler, f) };
  const frisch = (abl?.fertig || []).filter((x) => jetzt - x.zeit <= fertigMs).length;
  if (frisch > 0) return { art: 'fertig', anzahl: frisch, text: EINGANG.band.fertig };
  return null;
}

/* Der neueste Eintrag der Ableitung, aus dem etwas in diese Serie kam. */
export function eintragFuerSerie(abl, serieId) {
  return (abl?.liste || []).find((x) => (x.eintrag.ergebnis || []).some((r) => r.serie_id === serieId))?.eintrag ?? null;
}

/* ------------------------------------------------------------------ Gründe */

/* Ein Code → ein Satz für Eltern: erst die Gründe „bitte kurz ansehen“, dann die Gründe „geht nicht“ (Design 7.3 Punkt 6). Unbekannte Codes
 * bekommen den Rückfallsatz, nie den Code. `werte` füllt Platzhalter (`angekommen`, `anzahl`, `verwalter_dat`, …). */
export function grundSatz(code, werte = {}) {
  if (code === 'gruppe_unvollstaendig' && werte.angekommen === undefined && werte.anzahl === undefined) return EINGANG.gruppe_ohne_zahl; // der Eingang nennt keine Zahlen
  const text = Object.hasOwn(GRUENDE, code) ? GRUENDE[code] : Object.hasOwn(HINWEISE, code) ? HINWEISE[code] : null;
  return text === null ? EINGANG.grund_sonst : fuellen(text, werte);
}

/* Mehrere Codes → Sätze ohne Doppelte (`track_doppelt` und `track_teils_leer` sagen dasselbe). Unbekannte Codes fallen weg, solange es einen
 * bekannten gibt; ohne einen bekannten Code steht der Rückfallsatz da. */
export function gruendeSaetze(codes, werte = {}) {
  const bekannt = [...new Set((codes || []).filter((c) => Object.hasOwn(GRUENDE, c) || Object.hasOwn(HINWEISE, c)))].map((c) => grundSatz(c, werte));
  const saetze = [...new Set(bekannt)];
  return saetze.length ? saetze : [EINGANG.grund_sonst];
}

/* Alle Sätze eines Eingangs-Eintrags: Hinweise (`hinweise[].code`, auch „geht nicht“) und die Gründe der einsortierten Teile. Leer, wenn es nichts zu sagen gibt. */
export function eintragGruende(e, werte = {}) {
  const codes = [...(e?.hinweise || []).map((h) => h.code), ...(e?.ergebnis || []).flatMap((r) => r.pruefen_gruende || [])];
  const bekannt = [...new Set(codes.filter((c) => Object.hasOwn(GRUENDE, c) || Object.hasOwn(HINWEISE, c)))].map((c) => grundSatz(c, werte));
  const saetze = [...new Set(bekannt)];
  if (!saetze.length && codes.length) return [EINGANG.grund_sonst];
  return saetze;
}

/* ------------------------------------------------------------------ „Daraus ist geworden: …“ */

const einheitWort = (tabelle, art, n) => {
  const paar = tabelle[art] || tabelle.hoerspiel;
  return fuellen(n === 1 ? paar.eins : paar.mehr, { anzahl: n });
};

/* Zeile je Serie, in die etwas kam; `serien` ist optional: Objekt oder Funktion `id → Serie` (mit `art` und `einzeln`), sonst gilt die Art des Wunsches. */
function gruppen(e, { serieId = null, serien = null } = {}) {
  const nachId = new Map();
  for (const r of e?.ergebnis || []) {
    if (!r || !r.serie_id || (serieId && r.serie_id !== serieId)) continue;
    if (!nachId.has(r.serie_id)) nachId.set(r.serie_id, { id: r.serie_id, name: r.serie_name || r.anzeige || '', neu: !!r.serie_neu, posten: [] });
    nachId.get(r.serie_id).posten.push(r);
  }
  const holeSerie = (id) => (typeof serien === 'function' ? serien(id) : serien?.[id]) || null;
  return [...nachId.values()].map((g) => {
    const s = holeSerie(g.id);
    const art = s?.art || e?.wunsch?.art || null;
    const einzeln = s ? !!s.einzeln : e?.wunsch?.ziel === 'einzeln';
    return { ...g, art, einzeln };
  });
}

function gruppenSatz(g) {
  const werte = { name: g.name };
  const art = EINGANG.art[g.art] ? g.art : null;
  if (g.einzeln && g.neu) return fuellen(EINGANG.daraus_einzeln, { ...werte, einheit: EINGANG.einzeln[art || 'musik'] });
  const n = g.posten.length;
  if (g.neu) {
    // Hörbuch: eine Folge mit den Dateien als Kapitel; sonst je Datei eine Folge
    const zahl = art === 'hoerbuch' && n === 1 ? Math.max(1, Number(g.posten[0].tracks) || 1) : n;
    const einheit = einheitWort(EINGANG.einheit, art || 'hoerspiel', zahl);
    return art ? fuellen(EINGANG.daraus_neu, { ...werte, art: EINGANG.art[art], einheit }) : fuellen(EINGANG.daraus_neu_ohne_art, { ...werte, einheit });
  }
  return fuellen(EINGANG.daraus_dazu, { ...werte, einheit: einheitWort(EINGANG.einheit_dazu, art || 'hoerspiel', n) });
}

/* Der Satz „Daraus ist geworden: …“ (Design 7.3 Punkt 3b und 10). opt.serieId: nur, was in diese Serie kam (Serienseite); opt.serien: Auskunft über Art und
 * Einzeltitel; opt.hoechstens: wie viele Serien genannt werden (Vorgabe 3, der Rest als „und 2 weitere“). Ohne Ergebnis: ''. */
export function daraus(e, { serieId = null, serien = null, hoechstens = 3 } = {}) {
  const gs = gruppen(e, { serieId, serien });
  if (!gs.length) return '';
  const teile = gs.slice(0, hoechstens).map(gruppenSatz);
  const rest = gs.length - teile.length;
  const text = teile.join('; ') + (rest > 0 ? ` ${fuellen(EINGANG.daraus_weitere, { anzahl: rest })}` : '');
  return fuellen(EINGANG.daraus, { text });
}

/* ------------------------------------------------------------------ Zeitablauf */

/* Wann ändert sich die Ableitung ohne neue Daten? Entweder fällt ein Eintrag aus den 24 Stunden, oder „Alles hinzugefügt.“ läuft ab.
 * Rückgabe: ms bis dahin (mindestens 1000), oder null, wenn nichts mehr kommt. */
export function naechsteAenderung(eintraege, { jetzt = Date.now(), fertigMs = FERTIG_BAND_MS } = {}) {
  let min = null;
  for (const e of Array.isArray(eintraege) ? eintraege : []) {
    const t = eintragZeit(e);
    if (t === null) continue;
    for (const ende of [t + FENSTER_MS, e?.status === 'erledigt' || e?.fertig_am ? t + fertigMs : null]) {
      if (ende !== null && ende > jetzt && (min === null || ende - jetzt < min)) min = ende - jetzt;
    }
  }
  return min === null ? null : Math.max(1000, min);
}

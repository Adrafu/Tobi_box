/* Mock für die HA-WebSocket-Schnittstelle nach Vertrag W (ha-websocket-v1).
 *
 * `createMockHass()` liefert ein `hass`-Objekt mit connection.sendMessagePromise / subscribeMessage,
 * eine kleine Backend-Nachbildung im Arbeitsspeicher und einen XMLHttpRequest-Ersatz für den Upload.
 * Der Mock ist streng wie das echte Backend: unbekannte Felder und fehlende Pflichtfelder
 * ergeben `invalid_format`; Felder, die die Seite senden MUSS (`stand`, `erwartet_ziel`), ebenfalls.
 * Fehler kommen wie bei HA als Objekt { code, message }.
 */
import { createHash } from 'node:crypto';

/* Befehl -> Pflichtfelder (req), optionale Felder (opt), Felder, die die Seite immer senden muss (must). */
export const SCHEMA = {
  'tobibox/hello': { req: ['v'] },
  'tobibox/subscribe': { opt: ['themen'] },
  'tobibox/serien/list': { opt: ['art', 'text', 'auch_folgen', 'filter', 'sortierung', 'limit', 'offset'] },
  'tobibox/serie/get': { req: ['serie_id'] },
  'tobibox/serie/create': { req: ['name'], opt: ['typ', 'anfrage_id'] },
  'tobibox/serie/rename': { req: ['serie_id', 'name'] },
  'tobibox/folgen/order': { req: ['serie_id', 'folgen'], opt: ['stand'], must: ['stand'] },
  'tobibox/folge/delete': { req: ['serie_id', 'folge'], opt: ['tobies_bestaetigt', 'stand'], must: ['stand'] },
  'tobibox/medien/pruefen': {},
  'tobibox/papierkorb/list': { opt: ['limit', 'offset'] },
  'tobibox/papierkorb/restore': { req: ['eintrag_id'], opt: ['serie_id'] },
  'tobibox/papierkorb/empty': { req: ['bestaetigt'], opt: ['eintrag_ids'] },
  'tobibox/neue_tobies/list': { opt: ['limit', 'offset'] },
  'tobibox/neue_tobies/verwerfen': { req: ['uid'] },
  'tobibox/zuordnung/list': { opt: ['serie_id', 'limit', 'offset', 'text', 'neu'] },
  'tobibox/zuordnung/set': { req: ['uid', 'ziel'], opt: ['name', 'ueberschreiben', 'erwartet_ziel'], must: ['erwartet_ziel'] },
  'tobibox/zuordnung/remove': { req: ['uid'], opt: ['erwartet_ziel'], must: ['erwartet_ziel'] },
  'tobibox/lernmodus/start': { req: ['box', 'ziel'], opt: ['name', 'anfrage_id'] },
  'tobibox/lernmodus/antwort': { req: ['befehl_id', 'ueberschreiben'] },
  'tobibox/lernmodus/abbrechen': { req: ['box'] },
  'tobibox/boxen/list': {},
  'tobibox/box/sync': { req: ['box'], opt: ['anfrage_id'] },
  'tobibox/liste/neu_ausrollen': { req: ['bestaetigt'], opt: ['anfrage_id'] },
  'tobibox/serie/delete': { req: ['serie_id'], opt: ['tobies_bestaetigt', 'stand'], must: ['stand'] },
  'tobibox/folge/rename': { req: ['serie_id', 'folge', 'name'], opt: ['stand'], must: ['stand'] },
  'tobibox/folge/verschieben': { req: ['serie_id', 'folge', 'ziel_serie_id'], opt: ['tobies_bestaetigt', 'stand'], must: ['stand'] },
  'tobibox/serien/zusammenfuehren': { req: ['quelle_id', 'ziel_id'], opt: ['tobies_bestaetigt', 'stand_quelle', 'stand_ziel'], must: ['stand_quelle', 'stand_ziel'] },
  'tobibox/einsortierung/bestaetigen': { req: ['serie_id'], opt: ['folgen'] },
  'tobibox/eingang/list': { opt: ['filter', 'limit', 'offset'] },
  'tobibox/eingang/sortieren': { opt: ['eintrag_ids', 'sofort'] },
  'tobibox/konfig/export_lesen': {},
  'tobibox/konfig/aus_export': { req: ['bestaetigt'], opt: ['anfrage_id'] },
};

/* AP 4.7 und Erweiterungen v1.1 (Vertrag W, Abschnitt 10): eigener Satz, damit die Abdeckung der alten Befehle unverändert bleibt.
 * `braucht` ist die Fähigkeit aus hello.faehigkeiten, ohne die ein älteres Backend den Befehl nicht kennt (unknown_command);
 * FELDER_V11 sind neue optionale Eingabefelder alter Befehle: ohne die Fähigkeit lehnt das Backend sie ab (invalid_format). */
export const SCHEMA_V11 = {
  'tobibox/einstellungen/get': { braucht: 'einstellungen' },
  'tobibox/einstellungen/set': { opt: ['leise_zeiten', 'gute_nacht', 'lesezeichen_tage', 'erwartet_revision'], braucht: 'einstellungen' },
  'tobibox/eingang/entfernen': { req: ['eintrag_id', 'bestaetigt'], braucht: 'eingang_entfernen' },
  'tobibox/konfig/get': { braucht: 'konfig_lesen' },
};
/* Befehle der Bibliothek (A7, Vertrag W Nr. 37), getrennt, damit die Abdeckungsprüfung der alten Seite unverändert bleibt. */
export const SCHEMA_BIB = {
  'tobibox/folgen/list': { opt: ['art', 'text', 'filter', 'sortierung', 'limit', 'offset'], braucht: 'bibliothek' },
  'tobibox/serie/art_setzen': { req: ['serie_id', 'art'], braucht: 'bibliothek' }, // A8, Vertrag W Nr. 38
};
/* A11c (Vertrag W Nr. 43): „Anders einsortieren“. Eigener Satz, damit die Abdeckungsprüfung der alten Seite unverändert bleibt. */
export const SCHEMA_NEU = {
  'tobibox/einsortierung/neu': { req: ['eintrag_id', 'ziel'], opt: ['art', 'name', 'serie_id'], braucht: 'einsortier_wunsch' },
};
/* A9/A10 (Vertrag W 3.13, Nr. 47 bis 49): Warteschlange „Nächster neuer Tobie“. Eigener Satz, damit die Abdeckungsprüfung der alten Seite unverändert bleibt. */
export const SCHEMA_WS = {
  'tobibox/warteschlange/set': { req: ['box', 'ziel'], opt: ['name', 'anfrage_id'], braucht: 'warteschlange' },
  'tobibox/warteschlange/list': { braucht: 'warteschlange' },
  'tobibox/warteschlange/abbrechen': { req: ['eintrag_id'], braucht: 'warteschlange' },
};
export const FAEHIGKEITEN_A9 = ['warteschlange', 'zuordnung_rueckgaengig'];
/* A-2 Reinhören (Vertrag W Nr. 39 bis 42, 14.5, 14.6): Fähigkeit `reinhoeren`. Der Mock führt die Hörstelle je Serie im Speicher (ein Benutzer) und
 * baut den signierten Pfad wie das Backend: `/api/tobibox/audio/<serie>/<folge>[?track=n&]authSig=…`, jedes Segment mit `encodeURIComponent`. */
export const SCHEMA_REIN = {
  'tobibox/audio/bereit': { req: ['serie_id', 'folge'], opt: ['track', 'vorbereiten'], braucht: 'reinhoeren' },
  'tobibox/hoerstelle/get': { req: ['serie_id'], braucht: 'reinhoeren' },
  'tobibox/hoerstelle/set': { req: ['serie_id', 'folge', 'position_s', 'dauer_s'], opt: ['track', 'fertig'], braucht: 'reinhoeren' },
  'tobibox/hoerstelle/liste': { opt: ['limit'], braucht: 'reinhoeren' },
};
/* Stufe B „Gehört“ (Vertrag W 3.14, Nr. 50 bis 56) und der HA-Befehl für die Akku-Kurve. Eigener Satz, damit die Abdeckungsprüfung der alten Seite unverändert bleibt.
 * Fähigkeiten: `gehoert` (50 bis 54, Felder `spieler` und `spielt` bei Nr. 41, Sortierungen `zuletzt_gehoert` und `meist_gehoert`), `favoriten` (55, 56, Filter `favorit`). */
export const FAEHIGKEITEN_B = ['gehoert', 'favoriten'];
export const SCHEMA_B = {
  'tobibox/gehoert/zusammenfassung': { opt: ['wer', 'zeitraum', 'von', 'bis', 'nach', 'serie_id', 'sortierung', 'limit'], must: ['nach'], braucht: 'gehoert' },
  'tobibox/gehoert/zuletzt': { opt: ['wer', 'limit'], braucht: 'gehoert' },
  'tobibox/technik/verlauf': { req: ['box', 'von', 'bis'], braucht: 'gehoert' },
  'tobibox/gehoert/exportieren': { req: ['quelle'], braucht: 'gehoert' },
  'tobibox/gehoert/loeschen': { req: ['quelle'], opt: ['trocken', 'bestaetigung'], braucht: 'gehoert' },
  'tobibox/favorit/set': { req: ['serie_id', 'an'], opt: ['folge'], braucht: 'favoriten' },
  'tobibox/favoriten/list': { braucht: 'favoriten' },
  'recorder/statistics_during_period': { req: ['start_time', 'statistic_ids', 'period'], opt: ['end_time', 'types', 'units'] }, // HA-Kern, kein Befehl von Tobi Box
};
export const ADMIN_BEFEHLE_B = new Set(['tobibox/technik/verlauf', 'tobibox/gehoert/exportieren', 'tobibox/gehoert/loeschen']);

/* Online-Suche (Vertrag W 3.15, Nr. 57 bis 65, Fähigkeit `online_suche`, OS4; Nr. 65 mit `online_lauf_liste`). Nr. 57 bis 63 und 65 nur für Administratoren, Nr. 64 (voller Beschreibungstext) für alle (Recht lesen).
 * Eigener Satz und eigene Fähigkeit, nicht in `FAEHIGKEITEN`: die Abdeckungsprüfungen der alten Seiten bleiben unverändert. */
export const FAEHIGKEITEN_OS = ['online_suche', 'online_lauf_liste']; // `online_lauf_liste` (19.11., T11): Nr. 65; nur zusammen mit `online_suche`
export const SCHEMA_OS = {
  'tobibox/online/suchen': { req: ['serie_id'], opt: ['folge', 'text'], braucht: 'online_suche' },
  'tobibox/online/treffer': { opt: ['treffer_id', 'serie_id', 'vorschlag_id'], braucht: 'online_suche' },
  'tobibox/online/uebernehmen': { req: ['serie_id', 'felder'], opt: ['treffer_id', 'vorschlag_id', 'stand', 'anfrage_id'], braucht: 'online_suche' },
  'tobibox/online/zuruecknehmen': { opt: ['serie_id', 'aenderung_id', 'lauf_id'], braucht: 'online_suche' },
  'tobibox/online/vorschlag_verwerfen': { req: ['serie_id', 'vorschlag_id'], braucht: 'online_suche' },
  'tobibox/online/lauf': { req: ['aktion'], braucht: 'online_suche' },
  'tobibox/online/status': { braucht: 'online_suche' },
  'tobibox/online/beschreibung': { req: ['serie_id', 'folge'], braucht: 'online_suche' },
  'tobibox/online/lauf_aenderungen': { req: ['lauf_id'], braucht: 'online_lauf_liste' }, // Nr. 65 (19.11., T11)
};
export const ADMIN_BEFEHLE_OS = new Set(Object.keys(SCHEMA_OS).filter((t) => t !== 'tobibox/online/beschreibung'));

/* A8: Befehle nur für Administratoren (Vertrag 2.1). Mit der Mock-Option `nichtAdmin` darf der Benutzer alles andere (Alltag). */
export const ADMIN_BEFEHLE = new Set(['folgen/order', 'serien/zusammenfuehren', 'serie/create', 'papierkorb/restore', 'papierkorb/empty'].map((x) => `tobibox/${x}`));
export const FELDER_V11 = {
  'tobibox/zuordnung/remove': { als_neu: 'zuordnung_rueckgaengig' }, // A9, Vertrag 3.5 (13.11.)
  'tobibox/zuordnung/list': { uid: 'zuordnung_uid' },
  'tobibox/konfig/export_lesen': { stand: 'konfig_staende' }, // A12/A13: frühere Stände (Vertrag 2.4)
  'tobibox/konfig/aus_export': { stand: 'konfig_staende' },
  'tobibox/hoerstelle/set': { spieler: 'gehoert', spielt: 'gehoert' }, // Stufe B (Vertrag 41): nur mit der Fähigkeit `gehoert`
  'tobibox/serien/list': { alter: 'alter' }, // Altersfilter (Vertrag 14.2): nur mit der Fähigkeit `alter`
};

/* Altersfilter (Vertrag W Nr. 66, 14.2; Fähigkeit `alter`, 23.11.): Befehl `serie/alter_setzen` und die Eingabe `alter` bei `serien/list`. */
export const SCHEMA_AF = {
  'tobibox/serie/alter_setzen': { req: ['serie_id', 'alter_hand'], braucht: 'alter' },
};
const ALTER_OK = (x) => Number.isInteger(x) && x >= 0 && x <= 18; // Zahl 0 bis 18, kein bool

/* A12/A13 (Technik): Befehle der Stufe A, die nur Administratoren brauchen (Vertrag 3.12). */
export const SCHEMA_TECHNIK = {
  'tobibox/cover/neu_suchen': { opt: ['serie_id'], braucht: 'cover' },
  'tobibox/hoerkopie/neu_erzeugen': { opt: ['serie_id'], braucht: 'hoerkopie' },
  'tobibox/papierkorb/restore_letzte_stunde': { req: ['bestaetigt'] },
};
/* A7 (Vertrag W, 14.2): neue optionale Eingaben der Bibliothek. Ohne die Fähigkeit `bibliothek` lehnt das Backend sie ab (invalid_format). */
export const FELDER_BIB = {
  'tobibox/serien/list': ['art', 'text', 'auch_folgen', 'filter', 'sortierung', 'limit', 'offset'],
  'tobibox/zuordnung/list': ['text', 'neu'],
  'tobibox/einstellungen/set': ['erwartet_revision'], // A7b (Vertrag 3.11, 12.11.)
};
export const ARTEN = ['hoerspiel', 'hoerbuch', 'musik', 'geschichte'];
const FILTER_WERTE = ['ohne_tobie', 'neu', 'pruefen', 'sammlung', 'einzeln', 'favorit', 'online_vorschlag'];
const MOCK_JETZT = Date.parse('2026-11-13T12:00:00Z'); // „heute“ im Mock (Filter „neu“: letzte 14 Tage)
export const NACHRICHT_MAX = 64 * 1024; // Vertrag 8: eine Nachricht hat höchstens 64 KiB
export const FAEHIGKEITEN_V11 = ['einstellungen', 'eingang_entfernen', 'zuordnung_uid', 'konfig_lesen', 'upload_fertig_details'];

/* Befehle, die nur Administratoren ausführen dürfen (Vertrag 2.1). */
const LESEN = new Set(['hello', 'subscribe', 'serien/list', 'folgen/list', 'serie/get', 'papierkorb/list', 'neue_tobies/list', 'zuordnung/list', 'boxen/list', 'eingang/list', 'konfig/export_lesen', 'einstellungen/get', 'konfig/get', 'hoerstelle/get', 'hoerstelle/liste', 'gehoert/zusammenfassung', 'gehoert/zuletzt', 'favoriten/list', 'online/beschreibung'].map((x) => `tobibox/${x}`));

export const FAEHIGKEITEN = ['medien', 'upload', 'zuordnung', 'tobie_namen', 'neue_tobies', 'lernmodus', 'boxen', 'papierkorb', 'liste_ausrollen', 'konfig_export', 'sync', 'eingang', 'korrektur', 'serie_loeschen', 'bibliothek', 'cover'];

const fehler = (code, message = code) => ({ code, message });
const ISO = (d) => d.toISOString().slice(0, 10);

/* Ein Eintrag für `eingang/list` (Vertrag 3.9) mit sinnvollen Vorgaben; `teil` überschreibt. A11b: Band, Punkt am Reiter, Karte „bitte kurz ansehen“. */
let eingangZaehler = 0;
export function eingangEintrag(teil = {}) {
  const n = ++eingangZaehler;
  return { id: hex(`eingang-${n}`, 12), name: `Eintrag ${n}`, art: 'datei', dateien: 1, ignoriert: 0, groesse_bytes: 5 * 1048576, zuerst_gesehen: new Date().toISOString(), geaendert_am: new Date().toISOString(),
    status: 'erledigt', hinweise: [], ergebnis: [], fertig_am: new Date().toISOString(), quelle: 'upload', wunsch: null, pruefen: false, ...teil };
}
const gleich = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
const hex = (s, n = 16) => createHash('sha256').update(s).digest('hex').slice(0, n);

/* Wertebereiche der Bibliothek (Vertrag 14.2 und Befehl 37). */
function pruefeBibliothek(type, f, faehigkeiten) {
  const grenze = { 'tobibox/serien/list': 200, 'tobibox/folgen/list': 100, 'tobibox/zuordnung/list': 100 }[type];
  if (grenze === undefined) { if (type === 'tobibox/serie/alter_setzen' && !(f.alter_hand === null || ALTER_OK(f.alter_hand))) throw fehler('invalid_format', 'alter_hand: 0 bis 18 oder null'); return; }
  if ('limit' in f && !(Number.isInteger(f.limit) && f.limit >= 1 && f.limit <= grenze)) throw fehler('invalid_format', `limit 1 bis ${grenze}`);
  if ('offset' in f && !(Number.isInteger(f.offset) && f.offset >= 0)) throw fehler('invalid_format', 'offset ab 0');
  if ('text' in f && !(typeof f.text === 'string' && f.text.trim().length >= 2 && f.text.length <= 100)) throw fehler('invalid_format', 'text mit 2 bis 100 Zeichen');
  if ('art' in f && !ARTEN.includes(f.art)) throw fehler('invalid_format', 'art');
  if ('alter' in f && !(f.alter === 'ohne' || ALTER_OK(f.alter))) throw fehler('invalid_format', 'alter: 0 bis 18 oder "ohne"');
  if ('neu' in f && typeof f.neu !== 'boolean') throw fehler('invalid_format', 'neu');
  if ('auch_folgen' in f && typeof f.auch_folgen !== 'boolean') throw fehler('invalid_format', 'auch_folgen');
  if ('filter' in f) {
    if (!Array.isArray(f.filter) || f.filter.some((x) => !FILTER_WERTE.includes(x))) throw fehler('invalid_format', 'filter');
    if (faehigkeiten && f.filter.includes('favorit') && !faehigkeiten.includes('favoriten')) throw fehler('invalid_format', 'favorit braucht favoriten');
    if (faehigkeiten && f.filter.includes('online_vorschlag') && !faehigkeiten.includes('online_suche')) throw fehler('invalid_format', 'online_vorschlag braucht online_suche');
  }
  if ('sortierung' in f) {
    const gehoert = !faehigkeiten || faehigkeiten.includes('gehoert');
    const erlaubt = type === 'tobibox/folgen/list' ? ['titel', 'neu'] : ['name', 'neu', 'angehoert', ...(gehoert ? ['zuletzt_gehoert', 'meist_gehoert'] : [])];
    if (!erlaubt.includes(f.sortierung)) throw fehler('invalid_format', 'sortierung');
    if (f.sortierung === 'angehoert' && faehigkeiten && !faehigkeiten.includes('reinhoeren')) throw fehler('invalid_format', 'angehoert braucht reinhoeren');
  }
}

/* Wertebereiche der Befehle 39 bis 42 (Vertrag W). */
function pruefeRein(type, f) {
  const zahl = (x) => typeof x === 'number' && Number.isFinite(x);
  if ('serie_id' in f && !(typeof f.serie_id === 'string' && f.serie_id)) throw fehler('invalid_format', 'serie_id');
  if ('folge' in f && !(typeof f.folge === 'string' && f.folge)) throw fehler('invalid_format', 'folge');
  if ('track' in f && !(Number.isInteger(f.track) && f.track >= 0)) throw fehler('invalid_format', 'track');
  if ('vorbereiten' in f && typeof f.vorbereiten !== 'boolean') throw fehler('invalid_format', 'vorbereiten');
  if ('fertig' in f && typeof f.fertig !== 'boolean') throw fehler('invalid_format', 'fertig');
  if ('position_s' in f && !(zahl(f.position_s) && f.position_s >= 0)) throw fehler('invalid_format', 'position_s');
  if ('dauer_s' in f && !(zahl(f.dauer_s) && f.dauer_s > 0)) throw fehler('invalid_format', 'dauer_s');
  if ('limit' in f && !(Number.isInteger(f.limit) && f.limit >= 1 && f.limit <= 12)) throw fehler('invalid_format', 'limit 1 bis 12');
  if ('spieler' in f && !(typeof f.spieler === 'string' && /^[A-Za-z0-9_-]{8,64}$/.test(f.spieler))) throw fehler('invalid_format', 'spieler: 8 bis 64 Zeichen [A-Za-z0-9_-]');
  if ('spielt' in f && typeof f.spielt !== 'boolean') throw fehler('invalid_format', 'spielt');
  void type;
}

/* Wie das Backend: ohne Groß/Klein und ohne Umlaute; alle Wörter des Suchtexts müssen vorkommen. */
const normiere = (x) => String(x ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
const passtText = (text, haystack) => normiere(text).split(/\s+/).filter(Boolean).every((w) => haystack.some((h) => normiere(h).includes(w)));

/* ---- Beispielbibliothek (A7): n Einträge, deterministisch. Verteilung je 20 Einträge: 8 Hörspiele, 3 Hörbücher, 5 Alben,
 * 2 Geschichten-Sammlungen und 2 Einzeltitel (ein Lied, eine Geschichte). Etwa 70 % mit Cover, 60 % mit Dauer, einige „bitte ansehen“,
 * einige angehört, jeder fünfte mit Tobie (auch auf einzelne Folgen und eine Aktion). Die Namen sind erfunden. */
export function beispielBibliothek(n = 130) {
  const mkFolge = (name, anzeige, extra = {}) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * 1048576, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });
  let zufall = 42;
  const rnd = (von, bis) => { zufall = (zufall * 1664525 + 1013904223) % 4294967296; return von + (zufall % (bis - von + 1)); };
  const w1 = ['Kleine', 'Große', 'Lustige', 'Geheime', 'Fliegende', 'Mutige', 'Müde', 'Bunte', 'Wilde', 'Stille'];
  const w2 = ['Drachen', 'Piraten', 'Eulen', 'Füchse', 'Wolken', 'Sterne', 'Zwerge', 'Roboter', 'Bären', 'Feen'];
  const orte = ['im Wald', 'am See', 'auf dem Berg', 'in der Stadt', 'im Weltall', 'am Meer'];
  const lied = ['Wiegenlied', 'Regenlied', 'Sternenlied', 'Tanzlied', 'Schlaflied', 'Mondlied', 'Wanderlied'];
  const dauerSerie = { hoerspiel: [1500, 2700], hoerbuch: [18000, 36000], musik: [150, 260], geschichte: [300, 900] };
  const serien = {};
  const zuordnungen = {};
  const namen = new Set();
  const figuren = ['Löwe', 'Bär', 'Fuchs', 'Hase', 'Igel', 'Dachs', 'Otter', 'Rabe'];
  for (let i = 0; i < n; i += 1) {
    const k = i % 20;
    const art = k < 8 ? 'hoerspiel' : k < 11 ? 'hoerbuch' : k < 16 ? 'musik' : k === 18 ? 'musik' : 'geschichte';
    const einzeln = k >= 18;
    let name = einzeln
      ? (art === 'musik' ? `${lied[i % lied.length]} ${i}` : `Die Geschichte vom ${w2[i % 10]}`)
      : `${w1[(i * 3) % 10]} ${w2[(i * 7) % 10]} ${orte[i % 6]}`;
    if (namen.has(name)) name = `${name} (${i})`;
    namen.add(name);
    const id = hex(`serie-${i}`, 12);
    const anzahl = einzeln ? 1 : art === 'hoerbuch' ? 1 : art === 'musik' ? rnd(8, 20) : art === 'geschichte' ? rnd(4, 9) : rnd(3, 12);
    const [dv, db] = dauerSerie[art];
    const folgen = Array.from({ length: anzahl }, (_, j) => {
      const titel = einzeln ? name : art === 'musik' ? `${lied[(i + j) % lied.length]} ${j + 1}` : art === 'hoerbuch' ? name : `Folge ${j + 1}: ${['Der Schatz', 'Das Rätsel', 'Die Höhle', 'Der Sturm', 'Das Fest', 'Die Reise'][(i + j) % 6]}`;
      return mkFolge(`${String(j + 1).padStart(2, '0')}-${id}.mp3`, titel, { nummer: art === 'hoerspiel' ? j + 1 : null, pruefen: false });
    });
    const dauerEin = rnd(dv, db);
    serien[id] = {
      id, name, typ: 'normal', ordner: name, pruefen: i % 17 === 3, hinweise: [], folgen, art, einzeln,
      kapitel_anzahl: art === 'hoerbuch' ? rnd(8, 30) : 0,
      dauer_s: i % 5 < 3 ? dauerEin * anzahl : null,
      cover_stand: i % 10 < 7 ? hex(`cover-${i}`, 8) : null,
      angelegt_am: new Date(MOCK_JETZT - i * 12 * 3600 * 1000).toISOString().replace('.000', ''),
      ...(i % 9 === 2 ? { hoerstelle: i % 18 === 2 ? { anteil: 1, rest_s: 0, zeit: '2026-11-12T18:00:00Z', folge: folgen[0].name } : { anteil: 0.35 + (i % 4) * 0.1, rest_s: 1100 + i * 7, zeit: `2026-11-1${i % 3}T17:00:00Z`, folge: folgen[0].name } } : {}),
    };
    if (i % 5 === 1) {
      const uid = hex(`tobie-${i}`, 14).toUpperCase();
      zuordnungen[uid] = { uid, name: figuren[i % figuren.length], ziel: { typ: 'serie', serie: id }, angelegt_am: new Date(MOCK_JETZT - i * 3600 * 1000).toISOString().replace('.000', '') };
    }
    if (i % 11 === 4 && !einzeln) {
      const uid = hex(`tobie-folge-${i}`, 14).toUpperCase();
      zuordnungen[uid] = { uid, name: null, ziel: { typ: 'folge', serie: id, folge: folgen[0].name }, angelegt_am: new Date(MOCK_JETZT - i * 7200 * 1000).toISOString().replace('.000', '') };
    }
  }
  zuordnungen['04AA00AA00AA00'] = { uid: '04AA00AA00AA00', name: 'Gute Nacht', ziel: { typ: 'aktion', aktion: 'gute_nacht' }, angelegt_am: '2026-11-13T11:00:00Z' };
  return { serien, zuordnungen };
}

/* `faehigkeiten`: was das (simulierte) Backend zusagt. Ohne Angabe wird nur die Form geprüft (alles ist erlaubt). */
export function pruefeEingabe(msg, faehigkeiten = null) {
  const sch = SCHEMA[msg.type] || SCHEMA_V11[msg.type] || SCHEMA_BIB[msg.type] || SCHEMA_TECHNIK[msg.type] || SCHEMA_WS[msg.type] || SCHEMA_REIN[msg.type] || SCHEMA_NEU[msg.type] || SCHEMA_B[msg.type] || SCHEMA_OS[msg.type] || SCHEMA_AF[msg.type];
  if (!sch) throw fehler('unknown_command', `Unbekannter Befehl ${msg.type}`);
  if (faehigkeiten && sch.braucht && !faehigkeiten.includes(sch.braucht)) throw fehler('unknown_command', `Unbekannter Befehl ${msg.type}`);
  const { type, id, ...felder } = msg; // eslint-disable-line no-unused-vars
  const erlaubt = new Set([...(sch.req || []), ...(sch.opt || [])]);
  for (const [feld, f] of Object.entries(FELDER_V11[msg.type] || {})) if (!faehigkeiten || faehigkeiten.includes(f)) erlaubt.add(feld);
  for (const k of Object.keys(felder)) {
    if (faehigkeiten && !faehigkeiten.includes('bibliothek') && (FELDER_BIB[msg.type] || []).includes(k)) throw fehler('invalid_format', `Feld ${k} braucht die Fähigkeit bibliothek`);
    if (!erlaubt.has(k)) throw fehler('invalid_format', `Unbekanntes Feld ${k}`);
    if (felder[k] === undefined) throw fehler('invalid_format', `Feld ${k} ist undefined`);
  }
  pruefeBibliothek(msg.type, felder, faehigkeiten);
  if (SCHEMA_REIN[msg.type]) pruefeRein(msg.type, felder);
  for (const k of sch.req || []) if (!(k in felder)) throw fehler('invalid_format', `Pflichtfeld ${k} fehlt`);
  for (const k of sch.must || []) if (!(k in felder)) throw fehler('invalid_format', `Die Seite muss ${k} senden`);
  if ('bestaetigt' in felder && felder.bestaetigt !== true) throw fehler('invalid_format', 'bestaetigt muss true sein');
  if ('anfrage_id' in felder && !/^[0-9A-Za-z-]{8,64}$/.test(felder.anfrage_id)) throw fehler('invalid_format', 'anfrage_id');
  return felder;
}

/* ---- Stufe B: Hördaten und Favoriten des Mocks (Vertrag W 3.14, 15) ---- */
const addTage = (tag, n) => ISO(new Date(Date.parse(`${tag}T00:00:00Z`) + n * 86400000));
const tageZwischen = (von, bis) => { const l = []; for (let t = von; t <= bis; t = addTage(t, 1)) l.push(t); return l; };
/* ISO-Woche (Montag) als „JJJJ-Www“ */
export function isoWoche(tag) {
  const t = new Date(Date.parse(`${tag}T00:00:00Z`));
  t.setUTCDate(t.getUTCDate() + 3 - ((t.getUTCDay() + 6) % 7)); // Donnerstag derselben Woche
  const jahr = t.getUTCFullYear();
  const w1 = new Date(Date.UTC(jahr, 0, 4));
  const nr = 1 + Math.round(((t - w1) / 86400000 - 3 + ((w1.getUTCDay() + 6) % 7)) / 7);
  return `${jahr}-W${String(nr).padStart(2, '0')}`;
}

/* Beispieldaten: `tage` Tage bis `heute`, drei bis vier Quellen (zwei Boxen, zwei Personen), die ersten Einträge der Bibliothek (ab dem `ab`-ten). Deterministisch.
 * Zeile: { wer, serie, folge, tag, stunde, sekunden, mal (1 = beginnt ein zählendes Mal), fertig (1 = in dieser Sitzung fertig) }. `tag` null = Datum unbekannt. */
export function beispielGehoert(b, { tage = 60, heute = '2026-11-13', ab = 0 } = {}) {
  const serien = Object.values(b.serien).filter((s) => s.typ === 'normal' && s.folgen.length).slice(ab);
  if (!serien.length) return [];
  let z = 7;
  const rnd = (n) => { z = (z * 1103515245 + 12345) % 2147483648; return (z >>> 7) % n; };
  const quellen = [...b.boxen.slice(0, 2).map((x) => `box:${x.box}`), 'benutzer:u1', 'benutzer:u2'];
  const zeilen = [];
  for (let d = 0; d < tage; d += 1) {
    const tag = addTage(heute, -d);
    const n = 1 + rnd(4);
    for (let i = 0; i < n; i += 1) {
      const s = serien[rnd(Math.min(serien.length, 8))];
      const f = s.folgen[rnd(s.folgen.length)];
      zeilen.push({ wer: quellen[rnd(quellen.length)], serie: s.id, folge: f.name, tag, stunde: [7, 8, 15, 17, 18, 19, 19, 20][rnd(8)], sekunden: 120 + rnd(2400), mal: 1, fertig: rnd(3) === 0 ? 1 : 0 });
    }
  }
  return zeilen;
}

/* Befehle 50 bis 56 und der Akku-Verlauf; Auslegung nach Vertrag 3.14 (Zeitreihen lückenlos, höchstens 400 Zeilen, Ranglisten nach `sekunden`). */
function gehoertBefehle({ b, hat, emit, kurzform, istFavorit, holeSerie, holeFolge, istAdmin, opts }) {
  const G = b.gehoert;
  const ZEIT = ['tag', 'woche', 'monat', 'stunde'];
  const boxName = (id) => { const x = b.boxen.find((y) => y.box === id); return x ? (x.anzeige || x.anzeigename || x.box) : id; };
  const quellenName = (wer) => (wer.startsWith('box:') ? boxName(wer.slice(4)) : (G.personen[wer.slice(9)] ?? 'Früherer Benutzer'));
  const auswahl = () => {
    const alle = [...new Set([...b.boxen.map((x) => `box:${x.box}`), ...G.zeilen.map((z) => z.wer)])];
    return alle.map((wer) => ({ wer, name: quellenName(wer), art: wer.startsWith('box:') ? 'box' : 'person' }))
      .sort((x, y) => (x.art === y.art ? 0 : x.art === 'box' ? -1 : 1));
  };
  const werPruefen = (wer) => {
    if (wer === undefined || wer === 'alle' || wer === 'alle_boxen') return;
    if (typeof wer !== 'string' || !auswahl().some((x) => x.wer === wer)) throw fehler('wer_ungueltig');
  };
  const werPasst = (wer, z) => wer === undefined || wer === 'alle' || (wer === 'alle_boxen' ? z.wer.startsWith('box:') : z.wer === wer);
  const heute = () => G.heute;
  const ungueltig = (t) => fehler('invalid_format', t);
  const monatVon = (tag) => tag.slice(0, 7);
  const rasterWert = (art, tag) => (art === 'tag' ? tag : art === 'woche' ? isoWoche(tag) : art === 'monat' ? monatVon(tag) : null);

  const zusammenfassung = (m) => {
    if (!Array.isArray(m.nach) || m.nach.length < 1 || m.nach.length > 2 || new Set(m.nach).size !== m.nach.length) throw ungueltig('nach');
    if (m.nach.some((k) => !['wer', 'serie', 'folge', ...ZEIT].includes(k))) throw ungueltig('nach');
    const zeitSchluessel = m.nach.filter((k) => ZEIT.includes(k));
    if (zeitSchluessel.length > 1 || (m.nach.includes('serie') && m.nach.includes('folge')) || (m.nach.includes('folge') && !m.serie_id)) throw ungueltig('nach');
    const reihe = zeitSchluessel[0] ?? null;
    if (reihe && ('sortierung' in m || 'limit' in m)) throw ungueltig('sortierung und limit gelten nur ohne Zeitschlüssel');
    if ('sortierung' in m && !['sekunden', 'mal'].includes(m.sortierung)) throw ungueltig('sortierung');
    if ('limit' in m && !(Number.isInteger(m.limit) && m.limit >= 1 && m.limit <= 200)) throw ungueltig('limit');
    const frei = 'von' in m || 'bis' in m;
    if (frei === ('zeitraum' in m) || (frei && !('von' in m && 'bis' in m))) throw ungueltig('zeitraum oder von und bis');
    werPruefen(m.wer);
    if (m.serie_id) holeSerie(m.serie_id);
    const h = heute();
    const erste = G.zeilen.filter((z) => z.tag).map((z) => z.tag).sort()[0] ?? h;
    let von; let bis = h;
    if (frei) { von = m.von; bis = m.bis; } else von = m.zeitraum === 'woche' ? addTage(h, -6) : m.zeitraum === 'monat' ? addTage(h, -29) : m.zeitraum === 'jahr' ? addTage(h, -364) : erste;
    const alles = !frei && m.zeitraum === 'alles';
    const zeilenAlle = G.zeilen.filter((z) => werPasst(m.wer, z) && (!m.serie_id || z.serie === m.serie_id)
      && (z.tag ? z.tag >= von && z.tag <= bis : alles && !reihe));
    const schluessel = (z, k) => (k === 'wer' ? z.wer : k === 'serie' ? z.serie : k === 'folge' ? z.folge : k === 'stunde' ? z.stunde : rasterWert(k, z.tag));
    const gruppen = new Map();
    for (const z of zeilenAlle) {
      const key = JSON.stringify(m.nach.map((k) => schluessel(z, k)));
      const g = gruppen.get(key) ?? { teile: m.nach.map((k) => schluessel(z, k)), sekunden: 0, mal: 0, fertig: 0, folgenFertig: new Set() };
      g.sekunden += z.sekunden; g.mal += z.mal; g.fertig += z.fertig;
      if (z.fertig) g.folgenFertig.add(`${z.serie}/${z.folge}`);
      gruppen.set(key, g);
    }
    const zeile = (g) => {
      const o = {};
      m.nach.forEach((k, i) => { o[k] = g.teile[i]; });
      o.sekunden = g.sekunden; o.mal = g.mal; o.fertig = g.fertig;
      if (m.nach.includes('serie')) {
        const sid = o.serie;
        const sr = b.serien[sid];
        o.name = sr ? sr.name : 'Gelöscht'; o.geloescht = !sr;
        if (!sr) o.serie = null;
      }
      if ((m.nach.includes('serie') || m.serie_id) && !m.nach.includes('folge')) {
        const sr = b.serien[m.nach.includes('serie') ? o.serie : m.serie_id];
        o.folgen_fertig = sr ? [...g.folgenFertig].filter((x) => sr.folgen.some((f) => `${sr.id}/${f.name}` === x)).length : 0;
        o.folgen_gesamt = sr ? sr.folgen.length : 0;
      }
      return o;
    };
    const zeilen = [];
    let weitere = false;
    if (reihe) {
      let raster = [];
      if (reihe === 'stunde') raster = Array.from({ length: 24 }, (_, i) => i);
      else raster = [...new Set(tageZwischen(reihe === 'monat' && alles ? `${erste.slice(0, 7)}-01` : von, bis).map((t) => rasterWert(reihe, t)))];
      if (raster.length > 400) throw ungueltig('mehr als 400 Zeilen');
      const zweit = m.nach.find((k) => k !== reihe) ?? null;
      const leer = (teile) => ({ teile, sekunden: 0, mal: 0, fertig: 0, folgenFertig: new Set() });
      const mitZeit = (r, rest) => (m.nach[0] === reihe ? [r, ...rest] : [...rest, r]);
      if (zweit === 'wer') {
        const quellen = auswahl().map((x) => x.wer).filter((w) => werPasst(m.wer, { wer: w }));
        if (raster.length * quellen.length > 400) throw ungueltig('mehr als 400 Zeilen');
        for (const r of raster) for (const q of quellen) zeilen.push(zeile(gruppen.get(JSON.stringify(mitZeit(r, [q]))) ?? leer(mitZeit(r, [q]))));
      } else if (zweit) {
        for (const r of raster) for (const g of [...gruppen.values()].filter((x) => x.teile[m.nach.indexOf(reihe)] === r)) zeilen.push(zeile(g));
      } else for (const r of raster) zeilen.push(zeile(gruppen.get(JSON.stringify([r])) ?? leer([r])));
    } else {
      const name = (g) => { const z = zeile(g); return String(z.name ?? z.folge ?? quellenName(String(z.wer ?? '')) ?? ''); };
      let liste = [...gruppen.values()];
      liste.sort((x, y) => (m.sortierung === 'mal' ? y.mal - x.mal : y.sekunden - x.sekunden) || name(x).localeCompare(name(y), 'de'));
      const limit = m.limit ?? 50;
      weitere = liste.length > limit;
      liste = liste.slice(0, limit);
      liste.forEach((g) => zeilen.push(zeile(g)));
    }
    const mitDatum = zeilenAlle.filter((z) => z.tag);
    const summe = { sekunden: 0, mal: 0, fertig: 0 };
    for (const z of reihe ? mitDatum : zeilenAlle) { summe.sekunden += z.sekunden; summe.mal += z.mal; summe.fertig += z.fertig; }
    return { zeilen, summe, weitere, wer_auswahl: auswahl(), zeitzone: 'Europe/Berlin', von, bis };
  };

  const zuletzt = (m) => {
    werPruefen(m.wer);
    if ('limit' in m && !(Number.isInteger(m.limit) && m.limit >= 1 && m.limit <= 20)) throw ungueltig('limit');
    const wer = m.wer ?? 'alle_boxen';
    const letzte = new Map();
    for (const z of G.zeilen.filter((x) => x.tag && werPasst(wer, x) && b.serien[x.serie])) {
      const zeit = `${z.tag}T${String(z.stunde).padStart(2, '0')}:30:00Z`;
      if (!letzte.has(z.serie) || letzte.get(z.serie).zeit < zeit) letzte.set(z.serie, { zeit, wer: z.wer });
    }
    const eintraege = [...letzte.entries()].sort((x, y) => y[1].zeit.localeCompare(x[1].zeit)).slice(0, m.limit ?? 10)
      .map(([sid, x]) => ({ ...kurzform(b.serien[sid]), wer: x.wer, zeit: x.zeit }));
    return { eintraege };
  };

  const quelleGueltig = (q) => {
    if (['boxen', 'reinhoeren', 'alle'].includes(q)) return;
    if (typeof q === 'string' && (q.startsWith('box:') || q.startsWith('benutzer:')) && auswahl().some((x) => x.wer === q)) return;
    throw fehler('wer_ungueltig');
  };
  const quellePasst = (q, z) => q === 'alle' || (q === 'boxen' ? z.wer.startsWith('box:') : q === 'reinhoeren' ? z.wer.startsWith('benutzer:') : z.wer === q);

  const verlauf = (m) => {
    if (!b.boxen.some((x) => x.box === m.box)) throw fehler('box_unbekannt');
    if (!(/^\d{4}-\d\d-\d\d$/.test(m.von) && /^\d{4}-\d\d-\d\d$/.test(m.bis)) || m.von > m.bis) throw ungueltig('von und bis');
    if ((Date.parse(m.bis) - Date.parse(m.von)) / 86400000 > 400) throw ungueltig('höchstens 400 Tage');
    if (b.technikVerlauf?.[m.box]) return structuredClone(b.technikVerlauf[m.box]);
    const ende = `${m.bis}T12:00:00Z`;
    const stunde = (tag, h, min = 0) => `${tag}T${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}:00Z`;
    const tage = tageZwischen(m.von, m.bis);
    const ladevorgaenge = tage.map((t, i) => (i === tage.length - 1 ? { beginn: stunde(t, 9), ende: null, dauer_s: null } : { beginn: stunde(t, 20), ende: stunde(addTage(t, 1), 0, 10 + (i % 3) * 20), dauer_s: 15000 + (i % 3) * 1200 }));
    const laufzeiten = tage.slice(0, -1).map((t, i) => ({ von: stunde(addTage(t, 1), 0, 10 + (i % 3) * 20), bis: stunde(addTage(t, 1), 20), dauer_s: 70000 - (i % 4) * 3600 }));
    return { ladevorgaenge, laufzeiten, verbindung: [{ zeit: stunde(m.von, 7), online: true }, { zeit: stunde(addTage(m.bis, -1), 21), online: false }, { zeit: stunde(m.bis, 7), online: true }],
      syncs: [{ zeit: stunde(m.bis, 7, 5), ok: true, code: null }], fehler: [], verworfen: [{ zeit: stunde(m.von, 12), gesamt: 2 }, { zeit: ende, gesamt: 5 }], weitere: false };
  };

  const akku = (m) => {
    const out = {};
    const von = typeof m.start_time === 'string' ? Date.parse(m.start_time) : m.start_time;
    const bis = m.end_time ? (typeof m.end_time === 'string' ? Date.parse(m.end_time) : m.end_time) : von + 7 * 86400000;
    for (const id of m.statistic_ids) {
      if (!b.akkuEntitaeten?.includes(id)) continue;
      const l = [];
      for (let t = Math.floor(von / 3600000) * 3600000, i = 0; t < bis; t += 3600000, i += 1) {
        const h = i % 24;
        const wert = h < 5 ? 40 + h * 12 : Math.max(8, 100 - (h - 5) * 4.6);
        l.push({ start: t, end: t + 3600000, mean: Math.round(wert * 10) / 10, min: Math.round((wert - 2) * 10) / 10, max: Math.round((wert + 2) * 10) / 10 });
      }
      out[id] = l;
    }
    return out;
  };

  return {
    'tobibox/gehoert/zusammenfassung': zusammenfassung,
    'tobibox/gehoert/zuletzt': zuletzt,
    'tobibox/technik/verlauf': verlauf,
    'tobibox/gehoert/exportieren': (m) => { quelleGueltig(m.quelle); b.gehoert.exporte = [...(b.gehoert.exporte ?? []), m.quelle]; return { pfad: `/api/tobibox/export/u-admin/${encodeURIComponent(m.quelle)}?authSig=mock-export` }; },
    'tobibox/gehoert/loeschen': (m) => {
      quelleGueltig(m.quelle);
      if ('trocken' in m && typeof m.trocken !== 'boolean') throw ungueltig('trocken');
      if (!m.trocken && !['LÖSCHEN', 'LOESCHEN'].includes(m.bestaetigung)) throw ungueltig('bestaetigung');
      const betroffen = G.zeilen.filter((z) => quellePasst(m.quelle, z));
      if (!m.trocken) { G.zeilen = G.zeilen.filter((z) => !quellePasst(m.quelle, z)); G.loeschungen.push(m.quelle); emit('gehoert', 'geaendert', {}); }
      return { anzahl: betroffen.length };
    },
    'tobibox/favorit/set': (m) => {
      const s = holeSerie(m.serie_id);
      if ('folge' in m) holeFolge(s, m.folge);
      if (typeof m.an !== 'boolean') throw ungueltig('an');
      const folge = m.folge ?? null;
      const da = istFavorit(s.id, folge);
      if (m.an && !da) {
        if (b.favoriten.length >= (opts.favoritenMax ?? 1000)) throw fehler('zu_viele_favoriten');
        b.favoriten.unshift({ serie_id: s.id, folge, gesetzt_von: { id: 'u1', name: 'Person A' }, gesetzt_am: new Date().toISOString() });
      } else if (!m.an && da) b.favoriten = b.favoriten.filter((x) => !(x.serie_id === s.id && (x.folge ?? null) === folge));
      if (m.an !== da) emit('favoriten', 'geaendert', { serie_id: s.id, folge, an: m.an });
      return { an: m.an };
    },
    'tobibox/favoriten/list': () => ({ eintraege: b.favoriten.filter((x) => b.serien[x.serie_id] && (x.folge === null || b.serien[x.serie_id].folgen.some((f) => f.name === x.folge))).map((x) => structuredClone(x)) }),
    'recorder/statistics_during_period': akku,
  };
}

/* ---- Online-Suche (Vertrag W 3.15, 4.11, 14.2; Design docs/designs/online-suche.md): Befehle 57 bis 64 im Arbeitsspeicher.
 * Zustand in `b.online`:
 *   suchTreffer   Vorlagen für Nr. 57 (Liste von { quelle, titel, reihe?, nummer?, tracks?, art?, hat_cover?, frueher_abgelehnt?, werte: { <feld>[@<folge>]: Wert }, sicher?: { <feld>: bool } });
 *                 ohne Angabe liefert der Mock drei Treffer, die aus dem Eintrag gebildet werden. `werte.cover` ist `true`.
 *   treffer       gehaltene Treffer (treffer_id → { serie_id, folge, werte, sicher, quelle, hat_cover, abgelaufen }); `abgelaufen: true` oder Löschen lässt `treffer_abgelaufen` kommen (410)
 *   vorschlaege   serie_id → [{ id, art: 'felder'|'zusammenfuehren', quelle, felder, werte?, name?, grund?, ziel_serie_id?, zeit }]
 *   aenderungen   [{ id, serie_id, lauf_id, felder, vorher, nachher, zeit, status }]
 *   quellen       Antwort von Nr. 57 je Quelle (`ok`, `pause`, `fehler`); `quellenStatus` überschreibt Teile von `quellen` in Nr. 63
 *   lauf, laeufe  der laufende Lauf (oder null) und die letzten fünf beendeten
 *   plaetze       gehaltene `vorschau_id` von Vorschlägen mit Cover (T10, eigener Speicher): höchstens `O.plaetzeMax` (4), die älteste wird `abgelaufen` (HTTP 410); `suchPlaetze`: je Suche ein Platz, ebenfalls höchstens 4 (getrennt von den Vorschauen)
 *   listeMax      Obergrenze der Liste von Nr. 65 (Vertrag: 500; Tests setzen weniger, dann `weitere = true`)
 * Rechte wie im Backend: Nr. 57 bis 63 admin (in `verarbeite`), Nr. 64 für alle; Werte kommen nie aus der Eingabe. */
const OS_FELDER = ['serie_name', 'folge_titel', 'nummer', 'art', 'cover', 'beschreibung', 'alter_ab'];
const teileKeyOs = (k) => { const i = k.indexOf('@'); return i < 0 ? [k, null] : [k.slice(0, i), k.slice(i + 1)]; };

function kuerzeAmSatz(text, n = 300) {
  if (text.length <= n) return text;
  const stuck = text.slice(0, n);
  const punkt = Math.max(stuck.lastIndexOf('. '), stuck.lastIndexOf('! '), stuck.lastIndexOf('? '));
  return punkt > 0 ? stuck.slice(0, punkt + 1) : stuck.slice(0, stuck.lastIndexOf(' ')).trimEnd();
}

/* Die Ausgabefelder einer Folge (Vertrag 3.2): `beschreibung` höchstens 300 Zeichen am Satzende, `beschreibung_gekuerzt`, `beschreibung_quelle`; `beschreibung_voll` bleibt im Mock. */
export function folgeMitOnline(f) {
  const { beschreibung_voll: voll, ...rest } = f;
  const text = voll ?? f.beschreibung;
  if (typeof text !== 'string' || !text) return rest;
  const kurz = kuerzeAmSatz(text);
  return { ...rest, beschreibung: kurz, beschreibung_gekuerzt: kurz.length < text.length, beschreibung_quelle: f.beschreibung_quelle ?? 'tonies_shop' };
}

function onlineBefehle({ b, hat, emit, holeSerie, holeFolge, stand, kurzform, istAdmin }) {
  const O = b.online;
  const ungueltig = (t) => fehler('invalid_format', t);
  const jetzt = () => new Date(Date.now()).toISOString();
  const vorhandeneVorschlaege = (sid) => O.vorschlaege[sid] ?? [];

  /* Wert des Felds heute (`heute`): Name, Art, Folgentitel, Nummer, Beschreibung, Alter; Cover: die Quelle des heutigen Covers. */
  const heute = (s, key) => {
    const [feld, fn] = teileKeyOs(key);
    if (feld === 'serie_name') return s.name;
    if (feld === 'art') return s.art ?? null;
    if (feld === 'cover') return s.cover_stand ? (s.cover_quelle ?? 'auto') : null;
    const f = holeFolge(s, fn);
    if (feld === 'folge_titel') return f.anzeige;
    if (feld === 'nummer') return f.nummer ?? null;
    if (feld === 'beschreibung') return f.beschreibung_voll ?? f.beschreibung ?? null;
    if (feld === 'alter_ab') return f.alter_ab ?? null;
    return null;
  };
  const schreibe = (s, key, wert, quelle) => {
    const [feld, fn] = teileKeyOs(key);
    if (feld === 'serie_name') { s.name = wert; s.pruefen = false; return; }
    if (feld === 'art') { s.art = wert; s.art_quelle = 'online'; return; }
    if (feld === 'cover') {
      if (s.cover_quelle === 'eigen') { s.cover_online_da = true; return; } // Vorrang: eigenes Foto vor Online-Cover
      if (s.cover_quelle !== 'online') s.cover_auto = s.cover_stand ?? null;
      s.cover_stand = hex(`online-${s.id}-${++O.zaehler}`, 8); s.cover_quelle = 'online';
      return;
    }
    const f = holeFolge(s, fn);
    if (feld === 'folge_titel') f.anzeige = wert;
    else if (feld === 'nummer') f.nummer = wert;
    else if (feld === 'beschreibung') { f.beschreibung_voll = wert; delete f.beschreibung; f.beschreibung_quelle = quelle === 'itunes' ? 'itunes' : 'tonies_shop'; } else if (feld === 'alter_ab') f.alter_ab = wert;
  };
  const sieHand = (s, key) => (s.hand ?? []).includes(key);

  const standardTreffer = (s, folge) => {
    const f = folge ? s.folgen.find((x) => x.name === folge) : null;
    const folgenWerte = f ? { [`folge_titel@${f.name}`]: `${f.anzeige} (Neu)`, [`nummer@${f.name}`]: (f.nummer ?? 0) + 1, [`beschreibung@${f.name}`]: 'Ein Hörspiel über eine kleine Reise. Es gibt viel zu entdecken.', [`alter_ab@${f.name}`]: 5 } : {};
    return [
      { quelle: 'itunes', titel: `${s.name} (Apple)`, reihe: s.name, nummer: 1, tracks: 12, art: 'hoerspiel', hat_cover: true, werte: { art: 'hoerspiel', cover: true, ...folgenWerte }, sicher: { art: true, cover: true } },
      { quelle: 'tonies', titel: `${s.name} (Tonies)`, reihe: s.name, tracks: 8, art: 'hoerspiel', hat_cover: true, werte: { serie_name: `${s.name} Neu`, cover: true }, sicher: { cover: true } },
      { quelle: 'itunes', titel: `${s.name} (Album)`, reihe: null, art: 'musik', hat_cover: false, frueher_abgelehnt: true, werte: { art: 'musik' }, sicher: {} },
    ];
  };

  const status = () => ({
    lauf: O.lauf ? structuredClone(O.lauf) : null,
    quellen: { itunes: { erreichbar: true }, tonies: { erreichbar: true }, tonies_shop: { erreichbar: true }, claude: { eingerichtet: true, erreichbar: true }, ...(O.quellenStatus || {}) },
    tonie_liste: O.tonieListe === undefined ? { stand: '2026-11-12T08:00:00Z', anzahl: 1234 } : O.tonieListe,
    letzte_laeufe: structuredClone(O.laeufe),
  });

  /* alle Felder einer Änderung zurücknehmen: nur, wo noch der Online-Wert steht (sonst `seitdem_geaendert`) */
  const nimmZurueck = (a) => {
    const s = b.serien[a.serie_id];
    const uebersprungen = [];
    let zurueck = 0;
    if (!s) { return { zurueck, uebersprungen: a.felder.map((feld) => ({ serie_id: a.serie_id, feld, grund: 'serie_nicht_gefunden' })) }; }
    for (const key of a.felder) {
      let aktuell;
      try { aktuell = heute(s, key); } catch { uebersprungen.push({ serie_id: s.id, feld: key, grund: 'folge_verschoben' }); continue; }
      const [feld] = teileKeyOs(key);
      const gleichNachher = feld === 'cover' ? aktuell === 'online' : gleich(aktuell, a.nachher[key]);
      if (!gleichNachher) { uebersprungen.push({ serie_id: s.id, feld: key, grund: 'seitdem_geaendert' }); continue; }
      if (feld === 'cover') { s.cover_stand = s.cover_auto ?? null; s.cover_quelle = s.cover_stand ? 'auto' : null; } else if (feld === 'art') { s.art = a.vorher[key]; s.art_quelle = 'manuell'; } else {
        const [, fn] = teileKeyOs(key);
        if (feld === 'serie_name') s.name = a.vorher[key];
        else {
          const f = holeFolge(s, fn);
          if (feld === 'folge_titel') f.anzeige = a.vorher[key];
          else if (feld === 'nummer') f.nummer = a.vorher[key];
          else if (feld === 'beschreibung') { delete f.beschreibung_voll; if (a.vorher[key] == null) delete f.beschreibung; else f.beschreibung = a.vorher[key]; } else if (feld === 'alter_ab') { if (a.vorher[key] == null) delete f.alter_ab; else f.alter_ab = a.vorher[key]; }
        }
      }
      s.hand = (s.hand ?? []).filter((k) => k !== key);
      zurueck += 1;
    }
    if (zurueck > 0) a.status = 'zurueckgenommen'; // wie das Backend: ganz übersprungen bleibt `fertig`
    const rest = O.aenderungen.filter((x) => x.serie_id === s.id && x.status === 'fertig').sort((x, y) => y.zeit.localeCompare(x.zeit));
    s.online = rest[0] ? { zeit: rest[0].zeit, felder: [...new Set(rest[0].felder.map((k) => teileKeyOs(k)[0]))] } : null;
    return { zurueck, uebersprungen };
  };

  const befehle = {
    'tobibox/online/suchen': (m) => {
      const s = holeSerie(m.serie_id);
      if (s.typ !== 'normal') throw ungueltig('Überraschungs-Serie');
      if (m.folge !== undefined) holeFolge(s, m.folge);
      if ('text' in m && !(typeof m.text === 'string' && m.text.trim().length >= 2 && m.text.length <= 100)) throw ungueltig('text mit 2 bis 100 Zeichen');
      const q = { itunes: 'ok', tonies: 'ok', ...(O.quellen || {}) };
      if (q.itunes !== 'ok' && q.tonies !== 'ok' && !(O.suchTreffer || []).length) throw fehler('online_nicht_erreichbar');
      O.suchen.push({ serie_id: s.id, folge: m.folge ?? null, text: m.text ?? null });
      const vorlagen = (O.suchTreffer ?? standardTreffer(s, m.folge)).filter((t) => q[t.quelle] === 'ok' || (q[t.quelle] === undefined));
      const suchId = `such-${++O.zaehler}`; // wie das Backend: ein Platz je Suche (bis zu 10 Treffer teilen ihn), die älteste Suche fliegt
      O.suchPlaetze.push(suchId);
      while (O.suchPlaetze.length > O.plaetzeMax) { const alt = O.suchPlaetze.shift(); for (const x of Object.values(O.treffer)) if (x.suchId === alt) x.abgelaufen = true; }
      const treffer = vorlagen.slice(0, 10).map((t) => {
        const id = hex(`treffer-${++O.zaehler}`, 16);
        const werte = Object.fromEntries(Object.entries(t.werte).filter(([k]) => m.folge !== undefined || s.folgen.length === 1 || !k.includes('@'))); // ohne Folge keine Folgenfelder
        O.treffer[id] = { serie_id: s.id, folge: m.folge ?? null, quelle: t.quelle, werte, sicher: t.sicher ?? {}, hat_cover: t.hat_cover !== false && 'cover' in werte, titel: t.titel };
        O.treffer[id].suchId = suchId;
        return { treffer_id: id, quelle: t.quelle, titel: t.titel, reihe: t.reihe ?? null, ...(t.nummer != null ? { nummer: t.nummer } : {}), ...(t.tracks != null ? { tracks: t.tracks } : {}),
          ...(t.art ? { art: t.art } : {}), hat_cover: O.treffer[id].hat_cover, frueher_abgelehnt: !!t.frueher_abgelehnt, felder: Object.keys(werte) };
      });
      return { treffer, quellen: { itunes: q.itunes, tonies: q.tonies } };
    },
    'tobibox/online/treffer': (m) => {
      const mitTreffer = m.treffer_id !== undefined;
      const mitVorschlag = m.vorschlag_id !== undefined;
      if (mitTreffer === mitVorschlag || (mitVorschlag && m.serie_id === undefined) || (mitTreffer && m.serie_id !== undefined)) throw ungueltig('treffer_id oder serie_id mit vorschlag_id');
      let s; let werte; let sicher; let grund; let cover = true; let istVorschlag = false;
      if (mitTreffer) {
        const t = O.treffer[m.treffer_id];
        if (!t || t.abgelaufen || t.quelle === 'vorschlag') throw fehler('treffer_abgelaufen'); // eine vorschau_id ist kein Treffer
        s = holeSerie(t.serie_id); werte = t.werte; sicher = t.sicher;
        cover = t.hat_cover;
      } else {
        s = holeSerie(m.serie_id);
        const v = vorhandeneVorschlaege(s.id).find((x) => x.id === m.vorschlag_id);
        if (!v || v.art !== 'felder') throw fehler('vorschlag_nicht_gefunden');
        werte = v.werte ?? Object.fromEntries(v.felder.map((k) => [k, k === 'cover' ? true : v.name ?? null]));
        sicher = {};
        if (v.quelle === 'claude') grund = v.grund;
        cover = v.bildFehlt !== true;
        istVorschlag = true;
      }
      const felder = {};
      for (const [key, neu] of Object.entries(werte)) {
        const [feld] = teileKeyOs(key);
        if (feld === 'cover') { if (cover) felder[key] = { heute: heute(s, key), neu: true, sicher: !!sicher[key], hand: sieHand(s, key) || s.cover_quelle === 'eigen' }; continue; }
        const h = heute(s, key);
        if (gleich(h, neu)) continue; // gleiche Werte fehlen
        felder[key] = { heute: h, neu: feld === 'beschreibung' ? String(neu).slice(0, 2000) : neu, sicher: !!sicher[key], hand: sieHand(s, key) };
      }
      let vorschauId; // Vertrag 3.15, Nr. 58 (T10): nur bei einem Vorschlag, dessen Übersicht `cover` enthält; jede Abfrage eine neue Kennung
      if (istVorschlag && felder.cover) {
        vorschauId = hex(`vorschau-${++O.zaehler}`, 16);
        O.treffer[vorschauId] = { serie_id: s.id, folge: null, quelle: 'vorschlag', werte: {}, sicher: {}, hat_cover: true, titel: '' };
        O.plaetze.push(vorschauId);
        while (O.plaetze.length > O.plaetzeMax) { const alt = O.plaetze.shift(); if (O.treffer[alt]) O.treffer[alt].abgelaufen = true; }
      }
      return { felder, ...(grund ? { grund } : {}), ...(vorschauId ? { vorschau_id: vorschauId } : {}) };
    },
    'tobibox/online/uebernehmen': (m) => {
      const mitTreffer = m.treffer_id !== undefined;
      const mitVorschlag = m.vorschlag_id !== undefined;
      if (mitTreffer === mitVorschlag) throw ungueltig('treffer_id oder vorschlag_id');
      const s = holeSerie(m.serie_id);
      let werte; let quelle; let v = null;
      if (mitTreffer) {
        const t = O.treffer[m.treffer_id];
        if (!t || t.abgelaufen || t.quelle === 'vorschlag') throw fehler('treffer_abgelaufen'); // eine vorschau_id ist kein Treffer
        werte = t.werte; quelle = t.quelle;
      } else {
        v = vorhandeneVorschlaege(s.id).find((x) => x.id === m.vorschlag_id);
        if (!v) throw fehler('vorschlag_nicht_gefunden');
        if (v.art !== 'felder') throw ungueltig('Vorschlag zum Zusammenführen: Nr. 27');
        werte = v.werte ?? Object.fromEntries(v.felder.map((k) => [k, k === 'cover' ? true : v.name ?? null]));
        quelle = v.quelle;
      }
      if (!Array.isArray(m.felder) || !m.felder.length || m.felder.length > s.folgen.length * 4 + 3 || m.felder.some((k) => typeof k !== 'string' || !OS_FELDER.includes(teileKeyOs(k)[0]))) throw ungueltig('felder');
      const felder = [...new Set(m.felder)];
      if (felder.some((k) => !(k in werte))) throw ungueltig('Feld nicht angeboten');
      if (felder.includes('serie_name') && m.stand === undefined) throw ungueltig('stand ist Pflicht bei serie_name');
      for (const k of felder) { const [, fn] = teileKeyOs(k); if (fn !== null) holeFolge(s, fn); }
      if (m.stand !== undefined && m.stand !== stand(s)) throw fehler('stand_veraltet');
      if (felder.includes('serie_name') && !String(werte.serie_name ?? '').trim()) throw fehler('name_ungueltig');
      const claudeName = quelle === 'claude' && felder.length === 1 && felder[0] === 'serie_name';
      const vorher = {}; const nachher = {};
      for (const k of felder) {
        vorher[k] = heute(s, k);
        schreibe(s, k, werte[k], quelle);
        nachher[k] = heute(s, k);
        if (!claudeName) s.hand = [...new Set([...(s.hand ?? []), k])]; // eine Übernahme von Hand: die Felder gelten danach als von Hand
      }
      let id = null;
      if (!claudeName) {
        id = hex(`aenderung-${++O.zaehler}`, 12);
        const zeit = jetzt();
        O.aenderungen.push({ id, serie_id: s.id, lauf_id: null, felder, vorher, nachher, zeit, status: 'fertig' });
        s.online = { zeit, felder: [...new Set(felder.map((k) => teileKeyOs(k)[0]))] };
      }
      if (v) {
        v.felder = (v.felder || []).filter((k) => !felder.includes(k));
        if (!v.felder.length) O.vorschlaege[s.id] = vorhandeneVorschlaege(s.id).filter((x) => x !== v);
      }
      emit('medien', 'serien_geaendert', { serie_id: s.id });
      return { aenderung_id: id, serie_id: s.id, stand: stand(s) };
    },
    'tobibox/online/zuruecknehmen': (m) => {
      const form = [m.serie_id !== undefined && m.aenderung_id !== undefined ? 'aenderung' : m.serie_id !== undefined && m.lauf_id === undefined && m.aenderung_id === undefined ? 'serie' : m.lauf_id !== undefined && m.serie_id === undefined && m.aenderung_id === undefined ? 'lauf' : 'falsch'][0];
      if (form === 'falsch') throw ungueltig('eine der drei Formen');
      if (form === 'lauf') {
        if (![...O.laeufe, ...(O.lauf ? [O.lauf] : [])].some((l) => l.lauf_id === m.lauf_id)) throw fehler('lauf_nicht_gefunden');
        const liste = O.aenderungen.filter((a) => a.lauf_id === m.lauf_id && a.status === 'fertig');
        setTimeout(() => { // läuft im Hintergrund, das Ergebnis kommt als Ereignis
          let uebersprungen = 0; let zurueck = 0;
          liste.forEach((a, i) => { const r = nimmZurueck(a); zurueck += r.zurueck; uebersprungen += r.uebersprungen.length; emit('online', 'stand', { vorgang: 'zuruecknahme', lauf_id: m.lauf_id, zustand: 'laeuft', erledigt: i + 1, gesamt: liste.length, zurueckgenommen: zurueck, uebersprungen_anzahl: uebersprungen }); });
          emit('online', 'fertig', { vorgang: 'zuruecknahme', lauf_id: m.lauf_id, zustand: 'fertig', erledigt: liste.length, gesamt: liste.length, zurueckgenommen: zurueck, uebersprungen_anzahl: uebersprungen });
        }, 5);
        return { gestartet: true };
      }
      const s = holeSerie(m.serie_id);
      let liste = O.aenderungen.filter((a) => a.serie_id === s.id && a.status === 'fertig');
      if (form === 'aenderung') {
        const a = O.aenderungen.find((x) => x.serie_id === s.id && x.id === m.aenderung_id);
        if (!a) throw fehler('aenderung_nicht_gefunden');
        liste = a.status === 'fertig' ? [a] : [];
      }
      let zurueck = 0; const uebersprungen = [];
      for (const a of liste) { const r = nimmZurueck(a); zurueck += r.zurueck; uebersprungen.push(...r.uebersprungen); }
      emit('medien', 'serien_geaendert', { serie_id: s.id });
      return { zurueckgenommen: zurueck, uebersprungen: uebersprungen.slice(0, 50), uebersprungen_anzahl: uebersprungen.length };
    },
    'tobibox/online/vorschlag_verwerfen': (m) => {
      const s = holeSerie(m.serie_id);
      const v = vorhandeneVorschlaege(s.id).find((x) => x.id === m.vorschlag_id);
      if (!v) throw fehler('vorschlag_nicht_gefunden');
      O.vorschlaege[s.id] = vorhandeneVorschlaege(s.id).filter((x) => x !== v);
      O.verworfen.push({ serie_id: s.id, vorschlag_id: v.id });
      emit('medien', 'serien_geaendert', { serie_id: s.id });
      return {};
    },
    'tobibox/online/lauf': (m) => {
      if (!['start', 'stop'].includes(m.aktion)) throw ungueltig('aktion');
      if (m.aktion === 'start') {
        if (O.lauf) throw fehler('lauf_laeuft_schon');
        O.lauf = { lauf_id: hex(`lauf-${++O.zaehler}`, 12), zustand: 'laeuft', erledigt: 0, gesamt: O.gesamt ?? 340, geaendert: 0, vorschlaege: 0, keiner: 0 };
        O.laufBeginn = jetzt();
        return { lauf: structuredClone(O.lauf) };
      }
      if (!O.lauf) return { lauf: null };
      O.lauf.zustand = 'wird_angehalten';
      return { lauf: structuredClone(O.lauf) };
    },
    'tobibox/online/status': () => status(),
    'tobibox/online/lauf_aenderungen': (m) => { // Vertrag 3.15, Nr. 65 (T11): je Änderung des Laufs ein Eintrag, nach Namen sortiert, `fertig` und `zurueckgenommen`
      if (typeof m.lauf_id !== 'string' || !m.lauf_id) throw ungueltig('lauf_id');
      if (![...O.laeufe, ...(O.lauf ? [O.lauf] : [])].some((l) => l.lauf_id === m.lauf_id)) throw fehler('lauf_nicht_gefunden');
      const alle = O.aenderungen.filter((a) => a.lauf_id === m.lauf_id && ['fertig', 'zurueckgenommen'].includes(a.status) && a.felder.length && b.serien[a.serie_id])
        .map((a) => ({ serie_id: a.serie_id, name: b.serien[a.serie_id].name, aenderung_id: a.id, zeit: a.zeit, status: a.status, felder: [...a.felder] }))
        .sort((x, y) => x.name.localeCompare(y.name, 'de') || x.aenderung_id.localeCompare(y.aenderung_id));
      const max = O.listeMax ?? 500;
      return { eintraege: alle.slice(0, max), weitere: alle.length > max };
    },
    'tobibox/online/beschreibung': (m) => {
      const s = holeSerie(m.serie_id);
      const f = holeFolge(s, m.folge);
      const text = f.beschreibung_voll ?? f.beschreibung ?? null;
      if (!text) return { beschreibung: null, quelle: null };
      return { beschreibung: String(text).slice(0, 2000), ...(Number.isInteger(f.alter_ab) ? { alter_ab: f.alter_ab } : {}), quelle: f.beschreibung_quelle ?? 'tonies_shop' };
    },
  };
  return { befehle, status };
}

export function createMockHass(opts = {}) {
  const darf = opts.darf ?? true;
  const istAdmin = opts.istAdmin ?? (opts.nichtAdmin ? false : darf); // Administrator? (`darf: true, istAdmin: false` = Alltag: schreiben ja, Technik nein)
  const calls = []; // { type, msg } in der Reihenfolge des Eingangs
  const overrides = new Map(); // type -> Funktion (msg, b) => Ergebnis
  const failures = new Map(); // type -> [code…]
  const subs = [];
  const xhrs = [];
  let nextId = 1;

  /* ---- Backend im Arbeitsspeicher ---- */
  const folge = (name, anzeige, extra = {}) => ({ name, anzeige: anzeige ?? name.replace(/\.[^.]+$/, ''), nummer: null, datum: null, art: 'datei', tracks: 1,
    groesse_bytes: 5 * 1048576, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });
  const b = {
    konfig: { revision: 7, liste_id: 'liste-aaaa', zustand: 'ok', export_ok: true, export_geschrieben_am: '2026-11-09T08:00:00Z' },
    serien: {
      s1: { id: 's1', name: 'Die drei ???', typ: 'normal', ordner: 'Die drei ???', pruefen: false, hinweise: [],
        folgen: [folge('folge-01.mp3', 'Der Rabe'), folge('folge-02.mp3', 'Das Gespensterschloss'), folge('folge-03.mp3', 'Der Super-Papagei')] },
      s2: { id: 's2', name: 'Bibi Blocksberg', typ: 'normal', ordner: 'Bibi', pruefen: true, hinweise: [], folgen: [folge('b-01.mp3', 'Hexen gibt es doch', { pruefen: true, pruefen_gruende: ['tags_fehlen'] })] },
      s3: { id: 's3', name: 'Überraschung', typ: 'ueberraschung', ordner: 'Ueberraschung', pruefen: false, hinweise: [], folgen: [folge('u-01.mp3', 'Zufall')] },
    },
    ueberraschung: 'ok',
    zuordnungen: {
      '04A1B2C3D4E5F6': { uid: '04A1B2C3D4E5F6', name: 'Anna', ziel: { typ: 'serie', serie: 's1' } },
      '04FFEEDDCCBBAA': { uid: '04FFEEDDCCBBAA', name: null, ziel: { typ: 'folge', serie: 's1', folge: 'folge-02.mp3' } },
    },
    neueTobies: [{ uid: '0499887766554433', zuerst: '2026-11-09T07:00:00Z', zuletzt: '2026-11-09T07:05:00Z', anzahl: 2, boxen: { kueche: { zuerst: '2026-11-09T07:00:00Z', zuletzt: '2026-11-09T07:05:00Z', anzahl: 2, zeit_ok: true } } }],
    papierkorb: [{ id: 'aabbccddeeff', typ: 'folge', serie_id: 's1', serie_name: 'Die drei ???', folge: 'folge-09.mp3', anzeige: 'Alte Folge', art: 'datei', tracks: 1, groesse_bytes: 4000000, grund: 'manuell', geloescht_am: '2026-11-08T10:00:00Z' }],
    boxen: [
      { box: 'kueche', anzeigename: 'Küche', online: true, status: { speicher_frei_mb: 5120, netz: 'heim', akku_prozent: 80, version: '0.3.1', sync: { ergebnis: 'ok' }, letzter_fehler: null, konfig: { liste_id: 'liste-aaaa', revision: 7 } }, status_empfangen_am: '2026-11-09T08:00:00Z', konfig_stand: 'aktuell', lernmodus: null, ereignisse: [{ id: 'e1', ts: '2026-11-09T07:00:00Z', art: 'liste_abgelehnt', daten: {}, text: 'Die Box Küche hat eine Liste abgelehnt.' }] },
      { box: 'kinderzimmer', anzeigename: 'Kinderzimmer', online: false, status: { speicher_frei_mb: 900, konfig: { liste_id: 'liste-aaaa', revision: 5 } }, status_empfangen_am: '2026-11-08T20:00:00Z', konfig_stand: 'veraltet', lernmodus: null, ereignisse: [] },
    ],
    eingang: [{ id: '111111111111', name: 'Hoerbuch Neu', art: 'ordner', dateien: 3, ignoriert: 1, groesse_bytes: 90000000, zuerst_gesehen: '2026-11-09T07:30:00Z', geaendert_am: '2026-11-09T07:29:00Z', status: 'blockiert', hinweise: [{ code: 'kopierschutz', datei: 'a.m4b', text: 'Die Datei ist kopiergeschützt.' }], ergebnis: [], fertig_am: null }],
    eingangErledigt: [],
    neuGesperrt: new Set(), // A11c: Einträge, an deren Folgen schon etwas geändert wurde (`einsortierung/neu` → `neu_einsortieren_nicht_moeglich`)
    neuNach: null, // A11c: optional `(eintrag, wunsch) => …`, ruft der Mock nach einem angenommenen `einsortierung/neu` (der Browser-Mock lässt damit das Ergebnis kommen)
    warteschlange: [], // A9: Vormerkungen in der Reihenfolge der Anlage
    wsNr: 0,
    sigZaehler: 0,
    lern: null,
    exportDatei: { vorhanden: true, liste_id: 'liste-aaaa', revision: 9, exportiert_am: '2026-11-09T09:00:00Z', anzahl_zuordnungen: 4, anzahl_fenster: 0, neuer_als_ha: true },
    gesehenAnfragen: new Map(),
    hoerstellen: {}, // A-2: Serie → { zeit, folge, folgen: { Name → { p, d, t, fertig, track } } } (ein Benutzer)
    einstellungen: { leise_zeiten: { zeitzone: 'Europe/Berlin', fenster: [] }, gute_nacht: { timer_min: 30, ausblenden_s: 60 }, lesezeichen_tage: 14 },
  };

  if (opts.leer) { b.serien = {}; b.zuordnungen = {}; }
  if (opts.eingang) b.eingang = opts.eingang; // A11b: Einträge, die noch im Eingang liegen (`eingangEintrag()`); sonst der Grundbestand
  if (opts.eingangErledigt) b.eingangErledigt = opts.eingangErledigt; // … und die letzten einsortierten
  if (opts.viele) Object.assign(b, beispielBibliothek(opts.viele === true ? 130 : opts.viele));

  /* Stufe B: Fähigkeiten, Hördaten (`b.gehoert.zeilen`, siehe `beispielGehoert`) und Sterne (`b.favoriten`) */
  const hat = (name) => (opts.faehigkeiten || FAEHIGKEITEN).includes(name);
  b.favoriten = [];
  b.online = { suchTreffer: opts.onlineTreffer ?? null, treffer: {}, vorschlaege: {}, aenderungen: [], laeufe: [], lauf: null, quellen: null, quellenStatus: null, tonieListe: undefined, verworfen: [], suchen: [], zaehler: 0, gesamt: opts.onlineGesamt, plaetze: [], suchPlaetze: [], plaetzeMax: 4, listeMax: opts.onlineListeMax };
  b.gehoert = { heute: opts.heute ?? ISO(new Date(MOCK_JETZT)), zeilen: [], personen: { u1: 'Person A', u2: 'Person B' }, loeschungen: [] };
  const istFavorit = (sid, folge = null) => b.favoriten.some((x) => x.serie_id === sid && (x.folge ?? null) === folge);
  const zuletztGehoertAm = (sid) => {
    const l = b.gehoert.zeilen.filter((z) => z.serie === sid && z.wer.startsWith('box:'));
    if (!l.length) return null;
    return l.map((z) => `${z.tag}T${String(z.stunde).padStart(2, '0')}:30:00Z`).sort().at(-1);
  };
  const stand = (s) => hex(JSON.stringify([s.name, s.folgen.map((f) => [f.name, f.anzeige])]));
  /* Eintrags-Alter (Altersfilter 2.): `alter_hand`, sonst der kleinste gültige Shop-Wert (`alter_ab`) der Folgen, sonst keins. */
  const eintragsAlter = (s) => {
    if (ALTER_OK(s.alter_hand)) return s.alter_hand;
    const w = s.folgen.map((f) => f.alter_ab).filter(ALTER_OK);
    return w.length ? Math.min(...w) : null;
  };
  const kurzform = (s) => ({
    id: s.id, name: s.name, typ: s.typ, ordner: s.ordner, anzahl_folgen: s.folgen.length,
    anzahl_tobies: tobiesAuf(s.id).length, angelegt_am: s.angelegt_am ?? '2026-10-01T10:00:00Z', stand: stand(s),
    pruefen: s.pruefen, anzahl_pruefen: s.folgen.filter((f) => f.pruefen).length, hinweise: s.hinweise,
    art: s.art ?? 'hoerspiel', art_quelle: s.art_quelle ?? (s.art ? 'manuell' : 'tags'), einzeln: !!s.einzeln, kapitel_anzahl: s.kapitel_anzahl ?? 0,
    dauer_s: s.dauer_s ?? null, cover_stand: s.cover_stand ?? null, cover_quelle: s.cover_stand ? (s.cover_quelle ?? 'auto') : null,
    ...(hoerKurz(s) ? { hoerstelle: hoerKurz(s) } : {}),
    ...(eintragsAlter(s) !== null ? { alter_ab: eintragsAlter(s) } : {}), // Ausgabefelder brauchen keine Fähigkeit (Vertrag 14.1)
    ...(ALTER_OK(s.alter_hand) ? { alter_hand: s.alter_hand } : {}),
    ...(hat('favoriten') ? { favorit: istFavorit(s.id) } : {}),
    ...(hat('gehoert') ? { zuletzt_gehoert_am: zuletztGehoertAm(s.id) } : {}),
    ...(hat('online_suche') ? { online: s.online ?? null } : {}), // Vertrag 14.2: für alle Benutzer
  });
  /* `online_vorschlaege` nur für Administratoren und nur in serien/list, serie/get (Vertrag 14.2). */
  const kurzMitVorschlaegen = (s) => ({ ...kurzform(s), ...(hat('online_suche') && istAdmin ? { online_vorschlaege: (b.online.vorschlaege[s.id] ?? []).length } : {}) });
  /* Hörstelle des Anfragenden (Vertrag 14.2, 14.6): aus dem Speicher des Mocks, sonst die feste Angabe der Serie (`s.hoerstelle`). */
  function hoerMass(s, name, e) {
    const f = s.folgen.find((x) => x.name === name);
    const sp = Array.isArray(f?.spuren_s) && f.spuren_s.length > 1 ? f.spuren_s : null;
    if (sp && f.dauer_s && e.track < sp.length) return [sp.slice(0, e.track).reduce((a, c) => a + c, 0) + Math.min(e.p, sp[e.track]), f.dauer_s];
    return [Math.min(e.p, e.d), e.d];
  }
  const ordnerFolge = (s, name) => { const f = s.folgen.find((x) => x.name === name); return f?.art === 'ordner' && f.tracks > 1; };
  function hoerKurz(s) {
    const e = b.hoerstellen[s.id];
    if (!e) return s.hoerstelle;
    const name = s.folgen.some((f) => f.name === e.folge) ? e.folge : null;
    const f = name && e.folgen[name];
    if (!f) return s.hoerstelle;
    const [p, g] = hoerMass(s, name, f);
    return f.fertig ? { anteil: 1, rest_s: 0, zeit: f.t, folge: name } : { anteil: Math.round(Math.min(1, p / g) * 10000) / 10000, rest_s: Math.max(0, Math.round(g - p)), zeit: f.t, folge: name };
  }
  function tobiesAuf(id) {
    return Object.values(b.zuordnungen).filter((z) => z.ziel.serie === id);
  }
  const kurzTobie = (z) => ({ uid: z.uid, name: z.name ?? null });
  const holeSerie = (id) => { const s = b.serien[id]; if (!s) throw fehler('serie_nicht_gefunden'); return s; };
  const holeFolge = (s, name) => { const f = s.folgen.find((x) => x.name === name); if (!f) throw fehler('folge_nicht_gefunden'); return f; };
  const mitTobies = (s) => ({
    ...kurzMitVorschlaegen(s),
    ...(hat('online_suche') && istAdmin ? { online_vorschlaege_liste: structuredClone((b.online.vorschlaege[s.id] ?? []).map(({ werte, bildFehlt, ...rest }) => rest)) } : {}),
    folgen: s.folgen.map((f) => {
      const h = b.hoerstellen[s.id]?.folgen?.[f.name];
      return { ...folgeMitOnline(f), ...(hat('favoriten') ? { favorit: istFavorit(s.id, f.name) } : {}), ...(h ? { hoerstelle: { position_s: h.p, fertig: h.fertig, ...(f.art === 'ordner' && f.tracks > 1 ? { track: h.track ?? 0 } : {}) } } : {}), tobies: Object.values(b.zuordnungen).filter((z) => z.ziel.typ === 'folge' && z.ziel.serie === s.id && z.ziel.folge === f.name).map(kurzTobie) };
    }),
    zuordnungen: Object.values(b.zuordnungen).filter((z) => z.ziel.typ === 'serie' && z.ziel.serie === s.id).map(kurzTobie),
  });
  const pruefeStand = (s, st) => { if (st !== undefined && st !== stand(s)) throw fehler('stand_veraltet'); };
  const alsEintrag = (typ, s, f) => ({ id: hex(`${s.id}${f?.name}${Math.random()}`, 12), typ, serie_id: s.id, serie_name: s.name, folge: f?.name ?? null, anzeige: f ? f.anzeige : s.name, art: 'datei', tracks: f ? f.tracks : s.folgen.length, groesse_bytes: 1000, grund: 'manuell', geloescht_am: '2026-11-09T10:00:00Z' });
  const konfigAendern = () => { b.konfig = { ...b.konfig, revision: (b.konfig.revision || 0) + 1 }; return b.konfig; };
  const zielPruefen = (ziel) => {
    if (!ziel || !['serie', 'folge', 'aktion'].includes(ziel.typ)) throw fehler('ziel_ungueltig');
    if (ziel.typ === 'aktion') { if (!['status', 'gute_nacht'].includes(ziel.aktion)) throw fehler('ziel_ungueltig'); return; }
    const s = holeSerie(ziel.serie);
    if (s.typ === 'ueberraschung') throw fehler('ziel_ungueltig');
    if (ziel.typ === 'folge') holeFolge(s, ziel.folge);
  };
  // Rückfrage beim Löschen/Zusammenführen einer Serie: nur Ziel Serie oder vorhandene Folge (ein Tobie auf eine gelöschte Folge spielt ohnehin nichts)
  const mitWirkung = (s) => Object.values(b.zuordnungen).filter((z) => z.ziel.serie === s.id && (z.ziel.typ === 'serie' || (z.ziel.typ === 'folge' && s.folgen.some((f) => f.name === z.ziel.folge))));
  const betroffeneFolge = (sid, fname) => Object.values(b.zuordnungen).filter((z) => z.ziel.typ === 'folge' && z.ziel.serie === sid && z.ziel.folge === fname);
  const konfigBereit = () => { if (b.konfig.zustand !== 'ok') throw fehler('konfig_nicht_bereit'); };

  /* Die Prüfung des Backends (Box: parse_konfig; HA: store.pruefe_*), knapp nachgebaut. */
  const ungueltig = (pfad) => fehler('einstellung_ungueltig', `Diese Einstellung ist ungültig: ${pfad}. Es wurde nichts geändert.`);
  const ganz = (x) => Number.isInteger(x) && typeof x === 'number';
  const einstellungPruefen = {
    leise(lz) {
      if (!lz || typeof lz !== 'object' || Array.isArray(lz)) throw ungueltig('leise_zeiten');
      const zone = lz.zeitzone ?? 'Europe/Berlin';
      try { new Intl.DateTimeFormat('de-DE', { timeZone: zone }); } catch { throw ungueltig('leise_zeiten.zeitzone'); }
      if (!Array.isArray(lz.fenster) || lz.fenster.length > 32) throw ungueltig('leise_zeiten.fenster');
      const ids = new Set();
      const fenster = lz.fenster.map((f, i) => {
        if (!f || typeof f !== 'object') throw ungueltig(`fenster[${i}]`);
        if (typeof f.id !== 'string' || !/^[a-z0-9_-]{1,32}$/.test(f.id) || ids.has(f.id)) throw ungueltig(`fenster[${i}].id`);
        ids.add(f.id);
        if (!Array.isArray(f.tage) || !f.tage.length || !f.tage.every((t) => ganz(t) && t >= 1 && t <= 7) || new Set(f.tage).size !== f.tage.length) throw ungueltig(`fenster[${i}].tage`);
        if (typeof f.von !== 'string' || !/^([01]\d|2[0-3]):[0-5]\d$/.test(f.von)) throw ungueltig(`fenster[${i}].von`);
        if (typeof f.bis !== 'string' || !/^([01]\d|2[0-3]):[0-5]\d$/.test(f.bis) || f.bis === f.von) throw ungueltig(`fenster[${i}].bis`);
        if (f.wirkung === 'leiser') {
          if (!ganz(f.grenze) || f.grenze < 0 || f.grenze > 100) throw ungueltig(`fenster[${i}].grenze`);
          return { id: f.id, tage: f.tage, von: f.von, bis: f.bis, wirkung: 'leiser', grenze: f.grenze };
        }
        if (f.wirkung !== 'stumm') throw ungueltig(`fenster[${i}].wirkung`);
        return { id: f.id, tage: f.tage, von: f.von, bis: f.bis, wirkung: 'stumm' };
      });
      return { zeitzone: zone, fenster };
    },
    gute(gn) {
      if (!gn || typeof gn !== 'object') throw ungueltig('gute_nacht');
      if (!ganz(gn.timer_min) || gn.timer_min < 1 || gn.timer_min > 240) throw ungueltig('gute_nacht.timer_min');
      if (!ganz(gn.ausblenden_s) || gn.ausblenden_s < 5 || gn.ausblenden_s > 600) throw ungueltig('gute_nacht.ausblenden_s');
      return { timer_min: gn.timer_min, ausblenden_s: gn.ausblenden_s };
    },
    tage(t) { if (!ganz(t) || t < 0 || t > 365) throw ungueltig('lesezeichen_tage'); return t; },
  };

  const onlineMod = onlineBefehle({ b, hat, emit: (...a) => emit(...a), holeSerie, holeFolge, stand, kurzform, istAdmin });
  const H = {
    'tobibox/hello': () => ({ v: 1, version: '0.1.0', darf_schreiben: darf, faehigkeiten: opts.faehigkeiten || FAEHIGKEITEN, boxen: b.boxen.map((x) => x.box), konfig: b.konfig,
      grenzen: { upload_max_bytes: 524288000, upload_block_bytes: 1048576, upload_parallel: 2, endungen: ['mp3', 'm4a', 'm4b'], serie_name_max: 100, folge_anzeige_max: 200, tobie_name_max: 60, name_max_bytes: 255, limit_max: 100 } }),
    'tobibox/serien/list': (m) => {
      let l = Object.values(b.serien);
      const f = m.filter || [];
      const grenze = MOCK_JETZT - 14 * 86400000;
      if (m.art) l = l.filter((s) => (s.art ?? 'hoerspiel') === m.art);
      if (m.text) l = l.filter((s) => passtText(m.text, [s.name, ...(m.auch_folgen ? s.folgen.map((x) => x.anzeige) : [])]));
      if (m.alter === 'ohne') l = l.filter((s) => eintragsAlter(s) === null);
      else if (m.alter !== undefined) l = l.filter((s) => eintragsAlter(s) !== null && eintragsAlter(s) <= m.alter);
      if (f.includes('sammlung')) l = l.filter((s) => !s.einzeln);
      if (f.includes('einzeln')) l = l.filter((s) => s.einzeln);
      if (f.includes('neu')) l = l.filter((s) => Date.parse(s.angelegt_am ?? '2026-10-01T10:00:00Z') >= grenze);
      if (f.includes('ohne_tobie')) l = l.filter((s) => !tobiesAuf(s.id).length);
      if (f.includes('pruefen')) l = l.filter((s) => s.pruefen);
      if (f.includes('favorit')) l = l.filter((s) => istFavorit(s.id));
      if (f.includes('online_vorschlag')) {
        if (!istAdmin) throw fehler('unauthorized', 'Nur für Administratoren');
        l = l.filter((s) => (b.online.vorschlaege[s.id] ?? []).length > 0);
      }
      const name = (x, y) => x.name.localeCompare(y.name, 'de', { numeric: true });
      if (m.sortierung === 'zuletzt_gehoert') l.sort((x, y) => String(zuletztGehoertAm(y.id) ?? '').localeCompare(String(zuletztGehoertAm(x.id) ?? '')) || name(x, y));
      else if (m.sortierung === 'meist_gehoert') {
        const sum = (id) => b.gehoert.zeilen.filter((z) => z.serie === id).reduce((a, z) => a + z.sekunden, 0);
        l.sort((x, y) => sum(y.id) - sum(x.id) || name(x, y));
      } else if (m.sortierung === 'neu') l.sort((x, y) => Date.parse(y.angelegt_am ?? '2026-10-01T10:00:00Z') - Date.parse(x.angelegt_am ?? '2026-10-01T10:00:00Z') || name(x, y));
      else if (m.sortierung === 'angehoert') l.sort((x, y) => (Date.parse(hoerKurz(y)?.zeit ?? 0) || 0) - (Date.parse(hoerKurz(x)?.zeit ?? 0) || 0) || name(x, y));
      else if (m.sortierung === 'name' || (!m.sortierung && ['art', 'text', 'auch_folgen', 'filter', 'limit', 'offset'].some((k) => k in m))) l.sort(name);
      // ganz ohne Eingabe (alte Seite) bleibt die Reihenfolge des Speichers; das echte Backend sortiert auch dann nach Name
      const gesamt = l.length;
      const von = m.offset || 0;
      const seite = m.limit === undefined ? l.slice(von) : l.slice(von, von + m.limit);
      return { serien: seite.map(kurzMitVorschlaegen), gesamt, weitere: von + seite.length < gesamt, ueberraschung: b.ueberraschung, geprueft_am: '2026-11-09T08:00:00Z', pruefung_laeuft: false, hinweise: [] };
    },
    'tobibox/folgen/list': (m) => {
      const f = m.filter || [];
      const grenze = MOCK_JETZT - 14 * 86400000;
      let zeilen = [];
      for (const s of Object.values(b.serien)) {
        if (m.art && (s.art ?? 'hoerspiel') !== m.art) continue;
        if (f.includes('sammlung') && s.einzeln) continue;
        if (f.includes('einzeln') && !s.einzeln) continue;
        if (f.includes('neu') && Date.parse(s.angelegt_am ?? '2026-10-01T10:00:00Z') < grenze) continue;
        for (const fo of s.folgen) {
          if (m.text && !passtText(m.text, [fo.anzeige])) continue;
          const direkt = betroffeneFolge(s.id, fo.name);
          const ganze = Object.values(b.zuordnungen).some((z) => z.ziel.typ === 'serie' && z.ziel.serie === s.id);
          if (f.includes('ohne_tobie') && (ganze || direkt.length)) continue;
          if (f.includes('pruefen') && !(s.pruefen || fo.pruefen)) continue;
          if (f.includes('favorit') && !istFavorit(s.id, fo.name)) continue;
          zeilen.push({ s, fo, direkt, ganze });
        }
      }
      const titel = (x, y) => x.fo.anzeige.localeCompare(y.fo.anzeige, 'de', { numeric: true }) || x.s.name.localeCompare(y.s.name, 'de');
      if (m.sortierung === 'neu') zeilen.sort((x, y) => Date.parse(y.s.angelegt_am ?? '2026-10-01T10:00:00Z') - Date.parse(x.s.angelegt_am ?? '2026-10-01T10:00:00Z') || titel(x, y));
      else zeilen.sort(titel);
      const gesamt = zeilen.length;
      const von = m.offset || 0;
      const lim = m.limit ?? 60;
      zeilen = zeilen.slice(von, von + lim);
      return { gesamt, weitere: von + zeilen.length < gesamt, folgen: zeilen.map(({ s, fo, direkt, ganze }) => ({
        serie_id: s.id, serie_name: s.name, serie_einzeln: !!s.einzeln, art: s.art ?? 'hoerspiel', folge: fo.name, anzeige: fo.anzeige, nummer: fo.nummer ?? null, kapitel: 0,
        groesse_mb: Math.round(fo.groesse_bytes / 1048576), ...(hat('favoriten') ? { favorit: istFavorit(s.id, fo.name) } : {}), tobies: direkt.map(kurzTobie), serie_hat_tobie: ganze || direkt.length > 0 || tobiesAuf(s.id).length > 0 })) };
    },
    'tobibox/serie/get': (m) => mitTobies(holeSerie(m.serie_id)),
    'tobibox/audio/bereit': (m) => {
      const s = holeSerie(m.serie_id);
      const f = holeFolge(s, m.folge);
      const tracks = f.art === 'ordner' && f.tracks > 1 ? f.tracks : 1;
      if ((m.track ?? 0) >= tracks) throw fehler('folge_nicht_gefunden');
      const pfad = `/api/tobibox/audio/${encodeURIComponent(s.id)}/${encodeURIComponent(f.name)}`;
      return { zustand: 'bereit', pfad: `${pfad}?${m.track === undefined ? '' : `track=${m.track}&`}authSig=${opts.sigPraefix ?? 'mock'}-${++b.sigZaehler}`, quelle: 'original' };
    },
    'tobibox/hoerstelle/get': (m) => {
      const s = holeSerie(m.serie_id);
      const e = b.hoerstellen[s.id];
      if (!e) return { weiter: null, folgen: {} };
      const folgen = Object.fromEntries(Object.entries(e.folgen).filter(([n]) => s.folgen.some((f) => f.name === n)).map(([n, f]) => [n, { position_s: f.p, dauer_s: f.d, fertig: f.fertig, zeit: f.t, ...(ordnerFolge(s, n) ? { track: f.track ?? 0 } : {}) }]));
      const k = hoerKurz(s);
      const f = e.folgen[e.folge];
      return { weiter: f && folgen[e.folge] ? { folge: e.folge, position_s: f.p, track: f.track, anteil: k.anteil, rest_s: k.rest_s, zeit: f.t } : null, folgen };
    },
    'tobibox/hoerstelle/set': (m) => {
      const s = holeSerie(m.serie_id);
      const f = holeFolge(s, m.folge);
      const tracks = f.art === 'ordner' && f.tracks > 1 ? f.tracks : 1;
      const nr = m.track ?? 0;
      if (nr >= tracks) throw fehler('invalid_format', 'track');
      if (m.position_s > m.dauer_s + 2) throw fehler('invalid_format', 'position_s über dauer_s');
      const jetzt = new Date(Date.now()).toISOString();
      const e = (b.hoerstellen[s.id] ??= { zeit: jetzt, folge: m.folge, folgen: {} });
      e.zeit = jetzt; e.folge = m.folge;
      e.folgen[m.folge] = { p: Math.round(m.position_s), d: Math.round(m.dauer_s) || 1, t: jetzt, fertig: !!m.fertig || (nr >= tracks - 1 && m.position_s >= m.dauer_s - 2), track: nr };
      return {};
    },
    'tobibox/hoerstelle/liste': (m) => {
      const l = [];
      for (const [sid, e] of Object.entries(b.hoerstellen)) {
        const s = b.serien[sid];
        const f = s && e.folgen[e.folge];
        if (!s || !f || f.fertig || !s.folgen.some((x) => x.name === e.folge)) continue;
        const k = hoerKurz(s);
        l.push({ serie_id: sid, name: s.name, folge: e.folge, position_s: f.p, track: f.track, anteil: k.anteil, rest_s: k.rest_s, zeit: f.t });
      }
      l.sort((x, y) => y.zeit.localeCompare(x.zeit));
      return { eintraege: l.slice(0, m.limit ?? 8) };
    },
    'tobibox/serie/create': (m) => {
      if (!m.name.trim()) throw fehler('name_ungueltig');
      if (m.typ === 'ueberraschung' && Object.values(b.serien).some((s) => s.typ === 'ueberraschung')) throw fehler('ueberraschung_existiert');
      const id = hex(m.name + Date.now(), 12);
      b.serien[id] = { id, name: m.name, typ: m.typ || 'normal', ordner: m.name, pruefen: false, hinweise: [], folgen: [] };
      if (m.typ === 'ueberraschung') b.ueberraschung = 'leer';
      return { serie: kurzform(b.serien[id]) };
    },
    'tobibox/serie/art_setzen': (m) => {
      const s = holeSerie(m.serie_id);
      if (!ARTEN.includes(m.art)) throw fehler('invalid_format', 'art');
      s.art = m.art; s.art_quelle = 'manuell';
      s.pruefen_gruende = (s.pruefen_gruende || []).filter((c) => c !== 'art_geraten');
      return { serie: kurzform(s) };
    },
    'tobibox/serie/alter_setzen': (m) => { // Nr. 66: `null` löscht das Alter von Hand; Recht alltag; Ereignis wie Nr. 38
      const s = holeSerie(m.serie_id);
      if (m.alter_hand === null) delete s.alter_hand; else s.alter_hand = m.alter_hand;
      emit('medien', 'serien_geaendert', { serie_id: s.id });
      return { serie: kurzform(s) };
    },
    'tobibox/serie/rename': (m) => { const s = holeSerie(m.serie_id); if (!m.name.trim()) throw fehler('name_ungueltig'); s.name = m.name; s.pruefen = false; return { serie: kurzform(s) }; },
    'tobibox/folgen/order': (m) => {
      const s = holeSerie(m.serie_id); pruefeStand(s, m.stand);
      const alt = s.folgen.map((f) => f.name).sort(); const neu = [...m.folgen].sort();
      if (!gleich(alt, neu)) throw fehler('reihenfolge_ungueltig');
      s.folgen = m.folgen.map((n) => holeFolge(s, n));
      return { serie: kurzform(s) };
    },
    'tobibox/folge/delete': (m) => {
      const s = holeSerie(m.serie_id); pruefeStand(s, m.stand); const f = holeFolge(s, m.folge);
      const tob = betroffeneFolge(s.id, f.name);
      if (tob.length && !m.tobies_bestaetigt) throw fehler('tobies_betroffen');
      s.folgen = s.folgen.filter((x) => x !== f);
      const e = alsEintrag('folge', s, f); b.papierkorb.unshift(e);
      return { eintrag: e, betroffene_tobies: tob.map(kurzTobie) };
    },
    'tobibox/serie/delete': (m) => {
      const s = holeSerie(m.serie_id); pruefeStand(s, m.stand);
      const tob = Object.values(b.zuordnungen).filter((z) => z.ziel.serie === s.id);
      if (mitWirkung(s).length && !m.tobies_bestaetigt) throw fehler('tobies_betroffen');
      delete b.serien[s.id];
      const e = alsEintrag('serie', s); b.papierkorb.unshift(e);
      return { eintrag: e, betroffene_tobies: tob.map(kurzTobie), ueberraschung: b.ueberraschung };
    },
    'tobibox/folge/rename': (m) => {
      const s = holeSerie(m.serie_id); pruefeStand(s, m.stand); const f = holeFolge(s, m.folge);
      if (!m.name.trim()) throw fehler('name_ungueltig');
      f.anzeige = m.name; f.pruefen = false;
      return { serie: kurzform(s), folge: f };
    },
    'tobibox/folge/verschieben': (m) => {
      const q = holeSerie(m.serie_id); pruefeStand(q, m.stand); const z = holeSerie(m.ziel_serie_id); const f = holeFolge(q, m.folge);
      if (q === z) throw fehler('ziel_ungueltig');
      const tob = betroffeneFolge(q.id, f.name);
      if (tob.length && !m.tobies_bestaetigt) throw fehler('tobies_betroffen');
      if (tob.length) { konfigBereit(); tob.forEach((t) => { t.ziel = { typ: 'folge', serie: z.id, folge: f.name }; }); }
      q.folgen = q.folgen.filter((x) => x !== f); z.folgen.push(f);
      return { quelle: kurzform(q), ziel: kurzform(z), folge: f.name, betroffene_tobies: tob.map(kurzTobie), konfig: tob.length ? konfigAendern() : null, veroeffentlicht: tob.length ? true : null };
    },
    'tobibox/serien/zusammenfuehren': (m) => {
      const q = holeSerie(m.quelle_id); const z = holeSerie(m.ziel_id);
      if (q === z || q.typ !== 'normal' || z.typ !== 'normal') throw fehler('ziel_ungueltig');
      pruefeStand(q, m.stand_quelle); pruefeStand(z, m.stand_ziel);
      const tob = Object.values(b.zuordnungen).filter((t) => t.ziel.serie === q.id);
      if (mitWirkung(q).length && !m.tobies_bestaetigt) throw fehler('tobies_betroffen');
      const n = q.folgen.length;
      tob.forEach((t) => { t.ziel = { ...t.ziel, serie: z.id }; });
      z.folgen.push(...q.folgen); q.folgen = [];
      delete b.serien[q.id];
      const e = alsEintrag('serie', q); e.grund = 'zusammengefuehrt'; b.papierkorb.unshift(e);
      return { ziel: kurzform(z), verschoben: n, umbenannt: [], betroffene_tobies: tob.map(kurzTobie), eintrag: e, konfig: tob.length ? konfigAendern() : null, veroeffentlicht: tob.length ? true : null };
    },
    'tobibox/einsortierung/bestaetigen': (m) => {
      const s = holeSerie(m.serie_id);
      (m.folgen || s.folgen.map((f) => f.name)).forEach((n) => { holeFolge(s, n).pruefen = false; });
      if (!m.folgen) s.pruefen = false;
      /* Rest aus A-1c (B3, 17.11.): auch im Protokoll des Eingangs verschwindet „bitte ansehen“ (`ergebnis[].pruefen` und `pruefen` der Einträge) */
      for (const e of opts.ohneProtokollReset ? [] : [...b.eingang, ...b.eingangErledigt]) { // `ohneProtokollReset`: ein älteres Backend (vor B3)
        for (const r of e.ergebnis || []) if (r.serie_id === s.id && (!m.folgen || m.folgen.includes(r.folge))) { r.pruefen = false; r.pruefen_gruende = []; }
        if (e.pruefen && !(e.ergebnis || []).some((r) => r.pruefen)) e.pruefen = false;
      }
      return { serie: kurzform(s) };
    },
    /* A11c: „Anders einsortieren“ (Vertrag 43). Prüfreihenfolge: Eintrag, Wunsch, Bedingungen (`pruefen` oder höchstens 24 Stunden seit `fertig_am`; `b.neuGesperrt`
     * ist die Menge der Einträge, an deren Folgen schon etwas geändert wurde), Ziel. Der Eintrag geht auf „läuft“; das Ergebnis lässt der Test kommen. */
    'tobibox/einsortierung/neu': (m) => {
      const e = [...b.eingang, ...b.eingangErledigt].find((x) => x.id === m.eintrag_id);
      if (!e) throw fehler('eintrag_nicht_gefunden');
      const ok = ['neu', 'ergaenzen', 'einzeln'].includes(m.ziel) && (!('art' in m) || ['hoerspiel', 'hoerbuch', 'musik', 'geschichte'].includes(m.art))
        && (m.ziel !== 'neu' || (typeof m.name === 'string' && m.name.trim().length >= 1 && m.name.length <= 100 && 'art' in m)) && (m.ziel !== 'ergaenzen' || !!m.serie_id) && (m.ziel !== 'einzeln' || 'art' in m);
      if (!ok) throw fehler('wunsch_ungueltig');
      const jung = e.fertig_am && Date.now() - Date.parse(e.fertig_am) <= 24 * 3600 * 1000;
      if ((!e.pruefen && !jung) || (b.neuGesperrt && b.neuGesperrt.has(e.id))) throw fehler('neu_einsortieren_nicht_moeglich');
      if (m.ziel === 'ergaenzen' && !b.serien[m.serie_id]) throw fehler('serie_nicht_gefunden');
      b.eingangErledigt = b.eingangErledigt.filter((x) => x !== e);
      b.eingang = [...b.eingang.filter((x) => x !== e), { ...e, status: 'laeuft', fertig_am: null, pruefen: false, ergebnis: [], hinweise: [], geaendert_am: new Date().toISOString(), wunsch: { ziel: m.ziel, art: m.art ?? null } }];
      emit('eingang', 'geaendert', {});
      b.neuNach?.(e, m);
      return { gestartet: true };
    },
    'tobibox/medien/pruefen': () => ({ gestartet: true, laeuft_bereits: false }),
    'tobibox/papierkorb/list': (m) => ({ eintraege: b.papierkorb.slice(m.offset || 0, (m.offset || 0) + (m.limit || 100)), gesamt: b.papierkorb.length, gesamt_bytes: b.papierkorb.reduce((a, e) => a + e.groesse_bytes, 0) }),
    'tobibox/papierkorb/restore': (m) => {
      const e = b.papierkorb.find((x) => x.id === m.eintrag_id); if (!e) throw fehler('eintrag_nicht_gefunden');
      if (e.typ === 'folge' && !b.serien[m.serie_id || e.serie_id]) throw fehler('serie_nicht_gefunden');
      b.papierkorb = b.papierkorb.filter((x) => x !== e);
      return { serie: null, folge: e.folge };
    },
    'tobibox/papierkorb/empty': (m) => {
      const n = b.papierkorb.length; b.papierkorb = m.eintrag_ids ? b.papierkorb.filter((e) => !m.eintrag_ids.includes(e.id)) : [];
      return { geloescht: n - b.papierkorb.length, freigegeben_bytes: 1 };
    },
    'tobibox/neue_tobies/list': (m) => ({ eintraege: b.neueTobies.slice(m.offset || 0, (m.offset || 0) + (m.limit || 100)), gesamt: b.neueTobies.length }),
    'tobibox/neue_tobies/verwerfen': (m) => {
      const n = b.neueTobies.length; b.neueTobies = b.neueTobies.filter((x) => x.uid !== m.uid);
      if (n !== b.neueTobies.length) emit('neue_tobies', 'entfernt', { uid: m.uid, grund: 'verworfen' });
      return { entfernt: n !== b.neueTobies.length };
    },
    /* A9/A10: Warteschlange (Vertrag 3.13). Prüfreihenfolge: Eingabe, Ziel und Name, Sperre, doppelt, voll. */
    'tobibox/warteschlange/set': (m) => {
      if (m.box !== null && !b.boxen.some((x) => x.box === m.box)) throw fehler('box_unbekannt');
      zielPruefen(m.ziel);
      if ('name' in m && m.name !== null && (typeof m.name !== 'string' || !m.name.trim() || m.name.trim().length > 60)) throw fehler('name_ungueltig');
      konfigBereit();
      if (b.warteschlange.some((e) => e.box === m.box && gleich(e.ziel, m.ziel))) throw fehler('warteschlange_doppelt');
      if (b.warteschlange.length >= 5) throw fehler('warteschlange_voll');
      const sr = m.ziel.typ === 'aktion' ? null : b.serien[m.ziel.serie];
      const eintrag = { id: hex(`ws${++b.wsNr}${m.box}${JSON.stringify(m.ziel)}`, 12), nr: b.wsNr, box: m.box, ziel: m.ziel, serie_name: sr?.name ?? null,
        folge_anzeige: m.ziel.typ === 'folge' ? (sr.folgen.find((f) => f.name === m.ziel.folge)?.anzeige ?? null) : null, folge_vorhanden: m.ziel.typ === 'folge' ? true : null,
        angelegt_von: { id: 'u1', name: 'Person A' }, angelegt_am: new Date().toISOString(), name: typeof m.name === 'string' ? m.name.trim() : null };
      b.warteschlange.push(eintrag);
      const mitPos = (e) => { const { nr, ...rest } = e; return { ...rest, position: b.warteschlange.indexOf(e) + 1 }; }; // eslint-disable-line no-unused-vars
      emit('warteschlange', 'angelegt', { eintrag: mitPos(eintrag) });
      return { eintrag: mitPos(eintrag), gesamt: b.warteschlange.length };
    },
    'tobibox/warteschlange/list': () => ({ eintraege: b.warteschlange.map((e, i) => { const { nr, ...rest } = e; return { ...rest, position: i + 1 }; }), gesamt: b.warteschlange.length }), // eslint-disable-line no-unused-vars
    'tobibox/warteschlange/abbrechen': (m) => {
      const e = b.warteschlange.find((x) => x.id === m.eintrag_id);
      if (!e) return { abgebrochen: false };
      b.warteschlange = b.warteschlange.filter((x) => x !== e);
      emit('warteschlange', 'abgebrochen', { id: e.id, grund: 'nutzer' });
      return { abgebrochen: true };
    },
    'tobibox/zuordnung/list': (m) => {
      let alle = Object.values(b.zuordnungen).filter((z) => (!m.serie_id || z.ziel.serie === m.serie_id) && (!m.uid || z.uid === m.uid));
      const zielName = (z) => { const sr = b.serien[z.ziel.serie]; return z.ziel.typ === 'aktion' ? z.ziel.aktion : z.ziel.typ === 'folge' ? (sr?.folgen.find((f) => f.name === z.ziel.folge)?.anzeige ?? '') : (sr?.name ?? ''); };
      if (m.text) alle = alle.filter((z) => passtText(m.text, [z.name ?? '', zielName(z), b.serien[z.ziel.serie]?.name ?? '']));
      if (m.neu) alle.sort((x, y) => Date.parse(y.angelegt_am ?? '2026-10-01T10:00:00Z') - Date.parse(x.angelegt_am ?? '2026-10-01T10:00:00Z') || (x.uid < y.uid ? -1 : 1));
      else alle.sort((x, y) => (x.uid < y.uid ? -1 : 1));
      const seite = alle.slice(m.offset || 0, (m.offset || 0) + (m.limit || 100));
      return { konfig: b.konfig, gesamt: alle.length, zuordnungen: seite.map((z) => {
        const s = b.serien[z.ziel.serie];
        return { uid: z.uid, name: z.name ?? null, ziel: z.ziel, angelegt_am: z.angelegt_am ?? '2026-10-01T10:00:00Z', serie_name: z.ziel.typ === 'aktion' ? null : (s ? s.name : null),
          folge_anzeige: z.ziel.typ === 'folge' ? (s?.folgen.find((f) => f.name === z.ziel.folge)?.anzeige ?? null) : null,
          folge_vorhanden: z.ziel.typ === 'folge' ? !!s?.folgen.some((f) => f.name === z.ziel.folge) : null, vorher: z.vorher ?? null,
          cover_stand: z.ziel.typ === 'aktion' ? null : (s?.cover_stand ?? null) }; // K6 und K8 (13.11.)
      }) };
    },
    'tobibox/zuordnung/set': (m) => {
      if (!/^[0-9A-F]{8,}$/.test(m.uid)) throw fehler('kennung_ungueltig');
      konfigBereit(); zielPruefen(m.ziel);
      if ('name' in m && m.name !== null && (!m.name.trim() || m.name.length > 60)) throw fehler('name_ungueltig');
      const alt = b.zuordnungen[m.uid];
      if ('erwartet_ziel' in m && m.erwartet_ziel !== undefined) { if (!gleich(m.erwartet_ziel, alt?.ziel)) throw fehler('zuordnung_geaendert'); }
      else if (alt && !gleich(alt.ziel, m.ziel) && !m.ueberschreiben) throw fehler('zuordnung_existiert');
      const name = 'name' in m ? m.name : (alt?.name ?? null);
      if (alt && gleich(alt.ziel, m.ziel) && (alt.name ?? null) === (name ?? null)) return { geaendert: false, konfig: b.konfig, veroeffentlicht: null };
      /* K6: `vorher` = das Ziel vor der letzten Umstellung; das alte Ziel zurückzusetzen löscht es, ein neuer Tobie hat keins (Vertrag 3.5) */
      let vorher = alt?.vorher ?? null;
      if (alt && !gleich(alt.ziel, m.ziel)) vorher = vorher && gleich(vorher.ziel, m.ziel) ? null : { ziel: alt.ziel, am: new Date().toISOString() };
      b.zuordnungen[m.uid] = { uid: m.uid, name, ziel: m.ziel, angelegt_am: alt?.angelegt_am ?? new Date().toISOString(), ...(vorher ? { vorher } : {}) };
      if (b.neueTobies.some((x) => x.uid === m.uid)) { b.neueTobies = b.neueTobies.filter((x) => x.uid !== m.uid); emit('neue_tobies', 'entfernt', { uid: m.uid, grund: 'zugeordnet' }); }
      return { geaendert: true, konfig: konfigAendern(), veroeffentlicht: true };
    },
    'tobibox/zuordnung/remove': (m) => {
      konfigBereit();
      const alt = b.zuordnungen[m.uid];
      if (!gleich(m.erwartet_ziel, alt?.ziel)) throw fehler('zuordnung_geaendert');
      if (m.als_neu && !b.boxen.some((x) => x.box === m.als_neu.box)) throw fehler('box_unbekannt');
      if (!alt) return { geaendert: false, konfig: b.konfig, veroeffentlicht: null };
      delete b.zuordnungen[m.uid];
      if (m.als_neu) { // „Rückgängig“ bei einem neuen Tobie: wieder „unbekannt, zuletzt gesehen“ (Vertrag 3.5, 13.11.)
        const jetzt = new Date().toISOString();
        const eintrag = { uid: m.uid, zuerst: jetzt, zuletzt: jetzt, anzahl: 1, boxen: { [m.als_neu.box]: { zuerst: jetzt, zuletzt: jetzt, anzahl: 1, zeit_ok: true } } };
        b.neueTobies = [eintrag, ...b.neueTobies.filter((x) => x.uid !== m.uid)];
        emit('neue_tobies', 'neu', { eintrag });
      }
      return { geaendert: true, konfig: konfigAendern(), veroeffentlicht: true };
    },
    'tobibox/lernmodus/start': (m) => {
      const box = b.boxen.find((x) => x.box === m.box); if (!box) throw fehler('box_unbekannt');
      konfigBereit(); zielPruefen(m.ziel);
      if (!box.online) throw fehler('box_offline');
      if (b.lern && b.lern.box === m.box && !gleich(b.lern.ziel, m.ziel)) throw fehler('lernmodus_laeuft');
      b.lern = { box: m.box, befehl_id: `befehl-${Math.random().toString(16).slice(2)}`, ziel: m.ziel, name: m.name ?? null };
      return { befehl_id: b.lern.befehl_id, box: m.box, ziel: m.ziel, beginn: '2026-11-09T10:00:00Z', frist_bis: '2026-11-09T10:03:00Z' };
    },
    'tobibox/lernmodus/antwort': (m) => {
      if (!b.lern || b.lern.befehl_id !== m.befehl_id) throw fehler('kein_lernmodus');
      b.lern = null;
      return { zustand: m.ueberschreiben ? 'zugeordnet' : 'abgelehnt', konfig: b.konfig };
    },
    'tobibox/lernmodus/abbrechen': (m) => {
      if (!b.boxen.some((x) => x.box === m.box)) throw fehler('box_unbekannt');
      const war = !!b.lern; b.lern = null; return { abgebrochen: war };
    },
    'tobibox/boxen/list': () => ({ boxen: istAdmin ? b.boxen : b.boxen.map(({ ereignisse, ...rest }) => rest) }), // `ereignisse` nur für Administratoren (Vertrag 2.1)
    'tobibox/box/sync': (m) => {
      const box = b.boxen.find((x) => x.box === m.box); if (!box) throw fehler('box_unbekannt');
      if (!box.online) throw fehler('box_offline');
      return { befehl_id: 'sync-1', ttl_s: 300 };
    },
    'tobibox/liste/neu_ausrollen': () => { b.konfig = { ...b.konfig, zustand: 'ok', revision: 1, liste_id: `liste-${Math.random().toString(16).slice(2, 8)}` }; return { konfig: b.konfig, veroeffentlicht: true }; },
    'tobibox/eingang/list': (m) => {
      // Filter `alle` (Vertrag 29): was noch im Eingang liegt, dazu die letzten einsortierten Einträge aus dem Protokoll
      const l = (m.filter === 'erledigt') ? b.eingangErledigt : m.filter === 'alle' ? [...b.eingang, ...b.eingangErledigt] : b.eingang;
      const von = m.offset ?? 0;
      return { eintraege: l.slice(von, von + (m.limit ?? 50)), gesamt: l.length, sortierung_laeuft: false, geprueft_am: '2026-11-09T08:00:00Z' };
    },
    'tobibox/eingang/sortieren': () => ({ gestartet: true, laeuft_bereits: false, eintraege: b.eingang.length }),
    'tobibox/konfig/export_lesen': () => ({ ...b.exportDatei, konfig: b.konfig }),
    'tobibox/konfig/get': () => ({ konfig: b.konfig }),
    'tobibox/einstellungen/get': () => ({ ...b.einstellungen, konfig: b.konfig }),
    'tobibox/einstellungen/set': (m) => {
      konfigBereit();
      if (!('leise_zeiten' in m) && !('gute_nacht' in m) && !('lesezeichen_tage' in m)) throw fehler('invalid_format', 'nichts zu ändern');
      if ('erwartet_revision' in m && m.erwartet_revision !== b.konfig.revision) throw fehler('stand_veraltet'); // 12.11.: nichts wird geändert
      const neu = structuredClone(b.einstellungen);
      if ('leise_zeiten' in m) {
        // Nicht-Administratoren: `zeitzone` wird ignoriert, der gespeicherte Wert bleibt (Vertrag 2.4)
        const lz = istAdmin || !m.leise_zeiten || typeof m.leise_zeiten !== 'object' ? m.leise_zeiten : { ...m.leise_zeiten, zeitzone: b.einstellungen.leise_zeiten.zeitzone };
        neu.leise_zeiten = einstellungPruefen.leise(lz);
      }
      if ('gute_nacht' in m) neu.gute_nacht = einstellungPruefen.gute(m.gute_nacht);
      if ('lesezeichen_tage' in m) neu.lesezeichen_tage = einstellungPruefen.tage(m.lesezeichen_tage);
      if (gleich(neu, b.einstellungen)) return { geaendert: false, konfig: b.konfig, veroeffentlicht: null, ...b.einstellungen };
      b.einstellungen = neu;
      return { geaendert: true, konfig: konfigAendern(), veroeffentlicht: true, ...b.einstellungen };
    },
    'tobibox/eingang/entfernen': (m) => {
      const e = b.eingang.find((x) => x.id === m.eintrag_id); if (!e) throw fehler('eintrag_nicht_gefunden');
      b.eingang = b.eingang.filter((x) => x !== e);
      return { eintrag: { id: hex(e.id, 12), typ: 'eingang', serie_id: null, serie_name: null, folge: null, anzeige: e.name, art: e.art, tracks: e.dateien, groesse_bytes: e.groesse_bytes, grund: 'manuell', geloescht_am: '2026-11-09T10:00:00Z' } };
    },
    ...gehoertBefehle({ b, hat, emit: (...a) => emit(...a), kurzform, istFavorit, holeSerie, holeFolge, istAdmin, opts }),
    ...onlineMod.befehle,
    'tobibox/cover/neu_suchen': (m) => { if (m.serie_id) holeSerie(m.serie_id); return { gestartet: true, eintraege: m.serie_id ? 1 : Object.keys(b.serien).length }; },
    'tobibox/hoerkopie/neu_erzeugen': (m) => { if (m.serie_id) holeSerie(m.serie_id); return { eingereiht: m.serie_id ? 1 : 2 }; },
    /* alles, was in der letzten Stunde (vor MOCK_JETZT) in den Papierkorb kam */
    'tobibox/papierkorb/restore_letzte_stunde': () => {
      const ab = MOCK_JETZT - 3600000;
      const da = b.papierkorb.filter((e) => Date.parse(e.geloescht_am) >= ab);
      b.papierkorb = b.papierkorb.filter((e) => !da.includes(e));
      return { wiederhergestellt: da.length, uebersprungen: [] };
    },
    'tobibox/konfig/aus_export': () => {
      if (!b.exportDatei.vorhanden) throw fehler('export_nicht_gefunden');
      b.konfig = { ...b.konfig, zustand: 'ok', revision: 1, liste_id: `liste-${Math.random().toString(16).slice(2, 8)}` };
      return { konfig: b.konfig, veroeffentlicht: true, uebernommen: { zuordnungen: b.exportDatei.anzahl_zuordnungen, fenster: 0 } };
    },
  };

  async function verarbeite(msg) {
    calls.push({ type: msg.type, msg: structuredClone(msg) });
    const felder = pruefeEingabe(msg, opts.faehigkeiten || FAEHIGKEITEN);
    if (!darf && !LESEN.has(msg.type)) throw fehler('unauthorized', 'Nur für Administratoren');
    if (opts.nichtAdmin && ADMIN_BEFEHLE.has(msg.type)) throw fehler('unauthorized', 'Nur für Administratoren');
    if (!istAdmin && ADMIN_BEFEHLE_B.has(msg.type)) throw fehler('unauthorized', 'Nur für Administratoren'); // Stufe B: Verlauf, Export und Löschen der Hördaten
    if (!istAdmin && ADMIN_BEFEHLE_OS.has(msg.type)) throw fehler('unauthorized', 'Nur für Administratoren'); // Online-Suche: Nr. 57 bis 63 (Nr. 64 ist für alle)
    if (!istAdmin && msg.type.startsWith('tobibox/lernmodus/')) throw fehler('unauthorized', 'Nur für Administratoren'); // seit 13.11. admin (A0-Q, X13a)
    const f = failures.get(msg.type);
    if (f && f.length) { const c = f.shift(); throw typeof c === 'string' ? fehler(c, `Fehler ${c}`) : c; }
    if (msg.anfrage_id) {
      const alt = b.gesehenAnfragen.get(msg.anfrage_id);
      if (alt) { if (alt.type !== msg.type || !gleich(alt.felder, felder)) throw fehler('anfrage_id_konflikt'); return alt.antwort; }
    }
    const h = overrides.get(msg.type) || H[msg.type];
    const antwort = structuredClone(await h(felder, b));
    if (JSON.stringify(antwort).length > NACHRICHT_MAX) throw fehler('invalid_format', 'Die Antwort ist größer als 64 KiB (Vertrag 8)');
    if (msg.anfrage_id) b.gesehenAnfragen.set(msg.anfrage_id, { type: msg.type, felder, antwort });
    return antwort;
  }

  const connection = {
    sendMessagePromise: (msg) => new Promise((res, rej) => { queueMicrotask(() => { verarbeite({ id: nextId++, ...msg }).then(res, rej); }); }),
    subscribeMessage: (cb, msg) => new Promise((res, rej) => {
      queueMicrotask(() => {
        try { calls.push({ type: msg.type, msg: structuredClone(msg), abo: true }); pruefeEingabe({ id: nextId++, ...msg }); } catch (e) { rej(e); return; }
        // Vertrag 4.11: `online` gibt es nur für Administratoren; HA streicht es für alle anderen still (erst die Themen auflösen, dann streichen; eine leere Menge bleibt leer)
        const aufgeloest = msg.themen || ['boxen', 'neue_tobies', 'lernmodus', 'medien', 'eingang', 'konfig', 'upload', ...(opts.faehigkeiten?.includes('online_suche') ? ['online'] : [])];
        const abo = { cb, aktiv: true, themen: istAdmin ? aufgeloest : aufgeloest.filter((t) => t !== 'online') };
        subs.push(abo);
        res(() => { abo.aktiv = false; });
        /* Snapshot je Thema direkt nach dem Abonnieren (Vertrag 4) */
        const snap = {
          boxen: { boxen: b.boxen.map((x) => ({ box: x.box, online: x.online, konfig_stand: x.konfig_stand })) },
          neue_tobies: { gesamt: b.neueTobies.length }, lernmodus: { vorgaenge: [] },
          medien: { pruefung_laeuft: false, geprueft_am: '2026-11-09T08:00:00Z' },
          eingang: { offen: b.eingang.length, blockiert: 1, sortierung_laeuft: false, geprueft_am: '2026-11-09T08:00:00Z' },
          konfig: { konfig: b.konfig }, upload: {}, gehoert: {}, favoriten: {}, online: onlineMod.status(),
        };
        if (opts.snapshots !== false) abo.themen.forEach((t) => emit(t, 'snapshot', snap[t]));
      });
    }),
  };

  function emit(thema, art, daten = {}) {
    subs.filter((s) => s.aktiv && s.themen.includes(thema)).forEach((s) => s.cb({ v: 1, thema, art, daten: structuredClone(daten) }));
  }

  /* Ein Tobie wird auf eine Box gelegt (Box meldet `unbekannt`, Vertrag 3.13). Bekannt: nichts. Passende Vormerkung (älteste zuerst, `box` oder
   * `null`): Zuordnung sofort, Ereignis `warteschlange` `abgearbeitet`; ist die Liste gesperrt, bleibt der Eintrag und der Tobie steht in
   * „Neue Tobies“. Sonst `neue_tobies` `neu` (oder `aktualisiert`). `zeit` und `zeitOk` setzen die Meldezeit. Antwort: { art }. */
  function legeAuf(box, uid, { zeit = new Date().toISOString(), zeitOk = true } = {}) {
    if (b.zuordnungen[uid]) return { art: 'bekannt' };
    for (const e of b.warteschlange.filter((x) => x.box === null || x.box === box)) {
      const sr = e.ziel.typ === 'aktion' ? null : b.serien[e.ziel.serie];
      const da = e.ziel.typ === 'aktion' || (sr && (e.ziel.typ !== 'folge' || sr.folgen.some((f) => f.name === e.ziel.folge)));
      if (!da) { b.warteschlange = b.warteschlange.filter((x) => x !== e); emit('warteschlange', 'abgebrochen', { id: e.id, grund: 'ziel_fehlt' }); continue; }
      if (b.konfig.zustand !== 'ok') break; // Schritt b scheitert: Eintrag bleibt, die Meldung läuft den normalen Weg
      b.zuordnungen[uid] = { uid, name: e.name, ziel: e.ziel, angelegt_am: zeit };
      konfigAendern();
      b.warteschlange = b.warteschlange.filter((x) => x !== e);
      if (b.neueTobies.some((x) => x.uid === uid)) { b.neueTobies = b.neueTobies.filter((x) => x.uid !== uid); emit('neue_tobies', 'entfernt', { uid, grund: 'zugeordnet' }); }
      emit('warteschlange', 'abgearbeitet', { id: e.id, uid, box, ziel: e.ziel, serie_name: e.serie_name, folge_anzeige: e.folge_anzeige, angelegt_von: e.angelegt_von, name: e.name });
      return { art: 'zugeordnet', eintrag: e.id };
    }
    const alt = b.neueTobies.find((x) => x.uid === uid);
    const meldung = { zuerst: alt?.boxen?.[box]?.zuerst ?? zeit, zuletzt: zeit, anzahl: (alt?.boxen?.[box]?.anzahl ?? 0) + 1, zeit_ok: zeitOk };
    const eintrag = { uid, zuerst: alt?.zuerst ?? zeit, zuletzt: zeit, anzahl: (alt?.anzahl ?? 0) + 1, boxen: { ...(alt?.boxen || {}), [box]: meldung } };
    b.neueTobies = [eintrag, ...b.neueTobies.filter((x) => x.uid !== uid)];
    emit('neue_tobies', alt ? 'aktualisiert' : 'neu', { eintrag });
    return { art: alt ? 'aktualisiert' : 'neu' };
  }

  /* XMLHttpRequest-Ersatz. Modus 'auto': sendet Fortschritt und antwortet mit Erfolg. */
  class MockXHR {
    constructor() { this.upload = {}; this.headers = {}; this.status = 0; this.responseText = ''; xhrs.push(this); }
    open(method, url) { this.method = method; this.url = url; }
    setRequestHeader(k, v) { this.headers[k] = v; }
    send(body) {
      this.body = body;
      if ((opts.xhr || 'auto') === 'auto') queueMicrotask(() => { const g = this.body.get('datei')?.size ?? 100; this.fortschritt(Math.floor(g / 2), g); this.fortschritt(g, g); this.antwort(200, this.erfolg()); });
    }
    erfolg() {
      const d = this.body.get('datei');
      return { v: 1, upload_id: this.body.get('upload_id'), eingang_name: d?.name, serie_id: this.body.get('serie_id'), groesse_bytes: d?.size ?? 0, pruefung: 'ok', hinweis: null, wiederholt: false };
    }
    fortschritt(loaded, total) { this.upload.onprogress?.({ loaded, total, lengthComputable: true }); }
    antwort(status, obj) {
      this.upload.onload?.(); this.status = status; this.responseText = typeof obj === 'string' ? obj : JSON.stringify(obj); this.onload?.();
    }
    netzfehler() { this.onerror?.(); }
    abort() { this.abgebrochen = true; this.onabort?.(); } // A11a: „Abbrechen“ beim Hochladen
  }

  /* Cover: `hass.fetchWithAuth` wie in HA. `opts.ohneCover` (Menge von IDs) ergibt 404. Aufrufe stehen in `covers`. */
  const covers = [];
  /* A8f: POST (Rumpf `image/jpeg`) und DELETE `?quelle=eigen` wie das Backend (Vertrag 14.3): Aufrufe stehen in `coverAufrufe`, der Stand
   * der Serie ändert sich (`cover_stand`, `cover_quelle`). `opts.coverFehler` = Liste von { code, status } für die nächsten Aufrufe;
   * `opts.coverNetz` lässt den nächsten Aufruf mit einem Netzfehler scheitern. */
  const coverAufrufe = [];
  let coverZaehler = 0;
  const antwort = (status, obj) => ({ ok: status >= 200 && status < 300, status, json: async () => obj, blob: async () => new Blob([]) });
  const coverSchreiben = async (pfad, o) => {
    const id = decodeURIComponent(pfad.split('/cover/')[1]?.split('?')[0] ?? '');
    coverAufrufe.push({ pfad, id, methode: o.method, typ: o.headers?.['Content-Type'], groesse: o.body?.size ?? null, body: o.body });
    if (opts.coverNetz) { opts.coverNetz = false; throw new TypeError('Failed to fetch'); }
    const fehlerNaechster = opts.coverFehler?.shift();
    if (fehlerNaechster) return antwort(fehlerNaechster.status ?? 400, { v: 1, fehler: { code: fehlerNaechster.code, text: 'x' } });
    const sr = b.serien[id];
    if (!sr) return antwort(404, { v: 1, fehler: { code: 'serie_nicht_gefunden', text: 'x' } });
    if (o.method === 'DELETE' && /[?&]quelle=online\b/.test(pfad)) { // Vertrag 14.3: nur Administratoren; kein Fehler, wenn es kein Online-Cover gibt
      if (!istAdmin) return antwort(403, { v: 1, fehler: { code: 'unauthorized', text: 'x' } });
      if (sr.cover_quelle === 'online') { sr.cover_stand = sr.cover_auto ?? null; sr.cover_quelle = sr.cover_stand ? 'auto' : null; }
      return antwort(200, { v: 1, serie_id: id, cover_stand: sr.cover_stand ?? null, cover_quelle: sr.cover_stand ? (sr.cover_quelle ?? 'auto') : null });
    }
    if (o.method === 'POST') {
      if (sr.cover_quelle !== 'eigen') sr.cover_auto = sr.cover_stand ?? null; // das automatische Cover kommt mit DELETE zurück
      sr.cover_stand = hex(`eigen-${id}-${++coverZaehler}`, 8);
      sr.cover_quelle = 'eigen';
    } else if (sr.cover_quelle === 'eigen') {
      sr.cover_quelle = null;
      sr.cover_stand = sr.cover_auto ?? null; // ohne automatisches Cover gibt es danach keins
      if (sr.cover_stand) sr.cover_quelle = 'auto';
    }
    return antwort(200, { v: 1, serie_id: id, cover_stand: sr.cover_stand ?? null, cover_quelle: sr.cover_stand ? (sr.cover_quelle ?? 'auto') : null });
  };
  /* Online-Suche: `GET /api/tobibox/online/vorschau/<treffer_id>` (Vertrag 3.15): nur Administratoren (403), nur 16 Zeichen [0-9a-f] (sonst 404), abgelaufen 410, ohne Bild 404. Aufrufe in `vorschauAufrufe`. */
  const vorschauAufrufe = [];
  const vorschau = async (pfad) => {
    const id = decodeURIComponent(pfad.split('/vorschau/')[1]?.split('?')[0] ?? '');
    vorschauAufrufe.push(pfad);
    if (!istAdmin) return antwort(403, { v: 1, fehler: { code: 'unauthorized', text: 'x' } });
    if (!/^[0-9a-f]{16}$/.test(id)) return antwort(404, { v: 1, fehler: { code: 'cover_nicht_gefunden', text: 'x' } });
    const t = b.online.treffer[id];
    if (!t || t.abgelaufen) return antwort(410, { v: 1, fehler: { code: 'treffer_abgelaufen', text: 'x' } });
    if (!t.hat_cover) return antwort(404, { v: 1, fehler: { code: 'cover_nicht_gefunden', text: 'x' } });
    return { ok: true, status: 200, headers: { get: (k) => (/cache-control/i.test(k) ? 'no-store' : /content-type/i.test(k) ? 'image/jpeg' : null) }, blob: async () => new Blob(['jpeg'], { type: 'image/jpeg' }) };
  };
  const fetchWithAuth = async (pfad, o = {}) => {
    if (pfad.startsWith('/api/tobibox/online/vorschau/')) return vorschau(pfad);
    if (o.method === 'POST' || o.method === 'DELETE') return coverSchreiben(pfad, o);
    covers.push(pfad);
    const id = decodeURIComponent(pfad.split('/cover/')[1]?.split('?')[0] ?? '');
    if (!b.serien[id] || (opts.ohneCover && opts.ohneCover.has(id))) return { ok: false, status: 404, blob: async () => new Blob([]) };
    return { ok: true, status: 200, blob: async () => new Blob(['jpeg'], { type: 'image/jpeg' }) };
  };

  const hass = {
    connection,
    fetchWithAuth,
    auth: { data: { access_token: 'token-123' }, expired: false, refreshAccessToken: async () => { hass.auth.data.access_token = 'token-neu'; hass.auth.expired = false; } },
    user: { id: opts.userId ?? 'u-admin', is_admin: istAdmin }, // `userId`: eigene HA-Benutzerkennung (Papierkorb: „von anderen“)
    language: 'de',
  };

  return {
    hass, backend: b, calls, subs, xhrs, emit, MockXHR, covers, coverAufrufe, legeAuf, opts, vorschauAufrufe,
    /* Online-Suche: der laufende Lauf endet (Ereignis `online`/`fertig`, `letzte_laeufe` von Nr. 63). `grund` fehlt bei `fertig` und darf bei `abgebrochen` fehlen (Vertrag 4.11, 19.11.). */
    onlineLaufBeenden: (zustand = 'fertig', grund = undefined, zahlen = {}) => {
      const L = b.online.lauf;
      const z = { erledigt: L?.erledigt ?? 0, gesamt: L?.gesamt ?? 0, geaendert: L?.geaendert ?? 0, vorschlaege: L?.vorschlaege ?? 0, keiner: L?.keiner ?? 0, ...zahlen };
      const id = L?.lauf_id ?? hex(`lauf-${++b.online.zaehler}`, 12);
      b.online.laeufe.unshift({ lauf_id: id, beginn: b.online.laufBeginn ?? '2026-11-13T09:00:00Z', ende: new Date(Date.now()).toISOString(), zustand, ...(grund ? { grund } : {}), zahlen: z });
      b.online.laeufe = b.online.laeufe.slice(0, 5);
      b.online.lauf = null;
      emit('online', 'fertig', { vorgang: 'lauf', lauf_id: id, zustand, ...z, ...(grund ? { grund } : {}) });
      return id;
    },
    xhrFactory: () => new MockXHR(),
    /* Aufrufe eines Befehls (ohne Abos) */
    aufrufe: (type) => calls.filter((c) => c.type === type && !c.abo).map((c) => c.msg),
    letzter: (type) => calls.filter((c) => c.type === type && !c.abo).at(-1)?.msg,
    on: (type, fn) => overrides.set(type, fn),
    failNext: (type, ...codes) => { failures.set(type, [...(failures.get(type) || []), ...codes]); },
    reset: () => { calls.length = 0; },
    tick: () => new Promise((r) => setTimeout(r, 0)),
  };
}

/* A12/A13: `konfig/export_lesen` mit früheren Ständen (Fähigkeit `konfig_staende`, Vertrag 2.4). Ohne `stand`: der neueste Export
 * plus `staende`; mit `stand` n: die Angaben dieses Standes, sonst `export_nicht_gefunden`. Gibt die Liste der Stände zurück. */
export const BEISPIEL_STAENDE = [
  { stand: 1, revision: 8, exportiert_am: '2026-11-09T08:30:00Z', anzahl_zuordnungen: 4, anzahl_fenster: 1 },
  { stand: 2, revision: 7, exportiert_am: '2026-11-08T19:00:00Z', anzahl_zuordnungen: 3, anzahl_fenster: 0 },
];
export function mitStaenden(m, staende = BEISPIEL_STAENDE) {
  m.on('tobibox/konfig/export_lesen', (f, b) => {
    const basis = { ...b.exportDatei, konfig: b.konfig };
    if (f.stand === undefined) return { ...basis, staende: staende.map(({ stand, exportiert_am, anzahl_zuordnungen }) => ({ stand, exportiert_am, anzahl_zuordnungen })) };
    const x = staende.find((y) => y.stand === f.stand);
    if (!x) throw fehler('export_nicht_gefunden');
    return { ...basis, revision: x.revision, exportiert_am: x.exportiert_am, anzahl_zuordnungen: x.anzahl_zuordnungen, anzahl_fenster: x.anzahl_fenster, neuer_als_ha: false };
  });
  return staende;
}

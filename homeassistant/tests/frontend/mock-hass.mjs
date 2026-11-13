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
/* A9/A10 (Vertrag W 3.13, Nr. 47 bis 49): Warteschlange „Nächster neuer Tobie“. Eigener Satz, damit die Abdeckungsprüfung der alten Seite unverändert bleibt. */
export const SCHEMA_WS = {
  'tobibox/warteschlange/set': { req: ['box', 'ziel'], opt: ['name', 'anfrage_id'], braucht: 'warteschlange' },
  'tobibox/warteschlange/list': { braucht: 'warteschlange' },
  'tobibox/warteschlange/abbrechen': { req: ['eintrag_id'], braucht: 'warteschlange' },
};
export const FAEHIGKEITEN_A9 = ['warteschlange', 'zuordnung_rueckgaengig'];
/* A8: Befehle nur für Administratoren (Vertrag 2.1). Mit der Mock-Option `nichtAdmin` darf der Benutzer alles andere (Alltag). */
export const ADMIN_BEFEHLE = new Set(['folgen/order', 'serien/zusammenfuehren', 'serie/create', 'papierkorb/restore', 'papierkorb/empty'].map((x) => `tobibox/${x}`));
export const FELDER_V11 = {
  'tobibox/zuordnung/remove': { als_neu: 'zuordnung_rueckgaengig' }, // A9, Vertrag 3.5 (13.11.)
  'tobibox/zuordnung/list': { uid: 'zuordnung_uid' },
  'tobibox/konfig/export_lesen': { stand: 'konfig_staende' }, // A12/A13: frühere Stände (Vertrag 2.4)
  'tobibox/konfig/aus_export': { stand: 'konfig_staende' },
};

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
const FILTER_WERTE = ['ohne_tobie', 'neu', 'pruefen', 'sammlung', 'einzeln'];
const MOCK_JETZT = Date.parse('2026-11-13T12:00:00Z'); // „heute“ im Mock (Filter „neu“: letzte 14 Tage)
export const NACHRICHT_MAX = 64 * 1024; // Vertrag 8: eine Nachricht hat höchstens 64 KiB
export const FAEHIGKEITEN_V11 = ['einstellungen', 'eingang_entfernen', 'zuordnung_uid', 'konfig_lesen', 'upload_fertig_details'];

/* Befehle, die nur Administratoren ausführen dürfen (Vertrag 2.1). */
const LESEN = new Set(['hello', 'subscribe', 'serien/list', 'folgen/list', 'serie/get', 'papierkorb/list', 'neue_tobies/list', 'zuordnung/list', 'boxen/list', 'eingang/list', 'konfig/export_lesen', 'einstellungen/get', 'konfig/get'].map((x) => `tobibox/${x}`));

export const FAEHIGKEITEN = ['medien', 'upload', 'zuordnung', 'tobie_namen', 'neue_tobies', 'lernmodus', 'boxen', 'papierkorb', 'liste_ausrollen', 'konfig_export', 'sync', 'eingang', 'korrektur', 'serie_loeschen', 'bibliothek', 'cover'];

const fehler = (code, message = code) => ({ code, message });
const gleich = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
const hex = (s, n = 16) => createHash('sha256').update(s).digest('hex').slice(0, n);

/* Wertebereiche der Bibliothek (Vertrag 14.2 und Befehl 37). */
function pruefeBibliothek(type, f, faehigkeiten) {
  const grenze = { 'tobibox/serien/list': 200, 'tobibox/folgen/list': 100, 'tobibox/zuordnung/list': 100 }[type];
  if (grenze === undefined) return;
  if ('limit' in f && !(Number.isInteger(f.limit) && f.limit >= 1 && f.limit <= grenze)) throw fehler('invalid_format', `limit 1 bis ${grenze}`);
  if ('offset' in f && !(Number.isInteger(f.offset) && f.offset >= 0)) throw fehler('invalid_format', 'offset ab 0');
  if ('text' in f && !(typeof f.text === 'string' && f.text.trim().length >= 2 && f.text.length <= 100)) throw fehler('invalid_format', 'text mit 2 bis 100 Zeichen');
  if ('art' in f && !ARTEN.includes(f.art)) throw fehler('invalid_format', 'art');
  if ('neu' in f && typeof f.neu !== 'boolean') throw fehler('invalid_format', 'neu');
  if ('auch_folgen' in f && typeof f.auch_folgen !== 'boolean') throw fehler('invalid_format', 'auch_folgen');
  if ('filter' in f) {
    if (!Array.isArray(f.filter) || f.filter.some((x) => !FILTER_WERTE.includes(x))) throw fehler('invalid_format', 'filter');
  }
  if ('sortierung' in f) {
    const erlaubt = type === 'tobibox/folgen/list' ? ['titel', 'neu'] : ['name', 'neu', 'angehoert'];
    if (!erlaubt.includes(f.sortierung)) throw fehler('invalid_format', 'sortierung');
    if (f.sortierung === 'angehoert' && faehigkeiten && !faehigkeiten.includes('reinhoeren')) throw fehler('invalid_format', 'angehoert braucht reinhoeren');
  }
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
  const sch = SCHEMA[msg.type] || SCHEMA_V11[msg.type] || SCHEMA_BIB[msg.type] || SCHEMA_TECHNIK[msg.type] || SCHEMA_WS[msg.type];
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
  for (const k of sch.req || []) if (!(k in felder)) throw fehler('invalid_format', `Pflichtfeld ${k} fehlt`);
  for (const k of sch.must || []) if (!(k in felder)) throw fehler('invalid_format', `Die Seite muss ${k} senden`);
  if ('bestaetigt' in felder && felder.bestaetigt !== true) throw fehler('invalid_format', 'bestaetigt muss true sein');
  if ('anfrage_id' in felder && !/^[0-9A-Za-z-]{8,64}$/.test(felder.anfrage_id)) throw fehler('invalid_format', 'anfrage_id');
  return felder;
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
    warteschlange: [], // A9: Vormerkungen in der Reihenfolge der Anlage
    wsNr: 0,
    lern: null,
    exportDatei: { vorhanden: true, liste_id: 'liste-aaaa', revision: 9, exportiert_am: '2026-11-09T09:00:00Z', anzahl_zuordnungen: 4, anzahl_fenster: 0, neuer_als_ha: true },
    gesehenAnfragen: new Map(),
    einstellungen: { leise_zeiten: { zeitzone: 'Europe/Berlin', fenster: [] }, gute_nacht: { timer_min: 30, ausblenden_s: 60 }, lesezeichen_tage: 14 },
  };

  if (opts.leer) { b.serien = {}; b.zuordnungen = {}; }
  if (opts.viele) Object.assign(b, beispielBibliothek(opts.viele === true ? 130 : opts.viele));

  const stand = (s) => hex(JSON.stringify([s.name, s.folgen.map((f) => [f.name, f.anzeige])]));
  const kurzform = (s) => ({
    id: s.id, name: s.name, typ: s.typ, ordner: s.ordner, anzahl_folgen: s.folgen.length,
    anzahl_tobies: tobiesAuf(s.id).length, angelegt_am: s.angelegt_am ?? '2026-10-01T10:00:00Z', stand: stand(s),
    pruefen: s.pruefen, anzahl_pruefen: s.folgen.filter((f) => f.pruefen).length, hinweise: s.hinweise,
    art: s.art ?? 'hoerspiel', art_quelle: s.art ? 'manuell' : 'tags', einzeln: !!s.einzeln, kapitel_anzahl: s.kapitel_anzahl ?? 0,
    dauer_s: s.dauer_s ?? null, cover_stand: s.cover_stand ?? null, cover_quelle: s.cover_stand ? 'auto' : null,
    ...(s.hoerstelle ? { hoerstelle: s.hoerstelle } : {}),
  });
  function tobiesAuf(id) {
    return Object.values(b.zuordnungen).filter((z) => z.ziel.serie === id);
  }
  const kurzTobie = (z) => ({ uid: z.uid, name: z.name ?? null });
  const holeSerie = (id) => { const s = b.serien[id]; if (!s) throw fehler('serie_nicht_gefunden'); return s; };
  const holeFolge = (s, name) => { const f = s.folgen.find((x) => x.name === name); if (!f) throw fehler('folge_nicht_gefunden'); return f; };
  const mitTobies = (s) => ({
    ...kurzform(s),
    folgen: s.folgen.map((f) => ({ ...f, tobies: Object.values(b.zuordnungen).filter((z) => z.ziel.typ === 'folge' && z.ziel.serie === s.id && z.ziel.folge === f.name).map(kurzTobie) })),
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

  const H = {
    'tobibox/hello': () => ({ v: 1, version: '0.1.0', darf_schreiben: darf, faehigkeiten: opts.faehigkeiten || FAEHIGKEITEN, boxen: b.boxen.map((x) => x.box), konfig: b.konfig,
      grenzen: { upload_max_bytes: 524288000, upload_block_bytes: 1048576, upload_parallel: 2, endungen: ['mp3', 'm4a', 'm4b'], serie_name_max: 100, folge_anzeige_max: 200, tobie_name_max: 60, name_max_bytes: 255, limit_max: 100 } }),
    'tobibox/serien/list': (m) => {
      let l = Object.values(b.serien);
      const f = m.filter || [];
      const grenze = MOCK_JETZT - 14 * 86400000;
      if (m.art) l = l.filter((s) => (s.art ?? 'hoerspiel') === m.art);
      if (m.text) l = l.filter((s) => passtText(m.text, [s.name, ...(m.auch_folgen ? s.folgen.map((x) => x.anzeige) : [])]));
      if (f.includes('sammlung')) l = l.filter((s) => !s.einzeln);
      if (f.includes('einzeln')) l = l.filter((s) => s.einzeln);
      if (f.includes('neu')) l = l.filter((s) => Date.parse(s.angelegt_am ?? '2026-10-01T10:00:00Z') >= grenze);
      if (f.includes('ohne_tobie')) l = l.filter((s) => !tobiesAuf(s.id).length);
      if (f.includes('pruefen')) l = l.filter((s) => s.pruefen);
      const name = (x, y) => x.name.localeCompare(y.name, 'de', { numeric: true });
      if (m.sortierung === 'neu') l.sort((x, y) => Date.parse(y.angelegt_am ?? '2026-10-01T10:00:00Z') - Date.parse(x.angelegt_am ?? '2026-10-01T10:00:00Z') || name(x, y));
      else if (m.sortierung === 'angehoert') l.sort((x, y) => (Date.parse(y.hoerstelle?.zeit ?? 0) || 0) - (Date.parse(x.hoerstelle?.zeit ?? 0) || 0) || name(x, y));
      else if (m.sortierung === 'name' || (!m.sortierung && ['art', 'text', 'auch_folgen', 'filter', 'limit', 'offset'].some((k) => k in m))) l.sort(name);
      // ganz ohne Eingabe (alte Seite) bleibt die Reihenfolge des Speichers; das echte Backend sortiert auch dann nach Name
      const gesamt = l.length;
      const von = m.offset || 0;
      const seite = m.limit === undefined ? l.slice(von) : l.slice(von, von + m.limit);
      return { serien: seite.map(kurzform), gesamt, weitere: von + seite.length < gesamt, ueberraschung: b.ueberraschung, geprueft_am: '2026-11-09T08:00:00Z', pruefung_laeuft: false, hinweise: [] };
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
        groesse_mb: Math.round(fo.groesse_bytes / 1048576), tobies: direkt.map(kurzTobie), serie_hat_tobie: ganze || direkt.length > 0 || tobiesAuf(s.id).length > 0 })) };
    },
    'tobibox/serie/get': (m) => mitTobies(holeSerie(m.serie_id)),
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
      if (tob.length && !m.tobies_bestaetigt) throw fehler('tobies_betroffen');
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
      if (tob.length && !m.tobies_bestaetigt) throw fehler('tobies_betroffen');
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
      return { serie: kurzform(s) };
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
      const l = (m.filter === 'erledigt') ? b.eingangErledigt : b.eingang;
      return { eintraege: l, gesamt: l.length, sortierung_laeuft: false, geprueft_am: '2026-11-09T08:00:00Z' };
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
        const abo = { cb, aktiv: true, themen: msg.themen || ['boxen', 'neue_tobies', 'lernmodus', 'medien', 'eingang', 'konfig', 'upload'] };
        subs.push(abo);
        res(() => { abo.aktiv = false; });
        /* Snapshot je Thema direkt nach dem Abonnieren (Vertrag 4) */
        const snap = {
          boxen: { boxen: b.boxen.map((x) => ({ box: x.box, online: x.online, konfig_stand: x.konfig_stand })) },
          neue_tobies: { gesamt: b.neueTobies.length }, lernmodus: { vorgaenge: [] },
          medien: { pruefung_laeuft: false, geprueft_am: '2026-11-09T08:00:00Z' },
          eingang: { offen: b.eingang.length, blockiert: 1, sortierung_laeuft: false, geprueft_am: '2026-11-09T08:00:00Z' },
          konfig: { konfig: b.konfig }, upload: {},
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
  }

  /* Cover: `hass.fetchWithAuth` wie in HA. `opts.ohneCover` (Menge von IDs) ergibt 404. Aufrufe stehen in `covers`. */
  const covers = [];
  const fetchWithAuth = async (pfad) => {
    covers.push(pfad);
    const id = decodeURIComponent(pfad.split('/cover/')[1]?.split('?')[0] ?? '');
    if (!b.serien[id] || (opts.ohneCover && opts.ohneCover.has(id))) return { ok: false, status: 404, blob: async () => new Blob([]) };
    return { ok: true, status: 200, blob: async () => new Blob(['jpeg'], { type: 'image/jpeg' }) };
  };

  const hass = {
    connection,
    fetchWithAuth,
    auth: { data: { access_token: 'token-123' }, expired: false, refreshAccessToken: async () => { hass.auth.data.access_token = 'token-neu'; hass.auth.expired = false; } },
    user: { is_admin: istAdmin },
    language: 'de',
  };

  return {
    hass, backend: b, calls, subs, xhrs, emit, MockXHR, covers, legeAuf,
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

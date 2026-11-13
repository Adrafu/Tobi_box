/* Kleiner lokaler Server für die Browserprüfung (pruefe_seite.py), Paket A14-1a.
 *
 * Liefert die Seite der Integration (`custom_components/tobibox/frontend`) unter `/f/`, die Prüfseite `seite.html` und das
 * Messskript `messen.js`. Das Backend ist der echte Mock `../mock-hass.mjs`: `POST /ws?k=<Profil>[~<Lauf>]` schickt eine Nachricht an
 * `hass.connection.sendMessagePromise` des Mocks. Je Schlüssel gibt es einen eigenen Mock; der Teil nach `~` trennt parallele
 * Läufe voneinander, damit sich ihre Änderungen (Umbenennen, neue Leise-Zeit) nicht stören. Kein Netz, keine festen Pfade.
 *
 * Profile (Teil vor `~`): admin, user (Alltag: schreiben ja, Technik nein), leer (leere Bibliothek), akku (Box mit schwachem Akku),
 * warn (Konfiguration „Export neuer“, Box mit Stand „voraus“).
 *
 * A11a: `POST /api/tobibox/upload` (multipart, wie das Backend nach Vertrag 5 und 14.4, ohne die Dateien zu speichern) und `eingang/list` mit
 * Filter `alle`: Ein Upload legt nach kurzer Zeit einen Eingangs-Eintrag und das Ergebnis (Serie, Folgen) im Mock an. Marken im Dateinamen lösen
 * Fehler aus: `zu-gross` (413), `kein-platz` (507), `kopierschutz` (Eintrag „geht nicht“), `ansehen` (Eintrag „bitte kurz ansehen“).
 *
 * Aufruf: node server.mjs [Port]   (Port 0 oder keiner = freier Port). Die erste Zeile der Ausgabe ist `PORT <n>`.
 */
import http from 'node:http';
import { readFileSync, statSync } from 'node:fs';
import { join, extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const HIER = fileURLToPath(new URL('.', import.meta.url));
const FRONT = resolve(HIER, '../../../custom_components/tobibox/frontend');
const { createMockHass, FAEHIGKEITEN, FAEHIGKEITEN_V11, FAEHIGKEITEN_A9, mitStaenden, eingangEintrag } = await import(new URL('../mock-hass.mjs', import.meta.url));

const folge = (name, anzeige, extra = {}) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * 1048576, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });

function bauen(schluessel) {
  const profil = schluessel.split('~')[0];
  const leer = profil === 'leer';
  const m = createMockHass({
    faehigkeiten: [...new Set([...FAEHIGKEITEN, ...FAEHIGKEITEN_V11, ...FAEHIGKEITEN_A9, 'konfig_staende', 'hoerkopie', 'einsortier_wunsch'])],
    viele: leer ? false : 130, leer, darf: true, istAdmin: profil !== 'user',
  });
  mitStaenden(m);
  const b = m.backend;
  if (!leer) {
    // Sonderfälle der Serienseite: lange Liste mit langem Namen, „bitte ansehen“, Einzeltitel, Hörbuch, leere Sammlung
    b.serien.lang = { id: 'lang', name: 'Die wilde Reise der kleinen Drachen durch das Wolkenland', typ: 'normal', ordner: 'Lang', pruefen: false, hinweise: [], art: 'hoerspiel', dauer_s: 45 * 1500, cover_stand: 'aabb1122',
      hoerstelle: { anteil: 0.18, rest_s: 1260, zeit: '2026-11-12T18:00:00Z', folge: 'f03.mp3' },
      folgen: Array.from({ length: 45 }, (_, i) => folge(`f${String(i + 1).padStart(2, '0')}.mp3`, i === 2 ? 'Die alte Mühle am Rand des sehr langen und tiefen Waldes' : `Folge ${i + 1}: ${['Der Schatz', 'Das Rätsel', 'Die Höhle'][i % 3]}`,
        { nummer: i + 1, dauer_s: 1400 + i * 7, hoerstelle: i === 0 ? { position_s: 1400, fertig: true } : i === 1 ? { position_s: 600, fertig: false } : undefined })) };
    b.zuordnungen['04A0000000000001'] = { uid: '04A0000000000001', angelegt_am: '2026-11-13T10:00:00Z', name: 'Löwe', ziel: { typ: 'serie', serie: 'lang' } };
    b.zuordnungen['04A0000000000002'] = { uid: '04A0000000000002', angelegt_am: '2026-11-13T10:30:00Z', name: null, ziel: { typ: 'folge', serie: 'lang', folge: 'f02.mp3' } };
    b.serien.pruef = { id: 'pruef', name: 'Bibi Blocksberg', typ: 'normal', ordner: 'Bibi', pruefen: true, hinweise: [], art: 'hoerspiel', cover_stand: 'ccdd3344',
      folgen: [folge('b1.mp3', 'Hexen gibt es doch', { pruefen: true, pruefen_gruende: ['tags_fehlen', 'nummer_doppelt'] }), folge('b2.mp3', 'Der Hexenbesen')] };
    b.serien.lied = { id: 'lied', name: 'Wiegenlied', typ: 'normal', ordner: 'Wiegenlied', pruefen: false, hinweise: [], art: 'musik', einzeln: true, dauer_s: 66, cover_stand: null, folgen: [folge('wiegenlied.mp3', 'Wiegenlied')] };
    b.serien.buch = { id: 'buch', name: 'Das große Buch', typ: 'normal', ordner: 'Buch', pruefen: false, hinweise: [], art: 'hoerbuch', dauer_s: 34800, kapitel_anzahl: 14, cover_stand: 'eeff5566',
      folgen: [folge('buch', 'Das große Buch', { art: 'ordner', tracks: 14, dauer_s: 34800 })] };
    b.serien.kurz = { id: 'kurz', name: 'Kleine Reise', typ: 'normal', ordner: 'Kurz', pruefen: false, hinweise: [], art: 'hoerspiel', cover_stand: null,
      folgen: [folge('k1.mp3', 'Aufbruch', { nummer: 1 }), folge('k2.mp3', 'Unterwegs', { nummer: 2 }), folge('k3.mp3', 'Die Rast', { nummer: 3 }), folge('k4.mp3', 'Heimkehr', { nummer: 4 })] };
    b.serien.leersammlung = { id: 'leersammlung', name: 'Leere Sammlung', typ: 'normal', ordner: 'Leer', pruefen: false, hinweise: [], art: 'hoerspiel', folgen: [] };
  }
  // Geräte: zwei Boxen, eine spielt, eine ist aus; drei Leise-Zeiten (still, leiser, kurz)
  const ids = Object.keys(b.serien);
  const s0 = b.serien[ids[0]];
  b.einstellungen.leise_zeiten.fenster = leer ? [] : [
    { id: 'nacht', tage: [7, 1, 2, 3, 4], von: '19:30', bis: '06:30', wirkung: 'stumm' },
    { id: 'mittag', tage: [1, 2, 3, 4, 5, 6, 7], von: '13:00', bis: '14:00', wirkung: 'leiser', grenze: 25 },
    { id: 'kurz', tage: [5, 6], von: '20:00', bis: '21:00', wirkung: 'leiser', grenze: 40 },
  ];
  b.boxen[0].anzeige = 'Küche'; b.boxen[1].anzeige = 'Kinderzimmer';
  b.boxen[0].status = { ...b.boxen[0].status, zustand: profil === 'akku' ? 'pausiert' : 'spielt', akku_prozent: profil === 'akku' ? 15 : 80, lader: profil !== 'akku',
    ...(s0 ? { serie: { id: s0.id, name: s0.name }, folge: { name: s0.folgen[0].name, track: 0 } } : {}) };
  b.boxen[1].status = { ...b.boxen[1].status, akku_prozent: 35 };
  // Technik: Papierkorb mit langem Namen und gelöschter Serie
  b.papierkorb = [
    { id: 'aaaa11112222', typ: 'folge', serie_id: 's1', serie_name: 'Die drei ???', folge: 'f9.mp3', anzeige: 'Das Gespensterschloss (lange Folge mit sehr langem Namen zum Umbrechen)', art: 'datei', tracks: 1, groesse_bytes: 41000000, grund: 'manuell', geloescht_am: '2026-11-08T10:00:00Z', geloescht_von: { id: 'u1', name: 'Person B' } },
    { id: 'bbbb11112222', typ: 'serie', serie_id: null, serie_name: null, folge: null, anzeige: 'Alte Serie', art: 'ordner', tracks: 12, groesse_bytes: 410000000, grund: 'manuell', geloescht_am: '2026-11-13T11:30:00Z', geloescht_von: null },
  ];
  if (profil === 'warn') { b.konfig = { ...b.konfig, zustand: 'export_neuer' }; b.boxen[1].konfig_stand = 'voraus'; }
  // A11a: `eingang/list` mit Filter „alle“ (offen und erledigt), Uploads merken
  m.uploads = [];
  m.gruppen = new Map();
  m.on('tobibox/eingang/list', (msg, bk) => {
    const l = msg.filter === 'erledigt' ? bk.eingangErledigt : msg.filter === 'alle' ? [...bk.eingang, ...bk.eingangErledigt] : bk.eingang;
    return { eintraege: l, gesamt: l.length, sortierung_laeuft: false, geprueft_am: '2026-11-13T12:00:00Z' };
  });
  // A-1b: Ereignisse des Mocks sammeln; die Prüfseite holt sie mit `GET /ev` (Abo `subscribeMessage` der Seite)
  m.ereignisse = [];
  m.hass.connection.subscribeMessage((ev) => m.ereignisse.push(ev), { type: 'tobibox/subscribe', themen: ['boxen', 'neue_tobies', 'konfig', 'warteschlange', 'eingang'] });
  return m;
}

/* A11b: Zustände des Eingangs: jeder liefert [noch im Eingang, einsortiert (Protokoll)]. Zeiten sind relativ zu „jetzt“. */
const ZUSTAENDE_EINGANG = (() => {
  const vor = (jetzt, min) => new Date(jetzt - min * 60000).toISOString();
  const lauf = (jetzt, teil = {}) => eingangEintrag({ status: 'laeuft', fertig_am: null, zuerst_gesehen: vor(jetzt, 1), ...teil });
  const ansehen = (jetzt, teil = {}) => eingangEintrag({ fertig_am: vor(jetzt, 20), pruefen: true, wunsch: { ziel: 'neu', art: 'hoerspiel' },
    ergebnis: [{ serie_id: 'pruef', serie_name: 'Bibi Blocksberg', serie_neu: true, folge: 'b1.mp3', anzeige: 'Hexen gibt es doch', tracks: 1, pruefen: true, pruefen_gruende: ['tags_fehlen', 'nummer_doppelt'] }], ...teil });
  return {
    leer: () => [[], []],
    laeuft1: (j) => [[lauf(j)], []],
    laeuft2: (j) => [[lauf(j), lauf(j, { status: 'wartet' })], []],
    pruefen1: (j) => [[], [ansehen(j)]],
    pruefen2: (j) => [[], [ansehen(j), ansehen(j, { fertig_am: vor(j, 40), quelle: 'nas', wunsch: null })]],
    fehler: (j) => [[eingangEintrag({ status: 'blockiert', fertig_am: null, zuerst_gesehen: vor(j, 30), hinweise: [{ code: 'kopierschutz', datei: 'a.m4b', text: 'x' }] })], []],
    fertig: (j) => [[], [eingangEintrag({ fertig_am: vor(j, 2) })]],
  };
})();

const mocks = new Map();
const holeMock = (k) => { if (!mocks.has(k)) mocks.set(k, bauen(k)); return mocks.get(k); };
const MIME = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.svg': 'image/svg+xml', '.json': 'application/json' };
const FARBEN = ['#e9a23b', '#3b8ee9', '#c94f7c', '#4fa86b'];

async function koerper(req) { let t = ''; for await (const c of req) t += c; return t; }
function datei(res, pfad) {
  try {
    if (!statSync(pfad).isFile()) throw new Error('keine Datei');
    res.setHeader('content-type', MIME[extname(pfad)] || 'text/plain; charset=utf-8');
    res.end(readFileSync(pfad));
  } catch { res.statusCode = 404; res.end('nicht da'); }
}

/* A11a: multipart/form-data in Teile zerlegen (Name des Feldes, Dateiname, Inhalt). */
function multipart(buf, boundary) {
  const sep = Buffer.from(`--${boundary}`);
  const teile = [];
  let pos = buf.indexOf(sep);
  while (pos >= 0) {
    const weiter = buf.indexOf(sep, pos + sep.length);
    if (weiter < 0) break;
    const teil = buf.subarray(pos + sep.length + 2, weiter - 2);
    const k = teil.indexOf('\r\n\r\n');
    const kopf = teil.subarray(0, k).toString('utf8');
    teile.push({ name: /name="([^"]*)"/.exec(kopf)?.[1], dateiname: /filename="([^"]*)"/.exec(kopf)?.[1], inhalt: teil.subarray(k + 4) });
    pos = weiter;
  }
  return teile;
}
const ENDUNGEN = ['mp3', 'm4a', 'm4b', 'aac', 'flac', 'ogg', 'opus', 'wav'];
const nachName = (n) => String(n).replace(/\.[^.]+$/, '').replace(/^\s*\d+\s*[-._)]*\s*/, '').trim() || n;

/* Das Ergebnis einer Gruppe (oder einer einzelnen Datei) im Mock anlegen: Serie, Folgen und der Eintrag im Eingang. */
function einsortieren(m, gr) {
  const b = m.backend;
  const w = gr.wunsch;
  const id = (x) => `up${Math.abs([...x].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 7))}`;
  const eintrag = { id: id(gr.eingangName), name: gr.eingangName, art: gr.ordner ? 'ordner' : 'datei', dateien: gr.dateien.length, ignoriert: 0, groesse_bytes: gr.dateien.reduce((a, d) => a + d.groesse, 0),
    zuerst_gesehen: '2026-11-13T12:00:00Z', geaendert_am: '2026-11-13T12:00:00Z', status: 'erledigt', hinweise: [], ergebnis: [], fertig_am: '2026-11-13T12:00:01Z', quelle: 'upload', wunsch: w.ziel ? { ziel: w.ziel, art: w.art ?? null } : null, pruefen: false };
  if (gr.dateien.some((d) => /kopierschutz/i.test(d.name))) {
    Object.assign(eintrag, { status: 'blockiert', fertig_am: null, hinweise: [{ code: 'kopierschutz', datei: gr.dateien[0].name, text: 'x' }] });
    b.eingangErledigt.unshift(eintrag);
    return;
  }
  const pruefen = gr.dateien.some((d) => /ansehen/i.test(d.name)) || (w.ziel === 'auto' && gr.dateien.length > 1);
  const art = w.art ?? 'hoerspiel';
  const f = (d, i, nummer) => ({ name: d.name, anzeige: nachName(d.name), nummer, datum: null, art: 'datei', tracks: 1, groesse_bytes: d.groesse, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [] });
  const erg = (sid, name, neu, fo, tracks) => ({ serie_id: sid, serie_name: name, serie_neu: neu, folge: fo.name, anzeige: fo.anzeige, tracks, pruefen, pruefen_gruende: pruefen ? ['tags_fehlen'] : [] });
  if (w.ziel === 'ergaenzen' && b.serien[w.serie_id]) {
    const sr = b.serien[w.serie_id];
    gr.dateien.forEach((d) => { const fo = f(d, 0, sr.folgen.length + 1); sr.folgen.push(fo); eintrag.ergebnis.push(erg(sr.id, sr.name, false, fo, 1)); });
  } else if (w.ziel === 'einzeln') {
    gr.dateien.forEach((d) => {
      const sid = id(`${w.name || d.name}${d.id}`);
      const fo = f(d, 0, null);
      b.serien[sid] = { id: sid, name: d.wunschName || nachName(d.name), typ: 'normal', ordner: sid, pruefen: false, hinweise: [], art, einzeln: true, cover_stand: null, angelegt_am: '2026-11-13T12:00:00Z', folgen: [fo] };
      eintrag.ergebnis.push(erg(sid, b.serien[sid].name, true, fo, 1));
    });
  } else {
    const name = w.name || nachName(gr.dateien[0].name);
    const sid = id(`${name}${gr.eingangName}`);
    const hoerbuch = art === 'hoerbuch';
    const folgen = hoerbuch ? [{ ...f(gr.dateien[0], 0, null), name, anzeige: name, art: 'ordner', tracks: gr.dateien.length }] : gr.dateien.map((d, i) => f(d, i, art === 'hoerspiel' ? i + 1 : null));
    b.serien[sid] = { id: sid, name, typ: 'normal', ordner: sid, pruefen, hinweise: [], art, cover_stand: null, angelegt_am: '2026-11-13T12:00:00Z', folgen };
    folgen.forEach((fo) => eintrag.ergebnis.push(erg(sid, name, true, fo, fo.tracks)));
  }
  eintrag.pruefen = pruefen;
  b.eingangErledigt.unshift(eintrag);
}

/* A11a: ein Upload. Antwort wie das Backend (Vertrag 5.5) nach kurzer Verzögerung, damit die Seite „Datei 2 von 3“ zeigt. */
async function upload(req, res) {
  const m = holeMock(req.headers['x-tb-k'] || 'admin');
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const teile = multipart(Buffer.concat(chunks), /boundary=(.+)$/.exec(req.headers['content-type'] || '')?.[1] ?? '');
  const feld = (n) => teile.find((t) => t.name === n && t.dateiname === undefined)?.inhalt.toString('utf8');
  const dat = teile.find((t) => t.name === 'datei');
  const antwort = (status, obj) => setTimeout(() => { res.statusCode = status; res.setHeader('content-type', 'application/json'); res.end(JSON.stringify(obj)); }, 250);
  const fehler = (status, code) => antwort(status, { v: 1, fehler: { code, text: code } });
  const name = dat?.dateiname ?? '';
  const endung = name.split('.').pop().toLowerCase();
  if (!dat) return fehler(400, 'invalid_format');
  if (!ENDUNGEN.includes(endung)) return fehler(415, 'format_nicht_erlaubt');
  if (/zu-gross/i.test(name)) return fehler(413, 'datei_zu_gross');
  if (/kein-platz/i.test(name)) return fehler(507, 'kein_speicher');
  const wunsch = { ziel: feld('ziel'), art: feld('art'), name: feld('name'), serie_id: feld('serie_id'), gruppe: feld('gruppe'), gruppe_anzahl: Number(feld('gruppe_anzahl')) || null };
  m.uploads.push({ ...wunsch, upload_id: feld('upload_id'), datei: name, groesse: dat.inhalt.length });
  const d = { id: feld('upload_id'), name, groesse: dat.inhalt.length, wunschName: wunsch.name };
  const key = wunsch.gruppe || d.id;
  const gr = m.gruppen.get(key) || { wunsch, dateien: [], ordner: !!wunsch.gruppe, eingangName: wunsch.gruppe ? `Upload ${wunsch.gruppe.slice(0, 8)}` : name };
  m.gruppen.set(key, gr);
  gr.dateien.push(d);
  if (!wunsch.gruppe_anzahl || gr.dateien.length >= wunsch.gruppe_anzahl) setTimeout(() => einsortieren(m, gr), 300);
  return antwort(200, { v: 1, upload_id: d.id, eingang_name: name, serie_id: wunsch.serie_id ?? null, groesse_bytes: d.groesse, pruefung: 'ok', hinweis: null, wiederholt: false });
}

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  const p = u.pathname;
  res.setHeader('cache-control', 'no-store');
  if (p === '/favicon.ico') { res.statusCode = 204; res.end(); return; }
  if (p === '/ws' && req.method === 'POST') {
    const m = holeMock(u.searchParams.get('k') || 'admin');
    try { res.end(JSON.stringify({ ok: await m.hass.connection.sendMessagePromise(JSON.parse(await koerper(req))) })); } catch (e) { res.end(JSON.stringify({ error: e })); }
    return;
  }
  /* A-1b: Ereignisse für das Abo der Seite. `ab=-1` liefert nur den aktuellen Stand der Zählung (ohne die Snapshots vom Start). */
  if (p === '/ev') {
    const m = holeMock(u.searchParams.get('k') || 'admin');
    const ab = Number(u.searchParams.get('ab'));
    res.end(JSON.stringify(ab < 0 ? { n: m.ereignisse.length, ereignisse: [] } : { n: m.ereignisse.length, ereignisse: m.ereignisse.slice(ab) }));
    return;
  }
  /* A-1b: ein Tobie wird auf eine Box gelegt (Mock-Funktion `legeAuf`): Body { box, uid, zeitOk? } */
  if (p === '/legeauf' && req.method === 'POST') {
    const m = holeMock(u.searchParams.get('k') || 'admin');
    const { box, uid, ...opt } = JSON.parse(await koerper(req));
    res.end(JSON.stringify(m.legeAuf(box, uid, opt)));
    return;
  }
  /* B-1: viele Serien anlegen (Zielwahl wird lang, das Namensfeld auf der Seite des Tobies liegt weit unten): Body { anzahl } */
  if (p === '/serien-viele' && req.method === 'POST') {
    const m = holeMock(u.searchParams.get('k') || 'admin');
    const { anzahl = 12 } = JSON.parse(await koerper(req));
    for (let i = 1; i <= anzahl; i += 1) {
      const id = `viel${i}`;
      m.backend.serien[id] = { id, name: `Hörspiel Nummer ${i}`, typ: 'normal', ordner: `Viel${i}`, pruefen: false, hinweise: [], art: 'hoerspiel', cover_stand: null, angelegt_am: `2026-11-${String(10 + (i % 3)).padStart(2, '0')}T10:00:00Z`, folgen: [folge(`v${i}.mp3`, `Folge ${i}`, { nummer: 1 })] };
    }
    res.end(JSON.stringify({ anzahl }));
    return;
  }
  /* A-1b: Liste sperren oder freigeben (Fall „Auto-Zuordnung scheitert“): Body { zustand: 'export_neuer' | 'ok' } */
  if (p === '/sperre' && req.method === 'POST') {
    const m = holeMock(u.searchParams.get('k') || 'admin');
    const { zustand } = JSON.parse(await koerper(req));
    m.backend.konfig = { ...m.backend.konfig, zustand };
    m.emit('konfig', 'geaendert', { konfig: m.backend.konfig });
    res.end(JSON.stringify({ zustand }));
    return;
  }
  if (p === '/api/tobibox/upload' && req.method === 'POST') { await upload(req, res); return; }
  /* A-1b: Zustand des Mocks für Ablaufprüfungen (nur lesen): Zuordnungen, Vormerkungen, unbekannte Tobies */
  if (p === '/zustand') {
    const m = holeMock(u.searchParams.get('k') || 'admin');
    res.end(JSON.stringify({ zuordnungen: m.backend.zuordnungen, warteschlange: m.backend.warteschlange, neue: m.backend.neueTobies, konfig: m.backend.konfig, cover: m.coverInfo ?? [], uploads: m.uploads ?? [] }));
    return;
  }
  /* A11b: Zustand des Eingangs setzen (Band in der Bibliothek, gelbe Karte auf der Serienseite): Body { zustand }, ein Wert aus ZUSTAENDE_EINGANG.
   * Das Ereignis `eingang`/`geaendert` bringt die Seite dazu, `eingang/list` neu zu holen. Die Einträge zeigen auf die Serie `pruef` („bitte ansehen“). */
  if (p === '/eingang' && req.method === 'POST') {
    const m = holeMock(u.searchParams.get('k') || 'admin');
    const { zustand } = JSON.parse(await koerper(req));
    const f = ZUSTAENDE_EINGANG[zustand];
    if (!f) { res.statusCode = 400; res.end(JSON.stringify({ fehler: 'unbekannter Zustand' })); return; }
    [m.backend.eingang, m.backend.eingangErledigt] = f(Date.now());
    if (zustand.startsWith('pruefen') && m.backend.serien.pruef) { // frühere Abläufe haben die Serie vielleicht schon bestätigt: wieder „bitte prüfen“
      const sr = m.backend.serien.pruef;
      sr.pruefen = true; sr.folgen[0].pruefen = true; sr.folgen[0].pruefen_gruende = ['tags_fehlen', 'nummer_doppelt'];
    }
    m.emit('eingang', 'geaendert', {});
    res.end(JSON.stringify({ zustand }));
    return;
  }
  /* A8f: Cover hochladen (POST, JPEG) und zurücksetzen (DELETE ?quelle=eigen). Prüft wie das Backend (Vertrag 14.3) Größe (3 MiB) und die
   * Kopfbytes eines JPEG, den Stand führt der Mock (`fetchWithAuth` in mock-hass.mjs). Der Lauf kommt im Kopf `x-tb-k`. */
  if (p.startsWith('/api/tobibox/cover/') && (req.method === 'POST' || req.method === 'DELETE')) {
    const m = holeMock(req.headers['x-tb-k'] || 'admin');
    const roh = Buffer.concat(await (async () => { const t = []; for await (const c of req) t.push(c); return t; })());
    const fehler = (status, code) => { res.statusCode = status; res.setHeader('content-type', 'application/json'); res.end(JSON.stringify({ v: 1, fehler: { code, text: code } })); };
    if (req.method === 'POST' && roh.length > 3 * 1024 * 1024) { fehler(413, 'datei_zu_gross'); return; }
    if (req.method === 'POST' && (roh.length < 3 || roh[0] !== 0xff || roh[1] !== 0xd8 || roh[2] !== 0xff)) { fehler(400, 'cover_ungueltig'); return; }
    if (req.method === 'POST') { // Maße aus dem JPEG-Kopf (SOF), damit die Prüfung sieht, was wirklich ankam
      let breite = null; let hoehe = null;
      for (let i = 2; i + 9 < roh.length;) {
        if (roh[i] !== 0xff) { i += 1; continue; }
        const mk = roh[i + 1];
        if (mk >= 0xc0 && mk <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(mk)) { hoehe = roh.readUInt16BE(i + 5); breite = roh.readUInt16BE(i + 7); break; }
        i += 2 + roh.readUInt16BE(i + 2);
      }
      (m.coverInfo ??= []).push({ methode: 'POST', pfad: p, groesse: roh.length, breite, hoehe });
    } else (m.coverInfo ??= []).push({ methode: 'DELETE', pfad: `${p}${u.search}` });
    const a = await m.hass.fetchWithAuth(`${p}${u.search}`, { method: req.method, headers: { 'Content-Type': req.headers['content-type'] }, body: req.method === 'POST' ? new Blob([roh]) : undefined });
    res.statusCode = a.status; res.setHeader('content-type', 'application/json'); res.end(JSON.stringify(await a.json()));
    return;
  }
  if (p.startsWith('/api/tobibox/cover/')) {
    const h = [...p.split('/').pop(), ...(u.searchParams.get('v') || '')].reduce((a, c) => a + c.charCodeAt(0), 0);
    res.setHeader('content-type', 'image/svg+xml');
    res.end(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="${FARBEN[h % 4]}"/><circle cx="${30 + h % 40}" cy="55" r="${15 + h % 20}" fill="#ffffffaa"/></svg>`);
    return;
  }
  if (p === '/seite.html' || p === '/messen.js') { datei(res, join(HIER, p.slice(1))); return; }
  if (p.startsWith('/f/')) {
    const ziel = resolve(FRONT, `.${p.slice(2)}`);
    if (ziel !== FRONT && !ziel.startsWith(FRONT + sep)) { res.statusCode = 403; res.end('nein'); return; }
    datei(res, ziel);
    return;
  }
  res.statusCode = 404; res.end('nicht da');
});
server.listen(Number(process.argv[2] || 0), '127.0.0.1', () => console.log(`PORT ${server.address().port}`));

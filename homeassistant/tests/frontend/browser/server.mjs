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
 * Aufruf: node server.mjs [Port]   (Port 0 oder keiner = freier Port). Die erste Zeile der Ausgabe ist `PORT <n>`.
 */
import http from 'node:http';
import { readFileSync, statSync } from 'node:fs';
import { join, extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const HIER = fileURLToPath(new URL('.', import.meta.url));
const FRONT = resolve(HIER, '../../../custom_components/tobibox/frontend');
const { createMockHass, FAEHIGKEITEN, FAEHIGKEITEN_V11, mitStaenden } = await import(new URL('../mock-hass.mjs', import.meta.url));

const folge = (name, anzeige, extra = {}) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * 1048576, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });

function bauen(schluessel) {
  const profil = schluessel.split('~')[0];
  const leer = profil === 'leer';
  const m = createMockHass({
    faehigkeiten: [...new Set([...FAEHIGKEITEN, ...FAEHIGKEITEN_V11, 'konfig_staende', 'hoerkopie'])],
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
    b.zuordnungen.LANG0001 = { uid: 'LANG0001', name: 'Löwe', ziel: { typ: 'serie', serie: 'lang' } };
    b.zuordnungen.LANG0002 = { uid: 'LANG0002', name: null, ziel: { typ: 'folge', serie: 'lang', folge: 'f02.mp3' } };
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
  return m;
}

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
  if (p.startsWith('/api/tobibox/cover/')) {
    const h = [...p.split('/').pop()].reduce((a, c) => a + c.charCodeAt(0), 0);
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

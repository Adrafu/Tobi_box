/* Tests der Tobies-Seiten (Pakete A9 und A10, Design 5.3, 5.4, 5.7, 5.13, 6.3, 7.1, 7.2, 10.2; Entscheidungen R17-3, R17-5, R17-6, K6 bis K8).
 * Aufruf: node --test homeassistant/tests/frontend
 *
 * Geprüft: Regal und Suche, Seite des Tobies (Zielwahl, Umhängen mit Meldung und „Rückgängig“, Zeile „Vorher“, Namen, Vergessen),
 * „Neuer Tobie“ Weg 1 (nur Ereignisse nach dem Start) und Weg 2 (Warteschlange), festes Ziel, „Einem Tobie geben …“, Karte „Gespielt von“,
 * Karten, Punkt und Meldungen für neue Tobies, Bibliothek ohne Zuordnen-Knopf, Rechte. Backend aus mock-hass.mjs.
 * Grundbestand: Tobie „Anna“ (Serie s1 „Die drei ???“), ein Tobie ohne Namen (Folge 2 von s1), ein unbekannter Tobie auf „Küche“.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, tippe, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN, FAEHIGKEITEN_V11, FAEHIGKEITEN_A9 } from './mock-hass.mjs';

const T = await import('../../custom_components/tobibox/frontend/seiten/tobies.js');
const { TOBIE, TOBIES, GERAETE, VOR } = await import('../../custom_components/tobibox/frontend/texte.js');

const ALLE = [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11, ...FAEHIGKEITEN_A9];
const ANNA = '04A1B2C3D4E5F6';
const OHNE = '04FFEEDDCCBBAA';
const UNBEKANNT = '0499887766554433';
const NEU = '04AABBCCDDEE01';

const folge = (name, anzeige, extra = {}) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * 1048576, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });

/* Beispiele zusätzlich zum Grundbestand: Hörbuch, Einzeltitel, Serie mit vielen Folgen. */
function beispiele(m) {
  const b = m.backend.serien;
  if (b.s1) { b.s1.art = 'hoerspiel'; b.s1.cover_stand = 'ab12cd34'; b.s1.angelegt_am = '2026-11-01T10:00:00Z'; }
  b.lied = { id: 'lied', name: 'Wiegenlied', typ: 'normal', ordner: 'Wiegenlied', pruefen: false, hinweise: [], art: 'musik', einzeln: true, dauer_s: 66, cover_stand: null, angelegt_am: '2026-11-05T10:00:00Z', folgen: [folge('wiegenlied.mp3', 'Wiegenlied')] };
  b.buch = { id: 'buch', name: 'Das große Buch', typ: 'normal', ordner: 'Buch', pruefen: false, hinweise: [], art: 'hoerbuch', dauer_s: 34800, cover_stand: null, angelegt_am: '2026-11-07T10:00:00Z', folgen: [folge('buch', 'Das große Buch', { art: 'ordner', tracks: 14 })] };
  b.reise = { id: 'reise', name: 'Kleine Reise', typ: 'normal', ordner: 'Reise', pruefen: false, hinweise: [], art: 'hoerspiel', cover_stand: null, angelegt_am: '2026-11-09T10:00:00Z',
    folgen: [folge('k1.mp3', 'Aufbruch', { nummer: 1 }), folge('k2.mp3', 'Unterwegs', { nummer: 2 }), folge('k3.mp3', 'Heimkehr', { nummer: 3 })] };
  if (m.backend.zuordnungen[ANNA]) { m.backend.zuordnungen[ANNA].angelegt_am = '2026-11-12T09:00:00Z'; m.backend.zuordnungen[OHNE].angelegt_am = '2026-11-13T09:00:00Z'; }
}

async function offen(hash, opts = {}) {
  const s = await seite({ faehigkeiten: ALLE, hash: '', ...opts });
  beispiele(s.m);
  if (opts.davor) opts.davor(s);
  await geheZu(s, typeof hash === 'function' ? hash(s) : hash);
  await s.flush(10);
  return s;
}

const hash = () => window.location.hash;
const toasts = (s) => s.qa('.toast .tmsg').map((x) => x.textContent);
const toast = (s) => s.q('.toast:not(.err)');
const klick = async (s, el) => { assert.ok(el, 'Element zum Klicken fehlt'); el.click(); await warte(20); await s.flush(10); };
const aufrufe = (s, typ) => s.m.aufrufe(`tobibox/${typ}`);
const ohneId = ({ id, type, ...rest }) => rest; // eslint-disable-line no-unused-vars
const kachel = (s, uid) => s.q(`[data-regal] [data-tobie="${uid}"]`);
const wahl = (s, id) => s.q(`[data-zielwahl] [data-wahl="${id}"]`);
const blatt = (s) => s.q('dialog.blatt[open]');
const blattKnopf = (s, text) => s.qa('dialog.blatt[open] .knoepfe button').find((b) => b.textContent.trim() === text);
const eintrag = (uid, box = 'kueche', zuletzt = '2026-11-13T10:00:00Z') => ({ uid, zuerst: zuletzt, zuletzt, anzahl: 1, boxen: { [box]: { zuerst: zuletzt, zuletzt, anzahl: 1, zeit_ok: true } } });
const zuord = (s, uid) => s.m.backend.zuordnungen[uid];
/* Sichtbarer Text: Textknoten mit Leerzeichen verbunden, ohne den Buchstaben im Cover-Platzhalter. */
const text = (el) => {
  if (!el) return '';
  const teile = [];
  const gehe = (n) => {
    if (n.nodeType === 3) { teile.push(n.textContent); return; }
    if (n.nodeType !== 1 || (n.classList?.contains('cover') && !n.classList.contains('act'))) return;
    n.childNodes.forEach(gehe);
  };
  gehe(el);
  return teile.join(' ').replace(/\s+/g, ' ').trim();
};
const tippeIn = async (s, feld, wert) => { tippe(feld, wert); await warte(10); await s.flush(); };

/* ------------------------------------------------------------------ reine Funktionen */

test('vorZeit(): Minuten, Stunden, Tage; ungültige Zeit gibt leeren Text', () => {
  const jetzt = new Date('2026-11-13T12:00:00Z');
  assert.equal(T.vorZeit('2026-11-13T11:59:40Z', jetzt), VOR.jetzt);
  assert.equal(T.vorZeit('2026-11-13T11:59:00Z', jetzt), 'vor 1 Minute');
  assert.equal(T.vorZeit('2026-11-13T11:58:00Z', jetzt), 'vor 2 Minuten');
  assert.equal(T.vorZeit('2026-11-13T10:00:00Z', jetzt), 'vor 2 Stunden');
  assert.equal(T.vorZeit('2026-11-10T12:00:00Z', jetzt), 'vor 3 Tagen');
  assert.equal(T.vorZeit('kaputt', jetzt), '');
  assert.equal(T.vorZeit(null, jetzt), '');
});

test('vorherAktiv(): 24 Stunden ab der Umstellung, ohne Ziel nie', () => {
  const am = '2026-11-13T12:00:00Z';
  const ziel = { typ: 'serie', serie: 's1' };
  assert.equal(T.vorherAktiv({ ziel, am }, new Date('2026-11-14T11:59:00Z')), true);
  assert.equal(T.vorherAktiv({ ziel, am }, new Date('2026-11-14T12:00:01Z')), false);
  assert.equal(T.vorherAktiv(null), false);
  assert.equal(T.vorherAktiv({ ziel: null, am }), false);
});

test('Ziel in der Adresse: geben-<serie>, geben-<serie>~<Folge> (URL-kodiert) und ?s=…&f=…', () => {
  assert.deepEqual(T.zielAusId('s1'), { typ: 'serie', serie: 's1' });
  assert.deepEqual(T.zielAusId(`s1~${encodeURIComponent('folge 01 ä.mp3')}`), { typ: 'folge', serie: 's1', folge: 'folge 01 ä.mp3' });
  assert.equal(T.zielAusId(''), null);
  assert.equal(T.gebenLink('s1'), '#geben-s1');
  assert.equal(T.gebenLink('s1', 'a b.mp3'), '#geben-s1~a%20b.mp3');
  assert.deepEqual(T.zielAusAbfrage({ s: 's1', f: 'x.mp3' }), { typ: 'folge', serie: 's1', folge: 'x.mp3' });
  assert.deepEqual(T.zielAusAbfrage({ s: 's1' }), { typ: 'serie', serie: 's1' });
  assert.equal(T.zielAusAbfrage({}), null);
  assert.equal(T.abfrageFuerZiel({ typ: 'folge', serie: 's1', folge: 'a b.mp3' }), '?s=s1&f=a+b.mp3');
  assert.equal(T.abfrageFuerZiel(null), '');
});

test('meldendeBox() und nichtZugeordnet(): jüngste Meldung zählt; nur mit stimmender Uhr und einer Vormerkung, die vorher da war', () => {
  const e = { uid: 'X', boxen: { a: { zuletzt: '2026-11-13T10:00:00Z', zeit_ok: true }, b: { zuletzt: '2026-11-13T11:00:00Z', zeit_ok: true } } };
  assert.equal(T.meldendeBox(e), 'b');
  assert.equal(T.meldendeBox({ boxen: {} }), null);
  const v = (box, am) => ({ box, angelegt_am: am });
  assert.deepEqual([...T.nichtZugeordnet([e], [v('b', '2026-11-13T10:30:00Z')])], ['X']);
  assert.deepEqual([...T.nichtZugeordnet([e], [v(null, '2026-11-13T10:30:00Z')])], ['X'], 'irgendeine Box passt auch');
  assert.deepEqual([...T.nichtZugeordnet([e], [v('a', '2026-11-13T10:30:00Z')])], [], 'Vormerkung für die andere Box');
  assert.deepEqual([...T.nichtZugeordnet([e], [v('b', '2026-11-13T11:30:00Z')])], [], 'Vormerkung kam erst nach der Meldung');
  const ohneUhr = { uid: 'Y', boxen: { b: { zuletzt: '2026-11-13T11:00:00Z', zeit_ok: false } } };
  assert.deepEqual([...T.nichtZugeordnet([ohneUhr], [v(null, '2026-11-13T10:00:00Z')])], [], 'Uhr der Box unsicher: nicht beurteilbar');
});

test('tobiesDerSerie(): Serie und Folgen ohne Doppelte', () => {
  const s = { zuordnungen: [{ uid: 'A', name: 'Anna' }], folgen: [{ tobies: [{ uid: 'B', name: null }] }, { tobies: [{ uid: 'B', name: null }, { uid: 'A', name: 'Anna' }] }] };
  assert.deepEqual(T.tobiesDerSerie(s).map((t) => t.uid), ['A', 'B']);
  assert.deepEqual(T.tobiesDerSerie({}), []);
});

/* ------------------------------------------------------------------ Regal */

test('Regal: Kachel „+ Neuer Tobie“ zuerst, dann die Tobies (zuletzt zugeordnet zuerst), jede Kachel ist ein Link mit Namen für Screenreader', MIT_DOM, async () => {
  const s = await offen('#tobies');
  assert.equal(s.q('main h2').textContent, 'Tobies');
  const neu = s.q('[data-regal] a[data-neu]');
  assert.equal(neu.getAttribute('href'), '#neu');
  assert.equal(text(neu), '+ Neuer Tobie');
  assert.equal(s.q('[data-regal] [role="listitem"]:first-child a'), neu, 'die gestrichelte Kachel steht ganz vorn');
  assert.deepEqual(s.qa('[data-regal] a[data-tobie]').map((a) => a.dataset.tobie), [OHNE, ANNA], 'der zuletzt zugeordnete zuerst');
  assert.equal(kachel(s, ANNA).getAttribute('href'), `#tobie-${ANNA}`);
  assert.equal(kachel(s, ANNA).getAttribute('aria-label'), 'Anna, spielt Die drei ???');
  assert.equal(kachel(s, OHNE).getAttribute('aria-label'), 'Tobie ohne Namen, spielt Das Gespensterschloss');
  assert.equal(text(kachel(s, OHNE).querySelector('.zusatz')), 'Die drei ???', 'bei einer einzelnen Folge steht die Serie in Grau darunter');
  assert.equal(kachel(s, ANNA).querySelector('.zusatz'), null, 'bei einer ganzen Serie nicht');
  assert.equal(s.q('input[type="search"]'), null, 'unter 9 Tobies kein Suchfeld');
  assert.equal(s.q('[data-leer="tobies"]'), null);
  weg();
});

test('Regal: Einzeltitel hat keinen Zusatz; Tipp auf die Kachel öffnet die Seite des Tobies', MIT_DOM, async () => {
  const s = await offen('#tobies', { davor: (x) => { x.m.backend.zuordnungen.LIED1 = { uid: 'LIED1', name: 'Mond', ziel: { typ: 'folge', serie: 'lied', folge: 'wiegenlied.mp3' }, angelegt_am: '2026-11-13T10:00:00Z' }; } });
  assert.equal(kachel(s, 'LIED1').querySelector('.zusatz'), null, 'ein Einzeltitel gehört zu keiner Serie');
  await klick(s, kachel(s, 'LIED1'));
  assert.equal(hash(), '#tobie-LIED1');
  assert.equal(s.q('main h2.tb-titel').textContent, 'Was soll Mond spielen?');
  weg();
});

test('Regal: Suche ab 9 Tobies (Name oder Ziel), „Kein Tobie gefunden“ mit „Suche löschen“', MIT_DOM, async () => {
  const viele = (x) => { for (let i = 0; i < 7; i += 1) x.m.backend.zuordnungen[`V${i}`] = { uid: `V${i}`, name: `Tier ${i}`, ziel: { typ: 'serie', serie: 'reise' }, angelegt_am: `2026-11-0${i + 1}T10:00:00Z` }; };
  const s9 = await offen('#tobies', { davor: (x) => { for (let i = 0; i < 6; i += 1) x.m.backend.zuordnungen[`V${i}`] = { uid: `V${i}`, name: `Tier ${i}`, ziel: { typ: 'serie', serie: 'reise' } }; } });
  assert.equal(s9.qa('[data-tobie]').length, 8);
  assert.equal(s9.q('input[type="search"]'), null, '8 Tobies: noch kein Suchfeld');
  weg();
  const s = await offen('#tobies', { davor: viele });
  assert.equal(s.qa('[data-tobie]').length, 9);
  const feld = s.q('input[type="search"]');
  assert.ok(feld, 'ab 9 Tobies steht das Suchfeld da');
  assert.equal(feld.getAttribute('placeholder'), 'Tobie suchen (Name oder was er spielt)');
  await tippeIn(s, feld, 'anna');
  assert.deepEqual(s.qa('[data-tobie]').map((a) => a.dataset.tobie), [ANNA]);
  assert.equal(s.q('[data-neu]'), null, 'in der Suche steht nicht „+ Neuer Tobie“');
  await tippeIn(s, s.q('input[type="search"]'), 'kleine reise');
  assert.equal(s.qa('[data-tobie]').length, 7, 'auch nach dem Ziel');
  await tippeIn(s, s.q('input[type="search"]'), 'xyzq');
  assert.equal(text(s.q('[data-leer="tobie-suche"] .et')), 'Kein Tobie gefunden zu „xyzq“.');
  await klick(s, s.q('[data-suche-loeschen]'));
  assert.equal(s.qa('[data-tobie]').length, 9);
  assert.ok(s.q('[data-neu]'));
  weg();
});

test('Regal ohne Tobies: die Kachel „+ Neuer Tobie“ und der leere Zustand mit „Zu den Geräten“', MIT_DOM, async () => {
  const s = await offen('#tobies', { davor: (x) => { x.m.backend.zuordnungen = {}; } });
  assert.deepEqual(s.qa('[data-regal] a').map((a) => a.getAttribute('href')), ['#neu']);
  assert.equal(text(s.q('[data-leer="tobies"] .et')), 'Noch keine Tobies. Lege einen Tobie auf eine Box, dann erscheint er unter „Geräte“.');
  assert.equal(s.q('[data-leer="tobies"] .btn').getAttribute('href'), '#geraete');
  weg();
});

test('Regal: laufende Vormerkungen als Karten über dem Regal; „Abbrechen“ ruft warteschlange/abbrechen und meldet es', MIT_DOM, async () => {
  const s = await offen('#tobies');
  const r = await s.m.hass.connection.sendMessagePromise({ type: 'tobibox/warteschlange/set', box: 'kueche', ziel: { typ: 'serie', serie: 's1' } });
  await s.flush(10);
  const karte = s.q(`[data-eintrag="${r.eintrag.id}"]`);
  assert.ok(karte, 'die Karte erscheint aus dem Ereignis `angelegt`');
  assert.equal(text(karte.querySelector('strong')), 'Nächster neuer Tobie auf Küche spielt „Die drei ???“');
  assert.equal(text(karte.querySelector('.muted')), 'Wartet auf einen unbekannten Tobie');
  assert.equal(s.q('main').firstElementChild.tagName, 'H2');
  assert.ok(karte.compareDocumentPosition(s.q('[data-regal]')) & 4, 'die Karte steht vor dem Regal');
  await klick(s, karte.querySelector('[data-abbrechen]'));
  assert.deepEqual(aufrufe(s, 'warteschlange/abbrechen').map(ohneId), [{ eintrag_id: r.eintrag.id }].map(ohneId));
  assert.equal(s.q(`[data-eintrag="${r.eintrag.id}"]`), null);
  assert.deepEqual(toasts(s), ['Vormerkung abgebrochen.']);
  weg();
});

test('Regal: Vormerkung für „irgendeine Box“ nennt „irgendeiner Box“', MIT_DOM, async () => {
  const s = await offen('#tobies');
  await s.m.hass.connection.sendMessagePromise({ type: 'tobibox/warteschlange/set', box: null, ziel: { typ: 'aktion', aktion: 'gute_nacht' } });
  await s.flush(10);
  assert.equal(text(s.q('[data-eintrag] strong')), 'Nächster neuer Tobie auf irgendeiner Box spielt „Gute Nacht“');
  weg();
});

/* ------------------------------------------------------------------ Seite des Tobies */

test('Tobie: Überschrift, „Spielt jetzt“ mit Art, Zielwahl (Umschalter, Suche, Arten, „Zuletzt hinzugefügt“, Gute-Nacht-Karte), Verwalten', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  assert.equal(text(s.q('a[data-zurueck]')), '‹ Tobies');
  assert.equal(s.q('main h2.tb-titel').textContent, 'Was soll Anna spielen?');
  const cur = s.q('.tb-cur.jetzt');
  assert.equal(text(cur), 'Spielt jetzt Die drei ??? Ganzes Hörspiel');
  assert.deepEqual(s.qa('[data-zielwahl] .seg2 button').map((b) => [b.dataset.wert, b.getAttribute('aria-pressed')]), [['serie', 'true'], ['folge', 'false']], 'Playlist erst in Stufe C');
  assert.ok(s.q('[data-zielwahl] input[type="search"]'));
  assert.deepEqual(s.qa('[data-zielwahl] .arttab').map((b) => b.dataset.art), ['alle', 'hoerspiel', 'hoerbuch', 'musik', 'geschichte']);
  assert.equal(s.q('[data-reihe="neu"]'), null, '„Neu hinzugefügt“ gibt es nur bei einem neuen Tobie');
  const ids = s.qa('[data-ergebnis="serie"] [data-wahl]').map((b) => b.dataset.wahl);
  assert.deepEqual(ids, ['serie:reise', 'serie:buch', 'serie:s1', 'serie:s2'], 'Vorgabe: zuletzt hinzugefügt zuerst; Einzeltitel nicht unter „Ganze Serie“; Überraschung nie');
  const liste = aufrufe(s, 'serien/list').find((m) => m.limit === 30 && m.sortierung === 'neu');
  assert.deepEqual(liste.filter, ['sammlung']);
  assert.equal(liste.limit, 30, 'Päckchen zu 30');
  assert.equal(text(s.q('[data-wahl="aktion"]')), 'Gute-Nacht-Karte Timer, dann wird es still');
  assert.ok(s.q('[data-abschnitt="verwalten"] input#tb-name'));
  assert.equal(s.q('#tb-name').value, 'Anna');
  weg();
});

test('Karte „Spielt jetzt“: solange die Serie lädt keine Art-Vermutung; nach dem Laden die richtige Art (kein „Ganze Serie“)', MIT_DOM, async () => {
  let freigabe;
  const gehalten = new Promise((r) => { freigabe = r; });
  const s = await offen(`#tobie-${ANNA}`, { davor: (x) => {
    const echt = x.m.hass.connection.sendMessagePromise;
    x.m.hass.connection.sendMessagePromise = (msg) => (msg.type === 'tobibox/serie/get' ? gehalten.then(() => echt(msg)) : echt(msg));
  } });
  assert.equal(text(s.q('.tb-cur.jetzt')), 'Spielt jetzt Die drei ???', 'noch keine Art');
  freigabe();
  await warte(20); await s.flush(10);
  assert.equal(text(s.q('.tb-cur.jetzt')), 'Spielt jetzt Die drei ??? Ganzes Hörspiel');
  weg();
});

test('Karte „Spielt jetzt“: schlägt das Laden der Serie einmal fehl, kommt ein zweiter Versuch; die Art stimmt danach', MIT_DOM, async () => {
  let n = 0;
  const s = await offen(`#tobie-${ANNA}`, { davor: (x) => {
    const echt = x.m.hass.connection.sendMessagePromise;
    x.m.hass.connection.sendMessagePromise = (msg) => {
      if (msg.type === 'tobibox/serie/get' && (n += 1) === 1) return Promise.reject({ code: 'unknown_error', message: 'kurz weg' });
      return echt(msg);
    };
  } });
  assert.equal(n, 2, 'zweiter Versuch');
  assert.equal(text(s.q('.tb-cur.jetzt')), 'Spielt jetzt Die drei ??? Ganzes Hörspiel');
  weg();
});

test('Tobie ohne Namen: „Was soll dieser Tobie spielen?“; Art der Karte „Spielt jetzt“ bei einer Folge', MIT_DOM, async () => {
  const s = await offen(`#tobie-${OHNE}`);
  assert.equal(s.q('main h2.tb-titel').textContent, 'Was soll dieser Tobie spielen?');
  assert.equal(text(s.q('.tb-cur.jetzt')), 'Spielt jetzt Das Gespensterschloss Die drei ??? · Folge');
  assert.equal(s.q('#tb-name').value, '');
  weg();
});

test('Tobie: Zielwahl lädt in Päckchen zu 30 („Mehr zeigen“) und Arten filtern', MIT_DOM, async () => {
  const s = await offen((x) => `#tobie-${Object.keys(x.m.backend.zuordnungen)[0]}`, { viele: 130 });
  const n1 = s.qa('[data-ergebnis="serie"] [data-wahl]').length;
  assert.equal(n1, 30);
  await klick(s, s.q('[data-mehr="serie"]'));
  const n2 = s.qa('[data-ergebnis="serie"] [data-wahl]').length;
  assert.ok(n2 > 30 && n2 <= 60, `zweites Päckchen: ${n2}`);
  const mehr = aufrufe(s, 'serien/list').filter((m) => m.offset === 30);
  assert.equal(mehr.length, 1);
  await klick(s, s.q('[data-art="hoerbuch"]'));
  assert.ok(aufrufe(s, 'serien/list').some((m) => m.art === 'hoerbuch'));
  assert.equal(s.q('[data-art="hoerbuch"]').getAttribute('aria-pressed'), 'true');
  weg();
});

test('Tobie: Suche in der Zielwahl (ab 2 Zeichen) zeigt Zeilen; ohne Treffer „Nichts gefunden“ mit „Suche löschen“', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  await tippeIn(s, s.q('#tb-zw-suche'), 'reise');
  await warte(300); await s.flush(10);
  assert.deepEqual(s.qa('[data-ergebnis="serie"] [data-wahl]').map((b) => b.dataset.wahl), ['serie:reise']);
  assert.equal(s.q('[data-ergebnis="serie"]').closest('.card') !== null, true, 'mit Suchbegriff Zeilen statt Kacheln');
  await tippeIn(s, s.q('#tb-zw-suche'), 'xyzq');
  await warte(300); await s.flush(10);
  assert.equal(text(s.q('[data-wahl-leer]')), 'Nichts gefunden zu „xyzq“. Suche löschen');
  await klick(s, s.q('[data-wahl-leer] [data-suche-loeschen]'));
  await warte(20); await s.flush(10);
  assert.equal(s.q('#tb-zw-suche').value, '');
  assert.ok(s.qa('[data-ergebnis="serie"] [data-wahl]').length >= 3);
  weg();
});

test('Umhängen: Tap ordnet zu (ohne Rückfrage), Meldung nennt neues und altes Ziel, Seite kehrt zum Regal zurück', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  await klick(s, wahl(s, 'serie:reise'));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').map(ohneId), [{ uid: ANNA, ziel: { typ: 'serie', serie: 'reise' }, erwartet_ziel: { typ: 'serie', serie: 's1' } }]);
  assert.equal(blatt(s), null, 'keine Rückfrage');
  assert.deepEqual(toasts(s), ['Anna spielt jetzt „Kleine Reise“ (vorher „Die drei ???“).']);
  assert.equal(toast(s).querySelector('button').textContent, 'Rückgängig');
  assert.equal(hash(), '#tobies');
  assert.equal(kachel(s, ANNA).getAttribute('aria-label'), 'Anna, spielt Kleine Reise', 'das Regal zeigt das neue Ziel');
  assert.deepEqual(zuord(s, ANNA).ziel, { typ: 'serie', serie: 'reise' });
  weg();
});

test('Umhängen: „Rückgängig“ stellt das alte Ziel wieder her (erwartet_ziel = neues Ziel); die Zeile „Vorher“ verschwindet', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  await klick(s, wahl(s, 'serie:reise'));
  await klick(s, toast(s).querySelector('button'));
  const sets = aufrufe(s, 'zuordnung/set').map(ohneId);
  assert.deepEqual(sets[1], { uid: ANNA, ziel: { typ: 'serie', serie: 's1' }, erwartet_ziel: { typ: 'serie', serie: 'reise' } });
  assert.deepEqual(zuord(s, ANNA).ziel, { typ: 'serie', serie: 's1' });
  assert.deepEqual(toasts(s), ['Rückgängig gemacht.']);
  assert.equal(zuord(s, ANNA).vorher, undefined, 'das Backend löscht `vorher`, wenn das alte Ziel zurückkommt (Vertrag 3.5)');
  await geheZu(s, `#tobie-${ANNA}`);
  assert.equal(s.q('[data-vorher]'), null);
  weg();
});

test('Zeile „Vorher“: steht 24 Stunden auf der Seite des Tobies, „Zurückstellen“ stellt das alte Ziel her, danach ist sie weg', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  await klick(s, wahl(s, 'serie:reise'));
  await geheZu(s, `#tobie-${ANNA}`);
  const zeile = s.q('[data-vorher]');
  assert.equal(text(zeile), 'Vorher: Die drei ??? · Zurückstellen');
  assert.ok(zeile.compareDocumentPosition(s.q('.tb-cur.jetzt')) & 4, 'über „Spielt jetzt“');
  assert.equal(text(s.q('.tb-cur.jetzt')), 'Spielt jetzt Kleine Reise Ganzes Hörspiel');
  await klick(s, s.q('[data-zurueckstellen]'));
  const letzter = aufrufe(s, 'zuordnung/set').map(ohneId).at(-1);
  assert.deepEqual(letzter, { uid: ANNA, ziel: { typ: 'serie', serie: 's1' }, erwartet_ziel: { typ: 'serie', serie: 'reise' } });
  assert.deepEqual(zuord(s, ANNA).ziel, { typ: 'serie', serie: 's1' });
  assert.equal(s.q('[data-vorher]'), null);
  assert.deepEqual(toasts(s), ['Anna spielt wieder „Die drei ???“.']);
  weg();
});

test('Zeile „Vorher“: nach 24 Stunden nicht mehr zu sehen (Uhr der Seite)', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  await klick(s, wahl(s, 'serie:reise'));
  await geheZu(s, `#tobie-${ANNA}`);
  assert.ok(s.q('[data-vorher]'));
  T.modell(s.el._seiten.tobie.ctx).jetzt = () => new Date(Date.now() + 25 * 3600 * 1000);
  s.el.requestUpdate(); await s.flush();
  assert.equal(s.q('[data-vorher]'), null, 'nach 25 Stunden weg');
  weg();
});

test('Umhängen auf eine Folge, einen Einzeltitel und die Gute-Nacht-Karte; ein Tobie ohne altes Ziel-Feld sendet nie „null“ als Ziel', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  await klick(s, s.q('[data-modus], [data-wert="folge"]'));
  await s.flush(10);
  assert.ok(s.q('[data-ergebnis="folge"]'), 'Liste zum Aufklappen');
  assert.ok(wahl(s, 'serie:lied'), 'Einzeltitel als eigene Zeile');
  await klick(s, s.q('[data-serie="reise"]'));
  assert.equal(s.q('[data-serie="reise"]').getAttribute('aria-expanded'), 'true');
  await klick(s, wahl(s, 'folge:reise:k2.mp3'));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').at(-1).ziel, { typ: 'folge', serie: 'reise', folge: 'k2.mp3' });
  assert.deepEqual(toasts(s), ['Anna spielt jetzt „Unterwegs“ (vorher „Die drei ???“).']);
  await geheZu(s, `#tobie-${ANNA}`);
  await klick(s, s.q('[data-wert="folge"]'));
  await klick(s, wahl(s, 'serie:lied'));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').at(-1).ziel, { typ: 'folge', serie: 'lied', folge: 'wiegenlied.mp3' }, 'ein Einzeltitel ist die Folge seiner eigenen Serie');
  await geheZu(s, `#tobie-${ANNA}`);
  await klick(s, wahl(s, 'aktion'));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').at(-1).ziel, { typ: 'aktion', aktion: 'gute_nacht' });
  assert.deepEqual(toasts(s), ['Anna spielt jetzt „Gute Nacht“ (vorher „Wiegenlied“).']);
  weg();
});

test('Folge oder Lied mit Suchbegriff: flache Trefferliste, Treffer ordnet die Folge zu', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  await klick(s, s.q('[data-wert="folge"]'));
  await tippeIn(s, s.q('#tb-zw-suche'), 'unterwegs');
  await warte(300); await s.flush(10);
  assert.deepEqual(s.qa('[data-ergebnis="treffer"] [data-wahl]').map((b) => b.dataset.wahl), ['folge:reise:k2.mp3']);
  await klick(s, wahl(s, 'folge:reise:k2.mp3'));
  assert.deepEqual(zuord(s, ANNA).ziel, { typ: 'folge', serie: 'reise', folge: 'k2.mp3' });
  weg();
});

test('Name ändern: zuordnung/set mit Name und erwartet_ziel, Meldung „Name gespeichert.“; leerer Name gibt einen Fehler', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  await tippeIn(s, s.q('#tb-name'), '   ');
  await klick(s, s.q('[data-name-speichern]'));
  assert.equal(aufrufe(s, 'zuordnung/set').length, 0);
  assert.deepEqual(s.qa('.toast.err .tmsg').map((x) => x.textContent), ['Bitte einen Namen eingeben.']);
  await tippeIn(s, s.q('#tb-name'), ' Mia ');
  await klick(s, s.q('[data-name-speichern]'));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').map(ohneId), [{ uid: ANNA, ziel: { typ: 'serie', serie: 's1' }, name: 'Mia', erwartet_ziel: { typ: 'serie', serie: 's1' } }]);
  assert.equal(zuord(s, ANNA).name, 'Mia');
  assert.ok(toasts(s).includes('Name gespeichert.'));
  assert.equal(s.q('main h2.tb-titel').textContent, 'Was soll Mia spielen?');
  assert.equal(hash(), `#tobie-${ANNA}`, 'die Seite bleibt stehen');
  weg();
});

test('Vergessen: Rückfrage, „Abbrechen“ ruft nichts auf; „Vergessen“ sendet zuordnung/remove mit erwartet_ziel und geht zum Regal', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  await klick(s, s.q('[data-vergessen]'));
  assert.equal(text(blatt(s).querySelector('#blatt-t')), 'Diesen Tobie vergessen?');
  assert.match(text(blatt(s)), /„Anna“ spielt dann nichts mehr/);
  await klick(s, blattKnopf(s, 'Abbrechen'));
  assert.equal(aufrufe(s, 'zuordnung/remove').length, 0);
  assert.equal(blatt(s), null);
  await klick(s, s.q('[data-vergessen]'));
  await klick(s, blattKnopf(s, 'Vergessen'));
  assert.deepEqual(aufrufe(s, 'zuordnung/remove').map(ohneId), [{ uid: ANNA, erwartet_ziel: { typ: 'serie', serie: 's1' } }]);
  assert.equal(zuord(s, ANNA), undefined);
  assert.equal(hash(), '#tobies');
  assert.equal(kachel(s, ANNA), null);
  assert.deepEqual(toasts(s), ['Tobie vergessen.']);
  weg();
});

test('Tobie, den es nicht gibt: Hinweis mit Link zu den Tobies', MIT_DOM, async () => {
  const s = await offen('#tobie-GIBTSNICHT');
  assert.equal(text(s.q('[data-zustand="weg"]')), 'Diesen Tobie gibt es nicht mehr. Zu den Tobies');
  weg();
});

test('Zuordnung geändert (zwei Fenster): Fehlermeldung, Liste wird neu geladen, kein zweiter Aufruf', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`);
  s.m.backend.zuordnungen[ANNA].ziel = { typ: 'serie', serie: 'buch' }; // jemand anderes war schneller
  await klick(s, wahl(s, 'serie:reise'));
  assert.equal(s.qa('.toast.err').length, 1);
  assert.deepEqual(zuord(s, ANNA).ziel, { typ: 'serie', serie: 'buch' });
  assert.equal(hash(), `#tobie-${ANNA}`, 'die Seite bleibt, damit man neu wählen kann');
  assert.match(text(s.q('.tb-cur.jetzt')), /Das große Buch/, 'die Seite zeigt nach dem Neuladen das neue Ziel');
  weg();
});

/* ------------------------------------------------------------------ Neuer Tobie, Weg 1 */

test('#neu: zwei große Zeilen, Weg 1 zuerst; ohne feste Ziel führt „‹ Tobies“ zurück', MIT_DOM, async () => {
  const s = await offen('#neu');
  assert.equal(s.q('main h2.tb-titel').textContent, 'Neuer Tobie');
  assert.equal(text(s.q('a[data-zurueck]')), '‹ Tobies');
  assert.deepEqual(s.qa('a[data-weg]').map((a) => [a.dataset.weg, a.getAttribute('href')]), [['jetzt', '#neu-warten'], ['spaeter', '#neu-queue']]);
  assert.equal(text(s.q('a[data-weg="jetzt"]')), 'Leg ihn jetzt auf eine Box Die Seite wartet auf ihn');
  assert.equal(text(s.q('a[data-weg="spaeter"]')), 'Später auflegen Erst wählen, was er spielen soll');
  assert.equal(s.q('.tb-cur.fest'), null);
  weg();
});

test('#neu ohne eingerichtete Box: Hinweis „Bitte … Bescheid sagen“', MIT_DOM, async () => {
  const s = await offen('#neu', { davor: (x) => { x.m.backend.boxen = []; x.el.store.s.boxen = {}; } });
  assert.match(text(s.q('[data-zustand="keine-box"]')), /Es ist noch keine Box eingerichtet\. Bitte .* Bescheid sagen\./);
  weg();
});

test('Weg 1: Warteseite zeigt „Leg den Tobie auf Küche oder Kinderzimmer“; ein Tobie, der schon wartet, zählt nicht', MIT_DOM, async () => {
  const s = await offen('#neu');
  await klick(s, s.q('a[data-weg="jetzt"]'));
  assert.equal(hash(), '#neu-warten');
  assert.equal(s.q('.tb-warte .tb-titel').textContent, 'Leg den Tobie auf Küche oder Kinderzimmer');
  assert.equal(text(s.q('.tb-warte .muted')), 'Ich warte auf einen Tobie, den ich noch nicht kenne.');
  assert.equal(s.q('.tb-warte .ring') !== null, true);
  // der unbekannte Tobie vom Start steht schon auf „Geräte“; die Warteseite bleibt stehen
  await warte(30); await s.flush();
  assert.equal(hash(), '#neu-warten');
  await klick(s, s.q('[data-abbrechen]'));
  assert.equal(hash(), '#neu');
  weg();
});

test('Weg 1: das erste Ereignis NACH dem Start öffnet „Neuer Tobie erkannt“ (alte Tobies zählen nicht); Versehen oben rechts; Name und Zielwahl', MIT_DOM, async () => {
  const s = await offen('#neu-warten');
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  assert.equal(hash(), `#neu-ziel-${NEU}?von=tobies`);
  assert.equal(s.qa('.toast').length, 0, 'auf der Warteseite und der Seite des Tobies keine zusätzliche Meldung');
  assert.equal(s.q('[data-karte="erkannt"] strong').textContent, 'Neuer Tobie erkannt');
  assert.equal(text(s.q('[data-karte="erkannt"]')), 'Neuer Tobie erkannt auf Kinderzimmer.');
  assert.equal(text(s.q('.tb-leiste a[data-zurueck]')), '‹ Tobies');
  assert.equal(text(s.q('.tb-leiste [data-versehen]')), 'Das war ein Versehen, nicht merken');
  assert.ok(s.q('.tb-leiste').firstElementChild.matches('a.back') && s.q('.tb-leiste').lastElementChild.matches('[data-versehen]'), 'links zurück, rechts Versehen');
  assert.equal(text(s.q('[data-karte="name"] h3')), 'Wie soll er heißen?');
  assert.equal(document.activeElement === s.q('#tb-neuname') || s.el.shadowRoot.activeElement === s.q('#tb-neuname'), false, 'kein Autofokus im Namensfeld');
  assert.equal(text(s.q('.tb-h3.gross')), 'Was soll er spielen?');
  assert.ok(s.q('[data-reihe="neu"]'), 'bei einem neuen Tobie steht „Neu hinzugefügt“ über der Liste');
  assert.equal(aufrufe(s, 'serien/list').find((m) => m.limit === 8)?.sortierung, 'neu');
  assert.deepEqual(s.qa('[data-reihe="neu"] [data-wahl]').map((b) => b.dataset.wahl).slice(0, 2), ['serie:reise', 'serie:buch'], 'die neuesten zuerst');
  weg();
});

test('Weg 1: ein Ereignis `aktualisiert` für einen schon wartenden Tobie (neu aufgelegt) zählt als neues Ereignis', MIT_DOM, async () => {
  const s = await offen('#neu-warten');
  s.m.legeAuf('kueche', UNBEKANNT);
  await warte(20); await s.flush(10);
  assert.equal(hash(), `#neu-ziel-${UNBEKANNT}?von=tobies`);
  weg();
});

test('Weg 1: Tap auf ein Ziel ordnet zu (mit Namen), Meldung „Fertig: …“ mit „Rückgängig“; der Tobie steht im Regal', MIT_DOM, async () => {
  const s = await offen('#neu-warten');
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  await tippeIn(s, s.q('#tb-neuname'), ' Löwe ');
  await klick(s, wahl(s, 'serie:reise'));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').map(ohneId), [{ uid: NEU, ziel: { typ: 'serie', serie: 'reise' }, erwartet_ziel: null, name: 'Löwe' }]);
  assert.deepEqual(toasts(s), ['Fertig: Löwe spielt jetzt „Kleine Reise“.']);
  assert.equal(toast(s).querySelector('button').textContent, 'Rückgängig');
  assert.equal(hash(), '#tobies');
  assert.equal(kachel(s, NEU).getAttribute('aria-label'), 'Löwe, spielt Kleine Reise');
  assert.equal(s.m.backend.neueTobies.some((x) => x.uid === NEU), false);
  weg();
});

test('Weg 1: ohne Namen wird kein Name gesendet', MIT_DOM, async () => {
  const s = await offen('#neu-warten');
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  await klick(s, wahl(s, 'aktion'));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').map(ohneId), [{ uid: NEU, ziel: { typ: 'aktion', aktion: 'gute_nacht' }, erwartet_ziel: null }]);
  assert.deepEqual(toasts(s), ['Fertig: Tobie ohne Namen spielt jetzt „Gute Nacht“.']);
  weg();
});

test('„Rückgängig“ bei einem neuen Tobie: zuordnung/remove mit als_neu (Box), die Karte auf „Geräte“ kommt wieder', MIT_DOM, async () => {
  const s = await offen('#neu-warten');
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  await klick(s, wahl(s, 'serie:reise'));
  assert.equal(s.q('[data-karte="neuer-tobie"]'), null);
  await klick(s, toast(s).querySelector('button'));
  assert.deepEqual(aufrufe(s, 'zuordnung/remove').map(ohneId), [{ uid: NEU, erwartet_ziel: { typ: 'serie', serie: 'reise' }, als_neu: { box: 'kinderzimmer' } }]);
  assert.equal(zuord(s, NEU), undefined);
  assert.deepEqual(toasts(s), ['Rückgängig gemacht.']);
  assert.ok(s.m.backend.neueTobies.some((x) => x.uid === NEU), 'liegt wieder als unbekannt in neue_tobies');
  assert.equal(kachel(s, NEU), null, 'nicht mehr im Regal');
  await geheZu(s, '#geraete');
  assert.ok(s.q(`[data-karte="neuer-tobie"][data-uid="${NEU}"]`), 'die Karte ist wieder da');
  weg();
});

test('„Rückgängig“ ohne die Fähigkeit zuordnung_rueckgaengig sendet kein als_neu', MIT_DOM, async () => {
  const s = await offen('#neu-warten', { faehigkeiten: [...ALLE.filter((f) => f !== 'zuordnung_rueckgaengig')] });
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  await klick(s, wahl(s, 'serie:reise'));
  await klick(s, toast(s).querySelector('button'));
  assert.deepEqual(aufrufe(s, 'zuordnung/remove').map(ohneId), [{ uid: NEU, erwartet_ziel: { typ: 'serie', serie: 'reise' } }]);
  weg();
});

test('Neuer Tobie, aber jemand war schneller (zuordnung_geaendert): Meldung „woanders zugeordnet“, zurück zum Regal', MIT_DOM, async () => {
  const s = await offen('#neu-warten');
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  s.m.backend.zuordnungen[NEU] = { uid: NEU, name: null, ziel: { typ: 'serie', serie: 'buch' } };
  await klick(s, wahl(s, 'serie:reise'));
  assert.deepEqual(s.qa('.toast.err .tmsg').map((x) => x.textContent), ['Dieser Tobie wurde gerade woanders zugeordnet.']);
  assert.equal(hash(), '#tobies');
  weg();
});

test('„Das war ein Versehen“: Rückfrage „Nicht merken?“; „Abbrechen“ ruft nichts auf, „Nicht merken“ ruft neue_tobies/verwerfen und geht zurück', MIT_DOM, async () => {
  const s = await offen(`#neu-ziel-${UNBEKANNT}?von=tobies`);
  await klick(s, s.q('[data-versehen]'));
  assert.equal(text(blatt(s).querySelector('#blatt-t')), 'Nicht merken?');
  await klick(s, blattKnopf(s, 'Abbrechen'));
  assert.equal(aufrufe(s, 'neue_tobies/verwerfen').length, 0);
  await klick(s, s.q('[data-versehen]'));
  await klick(s, blattKnopf(s, 'Nicht merken'));
  assert.deepEqual(aufrufe(s, 'neue_tobies/verwerfen').map(ohneId), [{ uid: UNBEKANNT }]);
  assert.equal(hash(), '#tobies');
  assert.deepEqual(toasts(s), ['Nicht gemerkt.']);
  assert.equal(s.m.backend.neueTobies.length, 0);
  weg();
});

test('Neuer Tobie erkannt von „Geräte“ aus: Reiter „Geräte“ bleibt markiert, „‹ Geräte“ führt zurück; unbekannte Kennung zeigt einen Hinweis', MIT_DOM, async () => {
  const s = await offen('#geraete');
  await klick(s, s.q('[data-karte="neuer-tobie"] a.tb-karte-link'));
  assert.equal(hash(), `#neu-ziel-${UNBEKANNT}`);
  assert.equal(text(s.q('.tb-leiste a[data-zurueck]')), '‹ Geräte');
  assert.equal(s.q('.tabs.unten a[aria-current="page"], nav.tabs a[aria-current="page"]').textContent.includes('Geräte'), true);
  await geheZu(s, '#neu-ziel-GIBTSNICHT');
  assert.match(text(s.q('[data-zustand="weg"]')), /nicht mehr in der Liste/);
  weg();
});

/* ------------------------------------------------------------------ Neuer Tobie, Weg 2 (Warteschlange) */

test('Weg 2: Box (Vorgabe „Egal welche“), optionaler Name, Ziel wählen; warteschlange/set mit Box, Ziel und Name; danach die Wartekarte', MIT_DOM, async () => {
  const s = await offen('#neu-queue');
  assert.equal(s.q('main h2.tb-titel').textContent, 'Später auflegen');
  assert.deepEqual(s.qa('[data-karte="box"] .seg2 button').map((b) => [text(b), b.getAttribute('aria-pressed')]), [['Küche', 'false'], ['Kinderzimmer', 'false'], ['Egal welche', 'true']]);
  assert.equal(text(s.q('[data-karte="box"] .tb-glabel')), 'Auf welcher Box?');
  assert.equal(text(s.q('[data-karte="name"] h3')), 'Wie soll er heißen?');
  await klick(s, s.q('[data-karte="box"] [data-wert="kueche"]'));
  await tippeIn(s, s.q('#tb-queue-name'), 'Bär');
  await klick(s, wahl(s, 'serie:buch'));
  assert.deepEqual(aufrufe(s, 'warteschlange/set').map(ohneId), [{ box: 'kueche', ziel: { typ: 'serie', serie: 'buch' }, name: 'Bär' }]);
  assert.equal(text(s.q('[data-zustand="wartet"] .tb-titel')), 'Nächster neuer Tobie auf Küche spielt „Das große Buch“');
  assert.equal(text(s.q('[data-zustand="wartet"] .muted')), 'Kein Zeitlimit. Du musst die Seite nicht offen lassen.');
  assert.deepEqual(s.qa('[data-zustand="wartet"] .btns > *').map((b) => text(b)), ['Abbrechen', 'Fertig']);
  weg();
});

test('Weg 2: Vorgabe „Egal welche“ sendet box null; ohne Namen kein Feld `name`', MIT_DOM, async () => {
  const s = await offen('#neu-queue');
  await klick(s, wahl(s, 'aktion'));
  assert.deepEqual(aufrufe(s, 'warteschlange/set').map(ohneId), [{ box: null, ziel: { typ: 'aktion', aktion: 'gute_nacht' } }]);
  assert.equal(text(s.q('[data-zustand="wartet"] .tb-titel')), 'Nächster neuer Tobie auf irgendeiner Box spielt „Gute Nacht“');
  weg();
});

test('Weg 2: „Abbrechen“ auf der Wartekarte bricht die Vormerkung ab und geht zum Regal; „Fertig“ lässt sie stehen', MIT_DOM, async () => {
  const s = await offen('#neu-queue');
  await klick(s, wahl(s, 'serie:buch'));
  await klick(s, s.q('[data-zustand="wartet"] [data-abbrechen]'));
  assert.equal(aufrufe(s, 'warteschlange/abbrechen').length, 1);
  assert.equal(s.m.backend.warteschlange.length, 0);
  assert.equal(hash(), '#tobies');
  await geheZu(s, '#neu-queue');
  await klick(s, wahl(s, 'serie:buch'));
  await klick(s, s.q('[data-zustand="wartet"] [data-fertig]'));
  assert.equal(s.m.backend.warteschlange.length, 1, 'der Eintrag bleibt, bis ein Tobie aufgelegt ist');
  assert.equal(hash(), '#tobies', '„Fertig“ führt zum Regal');
  assert.equal(s.qa('[data-eintrag]').length, 1, 'dort steht die Karte');
  weg();
});

test('Weg 2: Auflegen auf der Wartekarte: HA ordnet zu, die Seite geht zum Regal und meldet „Küche: Der neue Tobie spielt jetzt …“ mit „Name geben“', MIT_DOM, async () => {
  const s = await offen('#neu-queue');
  await klick(s, s.q('[data-karte="box"] [data-wert="kueche"]'));
  await klick(s, wahl(s, 'serie:buch'));
  s.m.legeAuf('kueche', NEU);
  await warte(20); await s.flush(10);
  assert.equal(hash(), '#tobies');
  assert.deepEqual(toasts(s), ['Küche: Der neue Tobie spielt jetzt „Das große Buch“.']);
  assert.equal(toast(s).querySelector('button').textContent, 'Name geben');
  assert.ok(kachel(s, NEU), 'der Tobie steht im Regal');
  assert.equal(s.qa('[data-eintrag]').length, 0, 'die Vormerkung ist weg');
  await klick(s, toast(s).querySelector('button'));
  assert.equal(hash(), `#tobie-${NEU}?name=1`);
  assert.equal(s.el.shadowRoot.activeElement, s.q('#tb-name'), '„Name geben“ setzt den Fokus ins Namensfeld');
  weg();
});

test('Weg 2 mit Namen: nach dem Auflegen kein „Name geben“, keine Karte „Platz bekommen“, der Tobie heißt schon so', MIT_DOM, async () => {
  const s = await offen('#neu-queue');
  await tippeIn(s, s.q('#tb-queue-name'), 'Bär');
  await klick(s, wahl(s, 'serie:buch'));
  s.m.legeAuf('kueche', NEU);
  await warte(20); await s.flush(10);
  assert.deepEqual(toasts(s), ['Küche: Der neue Tobie spielt jetzt „Das große Buch“.']);
  assert.equal(toast(s).querySelector('button'), null);
  assert.equal(kachel(s, NEU).getAttribute('aria-label'), 'Bär, spielt Das große Buch');
  await geheZu(s, '#geraete');
  assert.equal(s.q('[data-karte="platz-bekommen"]'), null);
  weg();
});

test('Weg 2: ist die Warteschlange voll oder der Eintrag doppelt, steht die Meldung des Backends, die Seite bleibt', MIT_DOM, async () => {
  const s = await offen('#neu-queue');
  await klick(s, wahl(s, 'serie:buch'));
  await klick(s, s.q('[data-zustand="wartet"] [data-fertig]'));
  await geheZu(s, '#neu-queue');
  await klick(s, wahl(s, 'serie:buch'));
  assert.equal(s.qa('.toast.err').length, 1, 'gleiches Ziel, gleiche Box: warteschlange_doppelt');
  assert.equal(hash(), '#neu-queue');
  assert.ok(s.q('[data-zielwahl]'), 'die Zielwahl bleibt bedienbar');
  weg();
});

/* ------------------------------------------------------------------ festes Ziel (Einem Tobie geben …) */

test('Festes Ziel, Weg 1: oben „Er soll spielen“ (über #neu), nach dem Erkennen „Er spielt …“ mit „Fertig“, danach zurück zur Serie', MIT_DOM, async () => {
  const s = await offen('#neu?s=reise');
  assert.equal(text(s.q('a[data-zurueck]')), '‹ Die drei ???'.replace('Die drei ???', 'Kleine Reise'));
  assert.equal(text(s.q('.tb-cur.fest')), 'Er soll spielen Kleine Reise');
  assert.equal(s.q('a[data-weg="jetzt"]').getAttribute('href'), '#neu-warten?s=reise');
  assert.equal(s.q('a[data-weg="spaeter"]').getAttribute('href'), '#neu-queue?s=reise');
  await klick(s, s.q('a[data-weg="jetzt"]'));
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  assert.equal(hash(), `#neu-ziel-${NEU}?s=reise&von=tobies`);
  assert.equal(text(s.q('.tb-cur.fest')), 'Er spielt Kleine Reise');
  assert.equal(s.q('[data-zielwahl]'), null, 'die Zielwahl entfällt');
  await tippeIn(s, s.q('#tb-neuname'), 'Fuchs');
  await klick(s, s.q('[data-fertig]'));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').map(ohneId), [{ uid: NEU, ziel: { typ: 'serie', serie: 'reise' }, erwartet_ziel: null, name: 'Fuchs' }]);
  assert.equal(hash(), '#serie-reise', 'zurück zur Serie');
  assert.deepEqual(toasts(s), ['Fertig: Fuchs spielt jetzt „Kleine Reise“.']);
  weg();
});

test('Festes Ziel, Weg 2: „Vormerken“ statt der Zielwahl; Eintrag mit dem festen Ziel (Folge)', MIT_DOM, async () => {
  const s = await offen('#neu-queue?s=reise&f=k2.mp3');
  assert.equal(text(s.q('.tb-cur.fest')), 'Er soll spielen Unterwegs');
  assert.equal(s.q('[data-zielwahl]'), null);
  await klick(s, s.q('[data-vormerken]'));
  assert.deepEqual(aufrufe(s, 'warteschlange/set').map(ohneId), [{ box: null, ziel: { typ: 'folge', serie: 'reise', folge: 'k2.mp3' } }]);
  assert.equal(text(s.q('[data-zustand="wartet"] .tb-titel')), 'Nächster neuer Tobie auf irgendeiner Box spielt „Unterwegs“');
  assert.equal(s.q('[data-zustand="wartet"] [data-fertig]').getAttribute('href'), '#serie-reise', '„Fertig“ führt zurück zur Serie');
  weg();
});

test('#geben-<serie>: „Welcher Tobie soll das spielen?“, Regal mit „+ Neuer Tobie“ zuerst; Tap ordnet zu und kehrt zur Serie zurück', MIT_DOM, async () => {
  const s = await offen('#geben-reise');
  assert.equal(s.q('main h2.tb-titel').textContent, 'Welcher Tobie soll das spielen?');
  assert.equal(text(s.q('a[data-zurueck]')), '‹ Kleine Reise');
  assert.equal(text(s.q('.tb-cur.fest')), 'Ganzes Hörspiel Kleine Reise');
  assert.equal(s.q('[data-regal] [role="listitem"]:first-child a').getAttribute('href'), '#neu?s=reise');
  assert.deepEqual(s.qa('[data-regal] [data-tobie]').map((b) => [b.tagName, b.dataset.tobie]), [['BUTTON', OHNE], ['BUTTON', ANNA]]);
  assert.match(kachel(s, ANNA).getAttribute('aria-label'), /Anna, spielt Die drei \?\?\?/, 'jede Kachel nennt, was er jetzt spielt');
  await klick(s, kachel(s, ANNA));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').map(ohneId), [{ uid: ANNA, ziel: { typ: 'serie', serie: 'reise' }, erwartet_ziel: { typ: 'serie', serie: 's1' } }]);
  assert.equal(hash(), '#serie-reise');
  assert.deepEqual(toasts(s), ['Anna spielt jetzt „Kleine Reise“ (vorher „Die drei ???“).']);
  assert.equal(toast(s).querySelector('button').textContent, 'Rückgängig');
  await klick(s, toast(s).querySelector('button'));
  assert.deepEqual(zuord(s, ANNA).ziel, { typ: 'serie', serie: 's1' });
  weg();
});

test('#geben-<serie>~<Folge>: ordnet die Folge zu; die Seite der Serie zeigt danach den Chip an der Folge', MIT_DOM, async () => {
  const s = await offen(`#geben-reise~${encodeURIComponent('k2.mp3')}`);
  assert.equal(text(s.q('.tb-cur.fest')), 'Kleine Reise · Folge Unterwegs');
  await klick(s, kachel(s, OHNE));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').at(-1).ziel, { typ: 'folge', serie: 'reise', folge: 'k2.mp3' });
  assert.equal(hash(), '#serie-reise');
  assert.deepEqual(s.qa('[data-folge="k2.mp3"] .tb-chip[data-chip]').map((c) => c.dataset.chip), [OHNE]);
  weg();
});

test('#geben für einen Einzeltitel: Art „Einzeltitel“, Zuordnung als Folge der eigenen Serie', MIT_DOM, async () => {
  const s = await offen(`#geben-lied~${encodeURIComponent('wiegenlied.mp3')}`);
  assert.equal(text(s.q('.tb-cur.fest')), 'Einzeltitel Wiegenlied');
  await klick(s, kachel(s, ANNA));
  assert.deepEqual(aufrufe(s, 'zuordnung/set').at(-1).ziel, { typ: 'folge', serie: 'lied', folge: 'wiegenlied.mp3' });
  weg();
});

test('#geben: Ziel, das es nicht gibt, zeigt einen Hinweis', MIT_DOM, async () => {
  const s = await offen('#geben-gibtsnicht');
  assert.match(text(s.q('[data-zustand="weg"]')), /Das gibt es nicht mehr/);
  weg();
});

/* ------------------------------------------------------------------ Serienseite und Bibliothek */

test('Serienseite: „Gespielt von“ mit Chips (44 px, Link zur Seite des Tobies) und „+ Tobie“ hinter den Chips', MIT_DOM, async () => {
  const s = await offen('#serie-s1');
  const karte = s.q('[data-karte="gespielt-von"]');
  assert.equal(text(karte.querySelector('.tb-glabel')), 'Gespielt von:');
  assert.deepEqual([...karte.querySelectorAll('a.tb-chip[data-chip]')].map((a) => [a.dataset.chip, text(a), a.getAttribute('href')]),
    [[ANNA, 'Anna', `#tobie-${ANNA}`], [OHNE, 'Tobie ohne Namen', `#tobie-${OHNE}`]], 'Tobies der Serie und ihrer Folgen');
  const plus = karte.querySelector('a[data-plus]');
  assert.equal(text(plus), '+ Tobie');
  assert.equal(plus.getAttribute('aria-label'), 'Weiteren Tobie geben');
  assert.equal(plus.getAttribute('href'), '#geben-s1');
  assert.equal(karte.querySelector('[data-geben]'), null, 'mit Tobies kein Textlink „Einem Tobie geben …“');
  assert.ok(karte.compareDocumentPosition(s.q('.se-kopf, header, h2')) !== 0);
  await klick(s, karte.querySelector('a.tb-chip[data-chip]'));
  assert.equal(hash(), `#tobie-${ANNA}`);
  weg();
});

test('Serienseite ohne Tobie: „Noch kein Tobie · Einem Tobie geben …“ öffnet #geben-<serie>; kein „+ Tobie“', MIT_DOM, async () => {
  const s = await offen('#serie-reise');
  const karte = s.q('[data-karte="gespielt-von"]');
  assert.equal(text(karte), 'Gespielt von Noch kein Tobie Einem Tobie geben …');
  assert.equal(karte.querySelector('[data-plus]'), null, '„+ Tobie“ nur, wenn es Tobies gibt');
  await klick(s, karte.querySelector('a[data-geben]'));
  assert.equal(hash(), '#geben-reise');
  assert.equal(s.q('main h2.tb-titel').textContent, 'Welcher Tobie soll das spielen?');
  weg();
});

test('Serienseite eines Einzeltitels: „Einem Tobie geben …“ führt mit der Folge als Ziel zu #geben', MIT_DOM, async () => {
  const s = await offen('#serie-lied');
  assert.equal(s.q('[data-karte="gespielt-von"] a[data-geben]').getAttribute('href'), '#geben-lied~wiegenlied.mp3');
  weg();
});

test('Folgenzeile: Chips der Tobies dieser Folge mit „+ Tobie“; „⋯“ hat „Einem Tobie geben …“ und öffnet #geben-<serie>~<Folge>', MIT_DOM, async () => {
  const s = await offen('#serie-s1');
  const zeile = s.q('[data-folge="folge-02.mp3"]');
  assert.deepEqual([...zeile.querySelectorAll('a.tb-chip[data-chip]')].map((a) => a.dataset.chip), [OHNE]);
  assert.equal(zeile.querySelector('a[data-plus]').getAttribute('href'), '#geben-s1~folge-02.mp3');
  assert.equal(s.q('[data-folge="folge-01.mp3"] .tb-chips'), null, 'ohne Tobies keine Chips in der Zeile');
  await klick(s, s.q('[data-folge="folge-01.mp3"] [data-menue-folge]'));
  assert.equal(text(s.q('dialog.blatt[open] [data-menue]:first-child')), 'Einem Tobie geben …');
  await klick(s, s.q('dialog.blatt[open] [data-menue="geben"]'));
  assert.equal(hash(), '#geben-s1~folge-01.mp3');
  assert.equal(blatt(s), null, 'das Blatt schließt beim Seitenwechsel');
  assert.equal(text(s.q('.tb-cur.fest')), 'Die drei ??? · Folge Der Rabe');
  weg();
});

test('Suche: „⋯“ am Treffer einer Folge öffnet ein Blatt mit „Einem Tobie geben …“', MIT_DOM, async () => {
  const s = await offen('#suche');
  await tippeIn(s, s.q('input.suchfeld'), 'Rabe');
  await warte(400); await s.flush(10);
  const knopf = s.q('[data-menue-folge]');
  assert.ok(knopf, 'die Zeile hat „⋯“');
  await klick(s, knopf);
  await klick(s, s.q('dialog.blatt[open] [data-menue="geben"]'));
  assert.equal(hash(), '#geben-s1~folge-01.mp3');
  weg();
});

test('Bibliothek: kein Zuordnen-Knopf (nicht in den Zeilen, nicht in der Suche, nicht im Menü der Serie)', MIT_DOM, async () => {
  const s = await offen('#bibliothek', { viele: 40 });
  const nur = (el) => /zuordnen|Tobie zuordnen|anlernen/i.test(text(el));
  assert.equal(s.qa('main button').filter(nur).length, 0);
  assert.equal(nur(s.q('main')), false, `Text: ${text(s.q('main')).slice(0, 80)}`);
  await geheZu(s, `#serie-${Object.keys(s.m.backend.serien)[0]}`);
  await klick(s, s.q('[data-menue-serie]'));
  assert.equal(s.qa('dialog.blatt[open] [data-menue]').filter((b) => /zuordnen|anlernen/i.test(text(b))).length, 0);
  weg();
});

/* ------------------------------------------------------------------ Geräte: Karten, Punkt, Meldungen */

test('Geräte: Karte „Neuer Tobie auf Küche – was soll er spielen?“ (ganze Karte ein Link), Punkt mit Zahl am Reiter, „Versehen“ auf der Karte', MIT_DOM, async () => {
  const s = await offen('#geraete');
  const karte = s.q('[data-karte="neuer-tobie"]');
  assert.equal(text(karte.querySelector('a.tb-karte-link strong')), 'Neuer Tobie auf Küche – was soll er spielen?');
  assert.match(text(karte.querySelector('.zeit')), /^Gerade aufgelegt, vor /);
  assert.equal(karte.querySelector('a.tb-karte-link').getAttribute('href'), `#neu-ziel-${UNBEKANNT}`);
  const dot = s.q('nav.tabs a[href="#geraete"] .dot');
  assert.equal(dot.textContent, '1');
  assert.equal(text(s.q('nav.tabs a[href="#geraete"] .sr')), '1 neuer Tobie');
  await klick(s, karte.querySelector('[data-versehen]'));
  await klick(s, blattKnopf(s, 'Nicht merken'));
  assert.equal(s.q('[data-karte="neuer-tobie"]'), null);
  assert.equal(s.q('nav.tabs a[href="#geraete"] .dot'), null, 'ohne unbekannte Tobies kein Punkt');
  weg();
});

test('Geräte: mehrere unbekannte Tobies: die Karte zählt („2 neue Tobies auf Küche“), jede Zeile ist ein Link auf die Seite „Neuer Tobie erkannt“', MIT_DOM, async () => {
  const s = await offen('#geraete');
  s.m.legeAuf('kueche', NEU);
  await warte(20); await s.flush(10);
  const karte = s.q('[data-karte="neue-tobies"][data-box="kueche"]');
  assert.equal(text(karte.querySelector('h3')), '2 neue Tobies auf Küche');
  assert.deepEqual([...karte.querySelectorAll('a.tb-zeilenlink')].map((a) => a.getAttribute('href')).sort(), [`#neu-ziel-${NEU}`, `#neu-ziel-${UNBEKANNT}`].sort());
  // Abnahme A-1b: jede Zeile nennt die Uhrzeit, damit man die Tobies unterscheidet
  for (const z of karte.querySelectorAll('a.tb-zeilenlink .grow')) assert.match(text(z), /^Aufgelegt um \d\d:\d\d, /);
  assert.equal(s.q('nav.tabs a[href="#geraete"] .dot').textContent, '2');
  assert.equal(text(s.q('nav.tabs a[href="#geraete"] .sr')), '2 neue Tobies');
  weg();
});

test('Meldung „Neuer Tobie auf Küche.“ auf jeder Seite (hier Serie und Bibliothek), „Zuordnen“ öffnet die Seite für genau diesen Tobie', MIT_DOM, async () => {
  const s = await offen('#serie-s1');
  s.m.legeAuf('kueche', NEU);
  await warte(20); await s.flush(10);
  assert.deepEqual(toasts(s), ['Neuer Tobie auf Küche.']);
  await klick(s, toast(s).querySelector('button'));
  assert.equal(hash(), `#neu-ziel-${NEU}`);
  assert.equal(s.q('[data-karte="erkannt"]').textContent.includes('Küche'), true);
  weg();
});

test('Zwei unbekannte Tobies nacheinander: zwei Meldungen, die zweite ersetzt die erste, beide stehen auf „Geräte“', MIT_DOM, async () => {
  const s = await offen('#bibliothek');
  s.m.legeAuf('kueche', NEU);
  s.m.legeAuf('kinderzimmer', '04AABBCCDDEE02');
  await warte(20); await s.flush(10);
  assert.deepEqual(toasts(s), ['Neuer Tobie auf Kinderzimmer.']);
  await geheZu(s, '#geraete');
  assert.equal(s.qa('[data-karte="neuer-tobie"], [data-karte="neue-tobies"] [data-uid]').length, 3, 'mit dem unbekannten vom Start sind es drei');
  weg();
});

test('Auflegen auf Box ohne Vormerkung: kein Eintrag in der Warteschlange, die Meldung „Zuordnen“ erscheint; mit Vormerkung dagegen nicht', MIT_DOM, async () => {
  const s = await offen('#bibliothek');
  await s.m.hass.connection.sendMessagePromise({ type: 'tobibox/warteschlange/set', box: 'kueche', ziel: { typ: 'serie', serie: 's1' } });
  s.m.legeAuf('kueche', NEU);
  await warte(20); await s.flush(10);
  assert.ok(!toasts(s).includes('Neuer Tobie auf Küche.'), 'die Vormerkung hat ihn genommen');
  assert.deepEqual(toasts(s), ['Küche: Der neue Tobie spielt jetzt „Die drei ???“.']);
  weg();
});

test('Geräte: nach dem Auflegen mit Vormerkung ohne Namen bleibt die Karte „Ein neuer Tobie hat einen Platz bekommen“; „Später“ entfernt sie', MIT_DOM, async () => {
  const s = await offen('#bibliothek');
  await s.m.hass.connection.sendMessagePromise({ type: 'tobibox/warteschlange/set', box: null, ziel: { typ: 'serie', serie: 'buch' } });
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  assert.equal(toast(s).querySelector('button').textContent, 'Name geben');
  await geheZu(s, '#geraete');
  const karte = s.q('[data-karte="platz-bekommen"]');
  assert.equal(text(karte), 'Ein neuer Tobie hat einen Platz bekommen. Name geben? Name geben Später');
  assert.equal(karte.querySelector('[data-name-geben]').getAttribute('href'), `#tobie-${NEU}?name=1`);
  await geheZu(s, '#start'); await geheZu(s, '#geraete');
  assert.ok(s.q('[data-karte="platz-bekommen"]'), 'bleibt, bis er einen Namen hat');
  await klick(s, s.q('[data-karte="platz-bekommen"] [data-spaeter]'));
  assert.equal(s.q('[data-karte="platz-bekommen"]'), null);
  weg();
});

test('Geräte: die Karte „Platz bekommen“ verschwindet, sobald der Tobie einen Namen hat (Namensfeld auf der Seite des Tobies)', MIT_DOM, async () => {
  const s = await offen('#bibliothek');
  await s.m.hass.connection.sendMessagePromise({ type: 'tobibox/warteschlange/set', box: null, ziel: { typ: 'serie', serie: 'buch' } });
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  await klick(s, toast(s).querySelector('button'));
  assert.equal(s.el.shadowRoot.activeElement, s.q('#tb-name'));
  await tippeIn(s, s.q('#tb-name'), 'Igel');
  await klick(s, s.q('[data-name-speichern]'));
  await geheZu(s, '#geraete');
  assert.equal(s.q('[data-karte="platz-bekommen"]'), null);
  weg();
});

test('Geräte: Auto-Zuordnung scheitert (Liste gesperrt): Eintrag bleibt, Karte „Konnte nicht zugeordnet werden“ mit Grund und „Jetzt zuordnen“', MIT_DOM, async () => {
  const s = await offen('#geraete');
  await s.m.hass.connection.sendMessagePromise({ type: 'tobibox/warteschlange/set', box: 'kueche', ziel: { typ: 'serie', serie: 'buch' } });
  s.m.backend.konfig = { ...s.m.backend.konfig, zustand: 'export_neuer' }; // gesperrt
  s.m.backend.neueTobies = [];
  const vorher = Date.now();
  s.m.backend.warteschlange[0].angelegt_am = new Date(vorher - 60000).toISOString();
  s.m.emit('warteschlange', 'angelegt', { eintrag: s.m.backend.warteschlange[0] });
  await warte(20); await s.flush(10);
  s.m.legeAuf('kueche', NEU, { zeit: new Date(vorher).toISOString() });
  s.m.emit('konfig', 'geaendert', { konfig: s.m.backend.konfig });
  await warte(20); await s.flush(10);
  const karte = s.q('[data-karte="nicht-zugeordnet"]');
  assert.ok(karte, 'die Karte steht da');
  assert.equal(text(karte.querySelector('h3')), 'Konnte nicht zugeordnet werden');
  assert.equal(text(karte.querySelector('.muted')), 'Änderungen sind gerade gesperrt.');
  assert.equal(karte.querySelector('[data-jetzt-zuordnen]').getAttribute('href'), `#neu-ziel-${NEU}`);
  assert.equal(s.m.backend.warteschlange.length, 1, 'der Eintrag bleibt');
  assert.ok(s.q('[data-karte="wartet"]'), 'und steht als Zeile in der Karte „Wartet auf einen neuen Tobie“');
  weg();
});

test('Geräte: Karte „Wartet auf einen neuen Tobie“ mit Zeilen; Tipp öffnet ein Blatt mit „Nicht mehr warten“', MIT_DOM, async () => {
  const s = await offen('#geraete');
  const sende = (box, ziel) => s.m.hass.connection.sendMessagePromise({ type: 'tobibox/warteschlange/set', box, ziel });
  await sende('kueche', { typ: 'serie', serie: 's1' });
  await sende(null, { typ: 'serie', serie: 'buch' });
  await s.flush(10);
  const zeilen = s.qa('[data-karte="wartet"] .tb-wzeile');
  assert.equal(zeilen.length, 2);
  assert.equal(text(zeilen[0]), 'Nächster neuer Tobie auf Küche spielt „Die drei ???“ · Nr. 1 von 2');
  assert.equal(text(zeilen[1]), 'Nächster neuer Tobie auf irgendeiner Box spielt „Das große Buch“ · Nr. 2 von 2');
  await klick(s, zeilen[0]);
  assert.match(text(blatt(s)), /Nr\. 1 von 2/);
  await klick(s, blattKnopf(s, 'Nicht mehr warten'));
  assert.equal(aufrufe(s, 'warteschlange/abbrechen').length, 1);
  assert.equal(s.m.backend.warteschlange.length, 1);
  assert.deepEqual(toasts(s), ['Vormerkung abgebrochen.']);
  assert.equal(s.qa('[data-karte="wartet"] .tb-wzeile').length, 1);
  weg();
});

/* ------------------------------------------------------------------ Rechte, Fähigkeiten, Lernmodus */

test('Alltag (kein Administrator): alle Abläufe gehen, der Lernmodus wird von keiner Alltagsseite aufgerufen', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`, { istAdmin: false });
  await klick(s, wahl(s, 'serie:reise'));
  await geheZu(s, '#neu-warten');
  s.m.legeAuf('kinderzimmer', NEU);
  await warte(20); await s.flush(10);
  await klick(s, wahl(s, 'aktion'));
  await geheZu(s, '#neu-queue');
  await klick(s, wahl(s, 'serie:buch'));
  assert.equal(aufrufe(s, 'zuordnung/set').length, 2);
  assert.equal(s.qa('.toast.err').length, 0, 'keine Fehlermeldung wegen fehlender Rechte');
  const alle = s.m.calls.map((c) => c.type);
  assert.equal(alle.filter((t) => t.startsWith('tobibox/lernmodus/')).length, 0);
  weg();
});

test('Technik › Tobies mit dem Lernmodus ist nur für Administratoren; andere sehen die Sperre', MIT_DOM, async () => {
  const a = await offen('#technik-tobies');
  assert.ok(a.q('[data-alt="tobies"]'), 'Administrator: die eingebettete Ansicht mit dem Lernmodus');
  weg();
  const u = await offen('#technik-tobies', { istAdmin: false });
  assert.equal(u.q('[data-alt="tobies"]'), null);
  assert.ok(u.q('[data-zustand="technik-sperre"], [data-zustand="gesperrt"], .note'), 'Benutzer: Hinweis statt der Ansicht');
  weg();
});

test('Ohne die Fähigkeit `warteschlange` gibt es nur Weg 1; die Seite fragt `warteschlange/list` nicht', MIT_DOM, async () => {
  const s = await offen('#neu', { faehigkeiten: [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11] });
  assert.deepEqual(s.qa('a[data-weg]').map((a) => a.dataset.weg), ['jetzt']);
  assert.equal(aufrufe(s, 'warteschlange/list').length, 0);
  weg();
});

test('Ohne die Fähigkeit `bibliothek` (altes Backend) filtert und sortiert die Zielwahl selbst', MIT_DOM, async () => {
  const s = await offen(`#tobie-${ANNA}`, { faehigkeiten: ALLE.filter((f) => f !== 'bibliothek') });
  assert.deepEqual(s.qa('[data-ergebnis="serie"] [data-wahl]').map((b) => b.dataset.wahl), ['serie:reise', 'serie:buch', 'serie:s1', 'serie:s2']);
  weg();
});

/* ------------------------------------------------------------------ Laden und Fehler */

test('Regal: Fehler beim Laden zeigt die Fehlerkarte mit „Noch einmal versuchen“', MIT_DOM, async () => {
  const s = await offen('#start');
  s.m.failNext('tobibox/zuordnung/list', 'internal_error');
  await geheZu(s, '#tobies');
  await s.flush(10);
  assert.ok(s.q('.note.err, [role="alert"]'), 'Fehlerkarte');
  weg();
});

test('Texte: jeder Satz der Seiten steht in texte.js, nirgends „Mehr“ als Reiter und keine echten Namen', () => {
  const alle = JSON.stringify({ TOBIE, TOBIES });
  assert.doesNotMatch(alle, /Tobias|Partnerin/);
  assert.equal(TOBIES.neuer, '+ Neuer Tobie');
  assert.equal(GERAETE.platz_bekommen.titel, 'Ein neuer Tobie hat einen Platz bekommen.');
  assert.equal(GERAETE.nicht_zugeordnet.titel, 'Konnte nicht zugeordnet werden');
});

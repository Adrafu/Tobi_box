/* Tests der Seite zur Online-Suche (Paket OS4, Design docs/designs/online-suche.md Abschnitt 10, 5, 6.4). Aufruf: node --test homeassistant/tests/frontend
 *
 * Mock: Befehle 57 bis 64, HTTP-Vorschau und Ereignis `online` aus mock-hass.mjs (Vertrag W 3.15, 4.11, 14.2).
 * Geprüft: Zeile „Aus der Online-Suche übernommen“ für alle, Zurücknehmen und Blatt „Online suchen“ mit Übersicht nur für Administratoren, Vorschläge (Claude, Zusammenführen),
 * „ab 3“ und Beschreibung auf Tipp (auch für Benutzer), Technik › Online-Suche (Lauf, Quellen, Läufe, „Alle zurücknehmen“), Filter `online_vorschlag`, Fehlercodes mit Klartext,
 * Lauf `abgebrochen` ohne `grund`, und: ohne die Fähigkeit `online_suche` ist nichts davon zu sehen und es geht kein Befehl 57 bis 63 hinaus.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, tippe, domBereit, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN, FAEHIGKEITEN_V11, FAEHIGKEITEN_OS, SCHEMA_OS, createMockHass, folgeMitOnline } from './mock-hass.mjs';

if (MIT_DOM.skip === false) await domBereit(); // die alte Komponente (Technik) definiert ihr Element nur, wenn das DOM vor dem Laden da ist
const O = await import('../../custom_components/tobibox/frontend/seiten/online.js');
const TO = await import('../../custom_components/tobibox/frontend/seiten/technik_online.js');
const { ONLINE, FEHLER, SERIE, BIB, TECHNIK, fuellen } = await import('../../custom_components/tobibox/frontend/texte.js');

const ALLE = [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11, ...FAEHIGKEITEN_OS, 'konfig_lesen', 'hoerkopie', 'reinhoeren', 'einsortier_wunsch'];
const OHNE = ALLE.filter((f) => !FAEHIGKEITEN_OS.includes(f));
const text = (el) => (el?.textContent || '').replace(/\s+/g, ' ').trim();
const blatt = (s) => s.q('dialog.blatt[open]');
const blattKnopf = (s, t) => s.qa('dialog.blatt[open] .knoepfe button').find((b) => text(b) === t);
const toasts = (s) => s.qa('.toast .tmsg').map(text);
const klick = async (s, el, n = 12) => { assert.ok(el, 'Element zum Klicken fehlt'); el.click(); await warte(15); await s.flush(n); };
const aufrufe = (s, typ) => s.m.aufrufe(`tobibox/${typ}`);
const viele = (s, was) => s.m.calls.filter((c) => c.type.startsWith('tobibox/online/') && !c.abo).map((c) => c.type).filter((t) => !was || was.includes(t));
const folge = (name, anzeige, extra = {}) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * 1048576, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });
const LANG = 'Es war einmal ein Drache. Er wohnte in einer Höhle am Berg. '.repeat(8).trim(); // über 300 Zeichen: gekürzt

async function oeffne(id = 's1', { vor, hash = null, ...opts } = {}) {
  const s = await seite({ hash: '', faehigkeiten: ALLE, ...opts });
  vor?.(s.m);
  await geheZu(s, hash ?? `#serie-${id}`);
  await s.flush(10);
  return s;
}
const menue = async (s, id) => { await klick(s, s.q('[data-menue-serie]')); return id ? s.q(`dialog.blatt[open] [data-menue="${id}"]`) : null; };
const trefferSuche = async (s, folge = null) => { // „Online suchen“ im Menü des Eintrags oder der Folge
  if (folge) await klick(s, s.q(`[data-folge="${folge}"] [data-menue-folge]`)); else await klick(s, s.q('[data-menue-serie]'));
  await klick(s, s.q('dialog.blatt[open] [data-menue="online"]'), 14);
};

/* ------------------------------------------------------------------ reine Funktionen */

test('feldListe: Feldnamen in Worten, ohne Doppelte und ohne @Folge, unbekannte fallen weg', () => {
  assert.equal(O.feldListe(['cover', 'art']), 'Cover und Art');
  assert.equal(O.feldListe(['cover', 'art', 'nummer@f1', 'nummer@f2']), 'Cover, Art und Nummer');
  assert.equal(O.feldListe(['cover']), 'Cover');
  assert.equal(O.feldListe(['gibt_es_nicht', 'serie_name']), 'Name');
  assert.equal(O.feldListe([]), '');
  assert.equal(O.feldListe(null), '');
});

test('teileKey trennt am ersten @; vorauswahl setzt alles an außer „von Hand“ (O14); sortiereFelder: Eintrag zuerst, dann je Folge', () => {
  assert.deepEqual(O.teileKey('nummer@a@b.mp3'), ['nummer', 'a@b.mp3']);
  assert.deepEqual(O.teileKey('art'), ['art', null]);
  const v = O.vorauswahl({ art: { hand: false }, cover: { hand: true }, 'nummer@f1': { hand: false } });
  assert.deepEqual([...v].sort(), ['art', 'nummer@f1']);
  assert.deepEqual(O.sortiereFelder(['alter_ab@f2', 'cover', 'nummer@f1', 'folge_titel@f1', 'serie_name', 'art', 'beschreibung@f1'], [{ name: 'f1' }, { name: 'f2' }]),
    ['serie_name', 'art', 'cover', 'folge_titel@f1', 'nummer@f1', 'beschreibung@f1', 'alter_ab@f2']);
});

test('vorschlagText: Felder einer Quelle, Namensvorschlag von Claude, Zusammenführen mit und ohne Namen des Ziels', () => {
  assert.equal(O.vorschlagText({ art: 'felder', quelle: 'itunes', felder: ['cover', 'art'] }), 'Vorschlag aus der Online-Suche: Cover und Art von Apple');
  assert.equal(O.vorschlagText({ art: 'felder', quelle: 'tonies', felder: ['cover'] }), 'Vorschlag aus der Online-Suche: Cover von Tonies');
  assert.equal(O.vorschlagText({ art: 'felder', quelle: 'claude', felder: ['serie_name'], name: 'Janosch' }), 'Vorschlag von Claude: Name „Janosch“');
  assert.equal(O.vorschlagText({ art: 'zusammenfuehren', quelle: 'claude', ziel_serie_id: 'z' }, { z: { name: 'Micky Maus' } }), 'Vorschlag von Claude: mit „Micky Maus“ zusammenführen');
  assert.equal(O.vorschlagText({ art: 'zusammenfuehren', quelle: 'claude', ziel_serie_id: 'z' }), ONLINE.vorschlag.zusammen_ohne_name);
  assert.equal(O.istNamensvorschlag({ art: 'felder', quelle: 'claude', felder: ['serie_name'] }), true);
  assert.equal(O.istNamensvorschlag({ art: 'felder', quelle: 'itunes', felder: ['serie_name'] }), false);
});

test('uhrzeit und kuerzen', () => {
  assert.equal(O.uhrzeit('2026-11-19T13:20:00Z', 'Europe/Berlin'), '14:20');
  assert.equal(O.uhrzeit('kaputt'), '');
  assert.equal(O.kuerzen('kurz'), 'kurz');
  const k = O.kuerzen(LANG, 120);
  assert.ok(k.length <= 125 && k.endsWith(' …'));
});

test('Technik-Texte: Quelle, Claude, Lauf und Ende (auch abgebrochen ohne Grund)', () => {
  assert.equal(TO.quellenZustand({ erreichbar: true }), 'erreichbar');
  assert.equal(TO.quellenZustand({ erreichbar: false }), 'antwortet gerade nicht');
  assert.equal(TO.quellenZustand({ erreichbar: false, pause_bis: '2026-11-19T13:20:00Z' }, 'Europe/Berlin'), 'Pause bis 14:20');
  assert.equal(TO.claudeZustand({ eingerichtet: false, erreichbar: false }), ONLINE.technik.claude_aus);
  assert.equal(TO.claudeZustand({ eingerichtet: true, erreichbar: true }), 'bereit');
  assert.equal(TO.claudeZustand({ eingerichtet: true, erreichbar: false }), ONLINE.technik.claude_nein);
  assert.equal(TO.laufEndeText({ zustand: 'fertig', zahlen: { geaendert: 120, vorschlaege: 38, keiner: 12 } }), 'Fertig: 120 Einträge geändert, 38 Vorschläge, 12 ohne Treffer.');
  assert.equal(TO.laufEndeText({ zustand: 'angehalten', grund: 'angehalten' }), 'Angehalten.');
  assert.equal(TO.laufEndeText({ zustand: 'abgebrochen', grund: 'neustart' }), 'Abgebrochen (Neustart). Du kannst neu starten.');
  assert.equal(TO.laufEndeText({ zustand: 'abgebrochen', grund: 'quelle' }), 'Abgebrochen: Quelle nicht erreichbar.');
  assert.equal(TO.laufEndeText({ zustand: 'abgebrochen' }), 'Abgebrochen. Du kannst neu starten.', 'ohne Grund (Fehler außerhalb einer Serie, Vertrag 19.11.)');
  assert.equal(TO.laufEndeText({ zustand: 'abgebrochen', grund: 'unbekannt' }), 'Abgebrochen. Du kannst neu starten.');
  assert.equal(TO.laufText(null), 'Kein Lauf.');
  assert.equal(TO.laufText({ zustand: 'laeuft', erledigt: 5, gesamt: 340 }), 'Läuft: 5 von 340.');
  assert.equal(TO.laufText({ zustand: 'wird_angehalten' }), 'Hält nach dieser Serie an.');
  assert.equal(TO.laufText({ zustand: 'pausiert', pause_bis: '2026-11-19T13:20:00Z' }, { itunes: { erreichbar: false, pause_bis: '2026-11-19T13:20:00Z' } }, 'Europe/Berlin'), 'Pause bis 14:20, weil Apple bremst.');
  assert.equal(TO.laufText({ zustand: 'pausiert', pause_bis: '2026-11-19T13:20:00Z' }, {}, 'Europe/Berlin'), 'Pause bis 14:20.');
});

test('Alle sechs neuen Fehlercodes haben einen Klartext, der Text der Online-Suche steht wörtlich da', () => {
  for (const c of ['treffer_abgelaufen', 'vorschlag_nicht_gefunden', 'aenderung_nicht_gefunden', 'lauf_nicht_gefunden', 'lauf_laeuft_schon', 'online_nicht_erreichbar']) assert.ok(typeof FEHLER[c] === 'string' && FEHLER[c].length > 10, c);
  assert.equal(FEHLER.treffer_abgelaufen, 'Die Suche ist zu alt. Such bitte noch einmal.');
  assert.equal(FEHLER.online_nicht_erreichbar, 'Online-Suche gerade nicht erreichbar, später noch einmal.');
  assert.equal(ONLINE.suche.nichts, 'Nichts gefunden. Versuch einen anderen Namen.');
  assert.equal(ONLINE.suche.laeuft, 'Suche bei Apple und Tonies …');
  assert.equal(ONLINE.uebersicht.alles_gleich, 'Hier ist schon alles so.');
});

test('Texte der Online-Suche: nicht leer, mit den Vorgabewerten ganz füllbar, keine Netz-Adressen, keine Modellnamen (außer „Claude“), kein „Tonie“ für Figuren', () => {
  const alle = (o, pfad = 'ONLINE') => (typeof o === 'string' ? [[pfad, o]] : Object.entries(o).flatMap(([k, v]) => alle(v, `${pfad}.${k}`)));
  const liste = alle(ONLINE);
  assert.ok(liste.length > 100);
  for (const [pfad, t] of liste) {
    assert.ok(t.trim().length > 0, `${pfad} ist leer`);
    assert.doesNotMatch(fuellen(t), /\{[a-z_]+\}/, `${pfad} hat einen offenen Platzhalter`);
    assert.doesNotMatch(t, /https?:\/\//, pfad);
    assert.doesNotMatch(t, /\b(sonnet|haiku|fable)\b/i, pfad);
    assert.doesNotMatch(t, /\b(UID|Revision)\b/, pfad);
  }
});

/* ------------------------------------------------------------------ Mock: vertragstreu */

test('Mock: Nr. 57 bis 63 und 65 nur für Administratoren, Nr. 64 für alle; ohne die Fähigkeit unknown_command; Vorschau nur für Administratoren', async () => {
  const user = createMockHass({ faehigkeiten: ALLE, istAdmin: false });
  for (const t of Object.keys(SCHEMA_OS).filter((x) => x !== 'tobibox/online/beschreibung')) {
    const msg = { type: t, ...(t.endsWith('suchen') ? { serie_id: 's1' } : t.endsWith('uebernehmen') ? { serie_id: 's1', felder: ['art'] } : t.endsWith('verwerfen') ? { serie_id: 's1', vorschlag_id: 'x' } : t.endsWith('lauf') ? { aktion: 'start' } : t.endsWith('lauf_aenderungen') ? { lauf_id: 'l1' } : {}) };
    await assert.rejects(user.hass.connection.sendMessagePromise(msg), (e) => e.code === 'unauthorized', t);
  }
  const r = await user.hass.connection.sendMessagePromise({ type: 'tobibox/online/beschreibung', serie_id: 's1', folge: 'folge-01.mp3' });
  assert.deepEqual(r, { beschreibung: null, quelle: null });
  assert.equal((await user.hass.fetchWithAuth('/api/tobibox/online/vorschau/0123456789abcdef')).status, 403);
  const ohne = createMockHass({ faehigkeiten: OHNE });
  await assert.rejects(ohne.hass.connection.sendMessagePromise({ type: 'tobibox/online/status' }), (e) => e.code === 'unknown_command');
  const admin = createMockHass({ faehigkeiten: ALLE });
  assert.equal((await admin.hass.fetchWithAuth('/api/tobibox/online/vorschau/zzz')).status, 404, 'nur 16 Zeichen [0-9a-f]');
  assert.equal((await admin.hass.fetchWithAuth('/api/tobibox/online/vorschau/0123456789abcdef')).status, 410, 'unbekannter Treffer: abgelaufen');
  const t = await admin.hass.connection.sendMessagePromise({ type: 'tobibox/online/suchen', serie_id: 's1' });
  assert.match(t.treffer[0].treffer_id, /^[0-9a-f]{16}$/);
  assert.equal((await admin.hass.fetchWithAuth(`/api/tobibox/online/vorschau/${t.treffer[0].treffer_id}`)).status, 200);
  assert.equal((await admin.hass.fetchWithAuth(`/api/tobibox/online/vorschau/${t.treffer[2].treffer_id}`)).status, 404, 'Treffer ohne Bild');
  await assert.rejects(admin.hass.connection.sendMessagePromise({ type: 'tobibox/online/suchen', serie_id: 's3' }), (e) => e.code === 'invalid_format', 'Überraschungs-Serie');
});

test('Mock: Übernehmen schreibt die gewählten Felder, verlangt stand bei serie_name, nimmt nur Angebotenes und lässt sich zurücknehmen', async () => {
  const m = createMockHass({ faehigkeiten: ALLE });
  const api = (msg) => m.hass.connection.sendMessagePromise(msg);
  const t = await api({ type: 'tobibox/online/suchen', serie_id: 's1', folge: 'folge-01.mp3' });
  const id = t.treffer[0].treffer_id;
  const ue = await api({ type: 'tobibox/online/treffer', treffer_id: id });
  assert.deepEqual(Object.keys(ue.felder).sort(), ['alter_ab@folge-01.mp3', 'art', 'beschreibung@folge-01.mp3', 'cover', 'folge_titel@folge-01.mp3', 'nummer@folge-01.mp3'].sort());
  await assert.rejects(api({ type: 'tobibox/online/uebernehmen', serie_id: 's1', treffer_id: id, felder: ['serie_name'], stand: 'x' }), (e) => e.code === 'invalid_format', 'serie_name wird nicht angeboten');
  await assert.rejects(api({ type: 'tobibox/online/uebernehmen', serie_id: 's1', treffer_id: id, felder: ['art'], stand: 'falsch' }), (e) => e.code === 'stand_veraltet');
  const stand = (await api({ type: 'tobibox/serie/get', serie_id: 's1' })).stand;
  const r = await api({ type: 'tobibox/online/uebernehmen', serie_id: 's1', treffer_id: id, felder: ['art', 'cover', 'alter_ab@folge-01.mp3'], stand });
  assert.match(r.aenderung_id, /^[0-9a-f]{12}$/);
  const g = await api({ type: 'tobibox/serie/get', serie_id: 's1' });
  assert.equal(g.art_quelle, 'online');
  assert.equal(g.cover_quelle, 'online');
  assert.deepEqual(g.online.felder, ['art', 'cover', 'alter_ab']);
  assert.equal(g.folgen[0].alter_ab, 5);
  const z = await api({ type: 'tobibox/online/zuruecknehmen', serie_id: 's1', aenderung_id: r.aenderung_id });
  assert.equal(z.zurueckgenommen, 3);
  assert.equal(z.uebersprungen_anzahl, 0);
  const g2 = await api({ type: 'tobibox/serie/get', serie_id: 's1' });
  assert.equal(g2.online, null);
  assert.equal(g2.cover_quelle, null);
  assert.equal((await api({ type: 'tobibox/online/zuruecknehmen', serie_id: 's1' })).zurueckgenommen, 0, 'zweites Mal: 0 (Endzustand)');
  await assert.rejects(api({ type: 'tobibox/online/zuruecknehmen', serie_id: 's1', aenderung_id: 'gibtsnicht' }), (e) => e.code === 'aenderung_nicht_gefunden');
  await assert.rejects(api({ type: 'tobibox/online/zuruecknehmen', lauf_id: 'gibtsnicht' }), (e) => e.code === 'lauf_nicht_gefunden');
  await assert.rejects(api({ type: 'tobibox/online/zuruecknehmen', serie_id: 's1', lauf_id: 'x' }), (e) => e.code === 'invalid_format', 'Mischung der Formen');
});

test('Mock: Folgenfelder (gekürzt am Satzende, höchstens 300 Zeichen) und das Thema `online` nur für Administratoren, auch bei ausdrücklicher Nennung', async () => {
  const f = folgeMitOnline({ name: 'a', anzeige: 'A', beschreibung_voll: LANG, alter_ab: 4 });
  assert.ok(f.beschreibung.length <= 300 && f.beschreibung.endsWith('.'));
  assert.equal(f.beschreibung_gekuerzt, true);
  assert.equal(f.beschreibung_quelle, 'tonies_shop');
  assert.equal(f.beschreibung_voll, undefined);
  for (const [istAdmin, erwartet] of [[true, true], [false, false]]) {
    const m = createMockHass({ faehigkeiten: ALLE, istAdmin });
    const aus = [];
    await m.hass.connection.subscribeMessage((ev) => aus.push(ev), { type: 'tobibox/subscribe', themen: ['online', 'konfig'] });
    await warte(5);
    assert.equal(aus.some((e) => e.thema === 'online' && e.art === 'snapshot'), erwartet);
    m.emit('online', 'quelle', { quelle: 'itunes', erreichbar: false });
    assert.equal(aus.some((e) => e.thema === 'online' && e.art === 'quelle'), erwartet);
    assert.ok(aus.some((e) => e.thema === 'konfig'), 'die anderen Themen bleiben');
  }
});

/* ------------------------------------------------------------------ App: Abo */

test('Abo: `online` nur für Administratoren mit Fähigkeit; Nicht-Administratoren und alte Backends abonnieren es nicht', MIT_DOM, async () => {
  const themen = (s) => s.m.calls.find((c) => c.abo && c.type === 'tobibox/subscribe').msg.themen;
  const admin = await oeffne('s1');
  assert.ok(themen(admin).includes('online'));
  weg();
  const user = await oeffne('s1', { istAdmin: false });
  assert.ok(!themen(user).includes('online'), 'Nicht-Administrator');
  weg();
  const alt = await oeffne('s1', { faehigkeiten: OHNE });
  assert.ok(!themen(alt).includes('online'), 'ohne Fähigkeit');
  weg();
});

/* ------------------------------------------------------------------ Serienseite: für alle */

const MIT_ONLINE = (m) => {
  const s = m.backend.serien.s1;
  s.online = { zeit: '2026-11-18T10:00:00Z', felder: ['cover', 'art'] };
  s.folgen[0].alter_ab = 3;
  s.folgen[0].beschreibung = 'Ein kurzer Text.';
  s.folgen[0].beschreibung_quelle = 'tonies_shop';
  s.folgen[1].beschreibung_voll = LANG;
  s.folgen[1].beschreibung_quelle = 'itunes';
  s.folgen[1].alter_ab = 6;
};

test('Serienseite für Benutzer: Zeile „Aus der Online-Suche übernommen: Cover und Art.“ mit „Frag einen Administrator …“, ohne „Zurücknehmen“, ohne Menüpunkt, ohne Vorschläge', MIT_DOM, async () => {
  const s = await oeffne('s1', { istAdmin: false, vor: (m) => { MIT_ONLINE(m); m.backend.online.vorschlaege.s1 = [{ id: 'v1', art: 'felder', quelle: 'itunes', felder: ['cover'], zeit: '2026-11-18T10:00:00Z' }]; } });
  assert.equal(text(s.q('[data-online-text]')), 'Aus der Online-Suche übernommen: Cover und Art.');
  assert.equal(text(s.q('[data-online-frag]')), 'Frag einen Administrator, wenn etwas nicht stimmt.');
  assert.equal(s.q('[data-online-zurueck]'), null);
  assert.equal(s.q('[data-vorschlaege]'), null, 'Vorschläge sehen nur Administratoren');
  await klick(s, s.q('[data-menue-serie]'));
  assert.equal(s.q('dialog.blatt[open] [data-menue="online"]'), null);
  weg();
  const s2 = await oeffne('s1', { istAdmin: false, vor: MIT_ONLINE });
  await klick(s2, s2.q('[data-folge="folge-01.mp3"] [data-menue-folge]'));
  assert.equal(s2.q('dialog.blatt[open] [data-menue="online"]'), null);
  assert.deepEqual(viele(s2), [], 'kein Befehl 57 bis 63');
  weg();
});

test('Folgenzeile (alle Benutzer): „ab 3“ in der Nebenzeile; die Beschreibung erst auf Tipp, kurzer Text ohne Befehl 64', MIT_DOM, async () => {
  const s = await oeffne('s1', { istAdmin: false, vor: MIT_ONLINE });
  const z = s.q('[data-folge="folge-01.mp3"]');
  assert.equal(text(z.querySelector('[data-alter]')), 'ab 3');
  assert.equal(z.querySelector('[data-alter]').getAttribute('aria-label'), 'Empfohlen ab 3 Jahren');
  assert.equal(s.q('[data-folge="folge-03.mp3"] [data-beschreibung]'), null, 'ohne Beschreibung kein Knopf');
  assert.equal(s.q('[data-folge="folge-03.mp3"] [data-alter]'), null, 'ohne Angabe kein Alter');
  assert.equal(z.querySelector('[data-beschreibung-text]'), null, 'zugeklappt');
  const k = z.querySelector('[data-beschreibung]');
  assert.equal(k.getAttribute('aria-expanded'), 'false');
  await klick(s, k);
  assert.equal(text(s.q('[data-folge="folge-01.mp3"] [data-beschreibung-text]')), 'Ein kurzer Text.');
  assert.equal(text(s.q('[data-folge="folge-01.mp3"] [data-beschreibung-quelle]')), 'Von Tonies');
  assert.equal(s.q('[data-folge="folge-01.mp3"] [data-beschreibung]').getAttribute('aria-expanded'), 'true');
  assert.equal(aufrufe(s, 'online/beschreibung').length, 0, 'nicht gekürzt: nichts nachladen');
  await klick(s, s.q('[data-folge="folge-01.mp3"] [data-beschreibung]'));
  assert.equal(s.q('[data-folge="folge-01.mp3"] [data-beschreibung-text]'), null, 'wieder zu');
  assert.equal(s.q('[data-folge="folge-01.mp3"] [data-abspielen]').tagName, 'BUTTON', 'die Zeile spielt weiter');
  weg();
});

test('Folgenzeile: bei beschreibung_gekuerzt lädt die Seite den vollen Text mit Befehl 64 (auch für Benutzer), zeigt ihn und merkt ihn', MIT_DOM, async () => {
  const s = await oeffne('s1', { istAdmin: false, vor: MIT_ONLINE });
  const gekuerzt = s.m.backend.serien.s1.folgen[1];
  assert.ok(gekuerzt.beschreibung_voll.length > 300);
  await klick(s, s.q('[data-folge="folge-02.mp3"] [data-beschreibung]'), 14);
  const r = aufrufe(s, 'online/beschreibung');
  assert.deepEqual(r.map((x) => [x.serie_id, x.folge]), [['s1', 'folge-02.mp3']]);
  assert.equal(text(s.q('[data-folge="folge-02.mp3"] [data-beschreibung-text]')), LANG);
  assert.equal(text(s.q('[data-folge="folge-02.mp3"] [data-beschreibung-quelle]')), 'Von Apple');
  await klick(s, s.q('[data-folge="folge-02.mp3"] [data-beschreibung]'));
  await klick(s, s.q('[data-folge="folge-02.mp3"] [data-beschreibung]'));
  assert.equal(aufrufe(s, 'online/beschreibung').length, 1, 'der volle Text ist gemerkt');
  assert.equal(text(s.q('[data-folge="folge-02.mp3"] [data-beschreibung-text]')), LANG);
  assert.deepEqual(viele(s), ['tobibox/online/beschreibung']);
  weg();
});

test('Folgenzeile: Befehl 64 scheitert → Meldung, der gekürzte Text bleibt; ohne Fähigkeit bleibt es beim gekürzten Text und es geht kein Befehl 64 hinaus', MIT_DOM, async () => {
  const s = await oeffne('s1', { istAdmin: false, vor: (m) => { MIT_ONLINE(m); m.failNext('tobibox/online/beschreibung', 'serie_nicht_gefunden'); } });
  await klick(s, s.q('[data-folge="folge-02.mp3"] [data-beschreibung]'), 14);
  assert.ok(toasts(s).includes(FEHLER.serie_nicht_gefunden));
  assert.ok(text(s.q('[data-folge="folge-02.mp3"] [data-beschreibung-text]')).length <= 300, 'gekürzt');
  weg();
  const o = await oeffne('s1', { faehigkeiten: OHNE, vor: MIT_ONLINE });
  await klick(o, o.q('[data-folge="folge-02.mp3"] [data-beschreibung]'));
  const t = text(o.q('[data-folge="folge-02.mp3"] [data-beschreibung-text]'));
  assert.ok(t.length <= 300 && t.endsWith('.'), 'gekürzter Text, am Satzende');
  assert.equal(aufrufe(o, 'online/beschreibung').length, 0);
  weg();
});

test('Einzeltitel: „ab 3“ und die Beschreibung stehen unter dem Kopf; ohne Angaben nichts', MIT_DOM, async () => {
  const s = await oeffne('lied', { vor: (m) => {
    m.backend.serien.lied = { id: 'lied', name: 'Wiegenlied', typ: 'normal', ordner: 'W', pruefen: false, hinweise: [], art: 'musik', einzeln: true, cover_stand: null, folgen: [folge('w.mp3', 'Wiegenlied', { alter_ab: 1, beschreibung: 'Zum Einschlafen.' })] };
    m.backend.serien.lied2 = { id: 'lied2', name: 'Regenlied', typ: 'normal', ordner: 'R', pruefen: false, hinweise: [], art: 'musik', einzeln: true, cover_stand: null, folgen: [folge('r.mp3', 'Regenlied')] };
  } });
  assert.equal(text(s.q('[data-einzel-info] [data-alter]')), 'ab 1');
  await klick(s, s.q('[data-einzel-info] [data-beschreibung]'));
  assert.equal(text(s.q('[data-einzel-info] [data-beschreibung-text]')), 'Zum Einschlafen.');
  await geheZu(s, '#serie-lied2');
  await s.flush(10);
  assert.equal(s.q('[data-einzel-info]'), null);
  weg();
});

/* ------------------------------------------------------------------ Serienseite: Zurücknehmen */

test('Zurücknehmen (Administrator): Blatt „Zurücknehmen?“ nennt die Felder; Befehl 60 mit serie_id; „Zurückgenommen.“; die Zeile verschwindet', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: MIT_ONLINE });
  assert.equal(text(s.q('[data-online-text]')), 'Aus der Online-Suche übernommen: Cover und Art.');
  assert.equal(s.q('[data-online-frag]'), null);
  await klick(s, s.q('[data-online-zurueck]'));
  assert.equal(text(s.q('dialog.blatt[open] #blatt-t')), 'Zurücknehmen?');
  assert.equal(text(s.q('[data-zuruecknehmen-felder]')), 'Alle Änderungen der Online-Suche an diesem Eintrag nehmen wir zurück. Zuletzt: Cover und Art.', 'GO4-3: ehrlich, dass alle Änderungen zurückgehen');
  await klick(s, blattKnopf(s, SERIE.abbrechen));
  assert.equal(aufrufe(s, 'online/zuruecknehmen').length, 0, 'Abbrechen ändert nichts');
  await klick(s, s.q('[data-online-zurueck]'));
  s.m.backend.online.aenderungen.push({ id: 'a1', serie_id: 's1', lauf_id: null, felder: ['art'], vorher: { art: 'hoerspiel' }, nachher: { art: 'musik' }, zeit: '2026-11-18T10:00:00Z', status: 'fertig' });
  s.m.backend.serien.s1.art = 'musik';
  await klick(s, blattKnopf(s, 'Zurücknehmen'), 14);
  assert.deepEqual(aufrufe(s, 'online/zuruecknehmen').map(({ serie_id, aenderung_id, lauf_id }) => ({ serie_id, aenderung_id, lauf_id })), [{ serie_id: 's1', aenderung_id: undefined, lauf_id: undefined }]);
  assert.ok(toasts(s).includes('Zurückgenommen.'));
  assert.equal(s.q('[data-online-hinweis]'), null, 'die Zeile geht mit der Änderung');
  weg();
});

test('Zurücknehmen: Felder, die inzwischen geändert wurden, bleiben: „Zurückgenommen. 1 Feld blieb, weil es inzwischen geändert wurde.“ (Abnahme 12)', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => {
    MIT_ONLINE(m);
    m.backend.serien.s1.folgen[0].anzeige = 'Von Hand geändert';
    m.backend.online.aenderungen.push({ id: 'a1', serie_id: 's1', lauf_id: null, felder: ['folge_titel@folge-01.mp3'], vorher: { 'folge_titel@folge-01.mp3': 'Der Rabe' }, nachher: { 'folge_titel@folge-01.mp3': 'Online-Titel' }, zeit: '2026-11-18T10:00:00Z', status: 'fertig' });
  } });
  await klick(s, s.q('[data-online-zurueck]'));
  await klick(s, blattKnopf(s, 'Zurücknehmen'), 14);
  assert.ok(toasts(s).includes('Zurückgenommen. 1 Feld blieb, weil es inzwischen geändert wurde.'));
  assert.equal(text(s.q('[data-folge="folge-01.mp3"] .nm')), 'Von Hand geändert');
  weg();
});

test('Zurücknehmen: Fehler (Eintrag weg) mit Klartext, das Blatt schließt und die Seite lädt neu', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { MIT_ONLINE(m); m.failNext('tobibox/online/zuruecknehmen', 'serie_nicht_gefunden'); } });
  await klick(s, s.q('[data-online-zurueck]'));
  await klick(s, blattKnopf(s, 'Zurücknehmen'), 14);
  assert.ok(toasts(s).includes(FEHLER.serie_nicht_gefunden));
  assert.equal(blatt(s), null);
  weg();
});

/* ------------------------------------------------------------------ Blatt „Online suchen“ */

test('Menü: „Online suchen“ im Menü des Eintrags und der Folge (Administrator, Fähigkeit, normaler Eintrag); nicht bei der Überraschungs-Serie', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await klick(s, s.q('[data-menue-serie]'));
  const punkte = s.qa('dialog.blatt[open] [data-menue]').map((x) => x.dataset.menue);
  assert.ok(punkte.includes('online'));
  assert.equal(text(s.q('dialog.blatt[open] [data-menue="online"]')), 'Online suchen');
  await klick(s, blattKnopf(s, 'Schließen'));
  await klick(s, s.q('[data-folge="folge-02.mp3"] [data-menue-folge]'));
  assert.equal(text(s.q('dialog.blatt[open] [data-menue="online"]')), 'Online suchen');
  await klick(s, blattKnopf(s, 'Schließen'));
  await geheZu(s, '#serie-s3');
  await s.flush(10);
  await klick(s, s.q('[data-menue-serie]'));
  assert.equal(s.q('dialog.blatt[open] [data-menue="online"]'), null, 'Überraschungs-Serie');
  weg();
});

test('Suche: das Blatt öffnet mit dem Namen im Suchfeld und sucht gleich (Befehl 57 ohne text); „Suche bei Apple und Tonies …“ danach Treffer mit Vorschau, Marken und „früher abgelehnt“', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.serien.s1.cover_stand = 'ab12cd34'; } });
  const revoke = [];
  const alt = URL.revokeObjectURL;
  URL.revokeObjectURL = (u) => revoke.push(u);
  await trefferSuche(s);
  assert.equal(text(s.q('dialog.blatt[open] #blatt-t')), 'Online suchen');
  assert.equal(s.q('[data-os-text]').value, 'Die drei ???');
  assert.deepEqual(aufrufe(s, 'online/suchen').map(({ serie_id, folge, text: t }) => ({ serie_id, folge, text: t })), [{ serie_id: 's1', folge: undefined, text: undefined }]);
  const zeilen = s.qa('[data-treffer]');
  assert.equal(zeilen.length, 3);
  assert.deepEqual(zeilen.map((z) => text(z.querySelector('.nm'))), ['Die drei ??? (Apple)', 'Die drei ??? (Tonies)', 'Die drei ??? (Album)']);
  assert.deepEqual(zeilen.map((z) => text(z.querySelector('[data-marke="quelle"]'))), ['Apple', 'Tonies', 'Apple']);
  assert.equal(text(zeilen[0].querySelector('.muted')), 'Die drei ??? · Folge 1 · 12 Titel');
  assert.equal(zeilen[0].querySelector('[data-marke="frueher"]'), null);
  assert.equal(text(zeilen[2].querySelector('[data-marke="frueher"]')), 'früher abgelehnt');
  // Vorschau: nur Treffer mit Bild, über die HTTP-Vorschau mit Anmeldung (fetchWithAuth), als blob:
  assert.equal(s.m.vorschauAufrufe.length, 2);
  assert.ok(s.m.vorschauAufrufe.every((p) => /^\/api\/tobibox\/online\/vorschau\/[0-9a-f]{16}$/.test(p)));
  assert.equal(s.qa('[data-treffer] img[data-vorschau]').length, 2);
  assert.match(zeilen[0].querySelector('img').getAttribute('src'), /^blob:/);
  assert.ok(zeilen[2].querySelector('[data-vorschau-ohne]'), 'ohne Bild: Platzhalter');
  // Schließen gibt die Bilder frei
  await klick(s, blattKnopf(s, 'Schließen'));
  await warte(30);
  assert.equal(revoke.length, 2);
  URL.revokeObjectURL = alt;
  weg();
});

test('Suche für eine Folge: Befehl 57 mit folge; der Suchtext ist der Folgentitel; geänderter Text wird als text gesendet, ein zu kurzer nicht', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await trefferSuche(s, 'folge-02.mp3');
  assert.equal(s.q('[data-os-text]').value, 'Das Gespensterschloss');
  assert.equal(aufrufe(s, 'online/suchen')[0].folge, 'folge-02.mp3');
  tippe(s.q('[data-os-text]'), 'Gespenst');
  await klick(s, s.q('[data-os-suchen]'));
  assert.deepEqual(aufrufe(s, 'online/suchen').map((x) => x.text), [undefined, 'Gespenst']);
  tippe(s.q('[data-os-text]'), 'G');
  await klick(s, s.q('[data-os-suchen]'));
  assert.equal(aufrufe(s, 'online/suchen').length, 2, 'unter 2 Zeichen wird nicht gesendet');
  weg();
});

test('Suche: nichts gefunden; keine Quelle erreichbar (Satz statt Fehlerton); eine Quelle aus; gedrosselt mit Uhrzeit', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.online.suchTreffer = []; } });
  await trefferSuche(s);
  assert.equal(text(s.q('[data-suche-status="nichts"]')), 'Nichts gefunden. Versuch einen anderen Namen.');
  s.m.backend.online.quellen = { itunes: 'fehler', tonies: 'fehler' };
  await klick(s, s.q('[data-os-suchen]'));
  assert.equal(text(s.q('[data-suche-status="keine"]')), 'Online-Suche gerade nicht erreichbar, später noch einmal.');
  assert.deepEqual(toasts(s), [], 'kein Fehler-Toast (O9)');
  s.m.backend.online.suchTreffer = null;
  s.m.backend.online.quellen = { itunes: 'fehler', tonies: 'ok' };
  await klick(s, s.q('[data-os-suchen]'));
  assert.equal(text(s.q('[data-quelle-hinweis="itunes"]')), 'Apple antwortet gerade nicht. Das sind nur Treffer von Tonies.');
  assert.ok(s.qa('[data-treffer]').length >= 1, 'die Treffer der anderen Quelle stehen da');
  s.m.backend.online.quellen = { itunes: 'pause', tonies: 'ok' };
  s.m.backend.online.quellenStatus = { itunes: { erreichbar: false, pause_bis: '2026-11-19T13:20:00Z' } };
  await klick(s, s.q('[data-os-suchen]'), 16);
  assert.equal(text(s.q('[data-quelle-hinweis="itunes"]')), `Apple braucht eine Pause, bis ${O.uhrzeit('2026-11-19T13:20:00Z')}. Das sind nur Treffer von Tonies.`);
  weg();
});

test('Suche: sonstiger Fehler bei Befehl 57 → Fehlerkarte mit „Noch einmal versuchen“; Eintrag weg → Meldung und das Blatt schließt', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => m.failNext('tobibox/online/suchen', 'unknown_error') });
  await trefferSuche(s);
  assert.ok(s.q('dialog.blatt[open] [data-zustand="fehler"]'));
  assert.ok(toasts(s).length >= 1);
  await klick(s, s.q('dialog.blatt[open] [data-zustand="fehler"] button'));
  assert.equal(s.qa('[data-treffer]').length, 3);
  s.m.failNext('tobibox/online/suchen', 'serie_nicht_gefunden');
  await klick(s, s.q('[data-os-suchen]'));
  assert.equal(blatt(s), null);
  assert.ok(toasts(s).includes(FEHLER.serie_nicht_gefunden));
  weg();
});

/* ------------------------------------------------------------------ Übersicht und Übernehmen */

async function bisUebersicht(s, folge = null, n = 0) {
  await trefferSuche(s, folge);
  await klick(s, s.qa('[data-treffer]')[n], 14);
}

test('Übersicht: je Feld „heute → neu“ mit Häkchen, alle gesetzt, Cover als zwei kleine Bilder, „von Hand gesetzt“ ohne Häkchen, gleiche Werte fehlen', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.serien.s1.cover_stand = 'ab12cd34'; m.backend.serien.s1.folgen[0].nummer = 1; m.backend.serien.s1.hand = ['art']; } });
  await bisUebersicht(s, 'folge-01.mp3');
  assert.equal(aufrufe(s, 'online/treffer').length, 1);
  assert.deepEqual(Object.keys(aufrufe(s, 'online/treffer')[0]).filter((k) => k !== 'id' && k !== 'type'), ['treffer_id']);
  assert.equal(text(s.q('dialog.blatt[open] #blatt-t')), 'Was soll übernommen werden?');
  const keys = s.qa('[data-feld]').map((b) => b.dataset.feld);
  assert.deepEqual(keys, ['art', 'cover', 'folge_titel@folge-01.mp3', 'nummer@folge-01.mp3', 'alter_ab@folge-01.mp3', 'beschreibung@folge-01.mp3']);
  const haken = (k) => s.q(`[data-feld="${k}"]`).getAttribute('aria-checked');
  assert.equal(haken('art'), 'false', 'von Hand gesetzt: kein Häkchen');
  assert.ok(s.q('[data-feldzeile="art"] [data-hand]'));
  assert.equal(text(s.q('[data-feldzeile="art"] [data-hand]')), 'von Hand gesetzt');
  for (const k of keys.filter((x) => x !== 'art')) assert.equal(haken(k), 'true', k);
  assert.equal(text(s.q('[data-feld="nummer@folge-01.mp3"] [data-wert="nummer"]')), 'heute: 1 → neu: 2');
  assert.equal(text(s.q('[data-feld="alter_ab@folge-01.mp3"] [data-wert="alter_ab"]')), 'heute: leer → neu: ab 5');
  assert.match(text(s.q('[data-feld="art"] [data-wert="art"]')), /^heute: .+ → neu: Hörspiel$/);
  assert.ok(text(s.q('[data-feld="nummer@folge-01.mp3"]')).includes('Folge „Der Rabe“'), 'die Folge steht beim Feld');
  assert.equal(text(s.q('[data-feld="folge_titel@folge-01.mp3"] .os-fname')), 'Folge', 'beim Titel selbst steht sie nicht noch einmal');
  const cover = s.q('[data-feld="cover"] [data-wert="cover"]');
  assert.equal(cover.querySelectorAll('.os-cv').length, 2, 'zwei kleine Bilder');
  assert.ok(cover.querySelector('[data-cover="s1"]'), 'heute: das Cover des Eintrags');
  await warte(30); await s.flush(6);
  assert.ok(cover.querySelector('img[data-vorschau-neu]'), 'neu: die Vorschau des Treffers');
  assert.equal(s.m.vorschauAufrufe.length, 3, 'zwei beim Suchen, eine für die Übersicht');
  weg();
});

test('Eigenes Foto: das Cover steht ohne Häkchen mit „von Hand gesetzt“ (Abnahme 6); der Name, den die Seite nie automatisch ändert, hat Häkchen', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.serien.s1.cover_stand = 'ab12cd34'; m.backend.serien.s1.cover_quelle = 'eigen'; } });
  await bisUebersicht(s);
  assert.equal(s.q('[data-feld="cover"]').getAttribute('aria-checked'), 'false');
  assert.equal(text(s.q('[data-feldzeile="cover"] [data-hand]')), 'von Hand gesetzt');
  assert.equal(s.q('[data-feld="art"]').getAttribute('aria-checked'), 'true');
  weg();
});

test('Übersicht: „Übernehmen“ nur mit mindestens einem Häkchen; abwählbar; „Zurück“ führt zur Liste, die Treffer bleiben', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await bisUebersicht(s);
  const ue = () => blattKnopf(s, 'Übernehmen');
  assert.equal(ue().disabled, false);
  for (const b of s.qa('[data-feld]')) await klick(s, b, 4);
  assert.equal(s.qa('[data-feld][aria-checked="true"]').length, 0);
  assert.equal(ue().disabled, true);
  await klick(s, s.q('[data-feld="art"]'));
  assert.equal(ue().disabled, false);
  await klick(s, blattKnopf(s, 'Zurück'));
  assert.equal(s.qa('[data-treffer]').length, 3);
  assert.equal(aufrufe(s, 'online/suchen').length, 1, 'nicht neu gesucht');
  weg();
});

test('Übernehmen: sendet nur die angehakten Felder mit treffer_id, stand und anfrage_id; „Übernommen.“; die Seite lädt neu (Hinweiszeile, Zurücknehmen); Werte kommen nicht von der Seite', MIT_DOM, async () => {
  const s = await oeffne('s1');
  const stand0 = (await s.m.hass.connection.sendMessagePromise({ type: 'tobibox/serie/get', serie_id: 's1' })).stand;
  await bisUebersicht(s, 'folge-01.mp3');
  await klick(s, s.q('[data-feld="cover"]'), 4); // Cover abwählen
  await klick(s, blattKnopf(s, 'Übernehmen'), 16);
  const u = aufrufe(s, 'online/uebernehmen');
  assert.equal(u.length, 1);
  assert.deepEqual(u[0].felder.sort(), ['alter_ab@folge-01.mp3', 'art', 'beschreibung@folge-01.mp3', 'folge_titel@folge-01.mp3', 'nummer@folge-01.mp3']);
  assert.match(u[0].treffer_id, /^[0-9a-f]{16}$/);
  assert.equal(u[0].stand, stand0);
  assert.match(u[0].anfrage_id, /^[0-9A-Za-z-]{8,64}$/);
  assert.deepEqual(Object.keys(u[0]).filter((k) => !['id', 'type'].includes(k)).sort(), ['anfrage_id', 'felder', 'serie_id', 'stand', 'treffer_id']);
  assert.ok(toasts(s).includes('Übernommen.'));
  assert.equal(blatt(s), null);
  assert.equal(text(s.q('[data-online-text]')), 'Aus der Online-Suche übernommen: Art, Folge, Nummer, Alter und Beschreibung.');
  assert.ok(s.q('[data-online-zurueck]'));
  assert.equal(text(s.q('[data-folge="folge-01.mp3"] [data-alter]')), 'ab 5');
  assert.equal(text(s.q('[data-folge="folge-01.mp3"] .nm')), 'Der Rabe (Neu)');
  weg();
});

test('Übernehmen mit Cover: danach „Online“ als Quelle, das Cover-Blatt bietet „Online-Cover entfernen“ (nur Administratoren, nur bei cover_quelle online)', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.serien.s1.cover_stand = 'ab12cd34'; } });
  await bisUebersicht(s);
  await klick(s, blattKnopf(s, 'Übernehmen'), 16);
  assert.equal(aufrufe(s, 'serie/get').at(-1).serie_id, 's1');
  assert.equal(s.m.backend.serien.s1.cover_quelle, 'online');
  await klick(s, s.q('[data-menue-serie]'));
  await klick(s, s.q('dialog.blatt[open] [data-menue="cover"]'));
  assert.ok(s.q('[data-cover-online-weg]'));
  assert.equal(text(s.q('[data-cover-online-weg]')), 'Online-Cover entfernen');
  assert.equal(s.q('[data-cover-zurueck]'), null, 'kein eigenes Foto');
  await klick(s, s.q('[data-cover-online-weg]'), 14);
  assert.deepEqual(s.m.coverAufrufe.filter((c) => c.methode === 'DELETE').map((c) => c.pfad), ['/api/tobibox/cover/s1?quelle=online']);
  assert.ok(toasts(s).includes(ONLINE.menue.cover_weg_fertig));
  assert.equal(s.m.backend.serien.s1.cover_quelle, 'auto');
  weg();
  const u = await oeffne('s1', { istAdmin: false, vor: (m) => { m.backend.serien.s1.cover_stand = 'ab12cd34'; m.backend.serien.s1.cover_quelle = 'online'; } });
  await klick(u, u.q('[data-menue-serie]'));
  await klick(u, u.q('dialog.blatt[open] [data-menue="cover"]'));
  assert.equal(u.q('[data-cover-online-weg]'), null);
  weg();
});

test('Übernehmen von Name (Pflicht stand) und Namensfeld: „Der Name ist geändert.“', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await bisUebersicht(s, null, 1); // Tonies-Treffer mit Namen
  assert.ok(s.q('[data-feld="serie_name"]'));
  assert.equal(text(s.q('[data-feld="serie_name"] [data-wert="serie_name"]')), 'heute: Die drei ??? → neu: Die drei ??? Neu');
  for (const k of ['cover']) await klick(s, s.q(`[data-feld="${k}"]`), 4);
  await klick(s, blattKnopf(s, 'Übernehmen'), 16);
  assert.ok(aufrufe(s, 'online/uebernehmen')[0].stand, 'stand wird immer gesendet');
  assert.ok(toasts(s).includes('Der Name ist geändert.'));
  assert.equal(text(s.q('main h2')), 'Die drei ??? Neu');
  weg();
});

test('Treffer abgelaufen: bei der Übersicht und beim Übernehmen kommt „Die Suche ist zu alt. Such bitte noch einmal.“ und das Blatt steht wieder bei der Suche', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await trefferSuche(s);
  for (const t of Object.values(s.m.backend.online.treffer)) t.abgelaufen = true;
  await klick(s, s.qa('[data-treffer]')[0], 14);
  assert.ok(toasts(s).includes('Die Suche ist zu alt. Such bitte noch einmal.'));
  assert.ok(s.q('[data-os-suchen]'), 'wieder bei der Suche');
  assert.equal(s.qa('[data-treffer]').length, 0, 'die alten Treffer sind weg');
  await klick(s, s.q('[data-os-suchen]'), 14);
  assert.equal(s.qa('[data-treffer]').length, 3);
  await klick(s, s.qa('[data-treffer]')[0], 14);
  for (const t of Object.values(s.m.backend.online.treffer)) t.abgelaufen = true;
  await klick(s, blattKnopf(s, 'Übernehmen'), 14);
  assert.ok(s.q('[data-os-suchen]'), 'auch nach dem Übernehmen zurück zur Suche');
  assert.equal(s.m.backend.serien.s1.art_quelle, undefined, 'nichts übernommen');
  weg();
});

test('Übernehmen: stand_veraltet → Klartext, das Blatt schließt, die Seite lädt neu; name_ungueltig und andere Fehler lassen es offen', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await bisUebersicht(s);
  s.m.failNext('tobibox/online/uebernehmen', 'stand_veraltet');
  const vorher = aufrufe(s, 'serie/get').length;
  await klick(s, blattKnopf(s, 'Übernehmen'), 14);
  assert.ok(toasts(s).includes(FEHLER.stand_veraltet));
  assert.equal(blatt(s), null);
  assert.ok(aufrufe(s, 'serie/get').length > vorher);
  await bisUebersicht(s);
  s.m.failNext('tobibox/online/uebernehmen', 'medien_schreibfehler');
  await klick(s, blattKnopf(s, 'Übernehmen'), 14);
  assert.ok(toasts(s).includes(FEHLER.medien_schreibfehler.replace('{verwalter_dat}', 'dem Administrator')));
  assert.ok(blatt(s), 'bleibt offen: noch einmal versuchen');
  await klick(s, blattKnopf(s, 'Übernehmen'), 14);
  assert.equal(blatt(s), null);
  assert.equal(aufrufe(s, 'online/uebernehmen').at(-1).anfrage_id, aufrufe(s, 'online/uebernehmen').at(-2).anfrage_id, 'dieselbe Wahl: dieselbe anfrage_id');
  weg();
});

test('„Hier ist schon alles so.“, wenn der Treffer nichts Neues bringt', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.online.suchTreffer = [{ quelle: 'itunes', titel: 'Gleich', hat_cover: false, werte: { art: 'hoerspiel' } }]; m.backend.serien.s1.art = 'hoerspiel'; } });
  await bisUebersicht(s);
  assert.equal(text(s.q('[data-alles-gleich]')), 'Hier ist schon alles so.');
  assert.equal(blattKnopf(s, 'Übernehmen').disabled, true);
  weg();
});

test('Lange Beschreibung in der Übersicht: gekürzt mit „mehr“', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.online.suchTreffer = [{ quelle: 'tonies', titel: 'Mit Text', hat_cover: false, werte: { 'beschreibung@folge-01.mp3': LANG } }]; } });
  await bisUebersicht(s, 'folge-01.mp3');
  const w = () => text(s.q('[data-feld="beschreibung@folge-01.mp3"] .os-neu'));
  assert.ok(w().length < 160);
  assert.ok(w().endsWith('…'));
  await klick(s, s.q('[data-feld-mehr]'));
  assert.ok(w().includes(LANG));
  assert.equal(text(s.q('[data-feld-mehr]')), 'weniger');
  weg();
});

/* ------------------------------------------------------------------ Vorschläge (nur Administratoren) */

const VORSCHLAEGE = (m) => {
  m.backend.online.vorschlaege.s1 = [
    { id: 'v-apple', art: 'felder', quelle: 'itunes', felder: ['cover', 'art'], werte: { cover: true, art: 'musik' }, zeit: '2026-11-18T10:00:00Z' },
    { id: 'v-claude', art: 'felder', quelle: 'claude', felder: ['serie_name'], name: 'Die drei Fragezeichen', grund: 'Der Ordnername passt besser <b>fett</b>.', zeit: '2026-11-18T10:00:00Z' },
    { id: 'v-zus', art: 'zusammenfuehren', quelle: 'claude', ziel_serie_id: 's2', zeit: '2026-11-18T10:00:00Z' },
  ];
};

test('Karte für Administratoren: drei Vorschläge mit Text, Claude-Grund als Text (nie als HTML), Knöpfe mit Namen', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  const k = s.q('[data-karte="ansehen"]');
  assert.ok(k, 'die Karte steht auch ohne „bitte ansehen“');
  assert.equal(text(k.querySelector('strong')), 'Vorschlag aus der Online-Suche');
  assert.equal(s.qa('[data-vorschlag]').length, 3);
  assert.equal(text(s.q('[data-vorschlag="v-apple"] [data-vorschlag-text]')), 'Vorschlag aus der Online-Suche: Cover und Art von Apple');
  assert.equal(text(s.q('[data-vorschlag="v-claude"] [data-vorschlag-text]')), 'Vorschlag von Claude: Name „Die drei Fragezeichen“');
  const grund = s.q('[data-vorschlag="v-claude"] [data-vorschlag-grund]');
  assert.equal(text(grund), 'Der Ordnername passt besser <b>fett</b>.');
  assert.equal(grund.querySelector('b'), null, 'kein HTML');
  assert.equal(text(s.q('[data-vorschlag="v-zus"] [data-vorschlag-text]')), 'Vorschlag von Claude: mit „Bibi Blocksberg“ zusammenführen');
  assert.deepEqual(s.qa('[data-vorschlag="v-apple"] button').map(text), ['Ansehen', 'Nein']);
  assert.deepEqual(s.qa('[data-vorschlag="v-claude"] button').map(text), ['Übernehmen', 'Nein']);
  assert.deepEqual(s.qa('[data-vorschlag="v-zus"] button').map(text), ['Zusammenführen …', 'Nein']);
  assert.ok(s.q('[data-vorschlag="v-claude"] [data-vorschlag-aktion="nein"]').getAttribute('aria-label').includes('Fragezeichen'));
  weg();
});

test('Vorschlag „Ansehen“: Übersicht aus dem Vorschlag (Befehl 58 mit serie_id und vorschlag_id), Übernehmen mit vorschlag_id; der Vorschlag verschwindet', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  await klick(s, s.q('[data-vorschlag="v-apple"] [data-vorschlag-aktion="ansehen"]'), 14);
  const t = aufrufe(s, 'online/treffer');
  assert.deepEqual(t.map(({ serie_id, vorschlag_id, treffer_id }) => ({ serie_id, vorschlag_id, treffer_id })), [{ serie_id: 's1', vorschlag_id: 'v-apple', treffer_id: undefined }]);
  assert.equal(text(s.q('dialog.blatt[open] #blatt-t')), 'Was soll übernommen werden?');
  assert.deepEqual(s.qa('[data-feld]').map((b) => b.dataset.feld), ['art', 'cover']);
  assert.ok(s.q('[data-feld="cover"] img[data-vorschau-neu]'), 'T10: das neue Bild kommt über die vorschau_id von Nr. 58');
  assert.equal(s.m.vorschauAufrufe.length, 1);
  assert.deepEqual(s.qa('dialog.blatt[open] .knoepfe button').map(text), ['Abbrechen', 'Übernehmen']);
  await klick(s, blattKnopf(s, 'Übernehmen'), 16);
  const u = aufrufe(s, 'online/uebernehmen')[0];
  assert.equal(u.vorschlag_id, 'v-apple');
  assert.equal(u.treffer_id, undefined);
  assert.deepEqual(u.felder.sort(), ['art', 'cover']);
  assert.equal(s.q('[data-vorschlag="v-apple"]'), null);
  assert.ok(s.q('[data-vorschlag="v-claude"]'), 'die anderen bleiben');
  weg();
});

test('Vorschlag „Nein“: Befehl 61, „Der Vorschlag ist verworfen.“, die Karte verliert die Zeile; der letzte Vorschlag nimmt die Karte mit', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.online.vorschlaege.s1 = [{ id: 'v1', art: 'felder', quelle: 'tonies', felder: ['cover'], werte: { cover: true }, zeit: '2026-11-18T10:00:00Z' }]; } });
  await klick(s, s.q('[data-vorschlag="v1"] [data-vorschlag-aktion="nein"]'), 14);
  assert.deepEqual(aufrufe(s, 'online/vorschlag_verwerfen').map(({ serie_id, vorschlag_id }) => ({ serie_id, vorschlag_id })), [{ serie_id: 's1', vorschlag_id: 'v1' }]);
  assert.ok(toasts(s).includes('Der Vorschlag ist verworfen.'));
  assert.equal(s.q('[data-karte="ansehen"]'), null);
  weg();
});

test('Vorschlag weg (vorschlag_nicht_gefunden): Klartext, die Seite lädt neu', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  s.m.failNext('tobibox/online/vorschlag_verwerfen', 'vorschlag_nicht_gefunden');
  await klick(s, s.q('[data-vorschlag="v-apple"] [data-vorschlag-aktion="nein"]'), 14);
  assert.ok(toasts(s).includes(FEHLER.vorschlag_nicht_gefunden));
  weg();
});

test('Namensvorschlag von Claude „Übernehmen“: Befehl 59 mit felder [serie_name], stand und vorschlag_id; wirkt wie Umbenennen von Hand (keine Hinweiszeile); „Nein“ verwirft', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  await klick(s, s.q('[data-vorschlag="v-claude"] [data-vorschlag-aktion="uebernehmen"]'), 16);
  const u = aufrufe(s, 'online/uebernehmen');
  assert.equal(u.length, 1);
  assert.deepEqual([u[0].serie_id, u[0].vorschlag_id, u[0].felder], ['s1', 'v-claude', ['serie_name']]);
  assert.ok(u[0].stand && u[0].anfrage_id);
  assert.ok(toasts(s).includes('Der Name ist geändert.'));
  assert.equal(text(s.q('main h2')), 'Die drei Fragezeichen');
  assert.equal(s.q('[data-online-hinweis]'), null, 'ein angenommener Claude-Name ist keine Online-Änderung (GO-14)');
  assert.equal(s.q('[data-vorschlag="v-claude"]'), null);
  weg();
  const n = await oeffne('s1', { vor: VORSCHLAEGE });
  await klick(n, n.q('[data-vorschlag="v-claude"] [data-vorschlag-aktion="nein"]'), 14);
  assert.equal(aufrufe(n, 'online/vorschlag_verwerfen')[0].vorschlag_id, 'v-claude');
  assert.equal(n.m.backend.serien.s1.name, 'Die drei ???', 'der Name bleibt');
  weg();
});

test('Namensvorschlag: name_ungueltig und stand_veraltet mit Klartext; der Name bleibt', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { VORSCHLAEGE(m); m.failNext('tobibox/online/uebernehmen', 'name_ungueltig', 'stand_veraltet'); } });
  await klick(s, s.q('[data-vorschlag="v-claude"] [data-vorschlag-aktion="uebernehmen"]'), 14);
  assert.ok(toasts(s).includes(FEHLER.name_ungueltig));
  await klick(s, s.q('[data-vorschlag="v-claude"] [data-vorschlag-aktion="uebernehmen"]'), 14);
  assert.ok(toasts(s).includes(FEHLER.stand_veraltet));
  assert.equal(s.m.backend.serien.s1.name, 'Die drei ???');
  weg();
});

test('Vorschlag zum Zusammenführen: öffnet den vorhandenen Dialog, vorbelegt; bestätigt geht serien/zusammenfuehren mit beiden Ständen, nie Befehl 59', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  await klick(s, s.q('[data-vorschlag="v-zus"] [data-vorschlag-aktion="zusammen"]'), 14);
  assert.equal(text(s.q('dialog.blatt[open] #blatt-t')), fuellen(SERIE.zusammen.titel, { name: 'Die drei ???', ziel: 'Bibi Blocksberg' }));
  assert.equal(aufrufe(s, 'serien/zusammenfuehren').length, 0, 'erst die Rückfrage');
  await klick(s, blattKnopf(s, SERIE.zusammen.knopf), 16);
  const z = aufrufe(s, 'serien/zusammenfuehren');
  assert.equal(z.length, 1);
  assert.deepEqual([z[0].quelle_id, z[0].ziel_id], ['s1', 's2']);
  assert.ok(z[0].stand_quelle && z[0].stand_ziel);
  assert.equal(aufrufe(s, 'online/uebernehmen').length, 0);
  weg();
});

test('Vorschläge ohne Fähigkeit und für Benutzer: die Karte fehlt, auch wenn die Antwort die Liste trüge', MIT_DOM, async () => {
  const s = await oeffne('s1', { faehigkeiten: OHNE, vor: VORSCHLAEGE });
  assert.equal(s.q('[data-karte="ansehen"]'), null);
  assert.equal(s.q('[data-vorschlaege]'), null);
  weg();
  const u = await oeffne('s1', { istAdmin: false, vor: (m) => { VORSCHLAEGE(m); m.on('tobibox/serie/get', (msg, b) => ({ ...JSON.parse(JSON.stringify(b.serien.s1)), id: 's1', stand: 'x', cover_stand: null, online_vorschlaege_liste: [{ id: 'v', art: 'felder', quelle: 'itunes', felder: ['cover'] }], folgen: b.serien.s1.folgen, zuordnungen: [] })); } });
  assert.equal(u.q('[data-vorschlaege]'), null, 'für Benutzer nie');
  weg();
});

/* ------------------------------------------------------------------ Bibliothek: Filter */

test('Filter „Mit Vorschlag der Online-Suche“ (online_vorschlag): nur Administratoren mit Fähigkeit; die Liste fragt serien/list mit dem Filter', MIT_DOM, async () => {
  const s = await oeffne('s1', { hash: '#bibliothek', vor: VORSCHLAEGE });
  await klick(s, s.q('[data-sortieren]'));
  const namen = s.qa('dialog.blatt[open] .optrow[aria-pressed]').map(text);
  assert.ok(namen.includes(BIB.blatt.nur_wahl.online_vorschlag));
  await klick(s, s.qa('dialog.blatt[open] .optrow[aria-pressed]').find((b) => text(b) === BIB.blatt.nur_wahl.online_vorschlag));
  assert.deepEqual(aufrufe(s, 'serien/list').at(-1).filter, ['online_vorschlag']);
  await klick(s, blattKnopf(s, 'Fertig'));
  assert.deepEqual(s.qa('a.lrow, a.rcard').map((a) => a.dataset.serie), ['s1'], 'nur Einträge mit Vorschlag');
  weg();
  for (const opts of [{ istAdmin: false }, { faehigkeiten: OHNE }]) {
    const x = await oeffne('s1', { hash: '#bibliothek', ...opts });
    await klick(x, x.q('[data-sortieren]'));
    assert.ok(!x.qa('dialog.blatt[open] .optrow[aria-pressed]').map(text).includes(BIB.blatt.nur_wahl.online_vorschlag), JSON.stringify(opts));
    weg();
  }
});

/* ------------------------------------------------------------------ Technik › Online-Suche */

const technik = async (opts = {}) => oeffne('s1', { hash: '#technik-online', ...opts });

test('Technik: die Liste hat die Zeile „Online-Suche“ hinter „Speicher und Netz“ (nur mit Fähigkeit); die Unterseite sagt Quellen, Lauf und Läufe', MIT_DOM, async () => {
  const s = await oeffne('s1', { hash: '#technik' });
  const zeilen = s.qa('[data-technik="liste"] a.tzeile');
  assert.deepEqual(zeilen.map((a) => a.getAttribute('href')), ['#technik-boxen', '#technik-speicher', '#technik-online', '#technik-liste', '#technik-tobies', '#technik-meldungen', '#technik-einstellungen']);
  assert.equal(text(zeilen[2].querySelector('strong')), 'Online-Suche');
  weg();
  const o = await oeffne('s1', { hash: '#technik', faehigkeiten: OHNE });
  assert.equal(o.qa('[data-technik="liste"] a.tzeile').length, 6);
  assert.equal(o.q('a[href="#technik-online"]'), null);
  weg();
  const x = await technik({ faehigkeiten: OHNE });
  assert.ok(x.q('[data-technik="liste"]'), 'ohne Fähigkeit zeigt die Adresse die Liste');
  assert.deepEqual(viele(x), []);
  weg();
});

test('Technik › Online-Suche: Quellen (Apple, Tonies, Tonies-Shop, Claude eingerichtet und erreichbar, Tonie-Liste) und Zustand ohne Lauf', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => { m.backend.online.quellenStatus = { tonies_shop: { erreichbar: false }, claude: { eingerichtet: true, erreichbar: false } }; } });
  assert.equal(text(s.q('main h2')), 'Online-Suche');
  const q = (n) => text(s.q(`[data-quelle="${n}"]`));
  assert.equal(q('itunes'), 'Apple erreichbar');
  assert.equal(q('tonies'), 'Tonies erreichbar');
  assert.equal(q('tonies_shop'), 'Tonies-Shop antwortet gerade nicht');
  assert.equal(q('claude'), 'Claude antwortet gerade nicht');
  assert.match(q('tonie_liste'), /^Tonie-Liste Stand .+, 1234 Einträge$|^Tonie-Liste Stand .+, 1\.234 Einträge$/);
  assert.equal(text(s.q('[data-lauf-zustand="kein"]')), 'Kein Lauf.');
  assert.equal(text(s.q('[data-aktion="online_starten"]')), 'Bibliothek durchsuchen');
  assert.equal(text(s.q('[data-keine-laeufe]')), 'Noch kein Lauf.');
  assert.deepEqual(viele(s), ['tobibox/online/status']);
  s.m.backend.online.quellenStatus = { claude: { eingerichtet: false, erreichbar: false } };
  s.m.backend.online.tonieListe = null;
  await geheZu(s, '#technik');
  await geheZu(s, '#technik-online');
  assert.equal(q('claude'), 'Claude nicht eingerichtet, keine Namensvorschläge');
  assert.equal(q('tonie_liste'), 'Tonie-Liste noch nicht geladen');
  weg();
});

test('Technik › Online-Suche: Lauf starten (Befehl 62), Fortschritt über das Ereignis `online`, Pause, Anhalten, Ende mit Zahlen', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => { m.backend.online.gesamt = 340; } });
  await klick(s, s.q('[data-aktion="online_starten"]'), 14);
  assert.deepEqual(aufrufe(s, 'online/lauf').map((x) => x.aktion), ['start']);
  assert.ok(toasts(s).includes('Der Lauf ist gestartet.'));
  assert.equal(s.q('[data-aktion="online_starten"]'), null);
  assert.equal(text(s.q('[data-lauf-zustand="laeuft"]')), 'Läuft: 0 von 340.');
  assert.equal(s.q('[role="progressbar"]').getAttribute('aria-valuenow'), '0');
  s.m.emit('online', 'stand', { vorgang: 'lauf', lauf_id: s.m.backend.online.lauf.lauf_id, zustand: 'laeuft', erledigt: 85, gesamt: 340, geaendert: 20, vorschlaege: 6, keiner: 3 });
  await s.flush(6);
  assert.equal(text(s.q('[data-lauf-zustand="laeuft"]')), 'Läuft: 85 von 340.');
  assert.equal(s.q('[role="progressbar"]').getAttribute('aria-valuenow'), '25');
  assert.equal(text(s.q('[data-lauf-zahlen]')), '20 geändert, 6 Vorschläge, 3 ohne Treffer.');
  s.m.backend.online.quellenStatus = { itunes: { erreichbar: false, pause_bis: '2026-11-19T13:20:00Z' } };
  s.m.emit('online', 'quelle', { quelle: 'itunes', erreichbar: false, pause_bis: '2026-11-19T13:20:00Z' });
  s.m.emit('online', 'stand', { vorgang: 'lauf', lauf_id: 'x', zustand: 'pausiert', erledigt: 90, gesamt: 340, geaendert: 21, vorschlaege: 6, keiner: 3, pause_bis: '2026-11-19T13:20:00Z' });
  await s.flush(6);
  assert.equal(text(s.q('[data-lauf-zustand="pausiert"]')), `Pause bis ${O.uhrzeit('2026-11-19T13:20:00Z')}, weil Apple bremst.`);
  assert.match(text(s.q('[data-quelle="itunes"]')), /^Apple Pause bis \d\d:\d\d$/);
  s.m.emit('online', 'stand', { vorgang: 'lauf', lauf_id: 'x', zustand: 'laeuft', erledigt: 100, gesamt: 340, geaendert: 25, vorschlaege: 7, keiner: 3 });
  await s.flush(4);
  await klick(s, s.q('[data-aktion="online_anhalten"]'), 14);
  assert.deepEqual(aufrufe(s, 'online/lauf').map((x) => x.aktion), ['start', 'stop']);
  assert.equal(text(s.q('[data-lauf-zustand="wird_angehalten"]')), 'Hält nach dieser Serie an.');
  assert.equal(s.q('[data-aktion="online_anhalten"]').disabled, true);
  s.m.onlineLaufBeenden('angehalten', 'angehalten', { erledigt: 101, gesamt: 340, geaendert: 26, vorschlaege: 7, keiner: 3 });
  await warte(20); await s.flush(10);
  assert.equal(text(s.q('[data-lauf-zustand="kein"]')), 'Kein Lauf.');
  assert.equal(text(s.q('[data-lauf-ende]')), 'Angehalten.');
  assert.ok(s.q('[data-aktion="online_starten"]'));
  assert.equal(text(s.q('[data-lauf] [data-lauf-text]')), 'Angehalten.');
  weg();
});

test('Technik › Online-Suche: Ende „Fertig: …“ mit Zahlen; „abgebrochen“ mit Grund und ohne Grund (Vertrag 19.11.) wird sauber angezeigt, kein „undefined“', MIT_DOM, async () => {
  const s = await technik();
  await klick(s, s.q('[data-aktion="online_starten"]'), 12);
  s.m.onlineLaufBeenden('fertig', undefined, { erledigt: 340, gesamt: 340, geaendert: 120, vorschlaege: 38, keiner: 12 });
  await warte(20); await s.flush(10);
  assert.equal(text(s.q('[data-lauf-ende]')), 'Fertig: 120 Einträge geändert, 38 Vorschläge, 12 ohne Treffer.');
  await klick(s, s.q('[data-aktion="online_starten"]'), 12);
  s.m.onlineLaufBeenden('abgebrochen', undefined, { erledigt: 5, gesamt: 340, geaendert: 1, vorschlaege: 0, keiner: 0 });
  await warte(20); await s.flush(10);
  assert.equal(text(s.q('[data-lauf-ende]')), 'Abgebrochen. Du kannst neu starten.');
  await klick(s, s.q('[data-aktion="online_starten"]'), 12);
  s.m.onlineLaufBeenden('abgebrochen', 'neustart');
  await warte(20); await s.flush(10);
  assert.equal(text(s.q('[data-lauf-ende]')), 'Abgebrochen (Neustart). Du kannst neu starten.');
  await klick(s, s.q('[data-aktion="online_starten"]'), 12);
  s.m.onlineLaufBeenden('abgebrochen', 'quelle');
  await warte(20); await s.flush(10);
  assert.equal(text(s.q('[data-lauf-ende]')), 'Abgebrochen: Quelle nicht erreichbar.');
  const zeilen = s.qa('[data-lauf]');
  assert.deepEqual(zeilen.map((z) => z.dataset.zustand), ['abgebrochen', 'abgebrochen', 'abgebrochen', 'fertig']);
  assert.deepEqual(zeilen.map((z) => text(z.querySelector('[data-lauf-text]'))), ['Abgebrochen: Quelle nicht erreichbar.', 'Abgebrochen (Neustart). Du kannst neu starten.', 'Abgebrochen. Du kannst neu starten.', 'Fertig: 120 Einträge geändert, 38 Vorschläge, 12 ohne Treffer.']);
  assert.ok(!text(s.q('[data-online-seite]')).includes('undefined'));
  weg();
});

test('Technik › Online-Suche: ein bestehender Lauf beim Öffnen (Befehl 63), `lauf_laeuft_schon` beim Start mit Klartext', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => { m.backend.online.lauf = { lauf_id: 'l1', zustand: 'laeuft', erledigt: 10, gesamt: 100, geaendert: 2, vorschlaege: 1, keiner: 0 }; } });
  assert.equal(text(s.q('[data-lauf-zustand="laeuft"]')), 'Läuft: 10 von 100.');
  assert.ok(s.q('[data-aktion="online_anhalten"]'));
  weg();
  const t = await technik();
  t.m.failNext('tobibox/online/lauf', 'lauf_laeuft_schon');
  await klick(t, t.q('[data-aktion="online_starten"]'), 14);
  assert.ok(toasts(t).includes(FEHLER.lauf_laeuft_schon));
  weg();
});

test('Technik › Online-Suche: „Alle zurücknehmen“ je Lauf: Rückfrage mit der Zahl der Einträge, Befehl 60 mit lauf_id, Ergebnis über das Ereignis (mit „blieben“)', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => {
    m.backend.online.laeufe = [
      { lauf_id: 'l-neu', beginn: '2026-11-19T08:00:00Z', ende: '2026-11-19T09:00:00Z', zustand: 'fertig', zahlen: { erledigt: 50, gesamt: 50, geaendert: 2, vorschlaege: 1, keiner: 0 } },
      { lauf_id: 'l-leer', beginn: '2026-11-18T08:00:00Z', ende: '2026-11-18T09:00:00Z', zustand: 'fertig', zahlen: { erledigt: 50, gesamt: 50, geaendert: 0, vorschlaege: 0, keiner: 3 } },
    ];
    m.backend.serien.s1.art = 'musik'; m.backend.serien.s2.art = 'musik'; m.backend.serien.s2.name = 'Seitdem geändert';
    m.backend.online.aenderungen.push(
      { id: 'a1', serie_id: 's1', lauf_id: 'l-neu', felder: ['art'], vorher: { art: 'hoerspiel' }, nachher: { art: 'musik' }, zeit: '2026-11-19T08:30:00Z', status: 'fertig' },
      { id: 'a2', serie_id: 's2', lauf_id: 'l-neu', felder: ['serie_name'], vorher: { serie_name: 'Bibi Blocksberg' }, nachher: { serie_name: 'Online-Name' }, zeit: '2026-11-19T08:40:00Z', status: 'fertig' },
    );
  } });
  assert.equal(s.qa('[data-alle-zurueck]').length, 1, 'nur der Lauf mit Änderungen');
  await klick(s, s.q('[data-alle-zurueck="l-neu"]'));
  assert.equal(text(s.q('dialog.blatt[open] #blatt-t')), 'Alle zurücknehmen?');
  assert.equal(text(s.q('[data-alle-zurueck-text]')), '2 Einträge gehen auf die alten Werte zurück.');
  await klick(s, blattKnopf(s, TECHNIK.abbrechen));
  assert.equal(aufrufe(s, 'online/zuruecknehmen').length, 0);
  await klick(s, s.q('[data-alle-zurueck="l-neu"]'));
  await klick(s, blattKnopf(s, 'Alle zurücknehmen'), 14);
  assert.deepEqual(aufrufe(s, 'online/zuruecknehmen').map(({ lauf_id, serie_id, aenderung_id }) => ({ lauf_id, serie_id, aenderung_id })), [{ lauf_id: 'l-neu', serie_id: undefined, aenderung_id: undefined }]);
  await warte(60); await s.flush(12);
  assert.ok(toasts(s).includes('Zurückgenommen. 1 Feld blieb, weil es inzwischen geändert wurde.'));
  assert.equal(s.m.backend.serien.s1.art, 'hoerspiel');
  assert.equal(s.m.backend.serien.s2.name, 'Seitdem geändert');
  assert.equal(s.q('[data-rueck-laeuft]'), null, 'die Anzeige „Wird zurückgenommen“ ist weg');
  weg();
});

test('Technik › Online-Suche: lauf_nicht_gefunden bei „Alle zurücknehmen“ mit Klartext; der Stand der Läufe wird neu geholt', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => { m.backend.online.laeufe = [{ lauf_id: 'weg', beginn: '2026-11-19T08:00:00Z', ende: '2026-11-19T09:00:00Z', zustand: 'fertig', zahlen: { erledigt: 5, gesamt: 5, geaendert: 1, vorschlaege: 0, keiner: 0 } }]; m.failNext('tobibox/online/zuruecknehmen', 'lauf_nicht_gefunden'); } });
  await klick(s, s.q('[data-alle-zurueck="weg"]'));
  const status = aufrufe(s, 'online/status').length;
  await klick(s, blattKnopf(s, 'Alle zurücknehmen'), 14);
  assert.ok(toasts(s).includes(FEHLER.lauf_nicht_gefunden));
  assert.ok(aufrufe(s, 'online/status').length > status);
  weg();
});

test('Technik › Online-Suche: das Ereignis `quelle` ändert die Quelle; ein `snapshot` ersetzt den Stand; Fehler beim Laden zeigt die Fehlerkarte', MIT_DOM, async () => {
  const s = await technik();
  s.m.emit('online', 'quelle', { quelle: 'tonies', erreichbar: false });
  await s.flush(4);
  assert.equal(text(s.q('[data-quelle="tonies"]')), 'Tonies antwortet gerade nicht');
  s.m.emit('online', 'snapshot', { lauf: { lauf_id: 'q', zustand: 'laeuft', erledigt: 1, gesamt: 2, geaendert: 0, vorschlaege: 0, keiner: 0 }, quellen: { itunes: { erreichbar: true }, tonies: { erreichbar: true }, tonies_shop: { erreichbar: true }, claude: { eingerichtet: false, erreichbar: false } }, tonie_liste: null, letzte_laeufe: [] });
  await s.flush(4);
  assert.equal(text(s.q('[data-lauf-zustand="laeuft"]')), 'Läuft: 1 von 2.');
  assert.equal(text(s.q('[data-quelle="tonies"]')), 'Tonies erreichbar');
  weg();
  const f = await technik({ vor: (m) => m.failNext('tobibox/online/status', 'unknown_error') });
  assert.ok(f.q('[data-zustand="fehler"]'));
  weg();
});

/* ------------------------------------------------------------------ ohne Fähigkeit / ohne Recht: nichts von der Online-Suche */

test('Ohne Fähigkeit `online_suche` (Administrator): keine Menüpunkte, keine Karte, keine Filter, keine Technik-Zeile, kein Abo, kein Befehl 57 bis 64', MIT_DOM, async () => {
  const s = await oeffne('s1', { faehigkeiten: OHNE, vor: (m) => { VORSCHLAEGE(m); m.backend.serien.s1.folgen[0].beschreibung = 'Kurz.'; } });
  assert.equal(s.q('[data-online-hinweis]'), null);
  assert.equal(s.q('[data-karte="ansehen"]'), null);
  await klick(s, s.q('[data-menue-serie]'));
  assert.equal(s.q('dialog.blatt[open] [data-menue="online"]'), null);
  await klick(s, blattKnopf(s, 'Schließen'));
  await klick(s, s.q('[data-folge="folge-01.mp3"] [data-beschreibung]'));
  assert.equal(text(s.q('[data-beschreibung-text]')), 'Kurz.', 'ein vorhandenes Feld der Folge wird gezeigt, kurz');
  assert.deepEqual(viele(s), [], 'es ging kein Befehl der Online-Suche hinaus');
  assert.ok(!s.m.calls.some((c) => c.abo && (c.msg.themen || []).includes('online')));
  weg();
});

test('Benutzer (kein Administrator): sieht weder Suche noch Vorschläge noch Zurücknehmen noch die Technik-Zeile; die Technik-Adresse bleibt gesperrt; kein Abo `online`', MIT_DOM, async () => {
  const s = await oeffne('s1', { istAdmin: false, vor: (m) => { MIT_ONLINE(m); VORSCHLAEGE(m); } });
  assert.ok(s.q('[data-online-hinweis]'), 'die Zeile ist für alle da');
  assert.equal(s.q('[data-online-zurueck]'), null);
  assert.equal(s.q('[data-karte="ansehen"]'), null);
  assert.deepEqual(viele(s), []);
  assert.ok(!s.m.calls.some((c) => c.abo && (c.msg.themen || []).includes('online')));
  await geheZu(s, '#technik-online');
  assert.ok(s.q('[data-zustand="nur-admin"]'));
  assert.equal(s.q('[data-online-seite]'), null);
  assert.deepEqual(viele(s), []);
  weg();
});

/* ------------------------------------------------------------------ Goldfisch-Review OS4 (GO4-1 bis GO4-12) */

/* Seite der Technik ohne DOM: ein kleiner Kontext, der die Abos zählt. */
function fakeTechnik(extra = {}) {
  const subs = new Set();
  const gemeldet = [];
  const ctx = {
    hass: { config: {} }, grenzeMs: 1000, neuZeichnen() {}, laedt: () => null, fehlerKarte: () => null, melde: (t) => gemeldet.push(t),
    api: async () => ({ quellen: {}, lauf: null, letzte_laeufe: [] }),
    ereignis: (fn) => { subs.add(fn); return () => subs.delete(fn); },
    oeffneBlatt: async (o) => { o.knoepfe[1].fn(); },
    ...extra,
  };
  const technik = { beschaeftigt: null, tu: async (n, f) => { try { await f(); return true; } catch { return false; } } };
  const o = new TO.OnlineSeite(ctx, technik);
  const sende = (art, daten) => { for (const fn of [...subs]) fn({ thema: 'online', art, daten }); };
  return { o, subs, sende, gemeldet };
}

test('GO4-1: Rücknahme mit verpasstem `fertig`: nach Verlassen und Wiederkommen ist „Wird zurückgenommen“ weg und „Alle zurücknehmen“ wieder frei', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => {
    m.backend.online.laeufe = [{ lauf_id: 'l-neu', beginn: '2026-11-19T08:00:00Z', ende: '2026-11-19T09:00:00Z', zustand: 'fertig', zahlen: { erledigt: 5, gesamt: 5, geaendert: 2, vorschlaege: 0, keiner: 0 } }];
    m.on('tobibox/online/zuruecknehmen', () => ({ gestartet: true })); // das Ereignis `fertig` kommt nie an
  } });
  await klick(s, s.q('[data-alle-zurueck="l-neu"]'));
  await klick(s, blattKnopf(s, 'Alle zurücknehmen'), 14);
  assert.ok(s.q('[data-rueck-laeuft]'), 'läuft');
  assert.equal(s.q('[data-alle-zurueck="l-neu"]').disabled, true);
  await geheZu(s, '#technik');
  await geheZu(s, '#technik-online');
  assert.equal(s.q('[data-rueck-laeuft]'), null, 'die Wahrheit liefert Nr. 63');
  assert.equal(s.q('[data-alle-zurueck="l-neu"]').disabled, false);
  weg();
});

test('GO4-1/GO4-4: Technik meldet das Abo beim Verlassen ab und abonniert nur einmal; `fertig` vor der Antwort auf Nr. 60 lässt „Wird zurückgenommen“ nicht hängen', async () => {
  const f = fakeTechnik();
  f.o.betreten(); f.o.betreten();
  assert.equal(f.subs.size, 1, 'nur einmal abonniert');
  await warte(5);
  f.sende('quelle', { quelle: 'itunes', erreichbar: false });
  assert.equal(f.o.z.status.quellen.itunes.erreichbar, false, 'solange man da ist, wirkt das Ereignis');
  f.o.verlassen();
  assert.equal(f.subs.size, 0, 'beim Verlassen abgemeldet');
  f.o.betreten();
  assert.equal(f.subs.size, 1, 'beim Wiederkommen genau ein Abo');
  f.o.verlassen();
  // Reihenfolge: das Ereignis `fertig` kommt vor der Antwort
  const g = fakeTechnik();
  g.o.betreten(); await warte(5);
  g.o.technik.tu = async (n, fn) => { g.sende('stand', { vorgang: 'zuruecknahme', lauf_id: 'l1', zustand: 'laeuft', erledigt: 1, gesamt: 2 }); g.sende('fertig', { vorgang: 'zuruecknahme', lauf_id: 'l1', zustand: 'fertig', uebersprungen_anzahl: 0 }); await fn(); return true; };
  await g.o.alleZuruecknehmen({ lauf_id: 'l1', zahlen: { geaendert: 2 } });
  await warte(5);
  assert.equal(g.o.rueck, null, 'nicht nach dem Ereignis wieder gesetzt');
  assert.deepEqual(g.gemeldet, ['Zurückgenommen.']);
  g.o.verlassen();
});

test('GO4-12: nach dem Ereignis `fertig` zeigt „Lauf“ gleich das Ende dieses Laufs, nicht das des vorigen', async () => {
  const f = fakeTechnik({ api: async () => new Promise(() => {}) }); // Nr. 63 antwortet nicht
  f.o.z = { phase: 'bereit', fehlerCode: null, status: { quellen: {}, lauf: { lauf_id: 'neu', zustand: 'laeuft', erledigt: 1, gesamt: 2 }, letzte_laeufe: [{ lauf_id: 'alt', zustand: 'angehalten', zahlen: {} }] } };
  f.o._beobachten();
  f.sende('fertig', { vorgang: 'lauf', lauf_id: 'neu', zustand: 'fertig', erledigt: 2, gesamt: 2, geaendert: 7, vorschlaege: 1, keiner: 0 });
  const e = f.o.z.status.letzte_laeufe[0];
  assert.equal(e.lauf_id, 'neu');
  assert.match(TO.laufEndeText(e), /^Fertig: 7 Einträge geändert, 1 Vorschläge?, 0 ohne Treffer\.$/);
  assert.equal(f.o.z.status.letzte_laeufe.length, 2);
});

test('GO4-2: Zusammenführen-Vorschlag holt das Ziel beim Tippen frisch (Name und stand); der Dialog nennt den neuen Namen und die Zusammenführung gelingt', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  assert.match(text(s.q('[data-vorschlag="v-zus"] [data-vorschlag-text]')), /Bibi Blocksberg/);
  s.m.backend.serien.s2.name = 'Bibi und Tina'; // inzwischen umbenannt: neuer stand
  const vorher = aufrufe(s, 'serie/get').length;
  await klick(s, s.q('[data-vorschlag="v-zus"] [data-vorschlag-aktion="zusammen"]'), 14);
  assert.ok(aufrufe(s, 'serie/get').length > vorher, 'das Ziel wurde frisch geholt');
  assert.equal(text(s.q('dialog.blatt[open] #blatt-t')), fuellen(SERIE.zusammen.titel, { name: 'Die drei ???', ziel: 'Bibi und Tina' }));
  await klick(s, blattKnopf(s, SERIE.zusammen.knopf), 16);
  const z = aufrufe(s, 'serien/zusammenfuehren');
  assert.equal(z.length, 1);
  assert.equal(toasts(s).includes(FEHLER.stand_veraltet), false, 'kein stand_veraltet');
  weg();
});

test('GO4-3: „Zurücknehmen“ der Serienseite sendet weiter nur serie_id; das Blatt sagt „Alle Änderungen … Zuletzt: …“ und nennt bei einem Feld keine falsche Form', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { MIT_ONLINE(m); m.backend.serien.s1.online = { zeit: '2026-11-18T10:00:00Z', felder: ['cover'] }; } });
  await klick(s, s.q('[data-online-zurueck]'));
  const t = text(s.q('[data-zuruecknehmen-felder]'));
  assert.match(t, /^Alle Änderungen der Online-Suche an diesem Eintrag/);
  assert.match(t, /Zuletzt: Cover\.$/);
  assert.doesNotMatch(t, /gehen/);
  await klick(s, blattKnopf(s, 'Zurücknehmen'), 14);
  assert.deepEqual(aufrufe(s, 'online/zuruecknehmen').map(({ serie_id, aenderung_id, lauf_id }) => [serie_id, aenderung_id, lauf_id]), [['s1', undefined, undefined]]);
  weg();
});

test('GO4-5: ein Vorschaubild, das erst nach dem Schließen ankommt, wird gleich freigegeben; eine neue Suche gibt die Bilder der alten frei', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.serien.s1.cover_stand = 'ab12cd34'; } });
  const erzeugt = []; const frei = [];
  const altC = URL.createObjectURL; const altR = URL.revokeObjectURL;
  URL.createObjectURL = (...a) => { const u = altC(...a); erzeugt.push(u); return u; };
  URL.revokeObjectURL = (u) => frei.push(u);
  const echt = s.m.hass.fetchWithAuth;
  let tor; const offen = new Promise((r) => { tor = r; });
  s.m.hass.fetchWithAuth = async (p, o) => { if (p.includes('/online/vorschau/')) await offen; return echt(p, o); };
  await trefferSuche(s);
  await klick(s, blattKnopf(s, 'Schließen')); // die Bilder sind noch unterwegs
  tor();
  await warte(40);
  assert.equal(erzeugt.length, 2);
  assert.deepEqual([...frei].sort(), [...erzeugt].sort(), 'jede Adresse wurde freigegeben');
  // neue Suche im selben Blatt
  s.m.hass.fetchWithAuth = echt;
  erzeugt.length = 0; frei.length = 0;
  await trefferSuche(s);
  assert.equal(erzeugt.length, 2);
  await klick(s, s.q('[data-os-suchen]'), 14);
  assert.equal(frei.length, 2, 'die Bilder der alten Suche sind frei');
  await klick(s, blattKnopf(s, 'Schließen'));
  await warte(30);
  assert.equal(frei.length, 4);
  URL.createObjectURL = altC; URL.revokeObjectURL = altR;
  weg();
});

test('GO4-4: Doppeltipp auf „Übernehmen“ sendet nur einen Befehl 59; Doppeltipp auf „Nein“ der Karte nur einen Befehl 61', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await bisUebersicht(s);
  const b = blattKnopf(s, 'Übernehmen');
  b.click(); b.click();
  await warte(30); await s.flush(14);
  assert.equal(aufrufe(s, 'online/uebernehmen').length, 1);
  weg();
  const k = await oeffne('s1', { vor: VORSCHLAEGE });
  const nein = k.q('[data-vorschlag="v-apple"] [data-vorschlag-aktion="nein"]');
  nein.click(); nein.click();
  await warte(30); await k.flush(14);
  assert.equal(aufrufe(k, 'online/vorschlag_verwerfen').length, 1);
  weg();
});

test('GO4-6: Rücknahme mit aenderung_nicht_gefunden: Klartext, das Blatt schließt, die Seite lädt neu (der Text verspricht es)', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { MIT_ONLINE(m); m.failNext('tobibox/online/zuruecknehmen', 'aenderung_nicht_gefunden'); } });
  const vorher = aufrufe(s, 'serie/get').length;
  await klick(s, s.q('[data-online-zurueck]'));
  await klick(s, blattKnopf(s, 'Zurücknehmen'), 14);
  assert.ok(toasts(s).includes(FEHLER.aenderung_nicht_gefunden));
  assert.equal(blatt(s), null);
  assert.ok(aufrufe(s, 'serie/get').length > vorher, 'neu geladen');
  weg();
});

test('GO4-7: Übersicht eines Cover-Vorschlags ohne vorschau_id sagt es ausdrücklich; bei einem Treffer mit Bild steht der Hinweis nicht da', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  s.m.on('tobibox/online/treffer', () => ({ felder: { cover: { heute: null, neu: true, sicher: false, hand: false } } })); // ältere Antwort ohne `vorschau_id`
  await klick(s, s.q('[data-vorschlag="v-apple"] [data-vorschlag-aktion="ansehen"]'), 14);
  assert.equal(text(s.q('[data-cover-ohne-bild]')), 'Neues Cover: Das Bild siehst du erst bei „Online suchen“.');
  assert.equal(s.m.vorschauAufrufe.length, 0, 'ohne vorschau_id geht keine Vorschau hinaus');
  weg();
  const t = await oeffne('s1');
  await bisUebersicht(t);
  assert.ok(t.q('[data-feld="cover"] [data-vorschau-neu]'));
  assert.equal(t.q('[data-cover-ohne-bild]'), null);
  weg();
});

test('GO4-8: Beschreibung zweimal schnell getippt, während der volle Text lädt: bleibt zu; ein neuer stand der Serie ersetzt den gemerkten Text', MIT_DOM, async () => {
  let tor; const offen = new Promise((r) => { tor = r; });
  const s = await oeffne('s1', { faehigkeiten: [...ALLE, 'favoriten'], vor: (m) => { MIT_ONLINE(m); m.on('tobibox/online/beschreibung', async () => { await offen; return { beschreibung: LANG, quelle: 'itunes' }; }); } });
  const knopf = () => s.q('[data-folge="folge-02.mp3"] [data-beschreibung]');
  await klick(s, knopf());
  assert.ok(s.q('[data-beschreibung-laedt]'));
  await klick(s, knopf()); // zu
  tor();
  await warte(30); await s.flush(10);
  assert.equal(knopf().getAttribute('aria-expanded'), 'false');
  assert.equal(s.q('[data-folge="folge-02.mp3"] [data-beschreibung-text]'), null, 'bleibt zu');
  await klick(s, knopf());
  assert.equal(text(s.q('[data-folge="folge-02.mp3"] [data-beschreibung-text]')), LANG, 'der Text ist gemerkt');
  s.m.backend.serien.s1.folgen[0].anzeige = 'Anders benannt'; // neuer stand
  s.m.emit('favoriten', 'geaendert', { serie_id: 's1' });
  await warte(30); await s.flush(10);
  assert.notEqual(text(s.q('[data-folge="folge-02.mp3"] [data-beschreibung-text]')), LANG, 'der alte Text bleibt nicht stehen');
  weg();
});

test('GO4-10: sind beide Quellen gestört, steht „Das sind nur Treffer von …“ nirgends; antwortet eine, nur bei der gestörten', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.online.suchTreffer = [{ quelle: 'tonies', titel: 'Einer', hat_cover: false, werte: { art: 'musik' } }]; m.backend.online.quellen = { itunes: 'fehler', tonies: 'pause' }; } });
  await trefferSuche(s);
  assert.equal(text(s.q('[data-quelle-hinweis="itunes"]')), 'Apple antwortet gerade nicht.');
  assert.equal(text(s.q('[data-quelle-hinweis="tonies"]')), 'Tonies braucht eine Pause.');
  assert.ok(!text(s.q('dialog.blatt[open]')).includes('nur Treffer'));
  s.m.backend.online.quellen = { itunes: 'fehler', tonies: 'ok' };
  await klick(s, s.q('[data-os-suchen]'), 14);
  assert.equal(text(s.q('[data-quelle-hinweis="itunes"]')), 'Apple antwortet gerade nicht. Das sind nur Treffer von Tonies.');
  weg();
});

test('GO4-11: der Fokus liegt nach dem Wechsel Suche, Übersicht und zurück auf der Überschrift des Blatts', MIT_DOM, async () => {
  const s = await oeffne('s1');
  const fokus = () => s.el.shadowRoot.activeElement?.id;
  await trefferSuche(s);
  await klick(s, s.qa('[data-treffer]')[0], 14);
  await warte(20);
  assert.equal(fokus(), 'blatt-t', 'Übersicht');
  await klick(s, blattKnopf(s, 'Zurück'));
  await warte(20);
  assert.equal(fokus(), 'blatt-t', 'zurück bei der Suche');
  weg();
});

test('GO4-12: zu kurzer Suchtext bekommt einen Hinweis; ein langer Vorgabename wird auf 100 Zeichen gekürzt gesendet', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await trefferSuche(s);
  tippe(s.q('[data-os-text]'), 'G');
  await klick(s, s.q('[data-os-suchen]'));
  assert.equal(text(s.q('[data-suche-status="kurz"]')), 'Gib mindestens 2 Zeichen ein.');
  assert.equal(aufrufe(s, 'online/suchen').length, 1);
  tippe(s.q('[data-os-text]'), 'Drache'.repeat(30));
  await klick(s, s.q('[data-os-suchen]'), 14);
  assert.equal(aufrufe(s, 'online/suchen').at(-1).text.length, 100);
  assert.equal(s.q('[data-suche-status="kurz"]'), null);
  weg();
});

test('GO4-12: der Treffer sagt Quelle und „früher abgelehnt“ auch im Namen für Screenreader', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await trefferSuche(s);
  const z = s.qa('[data-treffer]');
  assert.match(z[0].getAttribute('aria-label'), /^Die drei \?\?\? \(Apple\) ansehen, .*Apple$/);
  assert.match(z[2].getAttribute('aria-label'), /früher abgelehnt$/);
  weg();
});

test('GO4-12: lange „heute“-Beschreibung ohne lange neue bekommt „mehr“', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.serien.s1.folgen[0].beschreibung_voll = LANG; m.backend.online.suchTreffer = [{ quelle: 'tonies', titel: 'Kurz', hat_cover: false, werte: { 'beschreibung@folge-01.mp3': 'Ganz kurz.' } }]; } });
  await bisUebersicht(s, 'folge-01.mp3');
  assert.ok(s.q('[data-feld-mehr]'));
  weg();
});

test('GO4-12: 404 „Bild noch nicht geladen“ bei der Vorschau: ein zweiter Versuch holt das Bild', MIT_DOM, async () => {
  const alt = O.VORSCHAU.nochmalMs; O.VORSCHAU.nochmalMs = 20;
  const s = await oeffne('s1', { vor: (m) => { m.backend.serien.s1.cover_stand = 'ab12cd34'; } });
  const echt = s.m.hass.fetchWithAuth;
  let n = 0;
  s.m.hass.fetchWithAuth = async (p, o) => { if (p.includes('/online/vorschau/') && n++ === 0) return { ok: false, status: 404, blob: async () => new Blob([]) }; return echt(p, o); };
  await trefferSuche(s);
  await warte(80); await s.flush(8);
  assert.ok(s.qa('[data-treffer] img[data-vorschau]').length >= 2, 'beide Bilder da, auch das erste nach dem zweiten Versuch');
  O.VORSCHAU.nochmalMs = alt;
  weg();
});

test('GO4-12: Knöpfe der Vorschlagskarte sind während einer Änderung grau', MIT_DOM, async () => {
  let tor; const offen = new Promise((r) => { tor = r; });
  const s = await oeffne('s1', { vor: (m) => { VORSCHLAEGE(m); m.on('tobibox/online/vorschlag_verwerfen', async () => { await offen; return {}; }); } });
  await klick(s, s.q('[data-vorschlag="v-apple"] [data-vorschlag-aktion="nein"]'), 6);
  assert.ok(s.qa('[data-vorschlag-aktion]').every((b) => b.disabled), 'alle grau');
  tor();
  await warte(30);
  weg();
});

test('GO4-12: der Filter online_vorschlag zählt und geht nicht hinaus, wenn Administrator oder Fähigkeit fehlen', async () => {
  const B = await import('../../custom_components/tobibox/frontend/seiten/bibliothek.js');
  const e = { ...B.STANDARD(), filter: { ...B.STANDARD().filter, online_vorschlag: true } };
  assert.equal(B.aktiveEinstellungen(e), 1);
  assert.equal(B.aktiveEinstellungen(e, { ohneOnline: true }), 0);
  assert.deepEqual(B.listenAnfrage(e).filter, ['online_vorschlag']);
  assert.equal(B.listenAnfrage(e, 0, { ohneOnline: true }).filter, undefined);
});

test('Einzeltitel und Hörbuch mit Kapiteln: „Online suchen“ an einem Eintrag mit genau einer Folge sendet Nr. 57 mit folge', MIT_DOM, async () => {
  const s = await oeffne('lied', { vor: (m) => { m.backend.serien.lied = { id: 'lied', name: 'Wiegenlied', typ: 'normal', ordner: 'W', pruefen: false, hinweise: [], art: 'musik', einzeln: true, cover_stand: null, folgen: [folge('w.mp3', 'Wiegenlied')] }; } });
  await klick(s, s.q('[data-menue-serie]'));
  await klick(s, s.q('dialog.blatt[open] [data-menue="online"]'), 14);
  assert.deepEqual(aufrufe(s, 'online/suchen').map(({ serie_id, folge: f }) => [serie_id, f]), [['lied', 'w.mp3']]);
  assert.equal(s.q('[data-os-text]').value, 'Wiegenlied');
  weg();
});

test('Serie mit erst einer Folge (nicht einzeln): „Online suchen“ sendet Nr. 57 ohne folge, mit dem Seriennamen; die Folgenfelder werden trotzdem angeboten', MIT_DOM, async () => {
  const s = await oeffne('eine', { vor: (m) => { m.backend.serien.eine = { id: 'eine', name: 'Neue Reihe', typ: 'normal', ordner: 'N', pruefen: false, hinweise: [], art: 'hoerspiel', einzeln: false, cover_stand: null, folgen: [folge('n1.mp3', 'Anfang')] }; m.backend.online.suchTreffer = [{ quelle: 'tonies', titel: 'Neue Reihe', hat_cover: false, werte: { 'alter_ab@n1.mp3': 5 } }]; } });
  await klick(s, s.q('[data-menue-serie]'));
  await klick(s, s.q('dialog.blatt[open] [data-menue="online"]'), 14);
  assert.deepEqual(aufrufe(s, 'online/suchen').map(({ serie_id, folge: f }) => [serie_id, f]), [['eine', undefined]]);
  assert.equal(s.q('[data-os-text]').value, 'Neue Reihe');
  await klick(s, s.qa('[data-treffer]')[0], 14);
  assert.ok(s.q('[data-feld="alter_ab@n1.mp3"]'), 'Alter der einen Folge wird angeboten');
  weg();
});

/* ------------------------------------------------------------------ T10: Bild des Vorschlags über `vorschau_id` (19.11.) */

const hex16 = /^[0-9a-f]{16}$/;
const ansehen = (s) => klick(s, s.q('[data-vorschlag="v-apple"] [data-vorschlag-aktion="ansehen"]'), 14);

test('Mock (T10): Nr. 58 liefert bei einem Vorschlag mit Cover eine neue vorschau_id je Abfrage, sonst keine; sie teilt die 4 Plätze (die älteste wird 410)', async () => {
  const m = createMockHass({ faehigkeiten: ALLE });
  m.backend.online.vorschlaege.s1 = [
    { id: 'v-apple', art: 'felder', quelle: 'itunes', felder: ['cover', 'art'], werte: { cover: true, art: 'musik' }, zeit: '2026-11-18T10:00:00Z' },
    { id: 'v-art', art: 'felder', quelle: 'itunes', felder: ['art'], werte: { art: 'musik' }, zeit: '2026-11-18T10:00:00Z' },
  ];
  const frage = (vorschlag_id) => m.hass.connection.sendMessagePromise({ type: 'tobibox/online/treffer', serie_id: 's1', vorschlag_id });
  const a = await frage('v-apple');
  const b = await frage('v-apple');
  assert.match(a.vorschau_id, hex16);
  assert.notEqual(a.vorschau_id, b.vorschau_id, 'jede Abfrage eine neue Kennung');
  assert.equal((await frage('v-art')).vorschau_id, undefined, 'ohne cover keine vorschau_id');
  assert.equal((await m.hass.fetchWithAuth(`/api/tobibox/online/vorschau/${a.vorschau_id}`)).status, 200);
  for (let i = 0; i < 4; i += 1) await frage('v-apple');
  assert.equal((await m.hass.fetchWithAuth(`/api/tobibox/online/vorschau/${a.vorschau_id}`)).status, 410, 'verdrängt');
  assert.equal((await m.hass.fetchWithAuth(`/api/tobibox/online/vorschau/${b.vorschau_id}`)).status, 410, 'verdrängt');
});

test('T10: Übersicht eines Vorschlags mit Cover zeigt das neue Bild (Nr. 58 → vorschau_id → HTTP-Vorschau mit fetchWithAuth als blob:), ohne den Platzhalter-Satz; beim Schließen wird die Adresse freigegeben', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  const frei = []; const altR = URL.revokeObjectURL;
  URL.revokeObjectURL = (u) => frei.push(u);
  await ansehen(s);
  await warte(30); await s.flush(8);
  const img = s.q('[data-feld="cover"] img[data-vorschau-neu]');
  assert.ok(img, 'das neue Bild steht da');
  assert.match(img.getAttribute('src'), /^blob:/);
  assert.equal(s.q('[data-cover-ohne-bild]'), null, 'kein Platzhalter-Satz');
  assert.equal(s.q('[data-vorschau-neu-ohne]'), null);
  assert.equal(s.m.vorschauAufrufe.length, 1);
  const id = s.m.vorschauAufrufe[0].split('/vorschau/')[1];
  assert.match(id, hex16);
  assert.ok(s.m.backend.online.treffer[id], 'die Kennung ist die aus Nr. 58');
  await klick(s, blattKnopf(s, 'Abbrechen'));
  await warte(20);
  assert.deepEqual(frei, [img.getAttribute('src')], 'die blob:-Adresse ist freigegeben');
  URL.revokeObjectURL = altR;
  weg();
});

test('T10: während das Bild lädt, steht der Satz „Das Bild siehst du erst …“ noch nicht da; „Zurück“ zum Vorschlag und noch einmal Ansehen holt eine neue vorschau_id', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  const echt = s.m.hass.fetchWithAuth;
  let tor; const offen = new Promise((r) => { tor = r; });
  s.m.hass.fetchWithAuth = async (p, o) => { if (p.includes('/online/vorschau/')) await offen; return echt(p, o); };
  await ansehen(s);
  assert.ok(s.q('[data-feld="cover"]'));
  assert.equal(s.q('[data-cover-ohne-bild]'), null, 'noch kein Satz, solange das Bild kommt');
  assert.ok(s.q('[data-vorschau-neu-ohne]'), 'der Platzhalter ohne Satz');
  tor();
  await warte(30); await s.flush(8);
  assert.ok(s.q('[data-feld="cover"] img[data-vorschau-neu]'));
  await klick(s, blattKnopf(s, 'Abbrechen'));
  await ansehen(s);
  await warte(30);
  assert.equal(s.m.vorschauAufrufe.length, 2);
  assert.notEqual(s.m.vorschauAufrufe[0], s.m.vorschauAufrufe[1], 'jede Abfrage eine neue Kennung');
  weg();
});

test('T10: 410 (verdrängt oder abgelaufen) und Netzfehler der Vorschau: wieder der beschriftete Platzhalter, die Übersicht bleibt benutzbar', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: VORSCHLAEGE });
  const echt = s.m.hass.fetchWithAuth;
  s.m.hass.fetchWithAuth = async (p, o) => {
    if (p.includes('/online/vorschau/')) { const id = p.split('/vorschau/')[1]; if (s.m.backend.online.treffer[id]) s.m.backend.online.treffer[id].abgelaufen = true; }
    return echt(p, o);
  };
  await ansehen(s);
  await warte(30); await s.flush(8);
  assert.equal(s.q('[data-feld="cover"] img[data-vorschau-neu]'), null);
  assert.ok(s.q('[data-feld="cover"] [data-vorschau-neu-ohne]'));
  assert.equal(text(s.q('[data-cover-ohne-bild]')), 'Das Bild ist nicht mehr da. Öffne den Vorschlag noch einmal.'); // GT-6: das Bild gibt es, nur die Vorschau nicht
  assert.equal(s.m.vorschauAufrufe.length, 1, '410 wird nicht wiederholt');
  assert.ok(s.q('[data-feld="cover"][aria-checked="true"]'), 'das Feld bleibt wählbar');
  await klick(s, blattKnopf(s, 'Abbrechen'));
  s.m.hass.fetchWithAuth = async (p, o) => { if (p.includes('/online/vorschau/')) throw new Error('Netz weg'); return echt(p, o); };
  await ansehen(s);
  await warte(30); await s.flush(8);
  assert.equal(text(s.q('[data-cover-ohne-bild]')), 'Das Bild ist nicht mehr da. Öffne den Vorschlag noch einmal.', 'auch bei einem Netzfehler der Platzhalter mit Satz');
  weg();
});

test('T10: Vorschlag ohne Cover im Angebot (nur Art) holt keine Vorschau; Treffer verhalten sich wie bisher', MIT_DOM, async () => {
  const s = await oeffne('s1', { vor: (m) => { m.backend.online.vorschlaege.s1 = [{ id: 'v-art', art: 'felder', quelle: 'itunes', felder: ['art'], werte: { art: 'musik' }, zeit: '2026-11-18T10:00:00Z' }]; } });
  await klick(s, s.q('[data-vorschlag="v-art"] [data-vorschlag-aktion="ansehen"]'), 14);
  await warte(30);
  assert.deepEqual(s.qa('[data-feld]').map((b) => b.dataset.feld), ['art']);
  assert.equal(s.m.vorschauAufrufe.length, 0);
  weg();
});

/* ------------------------------------------------------------------ T11: Liste der Änderungen je Lauf (Nr. 65, Fähigkeit `online_lauf_liste`) */

const LAUF = { lauf_id: 'l-neu', beginn: '2026-11-19T08:00:00Z', ende: '2026-11-19T09:00:00Z', zustand: 'fertig', zahlen: { erledigt: 50, gesamt: 50, geaendert: 3, vorschlaege: 1, keiner: 0 } };
const LISTE_VOR = (m) => {
  const o = m.backend.online;
  o.laeufe = [LAUF, { lauf_id: 'l-leer', beginn: '2026-11-18T08:00:00Z', ende: '2026-11-18T09:00:00Z', zustand: 'fertig', zahlen: { erledigt: 50, gesamt: 50, geaendert: 0, vorschlaege: 0, keiner: 3 } }];
  m.backend.serien.s1.art = 'musik'; m.backend.serien.s2.name = 'Online-Name'; m.backend.serien.s3.art = 'musik';
  o.aenderungen.push(
    { id: 'a1', serie_id: 's1', lauf_id: 'l-neu', felder: ['art', 'cover', 'nummer@folge-01.mp3'], vorher: { art: 'hoerspiel' }, nachher: { art: 'musik' }, zeit: '2026-11-19T08:30:00Z', status: 'fertig' },
    { id: 'a2', serie_id: 's2', lauf_id: 'l-neu', felder: ['serie_name'], vorher: { serie_name: 'Bibi Blocksberg' }, nachher: { serie_name: 'Online-Name' }, zeit: '2026-11-19T08:40:00Z', status: 'fertig' },
    { id: 'a3', serie_id: 's3', lauf_id: 'l-neu', felder: ['art'], vorher: { art: 'hoerspiel' }, nachher: { art: 'musik' }, zeit: '2026-11-19T08:50:00Z', status: 'zurueckgenommen' },
    { id: 'ax', serie_id: 's1', lauf_id: 'l-anders', felder: ['art'], vorher: {}, nachher: {}, zeit: '2026-11-18T08:50:00Z', status: 'fertig' },
  );
};
const auf = async (s, id = 'l-neu') => { await klick(s, s.q(`[data-liste-auf="${id}"]`), 14); await warte(20); await s.flush(8); };
const eintrag = (s, id) => s.q(`[data-eintrag="${id}"]`);

test('Mock (T11): Nr. 65 liefert die Änderungen des Laufs nach Namen, mit Status fertig/zurückgenommen, `weitere` über der Grenze; lauf_nicht_gefunden; ohne Fähigkeit unknown_command', async () => {
  const m = createMockHass({ faehigkeiten: ALLE, onlineListeMax: 2 });
  LISTE_VOR(m);
  const frage = (lauf_id) => m.hass.connection.sendMessagePromise({ type: 'tobibox/online/lauf_aenderungen', lauf_id });
  const r = await frage('l-neu');
  assert.equal(r.eintraege.length, 2, 'höchstens listeMax Einträge');
  assert.equal(r.weitere, true);
  const m2 = createMockHass({ faehigkeiten: ALLE });
  LISTE_VOR(m2);
  const r2 = await m2.hass.connection.sendMessagePromise({ type: 'tobibox/online/lauf_aenderungen', lauf_id: 'l-neu' });
  assert.equal(r2.weitere, false);
  assert.deepEqual(r2.eintraege.map((e) => e.name), [...r2.eintraege.map((e) => e.name)].sort((a, b) => a.localeCompare(b, 'de')));
  assert.deepEqual(r2.eintraege.map((e) => e.aenderung_id).sort(), ['a1', 'a2', 'a3']);
  assert.deepEqual(Object.keys(r2.eintraege[0]).sort(), ['aenderung_id', 'felder', 'name', 'serie_id', 'status', 'zeit']);
  assert.deepEqual(r2.eintraege.find((e) => e.aenderung_id === 'a3').status, 'zurueckgenommen');
  await assert.rejects(m2.hass.connection.sendMessagePromise({ type: 'tobibox/online/lauf_aenderungen', lauf_id: 'gibtsnicht' }), (e) => e.code === 'lauf_nicht_gefunden');
  await assert.rejects(m2.hass.connection.sendMessagePromise({ type: 'tobibox/online/lauf_aenderungen' }), (e) => e.code === 'invalid_format');
  const ohne = createMockHass({ faehigkeiten: ALLE.filter((f) => f !== 'online_lauf_liste') });
  await assert.rejects(ohne.hass.connection.sendMessagePromise({ type: 'tobibox/online/lauf_aenderungen', lauf_id: 'l-neu' }), (e) => e.code === 'unknown_command');
});

test('T11: „Liste der Änderungen“ je Lauf mit Änderungen (nicht bei geaendert 0): aufklappen holt Nr. 65 mit lauf_id; Name als Link, Felder in Klartext, Status; Zurücknehmen nur bei „Geändert“; zuklappen', MIT_DOM, async () => {
  const s = await technik({ vor: LISTE_VOR });
  assert.deepEqual(s.qa('[data-liste-auf]').map((b) => b.dataset.listeAuf), ['l-neu'], 'nur der Lauf mit Änderungen');
  assert.equal(aufrufe(s, 'online/lauf_aenderungen').length, 0, 'erst beim Aufklappen');
  assert.equal(text(s.q('[data-liste-auf]')), 'Liste der Änderungen');
  assert.equal(s.q('[data-liste-auf]').getAttribute('aria-expanded'), 'false');
  assert.match(s.q('[data-liste-auf]').getAttribute('aria-label'), /^Liste der Änderungen des Laufs von /);
  await auf(s);
  assert.deepEqual(aufrufe(s, 'online/lauf_aenderungen').map((m) => m.lauf_id), ['l-neu']);
  assert.equal(s.q('[data-liste-auf]').getAttribute('aria-expanded'), 'true');
  const namen = s.qa('[data-eintrag] [data-eintrag-serie]').map(text);
  assert.deepEqual(namen, [...namen].sort((a, b) => a.localeCompare(b, 'de')), 'nach Namen sortiert');
  assert.equal(namen.length, 3);
  const e1 = eintrag(s, 'a1');
  assert.equal(text(e1.querySelector('[data-eintrag-serie]')), 'Die drei ???');
  assert.equal(e1.querySelector('[data-eintrag-serie]').getAttribute('href'), '#serie-s1');
  assert.equal(text(e1.querySelector('[data-eintrag-felder]')), 'Art, Cover und Nummer');
  assert.equal(text(e1.querySelector('[data-eintrag-status]')), 'Geändert');
  assert.equal(text(e1.querySelector('[data-eintrag-zurueck]')), 'Zurücknehmen');
  assert.equal(e1.querySelector('[data-eintrag-zurueck]').getAttribute('aria-label'), 'Die drei ???: Art, Cover und Nummer zurücknehmen');
  const e3 = eintrag(s, 'a3');
  assert.equal(text(e3.querySelector('[data-eintrag-status]')), 'Zurückgenommen');
  assert.equal(e3.querySelector('[data-eintrag-zurueck]'), null, 'schon zurückgenommen: kein Knopf');
  assert.equal(s.q('[data-liste-weitere]'), null);
  assert.ok(s.q('[data-alle-zurueck="l-neu"]'), '„Alle zurücknehmen“ bleibt');
  assert.ok(!text(s.q('[data-online-seite]')).includes('undefined'));
  await klick(s, s.q('[data-liste-auf="l-neu"]'));
  assert.equal(s.q('[data-liste-aenderungen]'), null, 'zugeklappt');
  assert.equal(s.q('[data-liste-auf]').getAttribute('aria-expanded'), 'false');
  weg();
});

test('T11: „Zurücknehmen“ eines Eintrags: Nr. 60 mit serie_id und aenderung_id (nie lauf_id), Meldung, der Eintrag steht als „Zurückgenommen“, die anderen bleiben', MIT_DOM, async () => {
  const s = await technik({ vor: LISTE_VOR });
  await auf(s);
  await klick(s, s.q('[data-eintrag="a1"] [data-eintrag-zurueck]'), 14);
  await warte(20); await s.flush(8);
  assert.deepEqual(aufrufe(s, 'online/zuruecknehmen').map(({ serie_id, aenderung_id, lauf_id }) => ({ serie_id, aenderung_id, lauf_id })), [{ serie_id: 's1', aenderung_id: 'a1', lauf_id: undefined }]);
  assert.ok(toasts(s).includes('Zurückgenommen.') || toasts(s).some((t) => t.startsWith('Zurückgenommen')), `Meldung: ${toasts(s)}`);
  assert.equal(s.m.backend.serien.s1.art, 'hoerspiel');
  assert.equal(text(eintrag(s, 'a1').querySelector('[data-eintrag-status]')), 'Zurückgenommen');
  assert.equal(eintrag(s, 'a1').querySelector('[data-eintrag-zurueck]'), null);
  assert.ok(eintrag(s, 'a2').querySelector('[data-eintrag-zurueck]'), 'der andere Eintrag bleibt zurücknehmbar');
  assert.equal(s.m.backend.serien.s2.name, 'Online-Name');
  assert.ok(aufrufe(s, 'online/lauf_aenderungen').length >= 2, 'die Liste wird danach frisch geholt');
  weg();
});

test('T11: Rücknahme eines Eintrags, dessen Feld inzwischen geändert wurde: „1 Feld blieb …“, ganz übersprungen bleibt der Eintrag „Geändert“ (wie das Backend), kein Flackern', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => { LISTE_VOR(m); m.backend.serien.s2.name = 'Von Hand umbenannt'; } }); // seit der Online-Änderung von Hand geändert
  await auf(s);
  await klick(s, s.q('[data-eintrag="a2"] [data-eintrag-zurueck]'), 14);
  await warte(20); await s.flush(8);
  assert.ok(toasts(s).includes('Zurückgenommen. 1 Feld blieb, weil es inzwischen geändert wurde.'), `Meldung: ${toasts(s)}`);
  assert.equal(s.m.backend.serien.s2.name, 'Von Hand umbenannt', 'der neue Wert bleibt');
  assert.equal(text(eintrag(s, 'a2').querySelector('[data-eintrag-status]')), 'Geändert');
  assert.ok(eintrag(s, 'a2').querySelector('[data-eintrag-zurueck]'), 'der Knopf bleibt');
  weg();
});

test('T11: Doppeltipp auf „Zurücknehmen“ eines Eintrags sendet nur einen Befehl 60; während es läuft sind die anderen Knöpfe grau', MIT_DOM, async () => {
  const s = await technik({ vor: LISTE_VOR });
  await auf(s);
  const echt = s.m.hass.connection.sendMessagePromise;
  let tor; const offen = new Promise((r) => { tor = r; });
  s.m.hass.connection.sendMessagePromise = async (msg) => { if (msg.type === 'tobibox/online/zuruecknehmen') await offen; return echt(msg); };
  const k = s.q('[data-eintrag="a1"] [data-eintrag-zurueck]');
  k.click(); k.click();
  await warte(10); await s.flush(8);
  assert.ok(s.q('[data-eintrag="a2"] [data-eintrag-zurueck]').disabled, 'die anderen Knöpfe sind grau');
  assert.ok(s.q('[data-alle-zurueck="l-neu"]').disabled);
  tor();
  await warte(40); await s.flush(10);
  assert.equal(aufrufe(s, 'online/zuruecknehmen').length, 1);
  weg();
});

test('T11: Einzel-Rücknahme scheitert (aenderung_nicht_gefunden): Klartext, die Liste und die Läufe werden neu geholt', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => { LISTE_VOR(m); m.failNext('tobibox/online/zuruecknehmen', 'aenderung_nicht_gefunden'); } });
  await auf(s);
  const liste = aufrufe(s, 'online/lauf_aenderungen').length; const status = aufrufe(s, 'online/status').length;
  await klick(s, s.q('[data-eintrag="a1"] [data-eintrag-zurueck]'), 14);
  await warte(20); await s.flush(8);
  assert.ok(toasts(s).includes(FEHLER.aenderung_nicht_gefunden));
  assert.ok(aufrufe(s, 'online/lauf_aenderungen').length > liste);
  assert.ok(aufrufe(s, 'online/status').length > status);
  assert.equal(text(eintrag(s, 'a1').querySelector('[data-eintrag-status]')), 'Geändert', 'nichts vorgetäuscht');
  weg();
});

test('T11: `weitere`: der Hinweis „Es gibt mehr als 500 Änderungen; …“ steht unter der Liste, sonst nicht', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => { LISTE_VOR(m); m.backend.online.listeMax = 2; } });
  await auf(s);
  assert.equal(s.qa('[data-eintrag]').length, 2);
  assert.equal(text(s.q('[data-liste-weitere]')), 'Es gibt mehr als 500 Änderungen; hier stehen die ersten 500, nach Namen sortiert. Mit „Alle zurücknehmen“ gehen alle zurück.');
  weg();
});

test('T11: Fehler beim Holen der Liste zeigt die Fehlerkarte mit „Noch einmal versuchen“; lauf_nicht_gefunden schließt die Liste, meldet es und holt die Läufe neu', MIT_DOM, async () => {
  const s = await technik({ vor: (m) => { LISTE_VOR(m); m.failNext('tobibox/online/lauf_aenderungen', 'unknown_error'); } });
  await auf(s);
  assert.ok(s.q('[data-liste-aenderungen] .fehlerkarte, [data-liste-aenderungen] [data-fehler], [data-liste-aenderungen] button'), 'Fehlerkarte');
  assert.equal(s.q('[data-eintrag]'), null);
  const nochmal = s.qa('[data-liste-aenderungen] button').find((b) => /noch einmal/i.test(text(b)));
  await klick(s, nochmal, 14);
  await warte(20); await s.flush(8);
  assert.equal(s.qa('[data-eintrag]').length, 3, 'beim zweiten Versuch ist die Liste da');
  await klick(s, s.q('[data-liste-auf="l-neu"]'));
  s.m.failNext('tobibox/online/lauf_aenderungen', 'lauf_nicht_gefunden');
  const status = aufrufe(s, 'online/status').length;
  await auf(s);
  assert.equal(s.q('[data-liste-aenderungen]'), null, 'die Liste ist zu');
  assert.ok(toasts(s).includes(FEHLER.lauf_nicht_gefunden));
  assert.ok(aufrufe(s, 'online/status').length > status);
  weg();
});

test('T11: ohne Fähigkeit `online_lauf_liste` bleibt es wie bisher: Zahlen und „Alle zurücknehmen“, kein Aufklappen, kein Befehl 65', MIT_DOM, async () => {
  const s = await technik({ faehigkeiten: ALLE.filter((f) => f !== 'online_lauf_liste'), vor: LISTE_VOR });
  assert.equal(s.qa('[data-liste-auf]').length, 0);
  assert.equal(s.qa('[data-alle-zurueck]').length, 1);
  assert.ok(text(s.q('[data-lauf="l-neu"]')).includes('Fertig: 3 Einträge geändert'));
  assert.deepEqual(viele(s, ['tobibox/online/lauf_aenderungen']), []);
  weg();
  const o = await technik({ faehigkeiten: OHNE, vor: LISTE_VOR });
  assert.equal(o.q('[data-online-seite]'), null, 'ohne online_suche gibt es die Seite gar nicht');
  assert.deepEqual(viele(o), []);
  weg();
});

test('T11: nur für Administratoren: ein Benutzer sieht die Seite nicht und schickt keinen Befehl 65', MIT_DOM, async () => {
  const s = await technik({ istAdmin: false, vor: LISTE_VOR });
  assert.ok(s.q('[data-zustand="nur-admin"]'));
  assert.equal(s.q('[data-liste-auf]'), null);
  assert.deepEqual(viele(s), []);
  weg();
});

test('T11: „Alle zurücknehmen“ bei offener Liste: nach dem Ereignis `fertig` stehen die Einträge als „Zurückgenommen“ da', MIT_DOM, async () => {
  const s = await technik({ vor: LISTE_VOR });
  await auf(s);
  await klick(s, s.q('[data-alle-zurueck="l-neu"]'));
  await klick(s, blattKnopf(s, 'Alle zurücknehmen'), 14);
  await warte(80); await s.flush(12);
  assert.deepEqual(s.qa('[data-eintrag] [data-eintrag-status]').map(text), ['Zurückgenommen', 'Zurückgenommen', 'Zurückgenommen']);
  assert.equal(s.qa('[data-eintrag-zurueck]').length, 0);
  weg();
});

test('T11: beim Verlassen und Wiederkommen ist die Liste zu', MIT_DOM, async () => {
  const s = await technik({ vor: LISTE_VOR });
  await auf(s);
  assert.ok(s.q('[data-liste-aenderungen]'));
  await geheZu(s, '#technik');
  await geheZu(s, '#technik-online');
  assert.equal(s.q('[data-liste-aenderungen]'), null);
  assert.equal(s.q('[data-liste-auf]').getAttribute('aria-expanded'), 'false');
  weg();
});

test('GT-2/GT-3/GT-4 (Mock): Nr. 65 lässt Änderungen ohne Felder weg; Vorschau-Kennungen und Suchen haben getrennte Plätze (je 4), eine Suche zählt als ein Platz', async () => {
  const m = createMockHass({ faehigkeiten: ALLE });
  LISTE_VOR(m);
  m.backend.online.aenderungen.push({ id: 'a9', serie_id: 's2', lauf_id: 'l-neu', felder: [], vorher: {}, nachher: {}, zeit: '2026-11-19T08:55:00Z', status: 'fertig' });
  const send = (msg) => m.hass.connection.sendMessagePromise(msg);
  const r = await send({ type: 'tobibox/online/lauf_aenderungen', lauf_id: 'l-neu' });
  assert.ok(!r.eintraege.some((e) => e.aenderung_id === 'a9'));
  m.backend.online.vorschlaege.s1 = [{ id: 'v1', art: 'felder', quelle: 'itunes', felder: ['cover'], zeit: '2026-11-18T10:00:00Z' }];
  const such = await send({ type: 'tobibox/online/suchen', serie_id: 's1' });
  const vids = [];
  for (let i = 0; i < 6; i++) vids.push((await send({ type: 'tobibox/online/treffer', serie_id: 's1', vorschlag_id: 'v1' })).vorschau_id);
  assert.ok(m.backend.online.treffer[vids[0]].abgelaufen && m.backend.online.treffer[vids[1]].abgelaufen && !m.backend.online.treffer[vids[2]].abgelaufen);
  assert.ok(such.treffer.every((t) => !m.backend.online.treffer[t.treffer_id].abgelaufen), 'Vorschauen verdrängen keine Suche');
  for (let i = 0; i < 5; i++) await send({ type: 'tobibox/online/suchen', serie_id: 's1' });
  assert.ok(such.treffer.every((t) => m.backend.online.treffer[t.treffer_id].abgelaufen), 'die erste Suche ist nach fünf weiteren weg');
  assert.ok(!m.backend.online.treffer[vids[5]].abgelaufen, 'Suchen verdrängen keine Vorschau');
  await assert.rejects(send({ type: 'tobibox/online/treffer', treffer_id: vids[5] }), (e) => e.code === 'treffer_abgelaufen'); // eine vorschau_id ist kein Treffer
});

test('GT-7: `aria-controls` des Knopfs „Änderungen“ zeigt nur bei offener Liste auf deren Element', MIT_DOM, async () => {
  const s = await technik({ vor: LISTE_VOR });
  const knopf = () => s.q('[data-liste-auf="l-neu"]');
  assert.equal(knopf().getAttribute('aria-controls'), null, 'zu: kein Verweis ins Leere');
  await auf(s);
  const id = knopf().getAttribute('aria-controls');
  assert.ok(id && s.q(`#${id}`), 'offen: das Element ist da');
  weg();
});

test('GT-5: eine späte Antwort einer zugeklappten Liste überschreibt die neu geholte nicht (Zähler je Seite)', MIT_DOM, async () => {
  const s = await technik({ vor: LISTE_VOR });
  const echt = s.m.hass.connection.sendMessagePromise;
  let tor; const offen = new Promise((r) => { tor = r; });
  let erste = true;
  s.m.hass.connection.sendMessagePromise = async (msg) => {
    if (msg.type === 'tobibox/online/lauf_aenderungen' && erste) { erste = false; await offen; return { eintraege: [], weitere: false }; } // alt und leer
    return echt(msg);
  };
  await klick(s, s.q('[data-liste-auf="l-neu"]'), 14); // Anfrage A hängt
  await klick(s, s.q('[data-liste-auf="l-neu"]'), 14); // zu
  await klick(s, s.q('[data-liste-auf="l-neu"]'), 14); // wieder auf: Anfrage B
  await warte(20); await s.flush(8);
  assert.equal(s.qa('[data-eintrag]').length, 3);
  tor(); await warte(20); await s.flush(8);
  assert.equal(s.qa('[data-eintrag]').length, 3, 'Antwort A wird verworfen');
  weg();
});

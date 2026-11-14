/* Tests der Serienseite (AP A8, Design 5.3, 5.9, 10). Aufruf: node --test homeassistant/tests/frontend
 *
 * Backend aus mock-hass.mjs: s1 „Die drei ???“ (3 Folgen, ein Tobie „Anna“ auf der Serie, ein Tobie ohne Namen auf der zweiten Folge),
 * s2 „Bibi Blocksberg“ (bitte ansehen), s3 „Überraschung“. Dazu je Test Beispiele: lange Serie, Einzeltitel, Hörbuch, leere Serie.
 * Geprüft: Kopf, Folgenliste, Einzeltitel, Umbenennen, Art, Verschieben, Papierkorb mit Rückfrage, Admin-Menüpunkte, „Das ist richtig“,
 * Fehlerfälle (stand_veraltet, tobies_betroffen, nicht gefunden).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, tippe, taste, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN } from './mock-hass.mjs';

const { tobiesDerSerie, tobiesSatz, gruendeTexte, brauchtPruefung, folgenMeta, folgenMetaTeile, serienFortschritt, SICHTBAR } = await import('../../custom_components/tobibox/frontend/seiten/serie.js');
const { SERIE, GRUENDE, FEHLER } = await import('../../custom_components/tobibox/frontend/texte.js');

const folge = (name, anzeige, extra = {}) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * 1048576, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });

/* Beispiele zusätzlich zum Grundbestand des Mocks. */
function beispiele(m) {
  const b = m.backend.serien;
  b.lang = { id: 'lang', name: 'Lange Serie', typ: 'normal', ordner: 'Lange', pruefen: false, hinweise: [], art: 'hoerspiel', dauer_s: 45 * 1500, cover_stand: null,
    folgen: Array.from({ length: 45 }, (_, i) => folge(`f${String(i + 1).padStart(2, '0')}.mp3`, `Folge ${i + 1}`, { nummer: i + 1 })) };
  b.lied = { id: 'lied', name: 'Wiegenlied', typ: 'normal', ordner: 'Wiegenlied', pruefen: false, hinweise: [], art: 'musik', einzeln: true, dauer_s: 66, cover_stand: null, folgen: [folge('wiegenlied.mp3', 'Wiegenlied')] };
  b.buch = { id: 'buch', name: 'Das große Buch', typ: 'normal', ordner: 'Buch', pruefen: false, hinweise: [], art: 'hoerbuch', dauer_s: 34800, kapitel_anzahl: 14, cover_stand: null,
    folgen: [folge('buch', 'Das große Buch', { art: 'ordner', tracks: 14, dauer_s: 34800 })] };
  b.leer = { id: 'leer', name: 'Leere Sammlung', typ: 'normal', ordner: 'Leer', pruefen: false, hinweise: [], art: 'hoerspiel', folgen: [] };
  b.s1.cover_stand = 'ab12cd34';
}

async function oeffne(id = 's1', opts = {}) {
  const s = await seite({ hash: '', ...opts });
  beispiele(s.m);
  await geheZu(s, `#serie-${id}`);
  await s.flush(10);
  return s;
}

const hash = () => window.location.hash;
const blatt = (s) => s.q('dialog.blatt[open]');
const blattText = (s) => (blatt(s)?.textContent || '').replace(/\s+/g, ' ').trim();
const titelBlatt = (s) => s.q('dialog.blatt[open] #blatt-t')?.textContent.trim();
const punkt = (s, id) => s.q(`dialog.blatt[open] [data-menue="${id}"]`);
const punkte = (s) => s.qa('dialog.blatt[open] [data-menue]').map((x) => x.dataset.menue);
const leisteKnopf = (s, text) => s.qa('dialog.blatt[open] .knoepfe button').find((b) => b.textContent.trim() === text);
const toasts = (s) => s.qa('.toast .tmsg').map((x) => x.textContent);
const namen = (s) => s.qa('[data-folge] .nm').map((x) => x.textContent);
const klick = async (s, el) => { assert.ok(el, 'Element zum Klicken fehlt'); el.click(); await s.flush(10); };
const menue = (s) => klick(s, s.q('[data-menue-serie]'));
const folgeMenue = (s, name) => klick(s, s.q(`[data-folge="${name}"] [data-menue-folge]`));
const aufrufe = (s, typ) => s.m.aufrufe(`tobibox/${typ}`);
const ohneId = ({ id, type, ...rest }) => rest; // eslint-disable-line no-unused-vars
const standVon = async (s, id) => (await s.m.hass.connection.sendMessagePromise({ type: 'tobibox/serie/get', serie_id: id })).stand;

/* ------------------------------------------------------------------ reine Funktionen */

test('tobiesDerSerie und tobiesSatz: Serie und Folgen ohne Doppelte, Namen, Einzahl und Mehrzahl', () => {
  const s = { zuordnungen: [{ uid: 'A', name: 'Anna' }], folgen: [{ tobies: [{ uid: 'B', name: null }] }, { tobies: [{ uid: 'B', name: null }, { uid: 'A', name: 'Anna' }] }] };
  assert.deepEqual(tobiesDerSerie(s).map((t) => t.uid), ['A', 'B']);
  assert.deepEqual(tobiesDerSerie({}), []);
  assert.equal(tobiesSatz(SERIE.papierkorb.tobies, tobiesDerSerie(s)), '2 Tobies spielen dann nichts mehr: Anna, Tobie ohne Namen.');
  assert.equal(tobiesSatz(SERIE.papierkorb.tobies, [{ uid: 'A', name: 'Anna' }]), '1 Tobie spielt dann nichts mehr: Anna.');
  assert.equal(tobiesSatz(SERIE.papierkorb.tobies, []), '');
});

test('gruendeTexte und brauchtPruefung: Gründe aus Serie und Folgen, ohne Doppelte; ohne bekannten Grund der Rückfall', () => {
  const s = { pruefen: false, folgen: [{ pruefen: true, pruefen_gruende: ['tags_fehlen', 'nummer_doppelt'] }, { pruefen: true, pruefen_gruende: ['tags_fehlen'] }] };
  assert.equal(brauchtPruefung(s), true, 'auch nur eine Folge reicht');
  assert.deepEqual(gruendeTexte(s), [GRUENDE.tags_fehlen, GRUENDE.nummer_doppelt]);
  assert.deepEqual(gruendeTexte({ pruefen: true, folgen: [] }), [SERIE.ansehen.grund_sonst]);
  assert.deepEqual(gruendeTexte({ pruefen_gruende: ['gibt_es_nicht'], folgen: [] }), [SERIE.ansehen.grund_sonst]);
  assert.equal(brauchtPruefung({ pruefen: false, folgen: [{ pruefen: false }] }), false);
});

test('folgenMeta und serienFortschritt: nur, was das Backend kennt', () => {
  assert.equal(folgenMeta({}), '');
  assert.equal(folgenMeta({ dauer_s: 139 }), '2:19');
  assert.equal(folgenMeta({ dauer_s: 34800, art: 'ordner', tracks: 14 }), '9:40:00 · 14 Kapitel');
  assert.equal(folgenMeta({ art: 'ordner', tracks: 1 }), '', 'ein Track sind keine Kapitel');
  assert.equal(folgenMeta({ dauer_s: 60, kapitel: [{}, {}, {}] }), '1:00 · 3 Kapitel', 'die Kapitelliste geht vor');
  assert.equal(serienFortschritt({}), null);
  assert.equal(serienFortschritt({ hoerstelle: { anteil: 0, rest_s: 100 } }), null);
  assert.equal(serienFortschritt({ hoerstelle: { anteil: 0.18, rest_s: 1260 } }), 'Schon 18 % gehört · noch 21 Min.');
  assert.equal(serienFortschritt({ hoerstelle: { anteil: 1, rest_s: 0 } }), 'Fertig gehört');
  assert.equal(SICHTBAR, 20);
});

/* ------------------------------------------------------------------ Kopf */

test('Kopf: „‹ Bibliothek“, Menü, großes Cover, Titel und Untertitel; serie/get mit der Kennung; kein Player, keine Karte „Gespielt von“', MIT_DOM, async () => {
  const s = await oeffne('s1');
  assert.deepEqual(aufrufe(s, 'serie/get').map(ohneId).at(-1), { serie_id: 's1' });
  const zurueck = s.q('a[data-zurueck]');
  assert.equal(zurueck.textContent, '‹ Bibliothek');
  assert.equal(zurueck.getAttribute('href'), '#bibliothek');
  assert.equal(s.q('main h2').textContent, 'Die drei ???');
  assert.equal(s.q('[data-untertitel]').textContent, 'Hörspiel · 3 Folgen');
  const mehr = s.q('[data-menue-serie]');
  assert.equal(mehr.getAttribute('aria-label'), 'Mehr zu Die drei ???');
  assert.equal(mehr.getAttribute('aria-haspopup'), 'dialog');
  assert.ok(s.q('.cover.se-xl'), 'großes Cover');
  assert.equal(s.q('[data-fortschritt]'), null, 'ohne Hörstelle kein „Schon … gehört“');
  assert.equal(s.q('main button[data-reinhoeren], main [data-karte="gespielt"]'), null, 'Player und „Gespielt von“ kommen mit A8b und A9');
  assert.ok(!/\{[a-z_]+\}/.test(s.q('main').textContent), 'kein Platzhalter bleibt stehen');
  weg();
});

test('Kopf: das große Cover kommt aus `?groesse=gross` mit dem Stand; ohne Cover keine Anfrage', MIT_DOM, async () => {
  const s = await oeffne('s1');
  assert.ok(s.m.covers.some((p) => p === '/api/tobibox/cover/s1?groesse=gross&v=ab12cd34'), `Anfragen: ${s.m.covers}`);
  const bild = s.q('.cover.se-xl');
  assert.equal(bild.dataset.bild, '1');
  assert.match(bild.style.backgroundImage, /blob:mock-/);
  assert.equal(bild.querySelector('.bst').textContent, 'D', 'Platzhalter-Buchstabe darunter');
  await geheZu(s, '#serie-s2');
  await s.flush(8);
  assert.ok(!s.m.covers.some((p) => p.includes('/cover/s2')), 'kein cover_stand: nichts angefragt');
  assert.equal(s.q('.cover.se-xl').dataset.bild, undefined);
  weg();
});

test('Kopf: „Schon 18 % gehört · noch 21 Min.“ nur mit Hörstelle; Gesamtdauer im Untertitel', MIT_DOM, async () => {
  const s = await seite({ hash: '' });
  beispiele(s.m);
  s.m.backend.serien.s1.hoerstelle = { anteil: 0.18, rest_s: 1260, zeit: '2026-11-12T18:00:00Z', folge: 'folge-01.mp3' };
  s.m.backend.serien.s1.dauer_s = 3900;
  await geheZu(s, '#serie-s1');
  await s.flush(8);
  assert.equal(s.q('[data-fortschritt]').textContent, 'Schon 18 % gehört · noch 21 Min.');
  assert.equal(s.q('[data-untertitel]').textContent, 'Hörspiel · 3 Folgen · 1 Std. 5 Min.');
  weg();
});

test('Wechsel zwischen Serien: die zweite Seite zeigt sofort ihre Daten, nicht die der ersten', MIT_DOM, async () => {
  const s = await oeffne('s1');
  assert.equal(s.q('main h2').textContent, 'Die drei ???');
  await geheZu(s, '#serie-s2');
  assert.equal(s.q('main h2').textContent, 'Bibi Blocksberg');
  assert.deepEqual(namen(s), ['Hexen gibt es doch']);
  weg();
});

/* ------------------------------------------------------------------ Folgenliste */

test('Folgenliste: Abschnitt „Folgen“, je Zeile Nummer, Titel und ein „⋯“-Knopf von mindestens 44 px; die Zeile ist kein Link', MIT_DOM, async () => {
  const s = await oeffne('s1');
  assert.equal(s.q('.se-abschnitt').textContent, 'Folgen');
  assert.deepEqual(namen(s), ['Der Rabe', 'Das Gespensterschloss', 'Der Super-Papagei']);
  assert.deepEqual(s.qa('[data-folge] .se-num').map((x) => x.textContent), ['1', '2', '3']);
  const knoepfe = s.qa('[data-folge] [data-menue-folge]');
  assert.equal(knoepfe.length, 3);
  assert.equal(knoepfe[0].getAttribute('aria-label'), 'Mehr zu Der Rabe');
  assert.equal(knoepfe[0].getAttribute('aria-haspopup'), 'dialog');
  assert.equal(s.qa('[data-folge] a:not(.tb-chip)').length, 0, 'ohne die Chips der Tobies (A9) ist die Zeile kein Link');
  assert.equal(s.q('input[type="search"]'), null, 'unter 20 Folgen kein Suchfeld');
  assert.equal(s.q('[data-mehr]'), null);
  weg();
});

test('Folgenliste: Folgen-Nummer aus den Daten, Dauer, „· 14 Kapitel“ bei Ordner-Folgen, Fortschritt und „Fertig gehört“ nur mit Daten', MIT_DOM, async () => {
  const s = await seite({ hash: '' });
  beispiele(s.m);
  const f = s.m.backend.serien.s1.folgen;
  f[0].nummer = 7; f[0].dauer_s = 139;
  f[1].dauer_s = 600; f[1].hoerstelle = { position_s: 47, fertig: false };
  f[2].dauer_s = 300; f[2].hoerstelle = { position_s: 300, fertig: true };
  await geheZu(s, '#serie-s1');
  await s.flush(8);
  const z = s.qa('[data-folge]');
  assert.equal(z[0].querySelector('.se-num').textContent, '7');
  assert.equal(z[0].querySelector('.muted').textContent, '2:19');
  assert.equal(z[0].querySelector('.pbar'), null, 'nicht angefangen: kein Balken');
  assert.equal(z[1].querySelector('.pbar').getAttribute('aria-valuenow'), '8');
  assert.match(z[1].textContent, /noch 9:13/);
  assert.match(z[2].textContent, /Fertig gehört/);
  assert.equal(z[2].querySelector('.pbar'), null);
  await geheZu(s, '#serie-buch');
  await s.flush(8);
  assert.equal(s.q('[data-untertitel]').textContent, 'Hörbuch · 14 Kapitel · 9 Std. 40 Min.');
  assert.equal(s.q('[data-folge] .muted').textContent, '9:40:00 · 14 Kapitel');
  assert.equal(s.q('.se-abschnitt').textContent, 'Hörbuch');
  weg();
});

test('Lange Folgenliste: ab mehr als 20 ein Suchfeld und „Mehr laden“ in Päckchen von 20; Suche ohne Rücksicht auf Umlaute', MIT_DOM, async () => {
  const s = await oeffne('lang');
  assert.equal(s.qa('[data-folge]').length, 20);
  const feld = s.q('input#se-suche');
  assert.ok(feld, 'Suchfeld');
  assert.equal(feld.getAttribute('placeholder'), 'Hier suchen');
  assert.equal(s.q('label[for="se-suche"]').textContent, 'In diesem Eintrag suchen');
  assert.equal(s.q('[data-mehr]').textContent.trim(), 'Mehr laden (20 weitere)');
  await klick(s, s.q('[data-mehr]'));
  assert.equal(s.qa('[data-folge]').length, 40);
  assert.equal(s.q('[data-mehr]').textContent.trim(), 'Mehr laden (5 weitere)');
  await klick(s, s.q('[data-mehr]'));
  assert.equal(s.qa('[data-folge]').length, 45);
  assert.equal(s.q('[data-mehr]'), null);
  tippe(s.q('input#se-suche'), 'FOLGE 4');
  await s.flush();
  assert.deepEqual(namen(s), ['Folge 4', 'Folge 40', 'Folge 41', 'Folge 42', 'Folge 43', 'Folge 44', 'Folge 45']);
  assert.equal(s.q('[data-mehr]'), null);
  tippe(s.q('input#se-suche'), 'xyzq');
  await s.flush();
  assert.equal(s.qa('[data-folge]').length, 0);
  assert.match(s.q('[data-leer="suche"]').textContent, /Nichts gefunden zu „xyzq“\./);
  await klick(s, s.q('[data-leer="suche"] button'));
  assert.equal(s.qa('[data-folge]').length, 20, 'Suche gelöscht');
  assert.equal(s.q('input#se-suche').value, '');
  weg();
});

test('Leere Folgenliste: ein Satz und der Weg zum Hinzufügen, keine Zeilen', MIT_DOM, async () => {
  const s = await oeffne('leer');
  assert.equal(s.qa('[data-folge]').length, 0);
  assert.equal(s.q('[data-liste]'), null);
  const leer = s.q('[data-leer="serie"]');
  assert.equal(leer.querySelector('.et').textContent, 'In „Leere Sammlung“ ist nichts mehr drin.');
  assert.equal(leer.querySelector('a').getAttribute('href'), '#hinzufuegen');
  assert.equal(s.q('[data-untertitel]').textContent, 'Hörspiel · 0 Folgen');
  weg();
});

/* ------------------------------------------------------------------ Einzeltitel */

test('Einzeltitel: Kopf mit „Lied · einzeln“, ein Satz statt der Folgenliste; Menü ohne Verschieben und Reihenfolge', MIT_DOM, async () => {
  const s = await oeffne('lied');
  assert.equal(s.q('main h2').textContent, 'Wiegenlied');
  assert.equal(s.q('[data-untertitel]').textContent, 'Lied · einzeln · 1:06');
  assert.equal(s.qa('[data-folge]').length, 0, 'keine Folgenliste');
  assert.equal(s.q('[data-liste]'), null);
  assert.equal(s.q('.se-abschnitt'), null);
  assert.equal(s.q('[data-einzeln]').textContent, 'Das ist ein einzelnes Lied. Es steht für sich und gehört zu keinem Album. Du kannst einem Tobie das zu spielen geben.');
  await menue(s);
  assert.deepEqual(punkte(s), ['name', 'cover', 'art', 'zusammen', 'papierkorb'], 'Administrator: Name, Art, Zusammenführen (als Quelle erlaubt), Papierkorb');
  weg();
});

test('Einzeltitel: Menü und Papierkorb für Nicht-Administratoren; der Papierkorb löscht die Serie, nicht die Folge', MIT_DOM, async () => {
  const s = await seite({ hash: '', nichtAdmin: true });
  beispiele(s.m);
  await geheZu(s, '#serie-lied');
  await s.flush(8);
  await menue(s);
  assert.deepEqual(punkte(s), ['name', 'cover', 'art', 'papierkorb']);
  await klick(s, punkt(s, 'papierkorb'));
  assert.equal(titelBlatt(s), '„Wiegenlied“ in den Papierkorb?');
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  assert.equal(aufrufe(s, 'serie/delete').length, 1);
  assert.equal(aufrufe(s, 'folge/delete').length, 0);
  assert.equal(hash(), '#bibliothek');
  weg();
});

/* ------------------------------------------------------------------ Zustände */

test('Zustände: Serie nicht gefunden, Ladefehler mit „Noch einmal versuchen“', MIT_DOM, async () => {
  const s = await oeffne('gibt-es-nicht');
  const weg1 = s.q('[data-zustand="weg"]');
  assert.match(weg1.textContent, /Das gibt es nicht mehr\./);
  assert.equal(weg1.querySelector('a').getAttribute('href'), '#bibliothek');
  assert.ok(s.q('a[data-zurueck]'), 'der Weg zurück bleibt');
  assert.equal(s.q('[data-menue-serie]'), null, 'kein Menü für etwas, das es nicht gibt');
  s.m.failNext('tobibox/serie/get', 'medien_nicht_erreichbar');
  await geheZu(s, '#serie-s2');
  await s.flush(8);
  const fehler = s.q('[data-zustand="fehler"]');
  assert.ok(fehler, 'rote Karte');
  assert.match(fehler.textContent, /Code: medien_nicht_erreichbar/, 'Administratoren sehen den Code');
  await klick(s, fehler.querySelector('button'));
  assert.equal(s.q('main h2').textContent, 'Bibi Blocksberg');
  weg();
});

/* ------------------------------------------------------------------ Umbenennen */

test('Serie umbenennen: Menü → „Name ändern“ → Speichern; serie/rename, neuer Titel, Meldung „Gespeichert.“', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await menue(s);
  assert.equal(titelBlatt(s), 'Die drei ???');
  await klick(s, punkt(s, 'name'));
  assert.equal(titelBlatt(s), 'Umbenennen');
  const feld = s.q('dialog.blatt[open] input#se-name');
  assert.equal(feld.value, 'Die drei ???');
  assert.equal(feld.getAttribute('maxlength'), '100');
  assert.equal(s.q('dialog.blatt[open] label[for="se-name"]').textContent, 'Name');
  tippe(feld, '  Die drei Fragezeichen  ');
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.deepEqual(aufrufe(s, 'serie/rename').map(ohneId), [{ serie_id: 's1', name: 'Die drei Fragezeichen' }], 'Leerraum am Rand wird abgeschnitten');
  assert.equal(blatt(s), null, 'das Blatt ist zu');
  assert.equal(s.q('main h2').textContent, 'Die drei Fragezeichen');
  assert.deepEqual(toasts(s), ['Gespeichert.']);
  weg();
});

test('Serie umbenennen: leerer Name bleibt im Blatt mit Hinweis ohne Anruf; unveränderter Name schließt ohne Anruf; Enter speichert', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await menue(s);
  await klick(s, punkt(s, 'name'));
  tippe(s.q('dialog.blatt[open] input#se-name'), '   ');
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.ok(blatt(s), 'bleibt offen');
  assert.equal(s.q('dialog.blatt[open] .se-fehl').textContent, 'Bitte einen Namen eingeben.');
  assert.equal(s.q('dialog.blatt[open] input#se-name').getAttribute('aria-invalid'), 'true');
  assert.equal(aufrufe(s, 'serie/rename').length, 0);
  tippe(s.q('dialog.blatt[open] input#se-name'), 'Die drei ???');
  await s.flush();
  assert.equal(s.q('dialog.blatt[open] .se-fehl'), null, 'der Hinweis geht beim Tippen');
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.equal(blatt(s), null);
  assert.equal(aufrufe(s, 'serie/rename').length, 0, 'nichts geändert, nichts gesendet');
  await menue(s);
  await klick(s, punkt(s, 'name'));
  tippe(s.q('dialog.blatt[open] input#se-name'), 'Per Enter');
  taste(s.q('dialog.blatt[open] input#se-name'), 'Enter');
  await s.flush(10);
  assert.equal(aufrufe(s, 'serie/rename').length, 1);
  assert.equal(s.q('main h2').textContent, 'Per Enter');
  weg();
});

test('Serie umbenennen: name_ungueltig vom Backend steht im Blatt, andere Fehler als Meldung; das Blatt bleibt offen', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await menue(s);
  await klick(s, punkt(s, 'name'));
  tippe(s.q('dialog.blatt[open] input#se-name'), 'Neuer Name');
  s.m.failNext('tobibox/serie/rename', 'name_ungueltig');
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.equal(s.q('dialog.blatt[open] .se-fehl').textContent, FEHLER.name_ungueltig);
  s.m.failNext('tobibox/serie/rename', 'medien_schreibfehler');
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.ok(blatt(s), 'bleibt offen, damit man es noch einmal versuchen kann');
  assert.match(s.q('.toast.err .tmsg').textContent, /Das Speichern auf dem NAS hat nicht geklappt/);
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.equal(blatt(s), null);
  assert.equal(s.q('main h2').textContent, 'Neuer Name');
  weg();
});

test('Folge umbenennen: folge/rename mit Schlüssel und stand; die Zeile zeigt den neuen Namen, der Schlüssel bleibt', MIT_DOM, async () => {
  const s = await oeffne('s1');
  const stand0 = await standVon(s, 's1');
  await folgeMenue(s, 'folge-01.mp3');
  assert.equal(titelBlatt(s), 'Der Rabe');
  assert.deepEqual(punkte(s), ['geben', 'name', 'verschieben', 'papierkorb']); // A9: „Einem Tobie geben …“ zuerst
  await klick(s, punkt(s, 'name'));
  const feld = s.q('dialog.blatt[open] input#se-name');
  assert.equal(feld.value, 'Der Rabe');
  assert.equal(feld.getAttribute('maxlength'), '200');
  tippe(feld, 'Der schwarze Rabe');
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.deepEqual(aufrufe(s, 'folge/rename').map(ohneId), [{ serie_id: 's1', folge: 'folge-01.mp3', name: 'Der schwarze Rabe', stand: stand0 }]);
  assert.deepEqual(namen(s), ['Der schwarze Rabe', 'Das Gespensterschloss', 'Der Super-Papagei']);
  assert.equal(s.q('[data-folge]').dataset.folge, 'folge-01.mp3');
  weg();
});

test('Folge umbenennen: stand_veraltet → Meldung „Ansicht ist neu geladen“, das Blatt schließt, die Seite lädt neu', MIT_DOM, async () => {
  const s = await oeffne('s1');
  const vorher = aufrufe(s, 'serie/get').length;
  await folgeMenue(s, 'folge-01.mp3');
  await klick(s, punkt(s, 'name'));
  tippe(s.q('dialog.blatt[open] input#se-name'), 'Anders');
  s.m.failNext('tobibox/folge/rename', 'stand_veraltet');
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.equal(blatt(s), null);
  assert.equal(s.q('.toast.err .tmsg').textContent, FEHLER.stand_veraltet);
  assert.ok(aufrufe(s, 'serie/get').length > vorher, 'neu geladen');
  assert.deepEqual(namen(s)[0], 'Der Rabe', 'die Anzeige zeigt den Stand des Backends');
  weg();
});

/* ------------------------------------------------------------------ Art */

test('Art ändern: Blatt „Was ist das?“ mit vier Arten, die aktuelle gewählt; Speichern ruft serie/art_setzen und der Untertitel folgt', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await menue(s);
  await klick(s, punkt(s, 'art'));
  assert.equal(titelBlatt(s), 'Was ist das?');
  const wahl = s.qa('dialog.blatt[open] [role="radio"]');
  assert.deepEqual(wahl.map((x) => x.textContent.trim()), ['Hörspiel', 'Hörbuch', 'Musik', 'Geschichten']);
  assert.deepEqual(wahl.map((x) => x.getAttribute('aria-checked')), ['true', 'false', 'false', 'false']);
  await klick(s, wahl[2]);
  assert.deepEqual(s.qa('dialog.blatt[open] [role="radio"]').map((x) => x.getAttribute('aria-checked')), ['false', 'false', 'true', 'false']);
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.deepEqual(aufrufe(s, 'serie/art_setzen').map(ohneId), [{ serie_id: 's1', art: 'musik' }]);
  assert.equal(blatt(s), null);
  assert.equal(s.q('[data-untertitel]').textContent, 'Musik · 3 Lieder');
  assert.equal(s.q('.se-abschnitt').textContent, 'Lieder');
  assert.deepEqual(toasts(s), ['Gespeichert: Musik.']);
  weg();
});

test('Art ändern: dieselbe Art sendet nichts; ohne die Fähigkeit „bibliothek“ gibt es den Punkt nicht', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await menue(s);
  await klick(s, punkt(s, 'art'));
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.equal(aufrufe(s, 'serie/art_setzen').length, 0);
  assert.equal(blatt(s), null);
  weg();
  const alt = await seite({ hash: '', faehigkeiten: FAEHIGKEITEN.filter((f) => f !== 'bibliothek') });
  await geheZu(alt, '#serie-s1');
  await alt.flush(8);
  await menue(alt);
  assert.deepEqual(punkte(alt), ['name', 'cover', 'reihenfolge', 'zusammen', 'papierkorb']);
  weg();
});

/* ------------------------------------------------------------------ Verschieben */

test('Verschieben: die Zielwahl listet andere Sammlungen (ohne diese, ohne Einzeltitel); Wahl, Rückfrage, folge/verschieben mit stand', MIT_DOM, async () => {
  const s = await seite({ hash: '', nichtAdmin: true });
  beispiele(s.m);
  await geheZu(s, '#serie-s1');
  await s.flush(8);
  const stand0 = await standVon(s, 's1');
  await folgeMenue(s, 'folge-01.mp3');
  await klick(s, punkt(s, 'verschieben'));
  assert.equal(titelBlatt(s), 'Wohin verschieben?');
  const ziele = s.qa('dialog.blatt[open] [data-wahl]').map((x) => x.dataset.wahl);
  assert.deepEqual(ziele.sort(), ['buch', 'lang', 'leer', 's2'], 'weder s1 (diese), lied (Einzeltitel) noch s3 (Überraschung, nur für Administratoren)');
  const ersterAufruf = s.m.aufrufe('tobibox/serien/list').at(-1);
  assert.equal(ersterAufruf.limit, 30);
  assert.deepEqual(ersterAufruf.filter, ['sammlung']);
  assert.equal(s.q('dialog.blatt[open] [data-wahl="s2"]').getAttribute('aria-label'), 'Bibi Blocksberg wählen');
  await klick(s, s.q('dialog.blatt[open] [data-wahl="s2"]'));
  assert.equal(titelBlatt(s), '„Der Rabe“ nach „Bibi Blocksberg“ verschieben?');
  assert.ok(!blattText(s).includes('Tobie'), 'ohne Tobies keine Zeile dazu');
  await klick(s, leisteKnopf(s, 'Verschieben'));
  assert.deepEqual(aufrufe(s, 'folge/verschieben').map(ohneId), [{ serie_id: 's1', folge: 'folge-01.mp3', ziel_serie_id: 's2', stand: stand0 }]);
  assert.equal(blatt(s), null);
  assert.deepEqual(namen(s), ['Das Gespensterschloss', 'Der Super-Papagei']);
  assert.deepEqual(toasts(s), ['„Der Rabe“ ist jetzt in „Bibi Blocksberg“.']);
  assert.deepEqual(s.m.backend.serien.s2.folgen.map((f) => f.anzeige), ['Hexen gibt es doch', 'Der Rabe']);
  weg();
});

test('Verschieben: Administratoren sehen auch die Überraschungs-Serie; die Suche sendet text (nach kurzer Pause)', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await folgeMenue(s, 'folge-01.mp3');
  await klick(s, punkt(s, 'verschieben'));
  assert.ok(s.q('dialog.blatt[open] [data-wahl="s3"]'), 'Überraschung für Administratoren');
  tippe(s.q('dialog.blatt[open] #se-wahl-s'), 'bibi');
  await warte(320);
  await s.flush();
  assert.equal(s.m.aufrufe('tobibox/serien/list').at(-1).text, 'bibi');
  assert.deepEqual(s.qa('dialog.blatt[open] [data-wahl]').map((x) => x.dataset.wahl), ['s2']);
  tippe(s.q('dialog.blatt[open] #se-wahl-s'), 'xyzq');
  await warte(320);
  await s.flush();
  assert.equal(s.q('dialog.blatt[open] [data-wahl-leer]').textContent, 'Nichts gefunden.');
  assert.equal(s.qa('dialog.blatt[open] [data-wahl]').length, 0);
  weg();
});

test('Verschieben einer Folge mit Tobie: die Rückfrage nennt ihn und sagt, dass er von vorn beginnt; gesendet wird tobies_bestaetigt', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await folgeMenue(s, 'folge-02.mp3');
  await klick(s, punkt(s, 'verschieben'));
  await klick(s, s.q('dialog.blatt[open] [data-wahl="s2"]'));
  assert.match(blattText(s), /1 Tobie spielt genau diese Folge: Tobie ohne Namen\. Er spielt sie danach weiter, beginnt aber auf der Box von vorn\./);
  await klick(s, leisteKnopf(s, 'Verschieben'));
  const a = aufrufe(s, 'folge/verschieben').at(-1);
  assert.equal(a.tobies_bestaetigt, true);
  assert.deepEqual(namen(s), ['Der Rabe', 'Der Super-Papagei']);
  weg();
});

test('Verschieben ohne die Fähigkeit „bibliothek“: die Zielwahl lädt alles und filtert selbst', MIT_DOM, async () => {
  const s = await seite({ hash: '', nichtAdmin: true, faehigkeiten: FAEHIGKEITEN.filter((f) => f !== 'bibliothek') });
  beispiele(s.m);
  await geheZu(s, '#serie-s1');
  await s.flush(8);
  await folgeMenue(s, 'folge-01.mp3');
  await klick(s, punkt(s, 'verschieben'));
  assert.deepEqual(ohneId(s.m.aufrufe('tobibox/serien/list').at(-1)), {});
  assert.deepEqual(s.qa('dialog.blatt[open] [data-wahl]').map((x) => x.dataset.wahl).sort(), ['buch', 'lang', 'leer', 's2']);
  weg();
});

test('Verschieben: Abbrechen schließt ohne Anruf und der Fokus geht zum „⋯“ der Folge zurück', MIT_DOM, async () => {
  const s = await oeffne('s1');
  const knopf = s.q('[data-folge="folge-03.mp3"] [data-menue-folge]');
  await klick(s, knopf);
  await klick(s, punkt(s, 'verschieben'));
  await klick(s, s.q('dialog.blatt[open] [data-wahl="s2"]'));
  await klick(s, leisteKnopf(s, 'Abbrechen'));
  await warte(10);
  assert.equal(blatt(s), null);
  assert.equal(aufrufe(s, 'folge/verschieben').length, 0);
  assert.equal(s.el.shadowRoot.activeElement, knopf, 'Fokus am Auslöser, auch nach dem Weg über mehrere Blätter');
  weg();
});

test('Verschieben: stand_veraltet → Meldung, Blatt zu, neu geladen; die Folge bleibt', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await folgeMenue(s, 'folge-01.mp3');
  await klick(s, punkt(s, 'verschieben'));
  await klick(s, s.q('dialog.blatt[open] [data-wahl="s2"]'));
  s.m.failNext('tobibox/folge/verschieben', 'stand_veraltet');
  await klick(s, leisteKnopf(s, 'Verschieben'));
  assert.equal(blatt(s), null);
  assert.equal(s.q('.toast.err .tmsg').textContent, FEHLER.stand_veraltet);
  assert.equal(namen(s).length, 3);
  weg();
});

/* ------------------------------------------------------------------ Papierkorb */

test('Papierkorb einer Folge ohne Tobie: Rückfrage ohne Tobie-Satz, folge/delete ohne tobies_bestaetigt, Meldung, Zeile weg', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await folgeMenue(s, 'folge-01.mp3');
  await klick(s, punkt(s, 'papierkorb'));
  assert.equal(titelBlatt(s), '„Der Rabe“ in den Papierkorb?');
  assert.equal(blatt(s).getAttribute('role'), 'alertdialog');
  assert.equal(blattText(s).replace(/^.*?Der Rabe“ in den Papierkorb\? ?/, '').replace(/ ?(Abbrechen|In den Papierkorb)/g, '').trim(),
    'Es verschwindet aus der Liste. Der Administrator sieht es und kann es zurückholen.');
  assert.deepEqual(s.qa('dialog.blatt[open] .knoepfe button').map((b) => b.textContent.trim()), ['Abbrechen', 'In den Papierkorb']);
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  const a = aufrufe(s, 'folge/delete').map(ohneId);
  assert.equal(a.length, 1);
  assert.equal(a[0].tobies_bestaetigt, undefined);
  assert.equal(a[0].folge, 'folge-01.mp3');
  assert.ok(a[0].stand);
  assert.deepEqual(namen(s), ['Das Gespensterschloss', 'Der Super-Papagei']);
  assert.deepEqual(toasts(s), ['„Der Rabe“ ist im Papierkorb.']);
  assert.equal(s.q('[data-untertitel]').textContent, 'Hörspiel · 2 Folgen');
  weg();
});

test('Papierkorb einer Folge mit Tobie: die Rückfrage nennt ihn, gesendet wird tobies_bestaetigt', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await folgeMenue(s, 'folge-02.mp3');
  await klick(s, punkt(s, 'papierkorb'));
  assert.match(blattText(s), /Es verschwindet aus der Liste\. 1 Tobie spielt dann nichts mehr: Tobie ohne Namen\. Der Administrator sieht es/);
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  assert.equal(aufrufe(s, 'folge/delete').at(-1).tobies_bestaetigt, true);
  assert.deepEqual(namen(s), ['Der Rabe', 'Der Super-Papagei']);
  weg();
});

test('Papierkorb der Serie: die Rückfrage nennt alle Tobies mit Namen (Serie und Folgen); Bestätigen löscht und geht zur Bibliothek', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await menue(s);
  await klick(s, punkt(s, 'papierkorb'));
  assert.equal(titelBlatt(s), '„Die drei ???“ in den Papierkorb?');
  assert.match(blattText(s), /Es verschwindet aus der Bibliothek\. 2 Tobies spielen dann nichts mehr: Anna, Tobie ohne Namen\. Der Administrator sieht es und kann es zurückholen\./);
  assert.equal(aufrufe(s, 'serie/delete').length, 0, 'erst die Rückfrage');
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  const a = aufrufe(s, 'serie/delete').map(ohneId);
  assert.equal(a.length, 1);
  assert.equal(a[0].serie_id, 's1');
  assert.equal(a[0].tobies_bestaetigt, true);
  assert.ok(a[0].stand);
  assert.equal(hash(), '#bibliothek');
  assert.equal(s.m.backend.serien.s1, undefined);
  assert.ok(toasts(s).includes('„Die drei ???“ ist im Papierkorb.'));
  weg();
});

test('Papierkorb der Serie: „Abbrechen“ ändert nichts; eine Serie ohne Tobies schickt kein tobies_bestaetigt', MIT_DOM, async () => {
  const s = await oeffne('s2');
  await menue(s);
  await klick(s, punkt(s, 'papierkorb'));
  assert.ok(!blattText(s).includes('Tobie'), 'kein Tobie-Satz ohne Tobies');
  await klick(s, leisteKnopf(s, 'Abbrechen'));
  assert.equal(aufrufe(s, 'serie/delete').length, 0);
  assert.equal(hash(), '#serie-s2');
  await menue(s);
  await klick(s, punkt(s, 'papierkorb'));
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  assert.equal(aufrufe(s, 'serie/delete').at(-1).tobies_bestaetigt, undefined);
  assert.equal(hash(), '#bibliothek');
  weg();
});

test('Papierkorb der Serie: meldet das Backend „Tobies betroffen“, lädt die Seite neu und fragt noch einmal (jetzt mit Namen)', MIT_DOM, async () => {
  const s = await oeffne('s2');
  await menue(s);
  await klick(s, punkt(s, 'papierkorb'));
  // Zwischendurch hat jemand einen Tobie auf die Serie gelegt; die Seite wusste es nicht.
  s.m.backend.zuordnungen.AAAA1111 = { uid: 'AAAA1111', name: 'Fuchs', ziel: { typ: 'serie', serie: 's2' } };
  s.m.failNext('tobibox/serie/delete', 'tobies_betroffen');
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  assert.ok(blatt(s), 'eine neue Rückfrage');
  assert.match(blattText(s), /1 Tobie spielt dann nichts mehr: Fuchs\./);
  assert.equal(hash(), '#serie-s2');
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  assert.equal(aufrufe(s, 'serie/delete').length, 2);
  assert.equal(aufrufe(s, 'serie/delete').at(-1).tobies_bestaetigt, true);
  assert.equal(hash(), '#bibliothek');
  weg();
});

test('Papierkorb der Serie: „Tobies betroffen“, aber nach dem Neuladen sieht die Seite keine → keine Schleife, Meldung, Blatt zu', MIT_DOM, async () => {
  const s = await oeffne('s2');
  await menue(s);
  await klick(s, punkt(s, 'papierkorb'));
  // Das Backend meldet Tobies (zum Beispiel auf eine schon gelöschte Folge), die Seite bekommt keine zu sehen.
  s.m.failNext('tobibox/serie/delete', 'tobies_betroffen', 'tobies_betroffen', 'tobies_betroffen');
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  assert.equal(aufrufe(s, 'serie/delete').length, 1, 'kein zweiter und dritter Versuch');
  assert.equal(blatt(s), null, 'das Blatt ist zu');
  assert.equal(s.q('.toast.err .tmsg').textContent, SERIE.tobies_unklar);
  assert.equal(hash(), '#serie-s2');
  weg();
});

test('Papierkorb: Nicht-Administratoren dürfen (Alltag); stand_veraltet bei der Serie → Meldung, Blatt zu, neu geladen', MIT_DOM, async () => {
  const s = await seite({ hash: '', nichtAdmin: true });
  beispiele(s.m);
  await geheZu(s, '#serie-s2');
  await s.flush(8);
  await menue(s);
  await klick(s, punkt(s, 'papierkorb'));
  s.m.failNext('tobibox/serie/delete', 'stand_veraltet');
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  assert.equal(blatt(s), null);
  assert.equal(hash(), '#serie-s2', 'die Seite bleibt');
  assert.equal(s.q('.toast.err .tmsg').textContent, FEHLER.stand_veraltet);
  await menue(s);
  await klick(s, punkt(s, 'papierkorb'));
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  assert.equal(hash(), '#bibliothek', 'ohne Administrator-Recht geht es');
  weg();
});

test('Papierkorb: die Folge ist schon weg (folge_nicht_gefunden) → Meldung, Blatt zu, neu geladen', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await folgeMenue(s, 'folge-01.mp3');
  await klick(s, punkt(s, 'papierkorb'));
  s.m.failNext('tobibox/folge/delete', 'folge_nicht_gefunden');
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  assert.equal(blatt(s), null);
  assert.equal(s.q('.toast.err .tmsg').textContent, FEHLER.folge_nicht_gefunden);
  weg();
});

/* ------------------------------------------------------------------ Rechte */

test('Rechte: Administrator sieht „Reihenfolge ändern“ und „Mit anderem zusammenführen …“, Nicht-Administrator nicht (nicht nur gesperrt)', MIT_DOM, async () => {
  const admin = await oeffne('s1');
  await menue(admin);
  assert.deepEqual(punkte(admin), ['name', 'cover', 'art', 'reihenfolge', 'zusammen', 'papierkorb']);
  assert.equal(punkt(admin, 'reihenfolge').textContent.trim(), 'Reihenfolge ändern');
  assert.equal(punkt(admin, 'zusammen').textContent.trim(), 'Mit anderem zusammenführen …');
  assert.equal(punkt(admin, 'papierkorb').textContent.trim(), 'In den Papierkorb …');
  weg();
  const user = await seite({ hash: '', nichtAdmin: true });
  beispiele(user.m);
  await geheZu(user, '#serie-s1');
  await user.flush(8);
  await menue(user);
  assert.deepEqual(punkte(user), ['name', 'cover', 'art', 'papierkorb']);
  assert.ok(!blattText(user).includes('Reihenfolge') && !blattText(user).includes('zusammenführen'));
  weg();
});

test('Rechte: auch im Menü „Das stimmt nicht“ fehlt das Zusammenführen für Nicht-Administratoren; Folgenmenü ist für alle gleich', MIT_DOM, async () => {
  const user = await seite({ hash: '', nichtAdmin: true });
  await geheZu(user, '#serie-s2');
  await user.flush(8);
  await klick(user, user.q('[data-stimmt-nicht]'));
  assert.deepEqual(punkte(user), ['art', 'name', 'papierkorb']);
  weg();
  const admin = await oeffne('s2');
  await klick(admin, admin.q('[data-stimmt-nicht]'));
  assert.deepEqual(punkte(admin), ['art', 'name', 'zusammen', 'papierkorb']);
  await klick(admin, leisteKnopf(admin, 'Schließen'));
  await folgeMenue(admin, 'b-01.mp3');
  assert.deepEqual(punkte(admin), ['geben', 'name', 'verschieben', 'papierkorb'], 'in der Folge nichts nur für Administratoren');
  weg();
});

test('Rechte: ein Einzeltitel oder die Überraschungs-Serie bietet kein Zusammenführen als Ziel an, die Überraschung auch keine Art', MIT_DOM, async () => {
  const s = await oeffne('s3');
  await menue(s);
  assert.deepEqual(punkte(s), ['name', 'cover', 'papierkorb'], 'Überraschung: keine Art, kein Zusammenführen (Vertrag 27: nur normale Serien), eine Folge: keine Reihenfolge');
  weg();
});

/* ------------------------------------------------------------------ Reihenfolge (Administrator) */

test('Reihenfolge ändern: ▲/▼ je Zeile statt „⋯“; jeder Tausch sendet die ganze Liste mit dem neuesten stand; „Fertig“ beendet', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await menue(s);
  await klick(s, punkt(s, 'reihenfolge'));
  await warte(10);
  assert.equal(blatt(s), null);
  assert.equal(s.qa('[data-menue-folge]').length, 0, 'statt „⋯“ die Pfeile');
  assert.equal(s.qa('[data-auf]').length, 3);
  assert.equal(s.qa('[data-ab]').length, 3);
  assert.equal(s.q('[data-folge="folge-01.mp3"] [data-auf]').disabled, true, 'die erste kann nicht höher');
  assert.equal(s.q('[data-folge="folge-03.mp3"] [data-ab]').disabled, true, 'die letzte nicht tiefer');
  assert.equal(s.q('[data-folge="folge-02.mp3"] [data-auf]').getAttribute('aria-label'), 'Das Gespensterschloss nach oben');
  assert.equal(s.q('[data-folge="folge-02.mp3"] [data-ab]').getAttribute('aria-label'), 'Das Gespensterschloss nach unten');
  assert.equal(s.q('[data-fertig]').textContent.trim(), 'Fertig mit Reihenfolge');
  assert.equal(s.el.shadowRoot.activeElement, s.q('[data-fertig]'), 'Fokus auf „Fertig“');
  const stand0 = await standVon(s, 's1');
  await klick(s, s.q('[data-folge="folge-01.mp3"] [data-ab]'));
  assert.deepEqual(namen(s), ['Das Gespensterschloss', 'Der Rabe', 'Der Super-Papagei']);
  assert.equal(s.el.shadowRoot.activeElement, s.q('[data-folge="folge-01.mp3"] [data-ab]'), 'der Fokus bleibt am verschobenen Eintrag');
  const e1 = aufrufe(s, 'folgen/order').map(ohneId);
  assert.deepEqual(e1, [{ serie_id: 's1', folgen: ['folge-02.mp3', 'folge-01.mp3', 'folge-03.mp3'], stand: stand0 }]);
  await klick(s, s.q('[data-folge="folge-03.mp3"] [data-auf]'));
  const e2 = aufrufe(s, 'folgen/order').map(ohneId);
  assert.deepEqual(e2[1].folgen, ['folge-02.mp3', 'folge-03.mp3', 'folge-01.mp3']);
  assert.notEqual(e2[1].stand, stand0, 'der zweite Tausch trägt den neuen stand aus der Antwort');
  assert.deepEqual(s.m.backend.serien.s1.folgen.map((f) => f.name), ['folge-02.mp3', 'folge-03.mp3', 'folge-01.mp3']);
  await klick(s, s.q('[data-fertig]'));
  assert.equal(s.qa('[data-auf]').length, 0);
  assert.equal(s.qa('[data-menue-folge]').length, 3);
  weg();
});

test('Reihenfolge ändern: stand_veraltet → Meldung und neu laden mit dem Stand des Backends', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await menue(s);
  await klick(s, punkt(s, 'reihenfolge'));
  const vorher = aufrufe(s, 'serie/get').length;
  s.m.failNext('tobibox/folgen/order', 'stand_veraltet');
  await klick(s, s.q('[data-folge="folge-01.mp3"] [data-ab]'));
  await s.flush(10);
  assert.equal(s.q('.toast.err .tmsg').textContent, FEHLER.stand_veraltet);
  assert.ok(aufrufe(s, 'serie/get').length > vorher);
  assert.deepEqual(namen(s), ['Der Rabe', 'Das Gespensterschloss', 'Der Super-Papagei'], 'wieder die Reihenfolge des Backends');
  weg();
});

test('Reihenfolge ändern: nur mit mehr als einer Folge; Einzeltitel und Nicht-Administrator haben den Punkt nicht', MIT_DOM, async () => {
  const s = await oeffne('s2');
  await menue(s);
  assert.ok(!punkte(s).includes('reihenfolge'), 's2 hat eine Folge');
  weg();
});

/* ------------------------------------------------------------------ Zusammenführen (Administrator) */

test('Zusammenführen: Zielwahl nur normale Sammlungen, Rückfrage mit den Tobies, serien/zusammenfuehren mit beiden stand; danach die Zielseite', MIT_DOM, async () => {
  const s = await oeffne('s1');
  const standQ = await standVon(s, 's1');
  const standZ = await standVon(s, 's2');
  await menue(s);
  await klick(s, punkt(s, 'zusammen'));
  assert.equal(titelBlatt(s), 'Mit welchem zusammenführen?');
  const ziele = s.qa('dialog.blatt[open] [data-wahl]').map((x) => x.dataset.wahl).sort();
  assert.deepEqual(ziele, ['buch', 'lang', 'leer', 's2'], 'nicht s1, nicht den Einzeltitel, nicht die Überraschung');
  await klick(s, s.q('dialog.blatt[open] [data-wahl="s2"]'));
  assert.equal(titelBlatt(s), '„Die drei ???“ mit „Bibi Blocksberg“ zusammenführen?');
  assert.match(blattText(s), /Alle Folgen von „Die drei \?\?\?“ kommen nach „Bibi Blocksberg“\./);
  assert.match(blattText(s), /2 Tobies spielen „Die drei \?\?\?“: Anna, Tobie ohne Namen\. Sie spielen danach „Bibi Blocksberg“ und beginnen auf der Box von vorn\./);
  await klick(s, leisteKnopf(s, 'Zusammenführen'));
  assert.deepEqual(aufrufe(s, 'serien/zusammenfuehren').map(ohneId), [{ quelle_id: 's1', ziel_id: 's2', stand_quelle: standQ, stand_ziel: standZ, tobies_bestaetigt: true }]);
  assert.equal(hash(), '#serie-s2');
  await s.flush(10);
  assert.equal(s.q('main h2').textContent, 'Bibi Blocksberg');
  assert.equal(s.qa('[data-folge]').length, 4);
  assert.ok(toasts(s).includes('„Die drei ???“ ist jetzt in „Bibi Blocksberg“ zusammengeführt.'));
  weg();
});

test('Zusammenführen: ein Einzeltitel darf Quelle sein; ohne Tobies kein tobies_bestaetigt; stand_veraltet schließt und lädt neu', MIT_DOM, async () => {
  const s = await oeffne('lied');
  await menue(s);
  await klick(s, punkt(s, 'zusammen'));
  await klick(s, s.q('dialog.blatt[open] [data-wahl="s2"]'));
  assert.ok(!blattText(s).includes('Tobie'));
  s.m.failNext('tobibox/serien/zusammenfuehren', 'stand_veraltet');
  await klick(s, leisteKnopf(s, 'Zusammenführen'));
  assert.equal(blatt(s), null);
  assert.equal(hash(), '#serie-lied');
  assert.equal(s.q('.toast.err .tmsg').textContent, FEHLER.stand_veraltet);
  await menue(s);
  await klick(s, punkt(s, 'zusammen'));
  await klick(s, s.q('dialog.blatt[open] [data-wahl="s2"]'));
  await klick(s, leisteKnopf(s, 'Zusammenführen'));
  assert.equal(aufrufe(s, 'serien/zusammenfuehren').at(-1).tobies_bestaetigt, undefined);
  assert.equal(hash(), '#serie-s2');
  weg();
});

/* ------------------------------------------------------------------ Das ist richtig / Das stimmt nicht */

test('Karte „Bitte kurz ansehen“: Grund aus den Folgen, „Das ist richtig“ und „Das stimmt nicht“; ohne Prüfbedarf keine Karte', MIT_DOM, async () => {
  const s = await oeffne('s1');
  assert.equal(s.q('[data-karte="ansehen"]'), null);
  await geheZu(s, '#serie-s2');
  await s.flush(8);
  const karte = s.q('[data-karte="ansehen"]');
  assert.ok(karte.classList.contains('warn'), 'gelb');
  assert.equal(karte.querySelector('strong').textContent, 'Bitte kurz ansehen.');
  assert.equal(karte.querySelector('.se-grund').textContent, GRUENDE.tags_fehlen);
  assert.deepEqual([...karte.querySelectorAll('button')].map((b) => b.textContent.trim()), ['Das ist richtig', 'Das stimmt nicht']);
  weg();
});

test('„Das ist richtig“: einsortierung/bestaetigen für die ganze Serie, die Karte verschwindet, Meldung, Fokus auf die Überschrift', MIT_DOM, async () => {
  const s = await oeffne('s2');
  await klick(s, s.q('[data-richtig]'));
  assert.deepEqual(aufrufe(s, 'einsortierung/bestaetigen').map(ohneId), [{ serie_id: 's2' }]);
  assert.equal(s.q('[data-karte="ansehen"]'), null);
  assert.deepEqual(toasts(s), ['Danke, ist erledigt.']);
  assert.equal(s.m.backend.serien.s2.pruefen, false);
  assert.equal(s.m.backend.serien.s2.folgen[0].pruefen, false);
  assert.equal(s.el.shadowRoot.activeElement, s.q('main h2'));
  weg();
});

test('„Das ist richtig“: bei einem Fehler bleibt die Karte, die Meldung nennt den Grund', MIT_DOM, async () => {
  const s = await oeffne('s2');
  s.m.failNext('tobibox/einsortierung/bestaetigen', 'medien_schreibfehler');
  await klick(s, s.q('[data-richtig]'));
  assert.ok(s.q('[data-karte="ansehen"]'));
  assert.match(s.q('.toast.err .tmsg').textContent, /Das Speichern auf dem NAS hat nicht geklappt/);
  await klick(s, s.q('[data-richtig]'));
  assert.equal(s.q('[data-karte="ansehen"]'), null, 'der zweite Versuch klappt');
  weg();
});

test('„Das stimmt nicht“ öffnet das passende Menü (Art, Name, Papierkorb), kein „Anders einsortieren“; ein Punkt führt weiter zum Namensfeld', MIT_DOM, async () => {
  const s = await seite({ hash: '', nichtAdmin: true });
  await geheZu(s, '#serie-s2');
  await s.flush(8);
  const knopf = s.q('[data-stimmt-nicht]');
  await klick(s, knopf);
  assert.equal(titelBlatt(s), 'Was soll passieren?');
  assert.match(blattText(s), /Das Einsortieren hat „Bibi Blocksberg“ nicht richtig erkannt\./);
  assert.ok(!blattText(s).includes('Anders einsortieren'), 'kommt erst mit A-3');
  assert.deepEqual(punkte(s), ['art', 'name', 'papierkorb']);
  assert.match(blattText(s), /Tippe bei der Folge auf „⋯“ und wähle „In anderes verschieben …“\./);
  await klick(s, punkt(s, 'name'));
  assert.equal(titelBlatt(s), 'Umbenennen');
  tippe(s.q('dialog.blatt[open] input#se-name'), 'Bibi und Tina');
  await klick(s, leisteKnopf(s, 'Speichern'));
  assert.equal(s.q('main h2').textContent, 'Bibi und Tina');
  assert.equal(s.m.backend.serien.s2.pruefen, false, 'serie/rename löscht das Kennzeichen (Vertrag 6)');
  assert.ok(s.q('[data-karte="ansehen"]'), 'die Folge ist weiter „bitte prüfen“, darum bleibt die Karte');
  weg();
});

/* ------------------------------------------------------------------ Barrierefreiheit und Zusammenspiel */

test('Fokus: nach „Abbrechen“ im Namensfeld zurück zum „⋯“ des Eintrags; das Blatt hat Titel und Beschriftungen', MIT_DOM, async () => {
  const s = await oeffne('s1');
  const knopf = s.q('[data-menue-serie]');
  await klick(s, knopf);
  assert.equal(s.q('dialog.blatt[open]').getAttribute('aria-labelledby'), 'blatt-t');
  await klick(s, punkt(s, 'name'));
  await klick(s, leisteKnopf(s, 'Abbrechen'));
  await warte(10);
  assert.equal(blatt(s), null);
  assert.equal(s.el.shadowRoot.activeElement, knopf);
  weg();
});

test('Fokus: nach dem Löschen einer Folge geht der Fokus zur Überschrift (der Auslöser ist weg)', MIT_DOM, async () => {
  const s = await oeffne('s1');
  await folgeMenue(s, 'folge-01.mp3');
  await klick(s, punkt(s, 'papierkorb'));
  await klick(s, leisteKnopf(s, 'In den Papierkorb'));
  await warte(20);
  await s.flush();
  const aktiv = s.el.shadowRoot.activeElement;
  assert.ok(aktiv && (aktiv.matches('main h2') || aktiv.matches('[data-menue-folge]')), `Fokus liegt auf der Seite, nicht im Nichts: ${aktiv?.tagName}`);
  weg();
});

test('Zusammenspiel: Tipp auf eine Bibliothekszeile öffnet die Serienseite; „‹ Bibliothek“ führt zurück', MIT_DOM, async () => {
  const s = await seite({ viele: true, hash: '#bibliothek' });
  await s.flush(10);
  const zeile = s.q('.lrow');
  const id = zeile.dataset.serie;
  const name = zeile.querySelector('.lt').textContent;
  await geheZu(s, zeile.getAttribute('href'));
  await s.flush(8);
  assert.equal(s.q('main h2').textContent, name);
  assert.equal(aufrufe(s, 'serie/get').at(-1).serie_id, id);
  assert.equal(s.q('a[data-zurueck]').getAttribute('href'), '#bibliothek');
  await geheZu(s, '#bibliothek');
  assert.ok(s.q('.lrow'));
  weg();
});

test('Seite beim Verlassen: laufende Antworten werden verworfen (kein Zeichnen auf der falschen Seite)', MIT_DOM, async () => {
  const s = await seite({ hash: '' });
  let los;
  s.m.on('tobibox/serie/get', async () => { await new Promise((r) => { los = r; }); return s.m.backend.serien.s1 && { ...s.m.backend.serien.s1, folgen: [], zuordnungen: [] }; });
  await geheZu(s, '#serie-s1');
  assert.ok(s.q('[aria-busy="true"]'), 'lädt');
  await geheZu(s, '#bibliothek');
  los();
  await s.flush(8);
  assert.equal(s.q('[data-folge]'), null);
  assert.equal(s.q('main h2').textContent, 'Bibliothek');
  weg();
});

/* ------------------------------------------------------------------ Computer (AB3): großer Kopf, Folgenliste mit Spalten */

test('Serienseite am Computer: großer Kopf mit Cover links, Titel und Menü rechts; Folgenliste mit Spalten Nr., Titel, Dauer', MIT_DOM, async () => {
  const s = await oeffne('s1', { breite: 1280 });
  assert.equal(s.el.getAttribute('data-layout'), 'seite');
  assert.ok(s.q('.se-hero .cover.se-xl'), 'Cover im Kopf');
  assert.equal(s.qa('[data-menue-serie]').length, 1, 'ein Menüknopf, nicht zwei');
  assert.ok(s.q('.se-hero [data-menue-serie]'), 'er sitzt im großen Kopf');
  assert.equal(s.q('.se-leiste [data-menue-serie]'), null);
  assert.equal(s.q('.se-hero h2').textContent, 'Die drei ???');
  assert.deepEqual(s.qa('.se-spalten span').map((x) => x.textContent), ['Nr.', 'Titel', 'Dauer', '']);
  assert.ok(s.q('.se-zeile .se-dauer'), 'die Dauer hat eine eigene Spalte');
  weg();
});

test('folgenMetaTeile: Dauer und Kapitel einzeln, folgenMeta setzt sie wie bisher zusammen', () => {
  assert.deepEqual(folgenMetaTeile({ dauer_s: 139 }), { dauer: '2:19', kapitel: '' });
  assert.deepEqual(folgenMetaTeile({ dauer_s: 60, kapitel: [{}, {}] }), { dauer: '1:00', kapitel: '2 Kapitel' });
  assert.deepEqual(folgenMetaTeile({}), { dauer: '', kapitel: '' });
});

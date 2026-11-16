/* Tests der Kapitel und der Hörprobe-Karte (Paket A8d; Design 5.3, 5.12, 11.4.8; Entscheidungen AM11 bis AM17). Aufruf: node --test homeassistant/tests/frontend
 *
 * Geprüft: reine Funktionen (Titel aus Zahlen, Länge, Kapitel an einer Stelle, Ziel bei Ordner-Folgen), der Abschnitt „Kapitel“ nur beim Hörbuch aus
 * **einer** Folge, die Zeilen (ganze Zeile, ohne Play-Knopf, Häkchen, `aria-current`), Kapitelsprung eingebettet (Zeit setzen) und bei Ordner-Folgen
 * (`audio/bereit` mit `track`, dann Zeit im Track, Hörstelle mit `track` und `position_s`), AM13 (das geladene Kapitel öffnet nur den Player),
 * Zeile und Knopf „Kapitel“ im Player samt Blatt, die Sperre, die Gegenprobe ohne Kapitel, die Karte „Hörprobe wird vorbereitet“ mit reserviertem Platz
 * und die Zähler der Hörkopie-Warteschlange in „Technik“. `HTMLMediaElement` ist ersetzt (player-helfer.mjs).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { geheZu, weg, MIT_DOM, domBereit, seite } from './dom-helfer.mjs';
import { FAEHIGKEITEN } from './mock-hass.mjs';
import { mockAudio, spielSeite, lade, zeit, bereitAufrufe, setAufrufe, mikro, REIN } from './player-helfer.mjs';

if (MIT_DOM.skip === false) await domBereit();
const P = await import('../../custom_components/tobibox/frontend/player.js');
const { PLAYER, KAPITEL, HOERPROBE, SERIE, TECHNIK } = await import('../../custom_components/tobibox/frontend/texte.js');
const { hatKapitelAbschnitt } = await import('../../custom_components/tobibox/frontend/seiten/serie.js');

function mit(name, fn, opts = MIT_DOM) {
  test(name, opts, async (t) => {
    const au = await mockAudio();
    try { await fn(t, au); } finally { weg(); au.zurueck(); try { window.localStorage.clear(); } catch { /* ohne */ } }
  });
}

const folge = (name, anzeige, extra = {}) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5 * 1048576, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [], ...extra });
const EINGEBETTET = [{ titel: '1', start_s: 0 }, { titel: 'Der Hafen', start_s: 169 }, { titel: 'Der Sturm', start_s: 400 }];
const IM_ORDNER = [{ titel: '1', start_s: 0, track: 0 }, { titel: 'Zwei', start_s: 100, track: 1 }, { titel: 'Mitte', start_s: 160, track: 1 }, { titel: 'Drei', start_s: 220, track: 2 }];

/* Hörbuch aus einer Datei mit eingebetteten Kapiteln (`hb`), Hörbuch aus einem Ordner (`buch` aus den Beispielen, hier mit Kapiteln) und eine Serie mit mehreren Folgen,
 * deren erste Kapitel hat (`mehr`). */
function daten(m, { ordner = IM_ORDNER } = {}) {
  const b = m.backend.serien;
  b.hb = { id: 'hb', name: 'Das Buch', typ: 'normal', ordner: 'Hb', pruefen: false, hinweise: [], art: 'hoerbuch', dauer_s: 600, cover_stand: null,
    folgen: [folge('hb.m4b', 'Das Buch', { dauer_s: 600, kapitel: EINGEBETTET })] };
  b.buch.folgen[0].kapitel = ordner;
  b.mehr = { id: 'mehr', name: 'Lange Reise', typ: 'normal', ordner: 'Mehr', pruefen: false, hinweise: [], art: 'hoerspiel', cover_stand: null,
    folgen: [folge('a.m4b', 'Teil 1', { dauer_s: 600, kapitel: EINGEBETTET }), folge('b.mp3', 'Teil 2', { dauer_s: 100 })] };
}

async function seiteMit(hash, opts = {}) {
  const s = await spielSeite({ ...opts });
  daten(s.m, opts.daten);
  await geheZu(s, hash);
  await s.flush(10);
  return s;
}

const zeilen = (s) => s.qa('[data-liste="kapitel"] [data-kapitel]');
const knopfDerZeile = (s, i) => s.q(`[data-liste="kapitel"] [data-kapitel="${i}"] [data-abspielen]`);
const dlg = (s) => s.q('dialog.player');
const oeffneVoll = async (s) => { s.q('.mini .mopen').click(); await s.flush(8); return dlg(s); };

/* ------------------------------------------------------------------ reine Funktionen */

test('kapitelVon: Titel nur aus Zahlen heißt „Kapitel 1“, Länge aus dem nächsten Start und der Gesamtdauer, weniger als zwei Kapitel: keine Liste', () => {
  const k = P.kapitelVon({ name: 'x', dauer_s: 600, kapitel: EINGEBETTET });
  assert.deepEqual(k.map((x) => x.titel), ['Kapitel 1', 'Der Hafen', 'Der Sturm']);
  assert.deepEqual(k.map((x) => x.laenge_s), [169, 231, 200]);
  assert.deepEqual(k.map((x) => x.nr), [1, 2, 3]);
  assert.equal(P.kapitelVon({ name: 'x', dauer_s: 600, kapitel: [{ titel: 'A', start_s: 0 }] }).length, 0);
  assert.equal(P.kapitelVon({ name: 'x' }).length, 0);
  assert.equal(P.kapitelVon({ name: 'x', kapitel: [{ titel: '', start_s: 0 }, { titel: '  ', start_s: 5 }] })[1].titel, 'Kapitel 2');
  assert.equal(P.kapitelVon({ name: 'x', kapitel: [{ titel: 'A', start_s: 0 }, { titel: 'B', start_s: 5 }] })[1].laenge_s, null, 'ohne Dauer keine Länge');
  assert.equal(P.kapitelAb(k[1]), 'ab 2:49 · 3:51');
  assert.equal(P.kapitelAb({ start_s: 61, laenge_s: null }), 'ab 1:01');
});

test('kapitelIndex und kapitelZiel: eingebettet über die Zeit, Ordner-Folge über den Track', () => {
  const f = { name: 'buch', art: 'ordner', tracks: 3, spuren_s: [100, 120, 80], dauer_s: 300, kapitel: IM_ORDNER };
  const k = P.kapitelVon(f);
  assert.equal(P.kapitelIndex(k, f, 0, 50), 0);
  assert.equal(P.kapitelIndex(k, f, 1, 10), 1);
  assert.equal(P.kapitelIndex(k, f, 1, 60), 2, 'Track 1 ab 60 s ist global 160');
  assert.equal(P.kapitelIndex(k, f, 2, 0), 3);
  assert.deepEqual(P.kapitelZiel(f, k[1]), { track: 1, offset: 0 });
  assert.deepEqual(P.kapitelZiel(f, k[2]), { track: 1, offset: 60 });
  assert.deepEqual(P.kapitelZiel(f, k[3]), { track: 2, offset: 0 });
  const ohneSpuren = { ...f, spuren_s: undefined };
  assert.equal(P.kapitelIndex(P.kapitelVon(ohneSpuren), ohneSpuren, 2, 5), 3, 'ohne Track-Längen entscheidet der Track');
  const e = { name: 'x', dauer_s: 600, kapitel: EINGEBETTET };
  assert.deepEqual(P.kapitelZiel(e, P.kapitelVon(e)[1]), { track: 0, offset: 169 });
  assert.equal(P.kapitelIndex(P.kapitelVon(e), e, 0, 399), 1);
  assert.equal(P.kapitelIndex(P.kapitelVon(e), e, 0, 400), 2);
});

test('hatKapitelAbschnitt: nur ein Hörbuch aus einer Folge mit Kapiteln (AM12)', () => {
  const kap = { kapitel: EINGEBETTET, dauer_s: 600 };
  assert.equal(hatKapitelAbschnitt({ art: 'hoerbuch', folgen: [{ name: 'a', ...kap }] }), true);
  assert.equal(hatKapitelAbschnitt({ art: 'hoerbuch', folgen: [{ name: 'a', ...kap }, { name: 'b' }] }), false, 'mehrere Folgen: nur im Player');
  assert.equal(hatKapitelAbschnitt({ art: 'hoerspiel', folgen: [{ name: 'a', ...kap }] }), false);
  assert.equal(hatKapitelAbschnitt({ art: 'hoerbuch', folgen: [{ name: 'a' }] }), false, 'ohne Kapitel bleibt die Folgenliste');
  assert.equal(P.serieHatKapitel({ folgen: [{ name: 'a' }, { name: 'b', ...kap }] }), true);
  assert.equal(P.serieHatKapitel({ folgen: [{ name: 'a' }] }), false);
});

/* ------------------------------------------------------------------ Serienseite */

mit('Hörbuch aus einer Folge: der Abschnitt „Kapitel“ steht statt der Folgenliste, Zeilen ohne eigenen Play-Knopf', async () => {
  const s = await seiteMit('#serie-hb');
  assert.equal(s.q('[data-liste="folgen"]'), null, 'keine Folgenliste');
  assert.equal(s.q('.se-kopfzeile .se-abschnitt').textContent, KAPITEL.abschnitt);
  const z = zeilen(s);
  assert.equal(z.length, 3);
  assert.match(z[0].textContent, /Kapitel 1/, 'ein Titel „1“ heißt „Kapitel 1“');
  assert.match(z[1].textContent, /Der Hafen/);
  assert.match(z[1].textContent, /ab 2:49 · 3:51/);
  for (const x of z) {
    assert.equal(x.querySelectorAll('button').length, 1, 'ein einziger Knopf: die ganze Zeile, kein eigener Play-Knopf, kein „⋯“');
    assert.ok(x.querySelector('button.se-zeilenknopf[data-abspielen]'));
  }
  assert.equal(s.q('[data-liste="kapitel"] [aria-current="true"]'), null, 'ohne gemerkte Stelle ist keines markiert');
});

mit('mehrere Folgen: die Serienseite zeigt die Folgenliste, Kapitel nur im Player (AM12)', async () => {
  const s = await seiteMit('#serie-mehr');
  assert.ok(s.q('[data-liste="folgen"]'));
  assert.equal(s.q('[data-liste="kapitel"]'), null);
  assert.equal(s.qa('[data-liste="folgen"] [data-folge]').length, 2);
});

mit('Hörbuch ohne Kapitel in der Folge: die Folgenliste bleibt', async () => {
  const s = await spielSeite();
  daten(s.m);
  delete s.m.backend.serien.hb.folgen[0].kapitel;
  await geheZu(s, '#serie-hb'); await s.flush(10);
  assert.ok(s.q('[data-liste="folgen"]'));
  assert.equal(s.q('[data-liste="kapitel"]'), null);
});

mit('die Hörstelle markiert das Kapitel (`aria-current`), die davor tragen das Häkchen und „gehört“', async () => {
  const s = await spielSeite();
  daten(s.m);
  s.m.backend.hoerstellen.hb = { zeit: '2026-11-14T12:00:00Z', folge: 'hb.m4b', folgen: { 'hb.m4b': { p: 450, d: 600, t: '2026-11-14T12:00:00Z', fertig: false } } };
  await geheZu(s, '#serie-hb'); await s.flush(10);
  const z = zeilen(s);
  assert.deepEqual(z.map((x) => x.getAttribute('aria-current')), [null, null, 'true']);
  assert.ok(z[0].querySelector('.se-ok svg') && z[1].querySelector('.se-ok svg'), 'Häkchen bei den gehörten');
  assert.match(z[0].textContent, /gehört/);
  assert.match(z[2].textContent, /hier weiter/);
  assert.match(knopfDerZeile(s, 2).getAttribute('aria-label'), /aktuelles Kapitel/);
});

mit('ist alles gehört, tragen alle ein Häkchen und keines ist markiert', async () => {
  const s = await spielSeite();
  daten(s.m);
  s.m.backend.hoerstellen.hb = { zeit: '2026-11-14T12:00:00Z', folge: 'hb.m4b', folgen: { 'hb.m4b': { p: 600, d: 600, t: '2026-11-14T12:00:00Z', fertig: true } } };
  await geheZu(s, '#serie-hb'); await s.flush(10);
  assert.equal(s.qa('[data-liste="kapitel"] .se-ok').length, 3);
  assert.equal(s.q('[data-liste="kapitel"] [aria-current="true"]'), null);
});

mit('Kapitelsprung (eingebettet): Tipp auf die Zeile startet dort (`currentTime = start_s`), spielt, ein anderes Kapitel springt ohne neues `audio/bereit`', async () => {
  const s = await seiteMit('#serie-hb');
  knopfDerZeile(s, 1).click();
  await s.flush(12);
  const a = s.audio();
  assert.equal(bereitAufrufe(s).length, 1);
  assert.equal(bereitAufrufe(s)[0].track, undefined, 'eine Datei: kein `track`');
  lade(a, 600);
  await s.flush(8);
  assert.equal(a.currentTime, 169, 'der Start liegt am Kapitel');
  assert.equal(s.sp.spielt, true);
  assert.equal(s.q('[data-liste="kapitel"] [aria-current="true"]').dataset.kapitel, '1');
  knopfDerZeile(s, 2).click();
  await s.flush(8);
  assert.equal(a.currentTime, 400);
  assert.equal(bereitAufrufe(s).length, 1, 'derselbe Link, nur die Zeit ändert sich');
  assert.equal(s.sp.spielt, true);
  assert.equal(s.q('[data-liste="kapitel"] [aria-current="true"]').dataset.kapitel, '2');
  const sets = setAufrufe(s);
  assert.equal(sets.at(-1).position_s, 400, 'die Hörstelle merkt die Stelle im Kapitel');
  assert.equal(sets.at(-1).track, undefined);
});

mit('Kapitelsprung aus der Pause: springt und spielt weiter', async () => {
  const s = await seiteMit('#serie-hb');
  knopfDerZeile(s, 0).click();
  await s.flush(12);
  const a = s.audio();
  lade(a, 600); await s.flush(8);
  a.pause(); await s.flush(6);
  assert.equal(s.sp.spielt, false);
  knopfDerZeile(s, 1).click();
  await s.flush(8);
  assert.equal(a.currentTime, 169);
  assert.equal(s.sp.spielt, true, 'nach dem Tipp läuft der Ton wieder');
});

mit('AM13: Tipp auf das Kapitel, das geladen ist, öffnet nur die Vollansicht und ändert am Ton nichts (läuft und pausiert)', async () => {
  const s = await seiteMit('#serie-hb');
  knopfDerZeile(s, 1).click();
  await s.flush(12);
  const a = s.audio();
  lade(a, 600); await s.flush(8);
  const bis = setAufrufe(s).length;
  const aufrufe = bereitAufrufe(s).length;
  assert.equal(dlg(s), null);
  assert.match(knopfDerZeile(s, 1).getAttribute('aria-label'), /Player öffnen/);
  knopfDerZeile(s, 1).click();
  await s.flush(8);
  assert.ok(dlg(s)?.hasAttribute('open'), 'die Vollansicht ist offen');
  assert.equal(s.sp.spielt, true, 'der Ton läuft weiter');
  assert.equal(a.currentTime, 169, 'keine Bewegung');
  assert.equal(bereitAufrufe(s).length, aufrufe);
  // pausiert: ebenso
  s.sp.schliessen = () => {};
  s.sp.offen = false; s.sp.ctx.neuZeichnen(); await s.flush(6);
  a.pause(); await s.flush(6);
  knopfDerZeile(s, 1).click();
  await s.flush(8);
  assert.ok(dlg(s)?.hasAttribute('open'));
  assert.equal(s.sp.spielt, false, 'pausiert bleibt pausiert');
  assert.equal(a.currentTime, 169);
  assert.ok(setAufrufe(s).length >= bis);
});

mit('Kapitelsprung bei einer Ordner-Folge: neuer Link mit `track`, dann die Zeit im Track; die Hörstelle trägt `track` und `position_s`', async () => {
  const s = await seiteMit('#serie-buch');
  assert.equal(zeilen(s).length, 4);
  knopfDerZeile(s, 2).click(); // „Mitte“: Track 1, 60 s im Track
  await s.flush(12);
  const b = bereitAufrufe(s);
  assert.equal(b.length, 1);
  assert.equal(b[0].track, 1);
  const a = s.audio();
  assert.match(a.getAttribute('src'), /\/api\/tobibox\/audio\/buch\/buch\?track=1&authSig=/, 'neue Signatur je Track');
  lade(a, 120);
  await s.flush(8);
  assert.equal(a.currentTime, 60);
  assert.equal(s.q('[data-liste="kapitel"] [aria-current="true"]').dataset.kapitel, '2');
  knopfDerZeile(s, 3).click(); // „Drei“: anderer Track
  await s.flush(12);
  assert.equal(bereitAufrufe(s).length, 2);
  assert.equal(bereitAufrufe(s)[1].track, 2);
  assert.match(a.getAttribute('src'), /track=2&authSig=/);
  a.currentTime = 0; // eine neue Quelle beginnt im Browser bei 0 (der Ersatz setzt es nicht von selbst zurück)
  lade(a, 80);
  await s.flush(8);
  assert.equal(a.currentTime, 0);
  a.pause();
  await s.flush(6);
  const set = setAufrufe(s).at(-1);
  assert.equal(set.track, 2);
  assert.equal(set.position_s, 0);
  // zurück in den Track davor, im selben Track: nur die Zeit
  knopfDerZeile(s, 0).click();
  await s.flush(12);
  assert.equal(bereitAufrufe(s)[2].track, 0);
});

mit('Kapitelsprung ohne laufenden Player auf einer Folge mit Hörstelle: das Kapitel gewinnt gegen die gemerkte Stelle', async () => {
  const s = await spielSeite();
  daten(s.m);
  s.m.backend.hoerstellen.hb = { zeit: '2026-11-14T12:00:00Z', folge: 'hb.m4b', folgen: { 'hb.m4b': { p: 450, d: 600, t: '2026-11-14T12:00:00Z', fertig: false } } };
  await geheZu(s, '#serie-hb'); await s.flush(10);
  knopfDerZeile(s, 0).click();
  await s.flush(12);
  const a = s.audio();
  lade(a, 600); await s.flush(8);
  assert.equal(a.currentTime, 0);
});

/* ------------------------------------------------------------------ Player */

mit('Player: Zeile „Kapitel 2: Der Hafen (2 von 3)“ unter dem Titel und Knopf „Kapitel“ neben „Sperren“', async () => {
  const s = await seiteMit('#serie-hb');
  knopfDerZeile(s, 1).click();
  await s.flush(12);
  const a = s.audio();
  lade(a, 600); await s.flush(8);
  const d = await oeffneVoll(s);
  assert.equal(d.querySelector('[data-pkap]').textContent, 'Kapitel 2: Der Hafen (2 von 3)');
  const knoepfe = [...d.querySelectorAll('.speed button')].map((b) => b.textContent.trim());
  assert.deepEqual(knoepfe, [PLAYER.voll.kapitel, PLAYER.voll.sperren]);
  zeit(a, 405); await s.flush(6);
  assert.equal(d.querySelector('[data-pkap]').textContent, 'Kapitel 3: Der Sturm (3 von 3)', 'die Zeile folgt der Stelle');
  zeit(a, 10); await s.flush(6);
  assert.equal(d.querySelector('[data-pkap]').textContent, 'Kapitel 1 (1 von 3)', 'ein Titel „Kapitel 1“ steht nicht doppelt');
});

test('AM22: beginnt der Titel selbst mit „Kapitel“, steht kein zweites „Kapitel n:“ davor (Aria-Text); Gegenprobe: sprechender Titel behält es', () => {
  const k = P.kapitelVon({ name: 'x', dauer_s: 600, kapitel: [{ titel: 'Kapitel 1 & Kapitel 2.1', start_s: 0 }, { titel: 'kapitel 2.2', start_s: 100 }, { titel: 'Der Hafen', start_s: 200 }, { titel: '', start_s: 300 }] });
  assert.equal(P.kapitelAria(k[0], false), 'Kapitel 1 & Kapitel 2.1, ab 0:00, abspielen');
  assert.equal(P.kapitelAria(k[1], false), 'kapitel 2.2, ab 1:40, abspielen');
  assert.equal(P.kapitelAria(k[2], false), 'Kapitel 3: Der Hafen, ab 3:20, abspielen');
  assert.equal(P.kapitelAria(k[3], false), 'Kapitel 4, ab 5:00, abspielen', 'Rückfall „Kapitel n“ steht nicht doppelt');
  assert.equal(P.beginntMitKapitel('Kapitelweise'), false);
  assert.equal(P.beginntMitKapitel('Kapitel'), true);
});

mit('AM22: Zeile im Player zeigt „Kapitel 2.2 (2 von 3)“ ohne zweites „Kapitel 2:“', async () => {
  const s = await spielSeite({});
  s.m.backend.serien.hb = { id: 'hb', name: 'Das Buch', typ: 'normal', ordner: 'Hb', pruefen: false, hinweise: [], art: 'hoerbuch', dauer_s: 600, cover_stand: null,
    folgen: [folge('hb.m4b', 'Das Buch', { dauer_s: 600, kapitel: [{ titel: 'Kapitel 1.1', start_s: 0 }, { titel: 'Kapitel 2.2', start_s: 169 }, { titel: 'Der Sturm', start_s: 400 }] })] };
  await geheZu(s, '#serie-hb');
  await s.flush(10);
  knopfDerZeile(s, 1).click();
  await s.flush(12);
  const a = s.audio();
  lade(a, 600); await s.flush(8);
  const d = await oeffneVoll(s);
  assert.equal(d.querySelector('[data-pkap]').textContent, 'Kapitel 2.2 (2 von 3)');
  zeit(a, 405); await s.flush(6);
  assert.equal(d.querySelector('[data-pkap]').textContent, 'Kapitel 3: Der Sturm (3 von 3)', 'Gegenprobe: sprechender Titel behält das Präfix');
  assert.match(knopfDerZeile(s, 1).getAttribute('aria-label'), /^Kapitel 2\.2, ab 2:49/);
});

mit('Player: das Blatt „Kapitel“ listet alle, markiert das aktuelle; Tipp springt, spielt weiter und schließt das Blatt', async () => {
  const s = await seiteMit('#serie-hb');
  knopfDerZeile(s, 1).click();
  await s.flush(12);
  const a = s.audio();
  lade(a, 600); await s.flush(8);
  const d = await oeffneVoll(s);
  d.querySelector('[data-p="kapitel"]').click();
  await s.flush(10);
  const blatt = s.q('dialog.blatt[open]');
  assert.ok(blatt);
  const z = [...blatt.querySelectorAll('[data-kapitel]')];
  assert.equal(z.length, 3);
  assert.deepEqual(z.map((x) => x.getAttribute('aria-current')), [null, 'true', null]);
  assert.match(z[1].textContent, /ab 2:49 · 3:51/);
  assert.match(z[1].textContent, /läuft/);
  assert.match(z[0].textContent, /gehört/);
  assert.ok(z[0].querySelector('svg'), 'Häkchen');
  assert.equal(s.el.shadowRoot.activeElement, z[1], 'der Fokus liegt auf dem aktuellen Kapitel');
  a.pause(); await s.flush(6);
  z[2].click();
  await s.flush(12);
  assert.equal(a.currentTime, 400);
  assert.equal(s.sp.spielt, true, 'springen und weiterspielen');
  assert.equal(s.q('dialog.blatt[open]'), null, 'das Blatt schließt');
});

mit('Player: die Sperre sperrt den Knopf „Kapitel“', async () => {
  const s = await seiteMit('#serie-hb');
  knopfDerZeile(s, 1).click();
  await s.flush(12);
  lade(s.audio(), 600); await s.flush(8);
  const d = await oeffneVoll(s);
  assert.equal(d.querySelector('[data-p="kapitel"]').disabled, false);
  d.querySelector('[data-p="lock"]').click();
  await s.flush(8);
  assert.equal(d.querySelector('[data-p="kapitel"]').disabled, true);
  d.querySelector('[data-p="kapitel"]').click();
  await s.flush(6);
  assert.equal(s.q('dialog.blatt[open]'), null, 'gesperrt: kein Blatt');
});

mit('Player: eine Serie mit mehreren Folgen, nur eine mit Kapiteln: Zeile und Knopf bleiben stehen (Höhe fest), bei der anderen Folge leer und gesperrt', async () => {
  const s = await seiteMit('#serie-mehr');
  s.q('[data-reinhoeren]').click();
  await s.flush(12);
  const a = s.audio();
  lade(a, 600); await s.flush(8);
  const d = await oeffneVoll(s);
  assert.match(d.querySelector('[data-pkap]').textContent, /^Kapitel 1 \(1 von 3\)$/);
  assert.equal(d.querySelector('[data-p="kapitel"]').disabled, false);
  d.querySelector('[data-p="next"]').click();
  await s.flush(12);
  lade(s.audio(), 100); await s.flush(8);
  assert.equal(s.sp.folge.name, 'b.mp3');
  assert.ok(d.querySelector('[data-pkap]'), 'die Zeile ist noch da (dieselbe Lage)');
  assert.equal(d.querySelector('[data-pkap]').textContent, '');
  assert.equal(d.querySelector('[data-p="kapitel"]').disabled, true);
  assert.equal(d.querySelector('[data-p="kapitel"]').parentElement, d.querySelector('[data-p="lock"]').parentElement, 'beide Knöpfe in einer Reihe');
});

mit('Player, Gegenprobe: ohne Kapitel in der Serie gibt es weder Zeile noch Knopf', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  s.q('[data-reinhoeren]').click();
  await s.flush(12);
  lade(s.audio(), 120); await s.flush(8);
  const d = await oeffneVoll(s);
  assert.equal(d.querySelector('[data-pkap]'), null);
  assert.equal(d.querySelector('[data-p="kapitel"]'), null);
  assert.equal(d.querySelector('[data-pnote]'), null, 'auch kein Platz für die Hörprobe, wenn keine Kopie nötig ist');
});

mit('Player, Ordner-Folge mit Kapiteln: der Sprung im Blatt wechselt den Track (neuer Link)', async () => {
  const s = await seiteMit('#serie-buch');
  s.q('[data-reinhoeren]').click();
  await s.flush(12);
  lade(s.audio(), 100); await s.flush(8);
  const d = await oeffneVoll(s);
  assert.equal(d.querySelector('[data-pkap]').textContent, 'Kapitel 1 (1 von 4)');
  d.querySelector('[data-p="kapitel"]').click();
  await s.flush(10);
  [...s.qa('dialog.blatt[open] [data-kapitel]')][3].click();
  await s.flush(12);
  assert.equal(bereitAufrufe(s).at(-1).track, 2);
  lade(s.audio(), 80); await s.flush(8);
  assert.equal(s.audio().currentTime, 0);
  assert.equal(d.querySelector('[data-pkap]').textContent, 'Kapitel 4: Drei (4 von 4)');
});

/* ------------------------------------------------------------------ Hörprobe wird vorbereitet */

mit('„wird_vorbereitet“ (AM20): keine Karte, der Satz steht in der Zeile unter dem großen Knopf; nach 15 s fragt die Seite erneut und startet bei „bereit“ (Zustand nie aus dem Fehler des `<audio>`)', async (t) => {
  const s = await spielSeite();
  const f0 = s.m.backend.serien.s1.folgen[0];
  s.m.backend.serien.s1.folgen.forEach((f) => { f.hoerkopie = { zustand: 'nicht_angelegt' }; });
  await geheZu(s, '#serie-s1'); await s.flush(10);
  const vorher = s.q('[data-rein-zusatz]').textContent;
  assert.ok(vorher && vorher !== PLAYER.voll.vorbereitet, 'vor dem Tipp steht die normale Zeile');
  assert.equal(s.q('[data-hoerprobe-platz]'), null, 'kein reservierter Platz');
  let n = 0;
  s.m.on('tobibox/audio/bereit', (m) => { n += 1; return n === 1 ? { zustand: 'wird_vorbereitet', warte_s: 60, position: 1 } : { zustand: 'bereit', pfad: `/api/tobibox/audio/s1/${m.folge}?authSig=x`, quelle: 'kopie' }; });
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    s.q('[data-reinhoeren]').click();
    await mikro(s);
    assert.equal(s.q('[data-rein-zusatz]').textContent, PLAYER.voll.vorbereitet, 'der Satz steht in der Zeile unter dem Knopf');
    assert.equal(s.qa('[data-rein-zusatz]').length, 1, 'eine Zeile, kein zweiter Block');
    assert.equal(s.q('[data-karte="hoerprobe"]'), null, 'keine Karte (AM20)');
    assert.equal(s.q('[data-hoerprobe-platz]'), null);
    assert.equal(s.q('.se-hp, .se-hp-karte'), null);
    assert.ok(f0);
    t.mock.timers.tick(14999);
    await mikro(s);
    assert.equal(n, 1);
    t.mock.timers.tick(1);
    await mikro(s);
    assert.equal(n, 2);
    assert.equal(bereitAufrufe(s).at(-1).vorbereiten, false);
    assert.equal(s.audio().getAttribute('src'), `/api/tobibox/audio/s1/${f0.name}?authSig=x`, 'bei „bereit“ startet es');
    assert.notEqual(s.q('[data-rein-zusatz]').textContent, PLAYER.voll.vorbereitet, 'danach wieder die normale Zeile');
  } finally { t.mock.timers.reset(); }
});

mit('Hörprobe (AM20): ohne Warten steht die normale Zeile, nie Karte oder Platz (auch bei Folgen, die eine Kopie brauchen); eine andere Serie im Wartezustand ändert die Zeile nicht', async (t) => {
  const s = await spielSeite({ hash: '#serie-s1' });
  assert.equal(s.q('[data-hoerprobe-platz]'), null);
  assert.equal(s.q('[data-karte="hoerprobe"]'), null);
  assert.notEqual(s.q('[data-rein-zusatz]').textContent, PLAYER.voll.vorbereitet);
  s.m.backend.serien.s1.folgen.forEach((f) => { f.hoerkopie = { zustand: 'wartet' }; });
  await geheZu(s, '#serie-s1'); await s.flush(10);
  assert.equal(s.q('[data-hoerprobe-platz]'), null, 'auch mit Folgen, die eine Kopie brauchen, bleibt kein Platz frei');
  assert.notEqual(s.q('[data-rein-zusatz]').textContent, PLAYER.voll.vorbereitet);
  void t;
});

mit('Hörprobe: die Vollansicht hat den Platz für den Satz, der Satz selbst steht nur während des Wartens', async (t) => {
  const s = await spielSeite();
  s.m.backend.serien.s1.folgen.forEach((f) => { f.hoerkopie = { zustand: 'wartet' }; });
  await geheZu(s, '#serie-s1'); await s.flush(10);
  s.m.on('tobibox/audio/bereit', () => ({ zustand: 'wird_vorbereitet', warte_s: 60, position: 1 }));
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    s.q('[data-reinhoeren]').click();
    await mikro(s);
    s.q('.mini .mopen').click();
    await mikro(s);
    const note = dlg(s).querySelector('[data-pnote]');
    assert.ok(note);
    assert.equal(note.textContent, PLAYER.voll.vorbereitet);
    assert.ok(note.hasAttribute('data-vorbereitet'));
  } finally { t.mock.timers.reset(); }
});

mit('Hörprobe „fehlt“: Meldung, keine Karte', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  s.m.on('tobibox/audio/bereit', () => ({ zustand: 'fehlt', grund: 'zu_lang' }));
  s.q('[data-reinhoeren]').click();
  await s.flush(12);
  assert.ok(s.qa('.toast .tmsg').map((x) => x.textContent).includes(HOERPROBE.keine_datei));
  assert.equal(s.q('[data-karte="hoerprobe"]'), null);
});

/* ------------------------------------------------------------------ Hörkopie neu erzeugen für eine Serie, Technik */

mit('Menü der Serie (Administrator): „Hörkopie neu erzeugen“ nur bei einer Folge mit Fehler und mit der Fähigkeit `hoerkopie`', async () => {
  const mitFae = [...REIN, 'hoerkopie'];
  const s = await spielSeite({ faehigkeiten: mitFae });
  s.m.backend.serien.s1.folgen[0].hoerkopie = { zustand: 'fehler', grund: 'zu_lang' };
  await geheZu(s, '#serie-s1'); await s.flush(10);
  s.q('[data-menue-serie]').click();
  await s.flush(8);
  const punkt = s.q('dialog[open] [data-menue="hoerkopie"]');
  assert.ok(punkt);
  assert.equal(punkt.textContent, SERIE.menue.hoerkopie);
  punkt.click();
  await s.flush(10);
  const c = s.m.aufrufe('tobibox/hoerkopie/neu_erzeugen');
  assert.equal(c.length, 1);
  assert.equal(c[0].serie_id, 's1');
  // ohne Fehler und ohne Fähigkeit: kein Punkt
  const t2 = await spielSeite({ hash: '#serie-s1', faehigkeiten: mitFae });
  t2.q('[data-menue-serie]').click(); await t2.flush(8);
  assert.equal(t2.q('dialog[open] [data-menue="hoerkopie"]'), null);
  const t3 = await spielSeite({ faehigkeiten: REIN });
  t3.m.backend.serien.s1.folgen[0].hoerkopie = { zustand: 'fehler' };
  await geheZu(t3, '#serie-s1'); await t3.flush(10);
  t3.q('[data-menue-serie]').click(); await t3.flush(8);
  assert.equal(t3.q('dialog[open] [data-menue="hoerkopie"]'), null);
});

mit('Serienseite (AM27): Administratoren sehen bei fehlgeschlagener Hörkopie den Grund kurz in der Folgenzeile, andere nichts', async () => {
  const mitFae = [...REIN, 'hoerkopie'];
  const erwartet = { unplausibel: 'Keine Hörprobe: Datei wirkt beschädigt', zu_lang: 'Keine Hörprobe: zu lang', zeitgrenze: 'Keine Hörprobe: Umwandeln dauerte zu lange', kein_speicher: 'Keine Hörprobe: kein Platz', ffmpeg_fehlt: 'Keine Hörprobe: Umwandler fehlt', unbekannt_xyz: 'Keine Hörprobe' };
  for (const [grund, text] of Object.entries(erwartet)) {
    const s = await spielSeite({ faehigkeiten: mitFae });
    s.m.backend.serien.s1.folgen[0].hoerkopie = { zustand: 'fehler', grund };
    await geheZu(s, '#serie-s1'); await s.flush(10);
    const z = s.q('[data-folge] [data-keine-probe]');
    assert.ok(z, grund);
    assert.equal(z.textContent.trim(), text, grund);
    assert.equal(s.qa('[data-keine-probe]').length, 1, 'nur die Folge mit Fehler');
  }
  const ohneGrund = await spielSeite({ faehigkeiten: mitFae });
  ohneGrund.m.backend.serien.s1.folgen[0].hoerkopie = { zustand: 'fehler' };
  await geheZu(ohneGrund, '#serie-s1'); await ohneGrund.flush(10);
  assert.equal(ohneGrund.q('[data-keine-probe]').textContent.trim(), 'Keine Hörprobe');
  const alltag = await spielSeite({ faehigkeiten: mitFae, darf: true, istAdmin: false });
  alltag.m.backend.serien.s1.folgen[0].hoerkopie = { zustand: 'fehler', grund: 'unplausibel' };
  await geheZu(alltag, '#serie-s1'); await alltag.flush(10);
  assert.ok(alltag.q('[data-folge]'));
  assert.equal(alltag.q('[data-keine-probe]'), null, 'Nicht-Administratoren sehen nichts Neues');
  const fertig = await spielSeite({ faehigkeiten: mitFae });
  fertig.m.backend.serien.s1.folgen[0].hoerkopie = { zustand: 'wartet' };
  await geheZu(fertig, '#serie-s1'); await fertig.flush(10);
  assert.equal(fertig.q('[data-keine-probe]'), null);
});

const ALLE = [...FAEHIGKEITEN, 'konfig_lesen', 'konfig_staende', 'hoerkopie', 'einstellungen', 'eingang_entfernen', 'zuordnung_uid'];
async function technik(opts = {}, schlange) {
  const s = await seite({ hash: '', faehigkeiten: ALLE, ...opts });
  if (schlange !== undefined) {
    s.m.on('tobibox/hello', () => ({ v: 1, version: '0.1.0', darf_schreiben: true, faehigkeiten: opts.faehigkeiten || ALLE, boxen: [], konfig: s.m.backend.konfig, grenzen: { hoerkopie_schlange: schlange } }));
  }
  await geheZu(s, '#technik-speicher');
  await s.flush(12);
  return s;
}

mit('Technik: der Zähler der Hörkopie-Warteschlange und der Knopf nur mit der Fähigkeit `hoerkopie`', async () => {
  const s = await technik({}, { dateien: 3, dateien_max: 20, bytes: 1.4e9, bytes_max: 50e9 });
  assert.equal(s.q('[data-hoerkopien-schlange]').textContent, '3 von höchstens 20 Dateien · 1,4 von höchstens 50 GB');
  assert.ok(s.q('[data-aktion="hoerkopien"]'));
  const ohne = await technik({ faehigkeiten: ALLE.filter((f) => f !== 'hoerkopie') }, { dateien: 3, dateien_max: 20, bytes: 1.4e9, bytes_max: 50e9 });
  assert.equal(ohne.q('[data-hoerkopien-schlange]'), null);
  assert.equal(ohne.q('[data-aktion="hoerkopien"]'), null);
  const leer = await technik({});
  assert.equal(leer.q('[data-hoerkopien-schlange]'), null, 'ohne Angabe im Backend zeigt die Seite nichts');
  assert.ok(leer.q('[data-aktion="hoerkopien"]'));
  const kaputt = await technik({}, { dateien: 'drei' });
  assert.equal(kaputt.q('[data-hoerkopien-schlange]'), null);
});

test('Texte: die Sätze des Kapitel-Designs („12 Kapitel. Tippe auf ein Kapitel …“) kommen nicht zurück (AM16)', async () => {
  const { readFileSync } = await import('node:fs');
  const quelle = readFileSync(new URL('../../custom_components/tobibox/frontend/texte.js', import.meta.url), 'utf8');
  for (const satz of ['Tippe auf ein Kapitel', 'Im Player kannst du über das ganze Buch springen']) assert.ok(!quelle.includes(satz), satz);
  assert.equal(TECHNIK.aufraeumen.hoerkopien, 'Hörkopien neu erzeugen');
});

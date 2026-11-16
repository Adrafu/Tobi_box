/* Tests des Players (Pakete A8b, A8e, A7c; Design 5.12, 5.3, 5.2). Aufruf: node --test homeassistant/tests/frontend
 *
 * `HTMLMediaElement` ist ersetzt (player-helfer.mjs): jsdom spielt nichts ab. Geprüft: reine Funktionen (Ordner-Folgen über Tracks, Beschriftung des
 * Knopfs je Hörstelle), `audio/bereit` vor jedem Start (mit `folge`, nie `folge_id`), Fehler des `<audio>`-Elements führen zu neuem `audio/bereit`,
 * Link erneuern, nächste Datei im Voraus, Hörstelle gesammelt (10 s, sofort bei Pause und Sprung), Media-Session, Wischen auf und zu,
 * Neuladen ohne Ton, Tempo, Sperre (1,9 s entsperrt nicht, 2 s entsperrt), Reihe „Am Handy weiterhören“ und Fortschritt.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, taste, MIT_DOM } from './dom-helfer.mjs';
import { mockAudio, spielSeite, starteSerie, bereitAufrufe, setAufrufe, lade, zeit, ende, zeiger, mikro, REIN } from './player-helfer.mjs';

const P = await import('../../custom_components/tobibox/frontend/player.js');
const { PLAYER, FEHLER, HOERPROBE } = await import('../../custom_components/tobibox/frontend/texte.js');

/* Mit Medien-Ersatz; räumt danach auf. */
function mit(name, fn, opts = MIT_DOM) {
  test(name, opts, async (t) => {
    const au = await mockAudio();
    try { await fn(t, au); } finally { weg(); au.zurueck(); try { window.localStorage.clear(); } catch { /* ohne */ } }
  });
}

const dlg = (s) => s.q('dialog.player');
const alle = (s, sel) => s.qa(sel);
const toasts = (s) => s.qa('.toast .tmsg').map((x) => x.textContent);
const oeffneVoll = async (s) => { s.q('.mini .mopen').click(); await s.flush(8); return dlg(s); };

/* ------------------------------------------------------------------ reine Funktionen */

test('Ordner-Folgen: Tracks, Spuren, Zeitleiste über die ganze Folge, Sprung in einen anderen Track', () => {
  const buch = { name: 'buch', art: 'ordner', tracks: 3, spuren_s: [100, 120, 80], dauer_s: 300 };
  assert.equal(P.trackAnzahl(buch), 3);
  assert.equal(P.trackAnzahl({ art: 'datei', tracks: 1 }), 1);
  assert.equal(P.trackAnzahl({ art: 'ordner', tracks: 1 }), 1, 'ein Track ist keine Ordner-Folge im Sinn der Zeitleiste');
  assert.deepEqual(P.spurenVon(buch), [100, 120, 80]);
  assert.equal(P.spurenVon({ ...buch, spuren_s: [100, 120] }), null, 'unvollständig: nicht benutzen');
  assert.equal(P.gesamtVon(buch), 300);
  assert.equal(P.gesamtVon({ dauer_s: 66 }), 66);
  assert.equal(P.gesamtVon({}), null);
  assert.equal(P.globalPos(buch, 1, 20), 120);
  assert.equal(P.globalPos(buch, 2, 5), 225);
  assert.deepEqual(P.ortVon(buch, 0), { track: 0, offset: 0 });
  assert.deepEqual(P.ortVon(buch, 99), { track: 0, offset: 99 });
  assert.deepEqual(P.ortVon(buch, 100), { track: 1, offset: 0 });
  assert.deepEqual(P.ortVon(buch, 230), { track: 2, offset: 10 });
  assert.deepEqual(P.ortVon(buch, 9999), { track: 2, offset: 80 }, 'über das Ende: letzter Track, Ende');
  assert.deepEqual(P.ortVon({ name: 'x' }, 42), { track: 0, offset: 42 });
});

test('Beschriftung des Knopfs je Hörstelle: Reinhören, Hier weiterhören mit Zusatz, Noch einmal hören, Pause', () => {
  const folgen = [{ name: 'a', anzeige: 'Folge 1: Der Schatz', hoerstelle: { position_s: 100, fertig: true } }, { name: 'b', anzeige: 'Folge 2: Die alte Mühle' }, { name: 'c', anzeige: 'Folge 3: Das Fest' }];
  assert.deepEqual(P.knopfText({ name: 'S', folgen: folgen.map((f) => ({ name: f.name, anzeige: f.anzeige })) }), { art: 'rein', label: 'Reinhören', zusatz: 'Folge 1: Der Schatz' }); // AM15: die Zeile steht immer
  const weiter = P.knopfText({ name: 'S', hoerstelle: { folge: 'b' }, folgen: [folgen[0], { ...folgen[1], hoerstelle: { position_s: 47, fertig: false } }, folgen[2]] });
  assert.deepEqual(weiter, { art: 'weiter', label: 'Hier weiterhören', zusatz: 'Folge 2: Die alte Mühle · ab 0:47' });
  const naechste = P.hoerziel({ name: 'S', hoerstelle: { folge: 'a' }, folgen });
  assert.equal(naechste.art, 'weiter');
  assert.equal(naechste.folge.name, 'b', 'die zuletzt gehörte ist fertig: die nächste ungehörte');
  assert.equal(naechste.zeit, 0);
  const alles = P.knopfText({ name: 'S', hoerstelle: { folge: 'c' }, folgen: folgen.map((f) => ({ ...f, hoerstelle: { position_s: 1, fertig: true } })) });
  assert.deepEqual(alles, { art: 'nochmal', label: 'Noch einmal hören', zusatz: 'Folge 1: Der Schatz' });
  assert.deepEqual(P.knopfText({ name: 'S', folgen }, { spielt: true }), { art: 'pause', label: 'Pause', zusatz: 'Folge 2: Die alte Mühle · läuft' });
  assert.equal(P.knopfText({ name: 'S', folgen }, { spielt: true, aktuell: folgen[2] }).zusatz, 'Folge 3: Das Fest · läuft', 'die laufende Folge, nicht die der Hörstelle');
  assert.equal(P.knopfText({ name: 'Wiegenlied', folgen: [{ name: 'w', anzeige: 'Wiegenlied' }] }, { spielt: true }).zusatz, 'Wiegenlied · läuft', 'bei einer einzigen Folge der Name des Eintrags');
  const einzeln = P.knopfText({ name: 'Wiegenlied', hoerstelle: { folge: 'w' }, folgen: [{ name: 'w', anzeige: 'Wiegenlied', hoerstelle: { position_s: 61, fertig: false } }] });
  assert.equal(einzeln.zusatz, 'Wiegenlied · ab 1:01', 'bei einer einzigen Folge steht der Name des Eintrags');
  const fast0 = P.knopfText({ name: 'Wiegenlied', hoerstelle: { folge: 'w' }, folgen: [{ name: 'w', anzeige: 'Wiegenlied', hoerstelle: { position_s: 3, fertig: false } }] });
  assert.equal(fast0.zusatz, 'Wiegenlied', 'unter 5 s kein „ab …“');
  assert.equal(P.knopfText({ name: 'Wiegenlied', hoerstelle: { folge: 'w' }, folgen: [{ name: 'w', anzeige: 'Wiegenlied', hoerstelle: { position_s: 5, fertig: false } }] }).zusatz, 'Wiegenlied · ab 0:05');
  assert.equal(P.knopfText({ name: 'S', folgen: [] }), null);
});

test('weiterReihe und formatErlaubt', () => {
  const r = P.weiterReihe([{ serie_id: 'x', name: 'X', folge: 'f', anteil: 0.5, rest_s: 60 }, { serie_id: 'y', name: 'Y', folge: 'g', anteil: 0.1, rest_s: 10 }], [{ id: 'x', name: 'X', cover_stand: 'ab12cd34' }]);
  assert.deepEqual(r.map((s) => s.id), ['x', 'y']);
  assert.equal(r[0].cover_stand, 'ab12cd34');
  assert.equal(r[0].weiter.rest_s, 60);
  assert.equal(r[1].name, 'Y', 'ohne Kurzform: der Name aus der Liste');
  assert.equal(P.formatErlaubt({ canPlayType: () => '' }, 'a.mp3'), false);
  assert.equal(P.formatErlaubt({ canPlayType: (m) => (m === 'audio/mpeg' ? 'maybe' : '') }, 'a.MP3'), true);
  assert.equal(P.formatErlaubt({ canPlayType: () => '' }, 'Ordnername'), true, 'ohne Endung entscheidet der Server');
  assert.equal(P.formatErlaubt(null, 'a.ogg'), true);
});

/* ------------------------------------------------------------------ Starten, Leiste, Vollansicht */

mit('Reinhören: fragt audio/bereit mit `folge` (nie `folge_id`), setzt den signierten Pfad als src und zeigt die Leiste', async (t, au) => {
  const s = await spielSeite({ hash: '#serie-s1' });
  assert.ok(s.q('.mini').hidden, 'vorher keine Leiste');
  const a = await starteSerie(s);
  const b = bereitAufrufe(s);
  assert.equal(b.length, 1);
  assert.deepEqual({ ...b[0], id: undefined }, { id: undefined, type: 'tobibox/audio/bereit', serie_id: 's1', folge: 'folge-01.mp3' });
  assert.ok(!('folge_id' in b[0]), 'der Alias folge_id ist nur für das alte Testpanel');
  assert.ok(!('track' in b[0]), 'track nur bei Ordner-Folgen');
  assert.equal(a.getAttribute('src'), '/api/tobibox/audio/s1/folge-01.mp3?authSig=mock-1');
  assert.ok(au.aufrufe.some((x) => x.art === 'play'), 'startet nach dem Laden der Metadaten');
  assert.equal(s.q('.mini').hidden, false);
  assert.equal(s.q('.mini .mt').textContent, 'Der Rabe');
  assert.equal(s.q('.mini .ms').textContent, 'Die drei ???');
  assert.equal(s.q('.mini .mplay').getAttribute('aria-label'), 'Pause');
  assert.equal(s.q('.mini .mopen').getAttribute('aria-label'), 'Player öffnen: Der Rabe, Die drei ???');
  assert.equal(s.el.style.getPropertyValue('--minih'), '67px', 'die Höhe der Leiste geht an die Meldungen');
  assert.equal(s.q('[data-reinhoeren]').textContent.trim(), 'Pause');
});

mit('Leiste: Knopf schaltet Play und Pause, die Pause speichert die Stelle sofort (hoerstelle/set mit Länge der Datei)', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s);
  zeit(a, 33);
  s.q('.mini .mplay').click();
  await s.flush(6);
  assert.equal(s.q('.mini .mplay').getAttribute('aria-label'), 'Abspielen');
  const sets = setAufrufe(s);
  assert.equal(sets.length, 1);
  assert.deepEqual({ ...sets[0], id: undefined }, { id: undefined, type: 'tobibox/hoerstelle/set', serie_id: 's1', folge: 'folge-01.mp3', position_s: 33, dauer_s: 120 });
  s.q('.mini .mplay').click();
  await s.flush(6);
  assert.equal(s.q('.mini .mplay').getAttribute('aria-label'), 'Pause');
  assert.equal(s.q('.mini .mbar i').style.width, '27.5%', '33 von 120 Sekunden');
});

mit('Hörstelle: während der Wiedergabe höchstens alle 10 Sekunden, sofort bei Sprung und beim Schließen der Seite', async (t) => {
  const s = await spielSeite({ hash: '#serie-s1' });
  t.mock.timers.enable({ apis: ['Date'], now: 1_000_000 });
  try {
    const a = await starteSerie(s);
    zeit(a, 4);
    await mikro(s, 4);
    assert.equal(setAufrufe(s).length, 0, 'der Start zählt als Speicherung: die nächste frühestens nach 10 Sekunden');
    t.mock.timers.tick(9000);
    zeit(a, 13);
    await mikro(s, 4);
    assert.equal(setAufrufe(s).length, 0);
    t.mock.timers.tick(1500);
    zeit(a, 15);
    await mikro(s, 4);
    assert.equal(setAufrufe(s).length, 1, 'nach 10 Sekunden');
    zeit(a, 16);
    await mikro(s, 4);
    assert.equal(setAufrufe(s).length, 1);
    s.sp.sprung(30);
    await mikro(s, 4);
    assert.equal(setAufrufe(s).length, 2, 'ein Sprung speichert sofort');
    assert.equal(setAufrufe(s).at(-1).position_s, 46);
    window.dispatchEvent(new window.Event('pagehide'));
    await mikro(s, 4);
    assert.equal(setAufrufe(s).length, 3, 'beim Schließen der Seite sofort');
  } finally { t.mock.timers.reset(); }
});

mit('Vollansicht: Titel, „Eintrag · 1 von 3“, Zeitleiste mit aria-valuetext, ±30 s, Vorige und Nächste Folge, Griff, Schließen', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s);
  zeit(a, 101);
  const d = await oeffneVoll(s);
  assert.ok(d.hasAttribute('open'));
  assert.ok(s.el.hasAttribute('data-voll'), 'der Host weiß: der Player deckt die Seite (kein iOS-Blatt-Effekt)');
  assert.equal(d.querySelector('h2').textContent, 'Der Rabe');
  assert.equal(d.querySelector('[data-psub]').textContent, 'Die drei ??? · 1 von 3');
  assert.ok(d.querySelector('.grip'));
  const sl = d.querySelector('.pslider');
  assert.equal(sl.getAttribute('aria-label'), 'Position in der Folge');
  assert.equal(sl.getAttribute('max'), '120');
  assert.equal(sl.value, '101');
  assert.equal(sl.getAttribute('aria-valuetext'), '1:41 von 2:00');
  assert.equal(d.querySelector('[data-ptime]').textContent, '1:41');
  assert.equal(d.querySelector('[data-prest]').textContent, '−0:19');
  assert.equal(d.querySelector('#p-ansicht').textContent, 'Läuft gerade');
  const labels = [...d.querySelectorAll('.pctl button')].map((b) => b.getAttribute('aria-label'));
  assert.deepEqual(labels, ['Vorige Folge', '30 Sekunden zurück', 'Pause', '30 Sekunden vor', 'Nächste Folge']);
  assert.equal(d.querySelector('[data-p="prev"]').disabled, true, 'bei der ersten Folge gibt es keine vorige');
  d.querySelector('[data-p="back"]').click();
  assert.equal(a.currentTime, 71);
  d.querySelector('[data-p="fwd"]').click();
  assert.equal(a.currentTime, 101);
  assert.ok(d.querySelector('[data-p="more"]'), 'Tempo steht im „⋯“, nicht in der Hauptzeile');
  d.querySelector('[data-p="close"]').click();
  await s.flush(8);
  assert.equal(s.q('dialog.player'), null);
  assert.equal(s.el.hasAttribute('data-voll'), false);
  assert.equal(s.el.shadowRoot.activeElement, s.q('.mini .mopen'), 'der Fokus geht zur Leiste zurück');
});

mit('Vollansicht: der Regler springt (change), während des Ziehens zeigt die Zeit die Reglerstelle', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s);
  const d = await oeffneVoll(s);
  const sl = d.querySelector('.pslider');
  sl.value = '90';
  sl.dispatchEvent(new window.Event('input', { bubbles: true }));
  assert.equal(d.querySelector('[data-ptime]').textContent, '1:30');
  assert.equal(a.currentTime, 0, 'noch nicht gesprungen');
  zeit(a, 5);
  assert.equal(sl.value, '90', 'während des Ziehens überschreibt die Wiedergabe den Regler nicht');
  sl.dispatchEvent(new window.Event('change', { bubbles: true }));
  assert.equal(a.currentTime, 90);
  s.sp.seek(500);
  assert.equal(a.currentTime, 120, 'nicht über das Ende');
});

mit('Folgenwechsel: das Ende einer Folge startet die nächste (audio/bereit mit der nächsten Folge), nach der letzten ist Schluss', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s, 120);
  ende(a, 120);
  await s.flush(10);
  assert.deepEqual(bereitAufrufe(s).map((x) => x.folge), ['folge-01.mp3', 'folge-02.mp3']);
  assert.equal(setAufrufe(s).find((x) => x.fertig)?.folge, 'folge-01.mp3', 'die fertig gehörte Folge wird als fertig gespeichert');
  assert.equal(s.q('.mini .mt').textContent, 'Das Gespensterschloss');
  lade(a, 130);
  await s.flush(6);
  ende(a, 130);
  await s.flush(10);
  lade(a, 140);
  await s.flush(6);
  assert.equal(bereitAufrufe(s).length, 3);
  ende(a, 140);
  await s.flush(10);
  assert.equal(bereitAufrufe(s).length, 3, 'nach der letzten Folge kommt nichts mehr');
  assert.equal(s.q('.mini .mplay').getAttribute('aria-label'), 'Abspielen');
  assert.equal(s.q('.mini .mt').textContent, 'Der Super-Papagei');
});

mit('Vorige Folge: bei mehr als 5 Sekunden zuerst an den Anfang, sonst die vorige; Nächste Folge', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s);
  const d = await oeffneVoll(s);
  d.querySelector('[data-p="next"]').click();
  await s.flush(10);
  assert.equal(bereitAufrufe(s).at(-1).folge, 'folge-02.mp3');
  lade(a, 130);
  await s.flush(6);
  zeit(a, 40);
  s.q('dialog.player [data-p="prev"]').click();
  await s.flush(6);
  assert.equal(a.currentTime, 0, 'bei 40 s: zuerst an den Anfang');
  assert.equal(bereitAufrufe(s).length, 2);
  zeit(a, 3);
  s.q('dialog.player [data-p="prev"]').click();
  await s.flush(10);
  assert.equal(bereitAufrufe(s).at(-1).folge, 'folge-01.mp3', 'unter 5 s: die vorige Folge');
});

mit('Ordner-Folge: Tracks laufen ohne Unterbrechung der Zeitleiste, audio/bereit mit `track`, Sprung in einen anderen Track, Hörstelle mit Track', async () => {
  const s = await spielSeite({ hash: '#serie-buch' });
  const a = await starteSerie(s, 100);
  assert.deepEqual(bereitAufrufe(s).map((x) => x.track), [0], 'bei Ordner-Folgen wird der Track mitgeschickt');
  const d = await oeffneVoll(s);
  const sl = d.querySelector('.pslider');
  assert.equal(sl.getAttribute('max'), '300', 'die Zeitleiste läuft über das ganze Buch');
  zeit(a, 40);
  assert.equal(sl.value, '40');
  ende(a, 100);
  await s.flush(10);
  assert.deepEqual(bereitAufrufe(s).map((x) => x.track), [0, 1]);
  assert.match(a.getAttribute('src'), /\/api\/tobibox\/audio\/buch\/buch\?track=1&authSig=/);
  lade(a, 120);
  await s.flush(6);
  zeit(a, 20);
  assert.equal(sl.value, '120', 'Track 2 bei 20 s: 120 von 300');
  s.sp.seek(250); // Track 3, 30 s
  await s.flush(10);
  assert.equal(bereitAufrufe(s).at(-1).track, 2);
  lade(a, 80);
  await s.flush(6);
  assert.equal(a.currentTime, 30, 'nach dem Laden an der Stelle im Track');
  s.sp.sprung(0);
  await s.flush(4);
  const letzte = setAufrufe(s).at(-1);
  assert.equal(letzte.track, 2);
  assert.equal(letzte.position_s, 30);
  assert.equal(letzte.dauer_s, 80, 'die Länge der Datei, nicht des ganzen Buches');
  assert.equal(d.querySelector('[data-p="next"]').disabled, true, 'ein einziges Buch: keine nächste Folge');
});

mit('Sonderzeichen im Folgennamen: audio/bereit schickt den Namen unverändert, der signierte Pfad kodiert jedes Segment', async () => {
  const s = await spielSeite({ hash: '#serie-sonder' });
  const a = await starteSerie(s, 60);
  assert.equal(bereitAufrufe(s)[0].folge, 'Teil 1 #2 (Ende)?.mp3');
  assert.equal(a.getAttribute('src'), '/api/tobibox/audio/sonder/Teil%201%20%232%20(Ende)%3F.mp3?authSig=mock-1');
  s.sp.naechste();
  await s.flush(10);
  assert.match(bereitAufrufe(s)[1].folge, /^100% Mond\+Sterne&Rest\.mp3$/);
  assert.ok(a.getAttribute('src').startsWith('/api/tobibox/audio/sonder/100%25%20Mond%2BSterne%26Rest.mp3?'));
});

/* ------------------------------------------------------------------ Fehler und Zustände aus audio/bereit */

mit('Fehler des <audio>-Elements (401, 503, 404 sehen gleich aus) führen zu neuem audio/bereit; die Stelle bleibt', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s);
  zeit(a, 50);
  const alt = a.getAttribute('src');
  a.dispatchEvent(new window.Event('error'));
  await s.flush(10);
  assert.equal(bereitAufrufe(s).length, 2, 'neue Frage statt eines Versuchs mit dem alten Link');
  assert.notEqual(a.getAttribute('src'), alt, 'ein frischer signierter Pfad');
  lade(a, 120);
  await s.flush(6);
  assert.equal(a.currentTime, 50, 'an der Stelle weiter');
  assert.deepEqual(toasts(s), [], 'ein einzelner Fehler ist keine Meldung');
});

mit('Fehler bleiben es: nach zwei Versuchen „Das kann dieser Browser nicht abspielen“', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s);
  for (let i = 0; i < 3; i += 1) { a.dispatchEvent(new window.Event('error')); await s.flush(10); }
  assert.equal(bereitAufrufe(s).length, 3, 'ein Start und zwei neue Fragen, dann ist Schluss');
  assert.ok(toasts(s).includes(FEHLER.browser_spielt_nicht), toasts(s).join('|'));
  assert.equal(s.q('.mini .mplay').getAttribute('aria-label'), 'Abspielen');
});

mit('audio/bereit „wird_vorbereitet“: Hinweis, nach 15 Sekunden fragt die Seite erneut (ohne neu anzustoßen)', async (t) => {
  const s = await spielSeite({ hash: '#serie-s1' });
  let n = 0;
  s.m.on('tobibox/audio/bereit', (f) => { n += 1; return n === 1 ? { zustand: 'wird_vorbereitet', warte_s: 60, position: 1 } : { zustand: 'bereit', pfad: `/api/tobibox/audio/s1/${f.folge}?authSig=x`, quelle: 'kopie' }; });
  assert.equal(P.VORBEREITET_NEU_MS, 15000);
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    s.q('[data-reinhoeren]').click();
    await mikro(s);
    assert.ok(toasts(s).includes(HOERPROBE.vorbereitung));
    assert.equal(s.sp.zustand, 'vorbereitet');
    assert.equal(s.audio()?.getAttribute('src') ?? null, null, 'noch keine Quelle');
    t.mock.timers.tick(14999);
    await mikro(s);
    assert.equal(n, 1);
    t.mock.timers.tick(1);
    await mikro(s);
    assert.equal(n, 2);
    assert.equal(s.m.aufrufe('tobibox/audio/bereit').at(-1).vorbereiten, false, 'nur den Zustand lesen');
    assert.equal(s.audio().getAttribute('src'), '/api/tobibox/audio/s1/folge-01.mp3?authSig=x');
  } finally { t.mock.timers.reset(); }
});

mit('audio/bereit „fehlt“: Meldung statt Leiste', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  s.m.on('tobibox/audio/bereit', () => ({ zustand: 'fehlt', grund: 'medien_nicht_erreichbar' }));
  s.q('[data-reinhoeren]').click();
  await s.flush(12);
  assert.equal(s.q('.mini').hidden, true, 'ein erster Start, der nicht geht, lässt keine Leiste zurück');
  assert.match(toasts(s)[0], /NAS antwortet gerade nicht/);
  s.m.on('tobibox/audio/bereit', () => ({ zustand: 'fehlt', grund: 'zu_lang' }));
  s.q('[data-reinhoeren]').click();
  await s.flush(12);
  assert.ok(toasts(s).includes(HOERPROBE.keine_datei));
});

mit('Fehler von audio/bereit (zu viele Aufrufe, Folge weg): Meldung mit dem Text des Fehlercodes', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  s.m.failNext('tobibox/audio/bereit', 'zu_viele_aenderungen');
  s.q('[data-reinhoeren]').click();
  await s.flush(12);
  assert.equal(toasts(s)[0], FEHLER.zu_viele_aenderungen);
  assert.equal(s.q('.mini').hidden, true);
});

mit('Format: ohne Hörkopie und ohne Unterstützung des Browsers der Rückfalltext, kein audio/bereit', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  window.HTMLMediaElement.prototype.canPlayType = function canPlayType() { return ''; };
  s.q('[data-reinhoeren]').click();
  await s.flush(10);
  assert.equal(bereitAufrufe(s).length, 0);
  assert.deepEqual(toasts(s), [FEHLER.browser_spielt_nicht]);
});

mit('Link erneuern: nach über 20 Stunden holt Abspielen einen neuen Link und macht an der Stelle weiter', async (t) => {
  const s = await spielSeite({ hash: '#serie-s1' });
  t.mock.timers.enable({ apis: ['Date'], now: 5_000_000 });
  try {
    const a = await starteSerie(s);
    zeit(a, 70);
    s.q('.mini .mplay').click(); // Pause
    await s.flush(6);
    assert.equal(bereitAufrufe(s).length, 1);
    t.mock.timers.tick(19 * 3600 * 1000);
    s.q('.mini .mplay').click();
    await s.flush(6);
    assert.equal(bereitAufrufe(s).length, 1, 'nach 19 Stunden gilt der Link noch');
    s.q('.mini .mplay').click(); // wieder Pause
    await s.flush(6);
    t.mock.timers.tick(2 * 3600 * 1000);
    s.q('.mini .mplay').click();
    await s.flush(10);
    assert.equal(bereitAufrufe(s).length, 2, 'nach 21 Stunden ein neuer Link');
    lade(a, 120);
    await s.flush(6);
    assert.equal(a.currentTime, 70);
  } finally { t.mock.timers.reset(); }
});

mit('Nächste Datei im Voraus: kurz vor dem Ende wird sie signiert (ohne die Hörkopie anzustoßen), das Ende nutzt den Link ohne neue Frage', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s, 120);
  zeit(a, 60);
  await s.flush(4);
  assert.equal(bereitAufrufe(s).length, 1, 'noch weit vom Ende');
  zeit(a, 80);
  await s.flush(6);
  const b = bereitAufrufe(s);
  assert.equal(b.length, 2);
  assert.equal(b[1].folge, 'folge-02.mp3');
  assert.equal(b[1].vorbereiten, false);
  zeit(a, 100);
  await s.flush(4);
  assert.equal(bereitAufrufe(s).length, 2, 'nur einmal');
  ende(a, 120);
  await s.flush(10);
  assert.equal(bereitAufrufe(s).length, 2, 'der vorab signierte Link wird benutzt');
  assert.equal(a.getAttribute('src'), '/api/tobibox/audio/s1/folge-02.mp3?authSig=mock-2');
});

/* ------------------------------------------------------------------ Media-Session, Neuladen, Tempo */

mit('Media-Session: Titel, Eintrag, Art; Play, Pause, ±30 s, vorige und nächste Folge, Springen, Positionsangabe', async () => {
  const handler = {};
  const ms = { metadata: null, playbackState: 'none', setActionHandler: (n, f) => { handler[n] = f; }, setPositionState(o) { this.pos = o; } };
  Object.defineProperty(window.navigator, 'mediaSession', { value: ms, configurable: true });
  window.MediaMetadata = class { constructor(o) { Object.assign(this, o); } };
  try {
    const s = await spielSeite({ hash: '#serie-s1' });
    const a = await starteSerie(s);
    assert.equal(ms.metadata.title, 'Der Rabe');
    assert.equal(ms.metadata.artist, 'Die drei ???');
    assert.equal(ms.metadata.album, 'Hörspiel');
    assert.equal(ms.playbackState, 'playing');
    assert.deepEqual(Object.keys(handler).sort(), ['nexttrack', 'pause', 'play', 'previoustrack', 'seekbackward', 'seekforward', 'seekto']);
    assert.equal(ms.pos.duration, 120);
    zeit(a, 50);
    handler.seekforward({});
    assert.equal(a.currentTime, 80);
    handler.seekbackward({ seekOffset: 10 });
    assert.equal(a.currentTime, 70, 'iOS meldet 10 Sekunden');
    handler.seekto({ seekTime: 12 });
    assert.equal(a.currentTime, 12);
    handler.pause();
    assert.equal(ms.playbackState, 'paused');
    handler.play();
    assert.equal(ms.playbackState, 'playing');
    handler.nexttrack();
    await s.flush(10);
    assert.equal(ms.metadata.title, 'Das Gespensterschloss');
    weg();
  } finally { delete window.navigator.mediaSession; delete window.MediaMetadata; }
});

mit('Neuladen: die Leiste steht wieder da (pausiert, an der gemerkten Stelle, ohne Ton); Ton erst nach einem Tipp', async (t, au) => {
  const s1 = await spielSeite({ hash: '#serie-s1' });
  const a1 = await starteSerie(s1);
  zeit(a1, 66);
  s1.q('.mini .mplay').click();
  await s1.flush(6);
  const stand = structuredClone(s1.m.backend.hoerstellen);
  assert.equal(stand.s1.folgen['folge-01.mp3'].p, 66);
  weg();
  // „Neuladen“: neue App, das Backend merkt sich die Hörstelle
  const s = await spielSeite({});
  s.m.backend.hoerstellen = stand;
  s.sp._wiederhergestellt = false;
  await s.sp.wiederherstellen();
  await s.flush(10);
  assert.equal(s.q('.mini').hidden, false);
  assert.equal(s.q('.mini .mt').textContent, 'Der Rabe');
  assert.equal(s.q('.mini .mplay').getAttribute('aria-label'), 'Abspielen');
  assert.equal(s.q('.mini .mbar i').style.width, '55%', '66 von 120 Sekunden');
  const vorher = au.aufrufe.length;
  assert.equal(s.m.aufrufe('tobibox/audio/bereit').length, 0, 'ohne Tipp wird nichts geholt und nichts gespielt');
  assert.equal(au.aufrufe.length, vorher);
  s.q('.mini .mplay').click();
  await s.flush(12);
  assert.equal(s.m.aufrufe('tobibox/audio/bereit').length, 1);
  const a = s.audio();
  lade(a, 120);
  await s.flush(6);
  assert.equal(a.currentTime, 66, 'Weiterhören an der gemerkten Stelle');
  assert.ok(au.aufrufe.some((x) => x.art === 'play'));
});

mit('Neuladen: ohne Hörstelle oder ohne Fähigkeit keine Leiste', async () => {
  const s = await seite({ faehigkeiten: REIN });
  await s.flush(8);
  assert.equal(s.q('.mini').hidden, true);
  weg();
  const o = await seite();
  await o.flush(8);
  assert.equal(o.m.aufrufe('tobibox/hoerstelle/liste').length, 0, 'ohne die Fähigkeit reinhoeren wird nichts gefragt');
});

mit('Tempo im „⋯“: Blatt „Wiedergabe“, 1×, 1,25×, 1,5×; wird gemerkt und gilt für die nächste Folge', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s);
  const d = await oeffneVoll(s);
  d.querySelector('[data-p="more"]').click();
  await s.flush(8);
  const blatt = s.q('dialog.blatt[open]');
  assert.equal(blatt.querySelector('#blatt-t').textContent, 'Wiedergabe');
  assert.deepEqual([...blatt.querySelectorAll('[data-tempo]')].map((b) => b.textContent.trim()), ['1×', '1,25×', '1,5×']);
  assert.equal(blatt.querySelector('[data-tempo="1"]').getAttribute('aria-checked'), 'true');
  blatt.querySelector('[data-tempo="1.5"]').click();
  await s.flush(10);
  assert.equal(a.playbackRate, 1.5);
  assert.equal(window.localStorage.getItem('tobibox.tempo'), '1.5');
  s.sp.naechste();
  await s.flush(10);
  lade(a, 130);
  await s.flush(6);
  assert.equal(a.playbackRate, 1.5, 'gilt für alle Folgen');
});

/* ------------------------------------------------------------------ Wischen auf und zu */

mit('Wischen in der Leiste: nach oben (mindestens 40 px, deutlich senkrecht) öffnet, Kürzeres, Waagerechtes und nach unten nicht; ein Wisch löst keinen Tipp aus', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  await starteSerie(s);
  const leiste = () => s.q('.mini .mini-in');
  zeiger(leiste(), 'pointerdown', { clientX: 100, clientY: 700 });
  zeiger(leiste(), 'pointermove', { clientX: 100, clientY: 670 });
  await s.flush(4);
  assert.equal(dlg(s), null, 'unter 40 px nichts');
  zeiger(leiste(), 'pointerup', { clientX: 100, clientY: 670 });
  zeiger(leiste(), 'pointerdown', { clientX: 100, clientY: 700 });
  zeiger(leiste(), 'pointermove', { clientX: 190, clientY: 650 });
  await s.flush(4);
  assert.equal(dlg(s), null, 'mehr waagerecht als senkrecht: nichts');
  zeiger(leiste(), 'pointerup', { clientX: 190, clientY: 650 });
  zeiger(leiste(), 'pointerdown', { clientX: 100, clientY: 700 });
  zeiger(leiste(), 'pointermove', { clientX: 100, clientY: 760 });
  await s.flush(4);
  assert.equal(dlg(s), null, 'nach unten: nichts');
  zeiger(leiste(), 'pointerup', { clientX: 100, clientY: 760 });
  zeiger(leiste(), 'pointerdown', { clientX: 100, clientY: 700 });
  zeiger(leiste(), 'pointermove', { clientX: 105, clientY: 650 });
  await s.flush(8);
  assert.ok(dlg(s), 'nach oben (50 px): die Vollansicht öffnet');
  zeiger(leiste(), 'pointerup', { clientX: 105, clientY: 650 });
});

mit('Wischen in der Vollansicht: nach unten (mindestens 70 px, schnell) schließt, Kürzeres und Langsames nicht; der Knopf und Esc gehen weiter', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  await starteSerie(s);
  let d = await oeffneVoll(s);
  Object.defineProperty(d, 'offsetHeight', { value: 800, configurable: true });
  const feld = d.querySelector('.ptitle');
  zeiger(feld, 'pointerdown', { clientY: 300, timeStamp: 0 });
  zeiger(feld, 'pointermove', { clientY: 340, timeStamp: 20 });
  zeiger(feld, 'pointerup', { clientY: 340, timeStamp: 40 });
  await s.flush(6);
  assert.ok(dlg(s), 'unter 70 px nichts');
  assert.equal(d.style.getPropertyValue('--dy'), '', 'die Ansicht federt zurück');
  zeiger(feld, 'pointerdown', { clientY: 300, timeStamp: 100 });
  zeiger(feld, 'pointermove', { clientY: 400, timeStamp: 1000 });
  zeiger(feld, 'pointerup', { clientY: 400, timeStamp: 2000 });
  await s.flush(6);
  assert.ok(dlg(s), '100 px, aber langsam und unter 25 % der Höhe: bleibt');
  zeiger(feld, 'pointerdown', { clientY: 300, timeStamp: 3000 });
  zeiger(feld, 'pointermove', { clientY: 330, timeStamp: 3010 });
  zeiger(feld, 'pointermove', { clientY: 420, timeStamp: 3040 });
  assert.equal(d.style.getPropertyValue('--dy'), '120px', 'die Vollansicht folgt dem Finger');
  zeiger(feld, 'pointerup', { clientY: 420, timeStamp: 3050 });
  await s.flush(8);
  assert.equal(dlg(s), null, 'schnell und über 70 px: schließt');
  assert.equal(s.el.hasAttribute('data-voll'), false);
  // Zeitregler: Ziehen am Regler schließt nicht
  await warte(300); // die Tipp-Sperre nach einem Wisch
  d = await oeffneVoll(s);
  const sl = d.querySelector('.pslider');
  zeiger(sl, 'pointerdown', { clientY: 300, timeStamp: 0 });
  zeiger(sl, 'pointermove', { clientY: 500, timeStamp: 10 });
  zeiger(sl, 'pointerup', { clientY: 500, timeStamp: 20 });
  await s.flush(6);
  assert.ok(dlg(s));
  // Esc
  d.dispatchEvent(new window.Event('cancel', { cancelable: true }));
  await s.flush(8);
  assert.equal(dlg(s), null, 'Esc schließt');
});

mit('Nach einem Wisch kein Tipp: Tipp-Sperre 250 ms', async (t) => {
  const s = await spielSeite({ hash: '#serie-s1' });
  await starteSerie(s);
  t.mock.timers.enable({ apis: ['Date'], now: 9_000_000 });
  try {
    const leiste = s.q('.mini .mini-in');
    zeiger(leiste, 'pointerdown', { clientX: 100, clientY: 700 });
    zeiger(leiste, 'pointermove', { clientX: 100, clientY: 640 });
    await s.flush(6);
    const d = dlg(s);
    assert.ok(d);
    d.querySelector('[data-p="close"]').click();
    assert.ok(dlg(s), 'direkt nach dem Wisch löst der Tipp nichts aus');
    t.mock.timers.tick(300);
    d.querySelector('[data-p="close"]').click();
  } finally { t.mock.timers.reset(); }
  await s.flush(8);
  assert.equal(dlg(s), null);
});

/* ------------------------------------------------------------------ A8e: Sperre */

mit('Sperre: alle Bedienelemente disabled, der Titel heißt „Gesperrt“, Esc und Wischen schließen nicht', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  await starteSerie(s);
  const d = await oeffneVoll(s);
  d.querySelector('[data-p="lock"]').click();
  await s.flush(8);
  const knoepfe = [...d.querySelectorAll('button, input')].filter((b) => !b.matches('[data-p="unlock"]'));
  assert.ok(knoepfe.length >= 8, `gefunden: ${knoepfe.length}`);
  for (const b of knoepfe) assert.equal(b.disabled, true, `${b.localName}[${b.getAttribute('data-p') ?? b.className}] ist nicht gesperrt`);
  assert.equal(d.querySelector('#p-ansicht').textContent, 'Gesperrt');
  assert.ok(d.hasAttribute('data-gesperrt'));
  assert.equal(d.querySelector('[data-p="unlock"]').disabled, false);
  assert.equal(d.querySelector('[data-p="unlock"]').getAttribute('aria-label'), 'Entsperren: 2 Sekunden gedrückt halten');
  assert.equal(s.q('#live').textContent, 'Gesperrt. Zum Entsperren zwei Sekunden gedrückt halten.');
  const e = new window.Event('cancel', { cancelable: true });
  d.dispatchEvent(e);
  assert.equal(e.defaultPrevented, true);
  await s.flush(6);
  assert.ok(dlg(s), 'Esc schließt nicht');
  Object.defineProperty(d, 'offsetHeight', { value: 800, configurable: true });
  zeiger(d.querySelector('.ptitle'), 'pointerdown', { clientY: 300, timeStamp: 0 });
  zeiger(d.querySelector('.ptitle'), 'pointermove', { clientY: 340, timeStamp: 10 });
  zeiger(d.querySelector('.ptitle'), 'pointermove', { clientY: 500, timeStamp: 30 });
  zeiger(d.querySelector('.ptitle'), 'pointerup', { clientY: 500, timeStamp: 40 });
  await s.flush(6);
  assert.ok(dlg(s), 'Wischen schließt nicht');
  assert.ok(s.q('.mini .mplay'), 'die Leiste ist nicht Teil der Sperre');
  assert.equal(s.sp.spielt, true, 'die Wiedergabe läuft weiter');
});

mit('Sperre: 1,9 Sekunden Halten entsperrt nicht, 2 Sekunden entsperren (Maus und Touch); ein kurzer Tipp sagt es; Loslassen bricht ab', async (t) => {
  const s = await spielSeite({ hash: '#serie-s1' });
  await starteSerie(s);
  const d = await oeffneVoll(s);
  d.querySelector('[data-p="lock"]').click();
  await s.flush(8);
  const u = () => dlg(s).querySelector('[data-p="unlock"]');
  u().click();
  await s.flush(4);
  assert.deepEqual(toasts(s), ['Zum Entsperren zwei Sekunden gedrückt halten.'], 'ein kurzer Tipp');
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    zeiger(u(), 'pointerdown');
    assert.ok(u().classList.contains('holding'), 'der Füllbalken läuft');
    t.mock.timers.tick(1900);
    assert.equal(s.sp.gesperrt, true, '1,9 Sekunden entsperren nicht');
    zeiger(u(), 'pointerup');
    assert.equal(u().classList.contains('holding'), false);
    t.mock.timers.tick(500);
    assert.equal(s.sp.gesperrt, true, 'nach dem Loslassen läuft nichts weiter');
    zeiger(u(), 'pointerdown');
    t.mock.timers.tick(1999);
    assert.equal(s.sp.gesperrt, true);
    t.mock.timers.tick(1);
    assert.equal(s.sp.gesperrt, false, '2 Sekunden entsperren');
  } finally { t.mock.timers.reset(); }
  await s.flush(8);
  const knoepfe = [...dlg(s).querySelectorAll('.pctl button, .pslider')];
  assert.ok(knoepfe.length && knoepfe.every((b) => b.disabled === false || ['prev'].includes(b.dataset.p)), 'danach wieder bedienbar');
  assert.equal(dlg(s).querySelector('#p-ansicht').textContent, 'Läuft gerade');
  assert.equal(s.q('#live').textContent, 'Entsperrt.');
});

mit('Sperre: mit der Tastatur (Leertaste 2 Sekunden halten) entsperrt auch; Kontextmenü ist auf der gesperrten Ansicht aus', async (t) => {
  const s = await spielSeite({ hash: '#serie-s1' });
  await starteSerie(s);
  const d = await oeffneVoll(s);
  d.querySelector('[data-p="lock"]').click();
  await s.flush(8);
  const u = dlg(s).querySelector('[data-p="unlock"]');
  const m = new window.Event('contextmenu', { cancelable: true, bubbles: true });
  u.dispatchEvent(m);
  assert.equal(m.defaultPrevented, true);
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    assert.equal(taste(u, ' ').defaultPrevented, true);
    t.mock.timers.tick(1900);
    assert.equal(s.sp.gesperrt, true);
    u.dispatchEvent(new window.KeyboardEvent('keyup', { key: ' ', bubbles: true }));
    taste(u, 'Enter');
    t.mock.timers.tick(2000);
    assert.equal(s.sp.gesperrt, false);
  } finally { t.mock.timers.reset(); }
});

/* ------------------------------------------------------------------ A7c: Reihe „Am Handy weiterhören“, Knopf, Fortschritt */

mit('Knopf „Reinhören“: Beschriftung je Hörstelle (Reinhören, Hier weiterhören mit Zusatz, Noch einmal hören) und die Zeile darunter (AM15: immer da, kein Hinweissatz mehr)', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const text = () => s.q('[data-reinhoeren]').textContent.trim();
  assert.equal(text(), 'Reinhören');
  assert.equal(s.q('[data-rein-hinweis]'), null, 'AM16: der Satz „Das spielt hier am Handy …“ entfällt');
  assert.equal(s.q('[data-rein-zusatz]').textContent, 'Der Rabe', 'AM15: auch bei „Reinhören“ steht die Zeile');
  // Hörstelle: zweite Folge angefangen
  s.m.backend.hoerstellen.s1 = { zeit: '2026-11-14T10:00:00Z', folge: 'folge-02.mp3', folgen: { 'folge-01.mp3': { p: 120, d: 120, t: '2026-11-14T09:00:00Z', fertig: true, track: 0 }, 'folge-02.mp3': { p: 47, d: 130, t: '2026-11-14T10:00:00Z', fertig: false, track: 0 } } };
  await geheZu(s, '#bibliothek'); await geheZu(s, '#serie-s1'); await s.flush(10);
  assert.equal(text(), 'Hier weiterhören');
  assert.equal(s.q('[data-rein-zusatz]').textContent, 'Das Gespensterschloss · ab 0:47');
  s.m.backend.hoerstellen.s1.folgen['folge-02.mp3'].fertig = true;
  s.m.backend.hoerstellen.s1.folgen['folge-03.mp3'] = { p: 140, d: 140, t: '2026-11-14T11:00:00Z', fertig: true, track: 0 };
  await geheZu(s, '#bibliothek'); await geheZu(s, '#serie-s1'); await s.flush(10);
  assert.equal(text(), 'Noch einmal hören');
  assert.equal(s.q('[data-rein-zusatz]').textContent, 'Der Rabe');
});

mit('„Hier weiterhören“ spielt die Folge an der gemerkten Stelle (hoerstelle/get), nicht die erste', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  s.m.backend.hoerstellen.s1 = { zeit: '2026-11-14T10:00:00Z', folge: 'folge-02.mp3', folgen: { 'folge-02.mp3': { p: 47, d: 130, t: '2026-11-14T10:00:00Z', fertig: false, track: 0 } } };
  await geheZu(s, '#bibliothek'); await geheZu(s, '#serie-s1'); await s.flush(10);
  assert.equal(s.q('[data-reinhoeren]').textContent.trim(), 'Hier weiterhören');
  const a = await starteSerie(s, 130);
  assert.equal(bereitAufrufe(s).at(-1).folge, 'folge-02.mp3');
  assert.equal(a.currentTime, 47);
  assert.equal(s.q('.mini .mt').textContent, 'Das Gespensterschloss');
});

mit('Folgenzeile (AM11): die ganze Zeile (Knopf über der Zeilenfläche) spielt genau diese Folge; die Nummer wird zur Abspiel-Anzeige', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const knopf = (n) => s.q(`[data-folge="${n}"] [data-abspielen]`);
  assert.equal(knopf('folge-02.mp3').getAttribute('aria-label'), 'Das Gespensterschloss abspielen');
  knopf('folge-02.mp3').click();
  await s.flush(12);
  lade(s.audio(), 130);
  await s.flush(8);
  assert.equal(bereitAufrufe(s).at(-1).folge, 'folge-02.mp3');
  assert.equal(knopf('folge-02.mp3').getAttribute('aria-label'), 'Das Gespensterschloss im Player öffnen', 'AM13: die geladene Folge öffnet den Player');
  assert.equal(knopf('folge-01.mp3').getAttribute('aria-label'), 'Der Rabe abspielen');
  assert.ok(s.q('[data-folge="folge-02.mp3"] .se-num .eq'), 'die Abspiel-Anzeige steht statt der Nummer');
  assert.equal(s.q('[data-folge="folge-02.mp3"] .se-num .eq').getAttribute('aria-label'), 'läuft gerade');
  assert.equal(s.q('[data-folge="folge-01.mp3"] .se-num .eq'), null);
  assert.ok(s.q('.se-hero h2 .eq'), 'auch am Kopf der Serienseite, hinter dem Namen');
  s.el.spieler.toggle();
  await s.flush(8);
  assert.equal(s.q('[data-folge="folge-02.mp3"] .se-num .eq').getAttribute('aria-label'), 'pausiert');
  assert.ok(s.q('[data-folge="folge-02.mp3"] .se-num .eq').classList.contains('still'), 'bei Pause stehen die Balken still');
  assert.equal(bereitAufrufe(s).length, 1, 'Pause fragt nichts mehr');
});

mit('Folgenzeile (AM13): Tipp auf die geladene Folge öffnet die Vollansicht und lässt den Ton; jede andere Folge startet', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const knopf = (n) => s.q(`[data-folge="${n}"] [data-abspielen]`);
  knopf('folge-02.mp3').click();
  await s.flush(12);
  const a = s.audio();
  lade(a, 130);
  await s.flush(8);
  assert.equal(a.paused, false, 'die Folge läuft');
  assert.equal(s.q('dialog.player'), null);
  // laufend: Tipp öffnet die Vollansicht, der Ton läuft weiter
  knopf('folge-02.mp3').click();
  await s.flush(12);
  assert.ok(s.q('dialog.player'), 'die Vollansicht ist offen');
  assert.equal(a.paused, false, 'der Ton läuft weiter');
  assert.equal(bereitAufrufe(s).length, 1, 'nichts neu geladen');
  s.el.spieler.schliessen('knopf'); await s.flush(30);
  s.el.spieler.offen = false; s.el.neuZeichnen?.(); await s.flush(8);
  // pausiert: Tipp öffnet die Vollansicht, bleibt pausiert
  s.el.spieler.toggle();
  await s.flush(8);
  assert.equal(a.paused, true, 'pausiert');
  s.el.spieler.offen = false; await s.flush(8);
  assert.equal(knopf('folge-02.mp3').getAttribute('aria-label'), 'Das Gespensterschloss im Player öffnen');
  knopf('folge-02.mp3').click();
  await s.flush(12);
  assert.ok(s.q('dialog.player'), 'auch pausiert öffnet der Tipp die Vollansicht');
  assert.equal(a.paused, true, 'und bleibt pausiert');
  s.el.spieler.offen = false; await s.flush(8);
  // andere Folge: startet
  assert.equal(knopf('folge-01.mp3').getAttribute('aria-label'), 'Der Rabe abspielen');
  knopf('folge-01.mp3').click();
  await s.flush(12);
  assert.equal(bereitAufrufe(s).at(-1).folge, 'folge-01.mp3', 'eine andere Folge startet');
  assert.equal(s.q('dialog.player'), null, 'ohne Vollansicht');
});

mit('Folgenzeile (AM11): kein runder Play-Knopf mehr; „⋯“ und Tobie-Chip starten nichts', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  assert.equal(s.q('.se-play'), null, 'der runde Play-Knopf entfällt');
  const zeile = s.q('[data-folge="folge-02.mp3"]');
  const flaeche = zeile.querySelector(':scope > .se-zeilenknopf[data-abspielen]');
  assert.ok(flaeche, 'die Zeilenfläche ist ein Knopf (Tastatur, Name)');
  assert.equal(flaeche.getAttribute('aria-label'), 'Das Gespensterschloss abspielen');
  assert.ok(!flaeche.contains(zeile.querySelector('[data-menue-folge]')), '„⋯“ steckt nicht im Zeilenknopf');
  zeile.querySelector('[data-menue-folge]').click();
  await s.flush(10);
  assert.ok(s.q('dialog.blatt[open]'), '„⋯“ öffnet das Menü');
  assert.equal(bereitAufrufe(s).length, 0, '„⋯“ startet nichts');
  s.el.schliesseBlatt('code'); await s.flush(10);
  const chip = zeile.querySelector('.tb-chips a');
  if (chip) { chip.addEventListener('click', (e) => e.preventDefault()); chip.click(); await s.flush(6); assert.equal(bereitAufrufe(s).length, 0, 'ein Tobie-Chip startet nichts'); }
  assert.ok(chip, 'die Zeile hat einen Tobie-Chip');
  flaeche.click();
  await s.flush(12);
  assert.equal(bereitAufrufe(s).at(-1)?.folge, 'folge-02.mp3', 'ein Tipp auf die Zeilenfläche startet die Folge');
});

mit('Ohne die Fähigkeit reinhoeren: kein Knopf „Reinhören“, kein Abspielknopf, keine Leiste', async () => {
  const s = await seite({ hash: '' });
  const { beispiele } = await import('./player-helfer.mjs');
  beispiele(s.m);
  await geheZu(s, '#serie-s1'); await s.flush(10);
  assert.equal(s.q('[data-reinhoeren]'), null);
  assert.equal(s.q('[data-abspielen]'), null);
  assert.equal(s.q('.mini').hidden, true);
});

mit('Start: Reihe „Am Handy weiterhören“ mit Balken, „noch … Min.“ und Abspielknopf; fehlt ohne Hörstelle; der Knopf spielt dort weiter', async () => {
  const s = await spielSeite({ hash: '#start' });
  await s.flush(10);
  assert.equal(s.q('[data-reihe="weiterhoeren"]'), null, 'ohne Hörstelle keine Reihe');
  s.m.backend.hoerstellen.s1 = { zeit: '2026-11-14T10:00:00Z', folge: 'folge-02.mp3', folgen: { 'folge-02.mp3': { p: 50, d: 130, t: '2026-11-14T10:00:00Z', fertig: false, track: 0 } } };
  s.m.backend.hoerstellen.lied = { zeit: '2026-11-14T11:00:00Z', folge: 'wiegenlied.mp3', folgen: { 'wiegenlied.mp3': { p: 60, d: 66, t: '2026-11-14T11:00:00Z', fertig: false, track: 0 } } };
  s.m.backend.hoerstellen.buch = { zeit: '2026-11-14T12:00:00Z', folge: 'buch', folgen: { buch: { p: 80, d: 80, t: '2026-11-14T12:00:00Z', fertig: true, track: 2 } } };
  await geheZu(s, '#tobies'); await geheZu(s, '#start'); await s.flush(10);
  const reihe = s.q('[data-reihe="weiterhoeren"]');
  assert.ok(reihe, 'die Reihe steht da');
  assert.equal(s.q('.reihe .rowh').textContent, 'Am Handy weiterhören');
  const kacheln = [...reihe.querySelectorAll('.wh')];
  assert.deepEqual(kacheln.map((k) => k.dataset.weiter), ['lied', 's1'], 'zuletzt angehört zuerst, fertig Gehörtes fehlt');
  const k = kacheln[1];
  assert.equal(k.querySelector('.tn').textContent, 'Die drei ???');
  assert.equal(k.querySelector('.tm').textContent, 'noch 1 Min.', '80 von 130 Sekunden fehlen: gerundet 1 Min.');
  assert.equal(k.querySelector('[role="progressbar"]').getAttribute('aria-valuenow'), '38');
  assert.equal(k.querySelector('.playov').getAttribute('aria-label'), 'Die drei ??? weiterhören');
  assert.equal(k.querySelector('a.tile').getAttribute('href'), '#serie-s1');
  k.querySelector('.playov').click();
  await s.flush(14);
  assert.equal(bereitAufrufe(s).at(-1).folge, 'folge-02.mp3');
  const a = s.audio();
  lade(a, 130);
  await s.flush(8);
  assert.equal(a.currentTime, 50);
  assert.equal(s.q('.wh[data-weiter="s1"] .playov').getAttribute('aria-label'), 'Die drei ??? weiterhören');
  assert.ok(s.q('.wh[data-weiter="s1"] .eq'), 'die Abspiel-Anzeige auf dem Cover');
});

mit('Start (AM8, AM9): der Rückflug merkt sich die angetippte Kachel (Reihe, Platz) und den waagrechten Stand jeder Reihe', async () => {
  const s = await spielSeite({ hash: '#start' });
  s.m.backend.hoerstellen.s1 = { zeit: '2026-11-14T10:00:00Z', folge: 'folge-02.mp3', folgen: { 'folge-02.mp3': { p: 50, d: 130, t: '2026-11-14T10:00:00Z', fertig: false, track: 0 } } };
  await geheZu(s, '#tobies'); await geheZu(s, '#start'); await s.flush(10);
  const kacheln = (reihe) => [...s.el.shadowRoot.querySelectorAll(`.hscroll[data-reihe="${reihe}"] a[data-serie]`)];
  const oben = kacheln('weiterhoeren');
  const unten = kacheln('neu');
  const id = oben[0].dataset.serie;
  const platz = unten.findIndex((a) => a.dataset.serie === id);
  assert.ok(platz >= 0, 'die Serie steht in beiden Reihen');
  // die Flug-Messung ersetzen: der Test liest nur, was die App sich merkt
  let flug = null; let reihenWieder = null;
  s.el._coverFlug = function () { if (this._flug?.art === 'zurueck') flug = { ...this._flug }; };
  const alt = s.el._scrollHalten;
  s.el._scrollHalten = function () { reihenWieder = this._reihenWieder ? { ...this._reihenWieder } : reihenWieder; return alt.call(this); };
  const hscroll = s.el.shadowRoot.querySelector('.hscroll[data-reihe="neu"]');
  Object.defineProperty(hscroll, 'scrollLeft', { value: 300, writable: true, configurable: true });
  unten[platz].dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
  assert.deepEqual({ ...s.el._angetippt }, { id, reihe: 'neu', index: platz });
  await geheZu(s, `#serie-${id}`); await s.flush(10);
  await geheZu(s, '#start'); await s.flush(10);
  assert.deepEqual(flug?.kachel, { id, reihe: 'neu', index: platz }, 'der Rückflug kennt die untere Kachel, nicht die oberste');
  assert.equal(reihenWieder?.neu, 300, 'der waagrechte Stand der Reihe wird wiederhergestellt');
});

mit('Start: ein Fehler der Hörstelle lässt nur die Reihe weg, nie den Start', async () => {
  const s = await spielSeite({ hash: '' });
  s.m.failNext('tobibox/hoerstelle/liste', 'serie_nicht_gefunden');
  await geheZu(s, '#start'); await s.flush(10);
  assert.ok(s.q('[data-start="schnellzugriff"]'));
  assert.equal(s.q('[data-reihe="weiterhoeren"]'), null);
});

mit('Bibliothek: Fortschritt in der Liste und Sortierung „Zuletzt angehört“ (nur mit der Fähigkeit); neu angehört steht vorn', async () => {
  const s = await spielSeite({ hash: '#bibliothek' });
  s.m.backend.hoerstellen.lied = { zeit: '2026-11-14T11:00:00Z', folge: 'wiegenlied.mp3', folgen: { 'wiegenlied.mp3': { p: 33, d: 66, t: '2026-11-14T11:00:00Z', fertig: false, track: 0 } } };
  s.q('[data-sortieren]').click();
  await s.flush(8);
  const wahl = s.qa('dialog.blatt[open] [role="radio"]').find((b) => b.textContent.trim() === 'Zuletzt angehört');
  assert.ok(wahl, 'die Sortierung gibt es mit reinhoeren');
  wahl.click();
  await s.flush(10);
  s.qa('dialog.blatt[open] .knoepfe button').find((b) => b.textContent.trim() === 'Fertig').click();
  await s.flush(10);
  const erste = s.q('a.lrow[data-serie], a.rcard[data-serie]');
  assert.equal(erste.dataset.serie, 'lied');
  assert.ok(erste.querySelector('[role="progressbar"]'), 'der Fortschritt steht in der Zeile');
  assert.equal(s.m.letzter('tobibox/serien/list').sortierung, 'angehoert');
});

mit('Suche: Folgenzeilen haben den Abspielknopf, er startet genau diese Folge', async () => {
  const s = await spielSeite({ hash: '#suche' });
  const feld = s.q('input.suchfeld');
  feld.value = 'Rabe';
  feld.dispatchEvent(new window.Event('input', { bubbles: true }));
  await warte(400); await s.flush(10);
  const k = s.q('.frow [data-abspielen]');
  assert.ok(k, 'Abspielknopf in der Trefferzeile');
  k.click();
  await s.flush(14);
  lade(s.audio(), 120);
  await s.flush(8);
  assert.equal(bereitAufrufe(s).at(-1).folge, 'folge-01.mp3');
  assert.equal(s.q('.frow [data-abspielen]').getAttribute('aria-label'), 'Der Rabe pausieren');
});

mit('Texte: der Player hat alle Beschriftungen aus dem Design, ohne Platzhalter-Reste', () => {
  const alle = [];
  const geh = (o, pfad) => { for (const [k, v] of Object.entries(o)) typeof v === 'string' ? alle.push([`${pfad}.${k}`, v]) : geh(v, `${pfad}.${k}`); };
  geh(PLAYER, 'PLAYER');
  assert.ok(alle.length > 40);
  for (const [pfad, t] of alle) { assert.ok(t.trim().length, `${pfad} ist leer`); assert.ok(!/UID|Revision|Listen-ID/.test(t), pfad); }
  assert.equal(PLAYER.knopf.hinweis, undefined, 'AM16: der Hinweissatz ist weg');
  assert.equal(PLAYER.knopf.laeuft, '{ziel} · läuft');
  assert.equal(PLAYER.voll.entsperren_hinweis, 'Zum Entsperren zwei Sekunden gedrückt halten.');
  assert.equal(PLAYER.mini.tipp, 'Antippen oder nach oben wischen: Player öffnen');
});

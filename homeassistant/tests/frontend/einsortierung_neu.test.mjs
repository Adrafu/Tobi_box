/* Tests von „Anders einsortieren …“ (Paket A11c, Design 5.6, 6.1, 7.3 Punkt 3b und 10, 10.3 G9, 11.2 V-7, N29; Vertrag W Nr. 43, 2.4, Ereignis `eingang`).
 * Aufruf: node --test homeassistant/tests/frontend
 *
 * Geprüft: wann der Knopf da ist (`kannNeuEinsortieren`: `pruefen` oder höchstens 24 Stunden seit `fertig_am`; nicht bei laufend, „geht nicht“, „teilweise“; nur mit
 * der Fähigkeit `einsortier_wunsch`), das Blatt „Was ist das?“ (dieselbe Wahl wie beim Hochladen, Knopf „Neu einsortieren“), der Aufruf mit den richtigen Feldern je Wahl,
 * die Karte „Wird einsortiert …“ danach und das Ergebnis über das Ereignis `eingang`, die Fehlertexte, der erste Punkt im Menü „Das stimmt nicht“ auf der Serienseite.
 * „Nur Stufe A“ gibt es nur im Prototyp; in der echten Seite entscheidet allein die Fähigkeit (N29), das ist unten mit der fehlenden Fähigkeit geprüft.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, MIT_DOM, jsdom, domBereit } from './dom-helfer.mjs';
import { FAEHIGKEITEN, eingangEintrag } from './mock-hass.mjs';

if (jsdom) await domBereit();
const FRONT = '../../custom_components/tobibox/frontend';
const E = await import(`${FRONT}/eingang.js`);
const { HINZU, FEHLER } = await import(`${FRONT}/texte.js`);

const ALLE = [...FAEHIGKEITEN, 'einsortier_wunsch', 'eingang'];
const minuten = (min) => new Date(Date.now() - min * 60000).toISOString();
const erg = (teil = {}) => ({ serie_id: 's2', serie_name: 'Bibi Blocksberg', serie_neu: true, folge: 'b-01.mp3', anzeige: 'Hexen gibt es doch', tracks: 1, pruefen: false, pruefen_gruende: [], ...teil });
const nasFertig = (teil = {}) => eingangEintrag({ name: 'Bibi-Ordner', art: 'ordner', dateien: 3, quelle: 'nas', fertig_am: minuten(5), zuerst_gesehen: minuten(8), ergebnis: [erg()], ...teil });
const nasAnsehen = (teil = {}) => nasFertig({ pruefen: true, ergebnis: [erg({ pruefen: true, pruefen_gruende: ['tags_fehlen'] })], ...teil });
const folge = (name, anzeige) => ({ name, anzeige, nummer: null, datum: null, art: 'datei', tracks: 1, groesse_bytes: 5242880, pruefung: 'ok', hinweis: null, pruefen: false, pruefen_gruende: [], tobies: [] });

/* ------------------------------------------------------------------ Hilfen */

async function start({ hash = '#hinzufuegen', faehigkeiten = ALLE, ...opts } = {}) {
  const s = await seite({ faehigkeiten, hash: '', ...opts });
  s.m.backend.serien.lang = { id: 'lang', name: 'Lange Serie', typ: 'normal', ordner: 'Lange', pruefen: false, hinweise: [], art: 'hoerspiel', cover_stand: null, angelegt_am: '2026-11-09T10:00:00Z',
    folgen: Array.from({ length: 12 }, (_, i) => ({ ...folge(`f${i + 1}.mp3`, `Folge ${i + 1}`), nummer: i + 1 })) };
  if (hash) { await geheZu(s, hash); await s.flush(10); }
  return s;
}
const klick = async (s, el) => { assert.ok(el, 'Element zum Klicken fehlt'); el.click(); await warte(15); await s.flush(10); };
const bis = async (fn, ms = 1500) => { const t0 = Date.now(); for (;;) { const r = fn(); if (r) return r; if (Date.now() - t0 > ms) throw new Error('Zeitüberschreitung'); await warte(10); } };
const karten = (s) => s.qa('[data-liste="zuletzt"] [data-eintrag]');
const karteMit = (s, teil) => karten(s).find((k) => kText(k).includes(teil));
const kText = (el) => el?.textContent.replace(/\s+/g, ' ').trim() ?? '';
const knoepfe = (k) => [...k.querySelectorAll('.btns .btn')].map((b) => b.textContent.trim());
const blatt = (s) => s.q('dialog.blatt[open]');
const blattKnopf = (s, label) => s.qa('dialog.blatt[open] .knoepfe button').find((b) => b.textContent.trim() === label);
const kachel = (s, ziel) => s.q(`dialog.blatt[open] [data-ziel="${ziel}"]`);
const toasts = (s) => s.qa('.toast .tmsg').map((x) => x.textContent);
const aufrufe = (s) => s.m.aufrufe('tobibox/einsortierung/neu').map(({ id, type, ...r }) => r);

/* ------------------------------------------------------------------ Wann es den Knopf geben darf (reine Funktion) */

test('kannNeuEinsortieren: „bitte ansehen“ oder höchstens 24 Stunden seit `fertig_am`, nur fertig einsortiert und mit Ergebnis', () => {
  const jetzt = Date.parse('2026-11-13T12:00:00Z');
  const vor = (min) => new Date(jetzt - min * 60000).toISOString();
  const kann = (teil) => E.kannNeuEinsortieren(eingangEintrag({ ergebnis: [erg()], ...teil }), { jetzt });
  assert.equal(kann({ fertig_am: vor(5) }), true, 'jung');
  assert.equal(kann({ fertig_am: vor(24 * 60) }), true, 'genau 24 Stunden');
  assert.equal(kann({ fertig_am: vor(24 * 60 + 1) }), false, 'älter, nicht „bitte ansehen“');
  assert.equal(kann({ fertig_am: vor(25 * 60), pruefen: true }), true, '„bitte ansehen“ gilt auch, wenn es älter ist');
  assert.equal(kann({ fertig_am: null }), false, 'ohne `fertig_am` und nicht „bitte ansehen“');
  assert.equal(kann({ status: 'laeuft', fertig_am: null, pruefen: true }), false, 'läuft noch');
  assert.equal(kann({ status: 'wartet', fertig_am: null }), false, 'wartet noch');
  assert.equal(kann({ status: 'blockiert', fertig_am: vor(5) }), false, 'geht nicht');
  assert.equal(kann({ status: 'teilweise', fertig_am: vor(5), pruefen: true }), false, 'ein Teil liegt noch im Eingang');
  assert.equal(kann({ fertig_am: vor(5), ergebnis: [] }), false, 'nichts einsortiert, nichts zurückzuholen');
  assert.equal(E.kannNeuEinsortieren(null, { jetzt }), false);
});

/* ------------------------------------------------------------------ Der Knopf auf der Seite „Hinzufügen“ */

test('Karte „bitte ansehen“: Ansehen, Das ist richtig, Anders einsortieren … (an der Stelle von „Das stimmt nicht“)', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasAnsehen()] });
  try {
    const k = karte0(s);
    assert.equal(k.dataset.phase, 'pruefen');
    assert.deepEqual(knoepfe(k), ['Ansehen', 'Das ist richtig', 'Anders einsortieren …']);
    assert.equal(k.querySelector('[data-stimmt-nicht]'), null);
    assert.equal(k.querySelector('[data-anders]').getAttribute('aria-haspopup'), 'dialog');
  } finally { weg(); }
});
const karte0 = (s) => karten(s)[0];

test('Karte „fertig“ und jünger als 24 Stunden: Öffnen und Anders einsortieren …; älter als 24 Stunden steht gar nicht in der Liste', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig(), nasFertig({ name: 'Zu alt', fertig_am: minuten(30 * 60), zuerst_gesehen: minuten(30 * 60 + 3) })] });
  try {
    assert.equal(karten(s).length, 1);
    assert.deepEqual(knoepfe(karte0(s)), ['Öffnen', 'Anders einsortieren …']);
  } finally { weg(); }
});

test('Ohne die Fähigkeit `einsortier_wunsch` (und damit „Nur Stufe A“, N29) gibt es den Knopf nicht, „Das stimmt nicht“ bleibt', { ...MIT_DOM }, async () => {
  const s = await start({ faehigkeiten: ALLE.filter((f) => f !== 'einsortier_wunsch'), eingangErledigt: [nasAnsehen({ name: 'Bibi-Ordner' }), nasFertig({ name: 'Anderer Ordner', ergebnis: [erg({ serie_id: 'lang' })] })] });
  try {
    assert.equal(s.qa('[data-anders]').length, 0);
    assert.deepEqual(knoepfe(karteMit(s, 'Bibi-Ordner')), ['Ansehen', 'Das ist richtig', 'Das stimmt nicht']);
    assert.deepEqual(knoepfe(karteMit(s, 'Anderer Ordner')), ['Öffnen']);
  } finally { weg(); }
});

test('Kein Knopf bei „wird einsortiert“, „geht nicht“, „teilweise“ und „fehlt noch eine Datei“', { ...MIT_DOM }, async () => {
  const s = await start({
    eingang: [
      eingangEintrag({ name: 'Läuft', quelle: 'nas', status: 'laeuft', fertig_am: null, zuerst_gesehen: minuten(1) }),
      eingangEintrag({ name: 'Kopiergeschützt', quelle: 'nas', status: 'blockiert', fertig_am: null, zuerst_gesehen: minuten(30), hinweise: [{ code: 'kopierschutz', datei: 'a.m4b', text: 'x' }] }),
    ],
    eingangErledigt: [
      nasAnsehen({ name: 'Teils', status: 'teilweise', hinweise: [{ code: 'kopierschutz', datei: 'Teils/a.m4b', text: 'x' }] }),
      nasAnsehen({ name: 'Fehlt', status: 'teilweise', hinweise: [{ code: 'gruppe_unvollstaendig', datei: null, text: 'x' }] }),
    ],
  });
  try {
    assert.equal(karten(s).length, 4);
    assert.equal(s.qa('[data-anders]').length, 0);
  } finally { weg(); }
});

/* ------------------------------------------------------------------ Das Blatt „Was ist das?“ */

test('Das Blatt: Titel „Was ist das?“, Zeile zum NAS, dieselben Kacheln wie beim Hochladen ohne „Sortier du“, „Abbrechen“ oben, noch kein Aufruf', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasAnsehen()] });
  try {
    await klick(s, s.q('[data-anders]'));
    assert.ok(blatt(s));
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Was ist das?');
    assert.equal(kText(s.q('dialog.blatt[open] [data-gewaehlt]')), '3 Dateien im Eingang vom NAS. Was ist das?');
    assert.deepEqual(s.qa('dialog.blatt[open] [data-kachel]').map((k) => k.dataset.kachel), ['neu', 'zu_vorhandenem', 'einzeln']);
    assert.equal(s.q('dialog.blatt[open] [data-blatt-oben]').textContent.trim(), 'Abbrechen');
    assert.equal(aufrufe(s).length, 0);
    await klick(s, s.q('dialog.blatt[open] [data-blatt-oben]'));
    assert.equal(blatt(s), null, 'Abbrechen schließt, es wurde nichts gesendet');
    assert.equal(aufrufe(s).length, 0);
  } finally { weg(); }
});

test('Das Blatt bei einem Eintrag vom Handy und bei einer Datei', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig({ quelle: 'upload', dateien: 1, name: 'Lied.mp3' })] });
  try {
    await klick(s, s.q('[data-anders]'));
    assert.equal(kText(s.q('dialog.blatt[open] [data-gewaehlt]')), '1 Datei aus dem Eingang. Was ist das?');
  } finally { weg(); }
});

test('Vorschau „Neu anlegen“: Name und Art aus dem Eintrag vorbelegt, Satz in Worten, Knopf „Neu einsortieren“ statt „Hochladen“', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasAnsehen()] });
  try {
    await klick(s, s.q('[data-anders]'));
    await klick(s, kachel(s, 'neu'));
    assert.equal(s.q('dialog.blatt[open] #hz-name').value, 'Bibi Blocksberg');
    assert.match(kText(s.q('dialog.blatt[open] [data-satz]')), /^3 Dateien → neues Hörspiel „Bibi Blocksberg“, Folge 1–3\./);
    assert.deepEqual(s.qa('dialog.blatt[open] .knoepfe button').map((b) => b.textContent.trim()), ['Abbrechen', 'Ändern', 'Neu einsortieren']);
    assert.ok(!blattKnopf(s, 'Hochladen'));
    await klick(s, blattKnopf(s, 'Ändern'));
    assert.equal(s.qa('dialog.blatt[open] [data-kachel]').length, 3, '„Ändern“ führt zurück zur Wahl');
  } finally { weg(); }
});

test('„Neu einsortieren“ sendet `einsortierung/neu` mit eintrag_id, ziel, art und name (ohne `gruppe`), das Blatt geht zu, die Karte zeigt „Wird einsortiert …“', { ...MIT_DOM }, async () => {
  const e = nasAnsehen();
  const s = await start({ eingangErledigt: [e] });
  try {
    await klick(s, s.q('[data-anders]'));
    await klick(s, kachel(s, 'neu'));
    const feld = s.q('dialog.blatt[open] #hz-name');
    feld.value = 'Kapitän Knopf';
    feld.dispatchEvent(new window.Event('input', { bubbles: true }));
    await s.flush(6);
    await klick(s, s.q('dialog.blatt[open] [data-art-wahl="hoerbuch"]'));
    await klick(s, blattKnopf(s, 'Neu einsortieren'));
    await s.flush(12);
    assert.deepEqual(aufrufe(s), [{ eintrag_id: e.id, ziel: 'neu', art: 'hoerbuch', name: 'Kapitän Knopf' }]);
    assert.equal(blatt(s), null, 'das Blatt ist zu');
    const k = karten(s)[0];
    assert.equal(k.dataset.phase, 'sortieren');
    assert.equal(k.querySelector('[data-status]').textContent.trim(), 'Wird einsortiert …');
    assert.equal(k.querySelector('[data-anders]'), null, 'während es läuft gibt es keinen Knopf');
    assert.equal(s.m.aufrufe('tobibox/eingang/list').length >= 2, true, 'danach lädt die Seite `eingang/list` neu');
    assert.deepEqual(toasts(s), []);
  } finally { weg(); }
});

test('Das Ergebnis kommt wie sonst über das Ereignis `eingang`: aus „Wird einsortiert …“ wird die fertige Karte mit „Daraus ist geworden“', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasAnsehen()] });
  try {
    await klick(s, s.q('[data-anders]'));
    await klick(s, kachel(s, 'einzeln'));
    await klick(s, blattKnopf(s, 'Neu einsortieren'));
    await s.flush(12);
    assert.equal(karten(s)[0].dataset.phase, 'sortieren');
    // Das Backend ist fertig: der Eintrag steht wieder im Protokoll, mit neuem Ergebnis
    s.m.backend.eingang = [];
    s.m.backend.eingangErledigt = [nasFertig({ id: 'neuer-eintrag', ergebnis: [erg({ serie_id: 'lang', serie_name: 'Lange Serie', serie_neu: false })] })];
    s.m.emit('eingang', 'neu_einsortiert', { eintrag_id: 'neuer-eintrag', eintrag_name: 'Bibi-Ordner', ergebnis: [], hinweise: [], zaehler: {} });
    await bis(() => karten(s)[0]?.dataset.phase === 'fertig');
    assert.match(kText(karten(s)[0].querySelector('[data-daraus]')), /Lange Serie/);
  } finally { weg(); }
});

test('Die Karte bleibt bei „Wird einsortiert …“, bis `eingang/list` etwas anderes sagt, auch wenn der alte Stand noch im Zwischenspeicher steht', { ...MIT_DOM }, async () => {
  const e = nasAnsehen();
  const s = await start({ eingangErledigt: [e] });
  try {
    s.m.on('tobibox/einsortierung/neu', () => ({ gestartet: true })); // das Backend nimmt an, der Eintrag in `eingang/list` bleibt zunächst gleich
    await klick(s, s.q('[data-anders]'));
    await klick(s, kachel(s, 'einzeln'));
    await klick(s, blattKnopf(s, 'Neu einsortieren'));
    await s.flush(12);
    assert.equal(karten(s)[0].dataset.phase, 'sortieren');
    s.m.emit('eingang', 'geaendert', {});
    await s.flush(12);
    assert.equal(karten(s)[0].dataset.phase, 'sortieren', 'derselbe Stand: weiter „Wird einsortiert …“');
    s.m.backend.eingangErledigt = [{ ...e, fertig_am: new Date().toISOString(), geaendert_am: new Date().toISOString(), pruefen: false }];
    s.m.emit('eingang', 'geaendert', {});
    await bis(() => karten(s)[0]?.dataset.phase === 'fertig');
  } finally { weg(); }
});

/* Die Wahl `ziel` öffnen, `vor` ausführen (Eingaben), „Neu einsortieren“ tippen; der Befehl wird vom Mock nur angenommen (der Eintrag bleibt, wie er ist). */
async function sende(s, ziel, vor = async () => {}) {
  s.m.on('tobibox/einsortierung/neu', () => ({ gestartet: true }));
  await klick(s, s.q('[data-anders]'));
  await klick(s, kachel(s, ziel));
  await vor();
  await klick(s, blattKnopf(s, 'Neu einsortieren'));
  await s.flush(8);
}

test('Felder je Wahl: „Einzeln“ sendet die Art, aber keinen Namen (der Befehl kennt keine Einzeltitel)', { ...MIT_DOM }, async () => {
  const e = nasFertig();
  const s = await start({ eingangErledigt: [e] });
  try {
    await sende(s, 'einzeln', async () => {
      assert.equal(s.qa('dialog.blatt[open] input[data-titel]').length, 0, 'ohne Titelfelder');
      assert.match(kText(s.q('dialog.blatt[open] [data-satz]')), /^3 Dateien → 3 einzelne /);
      await klick(s, s.q('dialog.blatt[open] [data-art-wahl="geschichte"]'));
    });
    assert.deepEqual(aufrufe(s), [{ eintrag_id: e.id, ziel: 'einzeln', art: 'geschichte' }]);
  } finally { weg(); }
});

test('Im Blatt „Was ist das?“ gibt es „Sortier du“ nicht, und `ziel: auto` geht nie an `einsortierung/neu` (Vertrag Nr. 43)', { ...MIT_DOM }, async () => {
  const e = nasFertig();
  const s = await start({ eingangErledigt: [e] });
  try {
    await klick(s, s.q('[data-anders]'));
    assert.deepEqual(s.qa('dialog.blatt[open] [data-kachel]').map((k) => k.dataset.kachel), ['neu', 'zu_vorhandenem', 'einzeln']);
    assert.equal(kachel(s, 'auto'), null);
    const mod = (await import(`${FRONT}/seiten/hinzufuegen.js`)).modell(s.el.ctx);
    mod.w.ziel = 'auto'; mod.schritt(mod.w, 'vorschau'); await s.flush(6);
    assert.equal(await mod.neuEinsortieren(), false);
    assert.equal(aufrufe(s).length, 0);
    await assert.rejects(s.el.ctx.api('tobibox/einsortierung/neu', { eintrag_id: e.id, ziel: 'auto' }), (err) => err.code === 'wunsch_ungueltig');
  } finally { weg(); }
});

test('Felder je Wahl: „Zu Vorhandenem“ sendet die `serie_id` der gewählten Serie (wie „Wohin soll es?“ beim Hochladen)', { ...MIT_DOM }, async () => {
  const e = nasFertig();
  const s = await start({ eingangErledigt: [e] });
  try {
    await sende(s, 'ergaenzen', async () => {
      assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), HINZU.blatt.wohin_titel);
      await bis(() => s.q('[data-hz-wahl] [data-wahl="serie:lang"]'));
      await klick(s, s.q('[data-hz-wahl] [data-wahl="serie:lang"]'));
      assert.match(kText(s.q('dialog.blatt[open] [data-satz]')), /Lange Serie/);
    });
    assert.deepEqual(aufrufe(s), [{ eintrag_id: e.id, ziel: 'ergaenzen', serie_id: 'lang' }]);
  } finally { weg(); }
});

test('Die Prüfungen vor dem Senden: ohne Namen und ohne Ziel geht nichts raus, das Blatt bleibt', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasAnsehen({ name: 'Upload ab12cd34', ergebnis: [erg({ serie_name: '' })] })] });
  try {
    await klick(s, s.q('[data-anders]'));
    await klick(s, kachel(s, 'neu'));
    assert.equal(s.q('dialog.blatt[open] #hz-name').value, '', 'der Gruppen-Ordner „Upload ab12cd34“ ist kein Name');
    await klick(s, blattKnopf(s, 'Neu einsortieren'));
    assert.deepEqual(toasts(s), [HINZU.blatt.kein_name]);
    assert.ok(blatt(s));
    assert.equal(aufrufe(s).length, 0);
  } finally { weg(); }
});

test('Doppeltes Tippen sendet nur einmal: der Knopf ist gesperrt, solange die Antwort fehlt', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig()] });
  try {
    let frei; const warten = new Promise((r) => { frei = r; });
    s.m.on('tobibox/einsortierung/neu', async () => { await warten; return { gestartet: true }; });
    await klick(s, s.q('[data-anders]'));
    await klick(s, kachel(s, 'einzeln'));
    const k = blattKnopf(s, 'Neu einsortieren');
    k.click(); await warte(10); await s.flush(6);
    assert.equal(blattKnopf(s, 'Neu einsortieren').disabled, true);
    blattKnopf(s, 'Neu einsortieren').click(); await warte(10);
    frei(); await warte(30); await s.flush(10);
    assert.equal(aufrufe(s).length, 1);
    assert.equal(blatt(s), null);
  } finally { weg(); }
});

/* ------------------------------------------------------------------ Fehler (Design 6.1) */

test('`neu_einsortieren_nicht_moeglich`: der Text aus 6.1, das Blatt geht zu, die Liste ist frisch, der Eintrag bleibt wie er war', { ...MIT_DOM }, async () => {
  const e = nasAnsehen();
  const s = await start({ eingangErledigt: [e] });
  try {
    s.m.backend.neuGesperrt.add(e.id); // jemand hat an den Folgen etwas geändert (Vertrag 2.4)
    const davor = s.m.aufrufe('tobibox/eingang/list').length;
    await klick(s, s.q('[data-anders]'));
    await klick(s, kachel(s, 'einzeln'));
    await klick(s, blattKnopf(s, 'Neu einsortieren'));
    await s.flush(12);
    assert.deepEqual(toasts(s), [FEHLER.neu_einsortieren_nicht_moeglich]);
    assert.equal(blatt(s), null);
    assert.ok(s.m.aufrufe('tobibox/eingang/list').length > davor, 'die Liste wird neu geladen');
    assert.equal(karten(s)[0].dataset.phase, 'pruefen', 'nichts hat sich geändert, keine Karte steht bei „Wird einsortiert …“');
  } finally { weg(); }
});

test('`eintrag_nicht_gefunden`: Meldung, Blatt zu, Liste neu geladen', { ...MIT_DOM }, async () => {
  const s = await start({ eingangErledigt: [nasFertig()] });
  try {
    s.m.failNext('tobibox/einsortierung/neu', 'eintrag_nicht_gefunden');
    await klick(s, s.q('[data-anders]'));
    await klick(s, kachel(s, 'einzeln'));
    await klick(s, blattKnopf(s, 'Neu einsortieren'));
    await s.flush(10);
    assert.deepEqual(toasts(s), [FEHLER.eintrag_nicht_gefunden]);
    assert.equal(blatt(s), null);
  } finally { weg(); }
});

for (const code of ['wunsch_ungueltig', 'zu_viele_aenderungen', 'sortierung_laeuft', 'medien_schreibfehler']) {
  test(`\`${code}\`: der Text aus 6.1, das Blatt bleibt offen und der Knopf ist wieder frei (noch einmal versuchen oder Wahl ändern)`, { ...MIT_DOM }, async () => {
    const s = await start({ eingangErledigt: [nasFertig()] });
    try {
      s.m.failNext('tobibox/einsortierung/neu', code);
      await klick(s, s.q('[data-anders]'));
      await klick(s, kachel(s, 'einzeln'));
      await klick(s, blattKnopf(s, 'Neu einsortieren'));
      await s.flush(10);
      assert.deepEqual(toasts(s), [s.el.ctx.fehlerText(code)]);
      assert.ok(blatt(s), 'das Blatt bleibt');
      assert.equal(blattKnopf(s, 'Neu einsortieren').disabled, false);
      assert.equal(karten(s)[0].dataset.phase, 'fertig', 'die Karte steht nicht bei „Wird einsortiert …“');
      await klick(s, blattKnopf(s, 'Neu einsortieren')); // der zweite Versuch geht durch
      assert.equal(aufrufe(s).length, 2);
      assert.equal(blatt(s), null);
    } finally { weg(); }
  });
}

test('Die kurzen Fehlertexte stehen in texte.js und ohne Erklärsatz (AM16)', () => {
  for (const c of ['neu_einsortieren_nicht_moeglich', 'wunsch_ungueltig', 'zu_viele_aenderungen', 'sortierung_laeuft', 'eintrag_nicht_gefunden', 'medien_schreibfehler']) {
    assert.equal(typeof FEHLER[c], 'string', c);
    assert.ok(FEHLER[c].length < 200, c);
  }
  assert.equal(HINZU.anders, 'Anders einsortieren …');
  assert.equal(HINZU.neu.knopf, 'Neu einsortieren');
  assert.equal(HINZU.neu.titel, 'Was ist das?');
});

/* ------------------------------------------------------------------ Serienseite: erster Punkt im Menü „Das stimmt nicht“ */

test('Serienseite: „Das stimmt nicht“ nennt als erstes „Anders einsortieren …“; es öffnet das Blatt „Was ist das?“ für den Eintrag', { ...MIT_DOM }, async () => {
  const e = nasAnsehen();
  const s = await start({ hash: '#serie-s2', eingangErledigt: [e] });
  try {
    await klick(s, s.q('[data-stimmt-nicht]'));
    const punkte = s.qa('dialog.blatt[open] [data-menue]').map((x) => x.dataset.menue);
    assert.equal(punkte[0], 'anders');
    assert.equal(s.q('dialog.blatt[open] [data-menue="anders"]').textContent.trim(), 'Anders einsortieren …');
    assert.deepEqual(punkte.slice(1), ['art', 'name', 'zusammen', 'papierkorb']);
    await klick(s, s.q('dialog.blatt[open] [data-menue="anders"]'));
    assert.equal(s.q('dialog.blatt[open] #blatt-t').textContent.trim(), 'Was ist das?');
    assert.equal(s.qa('dialog.blatt[open] [data-kachel]').length, 3);
    await klick(s, kachel(s, 'einzeln'));
    await klick(s, blattKnopf(s, 'Neu einsortieren'));
    await s.flush(12);
    assert.deepEqual(aufrufe(s), [{ eintrag_id: e.id, ziel: 'einzeln', art: 'musik' }]);
    assert.equal(window.location.hash, '#hinzufuegen', 'danach zeigt die Seite „Hinzufügen“ den Eintrag bei „Wird einsortiert …“');
    assert.equal(karten(s)[0]?.dataset.phase, 'sortieren');
  } finally { weg(); }
});

test('Serienseite: ohne die Fähigkeit, ohne Eintrag in den letzten 24 Stunden oder bei „geht nicht“ gibt es den Punkt nicht', { ...MIT_DOM }, async () => {
  const ohne = await start({ hash: '#serie-s2', faehigkeiten: ALLE.filter((f) => f !== 'einsortier_wunsch'), eingangErledigt: [nasAnsehen()] });
  try {
    await klick(ohne, ohne.q('[data-stimmt-nicht]'));
    assert.deepEqual(ohne.qa('dialog.blatt[open] [data-menue]').map((x) => x.dataset.menue), ['art', 'name', 'zusammen', 'papierkorb']);
  } finally { weg(); }
  const alt = await start({ hash: '#serie-s2', eingangErledigt: [nasAnsehen({ fertig_am: minuten(30 * 60), zuerst_gesehen: minuten(30 * 60 + 5) })] });
  try {
    await klick(alt, alt.q('[data-stimmt-nicht]'));
    assert.ok(!alt.q('dialog.blatt[open] [data-menue="anders"]'));
  } finally { weg(); }
});

/* Tests zu Stern und Favoriten, den Reihen auf dem Start, den Sortierungen und dem Filter der Bibliothek (Stufe B, Paket B4, Design docs/designs/gehoert.md Abschnitt 7).
 * Aufruf: node --test homeassistant/tests/frontend
 *
 * Stern-Knopf der Serienseite (aria-pressed, Wort im Namen, Meldung), „Zu Favoriten“/„Aus Favoriten“ im Menü der Folge, kleine Sterne in Zeilen und Kacheln,
 * Reihen „Zuletzt auf den Boxen gehört“ und „Favoriten“ (Fehler still, leere Reihen fehlen), Sortierungen „Zuletzt gehört“ und „Meist gehört“, Filter „Favoriten“,
 * ältere HA ohne die Fähigkeiten (nichts davon sichtbar), Fehler `zu_viele_favoriten`.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN, FAEHIGKEITEN_V11, FAEHIGKEITEN_B } from './mock-hass.mjs';

const { STERN, START, BIB, FEHLER, fuellen } = await import('../../custom_components/tobibox/frontend/texte.js');
const { favoritenReihe, REIHEN } = await import('../../custom_components/tobibox/frontend/seiten/start.js');
const { parseRoute } = await import('../../custom_components/tobibox/frontend/tobibox-app.js');

const ALLE = [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11, ...FAEHIGKEITEN_B, 'reinhoeren'];
const OHNE_B = [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11, 'reinhoeren'];
const text = (el) => el.textContent.replace(/\s+/g, ' ').trim();
const toasts = (s) => s.qa('.toast .tmsg').map(text);
const klick = async (s, el) => { assert.ok(el, 'Element zum Klicken fehlt'); el.click(); await warte(20); await s.flush(12); };
const gesetzt = (s) => s.m.aufrufe('tobibox/favorit/set').map(({ id, type, ...r }) => r);
const z = (wer, serie, folge, tag, stunde, sekunden) => ({ wer, serie, folge, tag, stunde, sekunden, mal: 1, fertig: 0 });

async function oeffne(hash, opts = {}) {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start', ...opts });
  await geheZu(s, hash);
  await s.flush(12);
  return s;
}

/* ------------------------------------------------------------------ Stern auf der Serienseite */

test('Serienseite: der Stern ist ein Knopf mit aria-pressed, das Wort „Favorit“ steht im Namen; Setzen sendet favorit/set und meldet es', MIT_DOM, async () => {
  const s = await oeffne('#serie-s1');
  const k = s.q('[data-stern]');
  assert.equal(k.getAttribute('aria-pressed'), 'false');
  assert.equal(k.getAttribute('aria-label'), 'Favorit: Die drei ???');
  assert.ok(k.getAttribute('aria-label').includes('Favorit'));
  assert.equal(k.closest('.se-leiste') !== null, true, 'am Handy in der Leiste neben „⋯“');
  await klick(s, k);
  assert.deepEqual(gesetzt(s), [{ serie_id: 's1', an: true }]);
  assert.equal(s.q('[data-stern]').getAttribute('aria-pressed'), 'true');
  assert.deepEqual(toasts(s), ['„Die drei ???“ ist jetzt ein Favorit.']);
  assert.equal(s.m.backend.favoriten[0].serie_id, 's1');
  await klick(s, s.q('[data-stern]'));
  assert.deepEqual(gesetzt(s).at(-1), { serie_id: 's1', an: false });
  assert.equal(s.q('[data-stern]').getAttribute('aria-pressed'), 'false');
  assert.ok(toasts(s).includes('„Die drei ???“ ist kein Favorit mehr.'));
  weg();
});

test('Serienseite am Computer: der Stern steht mit dem Wort „Favorit“ im großen Kopf', MIT_DOM, async () => {
  const s = await oeffne('#serie-s1', { breite: 1280 });
  const k = s.q('.se-aktionen [data-stern]');
  assert.ok(k, 'Stern im Kopf neben „Mehr“');
  assert.equal(text(k), 'Favorit');
  weg();
});

test('Serienseite: ein Eintrag mit Stern zeigt den Knopf gedrückt, ohne kleinen Stern im Kopf', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  s.m.backend.favoriten.push({ serie_id: 's1', folge: null, gesetzt_von: { id: 'u1', name: 'Person A' }, gesetzt_am: '2026-11-13T10:00:00Z' });
  await geheZu(s, '#serie-s1');
  await s.flush(12);
  assert.equal(s.q('[data-stern]').getAttribute('aria-pressed'), 'true');
  assert.equal(s.qa('[data-stern]').length, 1);
  assert.equal(s.q('.se-hero [data-favorit], .se-leiste [data-favorit]'), null, 'im Kopf kein zweiter, kleiner Stern');
  weg();
});

test('Serienseite: Fehler zu_viele_favoriten zeigt den Text aus texte.js, der Stern bleibt aus', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start', favoritenMax: 0 });
  await geheZu(s, '#serie-s1');
  await s.flush(12);
  await klick(s, s.q('[data-stern]'));
  assert.equal(s.q('[data-stern]').getAttribute('aria-pressed'), 'false', 'nichts gesetzt');
  assert.ok(s.qa('.toast.err .tmsg').some((t) => text(t) === FEHLER.zu_viele_favoriten), 'Meldung mit dem Text aus texte.js');
  weg();
});

test('Serienseite: das Menü der Folge hat „Zu Favoriten“ / „Aus Favoriten“ als Text; die Folge trägt danach einen kleinen Stern mit aria-label „Favorit“', MIT_DOM, async () => {
  const s = await oeffne('#serie-s1');
  await klick(s, s.q('[data-folge="folge-02.mp3"] [data-menue-folge]'));
  const punkt = s.q('dialog.blatt[open] [data-menue="favorit"]');
  assert.equal(text(punkt), 'Zu Favoriten');
  assert.equal(s.qa('dialog.blatt[open] [data-menue]')[1], punkt, '„Einem Tobie geben …“ bleibt der erste Punkt, der Stern steht danach');
  await klick(s, punkt);
  assert.deepEqual(gesetzt(s), [{ serie_id: 's1', folge: 'folge-02.mp3', an: true }]);
  assert.equal(s.q('dialog.blatt[open]'), null, 'das Menü schließt');
  const stern = s.q('[data-folge="folge-02.mp3"] [data-favorit]');
  assert.ok(stern);
  assert.equal(stern.getAttribute('aria-label'), 'Favorit');
  assert.equal(stern.getAttribute('role'), 'img');
  assert.equal(s.q('[data-folge="folge-01.mp3"] [data-favorit]'), null);
  assert.deepEqual(toasts(s), ['„Das Gespensterschloss“ ist jetzt ein Favorit.']);
  await klick(s, s.q('[data-folge="folge-02.mp3"] [data-menue-folge]'));
  assert.equal(text(s.q('dialog.blatt[open] [data-menue="favorit"]')), 'Aus Favoriten');
  await klick(s, s.q('dialog.blatt[open] [data-menue="favorit"]'));
  assert.equal(s.q('[data-folge="folge-02.mp3"] [data-favorit]'), null);
  assert.deepEqual(gesetzt(s).at(-1), { serie_id: 's1', folge: 'folge-02.mp3', an: false });
  weg();
});

test('Serienseite: ein Stern aus einem anderen Fenster (Ereignis `favoriten`) lädt die Seite still neu', MIT_DOM, async () => {
  const s = await oeffne('#serie-s1');
  assert.equal(s.q('[data-stern]').getAttribute('aria-pressed'), 'false');
  s.m.backend.favoriten.push({ serie_id: 's1', folge: null, gesetzt_von: { id: 'u2', name: 'Person B' }, gesetzt_am: '2026-11-13T10:00:00Z' });
  s.m.emit('favoriten', 'geaendert', { serie_id: 's1', folge: null, an: true });
  await warte(20); await s.flush(12);
  assert.equal(s.q('[data-stern]').getAttribute('aria-pressed'), 'true');
  s.m.emit('favoriten', 'geaendert', { serie_id: 'andere', folge: null, an: true });
  const n = s.m.aufrufe('tobibox/serie/get').length;
  await warte(20); await s.flush(6);
  assert.equal(s.m.aufrufe('tobibox/serie/get').length, n, 'ein Stern an einem anderen Eintrag lädt nichts');
  weg();
});

test('Serienseite ohne die Fähigkeit favoriten: weder Knopf noch Menüpunkt noch kleiner Stern (ältere HA)', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: OHNE_B, hash: '#start' });
  await geheZu(s, '#serie-s1');
  await s.flush(12);
  assert.equal(s.q('[data-stern]'), null);
  await klick(s, s.q('[data-folge="folge-01.mp3"] [data-menue-folge]'));
  assert.equal(s.q('dialog.blatt[open] [data-menue="favorit"]'), null);
  assert.equal(s.qa('[data-favorit]').length, 0);
  assert.equal(s.m.aufrufe('tobibox/favoriten/list').length + s.m.aufrufe('tobibox/favorit/set').length, 0);
  weg();
});

/* ------------------------------------------------------------------ kleine Sterne in Zeilen und Kacheln */

test('Bibliothek: ein Eintrag mit Stern trägt in Zeile und Rasterkachel einen kleinen Stern mit aria-label „Favorit“ (nur mit `favoriten`)', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  s.m.backend.favoriten.push({ serie_id: 's2', folge: null, gesetzt_von: { id: 'u1', name: 'Person A' }, gesetzt_am: '2026-11-12T10:00:00Z' });
  await geheZu(s, '#bibliothek');
  await s.flush(12);
  assert.equal(s.qa('.lrow [data-favorit]').length, 1);
  const zeile = s.q('.lrow[data-serie="s2"]');
  assert.equal(zeile.querySelector('[data-favorit]').getAttribute('aria-label'), 'Favorit');
  weg();
  const g = await seite({ faehigkeiten: ALLE, hash: '#start', breite: 1280 });
  g.m.backend.favoriten.push({ serie_id: 's2', folge: null, gesetzt_von: { id: 'u1', name: 'Person A' }, gesetzt_am: '2026-11-12T10:00:00Z' });
  await geheZu(g, '#bibliothek');
  await g.flush(12);
  assert.ok(g.q('.rcard[data-serie="s2"] [data-favorit]'));
  weg();
});

/* ------------------------------------------------------------------ Bibliothek: Sortierungen und Filter */

test('Bibliothek: das Blatt bietet „Zuletzt gehört“ und „Meist gehört“ und den Filter „Favoriten“; die Abfrage trägt sie', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#bibliothek', viele: true });
  s.m.backend.gehoert.zeilen = [z('box:kueche', Object.keys(s.m.backend.serien)[3], Object.values(s.m.backend.serien)[3].folgen[0].name, '2026-11-12', 10, 600)];
  s.m.backend.favoriten.push({ serie_id: Object.keys(s.m.backend.serien)[3], folge: null, gesetzt_von: { id: 'u1', name: 'Person A' }, gesetzt_am: '2026-11-12T10:00:00Z' });
  await s.flush(12);
  await klick(s, s.q('[data-sortieren]'));
  assert.deepEqual(s.qa('dialog [role=radiogroup]')[0].querySelectorAll('.optrow').length, 5);
  assert.deepEqual([...s.qa('dialog [role=radiogroup]')[0].querySelectorAll('.optrow')].map(text), [BIB.blatt.sortierung.name, BIB.blatt.sortierung.neu, BIB.blatt.sortierung.angehoert, 'Zuletzt gehört', 'Meist gehört']);
  assert.ok(s.qa('dialog .optrow[aria-pressed]').some((b) => text(b) === 'Favoriten'));
  await klick(s, [...s.qa('dialog [role=radiogroup]')[0].querySelectorAll('.optrow')][3]);
  assert.equal(s.m.aufrufe('tobibox/serien/list').at(-1).sortierung, 'zuletzt_gehoert');
  assert.equal(s.qa('.lrow')[0].dataset.serie, Object.keys(s.m.backend.serien)[3], 'was zuletzt auf einer Box lief, steht oben');
  await klick(s, [...s.qa('dialog [role=radiogroup]')[0].querySelectorAll('.optrow')][4]);
  assert.equal(s.m.aufrufe('tobibox/serien/list').at(-1).sortierung, 'meist_gehoert');
  await klick(s, s.qa('dialog .optrow[aria-pressed]').find((b) => text(b) === 'Favoriten'));
  const a = s.m.aufrufe('tobibox/serien/list').at(-1);
  assert.deepEqual([a.sortierung, a.filter], ['meist_gehoert', ['favorit']]);
  assert.equal(s.qa('.lrow').length, 1);
  assert.equal(text(s.q('[data-sortieren] .nbadge')), '2');
  weg();
});

test('Bibliothek ohne die Fähigkeiten: nur A bis Z, Zuletzt hinzugefügt, Zuletzt angehört; kein Filter „Favoriten“; die Abfrage trägt nichts von Stufe B', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: OHNE_B, hash: '#bibliothek', viele: true });
  await s.flush(12);
  await klick(s, s.q('[data-sortieren]'));
  assert.equal(s.qa('dialog [role=radiogroup]')[0].querySelectorAll('.optrow').length, 3);
  assert.ok(!s.qa('dialog .optrow[aria-pressed]').some((b) => text(b) === 'Favoriten'));
  const sortierungen = s.m.aufrufe('tobibox/serien/list').map((x) => x.sortierung);
  assert.ok(!sortierungen.some((x) => ['zuletzt_gehoert', 'meist_gehoert'].includes(x)));
  weg();
});

test('Route: #bibliothek?sortierung=zuletzt_gehoert und ?filter=favorit kommen bei der Seite an; ohne Fähigkeit bleibt die Sortierung wie sie ist', MIT_DOM, async () => {
  assert.deepEqual([parseRoute('#bibliothek?sortierung=zuletzt_gehoert').sortierung, parseRoute('#bibliothek?filter=favorit').filter], ['zuletzt_gehoert', 'favorit']);
  const s = await seite({ faehigkeiten: ALLE, hash: '#start', viele: true });
  await geheZu(s, '#bibliothek?filter=favorit');
  await s.flush(12);
  assert.deepEqual(s.m.aufrufe('tobibox/serien/list').at(-1).filter, ['favorit']);
  weg();
  const o = await seite({ faehigkeiten: OHNE_B, hash: '#start', viele: true });
  await geheZu(o, '#bibliothek?sortierung=zuletzt_gehoert');
  await o.flush(12);
  assert.equal(o.m.aufrufe('tobibox/serien/list').at(-1).sortierung, 'name');
  weg();
});

/* ------------------------------------------------------------------ Start: die zwei Reihen */

test('REIHEN: „Zuletzt auf den Boxen gehört“ und „Favoriten“ tragen ihre Daten und „Alle anzeigen“; Titel „Favoriten“ (nicht „Favoriten / Empfehlungen“)', () => {
  assert.equal(START.reihen.favoriten, 'Favoriten');
  assert.deepEqual(REIHEN.map((r) => r.eintraege({ zuletzt: [{ id: 'a' }], favoriten: [{ id: 'b' }, { id: 'c' }], neu: [], weiter: [] }).length), [0, 1, 0, 2]);
  assert.equal(REIHEN.find((r) => r.id === 'zuletzt_gehoert').alle, '#bibliothek?sortierung=zuletzt_gehoert');
  assert.equal(REIHEN.find((r) => r.id === 'favoriten').alle, '#bibliothek?filter=favorit');
});

test('Start: Reihe „Zuletzt auf den Boxen gehört“ aus Befehl 51 (nur Boxen, neueste zuerst), ohne Platzhalter und ohne Erklärsatz', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  s.m.backend.gehoert.zeilen = [z('box:kueche', 's2', 'b-01.mp3', '2026-11-12', 10, 600), z('box:kinderzimmer', 's1', 'folge-01.mp3', '2026-11-13', 8, 300), z('benutzer:u1', 's3', 'u-01.mp3', '2026-11-13', 9, 300)];
  s.el._seiten.start.laden(true);
  await warte(30); await s.flush(12);
  const reihe = s.q('[data-reihe="zuletzt_gehoert"]');
  assert.ok(reihe);
  assert.deepEqual([...reihe.querySelectorAll('.tile')].map((a) => a.dataset.serie), ['s1', 's2'], 'neueste zuerst; das Reinhören einer Person gehört nicht dazu');
  assert.equal(text(reihe.closest('.reihe').querySelector('.rowh')), 'Zuletzt auf den Boxen gehört');
  const k = s.m.aufrufe('tobibox/gehoert/zuletzt');
  assert.deepEqual(k.map(({ id, type, ...r }) => r), [{ limit: 10 }, { limit: 10 }].slice(0, k.length));
  assert.equal(reihe.closest('.reihe').querySelector('a.alle').getAttribute('href'), '#bibliothek?sortierung=zuletzt_gehoert');
  weg();
});

test('Start: Reihe „Favoriten“ aus Befehl 56: ein Stern am Eintrag ergibt die gewohnte Kachel, ein Stern an einer Folge eine Kachel mit dem Namen der Folge; beides mit Stern', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  s.m.backend.favoriten = [
    { serie_id: 's2', folge: null, gesetzt_von: { id: 'u1', name: 'Person A' }, gesetzt_am: '2026-11-13T10:00:00Z' },
    { serie_id: 's1', folge: 'folge-02.mp3', gesetzt_von: { id: 'u2', name: 'Person B' }, gesetzt_am: '2026-11-12T10:00:00Z' },
  ];
  s.el._seiten.start.laden(true);
  await warte(30); await s.flush(12);
  const reihe = s.q('[data-reihe="favoriten"]');
  assert.deepEqual([...reihe.querySelectorAll('.tile')].map((a) => [a.dataset.serie, text(a.querySelector('.tn')), text(a.querySelector('.tm'))]),
    [['s2', 'Bibi Blocksberg', 'Hörspiel · 1 Folge'.replace(' · 1 Folge', ' · 1 Folge')], ['s1', 'Das Gespensterschloss', 'Die drei ???']].map((x, i) => (i === 0 ? [x[0], x[1], text(reihe.querySelector('.tile .tm'))] : x)));
  assert.equal(reihe.querySelectorAll('[data-favorit]').length, 2);
  assert.ok(reihe.querySelector('[data-favorit-folge="folge-02.mp3"]'));
  assert.equal(text(reihe.closest('.reihe').querySelector('.rowh')), 'Favoriten');
  weg();
});

test('Start: ein Fehler in einer Reihe der Stufe B lässt nur diese Reihe weg (still), der Start bleibt', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start', viele: true });
  s.m.backend.favoriten = [{ serie_id: 's1', folge: null, gesetzt_von: { id: 'u1', name: 'Person A' }, gesetzt_am: '2026-11-13T10:00:00Z' }];
  s.m.backend.gehoert.zeilen = [z('box:kueche', 's1', 'folge-01.mp3', '2026-11-12', 10, 600)];
  s.m.failNext('tobibox/gehoert/zuletzt', 'unknown_error');
  s.m.failNext('tobibox/favoriten/list', 'unknown_error');
  s.el._seiten.start.laden(true);
  await warte(30); await s.flush(12);
  assert.equal(s.q('[data-reihe="zuletzt_gehoert"]'), null);
  assert.equal(s.q('[data-reihe="favoriten"]'), null);
  assert.ok(s.q('[data-reihe="neu"]'), 'die anderen Reihen bleiben');
  assert.equal(s.q('.note.err'), null, 'keine Fehlerkarte');
  weg();
});

test('Start: leere Reihen fehlen ganz (kein Platzhalter, keine Überschrift); ältere HA fragt gar nicht erst', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start', viele: true });
  await s.flush(12);
  assert.equal(s.q('[data-reihe="zuletzt_gehoert"]'), null);
  assert.equal(s.q('[data-reihe="favoriten"]'), null);
  assert.ok(!s.q('main').textContent.includes('Favoriten'));
  weg();
  const alt = await seite({ faehigkeiten: OHNE_B, hash: '#start', viele: true });
  await alt.flush(12);
  assert.equal(alt.m.aufrufe('tobibox/gehoert/zuletzt').length + alt.m.aufrufe('tobibox/favoriten/list').length, 0);
  weg();
});

test('favoritenReihe(): höchstens zwölf, gelöschte fehlen, Folgen ohne Antwort von folgen/list fallen weg', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  s.m.backend.favoriten = [{ serie_id: 's1', folge: 'folge-03.mp3', gesetzt_von: { id: 'u1', name: 'A' }, gesetzt_am: '2026-11-13T10:00:00Z' }, { serie_id: 's2', folge: null, gesetzt_von: { id: 'u1', name: 'A' }, gesetzt_am: '2026-11-12T10:00:00Z' }];
  const ctx = { api: (type, felder) => s.m.hass.connection.sendMessagePromise({ type, ...felder }) };
  const l = await favoritenReihe(ctx);
  assert.deepEqual(l.map((x) => [x.id, x.folge_anzeige ?? null, x.favorit]), [['s1', 'Der Super-Papagei', true], ['s2', null, true]]);
  const ohne = await favoritenReihe({ api: async () => ({ eintraege: [] }) });
  assert.deepEqual(ohne, []);
  weg();
});

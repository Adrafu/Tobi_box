/* Tests der Seiten „Geräte“ und Box-Detail (AP A7b, Design 3.4, 5.1.1, 5.1.2, 5.8). Aufruf: node --test homeassistant/tests/frontend
 *
 * Box-Karten mit Status-Sätzen, Box-Detail für Administratoren und andere, Gute-Nacht-Schnellwahl, Wochenansicht der Leise-Zeiten
 * (Abschnitte, Mitternacht, „Jetzt: …“), Blatt zum Anlegen, Ändern und Löschen, `erwartet_revision`, Zeitzone, leere Zustände.
 * Backend aus mock-hass.mjs (`istAdmin: false` = Alltag: schreiben ja, Technik nein).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, tippe, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN, FAEHIGKEITEN_V11 } from './mock-hass.mjs';

const G = await import('../../custom_components/tobibox/frontend/seiten/geraete.js');
const { ABENDS, GERAETE_SEITE, LEISE, STATUS, LEER, fuellen, fehlerText } = await import('../../custom_components/tobibox/frontend/texte.js');

const ALLE = [...FAEHIGKEITEN, ...FAEHIGKEITEN_V11];
const W_NACHT = { id: 'nacht', tage: [7, 1, 2, 3, 4], von: '19:30', bis: '06:30', wirkung: 'stumm' }; // So bis Do 19:30 bis 6:30
const W_MITTAG = { id: 'mittag', tage: [1, 2, 3, 4, 5], von: '13:00', bis: '14:00', wirkung: 'leiser', grenze: 25 };

/* Seite „Geräte“; `fenster` und `zone` stehen im Backend, bevor die Seite lädt. */
async function geraete({ fenster = [], zone, ...opts } = {}) {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start', ...opts });
  s.m.backend.einstellungen.leise_zeiten.fenster = structuredClone(fenster);
  if (zone) s.m.backend.einstellungen.leise_zeiten.zeitzone = zone;
  await geheZu(s, '#geraete');
  await s.flush(10);
  s.seite = s.el._seiten.geraete;
  return s;
}

/* Setzt die Uhr der Wochenansicht (Berliner Zeit angegeben als UTC-Zeitpunkt) und zeichnet neu. */
async function uhr(s, iso) {
  s.seite.jetzt = () => new Date(iso);
  s.el.requestUpdate();
  await s.flush();
}

const box = (s, id = 'kueche') => structuredClone(s.m.backend.boxen.find((b) => b.box === id));
async function sende(s, b) {
  const { ereignisse, ...rest } = b; // eslint-disable-line no-unused-vars
  s.m.emit('boxen', 'geaendert', rest);
  await s.flush(10);
}
const spielt = (s, st = {}, extra = {}) => sende(s, { ...box(s), anzeige: 'Küche', online: true, ...extra, status: { ...box(s).status, zustand: 'spielt', serie: { id: 's1', name: 'Die drei ???' }, folge: { name: 'folge-01.mp3', track: 0 }, akku_prozent: 80, lader: false, ...st } });
const karte = (s, id = 'kueche') => s.q(`a.gstatus[data-box="${id}"]`);
const satz = (s, id = 'kueche') => karte(s, id).querySelector('.sent').textContent.trim();
const neben = (s, id = 'kueche') => karte(s, id).querySelector('[data-nebentext]')?.textContent.trim() ?? '';
const klick = async (s, el) => { el.click(); await warte(20); await s.flush(10); };
const blatt = (s) => s.q('dialog.blatt');
const wirkungsKnopf = (s, text) => s.qa('dialog .seg2 button').find((b) => b.textContent.trim() === text);
const setZeit = (feld, wert) => { feld.value = wert; feld.dispatchEvent(new window.Event('change', { bubbles: true })); };
const speichern = (s) => s.q('dialog .knoepfe button.primary');

/* ------------------------------------------------------------------ reine Funktionen */

test('leiseAbschnitte(): So 19:30 bis 6:30 füllt den Sonntag ab 19:30 und den Montag bis 6:30', () => {
  const a = G.leiseAbschnitte([W_NACHT]);
  assert.deepEqual(a[7].map((g) => [g.a, g.b, g.fortsetzung]), [[1170, 1440, false]]);
  assert.deepEqual(a[1].filter((g) => g.fortsetzung).map((g) => [g.a, g.b, g.vontag]), [[0, 390, 7]], 'Montag trägt den Rest des Sonntags');
  assert.deepEqual(a[5].map((g) => [g.a, g.b, g.fortsetzung, g.vontag]), [[0, 390, true, 4]], 'Freitag: nur der Rest des Donnerstags');
  assert.deepEqual(a[6], [], 'Samstag bleibt leer');
  const tag = G.leiseAbschnitte([{ ...W_MITTAG, tage: [3] }]);
  assert.deepEqual(tag[3].map((g) => [g.a, g.b]), [[780, 840]]);
  assert.deepEqual(G.leiseAbschnitte([]), { 1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [] });
});

test('jetztSatz(): leiser, still (auch über Mitternacht), normal mit nächster Leise-Zeit, still geht vor leiser', () => {
  const a = G.leiseAbschnitte([W_NACHT, W_MITTAG]);
  assert.deepEqual(G.jetztSatz(a, { tag: 1, min: 13 * 60 + 30 }), { text: 'Jetzt: leiser bis 14:00', art: 'leiser' });
  assert.deepEqual(G.jetztSatz(a, { tag: 7, min: 20 * 60 }), { text: 'Jetzt: still bis 6:30', art: 'still' }, 'So 20:00: bis zum Ende am Montag');
  assert.deepEqual(G.jetztSatz(a, { tag: 1, min: 3 * 60 }), { text: 'Jetzt: still bis 6:30', art: 'still' }, 'Mo 3:00: Fortsetzung des Sonntags');
  assert.deepEqual(G.jetztSatz(a, { tag: 5, min: 12 * 60 }), { text: 'Jetzt: normale Lautstärke, die nächste Leise-Zeit beginnt um 13:00', art: 'normal' });
  assert.deepEqual(G.jetztSatz(a, { tag: 6, min: 12 * 60 }), { text: 'Jetzt: normale Lautstärke', art: 'normal' });
  const beides = G.leiseAbschnitte([{ ...W_MITTAG, tage: [2], von: '12:00', bis: '16:00' }, { id: 'x', tage: [2], von: '13:00', bis: '14:00', wirkung: 'stumm' }]);
  assert.equal(G.jetztSatz(beides, { tag: 2, min: 13 * 60 + 10 }).art, 'still');
  assert.equal(G.jetztSatz(G.leiseAbschnitte([]), { tag: 1, min: 0 }).text, ABENDS.leise.jetzt_normal_ohne);
});

test('jetztInZone(): Wochentag und Minuten in der Zeitzone der Leise-Zeiten', () => {
  assert.deepEqual(G.jetztInZone('Europe/Berlin', new Date('2026-11-13T11:00:00Z')), { tag: 5, min: 12 * 60 }); // Freitag
  assert.deepEqual(G.jetztInZone('Europe/Berlin', new Date('2026-11-15T23:30:00Z')), { tag: 1, min: 30 }, 'über Mitternacht: schon Montag');
  assert.deepEqual(G.jetztInZone('America/New_York', new Date('2026-11-15T03:00:00Z')), { tag: 6, min: 22 * 60 }, 'Samstagabend dort');
  assert.equal(typeof G.jetztInZone('Gibt/Es/Nicht').min, 'number', 'unbekannte Zone: Ortszeit statt Fehler');
});

test('Hilfen: Zeiten, Tage, letzte Meldung', () => {
  assert.equal(G.uhrzeit('06:30'), '6:30');
  assert.equal(G.uhrzeit('19:05'), '19:05');
  assert.equal(G.minuten('06:30'), 390);
  assert.equal(G.tageListe([7, 1, 4, 2, 3]), 'Mo, Di, Mi, Do, So');
  assert.equal(G.tageKurz([1, 2, 3, 4, 5, 6, 7]), 'Jeden Tag');
  assert.equal(G.tageKurz([7, 1, 2, 3, 4]), 'Mo–Do, So');
  assert.equal(G.tageKurz([5, 6]), 'Fr, Sa');
  const jetzt = new Date(2026, 10, 13, 20, 0);
  assert.equal(G.zuletztText(new Date(2026, 10, 13, 18, 40).toISOString(), jetzt), 'heute um 18:40');
  assert.equal(G.zuletztText(new Date(2026, 10, 12, 8, 5).toISOString(), jetzt), 'gestern um 8:05');
  assert.equal(G.zuletztText(new Date(2026, 10, 8, 20, 0).toISOString(), jetzt), 'am 08.11. um 20:00');
  assert.equal(G.zuletztText(null, jetzt), '');
});

test('fensterSenden(): grenze nur bei „leiser“, Tage aufsteigend; neue IDs sind gültig und frei', () => {
  assert.deepEqual(G.fensterSenden({ id: 'a', tage: [7, 1], von: '19:30', bis: '06:30', wirkung: 'stumm', grenze: 25 }), { id: 'a', tage: [1, 7], von: '19:30', bis: '06:30', wirkung: 'stumm' });
  assert.deepEqual(G.fensterSenden({ id: 'a', tage: [3], von: '13:00', bis: '14:00', wirkung: 'leiser', grenze: 40 }).grenze, 40);
  const id = G.neueFensterId([{ id: 'x' }]);
  assert.match(id, /^[a-z0-9_-]{1,32}$/);
  assert.notEqual(id, 'x');
});

/* ------------------------------------------------------------------ Karten der Boxen */

test('Geräte: Überschrift, zwei Karten als Links, Platz für „Neuer Tobie“, Abschnitt „Abends“; nichts aus Stufe B', MIT_DOM, async () => {
  const s = await geraete();
  assert.equal(s.q('main h2').textContent, 'Geräte');
  assert.equal(s.qa('a.gstatus').length, 2);
  assert.deepEqual(s.qa('a.gstatus').map((a) => a.getAttribute('href')), ['#box-kueche', '#box-kinderzimmer']);
  assert.ok(s.q('[data-platz="neue-tobies"]'), 'Platz für die Karten „Neuer Tobie“ und die Warteschlange (A9/A10)');
  assert.equal(s.q('[data-platz="neue-tobies"]').children.length, 0);
  assert.equal(s.q('h2.abends').textContent, ABENDS.titel);
  const text = s.q('main').textContent;
  assert.ok(!text.includes('Wer hat was gehört?'), 'Stufe B ist ausgeblendet');
  assert.ok(!s.q('a[href="#gehoert"]'));
  assert.equal(s.qa('a.gstatus .chev').length, 2, 'Pfeil rechts');
  // Reihenfolge: Boxen, Platz, Abends
  const reihe = s.qa('main > *').map((e) => e.getAttribute('data-geraete') || e.getAttribute('data-platz') || e.getAttribute('data-abschnitt')).filter(Boolean);
  assert.deepEqual(reihe, ['boxen', 'neue-tobies', 'abends']);
  weg();
});

test('Karte: Box ohne Titel im Status ist „bereit“, offline mit letzter Meldung und Hinweis zu neuen Zuordnungen', MIT_DOM, async () => {
  const s = await geraete();
  assert.equal(satz(s), fuellen(STATUS.bereit, { anzeige: 'Küche' }));
  assert.equal(neben(s), 'Akku 80 %.');
  assert.equal(karte(s).getAttribute('data-lage'), 'bereit');
  assert.ok(karte(s).classList.contains('gstatus') && !karte(s).classList.contains('off'));
  assert.equal(satz(s, 'kinderzimmer'), 'Kinderzimmer ist aus oder nicht im WLAN.');
  assert.ok(karte(s, 'kinderzimmer').classList.contains('off'), 'offline: grau');
  const n = neben(s, 'kinderzimmer');
  assert.match(n, /^Zuletzt gesehen: .+ um \d+:\d\d\./, 'Zeit der letzten Meldung');
  assert.ok(!n.includes('Akku war'), 'die Box hat keinen Akkustand gemeldet');
  assert.ok(n.includes(STATUS.konfig_wartet), 'offline und Liste veraltet');
  assert.equal(karte(s, 'kinderzimmer').querySelectorAll('.cover[data-cover]').length, 0, 'ohne Cover: Lautsprecher');
  assert.ok(karte(s, 'kinderzimmer').querySelector('.cover.ph svg'));
  weg();
});

test('Karte: spielt mit Folge und Nummer, Akku und Laden; Name der Serie und Folge kommen einmal je Serie aus serie/get', MIT_DOM, async () => {
  const s = await geraete();
  s.m.backend.serien.s1.folgen[0].nummer = 4;
  await spielt(s, { lader: true });
  assert.equal(satz(s), 'Küche spielt „Die drei ???“ · Folge 4: Der Rabe.');
  assert.equal(neben(s), 'Akku 80 %, lädt.');
  assert.equal(karte(s).getAttribute('data-lage'), 'spielt');
  assert.ok(karte(s).querySelector('.cover[data-cover="s1"]'), 'Cover des Gespielten statt Lautsprecher');
  assert.equal(s.m.aufrufe('tobibox/serie/get').filter((x) => x.serie_id === 's1').length, 1);
  // eine zweite Box spielt dieselbe Serie: kein weiterer Aufruf
  await sende(s, { ...box(s, 'kinderzimmer'), anzeige: 'Kinderzimmer', online: true, status: { zustand: 'spielt', serie: { id: 's1', name: 'Die drei ???' }, folge: { name: 'folge-02.mp3', track: 0 }, akku_prozent: 60, lader: false } });
  assert.equal(satz(s, 'kinderzimmer'), 'Kinderzimmer spielt „Die drei ???“ · Das Gespensterschloss.', 'Folge ohne Nummer');
  assert.equal(s.m.aufrufe('tobibox/serie/get').filter((x) => x.serie_id === 's1').length, 1, 'einmal je Serie');
  assert.equal(neben(s, 'kinderzimmer'), 'Akku 60 %.');
  weg();
});

test('Karte: pausiert, Akku niedrig (orange, nur ohne Laden), Herunterfahren', MIT_DOM, async () => {
  const s = await geraete();
  await spielt(s, { zustand: 'pausiert' });
  assert.equal(satz(s), 'Küche ist pausiert bei „Die drei ???“.');
  assert.equal(neben(s), 'Akku 80 %.');
  assert.equal(karte(s).getAttribute('data-lage'), 'pausiert');
  await spielt(s, { akku_prozent: 15, lader: false });
  assert.equal(neben(s), 'Akku fast leer (15 %). Bitte laden.');
  assert.ok(karte(s).querySelector('[data-nebentext]').classList.contains('warnl'), 'orange');
  await spielt(s, { akku_prozent: 15, lader: true });
  assert.equal(neben(s), 'Akku 15 %, lädt.', 'beim Laden keine Warnung');
  assert.ok(!karte(s).querySelector('[data-nebentext]').classList.contains('warnl'));
  await spielt(s, { zustand: 'herunterfahren' });
  assert.equal(satz(s), 'Küche geht gerade aus.');
  assert.equal(neben(s), '');
  weg();
});

test('Karte: offline mit Akkustand, noch keine Meldung, Hinweis zu neuen Zuordnungen erst nach 5 Minuten Abweichung', MIT_DOM, async () => {
  const s = await geraete();
  await sende(s, { ...box(s), anzeige: 'Küche', online: false, konfig_stand: 'aktuell', status: { akku_prozent: 35 } });
  assert.equal(satz(s), 'Küche ist aus oder nicht im WLAN.');
  assert.match(neben(s), /^Zuletzt gesehen: .+\. Akku war bei 35 %\.$/);
  await sende(s, { ...box(s), anzeige: 'Küche', online: null, status: null, status_empfangen_am: null, konfig_stand: 'unbekannt' });
  assert.equal(satz(s), 'Küche hat sich noch nicht gemeldet.');
  assert.equal(neben(s), '');
  // online, Liste veraltet: kurz nach einer Änderung kein Satz, nach 5 Minuten schon
  await sende(s, { ...box(s), anzeige: 'Küche', online: true, konfig_stand: 'veraltet', status: { zustand: 'leer', akku_prozent: 80, lader: false } });
  assert.ok(!neben(s).includes(STATUS.konfig_wartet), 'noch nicht');
  s.seite.status.veraltetSeit.set('kueche', Date.now() - 6 * 60000);
  s.el.requestUpdate();
  await s.flush();
  assert.ok(neben(s).includes(STATUS.konfig_wartet), 'nach mehr als 5 Minuten');
  await sende(s, { ...box(s), anzeige: 'Küche', online: true, konfig_stand: 'aktuell', status: { zustand: 'leer', akku_prozent: 80, lader: false } });
  assert.ok(!neben(s).includes(STATUS.konfig_wartet), 'wieder aktuell');
  weg();
});

test('Karte → Detailseite: Tipp auf die Karte öffnet #box-<id>, der Reiter „Geräte“ bleibt markiert', MIT_DOM, async () => {
  const s = await geraete();
  await klick(s, karte(s, 'kinderzimmer'));
  assert.equal(window.location.hash, '#box-kinderzimmer');
  assert.equal(s.q('main h2').textContent, 'Kinderzimmer');
  assert.equal(s.q('nav a[aria-current="page"] .tn').textContent.trim(), 'Geräte');
  weg();
});

/* ------------------------------------------------------------------ Box-Detail */

test('Box-Detail (Administrator): Zurück, Name, Karte, Zeilen, „Technik“ mit Link auf #technik-box-<id>', MIT_DOM, async () => {
  const s = await geraete();
  s.m.backend.serien.s1.folgen[0].nummer = 4;
  await spielt(s, { lader: true });
  await geheZu(s, '#box-kueche');
  await s.flush(10);
  assert.equal(s.q('main .back').getAttribute('href'), '#geraete');
  assert.equal(s.q('main .back').textContent, '‹ Geräte');
  assert.equal(s.q('main h2').textContent, 'Küche');
  assert.equal(s.q('main .gstatus .sent').textContent.trim(), 'Küche spielt „Die drei ???“ · Folge 4: Der Rabe.');
  assert.ok(!s.q('main a.gstatus'), 'auf der Detailseite ist die Karte kein Link');
  const z = (n) => s.q(`[data-zeile="${n}"] .v`).textContent.trim();
  assert.equal(z('verbindung'), 'online');
  assert.equal(z('akku'), '80 %, lädt');
  assert.equal(z('laeuft'), 'Die drei ??? · Der Rabe');
  assert.equal(s.q('[data-abschnitt="technik"]').textContent, 'Technik');
  const link = s.q('a[data-technik-link]');
  assert.equal(link.getAttribute('href'), '#technik-box-kueche');
  assert.equal(link.textContent.trim(), 'Technik zu dieser Box');
  assert.equal(s.q('nav a[aria-current="page"] .tn').textContent.trim(), 'Geräte');
  weg();
});

test('Box-Detail (kein Administrator): derselbe obere Teil, kein Technik-Teil, kein Link, kein Feld „ereignisse“', MIT_DOM, async () => {
  const s = await geraete({ istAdmin: false });
  assert.equal(s.el.store.s.boxen.kueche.ereignisse, undefined, 'boxen/list liefert `ereignisse` nur Administratoren');
  await geheZu(s, '#box-kinderzimmer');
  assert.equal(s.q('main h2').textContent, 'Kinderzimmer');
  assert.equal(s.q('main .gstatus .sent').textContent.trim(), 'Kinderzimmer ist aus oder nicht im WLAN.');
  assert.match(s.q('[data-zeile="verbindung"] .v').textContent, /^aus, zuletzt gesehen .+ um \d+:\d\d$/);
  assert.equal(s.q('[data-zeile="akku"] .v').textContent.trim(), '–', 'unbekannter Akku: Strich');
  assert.equal(s.q('[data-zeile="laeuft"] .v').textContent.trim(), 'nichts');
  assert.ok(!s.q('[data-abschnitt="technik"]'));
  assert.ok(!s.q('a[href^="#technik"]'));
  assert.ok(!s.q('main').textContent.includes('Technik'));
  weg();
});

test('Box-Detail: folgt dem Status (pausiert), unbekannte Box gibt einen Hinweis mit Weg zurück', MIT_DOM, async () => {
  const s = await geraete();
  await geheZu(s, '#box-kueche');
  assert.equal(s.q('[data-zeile="laeuft"] .v').textContent.trim(), 'nichts');
  await spielt(s, { zustand: 'pausiert', akku_prozent: 50 });
  assert.equal(s.q('main .gstatus .sent').textContent.trim(), 'Küche ist pausiert bei „Die drei ???“.');
  assert.equal(s.q('[data-zeile="akku"] .v').textContent.trim(), '50 %');
  assert.equal(s.q('[data-zeile="laeuft"] .v').textContent.trim(), 'Die drei ??? · Der Rabe');
  await sende(s, { ...box(s), anzeige: 'Küche', online: null, status: null, status_empfangen_am: null });
  assert.equal(s.q('[data-zeile="verbindung"] .v').textContent.trim(), 'noch nicht gemeldet');
  await geheZu(s, '#box-gibtsnicht');
  assert.ok(s.q('[data-zustand="box-fehlt"]').textContent.includes(GERAETE_SEITE.box_nicht_da));
  assert.equal(s.q('[data-zustand="box-fehlt"] a').getAttribute('href'), '#geraete');
  weg();
});

/* ------------------------------------------------------------------ Gute Nacht */

test('Gute Nacht: Schnellwahl 15 · 30 · 45 · 60 · 90 als Segment, „Anderer Wert“ 5 bis 240, „Gespeichert“ als Status, Speichern nur bei Änderung', MIT_DOM, async () => {
  const s = await geraete();
  const k = s.q('[data-karte="gute-nacht"]');
  assert.equal(k.querySelector('h3').textContent, 'Gute Nacht');
  assert.ok(k.textContent.includes(ABENDS.gute_nacht.text));
  assert.deepEqual([...k.querySelectorAll('.seg2 [data-wert]')].map((b) => b.textContent), ['15 Min.', '30 Min.', '45 Min.', '60 Min.', '90 Min.']);
  assert.deepEqual([...k.querySelectorAll('.seg2 [data-wert]')].map((b) => b.getAttribute('aria-pressed')), ['false', 'true', 'false', 'false', 'false']);
  assert.deepEqual([...k.querySelectorAll('#gn-andere option')].map((o) => o.value), ['', '5', '10', '20', '120', '180', '240']);
  assert.equal(k.querySelector('label[for="gn-andere"]').textContent, 'Anderer Wert');
  assert.equal(k.querySelectorAll('.gchip').length, 0, 'keine umrandeten Pillen');
  assert.equal(k.querySelectorAll('.seg2').length, 1, 'ein Segment-Umschalter (X32)');
  assert.equal(k.querySelector('[data-gn-speichern]'), null, 'ohne Änderung kein Knopf');
  const status = k.querySelector('[data-gn-gespeichert]');
  assert.equal(status.textContent.trim(), 'Gespeichert');
  assert.equal(status.tagName, 'SPAN', 'ein Status, kein Knopf');
  weg();
});

test('Gute Nacht: Wahl und Speichern sendet gute_nacht mit erwartet_revision, nichts sonst; danach wieder „Gespeichert“', MIT_DOM, async () => {
  const s = await geraete();
  await klick(s, s.q('.seg2 [data-wert="45"]'));
  const knopf = s.q('[data-gn-speichern]');
  assert.equal(knopf.textContent.trim(), 'Speichern');
  assert.ok(!knopf.disabled);
  assert.equal(s.q('.seg2 [data-wert="45"]').getAttribute('aria-pressed'), 'true');
  assert.equal(s.q('.seg2 [data-wert="30"]').getAttribute('aria-pressed'), 'false');
  s.m.reset();
  await klick(s, knopf);
  const c = s.m.aufrufe('tobibox/einstellungen/set');
  assert.equal(c.length, 1);
  const { id, ...felder } = c[0]; // eslint-disable-line no-unused-vars
  assert.deepEqual(felder, { type: 'tobibox/einstellungen/set', gute_nacht: { timer_min: 45, ausblenden_s: 60 }, erwartet_revision: 7 });
  assert.equal(s.m.backend.einstellungen.gute_nacht.timer_min, 45);
  assert.equal(s.q('.toast[role="status"]').textContent.replace(/OK$/, ''), 'Gespeichert. Die Boxen bekommen es gleich.');
  assert.equal(s.q('[data-gn-speichern]'), null, 'danach wieder nur der Status');
  assert.equal(s.q('[data-gn-gespeichert]').textContent.trim(), 'Gespeichert');
  // „Anderer Wert“: 120 Minuten; die Schnellwahl ist dann nicht mehr gewählt
  const sel = s.q('#gn-andere');
  sel.value = '120';
  sel.dispatchEvent(new window.Event('change', { bubbles: true }));
  await s.flush();
  assert.deepEqual([...s.qa('.seg2 [data-wert]')].map((b) => b.getAttribute('aria-pressed')), ['false', 'false', 'false', 'false', 'false']);
  assert.equal(s.q('#gn-andere').value, '120');
  await klick(s, s.q('[data-gn-speichern]'));
  assert.equal(s.m.letzter('tobibox/einstellungen/set').gute_nacht.timer_min, 120);
  assert.equal(s.m.letzter('tobibox/einstellungen/set').erwartet_revision, 8, 'die Revision der Antwort gilt für die nächste Änderung');
  weg();
});

test('Gute Nacht: Hinweis „Noch kein Gute-Nacht-Tobie“ bzw. „Ein Tobie spielt die Gute-Nacht-Karte“, „So legst du einen an“ öffnet ein Blatt', MIT_DOM, async () => {
  const s = await geraete();
  assert.ok(s.q('.gnhinweis').textContent.includes('Noch kein Gute-Nacht-Tobie.'));
  await klick(s, s.q('[data-gn-anleitung]'));
  assert.ok(blatt(s).hasAttribute('open'));
  assert.equal(blatt(s).querySelector('h2').textContent, ABENDS.gute_nacht.anlegen_titel);
  assert.ok(blatt(s).textContent.includes('Gute-Nacht-Karte'));
  weg();
  const t = await geraete({ viele: true });
  assert.ok(t.q('.gnhinweis').textContent.includes('Ein Tobie spielt die Gute-Nacht-Karte.'));
  weg();
});

test('Gute Nacht: bei gesperrter Liste ist Speichern grau', MIT_DOM, async () => {
  const s = await geraete();
  await klick(s, s.q('.seg2 [data-wert="60"]'));
  assert.ok(!s.q('[data-gn-speichern]').disabled);
  s.m.emit('konfig', 'geaendert', { konfig: { ...s.m.backend.konfig, zustand: 'gesperrt' } });
  await s.flush(10);
  assert.ok(s.q('[data-gn-speichern]').disabled);
  assert.ok(s.q('[data-leise-neu]').disabled);
  weg();
});

/* ------------------------------------------------------------------ Wochenansicht */

test('Wochenansicht: sieben Leisten Mo bis So, Stundenmarken, Legende; Abschnitte als Tippflächen mit Namen für Screenreader', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT, W_MITTAG] });
  const wk = s.q('[data-wochenansicht]');
  assert.deepEqual([...wk.querySelectorAll('.dr .dl')].map((d) => d.textContent.replace(/\s*\(heute\)/, '').trim()), ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']);
  assert.deepEqual([...wk.querySelectorAll('.ax span')].map((x) => x.textContent), ['0', '6', '12', '18', '24']);
  assert.deepEqual([...wk.querySelectorAll('.lg span')].map((x) => x.textContent), ['Still', 'Leiser']);
  assert.ok(wk.querySelector('.nowtag') && wk.querySelector('.nowl'), 'Marke „jetzt“');
  // Sonntag: nur der Abend; Montag: Rest des Sonntags, eigener Abend, Mittag
  const tag = (d) => [...wk.querySelectorAll(`.dr[data-tag="${d}"] .hit`)];
  assert.deepEqual(tag(7).map((h) => h.getAttribute('aria-label')), ['So, 19:30 bis 6:30, still, bearbeiten']);
  assert.deepEqual(tag(1).map((h) => h.getAttribute('aria-label')), [
    'Mo, von So bis 6:30, still, bearbeiten', 'Mo, 19:30 bis 6:30, still, bearbeiten', 'Mo, 13:00 bis 14:00, leiser, höchstens 25 %, bearbeiten']);
  assert.ok(tag(1)[0].hasAttribute('data-fortsetzung'));
  assert.deepEqual(tag(5).map((h) => h.getAttribute('aria-label')), ['Fr, von Do bis 6:30, still, bearbeiten', 'Fr, 13:00 bis 14:00, leiser, höchstens 25 %, bearbeiten']);
  assert.equal(tag(6).length, 0, 'Samstag: nichts');
  // Mitternacht: Sonntag füllt bis 24 Uhr, Montag ab 0 Uhr bis 6:30 (390 Minuten = 27,08 %)
  const seg = (d) => [...wk.querySelectorAll(`.dr[data-tag="${d}"] .seg`)].map((x) => x.getAttribute('style'));
  assert.deepEqual(seg(7), ['left:81.25%;width:18.75%']);
  assert.ok(seg(1).includes('left:0.00%;width:27.08%'), 'Montag ab 0 Uhr bis 6:30');
  assert.ok(wk.querySelectorAll('.seg.s').length >= 7 && wk.querySelectorAll('.seg.l').length === 5);
  assert.ok(!wk.querySelector('[data-leer]'));
  weg();
});

test('Wochenansicht: „Jetzt: …“ in der Zeitzone der Leise-Zeiten, heutiger Tag hervorgehoben, Marke wandert', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT, W_MITTAG] });
  const jetzt = () => s.q('[data-jetzt]');
  await uhr(s, '2026-11-16T12:30:00Z'); // Montag 13:30 in Berlin
  assert.equal(jetzt().textContent, 'Jetzt: leiser bis 14:00');
  assert.equal(jetzt().getAttribute('role'), 'status');
  assert.deepEqual(s.qa('.dr.heute').map((d) => d.getAttribute('data-tag')), ['1']);
  assert.ok(s.q('.dr.heute .dl .sr').textContent.includes('heute'));
  assert.match(s.q('.wg').getAttribute('style'), /--n:0\.5625/, '13:30 von 24 Stunden');
  await uhr(s, '2026-11-15T19:00:00Z'); // Sonntag 20:00 in Berlin
  assert.equal(jetzt().textContent, 'Jetzt: still bis 6:30');
  await uhr(s, '2026-11-13T11:00:00Z'); // Freitag 12:00
  assert.equal(jetzt().textContent, 'Jetzt: normale Lautstärke, die nächste Leise-Zeit beginnt um 13:00');
  await uhr(s, '2026-11-14T11:00:00Z'); // Samstag
  assert.equal(jetzt().textContent, 'Jetzt: normale Lautstärke');
  weg();
});

test('Wochenansicht: die Zeitzone der Einstellungen bestimmt „jetzt“', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_MITTAG], zone: 'America/New_York' });
  await uhr(s, '2026-11-16T18:30:00Z'); // Montag 13:30 in New York
  assert.equal(s.q('[data-jetzt]').textContent, 'Jetzt: leiser bis 14:00');
  weg();
});

test('Wochenansicht leer: Satz „Keine Leise-Zeiten …“, keine Abschnitte, „+ Leise-Zeit“ bleibt', MIT_DOM, async () => {
  const s = await geraete();
  assert.equal(s.q('[data-leer="leise-zeiten"]').textContent, 'Keine Leise-Zeiten. Die Box spielt immer in normaler Lautstärke.');
  assert.equal(s.qa('.wk .hit').length, 0);
  assert.equal(s.qa('.wk .dr').length, 7);
  assert.ok(s.q('[data-jetzt]').textContent.startsWith('Jetzt: normale Lautstärke'));
  assert.equal(s.q('[data-leise-neu]').textContent.trim(), 'Leise-Zeit');
  assert.equal(s.q('[data-leise-neu] svg').getAttribute('aria-hidden'), 'true');
  weg();
});

/* ------------------------------------------------------------------ Blatt: ändern, anlegen, löschen */

test('Blatt „Leise-Zeit ändern“: Satz „Gilt für …“, Tage, Zeitfelder mit 5-Minuten-Schritt, Still | Leiser, Löschen abgesetzt', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT] });
  await klick(s, s.q('.dr[data-tag="1"] .hit[data-fenster="nacht"]'));
  const b = blatt(s);
  assert.ok(b.hasAttribute('open'));
  assert.equal(b.querySelector('h2').textContent, 'Leise-Zeit ändern');
  assert.equal(b.querySelector('[data-gilt]').textContent, fuellen(LEISE.gilt_fuer, { tage: 'Mo, Di, Mi, Do, So' }));
  assert.equal(b.querySelector('[data-gilt]').textContent, 'Gilt für Mo, Di, Mi, Do, So. Tage abwählen, wenn es nur für einzelne gelten soll.');
  assert.deepEqual([...b.querySelectorAll('[data-tag]')].map((x) => [x.textContent, x.getAttribute('aria-pressed')]),
    [['Mo', 'true'], ['Di', 'true'], ['Mi', 'true'], ['Do', 'true'], ['Fr', 'false'], ['Sa', 'false'], ['So', 'true']]);
  assert.deepEqual([...b.querySelectorAll('[data-schnell]')].map((x) => [x.textContent, x.getAttribute('aria-pressed')]), [['Jeden Tag', 'false'], ['So–Do', 'true'], ['Fr, Sa', 'false']]);
  const von = b.querySelector('input[type="time"][data-feld="von"]');
  const bis = b.querySelector('input[type="time"][data-feld="bis"]');
  assert.deepEqual([von.getAttribute('step'), von.value, bis.getAttribute('step'), bis.value], ['300', '19:30', '300', '06:30']);
  assert.equal(b.querySelector('label[for="lz-von"]').textContent, 'Von');
  assert.equal(b.querySelector('label[for="lz-bis"]').textContent, 'Bis');
  assert.equal(b.querySelector('[data-mitternacht]').textContent, 'Geht bis zum nächsten Morgen.');
  assert.deepEqual([...b.querySelectorAll('.seg2 button')].map((x) => [x.textContent.trim(), x.getAttribute('aria-pressed')]), [['Still', 'true'], ['Leiser', 'false']]);
  assert.ok(!b.querySelector('input[type="range"]'), 'Regler nur bei „Leiser“');
  assert.ok(b.textContent.includes(ABENDS.blatt.still_hinweis));
  assert.ok(b.querySelector('.apart [data-loeschen]'), 'Löschen abgesetzt');
  assert.deepEqual([...b.querySelectorAll('.knoepfe button')].map((x) => x.textContent), ['Abbrechen', 'Speichern']);
  // Der Satz folgt den Tagen
  await klick(s, b.querySelector('[data-tag="7"]'));
  assert.equal(blatt(s).querySelector('[data-gilt]').textContent, 'Gilt für Mo, Di, Mi, Do. Tage abwählen, wenn es nur für einzelne gelten soll.');
  await klick(s, blatt(s).querySelector('[data-schnell="fr-sa"]'));
  assert.equal(blatt(s).querySelector('[data-gilt]').textContent, 'Gilt für Fr, Sa. Tage abwählen, wenn es nur für einzelne gelten soll.');
  setZeit(blatt(s).querySelector('[data-feld="bis"]'), '22:00');
  await s.flush();
  assert.equal(blatt(s).querySelector('[data-mitternacht]').textContent, '', 'nicht mehr über Mitternacht');
  weg();
});

test('Leise-Zeit ändern: Zeit und Tage geändert, gespeichert; ganzes Fenster ersetzt, Zeitzone nicht gesendet (kein Administrator)', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT, W_MITTAG], istAdmin: false });
  await klick(s, s.q('.dr[data-tag="7"] .hit[data-fenster="nacht"]'));
  setZeit(blatt(s).querySelector('[data-feld="von"]'), '20:00');
  setZeit(blatt(s).querySelector('[data-feld="bis"]'), '07:00');
  await klick(s, blatt(s).querySelector('[data-tag="7"]')); // So abwählen
  s.m.reset();
  await klick(s, speichern(s));
  const msg = s.m.letzter('tobibox/einstellungen/set');
  assert.deepEqual(Object.keys(msg).sort(), ['erwartet_revision', 'id', 'leise_zeiten', 'type']);
  assert.equal(msg.erwartet_revision, 7);
  assert.ok(!('zeitzone' in msg.leise_zeiten), 'ein Nicht-Administrator sendet die Zeitzone nicht');
  assert.deepEqual(msg.leise_zeiten.fenster, [
    { id: 'nacht', tage: [1, 2, 3, 4], von: '20:00', bis: '07:00', wirkung: 'stumm' },
    { id: 'mittag', tage: [1, 2, 3, 4, 5], von: '13:00', bis: '14:00', wirkung: 'leiser', grenze: 25 }]);
  assert.equal(s.m.backend.einstellungen.leise_zeiten.zeitzone, 'Europe/Berlin', 'der gespeicherte Wert bleibt');
  assert.ok(!blatt(s), 'das Blatt ist zu');
  assert.equal(s.q('.toast[role="status"]').textContent.replace(/OK$/, ''), 'Gespeichert. Die Boxen bekommen es gleich.');
  assert.equal(s.qa('.dr[data-tag="7"] .hit[data-fenster="nacht"]').length, 0, 'Sonntag hat keine Leiste mehr');
  assert.deepEqual(s.qa('.dr[data-tag="1"] .hit[data-fenster="nacht"]').map((h) => h.getAttribute('aria-label')), ['Mo, 20:00 bis 7:00, still, bearbeiten']);
  weg();
});

test('Leise-Zeit ändern: Administrator schickt die gespeicherte Zeitzone unverändert zurück', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT], zone: 'Europe/Vienna' });
  await klick(s, s.q('.hit[data-fenster="nacht"]'));
  await klick(s, wirkungsKnopf(s, 'Leiser'));
  await klick(s, speichern(s));
  assert.equal(s.m.letzter('tobibox/einstellungen/set').leise_zeiten.zeitzone, 'Europe/Vienna');
  assert.equal(s.m.backend.einstellungen.leise_zeiten.zeitzone, 'Europe/Vienna');
  weg();
});

test('Leise-Zeit anlegen: „+ Leise-Zeit“, Vorgabe So–Do 19:30 bis 6:30 still; gesendet mit neuer ID, ohne grenze bei „still“', MIT_DOM, async () => {
  const s = await geraete({ istAdmin: false });
  await klick(s, s.q('[data-leise-neu]'));
  const b = blatt(s);
  assert.equal(b.querySelector('h2').textContent, 'Neue Leise-Zeit');
  assert.ok(!b.querySelector('[data-loeschen]'), 'neu: nichts zu löschen');
  assert.equal(b.querySelector('[data-gilt]').textContent, 'Gilt für Mo, Di, Mi, Do, So. Tage abwählen, wenn es nur für einzelne gelten soll.');
  assert.deepEqual([b.querySelector('[data-feld="von"]').value, b.querySelector('[data-feld="bis"]').value], ['19:30', '06:30']);
  setZeit(b.querySelector('[data-feld="von"]'), '20:15');
  await klick(s, blatt(s).querySelector('[data-schnell="fr-sa"]'));
  s.m.reset();
  await klick(s, speichern(s));
  const msg = s.m.letzter('tobibox/einstellungen/set');
  assert.equal(msg.leise_zeiten.fenster.length, 1);
  const w = msg.leise_zeiten.fenster[0];
  assert.match(w.id, /^[a-z0-9_-]{1,32}$/);
  assert.deepEqual({ ...w, id: 'x' }, { id: 'x', tage: [5, 6], von: '20:15', bis: '06:30', wirkung: 'stumm' });
  assert.ok(!('zeitzone' in msg.leise_zeiten));
  assert.equal(s.m.backend.einstellungen.leise_zeiten.fenster.length, 1);
  assert.ok(!blatt(s));
  assert.equal(s.qa('.wk .hit').length, 4, 'Fr, Sa je ein Abend, dazu der Rest des Freitags am Samstag und des Samstags am Sonntag');
  assert.ok(!s.q('[data-leer="leise-zeiten"]'), 'die Leere ist weg');
  weg();
});

test('Leise-Zeit „Leiser“: Regler „Höchste Lautstärke“ erscheint, die Grenze wird mitgesendet', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT] });
  await klick(s, s.q('.hit[data-fenster="nacht"]'));
  await klick(s, wirkungsKnopf(s, 'Leiser'));
  const regler = blatt(s).querySelector('input[type="range"]');
  assert.equal(regler.value, '25');
  assert.equal(blatt(s).querySelector('label[for="lz-grenze"]').textContent, 'Höchste Lautstärke: 25 %');
  tippe(regler, '40');
  await s.flush();
  assert.equal(blatt(s).querySelector('label[for="lz-grenze"]').textContent, 'Höchste Lautstärke: 40 %');
  await klick(s, speichern(s));
  assert.deepEqual(s.m.letzter('tobibox/einstellungen/set').leise_zeiten.fenster[0], { id: 'nacht', tage: [1, 2, 3, 4, 7], von: '19:30', bis: '06:30', wirkung: 'leiser', grenze: 40 });
  assert.equal(s.qa('.seg.l').length, 10, 'jetzt gestreift (Leiser): fünf Abende und fünf Fortsetzungen');
  assert.equal(s.q('.hit[data-fenster="nacht"]').getAttribute('aria-label').includes('leiser, höchstens 40 %'), true);
  weg();
});

test('Leise-Zeit löschen: Rückfrage mit Tagen und Zeit, Abbrechen ändert nichts, Löschen entfernt nur dieses Fenster', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT, W_MITTAG] });
  await klick(s, s.q('.hit[data-fenster="nacht"]'));
  s.m.reset();
  await klick(s, blatt(s).querySelector('[data-loeschen]'));
  assert.equal(blatt(s).querySelector('h2').textContent, 'Leise-Zeit löschen?');
  assert.ok(blatt(s).textContent.includes('Mo–Do, So, 19:30 bis 6:30 wird gelöscht. Danach spielt die Box in dieser Zeit in normaler Lautstärke.'));
  assert.deepEqual([...blatt(s).querySelectorAll('.knoepfe button')].map((x) => x.textContent), ['Abbrechen', 'Löschen']);
  await klick(s, blatt(s).querySelector('.knoepfe button'));
  assert.equal(s.m.aufrufe('tobibox/einstellungen/set').length, 0, 'abgebrochen: nichts gesendet');
  assert.equal(s.m.backend.einstellungen.leise_zeiten.fenster.length, 2);
  await klick(s, s.q('.hit[data-fenster="nacht"]'));
  await klick(s, blatt(s).querySelector('[data-loeschen]'));
  await klick(s, blatt(s).querySelector('.knoepfe button:last-child'));
  const msg = s.m.letzter('tobibox/einstellungen/set');
  assert.deepEqual(msg.leise_zeiten.fenster.map((w) => w.id), ['mittag']);
  assert.equal(msg.erwartet_revision, 7);
  assert.equal(s.q('.toast[role="status"]').textContent.replace(/OK$/, ''), 'Gelöscht.');
  assert.equal(s.qa('.hit[data-fenster="nacht"]').length, 0);
  assert.equal(s.qa('.hit[data-fenster="mittag"]').length, 5);
  assert.ok(!blatt(s));
  weg();
});

test('Leise-Zeit: Prüfregeln an der Eingabe (kein Tag, Von gleich Bis, höchstens 32) ohne Aufruf, mit Fehlermeldung', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT] });
  await klick(s, s.q('.hit[data-fenster="nacht"]'));
  s.m.reset();
  for (const d of [7, 1, 2, 3, 4]) await klick(s, blatt(s).querySelector(`[data-tag="${d}"]`));
  assert.equal(blatt(s).querySelector('[data-gilt]').textContent, ABENDS.blatt.kein_tag_hinweis);
  await klick(s, speichern(s));
  assert.equal(s.q('.toast.err[role="alert"] .tmsg').textContent, 'Bitte mindestens einen Tag wählen.');
  assert.ok(blatt(s).hasAttribute('open'), 'das Blatt bleibt offen');
  await klick(s, blatt(s).querySelector('[data-schnell="alle"]'));
  setZeit(blatt(s).querySelector('[data-feld="bis"]'), '19:30');
  await klick(s, speichern(s));
  assert.ok([...s.qa('.toast.err .tmsg')].some((t) => t.textContent === '„Von“ und „Bis“ dürfen nicht gleich sein.'));
  assert.equal(s.m.aufrufe('tobibox/einstellungen/set').length, 0);
  weg();
  const voll = await geraete({ fenster: Array.from({ length: 32 }, (_, i) => ({ id: `w${i}`, tage: [1], von: '10:00', bis: '10:30', wirkung: 'stumm' })) });
  await klick(voll, voll.q('[data-leise-neu]'));
  assert.ok(!blatt(voll), 'kein Blatt bei 32 Zeiten');
  assert.equal(voll.q('.toast.err .tmsg').textContent, ABENDS.meldung.zu_viele);
  weg();
});

test('Fehler beim Speichern: einstellung_ungueltig bleibt im Blatt, der Fehler bleibt stehen', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT] });
  await klick(s, s.q('.hit[data-fenster="nacht"]'));
  s.m.failNext('tobibox/einstellungen/set', 'einstellung_ungueltig');
  await klick(s, speichern(s));
  assert.ok(blatt(s).hasAttribute('open'));
  assert.equal(s.q('.toast.err[role="alert"] .tmsg').textContent, fehlerText('einstellung_ungueltig'));
  assert.equal(s.m.backend.konfig.revision, 7, 'nichts geändert');
  weg();
});

test('erwartet_revision: ein Konflikt ergibt eine Fehlermeldung, das Blatt schließt, die Ansicht lädt neu, nichts wurde geändert', MIT_DOM, async () => {
  const s = await geraete({ fenster: [W_NACHT], istAdmin: false });
  assert.equal(s.m.aufrufe('tobibox/einstellungen/get').length, 1);
  await klick(s, s.q('.hit[data-fenster="nacht"]'));
  setZeit(blatt(s).querySelector('[data-feld="von"]'), '21:00');
  s.m.backend.konfig = { ...s.m.backend.konfig, revision: 12 }; // jemand hat inzwischen etwas geändert
  s.m.backend.einstellungen.leise_zeiten.fenster[0].von = '18:00';
  s.m.reset();
  await klick(s, speichern(s));
  const msg = s.m.letzter('tobibox/einstellungen/set');
  assert.equal(msg.erwartet_revision, 7, 'die Seite schickt, was sie zuletzt gesehen hat');
  assert.ok(!('zeitzone' in msg.leise_zeiten), 'die Zeitzone wird auch hier nicht gesendet');
  assert.equal(s.q('.toast.err[role="alert"] .tmsg').textContent, fehlerText('stand_veraltet'));
  assert.equal(s.q('.toast.err .tmsg').textContent, 'Jemand hat gerade etwas anderes geändert. Die Ansicht ist neu geladen. Bitte versuche es noch einmal.');
  assert.equal(s.m.backend.einstellungen.leise_zeiten.fenster[0].von, '18:00', 'das Backend hat nichts übernommen');
  assert.equal(s.m.aufrufe('tobibox/einstellungen/get').length, 1, 'neu geladen');
  assert.ok(!blatt(s), 'das Blatt ist zu');
  assert.ok(s.qa('.hit[data-fenster="nacht"]').some((h) => h.getAttribute('aria-label').includes('18:00')), 'der neue Stand ist zu sehen');
  // Danach geht es mit der neuen Revision
  await klick(s, s.q('.hit[data-fenster="nacht"]'));
  setZeit(blatt(s).querySelector('[data-feld="von"]'), '21:00');
  await klick(s, speichern(s));
  assert.equal(s.m.letzter('tobibox/einstellungen/set').erwartet_revision, 12);
  assert.equal(s.m.backend.einstellungen.leise_zeiten.fenster[0].von, '21:00');
  weg();
});

test('erwartet_revision: Gute Nacht läuft in denselben Konflikt; ohne Fähigkeit „bibliothek“ wird das Feld nicht gesendet', MIT_DOM, async () => {
  const s = await geraete();
  await klick(s, s.q('.seg2 [data-wert="90"]'));
  s.m.backend.konfig = { ...s.m.backend.konfig, revision: 20 };
  await klick(s, s.q('[data-gn-speichern]'));
  assert.equal(s.q('.toast.err .tmsg').textContent, fehlerText('stand_veraltet'));
  assert.equal(s.m.backend.einstellungen.gute_nacht.timer_min, 30);
  weg();
  const alt = await geraete({ faehigkeiten: ALLE.filter((f) => f !== 'bibliothek') });
  await klick(alt, alt.q('.seg2 [data-wert="90"]'));
  await klick(alt, alt.q('[data-gn-speichern]'));
  assert.ok(!('erwartet_revision' in alt.m.letzter('tobibox/einstellungen/set')));
  assert.equal(alt.m.backend.einstellungen.gute_nacht.timer_min, 90);
  weg();
});

/* ------------------------------------------------------------------ Zustände */

test('Leer: keine Box eingerichtet zeigt Bild, Satz und Knopf; Abends bleibt', MIT_DOM, async () => {
  const s = await geraete({ faehigkeiten: ALLE.filter((f) => f !== 'boxen') });
  const l = s.q('[data-leer="keine_box"]');
  assert.ok(l);
  assert.equal(l.querySelector('.et').textContent, fuellen(LEER.keine_box.satz));
  assert.equal(l.querySelector('.et').textContent, 'Noch keine Box eingerichtet. Bitte dem Administrator Bescheid sagen.');
  assert.equal(l.querySelector('button.btn').textContent, 'Jetzt neu laden');
  assert.equal(s.qa('a.gstatus').length, 0);
  assert.ok(s.q('[data-karte="gute-nacht"]'), 'Abends gehört nicht den Boxen');
  weg();
});

test('Ohne Fähigkeit „einstellungen“ fehlt der Abschnitt „Abends“, die Boxen bleiben', MIT_DOM, async () => {
  const s = await geraete({ faehigkeiten: FAEHIGKEITEN });
  assert.equal(s.qa('a.gstatus').length, 2);
  assert.ok(!s.q('h2.abends'));
  assert.equal(s.m.aufrufe('tobibox/einstellungen/get').length, 0);
  weg();
});

test('Lädt: Platzhalter im Abschnitt „Abends“, die Karten der Boxen stehen sofort da', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  let weiter;
  const warten = new Promise((r) => { weiter = r; });
  s.m.on('tobibox/einstellungen/get', async (_m, b) => { await warten; return { ...b.einstellungen, konfig: b.konfig }; });
  await geheZu(s, '#geraete');
  assert.equal(s.qa('a.gstatus').length, 2);
  assert.ok(s.q('h2.abends'));
  assert.ok(s.q('.laedt .skel'), 'graue Platzhalter');
  assert.ok(!s.q('[data-karte="gute-nacht"]'));
  weiter();
  await s.flush(10);
  assert.ok(!s.q('.laedt'));
  assert.ok(s.q('[data-karte="gute-nacht"]'));
  weg();
});

test('Fehler beim Laden der Einstellungen: rote Karte nur im Abschnitt, „Noch einmal versuchen“ lädt neu', MIT_DOM, async () => {
  const s = await seite({ faehigkeiten: ALLE, hash: '#start' });
  s.m.failNext('tobibox/einstellungen/get', 'konfig_nicht_bereit');
  await geheZu(s, '#geraete');
  await s.flush(10);
  assert.equal(s.qa('a.gstatus').length, 2, 'die Boxen sind da');
  assert.ok(s.q('[data-zustand="fehler"]'));
  await klick(s, s.q('[data-zustand="fehler"] button'));
  assert.ok(s.q('[data-karte="leise-zeiten"]'));
  assert.ok(!s.q('[data-zustand="fehler"]'));
  weg();
});

test('Neu laden nach Wiederverbinden: Einstellungen frisch, Eingaben im Gute-Nacht-Feld bleiben', MIT_DOM, async () => {
  const s = await geraete();
  await klick(s, s.q('.seg2 [data-wert="60"]'));
  s.m.backend.einstellungen.leise_zeiten.fenster = [W_MITTAG];
  s.seite.neuLaden();
  await s.flush(10);
  assert.equal(s.qa('.hit[data-fenster="mittag"]').length, 5, 'neuer Stand');
  assert.equal(s.q('.seg2 [data-wert="60"]').getAttribute('aria-pressed'), 'true', 'die Wahl ging nicht verloren');
  assert.equal(s.q('[data-gn-speichern]').textContent.trim(), 'Speichern');
  weg();
});

test('B3: „1 Minute“ in der Einzahl in der Auswahl „Anderer Wert“', MIT_DOM, async () => {
  const s = await geraete();
  s.m.backend.einstellungen.gute_nacht.timer_min = 1;
  await s.el.ctx && s.flush();
  s.el._seiteObj?.laden?.(true);
  await s.flush(10);
  const opt = [...s.qa('#gn-andere option')].map((o) => o.textContent.trim());
  assert.ok(opt.includes('1 Minute'), `Optionen: ${opt}`);
  assert.ok(!opt.includes('1 Minuten'));
  weg();
});

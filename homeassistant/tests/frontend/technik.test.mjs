/* Tests der Seite „Technik“ (AP A12/A13, Design 5.9, 9, 10). Aufruf: node --test homeassistant/tests/frontend
 *
 * Sechs Unterseiten (Boxen, Speicher und Netz, Liste und Sicherung, Tobies, Meldungen, Einstellungen) plus `#technik-box-<id>`,
 * die Einbettung der alten Komponente `tobibox-panel` mit `eingebettet` und `bereich`, Warnleisten für Administratoren,
 * Frühere Stände, „Cover neu suchen“, der Papierkorb („gelöscht von“, „Letzte Stunde zurückholen“, Leeren) und die Sperre für
 * Nicht-Administratoren. Backend aus mock-hass.mjs. Die alte Komponente läuft im selben DOM (eigene Tests: panel*.test.mjs).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { seite, geheZu, weg, warte, domBereit, MIT_DOM } from './dom-helfer.mjs';
import { FAEHIGKEITEN, mitStaenden } from './mock-hass.mjs';

if (MIT_DOM.skip === false) await domBereit(); // die alte Komponente definiert ihr Element nur, wenn das DOM vor dem Laden da ist
const { UNTERSEITEN, PANEL_BEREICHE, unterseite } = await import('../../custom_components/tobibox/frontend/seiten/technik.js');
const { TECHNIK, SEITE, fuellen } = await import('../../custom_components/tobibox/frontend/texte.js');
const { parseRoute } = await import('../../custom_components/tobibox/frontend/tobibox-app.js');

const ALLE = [...FAEHIGKEITEN, 'konfig_lesen', 'konfig_staende', 'hoerkopie', 'einstellungen', 'eingang_entfernen', 'zuordnung_uid'];
const OHNE = (...namen) => ALLE.filter((f) => !namen.includes(f));

async function technik(hash = '#technik', opts = {}) {
  const s = await seite({ hash, faehigkeiten: ALLE, ...opts });
  await s.flush(10);
  return s;
}
const bereiche = (s) => s.qa('tobibox-panel').map((p) => p.getAttribute('bereich'));
const knopf = (s, aktion) => s.q(`[data-aktion="${aktion}"]`);
const blattKnoepfe = (s) => s.qa('dialog[open] .knoepfe button');
const blattKnopf = (s, text) => blattKnoepfe(s).find((b) => b.textContent.trim() === text);
const toasts = (s) => s.qa('.toast').map((t) => t.textContent);

test('parseRoute: #technik, #technik-<bereich> und #technik-box-<id> werden zerlegt', () => {
  assert.deepEqual([parseRoute('#technik').name, parseRoute('#technik').sub], ['technik', undefined]);
  for (const u of UNTERSEITEN) {
    const r = parseRoute(`#technik-${u}`);
    assert.deepEqual([r.name, r.tab, r.sub, r.id, r.seite, r.zurueck], ['technik', 'technik', u, null, `technik_${u}`, 'technik']);
  }
  const r = parseRoute('#technik-box-kueche');
  assert.deepEqual([r.name, r.sub, r.id, r.seite], ['technik', 'box-kueche', 'kueche', 'technik_box']);
  assert.equal(unterseite(r), 'box');
  assert.equal(unterseite(parseRoute('#technik-boxen')), 'boxen', '„boxen“ ist keine Box');
  assert.equal(unterseite(parseRoute('#technik-unsinn')), null, 'unbekannte Unterseite: die Liste');
  assert.equal(unterseite(parseRoute('#technik')), null);
});

test('PANEL_BEREICHE: jede Unterseite hat ihren Bereich der alten Komponente', () => {
  assert.deepEqual(Object.keys(PANEL_BEREICHE).sort(), [...UNTERSEITEN, 'box'].sort());
  assert.deepEqual(UNTERSEITEN, ['boxen', 'speicher', 'liste', 'tobies', 'meldungen', 'einstellungen'], 'Reihenfolge wie im Design 5.9');
});

test('Technik (Administrator): sechs große Zeilen, jede mit Pfeil und Ziel #technik-<bereich>', MIT_DOM, async () => {
  const s = await technik();
  assert.equal(s.q('main h2').textContent, TECHNIK.titel);
  const zeilen = s.qa('[data-technik="liste"] a.tzeile');
  assert.deepEqual(zeilen.map((a) => a.getAttribute('href')), UNTERSEITEN.map((u) => `#technik-${u}`));
  assert.deepEqual(zeilen.map((a) => a.querySelector('strong').textContent), UNTERSEITEN.map((u) => TECHNIK.zeilen[u].titel));
  assert.ok(zeilen.every((a) => a.querySelector('svg')), 'Pfeil');
  assert.equal(s.qa('tobibox-panel').length, 0, 'die Liste bettet nichts ein');
  assert.equal(s.q('[data-zustand="nur-admin"]'), null);
  assert.ok(s.q('.rund.tech'), 'Technik-Symbol im Kopf für Administratoren');
  weg();
});

test('Technik (kein Administrator): die Sperre statt der Seite, kein Symbol, keine alte Komponente, keine Befehle der Seite', MIT_DOM, async () => {
  for (const hash of ['#technik', '#technik-papierkorb', '#technik-liste', '#technik-box-kueche']) {
    const s = await seite({ hash, darf: false, faehigkeiten: ALLE });
    await s.flush(10);
    assert.equal(s.q('[data-zustand="nur-admin"]').textContent.trim(), fuellen(SEITE.technik_nur_admin), hash);
    assert.equal(s.q('.rund.tech'), null);
    assert.equal(s.qa('tobibox-panel').length, 0, hash);
    assert.equal(s.m.aufrufe('tobibox/papierkorb/list').length + s.m.aufrufe('tobibox/konfig/export_lesen').length, 0, hash);
    weg();
  }
});

test('Jede Unterseite bettet die alte Komponente mit eingebettet und dem richtigen bereich ein', MIT_DOM, async () => {
  const erwartet = { boxen: ['boxen'], speicher: ['aufraeumen', 'eingang'], liste: ['liste'], tobies: ['tobies'], meldungen: ['meldungen'], einstellungen: ['einstellungen'] };
  for (const [u, soll] of Object.entries(erwartet)) {
    const s = await technik(`#technik-${u}`);
    assert.deepEqual(bereiche(s), soll, u);
    assert.deepEqual(PANEL_BEREICHE[u], soll, `${u}: Tabelle und Seite stimmen überein`);
    for (const p of s.qa('tobibox-panel')) {
      assert.ok(p.hasAttribute('eingebettet'), u);
      assert.ok(p.hass, `${u}: hass ist gesetzt`);
    }
    assert.equal(s.q('a.back').getAttribute('href'), '#technik', `${u}: oben links „‹ Technik“`);
    assert.equal(s.q('a.back').textContent, '‹ Technik');
    assert.equal(s.q('main h2').textContent, TECHNIK.zeilen[u].titel);
    weg();
  }
});

test('Eingebettet: die alte Komponente blendet Kopf und Reiterleiste aus und zeigt nur ihren Bereich', MIT_DOM, async () => {
  const s = await technik('#technik-tobies');
  const p = s.q('tobibox-panel');
  await warte(30); await s.flush(6);
  const w = p.shadowRoot;
  assert.equal(w.querySelector('header'), null, 'kein Kopf');
  assert.equal(w.querySelector('nav'), null, 'keine Reiterleiste');
  assert.equal(w.querySelector('.app').getAttribute('data-bereich'), 'tobies');
  assert.ok(/Kennung von Hand eingeben/.test(w.textContent), 'Kennung von Hand');
  assert.ok(!/Hochladen|Papierkorb leeren|Revision/.test(w.textContent), 'nichts von den anderen Bereichen');
  // ohne eingebettet bleibt es die alte Seite mit Kopf und Reitern
  const roh = document.createElement('tobibox-panel');
  roh.hass = s.m.hass;
  document.body.appendChild(roh);
  await warte(30); await roh.updateComplete;
  assert.ok(roh.shadowRoot.querySelector('header') && roh.shadowRoot.querySelector('nav'));
  roh.remove();
  weg();
});

test('Eingebettet: bereich „alle“ (Vorgabe) zeigt alle Bereiche nacheinander; „boxen“ mit box nur diese Box', MIT_DOM, async () => {
  const s = await technik('#technik-liste');
  const p = document.createElement('tobibox-panel');
  p.setAttribute('eingebettet', '');
  p.hass = s.m.hass;
  document.body.appendChild(p);
  await warte(40); await p.updateComplete;
  assert.deepEqual([...p.shadowRoot.querySelectorAll('[data-bereich-teil]')].map((x) => x.getAttribute('data-bereich-teil')),
    ['boxen', 'liste', 'aufraeumen', 'eingang', 'papierkorb', 'tobies', 'einstellungen', 'meldungen']);
  p.setAttribute('bereich', 'boxen'); p.setAttribute('box', 'kinderzimmer');
  await warte(10); await p.updateComplete;
  const titel = [...p.shadowRoot.querySelectorAll('.karte .titel')].map((x) => x.textContent.trim());
  assert.equal(titel.length, 1);
  assert.match(titel[0], /Kinderzimmer/);
  p.remove();
  weg();
});

test('Boxen: je Box eine Zeile mit #technik-box-<id>, darunter alle Boxen im Detail (alte Komponente)', MIT_DOM, async () => {
  const s = await technik('#technik-boxen');
  const zeilen = s.qa('[data-technik="boxen"] a.tzeile');
  assert.deepEqual(zeilen.map((a) => a.getAttribute('href')), ['#technik-box-kueche', '#technik-box-kinderzimmer']);
  assert.match(zeilen[0].textContent, /Küche/);
  assert.match(zeilen[0].textContent, /online · Liste aktuell/);
  assert.match(zeilen[1].textContent, /offline · Liste veraltet/);
  assert.deepEqual(bereiche(s), ['boxen']);
  assert.equal(s.q('tobibox-panel').hasAttribute('box'), false);
  weg();
});

test('Box-Seite #technik-box-<id>: Name, nur diese Box (bereich boxen, box), Weg zum Lernmodus; unbekannte Box: Hinweis', MIT_DOM, async () => {
  const s = await technik('#technik-box-kinderzimmer');
  assert.equal(s.q('main h2').textContent, 'Kinderzimmer');
  const p = s.q('tobibox-panel');
  assert.deepEqual([p.getAttribute('bereich'), p.getAttribute('box'), p.hasAttribute('eingebettet')], ['boxen', 'kinderzimmer', true]);
  assert.equal(s.q('a.back').getAttribute('href'), '#technik');
  assert.equal(s.qa('a.tzeile')[0].getAttribute('href'), '#technik-tobies');
  await geheZu(s, '#technik-box-gibtsnicht');
  assert.equal(s.qa('tobibox-panel').length, 0);
  assert.equal(s.q('[data-zustand="unbekannte-box"]').textContent.trim(), TECHNIK.box.unbekannte_box);
  await geheZu(s, '#technik-box-kueche');
  assert.equal(s.q('main h2').textContent, 'Küche');
  assert.equal(s.q('tobibox-panel').getAttribute('box'), 'kueche', 'derselbe Baustein, neue Box');
  weg();
});

test('Wechsel der Unterseite: die Seite wird je Unterseite neu betreten (Konfig und Boxen frisch, Stände nur auf „Liste“)', MIT_DOM, async () => {
  const s = await technik('#technik-meldungen');
  mitStaenden(s.m);
  const konfig = () => s.m.aufrufe('tobibox/konfig/get').length;
  const stand = () => s.m.aufrufe('tobibox/konfig/export_lesen').length;
  const k0 = konfig();
  assert.equal(stand(), 0);
  await geheZu(s, '#technik-speicher');
  assert.equal(konfig(), k0 + 1);
  assert.equal(stand(), 0);
  await geheZu(s, '#technik-liste');
  assert.equal(konfig(), k0 + 2);
  assert.equal(stand(), 1);
  await geheZu(s, '#technik');
  assert.equal(konfig(), k0 + 3);
  weg();
});

/* ------------------------------------------------------------------ Warnleisten */

test('Warnleisten: leer_neu mit Entscheidung (Export holen oder neu beginnen), nur für Administratoren, oben auf der Technik-Seite', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.backend.konfig = { revision: null, liste_id: null, zustand: 'leer_neu', export_ok: true, export_geschrieben_am: null };
  await geheZu(s, '#technik-liste');
  const band = s.q('[data-warnleiste="leer_neu"]');
  assert.ok(band, 'Warnleiste');
  assert.equal(band.getAttribute('role'), 'alert');
  assert.match(band.textContent, /Die Liste der Tobies ist leer/);
  assert.deepEqual([...band.querySelectorAll('button')].map((b) => b.textContent.trim()), [TECHNIK.warnband.leer_neu.aus_export, TECHNIK.warnband.leer_neu.neu]);
  assert.ok(s.q('main').firstElementChild.matches('a.back') && band.compareDocumentPosition(s.q('tobibox-panel')) & 4, 'oben, vor der Komponente');
  weg();
});

test('Warnleisten: „Mit leerer Liste neu beginnen“ fragt nach und ruft liste/neu_ausrollen mit bestaetigt', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.backend.konfig = { revision: null, liste_id: null, zustand: 'leer_neu', export_ok: true, export_geschrieben_am: null };
  await geheZu(s, '#technik-liste');
  knopf(s, 'neu_ausrollen').click();
  await s.flush();
  assert.match(s.q('dialog[open]').textContent, /Alle Tobies verlieren ihre Zuordnung/);
  assert.equal(s.m.aufrufe('tobibox/liste/neu_ausrollen').length, 0, 'noch nichts gesendet');
  blattKnopf(s, TECHNIK.abbrechen).click();
  await s.flush();
  assert.equal(s.m.aufrufe('tobibox/liste/neu_ausrollen').length, 0, 'Abbrechen sendet nichts');
  knopf(s, 'neu_ausrollen').click();
  await s.flush();
  blattKnopf(s, TECHNIK.liste.neu_ja).click();
  await warte(20); await s.flush(8);
  const aufrufe = s.m.aufrufe('tobibox/liste/neu_ausrollen');
  assert.equal(aufrufe.length, 1);
  assert.equal(aufrufe[0].bestaetigt, true);
  assert.match(aufrufe[0].anfrage_id, /^[0-9A-Za-z-]{8,64}$/);
  assert.equal(s.q('[data-warnleiste]'), null, 'Zustand ok: die Leiste ist weg');
  assert.ok(toasts(s).includes(TECHNIK.liste.erledigt));
  weg();
});

test('Warnleisten: export_neuer – „Aus dem Export holen“ zeigt zuerst Stand, Zeit und Zuordnungen (export_lesen), dann konfig/aus_export', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.backend.konfig = { revision: 7, liste_id: 'liste-aaaa', zustand: 'export_neuer', export_ok: true, export_geschrieben_am: null };
  await geheZu(s, '#technik-liste');
  assert.ok(s.q('[data-warnleiste="export_neuer"]'));
  knopf(s, 'aus_export').click();
  await warte(10); await s.flush();
  assert.match(s.q('dialog[open]').textContent, /Stand 9, gesichert am \d\d\.\d\d\., \d\d:\d\d, 4 Zuordnungen/);
  assert.equal(s.m.aufrufe('tobibox/konfig/aus_export').length, 0);
  blattKnopf(s, TECHNIK.liste.export_ja).click();
  await warte(20); await s.flush(8);
  const a = s.m.letzter('tobibox/konfig/aus_export');
  assert.equal(a.bestaetigt, true);
  assert.equal('stand' in a, false, 'der neueste Export: kein stand');
  weg();
});

test('Warnleisten: Box mit neuerem Stand (voraus) und fehlende Sicherung; auf anderen Seiten ein Hinweis mit Weg zur Liste', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik-liste', faehigkeiten: ALLE });
  s.m.backend.boxen[1].konfig_stand = 'voraus';
  s.m.backend.konfig = { ...s.m.backend.konfig, export_ok: false };
  await geheZu(s, '#technik-meldungen');
  assert.match(s.q('[data-warnleiste="box_voraus"]').textContent, /Die Box Kinderzimmer hat einen neueren Stand als HA/);
  assert.match(s.q('[data-warnleiste="export_fehlt"]').textContent, /Die Sicherung auf dem NAS fehlt/);
  await geheZu(s, '#geraete');
  assert.equal(s.q('[data-warnleiste]'), null);
  weg();
  // Hinweis oben auf allen anderen Seiten (Gerüst), nur wenn hello eine Entscheidung verlangt
  const t = await seite({ hash: '#start', faehigkeiten: ALLE });
  assert.equal(t.q('[data-band="liste"]'), null, 'alles in Ordnung: keine Leiste');
  weg();
  const u = await seite({ hash: '#start', faehigkeiten: ALLE, darf: true, ...{} });
  u.m.emit('konfig', 'geaendert', { konfig: { revision: 7, liste_id: 'x', zustand: 'export_neuer', export_ok: true, export_geschrieben_am: null } });
  await u.flush();
  const band = u.q('[data-band="liste"]');
  assert.ok(band);
  assert.equal(band.querySelector('a').getAttribute('href'), '#technik-liste');
  await geheZu(u, '#technik-liste');
  assert.equal(u.q('[data-band="liste"]'), null, 'in Technik zeigt die Seite die Leiste selbst');
  weg();
});

test('Warnleisten: Nicht-Administratoren sehen nur „Änderungen sind gerade gesperrt“, nie die Leisten mit Knöpfen', MIT_DOM, async () => {
  const s = await seite({ hash: '#start', darf: false, faehigkeiten: ALLE });
  s.m.emit('konfig', 'geaendert', { konfig: { revision: 7, liste_id: 'x', zustand: 'leer_neu', export_ok: true, export_geschrieben_am: null } });
  await s.flush();
  assert.equal(s.q('[data-band="liste"]'), null);
  assert.match(s.q('[data-band="gesperrt"]').textContent, /Änderungen sind gerade gesperrt/);
  weg();
});

/* ------------------------------------------------------------------ Liste und Sicherung */

test('Frühere Stände: die Liste kommt aus konfig/export_lesen (staende), ein Stand wird mit stand=<n> gelesen', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  mitStaenden(s.m);
  await geheZu(s, '#technik-liste');
  assert.equal(s.q('[data-karte="staende"] h3').textContent, TECHNIK.liste.staende.titel);
  const zeilen = s.qa('[data-liste="staende"] button');
  assert.equal(zeilen.length, 2);
  assert.match(zeilen[0].textContent, /Stand 1 · \d\d\.\d\d\., \d\d:\d\d · 4 Zuordnungen/);
  assert.match(zeilen[1].textContent, /Stand 2 · .* · 3 Zuordnungen/);
  assert.ok(s.m.aufrufe('tobibox/konfig/export_lesen').some((m) => !('stand' in m)), 'zuerst ohne stand');
  zeilen[1].click();
  await warte(10); await s.flush();
  assert.equal(s.m.letzter('tobibox/konfig/export_lesen').stand, 2);
  assert.match(s.q('dialog[open]').textContent, /Stand 7, gesichert am .*, 3 Zuordnungen/);
  assert.match(s.q('dialog[open] h2').textContent, /Stand 2 zurückspielen\?/);
  blattKnopf(s, TECHNIK.abbrechen).click();
  await s.flush();
  assert.equal(s.m.aufrufe('tobibox/konfig/aus_export').length, 0, 'ansehen ändert nichts');
  weg();
});

test('Frühere Stände: „Diesen Stand zurückspielen“ sendet konfig/aus_export mit stand und bestaetigt', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  mitStaenden(s.m);
  await geheZu(s, '#technik-liste');
  s.q('[data-stand="1"]').click();
  await warte(10); await s.flush();
  blattKnopf(s, TECHNIK.liste.staende.zurueck).click();
  await warte(20); await s.flush(8);
  const a = s.m.letzter('tobibox/konfig/aus_export');
  assert.equal(a.stand, 1);
  assert.equal(a.bestaetigt, true);
  assert.match(a.anfrage_id, /^[0-9A-Za-z-]{8,64}$/);
  assert.ok(toasts(s).includes(fuellen(TECHNIK.liste.staende.gemacht, { nr: 1 })));
  weg();
});

test('Frühere Stände: ohne Fähigkeit konfig_staende gibt es die Karte nicht und kein stand wird gesendet', MIT_DOM, async () => {
  const s = await technik('#technik-liste', { faehigkeiten: OHNE('konfig_staende') });
  assert.equal(s.q('[data-karte="staende"]'), null);
  assert.equal(s.m.aufrufe('tobibox/konfig/export_lesen').length, 0);
  weg();
});

test('Frühere Stände: leer und Fehler in Worten', MIT_DOM, async () => {
  const leer = await seite({ hash: '#technik', faehigkeiten: ALLE });
  mitStaenden(leer.m, []);
  await geheZu(leer, '#technik-liste');
  assert.equal(leer.q('[data-karte="staende"] .muted:last-of-type').textContent, TECHNIK.liste.staende.leer);
  weg();
  const kaputt = await seite({ hash: '#technik', faehigkeiten: ALLE });
  kaputt.m.failNext('tobibox/konfig/export_lesen', 'medien_nicht_erreichbar');
  await geheZu(kaputt, '#technik-liste');
  assert.ok(kaputt.q('[data-karte="staende"] [data-zustand="fehler"]'));
  weg();
});

/* ------------------------------------------------------------------ Speicher und Netz */

test('Bibliothek aufräumen: Medien neu einlesen (medien/pruefen) und „Cover neu suchen“ (cover/neu_suchen, mit Rückfrage)', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  assert.equal(s.q('[data-karte="aufraeumen"] h3').textContent, TECHNIK.aufraeumen.titel);
  const vorher = s.m.aufrufe('tobibox/medien/pruefen').length; // die alte Komponente stößt beim Öffnen selbst eine Prüfung an
  knopf(s, 'einlesen').click();
  await warte(10); await s.flush();
  assert.equal(s.m.aufrufe('tobibox/medien/pruefen').length, vorher + 1);
  assert.ok(toasts(s).includes(TECHNIK.aufraeumen.einlesen_gemacht));

  knopf(s, 'cover').click();
  await s.flush();
  assert.equal(s.m.aufrufe('tobibox/cover/neu_suchen').length, 0, 'erst die Rückfrage');
  assert.match(s.q('dialog[open] h2').textContent, /Cover neu suchen\?/);
  blattKnopf(s, TECHNIK.abbrechen).click();
  await s.flush();
  assert.equal(s.m.aufrufe('tobibox/cover/neu_suchen').length, 0);
  knopf(s, 'cover').click();
  await s.flush();
  blattKnopf(s, TECHNIK.aufraeumen.cover_ja).click();
  await warte(20); await s.flush(8);
  const c = s.m.aufrufe('tobibox/cover/neu_suchen');
  assert.equal(c.length, 1);
  assert.equal('serie_id' in c[0], false, 'alle Einträge');
  assert.ok(toasts(s).includes(TECHNIK.aufraeumen.cover_gemacht));
  weg();
});

test('Bibliothek aufräumen: „Cover neu suchen“ und „Hörkopien neu erzeugen“ nur mit den Fähigkeiten cover und hoerkopie', MIT_DOM, async () => {
  const ohne = await technik('#technik-speicher', { faehigkeiten: OHNE('cover', 'hoerkopie') });
  assert.ok(knopf(ohne, 'einlesen'));
  assert.equal(knopf(ohne, 'cover'), null);
  assert.equal(knopf(ohne, 'hoerkopien'), null);
  weg();
  const mit = await technik('#technik-speicher');
  knopf(mit, 'hoerkopien').click();
  await warte(10); await mit.flush();
  assert.equal(mit.m.aufrufe('tobibox/hoerkopie/neu_erzeugen').length, 1);
  assert.ok(toasts(mit).includes('2 Folgen warten auf eine neue Hörkopie.'));
  weg();
});

test('Bibliothek aufräumen: ein Fehler des Backends steht in Worten und bleibt bis „OK“', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  s.m.failNext('tobibox/cover/neu_suchen', 'medien_nicht_erreichbar');
  knopf(s, 'cover').click(); await s.flush();
  blattKnopf(s, TECHNIK.aufraeumen.cover_ja).click();
  await warte(20); await s.flush(8);
  assert.ok(s.q('.toast.err'));
  assert.match(s.q('.toast.err').textContent, /Das NAS antwortet gerade nicht/);
  weg();
});

const korbEintrag = (id, extra = {}) => ({ id, typ: 'folge', serie_id: 's1', serie_name: 'Die drei ???', folge: `${id}.mp3`, anzeige: `Folge ${id}`, art: 'datei', tracks: 1, groesse_bytes: 4000000,
  grund: 'manuell', geloescht_am: '2026-11-08T10:00:00Z', geloescht_von: null, ...extra });

test('Papierkorb: jede Zeile ganz antippbar, mit „gelöscht von“ (nur wenn bekannt), Name „… wiederherstellen“, Satz zum Hinweis (AC3)', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.backend.papierkorb = [
    korbEintrag('aaaa', { geloescht_von: { id: 'u1', name: 'Person B' } }),
    korbEintrag('bbbb', { typ: 'serie', serie_id: null, serie_name: null, anzeige: 'Alte Serie', tracks: 12 }),
  ];
  await geheZu(s, '#technik-speicher');
  const z = s.qa('[data-liste="papierkorb"] button.tzeile');
  assert.equal(z.length, 2);
  assert.match(z[0].textContent, /Folge aaaa/);
  assert.match(z[0].textContent, /gelöscht am \d\d\.\d\d\., \d\d:\d\d von Person B/);
  assert.match(z[0].textContent, /Tippen zum Wiederherstellen/);
  assert.equal(z[0].getAttribute('aria-label'), 'Folge aaaa wiederherstellen');
  assert.ok(z[0].querySelector('svg'), 'Pfeil');
  assert.doesNotMatch(z[1].textContent, / von /, 'ohne geloescht_von kein „von“');
  assert.match(z[1].textContent, /12 Dateien/);
  assert.match(s.q('[data-karte="papierkorb"]').textContent, /sehen Administratoren einen Punkt am Technik-Symbol und oben auf „Speicher“ einen Hinweis/);
  assert.match(s.q('[data-korb-summe]').textContent, /2 Einträge/);
  weg();
});

test('Papierkorb: Tippen auf die Zeile stellt wieder her (papierkorb/restore) und lädt neu', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.backend.papierkorb = [korbEintrag('aaaa'), korbEintrag('bbbb')];
  await geheZu(s, '#technik-speicher');
  s.q('[data-korb="aaaa"]').click();
  await warte(20); await s.flush(8);
  assert.deepEqual(s.m.letzter('tobibox/papierkorb/restore').eintrag_id, 'aaaa');
  assert.equal(s.qa('[data-liste="papierkorb"] button').length, 1);
  assert.ok(toasts(s).includes('„Folge aaaa“ ist wieder da.'));
  weg();
});

test('Papierkorb: ist die Serie weg, wählt der Administrator ein anderes Hörspiel, dann geht serie_id mit', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.backend.papierkorb = [korbEintrag('aaaa', { serie_id: 'weg' })];
  await geheZu(s, '#technik-speicher');
  s.q('[data-korb="aaaa"]').click();
  await warte(30); await s.flush(8);
  assert.equal(s.qa('.toast.err').length, 0, 'kein Fehler vorab, nur die Auswahl');
  assert.match(s.q('dialog[open] h2').textContent, /In welches Hörspiel/);
  assert.ok(!s.q('dialog[open]').textContent.includes('Überraschung'), 'die Überraschungs-Serie ist kein Ziel');
  s.q('dialog[open] [data-serie="s1"]').click();
  await warte(30); await s.flush(8);
  assert.equal(s.m.letzter('tobibox/papierkorb/restore').serie_id, 's1');
  assert.equal(s.m.backend.papierkorb.length, 0);
  weg();
});

test('Papierkorb: „Letzte Stunde zurückholen“ fragt nach, sendet papierkorb/restore_letzte_stunde mit bestaetigt und meldet die Zahl', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.backend.papierkorb = [korbEintrag('alt'), korbEintrag('neu1', { geloescht_am: '2026-11-13T11:30:00Z' }), korbEintrag('neu2', { geloescht_am: '2026-11-13T11:45:00Z' })];
  await geheZu(s, '#technik-speicher');
  knopf(s, 'letzte_stunde').click();
  await s.flush();
  assert.equal(s.m.aufrufe('tobibox/papierkorb/restore_letzte_stunde').length, 0);
  assert.match(s.q('dialog[open]').textContent, /Alles, was in der letzten Stunde in den Papierkorb kam/);
  blattKnopf(s, TECHNIK.korb.letzte_stunde_ja).click();
  await warte(20); await s.flush(8);
  assert.deepEqual(s.m.aufrufe('tobibox/papierkorb/restore_letzte_stunde').map((m) => m.bestaetigt), [true]);
  assert.ok(toasts(s).includes('2 Einträge zurückgeholt.'));
  assert.deepEqual(s.qa('[data-korb]').map((b) => b.getAttribute('data-korb')), ['alt']);
  weg();
});

test('Papierkorb: „Letzte Stunde zurückholen“ – was nicht ging, steht dabei; war nichts drin, sagt es das', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.backend.papierkorb = [korbEintrag('a1')];
  s.m.on('tobibox/papierkorb/restore_letzte_stunde', () => ({ wiederhergestellt: 1, uebersprungen: [{ eintrag_id: 'x', code: 'datei_existiert' }] }));
  await geheZu(s, '#technik-speicher');
  knopf(s, 'letzte_stunde').click(); await s.flush();
  blattKnopf(s, TECHNIK.korb.letzte_stunde_ja).click();
  await warte(20); await s.flush(8);
  assert.ok(toasts(s).includes('1 Eintrag zurückgeholt.'));
  assert.match(s.q('.toast.err').textContent, /1 Eintrag ging nicht/);
  s.m.on('tobibox/papierkorb/restore_letzte_stunde', () => ({ wiederhergestellt: 0, uebersprungen: [] }));
  knopf(s, 'letzte_stunde').click(); await s.flush();
  blattKnopf(s, TECHNIK.korb.letzte_stunde_ja).click();
  await warte(20); await s.flush(8);
  assert.ok(toasts(s).includes(TECHNIK.korb.letzte_stunde_nichts));
  weg();
});

test('Papierkorb: Leeren fragt nach (Menge und Größe), sendet papierkorb/empty mit bestaetigt; danach der leere Zustand', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.backend.papierkorb = [korbEintrag('a1'), korbEintrag('a2')];
  await geheZu(s, '#technik-speicher');
  knopf(s, 'leeren').click();
  await s.flush();
  assert.match(s.q('dialog[open]').textContent, /2 Einträge .*für immer/);
  assert.equal(s.m.aufrufe('tobibox/papierkorb/empty').length, 0);
  blattKnopf(s, TECHNIK.korb.leeren_ja).click();
  await warte(20); await s.flush(8);
  assert.deepEqual(s.m.aufrufe('tobibox/papierkorb/empty').map((m) => m.bestaetigt), [true]);
  assert.ok(toasts(s).includes(TECHNIK.korb.geleert));
  assert.ok(s.q('[data-karte="papierkorb"] [data-leer], [data-karte="papierkorb"] .leer'), 'leerer Zustand');
  assert.match(s.q('[data-karte="papierkorb"]').textContent, /Der Papierkorb ist leer/);
  assert.ok(knopf(s, 'leeren').disabled, 'nichts mehr zu leeren');
  weg();
});

test('Papierkorb: Fehler beim Laden – rote Karte mit „Noch einmal versuchen“', MIT_DOM, async () => {
  const s = await seite({ hash: '#technik', faehigkeiten: ALLE });
  s.m.failNext('tobibox/papierkorb/list', 'medien_nicht_erreichbar');
  await geheZu(s, '#technik-speicher');
  const karte = s.q('[data-karte="papierkorb"] [data-zustand="fehler"]');
  assert.ok(karte);
  karte.querySelector('button').click();
  await warte(20); await s.flush(8);
  assert.equal(s.q('[data-karte="papierkorb"] [data-zustand="fehler"]'), null);
  weg();
});

test('Speicher und Netz: der Eingang steht im Detail darunter (bereich eingang)', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  assert.equal(s.q('[data-karte="eingang"] h3').textContent, TECHNIK.eingang);
  assert.equal(s.q('[data-karte="eingang"] tobibox-panel').getAttribute('bereich'), 'eingang');
  assert.equal(s.q('[data-karte="aufraeumen"] tobibox-panel').getAttribute('bereich'), 'aufraeumen');
  weg();
});

/* ------------------------------------------------------------------ Meldungen, Gerüst */

test('Meldungen: die alte Komponente zeigt das Protokoll der Boxen mit Codes', MIT_DOM, async () => {
  const s = await technik('#technik-meldungen');
  await warte(30); await s.flush(6);
  const w = s.q('tobibox-panel').shadowRoot;
  assert.equal(w.querySelector('.app').getAttribute('data-bereich'), 'meldungen');
  assert.match(w.textContent, /Küche/);
  assert.match(w.textContent, /liste_abgelehnt/);
  assert.match(w.textContent, /Die Box Küche hat eine Liste abgelehnt/);
  assert.ok(!/Kinderzimmer/.test(w.textContent), 'nur Boxen mit Meldungen');
  weg();
});

test('Technik: mit „Zurück“ im Browser und Technik-Symbol bleibt der Reiter „Technik“ aktiv (kein Reiter markiert)', MIT_DOM, async () => {
  const s = await technik('#technik-speicher');
  assert.equal(s.qa('nav.tabs a[aria-current="page"]').length, 0);
  assert.equal(s.q('.rund.tech').getAttribute('aria-current'), 'page');
  weg();
});

test('Technik: Nachladen bei neuer Verbindung (neuLaden) holt Konfig und Boxen frisch', MIT_DOM, async () => {
  const s = await technik('#technik-boxen');
  const vorher = s.m.aufrufe('tobibox/boxen/list').length;
  s.el._seiteObj.neuLaden();
  await warte(20); await s.flush(6);
  assert.ok(s.m.aufrufe('tobibox/boxen/list').length > vorher);
  weg();
});

test('Technik: Texte nennen keine echten Namen und keine Netz-Adressen', () => {
  const alles = JSON.stringify(TECHNIK);
  assert.doesNotMatch(alles, /https?:\/\//);
  assert.ok(Object.keys(TECHNIK.zeilen).join() === UNTERSEITEN.join());
});

/* ---- AC3: Punkt am Technik-Symbol und Hinweis „Neu im Papierkorb“ (kein HA-Ereignis, keine HA-Mitteilung) */

const KORB_SCHLUESSEL = 'tobibox.korb_gesehen';
const punktKorb = (s) => s.q('[data-punkt="papierkorb"]');
const fremder = (id, extra = {}) => korbEintrag(id, { geloescht_am: '2026-11-09T10:00:00Z', geloescht_von: { id: 'u-b', name: 'Person B' }, ...extra });

async function korbSeite(opts = {}, hash = '#start') {
  window.localStorage.removeItem(KORB_SCHLUESSEL);
  return technik(hash, opts);
}
const neuesEreignis = async (s, eintraege) => {
  s.m.backend.papierkorb = [...eintraege, ...s.m.backend.papierkorb];
  s.m.emit('medien', 'papierkorb_geaendert', {});
  await s.flush(10);
};

test('Papierkorb-Punkt (AC3): Administrator, vorhandene Einträge sind nicht neu, ein neuer Eintrag einer anderen Person setzt den Punkt', MIT_DOM, async () => {
  const s = await korbSeite({}, '#start');
  s.m.backend.papierkorb = [];
  assert.equal(s.m.aufrufe('tobibox/papierkorb/list').length >= 1, true, 'die App fragt den Papierkorb ab');
  assert.ok(s.m.subs.at(-1).themen.includes('medien'), 'Thema `medien` im Abo');
  assert.equal(punktKorb(s), null, 'beim ersten Besuch auf diesem Gerät nichts Neues');
  await neuesEreignis(s, [fremder('aaaa')]);
  assert.ok(punktKorb(s), 'Punkt am Technik-Symbol im Kopf');
  assert.ok(punktKorb(s).closest('a.rund.tech'));
  assert.match(s.q('a.rund.tech').getAttribute('aria-label'), new RegExp(TECHNIK.korb.punkt));
  weg();
});

test('Papierkorb-Punkt (AC3): am Computer in der Seitenleiste', MIT_DOM, async () => {
  const s = await korbSeite({ breite: 1280 });
  await neuesEreignis(s, [fremder('aaaa')]);
  assert.ok(punktKorb(s).closest('a.srow.tech'), 'Punkt an der Zeile „Technik“ der Seitenleiste');
  assert.equal(s.q('a.rund.tech'), null);
  weg();
});

test('Papierkorb-Punkt (AC3): eigene Einträge und Einträge ohne Person zählen nicht', MIT_DOM, async () => {
  const s = await korbSeite({ userId: 'u-ich' });
  await neuesEreignis(s, [fremder('eigen', { geloescht_von: { id: 'u-ich', name: 'Ich' } }), fremder('ohne', { geloescht_von: null })]);
  assert.equal(punktKorb(s), null);
  weg();
});

test('Papierkorb-Punkt (AC3): Nicht-Administrator sieht keinen Punkt, fragt den Papierkorb nicht ab und abonniert `medien` nicht', MIT_DOM, async () => {
  const s = await korbSeite({ istAdmin: false, darf: true });
  assert.equal(s.m.aufrufe('tobibox/papierkorb/list').length, 0);
  assert.ok(!s.m.subs.at(-1).themen.includes('medien'));
  assert.equal(punktKorb(s), null);
  assert.equal(s.q('a.rund.tech'), null);
  weg();
});

test('Papierkorb-Hinweis (AC3): „Neu im Papierkorb“ mit Person, Eintrag und Zeit; der Punkt geht, nach dem nächsten Besuch ist auch der Hinweis weg', MIT_DOM, async () => {
  const s = await korbSeite({}, '#start');
  await neuesEreignis(s, [fremder('aaaa'), fremder('bbbb', { anzeige: 'Zweite Folge' })]);
  assert.ok(punktKorb(s));
  await geheZu(s, '#technik-speicher');
  await s.flush(10);
  const h = s.q('[data-korb-neu]');
  assert.ok(h, 'Hinweis oben');
  assert.match(h.textContent, /Neu im Papierkorb:/);
  assert.match(h.textContent, /Person B hat „Folge aaaa“ am \d\d\.\d\d\., \d\d:\d\d hineingelegt\./);
  assert.match(h.textContent, /Person B hat „Zweite Folge“/);
  assert.ok(h.compareDocumentPosition(s.q('[data-karte="aufraeumen"]')) & 4, 'der Hinweis steht über den Karten');
  assert.equal(punktKorb(s), null, 'der Punkt verschwindet beim Besuch');
  assert.equal(s.m.aufrufe('tobibox/papierkorb/restore').length, 0);
  assert.ok(window.localStorage.getItem(KORB_SCHLUESSEL), 'der Stand „gesehen“ steht im Speicher dieses Geräts');
  // weg und wieder hin: nichts Neues
  await geheZu(s, '#technik');
  await geheZu(s, '#technik-speicher');
  await s.flush(10);
  assert.equal(s.q('[data-korb-neu]'), null);
  assert.equal(punktKorb(s), null);
  weg();
});

test('Papierkorb-Hinweis (AC3): mehr als drei Einträge, der Rest als „Dazu n weitere“; Nicht-Administrator sieht keinen Hinweis', MIT_DOM, async () => {
  const s = await korbSeite({}, '#start');
  await neuesEreignis(s, ['a1', 'a2', 'a3', 'a4', 'a5'].map((id) => fremder(id)));
  await geheZu(s, '#technik-speicher');
  await s.flush(10);
  assert.equal(s.qa('[data-korb-neu] li').length, 3);
  assert.match(s.q('[data-korb-neu]').textContent, /Dazu 2 weitere Einträge\./);
  weg();
  window.localStorage.removeItem(KORB_SCHLUESSEL);
  const n = await technik('#technik-speicher', { istAdmin: false, darf: true });
  assert.equal(n.q('[data-korb-neu]'), null);
  weg();
});

test('Papierkorb-Punkt (AC3): der Stand „gesehen“ bleibt im Speicher des Geräts, ein späterer Eintrag setzt den Punkt nach dem Neuladen', MIT_DOM, async () => {
  window.localStorage.setItem(KORB_SCHLUESSEL, String(Date.parse('2026-11-09T09:00:00Z')));
  const s = await technik('#start', { userId: 'u-ich' });
  s.m.backend.papierkorb = [fremder('neu1')];
  s.m.emit('medien', 'papierkorb_geaendert', {});
  await s.flush(10);
  assert.ok(punktKorb(s));
  weg();
  const t = await technik('#start', { userId: 'u-ich', papierkorb: [fremder('neu1')] });
  t.m.backend.papierkorb = [fremder('neu1')];
  t.m.emit('medien', 'papierkorb_geaendert', {});
  await t.flush(10);
  assert.ok(punktKorb(t), 'noch nicht besucht: der Punkt ist nach dem Neuladen wieder da');
  weg();
});

test('Papierkorb-Punkt (AC3): ohne localStorage (wirft) kein Fehler, es gilt der Stand seit dem Start der Seite', MIT_DOM, async () => {
  const echt = window.Storage.prototype;
  const { getItem, setItem } = echt;
  echt.getItem = () => { throw new Error('gesperrt'); };
  echt.setItem = () => { throw new Error('gesperrt'); };
  try {
    const s = await technik('#start', {});
    s.m.backend.papierkorb = [fremder('aaaa')];
    s.m.emit('medien', 'papierkorb_geaendert', {});
    await s.flush(10);
    assert.ok(punktKorb(s));
    await geheZu(s, '#technik-speicher');
    await s.flush(10);
    assert.ok(s.q('[data-korb-neu]'));
    assert.equal(punktKorb(s), null);
    weg();
  } finally { echt.getItem = getItem; echt.setItem = setItem; }
});

test('Papierkorb-Hinweis (AC3): kommt auf „Speicher“ etwas dazu, wird die Liste neu geholt (Thema `medien`)', MIT_DOM, async () => {
  const s = await korbSeite({}, '#technik-speicher');
  s.m.reset();
  s.m.backend.papierkorb = [fremder('spaet'), ...s.m.backend.papierkorb];
  s.m.emit('medien', 'papierkorb_geaendert', {});
  await s.flush(10);
  assert.ok(s.m.aufrufe('tobibox/papierkorb/list').length >= 1);
  assert.ok(s.qa('[data-liste="papierkorb"] button.tzeile').some((b) => /Folge spaet/.test(b.textContent)));
  assert.equal(punktKorb(s), null, 'wer die Liste ansieht, braucht keinen Punkt');
  weg();
});

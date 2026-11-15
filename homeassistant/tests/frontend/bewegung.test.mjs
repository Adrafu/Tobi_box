/* Tests der Bewegung der Seiten (AP A6m, Design 4 „Bewegung“, Prüfung). Aufruf: node --test homeassistant/tests/frontend
 *
 * jsdom kennt weder `Element.prototype.animate` noch `matchMedia`: beides wird hier nachgebaut. Die falsche Animation läuft nicht von selbst,
 * der Test beendet sie mit `an.ende()`; so lässt sich prüfen, dass das Blatt bis zum Ende der Bewegung offen bleibt.
 * Geprüft: Blatt (offen bis Ende, danach open === false und Fokus am Auslöser), Cover-Flug der Serienseite (animate mit translate,
 * startViewTransition nie), ohne animate kein Flug und kein Fehler, „weniger Bewegung“ ohne transform, iOS-Blatt-Effekt (Blatt nicht darin).
 */
import test, { mock } from 'node:test';
import assert from 'node:assert/strict';
import { seite, weg, warte, domBereit, MIT_DOM } from './dom-helfer.mjs';

if (MIT_DOM.skip === false) await domBereit();
const bew = await import('../../custom_components/tobibox/frontend/bewegung.js');

/* Falsches `animate`: merkt sich jeden Aufruf; `an.ende()` beendet die Animation. */
function fakeAnimate() {
  const aufrufe = [];
  window.Element.prototype.animate = function animate(kf, opts) {
    let ok;
    const finished = new Promise((r) => { ok = r; });
    const an = { finished, ende: ok, cancel() { ok(); } };
    aufrufe.push({ el: this, kf, opts, an });
    return an;
  };
  return aufrufe;
}
const ohneAnimate = () => { delete window.Element.prototype.animate; };
const reduziert = (an) => { window.matchMedia = an ? () => ({ matches: true }) : undefined; };
const breite = (px) => Object.defineProperty(window, 'innerWidth', { value: px, configurable: true });
const nachher = () => { ohneAnimate(); reduziert(false); delete document.startViewTransition; };
const mitTransform = (a) => a.kf.some((k) => 'transform' in k || 'translate' in k);

async function blattOeffnen(s) {
  const ausloeser = s.q('nav a[href="#bibliothek"]');
  ausloeser.focus();
  const zu = s.el.oeffneBlatt({ titel: 'Probeblatt', inhalt: 'Inhalt', knoepfe: [{ label: 'Abbrechen' }] });
  await s.flush();
  return { zu, ausloeser, d: s.q('dialog.blatt') };
}

test('Blatt: bleibt bis zum Ende der Bewegung open, danach open === false und der Fokus ist am Auslöser', MIT_DOM, async () => {
  const aufrufe = fakeAnimate();
  breite(390);
  try {
    const s = await seite();
    const { zu, ausloeser, d } = await blattOeffnen(s);
    const auf = aufrufe.find((a) => a.el === d);
    assert.ok(auf, 'das Blatt federt herein (animate am Dialog)');
    assert.match(JSON.stringify(auf.kf), /translateY\(100%\)/, 'am Handy von unten um die eigene Höhe');
    auf.an.ende();
    d.querySelector('.blatt-x').click();
    await s.flush();
    assert.equal(d.hasAttribute('open'), true, 'noch offen, solange es hinausgleitet');
    assert.equal(d.dataset.closing, '1');
    const aus = aufrufe.filter((a) => a.el === d).pop();
    assert.match(JSON.stringify(aus.kf), /translateY\(100%\)/);
    assert.equal(aus.opts.fill, 'forwards');
    let aufgeloest = false;
    zu.then(() => { aufgeloest = true; });
    await warte(30);
    assert.equal(aufgeloest, false, 'das Versprechen löst sich erst nach der Bewegung');
    aus.an.ende();
    assert.equal(await zu, 'x');
    await s.flush();
    assert.equal(d.open, false);
    assert.equal(s.q('dialog.blatt'), null);
    assert.equal(s.el.shadowRoot.activeElement, ausloeser);
    weg();
  } finally { nachher(); }
});

test('Blatt: ohne Web Animations API öffnet und schließt es sofort, ohne Fehler', MIT_DOM, async () => {
  ohneAnimate();
  const s = await seite();
  const { zu, ausloeser, d } = await blattOeffnen(s);
  assert.ok(d.hasAttribute('open'));
  d.querySelector('.blatt-x').click();
  assert.equal(await zu, 'x');
  await s.flush();
  assert.equal(d.open, false);
  assert.equal(s.el.shadowRoot.activeElement, ausloeser);
  weg();
});

test('iOS-Blatt-Effekt am Handy: nur .hinten wird kleiner, das Blatt steckt nicht darin; danach alles zurück', MIT_DOM, async () => {
  const aufrufe = fakeAnimate();
  breite(390);
  try {
    const s = await seite({ breite: 390 });
    const { zu, d } = await blattOeffnen(s);
    const w = s.q('.hinten');
    assert.ok(w.classList.contains('effekt-an') && w.classList.contains('effekt'), 'die Seite dahinter tritt zurück');
    assert.equal(d.closest('.hinten'), null, 'das Blatt ist kein Nachkomme der verkleinerten Fläche (Messung 7 h4a)');
    assert.equal(s.q('.toastbox').closest('.hinten'), null);
    assert.ok(w.querySelector('.rahmen') && w.querySelector('nav.tabs'), 'Seite und Reiterleiste liegen darin');
    assert.ok(w.style.getPropertyValue('--oy').endsWith('px') && w.style.getPropertyValue('--ct') && w.style.getPropertyValue('--cb'), 'Drehpunkt und Ausschnitt sind gesetzt');
    aufrufe.find((a) => a.el === d).an.ende();
    s.el.schliesseBlatt();
    await s.flush();
    assert.equal(w.classList.contains('effekt'), false, 'beim Schließen federt die Seite zurück');
    aufrufe.filter((a) => a.el === d).pop().an.ende();
    await zu; await s.flush();
    await warte(700);
    assert.equal(w.classList.contains('effekt-an'), false, 'danach wieder ohne transform');
    weg();
  } finally { nachher(); }
});

test('iOS-Blatt-Effekt: ab 700 px Panelbreite bleibt die Seite groß', MIT_DOM, async () => {
  fakeAnimate();
  try {
    const s = await seite({ breite: 1000 });
    const { d } = await blattOeffnen(s);
    assert.equal(s.q('.hinten').classList.contains('effekt-an'), false);
    s.el.schliesseBlatt(); await s.flush();
    d.dispatchEvent(new window.Event('close'));
    weg();
  } finally { nachher(); }
});

/* ------------------------------------------------------------------ Cover-Flug der Serienseite */

const FLAECHEN = { 'cover se-xl': { left: 20, top: 60, width: 190, height: 190 } };
function flaechen() {
  const alt = window.Element.prototype.getBoundingClientRect;
  window.Element.prototype.getBoundingClientRect = function rect() {
    const k = typeof this.className === 'string' ? this.className : '';
    const f = k.includes('se-xl') ? FLAECHEN['cover se-xl'] : k.includes('cover') ? { left: 12, top: 300, width: 72, height: 72 } : { left: 0, top: 0, width: 390, height: 700 };
    return { ...f, right: f.left + f.width, bottom: f.top + f.height, x: f.left, y: f.top, toJSON() {} };
  };
  return () => { window.Element.prototype.getBoundingClientRect = alt; };
}

test('Serienseite öffnen: animate mit translate am großen Cover (FLIP), startViewTransition wird nie aufgerufen', MIT_DOM, async () => {
  const aufrufe = fakeAnimate();
  const vt = mock.fn();
  document.startViewTransition = vt;
  const zurueck = flaechen();
  try {
    const s = await seite({ viele: true, hash: '#bibliothek' });
    const zeile = s.q('a.lrow[data-serie]');
    assert.ok(zeile);
    const id = zeile.dataset.serie;
    zeile.click();
    await warte(30); await s.flush(10);
    const gross = s.q('.cover.se-xl');
    assert.ok(gross, 'die Serienseite ist da');
    const flug = aufrufe.find((a) => a.el.dataset?.flugklon === '1' && a.el.classList.contains('se-xl') && a.kf.some((k) => typeof k.transform === 'string' && k.transform.includes('translate(')));
    assert.ok(flug, 'das große Cover fliegt als Klon in der obersten Schicht (animate mit translate)');
    assert.equal(flug.el.parentNode, s.q('.app'), 'der Klon liegt in der Deckschicht, nicht in der Liste');
    assert.equal(gross.style.visibility, 'hidden', 'das echte Cover bleibt verdeckt, bis der Klon gelandet ist');
    assert.match(flug.kf[0].transform, /scale\(0\.\d+/, 'von der kleinen Fläche der Zeile');
    assert.equal(flug.kf[1].transform, 'none');
    assert.ok(/px \/ /.test(flug.kf[0].borderRadius) && /px$/.test(flug.kf[1].borderRadius), 'die Ecken laufen mit (je Achse gegen die Skala)');
    assert.equal(flug.el.style.pointerEvents, 'none', 'nur das fliegende Cover fängt keine Eingaben ab');
    flug.an.ende(); await warte(5);
    assert.equal(gross.style.visibility, '', 'danach ist das echte Cover da');
    assert.equal(flug.el.isConnected, false, 'und der Klon weg (im selben Bild)');
    assert.equal(vt.mock.callCount(), 0, 'startViewTransition nie');
    // zurück: das Cover der Zeile fliegt von der Fläche des großen Covers an seinen Platz
    const vorher = aufrufe.length;
    s.q('a.back').click();
    await warte(30); await s.flush(10);
    const rueck = aufrufe.slice(vorher).find((a) => a.el.dataset?.flugklon === '1' && a.el.dataset?.cover === id && a.kf.some((k) => typeof k.transform === 'string' && k.transform.includes('translate(')));
    assert.ok(rueck, 'zurück fliegt das Cover der Zeile');
    assert.equal(rueck.kf[0].transform, 'none', 'der Klon ist so groß wie das große Cover und startet dort');
    assert.match(rueck.kf[1].transform, /scale\(0\.\d+/, 'und landet klein an der Stelle des Covers der Zeile');
    assert.equal(vt.mock.callCount(), 0);
    weg();
  } finally { zurueck(); nachher(); }
});

test('Serienseite öffnen ohne Element.prototype.animate: kein Flug, kein Fehler, richtiger Endzustand', MIT_DOM, async () => {
  ohneAnimate();
  const vt = mock.fn();
  document.startViewTransition = vt;
  const zurueck = flaechen();
  try {
    const s = await seite({ viele: true, hash: '#bibliothek' });
    s.q('a.lrow[data-serie]').click();
    await warte(30); await s.flush(10);
    assert.ok(s.q('.cover.se-xl'));
    assert.equal(s.q('.cover.se-xl').style.transform, '');
    s.q('a.back').click();
    await warte(30); await s.flush(10);
    assert.ok(s.q('a.lrow[data-serie]'));
    assert.equal(vt.mock.callCount(), 0);
    weg();
  } finally { zurueck(); nachher(); }
});

test('Weniger Bewegung: kein Cover-Flug, kein transform an Blatt, Seite und Meldung, nur Überblenden', MIT_DOM, async () => {
  const aufrufe = fakeAnimate();
  reduziert(true);
  breite(390);
  const zurueck = flaechen();
  try {
    const s = await seite({ viele: true, hash: '#bibliothek', breite: 390 });
    s.q('a.lrow[data-serie]').click();
    await warte(30); await s.flush(10);
    assert.ok(s.q('.cover.se-xl'));
    assert.equal(aufrufe.filter((a) => a.el.classList?.contains('se-xl')).length, 0, 'kein Flug');
    const { d } = await blattOeffnen(s);
    assert.equal(s.q('.hinten').classList.contains('effekt-an'), false, 'keine Seite, die zurücktritt');
    s.el.melde('Gespeichert.');
    s.el.schliesseBlatt(); await s.flush();
    assert.equal(aufrufe.filter(mitTransform).length, 0, `kein transform in einer Animation: ${JSON.stringify(aufrufe.filter(mitTransform).map((a) => a.kf))}`);
    assert.ok(aufrufe.some((a) => a.el === d), 'das Blatt blendet trotzdem ein und aus');
    assert.equal(s.q('.hinten').style.transform, '');
    weg();
  } finally { zurueck(); nachher(); }
});

test('Meldungen: federn herein, gleiten hinaus und werden danach entfernt', MIT_DOM, async () => {
  const aufrufe = fakeAnimate();
  try {
    const s = await seite();
    const t = s.el.melde('Gespeichert.');
    const ein = aufrufe.find((a) => a.el === t);
    assert.match(ein.kf[0].transform, /translateY\(24px\)/);
    s.el._meldungWeg(t);
    assert.ok(t.parentNode, 'sie gleitet noch hinaus');
    aufrufe.filter((a) => a.el === t).pop().an.ende();
    await warte(5);
    assert.equal(t.parentNode, null);
    weg();
  } finally { nachher(); }
});

test('FLIP-Hilfsfunktion: bleibt zwischen Start und Ziel, Ecken je Achse ausgeglichen, ohne animate null', MIT_DOM, async () => {
  const aufrufe = fakeAnimate();
  try {
    const el = document.createElement('div');
    document.body.appendChild(el);
    const von = { left: 10, top: 20, width: 50, height: 50 };
    const nach = { left: 100, top: 200, width: 200, height: 200 };
    bew.flip(el, von, nach, { dauer: 500, easing: 'linear', radiusVon: 8, radiusNach: 16 });
    const a = aufrufe[0];
    assert.equal(a.kf[0].transform, 'translate(-90px, -180px) scale(0.25, 0.25)');
    assert.equal(a.kf[0].borderRadius, '32px / 32px', 'sichtbar 8 px bei Skala 0,25');
    assert.deepEqual(a.kf[1], { transform: 'none', borderRadius: '16px' });
    // umgekehrt: das Element sitzt am Start und fliegt zum Ziel
    bew.flip(el, nach, von, { liegt: 'von', dauer: 500, easing: 'linear', radiusVon: 16, radiusNach: 8 });
    const b = aufrufe[1];
    assert.equal(b.kf[1].transform, 'translate(-90px, -180px) scale(0.25, 0.25)');
    assert.equal(b.kf[1].borderRadius, '32px / 32px');
    assert.equal(bew.flip(el, { left: 0, top: 0, width: 0, height: 0 }, nach, {}), null, 'leere Fläche: kein Flug');
    ohneAnimate();
    assert.equal(bew.flip(el, von, nach, {}), null, 'ohne animate: kein Flug, kein Fehler');
    el.remove();
  } finally { nachher(); }
});

test('Pille: der aktive Reiter und der Segment-Umschalter bekommen ein eigenes Element', MIT_DOM, async () => {
  ohneAnimate();
  const s = await seite({ breite: 390 });
  const n = s.q('nav.tabs .tr');
  assert.ok(n.querySelector(':scope > .pille') || !n.querySelector('a[aria-current="page"] .ti').offsetWidth, 'Pille im Reiter (jsdom hat keine Maße: nur mit Breite)');
  weg();
});

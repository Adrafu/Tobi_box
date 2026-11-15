/* Tests der Bewegung des Players (AP A8m, Design 4 „Bewegung“, Prüfung; Messung 7 vom 14.11.). Aufruf: node --test homeassistant/tests/frontend
 *
 * Wie bewegung.test.mjs: jsdom kennt weder `Element.prototype.animate` noch Flächen; beides wird nachgebaut. Geprüft: Cover-Flug Mini-Player ↔
 * Vollansicht nur per FLIP (`animate` mit `translate`, nie `startViewTransition`), Ecken laufen mit, Eingabesperre nur am fliegenden Cover, das
 * Mini-Cover ist während der Vollansicht verdeckt und danach wieder sichtbar, Mini-Player federt herein, Kreuzblende, „weniger Bewegung“ ohne Flug,
 * ohne `animate` ohne Fehler, Wischen folgt dem Finger und schließt von dort aus.
 */
import test, { mock } from 'node:test';
import assert from 'node:assert/strict';
import { weg, warte, MIT_DOM } from './dom-helfer.mjs';
import { mockAudio, spielSeite, starteSerie, lade, zeiger } from './player-helfer.mjs';

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

/* Flächen: das große Cover der Vollansicht (.pxl) 280 px, das Mini-Cover (.sm) 48 px unten links. */
function flaechen() {
  const alt = window.Element.prototype.getBoundingClientRect;
  window.Element.prototype.getBoundingClientRect = function rect() {
    const k = typeof this.className === 'string' ? this.className : '';
    const f = k.includes('pxl') ? { left: 55, top: 120, width: 280, height: 280 } : k.includes('sm') ? { left: 16, top: 640, width: 48, height: 48 } : { left: 0, top: 0, width: 390, height: 700 };
    return { ...f, right: f.left + f.width, bottom: f.top + f.height, x: f.left, y: f.top, toJSON() {} };
  };
  return () => { window.Element.prototype.getBoundingClientRect = alt; };
}

const mitTranslate = (a) => a.kf.some((k) => typeof k.transform === 'string' && k.transform.includes('translate('));
const klon = (a) => a.el.dataset?.flugklon === '1'; // der fliegende Klon in der obersten Schicht (Befund Tobias 14.11.)

function mit(name, fn, extra = {}) {
  test(name, MIT_DOM, async (t) => {
    const au = await mockAudio();
    const zurueck = flaechen();
    const vt = mock.fn();
    document.startViewTransition = vt;
    breite(extra.breite ?? 390);
    try { await fn(t, { vt }); } finally { weg(); au.zurueck(); zurueck(); ohneAnimate(); reduziert(false); delete document.startViewTransition; }
  });
}

async function spielend(opts = {}) {
  const s = await spielSeite({ hash: '#serie-s1', breite: 390, ...opts });
  const a = await starteSerie(s);
  return { s, a };
}
const oeffneVoll = async (s) => { s.q('.mini .mopen').click(); await s.flush(8); return s.q('dialog.player'); };
const kopf = (s) => s.el.shadowRoot;

mit('Öffnen: das große Cover fliegt per FLIP (animate mit translate und scale) vom Mini-Cover an seinen Platz; startViewTransition nie; Ecken laufen mit', async (t, { vt }) => {
  const aufrufe = fakeAnimate();
  const { s } = await spielend();
  const d = await oeffneVoll(s);
  const gross = d.querySelector('.pin > .cover');
  const flug = aufrufe.find((a) => klon(a) && mitTranslate(a));
  assert.ok(flug, 'animate am Klon des großen Covers mit translate');
  assert.equal(flug.el.parentNode, d, 'der Klon liegt in der Vollansicht (oberste Schicht), nicht zwischen Titel und Knöpfen');
  assert.equal(gross.style.visibility, 'hidden', 'das echte Cover bleibt bis zur Landung verdeckt');
  assert.match(flug.kf[0].transform, /translate\(-39px, 520px\) scale\(0\.171/, 'von der Fläche des Mini-Covers (48 px) nach oben links des großen');
  assert.equal(flug.kf[1].transform, 'none');
  assert.ok(/px \/ /.test(flug.kf[0].borderRadius) && /px$/.test(flug.kf[1].borderRadius), 'die Ecken laufen je Achse gegen die Skala mit (Messung 7)');
  assert.equal(flug.opts.fill, 'forwards', 'der Klon bleibt am Ziel, bis das echte Cover da ist');
  assert.equal(flug.el.style.pointerEvents, 'none', 'nur das fliegende Cover fängt keine Eingaben ab');
  assert.equal(d.style.pointerEvents, '', 'der Dialog bleibt bedienbar, nie global gesperrt');
  assert.ok(s.q('.mini').classList.contains('hebt'), 'das Mini-Cover ist während der Vollansicht verdeckt (visibility, nicht entfernt)');
  assert.ok(s.q('.mini .cover'), 'das Mini-Cover bleibt im DOM');
  // die Fläche der Vollansicht gleitet herauf, Titel und Steuerung blenden verzögert ein (140 ms, 14 px)
  assert.ok(aufrufe.some((a) => a.el === d.querySelector('.p-flaeche') && JSON.stringify(a.kf).includes('translateY(100%)')), 'die Fläche gleitet von unten herauf');
  const ein = aufrufe.find((a) => a.el === d.querySelector('.ptitle'));
  assert.equal(ein.opts.delay, 140);
  assert.match(JSON.stringify(ein.kf), /translateY\(14px\)/);
  assert.equal(aufrufe.filter((a) => a.el === d.querySelector('.grip')).length, 1);
  flug.an.ende(); await warte(5);
  assert.equal(gross.style.visibility, '', 'danach ist das echte Cover da');
  assert.equal(flug.el.isConnected, false, 'der Klon ist weg');
  assert.equal(gross.style.transform, '');
  assert.equal(vt.mock.callCount(), 0, 'startViewTransition wird nie aufgerufen');
});

mit('Schließen: das große Cover fliegt zur Fläche des Mini-Covers, die Vollansicht gleitet hinunter; danach ist das Mini-Cover wieder sichtbar und nichts bleibt verschoben', async (t, { vt }) => {
  const aufrufe = fakeAnimate();
  const { s } = await spielend();
  const d = await oeffneVoll(s);
  const gross = d.querySelector('.pin > .cover');
  aufrufe.forEach((a) => a.an.ende());
  await warte(10); // die Aufräumarbeit des Hinflugs ist durch, bevor es zurückgeht
  aufrufe.length = 0;
  d.querySelector('[data-p="close"]').click();
  await s.flush(6);
  assert.ok(d.hasAttribute('open') && d.dataset.closing === '1', 'noch offen, solange es hinunterfliegt');
  const flug = aufrufe.find((a) => klon(a) && mitTranslate(a));
  assert.ok(flug, 'animate beim Schließen');
  assert.equal(flug.kf[0].transform, 'none');
  assert.match(flug.kf[1].transform, /translate\(-39px, 520px\) scale\(0\.171/);
  assert.equal(flug.opts.fill, 'forwards', 'das große Cover bleibt am Ziel stehen, bis aufgeräumt wird');
  assert.equal(flug.el.style.pointerEvents, 'none');
  const flaeche = aufrufe.find((a) => a.el === d.querySelector('.p-flaeche'));
  assert.match(JSON.stringify(flaeche.kf), /translateY\(\d+px\)/, 'die Fläche gleitet hinunter');
  assert.ok(s.q('.mini').classList.contains('hebt'), 'das Mini-Cover bleibt verdeckt, bis das große gelandet ist');
  flug.an.ende();
  await s.flush(10);
  assert.equal(s.q('dialog.player'), null, 'danach ist die Vollansicht weg');
  assert.equal(d.open, false);
  assert.equal(s.q('.mini').classList.contains('hebt'), false, 'das Mini-Cover ist wieder sichtbar');
  assert.ok(s.q('.mini .cover'));
  assert.equal(s.el.hasAttribute('data-voll'), false);
  assert.equal(s.el.shadowRoot.activeElement, s.q('.mini .mopen'));
  assert.equal(vt.mock.callCount(), 0);
});

mit('Wischen nach unten: die Vollansicht folgt dem Finger, beim Loslassen setzt die Rückreise dort an (Cover mit `translate`), unter der Schwelle federt sie zurück', async () => {
  const aufrufe = fakeAnimate();
  const { s } = await spielend();
  const d = await oeffneVoll(s);
  aufrufe.forEach((a) => a.an.ende());
  Object.defineProperty(d, 'offsetHeight', { value: 800, configurable: true });
  const feld = d.querySelector('.ptitle');
  // unter der Schwelle: zurückfedern
  aufrufe.length = 0;
  zeiger(feld, 'pointerdown', { clientY: 300, timeStamp: 0 });
  zeiger(feld, 'pointermove', { clientY: 330, timeStamp: 10 });
  zeiger(feld, 'pointermove', { clientY: 350, timeStamp: 20 });
  assert.equal(d.style.getPropertyValue('--dy'), '50px', 'folgt dem Finger');
  assert.ok(d.classList.contains('zieht'));
  zeiger(feld, 'pointerup', { clientY: 350, timeStamp: 30 });
  assert.equal(d.style.getPropertyValue('--dy'), '');
  const zurueck = aufrufe.find((a) => a.el === d.querySelector('.pin > .cover') && a.kf.some((k) => 'translate' in k));
  assert.ok(zurueck, 'das Cover federt zurück');
  assert.equal(zurueck.kf[0].translate, '0 50px');
  assert.ok(d.hasAttribute('open'));
  // über der Schwelle: schließt von der Stelle des Fingers aus
  aufrufe.length = 0;
  zeiger(feld, 'pointerdown', { clientY: 300, timeStamp: 100 });
  zeiger(feld, 'pointermove', { clientY: 330, timeStamp: 110 });
  zeiger(feld, 'pointermove', { clientY: 450, timeStamp: 130 });
  zeiger(feld, 'pointerup', { clientY: 450, timeStamp: 140 });
  await s.flush(6);
  const gross = d.querySelector('.pin > .cover');
  assert.ok(aufrufe.some((a) => klon(a) && mitTranslate(a)), 'die Rückreise des Covers (Klon)');
  const fl = aufrufe.find((a) => a.el === d.querySelector('.p-flaeche'));
  assert.match(JSON.stringify(fl.kf[0]), /translateY\(150px\)/);
  aufrufe.filter((a) => a.opts.fill === 'forwards').forEach((a) => a.an.ende());
  await s.flush(10);
  assert.equal(s.q('dialog.player'), null);
});

mit('Ohne Element.prototype.animate: kein Flug, kein Fehler, richtiger Endzustand (Vollansicht auf und zu, Mini-Cover sichtbar)', async (t, { vt }) => {
  ohneAnimate();
  const { s } = await spielend();
  assert.equal(s.q('.mini').hidden, false, 'die Leiste erscheint auch ohne Feder');
  const d = await oeffneVoll(s);
  assert.ok(d.hasAttribute('open'));
  assert.equal(d.querySelector('.pin > .cover').style.transform, '');
  d.querySelector('[data-p="close"]').click();
  await s.flush(10);
  assert.equal(s.q('dialog.player'), null);
  assert.equal(s.q('.mini').classList.contains('hebt'), false);
  assert.equal(vt.mock.callCount(), 0);
});

mit('Weniger Bewegung: kein Cover-Flug, kein translate und scale, nur Überblenden; Mini-Cover danach sichtbar', async (t, { vt }) => {
  const aufrufe = fakeAnimate();
  reduziert(true);
  const { s } = await spielend();
  const d = await oeffneVoll(s);
  assert.equal(aufrufe.filter(mitTranslate).length, 0, 'nirgends translate');
  assert.equal(aufrufe.filter((a) => JSON.stringify(a.kf).includes('scale(')).length, 0);
  assert.equal(aufrufe.filter(klon).length, 0, 'das große Cover fliegt nicht');
  const ein = aufrufe.find((a) => a.el === d);
  assert.deepEqual(ein.kf, [{ opacity: 0 }, { opacity: 1 }], 'die Vollansicht blendet nur ein');
  aufrufe.forEach((a) => a.an.ende());
  aufrufe.length = 0;
  d.querySelector('[data-p="close"]').click();
  await s.flush(6);
  assert.equal(aufrufe.filter(mitTranslate).length, 0);
  assert.deepEqual(aufrufe.find((a) => a.el === d).kf, [{ opacity: 1 }, { opacity: 0 }]);
  aufrufe.forEach((a) => a.an.ende());
  await s.flush(10);
  assert.equal(s.q('dialog.player'), null);
  assert.equal(s.q('.mini').classList.contains('hebt'), false);
  assert.equal(vt.mock.callCount(), 0);
});

mit('Mini-Player federt herein, wenn zum ersten Mal etwas spielt; beim Wechsel der Folge blendet das Cover über (Kopie des alten Covers, neues federt von 0,9)', async () => {
  const aufrufe = fakeAnimate();
  const s = await spielSeite({ hash: '#serie-s1', breite: 390 });
  assert.equal(aufrufe.filter((a) => a.el.classList?.contains('mini')).length, 0, 'ohne Wiedergabe keine Leiste');
  await starteSerie(s);
  const herein = aufrufe.find((a) => a.el === s.q('.mini'));
  assert.ok(herein, 'die Leiste federt herein');
  assert.deepEqual(herein.kf, [{ transform: 'translateY(100%)', opacity: 0 }, { transform: 'none', opacity: 1 }]);
  aufrufe.forEach((a) => a.an.ende());
  aufrufe.length = 0;
  s.sp.naechste();
  await s.flush(12);
  lade(s.audio(), 130);
  await s.flush(8);
  assert.equal(aufrufe.filter((a) => a.el === s.q('.mini')).length, 0, 'nur beim ersten Mal');
  const klon = aufrufe.find((a) => a.kf.length === 2 && a.kf[0].opacity === 1 && a.kf[1].opacity === 0 && a.el !== s.q('.mini'));
  assert.ok(klon, 'eine Kopie des alten Covers blendet aus');
  assert.ok(klon.el.classList.contains('cover'));
  const neu = aufrufe.find((a) => a.el === s.q('.mini .mopen .cover') && a.kf[0].transform === 'scale(0.9)');
  assert.ok(neu, 'das neue Cover federt von 0,9 auf 1');
  const text = aufrufe.find((a) => a.el === s.q('.mini .mopen .grow'));
  assert.deepEqual(text.kf[0], { opacity: 0, transform: 'translateY(6px)' }, 'der Text blendet mit 6 px Weg ein');
  klon.an.ende(); await warte(5);
  assert.equal(s.qa('.mini .mopen .cover').length, 1, 'die Kopie ist wieder weg: nichts blinkt, nichts bleibt');
});

mit('Mini-Player mit weniger Bewegung: nur Einblenden', async () => {
  const aufrufe = fakeAnimate();
  reduziert(true);
  const s = await spielSeite({ hash: '#serie-s1', breite: 390 });
  await starteSerie(s);
  const herein = aufrufe.find((a) => a.el === s.q('.mini'));
  assert.deepEqual(herein.kf, [{ opacity: 0 }, { opacity: 1 }]);
  assert.equal(aufrufe.filter(mitTranslate).length, 0);
});

mit('Player offen: kein iOS-Blatt-Effekt für ein Blatt über dem Player (data-voll), ohne Player tritt die Seite zurück', async () => {
  fakeAnimate();
  const { s } = await spielend();
  s.el.oeffneBlatt({ titel: 'Probe', inhalt: 'x', knoepfe: [{ label: 'Zu' }] });
  await s.flush(6);
  assert.ok(s.q('.hinten').classList.contains('effekt-an'), 'ohne offenen Player: die Seite tritt zurück');
  s.el.schliesseBlatt();
  await s.flush(6);
  await warte(1300);
  const d = await oeffneVoll(s);
  assert.ok(d);
  assert.ok(s.el.hasAttribute('data-voll'));
  s.el.oeffneBlatt({ titel: 'Probe', inhalt: 'x', knoepfe: [{ label: 'Zu' }] });
  await s.flush(6);
  assert.equal(s.q('.hinten').classList.contains('effekt-an'), false, 'der Player deckt die Seite ganz: kein Effekt');
});

mit('Am Computer (ab 700 px): die Fläche gleitet 32 px und blendet ein, das Cover fliegt trotzdem', async () => {
  const aufrufe = fakeAnimate();
  const { s } = await spielend({ breite: 1000 });
  const d = await oeffneVoll(s);
  const fl = aufrufe.find((a) => a.el === d.querySelector('.p-flaeche'));
  assert.deepEqual(fl.kf, [{ transform: 'translateY(32px)', opacity: 0 }, { transform: 'none', opacity: 1 }]);
  assert.ok(aufrufe.some((a) => klon(a) && mitTranslate(a)));
}, { breite: 1000 });

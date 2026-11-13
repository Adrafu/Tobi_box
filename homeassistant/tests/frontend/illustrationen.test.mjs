/* Tests der Illustrationen der leeren Zustände (AP A6b, Design Abschnitt 6.2).
 * Aufruf: cd homeassistant/tests/frontend && TOBIBOX_JSDOM_DIR=<ordner mit jsdom> node --test
 *
 * Prüft illustrationen.js gegen die Tabelle in 6.2: jede Illustration existiert, jedes SVG ist wohlgeformt,
 * hat viewBox und aria-hidden, und Farben kommen nur aus CSS-Variablen (var(--…)).
 * Die Prüfung der Wohlgeformtheit braucht jsdom (sonst übersprungen, wie in den anderen Tests).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HIER = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(HIER, '../../..');
const QUELLE = join(ROOT, 'homeassistant/custom_components/tobibox/frontend/illustrationen.js');
const bilder = await import('../../custom_components/tobibox/frontend/illustrationen.js');
const { ILLUSTRATIONEN } = bilder;
const quelltext = readFileSync(QUELLE, 'utf8');
const design = readFileSync(join(ROOT, 'docs/designs/ha-oberflaeche.md'), 'utf8');

/* Die sieben Zeilen der Tabelle in 6.2: Satz-Name aus dem Design → Export. */
const ZUSTAENDE = [
  ['Bibliothek leer', 'bibliothekLeer'],
  ['Filter ohne Treffer (Bibliothek)', 'filterOhneTreffer'],
  ['Keine Tobies', 'keineTobies'],
  ['Keine Box eingerichtet (Geräte)', 'keineBox'],
  ['Suche ohne Treffer (Suchansicht, Tobies-Suche)', 'sucheOhneTreffer'],
  ['Papierkorb leer (Technik)', 'papierkorbLeer'],
  ['Gehört ohne Daten (Stufe B)', 'gehoertOhneDaten'],
];

/* Tabellenzeilen des Abschnitts 6.2 (ohne Kopf und Trennzeile). */
function tabelle62() {
  const i = design.indexOf('### 6.2 ');
  const j = design.indexOf('\n### ', i + 1);
  assert.ok(i >= 0, 'Abschnitt 6.2 nicht gefunden');
  // Die Trennzeile („|---|“) beginnt nicht mit „| “; nur der Kopf (erste Zeile) fällt weg.
  return design.slice(i, j).split('\n').filter((z) => z.startsWith('| ')).slice(1);
}

/* jsdom wie in den anderen Tests: Modul oder TOBIBOX_JSDOM_DIR. */
function ladeJsdom() {
  try { return createRequire(import.meta.url)('jsdom'); } catch { /* weiter */ }
  if (process.env.TOBIBOX_JSDOM_DIR) {
    try { return createRequire(join(process.env.TOBIBOX_JSDOM_DIR, 'x.js'))('jsdom'); } catch { /* weiter */ }
  }
  return null;
}
const jsdom = ladeJsdom();
const MIT_DOM = { skip: jsdom ? false : 'jsdom nicht verfügbar (TOBIBOX_JSDOM_DIR setzen oder npm i jsdom)' };

/* Alle Farbwerte eines SVG-Strings (Attribute und style); `none` ist erlaubt. */
function farbwerte(text) {
  const werte = [];
  for (const m of text.matchAll(/\b(fill|stroke|stop-color|color)\s*[:=]\s*"?([^;"]+)/g)) werte.push(m[2].trim());
  return werte;
}

/* Text ohne var(...)-Ausdrücke (auch mit verschachteltem Rückfall). */
function ohneVar(text) {
  return text.replace(/var\((?:[^()]|\([^()]*\))*\)/g, '');
}

const NAMEN = Object.keys(ILLUSTRATIONEN);

test('jede Illustration aus Abschnitt 6.2 existiert', () => {
  const zeilen = tabelle62();
  assert.equal(zeilen.length, ZUSTAENDE.length, 'Anzahl der Zeilen in 6.2 stimmt nicht mit der Prüfliste überein');
  for (const [satz, name] of ZUSTAENDE) {
    assert.ok(zeilen.some((z) => z.startsWith(`| ${satz} |`)), `Zeile fehlt im Design: ${satz}`);
    assert.equal(typeof ILLUSTRATIONEN[name], 'string', `Export fehlt: ${name}`);
    assert.ok(ILLUSTRATIONEN[name].length > 0, `Export leer: ${name}`);
  }
  assert.deepEqual([...NAMEN].sort(), ZUSTAENDE.map(([, n]) => n).sort(), 'ILLUSTRATIONEN enthält unerwartete Namen');
});

test('jedes SVG hat viewBox und aria-hidden', () => {
  for (const name of NAMEN) {
    const s = ILLUSTRATIONEN[name];
    assert.match(s, /^<svg\b[^>]*>/, `${name}: beginnt nicht mit <svg>`);
    assert.match(s, /\sviewBox="0 0 200 150"/, `${name}: viewBox fehlt`);
    assert.match(s, /\saria-hidden="true"/, `${name}: aria-hidden fehlt`);
    assert.doesNotMatch(s, /<script|<foreignObject|on[a-z]+="/i, `${name}: Skript oder Ereignis im SVG`);
  }
});

test('jedes SVG ist wohlgeformt', MIT_DOM, () => {
  const dom = new jsdom.JSDOM('<!doctype html><body></body>');
  const parser = new dom.window.DOMParser();
  for (const name of NAMEN) {
    const doc = parser.parseFromString(ILLUSTRATIONEN[name], 'image/svg+xml');
    assert.equal(doc.getElementsByTagName('parsererror').length, 0, `${name}: SVG ist nicht wohlgeformt`);
    const wurzel = doc.documentElement;
    assert.equal(wurzel.localName, 'svg', `${name}: Wurzel ist nicht svg`);
    assert.equal(wurzel.getAttribute('viewBox'), '0 0 200 150', `${name}: viewBox falsch`);
    assert.ok(wurzel.querySelectorAll('*').length > 3, `${name}: zu wenige Elemente`);
  }
});

test('Farben kommen nur aus CSS-Variablen (keine Hex-Farben, keine festen Farbnamen)', () => {
  for (const name of NAMEN) {
    const s = ILLUSTRATIONEN[name];
    for (const wert of farbwerte(s)) {
      assert.ok(wert === 'none' || /^var\(--[a-z0-9-]+\)$/.test(wert), `${name}: Farbe ohne var(): ${wert}`);
    }
    assert.doesNotMatch(ohneVar(s), /#[0-9a-fA-F]{3,8}\b/, `${name}: Hex-Farbe außerhalb von var()`);
    assert.doesNotMatch(ohneVar(s), /\b(rgba?|hsla?)\(/i, `${name}: rgb/hsl außerhalb von var()`);
  }
});

test('die Quelldatei enthält keine Hex-Farben außerhalb von var()', () => {
  assert.equal(ohneVar(quelltext).match(/#[0-9a-fA-F]{3,8}\b/g), null);
});

test('die Quelldatei hat keine Abhängigkeiten', () => {
  assert.doesNotMatch(quelltext, /^\s*import\s/m);
});

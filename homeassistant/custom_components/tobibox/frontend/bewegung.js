/* Bewegung der Seiten (Paket A6m, Design docs/designs/ha-oberflaeche.md, Abschnitt 4 „Bewegung“).
 *
 * Gemeinsame Hilfen für tobibox-app.js (Blätter, Meldungen, Seitenwechsel) und die Seiten (Cover-Flug). Dieses Modul lädt auch
 * ohne DOM. Alle Zeiten und Kurven kommen aus den Tokens im Stil der App (`--dauer-*`, `--kurve*`, `--feder*`); die Rückfallwerte
 * hier gelten nur, wenn ein Token nicht lesbar ist (Tests ohne Stil).
 *
 * Messung 7 (14.11., docs/plan/messungen-ha-testpanel.md) ist bindend:
 *   1. Der Cover-Flug läuft nur über FLIP mit `element.animate`. `document.startViewTransition` wird nie aufgerufen
 *      (Elemente im Shadow-DOM von HA werden von View Transitions nicht erfasst).
 *   2. FLIP animiert `borderRadius` zusammen mit `transform`, je Achse gegen die Skala ausgeglichen (`r / sx`, `r / sy`),
 *      sonst springen die Ecken am Ende.
 *   3. Der iOS-Blatt-Effekt steht in tobibox-app.js (nur der sichtbare Inhalt wird skaliert, das Blatt steckt nicht darin).
 */

export const RUECKFALL = {
  '--dauer-kurz': 150, '--dauer-mittel': 250, '--dauer-lang': 350, '--dauer-feder': 500,
  '--kurve': 'cubic-bezier(.2, 0, 0, 1)', '--kurve-aus': 'cubic-bezier(.4, 0, 1, 1)',
};

/* „Weniger Bewegung“ am Gerät? Ohne `matchMedia` (jsdom) gilt: nein. */
export function reduziert() {
  try { return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches === true; } catch { return false; }
}

/* Gibt es die Web Animations API an diesem Element? */
export function kannAnimieren(el) { return !!el && typeof el.animate === 'function'; }

/* Wert eines Tokens am Element (Text); leer oder nicht lesbar → Rückfall. */
export function tokenText(el, name, rueckfall = RUECKFALL[name]) {
  try {
    const v = getComputedStyle(el).getPropertyValue(name).trim();
    if (v) return v;
  } catch { /* ohne Stil */ }
  return rueckfall;
}

/* Dauer-Token in Millisekunden ('250ms' oder '0.25s'). */
export function tokenMs(el, name, rueckfall = RUECKFALL[name]) {
  const t = tokenText(el, name, null);
  const m = t && /^(-?\d*\.?\d+)\s*(ms|s)?$/.exec(t);
  if (!m) return rueckfall;
  const n = Number(m[1]);
  return m[2] === 's' ? n * 1000 : n;
}

/* Kurve für `element.animate`: das Token, sonst die feste Kurve (`linear()` kennt nicht jeder Browser). */
export function kurve(el, name = '--kurve') { return tokenText(el, name, RUECKFALL['--kurve']); }

/* Startet `el.animate(kf, opts)`. Lehnt der Browser die Kurve ab (kein `linear()`), noch einmal mit `--kurve`.
 * Gibt die Animation zurück oder `null` (keine Web Animations API, Fehler): der Aufrufer macht dann ohne Bewegung weiter. */
export function animiere(el, kf, opts) {
  if (!kannAnimieren(el)) return null;
  try { return el.animate(kf, opts); } catch { /* Kurve nicht verstanden */ }
  try { return el.animate(kf, { ...opts, easing: RUECKFALL['--kurve'] }); } catch { return null; }
}

/* Ruft `fn` genau einmal, wenn die Animation endet, abbricht oder nach `grenzeMs` (Zeitgeber, falls kein Ereignis kommt). Gibt `stop()` zurück. */
export function nachEnde(an, grenzeMs, fn) {
  let fertig = false;
  const los = () => { if (fertig) return; fertig = true; clearTimeout(t); fn(); };
  const t = setTimeout(los, grenzeMs);
  if (an && an.finished && typeof an.finished.then === 'function') an.finished.then(los, los);
  else if (an) { an.onfinish = los; an.oncancel = los; }
  return () => { fertig = true; clearTimeout(t); };
}

const radiusVon = (el) => { try { return parseFloat(getComputedStyle(el).borderTopLeftRadius) || 0; } catch { return 0; } };
const flaeche = (r) => !!r && r.width > 0 && r.height > 0;

/* Zwei Rechtecke → Tabelle für `flip` (Flächen im Fenster, wie `getBoundingClientRect`). */
export const rechteck = (r) => ({ left: r.left, top: r.top, width: r.width, height: r.height });

/* Gemeinsame FLIP-Hilfsfunktion (R17-1, Messung 7 h2). `el` liegt in der Seite an einer der beiden Flächen:
 *   liegt 'nach' (Standard): `el` sitzt schon am Ziel `nach` und fliegt von `von` dorthin (Serienseite öffnen, Kachel beim Zurück).
 *   liegt 'von':  `el` sitzt an `von` und fliegt zu `nach` (Vollansicht schließen, A8m); der Aufrufer räumt danach auf (`an.cancel()`).
 * `von` und `nach` sind Rechtecke ({ left, top, width, height }). Die Ecken laufen mit: der sichtbare Radius geht von `radiusVon`
 * zu `radiusNach` (Standard: der berechnete Radius von `el` für die Seite, an der es liegt, sonst derselbe Wert), je Achse gegen die
 * Skala ausgeglichen (`r / sx`, `r / sy`).
 * Rückgabe: die Animation oder `null` (keine Web Animations API, leere Fläche, Fehler): dann gibt es keinen Flug, `el` bleibt, wo es ist.
 * Während des Flugs liegt `el` über dem Rest (`z-index`) und fängt keine Eingaben ab (`pointer-events: none`, nur an diesem Element, nie global). */
export function flip(el, von, nach, { liegt = 'nach', dauer, easing, radiusVon: rv0, radiusNach: rn0, z = 30 } = {}) {
  if (!kannAnimieren(el) || !flaeche(von) || !flaeche(nach)) return null;
  const eigen = radiusVon(el);
  const rv = rv0 ?? (liegt === 'von' ? eigen : (rn0 ?? eigen));
  const rn = rn0 ?? (liegt === 'nach' ? eigen : rv);
  const auf = liegt === 'nach';
  const sx = auf ? von.width / nach.width : nach.width / von.width;
  const sy = auf ? von.height / nach.height : nach.height / von.height;
  const tr = auf
    ? `translate(${von.left - nach.left}px, ${von.top - nach.top}px) scale(${sx}, ${sy})`
    : `translate(${nach.left - von.left}px, ${nach.top - von.top}px) scale(${sx}, ${sy})`;
  const eck = (r) => `${r / sx}px / ${r / sy}px`;
  const kf = auf
    ? [{ transform: tr, borderRadius: eck(rv) }, { transform: 'none', borderRadius: `${rn}px` }]
    : [{ transform: 'none', borderRadius: `${rv}px` }, { transform: tr, borderRadius: eck(rn) }];
  const alt = { origin: el.style.transformOrigin, pe: el.style.pointerEvents, z: el.style.zIndex, pos: el.style.position };
  let pos = alt.pos;
  try { if (getComputedStyle(el).position === 'static') pos = 'relative'; } catch { /* ohne Stil */ }
  el.style.transformOrigin = '0 0';
  el.style.pointerEvents = 'none';
  el.style.zIndex = String(z);
  el.style.position = pos;
  const an = animiere(el, kf, { duration: dauer, easing, fill: auf ? 'none' : 'forwards' });
  const auf0 = () => { el.style.transformOrigin = alt.origin; el.style.pointerEvents = alt.pe; el.style.zIndex = alt.z; el.style.position = alt.pos; };
  if (!an) { auf0(); return null; }
  if (an.finished && typeof an.finished.then === 'function') an.finished.then(auf0, auf0); else { an.onfinish = auf0; an.oncancel = auf0; }
  return an;
}

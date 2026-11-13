/* Messfunktionen für pruefe_seite.py (Paket A14-1a). Läuft in der Prüfseite und liefert Befunde als Listen von Texten.
 *
 *   window.__mess()  →  { layout, hscroll, raus, klein, text, symbole, rand, leiste, extra, alt }
 *
 *   hscroll   waagerechtes Scrollen (Seite, Rahmen, Spalte, Hauptteil, Blatt, Panel)
 *   raus      sichtbare Teile, die seitlich aus dem Panel ragen (außer in gewollt scrollenden Reihen)
 *   klein     Tippziele unter 44 × 44 px (Fließtext-Links ausgenommen)
 *   text      Text unter 4,5:1 gegen den Grund
 *   symbole   Symbole (SVG) unter 3:1 gegen den Grund
 *   rand      sichtbare Ränder von Feldern und Auswahlknöpfen unter 3:1 gegen den Grund
 *   leiste    Reiterleiste (unten und oben, durchscheinend) gegen die sechs Cover-Farben: Text 4,5:1, Symbole 3:1
 *   extra     Leise-Zeiten: Abschnitte gegen die Leiste und Rand der Leiste (3:1), Wochenansicht aus dem Blatt
 *   alt       Befunde in der eingebetteten alten Komponente (tobibox-panel): nur Hinweise, die Komponente wird in Stufe A-2 ersetzt
 */
(() => {
  const MIN_TIPP = 43.5; // 44 px, Rundung der Darstellung erlaubt
  const zahlen = (s) => (String(s).match(/-?\d*\.?\d+(?:e-?\d+)?/gi) || []).map(Number);
  /* Farbe aus dem berechneten Stil: rgb(), rgba(), color(srgb …) → { c: [r,g,b] (0–255), a } oder null */
  function farbe(s) {
    if (!s || s === 'transparent') return { c: [0, 0, 0], a: 0 };
    const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(s.trim());
    if (hex) { const h = hex[1].length === 3 ? [...hex[1]].map((x) => x + x).join('') : hex[1]; return { c: [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)), a: 1 }; }
    const n = zahlen(s.replace(/^[a-z-]+\(/i, '').replace(/srgb/i, ''));
    if (n.length < 3 || n.some((x) => Number.isNaN(x))) return null;
    const faktor = /^color\(\s*srgb/i.test(s) ? 255 : 1;
    return { c: [n[0] * faktor, n[1] * faktor, n[2] * faktor], a: n.length > 3 ? n[3] : 1 };
  }
  const lum = (c) => { const [r, g, b] = c.map((x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const kontrast = (a, b) => { const x = lum(a); const y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const ueber = (f, grund) => (f.a >= 0.999 ? f.c : f.c.map((x, i) => x * f.a + grund[i] * (1 - f.a)));
  const eltern = (n) => n.parentElement || (n.getRootNode && n.getRootNode().host) || null;

  /* Farben so, wie der Betrachter sie sieht: von innen nach außen jede Ebene unter das Bisherige legen (Hintergrund), danach die
   * Deckkraft der Ebene als Gruppe anwenden (opacity gilt für Hintergrund und Inhalt zusammen). `vorn` = Farbe des Inhalts
   * ({ c, a }) oder null für den bloßen Grund. Ergebnis: RGB über weißem Blatt. */
  const rgbaUeber = (o, u) => {
    const a = o.a + u.a * (1 - o.a);
    if (a <= 0) return { c: [0, 0, 0], a: 0 };
    return { c: o.c.map((x, i) => (x * o.a + u.c[i] * u.a * (1 - o.a)) / a), a };
  };
  function sichtbarFarbe(e, vorn) {
    let cur = vorn || { c: [0, 0, 0], a: 0 };
    for (let n = e; n; n = eltern(n)) {
      const cs = getComputedStyle(n);
      const bg = farbe(cs.backgroundColor);
      if (bg && bg.a > 0) cur = rgbaUeber(cur, bg);
      const o = Number(cs.opacity);
      if (o < 1) cur = { c: cur.c, a: cur.a * o };
    }
    return rgbaUeber(cur, { c: [255, 255, 255], a: 1 }).c;
  }
  const grundVon = (e) => sichtbarFarbe(e, null);
  const beschreibe = (e, extra = '') => {
    const kl = (typeof e.className === 'string' ? e.className : e.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
    const text = (e.getAttribute('aria-label') || e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 24);
    return `${e.tagName.toLowerCase()}${kl ? `.${kl}` : ''}${text ? ` "${text}"` : ''}${extra ? ` ${extra}` : ''}`;
  };
  const sichtbar = (e) => {
    if (e.closest('.sr') || e.closest('dialog:not([open])')) return false;
    const r = e.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    if (getComputedStyle(e).visibility === 'hidden') return false;
    for (let n = e; n && n.nodeType === 1; n = n.parentElement) if (getComputedStyle(n).opacity === '0') return false; // unsichtbar (Pfeile der Reihen ohne Hover)
    return true;
  };
  const deaktiviert = (e) => !!(e.matches(':disabled') || e.closest('[aria-disabled="true"], [disabled], fieldset:disabled'));

  function wurzeln(sr) {
    const alle = [{ sr, alt: false }];
    for (const p of sr.querySelectorAll('tobibox-panel')) if (p.shadowRoot) alle.push({ sr: p.shadowRoot, alt: true });
    return alle;
  }

  function hscroll(el, sr) {
    const aus = [];
    const kandidaten = [...sr.querySelectorAll('.app, .rahmen, .spalte, main, dialog[open], tobibox-panel')];
    for (const e of kandidaten) if (e.scrollWidth > e.clientWidth + 1) aus.push(`${beschreibe(e)} scrollWidth ${e.scrollWidth} > ${e.clientWidth}`);
    for (const p of sr.querySelectorAll('tobibox-panel')) {
      for (const e of p.shadowRoot ? p.shadowRoot.querySelectorAll('.app, main') : []) if (e.scrollWidth > e.clientWidth + 1) aus.push(`alt:${beschreibe(e)} scrollWidth ${e.scrollWidth} > ${e.clientWidth}`);
    }
    if (el.scrollWidth > el.clientWidth + 1) aus.push(`Host scrollWidth ${el.scrollWidth} > ${el.clientWidth}`);
    if (document.documentElement.scrollWidth > innerWidth + 1) aus.push(`Dokument scrollWidth ${document.documentElement.scrollWidth} > ${innerWidth}`);
    return aus;
  }

  function raus(el, sr) {
    const aus = [];
    const h = el.getBoundingClientRect();
    for (const e of sr.querySelectorAll('*')) {
      if (e.closest('.sr, .hscroll, .artrow, tobibox-panel, .toastbox, dialog:not([open]), svg, [data-reihe]') || e.localName === 'dialog') continue;
      const r = e.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      const imBlatt = !!e.closest('dialog[open]'); // Blätter liegen im Top-Layer und richten sich nach dem Fenster, nicht nach dem Panel
      if (imBlatt && !e.closest('.blatt-in')) continue;
      const von = imBlatt ? 0 : h.left; const bis = imBlatt ? innerWidth : h.right;
      if (r.right > bis + 1.5 || r.left < von - 1.5) aus.push(`${beschreibe(e)} ${Math.round(r.left)}..${Math.round(r.right)} (${imBlatt ? 'Fenster' : 'Panel'} ${Math.round(von)}..${Math.round(bis)})`);
    }
    return aus.slice(0, 8);
  }

  function klein(sr, alt) {
    const aus = [];
    const sel = 'a[href], button, input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea, summary, [role=button]';
    for (const e of sr.querySelectorAll(sel)) {
      if (!sichtbar(e)) continue;
      const cs = getComputedStyle(e);
      if (e.localName === 'a' && cs.display === 'inline') continue; // Link im Fließtext
      const r = e.getBoundingClientRect();
      if (e.type === 'range') { if (r.height < MIN_TIPP) aus.push(`${beschreibe(e)} Höhe ${Math.round(r.height)}`); continue; }
      if (r.width < MIN_TIPP || r.height < MIN_TIPP) aus.push(`${alt ? 'alt:' : ''}${beschreibe(e)} ${Math.round(r.width)}x${Math.round(r.height)}`);
    }
    return aus;
  }

  function text(sr, alt) {
    const aus = [];
    for (const e of sr.querySelectorAll('*')) {
      if (['SCRIPT', 'STYLE', 'OPTION', 'OPTGROUP', 'svg', 'path'].includes(e.tagName) || e instanceof SVGElement) continue;
      const eigen = [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
      const feld = e.matches('input:not([type=range]):not([type=checkbox]):not([type=radio]):not([type=hidden]), select, textarea') && (e.value || e.localName === 'select');
      if (!eigen && !feld) continue;
      if (!sichtbar(e) || deaktiviert(e)) continue;
      const cs = getComputedStyle(e);
      const f = farbe(cs.color);
      if (!f) { aus.push(`${beschreibe(e)} Farbe nicht lesbar: ${cs.color}`); continue; }
      const k = kontrast(sichtbarFarbe(e, f), grundVon(e));
      if (k < 4.5) aus.push(`${alt ? 'alt:' : ''}${beschreibe(e, k.toFixed(2))}`);
    }
    return aus;
  }

  function symbole(sr, alt) {
    const aus = [];
    for (const e of sr.querySelectorAll('svg')) {
      if (!sichtbar(e) || deaktiviert(e) || e.closest('.bild, .sr, [data-bild]')) continue; // Illustrationen sind Schmuck
      const cs = getComputedStyle(e);
      let f = farbe(cs.fill === 'none' ? cs.stroke : cs.fill);
      if (!f || f.a === 0) continue;
      const k = kontrast(sichtbarFarbe(e, f), grundVon(e));
      if (k < 3) aus.push(`${alt ? 'alt:' : ''}${beschreibe(e.closest('a, button') || e.parentElement || e, k.toFixed(2))}`);
    }
    return aus;
  }

  function rand(sr, alt) {
    const aus = [];
    const sel = 'input:not([type=hidden]):not([type=range]):not([type=checkbox]):not([type=radio]), select, textarea, button, a.btn';
    for (const e of sr.querySelectorAll(sel)) {
      if (!sichtbar(e) || deaktiviert(e)) continue;
      const cs = getComputedStyle(e);
      const seiten = ['Top', 'Right', 'Bottom', 'Left'].filter((s) => parseFloat(cs[`border${s}Width`]) > 0 && cs[`border${s}Style`] !== 'none');
      // Felder: jeder Rand zählt. Knöpfe und Links: nur ein ganzer Rahmen (eine einzelne Trennlinie oben ist keine Kante des Bedienelements).
      if (!seiten.length || (!e.matches('input, select, textarea') && seiten.length < 4)) continue;
      const f = farbe(cs[`border${seiten[0]}Color`]);
      if (!f || f.a < 0.5) continue; // durchsichtiger Rand: der Knopf hat seine Füllung, der Text trägt ihn
      const grund = grundVon(e.parentElement || e);
      const k = kontrast(ueber(f, grund), grund);
      if (k < 3) aus.push(`${alt ? 'alt:' : ''}${beschreibe(e, k.toFixed(2))}`);
    }
    return aus;
  }

  /* Reiterleiste: unten und oben ist der Grund mit 94 % Deckkraft; das Cover darunter scheint mit 6 % durch (und unscharf). */
  function leiste(el, sr) {
    const aus = [];
    const nav = sr.querySelector('nav.tabs');
    if (!nav) return aus;
    const nf = farbe(getComputedStyle(nav).backgroundColor);
    const stil = getComputedStyle(el);
    const farben = [1, 2, 3, 4, 5, 6].map((i) => stil.getPropertyValue(`--c${i}`).trim());
    const seitenleiste = nav.closest('aside.seite') !== null; // ab 1100 px: Leiste liegt deckend auf der Seitenleiste, kein Cover dahinter
    farben.forEach((cf, i) => {
      const cover = farbe(cf);
      if (!cover || !nf) { aus.push(`Cover ${i + 1}: Farbe nicht lesbar`); return; }
      if (seitenleiste && i > 0) return;
      const leisteGrund = seitenleiste ? grundVon(nav) : ueber(nf, cover.c);
      const cl = seitenleiste ? 'Seitenleiste' : `Cover ${i + 1} (${cf})`;
      for (const a of nav.querySelectorAll('a')) {
        const aktiv = a.getAttribute('aria-current') === 'page';
        const tn = a.querySelector('.tn');
        const ti = a.querySelector('.ti');
        const chipF = ti ? farbe(getComputedStyle(ti).backgroundColor) : null;
        const chip = chipF && chipF.a > 0 ? ueber(chipF, leisteGrund) : leisteGrund;
        if (tn) {
          const tf = farbe(getComputedStyle(tn).color);
          const k = kontrast(ueber(tf, leisteGrund), leisteGrund);
          if (k < 4.5) aus.push(`${cl}: Text "${tn.textContent.trim()}"${aktiv ? ' (aktiv)' : ''} ${k.toFixed(2)}`);
        }
        const svg = a.querySelector('svg');
        if (svg) {
          const f = farbe(getComputedStyle(svg).fill);
          const k = kontrast(ueber(f, chip), chip);
          if (k < 3) aus.push(`${cl}: Symbol "${tn ? tn.textContent.trim() : ''}"${aktiv ? ' (aktiv)' : ''} ${k.toFixed(2)}`);
        }
      }
    });
    return aus;
  }

  /* Wochenansicht der Leise-Zeiten (A7b): Abschnitte gegen die Leiste und die Leiste gegen die Seite (3:1) */
  function extra(sr) {
    const aus = [];
    const trk = sr.querySelector('.wk .trk');
    if (!trk) return aus;
    const tb = grundVon(trk);
    const k = (a, b) => kontrast(a, b);
    const s = sr.querySelector('.wk .seg.s');
    const l = sr.querySelector('.wk .seg.l');
    const rl = farbe(getComputedStyle(trk).borderTopColor);
    const gegen = (name, a, b) => { const v = k(a, b); if (v < 3) aus.push(`${name} ${v.toFixed(2)}`); };
    if (s) gegen('still gegen Leiste', farbe(getComputedStyle(s).backgroundColor).c, tb);
    if (l) {
      const tinte = farbe(getComputedStyle(l).borderTopColor).c;
      gegen('leiser-Rand gegen Leiste', tinte, tb);
      const streifen = (getComputedStyle(sr.querySelector('.wk .lg i.l')).backgroundImage.match(/rgba?\([^)]*\)/g) || []).slice(-1)[0];
      if (streifen) gegen('leiser-Rand gegen Streifen', tinte, ueber(farbe(streifen), tb));
    }
    if (rl && rl.a > 0.5) gegen('Rand der Leiste gegen Seite', rl.c, grundVon(trk.parentElement));
    return aus;
  }

  window.__mess = () => {
    const el = window.__el;
    const sr = el.shadowRoot;
    const aus = { layout: el.getAttribute('data-layout'), hscroll: hscroll(el, sr), raus: raus(el, sr), klein: [], text: [], symbole: [], rand: [], leiste: leiste(el, sr), extra: extra(sr), alt: [] };
    for (const w of wurzeln(sr)) {
      const ziel = w.alt ? aus.alt : null;
      const k = klein(w.sr, w.alt); const t = text(w.sr, w.alt); const sy = symbole(w.sr, w.alt); const ra = rand(w.sr, w.alt);
      if (ziel) ziel.push(...k, ...t, ...sy, ...ra); else { aus.klein.push(...k); aus.text.push(...t); aus.symbole.push(...sy); aus.rand.push(...ra); }
    }
    return aus;
  };
  /* Wartet, bis die App fertig gezeichnet hat: keine Platzhalter, Dialog nicht in Bewegung, zwei Bilder lang ruhig. */
  window.__ruhe = async (maxMs = 4000) => {
    const el = window.__el;
    const ende = Date.now() + maxMs;
    const bild = () => new Promise((r) => requestAnimationFrame(() => r()));
    do {
      await el.updateComplete;
      await bild(); await bild();
      const sr = el.shadowRoot;
      if (!sr.querySelector('.skel') && !sr.querySelector('dialog[data-closing]') && !sr.querySelector('[aria-busy="true"]')) break;
      await new Promise((r) => setTimeout(r, 40));
    } while (Date.now() < ende);
    await new Promise((r) => setTimeout(r, 60));
    await el.updateComplete;
    return true;
  };
})();

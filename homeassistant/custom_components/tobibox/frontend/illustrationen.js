// Illustrationen der leeren Zustände (Design docs/designs/ha-oberflaeche.md, Abschnitt 6.2, Paket A6b).
// Ein ES-Modul ohne Abhängigkeiten. Jede Illustration ist ein Inline-SVG (viewBox 0 0 200 150),
// aria-hidden, weil der Satz daneben alles sagt. Keine fremden Marken oder Figuren.
// Farben nur über CSS-Variablen (Tokens); die Klassen des Prototyps werden beim Laden in
// style-Attribute mit var(--…) umgesetzt. Vorlage: docs/egm/ha-ui/prototyp.html (ILLU).

const FARBE = {
  f1: 'fill:var(--primary-soft)',
  f2: 'fill:var(--card)',
  f3: 'fill:var(--primary-ink)',
  f4: 'fill:var(--warn-bg)',
  f6: 'fill:var(--warn)',
  s1: 'stroke:var(--primary-ink);stroke-width:3',
  s2: 'stroke:var(--text2);stroke-width:3',
  s3: 'stroke:var(--warn);stroke-width:3',
  s4: 'stroke:var(--ok);stroke-width:3',
  th: 'stroke-width:7',
};

// Klasse → style. Eine unbekannte Klasse bricht ab, damit ein Tippfehler nicht still ungefärbt bleibt.
function farben(markup) {
  return markup.replace(/ class="([^"]*)"/g, (_, klassen) => {
    const teile = klassen.split(' ').map((k) => {
      if (!FARBE[k]) throw new Error(`Unbekannte Klasse in Illustration: ${k}`);
      return FARBE[k];
    });
    return ` style="${teile.join(';')}"`;
  });
}

const KOPF = '<svg class="illu" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 150" aria-hidden="true" focusable="false" fill="none" stroke="none" stroke-linecap="round" stroke-linejoin="round">';

function svg(inhalt) {
  return KOPF + farben(inhalt) + '</svg>';
}

// Sterne für Akzente (in mehreren Bildern gleich).
const SPARK = '<path class="f4 s3" d="M176 26l3 7 7 3-7 3-3 7-3-7-7-3 7-3z"/>';

// Bibliothek leer: leeres Regal mit Lücke und Note.
export const bibliothekLeer = svg(
  '<ellipse class="f1" cx="100" cy="138" rx="80" ry="9"/><rect class="f2 s1" x="36" y="20" width="128" height="108" rx="14"/><path class="s1" d="M36 76h128"/>' +
  '<rect class="f1 s1" x="52" y="40" width="16" height="36" rx="4"/><rect class="f4 s3" x="72" y="48" width="16" height="28" rx="4"/><rect class="f1 s1" x="94" y="40" width="16" height="36" rx="4" transform="rotate(10 102 76)"/>' +
  '<rect class="s2" x="54" y="90" width="24" height="32" rx="4" stroke-dasharray="5 6"/><circle class="f3" cx="112" cy="112" r="7"/><circle class="f3" cx="134" cy="108" r="7"/><path class="s1" d="M119 112V90l22-6v24"/>' + SPARK
);

// Keine Tobies: lächelnder Tobie über der Box.
export const keineTobies = svg(
  '<ellipse class="f1" cx="100" cy="138" rx="76" ry="9"/><rect class="f2 s1" x="46" y="82" width="108" height="50" rx="16"/><circle class="s2" cx="100" cy="107" r="15"/><circle class="f3" cx="100" cy="107" r="5"/>' +
  '<circle class="f4 s3" cx="100" cy="42" r="24"/><path class="s3" d="M89 47q11 10 22 0"/><circle class="f6" cx="92" cy="37" r="2.6"/><circle class="f6" cx="108" cy="37" r="2.6"/>' +
  '<circle class="f1" cx="100" cy="68" r="3"/><circle class="f1" cx="100" cy="76" r="2"/>' + SPARK
);

// Keine Box eingerichtet: schlafende Box mit Zzz und gezogenem Stecker.
export const keineBox = svg(
  '<ellipse class="f1" cx="100" cy="138" rx="80" ry="9"/><rect class="f2 s1" x="48" y="46" width="104" height="84" rx="18"/><path class="s2" d="M78 84q6 6 12 0M110 84q6 6 12 0M94 102q6 5 12 0"/>' +
  '<circle class="f1 s1" cx="76" cy="116" r="4"/><circle class="f1 s1" cx="124" cy="116" r="4"/><path class="s1" d="M158 40h14l-14 16h14M176 16h10l-10 12h10"/>' +
  '<path class="s2" d="M48 118c-14 0-14 12-26 12"/><rect class="f4 s3" x="12" y="124" width="12" height="12" rx="3"/>'
);

// Suche ohne Treffer (Suchansicht, Tobies-Suche): Lupe mit Fragezeichen.
export const sucheOhneTreffer = svg(
  '<ellipse class="f1" cx="100" cy="138" rx="76" ry="9"/><circle class="f2 s1 th" cx="88" cy="66" r="36"/><path class="s1 th" d="M115 93l34 34"/>' +
  '<path class="s2" d="M78 58q0-12 11-12t11 12q0 8-11 11v5"/><circle class="f3" cx="89" cy="86" r="3"/><circle class="f4" cx="160" cy="40" r="6"/><circle class="f1" cx="34" cy="34" r="7"/>'
);

// Filter ohne Treffer (Bibliothek): dieselbe Lupe wie bei der Suche (Design 6.2).
export const filterOhneTreffer = sucheOhneTreffer;

// Papierkorb leer (Technik): Papierkorb mit Haken.
export const papierkorbLeer = svg(
  '<ellipse class="f1" cx="100" cy="138" rx="72" ry="9"/><path class="f2 s1" d="M62 56h76l-6 72H68z"/><path class="s1" d="M54 56h92"/><path class="s1" d="M86 56V46a4 4 0 0 1 4-4h20a4 4 0 0 1 4 4v10"/>' +
  '<path class="s4 th" d="M84 94l12 12 24-26"/>' + SPARK
);

// Gehört ohne Daten (Stufe B): Kopfhörer mit leerem Diagramm.
export const gehoertOhneDaten = svg(
  '<ellipse class="f1" cx="100" cy="138" rx="76" ry="9"/><path class="s1 th" d="M52 98V82a48 48 0 0 1 96 0v16"/><rect class="f4 s3" x="40" y="92" width="24" height="38" rx="10"/><rect class="f4 s3" x="136" y="92" width="24" height="38" rx="10"/>' +
  '<rect class="f1 s2" x="82" y="106" width="9" height="16" rx="3"/><rect class="f1 s2" x="96" y="96" width="9" height="26" rx="3"/><rect class="f1 s2" x="110" y="110" width="9" height="12" rx="3"/><path class="s2" d="M78 128h44"/>' + SPARK
);

// Alle Illustrationen nach dem Namen aus dem Design (Abschnitt 6.2).
export const ILLUSTRATIONEN = {
  bibliothekLeer,
  keineTobies,
  keineBox,
  sucheOhneTreffer,
  filterOhneTreffer,
  papierkorbLeer,
  gehoertOhneDaten,
};

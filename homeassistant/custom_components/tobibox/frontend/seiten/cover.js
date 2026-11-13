/* Cover ändern (Design 5.5; Paket A8f): Blatt „Cover für „<Name>““ mit „Foto wählen“, Zuschneiden im Browser und
 * „Zurück zum automatischen Cover“. Gehört zur Serienseite (Menü „⋯“ des Eintrags, Serie und Einzeltitel) und wird von seiten/serie.js
 * mit `coverBlatt(...)` geöffnet; die Seite selbst ist keine Route.
 *
 * Ablauf: Foto wählen (`<input type="file" accept="image/*">`, am Handy Kamera oder Galerie) → mehr als 20 MB oder kein Bild:
 * Fehlermeldung (bleibt stehen, 6.3) → Zuschneiden: quadratische Vorschau (280 px), Verschieben mit Finger oder Maus, vier Pfeilknöpfen
 * oder den Pfeiltasten, Regler „Ausschnitt größer oder kleiner“ → „Speichern“ zeichnet das Quadrat auf 1024 × 1024 px, kodiert JPEG
 * (Qualität 0,85, bei mehr als 1,5 MiB weniger, höchstens 3 MiB) und sendet nur das Quadrat: `POST /api/tobibox/cover/<id>`
 * (Vertrag 14.3). „Zurück zum automatischen Cover“ (nur mit eigenem Foto, `cover_quelle === 'eigen'`): `DELETE …?quelle=eigen`.
 * Die Ausrichtung nach den EXIF-Angaben erledigt der Browser beim Dekodieren (`imageOrientation: 'from-image'`).
 * Die Vorschau ist ein <canvas>, das hier von Hand angelegt und ins Blatt gesetzt wird (Lit behält den Knoten).
 */
import { html, nothing, css } from '../bausteine.js';
import { COVER, SERIE, fuellen } from '../texte.js';

export const KANTE = 1024; // Seitenlänge der Ausgabe in Pixeln
export const VORSCHAU = 280; // Seitenlänge der Vorschau in CSS-Pixeln
export const FOTO_MAX = 20 * 1024 * 1024; // größeres Foto vom Handy wird abgelehnt (Design 5.5)
export const ZIEL_BYTES = 1.5 * 1024 * 1024; // darüber: weniger Qualität
export const MAX_BYTES = 3 * 1024 * 1024; // `COVER_UPLOAD_MAX_BYTES` (Vertrag 2.4)
export const QUALITAETEN = [0.85, 0.75, 0.65, 0.55, 0.45, 0.35];
export const ZOOM_MAX = 4; // Regler ganz rechts: Ausschnitt ein Viertel der kurzen Seite
const SCHRITT = 0.1; // ein Pfeilknopf verschiebt um ein Zehntel des Ausschnitts

/* ------------------------------------------------------------------ reine Funktionen */

const zwischen = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

/* Ausschnitt eines Fotos der Größe b × h: Regler 0 (ganzes Quadrat der kurzen Seite) bis 100 (ein Viertel davon), `mitte` = Mittelpunkt
 * in Bildpunkten. Das Quadrat bleibt immer ganz im Foto. Liefert { sx, sy, seite, cx, cy }. */
export function ausschnitt(b, h, regler = 0, mitte = null) {
  const kurz = Math.min(b, h);
  const seite = kurz / (1 + (ZOOM_MAX - 1) * (zwischen(Number(regler) || 0, 0, 100) / 100));
  const cx = zwischen(mitte?.x ?? b / 2, seite / 2, b - seite / 2);
  const cy = zwischen(mitte?.y ?? h / 2, seite / 2, h - seite / 2);
  return { sx: cx - seite / 2, sy: cy - seite / 2, seite, cx, cy };
}

/* Text zu einem Fehler des Hochladens: Netzfehler, Größe des Bildes (nicht der Text für Dateien mit 2 GB) und die Codes des Vertrags. */
export function coverFehlerText(ctx, code) {
  if (code === 'verbindung') return COVER.netz;
  if (code === 'datei_zu_gross') return COVER.bild_zu_gross;
  if (code === 'cover_zu_gross') return COVER.nach_verkleinern_zu_gross;
  return ctx.fehlerText(code);
}

/* Foto decodieren: `createImageBitmap` mit Ausrichtung nach EXIF, sonst ohne die Option, zuletzt über <img>. `null`: kein Bild. */
export async function ladeBild(datei) {
  const cib = globalThis.createImageBitmap;
  if (typeof cib === 'function') {
    for (const opt of [{ imageOrientation: 'from-image' }, null]) {
      try {
        const bmp = await (opt ? cib.call(globalThis, datei, opt) : cib.call(globalThis, datei));
        if (bmp && bmp.width > 0 && bmp.height > 0) return { bild: bmp, b: bmp.width, h: bmp.height, frei: () => bmp.close?.() };
      } catch { /* nächster Versuch */ }
    }
  }
  if (typeof Image === 'function' && typeof URL?.createObjectURL === 'function') {
    const url = URL.createObjectURL(datei);
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      if (img.naturalWidth > 0 && img.naturalHeight > 0) return { bild: img, b: img.naturalWidth, h: img.naturalHeight, frei: () => {} };
    } catch { /* kein Bild */ } finally { URL.revokeObjectURL?.(url); }
  }
  return null;
}

const alsBlob = (leinwand, qualitaet) => new Promise((ok, nein) => {
  try { leinwand.toBlob((b) => (b ? ok(b) : nein(new Error('toBlob ohne Ergebnis'))), 'image/jpeg', qualitaet); } catch (e) { nein(e); }
});

/* Zeichnet den Ausschnitt auf KANTE × KANTE und kodiert JPEG: Qualität 0,85; ist das Ergebnis größer als 1,5 MiB, Stufe für Stufe
 * weniger. Bleibt es über 3 MiB, wirft die Funktion { code: 'cover_zu_gross' }. Liefert { blob, qualitaet }. */
export async function kodiereQuadrat(foto, aus) {
  const c = document.createElement('canvas');
  c.width = KANTE; c.height = KANTE;
  const g = c.getContext?.('2d');
  if (!g) throw { code: 'cover_ungueltig' };
  g.fillStyle = '#ffffff'; // JPEG kennt keine Durchsicht
  g.fillRect(0, 0, KANTE, KANTE);
  g.imageSmoothingQuality = 'high';
  g.drawImage(foto.bild, aus.sx, aus.sy, aus.seite, aus.seite, 0, 0, KANTE, KANTE);
  let letzte = null;
  for (const q of QUALITAETEN) {
    let blob;
    try { blob = await alsBlob(c, q); } catch { throw { code: 'cover_ungueltig' }; }
    letzte = { blob, qualitaet: q };
    if (blob.size <= ZIEL_BYTES) return letzte;
  }
  if (letzte.blob.size > MAX_BYTES) throw { code: 'cover_zu_gross' };
  return letzte;
}

/* POST (mit `blob`) oder DELETE `quelle=eigen` des Covers mit `hass.fetchWithAuth`. Antwort `{ serie_id, cover_stand, cover_quelle, … }`;
 * Fehler werfen { code } (Netz: 'verbindung'; Antwort `fehler.code` des Backends, sonst nach dem HTTP-Status). */
export async function sendeCover(hass, id, blob = null) {
  const pfad = `/api/tobibox/cover/${encodeURIComponent(id)}${blob ? '' : '?quelle=eigen'}`;
  let r;
  try {
    r = await hass.fetchWithAuth(pfad, blob ? { method: 'POST', headers: { 'Content-Type': 'image/jpeg' }, body: blob } : { method: 'DELETE' });
  } catch { throw { code: 'verbindung' }; }
  let daten = null;
  try { daten = await r.json(); } catch { /* keine Antwort im JSON-Format */ }
  if (r.ok && daten && 'cover_stand' in daten) return daten;
  const nachStatus = { 413: 'datei_zu_gross', 429: 'zu_viele_aenderungen', 401: 'unauthorized', 403: 'unauthorized', 404: 'serie_nicht_gefunden' };
  throw { code: daten?.fehler?.code || nachStatus[r.status] || 'unknown_error' };
}

/* ------------------------------------------------------------------ Blatt */

const PFEIL = {
  hoch: 'M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z',
  runter: 'M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.58-5.59L4 12l8 8 8-8z',
  links: 'M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z',
  rechts: 'M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8z',
};
// Richtung eines Pfeils -> wohin sich die Mitte des Ausschnitts bewegt (das Foto selbst wandert in die Gegenrichtung)
const RICHTUNG = { hoch: [0, 1], runter: [0, -1], links: [1, 0], rechts: [-1, 0] };
const TASTEN = { ArrowUp: 'hoch', ArrowDown: 'runter', ArrowLeft: 'links', ArrowRight: 'rechts' };

/* Öffnet das Blatt.
 *   ctx            Seiten-Kontext (api, melde, meldeFehler, fehlerText, neuZeichnen, schliesseBlatt, covers, hass)
 *   serie()        liefert die aktuelle Kurzform { id, name, cover_quelle } (bei jedem Zeichnen neu gefragt)
 *   oeffne(opts)   öffnet ein Blatt wie `oeffneBlatt` (die Serienseite kümmert sich um den Fokus danach)
 *   geaendert(r)   Antwort von POST/DELETE (`cover_stand`, `cover_quelle`): die Seite zeigt das neue Cover ohne Neuladen
 *   fehler(err)    meldet einen Fehler; liefert 'zu' (Blatt schließen, die Seite lädt neu) oder 'offen'
 */
export function coverBlatt({ ctx, serie, oeffne, geaendert, fehler }) {
  const s0 = serie();
  const Z = { phase: 'wahl', foto: null, regler: 0, mitte: null, laeuft: null, vorher: 'wahl' }; // laeuft: null | 'lade' | 'speichern' | 'zurueck'
  const knoepfe = [];
  const canvas = document.createElement('canvas');
  canvas.width = VORSCHAU * 2; canvas.height = VORSCHAU * 2; // doppelt, damit die Vorschau auf scharfen Bildschirmen scharf ist
  canvas.className = 'cv-vorschau';
  canvas.tabIndex = 0;
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', COVER.vorschau);
  canvas.setAttribute('data-cover-vorschau', '');

  const aus = () => ausschnitt(Z.foto.b, Z.foto.h, Z.regler, Z.mitte);
  const zeichne = () => {
    if (!Z.foto) return;
    const a = aus();
    Z.mitte = { x: a.cx, y: a.cy };
    canvas.dataset.regler = String(Math.round(Z.regler));
    canvas.dataset.mitte = `${Math.round(a.cx)},${Math.round(a.cy)}`;
    const g = canvas.getContext?.('2d');
    if (!g) return;
    g.fillStyle = '#ffffff';
    g.fillRect(0, 0, canvas.width, canvas.height);
    g.drawImage(Z.foto.bild, a.sx, a.sy, a.seite, a.seite, 0, 0, canvas.width, canvas.height);
  };
  const schiebe = (dx, dy) => { // in Bildpunkten, bezogen auf die Mitte des Ausschnitts
    const a = aus();
    Z.mitte = { x: a.cx + dx, y: a.cy + dy };
    zeichne();
  };
  const pfeil = (richtung) => {
    if (!Z.foto) return;
    const a = aus();
    const [rx, ry] = RICHTUNG[richtung];
    schiebe(rx * a.seite * SCHRITT, ry * a.seite * SCHRITT);
  };

  // Ziehen mit Finger oder Maus: das Foto folgt dem Zeiger
  let zug = null;
  const px = () => canvas.getBoundingClientRect?.().width || VORSCHAU;
  canvas.addEventListener('pointerdown', (e) => {
    if (!Z.foto || (e.button ?? 0) > 0) return;
    zug = { x: e.clientX, y: e.clientY, start: aus() };
    try { canvas.setPointerCapture?.(e.pointerId); } catch { /* ohne */ }
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!zug || !Z.foto) return;
    const m = zug.start.seite / px(); // Bildpunkte je Bildschirmpunkt der Vorschau
    Z.mitte = { x: zug.start.cx - (e.clientX - zug.x) * m, y: zug.start.cy - (e.clientY - zug.y) * m };
    zeichne();
  });
  const zugEnde = () => { zug = null; };
  canvas.addEventListener('pointerup', zugEnde);
  canvas.addEventListener('pointercancel', zugEnde);
  canvas.addEventListener('keydown', (e) => {
    const r = TASTEN[e.key];
    if (!r || e.altKey || e.ctrlKey || e.metaKey) return;
    e.preventDefault();
    pfeil(r);
  });

  const setzeKnoepfe = () => {
    knoepfe.length = 0;
    knoepfe.push({ label: SERIE.abbrechen });
    if (Z.phase === 'schneiden') knoepfe.push({ label: COVER.speichern, kind: 'primary', fn: speichern });
  };

  const waehlen = () => ctx.wurzel?.querySelector('input[data-cover-datei]')?.click();

  const foto = async (e) => {
    const eingabe = e.target;
    const datei = eingabe.files?.[0];
    eingabe.value = ''; // dasselbe Foto lässt sich danach noch einmal wählen
    if (!datei || Z.laeuft) return;
    if (datei.size > FOTO_MAX) { ctx.meldeFehler(COVER.zu_gross); return; }
    if (datei.type && !datei.type.startsWith('image/')) { ctx.meldeFehler(COVER.kein_bild); return; }
    Z.laeuft = 'lade';
    ctx.neuZeichnen();
    const neu = await ladeBild(datei);
    Z.laeuft = null;
    if (!neu) { ctx.meldeFehler(COVER.kein_bild); ctx.neuZeichnen(); return; }
    Z.foto?.frei();
    Z.foto = neu; Z.regler = 0; Z.mitte = null; Z.phase = 'schneiden';
    setzeKnoepfe();
    ctx.neuZeichnen();
    setTimeout(() => { zeichne(); canvas.focus?.({ preventScroll: true }); }, 0);
  };

  async function speichern() {
    if (Z.laeuft || !Z.foto) return false;
    Z.laeuft = 'speichern';
    ctx.neuZeichnen();
    try {
      const { blob } = await kodiereQuadrat(Z.foto, aus());
      const r = await sendeCover(ctx.hass, serie().id, blob);
      ctx.covers.merke([{ id: r.serie_id ?? s0.id, cover_stand: r.cover_stand }]);
      geaendert(r);
      ctx.melde(COVER.gespeichert);
      return undefined;
    } catch (err) {
      return fehler(err) === 'zu' ? undefined : false;
    } finally { Z.laeuft = null; ctx.neuZeichnen(); }
  }

  async function zurueck() {
    if (Z.laeuft) return;
    Z.laeuft = 'zurueck';
    ctx.neuZeichnen();
    try {
      const r = await sendeCover(ctx.hass, serie().id);
      ctx.covers.merke([{ id: r.serie_id ?? s0.id, cover_stand: r.cover_stand }]);
      geaendert(r);
      ctx.melde(COVER.zurueck_fertig);
      ctx.schliesseBlatt('knopf');
    } catch (err) {
      fehler(err);
    } finally { Z.laeuft = null; ctx.neuZeichnen(); }
  }

  const pfeilKnopf = (r) => html`<button type="button" class="iconbtn cv-pfeil" data-cover-pfeil=${r} aria-label=${COVER.pfeil[r]} ?disabled=${!!Z.laeuft} @click=${() => pfeil(r)}>
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false"><path d=${PFEIL[r]}></path></svg></button>`;

  const inhalt = () => {
    const s = serie() ?? s0;
    const eigen = s.cover_quelle === 'eigen';
    const sperre = !!Z.laeuft;
    return html`<input type="file" accept="image/*" class="sr" tabindex="-1" data-cover-datei aria-hidden="true" @change=${foto}>
      ${Z.phase === 'wahl' ? html`<p class="muted">${COVER.satz}</p>
        <div class="btns"><button type="button" class="btn primary" data-cover-waehlen autofocus ?disabled=${sperre} @click=${waehlen}>${COVER.foto_waehlen}</button></div>
        ${eigen ? html`<div class="se-apart"><button type="button" class="btn link cv-zurueck" data-cover-zurueck ?disabled=${sperre} @click=${zurueck}>${COVER.zurueck}</button></div>` : nothing}`
        : html`<p class="muted">${COVER.satz_schneiden}</p>
        <div class="cv-mitte">${canvas}</div>
        <div class="cv-pfeile" role="group" aria-label=${COVER.pfeile}>${['links', 'hoch', 'runter', 'rechts'].map(pfeilKnopf)}</div>
        <div class="se-feld cv-regler"><label for="cv-regler">${COVER.regler}</label>
          <div class="cv-reglerzeile"><span aria-hidden="true">${COVER.groesser}</span>
            <input id="cv-regler" type="range" min="0" max="100" step="1" data-cover-regler ?disabled=${sperre} .value=${String(Z.regler)}
              @input=${(e) => { Z.regler = Number(e.target.value); zeichne(); }}>
            <span aria-hidden="true">${COVER.kleiner}</span></div></div>
        <div class="btns cv-neu"><button type="button" class="btn" data-cover-anderes ?disabled=${sperre} @click=${waehlen}>${COVER.anderes_foto}</button></div>`}
      ${Z.laeuft ? html`<p class="muted cv-status" role="status" data-cover-status>${Z.laeuft === 'lade' ? COVER.laedt : Z.laeuft === 'speichern' ? COVER.speichert : COVER.zurueck_laeuft}</p>` : nothing}`;
  };

  setzeKnoepfe();
  const p = oeffne({ titel: fuellen(COVER.titel, { name: s0.name }), inhalt, knoepfe });
  p.then(() => { Z.foto?.frei(); Z.foto = null; });
  return p;
}

/* Stil des Blatts (seiten/serie.js hängt ihn an den eigenen an). */
export function coverStil() {
  return css`
  .cv-mitte { display: grid; place-items: center; margin: 8px 0; }
  .cv-vorschau { width: min(280px, 100%); aspect-ratio: 1; border-radius: var(--r-card); border: 2px solid var(--line); background: var(--card); touch-action: none; cursor: grab; display: block; box-sizing: border-box; }
  .cv-vorschau:active { cursor: grabbing; }
  .cv-pfeile { display: flex; justify-content: center; gap: 12px; margin: 8px 0; }
  .cv-pfeil { min-width: 48px; min-height: 48px; width: 48px; height: 48px; border-radius: 12px; border: 1px solid var(--line); background: var(--primary-soft); color: var(--primary-ink); }
  .cv-pfeil:disabled { opacity: 0.4; }
  .cv-regler { margin: 12px 0 4px; }
  .cv-reglerzeile { display: flex; align-items: center; gap: 12px; color: var(--text2); }
  .cv-reglerzeile input[type="range"] { flex: 1; min-width: 0; min-height: 44px; width: auto; padding: 0; border: 0; background: none; accent-color: var(--primary-ink); }
  .se-apart .btn.link.cv-zurueck { color: var(--primary-ink); } /* kein Löschen: nicht rot wie „In den Papierkorb“ */
  .cv-neu { justify-content: center; margin-top: 8px; }
  .cv-status { text-align: center; margin: 8px 0 0; }
  `;
}

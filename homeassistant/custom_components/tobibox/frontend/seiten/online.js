/* Online-Suche auf der Serienseite (Design docs/designs/online-suche.md Abschnitt 10 und 5, Paket OS4): Blatt „Online suchen“ mit Trefferliste und
 * Übersicht „heute → neu“, die Übersicht eines Vorschlags aus der Karte „bitte ansehen“, die Zeilen der Vorschläge, das Blatt „Zurücknehmen?“
 * und die kleinen Helfer für Hinweiszeile, Alter und Beschreibung. Gehört zur Serienseite (seiten/serie.js) und zur Technik (seiten/technik_online.js).
 *
 * Alles hier gibt es nur für Administratoren mit der Fähigkeit `online_suche` (Befehle 57 bis 63, Vorschau-HTTP); nur der volle Beschreibungstext
 * (Nr. 64) ist für alle da. Texte aus den Quellen (Titel, Beschreibung, `grund` von Claude) stehen immer als Text, nie als HTML (Lit setzt Textknoten).
 *
 * Befehle: Nr. 57 `online/suchen` (beim Öffnen und auf „Suchen“), Nr. 58 `online/treffer` (Übersicht, mit `treffer_id` oder `serie_id` + `vorschlag_id`),
 * Nr. 59 `online/uebernehmen` (mit `stand` und `anfrage_id`; die Werte kommen nie von der Seite), Nr. 60 `online/zuruecknehmen` (Form `serie_id`).
 * Das Bild eines Treffers (oder, T10, eines Vorschlags über dessen `vorschau_id` aus Nr. 58) kommt über `GET /api/tobibox/online/vorschau/<treffer_id>` mit `hass.fetchWithAuth` als `blob:` (nur für die obersten 5 Treffer,
 * die HA schon geladen hat; sonst Platzhalter) und wird beim Schließen des Blatts freigegeben.
 */
import { html, nothing, css, ic, cover, coverKlasse, zaehle } from '../bausteine.js';
import { ONLINE, ZEILE, SERIE, SEITE, fuellen } from '../texte.js';

/* ------------------------------------------------------------------ reine Funktionen */

export const FELDER = ['serie_name', 'folge_titel', 'nummer', 'art', 'cover', 'beschreibung', 'alter_ab'];
export const VORSCHAU_ANZAHL = 5; // so viele der obersten Treffer hat HA schon mit Bild geladen (Vertrag 3.15, Nr. 57)
export const BESCHREIBUNG_KURZ = 120; // in der Übersicht: so viele Zeichen, dann „mehr“
const ENDE_FEHLER = ['stand_veraltet', 'serie_nicht_gefunden', 'folge_nicht_gefunden', 'vorschlag_nicht_gefunden', 'aenderung_nicht_gefunden']; // Blatt schließen, die Seite lädt neu

/* `serie_name` oder `folge_titel@Name` → [feld, folge|null]; getrennt wird am ersten „@“. */
export function teileKey(key) {
  const s = String(key);
  const i = s.indexOf('@');
  return i < 0 ? [s, null] : [s.slice(0, i), s.slice(i + 1)];
}

/* „Cover, Art“ aus einer Liste von Feldnamen (mit oder ohne `@Folge`): ohne Doppelte, unbekannte Namen fallen weg; „Cover, Art und Nummer“. */
export function feldListe(felder) {
  const aus = [];
  for (const k of felder || []) {
    const [f] = teileKey(k);
    const n = ONLINE.feld[f];
    if (n && !aus.includes(n)) aus.push(n);
  }
  return aus.length > 1 ? `${aus.slice(0, -1).join(', ')}${ONLINE.und}${aus.at(-1)}` : (aus[0] ?? '');
}

/* Uhrzeit „14:20“ aus einem Zeitstempel (in der Zeitzone von HA, sonst des Geräts); bei Unbrauchbarem ''. */
export function uhrzeit(iso, zone) {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return '';
  try { return new Intl.DateTimeFormat('de-DE', { hour: '2-digit', minute: '2-digit', timeZone: zone || undefined }).format(t); } catch { return new Intl.DateTimeFormat('de-DE', { hour: '2-digit', minute: '2-digit' }).format(t); }
}

export const quellenName = (q) => ONLINE.quelle[q] ?? q;

/* Die Suche von Hand gibt es für Administratoren mit der Fähigkeit bei normalen Einträgen (nicht bei der Überraschungs-Serie, Vertrag 3.15). */
export const darfSuchen = (ctx, s) => ctx.admin === true && ctx.faehig('online_suche') && s?.typ === 'normal';

/* Vorschläge (nur Administratoren mit Fähigkeit): die Liste aus `serie/get`, sonst leer. */
export const vorschlaege = (ctx, s) => (ctx.admin === true && ctx.faehig('online_suche') && Array.isArray(s?.online_vorschlaege_liste) ? s.online_vorschlaege_liste : []);

/* Welche Felder sind in der Übersicht angehakt? Entscheidung O14 (Design 5.2 Punkt 3): alle, außer die „von Hand“ gesetzten. Eine Stelle für die Regel. */
export function vorauswahl(felder) {
  return new Set(Object.entries(felder || {}).filter(([, w]) => !w?.hand).map(([k]) => k));
}

/* Reihenfolge in der Übersicht: Felder des Eintrags (Name, Art, Cover), danach je Folge (in der Reihenfolge der Serie) Titel, Nummer, Alter, Beschreibung. */
const EINTRAG_REIHE = ['serie_name', 'art', 'cover'];
const FOLGE_REIHE = ['folge_titel', 'nummer', 'alter_ab', 'beschreibung'];
export function sortiereFelder(keys, folgen = []) {
  const idx = (n) => { const i = folgen.findIndex((f) => f.name === n); return i < 0 ? 9999 : i; };
  const rang = (k) => {
    const [f, n] = teileKey(k);
    if (n === null) return [0, 0, EINTRAG_REIHE.indexOf(f) < 0 ? 9 : EINTRAG_REIHE.indexOf(f)];
    return [1, idx(n), FOLGE_REIHE.indexOf(f) < 0 ? 9 : FOLGE_REIHE.indexOf(f)];
  };
  return [...keys].sort((a, b) => { const x = rang(a); const y = rang(b); return x[0] - y[0] || x[1] - y[1] || x[2] - y[2] || a.localeCompare(b); });
}

/* Satz zu einem Vorschlag der Karte: Quelle `claude` mit Namen, Zusammenführen oder Felder einer Quelle. `ziele`: Zielserien (id → { name }). */
export function vorschlagText(v, ziele = {}) {
  if (v.art === 'zusammenfuehren') {
    const z = ziele[v.ziel_serie_id];
    return z?.name ? fuellen(ONLINE.vorschlag.zusammen, { ziel: z.name }) : ONLINE.vorschlag.zusammen_ohne_name;
  }
  if (istNamensvorschlag(v)) return fuellen(ONLINE.vorschlag.name, { name: v.name ?? '' });
  return fuellen(ONLINE.vorschlag.von, { felder: feldListe(v.felder), quelle: quellenName(v.quelle) });
}

export const istNamensvorschlag = (v) => v?.art === 'felder' && v?.quelle === 'claude' && Array.isArray(v.felder) && v.felder.includes('serie_name');

const anfrageId = () => (globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : `a${Math.random().toString(16).slice(2)}${Date.now().toString(16)}`);

/* Kurz: höchstens `n` Zeichen, am Wortende gekürzt, mit „…“. */
export function kuerzen(text, n = BESCHREIBUNG_KURZ) {
  const t = String(text ?? '');
  if (t.length <= n) return t;
  const rest = t.slice(0, n);
  const i = rest.lastIndexOf(' ');
  return `${(i > n * 0.6 ? rest.slice(0, i) : rest).trimEnd()} …`;
}

/* Wert eines Felds als Text für die Übersicht. */
function wertText(feld, wert) {
  if (wert === null || wert === undefined || wert === '') return null;
  if (feld === 'art') return ZEILE.art[wert] ?? String(wert);
  if (feld === 'alter_ab') return fuellen(ONLINE.uebersicht.alter, { alter: wert });
  return String(wert);
}

/* ------------------------------------------------------------------ Vorschaubild */

/* Das Bild eines Treffers als `blob:` oder null (kein Bild, abgelaufen, Fehler). Kein Bild von einem fremden Host: nur die Integration selbst, mit der Anmeldung von HA. */
export const VORSCHAU = { nochmalMs: 1500 }; // 404 `cover_nicht_gefunden` („Bild noch nicht geladen“): ein zweiter Versuch nach so vielen ms

async function holeVorschau(ctx, trefferId) {
  try {
    const hass = ctx.hass;
    if (!hass || typeof hass.fetchWithAuth !== 'function' || typeof URL.createObjectURL !== 'function') return { url: null, status: 0 };
    const r = await hass.fetchWithAuth(`/api/tobibox/online/vorschau/${encodeURIComponent(trefferId)}`);
    if (!r || !r.ok) return { url: null, status: r?.status ?? 0 };
    return { url: URL.createObjectURL(await r.blob()), status: 200 };
  } catch { return { url: null, status: 0 }; }
}

export async function ladeVorschau(ctx, trefferId) {
  return (await holeVorschau(ctx, trefferId)).url;
}

/* Wie `ladeVorschau`, bei 404 mit einem zweiten Versuch nach `VORSCHAU.nochmalMs`; `abbruch()` sagt, ob das Blatt oder die Suche inzwischen weg ist. */
async function ladeVorschauNochmal(ctx, trefferId, abbruch) {
  let r = await holeVorschau(ctx, trefferId);
  if (!r.url && r.status === 404 && !abbruch()) {
    await new Promise((res) => setTimeout(res, VORSCHAU.nochmalMs));
    if (abbruch()) return null;
    r = await holeVorschau(ctx, trefferId);
  }
  return r.url;
}

/* ------------------------------------------------------------------ Blatt „Online suchen“ und Übersicht */

/* Öffnet das Blatt.
 *   ctx            Seiten-Kontext (api, hass, melde, meldeFehler, fehlerText, neuZeichnen, schliesseBlatt, covers)
 *   serie()        die aktuelle Serie (Antwort von `serie/get`, mit `stand`, `folgen`, `cover_stand`)
 *   folge          Name der Folge, für die gesucht wird, oder null (Suche für den Eintrag)
 *   vorschlag      ein Vorschlag aus `online_vorschlaege_liste`: dann beginnt das Blatt gleich mit der Übersicht (Nr. 58 mit `vorschlag_id`)
 *   oeffne(opts)   öffnet ein Blatt wie `oeffneBlatt`
 *   neuLaden()     die Serienseite lädt neu (nach dem Übernehmen)
 *   fehler(err)    meldet einen Fehler; liefert 'zu' (Blatt schließen, die Seite lädt neu) oder 'offen'
 */
export function onlineBlatt({ ctx, serie, folge = null, vorschlag = null, oeffne, neuLaden, fehler }) {
  const s0 = serie();
  const f0 = folge ? (s0.folgen || []).find((f) => f.name === folge) : null;
  const vorgabe = f0 ? (f0.anzeige || f0.name) : s0.name;
  const Z = { phase: 'suche', text: vorgabe, geaendert: false };
  const S = { phase: 'idle', treffer: [], quellen: {}, pause: {}, fehlerCode: null, kurz: false, bilder: new Map() }; // bilder: treffer_id → blob oder null
  const U = { phase: 'laedt', felder: {}, grund: null, haken: new Set(), mehr: new Set(), laeuft: false, fehlerCode: null, quelle: null, titel: '', vorschau: null, id: null };
  const urls = new Set(); // alle blob:-Adressen dieses Blatts: beim Ersetzen und beim Schließen freigegeben
  let sucheLauf = 0;
  let ueLauf = 0;
  let zu = false; // das Blatt ist geschlossen: nichts mehr zeichnen, neu eintreffende Bilder gleich freigeben
  const frei = (u) => { if (!u) return; urls.delete(u); try { URL.revokeObjectURL?.(u); } catch { /* egal */ } };
  const merke = (u) => { if (u) urls.add(u); };

  const melde = (err) => {
    const r = fehler(err);
    return { code: err?.code || 'unknown_error', ende: r === 'zu' };
  };

  /* ---- Suche */
  const merkeBild = async (id, mein) => {
    const url = await ladeVorschauNochmal(ctx, id, () => zu || mein !== sucheLauf);
    if (zu || mein !== sucheLauf) { try { if (url) URL.revokeObjectURL?.(url); } catch { /* egal */ } return; } // zu spät: die Adresse gleich freigeben
    merke(url);
    S.bilder.set(id, url);
    ctx.neuZeichnen();
  };

  async function suche() {
    const text = Z.text.trim().slice(0, 100); // `maxlength` hilft nicht bei einem vorbelegten längeren Namen
    if (text.length < 2) { S.kurz = true; ctx.neuZeichnen(); return; } // Hinweis statt Schweigen; eine laufende Suche bleibt unberührt
    const mein = ++sucheLauf;
    S.kurz = false;
    S.phase = 'laedt'; S.fehlerCode = null;
    ctx.neuZeichnen();
    try {
      const r = await ctx.api('tobibox/online/suchen', { serie_id: serie().id, ...(folge ? { folge } : {}), ...(Z.geaendert ? { text } : {}) });
      if (mein !== sucheLauf) return;
      S.treffer = r.treffer || [];
      S.quellen = r.quellen || {};
      S.phase = 'bereit';
      S.pause = {};
      for (const u of S.bilder.values()) frei(u); // die Bilder der älteren Suche
      S.bilder = new Map();
      S.treffer.slice(0, VORSCHAU_ANZAHL).filter((t) => t.hat_cover).forEach((t) => merkeBild(t.treffer_id, mein));
      if (Object.values(S.quellen).includes('pause')) { // „Apple braucht eine Pause, bis 14:20.“: die Zeit steht in Nr. 63
        ctx.api('tobibox/online/status').then((st) => {
          if (mein !== sucheLauf) return;
          for (const q of ['itunes', 'tonies']) if (S.quellen[q] === 'pause') S.pause[q] = uhrzeit(st?.quellen?.[q]?.pause_bis, ctx.hass?.config?.time_zone);
          ctx.neuZeichnen();
        }).catch(() => {});
      }
    } catch (err) {
      if (mein !== sucheLauf) return;
      if (err?.code === 'online_nicht_erreichbar') { S.phase = 'keine'; ctx.neuZeichnen(); return; } // O9: Satz im Blatt, kein Fehlerton
      const m = melde(err);
      if (m.ende) { ctx.schliesseBlatt('code'); return; }
      S.phase = 'fehler'; S.fehlerCode = m.code;
    }
    ctx.neuZeichnen();
  }

  /* ---- Übersicht */
  async function uebersicht(quelle, titel) {
    const mein = ++ueLauf;
    Z.phase = 'uebersicht';
    const altesBild = U.vorschau;
    Object.assign(U, { phase: 'laedt', felder: {}, grund: null, haken: new Set(), mehr: new Set(), laeuft: false, fehlerCode: null, quelle, titel, vorschau: null, vorschauLaedt: false, vorschauWeg: false, id: null });
    ctx.neuZeichnen();
    frei(altesBild);
    ctx.blattFokus?.();
    try {
      const r = await ctx.api('tobibox/online/treffer', quelle.treffer_id ? { treffer_id: quelle.treffer_id } : { serie_id: serie().id, vorschlag_id: quelle.vorschlag_id });
      if (mein !== ueLauf) return;
      U.felder = r.felder || {};
      U.grund = r.grund ?? null;
      U.haken = vorauswahl(U.felder);
      U.phase = 'bereit';
      const bildId = quelle.treffer_id || (typeof r.vorschau_id === 'string' && r.vorschau_id) || null; // Treffer: seine Kennung; Vorschlag mit Cover: `vorschau_id` aus Nr. 58 (T10)
      if (U.felder.cover && bildId) { // das neue Bild: Vorschau (nach Nr. 58 hat HA es geladen); 410/Fehler: es bleibt beim Platzhalter
        if (!quelle.treffer_id) U.vorschauLaedt = true;
        ladeVorschauNochmal(ctx, bildId, () => zu || mein !== ueLauf).then((url) => {
          if (zu || mein !== ueLauf) { try { if (url) URL.revokeObjectURL?.(url); } catch { /* egal */ } return; }
          merke(url); U.vorschau = url; U.vorschauLaedt = false; U.vorschauWeg = !url && !quelle.treffer_id; ctx.neuZeichnen();
        });
      }
    } catch (err) {
      if (mein !== ueLauf) return;
      const m = melde(err);
      if (m.ende) { ctx.schliesseBlatt('code'); return; }
      if (m.code === 'treffer_abgelaufen') { zurueckZurSuche(); return; } // „Die Suche ist zu alt. Such bitte noch einmal.“
      U.phase = 'fehler'; U.fehlerCode = m.code;
    }
    ctx.neuZeichnen();
  }

  function zurueckZurSuche() {
    ueLauf += 1;
    Z.phase = 'suche';
    if (vorschlag) { ctx.schliesseBlatt('code'); return; }
    S.phase = 'idle'; S.treffer = []; // die Treffer sind abgelaufen: neue Suche
    ctx.neuZeichnen();
    ctx.blattFokus?.();
  }

  const ordnung = () => sortiereFelder(Object.keys(U.felder), serie().folgen || []);

  async function uebernehmen() {
    if (U.laeuft || U.phase !== 'bereit') return false;
    const felder = ordnung().filter((k) => U.haken.has(k));
    if (!felder.length) return false;
    U.laeuft = true;
    ctx.neuZeichnen();
    try {
      const s = serie();
      if (U.id?.key !== felder.join('|')) U.id = { key: felder.join('|'), id: anfrageId() }; // dieselbe Wahl noch einmal: dieselbe `anfrage_id`
      await ctx.api('tobibox/online/uebernehmen', {
        serie_id: s.id, ...(U.quelle.treffer_id ? { treffer_id: U.quelle.treffer_id } : { vorschlag_id: U.quelle.vorschlag_id }),
        felder, stand: s.stand, anfrage_id: U.id.id,
      });
      ctx.melde(felder.length === 1 && felder[0] === 'serie_name' ? ONLINE.uebersicht.fertig_name : ONLINE.uebersicht.fertig);
      await neuLaden();
      return undefined;
    } catch (err) {
      const m = melde(err);
      if (m.ende) return undefined;
      if (m.code === 'treffer_abgelaufen') { zurueckZurSuche(); return false; }
      return false;
    } finally { U.laeuft = false; ctx.neuZeichnen(); }
  }

  /* ---- Darstellung */
  const hinweisQuellen = () => {
    const aus = [];
    for (const q of ['itunes', 'tonies']) {
      const st = S.quellen[q];
      if (st === 'ok' || st === undefined) continue;
      const anderer = q === 'itunes' ? 'tonies' : 'itunes';
      const w = { quelle: quellenName(q), andere: quellenName(anderer) };
      const nur = S.quellen[anderer] === 'ok'; // „Das sind nur Treffer von …“ nur, wenn die andere Quelle antwortet
      let text;
      if (st === 'pause') text = S.pause[q] ? fuellen(ONLINE.suche.quelle_pause_bis, { ...w, uhr_bis: S.pause[q] }) + (nur ? ` ${fuellen(ONLINE.suche.nur_treffer, w)}` : '') : fuellen(nur ? ONLINE.suche.quelle_pause : ONLINE.suche.quelle_pause_allein, w);
      else text = fuellen(nur ? ONLINE.suche.quelle_aus : ONLINE.suche.quelle_aus_allein, w);
      aus.push(html`<p class="os-quelle" data-quelle-hinweis=${q} role="status">${text}</p>`);
    }
    return aus;
  };

  const bild = (t) => {
    const url = S.bilder.get(t.treffer_id);
    return url ? html`<img class="os-bild" data-vorschau=${t.treffer_id} src=${url} alt="">`
      : html`<span class=${`cover sm ${coverKlasse(t.treffer_id)}`} data-vorschau-ohne aria-hidden="true"><span class="bst">${String(t.titel ?? '?').trim().charAt(0).toUpperCase() || '?'}</span></span>`;
  };

  const trefferZeile = (t) => {
    const teile = [t.reihe, t.nummer != null ? fuellen(ONLINE.suche.nummer, { nr: t.nummer }) : null, t.tracks != null ? zaehle(ONLINE.suche.tracks, t.tracks) : null].filter(Boolean);
    const aria = [fuellen(ONLINE.suche.waehlen, { titel: t.titel }), ...teile, quellenName(t.quelle), ...(t.frueher_abgelehnt === true ? [ONLINE.suche.frueher] : [])].join(', '); // der Name ersetzt den Inhalt der Zeile: alles Wichtige gehört hinein
    return html`<button type="button" class="os-treffer" data-treffer=${t.treffer_id} aria-label=${aria} @click=${() => uebersicht({ treffer_id: t.treffer_id }, t.titel)}>
      ${bild(t)}<span class="grow"><span class="nm">${t.titel}</span>${teile.length ? html`<span class="muted">${teile.join(' · ')}</span>` : nothing}
        <span class="os-marken"><span class="os-marke" data-marke="quelle">${quellenName(t.quelle)}</span>${t.frueher_abgelehnt === true ? html`<span class="os-marke warn" data-marke="frueher">${ONLINE.suche.frueher}</span>` : nothing}</span></span>
      <span class="os-chev" aria-hidden="true">${ic('chev', 24)}</span></button>`;
  };

  const sucheInhalt = () => {
    let liste;
    if (S.phase === 'laedt') liste = html`<p class="muted os-status" role="status" data-suche-status="laedt">${ONLINE.suche.laeuft}</p>`;
    else if (S.phase === 'keine') liste = html`<p class="os-status" role="status" data-suche-status="keine">${ONLINE.suche.keine_quelle}</p>`;
    else if (S.phase === 'fehler') liste = ctx.fehlerKarte(S.fehlerCode, () => suche());
    else if (S.phase === 'bereit') {
      liste = html`${hinweisQuellen()}${S.treffer.length ? html`<div class="os-liste" data-treffer-liste>${S.treffer.map(trefferZeile)}</div>`
        : html`<p class="muted os-status" role="status" data-suche-status="nichts">${ONLINE.suche.nichts}</p>`}`;
    } else liste = nothing;
    if (S.kurz) liste = html`<p class="muted os-status" role="status" data-suche-status="kurz">${ONLINE.suche.zu_kurz}</p>${liste}`;
    return html`<form class="os-suchzeile" @submit=${(e) => { e.preventDefault(); suche(); }}>
        <label class="sr" for="os-text">${ONLINE.suche.label}</label>
        <input id="os-text" class="se-sfeld os-feld-text" type="search" autocomplete="off" maxlength="100" data-os-text .value=${Z.text}
          @input=${(e) => { Z.text = e.target.value; Z.geaendert = Z.text.trim() !== vorgabe.trim(); }}>
        <button type="submit" class="btn primary" data-os-suchen ?disabled=${S.phase === 'laedt'}>${ONLINE.suche.knopf}</button></form>
      ${liste}`;
  };

  const feldZeile = (key) => {
    const w = U.felder[key];
    const [feld, fname] = teileKey(key);
    const an = U.haken.has(key);
    const f = fname ? (serie().folgen || []).find((x) => x.name === fname) : null;
    const wechsel = () => { if (an) U.haken.delete(key); else U.haken.add(key); ctx.neuZeichnen(); };
    let werte;
    if (feld === 'cover') {
      const s = serie();
      const heute = w.heute ? cover(s, 'sm') : html`<span class=${`cover sm ${coverKlasse(s.id)}`} data-cover-ohne aria-hidden="true"><span class="bst">${String(s.name ?? '?').trim().charAt(0).toUpperCase() || '?'}</span></span>`;
      const neu = U.vorschau ? html`<img class="os-bild" data-vorschau-neu src=${U.vorschau} alt="">`
        : html`<span class=${`cover sm ${coverKlasse(U.titel || key)}`} data-vorschau-neu-ohne aria-hidden="true"><span class="bst">${ic('plus', 22)}</span></span>`;
      const ohneBild = !U.vorschau && !U.vorschauLaedt && !U.quelle?.treffer_id; // ein Vorschlag ohne (oder mit abgelaufener) `vorschau_id` hat kein Bild: der beschriftete Platzhalter
      werte = html`<span class="os-cover" data-wert="cover"><span class="os-cv"><span class="sr">${ONLINE.uebersicht.cover_heute}</span>${heute}</span> <span class="os-pfeil" aria-hidden="true">→</span> <span class="os-cv"><span class="sr">${ONLINE.uebersicht.cover_neu}</span>${neu}</span></span>${ohneBild ? html`<span class="muted os-cover-hinweis" data-cover-ohne-bild>${U.vorschauWeg ? ONLINE.uebersicht.cover_vorschau_weg : ONLINE.uebersicht.cover_ohne_bild}</span>` : nothing}`;
    } else {
      const kurz = feld === 'beschreibung' && !U.mehr.has(key);
      const t = (v) => { const x = wertText(feld, v); if (x === null) return html`<em class="muted">${ONLINE.uebersicht.leer}</em>`; return kurz ? kuerzen(x) : x; };
      werte = html`<span class="os-werte" data-wert=${feld}><span class="os-heute"><span class="sr">${ONLINE.uebersicht.heute}: </span>${t(w.heute)}</span> <span class="os-pfeil" aria-hidden="true">→</span> <span class="os-neu"><span class="sr">${ONLINE.uebersicht.neu}: </span>${t(w.neu)}</span></span>`;
    }
    const langerText = feld === 'beschreibung' && (String(w.neu ?? '').length > BESCHREIBUNG_KURZ || String(w.heute ?? '').length > BESCHREIBUNG_KURZ);
    return html`<div class="os-feldzeile" data-feldzeile=${key}>
      <button type="button" class="os-feld" role="checkbox" aria-checked=${an ? 'true' : 'false'} data-feld=${key} ?disabled=${U.laeuft} @click=${wechsel}>
        <span class="os-haken" aria-hidden="true">${an ? ic('check', 20) : nothing}</span>
        <span class="os-ftext"><span class="os-fname">${ONLINE.feld[feld] ?? feld}${f && feld !== 'folge_titel' ? html`<span class="muted os-ffolge"> · ${fuellen(ONLINE.uebersicht.folge_von, { folge: f.anzeige || f.name })}</span>` : nothing}</span>
          ${werte}${w.hand ? html`<span class="os-hand" data-hand>${ONLINE.uebersicht.hand}</span>` : nothing}</span></button>
      ${langerText ? html`<button type="button" class="os-link" data-feld-mehr=${key} aria-expanded=${U.mehr.has(key) ? 'true' : 'false'} @click=${() => { if (U.mehr.has(key)) U.mehr.delete(key); else U.mehr.add(key); ctx.neuZeichnen(); }}>${U.mehr.has(key) ? ONLINE.uebersicht.weniger : ONLINE.uebersicht.mehr}</button>` : nothing}</div>`;
  };

  const uebersichtInhalt = () => {
    if (U.phase === 'laedt') return html`<p class="muted os-status" role="status">${SEITE.laedt}</p>`;
    if (U.phase === 'fehler') return ctx.fehlerKarte(U.fehlerCode, () => uebersicht(U.quelle, U.titel));
    const keys = ordnung();
    if (!keys.length) return html`<p class="muted os-status" role="status" data-alles-gleich>${ONLINE.uebersicht.alles_gleich}</p>`;
    return html`${U.titel ? html`<p class="os-titel" data-treffer-titel>${U.titel}</p>` : nothing}
      ${U.grund ? html`<p class="os-grund" data-grund>${fuellen(ONLINE.uebersicht.grund, { grund: U.grund })}</p>` : nothing}
      <div class="os-felder" role="group" aria-label=${ONLINE.uebersicht.titel} data-felder>${keys.map(feldZeile)}</div>`;
  };

  const inhalt = () => (Z.phase === 'suche' ? sucheInhalt() : uebersichtInhalt());
  const titel = () => (Z.phase === 'suche' ? ONLINE.suche.titel : ONLINE.uebersicht.titel);
  const knoepfe = () => {
    if (Z.phase === 'suche') return [{ label: ONLINE.suche.schliessen }];
    const zurueck = vorschlag
      ? { label: SERIE.abbrechen }
      : { label: ONLINE.uebersicht.zurueck, fn: () => { ueLauf += 1; Z.phase = 'suche'; ctx.neuZeichnen(); ctx.blattFokus?.(); return false; } };
    const gehtNicht = U.phase !== 'bereit' || U.laeuft || !U.haken.size;
    return [zurueck, { label: ONLINE.uebersicht.uebernehmen, kind: 'primary', aus: gehtNicht, fn: uebernehmen }];
  };

  if (vorschlag) uebersicht({ vorschlag_id: vorschlag.id }, '');
  else suche();
  const p = oeffne({ titel, inhalt, knoepfe, fokus: 'titel' }); // Fokus auf die Überschrift: im Suchfeld löscht Esc nur den Text, statt das Blatt zu schließen
  p.then(() => { zu = true; sucheLauf += 1; ueLauf += 1; for (const u of [...urls]) frei(u); });
  return p;
}

/* ------------------------------------------------------------------ Blatt „Zurücknehmen?“ */

/* Kopf der Serienseite: „Zurücknehmen“ (Befehl 60, Form `serie_id`: alle Online-Änderungen des Eintrags). Das Blatt sagt ehrlich: alle Online-Änderungen dieses Eintrags gehen zurück; genannt wird nur die letzte (GO4-3). */
export function zuruecknehmenBlatt({ ctx, serie, oeffne, neuLaden, fehler }) {
  const s = serie();
  const felder = feldListe(s.online?.felder);
  let laeuft = false;
  const ok = async () => {
    if (laeuft) return false;
    laeuft = true;
    try {
      const r = await ctx.api('tobibox/online/zuruecknehmen', { serie_id: s.id });
      const n = r?.uebersprungen_anzahl ?? (r?.uebersprungen || []).length;
      ctx.melde(n > 0 ? zaehle(ONLINE.zuruecknehmen.uebersprungen, n) : ONLINE.zuruecknehmen.fertig);
      await neuLaden();
      return undefined;
    } catch (err) { return fehler(err) === 'zu' ? undefined : false; } finally { laeuft = false; }
  };
  return oeffne({
    titel: ONLINE.zuruecknehmen.titel,
    rolle: 'alertdialog',
    inhalt: html`<p data-zuruecknehmen-felder>${fuellen(ONLINE.zuruecknehmen.text, { felder })}</p>`,
    knoepfe: [{ label: SERIE.abbrechen }, { label: ONLINE.zuruecknehmen.knopf, kind: 'primary', fn: ok }],
  });
}

/* ------------------------------------------------------------------ Teile der Serienseite */

/* Zeile im Kopf (alle Benutzer, R1): „Aus der Online-Suche übernommen: Cover, Art.“ mit „Zurücknehmen“ (Administratoren mit Fähigkeit) oder dem Satz für alle anderen. */
export function hinweisZeile(ctx, s, onZurueck) {
  const o = s?.online;
  const liste = feldListe(o?.felder);
  if (!o || !liste) return nothing;
  const admin = ctx.admin === true && ctx.faehig('online_suche');
  return html`<div class="muted os-hinweis" data-online-hinweis><span data-online-text>${fuellen(ONLINE.hinweis.zeile, { felder: liste })}</span>
    ${admin ? html`<button type="button" class="os-link" data-online-zurueck aria-haspopup="dialog" @click=${(e) => onZurueck(e.currentTarget)}>${ONLINE.hinweis.zurueck}</button>`
    : html`<span data-online-frag>${ONLINE.hinweis.frag}</span>`}</div>`;
}

/* Zeilen der Vorschläge in der Karte „bitte ansehen“ (nur Administratoren). `aktionen`: { ansehen(v, el), uebernehmen(v, el), zusammen(v, el), nein(v, el) }. */
export function vorschlagZeilen(ctx, liste, ziele, aktionen, { gesperrt = false } = {}) {
  return html`<div class="os-vorschlaege" data-vorschlaege>${liste.map((v) => {
    const text = vorschlagText(v, ziele);
    const name = istNamensvorschlag(v);
    const zus = v.art === 'zusammenfuehren';
    const knopf = (label, aktion, aria, fn, primaer = false) => html`<button type="button" class=${primaer ? 'btn primary' : 'btn'} data-vorschlag-aktion=${aktion} ?disabled=${gesperrt} aria-label=${fuellen(aria, { text })} @click=${(e) => fn(v, e.currentTarget)}>${label}</button>`;
    return html`<div class="os-vorschlag" data-vorschlag=${v.id} data-quelle=${v.quelle}><span class="os-vtext" data-vorschlag-text>${text}</span>
      ${name && v.grund ? html`<span class="muted os-vgrund" data-vorschlag-grund>${v.grund}</span>` : nothing}
      <div class="btns">${name ? knopf(ONLINE.vorschlag.uebernehmen, 'uebernehmen', ONLINE.vorschlag.aria_uebernehmen, aktionen.uebernehmen)
    : zus ? (ctx.faehig('korrektur') ? knopf(ONLINE.vorschlag.zusammenfuehren, 'zusammen', ONLINE.vorschlag.aria_ansehen, aktionen.zusammen) : nothing)
      : knopf(ONLINE.vorschlag.ansehen, 'ansehen', ONLINE.vorschlag.aria_ansehen, aktionen.ansehen)}
        ${knopf(ONLINE.vorschlag.nein, 'nein', ONLINE.vorschlag.aria_nein, aktionen.nein)}</div></div>`;
  })}</div>`;
}

export { ENDE_FEHLER };

/* ------------------------------------------------------------------ Stil */

export function blattStil() {
  return css`
  .os-hinweis { display: flex; flex-wrap: wrap; align-items: center; gap: 0 8px; }
  .os-link { min-height: 44px; padding: 0 8px; border: 0; background: none; color: var(--primary-ink); font: inherit; font-weight: 500; border-radius: 8px; cursor: pointer; text-align: left; }
  .os-link:focus-visible, .os-knopf:focus-visible, .os-feld:focus-visible, .os-treffer:focus-visible { outline: 3px solid var(--focus); outline-offset: -3px; }
  .os-suchzeile { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; align-items: center; margin: 4px 0 8px; }
  .os-suchzeile .se-sfeld { margin: 0; }
  .os-status { padding: 12px 4px; margin: 0; }
  .os-quelle { margin: 4px 0 8px; padding: 8px 12px; border-radius: 12px; background: var(--warn-bg); color: var(--warn); font-size: 14px; }
  .os-liste { display: grid; margin-top: 4px; }
  .os-treffer { width: 100%; min-height: 64px; display: flex; align-items: center; gap: 12px; padding: 8px 0; border: 0; border-top: 1px solid var(--divider); background: none; text-align: left; color: inherit; font: inherit; }
  .os-treffer:first-child { border-top: 0; }
  .os-treffer:active { background: var(--primary-soft); }
  .os-treffer .grow { flex: 1; min-width: 0; display: grid; gap: 1px; overflow-wrap: anywhere; }
  .os-treffer .nm { font-weight: 500; }
  .os-bild { width: 48px; height: 48px; border-radius: 10px; object-fit: cover; flex: none; display: block; background: var(--divider); }
  .os-chev { flex: none; width: 24px; height: 24px; display: grid; place-items: center; color: var(--text2); }
  .os-chev svg { width: 24px; height: 24px; fill: currentColor; display: block; }
  .os-marken { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px; }
  .os-marke { display: inline-block; font-size: 13px; font-weight: 500; padding: 2px 10px; border-radius: 12px; background: var(--primary-soft); color: var(--primary-ink); }
  .os-marke.warn { background: var(--warn-bg); color: var(--warn); }
  .os-titel { margin: 4px 0 8px; font-weight: 500; overflow-wrap: anywhere; }
  .os-grund { margin: 0 0 8px; overflow-wrap: anywhere; }
  .os-felder { display: grid; gap: 8px; }
  .os-feldzeile { display: grid; gap: 0; }
  .os-feld { width: 100%; min-height: 56px; display: flex; align-items: flex-start; gap: 12px; padding: 10px 14px; border: 1px solid var(--line); border-radius: var(--r-card); background: var(--card); color: inherit; font: inherit; text-align: left; }
  .os-feld[aria-checked="true"] { background: var(--primary-soft); border-color: var(--primary-ink); }
  .os-feld:disabled { opacity: 0.6; }
  .os-haken { flex: none; width: 24px; height: 24px; margin-top: 1px; border: 2px solid var(--text2); border-radius: 6px; display: grid; place-items: center; color: var(--primary-ink); box-sizing: border-box; }
  .os-feld[aria-checked="true"] .os-haken { border-color: var(--primary-ink); }
  .os-haken svg { width: 20px; height: 20px; fill: currentColor; }
  .os-ftext { min-width: 0; display: grid; gap: 3px; flex: 1; }
  .os-fname { font-weight: 500; }
  .os-werte, .os-cover { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; overflow-wrap: anywhere; }
  .os-heute { color: var(--text2); }
  .os-neu { font-weight: 500; }
  .os-pfeil { color: var(--text2); }
  .os-cv { display: inline-flex; }
  .os-cv .cover.sm, .os-cv .os-bild { width: 48px; height: 48px; }
  .os-hand { display: inline-block; justify-self: start; font-size: 13px; font-weight: 500; padding: 2px 10px; border-radius: 12px; background: var(--warn-bg); color: var(--warn); }
  .os-feldzeile .os-link { justify-self: start; margin-left: 38px; }
  .os-vorschlaege { display: grid; gap: 12px; margin-top: 12px; padding-top: 8px; border-top: 1px solid var(--divider); }
  .os-vorschlag { display: grid; gap: 2px; }
  .os-vtext { font-weight: 500; overflow-wrap: anywhere; }
  .os-vgrund { overflow-wrap: anywhere; }
  .os-cover-hinweis { font-size: 14px; overflow-wrap: anywhere; }
  .os-alter { display: block; font-variant-numeric: tabular-nums; }
  .os-knopf { display: inline-flex; align-items: center; gap: 4px; min-height: 44px; padding: 0 8px 0 0; border: 0; background: none; color: var(--primary-ink); font: inherit; font-weight: 500; cursor: pointer; border-radius: 8px; justify-self: start; pointer-events: auto; }
  .os-knopf svg { width: 20px; height: 20px; fill: currentColor; transition: transform var(--dauer-kurz) var(--kurve); }
  .os-knopf[aria-expanded="true"] svg { transform: rotate(180deg); }
  .os-text { margin: 2px 0 6px; overflow-wrap: anywhere; pointer-events: auto; user-select: text; }
  .os-quellen { display: block; font-size: 13px; color: var(--text2); pointer-events: auto; }
  .os-einzel { display: grid; gap: 2px; margin: 0 0 12px; }
  `;
}

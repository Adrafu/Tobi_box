/* Seite „Technik“ (Design 5.9, 9, 10; Pakete A12/A13): nur für Administratoren, sechs Unterseiten.
 *
 * Routen (parseRoute in tobibox-app.js): `#technik` (Liste), `#technik-boxen`, `#technik-box-<id>`, `#technik-speicher`,
 * `#technik-liste`, `#technik-tobies`, `#technik-meldungen`, `#technik-einstellungen`. Eine unbekannte Unterseite zeigt die Liste.
 * Wer kein Administrator ist, sieht die Sperre; das Gerüst (tobibox-app.js `_seite`) fängt es ab, diese Seite wird dann nie betreten.
 *
 * Die alte Komponente `tobibox-panel` (Datei tobibox-panel.js) wird eingebettet: `<tobibox-panel eingebettet bereich="…">`
 * zeigt ohne Kopf und Reiterleiste nur ihren Bereich (PANEL_BEREICHE unten sagt, welcher Bereich auf welche Unterseite kommt).
 * Neu und nur hier: Warnleisten zur Liste mit Entscheidung, „Frühere Stände ansehen“, „Medien neu einlesen“, „Cover neu suchen“,
 * „Hörkopien neu erzeugen“ und der Papierkorb mit „gelöscht von“, „Letzte Stunde zurückholen“ und „Leeren“.
 * Schnittstelle zur App: siehe bausteine.js. Befehle: docs/protocol/ha-websocket-v1.md (Nr. 9, 10 bis 12, 21, 23, 31 bis 34, 44 bis 46).
 */
import { groesse, zeitKurz } from '../tobibox-panel.js'; // lädt auch die Komponente <tobibox-panel>; ohne DOM harmlos
import { html, nothing, css, ic, ladeMitGrenze, zaehle } from '../bausteine.js';
import { TECHNIK, SEITE, LEER, fuellen } from '../texte.js';

export const UNTERSEITEN = ['boxen', 'speicher', 'liste', 'tobies', 'meldungen', 'einstellungen'];

/* Bereiche der alten Komponente je Unterseite (Attribut `bereich`). `box` ist die Seite einer einzelnen Box. */
export const PANEL_BEREICHE = {
  boxen: ['boxen'], box: ['boxen'], speicher: ['aufraeumen', 'eingang'], liste: ['liste'], tobies: ['tobies'], meldungen: ['meldungen'], einstellungen: ['einstellungen'],
};

const KORB_SEITE = 100;

const anfrageId = () => (globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : `a${Math.random().toString(16).slice(2)}${Date.now().toString(16)}`);
const boxName = (b) => b.anzeige || b.anzeigename || b.box;

/* Welche Unterseite zeigt die Adresse? `route` ist das Ergebnis von parseRoute: { sub, id }. Gibt null für die Liste. */
export function unterseite(route) {
  const sub = route?.sub;
  if (typeof sub === 'string' && sub.startsWith('box-') && route.id != null) return 'box';
  return UNTERSEITEN.includes(sub) ? sub : null;
}

class TechnikSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.route = null;
    this.b = { phase: 'laedt', fehlerCode: null, konfig: null, boxen: [] };
    this.korb = { phase: 'laedt', fehlerCode: null, eintraege: [], gesamt: 0, bytes: 0, ladeMehr: false };
    this.staende = { phase: 'laedt', fehlerCode: null, liste: [] };
    this.beschaeftigt = null; // Name der laufenden Aktion; sperrt ihren Knopf
    this._lauf = 0;
  }

  betreten(route) {
    this.route = route;
    const sub = unterseite(route);
    this.ladeBasis();
    if (sub === 'speicher') this.ladeKorb();
    if (sub === 'liste' && this.ctx.faehig('konfig_staende')) this.ladeStaende();
  }
  neuLaden() { if (this.route) this.betreten(this.route); }
  verlassen() { this._lauf += 1; }

  /* ---- Daten */
  async ladeBasis() {
    const { ctx } = this;
    const lauf = this._lauf;
    const konfig = ctx.faehig('konfig_lesen') ? ctx.api('tobibox/konfig/get').then((r) => r.konfig) : ctx.api('tobibox/hello', { v: 1 }).then((r) => r.konfig);
    const boxen = ctx.faehig('boxen') ? ctx.api('tobibox/boxen/list').then((r) => r.boxen || []) : Promise.resolve([]);
    if (this.b.phase !== 'bereit') { this.b = { ...this.b, phase: 'laedt', fehlerCode: null }; ctx.neuZeichnen(); }
    const [k, bx] = await Promise.allSettled([ladeMitGrenze(konfig, ctx.grenzeMs), ladeMitGrenze(boxen, ctx.grenzeMs)]);
    if (lauf !== this._lauf) return;
    if (k.status === 'rejected' && bx.status === 'rejected') this.b = { ...this.b, phase: 'fehler', fehlerCode: bx.reason?.code || 'unknown_error' };
    else this.b = { phase: 'bereit', fehlerCode: null, konfig: k.status === 'fulfilled' ? k.value : this.b.konfig, boxen: bx.status === 'fulfilled' ? bx.value : this.b.boxen };
    ctx.neuZeichnen();
  }

  async ladeKorb(offset = 0) {
    const { ctx } = this;
    const lauf = this._lauf;
    if (!offset && this.korb.phase !== 'bereit') { this.korb = { ...this.korb, phase: 'laedt', fehlerCode: null }; ctx.neuZeichnen(); }
    try {
      const r = await ladeMitGrenze(ctx.api('tobibox/papierkorb/list', { limit: KORB_SEITE, offset }), ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.korb = { phase: 'bereit', fehlerCode: null, ladeMehr: false, eintraege: offset ? [...this.korb.eintraege, ...(r.eintraege || [])] : (r.eintraege || []), gesamt: r.gesamt ?? 0, bytes: r.gesamt_bytes ?? 0 };
    } catch (e) {
      if (lauf !== this._lauf) return;
      this.korb = { ...this.korb, phase: 'fehler', fehlerCode: e?.code || 'unknown_error', ladeMehr: false };
    }
    ctx.neuZeichnen();
  }

  async ladeStaende() {
    const { ctx } = this;
    const lauf = this._lauf;
    try {
      const r = await ladeMitGrenze(ctx.api('tobibox/konfig/export_lesen'), ctx.grenzeMs);
      if (lauf !== this._lauf) return;
      this.staende = { phase: 'bereit', fehlerCode: null, liste: r.staende || [] };
    } catch (e) {
      if (lauf !== this._lauf) return;
      this.staende = { phase: 'fehler', fehlerCode: e?.code || 'unknown_error', liste: [] };
    }
    ctx.neuZeichnen();
  }

  /* ---- Aktionen */
  /* Ja/Nein im Blatt; löst mit true bei „Ja“ auf. */
  bestaetige({ titel, text, ja, gefahr = true }) {
    return new Promise((fertig) => {
      let gewaehlt = false;
      this.ctx.oeffneBlatt({
        titel,
        inhalt: html`<p>${text}</p>`,
        knoepfe: [
          { label: ja, kind: gefahr ? 'danger' : 'primary', fn: () => { gewaehlt = true; } },
          { label: TECHNIK.abbrechen },
        ],
      }).then(() => fertig(gewaehlt));
    });
  }

  /* Führt `fn` aus und meldet Fehler in Worten; `name` sperrt den Knopf, solange es läuft. Gibt true bei Erfolg. */
  async tu(name, fn) {
    if (this.beschaeftigt) return false;
    this.beschaeftigt = name;
    this.ctx.neuZeichnen();
    try { await fn(); return true; } catch (e) {
      this.ctx.meldeFehler(this.ctx.fehlerText(e?.code));
      return false;
    } finally {
      this.beschaeftigt = null;
      this.ctx.neuZeichnen();
    }
  }

  async nachListeAenderung() {
    await this.ladeBasis();
    if (unterseite(this.route) === 'liste' && this.ctx.faehig('konfig_staende')) await this.ladeStaende();
  }

  /* Export ansehen und holen. `stand`: ein früherer Stand (1 ist der jüngste); ohne: der neueste Export. */
  async exportBlatt(stand = null) {
    const { ctx } = this;
    const T = TECHNIK.liste;
    let r;
    const gelesen = await this.tu('export_lesen', async () => { r = await ctx.api('tobibox/konfig/export_lesen', stand ? { stand } : {}); });
    if (!gelesen) return;
    if (!r.vorhanden) { ctx.meldeFehler(T.export_keiner); return; }
    const zeile = fuellen(T.export_zeile, { revision: r.revision ?? '–', zeit: zeitKurz(r.exportiert_am) || '–', zuordnungen: zaehle(TECHNIK.zuordnungen, r.anzahl_zuordnungen ?? 0) });
    const fenster = typeof r.anzahl_fenster === 'number' ? ` ${zaehle(T.staende.fenster, r.anzahl_fenster)}.` : '';
    const ja = await this.bestaetige({
      titel: stand ? fuellen(T.staende.zurueck_titel, { nr: stand }) : T.export_titel,
      text: stand ? `${zeile}${fenster} ${T.staende.zurueck_text}` : `${zeile}${fenster}`,
      ja: stand ? T.staende.zurueck : T.export_ja,
    });
    if (!ja) return;
    const ok = await this.tu('aus_export', async () => {
      await ctx.api('tobibox/konfig/aus_export', { bestaetigt: true, anfrage_id: anfrageId(), ...(stand ? { stand } : {}) });
    });
    if (!ok) return;
    ctx.melde(stand ? fuellen(T.staende.gemacht, { nr: stand }) : T.erledigt);
    await this.nachListeAenderung();
  }

  async neuAusrollen(grund) {
    const { ctx } = this;
    const T = TECHNIK.liste;
    const ja = await this.bestaetige({ titel: T.neu_titel, text: grund === 'leer_neu' ? T.neu_leer : (grund === 'export_neuer' ? T.neu_behalten : T.neu_ausrollen), ja: T.neu_ja });
    if (!ja) return;
    const ok = await this.tu('neu_ausrollen', async () => { await ctx.api('tobibox/liste/neu_ausrollen', { bestaetigt: true, anfrage_id: anfrageId() }); });
    if (!ok) return;
    ctx.melde(T.erledigt);
    await this.nachListeAenderung();
  }

  async einlesen() {
    const { ctx } = this;
    const T = TECHNIK.aufraeumen;
    let r;
    if (await this.tu('einlesen', async () => { r = await ctx.api('tobibox/medien/pruefen'); })) ctx.melde(r?.laeuft_bereits ? T.einlesen_laeuft : T.einlesen_gemacht);
  }

  async coverNeuSuchen() {
    const { ctx } = this;
    const T = TECHNIK.aufraeumen;
    if (!await this.bestaetige({ titel: T.cover_titel, text: T.cover_text, ja: T.cover_ja, gefahr: false })) return;
    if (await this.tu('cover', async () => { await ctx.api('tobibox/cover/neu_suchen'); })) ctx.melde(T.cover_gemacht);
  }

  async hoerkopienNeu() {
    const { ctx } = this;
    const T = TECHNIK.aufraeumen;
    let r;
    if (await this.tu('hoerkopien', async () => { r = await ctx.api('tobibox/hoerkopie/neu_erzeugen'); })) ctx.melde(zaehle(T.hoerkopien_gemacht, r?.eingereiht ?? 0));
  }

  async korbStelleHer(e, serieId = null) {
    const { ctx } = this;
    const T = TECHNIK.korb;
    if (this.beschaeftigt) return;
    this.beschaeftigt = 'korb';
    ctx.neuZeichnen();
    let fehler = null;
    try { await ctx.api('tobibox/papierkorb/restore', { eintrag_id: e.id, ...(serieId ? { serie_id: serieId } : {}) }); } catch (err) { fehler = err || {}; } finally {
      this.beschaeftigt = null;
      ctx.neuZeichnen();
    }
    if (!fehler) { ctx.melde(fuellen(T.wieder_da, { name: e.anzeige })); await this.ladeKorb(); return; }
    if (fehler.code === 'serie_nicht_gefunden' && e.typ === 'folge' && !serieId) { // Serie weg: ein anderes Hörspiel wählen (Vertrag, Nr. 11)
      const serie = await this.waehleSerie();
      if (serie) await this.korbStelleHer(e, serie);
      return;
    }
    ctx.meldeFehler(ctx.fehlerText(fehler.code));
    if (fehler.code === 'eintrag_nicht_gefunden') await this.ladeKorb();
  }

  async waehleSerie() {
    const { ctx } = this;
    const T = TECHNIK.korb;
    let serien = [];
    if (!await this.tu('serien', async () => { serien = ((await ctx.api('tobibox/serien/list', { limit: 200 })).serien || []).filter((s) => s.typ !== 'ueberraschung'); })) return null;
    return new Promise((fertig) => {
      let gewaehlt = null;
      ctx.oeffneBlatt({
        titel: T.serie_waehlen,
        inhalt: html`<p>${T.serie_text}</p><div class="tstapel">${serien.map((s) => html`
          <button type="button" class="tzeile" data-serie=${s.id} @click=${() => { gewaehlt = s.id; ctx.schliesseBlatt('knopf'); }}><span class="tz-t"><strong>${s.name}</strong></span></button>`)}</div>`,
        knoepfe: [{ label: TECHNIK.abbrechen }],
      }).then(() => fertig(gewaehlt));
    });
  }

  async korbLetzteStunde() {
    const { ctx } = this;
    const T = TECHNIK.korb;
    if (!await this.bestaetige({ titel: T.letzte_stunde_titel, text: T.letzte_stunde_text, ja: T.letzte_stunde_ja, gefahr: false })) return;
    let r;
    if (!await this.tu('letzte_stunde', async () => { r = await ctx.api('tobibox/papierkorb/restore_letzte_stunde', { bestaetigt: true }); })) return;
    const n = r?.wiederhergestellt ?? 0;
    const uebrig = (r?.uebersprungen || []).length;
    if (n) ctx.melde(zaehle(T.letzte_stunde_gemacht, n));
    else if (!uebrig) ctx.melde(T.letzte_stunde_nichts);
    if (uebrig) ctx.meldeFehler(zaehle(T.uebersprungen, uebrig));
    await this.ladeKorb();
  }

  async korbLeeren() {
    const { ctx } = this;
    const T = TECHNIK.korb;
    const k = this.korb;
    const ja = await this.bestaetige({ titel: T.leeren_titel, text: fuellen(T.leeren_text, { anzahl: zaehle(T.anzahl, k.gesamt), groesse: groesse(k.bytes) }), ja: T.leeren_ja });
    if (!ja) return;
    if (await this.tu('leeren', async () => { await ctx.api('tobibox/papierkorb/empty', { bestaetigt: true }); })) ctx.melde(T.geleert);
    await this.ladeKorb();
  }

  /* ---- Darstellung */
  _panel(bereich, box = null) {
    return html`<div class="alt" data-alt=${bereich}><tobibox-panel eingebettet bereich=${bereich} box=${box ?? nothing} .hass=${this.ctx.hass}></tobibox-panel></div>`;
  }

  _zeile(href, titel, zeile) {
    return html`<a class="tzeile" href=${href}><span class="tz-t"><strong>${titel}</strong><span class="muted">${zeile}</span></span>${ic('chev', 24)}</a>`;
  }

  _warnleisten() {
    const { b } = this;
    const W = TECHNIK.warnband;
    const out = [];
    const k = b.konfig;
    const knoepfe = (t, grund) => html`<div class="btns">
      <button type="button" class="btn" data-aktion="aus_export" ?disabled=${!!this.beschaeftigt} @click=${() => this.exportBlatt()}>${t.aus_export}</button>
      <button type="button" class="btn" data-aktion="neu_ausrollen" ?disabled=${!!this.beschaeftigt} @click=${() => this.neuAusrollen(grund)}>${t.neu}</button></div>`;
    if (k?.zustand === 'leer_neu' || k?.zustand === 'export_neuer') {
      const t = W[k.zustand];
      out.push(html`<div class="note warn" role="alert" data-warnleiste=${k.zustand}><strong>${t.titel}</strong> ${t.text}${knoepfe(t, k.zustand)}</div>`);
    }
    if (k && k.export_ok === false && k.zustand === 'ok') {
      out.push(html`<div class="note warn" role="alert" data-warnleiste="export_fehlt"><strong>${W.export_fehlt.titel}</strong> ${W.export_fehlt.text}</div>`);
    }
    for (const x of b.boxen.filter((y) => y.konfig_stand === 'voraus')) {
      const t = W.box_voraus;
      out.push(html`<div class="note warn" role="alert" data-warnleiste="box_voraus" data-box=${x.box}><strong>${fuellen(t.titel, { box: boxName(x) })}</strong> ${t.text}${knoepfe(t, 'voraus')}</div>`);
    }
    return out;
  }

  _boxZeile(x) {
    const T = TECHNIK.box;
    const wo = x.online === true ? T.online : (x.online === false ? T.offline : T.unbekannt);
    return this._zeile(`#technik-box-${encodeURIComponent(x.box)}`, boxName(x), `${wo} · ${T.stand[x.konfig_stand] || T.stand.unbekannt}`);
  }

  _aufraeumen() {
    const { ctx } = this;
    const T = TECHNIK.aufraeumen;
    const zu = !!this.beschaeftigt;
    const aktion = (name, label, text, fn) => html`<div class="taktion"><button type="button" class="btn" data-aktion=${name} ?disabled=${zu} @click=${fn}>${label}</button><p class="muted">${text}</p></div>`;
    return html`<section class="tkarte" data-karte="aufraeumen" aria-labelledby="t-aufraeumen"><h3 id="t-aufraeumen">${T.titel}</h3>
      ${aktion('einlesen', T.einlesen, T.einlesen_text, () => this.einlesen())}
      ${ctx.faehig('cover') ? aktion('cover', T.cover, T.cover_text, () => this.coverNeuSuchen()) : nothing}
      ${ctx.faehig('hoerkopie') ? aktion('hoerkopien', T.hoerkopien, T.hoerkopien_text, () => this.hoerkopienNeu()) : nothing}
      ${this._panel('aufraeumen')}</section>`;
  }

  _korbZeile(e) {
    const T = TECHNIK.korb;
    const wann = e.geloescht_von?.name
      ? fuellen(T.geloescht_von, { zeit: zeitKurz(e.geloescht_am), name: e.geloescht_von.name })
      : fuellen(T.geloescht, { zeit: zeitKurz(e.geloescht_am) });
    const teile = [T.typ[e.typ] || e.typ, e.serie_name ? fuellen(T.aus, { serie: e.serie_name }) : null, zaehle(T.dateien, e.tracks ?? 0), groesse(e.groesse_bytes), wann].filter(Boolean);
    return html`<button type="button" class="tzeile" data-korb=${e.id} aria-label=${fuellen(T.wiederherstellen, { name: e.anzeige })} ?disabled=${!!this.beschaeftigt} @click=${() => this.korbStelleHer(e)}>
      <span class="tz-t"><strong>${e.anzeige}</strong><span class="muted">${teile.join(' · ')} · ${T.tippen}</span></span>${ic('chev', 24)}</button>`;
  }

  _papierkorb() {
    const { ctx, korb: k } = this;
    const T = TECHNIK.korb;
    let inhalt;
    if (k.phase === 'laedt') inhalt = ctx.laedt();
    else if (k.phase === 'fehler') inhalt = ctx.fehlerKarte(k.fehlerCode, () => this.ladeKorb());
    else if (!k.eintraege.length) inhalt = ctx.leer('papierkorb', 'papierkorbLeer', { href: '#bibliothek' });
    else {
      inhalt = html`<p class="muted" data-korb-summe>${fuellen(T.summe, { anzahl: zaehle(T.anzahl, k.gesamt), groesse: groesse(k.bytes) })}</p>
        <div class="tstapel" data-liste="papierkorb">${k.eintraege.map((e) => this._korbZeile(e))}</div>
        ${k.eintraege.length < k.gesamt ? html`<div class="btns"><button type="button" class="btn" data-mehr @click=${() => this.ladeKorb(k.eintraege.length)}>${T.mehr}</button></div>` : nothing}`;
    }
    const zu = !!this.beschaeftigt;
    return html`<section class="tkarte" data-karte="papierkorb" aria-labelledby="t-korb"><h3 id="t-korb">${T.titel}</h3>
      ${inhalt}
      <div class="btns tknoepfe"><button type="button" class="btn" data-aktion="letzte_stunde" ?disabled=${zu} @click=${() => this.korbLetzteStunde()}>${T.letzte_stunde}</button>
        <button type="button" class="btn danger" data-aktion="leeren" ?disabled=${zu || !k.gesamt} @click=${() => this.korbLeeren()}>${T.leeren}</button></div>
      <p class="muted">${T.satz}</p></section>`;
  }

  _staende() {
    const { ctx, staende: s } = this;
    const T = TECHNIK.liste.staende;
    let inhalt;
    if (s.phase === 'laedt') inhalt = ctx.laedt();
    else if (s.phase === 'fehler') inhalt = ctx.fehlerKarte(s.fehlerCode, () => this.ladeStaende());
    else if (!s.liste.length) inhalt = html`<p class="muted">${T.leer}</p>`;
    else {
      inhalt = html`<div class="tstapel" data-liste="staende">${s.liste.map((x) => {
        const zuo = zaehle(TECHNIK.zuordnungen, x.anzahl_zuordnungen ?? 0);
        const zeit = zeitKurz(x.exportiert_am);
        const text = zeit ? fuellen(T.zeile, { nr: x.stand, zeit, zuordnungen: zuo }) : fuellen(T.zeile_ohne_zeit, { nr: x.stand, zuordnungen: zuo });
        return html`<button type="button" class="tzeile" data-stand=${x.stand} aria-label=${fuellen(T.blatt, { nr: x.stand })} ?disabled=${!!this.beschaeftigt} @click=${() => this.exportBlatt(x.stand)}>
          <span class="tz-t"><strong>${text}</strong></span>${ic('chev', 24)}</button>`;
      })}</div>`;
    }
    return html`<section class="tkarte" data-karte="staende" aria-labelledby="t-staende"><h3 id="t-staende">${T.titel}</h3><p class="muted">${T.text}</p>${inhalt}</section>`;
  }

  render(route) {
    const { ctx, b } = this;
    const sub = unterseite(route);
    const boxId = sub === 'box' ? decodeURIComponent(route.id) : null;
    const box = sub === 'box' ? b.boxen.find((x) => x.box === boxId) : null;
    const titel = sub === 'box' ? (box ? boxName(box) : SEITE.seiten.technik_box) : (sub ? TECHNIK.zeilen[sub].titel : TECHNIK.titel);
    const kopf = html`${sub ? html`<a class="back" href="#technik">${SEITE.zurueck.technik}</a>` : nothing}<h2>${titel}</h2>`;
    const baender = this._warnleisten();
    if (!sub) {
      return html`${kopf}${baender}<div class="tstapel" data-technik="liste">${UNTERSEITEN.map((u) => this._zeile(`#technik-${u}`, TECHNIK.zeilen[u].titel, TECHNIK.zeilen[u].zeile))}</div>`;
    }
    if ((sub === 'boxen' || sub === 'box') && b.phase !== 'bereit') {
      return html`${kopf}${b.phase === 'fehler' ? ctx.fehlerKarte(b.fehlerCode, () => this.ladeBasis()) : ctx.laedt()}`;
    }
    switch (sub) {
      case 'boxen':
        return html`${kopf}${baender}${b.boxen.length ? html`<div class="tstapel" data-technik="boxen">${b.boxen.map((x) => this._boxZeile(x))}</div>` : ctx.leer('keine_box', 'keineBox', { aktion: () => this.ladeBasis() })}
          ${b.boxen.length ? html`<h3 class="th">${TECHNIK.box.alle}</h3>${this._panel('boxen')}` : nothing}`;
      case 'box':
        if (!box) return html`${kopf}${baender}<div class="note warn" role="status" data-zustand="unbekannte-box">${TECHNIK.box.unbekannte_box}</div>`;
        return html`${kopf}${baender}${this._panel('boxen', box.box)}
          <div class="tstapel">${this._zeile('#technik-tobies', TECHNIK.box.lernmodus.titel, TECHNIK.box.lernmodus.zeile)}</div>`;
      case 'speicher':
        return html`${kopf}${baender}${this._aufraeumen()}${this._papierkorb()}
          <section class="tkarte" data-karte="eingang" aria-labelledby="t-eingang"><h3 id="t-eingang">${TECHNIK.eingang}</h3>${this._panel('eingang')}</section>`;
      case 'liste':
        return html`${kopf}${baender}${this._panel('liste')}${ctx.faehig('konfig_staende') ? this._staende() : nothing}`;
      default:
        return html`${kopf}${baender}${this._panel(sub)}`;
    }
  }
}

export const erzeuge = (ctx) => new TechnikSeite(ctx);

export const stil = () => css`
  .tstapel { display: grid; gap: 8px; margin: 8px 0 16px; }
  .tzeile { display: flex; align-items: center; justify-content: space-between; gap: 12px; width: 100%; min-height: 64px; padding: 8px 12px 8px 16px;
    border: 1px solid var(--line); border-radius: var(--r-card); background: var(--card); color: var(--text); text-align: left; text-decoration: none; }
  .tzeile:active { background: var(--primary-soft); }
  .tzeile:disabled { opacity: .6; }
  .tzeile svg { flex: none; fill: var(--text2); }
  .tz-t { display: grid; gap: 2px; min-width: 0; overflow-wrap: anywhere; }
  .tz-t strong { font-weight: 500; }
  .tkarte { margin: 16px 0; }
  .tkarte h3, .th { font-size: 17px; font-weight: 500; margin: 16px 0 6px; }
  .tkarte > .muted { margin: 4px 0 8px; }
  .taktion { margin: 8px 0 12px; }
  .taktion .muted { margin: 4px 0 0; }
  .tknoepfe { margin: 12px 0 8px; }
  .alt { margin: 12px 0; }
`;

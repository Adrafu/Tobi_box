/* Box-Detailseite `#box-<id>` (Design 5.1.2, Paket A7b).
 *
 * Für alle: oben „‹ Geräte“, Überschrift = Name der Box, dieselbe Status-Karte wie auf „Geräte“ (ohne Link), darunter die Zeilen
 * Verbindung, Akku und „Läuft gerade“. Nur für Administratoren folgt die Überschrift „Technik“ mit dem Link
 * „Technik zu dieser Box“ auf `#technik-box-<id>`; den Inhalt dieser Seite baut A12/A13. Die Daten kommen live aus dem Speicher der
 * App (`boxen/list` und Ereignisse; das Feld `ereignisse` bleibt Administratoren vorbehalten und wird hier nicht gezeigt).
 * Schnittstelle zur App: siehe bausteine.js.
 */
import { html, nothing, ic } from '../bausteine.js';
import { GERAETE_SEITE, SEITE, fuellen } from '../texte.js';
import { BoxStatus, boxKarte } from './geraete.js';

class BoxSeite {
  constructor(ctx) {
    this.ctx = ctx;
    this.status = new BoxStatus(ctx);
    this.id = null;
  }

  betreten(route) {
    this.id = route?.id ?? null;
    this.status.zuruecksetzen();
  }

  verlassen() { this.status.stoppen(); }

  nachRender() {
    const box = this.ctx.boxen()[this.id];
    if (box) this.status.beobachte([box]);
  }

  render(route) {
    const { ctx } = this;
    const id = route?.id ?? this.id; // render läuft vor betreten, wenn die Seite zum ersten Mal erscheint
    const zurueck = html`<a class="back" href="#geraete">${SEITE.zurueck.geraete}</a>`;
    const box = ctx.boxen()[id];
    if (!box) {
      return html`${zurueck}<h2>${SEITE.seiten.box}</h2>
        <div class="note warn" data-zustand="box-fehlt"><strong>${GERAETE_SEITE.box_nicht_da}</strong>
          <div class="btns"><a class="btn" href="#geraete">${GERAETE_SEITE.zu_den_geraeten}</a></div></div>`;
    }
    const d = this.status.daten(box);
    const T = GERAETE_SEITE.box;
    const verbindung = d.online === true ? T.online
      : d.online === false ? (d.zuletzt ? fuellen(T.aus, { zeit: d.zuletzt }) : T.aus_ohne_zeit)
        : T.nie;
    const akku = d.akku === null ? T.akku_unbekannt : fuellen(d.lader ? T.akku_laedt : T.akku_ohne_laden, { prozent: d.akku });
    const laeuft = d.serieName ? `${d.serieName}${d.folge ? ` · ${d.folge}` : ''}` : T.nichts;
    return html`${zurueck}<h2>${d.anzeige}</h2>
      ${boxKarte(d, { link: false })}
      <div class="gkarte gdetail" data-box-zeilen>
        <div class="gz" data-zeile="verbindung"><span class="k">${T.verbindung}</span><span class="v">${verbindung}</span></div>
        <div class="gz" data-zeile="akku"><span class="k">${T.akku}</span><span class="v">${akku}</span></div>
        <div class="gz" data-zeile="laeuft"><span class="k">${T.laeuft}</span><span class="v">${laeuft}</span></div>
      </div>
      ${ctx.admin ? html`<h2 class="technik" data-abschnitt="technik">${T.technik}</h2>
        <a class="gkarte glink" href=${`#technik-box-${box.box}`} data-technik-link>${T.technik_link}<span class="chev" aria-hidden="true">${ic('chev', 24)}</span></a>` : nothing}`;
  }
}

export const erzeuge = (ctx) => new BoxSeite(ctx);
export const stil = null; // Karte und Zeilen bringt seiten/geraete.js mit

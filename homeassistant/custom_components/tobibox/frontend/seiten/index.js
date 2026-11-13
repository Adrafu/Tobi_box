/* Verzeichnis der Seiten (Paket A7). tobibox-app.js liest nur diese Datei.
 *
 * Eine neue Seite (A7b geraete.js, A8 serie.js, A12/A13 technik.js) trägt sich hier ein:
 *   import * as serie from './serie.js';
import * as tb from './tobies.js';
 *   … SEITEN.serie = serie;
 * Der Schlüssel ist der Routenname aus `parseRoute(hash).name`. Jedes Modul liefert `erzeuge(ctx)` und `stil`
 * (eine Funktion `() => css`…``, oder `null`; Funktion, weil Lit erst nach dem Laden des Moduls bereitsteht); der Vertrag steht oben in ../bausteine.js. Routen ohne Eintrag zeigen den Platzhalter
 * des Gerüsts (Überschrift und leerer Platz).
 */
import * as start from './start.js';
import * as bibliothek from './bibliothek.js';
import * as suche from './suche.js';
import * as technik from './technik.js';
import * as geraete from './geraete.js';
import * as box from './box.js';
import * as serie from './serie.js';
import * as tb from './tobies.js';

export const SEITEN = {
  start, bibliothek, suche, technik, geraete, box, serie,
  tobies: tb.tobies, tobie: tb.tobie, neu: tb.neu, 'neu-warten': tb.neuWarten, 'neu-ziel': tb.neuZiel, 'neu-queue': tb.neuQueue, geben: tb.geben, // A9, A10
};

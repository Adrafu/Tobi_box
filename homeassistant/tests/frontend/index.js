/* Einstieg für `node --test homeassistant/tests/frontend`: Ab Node 21 läuft ein Ordner nicht mehr
 * von selbst; Node löst den Ordner über index.js auf. Die Tests selbst stehen in panel.test.mjs. */
import('./panel.test.mjs');

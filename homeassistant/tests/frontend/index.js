/* Einstieg für `node --test homeassistant/tests/frontend`: Ab Node 21 läuft ein Ordner nicht mehr
 * von selbst; Node löst den Ordner über index.js auf. Die Tests selbst stehen in panel.test.mjs und panel_quiet.test.mjs. */
import('./panel.test.mjs');
import('./panel_quiet.test.mjs'); // AP 4.7 (Einstellungen) und Erweiterungen v1.1 des Vertrags W

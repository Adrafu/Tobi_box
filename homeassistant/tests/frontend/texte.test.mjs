/* Tests der Texte (AP A5). Aufruf: node --test homeassistant/tests/frontend
 *
 * Prüft texte.js gegen vertraglich festgelegte Codes und Gründe (docs/protocol/ha-websocket-v1.md)
 * und gegen das Design (docs/designs/ha-oberflaeche.md).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HIER = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(HIER, '../../..');
const texte = await import('../../custom_components/tobibox/frontend/texte.js');
const { FEHLER, GRUENDE, HINWEISE, HOERPROBE, STATUS, LEER, GERAETE, TOBIE, LEISE, UPLOAD, SEITE, KACHELN, fehlerText, fuellen, statusSatz, FALLBACK } = texte;

const vertrag = readFileSync(join(ROOT, 'docs/protocol/ha-websocket-v1.md'), 'utf8');
const design = readFileSync(join(ROOT, 'docs/designs/ha-oberflaeche.md'), 'utf8');

/* Abschnitt eines Markdown-Dokuments: von `start` bis zur nächsten Überschrift derselben oder höheren Ebene. */
function abschnitt(doc, start, ende = null) {
  const i = doc.indexOf(start);
  assert.ok(i >= 0, `Abschnitt nicht gefunden: ${start}`);
  let j = ende ? doc.indexOf(ende, i + start.length) : -1;
  if (j < 0) j = doc.indexOf('\n## ', i + start.length);
  return doc.slice(i, j < 0 ? undefined : j);
}

/* Alle Texte (Strings) in einem beliebig verschachtelten Objekt. */
function alleTexte(obj, pfad = '') {
  if (typeof obj === 'string') return [[pfad, obj]];
  if (Array.isArray(obj)) return obj.flatMap((v, i) => alleTexte(v, `${pfad}[${i}]`));
  if (obj && typeof obj === 'object') return Object.entries(obj).flatMap(([k, v]) => alleTexte(v, pfad ? `${pfad}.${k}` : k));
  return [];
}

const GRUPPEN = { FEHLER, GRUENDE, HINWEISE, HOERPROBE, LEER, GERAETE, TOBIE, LEISE, UPLOAD, SEITE, KACHELN };

/* ------------------------------------------------------------------ Vertrag */

test('Jeder Fehlercode aus Vertrag Abschnitt 7 hat einen Text in FEHLER', () => {
  const tabelle = abschnitt(vertrag, '## 7. Gemeinsame Fehlercodes', '## 8. Grenzen');
  const codes = [...tabelle.matchAll(/^\| `([a-z_]+)` \|/gm)].map((m) => m[1]);
  assert.ok(codes.length >= 40, `gefunden: ${codes.length}`);
  for (const c of codes) {
    assert.ok(typeof FEHLER[c] === 'string', `Text für ${c} fehlt in FEHLER`);
  }
});

test('Jeder gemeldete Prüfgrund aus Vertrag 11.9 hat einen Text in GRUENDE', () => {
  const abs = abschnitt(vertrag, '### 11.9 ', '\n### ');
  const codes = [...abs.matchAll(/^\| `([a-z_]+)`/gm)].map((m) => m[1]);
  assert.ok(codes.length >= 10, `gefunden: ${codes.length}`);
  for (const c of codes) assert.ok(typeof GRUENDE[c] === 'string', `${c} fehlt in GRUENDE`);
});

test('Hinweis-Codes aus Vertrag 3.2 (Serien) haben einen Text', () => {
  // Codes „in Version 1“ laut Vertrag 3.2 (`hinweise[]`); serie_name_doppelt steht bei den Gründen.
  const codes = ['datei_fehlt', 'kopierschutz', 'nicht_lesbar', 'probedekodierung_fehlgeschlagen',
    'pruefung_nicht_moeglich', 'serie_name_doppelt', 'doppelte_id_korrigiert',
    'serie_json_ungueltig_repariert', 'reservierter_ordner'];
  for (const c of codes) assert.ok(HINWEISE[c] || GRUENDE[c], `${c} fehlt`);
});

/* ------------------------------------------------------------------ Design */

test('Jeder Grund „bitte kurz ansehen“ aus Design 7.3 hat einen Text in GRUENDE', () => {
  const abs = abschnitt(design, '### 7.3 ', '### 7.4 ');
  const teil = abs.slice(abs.indexOf('| Code | Text für Eltern |'), abs.indexOf('**Gründe „geht nicht“**'));
  const codes = [...teil.matchAll(/^\s*\| `([a-z_]+)`/gm)].map((m) => m[1]);
  assert.ok(codes.length >= 14, `gefunden: ${codes.length}`);
  for (const c of codes) assert.ok(typeof GRUENDE[c] === 'string', `${c} fehlt in GRUENDE`);
});

test('Jeder Grund „geht nicht“ aus Design 7.3 hat einen Text in HINWEISE', () => {
  const abs = abschnitt(design, '### 7.3 ', '### 7.4 ');
  const teil = abs.slice(abs.indexOf('**Gründe „geht nicht“**'), abs.indexOf('7. **Zwei Uploads'));
  const codes = [...teil.matchAll(/`([a-z_]+)`/g)].map((m) => m[1]).filter((c) => c !== 'hinweise' && c !== 'fehler');
  assert.ok(codes.length >= 6, `gefunden: ${codes.length}`);
  for (const c of codes) assert.ok(typeof HINWEISE[c] === 'string', `${c} fehlt in HINWEISE`);
});

test('Die Alltagscodes aus Design 6.1 haben den Text des Designs', () => {
  assert.equal(fuellen(FEHLER.medien_nicht_erreichbar), 'Das NAS antwortet gerade nicht. Versuche es in ein paar Minuten noch einmal. Wenn es so bleibt, sag dem Administrator Bescheid.');
  assert.equal(FEHLER.format_nicht_erlaubt, 'Dieses Dateiformat spielt die Box nicht. Erlaubt sind MP3, M4A, M4B, AAC, FLAC, OGG, Opus und WAV.');
  assert.equal(fuellen(FEHLER.lernmodus_laeuft), 'Auf Box 1 läuft schon das Anlernen für ein anderes Hörspiel. Beende es zuerst.');
  assert.equal(GRUENDE.art_geraten, 'Die Art ist geraten. Stimmt das?');
});

/* ------------------------------------------------------------------ Regeln */

test('Kein Text ist leer', () => {
  for (const [name, gruppe] of Object.entries(GRUPPEN)) {
    for (const [pfad, text] of alleTexte(gruppe)) {
      assert.ok(text.trim().length > 0, `${name}.${pfad} ist leer`);
    }
  }
});

test('Kein Text enthält UID, Revision oder Listen-ID', () => {
  for (const [name, gruppe] of Object.entries(GRUPPEN)) {
    for (const [pfad, text] of alleTexte(gruppe)) {
      assert.doesNotMatch(text, /\bUID\b/i, `${name}.${pfad}`);
      assert.doesNotMatch(text, /Revision/i, `${name}.${pfad}`);
      assert.doesNotMatch(text, /Listen-ID/i, `${name}.${pfad}`);
    }
  }
});

test('Jeder Text lässt sich mit den Vorgabewerten vollständig füllen', () => {
  // STATUS-Vorlagen füllt statusSatz (eigener Test), darum hier nicht.
  for (const [name, gruppe] of Object.entries(GRUPPEN)) {
    for (const [pfad, text] of alleTexte(gruppe)) {
      assert.doesNotMatch(fuellen(text), /\{[a-z_]+\}/, `${name}.${pfad} hat einen offenen Platzhalter`);
    }
  }
});

test('fehlerText mit unbekanntem Code liefert den Rückfall', () => {
  assert.equal(fehlerText('neuer_code_x'), fuellen(FALLBACK));
  assert.equal(fehlerText('neuer_code_x'), fehlerText('unknown_error'));
  assert.match(fehlerText('neuer_code_x'), /sag dem Administrator Bescheid\.$/);
  assert.equal(fehlerText('neuer_code_x', { admin: true }), `${fuellen(FALLBACK)} (Code: neuer_code_x)`);
  assert.doesNotMatch(fehlerText('neuer_code_x'), /Code:/);
});

test('fehlerText setzt Platzhalter aus den Werten ein', () => {
  assert.match(fehlerText('box_offline', { box: 'Box 2' }), /^Box 2 ist aus oder nicht im WLAN\./);
  assert.match(fehlerText('datei_zu_gross', { grenze: '2 GB' }), /\(mehr als 2 GB\)/);
  assert.equal(fehlerText('unauthorized'), 'Dafür fehlt dir die Berechtigung. Frag den Administrator.');
});

/* ------------------------------------------------------------------ Status-Sätze (5.1.1) */

test('Status: spielt mit Akku und Laden', () => {
  const s = statusSatz({ anzeige: 'Box 1', online: true, zustand: 'spielt', serie: 'Lange Serie', folge: 'Der Rabe', folge_nummer: 4, akku_prozent: 80, lader: true });
  assert.deepEqual(s, { lage: 'spielt', satz: 'Box 1 spielt „Lange Serie“ · Folge 4: Der Rabe.', nebentext: 'Akku 80 %, lädt.', warnung: false });
});

test('Status: pausiert ohne Laden', () => {
  const s = statusSatz({ anzeige: 'Box 1', online: true, zustand: 'pausiert', serie: 'Lange Serie', akku_prozent: 80, lader: false });
  assert.equal(s.satz, 'Box 1 ist pausiert bei „Lange Serie“.');
  assert.equal(s.nebentext, 'Akku 80 %.');
});

test('Status: leer, beendet, gehalten und unbekannt sind „bereit“', () => {
  for (const zustand of ['leer', 'beendet', 'gehalten', 'unbekannt']) {
    assert.equal(statusSatz({ anzeige: 'Box 1', online: true, zustand }).satz, 'Box 1 ist bereit. Es liegt kein Tobie auf.');
  }
});

test('Status: herunterfahren ohne Nebentext', () => {
  assert.deepEqual(statusSatz({ anzeige: 'Box 1', online: true, zustand: 'herunterfahren', akku_prozent: 50 }),
    { lage: 'herunterfahren', satz: 'Box 1 geht gerade aus.', nebentext: '', warnung: false });
});

test('Status: Akku bis 20 % ohne Laden ist eine Warnung', () => {
  const s = statusSatz({ anzeige: 'Box 1', online: true, zustand: 'leer', akku_prozent: 15, lader: false });
  assert.deepEqual(s, { lage: 'bereit', satz: 'Box 1 ist bereit. Es liegt kein Tobie auf.', nebentext: 'Akku fast leer (15 %). Bitte laden.', warnung: true });
  assert.equal(statusSatz({ anzeige: 'Box 1', online: true, zustand: 'leer', akku_prozent: 15, lader: true }).warnung, false);
});

test('Status: offline mit letzter Meldung', () => {
  const s = statusSatz({ anzeige: 'Box 2', online: false, zeit_letzte_meldung: 'heute um 18:40', akku_prozent: 35 });
  assert.deepEqual(s, { lage: 'offline', satz: 'Box 2 ist aus oder nicht im WLAN.', nebentext: 'Zuletzt gesehen: heute um 18:40. Akku war bei 35 %.', warnung: false });
});

test('Status: noch keine Meldung', () => {
  assert.deepEqual(statusSatz({ anzeige: 'Box 2', online: null }),
    { lage: 'nie_gemeldet', satz: 'Box 2 hat sich noch nicht gemeldet.', nebentext: '', warnung: false });
});

test('Status: Hinweis zu neuen Zuordnungen nur bei Offline oder Abweichung über 5 Minuten', () => {
  const satzNeu = 'Neue Zuordnungen kommen auf die Box, sobald sie wieder im WLAN ist.';
  assert.match(statusSatz({ anzeige: 'Box 2', online: false, konfig_stand: 'neu' }).nebentext, new RegExp(satzNeu));
  assert.match(statusSatz({ anzeige: 'Box 1', online: true, zustand: 'leer', konfig_stand: 'neu', abweichung_min: 10 }).nebentext, new RegExp(satzNeu));
  assert.doesNotMatch(statusSatz({ anzeige: 'Box 1', online: true, zustand: 'leer', konfig_stand: 'neu', abweichung_min: 2 }).nebentext, /Neue Zuordnungen/);
  assert.doesNotMatch(statusSatz({ anzeige: 'Box 1', online: true, zustand: 'leer', konfig_stand: 'aktuell' }).nebentext, /Neue Zuordnungen/);
});

/* ------------------------------------------------------------------ Leere Zustände, Geräte, Kacheln */

test('Leere Zustände, „Geräte“ und Kacheln: Design-Texte stehen wörtlich drin', () => {
  assert.equal(fuellen(LEER.bibliothek.satz), 'Noch nichts da. Tippe auf „Hinzufügen“.');
  assert.equal(fuellen(LEER.keine_box.satz), 'Noch keine Box eingerichtet. Bitte dem Administrator Bescheid sagen.');
  assert.equal(fuellen(GERAETE.abends.erklaerung), 'Gute Nacht und Leise-Zeiten');
  assert.equal(Object.keys(KACHELN).length, 5);
  assert.equal(KACHELN.sortier_du.zeile, 'Ich lese die Angaben');
});

/* ------------------------------------------------------------------ A5b: Textnachtrag Runde 17 */

/* Ein Text steht wörtlich im Design (Anführungszeichen und Satzzeichen wie dort). */
function imDesign(text) {
  const ohneFett = design.replace(/\*\*/g, '');
  assert.ok(ohneFett.includes(text.replace(/\*\*/g, '')), `Im Design steht nicht wörtlich: ${text}`);
}

test('A5b: „Mehr“ gibt es nicht mehr, „Geräte“ trägt die Texte aus Abschnitt 3.4', () => {
  assert.equal(texte.MEHR, undefined);
  assert.equal(GERAETE.titel, 'Geräte');
  assert.equal(GERAETE.abends.titel, 'Abends');
  imDesign('Zeile **„Wer hat was gehört?“**'.replace(/\*\*/g, ''));
  assert.equal(GERAETE.gehoert.titel, 'Wer hat was gehört?');
  for (const [pfad, text] of alleTexte({ GERAETE, LEER })) assert.doesNotMatch(text, /\bMehr\b/, pfad);
  // 6.2 und 5.7: „Geräte“ statt Startseite
  assert.equal(fuellen(LEER.tobies.satz), 'Noch keine Tobies. Lege einen Tobie auf eine Box, dann erscheint er unter „Geräte“.'); // A9: Design 6.2
  assert.equal(LEER.tobies.knopf, 'Zu den Geräten');
  assert.equal(fuellen(LEER.start.satz), 'Noch nichts da. Tippe in der Bibliothek auf „+“.');
  assert.equal(LEER.start.knopf, 'Zur Bibliothek');
});

test('A5b: Meldung beim Zuordnen nennt altes und neues Ziel (R17-3)', () => {
  assert.equal(fuellen(TOBIE.zugeordnet_umgehaengt), 'Löwe spielt jetzt „Abenteuer im Wald“ (vorher „Kommissar Kralle“).');
  assert.equal(fuellen(TOBIE.zugeordnet_neu), 'Fertig: Löwe spielt jetzt „Abenteuer im Wald“.');
  imDesign('Löwe spielt jetzt „Abenteuer im Wald“ (vorher „Kommissar Kralle“).');
  imDesign('Fertig: Löwe spielt jetzt „…“.');
  assert.equal(fuellen(TOBIE.zugeordnet_neu, { tobie: 'Mia', ziel: 'Pirat Pippo' }), 'Fertig: Mia spielt jetzt „Pirat Pippo“.');
  assert.equal(TOBIE.rueckgaengig, 'Rückgängig');
});

test('A5b: Zeile „Vorher“ auf der Tobie-Seite', () => {
  assert.equal(fuellen(TOBIE.zurueckgestellt, { tobie: 'Löwe', ziel: 'Kommissar Kralle' }), 'Löwe spielt wieder „Kommissar Kralle“.');
  assert.doesNotMatch(TOBIE.zurueckgestellt, /Fertig/, '„Fertig:“ gehört zum neuen Tobie');
  assert.equal(fuellen(TOBIE.vorher), 'Vorher: Kommissar Kralle');
  assert.equal(TOBIE.zurueckstellen, 'Zurückstellen');
  imDesign('Vorher: Kommissar Kralle · Zurückstellen');
});

test('A5b: Namensfeld, auch bei „Später auflegen“ (R17-5)', () => {
  assert.equal(TOBIE.name_frage, 'Wie soll er heißen?');
  assert.equal(TOBIE.name_hinweis, 'Du kannst das überspringen.');
  imDesign('Wie soll er heißen?** Du kannst das überspringen.');
  imDesign('Name, zum Beispiel Farbe oder Tier');
  assert.equal(TOBIE.name_geben, 'Name geben');
});

test('A5b: Meldung „Neuer Tobie auf Box 1“ mit dem Knopf „Zuordnen“ auf jeder Seite (R17-6)', () => {
  assert.equal(fuellen(TOBIE.neuer_tobie_meldung), 'Neuer Tobie auf Box 1.');
  assert.equal(fuellen(TOBIE.neuer_tobie_meldung, { box: 'Box 2' }), 'Neuer Tobie auf Box 2.');
  assert.doesNotMatch(TOBIE.neuer_tobie_meldung, /Zuordnen/, 'das Wort steht nur auf dem Knopf');
  assert.equal(TOBIE.zuordnen, 'Zuordnen');
  imDesign('Neuer Tobie auf Box 1');
  assert.equal(fuellen(TOBIE.aufgelegt_zugeordnet, { ziel: 'Lange Serie' }), 'Box 1: Der neue Tobie spielt jetzt „Lange Serie“.');
  imDesign('Box 1: Der neue Tobie spielt jetzt „Lange Serie“.');
});

test('A5b: Karten auf „Geräte“ (5.13, 7.1)', () => {
  assert.equal(fuellen(GERAETE.nicht_zugeordnet.titel), 'Konnte nicht zugeordnet werden');
  assert.equal(GERAETE.nicht_zugeordnet.jetzt_zuordnen, 'Jetzt zuordnen');
  assert.equal(GERAETE.platz_bekommen.titel, 'Ein neuer Tobie hat einen Platz bekommen.');
  assert.equal(GERAETE.platz_bekommen.frage, 'Name geben?');
  assert.equal(GERAETE.platz_bekommen.spaeter, 'Später');
  imDesign('Ein neuer Tobie hat einen Platz bekommen.** Name geben?');
  assert.equal(fuellen(GERAETE.neuer_tobie.titel), 'Neuer Tobie auf Box 1 – was soll er spielen?');
  assert.equal(fuellen(GERAETE.neuer_tobie.zeile), 'Gerade aufgelegt, vor 2 Minuten.');
  assert.equal(fuellen(GERAETE.neue_tobies.titel), '3 neue Tobies auf Box 1');
  assert.equal(fuellen(GERAETE.neue_tobies.titel, { anzahl: 2 }), '2 neue Tobies auf Box 1');
  assert.equal(GERAETE.wartet.titel, 'Wartet auf einen neuen Tobie');
  assert.equal(fuellen(GERAETE.wartet.zeile2), 'spielt „Lange Serie“ · Nr. 1 von 2');
  assert.equal(GERAETE.wartet.abbrechen, 'Nicht mehr warten');
  assert.equal(GERAETE.grund_gesperrt, 'Änderungen sind gerade gesperrt.');
});

test('A5b: Satz „Bildschirm anlassen“ nur als Upload-Zustand, „+ Tobie“, „Gilt für …“', () => {
  assert.equal(UPLOAD.bildschirm_anlassen, 'Bildschirm anlassen, bis es fertig ist.');
  imDesign('„**Bildschirm anlassen, bis es fertig ist.**“');
  assert.equal(TOBIE.plus_tobie, '+ Tobie');
  assert.equal(TOBIE.weiteren_tobie, 'Weiteren Tobie geben');
  assert.equal(fuellen(LEISE.gilt_fuer), 'Gilt für Mo, Di, Mi, Do, So. Tage abwählen, wenn es nur für einzelne gelten soll.');
  assert.equal(fuellen(LEISE.gilt_fuer, { tage: 'Fr, Sa' }), 'Gilt für Fr, Sa. Tage abwählen, wenn es nur für einzelne gelten soll.');
  imDesign('Gilt für Mo, Di, Mi, Do, So.** Tage abwählen, wenn es nur für einzelne gelten soll.');
  assert.equal(TOBIE.neue_tobies_punkt, '1 neuer Tobie');
});

test('A6: Texte des Rahmens stehen wörtlich im Design (Abschnitte 3.1, 6)', () => {
  assert.deepEqual(Object.values(SEITE.reiter), ['Start', 'Bibliothek', 'Tobies', 'Geräte']);
  assert.deepEqual(Object.values(SEITE.begruessung), ['Guten Morgen', 'Guten Tag', 'Guten Abend', 'Gute Nacht']);
  assert.equal(SEITE.fehler_laden.titel, 'Die Seite konnte nichts laden.');
  assert.equal(fuellen(SEITE.fehler_laden.text), 'Home Assistant antwortet gerade nicht. Warte kurz und versuche es noch einmal. Wenn es so bleibt, sag dem Administrator Bescheid.');
  imDesign('Home Assistant antwortet gerade nicht. Warte kurz und versuche es noch einmal. Wenn es so bleibt, sag dem Administrator Bescheid.');
  assert.equal(SEITE.fehler_laden.knopf, 'Noch einmal versuchen');
  assert.equal(SEITE.verbindung_weg.titel, 'Keine Verbindung zu Home Assistant.');
  imDesign('Die Ansicht wird von selbst aktuell, sobald die Verbindung wieder da ist.');
  assert.equal(fuellen(SEITE.liste_gesperrt), 'Änderungen sind gerade gesperrt. Bitte dem Administrator Bescheid sagen.');
  assert.equal(fuellen(SEITE.technik_nur_admin), 'Dieser Bereich ist nur für Administratoren. Wenn du etwas Technisches brauchst, frag den Administrator.');
  imDesign('Dieser Bereich ist nur für Administratoren. Wenn du etwas Technisches brauchst, frag den Administrator.');
  assert.equal(SEITE.veraltet, FEHLER.unknown_command);
  assert.equal(SEITE.testtitel, 'Tobi Box (Test)');
});

test('Texte nennen keine echten Namen und keine Netz-Adressen', () => {
  for (const [name, gruppe] of Object.entries(GRUPPEN)) {
    for (const [pfad, text] of alleTexte(gruppe)) assert.doesNotMatch(text, /https?:\/\//, `${name}.${pfad}`);
  }
});

/* ------------------------------------------------------------------ AB4: die Nummer steht nur einmal im Status-Satz */

test('Status: heißt die Folge schon „Folge 1: Der Schatz“, steht die Nummer nicht noch einmal davor', () => {
  const satz = (folge, nummer) => statusSatz({ anzeige: 'Box 1', online: true, zustand: 'spielt', serie: 'Drachen', folge, folge_nummer: nummer }).satz;
  assert.equal(satz('Folge 1: Der Schatz', 1), 'Box 1 spielt „Drachen“ · Folge 1: Der Schatz.', 'Ursache: die Anzeige trug „Folge 1:“ schon im Namen');
  assert.equal(satz('Der Schatz', 1), 'Box 1 spielt „Drachen“ · Folge 1: Der Schatz.', 'ohne Nummer im Namen bleibt sie davor');
  assert.equal(satz('01 - Der Schatz', 1), 'Box 1 spielt „Drachen“ · 01 - Der Schatz.');
  assert.equal(satz('1. Der Schatz', 1), 'Box 1 spielt „Drachen“ · 1. Der Schatz.');
  assert.equal(satz('Folge 12: Das Rätsel', 1), 'Box 1 spielt „Drachen“ · Folge 1: Folge 12: Das Rätsel.', 'Folge 12 ist nicht Folge 1');
  assert.equal(satz('1 Mann im Wald', 1), 'Box 1 spielt „Drachen“ · Folge 1: 1 Mann im Wald.', 'eine Zahl am Titelanfang ohne Trenner ist keine Nummer');
  assert.equal(satz('Folge 4 Das Rätsel', 4), 'Box 1 spielt „Drachen“ · Folge 4 Das Rätsel.');
});

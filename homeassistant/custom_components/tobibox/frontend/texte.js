// Texte der HA-Oberfläche (Design docs/designs/ha-oberflaeche.md, Pakete A5, A5b und A6).
// Ein ES-Modul ohne Abhängigkeiten. Die Texte stehen wörtlich im Design.
// Stellen ohne Design-Text sind mit „// neu, nicht im Design“ markiert.
//
// Platzhalter stehen in {geschweiften Klammern} und werden mit fuellen()
// eingesetzt. Fehlt ein Wert, nimmt fuellen() den Vorgabewert aus DEFAULT.
// Texte sind für Eltern gedacht: keine Fachbegriffe wie UID oder Revision.

// Vorgabewerte für Platzhalter (Beispiele aus dem Design).
export const VERWALTER = { akk: 'den Administrator', dat: 'dem Administrator' };

const DEFAULT = {
  box: 'Box 1',
  grenze: '2 GB',
  verwalter_akk: VERWALTER.akk,
  verwalter_dat: VERWALTER.dat,
  suchwort: 'Suchwort',
  angekommen: '2',
  anzahl: '3',
  tobie: 'Löwe',
  ziel: 'Abenteuer im Wald',
  vorher: 'Kommissar Kralle',
  tage: 'Mo, Di, Mi, Do, So',
  zeit: 'vor 2 Minuten',
  serie: 'Lange Serie',
  nr: '1',
  gesamt: '2',
};

// Ersetzt {name} durch werte.name, sonst durch den Vorgabewert. Unbekannte Platzhalter bleiben stehen.
export function fuellen(text, werte = {}) {
  return text.replace(/\{([a-z_]+)\}/g, (platzhalter, name) => {
    const wert = werte[name] ?? DEFAULT[name];
    return wert === undefined ? platzhalter : String(wert);
  });
}

// Rückfall für unbekannte Codes und für Standardtexte (Abschnitt 6.1).
export const FALLBACK = 'Das hat nicht geklappt. Versuche es noch einmal. Wenn es wieder nicht geht, sag {verwalter_dat} Bescheid.';

// Fehlertexte: Code aus dem Vertrag (Abschnitt 7) → Text mit der nächsten Handlung.
// Schlüssel ohne Vertragscode stehen am Ende (Seite selbst).
export const FEHLER = {
  // Vertrag, Abschnitt 6.1 (Alltagscodes)
  medien_nicht_erreichbar: 'Das NAS antwortet gerade nicht. Versuche es in ein paar Minuten noch einmal. Wenn es so bleibt, sag {verwalter_dat} Bescheid.',
  medien_schreibfehler: 'Das Speichern auf dem NAS hat nicht geklappt. Versuche es gleich noch einmal. Wenn es so bleibt, sag {verwalter_dat} Bescheid.',
  kein_speicher: 'Auf dem NAS ist kein Platz mehr. Bitte {verwalter_dat} Bescheid sagen.',
  mqtt_nicht_verbunden: 'Die Verbindung zu den Boxen ist gerade gestört. Es wurde nichts gesendet. Versuche es gleich noch einmal.',
  box_offline: '{box} ist aus oder nicht im WLAN. Schalte sie ein und versuche es noch einmal.',
  konfig_nicht_bereit: 'Änderungen sind gerade gesperrt. Bitte {verwalter_dat} Bescheid sagen.',
  unauthorized: 'Dafür fehlt dir die Berechtigung. Frag {verwalter_akk}.',
  zuordnung_geaendert: 'Jemand hat gerade etwas anderes geändert. Die Ansicht ist neu geladen. Bitte versuche es noch einmal.',
  stand_veraltet: 'Jemand hat gerade etwas anderes geändert. Die Ansicht ist neu geladen. Bitte versuche es noch einmal.',
  lernmodus_laeuft: 'Auf {box} läuft schon das Anlernen für ein anderes Hörspiel. Beende es zuerst.',
  format_nicht_erlaubt: 'Dieses Dateiformat spielt die Box nicht. Erlaubt sind MP3, M4A, M4B, AAC, FLAC, OGG, Opus und WAV.',
  datei_zu_gross: 'Die Datei ist zu groß (mehr als {grenze}). Kopiere sie am Computer in den Eingang-Ordner auf dem NAS. Frag {verwalter_akk} nach dem Ordner.',
  zu_viele_uploads: 'Es laufen schon mehrere Uploads. Die Seite wartet und sendet danach weiter.', // neu, nicht im Design (kein Fehler, nur Wartetext)
  name_ungueltig: 'Dieser Name geht nicht. Bitte kürzer oder anders schreiben.',
  einstellung_ungueltig: 'Eine Einstellung passt nicht. Nichts wurde geändert. Prüfe die Eingabe und versuche es noch einmal.', // neu, nicht im Design (Design verweist auf 4.6, dort steht kein Text)
  sortierung_laeuft: 'Es wird gerade einsortiert. Versuche es in einer Minute noch einmal.',
  upload_laeuft: 'Es läuft schon ein Hochladen. Warte, bis es fertig ist.',
  kein_lernmodus: 'Es läuft gerade kein Anlernen. Starte es noch einmal.',
  serie_nicht_gefunden: 'Das gibt es nicht mehr. Die Ansicht ist neu geladen.',
  folge_nicht_gefunden: 'Das gibt es nicht mehr. Die Ansicht ist neu geladen.',
  eintrag_nicht_gefunden: 'Das gibt es nicht mehr. Die Ansicht ist neu geladen.',
  kennung_ungueltig: 'Dieser Tobie ist hier nicht bekannt. Lege ihn auf eine Box.',
  ziel_ungueltig: 'Das geht als Ziel nicht. Wähle etwas anderes.',
  zu_viele_aenderungen: 'Das waren gerade sehr viele Änderungen. Warte eine Minute und versuche es noch einmal.',
  cover_ungueltig: 'Das Bild geht nicht. Nimm ein anderes Foto.',
  wunsch_ungueltig: 'Das passt so nicht zusammen. Wähle noch einmal, was du hochlädst.',
  neu_einsortieren_nicht_moeglich: 'Das lässt sich nicht mehr anders einsortieren, weil schon etwas daran geändert wurde. Lege es in den Papierkorb und lade es noch einmal hoch.',
  hoerkopie_warteschlange_voll: 'Gerade sind viele Hörproben in Arbeit. Versuche es in einer Viertelstunde noch einmal. Auf der Box spielt es schon.',
  zu_viele_streams: 'Es läuft schon auf mehreren Geräten etwas. Beende dort das Hören und versuche es noch einmal.',
  rueckfrage_abgelaufen: 'Das hat zu lange gedauert. Der Tobie spielt wie vorher.',

  // Vertrag, Abschnitt 7, ohne Design-Text
  invalid_format: 'Die Eingabe passt nicht. Versuche es noch einmal. Wenn es wieder nicht geht, sag {verwalter_dat} Bescheid.', // neu, nicht im Design
  unknown_command: 'Die Seite ist veraltet. Bitte lade sie neu (am Handy: Seite nach unten ziehen oder Browser neu öffnen).',
  unknown_error: FALLBACK,
  zuordnung_existiert: 'Dieser Tobie liegt schon woanders. Wenn du ihn umlegen willst, bestätige das noch einmal.', // neu, nicht im Design
  tobies_betroffen: 'Es hängen noch Tobies daran. Willst du trotzdem weitermachen? Dann bestätige das.', // neu, nicht im Design (kein Fehler, die Seite fragt nach)
  hoerkopie_wartet: 'Die Hörprobe wird noch vorbereitet. Versuche es in einer Minute noch einmal. Auf der Box spielt es schon.', // neu, nicht im Design
  cover_nicht_gefunden: 'Dieser Eintrag hat noch kein Bild.', // neu, nicht im Design
  warteschlange_voll: 'Es warten schon 5 Tobies. Warte, bis einer aufgelegt ist, oder nimm einen aus der Liste.', // Vertrag W, Änderung 13.11. (A0-Q)
  warteschlange_doppelt: 'Das wartet schon.', // Vertrag W, Änderung 13.11. (A0-Q)

  // Standardtext (Design 6.1: nur Administratoren sehen den Code dahinter)
  anfrage_id_konflikt: FALLBACK,
  export_nicht_gefunden: FALLBACK,
  export_ungueltig: FALLBACK,
  box_unbekannt: FALLBACK,
  konfig_zu_gross: FALLBACK,
  reihenfolge_ungueltig: FALLBACK,
  ueberraschung_existiert: FALLBACK,
  datei_existiert: FALLBACK,
  serie_existiert: FALLBACK,

  // Seiten-eigene Texte aus Abschnitt 6.1 (kein Vertragscode)
  verbindung_abgebrochen: 'Die Verbindung ist abgebrochen. Ob die Datei angekommen ist, siehst du in ein paar Minuten unter „Zuletzt hinzugefügt“. Wenn nicht, wähle sie noch einmal.',
  abspiel_link_abgelaufen: 'Die Verbindung ist abgebrochen. Tippe auf Abspielen, dann geht es weiter.',
  browser_spielt_nicht: 'Das kann dieser Browser nicht abspielen. Auf der Box spielt es trotzdem.',
};

// Hörproben (Design 6.1, Zustände ohne Fehlercode).
export const HOERPROBE = {
  vorbereitung: 'Die Hörprobe wird vorbereitet. Bei einem Lied dauert das etwa eine Minute, bei einem langen Hörbuch bis zu einer halben Stunde. Du kannst die Seite offen lassen, sie sagt Bescheid. Auf der Box spielt es schon.',
  fertig: 'Die Hörprobe ist fertig. Tippe auf Reinhören.',
  keine_datei: 'Für diese Datei gibt es keine Hörprobe. Auf der Box spielt sie trotzdem.',
  keine_datei_admin: 'Administratoren sehen den Grund in „Technik“. Dort gibt es auch „Hörkopien neu erzeugen“.', // neu, nicht im Design (sinngemäß aus 6.1)
};

// Gründe „bitte kurz ansehen“ (Design 7.3, Punkt 6, plus art_geraten und serie_name_doppelt aus 6.1 und 7.3).
export const GRUENDE = {
  tags_fehlen: 'In der Datei steht kein Albumname. Name und Hörspiel sind aus dem Dateinamen geraten.',
  serie_aus_interpret: 'Das Hörspiel ist aus dem Künstlernamen in der Datei abgeleitet.',
  serie_aus_ordner: 'Das Hörspiel ist aus dem Ordnernamen abgeleitet.',
  serie_widerspruch: 'Die Dateien nennen verschiedene Hörspiele. Das häufigste wurde genommen.',
  serie_mehrdeutig: 'Es passten mehrere Hörspiele. Das älteste wurde genommen.',
  nummer_widerspruch: 'Die Dateien nennen verschiedene Folgen-Nummern.',
  nummer_doppelt: 'Diese Folgen-Nummer gibt es in dem Hörspiel schon.',
  track_doppelt: 'Die Reihenfolge der Kapitel ist nicht eindeutig.',
  track_teils_leer: 'Die Reihenfolge der Kapitel ist nicht eindeutig.',
  name_geaendert: 'Der Name ging so nicht und wurde angepasst.',
  folge_gleicher_name: 'Eine Folge mit diesem Namen gibt es schon.',
  teilweise_doppelt: 'Ein Teil war schon da und wurde nicht noch einmal abgelegt.',
  vorgabe_serie_fehlt: 'Das gewählte Hörspiel gibt es nicht mehr.',
  serie_name_doppelt: 'Einen Eintrag mit diesem Namen gab es schon. Der neue heißt „Kapitän Knopf (2)“.',
  art_geraten: 'Die Art ist geraten. Stimmt das?',
};

// Hinweise und Gründe „geht nicht“ (Design 7.3, Punkt 6, zweiter Absatz, und 6.1; Hinweise aus dem Vertrag ohne Design-Text).
export const HINWEISE = {
  kopierschutz: 'Diese Datei ist kopiergeschützt (zum Beispiel von Audible oder Apple Books). Die Box kann sie nicht abspielen. Nimm eine Datei ohne Kopierschutz.',
  nicht_lesbar: 'Die Datei ist kaputt oder unvollständig. Bitte noch einmal kopieren.',
  probedekodierung_fehlgeschlagen: 'Die Datei ist kaputt oder unvollständig. Bitte noch einmal kopieren.',
  keine_audiodateien: 'Darin ist keine Audiodatei.',
  ffprobe_fehlt: 'Das Prüfprogramm fehlt. Bitte {verwalter_dat} Bescheid sagen.',
  verschieben_fehlgeschlagen: 'Das Ablegen hat nicht geklappt. Versuche es später noch einmal, sonst frag {verwalter_akk}.',
  doppelt: 'Das gab es schon und wurde nicht noch einmal angelegt.',
  gruppe_unvollstaendig: 'Es fehlt noch eine Datei. {angekommen} von {anzahl} Dateien sind angekommen. Wähle die fehlende Datei noch einmal. Kommt sie nicht, wird mit den vorhandenen einsortiert und mit „Bitte ansehen“ markiert.',
  datei_fehlt: 'Eine Datei aus dieser Folge fehlt auf dem NAS. Sie wird beim nächsten Prüfen aus der Liste genommen.', // neu, nicht im Design
  pruefung_nicht_moeglich: 'Die Datei lässt sich gerade nicht prüfen. Bitte {verwalter_dat} Bescheid sagen.', // neu, nicht im Design
  doppelte_id_korrigiert: 'Ein Eintrag war doppelt vorhanden. Die jüngere Kopie wurde neu benannt.', // neu, nicht im Design
  serie_json_ungueltig_repariert: 'Die Angaben einer Serie waren beschädigt und sind repariert. Bitte kurz prüfen, ob alles stimmt.', // neu, nicht im Design
  reservierter_ordner: 'Ein Ordner mit einem reservierten Namen liegt im Medien-Ordner. Er wird nicht einsortiert.', // neu, nicht im Design
};

// Sätze der Status-Karte einer Box (Design 5.1.1). Platzhalter: anzeige, serie, folge, zeit, prozent.
export const STATUS = {
  spielt: '{anzeige} spielt „{serie}“ · {folge}.',
  spielt_ohne_serie: '{anzeige} spielt etwas.', // neu, nicht im Design
  pausiert: '{anzeige} ist pausiert bei „{serie}“.',
  bereit: '{anzeige} ist bereit. Es liegt kein Tobie auf.',
  herunterfahren: '{anzeige} geht gerade aus.',
  offline: '{anzeige} ist aus oder nicht im WLAN.',
  nie_gemeldet: '{anzeige} hat sich noch nicht gemeldet.',
  folge_mit_nummer: 'Folge {nummer}: {folge}',
  folge_ohne_nummer: '{folge}', // neu, nicht im Design
  akku: 'Akku {prozent} %.',
  akku_laedt: 'Akku {prozent} %, lädt.',
  akku_fast_leer: 'Akku fast leer ({prozent} %). Bitte laden.',
  zuletzt: 'Zuletzt gesehen: {zeit}. Akku war bei {prozent} %.',
  zuletzt_ohne_akku: 'Zuletzt gesehen: {zeit}.', // neu, nicht im Design
  konfig_wartet: 'Neue Zuordnungen kommen auf die Box, sobald sie wieder im WLAN ist.',
};

// Leere Zustände (Design 6.2): Bildbeschreibung, Satz, Knopf.
export const LEER = {
  bibliothek: { bild: 'leeres Regal mit Lücke und Note', satz: 'Noch nichts da. Tippe auf „Hinzufügen“.', knopf: 'Hinzufügen' },
  filter: { bild: 'Lupe mit Fragezeichen', satz: 'Nichts gefunden. Nimm einen Filter weg.', knopf: 'Filter zurücksetzen' },
  start: { bild: 'leeres Regal mit Lücke und Note', satz: 'Noch nichts da. Tippe in der Bibliothek auf „+“.', knopf: 'Zur Bibliothek' }, // Design 5.1 Punkt 5
  tobies: { bild: 'lächelnder Tobie über der Box', satz: 'Noch keine Tobies. Lege einen Tobie auf eine Box, dann erscheint er unter „Geräte“.', knopf: 'Zu den Geräten' },
  keine_box: { bild: 'schlafende Box mit Zzz und gezogenem Stecker', satz: 'Noch keine Box eingerichtet. Bitte {verwalter_dat} Bescheid sagen.', knopf: 'Jetzt neu laden' },
  suche: { bild: 'Lupe mit Fragezeichen', satz: 'Nichts gefunden zu „{suchwort}“.', knopf: 'Suche löschen' },
  papierkorb: { bild: 'Papierkorb mit Haken', satz: 'Der Papierkorb ist leer.', knopf: 'Zur Bibliothek' },
  gehoert: { bild: 'Kopfhörer mit leerem Diagramm', satz: 'Noch nichts gehört. Sobald eine Box spielt oder jemand reinhört, steht es hier.', knopf: 'Zur Bibliothek' },
};

// Seite „Geräte“ (Design 3.4, ersetzt „Mehr“, Runde 15). Boxen, Karten für neue Tobies, Abends, Zeile „Gehört“.
export const GERAETE = {
  titel: 'Geräte',
  abends: { titel: 'Abends', erklaerung: 'Gute Nacht und Leise-Zeiten' },
  gehoert: { titel: 'Wer hat was gehört?', erklaerung: 'Rangliste, Hörzeit pro Tag, Tageszeiten' }, // Titel Design 3.4; Erklärung nur im Prototyp (Stufe B)
  neuer_tobie: { titel: 'Neuer Tobie auf {box} – was soll er spielen?', zeile: 'Gerade aufgelegt, {zeit}.' }, // Design 7.1
  neue_tobies: { titel: '{anzahl} neue Tobies auf {box}' }, // Design 5.13 (N12)
  wartet: { titel: 'Wartet auf einen neuen Tobie', zeile1: 'Nächster neuer Tobie auf {box}', zeile2: 'spielt „{serie}“ · Nr. {nr} von {gesamt}', abbrechen: 'Nicht mehr warten' }, // Design 5.13
  platz_bekommen: { titel: 'Ein neuer Tobie hat einen Platz bekommen.', frage: 'Name geben?', name_geben: 'Name geben', spaeter: 'Später' }, // Design 5.13 (N11)
  nicht_zugeordnet: { titel: 'Konnte nicht zugeordnet werden', jetzt_zuordnen: 'Jetzt zuordnen' }, // Design 5.13 (N20); der Grund kommt vom Backend oder aus FEHLER
  grund_gesperrt: 'Änderungen sind gerade gesperrt.', // Design 5.13, Tabelle „Liste gesperrt“
};

// Tobies zuordnen, Meldungen und Namen (Design 5.4, 5.7, 5.13, 6.3, 7.1; Runde 17: R17-3, R17-5, R17-6, N27).
export const TOBIE = {
  ohne_name: 'Tobie ohne Namen', // Design 5.4, Ergänzung b
  zugeordnet_neu: 'Fertig: {tobie} spielt jetzt „{ziel}“.', // Design 5.4, neuer Tobie
  zugeordnet_umgehaengt: '{tobie} spielt jetzt „{ziel}“ (vorher „{vorher}“).', // Design 5.4, R17-3
  rueckgaengig: 'Rückgängig',
  rueckgaengig_gemacht: 'Rückgängig gemacht.', // neu, nicht im Design (Ansage für Screenreader, wie im Prototyp)
  vorher: 'Vorher: {vorher}', // Design 5.4: „Vorher: Kommissar Kralle · Zurückstellen“; der Punkt und „Zurückstellen“ sind ein eigener Knopf
  zurueckstellen: 'Zurückstellen',
  neuer_tobie_meldung: 'Neuer Tobie auf {box} – Zuordnen', // Design 5.13 (R17-6)
  zuordnen: 'Zuordnen',
  aufgelegt_zugeordnet: '{box}: Der neue Tobie spielt jetzt „{ziel}“.', // Design 5.13, Auflegen
  name_geben: 'Name geben',
  name_frage: 'Wie soll er heißen?', // Design 7.1 (Weg 1) und 5.13 (Weg 2, R17-5)
  name_hinweis: 'Du kannst das überspringen.',
  name_platzhalter: 'Name, zum Beispiel Farbe oder Tier', // Design 7.1
  plus_tobie: '+ Tobie', // Design 5.3 (N27)
  weiteren_tobie: 'Weiteren Tobie geben', // Design 5.3 (aria-label, X20f)
  einem_tobie_geben: 'Einem Tobie geben …', // Design 5.3
  noch_kein_tobie: 'Noch kein Tobie', // Design 5.3
  neue_tobies_punkt: '1 neuer Tobie', // Design 3.1, für Screenreader am Reiter „Geräte“
  neue_tobies_punkt_mehr: '{anzahl} neue Tobies', // neu, nicht im Design (Mehrzahl zu 3.1)
};

// Satz im Blatt „Leise-Zeit ändern“ (Design 5.8, N24).
export const LEISE = {
  gilt_fuer: 'Gilt für {tage}. Tage abwählen, wenn es nur für einzelne gelten soll.',
};

// Hochladen: echte Zustände während des Uploads (Design 5.6a, 7.3; R17-4).
export const UPLOAD = {
  bildschirm_anlassen: 'Bildschirm anlassen, bis es fertig ist.',
};

// Rahmen der Seite (Design 3.1, 3.2, 6, 6.3): Reiter, Kopf, Zustände, Meldungen. Paket A6.
export const SEITE = {
  titel: 'Tobi Box',
  testtitel: 'Tobi Box (Test)',
  bereiche: 'Bereiche', // aria-label der Reiterleiste (Design 14)
  reiter: { start: 'Start', bibliothek: 'Bibliothek', tobies: 'Tobies', geraete: 'Geräte' },
  begruessung: { morgen: 'Guten Morgen', tag: 'Guten Tag', abend: 'Guten Abend', nacht: 'Gute Nacht' }, // Design 3.1
  suchen: 'Suchen',
  technik: 'Technik',
  hinzufuegen: 'Hinzufügen',
  schliessen: 'Schließen',
  ok: 'OK',
  zurueck: { bibliothek: '‹ Bibliothek', geraete: '‹ Geräte', tobies: '‹ Tobies', technik: '‹ Technik' }, // Design 3.2
  seiten: { // Überschriften der Unterseiten (Design 3.2, 5.4, 5.9, 7.1)
    suche: 'Suche', serie: 'Serie', hinzufuegen: 'Hinzufügen', anlernen: 'Tobie anlernen', tobie: 'Tobie', neu: 'Neuer Tobie',
    neu_warten: 'Neuer Tobie', neu_ziel: 'Neuer Tobie erkannt', neu_queue: 'Später auflegen', geben: 'Welcher Tobie soll das spielen?',
    box: 'Box', gehoert: 'Gehört', playlist: 'Playlist', technik: 'Technik', technik_boxen: 'Boxen',
    technik_speicher: 'Speicher und Netz', technik_liste: 'Liste und Sicherung', technik_tobies: 'Tobies',
    technik_meldungen: 'Meldungen', technik_einstellungen: 'Einstellungen', technik_box: 'Box',
  },
  laedt: 'Wird geladen …', // neu, nicht im Design (nur für Screenreader neben den Platzhaltern)
  fehler_laden: {
    titel: 'Die Seite konnte nichts laden.',
    text: 'Home Assistant antwortet gerade nicht. Warte kurz und versuche es noch einmal. Wenn es so bleibt, sag {verwalter_dat} Bescheid.',
    knopf: 'Noch einmal versuchen',
  }, // Design 6
  verbindung_weg: {
    titel: 'Keine Verbindung zu Home Assistant.',
    text: 'Die Ansicht wird von selbst aktuell, sobald die Verbindung wieder da ist.',
    knopf: 'Jetzt neu laden',
  }, // Design 6
  liste_gesperrt: 'Änderungen sind gerade gesperrt. Bitte {verwalter_dat} Bescheid sagen.', // Design 6, für Nicht-Administratoren
  technik_nur_admin: 'Dieser Bereich ist nur für Administratoren. Wenn du etwas Technisches brauchst, frag {verwalter_akk}.', // Design 3.1
  veraltet: 'Die Seite ist veraltet. Bitte lade sie neu (am Handy: Seite nach unten ziehen oder Browser neu öffnen).', // Design 6
};

// Kacheln im Blatt „Was lädst du hoch?“ (Design 5.6): Titel, Zeile darunter, Satz für Screenreader.
export const KACHELN = {
  neu: {
    titel: 'Neu anlegen',
    zeile: 'Hörspiel, Buch, Album',
    satz: 'Alle Dateien gehören zusammen und werden etwas Neues.',
  },
  zu_vorhandenem: {
    titel: 'Zu Vorhandenem',
    zeile: 'Neue Folgen dazu',
    satz: 'Die Dateien werden neue Folgen in einem Hörspiel, das schon da ist.', // neu, nicht im Design
  },
  einzeln: {
    titel: 'Einzeln',
    zeile: 'Lied oder Folge für sich',
    satz: 'Jede Datei wird ein eigenes Lied oder eine eigene Folge.', // neu, nicht im Design
  },
  playlist: {
    titel: 'Playlist',
    zeile: 'Stufe C – Idee',
    satz: 'Die Dateien werden Einzeltitel und gehören der Playlist.', // neu, nicht im Design
  },
  sortier_du: {
    titel: 'Sortier du',
    zeile: 'Ich lese die Angaben',
    satz: 'Ich lese die Angaben in den Dateien (Album, Interpret, Titel). Dateien, die zum selben Album gehören, bleiben zusammen. Passt etwas zu einem Hörspiel, das schon da ist, kommt es dort dazu. Wenn ich unsicher bin, steht danach „Bitte ansehen“ da, und du kannst es ändern.',
  },
};

// Fehlertext zu einem Code. werte: Platzhalterwerte, optional admin: true.
// Für Administratoren steht bei unbekannten Codes und Standardtexten der Code dahinter.
export function fehlerText(code, werte = {}) {
  const bekannt = typeof code === 'string' && Object.prototype.hasOwnProperty.call(FEHLER, code);
  const text = fuellen(bekannt ? FEHLER[code] : FALLBACK, werte);
  if (werte.admin && (!bekannt || FEHLER[code] === FALLBACK)) return `${text} (Code: ${code})`;
  return text;
}

// Satz, Nebentext und Warnung für eine Box-Karte (Design 5.1.1).
// box: { anzeige, online (true|false|null), zustand, serie, folge, folge_nummer,
//        akku_prozent, lader, zeit_letzte_meldung, konfig_stand, abweichung_min }
export function statusSatz(box = {}) {
  const anzeige = box.anzeige || DEFAULT.box;
  const serie = box.serie || '';
  const prozent = box.akku_prozent;
  const laedt = box.lader === true;
  const konfigWartet = box.konfig_stand !== undefined && box.konfig_stand !== 'aktuell'
    && (box.online === false || (box.abweichung_min ?? 0) > 5);
  const nebe = [];
  const akku = (satz) => (typeof prozent === 'number' ? fuellen(satz, { prozent }) : '');

  if (box.online === null || box.online === undefined) {
    return { lage: 'nie_gemeldet', satz: fuellen(STATUS.nie_gemeldet, { anzeige }), nebentext: '', warnung: false };
  }

  let lage;
  let satz;
  let warnung = false;
  if (box.online === false) {
    lage = 'offline';
    satz = fuellen(STATUS.offline, { anzeige });
    if (box.zeit_letzte_meldung) {
      nebe.push(typeof prozent === 'number'
        ? fuellen(STATUS.zuletzt, { zeit: box.zeit_letzte_meldung, prozent })
        : fuellen(STATUS.zuletzt_ohne_akku, { zeit: box.zeit_letzte_meldung }));
    }
  } else if (box.zustand === 'spielt') {
    lage = 'spielt';
    if (serie) {
      const folge = box.folge_nummer !== undefined && box.folge_nummer !== null
        ? fuellen(STATUS.folge_mit_nummer, { nummer: box.folge_nummer, folge: box.folge || '' })
        : fuellen(STATUS.folge_ohne_nummer, { folge: box.folge || '' });
      satz = fuellen(STATUS.spielt, { anzeige, serie, folge });
    } else {
      satz = fuellen(STATUS.spielt_ohne_serie, { anzeige });
    }
    nebe.push(akku(laedt ? STATUS.akku_laedt : STATUS.akku));
  } else if (box.zustand === 'pausiert') {
    lage = 'pausiert';
    satz = fuellen(STATUS.pausiert, { anzeige, serie });
    nebe.push(akku(laedt ? STATUS.akku_laedt : STATUS.akku));
  } else if (box.zustand === 'herunterfahren') {
    lage = 'herunterfahren';
    satz = fuellen(STATUS.herunterfahren, { anzeige });
  } else {
    lage = 'bereit';
    satz = fuellen(STATUS.bereit, { anzeige });
    nebe.push(akku(laedt ? STATUS.akku_laedt : STATUS.akku));
  }

  // Akku ≤ 20 % ohne Laden: orange Warnung statt des normalen Akkutexts (Design 5.1.1).
  if (lage !== 'offline' && lage !== 'herunterfahren' && typeof prozent === 'number' && prozent <= 20 && !laedt) {
    warnung = true;
    nebe[nebe.length - 1] = fuellen(STATUS.akku_fast_leer, { prozent });
  }
  if (lage === 'herunterfahren') nebe.length = 0;
  if (konfigWartet) nebe.push(STATUS.konfig_wartet);

  return { lage, satz, nebentext: nebe.filter(Boolean).join(' '), warnung };
}

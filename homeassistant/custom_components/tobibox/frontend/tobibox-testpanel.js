/* Tobi Box: Testpanel unter /tobibox-neu (Paket A0b). Nur zum Messen; wird mit TESTPANEL = False in const.py abgeschaltet. */
const MESS_URL = '/api/tobibox/testpanel/messung';
const FORMATE = {
  mp3: 'audio/mpeg', 'm4a/aac': 'audio/mp4; codecs="mp4a.40.2"', m4b: 'audio/mp4', flac: 'audio/flac',
  'ogg/vorbis': 'audio/ogg; codecs="vorbis"', opus: 'audio/ogg; codecs="opus"', wav: 'audio/wav',
};
const zeit = (s) => (Number.isFinite(s) ? `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}` : '–');

class TobiboxTestpanel extends HTMLElement {
  set hass(h) {
    const erst = !this._hass;
    this._hass = h;
    if (erst) this._start();
  }
  set narrow(n) { this._narrow = n; }
  $(id) { return this.querySelector(`#${id}`); }
  async _ws(msg) { return this._hass.connection.sendMessagePromise(msg); }
  _sag(id, text) { this.$(id).textContent = text; }

  _start() {
    this.innerHTML = `<style>
      tobibox-testpanel{display:block;height:100%;overflow:auto;box-sizing:border-box;padding:16px;font:14px/1.4 system-ui,sans-serif;color:var(--primary-text-color);background:var(--primary-background-color)}
      tobibox-testpanel section{background:var(--card-background-color,#fff);border-radius:12px;padding:12px 16px;margin:0 0 12px}
      tobibox-testpanel h2{font-size:16px;margin:0 0 8px}
      tobibox-testpanel select,tobibox-testpanel input,tobibox-testpanel button{font:inherit;max-width:100%;margin:2px 0}
      tobibox-testpanel pre{white-space:pre-wrap;word-break:break-word;margin:6px 0 0}
      tobibox-testpanel audio{width:100%} tobibox-testpanel img{max-width:100%;max-height:200px}
    </style>
    <h1>Tobi Box: Testpanel</h1>
    <section><h2>a) Abspielen</h2>
      <select id="serie"><option>Bibliothek wird geladen …</option></select>
      <select id="folge"></select> <select id="track" hidden></select>
      <audio id="player" controls preload="metadata" playsinline></audio>
      <div><button id="zurueck">−30 s</button> <button id="vor">+30 s</button> <span id="zeit">0:00 / –</span></div>
      <pre id="aus-a"></pre></section>
    <section><h2>b) Foto-Auswahl</h2><input id="foto" type="file" accept="image/*"><br><img id="vorschau" alt=""></section>
    <section><h2>c) Tastatur</h2><input id="text" type="text" placeholder="Hier tippen"></section>
    <section><h2>d) Safe Area</h2><pre id="aus-d"></pre></section>
    <section><h2>e) Upload messen</h2><input id="mess" type="file"> <button id="senden">Senden (wird nicht gespeichert)</button><pre id="aus-e"></pre></section>
    <section><h2>f) ffmpeg messen</h2><button id="ffmpeg">ffmpeg messen</button> (nutzt die oben gewählte Folge)<pre id="aus-f"></pre></section>
    <section><h2>g) Formate (canPlayType)</h2><pre id="aus-g"></pre></section>`;
    this._formate(); this._safeArea();
    this.$('serie').onchange = () => this._serieWahl();
    this.$('folge').onchange = () => this._folgeWahl();
    this.$('track').onchange = () => this._spiele(Number(this.$('track').value));
    this.$('zurueck').onclick = () => this._springe(-30);
    this.$('vor').onclick = () => this._springe(30);
    this.$('foto').onchange = (e) => { const f = e.target.files[0]; this.$('vorschau').src = f ? URL.createObjectURL(f) : ''; };
    this.$('senden').onclick = () => this._messeUpload();
    this.$('ffmpeg').onclick = () => this._messeFfmpeg();
    const p = this.$('player');
    p.ontimeupdate = p.onloadedmetadata = () => this._sag('zeit', `${zeit(p.currentTime)} / ${zeit(p.duration)}`);
    p.onended = () => this._weiter();
    p.onplaying = () => this._gespielt();
    p.onerror = () => this._fehler(p.error);
    this._serien();
  }

  /* --- a) Abspielen --- */
  async _serien() {
    try {
      const r = await this._ws({ type: 'tobibox/serien/list' });
      const sel = this.$('serie');
      sel.innerHTML = '';
      sel.add(new Option('Serie wählen …', ''));
      r.serien.forEach((x) => sel.add(new Option(`${x.name} (${x.anzahl_folgen})`, x.id)));
    } catch (e) { this._sag('aus-a', `Bibliothek nicht lesbar: ${e.message || e.code}`); }
  }
  async _serieWahl() {
    this._folgen = []; this.$('folge').innerHTML = ''; this.$('track').hidden = true;
    const id = this.$('serie').value;
    if (!id) return;
    const s = await this._ws({ type: 'tobibox/serie/get', serie_id: id });
    this._serieId = id; this._folgen = s.folgen;
    this.$('folge').add(new Option('Folge wählen …', ''));
    s.folgen.forEach((f, i) => { const o = new Option(`${f.anzeige || f.name} (${f.tracks} Track${f.tracks > 1 ? 's' : ''})`, i); this.$('folge').add(o); });
  }
  _folgeWahl() {
    const f = this._folgen[this.$('folge').value];
    const tr = this.$('track');
    tr.innerHTML = ''; tr.hidden = !f || f.tracks < 2;
    if (!f) return;
    for (let i = 0; i < f.tracks; i++) tr.add(new Option(`Track ${i + 1}`, i));
    this._spiele(0);
  }
  async _spiele(track, nochmal = true) {
    const f = this._folgen[this.$('folge').value];
    if (!f) return;
    this._track = track; this.$('track').value = track;
    const msg = { type: 'tobibox/audio/bereit', serie_id: this._serieId, folge_id: f.name };
    if (f.tracks > 1) msg.track = track;
    try {
      const r = await this._ws(msg);
      const p = this.$('player');
      p.src = this._hass.hassUrl(r.pfad);
      this._nochmal = nochmal; this._start_ms = performance.now();
      await p.play().catch((e) => this._sag('aus-a', `play() abgelehnt: ${e.name}. Bitte selbst auf Wiedergabe tippen.`));
      this._mediaSession(f);
    } catch (e) { this._sag('aus-a', `audio/bereit fehlgeschlagen: ${e.code || ''} ${e.message || ''}`); }
  }
  _gespielt() {
    if (this._ende_ms) { this._sag('aus-a', `Trackwechsel: Lücke ${Math.round(performance.now() - this._ende_ms)} ms (Track ${this._track + 1}).`); this._ende_ms = 0; }
    else if (this._start_ms) this._sag('aus-a', `Start nach ${Math.round(performance.now() - this._start_ms)} ms.`);
    this._start_ms = 0;
  }
  _weiter() {
    const f = this._folgen[this.$('folge').value];
    if (f && this._track + 1 < f.tracks) { this._ende_ms = performance.now(); this._spiele(this._track + 1); }
    else this._sag('aus-a', 'Ende erreicht.');
  }
  _fehler(err) {
    this._sag('aus-a', `Abspielfehler (MediaError ${err && err.code}). ${this._nochmal ? 'Neuer Link wird geholt.' : 'Zweiter Versuch fehlgeschlagen.'}`);
    if (this._nochmal) this._spiele(this._track || 0, false);
  }
  _springe(s) { const p = this.$('player'); p.currentTime = Math.max(0, Math.min(p.duration || 1e9, p.currentTime + s)); }
  _mediaSession(f) {
    if (!('mediaSession' in navigator)) { this._sag('aus-a', 'mediaSession gibt es hier nicht.'); return; }
    const p = this.$('player'); const m = navigator.mediaSession;
    m.metadata = new MediaMetadata({ title: f.anzeige || f.name, artist: 'Tobi Box Test', album: this.$('serie').selectedOptions[0].textContent });
    m.setActionHandler('play', () => p.play());
    m.setActionHandler('pause', () => p.pause());
    m.setActionHandler('seekbackward', () => this._springe(-30));
    m.setActionHandler('seekforward', () => this._springe(30));
    m.setActionHandler('nexttrack', () => this._weiter());
  }

  /* --- d, g) Anzeigen --- */
  _safeArea() {
    const sonde = document.createElement('div');
    sonde.style.cssText = 'position:absolute;visibility:hidden;padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)';
    this.appendChild(sonde);
    const c = getComputedStyle(sonde);
    this._sag('aus-d', `oben ${c.paddingTop}, rechts ${c.paddingRight}, unten ${c.paddingBottom}, links ${c.paddingLeft}\nFenster ${innerWidth} x ${innerHeight}, narrow: ${this._narrow}`);
    sonde.remove();
  }
  _formate() {
    const p = document.createElement('audio');
    this._sag('aus-g', Object.entries(FORMATE).map(([n, t]) => `${n}: ${p.canPlayType(t) || 'nein'}`).join('\n'));
  }

  /* --- e) Upload messen --- */
  async _messeUpload() {
    const f = this.$('mess').files[0];
    if (!f) { this._sag('aus-e', 'Bitte zuerst eine Datei wählen.'); return; }
    const a = this._hass.auth;
    try { if (a && a.expired && a.refreshAccessToken) await a.refreshAccessToken(); } catch { /* weiter */ }
    const xhr = new XMLHttpRequest(); const t0 = performance.now();
    const mb = (n) => (n / 1048576).toFixed(1);
    xhr.open('POST', this._hass.hassUrl(MESS_URL));
    xhr.setRequestHeader('Authorization', `Bearer ${a && a.data && a.data.access_token}`);
    xhr.upload.onprogress = (e) => this._sag('aus-e', `${mb(e.loaded)} von ${mb(f.size)} MB … ${((performance.now() - t0) / 1000).toFixed(0)} s`);
    const ende = (text) => this._sag('aus-e', text);
    xhr.onerror = xhr.ontimeout = () => ende(`Abgebrochen nach ${((performance.now() - t0) / 1000).toFixed(1)} s (Verbindung getrennt?). Bitte so melden.`);
    xhr.onload = () => {
      const s = (performance.now() - t0) / 1000;
      let b = {}; try { b = JSON.parse(xhr.responseText); } catch { /* kein JSON */ }
      if (xhr.status !== 200) { ende(`HTTP ${xhr.status} nach ${s.toFixed(1)} s ${(b.fehler && b.fehler.code) || ''}`); return; }
      ende(`${mb(b.bytes)} MB in ${s.toFixed(1)} s = ${(b.bytes / 1048576 / s).toFixed(2)} MB/s (${(b.bytes * 8 / 1e6 / s).toFixed(1)} Mbit/s). Server zählte ${b.bytes} Bytes${b.bytes === f.size ? ' (passt)' : ' (PASST NICHT zu ' + f.size + ')'}.`);
    };
    xhr.send(f);
  }

  /* --- f) ffmpeg messen --- */
  async _messeFfmpeg() {
    const f = this._folgen && this._folgen[this.$('folge').value];
    const msg = { type: 'tobibox/testpanel/ffmpeg_messen' };
    if (f) { msg.serie_id = this._serieId; msg.folge_id = f.name; if (f.tracks > 1) msg.track = 0; }
    this._sag('aus-f', 'Läuft … (bei 10 Minuten Audio kann das dauern)');
    try {
      const r = await this._ws(msg);
      if (!r.ffmpeg) { this._sag('aus-f', r.meldung); return; }
      const u = r.umwandlung;
      this._sag('aus-f', [r.version, `Quelle: ${r.quelle}`, 'AAC-Encoder:', ...r.aac_encoder.map((z) => '  ' + z),
        u ? `Umwandeln: ${u.zustand}, ${u.sekunden} s für ${u.audio_s ?? '?'} s Audio, Faktor ${u.faktor ?? '?'} x Echtzeit${u.text ? ' – ' + u.text : ''}` : 'Keine Folge gewählt: nur Version und Encoder.'].join('\n'));
    } catch (e) { this._sag('aus-f', `Fehler: ${e.code || ''} ${e.message || ''}`); }
  }
}
customElements.define('tobibox-testpanel', TobiboxTestpanel);

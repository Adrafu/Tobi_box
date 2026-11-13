/* Tobi Box: Testpanel unter /tobibox-neu (Paket A0b). Nur zum Messen; wird mit TESTPANEL = False in const.py abgeschaltet. */
const MESS_URL = '/api/tobibox/testpanel/messung';
const FORMATE = {
  mp3: 'audio/mpeg', 'm4a/aac': 'audio/mp4; codecs="mp4a.40.2"', m4b: 'audio/mp4', flac: 'audio/flac',
  'ogg/vorbis': 'audio/ogg; codecs="vorbis"', opus: 'audio/ogg; codecs="opus"', wav: 'audio/wav',
};
/* Bewegung (Abschnitt h): Feder-Kurve und Rückfall wie in docs/egm/ha-ui/prototyp.html */
const FEDER = 'linear(0, 0.031, 0.108, 0.21, 0.322, 0.435, 0.541, 0.637, 0.72, 0.791, 0.849, 0.896, 0.932, 0.96, 0.98, 0.995, 1.004, 1.01, 1.014, 1.015, 1.015, 1.014, 1.013, 1.011, 1.009, 1.008, 1)';
const KURVE = 'cubic-bezier(.2, 0, 0, 1)';
const FEDER_MS = 500;
const feder = () => (window.CSS && CSS.supports && CSS.supports('transition-timing-function', 'linear(0,1)') ? FEDER : KURVE);
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
      tobibox-testpanel h3{font-size:14px;margin:12px 0 4px}
      tobibox-testpanel .tt-karte{margin:8px 0;padding:12px 16px;border-radius:12px;background:var(--primary-color,#03a9f4);color:#fff}
      tobibox-testpanel dialog.tt-d{position:fixed;inset:0;width:100%;height:100%;max-width:none;max-height:none;margin:0;padding:0;border:0;background:transparent;overflow:hidden}
      tobibox-testpanel dialog.tt-d::backdrop{background:transparent}
      tobibox-testpanel .tt-blatt{position:absolute;left:0;right:0;bottom:0;max-height:70%;box-sizing:border-box;padding:8px 16px 24px;background:var(--card-background-color,#fff);color:var(--primary-text-color);border-radius:16px 16px 0 0;box-shadow:0 -2px 16px rgba(0,0,0,.3);transform:translateY(100%);transition:transform ${FEDER_MS}ms var(--tt-feder);touch-action:none}
      tobibox-testpanel .tt-blatt.an{transform:none}
      tobibox-testpanel .tt-blatt.zieht{transition:none}
      tobibox-testpanel .tt-griff{width:40px;height:5px;border-radius:3px;background:var(--divider-color,#999);margin:0 auto 8px}
      tobibox-testpanel .tt-kopf{display:flex;justify-content:space-between;align-items:center}
      tobibox-testpanel .tt-kopf button{font-size:24px;min-width:44px;min-height:44px}
      tobibox-testpanel.tt-hinten-an{transform-origin:50% 50%;transform:scale(calc(1 - .06 * var(--tt-t, 0)));border-radius:calc(14px * var(--tt-t, 0));filter:brightness(calc(1 - .2 * var(--tt-t, 0)));transition:transform ${FEDER_MS}ms var(--tt-feder),border-radius ${FEDER_MS}ms var(--tt-feder),filter ${FEDER_MS}ms ease}
      tobibox-testpanel.tt-hinten{--tt-t:1}
      tobibox-testpanel.tt-zieht{transition:none}
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
    <section><h2>g) Formate (canPlayType)</h2><pre id="aus-g"></pre></section>
    <section><h2>h) Bewegung</h2>
      <h3>h1 Cover-Flug mit View Transition (Elemente im Shadow-Root)</h3>
      <div id="h1-host"></div><pre id="aus-h1"></pre>
      <h3>h2 Rückfall FLIP (Web Animations)</h3>
      <div id="h2-host"></div><pre id="aus-h2"></pre>
      <h3>h3 Feder-Kurve</h3>
      <button id="h3-knopf">Karte hereinfahren</button><div id="h3-karte" class="tt-karte">Diese Karte federt herein.</div><pre id="aus-h3"></pre>
      <h3>h4 iOS-Blatt-Effekt</h3>
      <button id="h4-auf">Blatt öffnen</button><pre id="aus-h4"></pre>
      <h3>h5 Anzeige</h3><pre id="aus-h5"></pre>
      <dialog id="h4-dlg" class="tt-d" aria-label="Test-Blatt"><div id="h4-blatt" class="tt-blatt">
        <div class="tt-griff"></div>
        <div class="tt-kopf"><b>Test-Blatt</b><button id="h4-x" aria-label="Schließen">×</button></div>
        <p>Wische nach unten, tippe auf × oder tippe neben das Blatt, um es zu schließen.</p></div></dialog>
    </section>`;
    this._formate(); this._safeArea(); this._bewegung();
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

  disconnectedCallback() {
    const st = document.getElementById('tobibox-testpanel-vt');
    if (st) st.remove();
    if (this._rmMQ) this._rmMQ.removeEventListener('change', this._rmFn);
  }

  /* --- h) Bewegung --- */
  _bewegung() {
    this.style.setProperty('--tt-feder', feder());
    this._vtStil();
    this._buehne(this.$('h1-host'), 'vt', 'aus-h1');
    this._buehne(this.$('h2-host'), 'flip', 'aus-h2');
    this.$('h3-knopf').onclick = () => this._feder();
    this._sag('aus-h3', `linear() in Übergängen: ${window.CSS && CSS.supports('transition-timing-function', 'linear(0,1)') ? 'ja' : 'nein'}`);
    this.$('h4-auf').onclick = () => this._blattAuf();
    const dlg = this.$('h4-dlg'), blatt = this.$('h4-blatt');
    this.$('h4-x').onclick = () => this._blattZu();
    dlg.addEventListener('click', (e) => { if (e.target === dlg) this._blattZu(); });
    dlg.addEventListener('cancel', (e) => { e.preventDefault(); this._blattZu(); });
    this._blattWischen(blatt);
    const mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    this._rmMQ = mq;
    this._rmFn = () => this._anzeige();
    if (mq) mq.addEventListener('change', this._rmFn);
    this._anzeige();
  }
  _anzeige() {
    const rm = this._rmMQ && this._rmMQ.matches;
    const ua = (navigator.userAgent || '').replace(/^Mozilla\/5\.0 /, '').slice(0, 120);
    this._sag('aus-h5', `Reduzierte Bewegung: ${rm ? 'ja (die echte Seite würde nur überblenden; dieser Test bewegt trotzdem)' : 'nein'}\nBrowser: ${ua}`);
  }
  /* Die ::view-transition-Regeln wirken nur im Dokument, nicht im Shadow-DOM von Home Assistant. */
  _vtStil() {
    if (document.getElementById('tobibox-testpanel-vt')) return;
    const st = document.createElement('style');
    st.id = 'tobibox-testpanel-vt';
    st.textContent = `::view-transition-group(pcover){animation-duration:${FEDER_MS}ms;animation-timing-function:${feder()};z-index:2}
::view-transition-group(pdlg){z-index:1}
::view-transition-old(pcover),::view-transition-new(pcover){height:100%;width:100%;object-fit:cover;mix-blend-mode:normal}
::view-transition-new(pcover){animation:none;opacity:1}
::view-transition-old(pcover){animation:tt-raus 250ms ease both}
@keyframes tt-raus{to{opacity:0}}`;
    document.head.appendChild(st);
  }
  /* Kleine Bühne im Shadow-Root: Cover, das in eine „Vollansicht“ fliegt. modus: 'vt' (View Transition) oder 'flip'. */
  _buehne(host, modus, aus) {
    const sr = host.attachShadow({ mode: 'open' });
    sr.innerHTML = `<style>
      .stage{position:relative;min-height:120px;border:1px solid var(--divider-color,#ccc);border-radius:12px;padding:12px;box-sizing:border-box;overflow:hidden;display:flex;align-items:center;gap:12px}
      .cover{display:block;border:0;padding:0;background:linear-gradient(135deg,#ff7043,#5c6bc0);border-radius:12px;color:#fff;font:inherit}
      .mini{width:64px;height:64px}
      .voll{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;background:var(--card-background-color,#fff)}
      .voll[hidden]{display:none}
      .gross{width:150px;height:150px;border-radius:20px}
      button{font:inherit}
    </style>
    <div class="stage"><button class="cover mini" aria-label="Vollansicht öffnen"></button><span>Tipp auf das Cover</span>
      <div class="voll" hidden><button class="cover gross" aria-label="Cover"></button><button class="zu">Schließen</button></div></div>`;
    const mini = sr.querySelector('.mini'), gross = sr.querySelector('.gross'), voll = sr.querySelector('.voll');
    const zeigen = (auf) => { voll.hidden = !auf; };
    const name = (el, n) => { if (n) el.style.setProperty('view-transition-name', n); else el.style.removeProperty('view-transition-name'); };
    const alle = () => { [mini, gross, voll].forEach((e) => name(e, '')); };
    const lauf = (auf) => {
      if (modus === 'vt') this._h1(auf, { mini, gross, voll, zeigen, name, alle }, aus);
      else this._h2(auf, { mini, gross, voll, zeigen }, aus);
    };
    mini.onclick = () => lauf(true);
    sr.querySelector('.zu').onclick = () => lauf(false);
  }
  _h1(auf, e, aus) {
    const z = [`API document.startViewTransition: ${typeof document.startViewTransition === 'function' ? 'ja' : 'nein'}`];
    const zeige = () => this._sag(aus, z.join('\n'));
    if (typeof document.startViewTransition !== 'function') { e.zeigen(auf); z.push('Ohne API einfach umgeschaltet (hier greift der Rückfall h2).'); zeige(); return; }
    const t0 = performance.now();
    const ms = () => `${Math.round(performance.now() - t0)} ms`;
    e.name(auf ? e.mini : e.gross, 'pcover');
    if (!auf) e.name(e.voll, 'pdlg');
    let t;
    try {
      t = document.startViewTransition(() => {
        e.alle();
        e.zeigen(auf);
        e.name(auf ? e.gross : e.mini, 'pcover');
        if (auf) e.name(e.voll, 'pdlg');
      });
    } catch (err) { e.alle(); e.zeigen(auf); z.push(`startViewTransition warf: ${err.name}: ${err.message}`); zeige(); return; }
    z.push(`Transition: gestartet (${auf ? 'öffnen' : 'schließen'})`);
    const bestand = [];
    const messen = (wann) => {
      let n = 0, vt = 0, cover = 0, br = '?', dauer = '?';
      try {
        const an = document.documentElement.getAnimations({ subtree: true });
        n = an.length;
        an.forEach((a) => {
          const p = a.effect && a.effect.pseudoElement;
          if (p && p.indexOf('::view-transition') === 0) { vt++; if (p.indexOf('(pcover)') > -1) cover++; }
        });
      } catch (err) { z.push(`getAnimations warf: ${err.name}`); }
      try {
        const cs = getComputedStyle(document.documentElement, '::view-transition-group(pcover)');
        br = cs.width; dauer = cs.animationDuration;
      } catch { /* Pseudo-Stil nicht lesbar */ }
      bestand.push({ wann, n, vt, cover, br, dauer });
    };
    t.ready.then(() => {
      z.push(`ready erfüllt nach ${ms()}`);
      messen('bei ready');
      setTimeout(() => {
        messen('+150 ms');
        const zeilen = bestand.map((m) => `  ${m.wann}: Animationen ${m.n}, davon View-Transition ${m.vt}, davon am Cover ${m.cover}; Breite Cover-Gruppe ${m.br}; Dauer ${m.dauer}`);
        z.push('Laufende Animationen (documentElement, subtree):', ...zeilen);
        const ok = bestand.some((m) => m.cover > 0);
        z.push(`Cover von den Pseudo-Elementen animiert: ${ok ? 'JA' : 'NEIN'}`);
        if (!ok) z.push('Hinweis: Elemente im Shadow-DOM wurden nicht erfasst. Dann bleibt nur der Rückfall FLIP (h2).');
        zeige();
      }, 150);
    }, (err) => { z.push(`ready ABGELEHNT: ${err && err.name}: ${err && err.message}`); zeige(); });
    const ende = () => e.alle();
    t.finished.then(() => { z.push(`finished erfüllt nach ${ms()}`); zeige(); ende(); },
      (err) => { z.push(`finished ABGELEHNT: ${err && err.name}: ${err && err.message}`); zeige(); ende(); });
    t.updateCallbackDone.catch(() => {});
    zeige();
  }
  _h2(auf, e, aus) {
    const z = [];
    const t0 = performance.now();
    if (typeof Element.prototype.animate !== 'function') { e.zeigen(auf); this._sag(aus, 'el.animate gibt es hier nicht.'); return; }
    const el = e.gross;
    const von = (auf ? e.mini : el).getBoundingClientRect();
    if (auf) e.zeigen(true);
    const nach = (auf ? el : e.mini).getBoundingClientRect();
    const tr = `translate(${von.left - nach.left}px,${von.top - nach.top}px) scale(${von.width / nach.width},${von.height / nach.height})`;
    el.style.transformOrigin = '0 0';
    const kf = auf ? [{ transform: tr }, { transform: 'none' }] : [{ transform: 'none' }, { transform: tr }];
    let an, kurve = 'Feder';
    try { an = el.animate(kf, { duration: FEDER_MS, easing: feder(), fill: auf ? 'none' : 'forwards' }); }
    catch (err) { kurve = `Rückfall-Kurve (${err.name})`; an = el.animate(kf, { duration: FEDER_MS, easing: KURVE, fill: auf ? 'none' : 'forwards' }); }
    z.push(`FLIP gestartet (${auf ? 'öffnen' : 'schließen'}), Kurve: ${kurve}, Zustand: ${an.playState}`);
    this._sag(aus, z.join('\n'));
    const fertig = () => {
      el.style.transformOrigin = '';
      if (!auf) { e.zeigen(false); an.cancel(); }
      z.push(`FLIP fertig nach ${Math.round(performance.now() - t0)} ms (Soll ${FEDER_MS})`);
      this._sag(aus, z.join('\n'));
    };
    an.finished.then(fertig, (err) => { z.push(`FLIP abgebrochen: ${err && err.name}`); this._sag(aus, z.join('\n')); });
  }

  /* h3: Karte fährt mit linear()-Feder herein (CSS-Übergang) */
  _feder() {
    const k = this.$('h3-karte');
    const ok = window.CSS && CSS.supports && CSS.supports('transition-timing-function', 'linear(0,1)');
    k.style.transition = 'none'; k.style.transform = 'translateY(90px)'; k.style.opacity = '0';
    void k.offsetWidth;
    const t0 = performance.now();
    k.style.transition = `transform ${FEDER_MS}ms ${feder()}, opacity 250ms ease`;
    k.style.transform = 'none'; k.style.opacity = '1';
    const n = k.getAnimations ? k.getAnimations().length : '?';
    let min = 0, fertig = false;
    const lies = () => {
      try { min = Math.min(min, new DOMMatrix(getComputedStyle(k).transform).m42); } catch { /* kein DOMMatrix */ }
      if (!fertig && performance.now() - t0 < FEDER_MS + 150) requestAnimationFrame(lies);
    };
    requestAnimationFrame(lies);
    const zeile = (t) => this._sag('aus-h3', `linear() in Übergängen: ${ok ? 'ja' : 'nein'}\nÜbergänge gestartet: ${n}${t}`);
    zeile('');
    const ende = (e) => {
      if (e.propertyName !== 'transform') return;
      fertig = true; k.removeEventListener('transitionend', ende);
      zeile(`\ntransitionend nach ${Math.round(performance.now() - t0)} ms; Überschwingen über das Ziel: ${min < -0.3 ? `ja (${(-min).toFixed(1)} px)` : 'nicht gemessen'}`);
    };
    k.addEventListener('transitionend', ende);
  }

  /* h4: iOS-Blatt: das Panel dahinter wird kleiner, rund und dunkler; die HA-Kopfleiste bleibt */
  _blattAuf() {
    const dlg = this.$('h4-dlg'), blatt = this.$('h4-blatt');
    if (dlg.open) return;
    this._h4zu = false;
    const p = this.parentElement || (this.getRootNode() && this.getRootNode().host);
    this._h4p = p;
    if (p) { this._h4bg = p.style.background; p.style.background = '#000'; }
    this.classList.add('tt-hinten-an');
    blatt.classList.remove('an', 'zieht'); blatt.style.transform = '';
    dlg.showModal();
    void blatt.offsetWidth; void this.offsetWidth;
    blatt.classList.add('an'); this.classList.add('tt-hinten');
    setTimeout(() => {
      const cs = getComputedStyle(this);
      let skala = '?';
      try { skala = new DOMMatrix(cs.transform).a.toFixed(3); } catch { /* kein DOMMatrix */ }
      this._sag('aus-h4', `Blatt offen. Panel dahinter: Skala ${skala} (Soll 0,940), Ecken ${cs.borderTopLeftRadius}, Helligkeit ${cs.filter}.\nHintergrund hinter dem Panel gesetzt auf: ${p ? p.tagName.toLowerCase() : 'nichts gefunden'}. Kopfleiste von HA: bleibt, wie sie ist (bitte ansehen).`);
    }, FEDER_MS + 100);
  }
  _blattZu() {
    const dlg = this.$('h4-dlg'), blatt = this.$('h4-blatt');
    if (!dlg.open || this._h4zu) return;
    this._h4zu = true;
    blatt.classList.remove('an', 'zieht'); blatt.style.transform = '';
    this.classList.remove('tt-hinten', 'tt-zieht'); this.style.removeProperty('--tt-t');
    setTimeout(() => {
      dlg.close();
      this.classList.remove('tt-hinten-an');
      if (this._h4p) this._h4p.style.background = this._h4bg || '';
      this._sag('aus-h4', 'Blatt geschlossen.');
    }, FEDER_MS + 50);
  }
  _blattWischen(blatt) {
    let y0 = null, t0 = 0, dy = 0;
    blatt.addEventListener('pointerdown', (e) => {
      if (e.target.closest('button')) return;
      y0 = e.clientY; t0 = performance.now(); dy = 0;
      try { blatt.setPointerCapture(e.pointerId); } catch { /* egal */ }
      blatt.classList.add('zieht'); this.classList.add('tt-zieht');
    });
    blatt.addEventListener('pointermove', (e) => {
      if (y0 === null) return;
      dy = Math.max(0, e.clientY - y0);
      blatt.style.transform = `translateY(${dy}px)`;
      this.style.setProperty('--tt-t', String(Math.max(0, 1 - dy / (blatt.offsetHeight || 1))));
    });
    const los = () => {
      if (y0 === null) return;
      const v = dy / Math.max(1, performance.now() - t0);
      y0 = null;
      blatt.classList.remove('zieht'); this.classList.remove('tt-zieht');
      if (dy > blatt.offsetHeight * 0.25 || v > 0.6) { this._blattZu(); return; }
      blatt.style.transform = ''; this.style.removeProperty('--tt-t');
    };
    blatt.addEventListener('pointerup', los);
    blatt.addEventListener('pointercancel', los);
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

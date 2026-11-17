/* Tests: der Player sendet für „Gehört“ (Stufe B, Paket B4) mit jedem `hoerstelle/set` die Kennung `spieler` (einmal je Player-Instanz) und `spielt`, aber nur, wenn
 * `hello` die Fähigkeit `gehoert` meldet (Vertrag 41: eine ältere HA lehnt die Felder mit `invalid_format` ab). Aufruf: node --test homeassistant/tests/frontend
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { weg, MIT_DOM } from './dom-helfer.mjs';
import { mockAudio, spielSeite, starteSerie, setAufrufe, zeit, REIN } from './player-helfer.mjs';

const P = await import('../../custom_components/tobibox/frontend/player.js');

function mit(name, fn) {
  test(name, MIT_DOM, async (t) => {
    const au = await mockAudio();
    try { await fn(t, au); } finally { weg(); au.zurueck(); try { window.localStorage.clear(); } catch { /* ohne */ } }
  });
}

test('neueSpielerId(): 8 bis 64 Zeichen aus [A-Za-z0-9_-], bei jedem Aufruf eine andere (auch ohne crypto.randomUUID)', () => {
  const a = P.neueSpielerId();
  assert.match(a, /^[A-Za-z0-9_-]{8,64}$/);
  assert.notEqual(a, P.neueSpielerId());
  const uuid = globalThis.crypto.randomUUID;
  Object.defineProperty(globalThis.crypto, 'randomUUID', { value: undefined, configurable: true });
  try { assert.match(P.neueSpielerId(), /^[A-Za-z0-9_-]{8,64}$/); } finally { Object.defineProperty(globalThis.crypto, 'randomUUID', { value: uuid, configurable: true }); }
});

mit('Mit gehoert: jede Hörstelle trägt dieselbe Kennung `spieler`; `spielt` ist wahr beim Spielen und falsch nach der Pause', async () => {
  const s = await spielSeite({ hash: '#serie-s1', faehigkeiten: [...REIN, 'gehoert'] });
  const a = await starteSerie(s);
  zeit(a, 33);
  s.sp._speichere(true);
  s.q('.mini .mplay').click();
  await s.flush(6);
  const sets = setAufrufe(s);
  assert.equal(sets.length, 2);
  assert.match(sets[0].spieler, /^[A-Za-z0-9_-]{8,64}$/);
  assert.equal(sets[1].spieler, sets[0].spieler, 'eine Kennung je Player');
  assert.deepEqual(sets.map((x) => x.spielt), [true, false]);
  assert.equal(sets[0].position_s, 33);
  assert.equal(s.m.aufrufe('tobibox/hoerstelle/set').length, 2, 'der Mock hat beides angenommen (spieler und spielt mit gehoert erlaubt)');
});

mit('Mit gehoert: das Ende der Folge (`fertig`) sendet die Kennung und spielt = falsch', async () => {
  const s = await spielSeite({ hash: '#serie-s1', faehigkeiten: [...REIN, 'gehoert'] });
  await starteSerie(s);
  s.sp._speichere(true, { fertig: true });
  await s.flush(4);
  const x = setAufrufe(s).at(-1);
  assert.equal(x.fertig, true);
  assert.equal(x.spielt, false);
  assert.ok(x.spieler);
});

mit('Jede Player-Instanz hat ihre eigene Kennung (zwei Fenster zählen zwei Sitzungen)', async () => {
  const s1 = await spielSeite({ hash: '#serie-s1', faehigkeiten: [...REIN, 'gehoert'] });
  const id1 = s1.sp._spielerId;
  weg();
  const s2 = await spielSeite({ hash: '#serie-s1', faehigkeiten: [...REIN, 'gehoert'] });
  assert.notEqual(s2.sp._spielerId, id1);
  assert.ok(id1);
});

mit('Ohne die Fähigkeit gehoert (ältere HA): weder `spieler` noch `spielt` (sonst invalid_format)', async () => {
  const s = await spielSeite({ hash: '#serie-s1' });
  const a = await starteSerie(s);
  zeit(a, 33);
  s.sp._speichere(true);
  s.q('.mini .mplay').click();
  await s.flush(6);
  const sets = setAufrufe(s);
  assert.equal(sets.length, 2);
  for (const x of sets) assert.ok(!('spieler' in x) && !('spielt' in x), JSON.stringify(x));
});

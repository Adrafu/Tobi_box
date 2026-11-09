import os, asyncio
from sync_helfer import Ereignisse, dateien, rsync_daemon, schreibe
from tobibox import sync as s
MB=1024*1024
async def test_x(rsync_daemon):
    d=rsync_daemon
    schreibe(d.quelle/"s/gross.mp3", os.urandom(4*MB))
    aus=Ereignisse()
    sy=s.Sync(d.konfig(), d.box, ausgabe=aus, partial_dir=d.partial, zusatz=["--bwlimit=400"])
    sy.setze_netz("home")
    await sy.start()
    for i in range(100):
        await asyncio.sleep(0.1)
        print(i, [ (str(p.relative_to(d.partial.parent)), p.stat().st_size) for p in d.partial.parent.rglob("*") if p.is_file()])
        if any(p.is_file() and p.stat().st_size>0 for p in d.partial.rglob("*")): break
    os.system("ps aux | grep rsync | grep -v grep | cut -c1-200")
    await sy.abbrechen()
    print([ (str(p.relative_to(d.partial.parent)), p.stat().st_size) for p in d.partial.parent.rglob("*") if p.is_file()])

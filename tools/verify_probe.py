"""全プローブを順に実行し、検証済みの数値と画像をresultsへ保存する。"""

from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import sys

from run_probe import ROOT, PROBE, BUILD, NES_ROOT, MESEN_EXE


def main():
    for script, extra in (('bootstrap_probe.py',()),('run_probe.py',('--sweep',)),
                          ('run_dma_probe.py',()),('run_nes_baseline.py',()),('run_scene_probe.py',())):
        subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools'/script),*extra],check=True)
    dest=PROBE/'results';dest.mkdir(exist_ok=True)
    artifacts={
        'scalers.json':BUILD/'results.json',
        'dma.json':BUILD/'dma/results.json',
        'nes_baseline.json':BUILD/'nes_baseline/results.json',
        'scenes.json':BUILD/'scene_results.json',
        'mixed30.png':BUILD/'mixed30/gsu_framebuffer.png',
        'near_heavy30.png':BUILD/'near_heavy30/gsu_framebuffer.png',
        'dma192_ppu.png':BUILD/'dma/target192_full12k_ppu.png',
    }
    for name,source in artifacts.items():shutil.copy2(source,dest/name)
    inputs=list(PROBE.glob('*.s'))+list(PROBE.glob('*.lua'))+[PROBE/'rom.cfg',PROBE/'sources.lock.json']+list((ROOT/'tools').glob('*probe.py'))+[ROOT/'tools/run_nes_baseline.py']
    external=[NES_ROOT/'png/Tree0/Tree0_00.png',NES_ROOT/'src/gen/sprite_Tree0.s']
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    version=subprocess.run(['ca65','--version'],capture_output=True,text=True,check=True)
    manifest=dict(recorded_at=datetime.now(timezone.utc).isoformat(),
                  emulator_sha256=sha(MESEN_EXE),ca65=(version.stdout+version.stderr).strip(),
                  master_hz=21477272,gsu_clock_percent=100,fast_multiply=False,
                  inputs={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(inputs))},
                  external_inputs={str(p.relative_to(NES_ROOT)).replace('\\','/'):sha(p) for p in external},
                  artifacts={n:sha(dest/n) for n in artifacts})
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('全検証PASS。保存先:',dest)


if __name__=='__main__':main()

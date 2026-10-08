"""実機相当100% GSUのMesenで4bpp二面転送と60Hz更新を観測する。"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from PIL import Image
from run_probe import prepare_runtime, MESEN_EXE, lua
from build_game import BUILD, GAME

def main():
    p=argparse.ArgumentParser();p.add_argument('--frames',type=int,default=720);p.add_argument('--scenario',default='play');a=p.parse_args()
    labels={m[2]:int(m[1],16) for m in re.finditer(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
    dest=BUILD/f'four_{a.scenario}';dest.mkdir(exist_ok=True)
    for old in dest.iterdir():
        if old.is_file():old.unlink()
    script=(GAME/'test4.lua').read_text(encoding='utf-8').replace('LABELS',lua(labels)).replace('OUTDIR',lua(dest.as_posix())).replace('MAXFRAME',str(a.frames)).replace('SCENARIO',lua(a.scenario))
    path=dest/'test.lua';path.write_text(script,encoding='utf-8')
    exe=prepare_runtime(MESEN_EXE);settings=exe.parent/'settings.json';cfg=json.loads(settings.read_text());cfg['Snes'].update(DisableFrameSkipping=True,Port1={'Type':'SnesController'});cfg['Debug']['ScriptWindow']['ScriptTimeout']=30;settings.write_text(json.dumps(cfg))
    result=subprocess.run([str(exe),'--testRunner','--timeout=240','--doNotSaveSettings','--enableStdout',str(BUILD/'MonoSHFX2_v001.sfc'),str(path)],cwd=exe.parent,capture_output=True,timeout=250,creationflags=subprocess.CREATE_NO_WINDOW)
    (dest/'emulator.log').write_bytes(result.stdout+result.stderr)
    for f in dest.glob('*.rgb'):
        data=f.read_bytes();Image.frombytes('RGB',(256,len(data)//768),data).save(f.with_suffix('.png'))
    if result.returncode:
        print((result.stdout+result.stderr).decode(errors='replace'));raise SystemExit(result.returncode)
    print((dest/'summary.json').read_text())

if __name__=='__main__':main()

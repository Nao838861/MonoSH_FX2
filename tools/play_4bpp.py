"""4bpp実験専用のMesen設定で、配布ROMを開く。"""
import argparse
import json
import subprocess
import sys
from run_probe import ROOT, MESEN_EXE, prepare_runtime

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mono',action='store_true')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--build',action='store_true',help='このworktreeの4bpp版をビルドして起動する')
    args=parser.parse_args()
    rom=ROOT/'releases'/('MonoSHFX2_4bpp30_mono.sfc' if args.mono else 'MonoSHFX2_4bpp30_color.sfc')
    if args.build:
        subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/build_4bpp.py'),*([] if args.mono else ['--color'])],cwd=ROOT,check=True)
        rom=ROOT/'build/game_v001/MonoSHFX2_v001.sfc'
    if not rom.exists():raise SystemExit(f'ROM not found: {rom}')
    if not MESEN_EXE.exists():raise SystemExit(f'Mesen not found: {MESEN_EXE}; set MONOSH_FX2_MESEN')
    exe=prepare_runtime(MESEN_EXE)
    settings=exe.parent/'settings.json';config=json.loads(settings.read_text())
    config['Snes'].update(Region='Ntsc',GsuClockSpeed=100,DisableFrameSkipping=True)
    config['Snes']['Port1']={'Type':'SnesController','Mapping1':
        {'Up':24,'Down':26,'Left':23,'Right':25,'A':67,'Y':69,'Start':6}}
    settings.write_text(json.dumps(config))
    print(f'ROM: {rom}')
    print('Arrow keys: move / X: auto fire / Z: single fire / Enter: pause')
    if not args.prepare_only:subprocess.Popen([str(exe),'--doNotSaveSettings',str(rom)],cwd=exe.parent)

if __name__=='__main__':main()

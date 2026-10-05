"""通常設定を変更せず、専用Mesen設定で移植ROMを開く。"""
import argparse
import json
import subprocess
from run_probe import ROOT, MESEN_EXE, prepare_runtime

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true',help='専用設定を作成・確認して終了する')
    args=parser.parse_args()
    rom=ROOT/'releases/MonoSHFX2_v001.sfc'
    if not rom.exists(): raise SystemExit(f'ROM not found: {rom}')
    if not MESEN_EXE.exists(): raise SystemExit(f'Mesen not found: {MESEN_EXE}; set MONOSH_FX2_MESEN')
    mesen=prepare_runtime(MESEN_EXE)
    settings=mesen.parent/'settings.json'
    config=json.loads(settings.read_text())
    config['Snes']['Region']='Ntsc'
    # Mesen共通KeyDefinitions: 矢印、X=A、Z=Y、Enter=Start。
    config['Snes']['Port1']={'Type':'SnesController','Mapping1':
        {'Up':24,'Down':26,'Left':23,'Right':25,'A':67,'Y':69,'Start':6}}
    settings.write_text(json.dumps(config))
    if args.prepare_only:
        print(f'専用設定を準備しました: {settings}')
        return
    subprocess.Popen([str(mesen),'--doNotSaveSettings',str(rom)],cwd=mesen.parent)
    print('MonoSH FX2: Arrow keys / X=auto fire / Z=single fire / Enter=pause')

if __name__=='__main__': main()

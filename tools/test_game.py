"""単独起動、パッド操作、GSU/DMA、ゲーム状態をMesenで観測する。"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from PIL import Image
from run_probe import prepare_runtime, MESEN_EXE, lua
from build_game import BUILD, GAME

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--frames',type=int,default=360)
    parser.add_argument('--scenario',default='play',choices=['play','pause','boss','stress','packed','objects','long','profile','controls','stumble','display','scenery','equivalence','equivalence_boss','held','color'])
    parser.add_argument('--held-direction',default='up-left',choices=['up-left','up-right','down-left','down-right','up','down','left','right','none'])
    parser.add_argument('--held-fire',default='y',choices=['a','y','none'])
    parser.add_argument('--timeout',type=int,default=60)
    parser.add_argument('--dma-probe',action='store_true',help='専用ROMで転送量の各上限を最終許可行に検証する。')
    args=parser.parse_args()
    rom=BUILD/'MonoSHFX2_v001.sfc'
    rom_sha=hashlib.sha256(rom.read_bytes()).hexdigest()
    labels={m[2]:int(m[1],16) for m in re.finditer(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
    # GSU待ちに入る直前のCPU命令をROMから特定する。ROMを計測用に変更しない。
    code=rom.read_bytes()
    start=labels['render_started'];end=labels['render_finished']
    signature=bytes([0x20,labels['_fx_frame']&255,labels['_fx_frame']>>8,0xe2,0x20])
    region=code[0x10000+start:0x10000+end]
    assert region.count(signature)==1,'CPU frame return marker is ambiguous'
    labels['cpu_frame_return']=start+region.index(signature)+3
    output=BUILD/args.scenario; output.mkdir(exist_ok=True)
    assert output.resolve().parent==BUILD.resolve()
    # このツール専用のbuildサブディレクトリだけを空にする。前回の標本を混ぜない。
    for old in output.iterdir():
        if old.is_file(): old.unlink()
    if (output/'error.txt').exists(): (output/'error.txt').unlink()
    script=(GAME/'test.lua').read_text(encoding='utf-8').replace('LABELS',lua(labels)).replace('OUTDIR',lua(output.as_posix())).replace('MAXFRAME',str(args.frames)).replace('SCENARIO',lua(args.scenario))
    script=script.replace('HELD_DIRECTION',lua(args.held_direction)).replace('HELD_FIRE',lua(args.held_fire))
    script=script.replace('GSU_UV','true' if json.loads((BUILD/'build_mode.json').read_text())['gsuUv'] else 'false')
    script=script.replace('GSU_CLIP','true' if json.loads((BUILD/'build_mode.json').read_text())['gsuClip'] else 'false')
    script=script.replace('CPU_CLIP_COMMANDS','true' if json.loads((BUILD/'build_mode.json').read_text()).get('cpuClipCommands') else 'false')
    script=script.replace('DMA_ADMISSION_BYTES',str(json.loads((BUILD/'build_mode.json').read_text()).get('dmaAdmissionBytes',9216)))
    display=(GAME/'display.lua').read_text(encoding='utf-8')
    if args.dma_probe:
        assert args.scenario=='objects' and 'dma_probe_delay' in labels
        display+='\n'+(GAME/'dma_probe.lua').read_text(encoding='utf-8')
    script=script.replace('DISPLAY_CODE',display)
    if args.scenario=='color':script+='\n'+(GAME/'color_test.lua').read_text(encoding='utf-8')
    path=output/'test.lua'; path.write_text(script,encoding='utf-8')
    mesen=prepare_runtime(MESEN_EXE)
    settings=mesen.parent/'settings.json'
    config=json.loads(settings.read_text()); config['Snes']['Port1']={'Type':'SnesController'}
    # ホスト負荷によるPPU frame skipを無効化し、動的OBJと同じ世代のRGBを観測する。
    config['Snes']['DisableFrameSkipping']=True
    config['Debug']['ScriptWindow']['ScriptTimeout']=10
    settings.write_text(json.dumps(config))
    result=subprocess.run([str(mesen),'--testRunner',f'--timeout={args.timeout}','--doNotSaveSettings',
            '--enableStdout',str(BUILD/'MonoSHFX2_v001.sfc'),str(path)],
            cwd=mesen.parent,capture_output=True,timeout=args.timeout+10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (output/'emulator.log').write_bytes(result.stdout+result.stderr)
    print('Mesen exit',result.returncode)
    if (output/'trace.jsonl').exists():
        rows=[json.loads(x) for x in (output/'trace.jsonl').read_text().splitlines()]
        print('last records:',json.dumps(rows[-4:],ensure_ascii=False))
    if (output/'error.txt').exists(): print((output/'error.txt').read_text())
    for path in output.glob('*.rgb'):
        raw=path.read_bytes(); Image.frombytes('RGB',(256,len(raw)//768),raw).save(path.with_suffix('.png'))
    if result.returncode: raise SystemExit(result.returncode)
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==rom_sha,'ROM changed during test'
    summary_path=output/'summary.json'
    summary=json.loads(summary_path.read_text())
    summary['romSha256']=rom_sha
    if args.scenario=='held':
        summary['heldDirection']=args.held_direction;summary['heldFire']=args.held_fire
    summary_path.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    subprocess.run([sys.executable,str(Path(__file__).with_name('verify_game_pixels.py')),args.scenario],check=True)
    subprocess.run([sys.executable,str(Path(__file__).with_name('verify_game_objects.py')),args.scenario],check=True)
    if args.scenario in ('display','scenery'):
        subprocess.run([sys.executable,str(Path(__file__).with_name('verify_game_display.py')),args.scenario],check=True)
    if args.scenario=='color':
        subprocess.run([sys.executable,str(Path(__file__).with_name('verify_bg_colors.py'))],check=True)

if __name__=='__main__': main()

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
    p=argparse.ArgumentParser();p.add_argument('--frames',type=int,default=720);p.add_argument('--scenario',default='play');p.add_argument('--timeout',type=int,default=600);p.add_argument('--profile',action='store_true');a=p.parse_args()
    labels={m[2]:int(m[1],16) for m in re.finditer(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
    dest=BUILD/f'four_{a.scenario}';dest.mkdir(exist_ok=True)
    for old in dest.iterdir():
        if old.is_file():old.unlink()
    script=(GAME/'test4.lua').read_text(encoding='utf-8').replace('LABELS',lua(labels)).replace('OUTDIR',lua(dest.as_posix())).replace('MAXFRAME',str(a.frames)).replace('SCENARIO',lua(a.scenario)).replace('PROFILING','true' if a.profile else 'false')
    path=dest/'test.lua';path.write_text(script,encoding='utf-8')
    exe=prepare_runtime(MESEN_EXE);settings=exe.parent/'settings.json';cfg=json.loads(settings.read_text());cfg['Snes'].update(DisableFrameSkipping=True,Port1={'Type':'SnesController'});cfg['Debug']['ScriptWindow']['ScriptTimeout']=30;settings.write_text(json.dumps(cfg))
    result=subprocess.run([str(exe),'--testRunner',f'--timeout={a.timeout}','--doNotSaveSettings','--enableStdout',str(BUILD/'MonoSHFX2_v001.sfc'),str(path)],cwd=exe.parent,capture_output=True,timeout=a.timeout+10,creationflags=subprocess.CREATE_NO_WINDOW)
    (dest/'emulator.log').write_bytes(result.stdout+result.stderr)
    for f in dest.glob('*.rgb'):
        data=f.read_bytes();Image.frombytes('RGB',(256,len(data)//768),data).save(f.with_suffix('.png'))
    if result.returncode:
        if (dest/'failure.txt').exists():print((dest/'failure.txt').read_text())
        print((result.stdout+result.stderr).decode(errors='replace'));raise SystemExit(result.returncode)
    summary=json.loads((dest/'summary.json').read_text())
    summary['romSha256']=hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    records=[json.loads(line) for line in (dest/'trace.jsonl').read_text().splitlines()]
    summary['actualGsuMaxMs']=max(r['actualGsuMs'] for r in records if 'actualGsuMs' in r)
    presents=[r for r in records if 'present' in r]
    assert 0<=summary['logicCalls']-2*summary['renders']<=3,'not two logic calls per presented image'
    if a.scenario=='pause':
        paused=[r for r in presents if 165<=r['field']<=195]
        assert paused and all(r['paused']==1 for r in paused) and len({r['logic'] for r in paused})==1,'pause kept updating'
        assert any(r['field']>=240 and r['paused']==0 and r['logic']>paused[0]['logic'] for r in presents),'pause did not resume'
        summary['pauseResumeVerified']=True
    if a.scenario=='death':
        died=[r for r in presents if r['player']!=0]
        assert died and any(r['field']>died[-1]['field'] and r['player']==0 for r in presents),'death/respawn incomplete'
        summary['deathRespawnVerified']=True
    if a.scenario=='boss' and a.frames>=2600:
        assert all(summary[k] for k in ('bossSeen','dyingSeen','doneSeen','restartSeen')),'boss progression incomplete'
    if a.scenario=='controls':
        assert max(r['x'] for r in presents)-min(r['x'] for r in presents)>100,'horizontal input did not reach game'
        assert max(r['bottom'] for r in presents)-min(r['bottom'] for r in presents)>100,'vertical input did not reach game'
        assert max(r['shots'] for r in presents)>1,'held autofire did not reach game'
        summary['controlsFireVerified']=True
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()

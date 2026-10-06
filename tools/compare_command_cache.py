"""同じ実ゲーム矩形を4構成で再描画し、CPU分類と命令cache保持を分離して測る。"""
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import struct
import subprocess
import sys

from build_game import ROOT, GAME, BUILD
from run_probe import MESEN_EXE, prepare_runtime, lua
from verify_game_pixels import verify


INJECTION = '''
local replay_fixtures=FIXTURES
local fixture_number,fixture_index=0,0
local current_index,current_repeat=0,0
local packet_start=0
local cache_calls,cache_invalidations=0,0
local replay_report=assert(io.open(output..'/replay.jsonl','w'))
emu.addMemoryCallback(guard(function()
  fixture_number=fixture_number+1
  fixture_index=1+((fixture_number-1)//3)%#replay_fixtures
  local f=replay_fixtures[fixture_index]
  for i,v in ipairs(f.bytes) do put('_fx_draw',i-1,v) end
  put('_fx_draw_count',0,f.count)
  packet_start=emu.getState().masterClock
end),emu.callbackType.exec,0x7f0000+labels._fx_build_packet,0x7f0000+labels._fx_build_packet,
emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
  replay_report:write(encoded({kind='packet',scene=fixture_index,repeatIndex=1+(fixture_number-1)%3,
     ms=elapsed(emu.getState().masterClock,packet_start)})..'\\n')
end),emu.callbackType.exec,0x7f0000+labels.packet_done,0x7f0000+labels.packet_done,
emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function(a,v)
  if v~=1 then return end
  current_index=fixture_index;current_repeat=1+(fixture_number-1)%3
  cache_calls=0;cache_invalidations=0
end),emu.callbackType.write,0x7e1df0,0x7e1df0)
for _,address in ipairs(CACHE_ADDRESSES) do
  emu.addMemoryCallback(guard(function()
    cache_calls=cache_calls+1
    local base=assert(emu.getState()['cart.coprocessor.cacheBase'])
    if base~=((address+1)&0xfff0) then cache_invalidations=cache_invalidations+1 end
  end),emu.callbackType.exec,address,address,emu.cpuType.gsu,emu.memType.gsuMemory)
end
emu.addMemoryCallback(guard(function()
  replay_report:write(encoded({kind='gsu',scene=current_index,repeatIndex=current_repeat,
     ms=elapsed(emu.getState().masterClock,clock_start),cacheCalls=cache_calls,
     cacheInvalidations=cache_invalidations,image=rendered+1})..'\\n');replay_report:flush()
end),emu.callbackType.exec,labels.render_stop,labels.render_stop,emu.cpuType.gsu,emu.memType.gsuMemory)
'''


def fixtures():
    output=[]
    for name in ('boss_profile','boss_profile_linger'):
        directory=BUILD/name
        for path in sorted(directory.glob('draw[0-9]*.bin')):
            meta=json.loads(path.with_name('meta'+path.stem[4:]+'.json').read_text())
            output.append({'name':name+'/'+path.stem,'count':meta['count'],'bytes':list(path.read_bytes())})
    assert output, '先に通常入力のprofileを計測し、標本をbuildに残す。'
    p=GAME/'results/boss_profile_20261007/linger/worst_gsu_packet.bin'
    raw=p.read_bytes();count=struct.unpack_from('<H',raw)[0]
    output.append({'name':'boss_worst_19ms','count':count,'bytes':list(raw[32:32+count*10])})
    for name,center in [('inside64',128),('clipped64',0)]:
        raw=b''.join(struct.pack('<hh6B',center,120,13,19,0,0,i,0) for i in range(64))
        output.append({'name':name,'count':64,'bytes':list(raw)})
    # 各辺の内外、ちょうど右/下端、符号付き位置、奇数幅、zero寸法を独立照合。
    for center,bottom,w,h in [(0,20,13,19),(256,212,13,19),(249,212,14,19),
                              (7,39,14,19),(-300,100,13,19),(600,100,13,19),
                              (128,-100,13,19),(128,500,13,19),(128,100,0,19),
                              (128,100,13,0),(0,100,255,255),(128,212,255,192)]:
        raw=struct.pack('<hh6B',center,bottom,w,h,0,0,0,0)
        output.append({'name':f'edge_{center}_{bottom}_{w}_{h}','count':1,'bytes':list(raw)})
    return output


def run_variant(name, flags, cases):
    output=BUILD/('cache_compare_'+name);output.mkdir(exist_ok=True)
    if '--resume' in sys.argv and (output/'summary.json').exists() and not (output/'error.txt').exists():
        digest=hashlib.sha256((output/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
        config=json.loads((output/'build_mode.json').read_text())
        return summarize(output,digest,config,cases)
    subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/build_game.py'),*flags],check=True)
    assert output.resolve().parent==BUILD.resolve()
    for old in output.iterdir():
        if old.is_file():old.unlink()
    rom=BUILD/'MonoSHFX2_v001.sfc';digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    if name=='baseline':
        assert digest==hashlib.sha256((BUILD/'optimization_baseline/MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    for filename in ('MonoSHFX2_v001.sfc','game.lbl','build_mode.json'):
        shutil.copy2(BUILD/filename,output/filename)
    labels={m[2]:int(m[1],16) for m in re.finditer(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
    region=rom.read_bytes()[0x10000+labels['render_started']:0x10000+labels['render_finished']]
    signature=bytes([0x20,labels['_fx_frame']&255,labels['_fx_frame']>>8,0xe2,0x20])
    assert region.count(signature)==1
    labels['cpu_frame_return']=labels['render_started']+region.index(signature)+3
    config=json.loads((BUILD/'build_mode.json').read_text())
    caches=[v for k,v in labels.items() if k.endswith('_cache') and v>>16==1]
    caches.append(labels['render_entry'])
    script=(GAME/'test.lua').read_text(encoding='utf-8')
    script=script.replace('DISPLAY_CODE',(GAME/'display.lua').read_text(encoding='utf-8')+'\n'+
         INJECTION.replace('FIXTURES',lua(cases)).replace('CACHE_ADDRESSES',lua(caches)))
    # 全replay画像を独立したPython参照へ渡す。描画順・clip・反転・透明合成を検査。
    script=script.replace('rendered==0 or (rendered+1)%300==0','true or rendered==0 or (rendered+1)%300==0')
    script=script.replace('rendered==1 or rendered%300==0','true or rendered==1 or rendered%300==0')
    for key,value in {'LABELS':lua(labels),'OUTDIR':lua(output.as_posix()),'MAXFRAME':str(len(cases)*6+100),
                       'SCENARIO':lua('replay'),'HELD_DIRECTION':lua('none'),'HELD_FIRE':lua('none'),
                       'GSU_UV':str(config['gsuUv']).lower(),'GSU_CLIP':str(config['gsuClip']).lower(),
                       'CPU_CLIP_COMMANDS':str(config['cpuClipCommands']).lower()}.items():
        script=script.replace(key,value)
    path=output/'test.lua';path.write_text(script,encoding='utf-8')
    mesen=prepare_runtime(MESEN_EXE)
    settings=mesen.parent/'settings.json'
    data=json.loads(settings.read_text())
    data['Debug']['ScriptWindow']['ScriptTimeout']=10
    data['Snes'].update({'Port1':{'Type':'SnesController'},'DisableFrameSkipping':True})
    settings.write_text(json.dumps(data))
    result=subprocess.run([str(mesen),'--testRunner','--timeout=120','--doNotSaveSettings','--enableStdout',
                           str(output/rom.name),str(path)],cwd=mesen.parent,capture_output=True,
                          timeout=130,creationflags=subprocess.CREATE_NO_WINDOW)
    (output/'emulator.log').write_bytes(result.stdout+result.stderr)
    if (output/'error.txt').exists():raise RuntimeError((output/'error.txt').read_text())
    assert result.returncode==0, result.returncode
    return summarize(output,digest,config,cases)


def summarize(output,digest,config,cases):
    verify(output)
    records=[json.loads(line) for line in (output/'replay.jsonl').read_text().splitlines()]
    rows=[]
    for i,case in enumerate(cases,1):
        gsu=[r for r in records if r['kind']=='gsu' and r['scene']==i and r['repeatIndex'] in (2,3)
             and (output/f"frame{r['image']:05d}.bin").exists()]
        packet=[r for r in records if r['kind']=='packet' and r['scene']==i and r['repeatIndex'] in (2,3)]
        assert gsu and packet,case['name']
        hashes={hashlib.sha256((output/f"frame{r['image']:05d}.bin").read_bytes()).hexdigest() for r in gsu}
        rows.append({'scene':case['name'],'gsuMedianMs':statistics.median(r['ms'] for r in gsu),
                     'packetMedianMs':statistics.median(r['ms'] for r in packet),
                     'cacheCallsMedian':statistics.median(r['cacheCalls'] for r in gsu),
                     'cacheInvalidationsMedian':statistics.median(r['cacheInvalidations'] for r in gsu),
                     'framebufferHashes':sorted(hashes),'samples':len(gsu)})
    summary={'romSha256':digest,'buildMode':config,'scenes':rows,'imagesVerified':len(list(output.glob('frame[0-9]*.bin')))}
    (output/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


def main():
    cases=fixtures();result={}
    for name,flags in [('baseline',['--no-cpu-clip-commands','--no-stable-gsu-cache']),
                       ('commands',['--no-stable-gsu-cache']),('cache',['--no-cpu-clip-commands']),('both',[])]:
        print('Comparing',name,flush=True)
        result[name]=run_variant(name,flags,cases)
    for name,data in result.items():
        for before,after in zip(result['baseline']['scenes'],data['scenes']):
            assert before['framebufferHashes']==after['framebufferHashes'], (name,after['scene'])
            after['gsuTimeReductionPercent']=(1-after['gsuMedianMs']/before['gsuMedianMs'])*100
            after['packetChangeMs']=after['packetMedianMs']-before['packetMedianMs']
    (BUILD/'command_cache_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    (BUILD/'command_cache_fixtures.json').write_text(json.dumps(cases)+'\n')
    for name in ['boss_worst_19ms','inside64','clipped64']:
        print(name,[(variant,next(r for r in data['scenes'] if r['scene']==name)['gsuMedianMs'])
                    for variant,data in result.items()],flush=True)


if __name__=='__main__':main()

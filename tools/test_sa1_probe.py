"""実SA-1のmaster clockと4bpp描画を、独立した画素合成で検証する。"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import zipfile
import numpy as np
from PIL import Image
from build_sa1_probe import BUILD, ROOT, ART
from run_probe import prepare_runtime, MESEN_EXE, lua

def jobs():
    result=[]
    for asset,w,h in [(0,48,24),(1,64,32),(4,68,160),(5,64,64),(13,96,96),(14,96,96),(31,24,24)]:
        for flags in (0,16,32,48):result.append(dict(name=f'asset{asset}_flip{flags}',draws=[[128,170,w,h,asset,flags,0,0]]))
    result.extend([
        dict(name='edge_top_left',draws=[[2,22,64,64,5,0,0,0]]),
        dict(name='edge_bottom_right',draws=[[253,240,68,160,4,16,0,0]]),
        dict(name='overlap',draws=[[110,175,68,160,4,0,0,0],[135,150,96,96,13,0,0,0],[120,140,64,64,39,0,0,0]]),
    ])
    for scenario in ('play','boss','boss_hold','missile','laser','stage_effects'):
        p=ROOT/f'game/v001/results/four_bpp_20261008/color/{scenario}/samples.zip'
        if not p.exists():continue
        with zipfile.ZipFile(p) as z:
            names=sorted(n for n in z.namelist() if n.endswith('_meta.json'))
            for n in names[::max(1,len(names)//6)][:6]:
                prefix=n[:-10];raw=z.read(prefix+'_packet.bin');count=struct.unpack_from('<H',raw)[0]
                draws=[list(struct.unpack_from('<hh6B',raw,32+i*10)) for i in range(count)]
                result.append(dict(name=f'{scenario}_{prefix}',draws=draws))
    for j in result:j['packet']=list(b''.join(struct.pack('<hh6B',*d) for d in j['draws']))
    return result

def reference(job):
    rgb5=np.array(json.loads((ART/'palette.json').read_text())['rgb5'],dtype=np.int32)
    rgb=rgb5*8+(rgb5>>2);out=np.zeros((192,256),dtype=np.uint8)
    for center,bottom,w,h,asset,flags,*_ in job['draws']:
        if not w or not h:continue
        variant=flags&3
        p=ART/(f'{asset:02d}_hue{variant}.png' if variant and asset in (6,7,8,31,37) else f'{asset:02d}.png')
        a=np.array(Image.open(p).convert('RGBA'));ah,aw=a.shape[:2]
        pix=np.where(a[:,:,3]>=128,1+((a[:,:,:3,None].astype(np.int32)-rgb[1:].T[None,None,:,:])**2).sum(axis=2).argmin(axis=2),0).astype(np.uint8)
        du=aw*256//w;dv=ah*256//h
        u=np.arange(w)*du;v=np.arange(h)*dv
        if flags&16:u=aw*256-1-u
        if flags&32:v=ah*256-1-v
        scaled=pix[v>>8][:,u>>8]
        left=center-w//2;top=bottom-h-20
        x0=max(0,left);x1=min(256,left+w);y0=max(0,top);y1=min(192,top+h)
        if x0<x1 and y0<y1:
            patch=scaled[y0-top:y1-top,x0-left:x1-left];dest=out[y0:y1,x0:x1];dest[patch!=0]=patch[patch!=0]
    packed=out[:,::2]|(out[:,1::2]<<4)
    return packed.tobytes()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=0);args=ap.parse_args()
    fixtures=jobs();fixtures=fixtures[:args.limit] if args.limit else fixtures
    config=json.loads((BUILD/'mode.json').read_text());mode=config['mode']
    rom=BUILD/f'MonoSHSA1_{mode}_probe.sfc'
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==config['romSha256'],'ROM is not a completed build'
    assert hashlib.sha256((BUILD/'probe.lbl').read_bytes()).hexdigest()==config['labelsSha256'],'labels do not match the completed build'
    dest=BUILD/mode;dest.mkdir(exist_ok=True)
    for name in ('timings.json','summary.json'):(dest/name).unlink(missing_ok=True)
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'probe.lbl').read_text())}
    script='''local jobs=JOBS
local labels=LABELS
local output=OUTDIR
local index=1
local started,clear,draw=0,0,0
local rows={}
local ready=false
local function callback(name,cpu,fn)
 emu.addMemoryCallback(fn,emu.callbackType.exec,labels[name],labels[name],cpu,cpu==emu.cpuType.sa1 and emu.memType.sa1Memory or emu.memType.snesMemory)
end
callback('probe_ready',emu.cpuType.snes,function()
 if ready then return end
 local j=jobs[index]
 for i,v in ipairs(j.packet) do emu.write(0x430000+i-1,v,emu.memType.snesMemory) end
 emu.write16(0x3106,#j.draws,emu.memType.snesMemory)
 emu.write16(0x3100,1,emu.memType.snesMemory)
 ready=true
end)
callback('sa1_clear_start',emu.cpuType.sa1,function()started=emu.getState().masterClock end)
callback('sa1_clear_done',emu.cpuType.sa1,function()clear=emu.getState().masterClock-started end)
callback('sa1_draw_start',emu.cpuType.sa1,function()draw=emu.getState().masterClock end)
callback('sa1_draw_done',emu.cpuType.sa1,function()
 local clock=emu.getState().masterClock
 rows[#rows+1]=string.format('{"name":"%s","clearClocks":%d,"drawClocks":%d,"totalClocks":%d}',jobs[index].name,clear,clock-draw,clock-started)
end)
callback('probe_finished',emu.cpuType.snes,function()
 local f=assert(io.open(output..'/'..jobs[index].name..'.bin','wb'));local t={}
 for i=0,24575 do t[#t+1]=string.char(emu.read(i,emu.memType.snesSaveRam)) end
 f:write(table.concat(t));f:close()
 if index==#jobs then
  local f=assert(io.open(output..'/timings.json','w'));f:write('['..table.concat(rows,',')..']');f:close();emu.stop(0)
 else index=index+1;ready=false end
end)
'''.replace('JOBS',lua(fixtures)).replace('LABELS',lua(labels)).replace('OUTDIR',lua(dest.as_posix()))
    (dest/'test.lua').write_text(script)
    exe=prepare_runtime(MESEN_EXE)
    r=subprocess.run([str(exe),'--testRunner','--timeout=120','--doNotSaveSettings','--enableStdout',str(BUILD/f'MonoSHSA1_{mode}_probe.sfc'),str(dest/'test.lua')],cwd=exe.parent,capture_output=True,timeout=130,creationflags=subprocess.CREATE_NO_WINDOW)
    (dest/'emulator.log').write_bytes(r.stdout+r.stderr)
    if r.returncode or not (dest/'timings.json').exists():print((r.stdout+r.stderr).decode(errors='replace'));raise RuntimeError(f'Mesen {r.returncode}, no timings')
    times=json.loads((dest/'timings.json').read_text());assert len(times)==len(fixtures)
    for job,row in zip(fixtures,times):
        actual=(dest/(job['name']+'.bin')).read_bytes();expected=reference(job)
        if actual!=expected:
            (dest/(job['name']+'_expected.bin')).write_bytes(expected)
            raise AssertionError(f'{job["name"]}: {sum(a!=b for a,b in zip(actual,expected))} bytes differ')
        for key in ('clear','draw','total'):row[key+'Ms']=row[key+'Clocks']/21477.272
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==config['romSha256'],'ROM changed during emulation'
    summary={'mode':config,'pixelMatchedJobs':len(times),'maxDrawMs':max(x['drawMs'] for x in times),'maxTotalMs':max(x['totalMs'] for x in times),'timings':times}
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='timings'}))

if __name__=='__main__':main()

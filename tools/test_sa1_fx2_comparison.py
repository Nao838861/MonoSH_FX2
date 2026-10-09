"""SA-1と同一のpacketを、現行FX2 ROMの実GSUで描画して比較する。"""
import json
import re
import subprocess
import numpy as np
from test_sa1_probe import jobs, reference
from build_sa1_probe import ROOT, BUILD
from run_probe import prepare_runtime, MESEN_EXE, lua

def encode(packed):
    raw=np.frombuffer(packed,dtype=np.uint8).reshape(192,128)
    pix=np.stack((raw&15,raw>>4),axis=2).reshape(192,256)
    tiles=pix.reshape(24,8,32,8).transpose(2,0,1,3).reshape(768,8,8)
    out=np.zeros((768,32),dtype=np.uint8)
    for plane in range(4):out[:,plane//2*16+plane%2+np.arange(8)*2]=(((tiles>>plane)&1)*np.array([128,64,32,16,8,4,2,1])).sum(axis=2)
    return out.tobytes()

def main():
    fx=ROOT/'build/game_v001';fixtures=jobs();dest=BUILD/'fx2_comparison';dest.mkdir(exist_ok=True)
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(fx/'game.lbl').read_text())}
    script='''local jobs=JOBS
local labels=LABELS
local output=OUTDIR
local index=1
local starts,total=0,0
local rows={}
local function cb(name,fn)
 local a=0x7f0000+labels[name]
 emu.addMemoryCallback(fn,emu.callbackType.exec,a,a,emu.cpuType.snes,emu.memType.snesMemory)
end
local function prepare()
 local j=jobs[index]
 emu.write16(0,#j.draws,emu.memType.gsuWorkRam)
 for i,v in ipairs(j.packet) do emu.write(32+i-1,v,emu.memType.gsuWorkRam) end
 for i=0,15 do emu.write(0x1000+i,0,emu.memType.gsuWorkRam) end
 starts=emu.getState().masterClock
end
cb('render_started',function()total=0;prepare()end)
cb('render_second_started',prepare)
emu.addMemoryCallback(function()
 total=total+emu.getState().masterClock-starts
end,emu.callbackType.exec,labels.render_stop,labels.render_stop,emu.cpuType.gsu,emu.memType.gsuMemory)
cb('render_second_finished',function()
 rows[#rows+1]=string.format('{"name":"%s","totalClocks":%d}',jobs[index].name,total)
 local f=assert(io.open(output..'/'..jobs[index].name..'.bin','wb'));local t={}
 for i=0,24575 do t[#t+1]=string.char(emu.read(0x2000+i,emu.memType.gsuWorkRam)) end
 f:write(table.concat(t));f:close()
 if index==#jobs then
  local f=assert(io.open(output..'/timings.json','w'));f:write('['..table.concat(rows,',')..']');f:close();emu.stop(0)
 else index=index+1 end
end)
'''.replace('JOBS',lua(fixtures)).replace('LABELS',lua(labels)).replace('OUTDIR',lua(dest.as_posix()))
    (dest/'test.lua').write_text(script);exe=prepare_runtime(MESEN_EXE)
    r=subprocess.run([str(exe),'--testRunner','--timeout=180','--doNotSaveSettings','--enableStdout',str(fx/'MonoSHFX2_v001.sfc'),str(dest/'test.lua')],cwd=exe.parent,capture_output=True,timeout=190,creationflags=subprocess.CREATE_NO_WINDOW)
    (dest/'emulator.log').write_bytes(r.stdout+r.stderr)
    if r.returncode or not (dest/'timings.json').exists():print((r.stdout+r.stderr).decode(errors='replace'));raise RuntimeError('FX2 comparison failed')
    rows=json.loads((dest/'timings.json').read_text());assert len(rows)==len(fixtures)
    for job,row in zip(fixtures,rows):
        actual=(dest/(job['name']+'.bin')).read_bytes();expected=encode(reference(job))
        assert actual==expected,f'{job["name"]}: FX2 pixels differ'
        row['totalMs']=row['totalClocks']/21477.272
    (dest/'summary.json').write_text(json.dumps({'pixelMatchedJobs':len(rows),'timings':rows},indent=2)+'\n')
    print('FX2 same-packet pixel matches:',len(rows),'max total ms:',max(x['totalMs'] for x in rows))

if __name__=='__main__':main()

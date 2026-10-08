"""Capture identical art fixtures through Mesen's real PPU, not a host mock-up.

Can replay a pre-color, old-color, repaired-color or repaired-monochrome build.
All art positions, poses, sizes and the ground camera are fixed in every build.
The accompanying draw, GSU framebuffer, VRAM, CGRAM and OAM make each PNG auditable.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from PIL import Image
from run_probe import MESEN_EXE,prepare_runtime,lua

FIXTURES = [
 {'name':'foliage','draw':[[43,198,61,142,4,0,20,0],[123,189,70,38,0,0,10,0],[206,181,67,31,1,0,15,0],[176,93,53,39,2,0,50,0]]},
 {'name':'enemies','draw':[[67,105,110,60,3,0,30,0],[166,91,28,30,11,0,25,0],[222,91,32,32,12,0,24,0],*[ [24+i*51,179,44,44,32+i,0,20-i,0] for i in range(5)]]},
 {'name':'projectiles','draw':[[32,143,48,75,6,0,30,0],[96,143,59,75,7,0,25,0],[160,141,64,60,8,0,20,0],[224,137,64,44,37,0,15,0]]},
 {'name':'boss','draw':[[128,185,110,74,13,0,45,0],[120,162,76,51,13,0,55,0],[120,126,48,32,13,0,65,0],[122,154,55,84,14,0,20,0],[220,190,64,63,31,0,10,0]]},
 {'name':'player_shots','draw':[[58,187,32,48,9,0,0,2],[128,171,32,48,15,0,0,2],[199,179,32,48,16,16,0,2],[128,117,16,16,10,0,30,2],[99,89,10,10,10,0,50,2],[171,69,5,5,10,0,70,2]]},
 {'name':'overlap','draw':[[48,196,52,122,4,0,80,0],[127,91,88,48,3,0,70,0],[146,170,100,68,13,0,60,0],[143,175,60,92,14,0,40,0],[223,117,36,54,7,0,30,0],[127,142,60,48,31,0,20,0]]},
]
SCRIPT = r'''
local labels=LABELS
local output=OUTDIR
local fixtures=FIXTURES
local field=0
local started=false
local selected=1
local captured={}
local function put(name,off,value)
  emu.write(0x7e0000+assert(labels[name])+off,value&255,emu.memType.snesMemory)
end
local function word(name,value) put(name,0,value);put(name,1,value>>8) end
local function dump(name,mt,addr,count)
  local b={};for i=0,count-1 do b[#b+1]=string.char(emu.read(addr+i,mt)) end
  local f=assert(io.open(output..'/'..name,'wb'));f:write(table.concat(b));f:close()
end
local function guard(fn) return function(...)
  local ok,err=pcall(fn,...)
  if not ok then local f=io.open(output..'/error.txt','w');f:write(tostring(err));f:close();emu.stop(1) end
end end
local function camera()
 put('_monosh_ground_offset',0,32);put('_fx_ground_world_phase',0,32);put('_fx_ground_phase',0,6)
 word('_fx_far_u_acc',17*128);word('_fx_far_d_acc',17*256)
end
emu.addMemoryCallback(guard(function()
  started=true;selected=math.min(#fixtures,1+field//60)
  camera();word('_monosh_runtime_frame_counter',100)
  if labels.fx_color_mode then put('fx_color_mode',0,COLORMODE) end
  local records=fixtures[selected].draw
  for i,r in ipairs(records) do
    local b={r[1]&255,(r[1]>>8)&255,r[2]&255,(r[2]>>8)&255,r[3],r[4],r[5],r[6],r[7],r[8]}
    for j,v in ipairs(b) do put('_fx_draw',(i-1)*10+j-1,v) end
  end
  put('_fx_draw_count',0,#records)
end),emu.callbackType.exec,0x7f0000+labels._fx_build_packet,0x7f0000+labels._fx_build_packet,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(camera),emu.callbackType.exec,0x7f0000+labels._fx_build_ground,0x7f0000+labels._fx_build_ground,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function() emu.setInput({},0) end,emu.eventType.inputPolled)
emu.addEventCallback(guard(function()
  if not started then return end
  field=field+1
  if field%60==50 then
    local name=fixtures[selected].name
    local rgb={};for _,v in ipairs(emu.getScreenBuffer()) do rgb[#rgb+1]=string.char((v>>16)&255,(v>>8)&255,v&255) end
    local f=assert(io.open(output..'/'..name..'.rgb','wb'));f:write(table.concat(rgb));f:close()
    dump(name..'_fb.bin',emu.memType.gsuWorkRam,0x2000,12288)
    dump(name..'_vram.bin',emu.memType.snesVideoRam,0,65536)
    dump(name..'_cgram.bin',emu.memType.snesCgRam,0,512)
    dump(name..'_oam.bin',emu.memType.snesSpriteRam,0,544)
    captured[selected]=true
  end
  if field>=#fixtures*60 then
    for i=1,#fixtures do assert(captured[i],'missing capture') end
    emu.stop(0)
  end
end),emu.eventType.endFrame)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--build-dir',type=Path,default=Path('build/game_v001'))
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--mode',choices=['color','mono'],default='color')
 args=p.parse_args();build=args.build_dir.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 if (out/'error.txt').exists(): (out/'error.txt').unlink()
 labels={m[2]:int(m[1],16) for m in re.finditer(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(build/'game.lbl').read_text())}
 script=SCRIPT.replace('LABELS',lua(labels)).replace('OUTDIR',lua(str(out))).replace('FIXTURES',lua(FIXTURES)).replace('COLORMODE','1' if args.mode=='color' else '0')
 path=out/'capture.lua';path.write_text(script)
 mesen=prepare_runtime(MESEN_EXE);settings=mesen.parent/'settings.json';cfg=json.loads(settings.read_text());cfg['Snes'].update({'Port1':{'Type':'SnesController'},'DisableFrameSkipping':True});cfg['Debug']['ScriptWindow']['ScriptTimeout']=10;settings.write_text(json.dumps(cfg))
 rom=build/'MonoSHFX2_v001.sfc'
 result=subprocess.run([str(mesen),'--testRunner','--timeout=180','--doNotSaveSettings','--enableStdout',str(rom),str(path)],cwd=mesen.parent,capture_output=True,timeout=190)
 (out/'emulator.log').write_bytes(result.stdout+result.stderr)
 assert result.returncode==0,(result.returncode,(out/'error.txt').read_text() if (out/'error.txt').exists() else result.stdout[-1000:])
 for fixture in FIXTURES:
  raw=(out/(fixture['name']+'.rgb')).read_bytes();assert len(raw)%768==0
  Image.frombytes('RGB',(256,len(raw)//768),raw).save(out/(fixture['name']+'.png'))
 manifest={'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'mode':args.mode,'ground_camera':32,'logic_frame':100,'fixtures':FIXTURES,'captures':'Mesen 2.1.1 final PPU RGB, 256-pixel-wide SNES frame; fixed pose/position/size'}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'rom_sha256':manifest['rom_sha256'],'captures':len(FIXTURES),'mode':args.mode}))

if __name__=='__main__': main()

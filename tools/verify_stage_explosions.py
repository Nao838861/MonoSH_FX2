"""地上爆発の実際の画像選択と全FB・不透明PPU画素を六位相×二モードで確認する。"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

import numpy as np
from PIL import Image
from build_game import BUILD, GAME
from run_probe import MESEN_EXE, lua, prepare_runtime
from verify_game_display import rgb
from verify_palette_regions import decode_fb

SCRIPT = r'''
local labels=LABELS
local out=OUTDIR
local baseline=BASELINE
local field=0
local started=false
local selected=1
local draw=nil
local assets={5,39,40,41,40,39}
local function put(name,off,value) emu.write(0x7e0000+labels[name]+off,value,emu.memType.snesMemory) end
local function read(name,off) return emu.read(0x7e0000+labels[name]+off,emu.memType.snesMemory) end
local function guard(fn) return function(...)
 local ok,err=pcall(fn,...)
 if not ok then local f=io.open(out..'/error.txt','w');f:write(tostring(err));f:close();emu.stop(1) end
end end
local function dump(name,mt,addr,count)
 local bytes={};for i=0,count-1 do bytes[#bytes+1]=string.char(emu.read(addr+i,mt)) end
 local f=assert(io.open(out..'/'..name,'wb'));f:write(table.concat(bytes));f:close()
end
emu.addMemoryCallback(guard(function()
 started=true;selected=math.min(12,1+field//12)
 local phase=(selected-1)%6
 put('_monosh_ground_offset',0,32);put('_monosh_ground_screen_delta',0,4)
 local depth=labels._fx_ground_depth_rows+32*81
 put('_monosh_ground_depth_pointer',0,depth&255);put('_monosh_ground_depth_pointer',1,depth>>8)
 put('fx_color_mode',0,selected<=6 and 1 or 0)
 put('_monosh_stage_object_count',0,1)
 local data={0,0,60,2,12,48-phase*8}
 for i,v in ipairs(data) do put('_monosh_stage_objects',i-1,v) end
end),emu.callbackType.exec,0x7f0000+labels._fx_stage_render,0x7f0000+labels._fx_stage_render,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
 if not started then return end
 local matches={}
 for i=0,read('_fx_draw_count',0)-1 do
  local off=i*10
  if read('_fx_draw',off+8)==60 and read('_fx_draw',off+9)==0 then
   local bytes={};for j=0,9 do bytes[#bytes+1]=read('_fx_draw',off+j) end
   matches[#matches+1]=bytes
  end
 end
 assert(#matches==1,'ground explosion draw missing or ambiguous')
 draw=matches[1]
 local expected=assets[1+(selected-1)%6]
 if baseline and (selected-1)%6==0 then expected=38 end
 assert(draw[7]==expected,'wrong explosion asset '..draw[7]..' expected '..expected)
 -- 選択済みの地上爆発だけを残し、他の物体による遮蔽をなくして実PPUを調べる。
 for i,v in ipairs(draw) do put('_fx_draw',i-1,v) end
 put('_fx_draw_count',0,1)
end),emu.callbackType.exec,0x7f0000+labels._fx_build_packet,0x7f0000+labels._fx_build_packet,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function() emu.setInput({},0) end,emu.eventType.inputPolled)
emu.addEventCallback(guard(function()
 if not started then return end
 field=field+1
 if field%12==10 then
  local name=string.format('case%02d',selected)
  local bytes={};for _,v in ipairs(emu.getScreenBuffer()) do bytes[#bytes+1]=string.char((v>>16)&255,(v>>8)&255,v&255) end
  local f=assert(io.open(out..'/'..name..'.rgb','wb'));f:write(table.concat(bytes));f:close()
  f=assert(io.open(out..'/'..name..'_draw.bin','wb'));for _,v in ipairs(draw) do f:write(string.char(v)) end;f:close()
  dump(name..'_vram.bin',emu.memType.snesVideoRam,0,65536)
  dump(name..'_cgram.bin',emu.memType.snesCgRam,0,512)
 end
 if field>=144 then emu.stop(0) end
end),emu.eventType.endFrame)
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir',type=Path,default=BUILD)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    assert not any(out.iterdir()),'use a fresh output directory'
    build=args.build_dir.resolve();rom=build/'MonoSHFX2_v001.sfc'
    digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    labels={m[2]:int(m[1],16) for m in re.finditer(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(build/'game.lbl').read_text())}
    script=SCRIPT.replace('LABELS',lua(labels)).replace('OUTDIR',lua(out.as_posix())).replace('BASELINE',str(args.baseline).lower())
    path=out/'test.lua';path.write_text(script,encoding='utf-8')
    mesen=prepare_runtime(MESEN_EXE);settings=mesen.parent/'settings.json'
    cfg=json.loads(settings.read_text());cfg['Snes'].update(Port1={'Type':'SnesController'},DisableFrameSkipping=True)
    cfg['Debug']['ScriptWindow']['ScriptTimeout']=10;settings.write_text(json.dumps(cfg))
    result=subprocess.run([str(mesen),'--testRunner','--timeout=60','--doNotSaveSettings','--enableStdout',str(rom),str(path)],
                          cwd=mesen.parent,capture_output=True,timeout=70,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (out/'emulator.log').write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,(result.returncode,(out/'error.txt').read_text() if (out/'error.txt').exists() else result.stdout[-1000:])
    palette=struct.unpack('<32H',(GAME/'assets/bg_color/palette.bin').read_bytes())
    cases=[];ppu_pixels=0
    for n in range(1,13):
        name=f'case{n:02d}';phase=(n-1)%6;mode='color' if n<=6 else 'mono'
        data=(out/(name+'_draw.bin')).read_bytes();cx,bottom,w,h,asset,flags,z,priority=struct.unpack('<hh6B',data)
        expected_asset=([38,39,40,41,40,39] if args.baseline else [5,39,40,41,40,39])[phase]
        assert asset==expected_asset,(n,asset)
        source=np.array(Image.open(GAME/'assets/bg_color'/f'{asset:02d}.png'))
        sampled=source[(np.arange(h)*(source.shape[0]*256//h)>>8)[:,None],(np.arange(w)*(source.shape[1]*256//w)>>8)[None,:]]
        left=cx-w//2;top=bottom-h-20
        assert 0<=left and left+w<=256 and 0<=top and top+h<=192
        expected=np.zeros((192,256),dtype=np.uint8);expected[top:top+h,left:left+w]=sampled
        actual=decode_fb((out/(name+'_vram.bin')).read_bytes()[:12288])
        assert np.array_equal(actual,expected),(n,'framebuffer mismatch')
        raw=(out/(name+'.rgb')).read_bytes();image=Image.frombytes('RGB',(256,len(raw)//768),raw);image.save(out/(name+'.png'))
        colors=[rgb(word) for word in (palette[(1 if asset==38 else 4)*4:][:4] if mode=='color' else [0,0,0x7fff,0x7fff])]
        mask=expected!=0;screen=np.array(image)[19:211,:]
        assert not (np.any(screen!=np.array(colors)[expected],axis=2)&mask).any(),(n,'PPU color mismatch')
        checked=int(mask.sum());assert checked>0
        ppu_pixels+=checked
        cases.append({'phase':phase,'mode':mode,'asset':asset,'draw':[cx,bottom,w,h,asset,flags,z,priority],'opaquePpuPixels':checked})
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==digest
    summary={'romSha256':digest,'baseline':args.baseline,'cases':cases,'scenes':len(cases),'framebufferPixels':len(cases)*49152,
             'opaquePpuPixels':ppu_pixels,'bitmapErrors':0,'ppuColorErrors':0,'physicalHardwareTested':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(digest,'stage explosion',len(cases),'scenes;',ppu_pixels,'PPU pixels match')


if __name__=='__main__':main()

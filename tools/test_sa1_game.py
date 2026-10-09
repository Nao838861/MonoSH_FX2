"""実SA-1とPPUが動く統合ROMの計測。画面・転送後のVRAMも保存する。"""
import argparse,hashlib,json,re,subprocess,struct
import numpy as np
from PIL import Image
from build_sa1_game import BUILD
from run_probe import prepare_runtime,MESEN_EXE,lua
from test_sa1_probe import reference
from build_sa1_game import BASE

def verify_pixels(dest,labels):
    source=(BASE/'assets4/background4.bin').read_bytes()
    checked=0
    for path in sorted(dest.glob('present*_meta.bin')):
        prefix=path.name[:-9]
        raw=path.read_bytes();far,near,ground,count,page=struct.unpack_from('<5H',raw)
        draws=[list(struct.unpack_from('<hh6B',raw,10+i*10)) for i in range(count)]
        sprite=np.frombuffer(reference({'draws':draws}),dtype=np.uint8).reshape(192,128)
        sprite=np.stack((sprite&15,sprite>>4),axis=2).reshape(192,256)
        pix=np.zeros((192,256),dtype=np.uint8)
        for offset,scroll,top,height in ((0,far,77+ground,14),(0x8000,near,82+ground,9)):
            layer=np.frombuffer(source[offset:offset+height*512],dtype=np.uint8).reshape(height,512)[:,(np.arange(256)+scroll)&511]
            y0=max(0,top);y1=min(192,top+height)
            if y0<y1:
                p=layer[y0-top:y1-top];d=pix[y0:y1];d[p!=0]=p[p!=0]
        pix[sprite!=0]=sprite[sprite!=0]
        expected=(pix[:,::2]|pix[:,1::2]<<4).tobytes()
        actual=(dest/(prefix+'_fb.bin')).read_bytes()
        if actual!=expected:
            (dest/(prefix+'_expected.bin')).write_bytes(expected)
            raise AssertionError(f'{prefix}: framebuffer {sum(a!=b for a,b in zip(actual,expected))} bytes differ')
        tiles=pix.reshape(24,8,32,8).transpose(0,2,1,3).reshape(768,8,8)
        planar=np.zeros((768,32),dtype=np.uint8)
        for plane in range(4):planar[:,plane//2*16+plane%2+np.arange(8)*2]=(((tiles>>plane)&1)*np.array([128,64,32,16,8,4,2,1])).sum(axis=2)
        vram=(dest/(prefix+'_vram.bin')).read_bytes()[page*2:page*2+24576]
        assert vram==planar.tobytes(),f'{prefix}: converted VRAM differs'
        checked+=1
    return checked

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--frames',type=int,default=600);ap.add_argument('--scenario',default='play');args=ap.parse_args()
    dest=BUILD/args.scenario;dest.mkdir(exist_ok=True)
    for path in dest.glob('present*'):path.unlink()
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
    config=json.loads((BUILD/'manifest.json').read_text())
    assert hashlib.sha256((BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==config['romSha256']
    script='''local labels=LABELS
local output=OUTDIR
local maxframe=MAXFRAME
local scenario=SCENARIO
local padded=PADDED
local field,logic,presents=0,0,0
local begin,sa1begin,drawbegin=0,0,0
local times={}
local presentationTimes={}
local function word(name,value)
 emu.write16(0x7e0000+labels[name],value,emu.memType.snesMemory)
end
local function byte(name,value)
 emu.write(0x7e0000+labels[name],value,emu.memType.snesMemory)
end
local function cb(name,fn,cpu)
 cpu=cpu or emu.cpuType.snes
 local a=labels[name]+(cpu==emu.cpuType.snes and 0x7f0000 or 0)
 emu.addMemoryCallback(fn,emu.callbackType.exec,a,a,cpu,cpu==emu.cpuType.snes and emu.memType.snesMemory or emu.memType.sa1Memory)
end
local function dump(name,mem,a,n)
 local f=assert(io.open(output..'/'..name,'wb'));local t={}
 for i=0,n-1 do t[#t+1]=string.char(emu.read(a+i,mem)) end
 f:write(table.concat(t));f:close()
end
if labels.invoke_row then
 local recent=assert(io.open(output..'/native_trace.jsonl','w'))
 cb('invoke_row',function()
  local mt=emu.memType.sa1Memory
  local entry=emu.read16(0x7f1,mt)+65536*emu.read(0x7f3,mt)
  local n=emu.read16(0x8c,mt)
  if presents>=24 and presents<26 then
   recent:write(string.format('{"present":%d,"entry":%d,"len":%d,"dy":%d,"asset":%d,"wordstart":%d,"initialA":%d,"edge":%d}\\n',presents,entry,n,emu.read16(0x40,mt),emu.read16(0x3e,mt),emu.read16(0xd4,mt),emu.read16(0xd6,mt),emu.read16(0x90,mt)));recent:flush()
   dump('latest_jit.bin',emu.memType.sa1InternalRam,0x700,256)
  end
 end,emu.cpuType.sa1)
end
cb('_fx_frame',function()
 logic=logic+1
 if scenario=='boss' then
  byte('_monosh_player_invuln',255)
  if field>=90 then
   byte('_monosh_enemy_stage_complete_flag',1)
   byte('_monosh_enemy_active_count_value',0)
   byte('_monosh_stage_object_count',0)
   word('_monosh_stage_frame_counter',3900)
  end
 end
end)
cb('render_started',function()begin=emu.getState().masterClock end)
cb('sa1_clear_start',function()sa1begin=emu.getState().masterClock end,emu.cpuType.sa1)
cb('sa1_draw_start',function()drawbegin=emu.getState().masterClock end,emu.cpuType.sa1)
cb('sa1_draw_done',function()
 local now=emu.getState().masterClock
 if presents==0 then
  dump('first_bw.bin',emu.memType.snesSaveRam,0,65536)
  dump('first_iram.bin',emu.memType.sa1InternalRam,0,2048)
 end
 times[#times+1]=string.format('{"field":%d,"clearAndBgMs":%.6f,"drawMs":%.6f,"totalSa1Ms":%.6f}',field,(drawbegin-sa1begin)/21477.272,(now-drawbegin)/21477.272,(now-sa1begin)/21477.272)
end,emu.cpuType.sa1)
cb('dma_finished',function()
 presents=presents+1
 presentationTimes[#presentationTimes+1]=string.format('{"field":%d,"clock":%d,"dmaBytes":%d}',field,emu.getState().masterClock,emu.read16(0x7e0000+labels.fx4_dma_bytes,emu.memType.snesMemory))
 if presents<=120 or presents%60==0 then
  local n=string.format('present%05d',presents)
  if padded then
   local f=assert(io.open(output..'/'..n..'_fb.bin','wb'));local t={}
   for y=0,191 do for x=0,127 do t[#t+1]=string.char(emu.read(y*256+64+x,emu.memType.snesSaveRam))end end
   f:write(table.concat(t));f:close()
  else dump(n..'_fb.bin',emu.memType.snesSaveRam,0,24576)end
  dump(n..'_vram.bin',emu.memType.snesVideoRam,0,65536)
  local count=emu.read16(0x3106,emu.memType.snesMemory)
  local f=assert(io.open(output..'/'..n..'_meta.bin','wb'))
  local t={}
  for _,a in ipairs({0x3108,0x310a,0x310c,0x3106,0x7e0000+labels.fx4_page})do
   local v=emu.read16(a,emu.memType.snesMemory);t[#t+1]=string.char(v&255,v>>8)
  end
  for i=0,count*10-1 do t[#t+1]=string.char(emu.read(0x430000+i,emu.memType.snesMemory))end
  f:write(table.concat(t));f:close()
 end
end)
emu.addEventCallback(function()emu.setInput({a=true},0)end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 field=field+1
 if field==120 or field==maxframe then
  local f=assert(io.open(output..'/frame'..field..'.rgb','wb'));local t={}
  for _,v in ipairs(emu.getScreenBuffer())do t[#t+1]=string.char((v>>16)&255,(v>>8)&255,v&255)end
  f:write(table.concat(t));f:close()
 end
 if field==maxframe then
  local f=assert(io.open(output..'/summary.json','w'))
  f:write(string.format('{"fields":%d,"logic":%d,"presents":%d,"presentationTimes":[%s],"sa1Jobs":[%s]}',field,logic,presents,table.concat(presentationTimes,','),table.concat(times,',')));f:close()
  dump('iram.bin',emu.memType.sa1InternalRam,0,2048)
  emu.stop(0)
 end
end,emu.eventType.endFrame)
'''.replace('LABELS',lua(labels)).replace('OUTDIR',lua(dest.as_posix())).replace('MAXFRAME',str(args.frames)).replace('SCENARIO',lua(args.scenario)).replace('PADDED','true' if config.get('paddedFramebuffer',False) else 'false')
    path=dest/'test.lua';path.write_text(script)
    exe=prepare_runtime(MESEN_EXE)
    settings=exe.parent/'settings.json';cfg=json.loads(settings.read_text());cfg['Snes'].update(DisableFrameSkipping=True,Port1={'Type':'SnesController'});settings.write_text(json.dumps(cfg))
    result=subprocess.run([str(exe),'--testRunner','--timeout=180','--doNotSaveSettings','--enableStdout',str(BUILD/'MonoSHSA1_4bpp_game.sfc'),str(path)],cwd=exe.parent,capture_output=True,timeout=190,creationflags=subprocess.CREATE_NO_WINDOW)
    (dest/'emulator.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:print((result.stdout+result.stderr).decode(errors='replace'));raise RuntimeError('Mesen failed')
    for f in dest.glob('*.rgb'):
        raw=f.read_bytes();Image.frombytes('RGB',(256,len(raw)//768),raw).save(f.with_suffix('.png'))
    summary=json.loads((dest/'summary.json').read_text())
    print(json.dumps({k:v for k,v in summary.items() if k not in ('sa1Jobs','presentationTimes')}))
    assert summary['presents']>0,'SA-1 game never presented an image'
    print('SA-1 max ms:',max(x['totalSa1Ms'] for x in summary['sa1Jobs']))
    summary['pixelMatchedPresents']=verify_pixels(dest,labels)
    summary['romSha256']=config['romSha256']
    summary['labelsSha256']=hashlib.sha256((BUILD/'game.lbl').read_bytes()).hexdigest()
    intervals=np.diff([p['field'] for p in summary['presentationTimes'][2:]])
    summary['presentationFieldIntervals']={str(int(k)):int(v) for k,v in zip(*np.unique(intervals,return_counts=True))}
    summary['goal60fpsAchieved']=bool(len(intervals) and np.all(intervals==1))
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('Pixel-matched presents:',summary['pixelMatchedPresents'])

if __name__=='__main__':main()

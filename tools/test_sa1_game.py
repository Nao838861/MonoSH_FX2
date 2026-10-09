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
    ap=argparse.ArgumentParser();ap.add_argument('--frames',type=int,default=600);ap.add_argument('--scenario',default='play');ap.add_argument('--presents',type=int,default=0);args=ap.parse_args()
    dest=BUILD/args.scenario;dest.mkdir(exist_ok=True)
    (dest/'failure.txt').unlink(missing_ok=True)
    for path in dest.glob('present*'):path.unlink()
    for path in dest.glob('frame*'):
        if re.fullmatch(r'frame\d+\.(png|rgb)',path.name):path.unlink()
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
    config=json.loads((BUILD/'manifest.json').read_text())
    assert hashlib.sha256((BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==config['romSha256']
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    frame_size=int(re.search(r'frame_asm.o:\s+CODE\s+Offs=[0-9A-F]+\s+Size=([0-9A-F]+)',(BUILD/'game.map').read_text())[1],16)
    frame_start=labels['_fx_frame'];frame_code=rom[0x410000+frame_start:0x410000+frame_start+frame_size]
    calls={}
    for name in ('_fx_read_input','_monosh_combat_fast_frame','_monosh_combat_render','_monosh_enemy_frame','_monosh_stage_frame','_monosh_boss_frame','_monosh_boss_prepare_render','_monosh_boss_render_only','_fx_build_packet','_fx_build_ground'):
        needle=b'\x20'+struct.pack('<H',labels[name])
        calls[name]=[frame_start+i for i in range(len(frame_code)-2) if frame_code[i:i+3]==needle]
    script='''local labels=LABELS
local output=OUTDIR
local maxframe=MAXFRAME
local targetPresents=TARGETPRESENTS
local scenario=SCENARIO
local padded=PADDED
local pipeline=PIPELINE
local field,logic,presents=0,0,0
local begin,sa1begin,drawbegin=0,0,0
local dirtyDone,clearDone,nativeDone=0,0,0
local dirtyMs,clearMs,bgMs,nativeMs,logicMs=0,0,0,0,0
local times={}
local presentationTimes={}
local readyLine,startClock,waitMs=0,0,0
local cpuParts,cpuEntries={},{}
local cpuJobs={}
local sortReference=nil
local packetTrace=assert(io.open(output..'/packet_trace.bin','wb'))
local completedFrames={}
local completedPackets={}
local outputJobs={}
local queueSamples={}
local objectJobs={}
local dmaJobs={}
local dmaClock,dmaLength,dmaLine=0,0,0
local objectBegin=0
local function word(name,value)
 emu.write16(0x7e0000+labels[name],value,emu.memType.snesMemory)
end
for name,sites in pairs(CALLS)do
 for _,site in ipairs(sites)do
  emu.addMemoryCallback(function()cpuEntries[name]=emu.getState().masterClock end,emu.callbackType.exec,0x7f0000+site,0x7f0000+site)
  emu.addMemoryCallback(function()cpuParts[name]=(cpuParts[name] or 0)+(emu.getState().masterClock-cpuEntries[name])/21477.272 end,emu.callbackType.exec,0x7f0000+site+3,0x7f0000+site+3)
 end
end
local function byte(name,value)
 emu.write(0x7e0000+labels[name],value,emu.memType.snesMemory)
end
local function cb(name,fn,cpu)
 cpu=cpu or emu.cpuType.snes
 local a=labels[name]+(cpu==emu.cpuType.snes and 0x7f0000 or 0)
 emu.addMemoryCallback(function()local ok,err=pcall(fn);if not ok then local f=assert(io.open(output..'/failure.txt','w'));f:write(tostring(err));f:close();local g=assert(io.open(output..'/failure_state.txt','w'));for k,v in pairs(emu.getState())do g:write(tostring(k)..'='..tostring(v)..'\\n')end;g:close();emu.stop(1)end end,emu.callbackType.exec,a,a,cpu,cpu==emu.cpuType.snes and emu.memType.snesMemory or emu.memType.sa1Memory)
end
local packetClock,irqTicks,irqClock=0,0,0
local function activeClock()local c=emu.getState().masterClock;return c-irqTicks-(irqClock>0 and c-irqClock or 0)end
if pipeline then
 cb('pipe_irq',function()irqClock=emu.getState().masterClock end)
 cb('pipe_irq_exit',function()irqTicks=irqTicks+emu.getState().masterClock-irqClock;irqClock=0 end)
end
cb('_fx_build_packet',function()packetClock=activeClock() end)
for _,name in ipairs({'initialized','sorted','packet_done'})do
 cb(name,function()local c=activeClock();cpuParts['packet_'..name]=(c-packetClock)/21477.272;packetClock=c end)
end
if pipeline then
 cb('dma_started',function()
  local state=emu.getState();dmaClock=state.masterClock;dmaLine=state['ppu.scanline'];dmaLength=emu.read16(0x4305,emu.memType.snesMemory)
 end)
 cb('pipe_dma_measured_end',function()
  local state=emu.getState();dmaJobs[#dmaJobs+1]=string.format('{"field":%d,"line":%d,"endLine":%d,"length":%d,"ms":%.6f}',field,dmaLine,state['ppu.scanline'],dmaLength,(state.masterClock-dmaClock)/21477.272)
 end)
 local diag=assert(io.open(output..'/pipeline_trace.jsonl','w'))
 for _,name in ipairs({'pipe_irq','pipe_irq_transfer','pipe_wait_dma','dma_started','half_dma_finished','prefetch_finished','pipe_irq_done'})do
  cb(name,function()
   if presents<10 then
    local s=emu.getState();local mt=emu.memType.snesMemory
    diag:write(string.format('{\"label\":\"%s\",\"field\":%d,\"present\":%d,\"line\":%d,\"clock\":%d,\"src\":%d,\"len\":%d,\"grant\":%d}\\n',name,field,presents,s['ppu.scanline'],s.masterClock,emu.read16(0x4302,mt)+65536*emu.read(0x4304,mt),emu.read16(0x4305,mt),emu.read16(0x311c,mt)));diag:flush()
   end
  end)
 end
 cb('prefetch_finished',function()
  local mt=emu.memType.snesMemory
  local slot=emu.read16(0x7e0000+labels.pipe_target_slot,mt)
  local record=0x7e0000+labels.pipe_records+slot*512
  local gen=emu.read16(record+8,mt)
  if gen<=120 or gen%60==0 then
   local bank=emu.read16(record,mt);local t={}
   for i=0,24575 do t[#t+1]=string.char(emu.read((bank-0x40)*65536+i,emu.memType.snesSaveRam))end
   completedFrames[gen]=table.concat(t)
  end
 end)
 cb('pipe_irq_done',function()
  local line=emu.getState()['ppu.scanline'];assert(line<=22 or line>=203,'PPU transfer exceeded blank period line='..line..' field='..field..' presents='..presents)
  local mt=emu.memType.snesMemory;local ready=0;local rendering=0
  for i=0,DEPTH-1 do local s=emu.read16(0x7e0000+labels.pipe_status+i*2,mt);if s==2 then ready=ready+1 elseif s==1 then rendering=rendering+1 end end
  queueSamples[#queueSamples+1]=string.format('{\"field\":%d,\"line\":%d,\"ready\":%d,\"rendering\":%d,\"complete\":%d,\"flipped\":%d,\"target\":%d}',field,line,ready,rendering,emu.read16(0x7e0000+labels.pipe_complete,mt),emu.read16(0x7e0000+labels.pipe_presented_irq,mt),emu.read16(0x7e0000+labels.pipe_target_slot,mt))
 end)
end
if labels.sa1_sort_packet or labels.sa1_temporal_prepare then
 cb(labels.sa1_sort_packet and 'sa1_sort_packet' or 'sa1_temporal_prepare',function()
  local mt=emu.memType.snesMemory;local n=emu.read16(0x7e0000+labels.packet_work+8,mt)
  sortReference={}
  for i=0,n-2,2 do sortReference[#sortReference+1]={key=emu.read16(0x7e0000+labels.keys+i,mt),value=emu.read16(0x7e0000+labels.order+i,mt),index=i}end
  table.sort(sortReference,function(a,b)return a.key<b.key or (a.key==b.key and a.index<b.index)end)
 end)
 cb('sorted',function()
  if sortReference then
   for i,v in ipairs(sortReference)do assert(emu.read16(0x7e0000+labels.order+(i-1)*2,emu.memType.snesMemory)==v.value,'packet sort changed depth/priority/stability')end
   sortReference=nil
  end
 end)
end
local function dump(name,mem,a,n)
 local f=assert(io.open(output..'/'..name,'wb'));local t={}
 for i=0,n-1 do t[#t+1]=string.char(emu.read(a+i,mem)) end
 f:write(table.concat(t));f:close()
end
if labels.fast_base_ready then
 local debug=assert(io.open(output..'/fast_debug.txt','w'))
 for _,name in ipairs({'sa1_try_fast','fast_tiles','fast_fail','fast_base_ready','invoke_row'})do
  cb(name,function()
   if presents==0 then
    local mt=emu.memType.sa1Memory
    debug:write(name)
    for _,a in ipairs({0x34,0x36,0x38,0x3a,0x44,0x48,0xa0,0xa2,0xb0,0xb2,0xb4,0xc0,0xc2,0xf8})do debug:write(string.format(' %02x=%04x',a,emu.read16(a,mt)))end
    debug:write('\\n');debug:flush()
   end
  end,emu.cpuType.sa1)
 end
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
 begin=emu.getState().masterClock
 if scenario:match('^boss') then
  byte('_monosh_player_invuln',255)
  if field>=90 then
   byte('_monosh_enemy_stage_complete_flag',1)
   byte('_monosh_enemy_active_count_value',0)
   byte('_monosh_stage_object_count',0)
   word('_monosh_stage_frame_counter',3900)
  end
 end
end)
cb('render_started',function()begin=emu.getState().masterClock;cpuParts={} end)
cb('logic_finished',function()
 logicMs=(emu.getState().masterClock-begin)/21477.272
 local parts={};for name,v in pairs(cpuParts)do parts[#parts+1]=string.format('"%s":%.6f',name,v)end
 cpuJobs[#cpuJobs+1]=string.format('{"field":%d,"logicMs":%.6f,"parts":{%s}}',field,logicMs,table.concat(parts,','))
end)
cb('transfer_chunk',function()local s=emu.getState();readyLine=s['ppu.scanline'];startClock=s.masterClock end)
cb('dma_chunk_ready',function()waitMs=(emu.getState().masterClock-startClock)/21477.272;startClock=emu.getState().masterClock end)
cb('sa1_clear_start',function()sa1begin=emu.getState().masterClock end,emu.cpuType.sa1)
if labels.sa1_sprite_begin then
 cb('sa1_sprite_begin',function()objectBegin=emu.getState().masterClock end,emu.cpuType.sa1)
 cb('sa1_sprite_done',function()
  local mt=emu.memType.sa1Memory;local i=emu.read16(0x2c,mt);local a=0x430000+i*10;local ms=(emu.getState().masterClock-objectBegin)/21477.272
  if ms>0.5 then objectJobs[#objectJobs+1]=string.format('{\"field\":%d,\"job\":%d,\"index\":%d,\"asset\":%d,\"width\":%d,\"height\":%d,\"x\":%d,\"bottom\":%d,\"ms\":%.6f}',field,#times+1,i,emu.read(a+6,mt),emu.read(a+4,mt),emu.read(a+5,mt),emu.read16(a,mt),emu.read16(a+2,mt),ms)end
 end,emu.cpuType.sa1)
end
if labels.sa1_output_done then cb('sa1_output_done',function()outputJobs[#outputJobs+1]=string.format('{\"field\":%d,\"totalOutputMs\":%.6f}',field,(emu.getState().masterClock-sa1begin)/21477.272)end,emu.cpuType.sa1)end
if labels.sa1_dirty_done then
 cb('sa1_dirty_done',function()dirtyDone=emu.getState().masterClock;dirtyMs=(dirtyDone-sa1begin)/21477.272 end,emu.cpuType.sa1)
 cb('sa1_clear_done',function()clearDone=emu.getState().masterClock;clearMs=(clearDone-dirtyDone)/21477.272 end,emu.cpuType.sa1)
 cb('sa1_native_done',function()nativeDone=emu.getState().masterClock;nativeMs=(nativeDone-drawbegin)/21477.272 end,emu.cpuType.sa1)
end
cb('sa1_draw_start',function()drawbegin=emu.getState().masterClock;bgMs=(drawbegin-clearDone)/21477.272 end,emu.cpuType.sa1)
cb('sa1_draw_done',function()
 local now=emu.getState().masterClock
 local mt=emu.memType.sa1Memory;local n=emu.read16(0x106,mt);local trace={}
 for _,a in ipairs({0x108,0x10a,0x10c,0x106})do local v=emu.read16(a,mt);trace[#trace+1]=string.char(v&255,v>>8)end
 for i=0,n*10-1 do trace[#trace+1]=string.char(emu.read(0x430000+i,mt))end
 packetTrace:write(table.concat(trace))
 if pipeline then
  local cpuMt=emu.memType.snesMemory;local slot=emu.read16(0x7e0000+labels.pipe_render_slot,cpuMt)
  local gen=emu.read16(0x7e0000+labels.pipe_records+slot*512+8,cpuMt)
  if gen<=120 or gen%60==0 then local t={};for i=0,n*10-1 do t[#t+1]=string.char(emu.read(0x430000+i,mt))end;completedPackets[gen]=table.concat(t)end
 end
 local dirtyBytes=0
 for r=0,23 do local a=0x120+r*4;dirtyBytes=dirtyBytes+math.max(0,emu.read16(a+2,emu.memType.sa1Memory)-emu.read16(a,emu.memType.sa1Memory))*8 end
 if presents==0 then
  dump('first_bw.bin',emu.memType.snesSaveRam,0,65536)
  dump('first_iram.bin',emu.memType.sa1InternalRam,0,2048)
 end
 local parts={};for name,v in pairs(cpuParts)do parts[#parts+1]=string.format('"%s":%.6f',name,v)end
 times[#times+1]=string.format('{"field":%d,"clearAndBgMs":%.6f,"drawMs":%.6f,"totalSa1Ms":%.6f,"dirtyMs":%.6f,"clearMs":%.6f,"bgMs":%.6f,"nativeMs":%.6f,"compactMs":%.6f,"logicMs":%.6f,"dirtyBytes":%d,"cpuParts":{%s}}',field,(drawbegin-sa1begin)/21477.272,(now-drawbegin)/21477.272,(now-sa1begin)/21477.272,dirtyMs,clearMs,bgMs,nativeMs,(now-nativeDone)/21477.272,logicMs,dirtyBytes,table.concat(parts,','))
end,emu.cpuType.sa1)
cb('dma_finished',function()
 presents=presents+1
 if pipeline then local mt=emu.memType.snesMemory;local slot=emu.read16(0x7e0000+labels.pipe_front_slot,mt);assert(emu.read16(0x7e0000+labels.pipe_records+slot*512+8,mt)==presents,'pipeline skipped or reordered a frame')end
 local state=emu.getState();local line=state['ppu.scanline']
 local visibleField=field+(line>=203 and line<225 and 1 or 0)
 assert(line<=22 or line>=203,'page flip occurred during visible lines')
 presentationTimes[#presentationTimes+1]=string.format('{"field":%d,"visibleField":%d,"line":%d,"clock":%d,"dmaBytes":%d,"readyLine":%d,"waitMs":%.6f,"transferMs":%.6f}',field,visibleField,line,state.masterClock,emu.read16(0x7e0000+labels.fx4_dma_bytes,emu.memType.snesMemory),readyLine,waitMs,(state.masterClock-startClock)/21477.272)
 if presents<=120 or presents%60==0 then
  local n=string.format('present%05d',presents)
  local record=nil
  if pipeline then
   local mt=emu.memType.snesMemory;local slot=emu.read16(0x7e0000+labels.pipe_front_slot,mt)
   record=0x7e0000+labels.pipe_records+slot*512
   local gen=emu.read16(record+8,mt);assert(gen==presents,'pipeline skipped or reordered a frame')
   for i=0,23 do assert(emu.read(i,emu.memType.snesSpriteRam)==emu.read(record+64+i,mt),'pipeline OAM differs')end
   for i=0,7 do assert(emu.read(512+i,emu.memType.snesSpriteRam)==emu.read(record+192+i,mt),'pipeline high OAM differs')end
   local f=assert(io.open(output..'/'..n..'_fb.bin','wb'));f:write((assert(completedFrames[gen],'missing completed snapshot')));f:close();completedFrames[gen]=nil
  elseif padded then
   local f=assert(io.open(output..'/'..n..'_fb.bin','wb'));local t={}
   for y=0,191 do for x=0,127 do t[#t+1]=string.char(emu.read(y*256+64+x,emu.memType.snesSaveRam))end end
   f:write(table.concat(t));f:close()
  else dump(n..'_fb.bin',emu.memType.snesSaveRam,0,24576)end
  dump(n..'_vram.bin',emu.memType.snesVideoRam,0,65536)
  local count=emu.read16(pipeline and record+16 or 0x3106,emu.memType.snesMemory)
  local f=assert(io.open(output..'/'..n..'_meta.bin','wb'))
  local t={}
  local addresses=pipeline and {record+10,record+12,record+14,record+16,0x7e0000+labels.fx4_page} or {0x3108,0x310a,0x310c,0x3106,0x7e0000+labels.fx4_page}
  for _,a in ipairs(addresses)do
   local v=emu.read16(a,emu.memType.snesMemory);t[#t+1]=string.char(v&255,v>>8)
  end
  if pipeline then
   local gen=emu.read16(record+8,emu.memType.snesMemory)
   t[#t+1]=assert(completedPackets[gen],'missing completed packet');completedPackets[gen]=nil
  else
   for i=0,count*10-1 do t[#t+1]=string.char(emu.read(0x430000+i,emu.memType.snesMemory))end
  end
  f:write(table.concat(t));f:close()
 end
end)
emu.addEventCallback(function()emu.setInput({a=true},0)end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 field=field+1
 local finished=field==maxframe or (targetPresents>0 and presents>=targetPresents)
 if field==120 or finished then
  local f=assert(io.open(output..'/frame'..field..'.rgb','wb'));local t={}
  for _,v in ipairs(emu.getScreenBuffer())do t[#t+1]=string.char((v>>16)&255,(v>>8)&255,v&255)end
  f:write(table.concat(t));f:close()
 end
 if finished then
  local st=assert(io.open(output..'/end_state.txt','w'));for k,v in pairs(emu.getState())do st:write(tostring(k)..'='..tostring(v)..'\\n')end;st:close()
  dump('end_wram.bin',emu.memType.snesWorkRam,0,131072)
  packetTrace:close()
  local f=assert(io.open(output..'/summary.json','w'))
  f:write(string.format('{"fields":%d,"logic":%d,"presents":%d,"presentationTimes":[%s],"sa1Jobs":[%s],"cpuJobs":[%s],"outputJobs":[%s],"queueSamples":[%s],"objectJobs":[%s],"dmaJobs":[%s]}',field,logic,presents,table.concat(presentationTimes,','),table.concat(times,','),table.concat(cpuJobs,','),table.concat(outputJobs,','),table.concat(queueSamples,','),table.concat(objectJobs,','),table.concat(dmaJobs,',')));f:close()
  dump('iram.bin',emu.memType.sa1InternalRam,0,2048)
  emu.stop(0)
 end
end,emu.eventType.endFrame)
'''.replace('LABELS',lua(labels)).replace('CALLS',lua(calls)).replace('OUTDIR',lua(dest.as_posix())).replace('MAXFRAME',str(args.frames)).replace('TARGETPRESENTS',str(args.presents)).replace('SCENARIO',lua(args.scenario)).replace('PADDED','true' if config.get('paddedFramebuffer',False) else 'false').replace('DEPTH',str(config.get('pipelineDepth',3))).replace('PIPELINE','true' if config.get('pipeline',False) else 'false')
    path=dest/'test.lua';path.write_text(script)
    exe=prepare_runtime(MESEN_EXE)
    settings=exe.parent/'settings.json';cfg=json.loads(settings.read_text());cfg['Snes'].update(DisableFrameSkipping=True,Port1={'Type':'SnesController'});settings.write_text(json.dumps(cfg))
    result=subprocess.run([str(exe),'--testRunner','--timeout=180','--doNotSaveSettings','--enableStdout',str(BUILD/'MonoSHSA1_4bpp_game.sfc'),str(path)],cwd=exe.parent,capture_output=True,timeout=190,creationflags=subprocess.CREATE_NO_WINDOW)
    (dest/'emulator.log').write_bytes(result.stdout+result.stderr)
    if (dest/'failure.txt').exists():raise AssertionError((dest/'failure.txt').read_text())
    if result.returncode:print((result.stdout+result.stderr).decode(errors='replace'));raise RuntimeError('Mesen failed')
    for f in dest.glob('*.rgb'):
        raw=f.read_bytes();Image.frombytes('RGB',(256,len(raw)//768),raw).save(f.with_suffix('.png'))
    summary=json.loads((dest/'summary.json').read_text())
    print(json.dumps({k:v for k,v in summary.items() if k not in ('sa1Jobs','presentationTimes','cpuJobs','outputJobs','queueSamples','objectJobs','dmaJobs')}))
    assert summary['presents']>0,'SA-1 game never presented an image'
    print('SA-1 max ms:',max(x['totalSa1Ms'] for x in summary['sa1Jobs']))
    summary['pixelMatchedPresents']=verify_pixels(dest,labels)
    summary['romSha256']=config['romSha256']
    summary['labelsSha256']=hashlib.sha256((BUILD/'game.lbl').read_bytes()).hexdigest()
    intervals=np.diff([p['visibleField'] for p in summary['presentationTimes'][2:]])
    summary['presentationFieldIntervals']={str(int(k)):int(v) for k,v in zip(*np.unique(intervals,return_counts=True))}
    summary['goal60fpsAchieved']=bool(len(intervals) and np.all(intervals==1))
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('Pixel-matched presents:',summary['pixelMatchedPresents'])

if __name__=='__main__':main()

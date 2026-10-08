local labels=LABELS
local output=OUTDIR
local maxframe=MAXFRAME
local scenario=SCENARIO
local field=0
local starts,finishes,halves,logic=0,0,0,0
local gsu_start=0
local lastfield=0
local trace=assert(io.open(output..'/trace.jsonl','w'))
local intervals={}
local gsuMax=0
local fixture=false
local bossSeen,dyingSeen,doneSeen,restartSeen=false,false,false,false
local function put(name,offset,v)
  emu.write(0x7e0000+assert(labels[name])+offset,v&255,emu.memType.snesMemory)
end
local function word(name,v) put(name,0,v);put(name,1,v>>8) end
local function read(name,n)
  local a=0x7e0000+assert(labels[name],name)
  local v=emu.read(a,emu.memType.snesMemory)
  if n==2 then v=v+256*emu.read(a+1,emu.memType.snesMemory) end
  return v
end
local function dump(name,mem,a,n)
  local f=assert(io.open(output..'/'..name,'wb'));local t={}
  for i=0,n-1 do t[#t+1]=string.char(emu.read(a+i,mem)) end
  f:write(table.concat(t));f:close()
end
local function screenshot(name)
  local f=assert(io.open(output..'/'..name..'.rgb','wb'));local t={}
  for _,v in ipairs(emu.getScreenBuffer()) do t[#t+1]=string.char((v>>16)&255,(v>>8)&255,v&255) end
  f:write(table.concat(t));f:close()
end
local function cb(name,fn)
  local a=0x7f0000+assert(labels[name],name)
  emu.addMemoryCallback(fn,emu.callbackType.exec,a,a,emu.cpuType.snes,emu.memType.snesMemory)
end
cb('_fx_frame',function()
  logic=logic+1
  if scenario=='boss' or scenario=='boss_hold' then
    put('_monosh_player_invuln',0,255)
    if field>=90 and not fixture then
      fixture=true
      put('_monosh_enemy_stage_complete_flag',0,1)
      put('_monosh_enemy_active_count_value',0,0);put('_monosh_enemy_bullet_count',0,0)
      put('_monosh_stage_object_count',0,0)
      put('_monosh_stage_spawn_index',0,read('_monosh_stage1_spawn_count',2)-1)
      word('_monosh_stage_frame_counter',3900)
    end
    if scenario=='boss' and read('_monosh_boss_state',1)==1 and field>600 then
      local z=read('_boss_part_z',1)
      local height=emu.read(0x7e0000+labels._monosh_boss_face_geometry+math.min(z,110)*2+1,emu.memType.snesMemory)
      if z>=8 and z<=90 then
        put('_monosh_player_bullets',0,1)
        put('_monosh_player_bullets',1,read('_boss_part_x',1))
        put('_monosh_player_bullets',2,read('_boss_part_bottom',1)-height//2)
        put('_monosh_player_bullets',3,math.max(0,z//2-2));put('_monosh_player_bullets',4,3)
        put('_monosh_player_bullet_count',0,1)
      end
    end
  end
  if scenario=='controls' then put('_monosh_player_invuln',0,255) end
  if scenario=='death' and field>=300 and not fixture then
    fixture=true;put('_monosh_player_invuln',0,0);put('_hit_pending',0,1)
  end
end)
cb('render_started',function()
  starts=starts+1;gsu_start=emu.getState().masterClock
  trace:write(string.format('{"startLine":%d,"field":%d}\n',emu.getState()['ppu.scanline'],field))
  if starts%60==0 or starts==1 then
    dump(string.format('frame%05d_packet.bin',starts),emu.memType.gsuWorkRam,0,1536)
    dump(string.format('frame%05d_background.bin',starts),emu.memType.gsuWorkRam,0x1000,16)
    dump(string.format('frame%05d_prepared.bin',starts),emu.memType.gsuWorkRam,0x8000,0x3400)
  end
end)
cb('render_second_started',function() gsu_start=emu.getState().masterClock end)
cb('render_second_finished',function()
  trace:write(string.format('{"secondGsuMs":%.6f,"field":%d}\n',((emu.getState().masterClock-gsu_start)&0xffffffff)/21477.272,field))
end)
cb('render_finished',function()
  local ms=((emu.getState().masterClock-gsu_start)&0xffffffff)/21477.272
  gsuMax=math.max(gsuMax,ms)
  trace:write(string.format('{"gsuMs":%.6f,"field":%d,"logic":%d}\n',ms,field,read('_monosh_runtime_frame_counter',2)))
end)
local currentDraw=nil
local profile={}
local function endDraw()
 if currentDraw then
  local elapsed=(emu.getState().masterClock-currentDraw.clock)&0xffffffff
  local key=currentDraw.key;profile[key]=profile[key] or {sum=0,n=0,max=0}
  local a=profile[key];a.sum=a.sum+elapsed;a.n=a.n+1;a.max=math.max(a.max,elapsed);currentDraw=nil
 end
end
for _,nm in ipairs({'dispatch_nonzero','render_stop','generic','margin_render','scaled_render4'}) do
 emu.addMemoryCallback(function()
  if nm=='dispatch_nonzero' or nm=='render_stop' then endDraw();return end
  local ss=emu.getState();local meta=emu.read(0x0b,emu.memType.gsuWorkRam)
  currentDraw={clock=ss.masterClock,key=nm..'_'..(meta&63)}
 end,emu.callbackType.exec,labels[nm],labels[nm],emu.cpuType.gsu,emu.memType.gsuMemory)
end
emu.addMemoryCallback(function()
  trace:write(string.format('{"actualGsuMs":%.6f,"field":%d}\n',((emu.getState().masterClock-gsu_start)&0xffffffff)/21477.272,field))
end,emu.callbackType.exec,labels.render_stop,labels.render_stop,emu.cpuType.gsu,emu.memType.gsuMemory)
cb('dma_started',function()
  halves=halves+1
  local line=emu.getState()['ppu.scanline']
  assert(line>=203,'DMA started in visible region')
  trace:write(string.format('{"dmaStartLine":%d,"field":%d}\n',line,field))
end)
cb('dma_finished',function()
  finishes=finishes+1
  local interval=field-lastfield;intervals[interval]=(intervals[interval] or 0)+1;lastfield=field
  local state=emu.getState()
  assert(state['ppu.scanline']<=22,'4bpp swap missed the blanking boundary')
  local boss=read('_monosh_boss_state',1)
  bossSeen=bossSeen or boss==1;dyingSeen=dyingSeen or boss==2;doneSeen=doneSeen or boss==3
  restartSeen=restartSeen or (doneSeen and boss==0)
  trace:write(string.format('{"present":%d,"field":%d,"interval":%d,"logic":%d,"page":%d,"boss":%d,"line":%d}\n',finishes,field,interval,read('_monosh_runtime_frame_counter',2),read('fx4_page',2),read('_monosh_boss_state',1),state['ppu.scanline']))
  if finishes%60==0 then
    dump(string.format('frame%05d_fb.bin',finishes),emu.memType.gsuWorkRam,0x2000,24576)
    dump(string.format('frame%05d_vram.bin',finishes),emu.memType.snesVideoRam,0,65536)
    dump(string.format('frame%05d_bounds.bin',finishes),emu.memType.gsuWorkRam,0x580,64)
    local f=assert(io.open(output..string.format('/frame%05d_meta.json',finishes),'w'))
    f:write(string.format('{"page":%d,"field":%d}',read('fx4_page',2),field));f:close()
  end
end)
emu.addEventCallback(function()
  field=field+1
  local input={y=scenario~='boss_hold'}
  if scenario=='controls' then
    local phase=(field//240)%4
    input.up=phase==0;input.right=phase==1;input.down=phase==2;input.left=phase==3
  end
  if scenario=='pause' then input.start=(field>=151 and field<=154) or (field>=211 and field<=214) end
  emu.setInput(input,0)
  if field%240==0 then screenshot(string.format('screen%05d',field)) end
  if field>=maxframe then
    for k,v in pairs(profile) do trace:write(string.format("profile %s n=%d sumMs=%.3f maxMs=%.3f\n",k,v.n,v.sum/21477.272,v.max/21477.272)) end
    local sf=assert(io.open(output.."/state.json","w")); for k,v in pairs(emu.getState()) do sf:write(tostring(k).."="..tostring(v).."\n") end;sf:close()
    trace:close()
    local f=assert(io.open(output..'/summary.json','w'))
    local ii={};for k,v in pairs(intervals) do ii[#ii+1]=string.format('"%d":%d',k,v) end
    f:write(string.format('{"fields":%d,"renders":%d,"starts":%d,"halves":%d,"logicCalls":%d,"logic":%d,"gsuMaxMs":%.6f,"intervals":{%s},"bossSeen":%s,"dyingSeen":%s,"doneSeen":%s,"restartSeen":%s}',field,finishes,starts,halves,logic,read('_monosh_runtime_frame_counter',2),gsuMax,table.concat(ii,','),tostring(bossSeen),tostring(dyingSeen),tostring(doneSeen),tostring(restartSeen)));f:close();emu.stop(0)
  end
end,emu.eventType.startFrame)

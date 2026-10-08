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
local mathChecks=0
local dma_start_clock=0
local finished=false
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
  emu.addMemoryCallback(function(...)
    if finished then return end
    local ok,err=pcall(fn,...)
    if not ok then
      local f=assert(io.open(output..'/failure.txt','w'));f:write(tostring(err));f:close()
      trace:flush();emu.log(tostring(err));emu.stop(1)
    end
  end,emu.callbackType.exec,a,a,emu.cpuType.snes,emu.memType.snesMemory)
end
local nextPlayerInput=nil
local presentPlayerInput=nil
local nextBulletAges=nil
local presentBulletAges=nil
local nextEffectPhase=nil
local presentEffectPhase=nil
local objectBuilds=0
if labels.player4_present then
 cb('fx_build_obj',function()
  if scenario=='players' then
   local poses={9,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30}
   local phase=objectBuilds%408;objectBuilds=objectBuilds+1
   local pose=poses[phase%17+1];local flip=(phase//17)%4;local clipping=phase//68
   local centers={128,8,249,128,128,128};local bottoms={150,150,150,35,252,150}
   put('_fx_draw_count',0,1)
   local values={centers[clipping+1]&255,centers[clipping+1]>>8,bottoms[clipping+1]&255,bottoms[clipping+1]>>8,32,48,pose,flip*16+(clipping==5 and 128 or 0),0,2}
   for i,v in ipairs(values) do put('_fx_draw',i-1,v) end
  end
  nextPlayerInput=nil
  local mt=emu.memType.snesMemory;local base=0x7e0000+labels._fx_draw
  for i=0,read('_fx_draw_count',1)-1 do
   local a=base+i*10
   local function byte(o)return emu.read(a+o,mt)end
   local asset=byte(6)
   if byte(9)==2 and byte(4)==32 and byte(5)==48 and (asset==9 or asset>=15 and asset<=30) then
    local x=byte(0)+byte(1)*256;if x>=32768 then x=x-65536 end
    local y=byte(2)+byte(3)*256;if y>=32768 then y=y-65536 end
    local flags=byte(7);local visible=(flags&128)==0 or ((read('_monosh_runtime_frame_counter',2)>>1)&1)==0
    nextPlayerInput=string.format('{"center":%d,"bottom":%d,"asset":%d,"flags":%d,"visible":%s}',x,y,asset,flags,tostring(visible))
   end
  end
 end)
 cb('fx_latch_obj',function()presentPlayerInput=nextPlayerInput;presentBulletAges=nextBulletAges;presentEffectPhase=nextEffectPhase end)
end
if scenario=='effects' then
 local function seedExplosion()
  put('_monosh_enemy_active_count_value',0,1)
  put('_monosh_enemy_bullet_count',0,0)
  local data={1,2,0,48,96,144,40,0,64,48}
  for i,v in ipairs(data)do put('_monosh_enemies',i-1,v)end
 end
 cb('_monosh_enemy_fast_advance',seedExplosion)
 cb('_monosh_enemy_render_only',seedExplosion)
 cb('_fx_enemy_render',function()
  nextEffectPhase=((logic-1)//8)%6
  put('_monosh_enemy_active_count_value',0,1)
  local data={1,2,0,48-nextEffectPhase*8,96,144,40,0,64,48}
  for i,v in ipairs(data)do put('_monosh_enemies',i-1,v)end
 end)
 cb('_monosh_boss_render_only',function()
  for i=0,8 do put('_boss_part_active',i,0)end
  put('_boss_part_active',0,2);put('_boss_part_x',0,192)
  put('_boss_part_bottom',0,144);put('_boss_part_z',0,40)
  put('_boss_part_timer',0,112-(((logic-1)//8)%6)*8)
  put('_boss_render_camera_delta',0,read('_monosh_ground_screen_delta',1))
 end)
end
if scenario=='bullets' then
 cb('_fx_enemy_render_bullets',function()
  put('_monosh_enemy_bullet_count',0,4)
  local ages={}
  for i=0,2 do
   local age=(read('_monosh_runtime_frame_counter',2)+i*11)&63
   ages[#ages+1]=tostring(age)
   local data={1,96+i*32,150,8,0,0,age}
   for j,v in ipairs(data)do put('_monosh_enemy_bullets',i*7+j-1,v)end
  end
  local boss={1,128,90,8,0,0,128}
  for j,v in ipairs(boss)do put('_monosh_enemy_bullets',21+j-1,v)end
  nextBulletAges='['..table.concat(ages,',')..']'
  put('_monosh_player_invuln',0,255)
 end)
end
cb('math4_lift_result',function()
  local mt=emu.memType.snesMemory
  local z=emu.read(0x7e0380,mt);local world=emu.read(0x7e0381,mt)
  local scale=emu.read(0x7e0000+labels._monosh_boss_explosion_scale_low+z,mt)+(z<13 and 256 or 0)
  assert((emu.getState()['cpu.a']&65535)==((world*scale)//256)*2,'explosion lift differs from original arithmetic')
  mathChecks=mathChecks+1
end)
cb('_fx_frame',function()
  logic=logic+1
  if scenario=='effects' then
    put('_monosh_boss_state',0,1);put('_monosh_player_invuln',0,255)
    -- 敵描画の呼び出し自体がactive_countで省略されないよう、更新前にも枠を置く。
    put('_monosh_enemy_active_count_value',0,1)
    put('_monosh_enemies',0,1);put('_monosh_enemies',1,2);put('_monosh_enemies',3,0)
    put('_monosh_enemy_bullet_count',0,0)
  end
  if scenario=='bullets' then
    put('_monosh_enemy_bullet_count',0,4)
    for i=0,2 do
      local data={1,96+i*32,150,8,0,0,0}
      for j,v in ipairs(data)do put('_monosh_enemy_bullets',i*7+j-1,v)end
    end
    local boss={1,128,90,8,0,0,128}
    for j,v in ipairs(boss)do put('_monosh_enemy_bullets',21+j-1,v)end
    put('_monosh_player_invuln',0,255)
  end
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
  if scenario=='assets' or scenario=='full' then
    -- 全44素材、四つの反転、左右上下のclip。事前縮小にない幅のfallbackも照合する。
    local index=(starts-1)%880
    local asset=index%44;local flip=(index//44)%4;local clipping=index//176
    local widths={37,129,200,32,16};local heights={53,181,215,48,24}
    local centers={128,8,249,128,128};local bottoms={160,100,270,160,160}
    -- 胴・顔の事前縮小経路を通常位置と左上clipでも必ず通す。
    if asset==13 or asset==14 then
      widths[1]=asset==13 and 62 or 69;heights[1]=asset==13 and 41 or 101
      widths[2]=widths[1];heights[2]=heights[1];bottoms[2]=20
    end
    if scenario=='full' then
      asset=13;flip=0;clipping=0;widths[1]=255;heights[1]=184;centers[1]=128;bottoms[1]=212
    end
    local function cart(a,v) emu.write(a,v&255,emu.memType.gsuWorkRam) end
    local function cartword(a,v) cart(a,v);cart(a+1,v>>8) end
    cartword(0,1);cartword(32,centers[clipping+1]);cartword(34,bottoms[clipping+1])
    cart(36,widths[clipping+1]);cart(37,heights[clipping+1]);cart(38,asset);cart(39,flip*16)
    cartword(0x1002,192);cartword(0x1004,1)
    cartword(0x100a,192);cartword(0x100c,1)
  end
  trace:write(string.format('{"startLine":%d,"field":%d}\n',emu.getState()['ppu.scanline'],field))
  if starts%60==0 or starts==1 or scenario=='assets' or scenario=='full' or scenario=='players' or scenario=='bullets' or scenario=='effects' then
    dump(string.format('frame%05d_packet.bin',starts),emu.memType.gsuWorkRam,0,1536)
    dump(string.format('frame%05d_background.bin',starts),emu.memType.gsuWorkRam,0x1000,16)
    dump(string.format('frame%05d_prepared.bin',starts),emu.memType.gsuWorkRam,0x0600,128)
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
if PROFILING then
for _,nm in ipairs({'dispatch_nonzero','render_stop','generic','margin_render','scaled_render4','scaled_unpacked4','integer_render4'}) do
  emu.addMemoryCallback(function()
  if finished then return end
  if nm=='dispatch_nonzero' or nm=='render_stop' then endDraw();return end
  local ss=emu.getState();local meta=emu.read(0x0b,emu.memType.gsuWorkRam)
  currentDraw={clock=ss.masterClock,key=nm..'_'..(meta&63)}
 end,emu.callbackType.exec,labels[nm],labels[nm],emu.cpuType.gsu,emu.memType.gsuMemory)
end
end
emu.addMemoryCallback(function()
  if finished then return end
  trace:write(string.format('{"actualGsuMs":%.6f,"field":%d}\n',((emu.getState().masterClock-gsu_start)&0xffffffff)/21477.272,field))
end,emu.callbackType.exec,labels.render_stop,labels.render_stop,emu.cpuType.gsu,emu.memType.gsuMemory)
cb('dma_started',function()
  halves=halves+1
  local line=emu.getState()['ppu.scanline']
  assert(line>=203,'DMA started in visible region')
  dma_start_clock=emu.getState().masterClock
  trace:write(string.format('{"dmaStartLine":%d,"field":%d}\n',line,field))
end)
cb('half_dma_finished',function()
  local line=emu.getState()['ppu.scanline']
  assert(line<=22 or line>=203,'DMA exceeded forced blank')
  trace:write(string.format('{"dmaEndLine":%d,"dmaMs":%.6f,"halfBytes":%d,"descriptors":%d,"field":%d}\n',line,((emu.getState().masterClock-dma_start_clock)&0xffffffff)/21477.272,read('fx4_half_bytes',2),read('fx4_desc_count',2),field))
end)
cb('dma_finished',function()
  finishes=finishes+1
  local state=emu.getState()
  local visibleField=field+(state['ppu.scanline']>=203 and 1 or 0)
  local interval=visibleField-lastfield;intervals[interval]=(intervals[interval] or 0)+1;lastfield=visibleField
  assert(state['ppu.scanline']<=22 or state['ppu.scanline']>=203,'4bpp swap missed the blanking boundary')
  local boss=read('_monosh_boss_state',1)
  local paused=read('_monosh_runtime_paused',1)
  if scenario~='pause' then assert(paused==0,'unexpected pause without Start') end
  bossSeen=bossSeen or boss==1;dyingSeen=dyingSeen or boss==2;doneSeen=doneSeen or boss==3
  restartSeen=restartSeen or (doneSeen and boss==0)
  trace:write(string.format('{"present":%d,"field":%d,"interval":%d,"logic":%d,"page":%d,"boss":%d,"line":%d,"paused":%d,"player":%d,"x":%d,"bottom":%d,"shots":%d}\n',finishes,field,interval,read('_monosh_runtime_frame_counter',2),read('fx4_page',2),read('_monosh_boss_state',1),state['ppu.scanline'],paused,read('_monosh_player_state',1),read('_monosh_player_x',2),read('_monosh_player_bottom',2),read('_monosh_player_bullet_count',1)))
  trace:write(string.format('{"dmaBytes":%d,"field":%d}\n',read('fx4_dma_bytes',2),field))
  if finishes%60==0 or scenario=='assets' or scenario=='full' or scenario=='players' or scenario=='bullets' or scenario=='effects' then
    dump(string.format('frame%05d_fb.bin',finishes),emu.memType.gsuWorkRam,0x2000,24576)
    dump(string.format('frame%05d_vram.bin',finishes),emu.memType.snesVideoRam,0,65536)
    dump(string.format('frame%05d_bounds.bin',finishes),emu.memType.gsuWorkRam,0x580,64)
    dump(string.format('frame%05d_dma.bin',finishes),emu.memType.gsuWorkRam,0x1100,100)
    if labels.player4_present then
      dump(string.format('frame%05d_oam.bin',finishes),emu.memType.snesSpriteRam,0,544)
      dump(string.format('frame%05d_cgram.bin',finishes),emu.memType.snesCgRam,0,512)
      dump(string.format('frame%05d_obj.bin',finishes),emu.memType.snesMemory,0x7e0000+labels.fx_obj_present,136)
    end
    local f=assert(io.open(output..string.format('/frame%05d_meta.json',finishes),'w'))
    f:write(string.format('{"page":%d,"field":%d,"playerObjSource":%d,"playerInput":%s,"bulletAges":%s,"effectPhase":%s}',read('fx4_page',2),field,labels.player4_present and read('player4_present',2) or 0,presentPlayerInput or 'null',presentBulletAges or 'null',presentEffectPhase and tostring(presentEffectPhase) or 'null'));f:close()
  end
end)
emu.addEventCallback(function()
  local input={a=scenario~='boss_hold' and scenario~='boss' and scenario~='effects'}
  if scenario=='controls' then
    local phase=(field//240)%4
    input.up=phase==0;input.right=phase==1;input.down=phase==2;input.left=phase==3
  end
  if scenario=='pause' then input.start=(field>=151 and field<=154) or (field>=211 and field<=214) end
  if scenario=='play' and read('_monosh_boss_state',1)==1 then
    local z=read('_boss_part_z',1)
    local height=emu.read(0x7e0000+labels._monosh_boss_face_geometry+math.min(z,110)*2+1,emu.memType.snesMemory)
    local tx=read('_boss_part_x',1);local ty=read('_boss_part_bottom',1)-height//2+20
    local x=read('_monosh_player_x',2);local y=read('_monosh_player_bottom',2)
    input.right=x<tx-3;input.left=x>tx+3;input.up=y>ty+3;input.down=y<ty-3
  end
  emu.setInput(input,0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
  field=field+1
  if (scenario=='bullets' or scenario=='effects') and field%2==0 then screenshot(string.format('anim%05d',field)) end
  if field%240==0 then screenshot(string.format('screen%05d',field)) end
  if field>=maxframe then
    finished=true
    for k,v in pairs(profile) do trace:write(string.format('{"profile":"%s","n":%d,"sumMs":%.3f,"maxMs":%.3f}\n',k,v.n,v.sum/21477.272,v.max/21477.272)) end
    local sf=assert(io.open(output.."/state.txt","w")); for k,v in pairs(emu.getState()) do sf:write(tostring(k).."="..tostring(v).."\n") end;sf:close()
    trace:write(string.format('{"mathChecks":%d}\n',mathChecks))
    trace:close()
    local f=assert(io.open(output..'/summary.json','w'))
    local ii={};for k,v in pairs(intervals) do ii[#ii+1]=string.format('"%d":%d',k,v) end
    f:write(string.format('{"fields":%d,"renders":%d,"starts":%d,"halves":%d,"logicCalls":%d,"logic":%d,"gsuMaxMs":%.6f,"intervals":{%s},"bossSeen":%s,"dyingSeen":%s,"doneSeen":%s,"restartSeen":%s}',field,finishes,starts,halves,logic,read('_monosh_runtime_frame_counter',2),gsuMax,table.concat(ii,','),tostring(bossSeen),tostring(dyingSeen),tostring(doneSeen),tostring(restartSeen)));f:close();emu.stop(0)
  end
end,emu.eventType.startFrame)

local labels = LABELS
local output = OUTDIR
local maxframe = MAXFRAME
local scenario = SCENARIO
local held_direction = HELD_DIRECTION
local held_fire = HELD_FIRE
local gsu_uv = GSU_UV
local gsu_clip = GSU_CLIP
local cpu_clip_commands = CPU_CLIP_COMMANDS
local report = assert(io.open(output..'/trace.jsonl','w'))
local field = 0
local rendered = 0
local clock_start = 0
local gsu_start = 0
local dma_start = 0
local profile={}
local native_profile={}
local failed=false
local previous_field,previous_boss,previous_player=0,0,0
local last_logic,last_logic_field=-1,0
local stats={fields=0,rendered=0,checked=0,deaths=0,respawns=0,bossSeen=false,dyingSeen=false,doneSeen=false,loopSeen=false,
             enemyTypes={},enemyPaths={},em1States={},stumbles=0,reflected=0,maxCommands=0,minBytes=65535,maxBytes=0,
             interval1=0,interval2=0,interval3plus=0,cpuMaxMs=0,gsuMaxMs=0,dmaMaxMs=0}
local gsu_ms=0
local cpu_ms=0
-- Mesen LuaのmasterClockはuint32。約200秒ごとのwrapを時間差で吸収する。
local function elapsed(now,started) return ((now-started)&0xffffffff)/21477.272 end
local fixture_started=false
local function dump(name,memtype,address,count)
  local f=assert(io.open(output..'/'..name,'wb'));local bytes={}
  for i=0,count-1 do bytes[#bytes+1]=string.char(emu.read(address+i,memtype)) end
  f:write(table.concat(bytes));f:close()
end
local function screenshot(name)
  local f=assert(io.open(output..'/'..name..'.rgb','wb'));local rgb={}
  for _,v in ipairs(emu.getScreenBuffer()) do rgb[#rgb+1]=string.char((v>>16)&255,(v>>8)&255,v&255) end
  f:write(table.concat(rgb));f:close()
end
local function byte(name,offset)
  return emu.read(0x7E0000+assert(labels[name])+offset,emu.memType.snesMemory)
end
local function put(name,offset,value)
  emu.write(0x7E0000+assert(labels[name])+offset,value&255,emu.memType.snesMemory)
end
local function encoded(v)
  if type(v)=='table' then local out={};for k,x in pairs(v) do out[#out+1]='"'..tostring(k)..'":'..encoded(x) end;return '{'..table.concat(out,',')..'}' end
  if type(v)=='string' then return '"'..v..'"' end
  return tostring(v)
end
local function read(name, size)
  local addr=0x7E0000+assert(labels[name],name)
  local v=emu.read(addr,emu.memType.snesMemory)
  if size==2 then v=v+256*emu.read(addr+1,emu.memType.snesMemory) end
  return v
end
local function write(name,v)
  emu.write(0x7E0000+assert(labels[name]),v&255,emu.memType.snesMemory)
  emu.write(0x7E0000+assert(labels[name])+1,v>>8,emu.memType.snesMemory)
end
local function guard(fn)
  return function(...)
    if failed then return end
    local ok,err=pcall(fn,...)
    if not ok then
      failed=true
      local state=io.open(output..'/failure_state.json','w')
      state:write(encoded(emu.getState()));state:close()
      dump('failure_wram.bin',emu.memType.snesMemory,0x7e0000,65536)
      local input=io.open(output..'/failure_input.json','w')
      input:write(encoded(emu.getInput(0)));input:close()
      local q=io.open(output..'/debugram.bin','wb'); local t={}
      for k=0,32767 do t[#t+1]=string.char(emu.read(k,emu.memType.gsuWorkRam)) end
      q:write(table.concat(t)); q:close()
      local f=io.open(output..'/error.txt','w'); f:write(tostring(err)); f:close(); report:close();emu.stop(1)
    end
  end
end
DISPLAY_CODE
-- 実ゲームが出した開EM1の矩形を、全ZのWRAM表と照合する。
-- 人工描画リストのreplay/packed/stressでは任意寸法を許す。
if labels.fx_em1_open_sizes and scenario~='replay' and scenario~='packed' and scenario~='stress' and scenario~='objects' then
  emu.addMemoryCallback(guard(function()
    for i=0,read('_fx_draw_count')-1 do
      local at=i*10
      local asset=byte('_fx_draw',at+6)
      if asset>=32 and asset<=36 then
        local z=math.min(110,byte('_fx_draw',at+8))
        local addr=0x7f0000+labels.fx_em1_open_sizes+z*10+(asset-32)*2
        local width=emu.read(addr,emu.memType.snesMemory)
        local height=emu.read(addr+1,emu.memType.snesMemory)
        assert(byte('_fx_draw',at+4)==width and byte('_fx_draw',at+5)==height,'open EM1 depth lookup mismatch')
        stats.openEm1SizeChecks=(stats.openEm1SizeChecks or 0)+1
      end
    end
  end),emu.callbackType.exec,0x7f0000+labels._fx_build_packet,0x7f0000+labels._fx_build_packet,emu.cpuType.snes,emu.memType.snesMemory)
end
emu.addMemoryCallback(guard(function()
  report:write(string.format('{"bootSky":%d,"skyConstant":%d}\n',emu.read(0,emu.memType.snesCgRam)+256*emu.read(1,emu.memType.snesCgRam),read('_fx_sky_color',2)))
end),emu.callbackType.exec,0x7f0000+labels.game_started,0x7f0000+labels.game_started,emu.cpuType.snes,emu.memType.snesMemory)
local obj_clock=0
emu.addMemoryCallback(guard(function() obj_clock=emu.getState().masterClock end),
  emu.callbackType.exec,0x7F0000+labels.fx_upload_obj,0x7F0000+labels.fx_upload_obj,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
  report:write(string.format('{"objMs":%.6f,"objBytes":%d,"field":%d}\n',elapsed(emu.getState().masterClock,obj_clock),read('fx_obj_dma_bytes',2),field))
end),emu.callbackType.exec,0x7F0000+labels.fx_obj_upload_done,0x7F0000+labels.fx_obj_upload_done,emu.cpuType.snes,emu.memType.snesMemory)
if scenario=='objects' then
  emu.addEventCallback(guard(function()
    -- StartFrameでは直前の完成RGB、OAMは次に走査するfieldのもの。
    if field>=41 and field<=301 and (field-1)%4==0 then screenshot(string.format('objview%05d',field-1)) end
    if field>=40 and field<=300 and field%4==0 then
      dump(string.format('objview%05d_oam.bin',field),emu.memType.snesSpriteRam,0,544)
      dump(string.format('objview%05d_cgram.bin',field),emu.memType.snesCgRam,0,512)
    end
  end),emu.eventType.startFrame)
  emu.addMemoryCallback(guard(function()
    local n=read('_monosh_runtime_frame_counter',2)
    local poses={9,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30}
    local r={{128,165,68,158,4,0,0,0}}
    for i=1,6 do
      local size=1+(n+i)%16
      r[#r+1]={100+i*8,100+i*4,size,size,10,i>3 and 64 or 0,0,2}
    end
    local flags=((n//17)%4)*16
    if (n//68)%2==1 then flags=flags|128 end
    r[#r+1]={({0,256,128,128})[1+(n//4)%4],({48,180,28,230})[1+(n//7)%4],32,48,poses[1+n%17],flags,0,2}
    if n%17==0 then
      -- 最悪の重なり：初期自弾3＋反射弾3＋自機。同一走査線34tile以内。
      for i=2,7 do
        local size=(n%34==0 and i<=4) and 11 or 12
        r[i]={128,110,size,size,10,i>4 and 64 or 0,0,2}
      end
      r[8][1]=128;r[8][2]=125
    end
    for i,v in ipairs(r) do
      local b={v[1]&255,(v[1]>>8)&255,v[2]&255,(v[2]>>8)&255,v[3],v[4],v[5],v[6],v[7],v[8]}
      for j,c in ipairs(b) do put('_fx_draw',(i-1)*10+j-1,c) end
    end
    put('_fx_draw_count',0,#r)
  end),emu.callbackType.exec,0x7F0000+labels._fx_build_packet,0x7F0000+labels._fx_build_packet,emu.cpuType.snes,emu.memType.snesMemory)
end
for _,name in ipairs({'packed_one','packed_half','packed_quarter','packed_double',
                     'packed_mirror_one','packed_mirror_half','packed_mirror_quarter'}) do
  emu.addMemoryCallback(guard(function() stats[name]=(stats[name] or 0)+1 end),
    emu.callbackType.exec,labels[name],labels[name],emu.cpuType.gsu,emu.memType.gsuMemory)
end
if scenario=='packed' then
  emu.addMemoryCallback(guard(function()
    local sprites={{40,100,32,48,0},{90,100,16,24,0},{125,100,8,12,0},
      {165,100,32,48,32},{0,100,32,48,0},{215,30,32,48,0},
      {4,180,16,24,0},{256,180,8,12,0},{120,170,32,48,16},
      {120,190,68,158,0,4},{35,200,68,158,32,4},
      {160,180,16,24,16},{200,180,8,12,48}}
    local tail=read('_monosh_runtime_frame_counter',2)%8
    sprites[#sprites+1]={256-(56+tail)+34,190,68,158,tail%2==0 and 0 or 32,4}
    stats.doubleTailRequests=stats.doubleTailRequests or {}
    stats.doubleTailRequests[tail]=true
    for i,d in ipairs(sprites) do
      local values={d[1]&255,(d[1]>>8)&255,d[2],0,d[3],d[4],d[6] or 9,d[5],i,0}
      for j,v in ipairs(values) do put('_fx_draw',(i-1)*10+j-1,v) end
    end
    put('_fx_draw_count',0,#sprites)
  end),emu.callbackType.exec,0x7F0000+labels._fx_build_packet,0x7F0000+labels._fx_build_packet,emu.cpuType.snes,emu.memType.snesMemory)
end
if scenario=='equivalence' or scenario=='equivalence_boss' then
  -- Native移植前後で、物理frame数によらず同じlogic更新の状態を比較する。
  emu.addMemoryCallback(guard(function()
    put('_fx_fire_actions',0,2);put('_monosh_runtime_fire_actions',0,2)
    local inputs={1,2,8,4,9,6,0,0}
    local input=inputs[(read('_monosh_runtime_frame_counter',2)//96)%8+1]
    put('_fx_input',0,input)
    -- entry時点で引数は既にcc65 stackへ積まれている。実引数も揃える。
    emu.write(0x7e0000+read('c_sp',2),input,emu.memType.snesMemory)
  end),emu.callbackType.exec,0x7F0000+labels._monosh_player_update,0x7F0000+labels._monosh_player_update,emu.cpuType.snes,emu.memType.snesMemory)
  local states=assert(io.open(output..'/states.bin','wb'))
  local blocks={{'_monosh_runtime_frame_counter',2},{'_monosh_player_x',2},{'_monosh_player_bottom',2},
    {'_monosh_player_state',1},{'_monosh_player_invuln',1},{'_monosh_player_stumble',1},{'_monosh_player_pose',1},
    {'_player_fy',2},{'_death_vy',1},{'_death_timer',1},{'_movement_fraction',1},
    {'_death_accel_fraction',1},{'_intro_timer',1},{'_player_flip',1},{'_player_run_phase',1},
    {'_monosh_stage_title_timer',1},{'_monosh_title_visible',1},
    {'_monosh_stage_frame_counter',2},{'_monosh_stage_spawn_index',1},{'_monosh_stage_half_frame',1},
    {'_monosh_stage_object_count',1},{'_monosh_stage_objects',96},{'_monosh_enemy_spawn_index',1},
    {'_monosh_enemy_spawn_wait',2},{'_monosh_enemy_active_count_value',1},{'_monosh_enemy_em1_count',1},
    {'_monosh_enemy_stage_complete_flag',1},{'_monosh_enemies',80},{'_monosh_enemy_em1_phase',16},
    {'_monosh_enemy_em1_shrink',8},{'_monosh_enemy_bullet_count',1},{'_monosh_enemy_bullets',42},
    {'_boss_dda_phase',6},{'_boss_dda_x',6},{'_boss_dda_y',6},
    {'_monosh_player_bullet_count',1},{'_monosh_player_bullets',15},{'_monosh_reflected_bullet_count',1},
    {'_monosh_reflected_bullets',15},{'_monosh_boss_state',1},{'_monosh_boss_hp',1},
    {'_boss_part_x',9},{'_boss_part_bottom',9},{'_boss_part_z',9},{'_boss_part_active',9},{'_boss_part_timer',9},
    {'_monosh_ground_offset',1},{'_monosh_ground_screen_delta',1},{'_fx_ground_world_phase',1},
    {'_fx_far_u_acc',2},{'_fx_far_d_acc',2},{'_monosh_combat_fire_cooldown',1},{'_monosh_bullet_reflect_rng',1},
    {'_boss_age',1},{'_history_head',1},{'_boss_history_x',128},{'_boss_history_y',128},{'_boss_history_z',128},
    {'_fx_draw_count',1},{'_fx_draw',640}}
  local f=assert(io.open(output..'/state_blocks.json','w'));f:write(encoded(blocks));f:close()
  emu.addMemoryCallback(guard(function()
    local raw={}
    for _,b in ipairs(blocks) do for i=0,b[2]-1 do raw[#raw+1]=string.char(byte(b[1],i)) end end
    states:write(table.concat(raw));states:flush()
  end),emu.callbackType.exec,0x7F0000+labels._fx_build_packet,0x7F0000+labels._fx_build_packet,emu.cpuType.snes,emu.memType.snesMemory)
end
if scenario=='profile' then
for _,pair in ipairs({{'_fx_build_packet','packet_done'},{'_fx_ground_native','ground_done'},{'fx_build_color','fx_color_build_done'}}) do
  emu.addMemoryCallback(guard(function() native_profile[pair[1]]=emu.getState().masterClock end),
    emu.callbackType.exec,0x7F0000+labels[pair[1]],0x7F0000+labels[pair[1]],emu.cpuType.snes,emu.memType.snesMemory)
  emu.addMemoryCallback(guard(function()
    local start=native_profile[pair[1]]
    if start then report:write(string.format('{"function":"%s","ms":%.6f,"field":%d}\n',pair[1],elapsed(emu.getState().masterClock,start),field)) end
  end),emu.callbackType.exec,0x7F0000+labels[pair[2]],0x7F0000+labels[pair[2]],emu.cpuType.snes,emu.memType.snesMemory)
end
for _,name in ipairs({'_fx_frame','_fx_build_packet','_fx_build_ground','_fx_ground_native','_monosh_enemy_frame','_monosh_stage_frame'}) do
  emu.addMemoryCallback(guard(function()
    local clock=emu.getState().masterClock
    if profile.last then report:write(string.format('{"segment":"%s","ms":%.6f,"field":%d}\n',profile.last,elapsed(clock,profile.clock),field)) end
    profile.last=name;profile.clock=clock
  end),emu.callbackType.exec,0x7F0000+labels[name],0x7F0000+labels[name],emu.cpuType.snes,emu.memType.snesMemory)
end
end
emu.addMemoryCallback(guard(function()
  -- 入力方向の試験が敵接触による死亡アニメーションに切り替わらないよう固定。
  if scenario=='controls' then put('_monosh_player_invuln',0,255) end
  if scenario=='stumble' and field>=400 and not fixture_started then
    fixture_started=true
    write('_monosh_player_bottom',201)
    put('_monosh_player_invuln',0,0)
    put('_monosh_stage_spawn_index',0,read('_monosh_stage1_spawn_count',2)-1)
    for i,v in ipairs({0,0,1,3,0,0}) do put('_monosh_stage_objects',i-1,v) end
    put('_monosh_stage_object_count',0,1)
  end
  local fixture_frame=scenario=='equivalence_boss' and read('_monosh_runtime_frame_counter',2) or field
  if (scenario~='boss' and scenario~='equivalence_boss') or fixture_frame<90 then return end
  if scenario=='equivalence_boss' then put('_monosh_player_invuln',0,255) end
  if not fixture_started then
    fixture_started=true
    put('_monosh_player_invuln',0,255)
    put('_monosh_enemy_stage_complete_flag',0,1)
    put('_monosh_enemy_active_count_value',0,0);put('_monosh_enemy_bullet_count',0,0)
    put('_monosh_stage_object_count',0,0)
    put('_monosh_stage_spawn_index',0,read('_monosh_stage1_spawn_count',2)-1)
    write('_monosh_stage_frame_counter',3900)
  end
  -- 通常のボス射撃を先に観測。HPは変更せず、後半で自弾だけを命中位置へ置く。
  if read('_monosh_boss_state')==1 and fixture_frame>600 then
    local z=byte('_boss_part_z',0)
    local height=byte('_monosh_boss_face_geometry',math.min(z,110)*2+1)
    if z>=8 and z<=90 then
      put('_monosh_player_bullets',0,1)
      put('_monosh_player_bullets',1,byte('_boss_part_x',0))
      put('_monosh_player_bullets',2,byte('_boss_part_bottom',0)-height//2)
      put('_monosh_player_bullets',3,math.max(0,z//2-2));put('_monosh_player_bullets',4,3)
      put('_monosh_player_bullet_count',0,1)
      stats.injectedShots=(stats.injectedShots or 0)+1
    end
  end
end),emu.callbackType.exec,0x7F0000+labels._fx_frame,0x7F0000+labels._fx_frame,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
  if scenario~='stress' then return end
  for i=0,19 do
    local x=(i%10)*32-16;local bottom=i<10 and 212 or 112
    put('_fx_draw',i*10,x);put('_fx_draw',i*10+1,(x>>8)&255)
    put('_fx_draw',i*10+2,bottom);put('_fx_draw',i*10+3,0)
    put('_fx_draw',i*10+4,68);put('_fx_draw',i*10+5,160)
    put('_fx_draw',i*10+6,4);put('_fx_draw',i*10+7,i%2==0 and 16 or 0)
    put('_fx_draw',i*10+8,i);put('_fx_draw',i*10+9,0)
  end
  put('_fx_draw_count',0,20)
end),emu.callbackType.exec,0x7F0000+labels._fx_build_packet,0x7F0000+labels._fx_build_packet,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
  gsu_ms=elapsed(emu.getState().masterClock,clock_start)
  stats.gsuMaxMs=math.max(stats.gsuMaxMs,gsu_ms)
end),emu.callbackType.exec,labels.render_stop,labels.render_stop,emu.cpuType.gsu,emu.memType.gsuMemory)
emu.addMemoryCallback(guard(function()
  local now=emu.getState().masterClock
  cpu_ms=elapsed(now,clock_start)
  if scenario=='profile' and profile.last then
    report:write(string.format('{"segment":"%s","ms":%.6f,"field":%d}\n',profile.last,elapsed(now,profile.clock),field))
    profile.last=nil
  end
end),emu.callbackType.exec,0x7F0000+labels.cpu_frame_return,0x7F0000+labels.cpu_frame_return,emu.cpuType.snes,emu.memType.snesMemory)
local function trace()
  local s=emu.getState()
  if field==60 then
    local f=io.open(output..'/state.txt','w')
    for k,v in pairs(s) do if k:find('cpu') or k:find('coprocessor') then f:write(k..'='..tostring(v)..'\n') end end
    f:write('packet='..emu.read(0,emu.memType.gsuWorkRam)..' scratch='..emu.read(4,emu.memType.gsuWorkRam)..' ptr='..emu.read(6,emu.memType.gsuWorkRam)..'\n')
    for k,v in pairs(emu.getInput(0)) do f:write('input '..k..'='..tostring(v)..'\n') end
    f:write('joy='..emu.read(0x4218,emu.memType.snesMemory)..' hi='..emu.read(0x4219,emu.memType.snesMemory)..'\n')
    f:close()
  end
  report:write(string.format('{"field":%d,"logic":%d,"x":%d,"y":%d,"player":%d,"stage":%d,"enemies":%d,"shots":%d,"enemyShots":%d,"boss":%d,"hp":%d,"commands":%d,"cpuPC":%d,"ppuLine":%d,"gsuGO":%d}\n',
    field,read('_monosh_runtime_frame_counter',2),read('_monosh_player_x',2),read('_monosh_player_bottom',2),read('_monosh_player_state'),
    read('_monosh_stage_frame_counter',2),read('_monosh_enemy_active_count_value'),read('_monosh_player_bullet_count'),read('_monosh_enemy_bullet_count'),
    read('_monosh_boss_state'),read('_monosh_boss_hp'),read('_fx_packet_count',2),s['cpu.pc'],s['ppu.scanline'],emu.read(0x3030,emu.memType.snesMemory)))
  report:flush()
end
emu.addMemoryCallback(guard(function(a,v)
  if v~=1 then return end
  local s=emu.getState()
  gsu_start=s['cart.coprocessor.cycleCount'];clock_start=s.masterClock
  profile.last=nil
  if rendered==0 then
    for i=0,15 do emu.write(0x1ff0+i,0xa5,emu.memType.gsuWorkRam);emu.write(0x5000+i,0x5a,emu.memType.gsuWorkRam) end
  end
  if rendered==0 or (rendered+1)%300==0 or (scenario=='packed' and rendered<8) or (scenario=='objects' and (rendered+1)%((labels.dma_probe_delay and rendered>300) and 32 or 4)==0) then
    dump(string.format('draw%05d.bin',rendered+1),emu.memType.snesMemory,0x7E0000+labels._fx_draw,640)
    dump(string.format('obj%05d.bin',rendered+1),emu.memType.snesMemory,0x7E0000+labels.fx_obj_present,136)
    local f=assert(io.open(output..string.format('/meta%05d.json',rendered+1),'w'))
    f:write(encoded({count=read('_fx_draw_count'),logic=read('_monosh_runtime_frame_counter',2),gsuUv=gsu_uv,gsuClip=gsu_clip,cpuClipCommands=cpu_clip_commands}));f:close()
  end
end),emu.callbackType.write,0x7E1DF0,0x7E1DF0)
emu.addMemoryCallback(guard(function(a,v)
  if v~=2 then return end
  local s=emu.getState()
  local joined=elapsed(s.masterClock,clock_start)
  stats.cpuMaxMs=math.max(stats.cpuMaxMs,joined)
  report:write(string.format('{"joinedMs":%.5f,"cpuMs":%.5f,"gsuMs":%.5f,"field":%d}\n',joined,cpu_ms,gsu_ms,field))
end),emu.callbackType.write,0x7E1DF0,0x7E1DF0)
emu.addMemoryCallback(guard(function(a,v)
  if v~=3 then return end
  local s=emu.getState()
  dma_start=s.masterClock
  local line=s['ppu.scanline'];local count=read('fx_dma_count',2)
  local deadline=emu.read(0x7e1d10,emu.memType.snesMemory)
  -- 画像差し替え後はHDMAポインタ更新と可変長OAMに最大4行を要する。
  -- 完了側でも21行以内を検査し、22行OBJ準備の余裕を独立に守る。
  assert(line>=203 and line<=deadline+4,'DMA start outside admitted blank window')
  local weight=read('fx_dma_bytes',2)+count*(labels.select_dma_deadline and 64 or 128)+(labels.select_dma_deadline and 768 or 0)
  if labels.fx_upload_color then weight=weight+64+(read('fx_color_staged',2)==0 and (read('fx_color_dma_bytes',2)+read('fx_color_dma_count',2)*64) or 0) end
  if deadline>203 then
    local limit=deadline==220 and DMA_ADMISSION_BYTES or deadline==226 and 8960 or deadline==233 and 7680
    if labels.dma_deadline_fine then limit=math.min(DMA_ADMISSION_BYTES,(279-deadline)*170-1) end
    assert(limit and weight<=math.min(limit,DMA_ADMISSION_BYTES),'large DMA admitted late')
  end
  stats.lateDmaStarts=(stats.lateDmaStarts or 0)+(line>206 and 1 or 0)
  stats.maxDmaStartLine=math.max(stats.maxDmaStartLine or 0,line)
  stats.maxDmaSpanCount=math.max(stats.maxDmaSpanCount or 0,count)
  report:write(string.format('{"dmaStartLine":%d,"spans":%d,"deadline":%d,"field":%d}\n',line,count,deadline,field))
  if rendered==0 then
    local f=io.open(output..'/descriptors.txt','w')
    for i=0,31 do
      local addr=0x7E0000+labels.fx_dma_desc+i*4
      local a=emu.read(addr,emu.memType.snesMemory)+256*emu.read(addr+1,emu.memType.snesMemory)
      local n=emu.read(addr+2,emu.memType.snesMemory)+256*emu.read(addr+3,emu.memType.snesMemory)
      f:write(i..' '..a..' '..n..'\n')
    end
    f:close()
  end
end),emu.callbackType.write,0x7E1DF0,0x7E1DF0)
emu.addMemoryCallback(guard(function(a,v)
  if v~=4 then return end
  rendered=rendered+1
  local s=emu.getState()
  assert(s['ppu.scanline']<23 or s['ppu.scanline']>=203,'DMA overlaps visible area')
  assert(s['ppu.scanline']<=21 or s['ppu.scanline']>=203,'DMA missed OBJ preparation margin')
  local duration=elapsed(s.masterClock,dma_start)
  local bytes=read('fx_dma_bytes',2)
  stats.objMaxCount=math.max(stats.objMaxCount or 0,read('fx_obj_present_count',2))
  assert(read('fx_obj_overflow',2)==0,'OBJ packet capacity exceeded')
  for i=0,127 do assert(emu.read(i,emu.memType.snesSpriteRam)==byte('fx_obj_present',i),'OAM low snapshot differs') end
  for i=0,7 do assert(emu.read(512+i,emu.memType.snesSpriteRam)==byte('fx_obj_present',128+i),'OAM high snapshot differs') end
  stats.dmaMaxMs=math.max(stats.dmaMaxMs,duration)
  stats.minBytes=math.min(stats.minBytes,bytes);stats.maxBytes=math.max(stats.maxBytes,bytes)
  local interval=field-previous_field;previous_field=field
  if rendered>1 then if interval==1 then stats.interval1=stats.interval1+1 elseif interval==2 then stats.interval2=stats.interval2+1 else stats.interval3plus=stats.interval3plus+1 end end
  local boss=read('_monosh_boss_state');local player=read('_monosh_player_state')
  stats.enemyShotsMax=math.max(stats.enemyShotsMax or 0,read('_monosh_enemy_bullet_count'))
  if boss==1 then stats.bossSeen=true elseif boss==2 then stats.dyingSeen=true elseif boss==3 then stats.doneSeen=true end
  if previous_boss==3 and boss==0 then stats.loopSeen=true end
  if boss~=previous_boss then screenshot('boss_state'..boss) end
  if previous_player==0 and player~=0 then stats.deaths=stats.deaths+1 end
  if previous_player~=0 and player==0 then stats.respawns=stats.respawns+1 end
  if read('_monosh_player_stumble')>0 then stats.stumbles=stats.stumbles+1 end
  stats.stumbleMax=math.max(stats.stumbleMax or 0,read('_monosh_player_stumble'))
  stats.reflected=math.max(stats.reflected,read('_monosh_reflected_bullet_count'))
  previous_boss=boss;previous_player=player
  for i=0,read('_monosh_enemy_active_count_value')-1 do
    local addr=0x7E0000+labels._monosh_enemies+i*10
    local t=emu.read(addr+1,emu.memType.snesMemory);stats.enemyTypes[t]=true
    if t==5 then stats.enemyPaths[emu.read(addr+2,emu.memType.snesMemory)]=true end
    if t==6 then stats.em1States[emu.read(0x7E0000+labels._monosh_enemy_em1_phase+i*2+1,emu.memType.snesMemory)]=true end
  end
  stats.maxCommands=math.max(stats.maxCommands,read('_fx_packet_count',2))
  report:write(string.format('{"dmaMs":%.5f,"bytes":%d,"line":%d,"field":%d,"rendered":%d}\n',duration,bytes,s['ppu.scanline'],field,rendered))
  if maxframe<=720 or rendered<=10 or rendered%30==0 then
  local same=0
  for i=0,12287 do if emu.read(0x2000+i,emu.memType.gsuWorkRam)==emu.read(i,emu.memType.snesVideoRam) then same=same+1 end end
  if same~=12288 then
    local raw={};local f=io.open(output..'/vram.bin','wb')
    for i=0,12287 do raw[#raw+1]=string.char(emu.read(i,emu.memType.snesVideoRam)) end
    f:write(table.concat(raw));f:close()
    raw={};f=io.open(output..'/failed_fb.bin','wb')
    for i=0,12287 do raw[#raw+1]=string.char(emu.read(0x2000+i,emu.memType.gsuWorkRam)) end
    f:write(table.concat(raw));f:close()
    f=io.open(output..'/state_dma.txt','w')
    for k,v in pairs(s) do if k:find('dma') or k:find('ppu.vram') then f:write(k..'='..tostring(v)..'\n') end end
    f:close()
    local f=io.open(output..'/dma_debug.txt','w')
    for i=0,12287 do if emu.read(0x2000+i,emu.memType.gsuWorkRam)~=emu.read(i,emu.memType.snesVideoRam) then f:write(i..'='..emu.read(0x2000+i,emu.memType.gsuWorkRam)..' vs '..emu.read(i,emu.memType.snesVideoRam)..'\n') end end
    f:close()
  end
  assert(same==12288,'partial DMA: '..same)
  stats.checked=stats.checked+1
  for i=0,15 do assert(emu.read(0x1ff0+i,emu.memType.gsuWorkRam)==0xa5 and emu.read(0x5000+i,emu.memType.gsuWorkRam)==0x5a,'GSU clip writes outside framebuffer') end
  local current=emu.read(0,emu.memType.snesCgRam)+256*emu.read(1,emu.memType.snesCgRam)
  local valid=false
  for i=0,(labels.fx_sky_colors_end-labels.fx_sky_colors)//4-1 do
    if current==byte('fx_sky_colors',i*4+2)+256*byte('fx_sky_colors',i*4+3) then valid=true end
  end
  assert(valid,'sky gradient palette corrupted')
  end
  if rendered==1 then
    local f=io.open(output..'/framebuffer.bin','wb'); local b={}
    for i=0,12287 do b[#b+1]=string.char(emu.read(0x2000+i,emu.memType.gsuWorkRam)) end
    f:write(table.concat(b));f:close()
    f=io.open(output..'/packet.bin','wb');b={}
    for i=0,1311 do b[#b+1]=string.char(emu.read(i,emu.memType.gsuWorkRam)) end
    f:write(table.concat(b));f:close()
  end
  if rendered==1 or rendered%300==0 or (scenario=='packed' and rendered<=8) or (scenario=='objects' and rendered%((labels.dma_probe_delay and rendered>300) and 32 or 4)==0) then
    dump(string.format('frame%05d.bin',rendered),emu.memType.gsuWorkRam,0x2000,12288)
    dump(string.format('packet%05d.bin',rendered),emu.memType.gsuWorkRam,0,1312)
    dump(string.format('oam%05d.bin',rendered),emu.memType.snesSpriteRam,0,544)
  end
end),emu.callbackType.write,0x7E1DF0,0x7E1DF0)
emu.addEventCallback(guard(function()
  if scenario=='held' then
    local input={}
    for direction in held_direction:gmatch('[^-]+') do if direction~='none' then input[direction]=true end end
    if held_fire~='none' then input[held_fire]=true end
    emu.setInput(input,0)
  elseif scenario=='play' then
    emu.setInput({a=true,up=field>150 and field<180,right=field>180 and field<210,left=field>240 and field<275},0)
  elseif scenario=='long' or scenario=='profile' then
    if read('_monosh_boss_state')==1 then
      local z=byte('_boss_part_z',0)
      local tx=byte('_boss_part_x',0)
      local ty=byte('_boss_part_bottom',0)-byte('_monosh_boss_face_geometry',math.min(z,110)*2+1)//2+20
      local x=read('_monosh_player_x',2);local y=read('_monosh_player_bottom',2)
      emu.setInput({a=true,right=x<tx-3,left=x>tx+3,up=y>ty+3,down=y<ty-3},0)
    else emu.setInput({a=true},0) end
  elseif scenario=='boss' then emu.setInput({},0)
  elseif scenario=='pause' then
    emu.setInput({a=true,start=(field>=151 and field<=154) or (field>=211 and field<=214)},0)
  elseif scenario=='controls' then
    emu.setInput({right=field>=301 and field<=330,left=field>=361 and field<=390,
                  down=field>=401 and field<=430,up=field>=461 and field<=490,y=field>=601 and field<=606},0)
  end
end),emu.eventType.inputPolled)
emu.addEventCallback(guard(function()
  assert(emu.read(0x213e,emu.memType.snesMemory)&0xc0==0,'OBJ scanline range/time overflow')
end),emu.eventType.endFrame)
emu.addEventCallback(guard(function()
  field=field+1
  local status=emu.read(0x213e,emu.memType.snesMemory)
  assert(status&0xc0==0,'OBJ range/time overflow')
  if rendered>0 then
    if scenario=='held' and held_direction=='none' and field>=90 and field<=150 then
      screenshot(string.format('shot%05d',field))
    end
    if read('_monosh_boss_state')==1 and read('_boss_age')>=100 and not stats.bossImage then screenshot('scene_boss');stats.bossImage=true end
    if read('_monosh_enemy_active_count_value')>=3 and not stats.enemyImage then screenshot('scene_enemies');stats.enemyImage=true end
    if read('_monosh_player_state')~=0 and not stats.deathImage then screenshot('scene_death');stats.deathImage=true end
  end
  if scenario=='controls' and rendered>0 then
    if field==335 then assert(read('_monosh_player_x',2)>128,'right input failed') end
    if field==435 then stats.controlUpY=read('_monosh_player_bottom',2);assert(stats.controlUpY<120,'reverse down input failed') end
    if field==495 then assert(read('_monosh_player_bottom',2)>stats.controlUpY,'reverse up input failed') end
    stats.singleShotMax=math.max(stats.singleShotMax or 0,read('_monosh_player_bullet_count'))
  end
  if scenario=='pause' then
    if field==165 then stats.pauseLogic=read('_monosh_runtime_frame_counter',2) end
    if field==195 then assert(read('_monosh_runtime_frame_counter',2)==stats.pauseLogic,'pause keeps updating logic') end
    if field==240 then assert(read('_monosh_runtime_frame_counter',2)>stats.pauseLogic,'pause did not resume') end
  end
  if field%30==0 then trace() end
  if scenario=='held' then
    if rendered>0 then
      local logic=read('_monosh_runtime_frame_counter',2)
      if logic~=last_logic then last_logic=logic;last_logic_field=field end
      stats.maxLogicGap=math.max(stats.maxLogicGap or 0,field-last_logic_field)
      assert(read('_monosh_runtime_paused')==0,'unexpected pause without Start: cached JOY1='..read('_fx_buttons',2)..' field='..field)
      assert(field-last_logic_field<=90,'logic frozen while frames continue')
      if field>=60 then
        local bits={right=0x100,left=0x200,down=0x400,up=0x800,a=0x80,y=0x4000}
        local expected=bits[held_fire] or 0
        for direction in held_direction:gmatch('[^-]+') do expected=expected|(bits[direction] or 0) end
        assert(read('_fx_buttons',2)==expected,'held buttons were sampled mid-shift: '..read('_fx_buttons',2)..' expected '..expected)
        stats.heldSamplesChecked=(stats.heldSamplesChecked or 0)+1
      end
    end
    local gap=field-previous_field
    stats.maxPresentationGap=math.max(stats.maxPresentationGap or 0,rendered>0 and gap or 0)
    if gap>90 and field>120 then
      local f=assert(io.open(output..'/freeze_state.json','w'))
      f:write(encoded(emu.getState()));f:close()
      dump('freeze_wram.bin',emu.memType.snesMemory,0x7e0000,65536)
      dump('freeze_gsu.bin',emu.memType.gsuWorkRam,0,32768)
      dump('freeze_registers.bin',emu.memType.snesMemory,0x3000,128)
      screenshot('freeze')
      trace()
      assert(false,'presentation frozen: '..gap..' fields without a new image; rendered='..rendered..' field='..field)
    end
  end
  if field==120 or field==240 or field==maxframe then
    local f=assert(io.open(output..'/field'..field..'.rgb','wb'));local rgb={}
    for _,v in ipairs(emu.getScreenBuffer()) do rgb[#rgb+1]=string.char((v>>16)&255,(v>>8)&255,v&255) end
    f:write(table.concat(rgb));f:close()
  end
  if field>=maxframe then
    stats.fields=field;stats.rendered=rendered;stats.logic=read('_monosh_runtime_frame_counter',2);stats.stage=read('_monosh_stage_frame_counter',2)
    local f=assert(io.open(output..'/summary.json','w'));f:write(encoded(stats));f:close()
    assert(rendered>1,'no presented frames')
    if scenario=='packed' then for _,name in ipairs({'packed_one','packed_half','packed_quarter','packed_double',
      'packed_mirror_one','packed_mirror_half','packed_mirror_quarter'}) do assert((stats[name] or 0)>0,'unused packed path: '..name) end end
    if scenario=='packed' then for tail=0,7 do assert(stats.doubleTailRequests[tail],'unused double tail: '..tail) end end
    if scenario=='boss' then assert(stats.bossSeen and stats.dyingSeen and stats.doneSeen and stats.loopSeen,'boss progression incomplete') end
    if scenario=='long' then assert(stats.bossSeen and stats.loopSeen and stats.deaths>0 and stats.respawns>0,'natural stage progression incomplete') end
    if scenario=='controls' then assert(stats.singleShotMax==1,'single shot was not exactly one slot') end
    if scenario=='stumble' then assert(stats.stumbles==39 and stats.stumbleMax==39 and read('_monosh_player_stumble')==0,'40-update bush stumble/recovery failed') end
    report:close();emu.stop(0);return
  end
  if scenario=='play' then
    emu.setInput({a=true,up=field>150 and field<180,right=field>180 and field<210,left=field>240 and field<275},0)
  end
end),emu.eventType.endFrame)

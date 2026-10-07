-- 最終PPU合成の検査。三つのcamera高さで同じFX画像と四つの地上物を描く。
if scenario=='display' or scenario=='scenery' then
  emu.addMemoryCallback(guard(function()
    local offset=field<240 and 0 or (field<480 and 32 or 64)
    put('_monosh_ground_offset',0,offset)
    put('_fx_ground_world_phase',0,32)
    put('_fx_ground_phase',0,6)
    local farX=scenario=='scenery' and (field//4)%256 or 17
    write('_fx_far_u_acc',farX*128)
    write('_fx_far_d_acc',farX*256)
    local records={}
    for i,z in ipairs({0,24,60,110}) do
      local geometry=labels._monosh_stage_geometry+4*2
      local gp=emu.read(0x7e0000+geometry,emu.memType.snesMemory)+256*emu.read(0x7e0000+geometry+1,emu.memType.snesMemory)
      local w=emu.read(0x7e0000+gp+z*4,emu.memType.snesMemory)
      local h=emu.read(0x7e0000+gp+z*4+1,emu.memType.snesMemory)
      local source=emu.read(0x7e0000+gp+z*4+2,emu.memType.snesMemory)
      local d=byte('_fx_ground_depth_rows',offset*81+219-source)
      local sink=z>=9 and 3 or (z>=6 and 2 or (z>=2 and 1 or 0))
      records[#records+1]={({35,107,178,231})[i],207-d+sink,w,h,4,0,z,0}
    end
    records[#records+1]={66,90,32,48,9,0,0,2}
    records[#records+1]={184,75,88,38,42,0,0,2}
    if scenario=='scenery' then records={} end
    for i,r in ipairs(records) do
      local data={r[1]&255,(r[1]>>8)&255,r[2]&255,(r[2]>>8)&255,r[3],r[4],r[5],r[6],r[7],r[8]}
      for j,v in ipairs(data) do put('_fx_draw',(i-1)*10+j-1,v) end
    end
    put('_fx_draw_count',0,#records)
  end),emu.callbackType.exec,0x7F0000+labels._fx_build_packet,0x7F0000+labels._fx_build_packet,emu.cpuType.snes,emu.memType.snesMemory)
  local selected={[238]=true,[478]=true,[718]=true}
  emu.addEventCallback(guard(function()
    if not selected[field] then return end
    local prefix=string.format('display%05d',field)
    dump(prefix..'_vram.bin',emu.memType.snesVideoRam,0,65536)
    dump(prefix..'_cgram.bin',emu.memType.snesCgRam,0,512)
    dump(prefix..'_oam.bin',emu.memType.snesSpriteRam,0,544)
    local meta={}
    for _,r in ipairs({{'v',0x1d04,500,0x7f0000},{'c1',0x1d06,128,0x7e0000},
        {'c3',0x1d08,128,0x7e0000},{'far',0x1d0c,10,0x7e0000},{'h',0x1d0e,270,0x7e0000},
        {'sky',0x1d16,10,0x7e0000}}) do
      local p=emu.read(0x7e0000+r[2],emu.memType.snesMemory)+256*emu.read(0x7e0000+r[2]+1,emu.memType.snesMemory)
      dump(prefix..'_'..r[1]..'.bin',emu.memType.snesMemory,r[4]+p,r[3])
    end
    local far=emu.read(0x7e1d0a,emu.memType.snesMemory)+256*emu.read(0x7e1d0b,emu.memType.snesMemory)
    if far>=32768 then far=far-65536 end
    -- 表示中の画像にラッチ済みの座標を読む。次画像のgame状態とは時点が異なる。
    meta.farY=far;meta.offset=23-far
    meta.nearX=emu.read(0x7e1d14,emu.memType.snesMemory)+256*emu.read(0x7e1d15,emu.memType.snesMemory)
    local fp=emu.read(0x7e1d0c,emu.memType.snesMemory)+256*emu.read(0x7e1d0d,emu.memType.snesMemory)
    meta.farX=emu.read(0x7e0001+fp,emu.memType.snesMemory)+256*emu.read(0x7e0002+fp,emu.memType.snesMemory)
    meta.skyBase=labels.fx_sky_colors
    local sf=assert(io.open(output..'/'..prefix..'_state.txt','w'))
    for k,v in pairs(emu.getState()) do if k:find('ppu') and (k:lower():find('scroll') or k:lower():find('bg')) then sf:write(k..'='..tostring(v)..'\n') end end
    sf:close()
    dump(prefix..'_skycolors.bin',emu.memType.snesMemory,0x7e0000+labels.fx_sky_colors,labels.fx_sky_colors_end-labels.fx_sky_colors)
    local f=assert(io.open(output..'/'..prefix..'.json','w'));f:write(encoded(meta));f:close()
  end),emu.eventType.startFrame)
  emu.addEventCallback(guard(function()
    if selected[field] then screenshot(string.format('display%05d',field)) end
    if scenario=='scenery' and field>=140 and field<=220 and field%4==0 then screenshot(string.format('parallax%05d',field)) end
  end),emu.eventType.endFrame)
end

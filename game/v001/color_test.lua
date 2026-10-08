-- 実入力のSELECT押下・保持・再押下と、奥行き/反転/clip/消去を一つのROMで検証。
local latched_draw,latched_logic,latched_mode,latched_count
local color_samples=0
local fixture_case,latched_case
local function memblob(mem,address,n)
  local b={};for i=0,n-1 do b[#b+1]=string.char(emu.read(address+i,mem)) end
  return table.concat(b)
end
emu.addMemoryCallback(guard(function()
  local n=read('_monosh_runtime_frame_counter',2)
  local case=n%8
  if field>=40 and field<=210 then case=0 end
  fixture_case=case
  local r={{48,196,52,122,4,0,80,0},{127,91,88,48,3,0,70,0},
           {146,170,100,68,13,0,60,0},{143,175,60,92,14,0,40,0},
           {223,117,36,54,7,0,30,0},{127,142,60,48,31,0,20,0}}
  if case==1 then r[4][6]=16;r[3][6]=32 end
  if case==2 then r[1][1]=-3;r[4][1]=256 end
  if case==3 then r[4][2]=40;r[3][2]=235;r[3][6]=32 end
  if case==4 then r[4][6]=128 end
  if case==5 then r={{128,180,1,1,13,0,20,0},{255,180,2,2,14,48,1,0}} end
  if case==6 then r={{128,160,20,20,14,0,1,0},{128,160,96,64,13,0,90,0},
                     {128,155,44,19,42,0,0,2},{128,150,32,48,9,0,0,2}} end
  if case==7 then r={{128,160,100,100,14,128,1,0},{128,160,0,0,13,0,1,0}} end
  for i,v in ipairs(r) do
    local b={v[1]&255,(v[1]>>8)&255,v[2]&255,(v[2]>>8)&255,v[3],v[4],v[5],v[6],v[7],v[8]}
    for j,c in ipairs(b) do put('_fx_draw',(i-1)*10+j-1,c) end
  end
  put('_fx_draw_count',0,#r)
end),emu.callbackType.exec,0x7f0000+labels._fx_build_packet,0x7f0000+labels._fx_build_packet,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
  latched_count=read('_fx_draw_count')
  latched_draw=memblob(emu.memType.snesMemory,0x7e0000+labels._fx_draw,latched_count*10)
  latched_logic=read('_monosh_runtime_frame_counter',2)
  latched_mode=read('fx_color_mode')
  latched_case=fixture_case
end),emu.callbackType.exec,0x7f0000+labels.fx_latch_color,0x7f0000+labels.fx_latch_color,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
  local line=emu.getState()['ppu.scanline']
  assert(line<=21 or line>=203,'color staging entered visible lines: '..line)
end),emu.callbackType.exec,0x7f0000+labels.fx_color_stage_done,0x7f0000+labels.fx_color_stage_done,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function(a,v)
  if v~=4 then return end
  color_samples=color_samples+1
  local name=string.format('color%04d',color_samples)
  local f=assert(io.open(output..'/'..name..'_draw.bin','wb'));f:write(latched_draw);f:close()
  dump(name..'_map.bin',emu.memType.snesVideoRam,read('fx_color_vram_base',2)*2,1536)
  dump(name..'_cgram.bin',emu.memType.snesCgRam,64,64)
  dump(name..'_ram.bin',emu.memType.snesMemory,0x7e0000+read('fx_color_present_ptr',2),768)
  f=assert(io.open(output..'/'..name..'.json','w'))
  f:write(encoded({count=latched_count,logic=latched_logic,case=latched_case,mode=latched_mode,field=field,line=emu.getState()['ppu.scanline']}));f:close()
  assert(read('fx_color_present_mode')==latched_mode,'color mode generation differs')
  assert(read('c_sp',2)>=0x1800,'C stack reached color RAM')
end),emu.callbackType.write,0x7e1df0,0x7e1df0)
emu.addEventCallback(guard(function()
  emu.setInput({select=(field>=60 and field<76) or (field>=150 and field<166)},0)
end),emu.eventType.inputPolled)
emu.addEventCallback(guard(function()
  if field==55 or field==110 or field==200 then screenshot('color_mode_'..field) end
end),emu.eventType.startFrame)

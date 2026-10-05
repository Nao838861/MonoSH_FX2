local jobs=JOBS
local report=assert(io.open(REPORT,"w"))
local outdir=OUTDIR
local active=nil
local index=0
local frame=0
local start=nil

local function fail(err)
  report:write("ERROR\t"..tostring(err).."\n")
  for k,v in pairs(emu.getState()) do if k:find("cpu.pc") or k:find("ppu.scanline") or k:find("ppu.hClock") then report:write(k.."="..tostring(v).."\n") end end
  report:write("command="..emu.read(0x7E1F00,emu.memType.snesMemory).." marker="..emu.read(0x7E1FF0,emu.memType.snesMemory).."\n")
  report:close();emu.stop(1)
end
emu.addMemoryCallback(function(a,v)
  local ok,err=pcall(function()
    if not active then return end
    if v==3 then
      local s=emu.getState()
      start={clock=s.masterClock,line=s["ppu.scanline"],dot=s["ppu.hClock"]}
    elseif v==4 then
      local s=emu.getState()
      local valid=0
      for i=0,active.bytes-1 do
        if emu.read(i,emu.memType.snesVideoRam)==255 then valid=valid+1 end
      end
      report:write(active.name.."\t"..(s.masterClock-start.clock).."\t"..start.line.."\t"..s["ppu.scanline"].."\t"..valid.."\t"..active.bytes.."\n")
      report:flush()
      local f=assert(io.open(outdir.."/"..active.name.."_vram.bin","wb"))
      local buf={}
      for i=0,65535 do buf[#buf+1]=string.char(emu.read(i,emu.memType.snesVideoRam)) end
      f:write(table.concat(buf));f:close()
    elseif v==5 then
      local raw=assert(io.open(outdir.."/"..active.name..".rgb","wb"))
      local rgb={}
      for _,v in ipairs(emu.getScreenBuffer()) do rgb[#rgb+1]=string.char((v>>16)&255,(v>>8)&255,v&255) end
      raw:write(table.concat(rgb));raw:close()
      active=nil
    end
  end)
  if not ok then fail(err) end
end,emu.callbackType.write,0x7E1FF0,0x7E1FF0)

emu.addEventCallback(function()
  local ok,err=pcall(function()
    frame=frame+1
    if active then assert(frame-active.frame<10,"DMA timeout");return end
    if emu.read(0x7E1FF0,emu.memType.snesMemory)~=16 then return end
    index=index+1
    if index>#jobs then report:close();emu.stop(0);return end
    active=jobs[index];active.frame=frame
    for i=0,active.bytes-1 do emu.write(0x2000+i,255,emu.memType.gsuWorkRam) end
    for i,v in ipairs(active.hdma) do emu.write(0x7E1100+i-1,v,emu.memType.snesMemory) end
    emu.write(0x7E1F01,0,emu.memType.snesMemory)
    emu.write(0x7E1F02,active.height,emu.memType.snesMemory)
    emu.write(0x7E1F04,active.bytes&255,emu.memType.snesMemory)
    emu.write(0x7E1F05,active.bytes>>8,emu.memType.snesMemory)
    emu.write(0x7E1F00,2,emu.memType.snesMemory)
  end)
  if not ok then fail(err) end
end,emu.eventType.endFrame)

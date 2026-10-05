-- 測定対象は実ROMのGSU。Pythonのホスト時間をFX2性能として使わない。
local jobs = JOBS
local report = assert(io.open(REPORT, "w"))
local outdir = OUTDIR
local labels = LABELS
local index = 0
local active = nil
local startClock = nil
local stopClock = nil
local frame = 0
local clockKey = nil

local function guarded(callback)
  return function(...)
    local ok,err=pcall(callback,...)
    if not ok then report:write("ERROR\t"..tostring(err).."\n");report:close();emu.stop(1) end
  end
end

local function write16(a, v)
  emu.write(a, v & 255, emu.memType.snesMemory)
  emu.write(a+1, (v >> 8) & 255, emu.memType.snesMemory)
end
local function gsuclock()
  local s = emu.getState()
  if not clockKey then
    for k,v in pairs(s) do
      if k=="cart.coprocessor.cycleCount" then clockKey=k end
    end
    assert(clockKey, "GSU cycleCount is unavailable")
    report:write("clock_key\t"..clockKey.."\n")
    report:flush()
  end
  return s[clockKey]
end

local names={"clear", "nearest", "nearest_unroll", "runs", "integer", "bounded", "runs_copy", "runs_half", "runs_quarter"}
for _,name in ipairs({"packed_copy","packed_half","packed_quarter"}) do names[#names+1]=name end
if labels.scene_entry then names[#names+1]="scene" end
for _,name in ipairs(names) do
  local entry = labels[name.."_entry"]
  local stop = labels[name.."_stop"]
  emu.addMemoryCallback(guarded(function()
    if active and ((active.kernel=="scene") == (name=="scene")) then startClock=gsuclock() end
  end), emu.callbackType.exec, entry, entry, emu.cpuType.gsu, emu.memType.gsuMemory)
  emu.addMemoryCallback(guarded(function()
    if active and ((active.kernel=="scene") == (name=="scene")) then stopClock=gsuclock() end
  end), emu.callbackType.exec, stop, stop, emu.cpuType.gsu, emu.memType.gsuMemory)
end

emu.addMemoryCallback(guarded(function(a,v)
  if v~=2 or not active then return end
  assert(startClock and stopClock, "GSU instruction callbacks did not run")
  local bytes={}
  for i=0,12287 do bytes[#bytes+1]=string.char(emu.read(0x2000+i,emu.memType.gsuWorkRam)) end
  local f=assert(io.open(outdir.."/"..active.name..".bin","wb"))
  f:write(table.concat(bytes)); f:close()
  local guard=true
  for i=0,31 do
    if emu.read(0x1FE0+i,emu.memType.gsuWorkRam)~=0xA5 or emu.read(0x5000+i,emu.memType.gsuWorkRam)~=0xA5 then guard=false end
  end
  report:write(active.name.."\t"..(stopClock-startClock+1).."\t"..tostring(guard).."\n")
  report:flush()
  active=nil
end),emu.callbackType.write,0x7E1FF0,0x7E1FF0)

emu.addEventCallback(guarded(function()
  frame=frame+1
  if active then
    assert(frame-active.frame<30,"GSU job timeout")
    return
  end
  if emu.read(0x7E1FF0,emu.memType.snesMemory)~=0x10 then return end
  index=index+1
  if index>#jobs then report:close(); emu.stop(0); return end
  active=jobs[index];active.frame=frame;startClock=nil;stopClock=nil
  for i=0,12287 do emu.write(0x2000+i,active.seed,emu.memType.gsuWorkRam) end
  for i=0,31 do
    emu.write(0x1FE0+i,0xA5,emu.memType.gsuWorkRam)
    emu.write(0x5000+i,0xA5,emu.memType.gsuWorkRam)
  end
  for i=0,15 do write16(0x7E1F20+2*i,active.regs[i+1] or 0) end
  emu.write(0x7E1F00,1,emu.memType.snesMemory)
end),emu.eventType.endFrame)

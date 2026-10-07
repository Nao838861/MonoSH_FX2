-- 専用ROMだけで、1/32区間の最大量を最終受付行へ意図的に揃える。
-- objectsの木はFB列11..20。列8からの各転送は木と全消去跡を包含する。
emu.addMemoryCallback(guard(function()
  if rendered==0 then return end -- 最初の全12KiB初期化はそのまま。
  local tiers=labels.dma_deadline_fine and 21 or 3
  local index=rendered%(2*tiers)
  local count=index<tiers and 1 or 32
  local weight
  if labels.dma_deadline_fine then
    local deadline=220+index%tiers
    weight=(math.min(9984,(279-deadline)*170-1)//16)*16
  else
    weight=({9984,8960,7680})[1+(index%3)]
  end
  local bytes=weight-count*64-768
  local start=count==1 and 3072 or 3328
  local function word(offset,value)
    emu.write(offset,value&255,emu.memType.gsuWorkRam)
    emu.write(offset+1,value>>8,emu.memType.gsuWorkRam)
  end
  word(8,count);word(10,bytes)
  local stride=(bytes//count//16)*16
  local position=start
  for i=0,count-1 do
    local length=i==count-1 and start+bytes-position or stride
    word(0x600+i*4,position//2);word(0x602+i*4,length)
    position=position+length
  end
end),emu.callbackType.exec,labels.render_stop,labels.render_stop,emu.cpuType.gsu,emu.memType.gsuMemory)

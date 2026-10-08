-- 専用ROMだけで、1/32区間の最大量を最終受付行へ意図的に揃える。
-- objectsの木はFB列11..20。列8からの各転送は木と全消去跡を包含する。
emu.addMemoryCallback(guard(function()
  if rendered==0 then return end -- 最初の全12KiB初期化はそのまま。
  -- Reserve is exercised, not merely assumed: change the mode every image.
  if labels.fx_color_present_mode then
    put('fx_color_present_mode',0,rendered%2)
  end
  local tiers=labels.dma_deadline_fine and ((labels.dma_last_line or 240)-219) or 3
  local index=rendered%(2*tiers)
  local count=index<tiers and 1 or 32
  local weight
  if labels.dma_deadline_fine then
    local deadline=220+index%tiers
    weight=(math.min(9984,(279-deadline)*170-1)//16)*16
  else
    weight=({9984,8960,7680})[1+(index%3)]
  end
  local color=0
  if labels.fx_upload_color then
    color=64
    if read('fx_color_staged',2)==0 then
      if labels.gsu_color_begin then
        local function word_at(a)
          return emu.read(a,emu.memType.gsuWorkRam)+256*emu.read(a+1,emu.memType.gsuWorkRam)
        end
        color=color+word_at(0x1602)+word_at(0x1600)*64
      else
        color=color+read('fx_color_dma_bytes',2)+read('fx_color_dma_count',2)*64
      end
    end
  end
  local bytes=weight-count*64-768-color
  assert(bytes>=count*16,'probe must never create a zero-length DMA span')
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

-- Verify the protected palette DMA even at admission lines 254/255.
emu.addMemoryCallback(guard(function(a,v)
  if v~=4 or not labels.fx_color_present_mode then return end
  local monochrome={0,0,0x63,0x0c,0x10,0x42,0xff,0x7f}
  for i=0,63 do
    local expected=read('fx_color_present_mode')==0 and monochrome[1+i%8]
      or emu.read(labels.color_palette+i,emu.memType.snesMemory)
    assert(emu.read(64+i,emu.memType.snesCgRam)==expected,'deadline probe CGRAM mismatch')
  end
  stats.dmaPaletteChecks=(stats.dmaPaletteChecks or 0)+1
end),emu.callbackType.write,0x7e1df0,0x7e1df0)

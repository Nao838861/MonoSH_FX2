-- test.luaへ挿入する観測専用コード。ROM・ゲーム状態は書き換えない。
-- CPUは次世代、GSUは提示予定の世代を並行処理するため、sceneは開始時に固定する。
local boss_report=assert(io.open(output..'/timings.jsonl','w'))
local probe,previous_dma=nil,nil
local function stamp()
  local s=emu.getState()
  return {clock=s.masterClock,line=s['ppu.scanline'],hclock=s['memoryManager.hClock'],
          ppuFrame=s['ppu.frameCount'],field=field}
end
emu.addMemoryCallback(guard(function(a,v)
  if v==1 then
    probe={start=stamp(),boss=read('_monosh_boss_state'),hp=read('_monosh_boss_hp'),
      logic=read('_monosh_runtime_frame_counter',2),player=read('_monosh_player_state'),
      x=read('_monosh_player_x',2),y=read('_monosh_player_bottom',2),
      enemyShots=read('_monosh_enemy_bullet_count'),shots=read('_monosh_player_bullet_count'),
      previousDma=previous_dma,commands=read('_fx_packet_count',2)}
  elseif v==2 then probe.joined=stamp()
  elseif v==3 then
    probe.dmaStart=stamp()
    probe.deadline=emu.read(0x7e1d10,emu.memType.snesMemory)
    probe.bytes=read('fx_dma_bytes',2);probe.spans=read('fx_dma_count',2)
  elseif v==4 then
    probe.dmaEnd=stamp();probe.image=rendered+1
    local work=(probe.gsuEnd.clock-probe.start.clock)&0xffffffff
    if probe.boss==1 and work>(stats.bossWorstGsuClocks or 0) then
      stats.bossWorstGsuClocks=work
      dump('worst_gsu_frame.bin',emu.memType.gsuWorkRam,0x2000,12288)
      dump('worst_gsu_packet.bin',emu.memType.gsuWorkRam,0,1312)
      dump('worst_gsu_oam.bin',emu.memType.snesSpriteRam,0,544)
      local f=assert(io.open(output..'/worst_gsu.json','w'));f:write(encoded(probe));f:close()
    end
    boss_report:write(encoded(probe)..'\n');boss_report:flush()
    previous_dma={start=probe.dmaStart,finish=probe.dmaEnd,bytes=probe.bytes}
  end
end),emu.callbackType.write,0x7e1df0,0x7e1df0)
emu.addMemoryCallback(guard(function() if probe then probe.cpuEnd=stamp() end end),
  emu.callbackType.exec,0x7f0000+labels.cpu_frame_return,0x7f0000+labels.cpu_frame_return,
  emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function() if probe then probe.gsuEnd=stamp() end end),
  emu.callbackType.exec,labels.render_stop,labels.render_stop,emu.cpuType.gsu,emu.memType.gsuMemory)
-- wait_bottom直前のSEPは各提示で1回だけ通る。VBlank待ちを処理時間へ含めない。
emu.addMemoryCallback(guard(function() if probe then probe.ready=stamp() end end),
  emu.callbackType.exec,0x7f0000+labels.admission_ready,0x7f0000+labels.admission_ready,
  emu.cpuType.snes,emu.memType.snesMemory)
-- HBlank待ちが完了した直後。以後の固定設定とOAM転送を待ち時間から分離する。
emu.addMemoryCallback(guard(function() if probe then probe.admitted=stamp() end end),
  emu.callbackType.exec,0x7f0000+labels.admitted,0x7f0000+labels.admitted,
  emu.cpuType.snes,emu.memType.snesMemory)

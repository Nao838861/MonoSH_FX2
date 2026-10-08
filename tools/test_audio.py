"""実ROMのAPUIO・DSP・SPCを観測し、SE・ポーズ・一周後の演奏を確認する。"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys

from build_game import ROOT, BUILD, GAME
from run_probe import prepare_runtime, MESEN_EXE, lua

SCRIPT = r'''
local labels=LABELS
local output=OUTDIR
local field=0
local initialized=false
local report=assert(io.open(output..'/trace.jsonl','w'))
local commands={}
local parameters={0,0,0,0}
local shots=0
local busyCalls=0
local audioStart=0
local audioMax=0
local audioSum=0
local audioCalls=0
local requested=nil
local scheduled=nil
local captured={}
local fixtures={}
local pauseTick=nil
local pauseStable=0
local restoredBoss=nil
local function read(name) return emu.read(0x7e0000+assert(labels[name]),emu.memType.snesMemory) end
local function put(name,v) emu.write(0x7e0000+assert(labels[name]),v,emu.memType.snesMemory) end
local function tick() return emu.read16(3,emu.memType.spcRam) end
local function dump(name,mt,count)
  local f=assert(io.open(output..'/'..name,'wb'))
  local bytes={}
  for i=0,count-1 do bytes[#bytes+1]=string.char(emu.read(i,mt)) end
  f:write(table.concat(bytes));f:close()
end
local function snapshot(name)
  dump(name..'.ram',emu.memType.spcRam,65536)
  dump(name..'.dsp',emu.memType.spcDspRegisters,128)
  local f=assert(io.open(output..'/'..name..'.state','w'))
  for k,v in pairs(emu.getState()) do
    if k:sub(1,4)=='spc.' and (type(v)=='number' or type(v)=='boolean') then f:write(k..'='..tostring(v)..'\n') end
  end
  if name:sub(1,3)=='sfx' then
    for i=1,4 do f:write('capture.port'..(i-1)..'='..parameters[i]..'\n') end
  end
  f:close()
end
local function guard(fn)
  return function(...)
    local ok,err=pcall(fn,...)
    if not ok then local f=io.open(output..'/error.txt','w');f:write(tostring(err));f:close();emu.stop(1) end
  end
end
emu.addMemoryCallback(guard(function(a,v)
  parameters[a-0x2140+1]=v
  if a==0x2140 and initialized then
    local cmd=v&0x1e
    if cmd==6 then
      local id=parameters[2]
      commands[id]=(commands[id] or 0)+1
      report:write(string.format('{"field":%d,"sfx":%d,"tick":%d}\n',field,id,tick()))
      if not captured[id] then requested='sfx'..id;captured[id]=true end
    elseif cmd==0 or cmd==4 then
      report:write(string.format('{"field":%d,"command":%d,"tick":%d}\n',field,cmd,tick()))
    end
  end
end),emu.callbackType.write,0x2140,0x2143,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function(a,v)
  if initialized and v&1~=0 then shots=shots+1 end
end),emu.callbackType.write,0x7e0000+labels._fx_audio_events,0x7e0000+labels._fx_audio_events,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
  initialized=true
  if field<550 or field>1000 then put('_monosh_player_invuln',255) end
  if field>=400 and not fixtures.stumble then
    put('_hit_pending',2);fixtures.stumble=true
  end
  if field>=600 and not fixtures.death then
    put('_monosh_player_invuln',0);put('_hit_pending',1);fixtures.death=true
  end
end),emu.callbackType.exec,0x7f0000+labels._fx_frame,0x7f0000+labels._fx_frame,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
  audioStart=emu.getState().masterClock
  if emu.read(0x3030,emu.memType.snesMemory)&0x20~=0 then busyCalls=busyCalls+1 end
  if field>=320 and not fixtures.explosion then put('_fx_audio_events',2);fixtures.explosion=true end
  if field>=360 and not fixtures.reflect then put('_fx_audio_events',4);fixtures.reflect=true end
  if field>=950 and not fixtures.boss then
    restoredBoss=read('_monosh_boss_state');put('_monosh_boss_state',2);fixtures.boss=true
  end
end),emu.callbackType.exec,labels.fx_audio_process,labels.fx_audio_process,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(guard(function()
  local ms=((emu.getState().masterClock-audioStart)&0xffffffff)/21477.272
  audioMax=math.max(audioMax,ms);audioSum=audioSum+ms;audioCalls=audioCalls+1
  if restoredBoss then put('_monosh_boss_state',restoredBoss);restoredBoss=nil end
end),emu.callbackType.exec,0x7f0000+labels.render_finished+4,0x7f0000+labels.render_finished+4,emu.cpuType.snes,emu.memType.snesMemory)
-- Driver v0.4.2 mainloopの命令境界でSPCを書き出す。
emu.addMemoryCallback(guard(function()
  if requested then snapshot(requested);requested=nil end
end),emu.callbackType.exec,0x0394,0x0394,emu.cpuType.spc,emu.memType.spcMemory)
emu.addEventCallback(guard(function()
  emu.setInput({a=field>=110 and field<300,start=(field>=1100 and field<=1103) or (field>=1220 and field<=1223)},0)
end),emu.eventType.inputPolled)
emu.addEventCallback(guard(function()
  field=field+1
  if field==305 then requested='bgm' end
  if scheduled and field>=scheduled.field then requested=scheduled.name;scheduled=nil end
  if field==1140 then pauseTick=tick() end
  if field>1140 and field<1200 then assert(tick()==pauseTick,'music advanced while paused');pauseStable=pauseStable+1 end
  if field%300==0 then
    local env={}
    for ch=0,7 do env[#env+1]=emu.read(ch*16+8,emu.memType.spcDspRegisters) end
    report:write(string.format('{"field":%d,"tick":%d,"env":[%s]}\n',field,tick(),table.concat(env,',')))
  end
  if field==MAXFRAME-5 then requested='loop' end
  if field>=MAXFRAME then
    for id=0,5 do assert(commands[id] and commands[id]>0,'missing sfx '..id) end
    assert(busyCalls==0,'audio API called while GSU running')
    assert(pauseStable==59,'pause not checked')
    assert(shots>=commands[5],'more shot sounds than actual spawns')
    if CHECKLOOP then assert(tick()>30720,'song has not crossed loop point') end
    local f=assert(io.open(output..'/summary.json','w'))
    local counts={};for id=0,5 do counts[#counts+1]=commands[id] end
    f:write(string.format('{"fields":%d,"ticks":%d,"sfxCommands":[%s],"spawns":%d,"busyCalls":%d,"pauseStableFields":%d,"audioCalls":%d,"audioMaxMs":%.6f,"audioMeanMs":%.6f}',field,tick(),table.concat(counts,','),shots,busyCalls,pauseStable,audioCalls,audioMax,audioSum/audioCalls))
    f:close();report:close();emu.stop(0)
  end
end),emu.eventType.endFrame)
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frames', type=int, default=16000)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--quick', action='store_true', help='SE試聴用の短い再確認。長時間試験とは別フォルダ。')
    args = parser.parse_args()
    output = BUILD / ('audio_quick' if args.quick else 'audio')
    output.mkdir(exist_ok=True)
    for p in output.iterdir():
        if p.is_file():
            p.unlink()
    labels = {m[2]: int(m[1], 16) for m in re.finditer(r'al ([0-9A-Fa-f]+) \.([^\s]+)', (BUILD / 'game.lbl').read_text())}
    script = SCRIPT.replace('LABELS', lua(labels)).replace('OUTDIR', lua(output.as_posix())).replace('MAXFRAME', str(args.frames))
    script = script.replace('CHECKLOOP', 'false' if args.quick else 'true')
    path = output / 'test.lua'
    path.write_text(script, encoding='utf-8')
    mesen = prepare_runtime(MESEN_EXE)
    settings = mesen.parent / 'settings.json'
    config = json.loads(settings.read_text())
    config['Snes']['Port1'] = {'Type': 'SnesController'}
    config['Debug']['ScriptWindow']['ScriptTimeout'] = 10
    settings.write_text(json.dumps(config))
    rom = BUILD / 'MonoSHFX2_v001.sfc'
    result = subprocess.run([str(mesen), '--testRunner', f'--timeout={args.timeout}',
        '--doNotSaveSettings', '--enableStdout', str(rom), str(path)], cwd=mesen.parent,
        capture_output=True, timeout=args.timeout + 10, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (output / 'emulator.log').write_bytes(result.stdout + result.stderr)
    if (output / 'error.txt').exists():
        print((output / 'error.txt').read_text())
    if result.returncode:
        print(result.stdout.decode(errors='replace'), result.stderr.decode(errors='replace'))
        raise SystemExit(result.returncode)
    assert all((output / f'sfx{i}.ram').exists() for i in range(6)), 'missing SFX snapshots'
    for ram in output.glob('*.ram'):
        state = dict(line.split('=', 1) for line in ram.with_suffix('.state').read_text().splitlines())
        # Mesenのflat stateのキーはspc.a等。opcode境界なのでPC/レジスタが整合する。
        def number(name):
            return int(state['spc.' + name])
        spc = bytearray((GAME / 'audio/theme.spc').read_bytes())
        struct.pack_into('<H5B', spc, 0x25, number('pc'), number('a'), number('x'),
                         number('y'), number('ps'), number('sp'))
        data = bytearray(ram.read_bytes())
        # RAMに鏡像のないI/Oを実際のSPC register値で補う。
        data[0xf2] = number('dspReg')
        for i in range(4):
            data[0xf4 + i] = int(state.get(f'capture.port{i}', number(f'cpuRegs[{i}]')))
        spc[0x100:0x10100] = data
        spc[0x10100:0x10180] = ram.with_suffix('.dsp').read_bytes()
        spc[0x101c0:0x10200] = data[0xffc0:]
        ram.with_suffix('.spc').write_bytes(spc)
    summary = json.loads((output / 'summary.json').read_text())
    summary['romSha256'] = hashlib.sha256(rom.read_bytes()).hexdigest()
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
